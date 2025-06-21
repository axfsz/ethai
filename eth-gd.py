import requests
import pandas as pd
import time
from datetime import datetime
import numpy as np
import openpyxl
from openpyxl.styles import Font, Alignment
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', filename='log.file', filemode='a')

# 获取币安 ETHUSDT 最新价格和K线数据
def get_binance_data():
    try:
        # 获取最新价格
        ticker_url = "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
        price_resp = requests.get(ticker_url).json()
        current_price = float(price_resp['price'])

        # 获取最近 50 根1分钟K线
        kline_url = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=1m&limit=50"
        kline_resp = requests.get(kline_url).json()

        closes = [float(candle[4]) for candle in kline_resp]

        ma5 = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / 20

        return {
            "current_price": current_price,
            "ma5": ma5,
            "ma20": ma20,
            "klines": kline_resp
        }

    except Exception as e:
        logging.error(f"获取数据失败: {e}")
        return None

# 缠论分型分析
def find_fractals(klines):
    if len(klines) < 3:
        return "K线数量不足，无法分析分型"

    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])

    # 顶分型: 中间K线的最高价是3根K线中最高的
    top_fractal = (highs[-2] > highs[-3]) and (highs[-2] > highs[-1])
    # 底分型: 中间K线的最低价是3根K线中最低的
    bottom_fractal = (lows[-2] < lows[-3]) and (lows[-2] < lows[-1])

    if top_fractal:
        return "缠论分析: 最近3根K线形成顶分型，可能看跌。"
    elif bottom_fractal:
        return "缠论分析: 最近3根K线形成底分型，可能看涨。"
    else:
        return "缠论分析: 未形成明显分型。"

# 动态生成挂单表
def generate_order_table(market_data, investment_amount, leverage):
    current_price = market_data['current_price']
    ma5 = market_data['ma5']
    ma20 = market_data['ma20']
    klines = market_data['klines']

    # 均线分析
    if ma5 > ma20:
        ma_analysis = "分析: MA5上穿MA20金叉，看涨。"
        ma_conclusion = "结论: 建议追多。"
    else:
        ma_analysis = "分析: MA5下穿MA20死叉，看跌。"
        ma_conclusion = "结论: 建议追空。"

    # 缠论分型分析
    fractal_analysis = find_fractals(klines)

    # 为不同策略生成独立的备注
    buy_remark = f"现价:{current_price:.2f}, MA5:{ma5:.2f}, MA20:{ma20:.2f}. 分析: MA5上穿MA20金叉，看涨。结论: 建议追多。{fractal_analysis}"
    sell_remark = f"现价:{current_price:.2f}, MA5:{ma5:.2f}, MA20:{ma20:.2f}. 分析: MA5下穿MA20死叉，看跌。结论: 建议追空。{fractal_analysis}"

    # --- Time Estimation ---
    buy_trigger_price = round(current_price * 1.04, 2)
    sell_trigger_price = round(current_price * 0.96, 2)
    time_to_buy_trigger = estimate_time_to_trigger(klines, current_price, buy_trigger_price)
    time_to_sell_trigger = estimate_time_to_trigger(klines, current_price, sell_trigger_price)

    # --- BUY Strategy Calculations ---
    buy_order_price = round(current_price * 1.04 + 5, 2)
    buy_stop_loss_price = round(buy_order_price * 0.98, 2)
    buy_loss_per_unit = buy_order_price - buy_stop_loss_price
    buy_take_profit_price = round(buy_order_price + (buy_loss_per_unit * 3), 2)
    # --- SELL Strategy Calculations ---
    sell_order_price = round(current_price * 0.96 - 5, 2)
    sell_stop_loss_price = round(sell_order_price * 1.02, 2)
    sell_loss_per_unit = sell_stop_loss_price - sell_order_price
    sell_take_profit_price = round(sell_order_price - (sell_loss_per_unit * 3), 2)

    # 使用Excel公式动态计算
    # H: 投资资金, D: 挂单价格, I: 杠杆倍数, F: 止盈价格, E: 止损价格
    buy_quantity_formula = f'=H2/D2'
    sell_quantity_formula = f'=H3/D3'

    buy_estimated_profit = f'=(F2-D2)*G2*I2'
    buy_estimated_loss = f'=(D2-E2)*G2*I2'
    sell_estimated_profit = f'=(D3-F3)*G3*I3'
    sell_estimated_loss = f'=(E3-D3)*G3*I3'

    orders = [
        {
            "策略名称": "ETH突破追多",
            "方向": "BUY",
            "触发价格": round(current_price * 1.04, 2),
            "挂单价格": buy_order_price,
            "止损价格": buy_stop_loss_price,
            "止盈价格": buy_take_profit_price,
            "数量": buy_quantity_formula,
            "投资资金": investment_amount,
            "杠杆倍数": leverage,
            "预计盈利": buy_estimated_profit,
            "预计亏损": buy_estimated_loss,
            "预计到达时间": time_to_buy_trigger,
            "备注": buy_remark
        },
        {
            "策略名称": "ETH突破追空",
            "方向": "SELL",
            "触发价格": round(current_price * 0.96, 2),
            "挂单价格": sell_order_price,
            "止损价格": sell_stop_loss_price,
            "止盈价格": sell_take_profit_price,
            "数量": sell_quantity_formula,
            "投资资金": investment_amount,
            "杠杆倍数": leverage,
            "预计盈利": sell_estimated_profit,
            "预计亏损": sell_estimated_loss,
            "预计到达时间": time_to_sell_trigger,
            "备注": sell_remark
        }
    ]

    return pd.DataFrame(orders)

# 预测到达触发价格的时间
def estimate_time_to_trigger(klines, current_price, trigger_price):
    if not klines or len(klines) < 10:
        return "数据不足"

    # 计算最近10根K线的平均波动幅度
    recent_klines = klines[-10:]
    avg_range = np.mean([float(k[2]) - float(k[3]) for k in recent_klines]) # high - low

    if avg_range == 0:
        return "市场无波动"

    price_diff = abs(trigger_price - current_price)
    estimated_minutes = price_diff / avg_range

    return f"约 {estimated_minutes:.1f} 分钟"

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
        logging.info(f"当前价格: {data['current_price']}, MA5: {data['ma5']:.2f}, MA20: {data['ma20']:.2f}")

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

# 定时任务线程
def run_scheduler():
    # 立即执行一次
    scheduled_task()
    
    # 设置每小时执行一次
    schedule.every(1).hours.do(scheduled_task)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# 主逻辑
if __name__ == "__main__":
    # 启动定时任务线程
    scheduler_thread = Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    logging.info("✅ 定时策略服务已启动，每两小时自动分析市场行情并生成策略")
    logging.info("按 Ctrl+C 退出...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("\n服务已停止")
