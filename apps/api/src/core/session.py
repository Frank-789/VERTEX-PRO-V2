"""会话记录（JSONL 追加写）。

每个会话一个文件：data/sessions/<id>.jsonl，一行一条消息。
选 JSONL 而不是数据库的理由：追加写不会因为进程被杀而损坏已有内容，
出问题时能直接打开看，也方便将来喂给别的分析脚本。

这里只存「对话」，不含工具调用的完整输出（那部分在 event-log 里）。
"""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from .paths import data_home

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_TURNS = 20
"""回灌给模型的历史条数上限。"""


def new_session_id() -> str:
    return uuid.uuid4().hex[:16]


def is_valid_id(session_id: str) -> bool:
    return bool(_SAFE_ID.match(session_id))


def _path(session_id: str) -> Path:
    # 会话 id 来自客户端，必须挡住路径穿越
    if not is_valid_id(session_id):
        raise ValueError(f"非法会话 id：{session_id!r}")
    d = data_home() / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{session_id}.jsonl"


def append(session_id: str, role: str, content: str) -> None:
    """追加一条消息。写失败不抛 —— 记不下历史不该让对话中断。"""
    try:
        rec = {"ts": time.time(), "role": role, "content": content}
        with _path(session_id).open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


def history(session_id: str, limit: int = MAX_TURNS) -> list[dict[str, Any]]:
    """读取最近若干条 user/assistant 消息，转成 OpenAI messages 格式。

    只吞 OSError（文件不存在很正常），非法 id 的 ValueError 必须往上抛 ——
    静默返回空列表会把攻击痕迹抹掉。
    """
    try:
        raw = _path(session_id).read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError:
        return []

    out: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue  # 半行（进程被杀）跳过就行
        if rec.get("role") in ("user", "assistant") and rec.get("content"):
            out.append({"role": rec["role"], "content": rec["content"]})

    # 上一轮如果中途失败，会留下一条没有回答的 user 记录。
    # 当前这句话是单独追加的，所以尾部悬空的 user 要去掉，
    # 否则会出现连续两条 user —— 部分供应商会直接报错。
    while out and out[-1]["role"] == "user":
        out.pop()

    # 同理，把相邻同角色的合并掉
    merged: list[dict[str, Any]] = []
    for m in out:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1] = {
                "role": m["role"],
                "content": merged[-1]["content"] + "\n" + m["content"],
            }
        else:
            merged.append(dict(m))

    return merged[-limit:]
