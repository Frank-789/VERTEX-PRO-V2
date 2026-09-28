"""Agent 循环。

一轮对话的流程：
    1. 带工具清单问模型「要不要调工具」
    2. 要调就执行，把结果回灌，再问一次（最多 MAX_STEPS 轮）
    3. 不再调工具时，流式产出最终回答

产出的是结构化事件，由 HTTP 层翻译成 SSE。这样 agent 逻辑与传输协议解耦，
将来接 WebSocket 或命令行都不用改这里。
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from . import event_log
from .prompts import get_prompt
from .provider_router import ProviderUnavailable, get_router
from .tool_center import get_tool_center

log = logging.getLogger(__name__)

MAX_STEPS = 4
"""最多连续调几轮工具。超过就强制模型作答，避免无限循环烧 token。"""


@dataclass
class TextChunk:
    text: str


@dataclass
class ToolEvent:
    id: str
    name: str
    label: str
    status: str  # running | ok | failed
    source: str | None = None
    count: int | None = None
    duration_ms: int | None = None
    error: str | None = None
    detail: str | None = None


@dataclass
class ErrorEvent:
    message: str


Event = TextChunk | ToolEvent | ErrorEvent


def _build_messages(
    user_message: str,
    history: list[dict[str, Any]] | None,
    platform: str | None,
) -> list[dict[str, Any]]:
    system = get_prompt("persona")

    ready = get_tool_center().ready()
    if ready:
        listing = "\n".join(f"- {t.label}（{t.name}）：{t.description}" for t in ready)
        system += f"\n\n## 你可以调用的工具\n\n{listing}\n\n有工具能回答的问题，先调工具拿数据，不要凭印象回答。"
    else:
        system += "\n\n## 注意\n\n当前没有已配置的数据采集工具。涉及实时数据的问题，直说拿不到，不要编造。"

    if platform:
        system += f"\n\n用户关注的平台是「{platform}」。"

    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    if history:
        # 只带最近若干轮，防止上下文无限增长
        messages.extend(history[-20:])
    messages.append({"role": "user", "content": user_message})
    return messages


def _count_items(payload: str) -> int | None:
    """尽力从工具输出里数出条目数，纯粹为了 UI 上那一行摘要。"""
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(data, dict):
        for key in ("命中", "count", "total"):
            if isinstance(data.get(key), int):
                return data[key]
        for key in ("商品", "结果", "items", "results"):
            if isinstance(data.get(key), list):
                return len(data[key])
    if isinstance(data, list):
        return len(data)
    return None


async def run_turn(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    platform: str | None = None,
    turn: event_log.Turn | None = None,
) -> AsyncIterator[Event]:
    """跑一轮对话，产出事件流。

    `turn` 是可选的事件日志记录器。传 None 就完全不落盘 ——
    测试和一次性脚本不必为此建目录。
    """
    router = get_router()
    center = get_tool_center()
    messages = _build_messages(user_message, history, platform)
    tools = center.openai_tools()

    # ---- 阶段一：工具轮 ----
    for _step in range(MAX_STEPS):
        if not tools:
            break

        try:
            msg = await router.complete_message(messages, tools=tools)
        except ProviderUnavailable as exc:
            if turn:
                turn.error(str(exc))
            yield ErrorEvent(str(exc))
            return

        calls = msg.get("tool_calls") or []
        if not calls:
            break

        if turn:
            turn.step()
        messages.append(msg)

        for call in calls:
            fn = call.get("function") or {}
            fn_name = fn.get("name", "")
            call_id = call.get("id") or fn_name

            spec = center.resolve_fn(fn_name)
            label = spec.label if spec else fn_name
            tool_name = spec.name if spec else fn_name

            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}

            yield ToolEvent(
                id=call_id, name=tool_name, label=label, status="running",
                source=spec.source if spec else None,
            )

            started = time.monotonic()
            try:
                result = await center.call(tool_name, args)
                payload = result if isinstance(result, str) else json.dumps(
                    result, ensure_ascii=False, default=str
                )
                elapsed = int((time.monotonic() - started) * 1000)
                count = _count_items(payload)
                if turn:
                    # 这里落**完整**输出；给前端的 detail 截到 4000 是为了别把
                    # SSE 撑爆，但日志存在的意义恰恰是留下原始返回
                    turn.tool(
                        name=tool_name, status="ok", ms=elapsed,
                        args=args, result=payload, count=count,
                    )
                yield ToolEvent(
                    id=call_id, name=tool_name, label=label, status="ok",
                    source=spec.source if spec else None,
                    count=count,
                    duration_ms=elapsed,
                    detail=payload[:4000],
                )
            except Exception as exc:  # noqa: BLE001
                elapsed = int((time.monotonic() - started) * 1000)
                payload = f"工具调用失败：{exc}"
                if turn:
                    turn.tool(
                        name=tool_name, status="failed", ms=elapsed,
                        args=args, error=str(exc),
                    )
                yield ToolEvent(
                    id=call_id, name=tool_name, label=label, status="failed",
                    duration_ms=elapsed, error=str(exc),
                )

            messages.append(
                {"role": "tool", "tool_call_id": call_id, "content": payload}
            )

    # ---- 阶段二：流式作答（不再给工具，逼模型输出文字）----
    try:
        async for _provider, delta in router.stream(messages):
            yield TextChunk(delta)
    except ProviderUnavailable as exc:
        yield ErrorEvent(str(exc))
