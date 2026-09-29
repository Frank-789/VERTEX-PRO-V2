# VERTEX-PRO-V2 进度日志

> 这份文件的用途：**换一个对话窗口也不会失忆**。
> 任何人（或任何 AI）接手时，先读这里，再读 `docs/01-架构重构方案.md`。
> 规则：每完成一件事就更新这里，别攒着写。

**最后更新**：2026-09-29
**当前阶段**：**Phase 3 的定时任务已推上去 ✅** 远端 `main` = `0920e79`，
CI 三个 job 全绿（`actions/runs/36538512914`），含新增的「定时任务逻辑测试」step。

**本轮完成 —— Phase 3 第一项：`data/issues/<id>.md` 自调度** ✅ 纯后端、不依赖任何账号，
已**真机跑通**（详见第二节「定时任务」小节）。测试从 35 项涨到 **140 项**
（冒烟 59 + 定时任务 81）。文档、示例、配置参考一并补齐。

> 🔑 **推送那个「玄学」找到了真凶：不是 github.com 抽风，是沙箱。**
> 同一个环境里 `curl https://github.com/` 通（200，0.9 秒），
> 但 `git push` 死活 `Failed to connect to github.com port 443`（卡满 75 秒）。
> **curl 的流量被放行，git 的出站被拦** —— 所以一直看着像「网站间歇性抽风」。
> 关掉沙箱再推，**一次就过**。踩了整整两轮的坑，见第五节新增的两行。

下一步：① Vercel 部署前端（逐步清单在 `docs/02-部署指南.md` 第三节，
两条关键：Root Directory 设 `apps/web`、环境变量 `API_ORIGIN`）
→ ② 前端入件箱展示（后端 + API 已就绪）
→ ③ `apps/api/Dockerfile` + `docker-entrypoint.sh` 那两份改动还没提交，见下。

> **推送堵点已彻底解决**（见第七节）。用户新做了一个 **classic token**
> （勾了 `repo` + `workflow`），实测 scopes 齐全、写探针 **201**，一次推成功。
> **之前「缺 workflow 作用域」的判断是错的** —— 真根因是旧 token 只读。

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
- [x] 写 `.gitignore`（重点：`.env`、`data/*`、`prompts/user/`）
- [x] 把方案文档推成了 V2 仓库的第一个 commit
- [x] `README.md` —— **2026-09-27 已完全重写**，见下面「GitHub 呈现」小节。
      （初版是纯文字表格、无图；现在是 OpenAlice 那种「功能小节 + 并排截图 + 一句说明」）

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
  - `MessageItem` 用户发言右对齐浅色气泡 / 助手回复直接铺在画布上（**已重排，见下节**）
  - `ToolCallCard` 默认折叠，展开看原始返回
  - `StickerBubble` 无气泡底，最大 160px
  - `RichText` 先切表情再走 Markdown
  - `Composer` 自动增高、Enter 发送、Shift+Enter 换行、Esc 打断、中文输入法防误发
  - `ConversationTranscript` 只在用户本来就贴着底部时才自动滚动
- [x] 落地页 `page.tsx`（一个输入框 + 4 张示例卡；**已按新规格重排，见下节**）
- [x] 对话页 `chat/page.tsx`（`?q=` 自动发送一次）
- [x] `next.config.ts` 同源代理 `/api/v1/*` → 后端，**彻底消灭 CORS**，
      也顺带保证 `NEXT_PUBLIC_*` 密钥泄露的事不会再发生
- [x] 开发服务器起得来，落地页和对话页都截图确认过渲染正常

### 对话界面按对方规格重排（本轮新增）

用户的要求是「chat 部分 1:1 照搬他的」。**做法上有一条线不能越**：
版式尺寸、交互行为、语义令牌架构属于**设计规格**，可以对齐；
具体十六进制色值和源码属于对方（AGPL），保持 MIT 就不能搬。
所以下面每一条都是「照规格重写」，不是复制粘贴。

- [x] `MessageItem` —— **推翻了原来的「不做气泡」决定**。改成：
  - 用户发言：右对齐、`--secondary` 底、20px 圆角、`max-w-[min(88%,42rem)]`、`px-4 py-3`
  - 助手回复：直接铺在画布上，**无气泡无描边**，占满阅读宽度
  - 这个不对称是刻意的：用户的话是「一句话」，助手的话是「一份东西」。
    两边都套气泡，长回答会被挤成窄条
  - 用户输入**不做 Markdown 渲染** —— 他打 `**粗体**` 就该原样看到星号
- [x] 阅读宽度 736px 居中：`px-[max(24px,calc((100%-736px)/2))]`（正文和输入框共用同一套）
- [x] 消息间距 32px（`gap-8`）
- [x] `ToolCallCard` —— 从「嵌套卡片」改成**内嵌轨道**：
  `border-l + margin-left:8px + padding-left:17px`。工具步骤缩进在回答里，
  读起来是「过程中的一步」而不是「一个独立的东西」
- [x] 工具成功态**不用绿色**。绿在这个产品里表示「盈利 / 安全」，
  用绿勾会让「跑了个工具」看起来像「赚到钱了」
- [x] `Composer` —— 26px 大圆角外壳，**不描边**，用一圈极淡的多层阴影当边界。
  描边会让它像个表单，阴影才像个「可以往里放东西的托盘」。
  聚焦反馈由外壳承担（`focus-within` 加深阴影），textarea 自身去掉 outline。
  范围 68px ~ 168px，超出内部滚动。发送键 32px 圆形实心前景色
- [x] `StickerBubble` 104px → **160px**（`maxHeight: 320`，宽高 auto）
- [x] `ConversationTranscript` —— 自动滚动阈值 72px + 「回到最新」浮标
- [x] **删掉了打字光标**（`.caret` + `caret-pulse` 关键帧）。
  对方表达「正在生成」靠的是**过程文字与结论文字的深浅对比**，不是闪光标
- [x] `isProgressText()` —— 一条回复里后面还有文字的段落，颜色退到
      `color-mix(foreground 88%, muted-foreground)`，让最终结论跳出来
