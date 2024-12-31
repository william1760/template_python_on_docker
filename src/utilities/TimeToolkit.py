import logging
from datetime import datetime


class InvalidTimeInputError(Exception):
    def __init__(self, message):
        super().__init__(message)


class TimeToolkit:
    @staticmethod
    def parse_time_string(time_str):
        """
        Parses a time string in the format 'HH:MM' and returns a list containing hour and minute.

        :param time_str: The input time string.
        :return: A list containing hour and minute as integers.
        :raises InvalidTimeInputError: If the input time string is invalid.
        """
        try:
            time_obj = datetime.strptime(time_str, '%H:%M')
            return [time_obj.hour, time_obj.minute]
        except ValueError as e:
            logging.error(f"[TimeToolkit] Error parsing time string '{time_str}': {e}")
            return None


if __name__ == '__main__':
    try:
        print(TimeToolkit.parse_time_string('01:10'))
        print(TimeToolkit.parse_time_string('23:59'))
    except InvalidTimeInputError as e:
        print(f"Error: {e}")
