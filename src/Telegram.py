import requests
import logging
import argparse
import datetime
from KeyManager import KeyManager


class Telegram:
    def __init__(self, telegram_chat: str):
        self.key_manager = KeyManager()
        self.telegram_bot = self.__get_token_key('telegram_bot')
        self.telegram_token = self.__get_chat_id(telegram_chat, self.telegram_bot)

        # Debug
        # logging.debug(f'[Telegram] telegram_bot: {self.telegram_bot}, telegram_token: {self.telegram_token}
    def __get_token_key(self, token_name: str):
        """
        Retrieve the bot token key from the KeyManager or create a new one if it doesn't exist.

        Args:
            token_name (str): The name of the token.

        Returns:
            str: The bot token key.
        """
        if not self.key_manager.exists(token_name):
            logging.error(f"[Telegram][_get_token_key] Key '{token_name}' not found. Preparing to create a new one...")
            self.key_manager.add(token_name)
            logging.info(f"[Telegram][_get_token_key] Generated and saved for {token_name}")

        return self.key_manager.get(token_name)

    def __get_chat_id(self, chat_name: str, bot_token: str):
        """
        Retrieve the chat ID associated with a chat name and bot token.

        Args:
            chat_name (str): The name of the chat.
            bot_token (str): The bot token.

        Returns:
            int: The largest chat ID found.
        """
        base_url = f'https://api.telegram.org/bot{bot_token}'
        url = f'{base_url}/getUpdates'

        try:
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
            else:
                logging.error('Error fetching updates:', response.text)
                return None
        except requests.RequestException as e:
            logging.error('Error during API request:', str(e))
            return None

        largest_update_id = None
        largest_chat_id = None

        for result in data.get('result', []):
            update_id = result.get('update_id')
            chat = result.get('message', {}).get('chat', {})
            title = chat.get('title', '')
            chat_id = chat.get('id', None)

            if title == chat_name and chat_id is not None:
                if largest_update_id is None or update_id > largest_update_id:
                    largest_update_id = update_id
                    largest_chat_id = chat_id

        # debug
        # logging.debug(f'[telegram][debug] chat_name: {chat_name}, largest_chat_id: {largest_chat_id}')
        if largest_chat_id is not None:
            if self.key_manager.exists(chat_name):
                self.key_manager.update(chat_name, largest_chat_id)
            else:
                self.key_manager.add(chat_name, largest_chat_id)

            logging.info(f"[Telegram][__get_chat_id] Chat ID: '{chat_name}' ready.")
        else:
            if self.key_manager.exists(chat_name):
                largest_chat_id = self.key_manager.get(chat_name)
            else:
                logging.error(f"[Telegram][__get_chat_id] No '{chat_name}' chat found.")

        return largest_chat_id

    @staticmethod
    def display_token(telegram_chat: str):
        """
        Display the existence and value of the Telegram token for the specified chat.

        Args:
            telegram_chat (str): The name of the chat.

        Returns:
            None
        """
        token_name = "telegram_bot"
        key_manager = KeyManager()

        if key_manager.exists(token_name) == 0:
            print(f"[Telegram][init_token_key] {token_name} does not exist.")
        else:
            print(f"[Telegram][init_token_key] {token_name} exists and value '{key_manager.get(token_name)}'.")

        if key_manager.exists(telegram_chat) == 0:
            print(f"[Telegram][init_token_key] {telegram_chat} does not exist.")
        else:
            print(f"[Telegram][init_token_key] {telegram_chat} exists and value '{key_manager.get(telegram_chat)}.")

    def send_message(self, message: str):
        """
        Send a message to the specified chat using the Telegram Bot API.

        Args:
            message (str): The message to be sent.

        Returns:
            None
        """
        bot_token = self.telegram_bot
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': self.telegram_token,
                'text': message
            }
            headers = {
                'Authorization': f'Bearer {bot_token}',
                'Content-Type': 'application/json'
            }
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            logging.info("Message sent successfully!")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending message: {e}")


if __name__ == '__main__':
    default_chat = 'TG_TESTING'
    parser = argparse.ArgumentParser(description="User input for the Telegram API name and token generation")
    parser.add_argument(
        "--display_token",
        action="store_true",
        help="Generate a new Telegram Bot and Chat Id",
    )
    parser.add_argument(
        "--chat_name",
        default=default_chat,
        help="Name of the Telegram chat room to use",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)  # Configure logging level

    telegram_instance = Telegram(args.chat_name)

    if args.display_token:
        telegram_instance.display_token(args.chat_name)
    else:
        telegram_message = f"[Telegram_Bot] Test message @ {datetime.datetime.now().strftime('%Y %m %d %H:%M:%S')}"
        telegram_instance.send_message(telegram_message)
