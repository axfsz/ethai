import ccxt
import pandas as pd
from typing import Dict
from logging_config import logger
from database_manager import DatabaseManager

class SimpleDataProcessor:
    """Purely responsible for fetching data from the exchange and storing it in InfluxDB."""

    def __init__(self, config: Dict, db_manager: DatabaseManager):
        """Initializes the data processor with exchange configuration and a database manager instance."""
        self.exchange = self._init_exchange(config['exchange'])
        self.symbol = config['symbol']
        self.timeframes = config['timeframes']
        self.db_manager = db_manager
        logger.info("SimpleDataProcessor initialized.")

    def _init_exchange(self, exchange_config: Dict) -> ccxt.Exchange:
        """Initializes the ccxt exchange instance."""
        exchange_class = getattr(ccxt, exchange_config['name'])
        exchange = exchange_class({
            'apiKey': exchange_config['apiKey'],
            'secret': exchange_config['secret'],
            'options': {
                'defaultType': 'swap',
            },
        })
        if exchange_config.get('proxy'):
            exchange.proxies = {'http': exchange_config['proxy'], 'https': exchange_config['proxy']}
        logger.info(f"CCXT exchange '{exchange_config['name']}' initialized.")
        return exchange

    def fetch_and_store_ohlcv_data(self):
        """Fetches OHLCV data for all configured timeframes and stores it in InfluxDB."""
        for timeframe in self.timeframes:
            try:
                logger.info(f"Fetching OHLCV data for {self.symbol} with timeframe {timeframe}...")
                # Fetch a reasonable number of recent candles to ensure data continuity
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=500)
                
                if not ohlcv:
                    logger.warning(f"No data returned for {self.symbol} with timeframe {timeframe}.")
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # The database manager handles the data writing
                self.db_manager.write_ohlcv_data(measurement=timeframe, data=df, symbol=self.symbol)
                
            except Exception as e:
                logger.error(f"Error fetching or storing data for {timeframe}: {e}", exc_info=True)
