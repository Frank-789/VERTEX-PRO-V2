"""cron 表达式解析与匹配。**无第三方依赖。**

为什么不装 `croniter`：这里只用得上两件事 —— 「某个时刻是否命中」和
「严格晚于某时刻的下一个命中」—— 5 个字段的语法（`*` `,` `-` `/`）穷举下来
不到 100 行。为这点需求引一个依赖不划算，而且 croniter 还夹带它自己的
时区语义，出了问题要在别人的代码里找。

**时区处理（这块最容易错）**：所有算术都在目标时区的**墙上时间**里做，
不是在 UTC 时间轴上。也就是说 `0 9 * * *` + `Asia/Shanghai` 永远意味着
「当地早上 9 点」，不论冬夏。代价是夏令时切换那天的个别分钟可能被跳过或
重复 —— 这与系统 cron 的行为一致，属于有意为之，不是 bug。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

MAX_SCAN_DAYS = 4 * 366
"""向前找下一个命中时刻时最多扫多久。

四年是为了兜住 `0 0 29 2 *`（只在闰年 2 月 29 日跑）这种极端表达式。
扫不到就返回 None，调用方按「永不再跑」处理。
"""

# (属性名, 报错时用的中文名, 最小值, 最大值)
# 属性名和显示名必须分开 —— 混用会让中文名直接当关键字参数传进构造函数。
_FIELDS: tuple[tuple[str, str, int, int], ...] = (
    ("minute", "分钟", 0, 59),
    ("hour", "小时", 0, 23),
    ("dom", "日", 1, 31),
    ("month", "月", 1, 12),
    ("dow", "星期", 0, 7),  # cron 里 0 和 7 都表示周日
)


def _int(text: str, name: str, lo: int, hi: int) -> int:
    if not text.lstrip("-").isdigit():
        raise ValueError(f"{name}字段「{text}」不是数字")
    value = int(text)
    if not lo <= value <= hi:
        raise ValueError(f"{name}字段 {value} 超出范围 {lo}-{hi}")
    return value


def _parse_field(text: str, name: str, lo: int, hi: int) -> set[int] | None:
    """把单个字段展开成允许值集合。

    **返回 None 表示这个字段是 `*`（未加限制）** —— 调用方需要靠这个信息
    实现「日 和 星期 都写了才取 OR」的标准 cron 语义，所以不能简单返回全集。
    """
    text = text.strip()
    if text == "*":
        return None

    out: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            raise ValueError(f"{name}字段里有空项：{text!r}")

        step = 1
        if "/" in part:
            part, _, raw_step = part.partition("/")
            if not raw_step.isdigit() or int(raw_step) < 1:
                raise ValueError(f"{name}字段的步长非法：{raw_step!r}")
            step = int(raw_step)
            if not part:
                part = "*"

        if part == "*":
            start, end = lo, hi
        elif "-" in part:
            raw_lo, _, raw_hi = part.partition("-")
            start = _int(raw_lo, name, lo, hi)
            end = _int(raw_hi, name, lo, hi)
            if start > end:
                raise ValueError(f"{name}字段的区间反了：{part!r}")
        else:
            start = end = _int(part, name, lo, hi)

        out.update(range(start, end + 1, step))

    # `*/1`、`0-59` 这种写全了的，等同于 `*`。按未限制处理更符合直觉 ——
    # 否则「日 写了 1-31」和「日 写了 *」会得到不同的 dom/dow 组合语义。
    if out == set(range(lo, hi + 1)):
        return None
    return out


@dataclass(frozen=True)
class CronSpec:
    """一条解析好的 5 字段 cron。"""

    expr: str
    minute: set[int] | None
    hour: set[int] | None
    dom: set[int] | None
    month: set[int] | None
    dow: set[int] | None

    @classmethod
    def parse(cls, expr: str) -> CronSpec:
        parts = expr.split()
        if len(parts) != 5:
            raise ValueError(
                f"cron 必须是 5 个字段（分 时 日 月 星期），收到 {len(parts)} 个：{expr!r}"
            )
        values = {
            attr: _parse_field(raw, label, lo, hi)
            for raw, (attr, label, lo, hi) in zip(parts, _FIELDS)
        }
        # cron 里 7 是周日，Python 里 0 是周一。统一到 cron 的编号前先把 7 折成 0。
        if values["dow"] and 7 in values["dow"]:
            values["dow"] = (values["dow"] - {7}) | {0}
        return cls(expr=expr, **values)

    def _day_match(self, day: date) -> bool:
        """日 / 星期 的联合判断。"""
        if self.month is not None and day.month not in self.month:
            return False

        dom_ok = self.dom is None or day.day in self.dom
        # Python: 周一=0 … 周日=6；cron: 周日=0 … 周六=6
        cron_dow = (day.weekday() + 1) % 7
        dow_ok = self.dow is None or cron_dow in self.dow

        if self.dom is None and self.dow is None:
            return True
        if self.dom is None:
            return dow_ok
        if self.dow is None:
            return dom_ok
        # 两个都写了 → 取 **OR**。这是标准 cron 的行为（不是 AND），
        # 也是最常被误解的一条：`0 0 1 * 1` 是「每月 1 号 **或** 每周一」。
        return dom_ok or dow_ok

    def matches(self, moment: datetime) -> bool:
        """`moment` 这一分钟是否命中。秒和微秒忽略。"""
        return (
            self._day_match(moment.date())
            and (self.hour is None or moment.hour in self.hour)
            and (self.minute is None or moment.minute in self.minute)
        )

    def next_after(self, after: datetime) -> datetime | None:
        """严格晚于 `after` 的下一个命中时刻，保持同一时区。

        在墙上时间里逐级推进（月/日 → 时 → 分），不是逐分钟暴力扫描 ——
        否则一条年跑一次的表达式要空转 50 万次。
        """
        tz = after.tzinfo
        # 先摘掉时区做纯墙上时间算术，算完再贴回去。见模块开头的说明。
        cur = (after.replace(tzinfo=None) + timedelta(minutes=1)).replace(
            second=0, microsecond=0
        )
        limit = cur + timedelta(days=MAX_SCAN_DAYS)

        while cur < limit:
            if self.month is not None and cur.month not in self.month:
                cur = (cur + timedelta(days=1)).replace(hour=0, minute=0)
                continue
            if not self._day_match(cur.date()):
                cur = (cur + timedelta(days=1)).replace(hour=0, minute=0)
                continue
            if self.hour is not None and cur.hour not in self.hour:
                cur = (cur + timedelta(hours=1)).replace(minute=0)
                continue
            if self.minute is not None and cur.minute not in self.minute:
                cur += timedelta(minutes=1)
                continue
            return cur.replace(tzinfo=tz)

        return None

    def describe(self) -> str:
        """给日志和接口用的人话摘要。不求完整，求一眼能懂。"""
        if self.minute is None and self.hour is None and self.dom is None:
            if self.dow is None and self.month is None:
                return "每分钟"
        bits: list[str] = []
        if self.month is not None:
            bits.append(f"{sorted(self.month)} 月")
        if self.dom is not None:
            bits.append(f"{sorted(self.dom)} 日")
        if self.dow is not None:
            names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
            bits.append("/".join(names[d] for d in sorted(self.dow)))
        if self.hour is not None:
            bits.append(f"{sorted(self.hour)} 点")
        if self.minute is not None:
            bits.append(f"{sorted(self.minute)} 分")
        return " ".join(bits) if bits else "每分钟"
