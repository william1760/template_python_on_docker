import logging
import certifi
import ssl
import os
import time
import json
from tabulate import tabulate
from datetime import datetime, date
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError
from .KeyManager import KeyManager
from .config_manager import ConfigManager


class Calendarific:
    USER_AGENT = "Mozilla/5.0"

    def __init__(self, config: dict):
        self.key_manager = KeyManager()
        self.context = ssl.create_default_context(cafile=certifi.where())
        self.calendarific_api_token = self.__get_key('calendarific_api_token')

        # Validate the required key
        if "calendarific_endpoint" not in config:
            raise KeyError("[Calendarific] The configuration dictionary must include a 'calendarific_endpoint' key.")

        if "data_folder" not in config:
            raise KeyError("[Calendarific] The configuration dictionary must include a 'data_folder' key.")

        self.request_timeout = config.get("request_timeout", 10)  # Default to 10 seconds
        self.calendarific_data_age_limit = config.get("calendarific_data_age_limit", 7)  # Default to 7 days
        self.calendarific_endpoint = config["calendarific_endpoint"]
        self.data_folder = config["data_folder"]
        self.countries = config["calendarific_country"]
        self.default_type = config["calendarific_default_type"]

        os.makedirs(self.data_folder, exist_ok=True)  # Ensure the data folder exists

    def __get_key(self, token_name: str) -> str:
        if not self.key_manager.exists(token_name):
            logging.error(f"[Calendarific.__get_key] Key '{token_name}' not found. Preparing to create a new one...")
            self.key_manager.add(token_name)
            logging.info(f"[Calendarific.__get_key] Generated and saved for {token_name}")

        return self.key_manager.get(token_name)

    def get_data_from_calendarific(self, country_code, selected_year, holiday_type=None) -> json:
        logging.info(f'[get_holidays_from_calendarific] Download calendar for {country_code} / {selected_year} / '
                     f'{"None" if not holiday_type else holiday_type}')

        params = {"api_key": self.calendarific_api_token, "country": country_code, "year": selected_year}
        query_string = urlencode(params)

        file_name = os.path.join(self.data_folder, f"calendar_data_{selected_year}_{country_code}.json")

        url = f"{self.calendarific_endpoint}?&{query_string}"
        if holiday_type:
            url += f"&type={holiday_type}"

        start_time = time.time()
        result = None

        try:
            request = Request(url, headers={'User-Agent': self.USER_AGENT})
            response = urlopen(request, context=self.context, timeout=10)
            response_text = json.loads(response.read().decode('utf-8'))
            result = {"success": True, "response": response_text}
        except HTTPError as e:
            result = {"success": False, "error": f"HTTPError: {e.code} - {e.reason}"}
        except URLError as e:
            result = {"success": False, "error": f"URLError: {e.reason}"}
        except Exception as e:
            result = {"success": False, "error": f"Unexpected error: {e}"}
        finally:
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000)  # Convert to milliseconds
            # Add duration to the log message and result
            if result["success"]:
                logging.info(f'[Calendarific.get_holidays] Download holiday success (Duration: {response_time:.2f} ms)')

                with open(file_name, 'w') as file:
                    json.dump(result["response"], file, indent=2)
                logging.info(f'[get_holidays_from_calendarific] Downloaded and saved to local - {file_name}')
            else:
                logging.error(f'[Calendarific.get_holidays] {result["error"]} (Duration: {response_time:.2f} ms)')
            result["duration_ms"] = response_time
        return result["response"]

    @staticmethod
    def is_valid_json(data):
        """Check if the given data is a valid JSON structure."""
        return 'response' in data and 'holidays' in data['response']

    def get_holiday_type(self, country_code: str) -> str:
        # Search for the country in the list
        for country in self.countries:
            if country["code"] == country_code:
                # Return the type if it exists, or a default value
                return country.get("type", self.default_type)
        # Return a fallback if the country is not found
        return self.default_type

    @staticmethod
    def transform_holiday_data(holidays):
        count_width = len(str(len(holidays)))
        return [
            {
                "Count Id": str(count).zfill(count_width),
                "Country ID": holiday_item['country']['id'].upper(),
                "Country Name": holiday_item['country']['name'],
                "Name": holiday_item['name'],
                "Date ISO": holiday_item['date']['iso'],
                "Type": ', '.join(holiday_item['type']),
                "Primary Type": holiday_item.get('primary_type', ""),
                "Locations": holiday_item.get('locations', "")
            }
            for count, holiday_item in enumerate(holidays, start=1)
        ]

    def get_holidays_by_country(self, country_code: str, selected_year: int):
        """
        Retrieve holidays for a specific country and year, either from local cache or Calendarific API.

        Args:
            country_code (str): Country code (e.g., "HK", "JP").
            selected_year (int): Year to fetch holidays for.

        Returns:
            list: Transformed holiday data.
        """
        country_code = country_code.upper()
        holiday_type = self.get_holiday_type(country_code)
        file_name = os.path.join(self.data_folder, f"calendar_data_{selected_year}_{country_code}.json")

        # Try to load holidays from the cache
        data = self.load_cached_file(file_name)

        if data:
            file_age = self.get_file_age_in_days(file_name)
            if file_age > self.calendarific_data_age_limit:
                logging.warning(
                    f'[get_holidays_by_country] Cached file too old ({file_age} days), refreshing: {file_name}')
                data = self.get_data_from_calendarific(country_code, selected_year, holiday_type)
        else:
            logging.warning(f'[get_holidays_by_country] No cached file found, downloading: {file_name}')
            data = self.get_data_from_calendarific(country_code, selected_year, holiday_type)

        if not self.is_valid_json(data):
            logging.warning(f'[get_holidays_by_country] Invalid data in file {file_name}, re-fetching...')
            data = self.get_data_from_calendarific(country_code, selected_year, holiday_type)

        return self.transform_holiday_data(data['response']['holidays'])

    @staticmethod
    def load_cached_file(file_name: str):
        """Load a cached JSON file if it exists."""
        if not os.path.exists(file_name):
            return None

        try:
            with open(file_name, 'r') as file:
                return json.load(file)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"[load_cached_file] Error loading {file_name}: {e}")
            return None

    @staticmethod
    def get_file_age_in_days(file_name: str) -> int:
        """Calculate the age of a file in days."""
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_name)).date()
        return (datetime.now().date() - file_mtime).days

    def get_countries(self) -> list:
        """Retrieve a list of countries from the configuration."""
        return [country["code"] for country in self.countries]

    def check_holidays(self, target_date: date = None) -> list[dict]:
        """Retrieve holidays for all countries on a specific date."""
        if target_date is None:
            target_date = datetime.now().date()

        selected_year = target_date.year

        try:
            countries = self.get_countries()
            if not countries:
                logging.warning("[check_holidays] No countries found in configuration.")
                return []
        except Exception as e:
            logging.error(f"[check_holidays] Failed to retrieve countries: {e}")
            return []

        result_array = []
        logging.info(
            f"[check_holidays] Date: {target_date.isoformat()} / Year: {selected_year} / Countries: {countries}")

        for country_code in countries:
            try:
                holidays = self.get_holidays_by_country(country_code, selected_year)
                matching_holidays = [
                    holiday for holiday in holidays if holiday.get("Date ISO") == target_date.strftime("%Y-%m-%d")
                ]
                result_array.extend(matching_holidays)
            except Exception as e:
                logging.error(f"[check_holidays] Failed to retrieve holidays for {country_code}: {e}")
                continue

        for count, item in enumerate(sorted(result_array, key=lambda x: x.get("Country ID", "")), start=1):
            item["Count Id"] = str(count).zfill(len(str(len(result_array))))

        logging.info(f"[check_holidays] Found {len(result_array)} matching holidays.")
        return result_array

    @staticmethod
    def create_holiday_table(holidays: list[dict]) -> str:
        """Create a table of holiday data."""
        table_headers = ["Count Id", "Country ID", "Country Name", "Date ISO", "Name", "Type", "Primary Type",
                         "Locations"]
        table_data = [(h["Count Id"], h["Country ID"], h["Country Name"], h["Date ISO"], h["Name"], h["Type"],
                       h["Primary Type"], h["Locations"]) for h in holidays]
        return tabulate(table_data, headers=table_headers, tablefmt="pretty")

    @staticmethod
    def format_holiday_text(result_array: list[dict]) -> str:
        """Format the holiday result array into a text summary."""
        formatted_lines = []
        for holiday_item in result_array:
            count_id = holiday_item.get("Count Id", "N/A")
            date_iso = holiday_item.get("Date ISO", "N/A")
            name = holiday_item.get("Name", "N/A")
            holiday_type = holiday_item.get("Type", "N/A")
            primary_type = holiday_item.get("Primary Type", "N/A")

            formatted_line = f"{date_iso} : {name} ({primary_type})"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)

    def show_holiday(self, target_date: date = None, target_year: int = None,
                     country: str = None, text_mode=False) -> str:
        """Display the holiday results in a table format."""
        target_date = target_date or datetime.now().date()
        target_year = target_year or target_date.year

        if target_date.weekday() == 6 and target_date == date.today():
            logging.info(f'[show_holiday_result] Today is a Sunday.')
            return 'Today is a Sunday.'
        elif target_date.weekday() == 6:
            logging.info(f'[show_holiday_result] {target_date.strftime("%Y-%m-%d")} falls on a Sunday.')
            return f'{target_date.strftime("%Y-%m-%d")} falls on a Sunday.'

        data = self.get_holidays_by_country(country, target_year) if country else self.check_holidays(target_date)

        if not data:
            logging.info(f'[show_holiday_result] No holiday for {target_date.strftime("%Y-%m-%d")}')
            return f'No holiday for {target_date.strftime("%Y-%m-%d")}'

        result_array = sorted(data, key=lambda x: x["Country ID"])
        table = self.create_holiday_table(result_array)
        word_country = "Countries" if len(result_array) > 1 else "Country"
        unique_country_ids = {info["Country ID"] for info in result_array}
        country_ids_string = ", ".join(unique_country_ids)
        logging.info(f"[show_holiday_result] Found {len(result_array)} holidays. {word_country}: {country_ids_string}")

        logging.info(f'[show_holiday_result] Summary table:\n\n{table}')

        if text_mode:
            summary_result = f'Country: {country_ids_string} / Year: {target_year}'
            summary_result += "\n\n" + self.format_holiday_text(result_array)
        else:
            summary_result = f'{target_date.strftime("%Y-%m-%d")} - {word_country} with Holidays: : {country_ids_string}'

        return summary_result


if __name__ == '__main__':
    # Configure logging
    input_config = ConfigManager.load_config('../config.json')

    date_selected = datetime.strptime("2025-01-03", "%Y-%m-%d").date()
    holiday = Calendarific(input_config)

    print(holiday.show_holiday(target_date=date_selected, text_mode=False))
    holiday.show_holiday(country="HK", target_year=2027, text_mode=False)
