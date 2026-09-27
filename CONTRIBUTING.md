# 贡献指南

## 先读这两份

1. **[docs/01-架构重构方案.md](docs/01-架构重构方案.md)** —— 目标架构、迁移映射、分阶段计划
2. **[PROGRESS.md](PROGRESS.md)** —— 做到哪了、踩过哪些坑、当前堵点

`PROGRESS.md` 的用途是**换一个对话窗口（或换一个人）也不会失忆**，所以它必须保持最新。

---

## ⚠️ 一条不可越的线：许可证

本项目 **MIT**。我们参考的 [OpenAlice](https://github.com/TraderAlice/OpenAlice) 是 **AGPL-3.0**
（带网络条款的强 copyleft）。

> 只要服务通过网络向用户提供 AGPL 代码的功能，就**必须**把整个服务的完整源码以 AGPL-3.0 公开。

所以：

| 可以做 | 不可以做 |
|---|---|
| 读它的 `docs/`，学架构思想 | 复制它的 `src/` 代码 |
| 学设计模式（统一注册表、供应商路由、文件态自调度） | 照抄具体实现、常量、提示词 |
| 对齐设计规格（间距尺度、交互行为） | 搬运具体色值、文案 |

**思想不受著作权保护，表达受。** 拿不准的时候，自己重写一遍。

提交前请自查：这段代码我是不是从 AGPL 项目里抄的？如果是，重写。

---

## 开发环境

```bash
cd apps/api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd apps/web && npm install
cp .env.example .env
```

没有 API key 也能跑 —— 用仓库自带的假供应商，见
[docs/02-部署指南.md](docs/02-部署指南.md#一本地开发已验证可用)。

```bash
cd apps/api && .venv/bin/python dev/mock_provider.py
cd apps/api && .venv/bin/python -m uvicorn src.main:app --reload --port 8000
cd apps/web && npm run dev
```

---

## 提交前必须过的三关

```bash
# 1. 后端冒烟测试（21 项，不需要 key，不需要网络）
cd apps/api && .venv/bin/python tests/test_smoke.py

# 2. 前端构建（同时是 TypeScript 类型检查）
cd apps/web && npm run build

# 3. 密钥扫描
grep -rInE 'sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|apify_api_[a-zA-Z0-9]{10,}' . \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=.venv
```

CI（`.github/workflows/ci.yml`）会把这三关都跑一遍。

> **第 3 关不是形式主义。** 第一代把一个真实可用的 DeepSeek key 提交进了公开仓库的
> `.env.example`，被爬虫收录；还把三个密钥以 `NEXT_PUBLIC_*` 打包进了浏览器 bundle。
> 这两类事故一次就够了。

---

## 代码约定

### 后端

- **配置即数据** —— 行为开关放 `config/*.json`，不要新增 `os.getenv` 散落各处
- **不硬编码路径** —— 一律走 `core/paths.py`（第一代把知识库写死成 `~/Desktop/...`，容器里必然失效）
- **拿不到数据就报错** —— 工具绝不返回编造的数据。这是第一代最危险的问题
- **降级逻辑只写一份** —— 供应商路由统一在 `core/provider_router.py`
- **能力只注册一次** —— 新工具注册进 `core/tool_center.py`，不要另起一套注册表

### 前端

- 改之前先读 [apps/web/AGENTS.md](apps/web/AGENTS.md) —— 这版 Next.js 有破坏性变更
- 不裸 `fetch`，走 `src/lib/` 里的封装
- **永远不用 `NEXT_PUBLIC_*` 存密钥** —— 它会被打包进浏览器
- 颜色用语义令牌（`--background` / `--primary` …），不要写死十六进制值

### 提示词

改语气、改报告格式 → 改 `prompts/default/*.md`，**不要改代码**。

想本地实验而不影响仓库 → 放 `prompts/user/`（已 gitignore）。

---

## 提交信息

```
<类型>: <一句话说清改了什么>

feat:     新功能
fix:      修缺陷
docs:     文档
refactor: 重构（不改行为）
chore:    杂务
```

---

## 报告问题

请附上：

- `curl localhost:8000/health` 的输出
- 复现步骤
- 如果是工具失败，说明该工具的凭证是否已配置（`pending` 是**预期行为**，不是 bug）
