import ssl
import logging
import argparse
import base64
import certifi
import time
import validators
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from config_manager import ConfigManager
from KeyManager import KeyManager


class Dyn_Updater:
    """
    A class to manage dynamic DNS updates.

    :param dyn_config: A dictionary containing configuration data. Must include:
        - dyn_endpoint: The API endpoint for the dynamic DNS update.
    :type dyn_config: dict
    :raises KeyError: If 'dyn_endpoint' is not present in the configuration.
    """

    def __init__(self, dyn_config: dict):
        self.key_manager = KeyManager()
        self.context = ssl.create_default_context(cafile=certifi.where())
        self.dyn_username = self.__get_key('dyn_username')
        self.dyn_token = self.__get_key('dyn_token')

        # Validate the required key
        if "dyn_endpoint" not in dyn_config:
            raise KeyError("[Dyn_Updater] The configuration dictionary must include a 'dyn_endpoint' key.")

        self.dyn_endpoint = dyn_config["dyn_endpoint"]

    def __get_key(self, token_name: str) -> str:
        if not self.key_manager.exists(token_name):
            logging.error(f"[dyn.__get_key] Key '{token_name}' not found. Preparing to create a new one...")
            self.key_manager.add(token_name)
            logging.info(f"[dyn.__get_key] Generated and saved for {token_name}")

        return self.key_manager.get(token_name)

    def update(self, host: str, ip_address: str) -> dict:
        if not validators.domain(host):
            return {"success": False, "error": f"Invalid host: {host}"}
        if not (validators.ipv4(ip_address) or validators.ipv6(ip_address)):
            return {"success": False, "error": f"Invalid IP address: {ip_address}"}

        url = f"{self.dyn_endpoint}?hostname={host}&myip={ip_address}"
        logging.debug(f"[dyn.update] URL prepared")

        credentials = f"{self.dyn_username}:{self.dyn_token}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        headers = {"Authorization": f"Basic {encoded_credentials}"}

        start_time = time.time()
        result = None

        try:
            request = Request(url, headers=headers)
            response = urlopen(request, context=self.context)
            response_text = response.read().decode('utf-8')
            result = {"success": True, "response": response_text}
        except HTTPError as e:
            result = {"success": False, "error": f"HTTPError: {e.code} - {e.reason}"}
        except URLError as e:
            result = {"success": False, "error": f"URLError: {e.reason}"}
        except Exception as e:
            result = {"success": False, "error": f"Unexpected error: {e}"}
        finally:
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000) # Convert to milliseconds
            # Add duration to the log message and result
            if result["success"]:
                logging.info(f'[dyn.update] Update Status: {result["response"]} (Duration: {response_time:.2f} ms)')
            else:
                logging.error(f'[dyn.update] {result["error"]} (Duration: {response_time:.2f} ms)')
            result["duration_ms"] = response_time

        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="User input for the Dyn username and token generation")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Configure logging
    config = ConfigManager.load_config('config.json')
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    dyn = Dyn_Updater(config)
    update_result = dyn.update("kityan-hgc.dyndns.org", "223.19.132.251")
    print(update_result)