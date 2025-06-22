# ETH交易策略服务 使用说明

## 1. 项目概述

本服务是一个基于Docker的自动化ETH交易策略分析与通知系统。它由两个核心组件构成：

- **策略生成器 (`eth-gd.py`)**: 定时从币安API获取最新的ETH市场数据，基于多时间框架（日线、4小时、15分钟）的K线进行趋势、波段和入场信号分析，最终生成具体的“追多”或“追空”交易策略，并将结果保存到 `ETH_动态挂单表.xlsx` 文件中。
- **通知服务 (`strategy_notifier.py`)**: 一个Flask Web服务，负责监控策略文件的变化。当检测到策略更新时，它会生成一份格式化的HTML报告，并通过Telegram Bot发送给指定的用户或频道。

整个系统通过 `Supervisor` 进行进程管理，确保两个核心服务的稳定运行，并通过 `docker-compose` 进行容器化部署，实现了环境隔离和一键启停。

## 2. 功能特性

- **自动化策略分析**: 无需人工干预，定时分析市场并生成交易信号。
- **多时间框架决策**: 结合长、中、短周期数据，提高决策的准确性。
- **实时Telegram通知**: 策略一旦更新，立即通过Telegram发送，确保用户不会错过交易机会。
- **非root用户运行**: 增强了容器的安全性，所有进程均以非特权用户 `appuser` 运行。
- **统一日志管理**: 所有服务的日志（包括Supervisor本身）都统一输出到容器内的 `/app/log.file`，方便集中排查问题。
- **灵活的测试脚本**: 提供 `test_notification.sh`，方便开发者快速测试通知功能。
- **容器化部署**: 使用Docker和docker-compose，简化了部署和运维流程。

## 3. 技术架构

- **核心语言**: Python 3.10
- **核心库**: Pandas, Numpy, aiohttp, Flask, python-telegram-bot
- **进程管理**: Supervisor
- **容器化**: Docker, Docker Compose
- **数据源**: 币安 (Binance) API
- **通知渠道**: Telegram

## 4. 如何部署和运行

### 4.1. 环境准备

- 安装 [Docker](https://www.docker.com/get-started)
- 安装 [Docker Compose](https://docs.docker.com/compose/install/)

### 4.2. 配置文件说明

在部署前，您可能需要根据实际情况修改以下配置：

- **`strategy_notifier.py`**: 
  - `DEFAULT_TELEGRAM_TOKEN`: 替换为您自己的Telegram Bot Token。
  - `DEFAULT_TELEGRAM_CHAT_IDS`: 替换为您希望接收通知的Telegram聊天ID（可以是用户ID或频道ID）。

- **`docker-compose.yaml`**: 
  - `ports`: 如果默认的 `5001` 端口已被占用，可以映射到其他主机端口。

### 4.3. 构建与启动

在项目根目录下，执行以下命令：

```bash
# 构建并以后台模式启动服务
docker-compose up --build -d
```

### 4.4. 查看服务状态和日志

```bash
# 查看容器运行状态
docker-compose ps

# 实时查看统一日志
docker-compose logs -f
```

### 4.5. 停止服务

```bash
# 停止并移除容器
docker-compose down
```

## 5. 如何使用

### 5.1. 自动运行

服务启动后，`eth-gd.py` 会在容器启动时立即执行一次，之后每小时自动运行一次，生成最新的策略。`strategy_notifier.py` 会在策略更新时自动发送通知。

### 5.2. 手动测试通知

如果您想立即测试Telegram通知功能，可以执行测试脚本：

```bash
# 确保服务正在运行
# 在项目根目录下执行
./test_notification.sh
```

该脚本会向 `strategy_notifier.py` 服务发送一个请求，触发一次基于当前 `ETH_动态挂单表.xlsx` 内容的通知。

您也可以自定义测试目标和文件：

```bash
# 测试另一台主机上的服务
HOST="192.168.1.100" PORT="8000" ./test_notification.sh

# 使用不同的Excel文件进行测试
./test_notification.sh /path/to/another/file.xlsx
```

## 6. 文件结构说明

```
.
├── DEPLOY.md             # 本部署与使用说明
├── Dockerfile            # Docker镜像构建文件
├── ETH_动态挂单表.xlsx   # 策略生成结果
├── docker-compose.yaml   # Docker Compose部署文件
├── eth-gd.py             # 策略生成脚本
├── k.md                  # K线分析逻辑参考（文档）
├── log.file              # 统一日志文件
├── requirements.txt      # Python依赖
├── strategy_notifier.py  # 策略通知服务
├── supervisord.conf      # Supervisor进程管理配置
├── test_notification.sh  # 手动测试通知脚本
└── xinhao.md             # 信号逻辑参考（文档）
```

## 系统要求
- Docker 20.10+ 
- Docker Compose 1.29+

## 部署步骤

1. **构建并启动容器**
   ```bash
   docker-compose up -d --build
   ```

2. **查看运行状态**
   ```bash
   docker-compose ps
   ```

3. **查看日志**
   ```bash
   docker-compose logs -f
   ```

4. **停止服务**
   ```bash
   docker-compose down
   ```

## 服务说明

- **eth-gd.py**: 每小时分析ETH市场行情并生成策略表格
- **strategy_notifier.py**: 监听策略更新并发送通知

## 数据持久化

- `ETH_动态挂单表.xlsx` 文件会保存在宿主机当前目录
- 日志文件保存在 `log.file`