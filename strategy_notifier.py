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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='strategy_notifier.log'
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
            'signal': str(row.get('进仓信号', '')).strip(),
            'buy_price': float(row.get('买入价格', 0)),
            'qty': float(row.get('数量', 0)),
            'take_profit': float(row.get('止盈价格', 0)),
            'stop_loss': float(row.get('止损价格', 0)),
            'extra_condition': str(row.get('额外条件', '')).strip(),
            'symbol': str(row.get('币种', 'ETH')).strip()
        }
        orders.append(order)
    return orders

def generate_order_strategy_message(order: dict) -> str:
    from datetime import datetime, timedelta
    # 转换为北京时间 (UTC+8)
    now = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M (北京时间)")
    
    message = (
        f"🚀 *{order['symbol']} 动态挂单策略更新*\n\n"
        f"📊 *进仓信号:* \n"
        f"- 突破关键阻力位 {order.get('break_price', order['buy_price']*0.98):.2f} USDT\n"
        f"- 15分钟K线收盘价确认\n\n"
        f"🛒 *挂单策略:*\n"
        f"- 买入挂单: {order['buy_price']:.2f} USDT, 数量: {order['qty']:.4f} {order['symbol']}\n"
        f"- 止盈价格: {order['take_profit']:.2f} USDT ({((order['take_profit']/order['buy_price'])-1)*100:.1f}%)\n"
        f"- 止损价格: {order['stop_loss']:.2f} USDT ({((order['buy_price']-order['stop_loss'])/order['buy_price'])*100:.1f}%)\n\n"
    )
    if order['extra_condition']:
        message += f"📌 *额外条件:* {order['extra_condition']}\n\n"
    message += (
        f"📈 *策略说明:* \n"
        f"短期突破跟随策略，价格突破后入场\n"
        f"{((order['take_profit']/order['buy_price'])-1)*100:.1f}%止盈目标，{((order['buy_price']-order['stop_loss'])/order['buy_price'])*100:.1f}%止损保护\n"
        f"自动撤单60分钟未成交\n\n"
        f"⏰ *生成时间:* {now}"
    )
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