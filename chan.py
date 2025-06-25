import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass

class KLine:
    def __init__(self, open_price: float, high: float, low: float, close: float, volume: float):
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

class ChanCore:
    def __init__(self):
        self.klines: Dict[str, List[KLine]] = {}  # timeframe -> klines
        
    def add_klines(self, timeframe: str, klines: List[Dict]):
        """Add K-line data for a specific timeframe"""
        self.klines[timeframe] = [KLine(**k) for k in klines]
        
    def detect_bi(self, timeframe: str) -> Optional[List[KLine]]:
        """Detect bi (stroke) in K-lines"""
        if timeframe not in self.klines:
            return None
            
        klines = self.klines[timeframe]
        if len(klines) < 3:
            return None
            
        bis = []
        for i in range(0, len(klines) - 2, 2):
            if klines[i].close > klines[i+1].close and klines[i+2].close > klines[i+1].close:
                bis.append(klines[i+2])
            elif klines[i].close < klines[i+1].close and klines[i+2].close < klines[i+1].close:
                bis.append(klines[i+2])
        return bis
        
    def detect_duan(self, timeframe: str) -> Optional[List[KLine]]:
        """Detect duan (segment) in K-lines"""
        bis = self.detect_bi(timeframe)
        if not bis or len(bis) < 2:
            return None
            
        duans = []
        for i in range(0, len(bis) - 1):
            if bis[i].close < bis[i+1].close:
                duans.append(bis[i+1])
            elif bis[i].close > bis[i+1].close:
                duans.append(bis[i+1])
        return duans
        
    def detect_zhongshu(self, timeframe: str) -> Optional[List[float]]:
        """Detect zhongshu (central pivot)"""
        duans = self.detect_duan(timeframe)
        if not duans or len(duans) < 3:
            return None
            
        zhongshu = []
        for i in range(0, len(duans) - 2, 2):
            high = max(duans[i].high, duans[i+1].high, duans[i+2].high)
            low = min(duans[i].low, duans[i+1].low, duans[i+2].low)
            zhongshu.extend([low, high])
        return zhongshu
