"""定时任务的纯逻辑测试。

    cd apps/api && .venv/bin/python tests/test_issues.py

覆盖 cron 解析与匹配、frontmatter 解析、判到点、状态读写、收件箱。
**不需要 API key，也不碰真实 data/** —— 每个用例都在临时目录里跑。

执行链路（真的跑一轮 agent）在 test_smoke.py 里测，那边有打好桩的供应商。
这里只管「决定该不该跑」这一半 —— 它全是纯函数，错了最容易查。
"""

import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FAIL = []
SH = ZoneInfo("Asia/Shanghai")


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}{'  ' + str(extra) if extra else ''}")
    if not cond:
        FAIL.append(name)


def raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


from src.core.cron import CronSpec  # noqa: E402

# ── 1. cron 解析 ─────────────────────────────────────────────
check("每分钟：五个字段全未限制", vars(CronSpec.parse("* * * * *"))["minute"] is None)

c = CronSpec.parse("0 9 * * *")
check("固定时刻", c.minute == {0} and c.hour == {9}, (c.minute, c.hour))

c = CronSpec.parse("*/15 * * * *")
check("步长 */15", c.minute == {0, 15, 30, 45}, sorted(c.minute or []))

c = CronSpec.parse("30 8 * * 1-5")
check("文档里那条 30 8 * * 1-5", c.minute == {30} and c.hour == {8} and c.dow == {1, 2, 3, 4, 5})

c = CronSpec.parse("1-30/5 * * * *")
check("区间加步长", c.minute == {1, 6, 11, 16, 21, 26}, sorted(c.minute or []))

c = CronSpec.parse("0,30 * * * *")
check("枚举", c.minute == {0, 30}, sorted(c.minute or []))

c = CronSpec.parse("0 0 * * 7")
check("星期 7 折成 0（周日）", c.dow == {0}, c.dow)

c = CronSpec.parse("0-59 * * * *")
check("写全的区间等同于 *（不限制）", c.minute is None, c.minute)

c = CronSpec.parse("*/1 * * * *")
check("步长 1 等同于 *（不限制）", c.minute is None, c.minute)

check("字段数不对要报错", raises(lambda: CronSpec.parse("0 9 * *")))
check("六个字段要报错", raises(lambda: CronSpec.parse("0 9 * * * *")))
check("非数字要报错", raises(lambda: CronSpec.parse("a 9 * * *")))
check("超范围要报错", raises(lambda: CronSpec.parse("0 24 * * *")))
check("区间反了要报错", raises(lambda: CronSpec.parse("30-10 * * * *")))
check("步长为 0 要报错", raises(lambda: CronSpec.parse("*/0 * * * *")))
check("空项要报错", raises(lambda: CronSpec.parse("0,,5 * * * *")))

# ── 2. cron 匹配 ─────────────────────────────────────────────
c = CronSpec.parse("0 9 * * *")
check("命中 09:00", c.matches(datetime(2026, 9, 28, 9, 0, tzinfo=SH)))
check("不命中 09:01", not c.matches(datetime(2026, 9, 28, 9, 1, tzinfo=SH)))
check("秒和微秒被忽略", c.matches(datetime(2026, 9, 28, 9, 0, 59, 999, tzinfo=SH)))

# 2026-09-28 是周一
c = CronSpec.parse("0 9 * * 1-5")
check("工作日命中周一", c.matches(datetime(2026, 9, 28, 9, 0, tzinfo=SH)))
check("工作日不命中周六", not c.matches(datetime(2026, 10, 3, 9, 0, tzinfo=SH)))

# 星期编号不能错位：这是最容易写错的一处
check(
    "周日 = 0",
    CronSpec.parse("0 0 * * 0").matches(datetime(2026, 9, 27, 0, 0, tzinfo=SH)),
)
check(
    "周一 = 1",
    CronSpec.parse("0 0 * * 1").matches(datetime(2026, 9, 28, 0, 0, tzinfo=SH)),
)

# 日 和 星期 都写时取 OR（标准 cron 行为）
c = CronSpec.parse("0 0 1 * 1")
check("日1号命中", c.matches(datetime(2026, 9, 1, 0, 0, tzinfo=SH)))
check("周一也命中（OR 而非 AND）", c.matches(datetime(2026, 9, 28, 0, 0, tzinfo=SH)))
check("既非1号也非周一则不命中", not c.matches(datetime(2026, 9, 2, 0, 0, tzinfo=SH)))

