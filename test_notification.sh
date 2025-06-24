#!/bin/bash

# 通知服务的URL
NOTIFIER_URL="http://localhost:5001"

# 触发“无交易机会”状态通知
echo "正在触发'无交易机会'状态通知..."
curl -X POST "$NOTIFIER_URL/notify_status"

echo "\n"
echo "正在触发缠论策略模拟通知..."
curl -X POST "$NOTIFIER_URL/test_notify"

echo "测试通知已发送。请检查您的Telegram。"