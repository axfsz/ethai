import requests
import pandas as pd
import time
from datetime import datetime
import numpy as np
import openpyxl
from openpyxl.styles import Font, Alignment
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 获取币安 ETHUSDT 最新价格和多时间框架K线数据
def get_binance_data():
    try:
        # 获取最新价格
        ticker_url = "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
        price_resp = requests.get(ticker_url).json()
        current_price = float(price_resp['price'])

        # 根据新要求，获取4h, 1h, 15m三个时间框架的K线数据
        # 4小时数据，用于判断主趋势
        kline_url_4h = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=4h&limit=50"
        klines_4h = requests.get(kline_url_4h).json()

        # 1小时数据，用于识别波段推进结构
        kline_url_1h = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=1h&limit=100"
        klines_1h = requests.get(kline_url_1h).json()

        # 15分钟数据，用于精确入场
        kline_url_15m = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=15m&limit=50"
        klines_15m = requests.get(kline_url_15m).json()

        return {
            "current_price": current_price,
            "klines_4h": klines_4h,
            "klines_1h": klines_1h,
            "klines_15m": klines_15m
        }

    except Exception as e:
        logging.error(f"获取多时间框架数据失败: {e}")
        return None

# --- 辅助计算函数 ---
def calc_ema(data, period):
    if len(data) < period:
        return np.array([np.mean(data)])
    ema = [sum(data[:period]) / period]
    alpha = 2 / (period + 1)
    for price in data[period:]:
        ema.append(alpha * price + (1 - alpha) * ema[-1])
    return np.array(ema)

def detect_swings(klines, order=5):
    """更精确的波段高低点检测."""
    highs = pd.Series([float(k[2]) for k in klines])
    lows = pd.Series([float(k[3]) for k in klines])
    
    # 使用scipy.signal.argrelextrema寻找局部极值点
    from scipy.signal import argrelextrema
    
    # 寻找高点 (order参数定义了在转折点一侧需要多少个点来确认)
    high_indices = argrelextrema(highs.values, np.greater_equal, order=order)[0]
    # 寻找低点
    low_indices = argrelextrema(lows.values, np.less_equal, order=order)[0]
    
    swing_highs = [(i, highs[i]) for i in high_indices]
    swing_lows = [(i, lows[i]) for i in low_indices]
    
    return swing_highs, swing_lows

def create_order(name, direction, trigger, order_price, sl, tp, investment, leverage, analysis):
    quantity_formula = f'={investment}/{order_price}'
    if direction == "BUY":
        profit_formula = f'=({tp}-{order_price})*G2*I2' # Assuming G2 is quantity, I2 is leverage
        loss_formula = f'=({order_price}-{sl})*G2*I2'
    else:
        profit_formula = f'=({order_price}-{tp})*G3*I3' # Assuming G3 is quantity, I3 is leverage
        loss_formula = f'=({sl}-{order_price})*G3*I3'

    return {
        "策略名称": name,
        "方向": direction,
        "触发信号": trigger,
        "挂单价格": order_price,
        "止损价格": sl,
        "止盈价格": tp,
        "数量": quantity_formula,
        "杠杆倍数": leverage,
        "预计盈利": profit_formula,
        "预计亏损": loss_formula,
        "策略分析": analysis
    }

