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

        # 根据k.md，获取多个时间框架的K线数据
        # 日线数据，用于判断主趋势
        kline_url_1d = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=1d&limit=30"
        klines_1d = requests.get(kline_url_1d).json()

        # 4小时数据，用于识别波段结构
        kline_url_4h = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=4h&limit=200"
        klines_4h = requests.get(kline_url_4h).json()

        # 15分钟数据，用于精确入场
        kline_url_15m = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=15m&limit=50"
        klines_15m = requests.get(kline_url_15m).json()

        return {
            "current_price": current_price,
            "klines_1d": klines_1d,
            "klines_4h": klines_4h,
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

def create_order(name, direction, trigger, order_price, sl, tp, investment, leverage, remark):
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
        "备注": remark
    }

# 动态生成挂单表 (重构版)
def generate_order_table(market_data, investment_amount, leverage):
    current_price = market_data['current_price']
    klines_1d = market_data['klines_1d']
    klines_4h = market_data['klines_4h']
    klines_15m = market_data['klines_15m']

    # --- 1. 多周期分析 --- 
    # 日线级别: 判断主趋势 (EMA20)
    closes_1d = [float(k[4]) for k in klines_1d]
    ema20_1d = calc_ema(closes_1d, 20)[-1]
    main_trend = "多头" if current_price > ema20_1d else "空头"

    # 4小时级别: 识别波浪结构和关键位
    highs_4h = [float(k[2]) for k in klines_4h]
    lows_4h = [float(k[3]) for k in klines_4h]
    swing_highs, swing_lows = detect_swings(klines_4h)
    last_high = swing_highs[-1][1] if swing_highs else max(highs_4h)
    last_low = swing_lows[-1][1] if swing_lows else min(lows_4h)
    swing_range = abs(last_high - last_low)

    # 15分钟级别: 精确入场信号 (成交量)
    volumes_15m = [float(k[5]) for k in klines_15m]
    avg_volume_15m = np.mean(volumes_15m[-20:])
    is_volume_breakout = volumes_15m[-1] > avg_volume_15m * 1.5

    # --- 2. 策略决策: 趋势黄金三角 (波浪+EMA+放量) ---
    # 精确波段分析
    wave_analysis = "结构不明"
    if main_trend == "多头":
        if swing_lows and current_price > swing_lows[-1][1]:
            if len(swing_lows) > 1 and swing_lows[-1][1] > swing_lows[-2][1]:
                wave_analysis = f"上升趋势延续，形成更高低点({swing_lows[-1][1]:.2f})，确认支撑。"
            else:
                wave_analysis = f"价格在关键支撑({last_low:.2f})上方运行，可能启动新一轮上涨。"
        else:
            wave_analysis = f"处于回调阶段，关注下方支撑({last_low:.2f})的有效性。"
    elif main_trend == "空头":
        if swing_highs and current_price < swing_highs[-1][1]:
            if len(swing_highs) > 1 and swing_highs[-1][1] < swing_highs[-2][1]:
                wave_analysis = f"下降趋势延续，形成更低高点({swing_highs[-1][1]:.2f})，确认阻力。"
            else:
                wave_analysis = f"价格在关键阻力({last_high:.2f})下方运行，可能启动新一轮下跌。"
        else:
            wave_analysis = f"处于反弹阶段，关注上方阻力({last_high:.2f})的有效性。"

    # --- 3. 生成交易订单 --- 
    orders = []
    # 买入策略: 主趋势多头 + 4H回调结束 + 15M放量突破
    if main_trend == "多头" and is_volume_breakout:
        # 修正逻辑: 追多时，触发价 > 挂单价，止损价 < 挂单价
        buy_order_price = round(current_price * (1 - 0.001), 2) # 挂单价比现价稍低
        buy_trigger_price = round(current_price * (1 + 0.001), 2) # 触发价比现价稍高
        stop_loss_price = round(last_low * 0.995, 2) # 止损设置在波段低点下方
        risk_amount = buy_order_price - stop_loss_price
        take_profit_price = round(buy_order_price + risk_amount * 3, 2)

        buy_remark = (
            f"主趋势分析: {main_trend}，日线EMA20之上，市场强势。|"
            f"波段结构分析: {wave_analysis}|"
            f"入场信号分析: 15分钟线出现显著放量({volumes_15m[-1]:.0f} > {avg_volume_15m*1.5:.0f})，动能增强。|"
            f"核心策略: 趋势黄金三角 (多周期共振)。|"
            f"风险评估: 盈亏比大于3:1，止损设置于关键结构位下方，风险可控。"
        )
        orders.append(create_order("ETH趋势追多", "BUY", buy_trigger_price, buy_order_price, stop_loss_price, take_profit_price, investment_amount, leverage, buy_remark))

    # 卖出策略: 主趋势空头 + 4H反弹结束 + 15M放量突破
    if main_trend == "空头" and is_volume_breakout:
        # 修正逻辑: 追空时，触发价 < 挂单价，止损价 > 挂单价
        sell_order_price = round(current_price * (1 + 0.001), 2) # 挂单价比现价稍高
        sell_trigger_price = round(current_price * (1 - 0.001), 2) # 触发价比现价稍低
        stop_loss_price = round(last_high * 1.005, 2) # 止损设置在波段高点上方
        risk_amount = stop_loss_price - sell_order_price
        take_profit_price = round(sell_order_price - risk_amount * 3, 2)

        sell_remark = (
            f"主趋势分析: {main_trend}，日线EMA20之下，市场弱势。|"
            f"波段结构分析: {wave_analysis}|"
            f"入场信号分析: 15分钟线出现显著放量({volumes_15m[-1]:.0f} > {avg_volume_15m*1.5:.0f})，动能增强。|"
            f"核心策略: 趋势黄金三角 (多周期共振)。|"
            f"风险评估: 盈亏比大于3:1，止损设置于关键结构位上方，风险可控。"
        )
        orders.append(create_order("ETH趋势追空", "SELL", sell_trigger_price, sell_order_price, stop_loss_price, take_profit_price, investment_amount, leverage, sell_remark))

    return pd.DataFrame(orders)



