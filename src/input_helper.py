import sys
import logging
from Telegram import Telegram


class InputHelper:
    @staticmethod
    def get_user_input() -> dict:
        """Prompt the user for input, validate, and return as a dictionary."""
        try:
            # Prompt and validate interval
            while True:
                try:
                    input_interval = int(input("Enter the interval in minutes (positive integer): ").strip())
                    if input_interval >= 0:
                        break
                    else:
                        print("Interval must be a positive integer.")
                except ValueError:
                    print("Invalid input. Please enter a positive integer for interval.")

            input_schedule = input("Enter the schedule time (e.g., 13:30): ").strip()

            while True:
                input_notification = input("Notification? (y/a/n): ").strip().lower()
                if input_notification in {"y", "a", "n"}:
                    break
                else:
                    print("Invalid input. Please enter 'y' for Yes, 'a' for All, or 'n' for No.")

            while True:
                input_checkpoint_notification = input("Checkpoint Notification? (y/n): ").strip().lower()
                if input_checkpoint_notification in {"y", "n"}:
                    break
                else:
                    print("Invalid input. Please enter 'y' for Yes or 'n' for No.")

            if input_notification == "y" or input_checkpoint_notification == "y":
                input_telegram = input("Enter the Telegram chatroom: ").strip()

                tg = Telegram(input_telegram)
                print(f'Telegram chat id - "{input_telegram}:{tg.telegram_token}" is ready.')
            else:
                input_telegram = ""

            # Return the collected data as a dictionary
            result_input_message = (f'[InputHelper.get_user_input] Input values: '
                                    f'interval={input_interval}, '
                                    f'schedule={input_schedule}, '
                                    f'notification={input_notification}, '
                                    f'checkpoint_notification={input_checkpoint_notification}, '
                                    f'telegram={input_telegram}')
            logging.debug(result_input_message)

            return {
                "interval": input_interval,
                "schedule": input_schedule,
                "notification": input_notification,
                "checkpoint_notification": input_checkpoint_notification,
                "telegram": input_telegram
            }

        except KeyboardInterrupt:
            print("\nUser interrupted the process. Exiting...")
            logging.warning("User interrupted the process.")
            sys.exit(1)  # Exit the program gracefully

    @staticmethod
    def get_additional_input(existing_config: dict, additional_config_name: str) -> dict:
        """
        Adds or updates an additional configuration setting in an existing config object.

        :param existing_config: The existing configuration dictionary.
        :param additional_config_name: The name of the additional configuration to add.
        :return: The updated configuration dictionary.
        """
        try:
            # Prompt for the additional configuration
            input_additional_value = input(f"Enter the value for {additional_config_name}: ").strip()

            # Update the existing configuration
            existing_config[additional_config_name] = input_additional_value

            # Log the updated configuration
            logging.info(f"[InputHelper.get_additional_input] Added "
                         f"'{additional_config_name}': '{input_additional_value}'")

            return existing_config

        except KeyboardInterrupt:
            print("\nUser interrupted the additional input process. Exiting...")
            logging.warning("User interrupted the additional input process.")
            sys.exit(1)  # Exit the program gracefully
