import base64
import json
import os
import uuid
import logging
from getpass import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class KeyManager:
    def __init__(self, token_file_path=None, password=None):
        """
        Initialize the KeyManager object.

        Parameters:
        - file_path: The file path where the encrypted key data will be stored.
          If None, the default file path is used.
        - password: The password used to generate the encryption key.
          If None, a random UUID-based password will be generated.
        """
        self.token_file_path = token_file_path or os.path.join(os.path.dirname(__file__), 'Token.key')
        self.password = password or str(uuid.uuid1()).encode('utf-8')

    @staticmethod
    def _get_pass(get_pass_msg="Enter password: "):
        """
        Safely retrieves a password from the user input.

        Args:
            get_pass_msg (str, optional): The message prompt for getting the password. Defaults to "Enter password: ".

        Returns:
            str: The entered password.

        Raises:
            KeyboardInterrupt: If Ctrl-C is detected, the function prints a message and exits the program.
        """
        try:
            password = getpass(prompt=get_pass_msg)
            return password
        except KeyboardInterrupt:
            print("\nCtrl-C detected. Exiting...")
            exit()

    def _get_fernet_key(self):
        """
        Generate a Fernet key using PBKDF2HMAC.

        Returns:
            bytes: The Fernet key.
        """
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password))
        return key

    def _read_keys_from_file(self):
        """
        Read the encrypted key data from the JSON file.

        Returns:
        - keys_data: A dictionary containing the key data.
        """
        if os.path.exists(self.token_file_path):
            with open(self.token_file_path, "rb") as token_file:
                keys = json.load(token_file)
        else:
            keys = []
        return keys

    def _write_keys_to_file(self, keys):
        """
        Write the updated key data to the JSON file.

        Parameters:
        - keys_data: A dictionary containing the updated key data.
        """
        with open(self.token_file_path, "w") as token_file:
            json.dump(keys, token_file)

    def get(self, item):
        """
        Find the item in the JSON file and return the decrypted value.

        Parameters:
            item (str): The item name.

        Returns:
            str: The decrypted value.

        """
        keys_data = self._read_keys_from_file()
        for key_data in keys_data:
            if key_data['Name'] == item:
                cipher_suit = Fernet(key_data['Token'])
                cipher = cipher_suit.decrypt(key_data['Key'].encode())
                return cipher.decode('utf-8')
        return None

    def list(self):
        """
        List the names of all saved records in the JSON file.

        Returns:
            list: The list of item names.
        """
        keys_data = self._read_keys_from_file()
        return [key_data['Name'] for key_data in keys_data]

    def _generate_cipher(self):
        msg = '[KeyManger][_generate_cipher] Enter cipher value: '
        password = self._get_pass(msg)
        encoded_password = password.encode()
        cipher_key = self._get_fernet_key()
        cipher_suit = Fernet(cipher_key)
        cipher = cipher_suit.encrypt(encoded_password)
        return cipher

    def add(self, item, token=None):
        """
        Add a new item and save the encrypted values.

        Parameters:
            item (str): The item name.
            token (str): Input token key value.

        Returns:
            bytes: The encrypted key.
        """
        if self.exists(item):
            logging.error(f"Item '{item}' already exists in the keyring. Use 'update' to update it.")

        if token is None:
            msg = f'[KeyManager][add] Require user input for \'{item}\':'
            password = self._get_pass(msg)
        else:
            password = str(token)

        encoded_password = password.encode()
        cipher_key = self._get_fernet_key()
        cipher_suit = Fernet(cipher_key)
        cipher = cipher_suit.encrypt(encoded_password)
        keys_data = self._read_keys_from_file()

        keys_data.append({'Name': item, 'Key': cipher.decode('utf-8'), 'Token': cipher_key.decode('utf-8')})
        self._write_keys_to_file(keys_data)
        return cipher

    def update(self, item, token=None):
        """
        Update an existing item and save the encrypted values.

        Parameters:
            item (str): The item name.
            token (str): Input token key value.

        Returns:
            bytes: The encrypted key.
        """
        if not self.exists(item):
            logging.error(f"Item '{item}' does not exist in the keyring. Use 'add_key' to add it.")

        if token is None:
            msg = f'[KeyManager][update] Enter update value for \'{item}\': '
            password = self._get_pass(msg)
        else:
            password = str(token)

        encoded_password = password.encode()
        cipher_key = self._get_fernet_key()
        cipher_suit = Fernet(cipher_key)
        cipher = cipher_suit.encrypt(encoded_password)
        keys_data = self._read_keys_from_file()

        for key_data in keys_data:
            if key_data['Name'] == item:
                key_data['Key'] = cipher.decode('utf-8')
                key_data['Token'] = cipher_key.decode('utf-8')
                break

        self._write_keys_to_file(keys_data)
        return cipher

    def remove(self, item):
        """
        Remove an item from the JSON file.

        Parameters:
            item (str): The item name.
        """
        keys_data = self._read_keys_from_file()
        msg = f'[KeyManager][remove] Removing item: \'{item}\''
        logging.info(msg)

        if self.exists(item):
            keys_data = [key_data for key_data in keys_data if key_data['Name'] != item]
        else:
            logging.error(f"[KeyManager][remove] Item '{item}' does not exist in the keyring.")

        self._write_keys_to_file(keys_data)

    def exists(self, item):
        """
        Check if the item exists in the JSON file.

        Parameters:
            item (str): The item name.

        Returns:
            int: 1 if the item exists, 0 otherwise.
        """
        keys_data = self._read_keys_from_file()
        return any(key_data['Name'] == item for key_data in keys_data)


if __name__ == "__main__":
    key_manager = KeyManager()
    print(r'KeyManager example usage. Key = "my_item"')

    # Add or update item and save encrypted value
    key_manager.add("my_item")

    # Get the decrypted value
    value = key_manager.get("my_item")
    print(f"Decrypted value: {value}")

    # List all item names
    items = key_manager.list()
    print("All item names:", items)

    # update item names
    key_manager.update("my_item")
    print("Update item names:", items)

    # Get latest decrypted value
    value = key_manager.get("my_item")
    print(f"Decrypted value: {value}")

    # Remove an item
    print(f"Remove value: {value}")
    key_manager.remove("my_item")
    items = key_manager.list()
    print("Final item list:", items)