- [x] 删掉两个死令牌：`--sticker-bg`、`--shadow-color`（四个色板和 `@theme` 里都清了）
- [x] 对话页错误框改成 `rounded-[10px]` + 半透明红描边 + `<strong>没能继续</strong>` 抬头
- [x] 截图逐项确认过：气泡版式、表格、编号列表、表情包（240×240 SVG 正常渲染并被 160px 上限收住）、
      「回到最新」浮标、输入框阴影

### 色板切换器 + 首页对齐（本轮新增）

上一轮四个色板只有机制、没有入口 —— 想换色得开控制台敲
`document.documentElement.setAttribute(...)`。这轮把入口补上了。

- [x] `lib/palette.ts` —— 色板注册表（纸白 / 亚麻 / 石墨 / 午夜 / 跟随系统）。
      **色板的定义在 CSS 里，这里只登记有哪些、怎么切** —— 加色板要同时改两个文件
- [x] `components/PaletteMenu.tsx` —— 页眉里一个图标按钮 + 下拉，
      每项带一个「底色+主色」的小圆点（比只写名字好认）。选完即走，不弹面板
- [x] 选择存 `localStorage`，跨页面、跨刷新保持
- [x] **首帧不闪**：`layout.tsx` 的 `<head>` 里塞一段内联脚本，
      浏览器解析 HTML 时同步执行，早于绘制也早于 React。
      实测：重载后连采 25 帧，**从第一帧（t=28ms）就是石墨色，没有一帧纸白**
- [x] 首页 `page.tsx` 按新规格重排 —— 提问框与对话页输入框**同源**
      （共用新增的 `lib/surface.ts`：26px 圆角、四层阴影、68/168px 高度上限）。
      从首页走到对话页，光标不该有落差
- [x] 抽出 `lib/surface.ts` / `components/InlineScript.tsx`；阅读宽度也收进常量，
      对话区、输入框、错误框三处共用同一套 padding，左边缘严格对齐
- [x] 两个输入框补 `name`，消掉 a11y 告警
- [x] 验证：`tsc --noEmit` 干净、`next build` 通过（**两个路由仍是静态预渲染** ——
      内联脚本没有破坏静态化，这点和「在 layout 里读 cookie」的方案不同）、
      冒烟测试 21 项仍全过、深浅两套色板各截图确认

### 事件日志（Phase 2 第一项，本轮新增）

方案文档第 349 行早就点名了 `core/event_log.py`，这轮把它建起来了。

- [x] `core/event_log.py` —— 按天落盘 `data/event-log/<日期>.jsonl`，
      记录 `turn.start` / `tool.call` / `turn.end` / `error`，用 `turn` id 串起一轮
- [x] **和 `sessions/` 的分工**（这是关键）：
      `sessions/` 是「对话」，会被回灌给模型，里面**只有自然语言**；
      `event-log/` 是「运行过程」，模型永远看不到，工具**完整输出**只在这里。
      把工具原始 JSON 塞进会话历史既白烧上下文又污染下一轮对话
- [x] 三条设计取舍：每条记录都带 `session`（省得先查 `turn.start`）；
      用户发问只存前 500 字 `preview`（全文在 `sessions/` 里已有）；
      结果上限 64KB，超出截断并标 `truncated`（无界会被一个返回 50MB 的工具写满磁盘）
- [x] 写失败**绝不抛异常**，但打 `warning` —— 日志是旁路，不能因为它挂掉整轮对话
- [x] `EVENT_LOG=0` 可整体关闭（在意用户内容落盘的部署用得上）
- [x] `prune()` 保留 30 天，启动时清一次
- [x] 验证：冒烟测试 21 → **35 项**（新增 14 项：日志生成 / 三笔记录同一 turn /
      完整结果未截断 / 工具输出没漏进会话文件 / 超长截断打标 / 清理过期且不误删当天 /
      开关关掉后完全静默 等）；另跑了一轮**真实 HTTP 请求**确认端到端

### 定时任务：`data/issues/<id>.md` 自调度（Phase 3 第一项，本轮新增）

学的是 Alice 的「**用文件替代事件总线**」：**没有中央任务库，没有调度定义表**。
一个 Markdown 文件就是一个任务，带上 `when:` 就是定时任务，去掉就是一张看板卡片。
进程重启任务不丢 —— 因为真相在文件里，不在内存里。

```markdown
---
title: 每日利润测算
when: { kind: cron, cron: "0 9 * * *", timezone: "Asia/Shanghai" }
---

帮我算一下成本 45、售价 129、拼多多平台的利润，并说明保本售价。
```

六个新文件，每个只干一件事：

- [x] `core/cron.py` —— **纯函数、零依赖**的 cron 解析（5 字段 + `*` / `,` / `-` / `/`）。
      单独拆出来是因为它最容易出错，拆开后能脱离调度器单独测
- [x] `core/issues.py` —— frontmatter 解析 / 扫描 / 状态 / 判到点
- [x] `core/inbox.py` —— 报告投递到 `data/inbox/`，文件名即索引
- [x] `core/runner.py` —— **无头执行**，复用 `agent.run_turn`，和聊天走同一条循环
- [x] `core/scheduler.py` —— 进程内的后台循环；`tick_once()` 单独可调、可断言
- [x] `api/issues.py` —— 四个薄路由，不含业务逻辑

#### 四条设计决定（它们决定了代码长什么样）

**① 状态另存 `.state.json`，不写回 `.md`**（这点和 Alice 不同，是刻意的）

Alice 把 `lastRun` 写回任务文件。我们不这么做，因为那意味着 runner 每次都要
改写用户正在编辑的文件：① 和编辑器打架；② 文件若纳入 git 会一路噪音；
③ **写到一半被杀，任务定义就坏了** —— 拿状态换定义，不划算。
所以状态存 `data/issues/.state.json`（临时文件 + `os.replace` 原子替换），
`.md` 保持纯声明、归人所有。

**② 判据是「上次跑之后有没有命中过」，不是「当前这一分钟是否命中」**

后者依赖调度器恰好在那分钟醒着 —— 进程重启、tick 延迟、机器休眠都会让那一分钟
被跳过，任务就**静默漏跑**了。前者从 `lastRun` 往后推，只要那一刻已经过去就算欠着，
**天然抗重启**。这是整个设计里最要紧的一条。

