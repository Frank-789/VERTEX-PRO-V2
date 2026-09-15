#!/usr/bin/env python3
"""生成 Vertex 表情包（原创矢量图）。

设计：一个「购物袋」吉祥物，暖色调扁平风格，20 个表情。
输出为 SVG，写入 apps/web/public/stickers/vertex-default/。

用法：
    python3 scripts/generate_stickers.py
"""

from __future__ import annotations

import json
import pathlib

# ---------------------------------------------------------------- 调色板

INK = "#3B322A"          # 描边 / 五官
BG = "#FFF9F3"           # 底色点缀
BODY = "#E8A87C"         # 主体暖橙
ACCENT = "#D97757"       # 强调
BLUSH = "#F0A6A0"        # 腮红
WHITE = "#FFFFFF"

# 每个表情可覆写主体色，制造情绪差异
MOOD_COLOR = {
    "warning": "#E5B567",
    "nope": "#B8A99A",
    "sorry": "#C9B8AC",
    "exhausted": "#B8A99A",
    "confident": "#D98E5F",
    "celebrate": "#E08A5C",
    "heart": "#E39393",
    "laugh": "#EBAE72",
}

# ---------------------------------------------------------------- 零件
# 所有坐标基于 240x240 画布，吉祥物主体为圆角购物袋。


def bag(color: str) -> str:
    """购物袋主体 + 提手。"""
    return f"""
    <path d="M 92 84 q 0 -30 28 -30 q 28 0 28 30"
          fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>
    <rect x="52" y="80" width="136" height="122" rx="34"
          fill="{color}" stroke="{INK}" stroke-width="7"/>"""


def eyes(kind: str) -> str:
    lx, rx, y = 94, 146, 132
    if kind == "normal":
        return (f'<circle cx="{lx}" cy="{y}" r="9" fill="{INK}"/>'
                f'<circle cx="{rx}" cy="{y}" r="9" fill="{INK}"/>')
    if kind == "happy":  # ^ ^
        return (f'<path d="M {lx-11} {y+5} q 11 -14 22 0" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
                f'<path d="M {rx-11} {y+5} q 11 -14 22 0" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>')
    if kind == "closed":  # — —
        return (f'<path d="M {lx-11} {y} h 22" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
                f'<path d="M {rx-11} {y} h 22" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>')
    if kind == "wide":
        return (f'<circle cx="{lx}" cy="{y}" r="13" fill="{WHITE}" stroke="{INK}" stroke-width="6"/>'
                f'<circle cx="{rx}" cy="{y}" r="13" fill="{WHITE}" stroke="{INK}" stroke-width="6"/>'
                f'<circle cx="{lx}" cy="{y}" r="5" fill="{INK}"/>'
                f'<circle cx="{rx}" cy="{y}" r="5" fill="{INK}"/>')
    if kind == "squint":  # 满足的细眼
        return (f'<path d="M {lx-11} {y-2} q 11 9 22 0" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
                f'<path d="M {rx-11} {y-2} q 11 9 22 0" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>')
    if kind == "dizzy":  # x x
        return (f'<path d="M {lx-9} {y-9} l 18 18 M {lx+9} {y-9} l -18 18" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
                f'<path d="M {rx-9} {y-9} l 18 18 M {rx+9} {y-9} l -18 18" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>')
    if kind == "heart":
        return (heart(lx, y, 11) + heart(rx, y, 11))
    if kind == "upturn":  # 看向上方
        return (f'<circle cx="{lx}" cy="{y-3}" r="9" fill="{INK}"/>'
                f'<circle cx="{rx}" cy="{y-3}" r="9" fill="{INK}"/>'
                f'<path d="M {lx-12} {y-16} q 12 -7 24 0" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
                f'<path d="M {rx-12} {y-16} q 12 -7 24 0" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>')
    raise ValueError(kind)


def heart(cx: float, cy: float, r: float) -> str:
    return (f'<path d="M {cx} {cy+r*0.75} C {cx-r*1.5} {cy-r*0.3} {cx-r*0.5} {cy-r*1.2} {cx} {cy-r*0.35}'
            f' C {cx+r*0.5} {cy-r*1.2} {cx+r*1.5} {cy-r*0.3} {cx} {cy+r*0.75} Z" fill="{ACCENT}"/>')


