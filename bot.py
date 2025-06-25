import ccxt
import pandas as pd
from flask import Flask, request, jsonify
from .config import config
from .chan import ChanCore
from .signal import SignalDetector
from .strategy import StrategyGenerator

app = Flask(__name__)
chan_core = ChanCore()
signal_detector = SignalDetector()
strategy_generator = StrategyGenerator()

@app.route('/predict_strategy', methods=['POST'])
def predict_strategy():
    """Predict trading strategy based on current market conditions"""
    try:
        # Get market data for all timeframes
        exchange = ccxt.binance()
        symbol = 'ETH/USDT'
        
        klines = {}
        for timeframe in config.TIMEFRAMES.values():
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            klines[timeframe] = df
            
        # Detect signals for each timeframe
        all_signals = []
        for timeframe, df in klines.items():
            signals = signal_detector.detect_all_signals(df, timeframe)
            all_signals.extend(signals)
            
        # Generate strategy
        strategy = strategy_generator.generate_strategy(all_signals, '1h')
        
        if strategy:
            return jsonify({
                'signals': [s.name for s in all_signals],
                'position_size': strategy.position_size,
                'risk_reward_ratio': strategy.risk_reward_ratio
            })
        else:
            return jsonify({'message': 'No valid strategy found'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host=config.API_HOST, port=config.API_PORT, debug=config.API_DEBUG)
