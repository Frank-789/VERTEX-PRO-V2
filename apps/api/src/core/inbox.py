"""Inbox —— 定时任务的产出投递到这里。

一个报告一个 Markdown 文件，落在 `data/inbox/`：

    data/inbox/2026-09-28T090012-price-watch.md

**文件名带上时间戳前缀**，所以按文件名排序就等于按时间排序 ——
不需要额外维护一份索引文件。索引和真实文件一旦不同步就是个持续的小麻烦，
不如直接从目录算出来。

正文是模型的原始回答，头部是这次运行的元信息（排期时刻、实际开跑时刻、
延迟多久、耗时、用了哪些工具、对应的 event-log turn id）。
**延迟单独记一个字段**：错过的班次只补跑一次，`lagSeconds` 是唯一能看出
「这次其实是三天前就该跑的」的地方。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from .paths import data_home

log = logging.getLogger(__name__)

# 尾部宽松到 72 —— 撞名时会加上 `-2` 之类的序号，那部分也含在这里面。
# 这个正则只负责挡路径穿越和怪字符，不负责精确解析任务 id（id 以 frontmatter 为准）。
_FILENAME = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}-[A-Za-z0-9_-]{1,72}\.md$")

_BODY_LIMIT = 20_000
"""单份报告正文的落盘上限。超了截断并打标 —— 一个跑偏的任务不该写满磁盘。"""


class BadReportName(ValueError):
    """文件名不合法（含路径穿越尝试）。"""


def inbox_dir() -> Path:
    d = data_home() / "inbox"
    d.mkdir(parents=True, exist_ok=True)
    return d


def is_valid_name(name: str) -> bool:
    return bool(_FILENAME.match(name))


def _path(name: str) -> Path:
    # 报告名来自 URL，必须挡住 `../` 之类
    if not is_valid_name(name):
        raise BadReportName(f"非法报告名：{name!r}")
    return inbox_dir() / name


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H%M%S")


def write(
    *,
    issue_id: str,
    title: str,
    body: str,
    run_at: datetime,
    scheduled_at: datetime | None = None,
    duration_ms: int | None = None,
    ok: bool = True,
    steps: int = 0,
    tools: list[str] | None = None,
    turn: str | None = None,
    error: str | None = None,
) -> Path | None:
    """写一份报告。失败返回 None 并打 warning —— 和 event_log 一样，
    投递是旁路，不能因为它写不进去就把整个任务判失败。"""
    # issue_id 会被拼进文件名。写入口也必须校验 —— 只靠读入口校验的话，
    # 一个带 `../` 的 id 在**写入时**就已经把文件放到目录外面去了。
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", issue_id):
        log.warning("任务 id 不合法，拒绝写报告：%r", issue_id)
        return None

    name = f"{_stamp(run_at)}-{issue_id}.md"
    truncated = len(body) > _BODY_LIMIT
    text = body[:_BODY_LIMIT]

    meta: dict[str, object] = {
        "issue": issue_id,
        "title": title,
        "runAt": run_at.isoformat(),
        "durationMs": duration_ms,
        "ok": ok,
        "steps": steps,
        "tools": tools or [],
        "turn": turn,
    }
    if scheduled_at is not None:
        meta["scheduledAt"] = scheduled_at.isoformat()
        # 排期时刻和实际开跑时刻差多少秒。停机后补跑的那次，这个数会很大，
        # 是唯一能看出「这次迟到」的地方。
        meta["lagSeconds"] = int((run_at - scheduled_at).total_seconds())
    if error:
        meta["error"] = error
    if truncated:
        meta["truncated"] = True

    try:
        import yaml

        # sort_keys=False 保住字段顺序 —— 报告是给人看的，顺序乱了读起来累
        head = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
        content = f"---\n{head}\n---\n\n{text}\n"
        # 文件名的时间戳只精确到秒，同一秒里跑两次同一个任务（比如手动触发
        # 紧跟在定时之后）会撞名。收件箱是只追加的审计记录，静默覆盖等于丢一份
        # 报告 —— 撞了就加序号，不覆盖。
        path = inbox_dir() / name
        seq = 2
        while path.exists():
            path = inbox_dir() / f"{_stamp(run_at)}-{issue_id}-{seq}.md"
            seq += 1
        path.write_text(content, encoding="utf-8")
        return path
    except Exception as exc:  # noqa: BLE001
        log.warning("报告写入失败（不影响任务本身）：%s", exc)
        return None


def _read_meta(path: Path) -> dict:
    """只取文件名和 frontmatter，不读正文 —— 列表接口不该把几十份报告全文拖出来。"""
    out: dict[str, object] = {"name": path.name, "size": path.stat().st_size}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return out
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            try:
                import yaml

                meta = yaml.safe_load("\n".join(lines[1:i])) or {}
                if isinstance(meta, dict):
                    out.update(meta)
            except Exception:  # noqa: BLE001
                pass
            break
    return out


def list_reports(limit: int = 50) -> list[dict]:
    """最近的报告，新的在前。

    文件名前缀是时间戳，所以**按文件名倒序就是按时间倒序** —— 用 mtime 反而
    不准（复制、恢复备份都会改 mtime）。
    """
    d = inbox_dir()
    names = sorted((p for p in d.glob("*.md") if is_valid_name(p.name)), reverse=True)
    return [_read_meta(p) for p in names[: max(1, limit)]]


def read(name: str) -> str:
    path = _path(name)
    if not path.is_file():
        raise FileNotFoundError(name)
    return path.read_text(encoding="utf-8")


def count() -> int:
    return sum(1 for p in inbox_dir().glob("*.md") if is_valid_name(p.name))
