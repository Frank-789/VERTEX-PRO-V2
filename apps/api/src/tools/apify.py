"""Apify 采集（通用 Actor 执行器）。

Apify 上每个平台对应一个 Actor。不把 Actor ID 写死在代码里 ——
不同卖家会用不同的 Actor，放在环境变量里按平台配置。

    APIFY_TOKEN           必填
    APIFY_ACTOR_<PLATFORM>  可选，如 APIFY_ACTOR_AMAZON=junglee/amazon-crawler
    APIFY_DEFAULT_ACTOR     兜底 Actor
"""

from __future__ import annotations

import json
import os

import httpx

from ..core.tool_center import ToolSpec

APIFY_BASE = "https://api.apify.com/v2"


def _resolve_actor(platform: str | None) -> str | None:
    if platform:
        key = f"APIFY_ACTOR_{platform.upper().replace('-', '_')}"
        if actor := os.getenv(key, "").strip():
            return actor
    return os.getenv("APIFY_DEFAULT_ACTOR", "").strip() or None


async def apify_scrape(
    query: str,
    platform: str | None = None,
    limit: int = 20,
    actor: str | None = None,
) -> str:
    token = os.getenv("APIFY_TOKEN", "").strip()
    if not token:
        raise RuntimeError("未配置 APIFY_TOKEN")

    actor_id = actor or _resolve_actor(platform)
    if not actor_id:
        hint = f"APIFY_ACTOR_{(platform or '').upper()}" if platform else "APIFY_DEFAULT_ACTOR"
        raise RuntimeError(f"未指定 Actor，请配置环境变量 {hint}")

    # run-sync-get-dataset-items：同步跑完直接拿结果，省去轮询
    url = f"{APIFY_BASE}/acts/{actor_id.replace('/', '~')}/run-sync-get-dataset-items"
    payload = {"search": query, "query": query, "keyword": query, "maxItems": limit}

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(url, params={"token": token}, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"Apify 返回 {resp.status_code}: {resp.text[:200]}")
        items = resp.json()

    if not isinstance(items, list):
        items = [items]

    return json.dumps(
        {
            "平台": platform or "unknown",
            "Actor": actor_id,
            "关键词": query,
            "命中": len(items),
            "结果": items[:limit],
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    )


APIFY_SCRAPE = ToolSpec(
    name="apify.scrape",
    label="Apify 采集",
    description=(
        "通过 Apify Actor 采集电商平台商品数据。当用户要求采集 "
        "Amazon / Shopee / Shein / TikTok 等平台数据，且内置工具覆盖不到时使用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词或目标 URL"},
            "platform": {
                "type": "string",
                "description": "平台标识，如 amazon / shopee / shein",
            },
            "limit": {"type": "integer", "description": "返回条数，默认 20"},
        },
        "required": ["query"],
    },
    handler=apify_scrape,
    required_env=["APIFY_TOKEN"],
    source="realtime",
    tags=["采集", "Apify"],
)
