import logging
import requests
import os
import pandas as pd
from datetime import datetime
from flask import Flask, request
import json

app = Flask(__name__)

# ================== 配置区 ==================
DEFAULT_TELEGRAM_TOKEN = '7378390777:AAEPODs9r_J1Y488nUJx-79XcdUiLcAzaos'
DEFAULT_TELEGRAM_CHAT_IDS = ['6835958824', '-4826150576']
REQUEST_TIMEOUT = 10

TELEGRAM_TOKEN = DEFAULT_TELEGRAM_TOKEN
TELEGRAM_CHAT_IDS = DEFAULT_TELEGRAM_CHAT_IDS.copy()

# ================== 日志配置 ==================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ================== 通用函数 ==================
def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    success = True
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            "chat_id": chat_id.strip(),
            "text": message,
            "parse_mode": "HTML",
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
        # 读取最新的工作表
        xls = pd.ExcelFile(file_path)
        sheet_name = xls.sheet_names[-1]
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        app.logger.error(f"读取Excel最新工作表失败: {str(e)}")
        return []
    orders = []
    for _, row in df.iterrows():
        order = {
            'strategy': str(row.get('策略名称', '')).strip(),
            'direction': str(row.get('方向', '')).strip(),
            'trigger_signal': row.get('触发信号', ''),
            'order_price': row.get('挂单价格', ''),
            'stop_loss': row.get('止损价格', ''),
            'take_profit': row.get('止盈价格', ''),
            'qty': row.get('数量', ''),
            'investment': row.get('投资资金', ''),
            'leverage': row.get('杠杆倍数', ''),
            'profit': row.get('预计盈利', ''),
            'loss': row.get('预计亏损', ''),
            '策略分析': str(row.get('策略分析', '')).strip(), # 修正键名
            'symbol': 'ETH'
        }
        orders.append(order)
    return orders

HISTORY_FILE = "last_strategy.json"

def generate_order_strategy_message(orders: list) -> str:
    from datetime import datetime, timedelta
    now = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M (北京时间)")

    message = f"<b>📈 ETH 趋势黄金三角策略分析</b>\n<pre>--------------------------</pre>\n"

    for order in orders:
        direction_icon = "🟢 追多 (BUY)" if order.get('direction', '').upper() == 'BUY' else "🔴 追空 (SELL)"

        # 将策略分析内容包裹在<pre>标签中以保持格式
        analysis_content = order.get('策略分析', '无')
        analysis_html = f"<pre>{analysis_content}</pre>"

        trigger_signal = order.get('trigger_signal', 'N/A')
        if isinstance(trigger_signal, (int, float)):
            trigger_signal = f"{trigger_signal:.2f}"

        message += (
            f"<b>🔹 策略方向: {direction_icon}</b>\n"
            f"   - <b>触发信号:</b> <code>{trigger_signal}</code>\n"
            f"   - <b>挂单价格:</b> <code>{order.get('order_price', 'N/A')}</code>\n"
            f"   - <b>止损防守:</b> <code>{order.get('stop_loss', 'N/A')}</code>\n"
            f"   - <b>止盈目标:</b> <code>{order.get('take_profit', 'N/A')}</code>\n\n"
            f"<b>- - - - - 策略逻辑拆解 - - - - -</b>\n"
            f"{analysis_html}\n"
        )

    message += f"<pre>====================</pre>\n"
    message += f"<i>免责声明：以上内容仅为AI策略分析，不构成任何投资建议。</i>\n"
    message += f"⏰ <b>生成时间:</b> {now}"
    return message

# 对比策略内容和信号差值
def is_strategy_changed(new_orders, threshold=5):
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                last_orders = json.load(f)
        else:
            last_orders = None
    except Exception:
        last_orders = None
    if not last_orders:
        return True
    def get_signal(order):
        try:
            # 修正键名
            return float(order.get('trigger_signal', 0))
        except (ValueError, TypeError):
            return 0
    for new, old in zip(new_orders, last_orders):
        if new['direction'] == old['direction']:
            if abs(get_signal(new) - get_signal(old)) < threshold and new['remark'] == old['remark']:
                continue
            else:
                return True
    return False

def save_strategy(orders):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False)
    except Exception as e:
        app.logger.error(f"保存策略历史失败: {e}")

def notify_order_strategy(file_path: str):
    orders = load_order_data_from_excel(file_path)
    if not orders:
        app.logger.warning("未加载到挂单策略数据")
        return
    if not is_strategy_changed(orders):
        app.logger.info("策略内容与历史无明显变化或信号差值小于5，未发送通知。")
        return
    msg = generate_order_strategy_message(orders)
    if send_telegram(msg):
        app.logger.info("挂单策略通知发送成功")
        save_strategy(orders)
    else:
        app.logger.error(f"挂单策略通知发送失败 | 内容: {msg}")

# ================== HTTP 接口 ==================
@app.route("/notify_order_strategy", methods=["POST"])
def api_notify_order_strategy():
    file_path = request.args.get("file", "ETH_动态挂单表.xlsx")
    notify_order_strategy(file_path)
    return "策略通知已触发", 200

@app.route("/notify_status", methods=["POST"])
def api_notify_status():
    from datetime import datetime, timedelta
    now = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M (北京时间)")
    message = f"<b>📉 ETH 策略分析</b>\n\n<i>当前无明确交易信号，市场方向不明，建议保持观望。</i>\n\n⏰ <i>{now}</i>"
    send_telegram(message)
    return "状态通知已发送", 200

@app.route("/test_notify", methods=["POST"])
def test_notify():
    # 用于测试的模拟订单数据
    test_orders = [
        {
            'direction': 'BUY',
            'trigger_signal': 2300.50,
            'order_price': 2305.00,
            'stop_loss': 2280.00,
            'take_profit': 2380.00,
            '策略分析': '缠论15M短线多单：15M级别出现底背驰买入结构，入场点2305，止损2280，目标2380。\n缠论1H长线多单：1H与15M共振，1H级别出现买入结构，止损2280，入场点2305，目标2380。\n策略：短线快进快出，长线持有，盈亏比目标分别为1.5:1和3:1。'
        },
        {
            'direction': 'SELL',
            'trigger_signal': 2250.00,
            'order_price': 2245.00,
            'stop_loss': 2270.00,
            'take_profit': 2180.00,
            '策略分析': '缠论15M短线空单：15M级别出现顶背驰卖出结构，入场点2245，止损2270，目标2180。\n缠论1H长线空单：1H与15M共振，1H级别出现卖出结构，止损2270，入场点2245，目标2180。\n策略：短线快进快出，长线持有，盈亏比目标分别为1.5:1和3:1。'
        }
    ]
    # 测试有策略的通知
    strategy_msg = generate_order_strategy_message(test_orders)
    send_telegram(strategy_msg)
    # 测试无策略的通知
    api_notify_status()
    return "测试通知已发送", 200

# ================== 启动 ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)