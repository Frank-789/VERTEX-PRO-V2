"""提示词加载：默认 + 用户覆盖。

    prompts/default/<name>.md   随仓库分发，进 git
    prompts/user/<name>.md      本地覆盖，不进 git

改提示词不需要动代码，也不需要在版本库里制造噪音。
第一代把 prompt 硬编码在 4 个文件、前后端各一份 —— 改一处必忘另一处。
"""

from __future__ import annotations

import logging
from functools import lru_cache

from .paths import prompts_dir

log = logging.getLogger(__name__)

# 默认人设：prompts 文件缺失时的兜底，保证服务永远能起来
_FALLBACK_PERSONA = (
    "你是 Vertex，一个陪中小电商卖家做经营决策的助手。"
    "先给结论再说依据，说人话，数字要具体，不确定就说不确定。"
)


def _read(name: str) -> str | None:
    """先找 user 覆盖，再找 default。"""
    for sub in ("user", "default"):
        path = prompts_dir() / sub / f"{name}.md"
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    return text
            except OSError as exc:
                log.warning("读取提示词 %s 失败：%s", path, exc)
    return None


@lru_cache(maxsize=8)
def get_prompt(name: str) -> str:
    text = _read(name)
    if text is None:
        log.warning("提示词 %s.md 不存在，使用兜底内容", name)
        return _FALLBACK_PERSONA if name == "persona" else ""
    return text


def reload_prompts() -> None:
    """开发期热重载。"""
    get_prompt.cache_clear()
