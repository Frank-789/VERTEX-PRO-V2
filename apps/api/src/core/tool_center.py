"""统一工具注册表。

第一代有两套互不相通的注册表 —— tools/registry.py（4 个平台工具）和
crawler/registry.py（7 个采集平台）。同一个能力在两个地方各注册一次，
UI 拿不到全局视图，Agent 也不知道对方存在。

这里合并成一个 ToolCenter：能力只注册一次，同时导出给
  · Agent（OpenAI function-calling 格式）
  · 前端（健康状态与能力清单）
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    """一个可被 Agent 调用的能力。"""

    name: str
    """机器标识，如 alibaba.search。"""
    label: str
    """人类可读名，如「1688 搜索」。"""
    description: str
    """给模型看的说明 —— 这句话的质量直接决定模型用得对不对。"""
    parameters: dict[str, Any]
    """JSON Schema。"""
    handler: Callable[..., Any]
    required_env: list[str] = field(default_factory=list)
    source: str = "realtime"
    """数据来源可信度，前端会标注出来。"""
    tags: list[str] = field(default_factory=list)

    def missing_env(self) -> list[str]:
        import os

        return [k for k in self.required_env if not os.getenv(k, "").strip()]

    def is_ready(self) -> bool:
        return not self.missing_env()

    def to_openai(self) -> dict[str, Any]:
        """导出为 OpenAI function-calling 工具定义。"""
        return {
            "type": "function",
            "function": {
                "name": self.name.replace(".", "_"),
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_public(self) -> dict[str, Any]:
        """导出给前端的公开信息 —— 不含 handler。"""
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "source": self.source,
            "tags": self.tags,
            "ready": self.is_ready(),
            "required_env": self.required_env,
        }


class ToolCenter:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        # 模型看到的函数名不能带点，这里做一次映射
        self._by_fn_name: dict[str, str] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            log.warning("工具 %s 重复注册，后者覆盖前者", spec.name)
        self._tools[spec.name] = spec
        self._by_fn_name[spec.name.replace(".", "_")] = spec.name

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def resolve_fn(self, fn_name: str) -> ToolSpec | None:
        """把模型返回的函数名还原成工具。"""
        real = self._by_fn_name.get(fn_name)
        return self._tools.get(real) if real else None

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def ready(self) -> list[ToolSpec]:
        return [t for t in self._tools.values() if t.is_ready()]

    def openai_tools(self) -> list[dict[str, Any]]:
        """只导出已就绪的工具 —— 让模型看不见用不了的选项，少犯错。"""
        return [t.to_openai() for t in self.ready()]

    def public_listing(self) -> list[dict[str, Any]]:
        """全部工具（含未就绪），供前端展示配置缺口。"""
        return [t.to_public() for t in self.all()]

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        spec = self.get(name) or self.resolve_fn(name)
        if spec is None:
            raise KeyError(f"未知工具：{name}")
        missing = spec.missing_env()
        if missing:
            raise RuntimeError(f"{spec.label} 未配置：缺少 {', '.join(missing)}")

        result = spec.handler(**arguments)
        if inspect.isawaitable(result):
            result = await result
        return result


_center: ToolCenter | None = None


def get_tool_center() -> ToolCenter:
    global _center
    if _center is None:
        _center = ToolCenter()
        _register_builtin(_center)
    return _center


def _register_builtin(center: ToolCenter) -> None:
    """注册内置工具。

    导入放在函数内部：某个工具依赖装不上时，不该拖垮整个服务启动。
    第一代就是因为在模块顶层 import 了需要 Chromium 的工具，
    容器里没装浏览器导致注册直接抛异常。
    """
    try:
        from ..tools import register_all

        register_all(center)
    except Exception as exc:  # noqa: BLE001
        log.error("内置工具注册失败：%s", exc)
