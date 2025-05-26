# backend/Dockerfile
FROM python:3.13-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 构建工具
    build-essential \
    gcc \
    pkg-config \
    # 数据库支持
    default-libmysqlclient-dev \
    # 网络工具
    netcat-openbsd \
    curl \
    # 系统工具
    vim-tiny \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装Python依赖
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 复制应用代码
COPY . .

# 创建静态文件和媒体文件目录
RUN mkdir -p staticfiles media static

# 设置权限
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
