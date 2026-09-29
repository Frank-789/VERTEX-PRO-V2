"""定时任务的 HTTP 层。

    GET  /api/v1/issues            任务清单（含排期、上次、下次）
    POST /api/v1/issues/{id}/run   立刻跑一次，不等排期
    GET  /api/v1/inbox             报告清单（只带元信息，不带正文）
    GET  /api/v1/inbox/{name}      一份报告的全文

这一层刻意很薄 —— 扫描、判到点、执行全在 core 里，路由只做参数校验和翻译。
所有 `{id}` / `{name}` 都会被 `core` 里的正则挡一道，不允许路径穿越。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from ..core import inbox
from ..core import issues as issues_mod
from ..core.scheduler import AlreadyRunning, get_scheduler

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/issues")
async def list_issues() -> dict[str, Any]:
    """任务清单。

    把「文件里写的」和「状态里记的」拼在一起返回，前端一次拿全，
    不用自己再对一遍。坏掉的任务也照常列出来，并带上 `error` ——
    静默跳过会让用户以为文件没生效，实际上只是格式写错了。
    """
    state = issues_mod.load_state()
    out: list[dict[str, Any]] = []
    for issue in issues_mod.scan():
        entry = state.get(issue.id)
        item = issue.to_public()
        item.update(entry.to_public() if entry else {})
        nxt = issues_mod.next_fire(issue, entry) if entry else issues_mod.next_fire(
            issue, issues_mod.IssueState()
        )
        item["nextRun"] = nxt.isoformat() if nxt else None
        out.append(item)
    return {"issues": out, "scheduler": get_scheduler().status()}


@router.post("/issues/{issue_id}/run")
async def run_issue_now(issue_id: str) -> dict[str, Any]:
    """手动跑一次。

    走的是和定时完全相同的执行路径（`Scheduler._execute`），
    所以手动跑也会更新 `lastRun` —— 否则手动跑完，下一分钟定时又会再跑一次。
    """
    scheduler = get_scheduler()
    try:
        result = await scheduler.run_now(issue_id)
    except ValueError as exc:
        # id 不合法（含路径穿越）—— 400 而不是 404，这是格式问题
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"没有这个任务：{issue_id}") from exc
    except AlreadyRunning as exc:
        # 409 而不是 500：这不是错误，是「你等它跑完」
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result.to_public()


@router.get("/inbox")
async def list_inbox(limit: int = 50) -> dict[str, Any]:
    """报告清单，新的在前。默认只回元信息 —— 几十份报告全文一次拖出去太大。"""
    return {"reports": inbox.list_reports(limit=min(max(limit, 1), 200)), "total": inbox.count()}


@router.get("/inbox/{name}")
async def read_report(name: str) -> dict[str, Any]:
    try:
        return {"name": name, "content": inbox.read(name)}
    except inbox.BadReportName as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"没有这份报告：{name}") from exc