**③ 欠了多班只补跑一班（合并），且补的是最早那次**

一个每分钟的任务停机一天要补 1440 次，显然是错的 —— 监控类任务只关心「现在」。
补跑之后 `lastRun` 置为当前时刻，下一班从此刻重新起算。
**返回最早那次而不是最近那次是刻意的**：停机三天后补跑，若返回最近那次，
报告上的 `lagSeconds` 只有几秒，「停机三天」这个信息就彻底丢了。
真机实测那次打出 `lagSeconds: 92568`（≈25.7 小时），正好对上前一天 09:00 的排期。

**④ 状态先于执行落盘（persist-before-execute）**

`_execute` 先写 `lastRun` 再开跑，顺序反过来的话，跑到一半被杀、重启后
`lastRun` 还停在上一轮，这条任务会立刻再跑一次 —— **崩溃即死循环**。
代价是崩溃那次算「跑过了」，漏一班；**宁可漏，不可循环**。

#### 其他细节

- [x] 坏掉的规则**不抛异常**，返回一个带 `error` 的 `When`，前端照样列出来并显示原因 ——
      一个文件写错不该让整个扫描挂掉、也不该让服务起不来（和 `config.py` 同原则）
- [x] 没有 frontmatter 的 `.md` 直接跳过（`data/issues/` 下可能被随手放笔记进去，
      不该刷一屏警告）；单个文件读不动只影响它自己
- [x] 任务 id 在**读入口和写入口都**卡 `^[A-Za-z0-9_-]{1,64}$`。
      只卡读入口是不够的 —— 一个带 `../` 的 id 在**写入时**就已经把文件放到目录外面去了
- [x] 报告文件名精确到秒，**撞了就加 `-2` / `-3` 后缀，绝不覆盖**。
      这个是真机跑的时候暴露的：手动触发的那份把定时那天的同名报告悄悄盖掉了
- [x] `runs` 计数：开跑前的「占坑」写入传 `count=False`，否则一处跑一次显示成两次
- [x] `MAX_PER_TICK`（默认 5）—— 机器睡一夜醒来别让二十个任务同时开跑打满供应商配额；
      没跑到的下轮继续，状态是「欠着」不会丢
- [x] `ISSUE_SCHEDULER=0` 可整体关掉（测试环境就是靠它，否则后台循环会干扰断言）
- [x] **`tick_once` 与后台循环分开** —— 测试直接调它，不用和后台时序搏斗；
      真出问题时也是先手动调它定位

#### 真机验证（不是只有单测）

起服务看到 `调度器启动：每 30 秒扫一次 data/issues/`；一条逾期任务在**第一个 tick**
就被捞起来跑完，`scheduledAt` 是昨天 09:00、`lagSeconds` 92568、`nextRun` 是明天 09:00；
**第二个 tick 没有重复执行**；四个 API 端点返回值都对着。
（`data/inbox/2026-09-28T024248-demo-price-watch.md` 就是那次的报告。）

> ⚠️ 现存 `data/issues/.state.json` 里 `runs: 2` —— 那是**修复前**的旧服务写的。
> `count=False` 的修复已有单测覆盖，但**没有**再清空状态重跑一遍验证
> （清状态会连带删掉 `data/inbox/` 的内容，用户否掉了这个操作）。
> 下次自然跑一班后，若 `runs` 变成 3 就说明修复没生效，若还是 2 就对了。

#### 测试

- [x] `tests/test_issues.py` —— **81 项**，全是纯逻辑，跑在临时 `DATA_HOME` 里，
      **不碰真实 `data/`**，不需要任何 key、不需要网络。覆盖：
      cron 解析（合法 + 7 种错误写法）、命中判断、`next_after`（含闰日 `0 0 29 2 *`、
      夏令时边界、跨周）、frontmatter（9 种畸形）、判到点（含合并语义、
      8 天停机后 `lagSeconds > 6*86400`）、状态存取往返 + 原子性、
      **读写两侧的路径穿越**、报告排序 / 截断 / 重名
- [x] `test_smoke.py` 加第 7 节端到端：写一条 `* * * * *` 的任务、把 mtime 往前挪 5 分钟、
      `Scheduler().tick_once()` → 断言跑成功 + 用到了 `profit.calc` + 报告落盘 +
      状态已持久化 + **第二个 tick 是空操作** + 6 个端点 + 400/404/409 + `/health`
- [x] 合计 **140 项**（59 + 81），CI 里已是两个 step 分别跑

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

### GitHub 呈现（2026-09-27）

- [x] `README.md` 按 OpenAlice 的排布重写：居中 logo → 标题 + 一句话 → 徽章 →
      大截图 → 快速开始 → 功能（### 小节各配图）→ 架构 → 部署 → 文档 → 路线图 → 许可证
- [x] `docs/images/` 五张实拍截图 + 一个 logo（都是本地跑起来真截的，不是效果图）
      —— `hero-chat` / `chat-answer` / `chat-dark` / `landing` / `stickers` / `logo-wave`
- [x] 仓库 topics（12 个）+ description 精简到一行 + homepage
- [x] `CHANGELOG.md`、`CONTRIBUTING.md`、`.gitattributes`
- [x] `docs/` 从 1 篇补到 3 篇（加 `02-部署指南.md`、`03-配置参考.md`）
- [x] `.github/workflows/ci.yml` —— 三个 job：后端冒烟测试 / 前端构建 / **密钥扫描**
  - ⚠️ **写了但还没推上去**：推送 `.github/workflows/` 下的文件要求 token 具备
    **`workflow` 作用域**，当前 token 只有 `repo`。GitHub 会直接拒绝：
    `refusing to allow a Personal Access Token to create or update workflow ... without workflow scope`
  - Contents API 那条路也走不通（GitHub 返回 404 防探测，不是 403）
  - **解法**：去 https://github.com/settings/tokens 给 token 勾上 `workflow`，然后重推

### 后端容器化（2026-09-27）

