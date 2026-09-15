"""FastAPI 应用入口。

    uvicorn src.main:app --reload --port 8000

生产环境**不需要** CORS：前端通过 Next.js 的 rewrites 走同源代理，
浏览器眼里所有请求都发给自己。开发时如果前端跑在 3000 端口而没走代理，
下面的 dev 白名单能兜住。
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.chat import router as chat_router
from .core.paths import data_home, ensure_dirs, prompts_dir, repo_root
from .core.provider_router import get_router
from .core.tool_center import get_tool_center

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
log = logging.getLogger("vertex")

# 仓库根目录的 .env —— 密钥只在这里，且它在 .gitignore 里
load_dotenv(repo_root() / ".env")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_dirs()

    router = get_router()
    providers = router.available()
    if providers:
        log.info("AI 供应商就绪：%s", ", ".join(providers))
    else:
        log.warning(
            "没有任何可用的 AI 供应商 —— 对话会直接报错。"
            "请在仓库根目录的 .env 里配置 DEEPSEEK_API_KEY。"
        )

    center = get_tool_center()
    ready = [t.name for t in center.ready()]
    pending = [t.name for t in center.all() if not t.is_ready()]
    log.info("工具就绪 %d 个：%s", len(ready), ", ".join(ready) or "无")
    if pending:
        # 明确列出来，别让用户猜为什么某个能力不工作
        log.info("工具待配置 %d 个：%s", len(pending), ", ".join(pending))

    log.info("数据目录：%s", data_home())
    log.info("提示词目录：%s", prompts_dir())
    yield


app = FastAPI(
    title="VERTEX API",
    description="电商经营智能体",
    version="2.0.0",
    lifespan=lifespan,
)

# 开发期兜底。生产走同源代理，用不到这段。
if os.getenv("ALLOW_DEV_CORS", "1") == "1":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

app.include_router(chat_router, prefix="/api/v1", tags=["chat"])


@app.get("/health")
async def health() -> JSONResponse:
    """健康检查 —— 顺带把配置缺口暴露出来，方便排障。"""
    router = get_router()
    center = get_tool_center()
    return JSONResponse(
        {
            "ok": True,
            "providers": router.available(),
            "tools": {
                "ready": [t.name for t in center.ready()],
                "pending": [t.name for t in center.all() if not t.is_ready()],
            },
        }
    )
