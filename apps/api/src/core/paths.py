"""路径解析。

所有可写状态统一落在 DATA_HOME 之下，容器里挂 /data 卷即可持久化。
绝不出现硬编码的绝对路径 —— 第一代把知识库写死成
`~/Desktop/Vertex/知识库`，在容器里必然失效且静默降级。
"""

from __future__ import annotations

import os
from pathlib import Path

# 项目根：src/core/paths.py -> src/core -> src -> apps/api -> apps -> 仓库根
_REPO_ROOT = Path(__file__).resolve().parents[4]


def repo_root() -> Path:
    """仓库根目录。"""
    return _REPO_ROOT


def data_home() -> Path:
    """可写状态根目录。"""
    raw = os.getenv("DATA_HOME")
    return Path(raw).expanduser().resolve() if raw else _REPO_ROOT / "data"


def config_dir() -> Path:
    """配置目录（只读，随仓库分发）。"""
    raw = os.getenv("CONFIG_HOME")
    return Path(raw).expanduser().resolve() if raw else _REPO_ROOT / "config"


def prompts_dir() -> Path:
    """提示词目录。"""
    raw = os.getenv("PROMPTS_HOME")
    return Path(raw).expanduser().resolve() if raw else _REPO_ROOT / "prompts"


def ensure_dirs() -> None:
    """建好运行期需要的目录。幂等。"""
    for sub in ("sessions", "inbox", "issues", "workspaces", "event-log", "cache"):
        (data_home() / sub).mkdir(parents=True, exist_ok=True)
