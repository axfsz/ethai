#!/bin/bash

# 测试本地通知服务状态
curl -X POST http://127.0.0.1:5000/notify_status
# 测试本地缠论策略推送
curl -X POST http://127.0.0.1:5000/test_notify

echo "本地测试通知已发送，请检查您的Telegram。"

# 通知服务的URL
NOTIFIER_URL="http://localhost:5001"

# 触发“无交易机会”状态通知
curl -X POST "$NOTIFIER_URL/notify_status"
# 触发缠论策略模拟通知
curl -X POST "$NOTIFIER_URL/test_notify"

echo "远程测试通知已发送，请检查您的Telegram。"