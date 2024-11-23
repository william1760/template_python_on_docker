import argparse
import logging
import contextlib
import json
import os
from io import StringIO
from tzlocal import get_localzone
from apscheduler.schedulers.blocking import BlockingScheduler
from Log4Me import Log4Me
from KeyManager import KeyManager
from Telegram import Telegram
from ConsoleTitle import ConsoleTitle
from TimeToolkit import TimeToolkit

# Configuration variables
title = "template_python_on_docker"
log_file_name = 'template_python_on_docker'
result_message = ''
domain = ''
dns_server = ''
key_manager = KeyManager()

# Variables for Config.json
interval = None
config_path = os.path.join(os.getcwd(), "config.json")
misfire_grace_time = 300
schedule_time = [0, 0]
schedule = "00:00"
telegram_chatroom = ""


def load_config(file_path):
    # Check if the file exists
    if not os.path.exists(file_path):
        load_config_message = f"Configuration file '{file_path}' is missing."
        logging.warning(load_config_message)
        print(f'[load_config] {load_config_message}')
        return None

    try:
        # Open and load the JSON file
        with open(file_path, 'r') as file:
            config_json = json.load(file)

        # Validate the contents
        if "interval" not in config_json or "schedule" not in config_json or "telegram" not in config_json:
            load_config_message = "Configuration file is missing 'schedule' or 'interval' or 'telegram' keys."
            logging.warning(load_config_message)
            print(f'[load_config] {load_config_message}')
            return None

        # Return the valid config data
        return config_json

    except json.JSONDecodeError:
        load_config_message = "Configuration file contains invalid JSON."
        logging.warning(load_config_message)
        print(f'[load_config] {load_config_message}')
        return None


def get_user_input():
    """Prompt the user for input, validate, and return as a dictionary."""
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

    input_telegram = input("Enter the Telegram chatroom: ").strip()

    # Return the collected data as a dictionary
    result_input_message = (f'Input values: '
                            f'interval={input_interval},'
                            f'schedule={input_schedule},'
                            f'schedule={input_telegram}')
    logging.debug(result_input_message)
    print(result_input_message)

    return {
        "interval": input_interval,
        "schedule": input_schedule,
        "telegram": input_telegram
    }


def save_config(data, file_path="config.json"):
    """Save the configuration data to a JSON file."""
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

        result_save_message = f"Configuration saved to {file_path}"
        logging.info(result_save_message)
        print(result_save_message)
    except IOError as e:
        result_message = f"Error saving configuration: {e}"
        logging.error(result_message)
        print(result_message)


def template_function():
    template_function_message = f'called template function.'
    print(template_function_message)
    logging.info(template_function_message)

    return template_function_message


def template_main():
    return_message = template_function()
    telegram_message = f'[template_python_on_docker] {return_message}'

    print(telegram_message)
    telegram_instance = Telegram(telegram_chatroom)
    telegram_instance.send_message(telegram_message)


if __name__ == "__main__":
    ConsoleTitle.show_title(title, True, 50)
    Log4Me.init_logging(log_file_name)

    parser = argparse.ArgumentParser(description=f"{template_main}")
    parser.add_argument('--setup', action="store_true")
    parser.add_argument('--dryrun', action="store_true")

    args = parser.parse_args()

    if args.setup:
        config_data = get_user_input()
        save_config(config_data)

        if not key_manager.exists(telegram_chatroom):
            telegram = Telegram(telegram_chatroom)
            print(f'[{title}][SETUP] Telegram chat id - "{telegram_chatroom}" is ready.')
    else:
        config = load_config(config_path)

        if config:
            interval = config["interval"]
            schedule = config["schedule"]
            telegram_chatroom = config["telegram"]
            schedule_time = TimeToolkit.parse_time_string(config["schedule"])
            config_message = (f"Loaded configuration from {config_path}: "
                              f"interval={interval}, "
                              f"schedule={schedule_time}, "
                              f"telegram={telegram_chatroom}")
            logging.debug(config_message)
            print(config_message)

        if args.dryrun:
            template_main()
        else:
            scheduler = BlockingScheduler(timezone=str(get_localzone()))
            if interval == 0:
                scheduler.add_job(template_main, 'cron', hour=schedule_time[0], minute=schedule_time[1],
                                  misfire_grace_time=misfire_grace_time)
                scheduled_job_msg = f"Scheduled jobs: {schedule}"
            else:
                scheduler.add_job(template_main, 'interval', minutes=int(interval),
                                  misfire_grace_time=misfire_grace_time)
                scheduled_job_msg = f"Scheduled jobs: interval {interval} minute(s)."

            print(scheduled_job_msg)
            logging.info(scheduled_job_msg)

            # Capture the print_jobs() output into a string
            with contextlib.redirect_stdout(StringIO()) as buffer:
                scheduler.print_jobs()
            scheduler_msg = buffer.getvalue().rstrip('\n')
            logging.info(scheduler_msg)
            print(scheduler_msg)

            try:
                scheduler.start()
            except KeyboardInterrupt:
                keyboard_interrupt_message = "Ctrl-C pressed. Stopping the scheduler..."
                print(keyboard_interrupt_message)
                logging.warning(keyboard_interrupt_message)
