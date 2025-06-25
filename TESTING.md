# API测试用例说明

## 1. 启动测试

1. 确保Python环境已安装所需依赖：
   ```bash
   pip install ccxt flask requests pandas ta
   ```

2. 启动主程序：
   ```bash
   python strategy_notifier.py
   ```

3. 在另一个终端中运行测试脚本：
   - Windows:
     ```bash
     test_api.bat
     ```
   - Linux/Mac:
     ```bash
     chmod +x test_api.sh
     ./test_api.sh
     ```

## 2. API接口说明

### /predict_strategy (POST)
- 功能：生成交易策略并发送通知
- 期望响应："策略预测已发送"
- 失败响应："策略预测失败: [错误信息]"

### /notify_status (POST)
- 功能：发送当前市场状态
- 期望响应："状态通知已发送"
- 失败响应："状态通知失败: [错误信息]"

### /test_notify (POST)
- 功能：测试Telegram通知功能
- 期望响应："测试通知已发送"
- 失败响应："测试通知失败: [错误信息]"

### /notify_order_strategy (POST)
- 功能：通知挂单策略
- 参数：file=ETH_动态挂单表.xlsx
- 期望响应："策略通知已触发"
- 失败响应："策略通知失败: [错误信息]"

## 3. 预期测试结果

1. 启动时应立即收到启动通知
2. 每小时自动收到状态更新通知
3. 所有API接口调用应成功并返回相应消息
4. Telegram聊天中应收到所有通知消息

## 4. 常见问题

1. 如果收到"连接被拒绝"错误：
   - 确保主程序已启动
   - 确保端口5001未被占用

2. 如果Telegram通知未收到：
   - 检查Telegram Bot Token是否正确
   - 检查Chat ID是否正确
   - 确保Telegram Bot有权限发送消息

3. 如果API返回错误：
   - 检查错误信息
   - 查看主程序日志
   - 确保所有依赖已正确安装
