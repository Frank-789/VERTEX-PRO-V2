"""冒烟测试。

    cd apps/api && .venv/bin/python tests/test_smoke.py

把供应商换成假的，验证：工具注册 → agent 循环 → SSE 事件编码 → 会话落盘
这条链路是通的。**不需要任何 API key**，所以 CI 里也能跑。

真实模型的行为（提示词质量、工具选择是否合理）这里测不了 —— 那是一类
独立的评估问题，不该混进冒烟测试里假装覆盖了。
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core import provider_router, session  # noqa: E402
from src.core.provider_router import ProviderRouter  # noqa: E402
from src.core.tool_center import get_tool_center  # noqa: E402

FAIL = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}{'  ' + str(extra) if extra else ''}")
    if not cond:
        FAIL.append(name)


# ── 1. 工具注册 ──────────────────────────────────────────────
center = get_tool_center()
names = sorted(t.name for t in center.all())
check("工具已注册", names == ["apify.scrape", "ebay.search", "profit.calc"], names)

ready = sorted(t.name for t in center.ready())
check("无需凭证的工具就绪", ready == ["profit.calc"], ready)

openai_names = sorted(t["function"]["name"] for t in center.openai_tools())
check("函数名不含点（OpenAI 限制）", openai_names == ["profit_calc"], openai_names)

check("resolve_fn 能把函数名还原", center.resolve_fn("profit_calc").name == "profit.calc")

# ── 2. 工具真的能算 ──────────────────────────────────────────
out = asyncio.run(center.call("profit.calc", {"cost": 30, "price": 99, "platform": "淘宝"}))
data = json.loads(out)
check("利润测算有结果", data["平台"] == "淘宝", f"净利={data['单件净利']}")
check("保本售价为正", data["保本售价"] > 0, data["保本售价"])

# 未配置凭证的工具必须报错，不能伪造数据
try:
    asyncio.run(center.call("ebay.search", {"keyword": "test"}))
    check("缺凭证时 eBay 应报错", False, "居然没报错 —— 可能在造假数据")
except RuntimeError as e:
    check("缺凭证时 eBay 报错", "EBAY_API_KEY" in str(e), str(e)[:50])

# ── 3. 打桩，跑通 agent + SSE ────────────────────────────────
CALLS = {"n": 0}
SID = session.new_session_id()


async def fake_complete_message(self, messages, *, tools=None, **kw):
    CALLS["n"] += 1
    if CALLS["n"] == 1:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "profit_calc",
                        "arguments": json.dumps({"cost": 30, "price": 99}),
                    },
                }
            ],
        }
    return {"role": "assistant", "content": "算完了"}


async def fake_stream(self, messages, **kw):
    for piece in ["成本 30，卖 99，", "净利率 61.9%。", "[[sticker/celebrate.svg]]"]:
        yield "stub", piece


ProviderRouter.complete_message = fake_complete_message
ProviderRouter.stream = fake_stream
provider_router.get_router.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from src.main import app  # noqa: E402

with TestClient(app) as client:
    r = client.get("/health")
    check("健康检查 200", r.status_code == 200, r.json().get("tools"))

    with client.stream(
        "POST",
        "/api/v1/chat",
        json={"message": "成本30卖99能赚多少", "sessionId": SID},
    ) as resp:
        check("对话返回 SSE", resp.headers["content-type"].startswith("text/event-stream"))
        body = "".join(resp.iter_text())

events = []
name = None
for line in body.split("\n"):
    if line.startswith("event:"):
        name = line[6:].strip()
    elif line.startswith("data:") and name:
        events.append((name, json.loads(line[5:].strip())))

kinds = [e[0] for e in events]
check("事件顺序含 tool_call", "tool_call" in kinds, kinds)
check("以 done 收尾", kinds[-1] == "done", kinds[-1])
check("末尾有空行分隔", body.endswith("\n\n"))

tool_evs = [d for k, d in events if k == "tool_call"]
check("工具事件有 running 与 ok 两态", [t["status"] for t in tool_evs] == ["running", "ok"])
check("工具事件带 camelCase durationMs", "durationMs" in tool_evs[-1], list(tool_evs[-1]))
check("工具事件带条数/耗时摘要", tool_evs[-1].get("durationMs") is not None)

text = "".join(d["text"] for k, d in events if k == "chunk")
check("文本分片完整", "净利率 61.9%" in text, text[:40])
check("表情包标记原样传给前端", "[[sticker/celebrate.svg]]" in text)

# ── 4. 会话落盘 ──────────────────────────────────────────────
hist = session.history(SID)
check("会话已落盘且问答成对", [h["role"] for h in hist] == ["user", "assistant"], len(hist))
check("历史不含工具内部细节", all("tool_call" not in h["content"] for h in hist))

try:
    session.history("../../etc/passwd")
    check("会话 id 挡路径穿越", False, "没拦住")
except ValueError:
    check("会话 id 挡路径穿越", True)

# 悬空的 user 记录（上一轮失败留下的）不该被当成上下文回灌
session.append(SID, "user", "这句没有回答")
check("尾部悬空 user 已剔除", session.history(SID)[-1]["role"] == "assistant")

print()
print(f"{'全部通过' if not FAIL else '失败：' + ', '.join(FAIL)}")
sys.exit(1 if FAIL else 0)
