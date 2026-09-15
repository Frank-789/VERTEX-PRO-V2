"""内置工具集。"""

from __future__ import annotations

from ..core.tool_center import ToolCenter, ToolSpec

__all__ = ["register_all"]


def register_all(center: ToolCenter) -> None:
    """把全部内置工具注册进中心。

    每个工具单独 try —— 一个模块导入失败不影响其余工具。
    """
    specs: list[ToolSpec] = []

    try:
        from .ebay import EBAY_SEARCH

        specs.append(EBAY_SEARCH)
    except Exception:  # noqa: BLE001
        pass

    try:
        from .apify import APIFY_SCRAPE

        specs.append(APIFY_SCRAPE)
    except Exception:  # noqa: BLE001
        pass

    try:
        from .profit import PROFIT_CALC

        specs.append(PROFIT_CALC)
    except Exception:  # noqa: BLE001
        pass

    for spec in specs:
        center.register(spec)
