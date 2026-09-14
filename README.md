<div align="center">

# Vertex

**面向中小电商卖家的 AI 经营决策智能体**

从选品调研到主图生成，一条对话跑完全流程。

[![Status](https://img.shields.io/badge/status-架构重构中-orange)]()
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python%203.11-009688)](https://fastapi.tiangolo.com)

</div>

---

> **📌 当前状态：V2 架构重构中**
>
> 本仓库是 Vertex 的第二代实现，正在按分阶段计划重建。线上运行的仍是第一代版本
> （[VERTEX-pro](https://github.com/Frank-789/VERTEX-pro) · [vertex-pro-pink.vercel.app](https://vertex-pro-pink.vercel.app)）。
>
> 重构方案见 **[docs/01-架构重构方案.md](docs/01-架构重构方案.md)**。

---

## 它解决什么问题

中小电商卖家做经营决策时，工具是割裂的：选品看一个站、比价开一个表、做主图找设计师、盯差评靠手动刷后台。信息散在五六个地方，决策靠经验拍脑袋。

Vertex 把这些收进一条对话：**说清楚你想卖什么，它自己去采集数据、跑分析、给结论，需要出图就出图，需要盯盘就定时盯。**

## 功能

| 模块 | 能力 |
|---|---|
| **Vertex Chat** | 核心智能体对话。自然语言 → 自动采集多平台数据 → 五维选品分析报告 |
| **Market Lab** | 数据分析工作台。查询历史、平台对比、价格分布、机会排行、导出 |
| **Creative Studio** | 电商主图套件。白底图 / 场景图 / 卖点图 / 对比图 / 详情首屏 + Listing 文案 |
| **Store Pilot** | 售中监控。库存预警、差评提醒、清货建议、滞销识别 |
| **Data Crawler** | 数据采集工作台。多平台商品搜索、价格监控、评论抓取、货源扫描 |
| **Settings** | 商家画像。资金安全线计算、风险偏好、经营目标配置 |

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Next.js 16 (App Router) · React 19 · Tailwind v4 · Zustand · SWR |
| 后端 | FastAPI · Uvicorn · Python 3.11 |
| AI | DeepSeek（主）· Kimi（降级）· 可扩展生图供应商 |
| 采集 | Oxylabs · Apify · eBay Browse API · Playwright |
| 存储 | JSONL（会话 / 事件 / 任务轨迹）+ Postgres（领域数据） |
| 部署 | Vercel（前端）· Docker（后端） |

## 架构

```
apps/
  web/     Next.js 前端（Vercel）
  api/     FastAPI 后端（Docker）
    src/
      core/       配置 · 路径 · 事件日志 · 工具注册表 · 供应商路由 · 凭证加密
      providers/  AI 供应商适配（DeepSeek / Kimi / 生图）
      tools/      平台数据工具
      crawler/    采集适配器
      domain/     业务领域（选品分析 / 主图策划 / 售中监控）
      issues/     定时任务（文件即任务）
      inbox/      报告回流
      api/        路由层
config/    配置即数据（JSON + 校验）
prompts/   提示词双层覆盖（default 进 git / user 覆盖）
data/      持久化根（挂载 /data）
```

设计说明详见 [docs/01-架构重构方案.md](docs/01-架构重构方案.md)。

## 部署

- **前端 → Vercel**：纯 UI 层，经同源代理转发到后端
- **后端 → Docker**：常驻进程，持久卷挂载 `/data`

> 智能体运行时需要常驻进程、持久文件系统和定时调度，**无法运行在 Serverless 环境**。
> Vercel 只承载 UI。

## 快速开始

> 实施中，脚手架落地后补全本节。

## 许可证

[MIT](LICENSE)

---

<div align="center">
<sub>本项目的架构设计参考了 <a href="https://github.com/TraderAlice/OpenAlice">OpenAlice</a>（AGPL-3.0）的公开文档与设计思想。<br>
未复制其任何源代码，本项目以 MIT 独立实现。</sub>
</div>
