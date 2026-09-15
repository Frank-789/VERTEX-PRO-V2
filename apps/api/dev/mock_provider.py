"""开发用假供应商 —— 一个最小的 OpenAI 兼容端点。

    python dev/mock_provider.py          # 监听 8899

然后在仓库根目录的 .env 里加：

    MOCK_API_KEY=dev

`config/providers.json` 里 mock 排在最后，所以配了真 key 就不会被用到。
想强制走 mock 时把 MOCK_API_KEY 留着、把真 key 注释掉即可。

为什么值得存在：没有它，任何人想改一句提示词、调一下工具卡片的样式，
都得先申请一个 API key、再烧掉一点额度。有了它，前端和 Agent 循环的
改动都能在本地闭环验证。
"""

from __future__ import annotations

import json
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()

TOOL_REPLY = {
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "call_mock_1",
            "type": "function",
            "function": {
                "name": "profit_calc",
                "arguments": json.dumps(
                    {"cost": 78, "price": 199, "platform": "淘宝", "shipping": 8}
                ),
            },
        }
    ],
}

FINAL_TEXT = """这个品能做，但**不适合当主力**。

| 项目 | 金额 |
| --- | --- |
| 售价 | ¥199.00 |
| 平台佣金 | ¥9.95 |
| 进货 + 发货 | ¥86.00 |
| **单件净利** | **¥101.66** |
| 净利率 | 51.1% |

三点判断：

1. **毛利够厚** —— 51% 的净利率，一次退货要卖两单才补得回来，容错空间够。
2. **保本价 ¥108.34** —— 促销打到这个价以下就是纯亏，别再往下让。
3. **风险在退货率** —— 上面按 3% 算的。这个类目如果是服饰，实际能到 15%，
   净利率会掉到 38% 左右。**发货前务必确认退货率**。

要不要我把同款在 1688 的拿货价也拉出来比一比？[[sticker/confident.svg]]"""


@app.post("/v1/chat/completions")
async def completions(req: Request):
    body = await req.json()
    messages = body.get("messages", [])
    already_used_tool = any(m.get("role") == "tool" for m in messages)
    wants_tools = bool(body.get("tools"))

    # 第一轮且给了工具 → 假装要调工具（走非流式，和真供应商一致）
    if wants_tools and not already_used_tool:
        return JSONResponse(
            {
                "id": "mock",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": body.get("model", "mock"),
                "choices": [{"index": 0, "message": TOOL_REPLY, "finish_reason": "tool_calls"}],
            }
        )

    if not body.get("stream"):
        return JSONResponse(
            {
                "id": "mock",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": body.get("model", "mock"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": FINAL_TEXT},
                        "finish_reason": "stop",
                    }
                ],
            }
        )

    def sse():
        # 按字符切片，模拟真实的逐字流式
        for i in range(0, len(FINAL_TEXT), 3):
            chunk = {
                "choices": [{"index": 0, "delta": {"content": FINAL_TEXT[i : i + 3]}}]
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            time.sleep(0.012)
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"ok": True, "mock": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8899, log_level="warning")
