# 1. 使用官方Python 3.12 slim版本作为基础镜像
FROM python:3.12-slim

# 2. 设置环境变量，防止Python写入.pyc文件
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. 设置时区为北京时间
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 4. 创建工作目录
WORKDIR /app

# 5. 安装依赖
# 首先复制依赖文件，利用Docker的层缓存机制
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 复制项目代码到工作目录
COPY . .

# 7. 暴露应用程序运行的端口
EXPOSE 5001

# 8. 定义容器启动时执行的命令
CMD ["python", "strategy_notifier.py"]