import time
import schedule
from config import config
from simple_data_processor import SimpleDataProcessor
from signal_detector import SignalDetector
from strategy_notifier import StrategyNotifier
from database_manager import DatabaseManager
from logging_config import logger

def main():
    """Main function to initialize and run the trading bot."""
    logger.info("=========================================================")
    logger.info("===         Starting ChanTradeBot with InfluxDB       ===")
    logger.info("=========================================================")
    
    # Adapt the config object to the dictionary format expected by other modules.
    app_config = {
        'exchange': {
            'name': config.EXCHANGE,
            'apiKey': config.CCXT_API_KEY,
            'secret': config.CCXT_SECRET_KEY,
            'proxy': config.CCXT_PROXY
        },
        'symbol': config.SYMBOL,
        'timeframes': list(config.TIMEFRAMES.keys()),
        'telegram': {
            'token': config.TELEGRAM_BOT_TOKEN,
            'chat_id': config.TELEGRAM_CHAT_ID
        },
        'schedule_minutes': config.SCHEDULE_MINUTES
    }
    
    try:
        # Initialize DatabaseManager by passing config values directly (Dependency Injection).
        db_manager = DatabaseManager(
            url=config.INFLUXDB_URL,
            token=config.INFLUXDB_TOKEN,
            org=config.INFLUXDB_ORG,
            bucket=config.INFLUXDB_BUCKET
        )
    except ValueError as e:
        # This will catch the error if any of the required InfluxDB config values are missing from the environment.
        logger.critical(f"CRITICAL: Failed to initialize DatabaseManager. Bot cannot start. Error: {e}")
        logger.critical("Please ensure INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, and INFLUXDB_BUCKET are set correctly in docker-compose.yaml.")
        return

    data_processor = SimpleDataProcessor(app_config, db_manager)
    signal_detector = SignalDetector()
    strategy_notifier = StrategyNotifier(app_config.get('telegram', {}))

    def job():
        """The main job to be scheduled. Fetches, stores, and analyzes data."""
        logger.info("------------------- Running Scheduled Job -------------------")
        try:
            # Step 1: Fetch latest data and store it in InfluxDB.
            # This ensures our database is always up-to-date.
            logger.info("[WORKFLOW] Step 1: Fetching and storing latest market data.")
            data_processor.fetch_and_store_ohlcv_data()

            all_signals = {}
            # Step 2: For each timeframe, query a full history from the DB and analyze.
            logger.info("[WORKFLOW] Step 2: Querying historical data and detecting signals.")
            for timeframe in app_config['timeframes']:
                # Query a long history for more accurate analysis (e.g., 30 days).
                # Chan theory and other indicators benefit greatly from more context.
                historical_df = db_manager.query_ohlcv_data(
                    measurement=timeframe, 
                    symbol=app_config['symbol'], 
                    time_range_start="-30d"
                )
                
                if historical_df.empty or len(historical_df) < 100: # Ensure enough data for analysis
                    logger.warning(f"Not enough historical data for {timeframe} (found {len(historical_df)}). Skipping analysis.")
                    continue
                
                logger.info(f"Detecting signals for {timeframe} using {len(historical_df)} data points from DB...")
                # Convert DataFrame to the list of lists format expected by the detector
                ohlcv_list = historical_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
                # NOTE: Indicator calculation is not yet implemented. We are passing an empty dict for now.
                # The Chan analysis might still work if it calculates its own MACD internally.
                indicators = {}
                # Convert DataFrame to the list of lists format expected by the detector
                ohlcv_list = historical_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
                # NOTE: Indicator calculation is not yet implemented. We are passing an empty dict for now.
                # The Chan analysis might still work if it calculates its own MACD internally.
                indicators = {}
                signals = signal_detector.detect_all_signals(timeframe, indicators, ohlcv_list)
                all_signals[timeframe] = signals
            
            # Step 3: Generate and send notifications if any signals were found.
            logger.info("[WORKFLOW] Step 3: Generating strategy and notifying.")
            if any(s for s in all_signals.values() if s):
                strategy_notifier.notify(all_signals, symbol=app_config['symbol'])
            else:
                logger.info("No trading signals detected across all timeframes.")
            logger.info("------------------- Scheduled Job Finished -------------------")

        except Exception as e:
            logger.error(f"An critical error occurred in the main job: {e}", exc_info=True)

    # --- Scheduler Setup ---
    schedule.every(app_config['schedule_minutes']).minutes.do(job)
    logger.info(f"Job scheduled to run every {app_config['schedule_minutes']} minutes.")

    # Run the job immediately at startup, then enter the main loop.
    logger.info("Running initial job at startup...")
    job()

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
