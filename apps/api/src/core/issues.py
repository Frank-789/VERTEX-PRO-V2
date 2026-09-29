"""定时任务（Issue）—— 一个 Markdown 文件就是一个任务。

学 OpenAlice 的「文件即任务」：**没有中央任务库，没有独立的调度定义**。
去掉 `when:` 它就是一张看板卡片，带上 `when:` 它就是一个定时任务。
好处是人能读能改，Agent 也能读能改 —— 不需要给用户做一套任务管理 UI。

    data/issues/price-watch.md
    ---
    title: 竞品价格监控
    when: { kind: cron, cron: "0 9 * * *", timezone: Asia/Shanghai }
    ---
    监控该商品在 1688/淘宝的竞品价格，跌幅超 5% 时说明原因。

**状态为什么不写回 `.md`**（这点和 Alice 不同，是刻意的取舍）：
把 `lastRun` 写回任务文件，意味着 runner 每次都要改写用户的文件。三个问题：
① 和编辑器打架（你正在编辑，它给你覆盖）；② 文件若纳入 git 会一路噪音；
③ 进程在写文件的中途被杀，**任务定义就坏了** —— 用状态换定义，不划算。
所以状态另存 `data/issues/.state.json`（临时文件 + `os.replace` 原子替换），
`.md` 保持纯声明、归人所有。
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .cron import CronSpec
from .paths import data_home

log = logging.getLogger(__name__)

# 任务 id 会被拼进文件名、也会从 URL 里取。和 session.py 同样的做法：
# 入口就卡死，别让它有机会到磁盘层。
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

STATE_VERSION = 1

DEFAULT_TZ = os.getenv("ISSUE_DEFAULT_TZ", "Asia/Shanghai")
"""`when` 里没写 timezone 时用哪个。默认东八区 —— 这是个给国内商家用的产品，
默认 UTC 只会让「早上九点」变成下午五点。"""


def is_valid_id(issue_id: str) -> bool:
    return bool(_SAFE_ID.match(issue_id))


def issues_dir() -> Path:
    d = data_home() / "issues"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _state_path() -> Path:
    return issues_dir() / ".state.json"


# ── frontmatter ──────────────────────────────────────────────


@dataclass
class When:
    """解析好的调度规则。`cron` 为 None 表示规则写错了（`error` 里有原因）。"""

    kind: str
    raw: str
    cron: CronSpec | None = None
    timezone: str = DEFAULT_TZ
    tz: ZoneInfo | None = None
    error: str | None = None


@dataclass
class Issue:
    id: str
    title: str
    when: When | None
    body: str
    path: Path
    created_at: datetime
    status: str = "todo"
    enabled: bool = True
    error: str | None = None
    """整份文件级别的问题（frontmatter 坏掉之类）。"""

    @property
    def schedulable(self) -> bool:
        return (
            self.enabled
            and self.status not in ("done", "paused")
            and self.when is not None
            and self.when.cron is not None
        )

    @property
    def instruction(self) -> str:
        """真正交给模型的那句话。正文优先，正文空了退而用标题。"""
        return self.body.strip() or self.title.strip()

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "enabled": self.enabled,
            "schedulable": self.schedulable,
            "cron": self.when.cron.expr if (self.when and self.when.cron) else None,
            "schedule": self.when.cron.describe() if (self.when and self.when.cron) else None,
            "timezone": self.when.timezone if self.when else None,
            "error": self.error or (self.when.error if self.when else None),
        }


def _split_frontmatter(text: str) -> tuple[str, str] | None:
    """切开 `---` 包起来的头部。没有 frontmatter 就返回 None。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :])
    return None


