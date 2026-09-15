"""配置加载：配置即数据。

JSON 文件 + pydantic 校验 + 缺省回退。
配置文件缺失不该让服务起不来 —— 回退到内置默认值，并在日志里说清楚。
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from .paths import config_dir

log = logging.getLogger(__name__)


class ProviderSpec(BaseModel):
    id: str
    provider: str = "openai-compat"
    base_url: str
    model: str
    api_key_env: str
    timeout: float = 60.0


class ProvidersConfig(BaseModel):
    chat: list[ProviderSpec] = Field(default_factory=list)
    planning: list[ProviderSpec] = Field(default_factory=list)


DEFAULTS: dict[str, Any] = {
    "providers": {
        "chat": [
            {
                "id": "deepseek",
                "provider": "openai-compat",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "api_key_env": "DEEPSEEK_API_KEY",
                "timeout": 60,
            }
        ],
        "planning": [],
    }
}


def _read_json(path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("配置文件 %s 读取失败，改用默认值：%s", path, exc)
        return None


@lru_cache(maxsize=1)
def load_providers() -> ProvidersConfig:
    """读取 config/providers.json，失败则回退默认值。"""
    raw = _read_json(config_dir() / "providers.json")
    if raw is None:
        log.info("未找到 providers.json，使用内置默认配置")
        raw = DEFAULTS["providers"]

    # 去掉以 $ 开头的注释键
    raw = {k: v for k, v in raw.items() if not k.startswith("$")}
    if not raw.get("planning"):
        raw["planning"] = raw.get("chat", [])

    try:
        return ProvidersConfig.model_validate(raw)
    except ValidationError as exc:
        log.error("providers.json 校验失败，回退默认值：%s", exc)
        return ProvidersConfig.model_validate(DEFAULTS["providers"])


def reload_config() -> None:
    """开发期热重载。"""
    load_providers.cache_clear()
