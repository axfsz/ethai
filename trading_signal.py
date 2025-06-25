import pandas as pd
from typing import List
from dataclasses import dataclass

class Signal:
    def __init__(self, name: str, strength: int, timeframe: str):
        self.name = name
        self.strength = strength
        self.timeframe = timeframe

class SignalDetector:
    def __init__(self):
        self.signals = []
        
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
