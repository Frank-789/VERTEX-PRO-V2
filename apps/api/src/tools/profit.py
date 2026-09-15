"""利润测算。

这个工具不需要任何凭证 —— 它是纯计算，但价值不低：
卖家最常算错的就是平台佣金、运费和退货率的叠加影响。
"""

from __future__ import annotations

import json

from ..core.tool_center import ToolSpec

# 各平台常见费率（佣金 + 支付通道费），只作默认值，调用方可覆盖
PLATFORM_FEE = {
    "淘宝": 0.05,
    "天猫": 0.08,
    "拼多多": 0.006,
    "京东": 0.08,
    "1688": 0.0,
    "ebay": 0.13,
    "amazon": 0.15,
    "shopee": 0.06,
    "shein": 0.1,
}


def profit_calc(
    cost: float,
    price: float,
    platform: str = "淘宝",
    shipping: float = 0.0,
    return_rate: float = 0.03,
    other_cost: float = 0.0,
    fee_rate: float | None = None,
) -> str:
    """算单件利润与保本点。

    Args:
        cost: 进货成本（含国内运费）
        price: 售价
        platform: 平台名，用于取默认佣金率
        shipping: 每单发货成本
        return_rate: 退货率 0~1
        other_cost: 其他单件成本（包装、赠品等）
        fee_rate: 覆盖默认佣金率
    """
    rate = fee_rate if fee_rate is not None else PLATFORM_FEE.get(platform, 0.05)

    fee = price * rate
    # 退货的损失按「来回运费 + 一次发货成本」估，商品本身可二次销售
    return_loss = return_rate * (shipping * 2 + other_cost)
    unit_cost = cost + shipping + other_cost + return_loss
    profit = price - fee - unit_cost
    margin = profit / price if price else 0.0

    # 保本售价：使 profit == 0 的 price
    denom = 1 - rate
    breakeven = unit_cost / denom if denom > 0 else float("inf")

    result = {
        "平台": platform,
        "佣金率": f"{rate:.1%}",
        "售价": round(price, 2),
        "平台佣金": round(fee, 2),
        "进货成本": round(cost, 2),
        "发货成本": round(shipping, 2),
        "其他成本": round(other_cost, 2),
        "退货摊销": round(return_loss, 2),
        "单件净利": round(profit, 2),
        "净利率": f"{margin:.1%}",
        "保本售价": round(breakeven, 2),
        "每卖一件赚": round(profit, 2),
    }
    if margin < 0.1:
        result["提示"] = "净利率低于 10%，一次退货就可能吃掉好几单利润，谨慎。"
    return json.dumps(result, ensure_ascii=False, indent=2)


PROFIT_CALC = ToolSpec(
    name="profit.calc",
    label="利润测算",
    description=(
        "计算单件商品的净利润、净利率和保本售价，已考虑平台佣金、"
        "发货成本与退货摊销。用户问到「能赚多少」「划不划算」「保本价」时必须调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "cost": {"type": "number", "description": "进货成本（含国内运费），单位元"},
            "price": {"type": "number", "description": "预期售价，单位元"},
            "platform": {
                "type": "string",
                "description": "平台名，如 淘宝/拼多多/1688/amazon",
            },
            "shipping": {"type": "number", "description": "每单发货成本，默认 0"},
            "return_rate": {"type": "number", "description": "退货率 0~1，默认 0.03"},
            "other_cost": {"type": "number", "description": "其他单件成本，默认 0"},
        },
        "required": ["cost", "price"],
    },
    handler=profit_calc,
    required_env=[],
    source="estimated",
    tags=["计算", "利润"],
)
