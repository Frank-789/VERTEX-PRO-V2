"""对话 HTTP 层。

把 agent 产出的结构化事件翻译成 SSE。协议沿用第一代，前端不用改：

    event: tool_call   data: {id, name, label, status, source, count, durationMs, error, detail}
    event: chunk       data: {text}
    event: done        data: {sessionId}
    event: error       data: {message}

SSE 三处容易踩的坑，这里都处理了：
  1. 事件之间必须空行分隔，否则浏览器会把两条粘成一条
  2. JSON 里不能出现裸换行 —— 用 ensure_ascii=False + 手动转义
  3. 中间层（Nginx / 反代）会缓冲响应，必须显式声明 no-cache 和 X-Accel-Buffering
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ..core import event_log, session
from ..core.agent import ErrorEvent, TextChunk, ToolEvent, run_turn
from ..core.paths import ensure_dirs
from ..core.tool_center import get_tool_center

log = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = Field(default=None, alias="sessionId")
    platform: str | None = None
    stream: bool = True

    model_config = {"populate_by_name": True}

    @field_validator("session_id")
    @classmethod
    def _check_session_id(cls, v: str | None) -> str | None:
        # 会话 id 会被拼进文件路径，在入口就卡死，别让它有机会到磁盘层
        if v is not None and not session.is_valid_id(v):
            raise ValueError("会话 id 只能包含字母、数字、下划线和连字符，且不超过 64 位")
        return v


def _sse(event: str, data: dict[str, Any]) -> str:
    body = json.dumps(data, ensure_ascii=False).replace("\n", "\\n")
    return f"event: {event}\ndata: {body}\n\n"


async def _event_stream(req: ChatRequest) -> AsyncIterator[str]:
    session_id = req.session_id or session.new_session_id()
    history = session.history(session_id) if req.session_id else []
    session.append(session_id, "user", req.message)

    answer: list[str] = []
    turn = event_log.Turn(session_id=session_id, user_message=req.message)
    ok = True
    try:
        async for ev in run_turn(
            req.message, history=history, platform=req.platform, turn=turn
        ):
            if isinstance(ev, TextChunk):
                answer.append(ev.text)
                yield _sse("chunk", {"text": ev.text})
            elif isinstance(ev, ToolEvent):
                payload = asdict(ev)
                # 前端用 camelCase
                payload["durationMs"] = payload.pop("duration_ms")
                yield _sse("tool_call", payload)
            elif isinstance(ev, ErrorEvent):
                yield _sse("error", {"message": ev.message})
    except Exception as exc:  # noqa: BLE001 —— 流已经开始，只能把错误发下去
        ok = False
        log.exception("对话出错")
        turn.error(f"服务异常：{exc}")
        yield _sse("error", {"message": f"服务异常：{exc}"})
    finally:
        if answer:
            session.append(session_id, "assistant", "".join(answer))
        turn.finish(chars=sum(len(a) for a in answer), ok=ok)
        yield _sse("done", {"sessionId": session_id})


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    ensure_dirs()
    return StreamingResponse(
        _event_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 让 Nginx 别缓冲
        },
    )


@router.get("/tools")
async def tools() -> dict[str, Any]:
    """能力清单。前端用它展示「哪些工具可用、哪些缺配置」。"""
    center = get_tool_center()
    return {"tools": center.public_listing()}