# 动态生成挂单表 (V3 - 核心逻辑重构)
def generate_order_table(market_data, investment_amount, leverage):
    current_price = market_data['current_price']
    klines_4h = market_data['klines_4h']
    klines_1h = market_data['klines_1h']
    klines_15m = market_data['klines_15m']
    orders = []

    # --- 1. 核心信号分析 --- 
    # 信号1: 4H级别主趋势 (EMA20)
    closes_4h = [float(k[4]) for k in klines_4h]
    ema20_4h = calc_ema(closes_4h, 20)[-1]
    main_trend = "多头" if current_price > ema20_4h else "空头"
    trend_analysis = f"4H EMA20判断为{main_trend}趋势 (现价:{current_price:.2f} vs EMA:{ema20_4h:.2f})。"

    # 信号2: 1H级别波浪推进结构
    swing_highs_1h, swing_lows_1h = detect_swings(klines_1h, order=5)
    is_up_propulsion = False
    is_down_propulsion = False
    wave_analysis = "结构不明"

    if len(swing_lows_1h) >= 2 and len(swing_highs_1h) >= 2:
        # 上升推进: 更高的高点和更高的低点
        if swing_highs_1h[-1][1] > swing_highs_1h[-2][1] and swing_lows_1h[-1][1] > swing_lows_1h[-2][1]:
            is_up_propulsion = True
            wave_analysis = f"1H形成上升推进结构 (高点:{swing_highs_1h[-1][1]:.2f} > {swing_highs_1h[-2][1]:.2f}, 低点:{swing_lows_1h[-1][1]:.2f} > {swing_lows_1h[-2][1]:.2f})。"
        # 下降推进: 更低的高点和更低的低点
        elif swing_highs_1h[-1][1] < swing_highs_1h[-2][1] and swing_lows_1h[-1][1] < swing_lows_1h[-2][1]:
            is_down_propulsion = True
            wave_analysis = f"1H形成下降推进结构 (高点:{swing_highs_1h[-1][1]:.2f} < {swing_highs_1h[-2][1]:.2f}, 低点:{swing_lows_1h[-1][1]:.2f} < {swing_lows_1h[-2][1]:.2f})。"
    else:
        wave_analysis = "1H波浪结构不明确，无法确认推进。"

    # 信号3: 15M级别突破放量
    volumes_15m = [float(k[5]) for k in klines_15m]
    avg_volume_15m = np.mean(volumes_15m[-20:-1]) # 计算最近20根K线的平均成交量（不含当前）
    is_volume_breakout = volumes_15m[-1] > avg_volume_15m * 2 # 当前成交量是平均的2倍以上
    volume_analysis = f"15M成交量{'显著放大' if is_volume_breakout else '平稳'} (当前:{volumes_15m[-1]:.0f} vs 平均:{avg_volume_15m:.0f})。"

    # --- 2. 策略决策与订单生成 ---
    # 追多策略: 4H多头 + 1H上升推进 + 15M放量
    if main_trend == "多头" and is_up_propulsion and is_volume_breakout:
        last_low = swing_lows_1h[-1][1]
        buy_order_price = round(current_price * 1.001, 2)
        buy_trigger_price = round(current_price, 2)
        stop_loss_price = round(last_low * 0.99, 2)
        risk_amount = buy_order_price - stop_loss_price
        take_profit_price = round(buy_order_price + risk_amount * 3, 2)

        final_analysis = (
            f"主趋势分析: {trend_analysis}\n"
            f"波段结构分析: {wave_analysis}\n"
            f"入场信号分析: {volume_analysis}\n"
            f"核心策略: 趋势黄金三角 (4H趋势+1H推进+15M放量)。\n"
            f"风险评估: 盈亏比大于3:1，止损设置于1H关键结构位下方，风险可控。"
        )
        orders.append(create_order("ETH趋势追多", "BUY", buy_trigger_price, buy_order_price, stop_loss_price, take_profit_price, investment_amount, leverage, final_analysis))

    # 追空策略: 4H空头 + 1H下降推进 + 15M放量
    if main_trend == "空头" and is_down_propulsion and is_volume_breakout:
        last_high = swing_highs_1h[-1][1]
        sell_order_price = round(current_price * 0.999, 2)
        sell_trigger_price = round(current_price, 2)
        stop_loss_price = round(last_high * 1.01, 2)
        risk_amount = stop_loss_price - sell_order_price
        take_profit_price = round(sell_order_price - risk_amount * 3, 2)

        final_analysis = (
            f"主趋势分析: {trend_analysis}\n"
            f"波段结构分析: {wave_analysis}\n"
            f"入场信号分析: {volume_analysis}\n"
            f"核心策略: 趋势黄金三角 (4H趋势+1H推进+15M放量)。\n"
            f"风险评估: 盈亏比大于3:1，止损设置于1H关键结构位上方，风险可控。"
        )
        orders.append(create_order("ETH趋势追空", "SELL", sell_trigger_price, sell_order_price, stop_loss_price, take_profit_price, investment_amount, leverage, final_analysis))

    return pd.DataFrame(orders)



last_status_notify_time = 0

# 主任务：获取数据、生成订单并写入Excel
def run_main_task():
    global last_status_notify_time
    output_file = "ETH_动态挂单表.xlsx"
    investment_amount = 5000  # 投资资金
    leverage = 10  # 杠杆倍数

    logging.info("正在获取实时市场数据...")
    data = get_binance_data()
    if data:
        logging.info(f"当前价格: {data['current_price']}")

        df = generate_order_table(data, investment_amount, leverage)

        if df.empty:
            logging.info("当前无满足条件的交易信号，不生成新表。")
            # 每小时通知一次无信号状态
            current_time = time.time()
            if current_time - last_status_notify_time > 3600:
                try:
                    requests.post("http://localhost:5001/notify_status")
                    logging.info("已发送无交易机会的状态通知。")
                    last_status_notify_time = current_time
                except Exception as e:
                    logging.error(f"发送状态通知失败: {e}")
            return

        try:
            book = openpyxl.load_workbook(output_file)
            while len(book.sheetnames) >= 2:
                oldest_sheet_name = book.sheetnames[0]
                if oldest_sheet_name != 'Init':
                    book.remove(book[oldest_sheet_name])
                    logging.info(f"🗑️ 已删除最旧的工作表: {oldest_sheet_name}")
                else: # 如果最旧的是Init，则删除下一个
                    if len(book.sheetnames) > 1:
                        book.remove(book[book.sheetnames[1]])
                        logging.info(f"🗑️ 已删除最旧的工作表: {book.sheetnames[1]}")
            book.save(output_file)
        except FileNotFoundError:
            pass

        sheet_name = datetime.now().strftime('%Y-%m-%d %H_%M')
        with pd.ExcelWriter(output_file, engine='openpyxl', mode='a') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column].width = adjusted_width
        logging.info(f"📈 新的挂单表已生成: {sheet_name}")
        # 触发策略通知
        try:
            requests.post("http://localhost:5001/notify_order_strategy", params={"file": output_file})
            logging.info("已触发策略通知")
        except Exception as e:
            logging.error(f"触发策略通知失败: {e}")

# 主程序入口
if __name__ == "__main__":
    output_file = "ETH_动态挂单表.xlsx"
    try:
        book = openpyxl.load_workbook(output_file)
        if not book.sheetnames or 'Init' not in book.sheetnames:
            book.create_sheet("Init", 0)
            book.save(output_file)
    except FileNotFoundError:
        book = openpyxl.Workbook()
        book.create_sheet("Init", 0)
        book.save(output_file)
    
    logging.info("✅ 实时监控已启动，每15分钟执行一次策略分析。")

    while True:
        try:
            run_main_task()
            logging.info("本次任务执行完毕，等待15分钟后再次运行...")
            time.sleep(900)  # 等待15分钟
        except KeyboardInterrupt:
            logging.info("程序被用户中断。")
            break
        except Exception as e:
            logging.error(f"程序发生未知错误: {e}")
            logging.info("发生错误，等待5分钟后重试...")
            time.sleep(300) # 发生错误时，等待5分钟再重试