import schedule
import time
from threading import Thread

# 定时任务函数
def scheduled_task():
    output_file = "ETH_动态挂单表.xlsx"
    investment_amount = 5000  # 在此设置您的投资资金（即头寸总价值）
    leverage = 10  # 在此设置您的杠杆倍数

    logging.info("正在获取实时市场数据...")
    data = get_binance_data()
    if data:
        logging.info(f"当前价格: {data['current_price']}")

        # 生成新的挂单表 DataFrame
        df = generate_order_table(data, investment_amount, leverage)

        # 管理Excel工作表，只保留最近两个
        try:
            book = openpyxl.load_workbook(output_file)
            # 当工作表数量达到或超过2个时，删除最旧的，以保持最多2个
            while len(book.sheetnames) >= 2:
                oldest_sheet_name = book.sheetnames[0]
                book.remove(book[oldest_sheet_name])
                logging.info(f"🗑️ 已删除最旧的工作表: {oldest_sheet_name}")
            book.save(output_file)
        except FileNotFoundError:
            # 如果文件不存在，后续的ExcelWriter会自动创建
            pass

        # 使用追加模式写入新的工作表
        with pd.ExcelWriter(output_file, engine='openpyxl', mode='a', if_sheet_exists='new') as writer:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sheet_name = f"挂单_{timestamp}"
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            # --- 开始格式化 ---
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]

            # 定义样式
            font_remark = Font(name='仿宋', size=12, bold=True, color='008000') # 绿色
            align_remark = Alignment(horizontal='left', vertical='center', wrap_text=True)

            font_default = Font(name='宋体', size=11, bold=True)
            align_default = Alignment(horizontal='center', vertical='center')

            # 找到备注列的索引 (从1开始)
            remark_col_idx = -1
            for i, col_name in enumerate(df.columns):
                if col_name == '备注':
                    remark_col_idx = i + 1
                    break

            # 应用样式到表头和数据行
            for row in worksheet.iter_rows():
                for cell in row:
                    if cell.column == remark_col_idx:
                        cell.font = font_remark
                        cell.alignment = align_remark
                    else:
                        cell.font = font_default
                        cell.alignment = align_default
            
            # 调整列宽
            for i, column_cells in enumerate(worksheet.columns):
                col_letter = openpyxl.utils.get_column_letter(i + 1)
                if i + 1 == remark_col_idx:
                    worksheet.column_dimensions[col_letter].width = 80
                else:
                    worksheet.column_dimensions[col_letter].width = 15

            logging.info(f"✅ 已生成并格式化新的挂单表: {sheet_name}")
            
            # 触发通知脚本
            try:
                requests.post("http://localhost:5001/notify_order_strategy", params={"file": output_file})
                logging.info("✅ 已触发策略通知")
            except Exception as e:
                logging.error(f"❌ 触发策略通知失败: {e}")

    else:
        logging.error("❌ 获取市场数据失败，未生成挂单表")

# 定时任务主循环
def main():
    logging.info("服务启动，立即执行一次初始任务...")
    scheduled_task()  # 启动时立即执行一次

    schedule.every(1).hour.do(scheduled_task)
    logging.info("定时任务已设置为每小时执行一次。")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# 主逻辑
if __name__ == "__main__":
    logging.info("✅ 定时策略服务已启动，每小时自动分析市场行情并生成策略")
    logging.info("按 Ctrl+C 退出...")
    try:
        main()
    except KeyboardInterrupt:
        logging.info("\n服务已停止")
