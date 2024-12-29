import os
import time
import logging
from datetime import date


# Custom Formatter with ANSI Color Codes for Different Log Levels
class CustomFormatter(logging.Formatter):
    """Custom logging.Formatter that adds colors to log output."""
    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.format)
        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class Log4Me:
    """
    A utility class for logging management and maintenance.

    The Log4Me class provides functions to initialize logging configuration,
    manage log files, and perform log-related tasks.

    Args:
        None

    Methods:
        self_exit(err_msg): Log an error message and exit the program.
        remove_old_logs(file_path, days_to_keep): Remove old log files from a directory.
        init_logging(log_name='LOG', log_days_to_keep=30, subdirectory='LOGS', asterisk_count=100):
            Initialize logging configuration and manage log files.
    """

    @staticmethod
    def self_exit(err_msg):
        """
        Log the error message and exit the program.

        :param err_msg: The error message to log and display.
        """
        logging.error(err_msg)
        print(err_msg)
        exit()

    @staticmethod
    def remove_old_logs(file_path, days_to_keep):
        """
        Remove log files older than a specified number of days.

        :param file_path: The path to the directory containing log files.
        :param days_to_keep: The number of days to keep log files.
        """
        now = time.time()
        try:
            for file in os.listdir(file_path):
                full_path = os.path.join(file_path, file)
                if os.path.isfile(full_path):
                    age_in_days = (now - os.path.getmtime(full_path)) / 86400
                    if age_in_days > days_to_keep:
                        os.remove(full_path)
        except Exception as e:
            raise Exception(e)

    @staticmethod
    def init_logging(log_name: str = 'LOG', log_days_to_keep: int = 30, subdirectory: str = 'LOGS',
                     asterisk_count: int = 100, console_logging_level = logging.NOTSET):
        """
        Initialize logging configuration and manage log files.

        :param log_name: The base name for log files (default: 'LOG').
        :param log_days_to_keep: The number of days to keep log files (default: 30).
        :param subdirectory: The subdirectory for log files (default: 'LOGS').
        :param asterisk_count: The number of asterisks for log separation (default: 100).
        :param console_logging_level: Show the logging in root console (default: logging.NOTSET).
        """
        today = date.today()
        subdirectory = subdirectory[1:] if subdirectory.startswith('/') else subdirectory

        print('[Log4Me] Initialization...')

        try:
            if not os.path.exists(subdirectory):
                os.makedirs(subdirectory)
                print(f"[Log4Me] Created '{subdirectory}' subdirectory for logs")

            log_path = os.path.join(subdirectory, f'{log_name}_{today.strftime("%Y%m%d")}.log')
            log_path = os.path.abspath(log_path)
            log_format = '%(asctime)s %(levelname)s: %(message)s'
            full_path = os.path.dirname(log_path)

            print(f"[Log4Me] Path:  {log_path}")
            print(f"[Log4Me] Remove logs older than '{log_days_to_keep}' days under '{full_path}'")
            Log4Me.remove_old_logs(full_path, log_days_to_keep)

            # Configure logging to write to the log file
            logging.basicConfig(level=logging.DEBUG, filename=log_path, filemode='a', format=log_format)

            if console_logging_level != logging.NOTSET:
                # Show logs in console when console_logging_level is set.
                console_handler = logging.StreamHandler()
                console_handler.setLevel(console_logging_level)
                console_handler.setFormatter(CustomFormatter())

                # Add the console handler to the root logger
                logging.getLogger('').addHandler(console_handler)

            logging.info('*' * asterisk_count)
            logging.info(f'[Log4Me] Logging Start: {log_path}')
        except Exception as e:
            raise Exception(e)

    @staticmethod
    def log_and_print(msg, level="info"):
        """
        Log and print a message.
        :param msg: Message to log and print.
        :param level: Logging level (default: "info").
        """
        try:
            # Dynamically call the logging method based on the level
            getattr(logging, level.lower())(msg)
            print(msg)
        except AttributeError:
            logging.error(f"Invalid logging level: {level}. Message: {msg}")


if __name__ == "__main__":
    # Initialize logging configuration
    Log4Me.init_logging()

    Log4Me.log_and_print("This is an info message.", "info")
    Log4Me.log_and_print("This is an error message.", "error")
    Log4Me.log_and_print("This is a debug message.", "debug")
    Log4Me.log_and_print("This is a warning message.", "warning")
    Log4Me.log_and_print("This will log an error about the invalid level.", "invalid")