# 更新日志

本文件记录**用户可见的变化**。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

> 第一代（[VERTEX-pro](https://github.com/Frank-789/VERTEX-pro)）的历史不在此追溯 ——
> 那是一套独立实现，V2 是重写，不是增量升级。

---

## [Unreleased]

### 计划中

- Phase 0 收尾：轮换第一代泄露的凭证，用 `git filter-repo` 清理旧仓库历史
- Phase 2 持久化：事件日志落盘、领域数据进 Postgres
- Phase 3 自动化：`issues/*.md` + `when:` frontmatter 文件自调度 → Store Pilot 真实化
- 色板切换器 UI（机制已就绪，界面上还没有入口）
- 落地页按新设计规格重排
- 后端鉴权（目前所有端点无鉴权，因此仅绑回环地址）

---

## 2026-09-27

### 新增

- **`Dockerfile` + `docker-compose.yml`** —— 后端可自托管
  - `tini` 作 PID 1、非 root（UID 10001）、`HEALTHCHECK` 打 `/health`
  - `/data` 持久卷；端口默认只绑 `127.0.0.1`（后端持有全部密钥且无鉴权）
  - 构建必须在仓库根执行（镜像需要 `config/` 与 `prompts/`）
- **`.dockerignore`** —— 密钥、依赖、构建产物、运行期状态、文档一律不进镜像
- **`.github/workflows/ci.yml`** —— 三个 job：后端冒烟测试 / 前端构建 / 密钥扫描
- **`CHANGELOG.md`**、**`CONTRIBUTING.md`**、**`.gitattributes`**
- **`docs/02-部署指南.md`**、**`docs/03-配置参考.md`**
- `docs/images/` —— 5 张本地实拍截图 + logo

### 变更

- **`README.md` 按 OpenAlice 的排布完全重写**：居中 logo → 标题 → 徽章 → 大截图 →
  快速开始 → 功能（### 小节各配图）→ 架构 → 部署 → 文档 → 路线图 → 许可证
- 仓库 description 精简为一行，补齐 12 个 topics

### 修复

- **解除推送堵点** —— 之前 `github.com:443` 间歇性不可达且本机无可用凭证；
  现 `git push` 直接可用（用一次性 URL，token 不落盘）

### 已知限制

- 镜像**尚未实际构建验证**（开发机没有 Docker）。路径解析逻辑已在
  模拟的容器目录结构下验证通过，但 `requirements.txt` 的版本兼容性未在
  `python:3.11-slim` 上实测
- `.github/workflows/ci.yml` 因 token 缺少 `workflow` 作用域暂未推送

---

## 2026-09-15

### 新增

- **开发用假供应商** `apps/api/dev/mock_provider.py` —— 本地起一个 OpenAI 兼容端点，
  让「工具调用 → 流式回答 → 表情包」整条链路**零成本**闭环验证
- `apps/web` 落地页与对话页（Next.js 16 App Router）
- **20 个原创 SVG 表情**，购物袋吉祥物，程序化生成（`scripts/generate_stickers.py`）
- 四套可切换色板：`paper` / `linen` / `graphite` / `midnight`，未选择时跟随系统深色偏好
- `apps/api/tests/test_smoke.py` —— 21 项冒烟测试，**不需要 API key 也不需要网络**

### 变更

- **对话界面按公开设计规格完全重排**
  - 用户发言右对齐气泡；助手回复直接铺在画布上、无气泡无描边
    （不对称是刻意的：用户的话是「一句话」，助手的话是「一份东西」）
  - 工具调用从独立卡片改为**内嵌轨道**，缩进出现在回答中间
  - 阅读宽度 736px 居中，消息间距 32px
  - 输入框改为 26px 大圆角 + 多层淡阴影，不描边
  - 删掉了打字光标 —— 用过程文字与结论文字的深浅对比表达「正在生成」
  - 工具成功态**不用绿色**（绿在这个产品里表示「盈利 / 安全」）

### 修复

- 输入框双重聚焦环（`globals.css` 里的无层级 `:focus-visible` 永远赢过 `@layer` 规则）
- 切换色板后颜色不变（Tailwind 会烤死 `@theme` 的值 → 改用 `@theme inline`）
- 表情包尺寸不生效（定值 `width/height` 与 240×240 的 SVG 冲突 → 属性占位 + `style` 限幅）
- 后端启动被拖垮（依赖 Chromium 的模块在顶层 import）

### 安全

- **彻底移除 `NEXT_PUBLIC_*` 密钥用法**。第一代把三个密钥打包进浏览器 bundle，人人可见
- 前端改为**同源代理**访问后端（`next.config.ts` rewrites），从根上消灭 CORS
- `.env` 进 `.gitignore` 且 `chmod 600`
- 工具契约改为**拿不到数据就报错**，绝不返回编造的数据

---

## 2026-09-14

### 新增

- 仓库初始化，选定 **MIT** 许可证（与参考项目 OpenAlice 的 AGPL-3.0 明确划清界限）
- [docs/01-架构重构方案.md](docs/01-架构重构方案.md) —— 对标分析、现状体检、
  迁移映射表、分阶段计划、许可证红线

### 变更

- 后端按 `core/` 分层重建：`config` / `paths` / `prompts` / `tool_center` /
  `provider_router` / `session` / `agent`
- 合并第一代**两套互不相通的注册表**（`tools/` 与 `crawler/`）为统一 ToolCenter
- 供应商降级逻辑从前后端各一份**收敛为一份**（`core/provider_router.py`）
- 提示词改为双层覆盖：`prompts/default/`（进 git）+ `prompts/user/`（gitignore）
