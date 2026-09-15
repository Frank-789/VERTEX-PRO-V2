"""供应商路由。

第一代把 DeepSeek→Kimi 的降级逻辑在前后端各写了一遍，改一处必忘另一处。
这里收敛成唯一实现：调用方只说「我要 chat」，路由按配置顺序尝试。

密钥只在服务端读取 —— 客户端永远拿不到 api_key。
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

import httpx

from .config import ProviderSpec, load_providers

log = logging.getLogger(__name__)


class ProviderUnavailable(RuntimeError):
    """所有候选项都不可用。"""


class ProviderRouter:
    def __init__(self) -> None:
        self._cfg = load_providers()

    def _candidates(self, capability: str) -> list[ProviderSpec]:
        specs = getattr(self._cfg, capability, None) or self._cfg.chat
        # 只保留配了密钥的
        return [s for s in specs if os.getenv(s.api_key_env, "").strip()]

    def available(self, capability: str = "chat") -> list[str]:
        """已配置密钥、可用的供应商 id 列表。"""
        return [s.id for s in self._candidates(capability)]

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        capability: str = "chat",
        temperature: float = 0.7,
    ) -> AsyncIterator[tuple[str, str]]:
        """流式生成。

        产出 (provider_id, text_delta) 二元组 —— 带上 provider_id 是为了
        在降级发生时能让调用方知道究竟是谁答的。
        """
        candidates = self._candidates(capability)
        if not candidates:
            raise ProviderUnavailable(
                f"没有可用的 AI 供应商（capability={capability}）。"
                "请在后端 .env 里配置 DEEPSEEK_API_KEY。"
            )

        last_error: Exception | None = None
        for spec in candidates:
            api_key = os.getenv(spec.api_key_env, "").strip()
            try:
                async for delta in self._stream_one(spec, api_key, messages, temperature):
                    yield spec.id, delta
                return
            except Exception as exc:  # noqa: BLE001 —— 降级需要兜住任何异常
                last_error = exc
                log.warning("供应商 %s 失败，尝试下一个：%s", spec.id, exc)
                continue

        raise ProviderUnavailable(f"全部供应商均失败：{last_error}") from last_error

    async def _stream_one(
        self,
        spec: ProviderSpec,
        api_key: str,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> AsyncIterator[str]:
        """对单个 OpenAI 兼容端点做流式请求。"""
        url = f"{spec.base_url.rstrip('/')}/v1/chat/completions"
        payload = {
            "model": spec.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=spec.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")[:400]
                    raise RuntimeError(f"{spec.id} 返回 {resp.status_code}: {body}")

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        chunk = httpx.Response(200, content=data).json()
                    except Exception:  # noqa: BLE001
                        continue
                    for choice in chunk.get("choices", []):
                        delta = (choice.get("delta") or {}).get("content")
                        if delta:
                            yield delta

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        capability: str = "chat",
        temperature: float = 0.7,
    ) -> str:
        """非流式，拼完整结果。"""
        parts: list[str] = []
        async for _pid, delta in self.stream(
            messages, capability=capability, temperature=temperature
        ):
            parts.append(delta)
        return "".join(parts)

    async def complete_message(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        capability: str = "chat",
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """非流式，返回完整的 message 对象（含 tool_calls）。

        Agent 循环用它做「要不要调工具」的判断。流式模式下 tool_calls 的
        分片重组很容易出错，所以这里刻意走非流式 —— 换来的是可预测性。
        """
        candidates = self._candidates(capability)
        if not candidates:
            raise ProviderUnavailable(
                f"没有可用的 AI 供应商（capability={capability}）。"
                "请在后端 .env 里配置 DEEPSEEK_API_KEY。"
            )

        last_error: Exception | None = None
        for spec in candidates:
            api_key = os.getenv(spec.api_key_env, "").strip()
            url = f"{spec.base_url.rstrip('/')}/v1/chat/completions"
            payload: dict[str, Any] = {
                "model": spec.model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            try:
                async with httpx.AsyncClient(timeout=spec.timeout) as client:
                    resp = await client.post(
                        url,
                        json=payload,
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    if resp.status_code >= 400:
                        raise RuntimeError(
                            f"{spec.id} 返回 {resp.status_code}: {resp.text[:300]}"
                        )
                    data = resp.json()
                return data["choices"][0]["message"]
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                log.warning("供应商 %s 失败，尝试下一个：%s", spec.id, exc)
                continue

        raise ProviderUnavailable(f"全部供应商均失败：{last_error}") from last_error


@lru_cache(maxsize=1)
def get_router() -> ProviderRouter:
    return ProviderRouter()
