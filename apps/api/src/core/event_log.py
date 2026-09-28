"""事件日志（JSONL 追加写）。

与 `sessions/` 的分工 —— 这两者刻意不合并：

    sessions/<id>.jsonl      「对话」本身：谁说了什么。用来回灌模型历史。
    event-log/<日期>.jsonl    「运行过程」：每一步干了什么、多久、拿到什么。
                             用来排障和算成本，**模型永远看不到**。

所以工具调用的完整输出只在这里，会话文件里只有自然语言 ——
把工具原始返回塞进会话历史，既浪费上下文，也会污染下一轮的对话。

**按天分文件**，不按会话分：一次排障往往横跨好几个会话，
按会话分就得在几十个小文件里翻；按天分可以直接 `grep` 一天的量，
单个文件也不至于长到打不开。

**为什么是 JSONL**：和 sessions 同理 —— 追加写不会因为进程被杀而损坏已有内容。

**失败绝不抛异常**：日志是旁路，不能因为它写不进去就把整轮对话搞挂。
但会打 warning，免得静默丢数据没人发现。
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from .paths import data_home

log = logging.getLogger(__name__)

MAX_RESULT = 64_000
"""单条工具结果落盘的字符上限。超出截断并标 truncated。

设这么大是因为「完整输出」正是这个日志存在的理由；
但它不能无界，否则一个返回 50MB 的工具能把磁盘写满。
"""

MAX_PREVIEW = 500
"""用户发问只记前 500 字。

会话文件里已经有全文了，这里再存一份只是重复。
留个开头是为了让日志能自解释 —— 看到一行记录能想起「当时问的是什么」，
而不用再去翻 sessions/。
"""

DEFAULT_RETENTION_DAYS = 30


def _enabled() -> bool:
    """允许用环境变量整体关掉（例如在意用户内容落盘的部署）。"""
    return os.getenv("EVENT_LOG", "1").strip().lower() not in ("0", "false", "no", "off")


def _path(day: str) -> Path:
    d = data_home() / "event-log"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{day}.jsonl"


def write(record: dict[str, Any]) -> None:
    """追加一条记录。任何异常都吞掉 —— 但会留下 warning。"""
    if not _enabled():
        return
    try:
        day = time.strftime("%Y-%m-%d", time.localtime())
        rec = {"ts": round(time.time(), 3), **record}
        with _path(day).open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:  # noqa: BLE001
        log.warning("事件日志写入失败（不影响对话）：%s", exc)


def _clip(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_RESULT:
        return text, False
    return text[:MAX_RESULT], True


class Turn:
    """一轮对话的记录器。

    用法：

        turn = event_log.Turn(session_id="abc", user_message=msg)
        turn.tool(name="profit.calc", status="ok", ms=12, result=payload)
        turn.finish(steps=1, chars=456)

    刻意做成显式传参而不是 contextvars：调用点在 agent 循环里，
    显式传递一眼能看出「这里记了一笔」，隐式上下文容易漏。
    """

    def __init__(self, session_id: str | None, user_message: str = "") -> None:
        self.id = uuid.uuid4().hex[:12]
        self.session_id = session_id
        self._started = time.monotonic()
        self._steps = 0
        self._tools = 0
        write(
            {
                "type": "turn.start",
                "turn": self.id,
                "session": session_id,
                "preview": user_message[:MAX_PREVIEW],
                "chars": len(user_message),
            }
        )

    def tool(
        self,
        *,
        name: str,
        status: str,
        ms: int,
        args: dict[str, Any] | None = None,
        result: str | None = None,
        error: str | None = None,
        count: int | None = None,
    ) -> None:
        self._tools += 1
        rec: dict[str, Any] = {
            "type": "tool.call",
            "turn": self.id,
            # 每条都带 session，虽然 turn 已经能追回去 ——
            # 排查时最常见的动作是 `grep <会话id>`，多一个字段就不用先查 turn.start
            "session": self.session_id,
            "name": name,
            "status": status,
            "ms": ms,
        }
        if args:
            rec["args"] = args
        if count is not None:
            rec["count"] = count
        if error:
            rec["error"] = error
        if result is not None:
            clipped, truncated = _clip(result)
            rec["result"] = clipped
            rec["resultChars"] = len(result)
            rec["truncated"] = truncated
        write(rec)

    def step(self) -> None:
        """完成一轮「问模型 → 执行工具」。"""
        self._steps += 1

    def finish(self, *, chars: int = 0, ok: bool = True) -> None:
        write(
            {
                "type": "turn.end",
                "turn": self.id,
                "session": self.session_id,
                "ms": int((time.monotonic() - self._started) * 1000),
                "steps": self._steps,
                "tools": self._tools,
                "chars": chars,
                "ok": ok,
            }
        )

    def error(self, message: str) -> None:
        write(
            {
                "type": "error",
                "turn": self.id,
                "session": self.session_id,
                "message": message,
            }
        )


def prune(days: int = DEFAULT_RETENTION_DAYS) -> int:
    """删掉超过保留期的按天文件。返回删除数量。幂等，启动时调一次即可。"""
    cutoff = time.time() - days * 86400
    removed = 0
    d = data_home() / "event-log"
    if not d.is_dir():
        return 0
    for f in d.glob("*.jsonl"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            continue
    if removed:
        log.info("事件日志清理：删除 %d 个超过 %d 天的文件", removed, days)
    return removed
