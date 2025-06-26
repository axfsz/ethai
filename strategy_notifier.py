import logging
from typing import Dict, Any
from telegram_notifier import TelegramNotifier

class StrategyNotifier:
    """
    Handles the formatting of signals into human-readable messages and 
    sends them via the Telegram notifier.
    """
    def __init__(self, telegram_config: Dict[str, Any]):
        """
        Initializes the StrategyNotifier with Telegram configuration.

        Args:
            telegram_config (Dict[str, Any]): A dictionary containing 'token' and 'chat_id'.
        """
        self.telegram_notifier = TelegramNotifier(
            token=telegram_config.get('token'),
            chat_id=telegram_config.get('chat_id')
        )
        logging.info("StrategyNotifier initialized.")

    def notify(self, signals: Dict[str, Any], symbol: str):
        """
        Formats and sends notifications based on detected signals for a specific symbol.

        Args:
            signals (Dict[str, Any]): The dictionary of detected signals from SignalDetector.
            symbol (str): The trading symbol (e.g., 'ETH/USDT') for which signals were detected.
        """
        if not self.telegram_notifier.is_configured():
            logging.warning("Telegram notifier is not configured. Skipping notification.")
            return

        message = self._format_message(signals, symbol)
        if message:
            logging.info(f"Sending notification for {symbol}...")
            self.telegram_notifier.send_message(message)
            logging.info("Notification sent successfully.")
        else:
            logging.info(f"No significant signals detected for {symbol}. No notification will be sent.")

    def _format_message(self, signals: Dict[str, Any], symbol: str) -> str:
        """
        Creates a formatted message from the signals dictionary.

        Args:
            signals (Dict[str, Any]): The dictionary of detected signals.
            symbol (str): The trading symbol to include in the message.

        Returns:
            str: A formatted message string, or an empty string if no signals are present.
        """
        if not signals or not any(signals.values()):
            return ""

        message_parts = [f"🔔 Trading Signal Alert for {symbol} 🔔\n"]
        has_signal = False
        for timeframe, signal_details in sorted(signals.items()):
            if signal_details:
                has_signal = True
                recommendation = signal_details.get('recommendation', 'Hold')
                confidence = signal_details.get('confidence', 'N/A')
                message_parts.append(f"📈 Timeframe: {timeframe}")
                message_parts.append(f"   - Action: {recommendation}")
                message_parts.append(f"   - Confidence: {confidence}\n")
        
        if not has_signal:
            return ""
            
        return "\n".join(message_parts)