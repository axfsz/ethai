import os
from dataclasses import dataclass

@dataclass
class Config:
    # Telegram Bot settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Exchange settings
    EXCHANGE = 'binance'
    CCXT_API_KEY = os.getenv('CCXT_API_KEY', '')
    CCXT_SECRET_KEY = os.getenv('CCXT_SECRET_KEY', '')
    CCXT_PROXY = os.getenv('CCXT_PROXY') # Set to your proxy URL if needed, e.g., 'http://127.0.0.1:7890'

    # Trading settings
    SYMBOL = os.getenv('SYMBOL', 'ETH/USDT')

    # Scheduler settings
    SCHEDULE_MINUTES = int(os.getenv('SCHEDULE_MINUTES', '5'))
    
    # Timeframes
    TIMEFRAMES = {
        '1h': '1h',
        '4h': '4h',
        '1d': '1d',
        '1w': '1w'
    }
    
    # Signal thresholds
    MIN_SIGNALS_FOR_HEAVY_POSITION = 3
    MIN_RISK_REWARD_RATIO = 3.0
    
    # Position sizing
    POSITION_SIZES = {
        'light': (0.01, 0.02),  # 1%-2%
        'medium': (0.03, 0.05), # 3%-5%
        'heavy': (0.05, 0.08)   # 5%-8%
    }
    
    # API settings
    API_HOST = '0.0.0.0'
    API_PORT = 5000
    API_DEBUG = True

config = Config()
