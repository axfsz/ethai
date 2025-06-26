import time
import schedule
from config import load_config
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
    
    config = load_config()
    
    try:
        db_manager = DatabaseManager()
    except ValueError as e:
        logger.critical(f"CRITICAL: Failed to initialize DatabaseManager. Bot cannot start. Error: {e}", exc_info=True)
        return

    data_processor = SimpleDataProcessor(config, db_manager)
    signal_detector = SignalDetector()
    strategy_notifier = StrategyNotifier(config.get('telegram', {}))

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
            for timeframe in config['timeframes']:
                # Query a long history for more accurate analysis (e.g., 30 days).
                # Chan theory and other indicators benefit greatly from more context.
                historical_df = db_manager.query_ohlcv_data(
                    measurement=timeframe, 
                    symbol=config['symbol'], 
                    time_range_start="-30d"
                )
                
                if historical_df.empty or len(historical_df) < 100: # Ensure enough data for analysis
                    logger.warning(f"Not enough historical data for {timeframe} (found {len(historical_df)}). Skipping analysis.")
                    continue
                
                logger.info(f"Detecting signals for {timeframe} using {len(historical_df)} data points from DB...")
                signals = signal_detector.detect_all_signals(historical_df)
                all_signals[timeframe] = signals
            
            # Step 3: Generate and send notifications if any signals were found.
            logger.info("[WORKFLOW] Step 3: Generating strategy and notifying.")
            if any(s for s in all_signals.values() if s):
                strategy_notifier.generate_and_notify_strategy(all_signals)
            else:
                logger.info("No trading signals detected across all timeframes.")
            logger.info("------------------- Scheduled Job Finished -------------------")

        except Exception as e:
            logger.error(f"An critical error occurred in the main job: {e}", exc_info=True)

    # --- Scheduler Setup ---
    schedule_minutes = config.get('schedule_minutes', 5)
    schedule.every(schedule_minutes).minutes.do(job)
    logger.info(f"Job scheduled to run every {schedule_minutes} minutes.")

    # Run the job immediately at startup, then enter the main loop.
    logger.info("Running initial job at startup...")
    job()

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
