# 基于官方 Python 运行时镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY eth-gd.py strategy_notifier.py ./

# 安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 暴露服务端口
EXPOSE 5001

# 安装supervisor
RUN apt-get update && apt-get install -y supervisor

# 配置supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 启动服务
CMD ["/usr/bin/supervisord"]
