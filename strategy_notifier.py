import ccxt
import pandas as pd
import ta
import logging
import requests
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)

# Telegram 配置
TELEGRAM_TOKEN = '7378390777:AAEPODs9r_J1Y488nUJx-79XcdUiLcAzaos'
TELEGRAM_CHAT_IDS = ['6835958824', '-4826150576']
REQUEST_TIMEOUT = 10

# 初始化交易所
exchange = ccxt.binance({'enableRateLimit': True})
symbol = 'ETH/USDT'

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
                app.logger.error(f"Telegram 发送失败 | 聊天ID: {chat_id} | 状态码: {response.status_code} | 响应: {response.text.strip()}")
                success = False
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Telegram 请求异常 | 聊天ID: {chat_id} | 错误: {e}")
            success = False
    return success

# ================== 策略核心 ==================
def fetch_ohlcv(symbol, timeframe, limit):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calc_indicators(df):
    df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['macd'], df['macdsignal'], _ = ta.trend.macd(df['close'])
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['volume_ma'] = df['volume'].rolling(window=20).mean()
    bb = ta.volatility.BollingerBands(df['close'])
    df['bb_high'] = bb.bollinger_hband()
    df['bb_low'] = bb.bollinger_lband()
    return df

def detect_signals():
    df_1w = calc_indicators(fetch_ohlcv(symbol, '1w', 60))
    df_1d = calc_indicators(fetch_ohlcv(symbol, '1d', 180))
    df_4h = calc_indicators(fetch_ohlcv(symbol, '4h', 200))
    df_1h = calc_indicators(fetch_ohlcv(symbol, '1h', 120))

    signals = []
    
    # 周线 EMA20 判断多头趋势
    if df_1w['ema20'].iloc[-1] > df_1w['ema20'].iloc[-5]:
        signals.append('周线EMA上升')

    # 日线 RSI 底背离
    if df_1d['close'].iloc[-1] < df_1d['close'].iloc[-5] and df_1d['rsi'].iloc[-1] > df_1d['rsi'].iloc[-5]:
        signals.append('日线RSI底背离')

    # 4H 放量突破
    if (df_4h['close'].iloc[-1] > df_4h['bb_high'].iloc[-1] and
        df_4h['volume'].iloc[-1] > 1.5 * df_4h['volume_ma'].iloc[-1]):
        signals.append('4小时放量突破')

    # 1H MACD 金叉
    if (df_1h['macd'].iloc[-1] > df_1h['macdsignal'].iloc[-1] and
        df_1h['macd'].iloc[-2] <= df_1h['macdsignal'].iloc[-2]):
        signals.append('1小时MACD金叉')

    return signals

def generate_strategy_message(signals):
    now = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M (北京时间)")
    if len(signals) >= 3:
        position = "重仓建议 (5%-8%)"
    elif len(signals) == 2:
        position = "轻仓建议 (3%-5%)"
    elif len(signals) == 1:
        position = "试探单建议 (1%-2%)"
    else:
        position = "观望 (无明显交易机会)"
    
    message = f"<b>📊 ETH 策略预测</b>\n<pre>--------------------------</pre>\n"
    message += f"⚡ 检测信号: {', '.join(signals) if signals else '无'}\n"
    message += f"💡 仓位建议: {position}\n"
    message += f"<pre>====================</pre>\n"
    message += f"<i>免责声明：以上为AI策略预测，不构成投资建议。</i>\n"
    message += f"⏰ <b>生成时间:</b> {now}"
    return message

# ================== Flask 接口 ==================
@app.route("/predict_strategy", methods=["POST"])
def predict_strategy():
    try:
        signals = detect_signals()
        msg = generate_strategy_message(signals)
        send_telegram(msg)
        return "策略预测已发送", 200
    except Exception as e:
        app.logger.error(f"策略预测失败: {e}")
        return f"策略预测失败: {e}", 500

# ================== 启动 ==================
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=False)