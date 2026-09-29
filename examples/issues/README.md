# 任务示例

这里的 `.md` 是**示例**，不会被执行 —— 后端只扫 `data/issues/`
（`data/` 在 `.gitignore` 里，所以真正的任务不会进仓库）。

想试哪个就复制过去：

```bash
mkdir -p data/issues
cp examples/issues/daily-profit.md data/issues/
```

后端 30 秒内会扫到它。不用等排期，直接跑：

```bash
curl -X POST localhost:8000/api/v1/issues/daily-profit/run
```

完整格式说明见 **[docs/04-定时任务.md](../../docs/04-定时任务.md)**。

---

## 这几个文件各自演示什么

| 文件 | 演示 |
|---|---|
| `daily-profit.md` | 最基本的用法 —— 每天定点跑一次，正文就是一句大白话 |
| `price-watch.md` | 多班次监控（每 6 小时），且正文里写了「没变化就不用长篇大论」 |
| `weekly-review.md` | 星期几的写法（`* * 1` = 每周一），以及一次测多个品、让结果可排序 |
| `card-only.md` | **没有 `when:`** —— 它不会被调度，只是一张列在清单里的看板卡片 |

## ⚠️ 两个前提

1. **`price-watch.md` 需要采集凭证**（`APIFY_TOKEN` / `EBAY_API_KEY`）。
   不配也不会伪造数据 —— 报告里会是一句明确的报错，`ok: false`。
   这本身是正确行为，想真跑起来就先把凭证配上。
2. **每跑一次都真实消耗额度。** `daily-profit.md` 只用 `profit.calc`（纯计算，
   不花钱、不需要网络），适合拿来做第一个测试。

## 关于正文的写法

正文就是你平时会对它说的那句话，**不需要模板语法**。但有一点值得注意：

它跑的时候**没人在旁边接着问**。所以正文里最好把「要什么」说完整 ——
比如 `price-watch.md` 里加了「跌幅不到 5% 就一句话带过」，
否则它每天都会给你写一篇长文，而绝大多数时候你只想知道「有没有事」。
