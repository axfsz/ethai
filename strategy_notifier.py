import logging
import requests
import os
import pandas as pd
from datetime import datetime
from flask import Flask, request

app = Flask(__name__)

# ================== 配置区 ==================
DEFAULT_TELEGRAM_TOKEN = '7378390777:AAEPODs9r_J1Y488nUJx-79XcdUiLcAzaos'
DEFAULT_TELEGRAM_CHAT_IDS = ['6835958824', '-4826150576']
REQUEST_TIMEOUT = 10

TELEGRAM_TOKEN = DEFAULT_TELEGRAM_TOKEN
TELEGRAM_CHAT_IDS = DEFAULT_TELEGRAM_CHAT_IDS.copy()

# ================== 日志配置 ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    filename='log.file',
    filemode='a'
)

# ================== 通用函数 ==================
def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    success = True
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            "chat_id": chat_id.strip(),
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                app.logger.error(f"Telegram API异常 | 聊天ID: {chat_id} | 状态码: {response.status_code} | 响应: {response.text.strip()}")
                success = False
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Telegram请求失败 | 聊天ID: {chat_id} | 类型: {type(e).__name__} | 详情: {str(e)}")
            success = False
    return success

def load_order_data_from_excel(file_path: str) -> list:
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        app.logger.error(f"读取Excel失败: {str(e)}")
        return []
    orders = []
    for _, row in df.iterrows():
        order = {
            'strategy': str(row.get('策略名称', '')).strip(),
            'direction': str(row.get('方向', '')).strip(),
            'trigger_price': row.get('触发价格', ''),
            'order_price': row.get('挂单价格', ''),
            'stop_loss': row.get('止损价格', ''),
            'take_profit': row.get('止盈价格', ''),
            'qty': row.get('数量', ''),
            'investment': row.get('投资资金', ''),
            'leverage': row.get('杠杆倍数', ''),
            'profit': row.get('预计盈利', ''),
            'loss': row.get('预计亏损', ''),
            'eta': row.get('预计到达时间', ''),
            'remark': str(row.get('备注', '')).strip(),
            'symbol': 'ETH'
        }
        orders.append(order)
    return orders

def generate_order_strategy_message(orders: list) -> str:
    from datetime import datetime, timedelta
    now = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M (北京时间)")
    message = ""
    for order in orders:
        message += (
            f"🚀 *{order['strategy']}*\n\n"
            f"📊 *方向:* {order['direction']}\n"
            f"- 触发价格: {order['trigger_price']}\n"
            f"- 挂单价格: {order['order_price']}\n"
            f"- 止盈价格: {order['take_profit']}\n"
            f"- 止损价格: {order['stop_loss']}\n"
            f"- 预计到达时间: {order['eta']}\n\n"
        )
        if order['remark']:
            message += f"📌 策略分析: {order['remark']}\n\n"
    message += f"⏰ 生成时间: {now}"
    return message

def notify_order_strategy(file_path: str):
    orders = load_order_data_from_excel(file_path)
    if not orders:
        app.logger.warning("未加载到挂单策略数据")
        return

    for order in orders:
        msg = generate_order_strategy_message(order)
        if send_telegram(msg):
            app.logger.info(f"挂单策略通知发送成功 | 币种: {order['symbol']} | 买入价: {order['buy_price']}")
        else:
            app.logger.error(f"挂单策略通知发送失败 | 内容: {order}")

# ================== HTTP 接口 ==================
@app.route("/notify_order_strategy", methods=["POST"])
def api_notify_order_strategy():
    file_path = request.args.get("file", "ETH_动态挂单表.xlsx")
    notify_order_strategy(file_path)
    return "策略通知已触发", 200

# ================== 启动 ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)