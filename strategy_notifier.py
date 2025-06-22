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
        df = pd.read_excel(file_path)
    except Exception as e:
        app.logger.error(f"读取Excel失败: {str(e)}")
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
            'remark': str(row.get('备注', '')).strip(),
            'symbol': 'ETH'
        }
        orders.append(order)
    return orders

HISTORY_FILE = "last_strategy.json"

def generate_order_strategy_message(orders: list) -> str:
    from datetime import datetime, timedelta
    now = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M (北京时间)")
    
    if not orders:
        return f"<b>ETH策略分析</b>\n\n`当前无明确交易信号`\n\n⏰ <i>{now}</i>"

    message = f"<b>📈 ETH 趋势黄金三角策略</b>\n\n"

    for order in orders:
        direction_icon = "🟢" if order.get('direction', '').upper() == 'BUY' else "🔴"
        direction_text = "追多" if order.get('direction', '').upper() == 'BUY' else "追空"

        # 解析新的备注信息 (assuming '|' separated key:value pairs)
        remark = order.get('remark', '')
        analysis = {
            '主趋势': 'N/A',
            '波段结构': 'N/A',
            '入场动能': 'N/A',
            '风险评估': 'N/A'
        }
        if remark:
            try:
                analysis_map = {}
                parts = [p.strip() for p in remark.split('|')]
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':', 1)
                        analysis_map[key.strip()] = value.strip()

                # 修正键名和提取逻辑
                analysis['主趋势'] = analysis_map.get('主趋势分析', 'N/A')
                analysis['波段结构'] = analysis_map.get('波段结构分析', 'N/A')
                analysis['入场动能'] = analysis_map.get('入场信号分析', 'N/A') # 键名修正
                analysis['风险评估'] = analysis_map.get('风险评估', 'N/A')

            except Exception as e:
                app.logger.error(f"Error parsing remark '{remark}': {e}")

        message += (
            f"{direction_icon} <b>ETH {direction_text}策略</b>\n"
            f"- <b>触发信号:</b> `{order.get('trigger_signal', 'N/A')}`\n"
            f"- <b>挂单价格:</b> `{order.get('order_price', 'N/A')}`\n"
            f"- <b>止损价格:</b> `{order.get('stop_loss', 'N/A')}`\n"
            f"- <b>止盈价格:</b> `{order.get('take_profit', 'N/A')}`\n\n"
            f"<b>- - - - - 策略分析 - - - - -</b>\n"
            f"▫️ <b>主趋势:</b> {analysis['主趋势']}\n"
            f"▫️ <b>波段结构:</b> {analysis['波段结构']}\n"
            f"▫️ <b>入场动能:</b> {analysis['入场动能']}\n"
            f"▫️ <b>风险评估:</b> {analysis['风险评估']}\n\n"
        )

    message += f"<pre>====================</pre>\n"
    message += f"⏰ <i>生成时间: {now}</i>"
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

# ================== 启动 ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)