def _parse_when(raw: object, issue_id: str) -> When | None:
    """把 frontmatter 里的 `when` 解析成 When。

    坏掉的规则**不抛异常**，而是返回一个带 `error` 的 When ——
    一个文件写错不该让整个扫描挂掉，也不该让服务起不来。
    这跟 config.py「配置坏了回退默认值并打日志」是同一个原则。
    """
    if raw is None:
        return None

    if isinstance(raw, str):
        rule: dict = {"kind": "cron", "cron": raw}
    elif isinstance(raw, dict):
        rule = raw
    else:
        return When(
            kind="?", raw=str(raw), error=f"when 应该是映射或字符串，收到 {type(raw).__name__}"
        )

    kind = str(rule.get("kind", "cron")).lower()
    tz_name = str(rule.get("timezone") or DEFAULT_TZ)
    expr = rule.get("cron")
    when = When(kind=kind, raw=str(expr or ""), timezone=tz_name)

    if kind != "cron":
        # 只支持 cron。将来要加 interval / once 就在这里分支。
        when.error = f"暂不支持的 when.kind：{kind!r}（目前只支持 cron）"
        return when

    if not expr or not isinstance(expr, str):
        when.error = "when 里缺少 cron 表达式"
        return when

    try:
        when.tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        when.error = f"不认识的时区：{tz_name!r}"
        return when

    try:
        when.cron = CronSpec.parse(expr)
    except ValueError as exc:
        when.error = f"cron 解析失败：{exc}"
        return when

    log.debug("任务 %s 的调度规则：%s", issue_id, when.cron.describe())
    return when


def parse_file(path: Path) -> Issue | None:
    """读一个 `.md` 变成 Issue。读不动就返回 None（调用方跳过）。"""
    issue_id = path.stem
    try:
        text = path.read_text(encoding="utf-8")
        stat = path.stat()
    except OSError as exc:
        log.warning("任务文件读不了，跳过 %s：%s", path, exc)
        return None

    created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

    split = _split_frontmatter(text)
    if split is None:
        # 没有 frontmatter 的 .md 就当它不存在 —— data/issues 下可能被用户
        # 随手放笔记进去，不该被当成坏任务刷一屏警告。
        log.debug("任务文件没有 frontmatter，跳过：%s", path.name)
        return None

    head, body = split
    try:
        import yaml

        meta = yaml.safe_load(head) or {}
    except Exception as exc:  # noqa: BLE001 —— yaml 的异常类型很杂
        log.warning("任务 %s 的 frontmatter 不是合法 YAML：%s", issue_id, exc)
        return Issue(
            id=issue_id,
            title=issue_id,
            when=None,
            body=body,
            path=path,
            created_at=created,
            error=f"frontmatter 不是合法 YAML：{exc}",
        )

    if not isinstance(meta, dict):
        return Issue(
            id=issue_id,
            title=issue_id,
            when=None,
            body=body,
            path=path,
            created_at=created,
            error="frontmatter 不是键值对",
        )

    return Issue(
        id=issue_id,
        title=str(meta.get("title") or issue_id),
        when=_parse_when(meta.get("when"), issue_id),
        body=body,
        path=path,
        created_at=created,
        status=str(meta.get("status") or "todo"),
        enabled=bool(meta.get("enabled", True)),
    )


def scan() -> list[Issue]:
    """扫描 `data/issues/*.md`，按 id 排序。

    单个文件坏掉只影响它自己 —— 不让一个格式错误的任务把整轮扫描搞挂。
    """
    d = issues_dir()
    out: list[Issue] = []
    for path in sorted(d.glob("*.md")):
        if not is_valid_id(path.stem):
            log.warning("任务文件名不合法，跳过：%s（只允许字母数字下划线连字符）", path.name)
            continue
        issue = parse_file(path)
        if issue is not None:
            out.append(issue)
    return out


def get(issue_id: str) -> Issue | None:
    if not is_valid_id(issue_id):
        raise ValueError(f"非法任务 id：{issue_id!r}")
    path = issues_dir() / f"{issue_id}.md"
    if not path.is_file():
        return None
    return parse_file(path)


# ── 状态 ─────────────────────────────────────────────────────


@dataclass
class IssueState:
    last_run: float | None = None
    last_status: str | None = None
    last_duration_ms: int | None = None
    last_error: str | None = None
    runs: int = 0
    extra: dict = field(default_factory=dict)

    @property
    def last_run_dt(self) -> datetime | None:
        if self.last_run is None:
            return None
        return datetime.fromtimestamp(self.last_run, tz=timezone.utc)

    def to_public(self) -> dict:
        return {
            "lastRun": self.last_run,
            "lastStatus": self.last_status,
            "lastDurationMs": self.last_duration_ms,
            "lastError": self.last_error,
            "runs": self.runs,
        }