- [x] `apps/api/Dockerfile` —— 多阶段构建，tini 作 PID 1、非 root（UID 10001）、
      `HEALTHCHECK` 用 python 探活（省掉装 curl）、`/data` 卷、`ALLOW_DEV_CORS=0`
- [x] `docker-compose.yml` —— 端口只绑 `127.0.0.1:8000`（后端无鉴权，不该裸暴露）、
      `restart: unless-stopped`、`stop_grace_period: 30s`、日志轮转 10m×3
- [x] `.dockerignore` —— 密钥 / 依赖 / 构建产物 / `data/` / 文档一律不进镜像
- [x] 路径逻辑已在**模拟的容器目录结构**下验证：
      `/app/apps/api/src/core/paths.py` → `parents[4]` = `/app`，不越界

> ⚠️ **镜像尚未实际构建过** —— 开发机上没有 Docker。
> 首次构建若失败，优先查 `requirements.txt` 在 `python:3.11-slim` 上的兼容性。
>
> ⚠️ **目录层级不能改**：`paths.py` 靠 `parents[4]` 推仓库根，
> 把 `apps/api/src/` 打平会让所有路径解析**静默失败**。Dockerfile 里有注释标了这一点。

---

## 三、还没做的

### Phase 0 止血（**最高优先级**）

> ⚠️ **下面全部是「第一代 `VERTEX-pro`」的遗留问题，不是 V2 的。**
> V2 从第一天就没犯这些错 —— 无 `NEXT_PUBLIC_*`、无硬编码路径、无伪造数据。
> 但**只要 V1 还在线上、旧 git 历史还在 GitHub 上，风险就还在**。

**密钥轮换（只能你本人去各家控制台操作）：**

- [ ] DeepSeek key（`sk-1b1de9af...`）—— **曾提交在公开仓库的 `.env.example`**，被爬虫收录过，最紧急
- [ ] Apify token —— 只在本机 `.env`，但保险起见也换掉（**不在文档里写片段**）
- [ ] GitHub PAT —— 见第七节。桌面那两个文件里一共 **5 个 token，全部已废**：
      `Github终端更新指令.txt` 里 3 个（两个 `ghp_` 已 401、一个 `github_pat_` 是只读），
      `部署流程.txt` 里 2 个（均 401）。全部明文存桌面、且已在对话里出现过。
      **建议重建后改存 keychain，并把文件里的删干净**

**代码与历史清理：**

- [ ] 用 `git filter-repo` 从 `VERTEX-pro` 历史里抹掉那张 key（**只改文件没用，历史还在**）
- [ ] V1 前端的三个 `NEXT_PUBLIC_*` 密钥（会打包进浏览器，人人可见）
- [ ] V1 的 `render.yaml`（`repo:` 还是占位符，且没声明爬虫环境变量）
- [ ] V1 的 Dockerfile 缺 `playwright install chromium`（容器里没浏览器，采集工具全废）

> 📌 注意：**V2 的 Dockerfile 不需要 playwright** —— V2 的三个工具
> （`profit.calc` / `ebay.search` / `apify.scrape`）都不依赖浏览器。
> 上面这条是第一代的问题，别照搬过来。

### Phase 2 持久化

- [x] 事件日志落盘 `data/event-log/`（JSONL）—— **本轮完成**
- [ ] Postgres 存领域数据（商品、利润测算记录）—— **建议推迟到 Phase 3**，
      理由见下面「关于 Postgres 的判断」

#### 关于 Postgres 的判断（2026-09-28，建议推迟）

方案文档第 535 行自己写了风险和对策：
> 「Postgres 引入成本 —— 目前零数据库，一步到位有迁移量。
>   先 JSONL 满足会话/事件/Issue，Postgres 只承载需要查询的领域表」

那**现在有需要查询的领域表吗？没有**：

- `profit.calc` 是**纯函数**，算完就返回，什么都不存
- `ebay.search` / `apify.scrape` 只是抓了数据回灌给模型，也不落库
- 商家 / 商品 / 采集任务 这三张表要等 **Phase 3 自动化**（爬虫凭证到位）才有数据

现在建表 = 给一个**没人写入的模型**设计 schema，等真做 Phase 3 时大概率要推翻重来。
而且还有实打实的代价：

1. **部署复杂度上一个台阶** —— 现在 `docker compose up` 就完事，
   加了 Postgres 就多一个有状态依赖，`docker-compose.yml` 里目前连 db 服务都没有
2. **本地开发门槛变高** —— 现在 clone 下来 `npm install` + 一个 venv 就能跑，
   mock_provider 甚至不需要任何 key
3. **要处理连不上时的降级** —— 否则数据库一挂整个应用起不来

**结论**：先把 JSONL 这层做扎实（已完成），等 Phase 3 真的开始写
商品和采集任务时，再按那时候的真实查询需求建表。届时同步加
`docker-compose` 的 db 服务和一个最小迁移脚本。

> 如果希望**现在**就要数据库，那也合理 —— 但请明确说，
> 我会顺带把「没有 DATABASE_URL 时优雅降级到 JSONL」这条路径一起做掉，
> 否则本地开发和 CI 都会被迫依赖一个数据库。

### Phase 3 自动化

- [x] `data/issues/<id>.md` + `when:` frontmatter 自调度 —— **本轮完成**，
      见第二节「定时任务」。后端 + API 全通，真机验证过
- [ ] **前端入件箱展示** —— 后端和 API 都有了（`GET /api/v1/inbox`），
      界面上还没有入口。`data/inbox/` 里的报告现在只能 `ls` 或 `curl` 看
- [ ] `examples/issues/` 示例任务 —— `data/` 在 `.gitignore` 里，
      所以现在**仓库里一个示例都没有**，clone 下来的人不知道格式长什么样。
      应该在仓库里放几个只读示例（`examples/issues/*.md`），
      文档指向它，而不是让人去看被忽略的 `data/`
- [ ] `docs/04-定时任务.md` —— 格式、`when:` 语义、合并、为什么状态是旁挂的、
      怎么查件箱。`.env.example` 也还差 `ISSUE_SCHEDULER` /
      `ISSUE_TICK_SECONDS` / `ISSUE_DEFAULT_TZ` / `ISSUE_MAX_PER_TICK` 四个开关
