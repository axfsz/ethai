from dataclasses import dataclass, field
from typing import Dict, List, Any

# 导入我们全新的缠论分析引擎
from chan import ChanAnalyzer, BuySellPoint

@dataclass
class Signal:
    """标准化的信号数据结构"""
    name: str
    type: str  # 'bullish', 'bearish', 'neutral'
    description: str
    source: str # 'MACD', 'RSI', 'Volume', 'BBands', 'Chan'

class SignalDetector:
    """信号检测器，现在集成了缠论分析"""
    def __init__(self):
        self.chan_analyzer = ChanAnalyzer()

    def detect_all_signals(self, timeframe: str, indicators: Dict[str, Any], ohlcv: List[List[Any]]) -> List[Signal]:
        """检测所有来源的信号，包括缠论信号"""
        signals = []
        signals.extend(self.detect_macd_signals(timeframe, indicators))
        signals.extend(self.detect_rsi_signals(timeframe, indicators))
        signals.extend(self.detect_volume_signals(timeframe, indicators, ohlcv))
        signals.extend(self.detect_bollinger_bands_signals(timeframe, indicators))
        
        # 新增：调用缠论信号检测
        signals.extend(self.detect_chan_signals(timeframe, indicators, ohlcv))

        return signals

    def detect_chan_signals(self, timeframe: str, indicators: Dict[str, Any], ohlcv: List[List[Any]]) -> List[Signal]:
        """从缠论结构中检测买卖点信号"""
        chan_signals = []
        macd_hist = indicators.get('macd_hist', [])
        if not macd_hist or not ohlcv:
            return chan_signals

        # 使用完整的分析流程
        try:
            _strokes, _segments, _centers, buy_sell_points = self.chan_analyzer.analyze(ohlcv, macd_hist)
            
            for point in buy_sell_points:
                if point.point_type == '1st_buy':
                    chan_signals.append(Signal(
                        name=f"{timeframe} 缠论一类买点",
                        type='bullish',
                        description=f"在 {point.time} 出现缠论第一类买点，价格约为 {point.price:.2f}，由盘整背驰引发。",
                        source='Chan'
                    ))
                elif point.point_type == '1st_sell':
                    chan_signals.append(Signal(
                        name=f"{timeframe} 缠论一类卖点",
                        type='bearish',
                        description=f"在 {point.time} 出现缠论第一类卖点，价格约为 {point.price:.2f}，由盘整背驰引发。",
                        source='Chan'
                    ))
        except Exception as e:
            # 在分析过程中可能会有各种异常，例如数据不足等，这里暂时只打印
            print(f"Error during Chan analysis on {timeframe}: {e}")

        return chan_signals

    def detect_macd_signals(self, timeframe: str, indicators: Dict[str, Any]) -> List[Signal]:
        """检测MACD信号"""
        # ... (以下代码保持不变)
        signals = []
        macd = indicators.get('macd', [])
        signal_line = indicators.get('signal_line', [])
        if len(macd) < 2 or len(signal_line) < 2:
            return signals

        # 金叉
        if macd[-2] < signal_line[-2] and macd[-1] > signal_line[-1]:
            signals.append(Signal(name=f"{timeframe} MACD金叉", type='bullish', description="MACD快线上穿慢线", source='MACD'))
        # 死叉
        if macd[-2] > signal_line[-2] and macd[-1] < signal_line[-1]:
            signals.append(Signal(name=f"{timeframe} MACD死叉", type='bearish', description="MACD快线下穿慢线", source='MACD'))
        return signals

    def detect_rsi_signals(self, timeframe: str, indicators: Dict[str, Any]) -> List[Signal]:
        """检测RSI信号"""
        signals = []
        rsi = indicators.get('rsi', [])
        if not rsi:
            return signals
        
        if rsi[-1] > 70:
            signals.append(Signal(name=f"{timeframe} RSI超买", type='bearish', description=f"RSI值为 {rsi[-1]:.2f}，进入超买区", source='RSI'))
        if rsi[-1] < 30:
            signals.append(Signal(name=f"{timeframe} RSI超卖", type='bullish', description=f"RSI值为 {rsi[-1]:.2f}，进入超卖区", source='RSI'))
        return signals

    def detect_volume_signals(self, timeframe: str, indicators: Dict[str, Any], ohlcv: List[List[Any]]) -> List[Signal]:
        """检测成交量信号"""
        signals = []
        if len(ohlcv) < 20:
            return signals
        
        volumes = [x[5] for x in ohlcv]
        avg_volume = sum(volumes[-20:-1]) / 19
        last_volume = volumes[-1]
        last_close = ohlcv[-1][4]
        prev_close = ohlcv[-2][4]

        if last_volume > avg_volume * 2:
            if last_close > prev_close:
                signals.append(Signal(name=f"{timeframe} 放量上涨", type='bullish', description="成交量显著放大，价格上涨", source='Volume'))
            else:
                signals.append(Signal(name=f"{timeframe} 放量下跌", type='bearish', description="成交量显著放大，价格下跌", source='Volume'))
        return signals

    def detect_bollinger_bands_signals(self, timeframe: str, indicators: Dict[str, Any]) -> List[Signal]:
        """检测布林带信号"""
        signals = []
        bandwidth = indicators.get('bandwidth', [])
        close_prices = indicators.get('close', [])
        upper_band = indicators.get('upper_band', [])
        lower_band = indicators.get('lower_band', [])

        if len(bandwidth) < 2 or len(close_prices) < 1:
            return signals

        # 收口后突破
        if bandwidth[-2] < 0.05: # 带宽小于5%视为收口
            if close_prices[-1] > upper_band[-1]:
                signals.append(Signal(name=f"{timeframe} 布林带收口后向上突破", type='bullish', description="价格在布林带收口后突破上轨", source='BBands'))
            elif close_prices[-1] < lower_band[-1]:
                signals.append(Signal(name=f"{timeframe} 布林带收口后向下突破", type='bearish', description="价格在布林带收口后突破下轨", source='BBands'))
        return signals

            
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