def mouth(kind: str) -> str:
    cx, y = 120, 160
    if kind == "smile":
        return f'<path d="M {cx-16} {y} q 16 16 32 0" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    if kind == "grin":
        return (f'<path d="M {cx-22} {y-4} q 22 30 44 0 Z" fill="{INK}"/>'
                f'<path d="M {cx-8} {y+12} q 8 8 16 0 Z" fill="{BLUSH}"/>')
    if kind == "open":
        return f'<ellipse cx="{cx}" cy="{y+4}" rx="14" ry="17" fill="{INK}"/>'
    if kind == "flat":
        return f'<path d="M {cx-16} {y+2} h 32" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    if kind == "frown":
        return f'<path d="M {cx-16} {y+8} q 16 -16 32 0" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    if kind == "wavy":
        return (f'<path d="M {cx-20} {y} q 10 -11 20 0 q 10 11 20 0" fill="none"'
                f' stroke="{INK}" stroke-width="7" stroke-linecap="round"/>')
    if kind == "small":
        return f'<circle cx="{cx}" cy="{y+2}" r="6" fill="{INK}"/>'
    if kind == "smirk":
        return f'<path d="M {cx-14} {y+4} q 16 10 30 -6" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    raise ValueError(kind)


# ---------------------------------------------------------------- 装饰

def blush() -> str:
    return (f'<ellipse cx="76" cy="152" rx="13" ry="8" fill="{BLUSH}" opacity="0.75"/>'
            f'<ellipse cx="164" cy="152" rx="13" ry="8" fill="{BLUSH}" opacity="0.75"/>')


def sparkles() -> str:
    def star(cx, cy, r):
        return (f'<path d="M {cx} {cy-r} L {cx+r*0.28} {cy-r*0.28} L {cx+r} {cy}'
                f' L {cx+r*0.28} {cy+r*0.28} L {cx} {cy+r} L {cx-r*0.28} {cy+r*0.28}'
                f' L {cx-r} {cy} L {cx-r*0.28} {cy-r*0.28} Z" fill="{ACCENT}"/>')
    return star(38, 74, 13) + star(200, 100, 10) + star(190, 60, 7)


def sweat() -> str:
    return (f'<path d="M 190 96 q 12 16 12 24 a 12 12 0 0 1 -24 0 q 0 -8 12 -24 Z"'
            f' fill="#7FB3D5" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')


def zzz() -> str:
    return (f'<text x="186" y="70" font-family="system-ui,sans-serif" font-size="30"'
            f' font-weight="700" fill="{INK}">z</text>'
            f'<text x="204" y="48" font-family="system-ui,sans-serif" font-size="22"'
            f' font-weight="700" fill="{INK}">z</text>')


def question() -> str:
    return (f'<text x="186" y="86" font-family="system-ui,sans-serif" font-size="48"'
            f' font-weight="800" fill="{ACCENT}">?</text>')


def bang() -> str:
    return (f'<text x="188" y="86" font-family="system-ui,sans-serif" font-size="48"'
            f' font-weight="800" fill="#D9603F">!</text>')


def gears() -> str:
    return (f'<circle cx="182" cy="72" r="13" fill="none" stroke="{INK}" stroke-width="6"/>'
            f'<circle cx="202" cy="94" r="9" fill="none" stroke="{INK}" stroke-width="5"/>')


def magnifier() -> str:
    return (f'<circle cx="186" cy="72" r="15" fill="none" stroke="{INK}" stroke-width="6"/>'
            f'<path d="M 197 83 l 14 14" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>')


def cart() -> str:
    return (f'<path d="M 176 62 h 12 l 8 30 h -30 l 6 -22 h 22" fill="none"'
            f' stroke="{INK}" stroke-width="6" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="166" cy="102" r="5" fill="{INK}"/>'
            f'<circle cx="190" cy="102" r="5" fill="{INK}"/>')


def coin() -> str:
    return (f'<circle cx="192" cy="78" r="17" fill="{ACCENT}" stroke="{INK}" stroke-width="6"/>'
            f'<text x="192" y="86" text-anchor="middle" font-family="system-ui,sans-serif"'
            f' font-size="20" font-weight="800" fill="{WHITE}">¥</text>')


def cup() -> str:
    return (f'<path d="M 176 68 h 30 v 26 a 15 15 0 0 1 -30 0 Z" fill="{WHITE}"'
            f' stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M 176 78 h 30" stroke="{INK}" stroke-width="4"/>')