- [ ] 让「店铺管家」（Store Pilot）从演示壳变成真能跑
      —— **卡在爬虫凭证**。方案文档第 546 行自己记了这条依赖：
      没有可用的采集凭证，价格监控 / 差评监控 / 库存预警都只能是空转。
      调度这层（上面那个刚做完）已经是它们的全部前置了

### Phase 4 剩下的

> 「GitHub 呈现」与「后端容器化」**已完成**，见「二、已经做完的」里对应的两个小节。

- [ ] **Vercel 部署前端** —— 逐步清单在 `docs/02-部署指南.md` 第三节
      （关键两条：**Root Directory 设 `apps/web`**、环境变量 `API_ORIGIN` = 后端公网地址）。
      ⚠️ **新增了一条约束**：调度器是常驻后台循环，**后端必须跑在
      「起来就不停」的进程里**（容器 / VPS）。放到 Serverless 上会随实例回收而停摆 ——
      任务不会丢（真相在 `data/issues/` 的文件里），但**不会按点跑**。
      详见 `docs/02-部署指南.md` 里那张「运行时需求 vs Serverless 现实」的表
- [ ] GitHub Releases 打包桌面版
- [ ] 后端鉴权（目前无鉴权，所以端口只绑回环）。
      **调度器上来之后这条更值钱了** —— 现在 `POST /api/v1/issues/{id}/run`
      能触发一次真实执行，端口一旦对公网开就是「谁都能花你的额度」

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

**换外观**：页面右上角有个配色菜单（纸白 / 亚麻 / 石墨 / 午夜 / 跟随系统），
选完存在 `localStorage`。要脚本化切换才用：
`document.documentElement.setAttribute('data-palette','graphite')`

**试定时任务**：往 `data/issues/` 丢一个 `.md`（格式见上），后端起来后
**30 秒内**会被扫到。手动立刻跑一次、不用等排期：

```bash
curl -X POST localhost:8000/api/v1/issues/<id>/run    # 409 = 上一次还在跑
curl -s localhost:8000/api/v1/issues | python3 -m json.tool
ls data/inbox/                                        # 报告就在这儿
```

