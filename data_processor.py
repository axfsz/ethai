import pandas as pd
import ta
from typing import Dict, List

class DataProcessor:
    def __init__(self):
        self.symbol = 'ETH/USDT'
        
    def fetch_ohlcv(self, exchange, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """获取K线数据"""
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
        df['macd'], df['macdsignal'], _ = ta.trend.macd(df['close'])
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        bb = ta.volatility.BollingerBands(df['close'])
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()
        return df
        
    def get_all_timeframes_data(self, exchange) -> Dict[str, pd.DataFrame]:
        """获取所有时间周期的数据"""
        timeframes = {
            '1w': 60,
            '1d': 180,
            '4h': 200,
            '1h': 120
        }
        
        data = {}
        for timeframe, limit in timeframes.items():
            df = self.fetch_ohlcv(exchange, self.symbol, timeframe, limit)
            df = self.calculate_indicators(df)
            data[timeframe] = df
        
        return data
