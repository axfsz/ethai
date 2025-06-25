from dataclasses import dataclass
from typing import List, Dict
from .config import config
from .signal import Signal

class Strategy:
    def __init__(self, signals: List[Signal], timeframe: str):
        self.signals = signals
        self.timeframe = timeframe
        self.position_size = self.calculate_position_size()
        self.risk_reward_ratio = self.calculate_risk_reward()
        
    def calculate_position_size(self) -> float:
        """Calculate position size based on signal strength"""
        signal_count = len(self.signals)
        
        if signal_count >= config.MIN_SIGNALS_FOR_HEAVY_POSITION:
            return config.POSITION_SIZES['heavy'][0]
        elif signal_count >= 2:
            return config.POSITION_SIZES['medium'][0]
        else:
            return config.POSITION_SIZES['light'][0]
            
    def calculate_risk_reward(self) -> float:
        """Calculate risk/reward ratio"""
        # This is a placeholder - actual implementation would require more context
        return 3.0  # Minimum required ratio
        
    def is_valid(self) -> bool:
        """Check if strategy meets minimum requirements"""
        return self.risk_reward_ratio >= config.MIN_RISK_REWARD_RATIO

class StrategyGenerator:
    def __init__(self):
        self.strategies = []
        
    def generate_strategy(self, signals: List[Signal], timeframe: str) -> Optional[Strategy]:
        """Generate a trading strategy based on signals"""
        strategy = Strategy(signals, timeframe)
        if strategy.is_valid():
            return strategy
        return None
