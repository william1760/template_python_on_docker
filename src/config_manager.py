
import json
import os
import logging


class ConfigManager:
    @staticmethod
    def load_config(file_path):
        import_file_path = os.path.join(os.getcwd(), file_path)

        # Check if the file exists
        if not os.path.exists(import_file_path):
            load_config_message = f"Configuration file '{import_file_path}' is missing."
            logging.warning(load_config_message)
            print(f'[load_config] {load_config_message}')
            return None

        try:
            # Open and load the JSON file
            with open(import_file_path, 'r') as file:
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

    @staticmethod
    def save_config(data, file_path="config.json"):
        """Update the configuration data in a JSON file without overwriting other settings."""
        import_file_path = os.path.join(os.getcwd(), file_path)

        try:
            # Load existing config if the file exists
            if os.path.exists(import_file_path):
                with open(import_file_path, 'r') as file:
                    existing_data = json.load(file)
            else:
                existing_data = {}

            # Merge existing data with new data
            merged_data = {**existing_data, **data}

            # Save the merged configuration back to the file
            with open(import_file_path, 'w') as file:
                json.dump(merged_data, file, indent=4)

            result_save_message = f"Configuration updated and saved to {import_file_path}"
            logging.info(result_save_message)
            print(result_save_message)
        except (IOError, json.JSONDecodeError) as e:
            result_save_message = f"Error saving configuration: {e}"
            logging.error(result_save_message)
            print(result_save_message)