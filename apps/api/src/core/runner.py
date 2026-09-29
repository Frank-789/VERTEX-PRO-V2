"""任务执行器 —— 把一条 Issue 跑成一封 Inbox 报告。

复用 `agent.run_turn`，所以定时任务和对话**走的是同一套 Agent 循环与工具**，
不存在「定时任务版 agent」这种需要单独维护的第二实现。

和对话的差别只有三点：
  1. 没有会话历史（任务每次独立跑，不带上下文）
  2. 产出的文字不推给谁看，而是落成一封报告
  3. 有硬性超时 —— 对话挂了用户会重发，定时任务挂了不能一直占着
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import event_log, inbox
from .agent import ErrorEvent, TextChunk, ToolEvent, run_turn
from .issues import Issue

log = logging.getLogger(__name__)

RUN_TIMEOUT_SECONDS = 300.0
"""单次任务的墙上时间上限。

比对话宽松（对话靠用户等不及了自己打断，任务没人盯着），但不能没有 ——
一个卡死的采集任务会把调度器后面的任务全堵住。
"""


@dataclass
class RunResult:
    issue_id: str
    ok: bool
    duration_ms: int
    steps: int = 0
    tools: list[str] = field(default_factory=list)
    turn_id: str = ""
    error: str | None = None
    report: Path | None = None
    answer: str = ""

    def to_public(self) -> dict:
        return {
            "issueId": self.issue_id,
            "ok": self.ok,
            "durationMs": self.duration_ms,
            "steps": self.steps,
            "tools": self.tools,
            "turn": self.turn_id,
            "error": self.error,
            "report": self.report.name if self.report else None,
        }


@dataclass
class _Sink:
    """收集 agent 事件流。做成小对象是为了让超时分支也能读到已收到的内容 ——
    跑到一半超时，已经产出的文字不该丢。"""

    text: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    steps: int = 0
    error: str | None = None

    @property
    def answer(self) -> str:
        return "".join(self.text)


async def _consume(issue: Issue, turn: event_log.Turn, sink: _Sink) -> None:
    # aclosing 保证即使被 wait_for 取消，生成器也会被显式关掉，
    # 不会留下一个还挂在供应商 HTTP 连接上的半死循环
    async with contextlib.aclosing(run_turn(issue.instruction, turn=turn)) as stream:
        async for ev in stream:
            if isinstance(ev, TextChunk):
                sink.text.append(ev.text)
            elif isinstance(ev, ToolEvent):
                if ev.status == "running":
                    sink.steps += 1
                elif ev.status == "ok" and ev.name not in sink.tools:
                    sink.tools.append(ev.name)
            elif isinstance(ev, ErrorEvent):
                sink.error = ev.message


def _timeout_note(seconds: float) -> str:
    return f"任务超过 {int(seconds)} 秒未结束，已中断"


async def run_issue(
    issue: Issue,
    *,
    scheduled_at: datetime | None = None,
    timeout: float = RUN_TIMEOUT_SECONDS,
) -> RunResult:
    """跑一条任务，并把结果写进 Inbox。

    **无论成功失败都会写报告** —— 失败也是结果。一个每天早上九点该到的报告
    没出现，用户分不清是「任务没跑」还是「跑了但没话说」，所以失败要留痕。
    """
    started = time.monotonic()
    turn = event_log.Turn(session_id=f"issue-{issue.id}", user_message=issue.instruction)
    sink = _Sink()

    try:
        await asyncio.wait_for(_consume(issue, turn, sink), timeout=timeout)
    except TimeoutError:
        # Python 3.11 起 asyncio.TimeoutError 就是内置 TimeoutError
        sink.error = _timeout_note(timeout)
        log.warning("任务 %s 超时（%.0fs）", issue.id, timeout)
    except Exception as exc:  # noqa: BLE001 —— 任务失败不该把调度器带崩
        sink.error = f"执行异常：{exc}"
        log.exception("任务 %s 执行异常", issue.id)

    elapsed = int((time.monotonic() - started) * 1000)
    ok = sink.error is None
    run_at = datetime.now(timezone.utc)

    body = sink.answer.strip()
    if not ok:
        # 失败时正文写成错误说明，报告本身就是「这次为什么没结果」的答案
        body = f"**任务未能完成。**\n\n{sink.error}\n\n"
        if body and sink.answer.strip():
            body += f"中断前已产出的内容：\n\n{sink.answer.strip()}\n"
    elif not body:
        body = "任务跑完了，但模型没有产出任何内容。"

    report = inbox.write(
        issue_id=issue.id,
        title=issue.title,
        body=body,
        run_at=run_at,
        scheduled_at=scheduled_at,
        duration_ms=elapsed,
        ok=ok,
        steps=sink.steps,
        tools=sink.tools,
        turn=turn.id,
        error=sink.error,
    )

    turn.finish(chars=len(sink.answer), ok=ok)
    if not ok:
        turn.error(sink.error or "未知错误")

    result = RunResult(
        issue_id=issue.id,
        ok=ok,
        duration_ms=elapsed,
        steps=sink.steps,
        tools=sink.tools,
        turn_id=turn.id,
        error=sink.error,
        report=report,
        answer=sink.answer,
    )
    log.info(
        "任务 %s %s：%dms，%d 步，工具 %s",
        issue.id,
        "完成" if ok else "失败",
        elapsed,
        sink.steps,
        ", ".join(sink.tools) or "无",
    )
    return result
