# ETH交易策略服务部署指南

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