from typing import Dict, List, Tuple
import statistics

class SimpleDataProcessor:
    def __init__(self):
        self.symbol = 'ETH/USDT'
        
    def fetch_ohlcv(self, exchange, symbol: str, timeframe: str, limit: int) -> List[Tuple]:
        """获取K线数据"""
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        return ohlcv
        
    def calculate_indicators(self, ohlcv: List[Tuple]) -> Dict[str, List[float]]:
        """计算技术指标"""
        close_prices = [float(x[4]) for x in ohlcv]
        volumes = [float(x[5]) for x in ohlcv]
        
        # 计算EMA20
        ema20 = self.calculate_ema(close_prices, 20)
        
        # 计算MACD
        macd, macdsignal = self.calculate_macd(close_prices)
        
        # 计算RSI
        rsi = self.calculate_rsi(close_prices, 14)
        
        # 计算成交量均线
        volume_ma = self.calculate_ma(volumes, 20)

        # 计算布林带
        bb_upper, bb_middle, bb_lower, bb_width = self.calculate_bollinger_bands(close_prices)
        
        return {
            'close': close_prices,
            'macd': macd,
            'macdsignal': macdsignal,
            'rsi': rsi,
            'volume': volumes,
            'volume_ma': volume_ma,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'bb_width': bb_width
        }
        
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """计算EMA"""
        multiplier = 2 / (period + 1)
        ema = []
        if len(prices) >= period:
            ema.append(sum(prices[:period]) / period)
            for price in prices[period:]:
                ema.append((price - ema[-1]) * multiplier + ema[-1])
        return ema
        
    def calculate_macd(self, prices: List[float]) -> Tuple[List[float], List[float]]:
        """计算MACD"""
        fast_ema = self.calculate_ema(prices, 12)
        slow_ema = self.calculate_ema(prices, 26)
        macd = []
        macdsignal = []
        
        if len(fast_ema) >= len(slow_ema):
            for i in range(len(slow_ema)):
                macd.append(fast_ema[i] - slow_ema[i])
            
            macdsignal = self.calculate_ema(macd, 9)
        
        return macd, macdsignal
        
    def calculate_rsi(self, prices: List[float], period: int) -> List[float]:
        """计算RSI"""
        rsi = []
        if len(prices) >= period:
            gains = []
            losses = []
            
            # 计算第一个RSI
            first_gain = sum([x for x in prices[1:period] if x > prices[0]])
            first_loss = sum([x for x in prices[1:period] if x < prices[0]])
            avg_gain = first_gain / period
            avg_loss = first_loss / period
            
            rsi.append(100 - (100 / (1 + avg_gain / avg_loss)))
            
            # 计算后续RSI
            for i in range(period, len(prices)):
                gain = prices[i] - prices[i-1] if prices[i] > prices[i-1] else 0
                loss = abs(prices[i] - prices[i-1]) if prices[i] < prices[i-1] else 0
                
                avg_gain = ((avg_gain * (period - 1)) + gain) / period
                avg_loss = ((avg_loss * (period - 1)) + loss) / period
                
                rsi.append(100 - (100 / (1 + avg_gain / avg_loss)))
        
        return rsi
        
    def calculate_ma(self, values: List[float], period: int) -> List[float]:
        """计算简单移动平均"""
        ma = []
        if len(values) >= period:
            for i in range(len(values) - period + 1):
                ma.append(sum(values[i:i+period]) / period)
        return ma

    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: int = 2) -> Tuple[List[float], List[float], List[float], List[float]]:
        """计算布林带指标"""
        upper_band = []
        middle_band = []
        lower_band = []
        bandwidth = []
        if len(prices) >= period:
            middle_band = self.calculate_ma(prices, period)
            
            stdevs = []
            for i in range(len(prices) - period + 1):
                window = prices[i:i+period]
                stdevs.append(statistics.stdev(window))
            
            for i in range(len(middle_band)):
                upper = middle_band[i] + (stdevs[i] * std_dev)
                lower = middle_band[i] - (stdevs[i] * std_dev)
                upper_band.append(upper)
                lower_band.append(lower)
                if middle_band[i] != 0:
                    bandwidth.append((upper - lower) / middle_band[i])
                else:
                    bandwidth.append(0)

        return upper_band, middle_band, lower_band, bandwidth
        
    def get_all_timeframes_data(self, exchange) -> Dict[str, Dict[str, List[float]]]:
        """获取所有时间周期的数据"""
        timeframes = {
            '1w': 60,
            '1d': 180,
            '4h': 200,
            '1h': 120
        }
        
        data = {}
        for timeframe, limit in timeframes.items():
            ohlcv = self.fetch_ohlcv(exchange, self.symbol, timeframe, limit)
            indicators = self.calculate_indicators(ohlcv)
            data[timeframe] = indicators
        
        return data
