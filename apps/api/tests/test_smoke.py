"""冒烟测试。

    cd apps/api && .venv/bin/python tests/test_smoke.py

把供应商换成假的，验证：工具注册 → agent 循环 → SSE 事件编码 → 会话落盘
这条链路是通的。**不需要任何 API key**，所以 CI 里也能跑。

真实模型的行为（提示词质量、工具选择是否合理）这里测不了 —— 那是一类
独立的评估问题，不该混进冒烟测试里假装覆盖了。
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 关掉后台调度循环：测试要的是「可断言的一次 tick」，不是和一个后台任务抢时序。
# 必须在 TestClient 进入 lifespan 之前设好。
os.environ.setdefault("ISSUE_SCHEDULER", "0")

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

# ── 5. 事件日志 ──────────────────────────────────────────────
import tempfile  # noqa: E402
import time  # noqa: E402

from src.core import event_log  # noqa: E402
from src.core.paths import data_home  # noqa: E402

day = time.strftime("%Y-%m-%d", time.localtime())
logfile = data_home() / "event-log" / f"{day}.jsonl"

check("事件日志已按天生成", logfile.exists(), logfile.name)

recs = []
if logfile.exists():
    for line in logfile.read_text(encoding="utf-8").splitlines():
        if line.strip():
            recs.append(json.loads(line))

# 只挑刚才这轮（一个会话里可能还有别人跑过的记录）
mine = [r for r in recs if r.get("session") == SID]
kinds = [r["type"] for r in mine]
check("记录了 turn.start / tool.call / turn.end", kinds == ["turn.start", "tool.call", "turn.end"], kinds)

turns = {r.get("turn") for r in mine}
check("三笔记录同属一轮（turn id 一致）", len(turns) == 1, turns)

tc = next((r for r in mine if r["type"] == "tool.call"), {})
check("工具记录带完整结果", "单件净利" in tc.get("result", ""), tc.get("resultChars"))
check("工具记录带耗时与状态", tc.get("ms") is not None and tc.get("status") == "ok")
check("工具记录没有截断", tc.get("truncated") is False, tc.get("truncated"))

te = next((r for r in mine if r["type"] == "turn.end"), {})
check("turn.end 标记成功", te.get("ok") is True)
check("turn.end 汇总了步数与字数", te.get("steps") == 1 and te.get("chars", 0) > 0, te.get("steps"))

# 日志不该反过来污染会话历史
check(
    "工具原始输出没进会话文件",
    all("单件净利" not in h["content"] for h in session.history(SID)),
)

# ── 6. 截断与清理（隔离在临时目录里跑）──────────────────────
old_home = os.environ.get("DATA_HOME")
with tempfile.TemporaryDirectory() as tmp:
    os.environ["DATA_HOME"] = tmp
    try:
        big = "x" * (event_log.MAX_RESULT + 1000)
        t = event_log.Turn(session_id="tmp", user_message="hi")
        t.tool(name="profit.calc", status="ok", ms=1, result=big)
        t.finish(chars=1)

        tmpdir = Path(tmp) / "event-log"
        tmp_recs = [
            json.loads(line)
            for line in (tmpdir / f"{day}.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        big_rec = next(r for r in tmp_recs if r["type"] == "tool.call")
        check("超长结果被截断并打标", big_rec["truncated"] is True, big_rec["resultChars"])
        check("截断后长度等于上限", len(big_rec["result"]) == event_log.MAX_RESULT)

        # 造一个「31 天前」的文件，看清理会不会带走它
        stale = tmpdir / "2000-01-01.jsonl"
        stale.write_text("{}\n", encoding="utf-8")
        os.utime(stale, (time.time() - 31 * 86400, time.time() - 31 * 86400))
        removed = event_log.prune(days=30)
        check("清理删掉过期文件", removed == 1 and not stale.exists(), removed)
        check("清理没误删当天的", (tmpdir / f"{day}.jsonl").exists())

        # 关掉开关就一条都不写
        os.environ["EVENT_LOG"] = "0"
        before = (tmpdir / f"{day}.jsonl").read_text(encoding="utf-8")
        event_log.write({"type": "should.not.appear"})
        check(
            "EVENT_LOG=0 时完全静默",
            (tmpdir / f"{day}.jsonl").read_text(encoding="utf-8") == before,
        )
    finally:
        os.environ.pop("EVENT_LOG", None)
        if old_home is None:
            os.environ.pop("DATA_HOME", None)
        else:
            os.environ["DATA_HOME"] = old_home

# ── 7. 定时任务端到端 ────────────────────────────────────────
# 扫到点 → 真跑一轮 agent（工具 + 流式）→ 投递报告 → 接口读回。
from src.core import inbox, issues as issues_mod  # noqa: E402
from src.core.scheduler import Scheduler  # noqa: E402

old_home2 = os.environ.get("DATA_HOME")
with tempfile.TemporaryDirectory() as tmp2:
    os.environ["DATA_HOME"] = tmp2
    try:
        idir = Path(tmp2) / "issues"
        idir.mkdir(parents=True, exist_ok=True)
        task_file = idir / "daily-report.md"
        task_file.write_text(
            "---\n"
            "title: 每日测算\n"
            'when: { kind: cron, cron: "* * * * *", timezone: "Asia/Shanghai" }\n'
            "---\n"
            "算一下成本30卖99能赚多少\n",
            encoding="utf-8",
        )
        # 把 mtime 拨到 5 分钟前 —— 模拟「任务文件躺了一会儿，已经欠了班次」
        past = time.time() - 300
        os.utime(task_file, (past, past))

        sch = Scheduler()
        CALLS["n"] = 0  # 让打桩的供应商从这个任务重新开始计数
        results = asyncio.run(sch.tick_once())

        check("到点的任务被跑了一次", len(results) == 1, [r.issue_id for r in results])
        r0 = results[0] if results else None
        check("任务执行成功", r0 is not None and r0.ok, r0.error if r0 else "没跑")
        check("任务真的调了工具", r0 is not None and "profit.calc" in r0.tools, r0.tools if r0 else None)

        reports = inbox.list_reports()
        check("结果投递进了收件箱", len(reports) == 1, [x.get("name") for x in reports])
        check("报告标成功", reports[0].get("ok") is True if reports else False)

        content = inbox.read(reports[0]["name"]) if reports else ""
        check("报告正文是模型输出", "净利率 61.9%" in content, content[-60:].strip())
        check("报告记了排期与实际时刻", "scheduledAt" in content and "lagSeconds" in content)
        check("报告带 turn id（可回查 event-log）", "turn:" in content)

        # 状态落盘了，所以不会连着跑第二次 —— 这是「不重复触发」的核心保证
        st = issues_mod.load_state()
        check("状态记了 lastRun", st.get("daily-report") is not None, st.get("daily-report"))
        check("状态记了 ok", (st.get("daily-report").last_status if st.get("daily-report") else None) == "ok")

        CALLS["n"] = 0
        again = asyncio.run(sch.tick_once())
        check("刚跑完不会立刻重跑", again == [], [x.issue_id for x in again])

        # ── 接口 ──
        with TestClient(app) as client:
            r = client.get("/api/v1/issues")
            check("任务清单接口 200", r.status_code == 200)
            listed = r.json().get("issues", [])
            check("清单里能看到任务", len(listed) == 1 and listed[0]["id"] == "daily-report", listed)
            check("清单带排期人话摘要", bool(listed[0].get("schedule")), listed[0].get("schedule"))
            check("清单带下次运行时刻", bool(listed[0].get("nextRun")), listed[0].get("nextRun"))

            r = client.get("/api/v1/inbox")
            check("收件箱接口 200", r.status_code == 200 and r.json()["total"] == 1)

            name = reports[0]["name"]
            r = client.get(f"/api/v1/inbox/{name}")
            check("报告全文接口 200", r.status_code == 200 and "净利率" in r.json()["content"])

            r = client.get("/api/v1/inbox/evil")
            check("非法报告名 400", r.status_code == 400, r.status_code)

            r = client.post("/api/v1/issues/nope/run")
            check("不存在的任务 404", r.status_code == 404, r.status_code)

            CALLS["n"] = 0
            r = client.post("/api/v1/issues/daily-report/run")
            check("手动触发 200", r.status_code == 200 and r.json()["ok"] is True, r.json())
            # 手动那次和定时那次在同一秒内，文件名会撞 —— 必须加序号而不是覆盖
            check(
                "手动触发的报告没覆盖定时那次",
                r.json()["report"] != reports[0]["name"],
                (reports[0]["name"], r.json()["report"]),
            )
            check("收件箱现在有两份", client.get("/api/v1/inbox").json()["total"] == 2)

            h = client.get("/health").json()
            check("健康检查带任务与调度器状态", "issues" in h and "scheduler" in h, h.get("issues"))
            check("测试环境下调度循环是停的", h["scheduler"]["running"] is False)
    finally:
        if old_home2 is None:
            os.environ.pop("DATA_HOME", None)
        else:
            os.environ["DATA_HOME"] = old_home2

print()
print(f"{'全部通过' if not FAIL else '失败：' + ', '.join(FAIL)}")
sys.exit(1 if FAIL else 0)
