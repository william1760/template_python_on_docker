import argparse
import logging
from io import StringIO
from contextlib import redirect_stdout
from tzlocal import get_localzone
from apscheduler.schedulers.blocking import BlockingScheduler
from Log4Me import Log4Me
from Telegram import Telegram
from ConsoleTitle import ConsoleTitle
from TimeToolkit import TimeToolkit
from config_manager import ConfigManager
from input_helper import InputHelper

# Configuration variables
config_path = "config.json"
title = ""
notification = ""
telegram_chatroom = ""


def setup_config():
    global config_path
    config_data = InputHelper.get_user_input()
    ConfigManager.save_config(config_data, config_path)
    print(config_data)

    if config_data["notification"] == 'y':
        tg_chat_room = config_data['telegram']
        tg = Telegram(tg_chat_room)
        print(f'[{title}][SETUP] Telegram chat id - "{tg_chat_room}:{tg.telegram_token}" is ready.')


def load_config():
    """Load configuration and log the result."""
    global config_path
    file_config = ConfigManager.load_config(config_path)

    if file_config:
        load_title = file_config["title"]
        load_log_file_name = file_config["log_file_name"]
        load_interval = file_config["interval"]
        load_schedule = file_config["schedule"]
        load_telegram_chatroom = file_config["telegram"]
        load_schedule_time = TimeToolkit.parse_time_string(load_schedule)
        config_message = (f"Loaded configuration: "
                          f"title={load_title}, "
                          f"log_file_name={load_log_file_name}, "
                          f"interval={load_interval}, "
                          f"interval={load_schedule}, "
                          f"schedule={load_schedule_time}, "
                          f"telegram={load_telegram_chatroom}")
        logging.debug(config_message)
        print(config_message)
        return file_config
    else:
        raise FileNotFoundError("Configuration not found!")


def setup_scheduler(input_template_main, input_config):
    """Set up the scheduler with the loaded configuration."""
    scheduler = BlockingScheduler(timezone=str(get_localzone()))
    interval = input_config["interval"]
    misfire_grace_time = input_config["schedule_misfire_grace_time"]
    schedule_time = TimeToolkit.parse_time_string(input_config["schedule"])

    if interval == 0:
        scheduler.add_job(input_template_main, 'cron', hour=schedule_time[0], minute=schedule_time[1],
                          misfire_grace_time=misfire_grace_time)
        scheduled_job_msg = f"Scheduled jobs: {input_config['schedule']}"
    else:
        scheduler.add_job(input_template_main, 'interval', minutes=int(interval),
                          misfire_grace_time=misfire_grace_time)
        scheduled_job_msg = f"Scheduled jobs: interval {interval} minute(s)."

    print(scheduled_job_msg)
    logging.info(scheduled_job_msg)

    with redirect_stdout(StringIO()) as buffer:
        scheduler.print_jobs()
    scheduler_msg = buffer.getvalue().rstrip('\n')
    logging.info(scheduler_msg)
    print(scheduler_msg)

    return scheduler


def template_function():
    template_function_message = f'called <template_function>.'
    print(template_function_message)
    logging.info(template_function_message)

    return template_function_message


def template_main():
    global title, telegram_chatroom, notification
    return_message = template_function()

    if notification.lower() == 'y':
        telegram_message = f'[{title}] Sending Telegram: {return_message}'
        print(telegram_message)
        telegram_instance = Telegram(telegram_chatroom)
        telegram_instance.send_message(telegram_message)
    else:
        print(f'[{title}] Message: {return_message}')


if __name__ == "__main__":
    try:
        config = ConfigManager.load_config(config_path)

        title = config["title"]
        log_file_name = config["log_file_name"]
        notification = config["notification"]
        telegram_chatroom = config["telegram"]

        ConsoleTitle.show_title(title, True, 50)
        Log4Me.init_logging()

        parser = argparse.ArgumentParser(description=f"{template_main}")
        parser.add_argument('--setup', action="store_true")
        parser.add_argument('--run', action="store_true")

        args = parser.parse_args()

        if args.setup:
            setup_config()
        elif args.run:
            template_main()
        else:
            try:
                main_scheduler = setup_scheduler(template_main, config)
                main_scheduler.start()
            except KeyboardInterrupt:
                keyboard_interrupt_message = "Ctrl-C pressed. Stopping the scheduler..."
                print(keyboard_interrupt_message)
                logging.warning(keyboard_interrupt_message)
    except FileNotFoundError as e:
        print(str(e))
        logging.error(str(e))