写坏了不要紧：规则写错**不会**让服务起不来，那条任务会带着 `error` 字段
出现在 `GET /api/v1/issues` 里，原因写得很直白。

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
| 表情包渲染不出来 | `StickerBubble` 用了 `width/height=160` 的定值，但 SVG 是 240×240 | 属性给 160（占位防抖），`style` 里放 `width/height:auto` + `maxWidth/maxHeight` 限幅 |
| 顺手改小表情尺寸，改完没生效 | 四个色板上方的 `@theme inline` 里还留着指向已删变量的映射行 | 删变量时**连映射一起删**，否则指向 undefined（`sed` 批量替换特别容易漏） |
| 沙箱里 `git push` 卡死 75 秒 | **github.com:443 是间歇性被拦**，不是稳定被墙。`api.github.com` 和 `raw.githubusercontent.com` 始终通 | **先 `curl https://github.com/` 探一下**再下结论。见第七节 |
| 以为「推不上去」只有一个原因 | 实际是**两个独立问题叠加**：网络间歇 + 本机无凭证。只解决一个仍然推不动 | 分开验证：先测连通性，再测凭证（`curl -H "Authorization: Bearer $TOK" api.github.com/user`） |
| 翻遍桌面也找不到可用 token | 能用的那个在 `Github终端更新指令.txt`，不在 `部署流程.txt`（后者那个已失效） | 找凭证时**两个文件都要翻** |
| `.github/workflows/` 推不上去 | token 只有 `repo` 作用域，推送 workflow 文件需要额外的 **`workflow` 作用域** | 去 token 设置勾上 `workflow`。**Contents API 绕不过去**（GitHub 返回 404 防探测） |
| 想验证 Docker 镜像但本机没 Docker | 开发机上没装 Docker | 退而求其次：**用模拟的目录结构验证 `paths.py` 的层级推算**（已是这么做的）。但版本兼容性必须在真镜像里才能验 |
| **开发模式下色板属性被清掉** | React Strict Mode 会重新挂载一次组件，并把 `<html>`/`<head>`/`<body>` 的属性**重置为 JSX 里声明过的那些**，内联脚本打上的 `data-palette` 就此消失 | 在持有该状态的组件里用 `useLayoutEffect` 再补一次（生产环境是 no-op）。见 `PaletteMenu.tsx` |
| React 警告「渲染出了 `<script>` 标签」 | 内联脚本的 `type` 在服务端和客户端必须不同 | 服务端 `text/javascript`（浏览器同步执行），客户端 `text/plain`（浏览器忽略）+ `suppressHydrationWarning`。已封装成 `InlineScript.tsx` |
| 色板闪一下才变 | 只靠 JS 读 localStorage 后再设属性，太晚 | 内联脚本放进 `<head>`，解析期同步执行。**别改成在 layout 里读 cookie** —— 那会让整站掉出静态预渲染 |
| fine-grained token 死活推不上去 | 建 token 时 **Repository permissions → Contents** 默认是 `Read`，需要手动改成 `Read and write`。响应头 `x-accepted-github-permissions` 会直接点名缺哪个权限 | 读操作正常（200）但写操作 403，就是这个原因。**光看「token 有效」不够，要分别测读和写** |
| dry-run 说能推，真推却被拒 | `git push --dry-run` 只做引用协商，**不传对象，因此不触发 workflow 作用域校验** | 判断能不能推 workflow 文件，必须真推一次，别信 dry-run |
| fine-grained token「勾了权限还是不行」 | 建 token 时 `Repository access` 选了 **`Public Repositories (read-only)`** —— 这个选项会把整个权限面板**锁死成只读、灰掉勾不动**。表现：读公开仓库正常（200），一写就 403。而且**这个页面上根本没有 `workflow` 勾选框**，那是经典 token 才有的 | 重建时选 **`Only select repositories`** 并勾上目标仓库，权限面板才解锁。要推 workflow 文件需**同时**给 `Contents: Read and write` 和 `Workflows: Read and write` |
| 翻遍桌面找不到可用 token | `Github终端更新指令.txt` 里其实有 **3 个不同 token**，而 `grep 'ghp_'` 只捞到**已经失效的那两个经典 token**，恰好漏掉唯一活着的 fine-grained 那个 | 找凭证要**匹配两种前缀**：`ghp_`（经典）+ `github_pat_`（fine-grained）；而且必须**逐个实测**，文件里有 token ≠ token 能用 |
| 死盯一个旧报错反复诊断 | `workflow scope` 那条报错是 9-27 的状态。之后 token 换过，**报错早就不是那个了**（变成了 401 / 403） | 重新动手前**先重新实测一遍当前状态**，别拿几天前的报错当现状 |
| 数错了「领先几个提交」 | 本地的 `origin/main` 引用是**旧的**（停在 `6e8a364`），实际远端早到了 `b46f480`。`git rev-list origin/main..HEAD` 数出来 5 个，真实只差 4 个 | **下结论前先 `git fetch`**。本地的 `origin/*` 只是个缓存，不代表远端现状 |
| 以为「token 能登录」=「token 能用」 | 登录只走读接口。GitHub 的权限是**读写分开**判的，读 200 完全不代表写能过 | 建完 token **先打一发写探针**（`POST /git/blobs`）再推。这次就是靠它确认 201 才敢推 |
| `CronSpec() got an unexpected keyword argument '分钟'` | `_FIELDS` 把**属性名**和**中文显示名**混在一个元组里，解包时中文名被当关键字参数传进了构造函数 | 存成 `(属性名, 显示名, 下限, 上限)` 四元组，解包时 `for raw, (attr, label, lo, hi) in zip(...)`。**给报错信息用的名字和给代码用的名字要分开** |
| cron 写「每月 1 号**且**每周一」结果命中一堆 | 标准 cron 就是这么定的：**日 和 星期 同时被限制时取 OR**，不是 AND。`0 0 1 * 1` = 「每月 1 号或每周一」 | 这是最容易被误解的 cron 语义。解析 `*` 时返回 `None`（表示「未限制」），判日时才能正确区分「`*`」和「写满了」 |
| 报告文件被悄悄覆盖 | 文件名时间戳只精确到秒，同一秒内的两次运行（定时 + 手动触发）算出同一个名字。**真机跑的时候才暴露**，单测里两条任务跑不到同一秒 | 写入前 `while path.exists()` 加 `-2` / `-3` 后缀。**凡是拿时间戳当唯一键，都要问一句「同一秒撞了怎么办」** |
| 一条任务跑一次，`runs` 显示 2 | `_execute` 调了两次 `mark_run`：开跑前占坑一次、跑完记一次。占坑那次不是「跑过的运行」 | `mark_run` 加 `count=False`，占坑调用传进去。**计数器要问「哪一次才算数」** |
| 测试说「欠的应该是最近的排期」判 FAILED | **代码是对的，我的测试写错了**。返回最早那次，`lagSeconds` 才留得住「停机三天」这个信息；返回最近那次数字只有几秒，排障时等于没有 | 改测试而不是改代码，并把语义写进 docstring。**代码和测试打架时，先想清楚哪个语义才对，别默认代码错** |
| 带 `../` 的任务 id 能跑到目录外 | 只在**读**入口卡了 id 白名单，`inbox.write` 那条**写**入口没卡 —— 一个 `../evil` 在写入时就已经把文件放到 `data/inbox/` 外面去了 | 读入口和写入口**都要校验**。同一条 id 经过几条路径，就有几处要卡（已补测试：`"x"*100` 和 `"../evil"`） |
| `PyYAML` / `tzdata` 一直是「能用」的 | 那是蹭 `uvicorn[standard]` 的**传递依赖** —— 巧合，不是契约。上游哪天换个依赖树就炸。`python:3.11-slim` 里也**不保证**有 `/usr/share/zoneinfo`，缺了直接 `ZoneInfoNotFoundError` | 直接 import 的包就写进 `requirements.txt`，并注明**为什么**需要它。**「能跑」不等于「声明过」** |
| 改测试文件时把别的测试弄挂了 | 我把新增的 `count=False` 测试块**插在了状态往返断言前面**，`lastStatus` 被改成 `"running"`，导致「状态存取往返一致」失败 | 新测试块要有自己的独立状态对象，别复用别人正在断言的那个 |
| **`git push` 卡满 75 秒报连不上 github.com** | **是沙箱，不是网络。** 同一个环境里 `curl https://github.com/` 秒回 200（0.9 秒、DNS 正常、无代理），但 git 的出站被沙箱拦着 —— **curl 放行、git 不放**，所以现象看起来就是「github.com 间歇性抽风」 | **别去重试，直接去掉沙箱跑**。2026-09-29 实测：关掉沙箱一次就过。这一条推翻了第七节原来的判断 |
| 拿 curl 的结果推断 git 能不能用 | 两者走的出站通道在沙箱里**待遇不同**。`curl 200` 完全不能说明 `git push` 能过 —— 这次就是这么被误导的 | 判断 git 的网络能力，**要么直接推一次**，要么用同样的通道测。别拿另一个工具的连通性当证据 |

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
6. 本仓库**每次提交前扫一遍密钥**。`.github/workflows/ci.yml` 里有自动化的
   密钥扫描 job（推上去之后生效）。
7. **他自己的教程未必是最优解，照做之前先看一眼。** 例：`部署流程.txt` 教的是
   `git remote set-url origin https://TOKEN@...` 推完再改回来 —— 这会把 token
   写进 `.git/config`。改成 **一次性 URL**（`git push https://TOKEN@host/repo.git main`）
   效果一样但不在任何地方落盘。用户接受这类改进，**说明理由即可**。
8. **截图要真跑真截**，不要拿效果图充数。这轮的 5 张图是起了
   mock_provider + FastAPI + Next.js 完整链路、让 Agent 真跑完一轮工具调用后截的。
9. **`git push` 要关掉沙箱跑**（2026-09-29 确认）。在这个环境里沙箱放行
   `curl`、拦截 `git` 的出站，所以会看到「curl 通、git 卡 75 秒」这种
   自相矛盾的现象。**别重试、别改配置、别怀疑网络 —— 直接去掉沙箱。**
   第七节原来那条「github.com 间歇性抽风」的判断已被这条推翻。

