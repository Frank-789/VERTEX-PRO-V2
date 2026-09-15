"""eBay 商品搜索（Browse API）。

第一代这个工具在拿不到密钥时会伪造一批假数据返回，这是危险的 ——
用户分不清哪条是真的。现在没配密钥就直接报错，前端会标注「未配置」。
"""

from __future__ import annotations

import json
import os

import httpx

from ..core.tool_center import ToolSpec

BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


async def ebay_search(keyword: str, limit: int = 20) -> str:
    token = os.getenv("EBAY_API_KEY", "").strip()
    if not token:
        raise RuntimeError("未配置 EBAY_API_KEY，无法调用 eBay API")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": os.getenv("EBAY_MARKETPLACE", "EBAY_US"),
    }
    params = {"q": keyword, "limit": min(max(limit, 1), 50)}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(BROWSE_URL, headers=headers, params=params)
        if resp.status_code >= 400:
            raise RuntimeError(f"eBay 返回 {resp.status_code}: {resp.text[:200]}")
        data = resp.json()

    items = []
    for it in data.get("itemSummaries", []):
        price = it.get("price") or {}
        items.append(
            {
                "标题": it.get("title"),
                "价格": f"{price.get('value')} {price.get('currency')}"
                if price.get("value")
                else None,
                "状况": (it.get("condition") or "").strip() or None,
                "链接": it.get("itemWebUrl"),
            }
        )

    return json.dumps(
        {"关键词": keyword, "命中": len(items), "商品": items},
        ensure_ascii=False,
        indent=2,
    )


EBAY_SEARCH = ToolSpec(
    name="ebay.search",
    label="eBay 搜索",
    description="在 eBay 上搜索在售商品，返回标题、价格、成色和链接。用户提到 eBay 或跨境出海时使用。",
    parameters={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "搜索关键词"},
            "limit": {"type": "integer", "description": "返回条数，1~50，默认 20"},
        },
        "required": ["keyword"],
    },
    handler=ebay_search,
    required_env=["EBAY_API_KEY"],
    source="realtime",
    tags=["跨境", "eBay"],
)
