#!/bin/bash

# 测试策略预测接口
echo "=== 测试策略预测接口 ==="
curl -X POST http://localhost:5001/predict_strategy

# 测试状态更新接口
echo "\n=== 测试状态更新接口 ==="
curl -X POST http://localhost:5001/notify_status

# 测试通知功能
echo "\n=== 测试通知功能 ==="
curl -X POST http://localhost:5001/test_notify

# 测试挂单策略通知
echo "\n=== 测试挂单策略通知 ==="
curl -X POST "http://localhost:5001/notify_order_strategy?file=ETH_动态挂单表.xlsx"
