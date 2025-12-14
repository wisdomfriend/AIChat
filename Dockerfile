FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt并安装Python依赖
# 使用国内镜像源加速（适合中国大陆网络）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn

# 复制应用代码（保持包结构）
COPY flask_app/ /app/flask_app/

# 复制WSGI入口文件
COPY wsgi.py /app/wsgi.py

# 复制 .env 文件（如果存在）
COPY .env /app/.env

# 端口导出为5000
EXPOSE 5000

# 使用gunicorn启动应用（通过wsgi.py）
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:app"]