# ── 3. next_after ────────────────────────────────────────────
c = CronSpec.parse("0 9 * * *")
n = c.next_after(datetime(2026, 9, 28, 8, 59, tzinfo=SH))
check("08:59 → 当天 09:00", n == datetime(2026, 9, 28, 9, 0, tzinfo=SH), n)

n = c.next_after(datetime(2026, 9, 28, 9, 0, tzinfo=SH))
check("严格晚于：09:00 → 次日 09:00", n == datetime(2026, 9, 29, 9, 0, tzinfo=SH), n)

n = c.next_after(datetime(2026, 9, 28, 9, 0, 30, tzinfo=SH))
check("09:00:30 这一分钟已过 → 次日", n == datetime(2026, 9, 29, 9, 0, tzinfo=SH), n)

n = c.next_after(datetime(2026, 9, 28, 23, 59, tzinfo=SH))
check("跨天", n == datetime(2026, 9, 29, 9, 0, tzinfo=SH), n)

check("保持同一时区", n is not None and n.tzinfo is SH)

c = CronSpec.parse("*/15 * * * *")
n = c.next_after(datetime(2026, 9, 28, 9, 7, tzinfo=SH))
check("*/15：09:07 → 09:15", n == datetime(2026, 9, 28, 9, 15, tzinfo=SH), n)

# 周五 09:30 之后的下一个工作日是周一
c = CronSpec.parse("0 9 * * 1-5")
n = c.next_after(datetime(2026, 10, 2, 9, 30, tzinfo=SH))  # 10-02 是周五
check("周五过后跳到周一", n == datetime(2026, 10, 5, 9, 0, tzinfo=SH), n)

# 闰日：2026/2027 都不是闰年，下一个 2 月 29 日是 2028
c = CronSpec.parse("0 0 29 2 *")
n = c.next_after(datetime(2026, 3, 1, 0, 0, tzinfo=SH))
check("闰日会一直找到 2028", n == datetime(2028, 2, 29, 0, 0, tzinfo=SH), n)

c = CronSpec.parse("* * * * *")
n = c.next_after(datetime(2026, 9, 28, 9, 0, tzinfo=SH))
check("每分钟：只往后推一分钟", n == datetime(2026, 9, 28, 9, 1, tzinfo=SH), n)

# 夏令时地区不能崩（美国 2026-11-01 回拨）
us = ZoneInfo("America/New_York")
c = CronSpec.parse("0 9 * * *")
n = c.next_after(datetime(2026, 10, 31, 9, 0, tzinfo=us))
check("夏令时切换前后不崩", n is not None, n)

# ── 4. frontmatter 解析 ──────────────────────────────────────
from src.core import inbox  # noqa: E402
from src.core import issues as im  # noqa: E402

old_home = os.environ.get("DATA_HOME")
tmp = tempfile.TemporaryDirectory()
os.environ["DATA_HOME"] = tmp.name

