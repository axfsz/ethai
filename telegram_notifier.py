import logging
import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

class TelegramNotifier:
    """
    A wrapper to send messages via the python-telegram-bot library.
    """
    def __init__(self, token: Optional[str], chat_id: Optional[str]):
        """
        Initializes the TelegramNotifier.

        Args:
            token (Optional[str]): The Telegram Bot token.
            chat_id (Optional[str]): The Telegram chat ID to send messages to.
        """
        self.token = token
        self.chat_id = chat_id
        self.bot = Bot(token=self.token) if self.token else None
        if self.is_configured():
            logging.info("TelegramNotifier initialized and configured.")
        else:
            logging.warning("TelegramNotifier initialized but not configured (token or chat_id is missing).")

    def is_configured(self) -> bool:
        """
        Checks if the notifier is fully configured with a token and chat_id.

        Returns:
            bool: True if both token and chat_id are set, False otherwise.
        """
        return bool(self.bot and self.chat_id)

    def send_message(self, message: str) -> bool:
        """
        Sends a message to the configured Telegram chat. This method is a sync wrapper
        around an async call.

        Args:
            message (str): The message text to send.

        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """
        if not self.is_configured():
            logging.error("Cannot send Telegram message: Notifier is not configured.")
            return False
        
        try:
            # Use asyncio.run to execute the async send_message method
            return asyncio.run(self._send_message_async(message))
        except Exception as e:
            logging.error(f"An unexpected error occurred when trying to send Telegram message: {e}")
            return False

    async def _send_message_async(self, message: str) -> bool:
        """
        The actual async method to send a message.
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logging.info(f"Telegram message sent successfully to chat_id {self.chat_id}.")
            return True
        except TelegramError as e:
            logging.error(f"Failed to send Telegram message due to Telegram API error: {e}")
            return False
