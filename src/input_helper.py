import sys
import logging
from Telegram import Telegram

class InputHelper:
    @staticmethod
    def get_user_input():
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

            input_notification = input("Notification? (y/n): ").strip()
            if input_notification.lower() == "y":
                input_telegram = input("Enter the Telegram chatroom: ").strip()

                tg = Telegram(input_telegram)
                print(f'[InputHelper.get_user_input] Telegram chat id - "{input_telegram}:{tg.telegram_token}" is ready.')
            else:
                input_telegram = ""

            # Return the collected data as a dictionary
            result_input_message = (f'Input values: '
                                    f'interval={input_interval}, '
                                    f'schedule={input_schedule}, '
                                    f'notification={input_notification}, '
                                    f'telegram={input_telegram}')
            logging.debug(result_input_message)
            print(result_input_message)

            return {
                "interval": input_interval,
                "schedule": input_schedule,
                "notification": input_notification,
                "telegram": input_telegram
            }

        except KeyboardInterrupt:
            print("\nUser interrupted the process. Exiting...")
            logging.warning("User interrupted the process.")
            sys.exit(1)  # Exit the program gracefully
