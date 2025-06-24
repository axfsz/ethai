import requests
import logging
import openpyxl

output_file = "ETH_动态挂单表.xlsx"

# 触发策略通知
try:
    requests.post("http://localhost:5001/notify_order_strategy", params={"file": output_file})
    logging.info("已触发策略通知")
except Exception as e:
    logging.error(f"触发策略通知失败: {e}")

# 主程序入口
if __name__ == "__main__":
    try:
        book = openpyxl.load_workbook(output_file)
        if not book.sheetnames or 'Init' not in book.sheetnames:
            book.create_sheet("Init", 0)
            book.save(output_file)
    except FileNotFoundError:
        book = openpyxl.Workbook()
        book.create_sheet("Init", 0)
        book.save(output_file)