def image_icon() -> str:
    return (f'<rect x="172" y="58" width="42" height="34" rx="7" fill="{WHITE}"'
            f' stroke="{INK}" stroke-width="6"/>'
            f'<circle cx="184" cy="70" r="4" fill="{ACCENT}"/>'
            f'<path d="M 176 88 l 12 -12 l 9 8 l 8 -7 l 5 11" fill="none"'
            f' stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>')


def flag_done() -> str:
    return (f'<path d="M 182 56 v 44" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
            f'<path d="M 182 58 h 34 l -9 12 l 9 12 h -34 Z" fill="{ACCENT}"'
            f' stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')


# ---------------------------------------------------------------- 表情定义
# (文件名, 主体色覆写, 眼睛, 嘴巴, 额外装饰, 中文含义, 英文含义)

STICKERS = [
    ("wave",       None,      "happy",   "smile",  None,          "打招呼",   "Greeting / saying hello"),
    ("goodbye",    None,      "closed",  "smile",  None,          "收工告辞", "Saying goodbye"),
    ("thanks",     None,      "squint",  "grin",   blush(),       "谢谢",     "Thanks / appreciation"),
    ("sorry",      None,      "closed",  "frown",  sweat(),       "抱歉",     "Apology / feeling sorry"),
    ("thinking",   None,      "upturn",  "flat",   gears(),       "思考中",   "Thinking / considering"),
    ("searching",  None,      "normal",  "small",  magnifier(),   "找货中",   "Searching products"),
    ("calculating",None,      "squint",  "flat",   coin(),        "算账中",   "Calculating numbers"),
    ("generating", None,      "upturn",  "open",   image_icon(),  "出图中",   "Generating images"),
    ("success",    None,      "happy",   "grin",   flag_done(),   "搞定了",   "Done / success"),
    ("celebrate",  None,      "happy",   "open",   sparkles(),    "爆单了",   "Celebration / big win"),
    ("warning",    None,      "wide",    "wavy",   bang(),        "有风险",   "Warning / risk"),
    ("nope",       None,      "closed",  "flat",   None,          "不行",     "Refusal / saying no"),
    ("wait",       None,      "normal",  "small",  None,          "稍等",     "Wait a moment"),
    ("confused",   None,      "dizzy",   "wavy",   question(),    "迷惑了",   "Confused"),
    ("confident",  None,      "squint",  "smirk",  None,          "稳了",     "Confident / locked in"),
    ("exhausted",  None,      "closed",  "open",   zzz(),         "累瘫了",   "Exhausted"),
    ("coffee",     None,      "squint",  "smile",  cup(),         "喝口水",   "Taking a break"),
    ("shocked",    None,      "wide",    "open",   bang(),        "惊了",     "Surprise / shock"),
    ("skeptical",  None,      "squint",  "wavy",   question(),    "存疑",     "Skeptical"),
    ("laugh",      None,      "happy",   "grin",   blush(),       "笑死",     "Laughter / amusement"),
]


def render(filename: str, body_override: str | None, eye_kind: str,
           mouth_kind: str, extra: str | None) -> str:
    color = body_override or MOOD_COLOR.get(filename, BODY)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" width="240" height="240">',
        f'<circle cx="120" cy="124" r="112" fill="{BG}"/>',
        bag(color),
        eyes(eye_kind),
        mouth(mouth_kind),
    ]
    if extra:
        parts.append(extra)
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    out = root / "apps" / "web" / "public" / "stickers" / "vertex-default"
    out.mkdir(parents=True, exist_ok=True)

    manifest = []
    for filename, override, eye_kind, mouth_kind, extra, zh, en in STICKERS:
        svg = render(filename, override, eye_kind, mouth_kind, extra)
        (out / f"{filename}.svg").write_text(svg, encoding="utf-8")
        manifest.append({
            "file": f"{filename}.svg",
            "description": f"{en} / {zh}",
            "label": zh,
        })

    pack = {
        "schemaVersion": 1,
        "id": "vertex-default",
        "name": "Vertex · 经营助手",
        "version": "1.0.0",
        "stickers": manifest,
    }
    (out / "pack.json").write_text(
        json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"生成 {len(manifest)} 个表情 → {out}")


if __name__ == "__main__":
    main()