def load_state() -> dict[str, IssueState]:
    """读状态。文件坏了就当空的 —— 大不了所有任务重跑一次，不该起不来。"""
    path = _state_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("任务状态文件读不了，按空状态处理：%s", exc)
        return {}
    if not isinstance(raw, dict) or raw.get("version") != STATE_VERSION:
        log.warning("任务状态文件版本不符，按空状态处理")
        return {}

    out: dict[str, IssueState] = {}
    for key, val in (raw.get("issues") or {}).items():
        if not isinstance(val, dict):
            continue
        out[key] = IssueState(
            last_run=val.get("lastRun"),
            last_status=val.get("lastStatus"),
            last_duration_ms=val.get("lastDurationMs"),
            last_error=val.get("lastError"),
            runs=int(val.get("runs") or 0),
        )
    return out


def save_state(state: dict[str, IssueState]) -> None:
    """原子写：先写临时文件再 `os.replace`。

    直接覆盖原文件的话，写一半被杀就只剩半个 JSON，下次启动所有任务
    的状态全丢 —— 那意味着所有任务会立刻重跑一遍。
    """
    path = _state_path()
    payload = {
        "version": STATE_VERSION,
        "updatedAt": time.time(),
        "issues": {
            k: {
                "lastRun": v.last_run,
                "lastStatus": v.last_status,
                "lastDurationMs": v.last_duration_ms,
                "lastError": v.last_error,
                "runs": v.runs,
            }
            for k, v in state.items()
        },
    }
    tmp = path.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)  # 同一文件系统内的替换是原子的
    except OSError as exc:
        log.warning("任务状态写入失败：%s", exc)


# ── 到点判断 ─────────────────────────────────────────────────


def pending_occurrence(
    issue: Issue,
    state: IssueState,
    now: datetime | None = None,
) -> datetime | None:
    """判断有没有「已经到点、但还没跑」的班次，有就返回**最早欠的那一次**。

    **核心判据不是「当前这一分钟是否命中」，而是「上次跑之后有没有命中过」。**
    差别在于：前者依赖调度器恰好在那分钟醒着 —— 进程重启、tick 延迟、机器休眠
    都会让那一分钟被跳过，任务就**静默漏跑**了。后者从 `lastRun` 往后推，
    只要那一刻已经过去，不管调度器当时在不在，都算欠着，天然抗重启。

    **返回最早那次而不是最近那次，是刻意的。** 停机三天后补跑，如果返回最近
    那次，报告上的 `lagSeconds` 只有几秒，「停机三天」这个信息就彻底丢了。
    返回最早那次，报告读起来是「本该三天前跑」—— 这才是排障时要的。

    一次只补跑一班（合并）：停机期间欠下的其余班次直接作废。一个每分钟一次的
    任务停机一天要补 1440 次，显然是错的 —— 监控类任务只关心「现在」。
    补跑之后 `lastRun` 被置为当前时刻，下一班从此刻重新起算。

    从没见过（`lastRun` 为空）时，起点取**文件自己的修改时间** ——
    意味着「新建的任务不会立刻跑，等到下一个排期点」。这是最少意外行为。
    """
    if not issue.schedulable:
        return None
    assert issue.when is not None and issue.when.cron is not None and issue.when.tz is not None

    now = now or datetime.now(timezone.utc)
    base = state.last_run_dt or issue.created_at
    nxt = issue.when.cron.next_after(base.astimezone(issue.when.tz))
    if nxt is None:
        return None
    return nxt if nxt <= now.astimezone(issue.when.tz) else None


def next_fire(issue: Issue, state: IssueState, now: datetime | None = None) -> datetime | None:
    """下一次该跑的时刻，纯粹给前端/日志看。"""
    if not issue.schedulable:
        return None
    assert issue.when is not None and issue.when.cron is not None and issue.when.tz is not None
    now = now or datetime.now(timezone.utc)
    base = state.last_run_dt or issue.created_at
    if base < now:
        base = now
    return issue.when.cron.next_after(base.astimezone(issue.when.tz))


def mark_run(
    state: dict[str, IssueState],
    issue_id: str,
    *,
    at: float,
    status: str,
    duration_ms: int | None = None,
    error: str | None = None,
    count: bool = True,
) -> None:
    """记一次运行。

    `count=False` 用于**开跑前的占坑**（`scheduler._execute` 先落一次
    `status="running"` 再执行）。那种写入不是一次「跑过的运行」，
    把它算进 `runs` 会让计数直接翻倍 —— 一处跑一次显示成两次。
    """
    entry = state.get(issue_id) or IssueState()
    entry.last_run = at
    entry.last_status = status
    entry.last_duration_ms = duration_ms
    entry.last_error = error
    if count:
        entry.runs += 1
    state[issue_id] = entry
