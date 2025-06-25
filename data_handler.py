import pandas as pd
import ta
from typing import Dict, List
from dataclasses import dataclass

class Signal:
    def __init__(self, name: str, strength: int, timeframe: str):
        self.name = name
        self.strength = strength
        self.timeframe = timeframe

class DataHandler:
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
        
    def detect_macd_signals(self, df: pd.DataFrame, timeframe: str) -> List[Signal]:
        """检测MACD信号"""
        signals = []
        
        # 检查MACD金叉
        if df['macd'].iloc[-1] > df['macdsignal'].iloc[-1] and df['macd'].iloc[-2] <= df['macdsignal'].iloc[-2]:
            signals.append(Signal('MACD Bullish', 2, timeframe))
        elif df['macd'].iloc[-1] < df['macdsignal'].iloc[-1] and df['macd'].iloc[-2] >= df['macdsignal'].iloc[-2]:
            signals.append(Signal('MACD Bearish', 2, timeframe))
            
        return signals
        
    def detect_rsi_signals(self, df: pd.DataFrame, timeframe: str) -> List[Signal]:
        """检测RSI信号"""
        signals = []
        
        # 检查RSI背离
        if df['rsi'].iloc[-1] > 70 and df['close'].iloc[-1] < df['close'].iloc[-2]:
            signals.append(Signal('RSI Bearish Divergence', 3, timeframe))
        elif df['rsi'].iloc[-1] < 30 and df['close'].iloc[-1] > df['close'].iloc[-2]:
            signals.append(Signal('RSI Bullish Divergence', 3, timeframe))
            
        return signals
        
    def detect_volume_signals(self, df: pd.DataFrame, timeframe: str) -> List[Signal]:
        """检测成交量信号"""
        signals = []
        
        # 检查成交量突破
        if df['volume'].iloc[-1] > 1.5 * df['volume_ma'].iloc[-1] and df['close'].iloc[-1] > df['close'].iloc[-2]:
            signals.append(Signal('Volume Breakout', 2, timeframe))
            
        return signals
        
    def detect_all_signals(self, df: pd.DataFrame, timeframe: str) -> List[Signal]:
        """检测所有信号"""
        signals = []
        signals.extend(self.detect_macd_signals(df, timeframe))
        signals.extend(self.detect_rsi_signals(df, timeframe))
        signals.extend(self.detect_volume_signals(df, timeframe))
        return signals