### 本轮已提交的内容（4 个提交，已推）

| 提交 | 内容 |
|---|---|
| `08aec91` | `feat(api)` —— 定时任务：6 个新文件（cron / issues / inbox / runner / scheduler / 路由）+ `main.py` 接线 + `requirements.txt` |
| `0db5264` | `test(api)` —— 81 项逻辑测试 + 冒烟测试第 7 节端到端 + CI 加第二个 step |
| `e1041c4` | `docs` —— `docs/04-定时任务.md`、`docs/03` 补两处、`examples/issues/`、`.env.example`、README |
| `0920e79` | `docs` —— CHANGELOG + PROGRESS |

提交前扫过增量：`ghp_` / `github_pat_` / `sk-` / `apify_api_` / 私钥 /
`api_key=` 赋值 —— 全空。

### ⚠️ 还躺在工作区、**别的会话留下的**两个文件（本轮没碰）

| 状态 | 文件 | 它是干什么的 |
|---|---|---|
| 改动 | `apps/api/Dockerfile` | 加了 `PORT` 环境变量支持（Render 会注入），HEALTHCHECK 跟着走，`CMD` 改成调启动脚本 |
| 未跟踪 | `apps/api/docker-entrypoint.sh` | 容器里同时起 mock 供应商 + uvicorn，让 demo 零成本可跑。**开关就是 `MOCK_API_KEY`** —— 和 `provider_router.py` 判断 mock 可用性的条件保持一致，否则会「路由以为能用的供应商其实没起」 |

看着是完整、自洽的一批（Render 部署 + 零成本 demo），**但不是我写的，我没验过**。
要提交的话建议单独一个 `feat(deploy)` 提交。

---

## 七、推送堵点 —— 已解决 ✅（2026-09-27）

**结论：`git push` 直接能用，之前那套 Git Data API 绕行方案已经不需要了。**

```bash
git push https://<token>@github.com/Frank-789/VERTEX-PRO-V2.git main
```

用**一次性 URL** 而不是 `git remote set-url` —— 后者会把 token 写进 `.git/config`，
中途出错就留在磁盘上了。效果一样，但不在任何地方持久化。

### 当初卡住的真实原因（两个独立问题，缺一不可）

**① github.com:443 间歇性连不上**

```
curl https://github.com/      → 000（20 秒超时）
curl https://api.github.com/  → 200（0.5 秒）
```

注意这是**间歇性**的：会话早期通、后来断、2026-09-27 又通了。
不是配置问题，是环境级的网络抖动。**`api.github.com` 和 `raw.githubusercontent.com`
始终可用**，所以当年才用 Git Data API 绕行。

> 🔴 **2026-09-29 更正：上面这条判断是错的（至少不完整）。**
> 同一天实测：`curl https://github.com/` **秒回 200**（0.9 秒），
> 而 `git push` 依然卡满 75 秒报 `Failed to connect to github.com port 443`。
> 关掉沙箱再推，**一次就过**。
>
> 也就是说 **curl 和 git 在这个环境里的出站待遇不一样** ——
> 沙箱放行 curl、拦截 git。当年看到的「间歇性」很可能是同一回事的两种表现，
> 而不是 GitHub 真的在抽风。
> **下次遇到「推不上去」，先怀疑沙箱，别先怀疑网络。**

**② 本机没有任何可用凭证**

| 检查 | 结果 |
|---|---|
| `~/Desktop/部署流程.txt` 里的 PAT（`ghp_7Fey…`） | 401 已失效 |
| `~/Desktop/Github终端更新指令.txt` 里的 fine-grained PAT | 401 已失效 |
| `~/Desktop/Github终端更新指令.txt` 里的 `ghp_42FT…` | ✅ **有效**（`repo` 全权限，admin/push） |
| keychain / `gh` CLI / SSH key / `~/.netrc` | 全都没有 |

**第一个能用的 token 藏在 `~/Desktop/Github终端更新指令.txt` 里** ——
之前只看 `部署流程.txt` 所以漏了。下次找不到凭证时，两个文件都要翻。

### ⚠️ 遗留的安全隐患（下次务必处理）

1. `~/Desktop/Github终端更新指令.txt` 和 `部署流程.txt` 里的 token 都是**明文**存桌面，
   且这两个 token 已经在本对话里出现过。**建议轮换并从文件里删掉。**
2. 以后统一走 `git push` + 一次性 URL，**别再建议 Git Data API 绕行** ——
   除非确认 github.com 又断了。
3. `api.github.com` 匿名限流只有 60 次/小时，批量拉数据时容易撞到，
   带上 token 可提到 5000。

### ✅ 已解决：全部推送成功（2026-09-28）

```
b46f480..36ac7ad  main -> main
```

远端 `main` 现在指向 `36ac7ad`，`.github/workflows/ci.yml` 在远端返回 200。
**CI 第 1 次运行三个 job 全部 success**（`actions/runs/36370067493`）：

```
后端 · 冒烟测试    completed  success      ← 35 项，无需任何 API key
密钥扫描          completed  success      ← 密钥扫描 job 从此自动跑
前端 · 构建        completed  success
```

**注意实际只推了 4 个提交** —— 本地 `origin/main` 引用是**旧的**（停在 `6e8a364`），
`e870e94` 和 `b46f480` 其实早就在远端了。**别信本地的 `origin/*` 引用**，
下结论前先 `git fetch`。

| 提交 | 内容 | 推没推 |
|---|---|---|
| `e870e94` | 后端容器化（Dockerfile / compose / dockerignore） | 早就在远端 |
| `b46f480` | PROGRESS 整理（纯文档） | 早就在远端 |
| `aa3f7e2` | CI 工作流（`.github/workflows/ci.yml`） | ✅ 本次 |
| `6801124` | 色板切换器 + 首页重排 | ✅ 本次 |
| `6da4693` | 事件日志落盘（Phase 2 第一项） | ✅ 本次 |
| `36ac7ad` | PROGRESS 纠错 | ✅ 本次 |

