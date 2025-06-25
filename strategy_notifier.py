import ccxt
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request
from simple_data_processor import SimpleDataProcessor
from signal_detector import SignalDetector
import threading
import time
from config import config
from dotenv import load_dotenv
import os
import logging
from logging_config import logger, log_function_call

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# Telegram 配置
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_IDS = [os.getenv('TELEGRAM_CHAT_ID')]
REQUEST_TIMEOUT = 10

# 初始化组件
data_processor = SimpleDataProcessor()
signal_detector = SignalDetector()
exchange = ccxt.binance({'enableRateLimit': True})

# 设置Flask日志级别
app.logger.setLevel(logging.INFO)

# 使用日志装饰器装饰所有路由函数
@app.route("/predict_strategy", methods=["POST"])
@log_function_call
def predict_strategy():
    """预测交易策略"""
    try:
        signals = detect_signals()
        msg = generate_strategy_message(signals)
        if send_telegram(msg):
            app.logger.info("策略预测通知发送成功")
            return "策略预测已发送", 200
        else:
            app.logger.error("策略预测通知发送失败")
            return "策略预测通知发送失败", 500
    except Exception as e:
        app.logger.error(f"策略预测失败: {e}")
        return f"策略预测失败: {str(e)}", 500

@app.route("/notify_status", methods=["POST"])
@log_function_call
def notify_status():
    """发送状态更新"""
    try:
        msg = generate_status_message()
        if send_telegram(msg):
            app.logger.info("状态更新通知发送成功")
            return "状态通知已发送", 200
        else:
            app.logger.error("状态更新通知发送失败")
            return "状态通知发送失败", 500
    except Exception as e:
        app.logger.error(f"状态通知失败: {e}")
        return f"状态通知失败: {str(e)}", 500

@app.route("/test_notify", methods=["POST"])
@log_function_call
def test_notify():
    """测试通知功能"""
    try:
        msg = "🔔 <b>测试通知</b>\n" \
            "🚀 这是一条测试通知消息。\n" \
            "✅ 如果您收到此消息，说明通知功能正常工作。"
        if send_telegram(msg):
            app.logger.info("测试通知发送成功")
            return "测试通知已发送", 200
        else:
            app.logger.error("测试通知发送失败")
            return "测试通知发送失败", 500
    except Exception as e:
        app.logger.error(f"测试通知失败: {e}")
        return f"测试通知失败: {str(e)}", 500

@app.route("/notify_order_strategy", methods=["POST"])
@log_function_call
def notify_order_strategy():
    """通知挂单策略"""
    try:
        file_path = request.args.get("file", "ETH_动态挂单表.xlsx")
        # 这里可以添加挂单策略的处理逻辑
        msg = f"📊 <b>挂单策略更新</b>\n" \
            f"📄 文件: {file_path}\n" \
            "🚀 策略已更新并发送通知。"
        if send_telegram(msg):
            app.logger.info("策略更新通知发送成功")
            return "策略通知已触发", 200
        else:
            app.logger.error("策略更新通知发送失败")
            return "策略通知发送失败", 500
    except Exception as e:
        app.logger.error(f"策略通知失败: {e}")
        return f"策略通知失败: {str(e)}", 500

# ================== 通用函数 ==================
@log_function_call
def send_telegram(message: str) -> bool:
    """发送Telegram消息"""
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
                app.logger.error(f"Telegram 发送失败 | 聊天ID: {chat_id} | 状态码: {response.status_code} | 响应: {response.text.strip()}")
                success = False
            else:
                app.logger.info(f"Telegram 发送成功 | 聊天ID: {chat_id} | 响应: {response.text.strip()}")
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Telegram 请求异常 | 聊天ID: {chat_id} | 错误: {e}")
            success = False
    return success

# ================== 策略核心 ==================
@log_function_call
def detect_signals():
    """检测交易信号"""
    # 获取所有时间周期的数据
    data = data_processor.get_all_timeframes_data(exchange)
    
    signals = []
    for timeframe, indicators in data.items():
        # 检测当前时间周期的所有信号
        timeframe_signals = signal_detector.detect_all_signals(indicators, timeframe)
        signals.extend(timeframe_signals)
    
    return signals

@log_function_call
def generate_strategy_message(signals):
    """生成策略消息"""
    now = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M (北京时间)")
    bullish_signals = [s.name for s in signals if 'Bullish' in s.name or 'Breakout' in s.name]
    bearish_signals = [s.name for s in signals if 'Bearish' in s.name]

    if len(bullish_signals) >= 2:
        position = f"做多 (发现 {len(bullish_signals)} 个看涨信号)"
    elif len(bearish_signals) >= 2:
        position = f"做空 (发现 {len(bearish_signals)} 个看跌信号)"
    else:
        position = "观望 (信号不足或冲突)"
    
    message = f"<b>📊 ETH 策略预测</b>\n"
    message += "....................................\n"
    message += f"⚡ 检测信号: {', '.join(s.name for s in signals) if signals else '无'}\n"
    message += f"💡 仓位建议: {position}\n"
    message += "....................................\n"
    message += f"<i>免责声明：以上为AI策略预测，不构成投资建议。</i>\n"
    message += f"⏰ <b>生成时间:</b> {now}"
    return message

@log_function_call
def generate_status_message():
    """生成状态更新消息"""
    now = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M (北京时间)")
    
    # 获取最新价格
    ticker = exchange.fetch_ticker('ETH/USDT')
    price = ticker['last']
    
    message = f"<b>📊 ETH 状态更新</b>\n"
    message += "....................................\n"
    message += f"💰 当前价格: ${price:.2f}\n"
    message += "....................................\n"
    message += f"⏰ <b>更新时间:</b> {now}"
    return message

@log_function_call
def hourly_status_update():
    """每小时发送状态更新"""
    while True:
        try:
            msg = generate_status_message()
            if send_telegram(msg):
                app.logger.info("状态更新通知发送成功")
            else:
                app.logger.error("状态更新通知发送失败")
            # 等待1小时
            time.sleep(3600)
        except Exception as e:
            app.logger.error(f"状态更新失败: {e}")
            # 即使出错也继续等待1小时
            time.sleep(3600)

# ================== 启动 ==================
@log_function_call
def main():
    # 启动每小时状态更新线程
    status_thread = threading.Thread(target=hourly_status_update, daemon=True)
    status_thread.start()
    
    # 立即发送启动通知
    msg = "🤖 <b>ChanTradeBot 已启动</b>\n" \
        "🚀 系统开始运行，每小时将自动发送状态更新。\n" \
        "⏰ 下一次状态更新将在1小时后。"
    if send_telegram(msg):
        app.logger.info("启动通知发送成功")
    else:
        app.logger.error("启动通知发送失败")
    
    # 启动Flask应用
    app.run(host="0.0.0.0", port=5001, debug=True)

if __name__ == '__main__':
    main()