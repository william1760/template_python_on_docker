import os
import logging
from logging.handlers import TimedRotatingFileHandler


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

    @staticmethod
    def self_exit(err_msg):
        logging.error(err_msg)
        print(err_msg)
        exit()

    @staticmethod
    def init_logging(log_name: str = 'LOG', log_days_to_keep: int = 30, subdirectory: str = 'LOGS',
                     asterisk_count: int = 100, console_logging_level=logging.NOTSET,
                     file_logging_level=logging.DEBUG):
        subdirectory = subdirectory[1:] if subdirectory.startswith('/') else subdirectory

        print('[Log4Me] Initialization...')

        try:
            if not os.path.exists(subdirectory):
                os.makedirs(subdirectory)
                print(f"[Log4Me] Created '{subdirectory}' subdirectory for logs")

            log_path = os.path.abspath(os.path.join(subdirectory, f'{log_name}.log'))
            log_format = '%(asctime)s %(levelname)s: %(message)s'

            print(f"[Log4Me] Path: {log_path}")
            print(f"[Log4Me] Rotation: daily, keeping {log_days_to_keep} days")

            root_logger = logging.getLogger()
            # Root must be DEBUG so individual handlers do their own filtering
            root_logger.setLevel(logging.DEBUG)

            file_handler = TimedRotatingFileHandler(
                log_path, when='midnight', interval=1,
                backupCount=log_days_to_keep, encoding='utf-8'
            )
            file_handler.setLevel(file_logging_level)
            file_handler.setFormatter(logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S'))
            root_logger.addHandler(file_handler)

            if console_logging_level != logging.NOTSET:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(console_logging_level)
                console_handler.setFormatter(CustomFormatter())
                root_logger.addHandler(console_handler)

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