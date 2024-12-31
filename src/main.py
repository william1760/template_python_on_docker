import datetime
import os
import sys
import logging
import argparse
from utilities import Log4Me, Telegram, ConsoleTitle, ConfigManager, InputHelper, Scheduler

# Configuration variables
config_path = "config.json"
config = None


def setup_config():
    global config_path

    config_data = InputHelper.get_user_input()
    ConfigManager.save_config(config_data, config_path)
    print(f'Config: {config_data}')


def main(trigger_notification: bool = False):
    global config
    main_title = config["title"]
    notification = config["notification"]
    telegram_chatroom = config["telegram"]

    result_message = f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Function "main" called'

    if notification.lower() == 'y' or notification.lower() == 'a' or trigger_notification:
        telegram_message = f"[{main_title}] {result_message}"
        Log4Me.log_and_print(f'[main] telegram_message: {telegram_message}', "debug")
        telegram_instance = Telegram(telegram_chatroom)

        if telegram_instance.send_message(telegram_message):
            Log4Me.log_and_print(f'[main] Telegram: message sent successfully.')
        else:
            Log4Me.log_and_print(f'[main] Telegram: Failed to send message.')
    else:
        print(f'[{title}][template_main] Message: {result_message}')


if __name__ == "__main__":
    try:
        if not os.path.exists(config_path):
            print(f"Error: The required file '{config_path}' does not exist.")
            sys.exit(1)  # Exit the script with a non-zero exit code

        config = ConfigManager.load_config(config_path)
        log_file_name = config["log_file_name"]
        title = config["title"]

        ConsoleTitle.show_title(title, False, 60)
        Log4Me.init_logging(log_name=log_file_name)
        logging.info(f'[Main] Load Config: {config}')

        parser = argparse.ArgumentParser(description=f"{title}")
        parser.add_argument('--setup', action="store_true", help="Setup configuration")
        parser.add_argument('--run', action="store_true", help="Execute now without schedule")

        args = parser.parse_args()

        if args.setup:
            setup_config()
        elif args.run:
            main()
        else:
            try:
                job_schedule = Scheduler()

                if int(config["interval"]) > 0:
                    job_schedule.add(main,
                                     schedule_type='interval',
                                     interval=int(config["interval"]),
                                     misfire_grace_time=config["schedule_misfire_grace_time"])

                if config["schedule"]:
                    cp_notification = True if config["checkpoint_notification"].lower == 'y' else False
                    job_schedule.add(main,
                                     schedule_type='cron',
                                     schedule_time=config["schedule"],
                                     checkpoint_notification=cp_notification,
                                     misfire_grace_time=int(config["schedule_misfire_grace_time"]))

                job_schedule.show_jobs()
                job_schedule.start()

            except KeyboardInterrupt:
                keyboard_interrupt_message = "Ctrl-C pressed. Stopping the scheduler..."
                Log4Me.log_and_print(keyboard_interrupt_message, "error")
                sys.exit(1)  # Exit the program gracefully
    except Exception as e:
        print(str(e))
