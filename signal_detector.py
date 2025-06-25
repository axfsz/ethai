from dataclasses import dataclass
from typing import List, Dict, Any

class Signal:
    def __init__(self, name: str, strength: int, timeframe: str):
        self.name = name
        self.strength = strength
        self.timeframe = timeframe

class SignalDetector:
    def detect_macd_signals(self, data: Dict[str, Any], timeframe: str) -> List[Signal]:
        """检测MACD信号"""
        signals = []
        
        # 检查MACD金叉
        if data['macd'][-1] > data['macdsignal'][-1] and data['macd'][-2] <= data['macdsignal'][-2]:
            signals.append(Signal('MACD Bullish', 2, timeframe))
        elif data['macd'][-1] < data['macdsignal'][-1] and data['macd'][-2] >= data['macdsignal'][-2]:
            signals.append(Signal('MACD Bearish', 2, timeframe))
            
        return signals
        
    def detect_rsi_signals(self, data: Dict[str, Any], timeframe: str) -> List[Signal]:
        """检测RSI信号"""
        signals = []
        
        # 检查RSI背离
        if data['rsi'][-1] > 70 and data['close'][-1] < data['close'][-2]:
            signals.append(Signal('RSI Bearish Divergence', 3, timeframe))
        elif data['rsi'][-1] < 30 and data['close'][-1] > data['close'][-2]:
            signals.append(Signal('RSI Bullish Divergence', 3, timeframe))
            
        return signals
        
    def detect_volume_signals(self, data: Dict[str, Any], timeframe: str) -> List[Signal]:
        """检测成交量信号"""
        signals = []
        
        # 检查成交量突破
        if data['volume'][-1] > 1.5 * data['volume_ma'][-1] and data['close'][-1] > data['close'][-2]:
            signals.append(Signal('Volume Breakout', 2, timeframe))
            
        return signals
        
    def detect_bollinger_bands_signals(self, data: Dict[str, Any], timeframe: str) -> List[Signal]:
        """检测布林带收口突破信号"""
        signals = []
        
        # 检查布林带收口（带宽小于5%）后，价格突破上下轨
        if len(data.get('bb_width', [])) > 1 and len(data.get('close', [])) > 1:
            is_squeeze = data['bb_width'][-2] < 0.05
            
            if is_squeeze:
                if data['close'][-1] > data['bb_upper'][-1]:
                    signals.append(Signal('Bollinger Breakout Bullish', 2, timeframe))
                elif data['close'][-1] < data['bb_lower'][-1]:
                    signals.append(Signal('Bollinger Breakout Bearish', 2, timeframe))
                    
        return signals
        
    def detect_all_signals(self, data: Dict[str, Any], timeframe: str) -> List[Signal]:
        """检测所有信号"""
        signals = []
        signals.extend(self.detect_macd_signals(data, timeframe))
        signals.extend(self.detect_rsi_signals(data, timeframe))
        signals.extend(self.detect_volume_signals(data, timeframe))
        signals.extend(self.detect_bollinger_bands_signals(data, timeframe))
        return signals