try:
    d = Path(tmp.name) / "issues"
    d.mkdir(parents=True, exist_ok=True)

    def write_issue(name, text, mtime_offset=0.0):
        p = d / f"{name}.md"
        p.write_text(text, encoding="utf-8")
        if mtime_offset:
            t = time.time() + mtime_offset
            os.utime(p, (t, t))
        return p

    write_issue(
        "good",
        "---\ntitle: 竞品价格监控\n"
        'when: { kind: cron, cron: "0 9 * * *", timezone: Asia/Shanghai }\n'
        "---\n监控竞品价格。\n",
    )
    write_issue("no-when", "---\ntitle: 看板卡片\n---\n只是一个待办。\n")
    write_issue("no-fm", "# 只是篇笔记\n没有 frontmatter。\n")
    write_issue("bad-yaml", "---\ntitle: [没闭合\n---\n正文\n")
    write_issue("bad-cron", '---\ntitle: 写错了\nwhen: { kind: cron, cron: "0 99 * * *" }\n---\n')
    write_issue("bad-kind", '---\ntitle: 别的方式\nwhen: { kind: interval, every: "5m" }\n---\n')
    write_issue("bad-tz", '---\ntitle: 时区写错\nwhen: { kind: cron, cron: "0 9 * * *", timezone: "Mars/Olympus" }\n---\n')
    write_issue("off", '---\ntitle: 关掉了\nenabled: false\nwhen: { kind: cron, cron: "0 9 * * *" }\n---\n')
    write_issue("done", '---\ntitle: 做完了\nstatus: done\nwhen: { kind: cron, cron: "0 9 * * *" }\n---\n')
    write_issue("bare", '---\ntitle: 简写\nwhen: "0 9 * * *"\n---\n')

    found = {i.id: i for i in im.scan()}

    check("合法任务被扫到", "good" in found)
    check("可调度", found["good"].schedulable)

    check("没有 when 的是看板卡片，不调度", not found["no-when"].schedulable)
    check("没有 frontmatter 的不算任务", "no-fm" not in found)

    check("YAML 坏了有 error 且不调度", found["bad-yaml"].error and not found["bad-yaml"].schedulable)
    check("cron 坏了有 error 且不调度", bool(found["bad-cron"].when.error) and not found["bad-cron"].schedulable)
    check("未知 kind 有 error", "暂不支持" in (found["bad-kind"].when.error or ""))
    check("时区写错有 error", "时区" in (found["bad-tz"].when.error or ""))
    check("enabled:false 不调度", not found["off"].schedulable)
    check("status:done 不调度", not found["done"].schedulable)
    check("when 直接写字符串也认", found["bare"].schedulable)

    check("instruction 取正文", found["good"].instruction == "监控竞品价格。")

    # 一次性坏文件不该让整轮扫描挂掉 —— 上面九个文件里一个有问题的都没有把 scan() 搞崩
    check("坏文件不影响好文件", len(found) >= 9, len(found))

    # ── 5. 判到点 ────────────────────────────────────────────
    from src.core.issues import IssueState

    c = CronSpec.parse("0 9 * * *")
    g = found["good"]
    # 手动把 created_at 拨到 3 天前，模拟「文件躺了几天」
    g.created_at = datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)

    now = datetime(2026, 9, 28, 1, 0, tzinfo=timezone.utc)  # 北京时间 09:00
    due = im.pending_occurrence(g, IssueState(), now)
    check("从没跑过、已过排期 → 欠一次", due is not None, due)
    # 返回**最早**欠的那次（文件的 mtime 之后第一班），不是最近那次。
    # 这样 lagSeconds 才等于「欠了多久」，停机时长不会被抹掉。
    check(
        "欠的是最早那次，lag 才能反映停机时长",
        due == datetime(2026, 9, 25, 9, 0, tzinfo=SH),
        due,
    )

    # 已经跑过了就不该再欠
    st = IssueState(last_run=now.timestamp())
    check("刚跑过 → 不欠", im.pending_occurrence(g, st, now) is None)

    # 排期还没到
    early = datetime(2026, 9, 28, 0, 30, tzinfo=timezone.utc)  # 北京 08:30
    st2 = IssueState(last_run=datetime(2026, 9, 27, 5, 0, tzinfo=timezone.utc).timestamp())
    check("排期还没到 → 不欠", im.pending_occurrence(g, st2, early) is None)

    # 停机三天只补一次：无论停多久，pending_occurrence 只返回一个时刻
    long_ago = IssueState(last_run=datetime(2026, 9, 20, 1, 0, tzinfo=timezone.utc).timestamp())
    d1 = im.pending_occurrence(g, long_ago, now)
    check("停机 8 天只欠一次（合并），不是 8 次", isinstance(d1, datetime), d1)
    # 欠的那次要能反映停机时长 —— 报告上的 lagSeconds 就取这两个值之差
    lag = int((now.astimezone(SH) - d1).total_seconds()) if d1 else 0
    check("lag 反映的是停机时长（约 7 天），不是几秒", lag > 6 * 86400, f"{lag}s")

    check("不可调度的任务永远不欠", im.pending_occurrence(found["no-when"], IssueState(), now) is None)

    nxt = im.next_fire(g, IssueState(), now)
    check("next_fire 给的是未来时刻", nxt is not None and nxt > now.astimezone(SH), nxt)

    # ── 6. 状态读写 ──────────────────────────────────────────
    st = {}
    im.mark_run(st, "good", at=123.0, status="ok", duration_ms=42)
    im.mark_run(st, "good", at=456.0, status="failed", error="炸了")
    check("runs 会累加", st["good"].runs == 2, st["good"].runs)
    check("后一次覆盖前一次", st["good"].last_run == 456.0 and st["good"].last_status == "failed")

    im.save_state(st)
    back = im.load_state()
    check("状态存取往返一致", back["good"].last_status == "failed" and back["good"].runs == 2)

    # 占坑那次（count=False）不该算进 runs —— 否则一次执行记成两次。
    # 单独用一个字典，别弄脏上面的往返用例。
    st2: dict = {}
    im.mark_run(st2, "x", at=1.0, status="ok")
    im.mark_run(st2, "x", at=2.0, status="running", count=False)
    check("占坑不增加 runs", st2["x"].runs == 1, st2["x"].runs)
    check("占坑仍会更新 lastStatus", st2["x"].last_status == "running")
    check("没留下临时文件", not (Path(tmp.name) / "issues" / ".state.json.tmp").exists())

    (Path(tmp.name) / "issues" / ".state.json").write_text("{坏掉的 json", encoding="utf-8")
    check("状态文件坏了当空处理，不抛", im.load_state() == {})

    # ── 7. 任务 id 与路径穿越 ────────────────────────────────
    check("挡路径穿越", raises(lambda: im.get("../../etc/passwd"), ValueError))
    check("合法 id 放行", im.is_valid_id("price-watch_01"))

    # ── 8. 收件箱 ────────────────────────────────────────────
    run_at = datetime(2026, 9, 28, 9, 0, 12, tzinfo=SH)
    sched = datetime(2026, 9, 28, 9, 0, 0, tzinfo=SH)
    p = inbox.write(
        issue_id="good",
        title="竞品价格监控",
        body="跌了 8%。",
        run_at=run_at,
        scheduled_at=sched,
        duration_ms=1892,
        tools=["apify.scrape"],
        turn="abc123",
    )
    check("报告写出来了", p is not None and p.exists(), p.name if p else None)

    text = inbox.read(p.name)
    check("报告带回读", "跌了 8%。" in text and "apify.scrape" in text)
    check("报告记了延迟秒数", "lagSeconds: 12" in text, [ln for ln in text.splitlines() if "lag" in ln])

    inbox.write(issue_id="good", title="第二次", body="第二次的内容", run_at=datetime(2026, 9, 29, 9, 0, tzinfo=SH))
    reports = inbox.list_reports()
    check("清单新的在前", "2026-09-29" in reports[0]["name"], reports[0]["name"])
    check("清单带元信息", reports[0].get("title") == "第二次")
    check("清单条目数对", len(reports) == 2, len(reports))
    check("清单不拖正文", "content" not in reports[0])

    check("收件箱挡路径穿越", raises(lambda: inbox.read("../../.env"), inbox.BadReportName))
    check("非法文件名不给读", raises(lambda: inbox.read("not-a-report.md"), inbox.BadReportName))

    big = inbox.write(issue_id="good", title="超长", body="x" * 30_000, run_at=run_at)
    check("超长正文被截断打标", "truncated: true" in big.read_text(encoding="utf-8"))

    # 收件箱写失败不该抛（非法 id 会被拒绝，返回 None）
    check("写失败不抛异常", inbox.write(issue_id="x" * 100, title="t", body="b", run_at=run_at) is None)
    check("带路径分隔符的 id 拒绝写入", inbox.write(issue_id="../evil", title="t", body="b", run_at=run_at) is None)

    # 同一秒里跑两次同一个任务会撞名。收件箱是只追加的审计记录，
    # 覆盖等于丢报告 —— 撞了必须加序号，两份都留下。
    same = datetime(2026, 9, 30, 9, 0, 0, tzinfo=SH)
    a = inbox.write(issue_id="good", title="甲", body="第一份", run_at=same)
    b = inbox.write(issue_id="good", title="乙", body="第二份", run_at=same)
    check("同一秒撞名不覆盖", a != b and a.exists() and b.exists(), (a.name, b.name))
    check(
        "两份内容都还在",
        "第一份" in a.read_text(encoding="utf-8") and "第二份" in b.read_text(encoding="utf-8"),
    )
    check("加过序号的报告仍能被列出", len(inbox.list_reports()) >= 4, len(inbox.list_reports()))

finally:
    tmp.cleanup()
    if old_home is None:
        os.environ.pop("DATA_HOME", None)
    else:
        os.environ["DATA_HOME"] = old_home

print()
print(f"{'全部通过' if not FAIL else '失败：' + ', '.join(FAIL)}")
sys.exit(1 if FAIL else 0)