推之前扫过这批提交的增量：`ghp_` / `github_pat_` / `sk-` / `apify_api_` /
私钥 / `api_key=` 赋值 —— **全空，没有密钥字面量**。扫完再推，别省这一步。

### 真正的堵点：不是 workflow，是「只读」（2026-09-28 实测）

之前一直以为是缺 `workflow` 作用域。**错了。** 今天把每个 token 都重测了一遍：

| Token（按存放位置 + 前缀标识） | 读 | 写 | 结论 |
|---|---|---|---|
| `Github终端更新指令.txt` · `ghp_7Fey…` | 401 | — | 已失效 |
| `Github终端更新指令.txt` · `ghp_42FT…` | **401** | — | **已失效** —— 本文档 9-27 那版说它有效，那是当时的快照 |
| `部署流程.txt` · `github_pat_…b7oG` | 401 | — | 已失效 |
| `Github终端更新指令.txt` · `github_pat_…3Xxb` | **200** ✅ | **403** ❌ | **唯一活着的，但权限是只读** |

活着的那个写操作被拒，响应头直接点名：

```
x-accepted-github-permissions: contents=write
{"message": "Resource not accessible by personal access token"}
```

两个独立的误会凑在一起，才让人一直以为是 workflow 的问题：

1. **推送第一步是把对象写上去**，这步就被 `contents=write` 挡住了，
   **根本走不到检查 workflow 那一步**。看到的那条 workflow 报错是 9-27 的旧状态。
2. **fine-grained token 的设置页上没有 `workflow` 这个勾选框** —— 那是
   经典 token 才有的。fine-grained 要的是 `Contents` 和 `Workflows` 两个
   **独立权限项**，各设成 `Read and write`，少一个都不行。

**「改不了权限」也是有名有姓的**：建 fine-grained token 时
`Repository access` 如果选了 **`Public Repositories (read-only)`**，
整个权限面板会被**锁死成只读、灰掉勾不动**。现象完全对得上。

### 最后是怎么解决的

**A. 经典 token —— ✅ 走的就是这条，一次成功**

https://github.com/settings/tokens → `Generate new token (classic)` →
勾上 **`repo`** + **`workflow`** → 生成。

新 token 的实测结果（**光看「能登录」不够，要看到写探针返回 201**）：

```
GET  /user      → HTTP/2 200
x-oauth-scopes: admin:enterprise, ..., repo, ..., workflow, ...

POST /git/blobs → HTTP/2 201 Created     ← 这行才是关键
```

**B. fine-grained token（要选对仓库访问方式，否则权限锁死）—— 未走通，留作参考**

https://github.com/settings/tokens?type=beta → `Generate new token` →
`Repository access` 选 **`Only select repositories`** → 勾 `VERTEX-PRO-V2` →
`Repository permissions` 里把 **`Contents`** 和 **`Workflows`**
**两项都**设成 `Read and write` → 生成。

### 换 token 时的验证流程（留档，下次还用这套）

**别把 token 写进命令行** —— 那会留在 shell 历史里。用 `read -s` 读，
不回显也不进历史（zsh）：

```bash
read -s "TOK?粘贴新 token 后回车（不回显）: "; echo

# ① 先验权限。经典 token 会打印 scopes，看到 repo, workflow 才算对
curl -s -o /dev/null -D - -H "Authorization: token $TOK" \
  https://api.github.com/user | grep -iE '^HTTP/|x-oauth-scopes'

# ② 验过了再推
git -C ~/Desktop/Vertex/VERTEX-PRO-V2 push \
  "https://${TOK}@github.com/Frank-789/VERTEX-PRO-V2.git" main
```

用**一次性 URL**，不要 `git remote set-url` —— 后者会把 token 写进
`.git/config`，中途出错就留在磁盘上了。

> ⚠️ ① 那行如果打印的不是 `HTTP/2 200`，或者经典 token 的 scopes 里没有
> `workflow` —— **先别推**，说明 token 还是不对，推了只会再浪费一轮。

### ⚠️ 桌面那两个文件该清了（现在比之前更紧急）

`Github终端更新指令.txt` 里现在有 **3 个** token：新加的 `ghp_tMzX…`
（**能用，而且权限极大**）+ 两个已失效的旧版；`部署流程.txt` 里 2 个（已失效）。

**风险点**：这个能用的 token，实测 scopes 是

```
admin:enterprise, admin:org, admin:repo_hook, delete_repo, repo,
workflow, write:packages, copilot, gist, notifications, …
```

——**几乎等于账号全权限，没有过期时间，明文躺在桌面**。
这台机器被人碰到、或桌面被同步进 iCloud/备份，等于把整个 GitHub 账号交出去。

建议：

1. 从这两个文件里**删掉所有 token**（失效的也删，免得下次又逐个试一遍浪费一轮）
2. 用 keychain 存，输一次以后自动记住：

```bash
git config --global credential.helper osxkeychain
```

3. 如果一定要留在文件里，**把 scope 收窄**：这个项目只用到
   `repo` + `workflow`，没必要开 `admin:org` / `delete_repo` / `write:packages`。

### 教训

**① 别拿几天前的报错当现状。** 这条堵点兜了两圈，根因就是：
9-27 写下的 `workflow scope` 结论被当成事实沿用，而中间 token 早换过了，
报错也从「缺 workflow」变成了「401」再变成「403 只读」。
**重新动手前，先把当前状态重测一遍。**

**② 判断「能不能推」，要测写、不测读。** 整个过程中最有效的一步是
`POST /git/blobs` 那一发写探针 —— 它一次把「token 还活着吗 / 能写吗 /
缺哪个权限」三个问题全答了，响应头 `x-accepted-github-permissions`
还会直接点名缺哪个。**以后换 token 都先打这一发，别等推完 4 个提交才发现。**

**③ 也别忘了承认前一个判断是错的。** 这份文档 9-27 那版白纸黑字写着
「唯一能推的是 `ghp_42FT…`，解法是勾 `workflow`」——用户照着做了，
但那个 token 当天晚些就失效了，照做当然没用。**文档里的「结论」要标日期，
不能当成永久事实。**


