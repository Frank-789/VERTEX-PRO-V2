# VERTEX-PRO-V2 进度日志

> 这份文件的用途：**换一个对话窗口也不会失忆**。
> 任何人（或任何 AI）接手时，先读这里，再读 `docs/01-架构重构方案.md`。
> 规则：每完成一件事就更新这里，别攒着写。

**最后更新**：2026-09-15
**当前阶段**：**前后端已端到端跑通**，可以对话、调工具、发表情包。
下一步是 Phase 0 止血（轮换泄露的密钥）。

---

## 一、这个项目是什么

电商经营智能体。用户用大白话问「这个品能不能做」「帮我算算利润」，
它调工具拿真实数据，算完给结论，还会发表情包。

**对标对象**：[TraderAlice/OpenAlice](https://github.com/TraderAlice/OpenAlice)。
学的是**架构思路和产品体验**，不是代码 —— 对方是 AGPL-3.0，
抄代码会传染整个项目，我们保持 MIT。（详见方案文档第 9 章）

**仓库**：https://github.com/Frank-789/VERTEX-PRO-V2
**上一代**：https://github.com/Frank-789/VERTEX-pro （有 4 个待修的严重缺陷，见下）

---

## 二、已经做完的

### 规划与仓库

- [x] 通读 OpenAlice 的架构（用 GitHub API + raw 文件，因为 `git clone` 在这个环境里被墙）
- [x] 写完整重构方案 `docs/01-架构重构方案.md`（10 章，27KB）
- [x] 纠正了三个最初的误判（都写进方案文档了）：
  - OpenAlice **有**部署到 Vercel，但只是静态 demo shell，不是运行时
  - OpenAlice 是交易机器人，VertEx 是电商 —— 功能不能照搬，架构可以
  - Alice 的运行时要常驻进程 + 持久文件系统 + spawn 子进程，**结构上不可能跑在 Vercel**
- [x] 建 MIT `LICENSE`（版权人：罗鑫坤 / Frank-789）
- [x] 写 `README.md`（按 OpenAlice 的呈现方式：徽章 → 一句话定位 → 状态横幅 → 功能表 → 技术栈表 → 架构图 → 部署）
- [x] 写 `.gitignore`（重点：`.env`、`data/*`、`prompts/user/`）
- [x] 把方案文档推成了 V2 仓库的第一个 commit

### 表情包（这是「人性化」的关键）

- [x] `scripts/generate_stickers.py` —— 程序化生成 **20 个原创 SVG 表情**
  - 形象：购物袋吉祥物（原创，不是 Alice 的资产）
  - 20 个：打招呼 / 收工告辞 / 谢谢 / 抱歉 / 思考中 / 找货中 / 算账中 / 出图中 /
    搞定了 / 爆单了 / 有风险 / 不行 / 稍等 / 迷惑了 / 稳了 / 累瘫了 / 喝口水 / 惊了 / 存疑 / 笑死
  - 已经截图逐个肉眼验证过，渲染都正常

### 前端 `apps/web/` （Next.js 16 + React 19 + Tailwind v4）

- [x] 设计系统 `src/app/globals.css` —— **色板架构对齐 OpenAlice**
  - **两层结构**：`--background/--foreground/--card/--primary/--border` 等语义名
    （shadcn 业界通用约定）+ `@theme inline` 映射到 Tailwind 工具类。
    `inline` 是必须的 —— 不加的话 Tailwind 构建期会把色值烤死，切色板失效。
  - **四个可切换色板**：`paper`（暖白，默认）/ `linen`（冷纸面）/
    `graphite`（深色中性灰）/ `midnight`（深色偏蓝）。切法：
    `document.documentElement.setAttribute('data-palette', 'graphite')`
  - 没显式选色板时跟随系统深色偏好；选过就听用户的
  - 圆角尺度（5/8/10/12/16/20）与动效令牌（110/160/250ms +
    `cubic-bezier(0.22,1,0.36,1)`）对齐对方公开规格
  - 蓝色只用于交互、绿/红表财务语义、琥珀表警告；无渐变无毛玻璃
  - 数字用等宽字形（tabular numerals）；动效 `prefers-reduced-motion` 全量降级
  - **色值是自己推的，不是照抄**。设计语言（暖白纸面 + 克制的蓝 + 细分隔线）
    是思路，可以学；具体十六进制值属对方代码，我们保持 MIT，不搬。
    另外对方是仪表盘只需两级文字色，我们要排长回答，多加了
    `soft/faint/ghost` 三级作为超集。
- [x] `src/lib/types.ts` —— 消息由「块」组成（文本块/表情块/工具块），
      工具调用因此能出现在回答**中间**，而不是被挤到开头
- [x] `src/lib/stickers.ts` —— `[[sticker/xxx.svg]]` 语法解析
- [x] `src/lib/useChat.ts` —— SSE 流式解析（用 fetch 不用 EventSource，因为要 POST）
- [x] `src/components/conversation/` —— 六个组件：
  - `MessageItem` 刻意**不做** IM 那种左右气泡，用左侧竖线区分，更像工作台
  - `ToolCallCard` 默认折叠，展开看原始返回
  - `StickerBubble` 无气泡底，104×104
  - `RichText` 先切表情再走 Markdown
  - `Composer` 自动增高、Enter 发送、Shift+Enter 换行、Esc 打断、中文输入法防误发
  - `ConversationTranscript` 只在用户本来就贴着底部时才自动滚动
- [x] 落地页 `page.tsx`（一个输入框 + 4 张示例卡）
- [x] 对话页 `chat/page.tsx`（`?q=` 自动发送一次）
- [x] `next.config.ts` 同源代理 `/api/v1/*` → 后端，**彻底消灭 CORS**，
      也顺带保证 `NEXT_PUBLIC_*` 密钥泄露的事不会再发生
- [x] 开发服务器起得来，落地页和对话页都截图确认过渲染正常

### 后端 `apps/api/` （FastAPI）

- [x] `core/paths.py` —— 所有可写状态收进 `DATA_HOME`，容器挂 `/data` 卷即可
- [x] `core/config.py` + `config/providers.json` —— 供应商按能力分组，DeepSeek 主、Kimi 备
- [x] `core/provider_router.py` —— 降级逻辑**只此一份**
      （第一代在前后端各写一遍，改一处必忘另一处）
- [x] `core/prompts.py` + `prompts/default/persona.md` —— 人格与表情包使用规则
      （关键规则：一条回复最多 1 个表情；用户说亏钱了/遇到纠纷了，禁用表情）
- [x] `core/tool_center.py` —— 合并第一代**两套互不相通的注册表**
- [x] `core/session.py` —— 会话 JSONL 追加写，挡路径穿越
- [x] `core/agent.py` —— Agent 循环（工具轮 → 流式作答）
- [x] 三个工具：`profit.calc`（纯计算，无需凭证）、`ebay.search`、`apify.scrape`
      ——**拿不到数据一律报错，绝不伪造**（第一代会造假数据，这是危险的）
- [x] `api/chat.py` —— SSE 端点（`POST /api/v1/chat`、`GET /api/v1/tools`）
- [x] `main.py` —— FastAPI 组装，启动时把「供应商/工具/数据目录」状态打进日志，
      `/health` 顺带暴露配置缺口，排障不用猜
- [x] `dev/mock_provider.py` —— **开发用假供应商**。没有它，改一句提示词、
      调一下工具卡片样式，都得先申请 API key 再烧额度。有了它前端和 Agent
      循环的改动都能本地闭环验证，零成本。
      用法：`python dev/mock_provider.py` + `.env` 里加 `MOCK_API_KEY=dev`
- [x] **端到端跑通并截图确认**：浏览器 → Next 同源代理 → FastAPI →
      Agent 循环 → 工具执行 → 回流模型 → 流式回答 + 表情包，整条链路验证过

### 验证

- [x] `apps/api` 冒烟测试 **21 项全过**（工具注册 / 凭证缺失必须报错 /
      SSE 事件顺序与字段 / 会话落盘 / 路径穿越防护），脚本在
      `apps/api/tests/test_smoke.py`，**不需要任何 API key**，CI 里也能跑：
      `cd apps/api && .venv/bin/python tests/test_smoke.py`
- [x] `npm run build` 通过，TypeScript 无错
- [x] 浅色 / 深色两套色板都截图确认

---

## 三、还没做的

### Phase 0 止血（**最高优先级，代码再漂亮也挡不住密钥泄露**）

- [ ] 轮换两个泄露的 GitHub PAT（写在 `~/Desktop/部署流程.txt` 里，明文）
- [ ] 轮换泄露的 DeepSeek key（`sk-1b1de9af...`，**曾提交在公开仓库的 `.env.example`**）
- [ ] 轮换 Apify token（`apify_api_4kwI...`，用户说别泄露，目前只存在本地 `.env`）
- [ ] 用 `git filter-repo` 从 VERTEX-pro 历史里彻底抹掉那个 key（改文件没用，历史还在）
- [ ] 删掉上一代前端里的三个 `NEXT_PUBLIC_*` 密钥（会打包进浏览器，人人可见）
- [ ] Dockerfile 补 `playwright install chromium`（第一代容器里没浏览器，采集工具全废）
- [ ] 修 `render.yaml`

### Phase 2 持久化

- [ ] 事件日志落盘 `data/event-log/`（JSONL）
- [ ] Postgres 存领域数据（商品、利润测算记录）——**结构已定，还没建表**

### Phase 3 自动化（等爬虫凭证）

- [ ] `data/issues/<id>.md` + `when:` frontmatter 自调度
      —— 学 Alice 用**文件**替代事件总线：进程重启后任务不丢
- [ ] 让「店铺管家」（Store Pilot）从演示壳变成真能跑

### Phase 4 部署与呈现

- [ ] Docker 多阶段构建 + `/data` 卷 + 只在回环地址暴露端口
- [ ] Vercel 部署静态 UI demo shell（**只放 demo，不放运行时**）
- [ ] README 补 UI 截图（用户特别提过「他还会发一个 ui 图片」）
- [ ] GitHub Releases 打包桌面版

---

## 四、怎么跑起来

```bash
# 一次性：装依赖
cd apps/api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd apps/web && npm install

# 配置：把根目录的 .env.example 复制成 .env，至少填 DEEPSEEK_API_KEY
cp .env.example .env

# 起服务（三个终端）
cd apps/api && .venv/bin/python -m uvicorn src.main:app --reload --port 8000
cd apps/web && npm run dev                      # http://localhost:3000
cd apps/api && .venv/bin/python dev/mock_provider.py   # 可选：假供应商

# 验证
curl localhost:8000/health                     # 看供应商与工具状态
cd apps/api && .venv/bin/python tests/test_smoke.py    # 不需 key
```

**没有 API key 时**：在 `.env` 里填 `MOCK_API_KEY=dev` 并起 mock_provider，
整条链路（工具调用 + 流式 + 表情包）都能跑通，不花一分钱。

**换深色外观**：`document.documentElement.setAttribute('data-palette','graphite')`

---

## 五、踩过的坑（别重蹈覆辙）

| 坑 | 根因 | 解法 |
|---|---|---|
| 输入框出现**双重聚焦环** | globals.css 里的 `:focus-visible` 是**无层级**样式，而 CSS 里无层级样式**永远赢过**任何 `@layer`，与优先级无关 | 把规则包进 `@layer base`（文件里已加注释说明） |
| `git clone` / WebFetch 打不开 GitHub | 该环境对 github.com 直连被拦 | 走 `curl api.github.com` + `raw.githubusercontent.com` |
| 拉 OpenAlice 的 `main` 分支 404 | 它的默认分支是 **`master`** | 用 master |
| 后端工具导入拖垮启动 | 顶楼 import 依赖 Chromium 的模块 | 注册放进函数内部 + try/except（已实现） |
| `ToolCenter.ready()` 崩溃 | 遍历 `self._tools` 拿到的是**键（字符串）**不是值 | 改成 `.values()`。是冒烟测试抓出来的 —— 所以别跳过它 |
| 切色板后颜色不跟着变 | Tailwind 会在构建期把 `@theme` 的值烤死 | 用 `@theme inline`，让工具类输出 `var(...)` 而不是字面值 |

---

## 六、给下一个对话窗口的话

1. **先读** `docs/01-架构重构方案.md`，再读这份。
2. **别抄 Alice 的代码**，只学思路。AGPL 会传染，我们是 MIT。
3. 改前端前先看 `apps/web/AGENTS.md` —— 这版 Next.js 有破坏性变更，
   本地 `node_modules/next/dist/docs/` 里有正确的文档。
4. 用户的工作偏好：**先分析再说结论、讲证据、能用就别乱动**。
   如果他的前提有误（比如「OpenAlice 没部署到 Vercel」），
   拿证据纠正他，别顺着说。
5. `.env` 已经在 `.gitignore` 里且 `chmod 600`。**永远不要提交它。**
