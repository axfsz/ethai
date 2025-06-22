#!/bin/bash

# ==============================================================================
# test_notification.sh - 测试 strategy_notifier.py 的通知功能
#
# 用法:
#   1. 直接运行: ./test_notification.sh
#      - 将使用默认配置 (localhost:5001) 和默认的Excel文件。
#
#   2. 自定义主机和端口:
#      HOST="192.168.1.100" PORT="8000" ./test_notification.sh
#      - 将请求发送到 http://192.168.1.100:8000
#
#   3. 自定义Excel文件路径:
#      ./test_notification.sh /path/to/your/file.xlsx
#      - 将使用指定的Excel文件路径。
# ==============================================================================

# --- 配置 ---
# 使用环境变量或提供默认值
HOST="${HOST:-localhost}"
PORT="${PORT:-5001}"

# 获取当前脚本所在的目录
SCRIPT_DIR=$(dirname "$0")

# 优先使用命令行传入的第一个参数作为文件路径，否则使用默认路径
DEFAULT_EXCEL_FILE_PATH="$SCRIPT_DIR/ETH_动态挂单表.xlsx"
EXCEL_FILE_PATH="${1:-$DEFAULT_EXCEL_FILE_PATH}"

# --- 检查文件是否存在 ---
if [ ! -f "$EXCEL_FILE_PATH" ]; then
  echo "❌ 错误: Excel文件未找到于路径 '$EXCEL_FILE_PATH'"
  exit 1
fi

# --- 执行请求 ---
URL="http://${HOST}:${PORT}/notify_order_strategy"

echo "🚀 正在向 $URL 发送测试请求..."
echo "   使用文件: $EXCEL_FILE_PATH"

# 发送POST请求，并捕获响应体和HTTP状态码
response=$(curl -s -w "\n%{http_code}" -X POST "$URL" --data-urlencode "file=$EXCEL_FILE_PATH")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

# --- 结果处理 ---
if [ "$http_code" -eq 200 ]; then
  echo "✅ 请求成功 (HTTP $http_code)。"
  echo "   服务器响应: $body"
  echo "   请检查您的Telegram是否收到通知。"
else
  echo "❌ 请求失败 (HTTP $http_code)。"
  echo "   服务器响应: $body"
  echo "   请检查:"
  echo "   - strategy_notifier.py 服务是否在 ${HOST}:${PORT} 上运行。"
  echo "   - 网络连接是否正常。"
  echo "   - Excel文件路径是否正确。"
  exit 1
fi

exit 0