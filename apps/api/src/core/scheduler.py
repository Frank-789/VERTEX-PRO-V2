"""调度器 —— 盯着 `data/issues/`，到点的就交给 runner 跑。

**为什么是一个进程内的循环，而不是 Celery / Redis / cron 服务**：
这个项目的部署形态是「跑起来就不停」（见 main.py 的生命周期注释），
任务定义又已经是文件了，再加一套需要单独运维的调度基础设施，
换来的只是「分布式」，而我们只有一台机器。真要横向扩，那时候再换也不亏 ——
因为**真相在文件里**，迁移成本只是换个读文件的进程。

**tick_once 和循环是分开的**：`tick_once` 是一次完整、可断言的调度决策，
测试直接调它，不用去和后台任务的时序搏斗。真出问题时也是先手动调它定位。
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone

from . import issues as issues_mod
from .issues import IssueState
from .runner import RunResult, run_issue

log = logging.getLogger(__name__)

TICK_SECONDS = float(os.getenv("ISSUE_TICK_SECONDS", "30") or 30)
MAX_PER_TICK = int(os.getenv("ISSUE_MAX_PER_TICK", "5") or 5)
"""一次 tick 最多跑几个任务。

防止「机器睡了一夜醒来，二十个任务同时开跑」把供应商的并发配额一次打满。
没跑到的下一个 tick 继续 —— 状态是「欠着」，不会丢。
"""


class AlreadyRunning(RuntimeError):
    """同一条任务上一次还没跑完。"""


def enabled() -> bool:
    return os.getenv("ISSUE_SCHEDULER", "1").strip().lower() not in ("0", "false", "no", "off")


class Scheduler:
    def __init__(self, tick_seconds: float = TICK_SECONDS) -> None:
        self.tick_seconds = tick_seconds
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()
        self._inflight: set[str] = set()
        self._last_error: str | None = None

    @property
    def running_ids(self) -> list[str]:
        return sorted(self._inflight)

    async def tick_once(self) -> list[RunResult]:
        """跑一轮调度决策，返回本轮实际执行的结果。"""
        now = datetime.now(timezone.utc)
        try:
            found = issues_mod.scan()
        except Exception as exc:  # noqa: BLE001
            self._last_error = f"扫描任务目录失败：{exc}"
            log.exception("扫描 data/issues 失败")
            return []

        if not found:
            return []

        state = issues_mod.load_state()
        results: list[RunResult] = []

        for issue in found:
            if len(results) >= MAX_PER_TICK:
                log.info("本轮已达上限 %d，剩余任务留到下一轮", MAX_PER_TICK)
                break
            if issue.id in self._inflight:
                continue

            entry = state.get(issue.id) or IssueState()
            due = issues_mod.pending_occurrence(issue, entry, now)
            if due is None:
                continue

            results.append(await self._execute(issue, state, due))

        return results

    async def run_now(self, issue_id: str) -> RunResult:
        """手动触发一次，不等排期。走和定时完全相同的执行路径。"""
        issue = issues_mod.get(issue_id)
        if issue is None:
            raise FileNotFoundError(issue_id)
        if issue_id in self._inflight:
            raise AlreadyRunning(f"任务 {issue_id} 上一次还在跑")

        state = issues_mod.load_state()
        return await self._execute(issue, state, None)

    async def _execute(self, issue, state: dict[str, IssueState], due) -> RunResult:
        # 先占坑再跑：两次 tick 之间不能重入，异步单线程下这里没有 await，
        # 检查与写入之间不会被切走
        self._inflight.add(issue.id)
        started = time.time()

        # **状态先于执行落盘**。反过来的话，跑到一半进程被杀，重启后
        # `lastRun` 还停在上一轮，这条任务会立刻再跑一次 —— 崩溃即死循环。
        # 代价是崩溃那次算「跑过了」，漏一班；宁可漏，不可循环。
        issues_mod.mark_run(state, issue.id, at=started, status="running", count=False)
        issues_mod.save_state(state)

        try:
            result = await run_issue(issue, scheduled_at=due)
        except Exception as exc:  # noqa: BLE001
            log.exception("任务 %s 抛出未捕获异常", issue.id)
            self._last_error = str(exc)
            issues_mod.mark_run(
                state, issue.id, at=started, status="failed", error=str(exc)
            )
            issues_mod.save_state(state)
            return RunResult(issue_id=issue.id, ok=False, duration_ms=0, error=str(exc))
        finally:
            self._inflight.discard(issue.id)

        issues_mod.mark_run(
            state,
            issue.id,
            at=started,
            status="ok" if result.ok else "failed",
            duration_ms=result.duration_ms,
            error=result.error,
        )
        issues_mod.save_state(state)
        return result

    # ── 生命周期 ─────────────────────────────────────────────

    async def _loop(self) -> None:
        log.info("调度器启动：每 %.0f 秒扫一次 data/issues/", self.tick_seconds)
        while not self._stopping.is_set():
            try:
                await self.tick_once()
            except Exception as exc:  # noqa: BLE001 —— 循环绝不能因为一次异常退出
                self._last_error = str(exc)
                log.exception("调度循环出错，下一轮继续")
            try:
                # 用 wait_for 而不是 sleep：停机时能被立刻叫醒，
                # 不用干等一个 tick
                await asyncio.wait_for(self._stopping.wait(), timeout=self.tick_seconds)
            except TimeoutError:
                pass
        log.info("调度器已停止")

    def start(self) -> None:
        if self._task is not None:
            return
        if not enabled():
            log.info("调度器已禁用（ISSUE_SCHEDULER=0）")
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._loop(), name="vertex-scheduler")

    async def stop(self) -> None:
        self._stopping.set()
        task, self._task = self._task, None
        if task is None:
            return
        try:
            await asyncio.wait_for(task, timeout=5)
        except (TimeoutError, asyncio.CancelledError):
            task.cancel()
            # 取回取消结果，避免留下「Task exception was never retrieved」告警
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

    def status(self) -> dict:
        return {
            "enabled": enabled(),
            "running": bool(self._task and not self._task.done()),
            "inflight": self.running_ids,
            "tickSeconds": self.tick_seconds,
            "lastError": self._last_error,
        }


_scheduler: Scheduler | None = None


def get_scheduler() -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler
