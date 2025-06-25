@echo off

echo === 测试策略预测接口 ===
curl -X POST http://localhost:5001/predict_strategy
echo.

echo === 测试状态更新接口 ===
curl -X POST http://localhost:5001/notify_status
echo.

echo === 测试通知功能 ===
curl -X POST http://localhost:5001/test_notify
echo.

echo === 测试挂单策略通知 ===
curl -X POST "http://localhost:5001/notify_order_strategy?file=ETH_动态挂单表.xlsx"
