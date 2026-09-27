# syntax=docker/dockerfile:1
#
# 构建（**必须在仓库根目录执行**，因为要拷 config/ 和 prompts/）：
#
#     docker build -f apps/api/Dockerfile -t vertex-api .
#
# 运行：
#
#     docker run --rm -p 8000:8000 \
#       -e DEEPSEEK_API_KEY=sk-xxx \
#       -v vertex-data:/data \
#       vertex-api

# ─────────────────────────── 构建阶段 ───────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────── 运行阶段 ───────────────────────────
FROM python:3.11-slim

# tini 作 PID 1：正确转发信号、回收僵尸进程。
# 没有它，docker stop 会等到超时才杀掉 uvicorn。
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

# 非 root 用户，固定 UID 便于挂卷时对齐权限
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin vertex

# ⚠️ 目录层级不能改。
# core/paths.py 用 Path(__file__).resolve().parents[4] 推算仓库根，
# src/core/paths.py → src/core → src → api → apps → 仓库根。
# 打平了就会越界，所有路径解析全错。
WORKDIR /app/apps/api

# 只读的镜像资源
COPY config/          /app/config/
COPY prompts/         /app/prompts/
COPY apps/api/src/    /app/apps/api/src/
COPY apps/api/dev/    /app/apps/api/dev/

# 可写状态统一落在 /data，挂卷即可持久化
ENV DATA_HOME=/data \
    CONFIG_HOME=/app/config \
    PROMPTS_HOME=/app/prompts \
    ALLOW_DEV_CORS=0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN mkdir -p /data && chown -R vertex:vertex /data
VOLUME ["/data"]

USER vertex
EXPOSE 8000

# 用 python 探活，省掉在镜像里装 curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
