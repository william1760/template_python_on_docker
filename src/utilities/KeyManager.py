import base64
import json
import os
import logging
from getpass import getpass
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class KeyManager:
    def __init__(self, token_file_path=None, password=None):
        """
        Initialize the KeyManager object.

        Master password resolution order:
          1. `password` parameter (useful for testing)
          2. KEYMANAGER_PASSWORD environment variable (headless Docker)
          3. Interactive prompt via getpass (--setup stage)

        Parameters:
        - token_file_path: Path to the encrypted key store file.
          Defaults to DATA/Token.key relative to this file.
        - password: Override master password (bytes or str).
          If None, resolved from env var or interactive prompt.
        """
        data_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../DATA'))
        os.makedirs(data_folder, exist_ok=True)

        self.token_file_path = token_file_path or os.path.join(data_folder, 'Token.key')

        if password is not None:
            self.password = password if isinstance(password, bytes) else str(password).encode('utf-8')
        else:
            master = os.environ.get('KEYMANAGER_PASSWORD') or self._get_pass('Master password: ')
            self.password = master.encode('utf-8')

        if os.path.exists(self.token_file_path):
            self._validate_password()

    @staticmethod
    def _get_pass(get_pass_msg="Enter password: "):
        """
        Safely retrieves a password from the user input.

        Returns:
            str: The entered password.
        """
        try:
            return getpass(prompt=get_pass_msg)
        except KeyboardInterrupt:
            print("\nCtrl-C detected. Exiting...")
            exit()

    def _get_fernet_key(self, salt: bytes) -> bytes:
        """
        Derive a Fernet key from the master password and a given salt
        using PBKDF2HMAC. The derived key is never stored — only the
        salt is stored, allowing the key to be re-derived on demand.

        Parameters:
            salt: 16 random bytes. Must be the same salt used at encrypt time.

        Returns:
            bytes: The derived Fernet key.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.password))

    _VALIDATION_NAME = '__validation__'
    _VALIDATION_PLAINTEXT = b'__validation__'

    def _create_validation_entry(self) -> dict:
        salt = os.urandom(16)
        cipher = Fernet(self._get_fernet_key(salt)).encrypt(self._VALIDATION_PLAINTEXT)
        return {
            'Name': self._VALIDATION_NAME,
            'Key': cipher.decode('utf-8'),
            'Salt': base64.b64encode(salt).decode('utf-8')
        }

    def _validate_password(self):
        """
        Validate the master password against the sentinel entry in Token.key.
        Raises ValueError if the sentinel is missing or the password is wrong.
        Only called when Token.key already exists.
        """
        keys_data = self._read_keys_from_file(skip_validation=True)
        sentinel = next((k for k in keys_data if k['Name'] == self._VALIDATION_NAME), None)

        if sentinel is None:
            # Legacy file with no sentinel — bootstrap one with the current password.
            self._write_keys_to_file(self._read_keys_from_file())
            return

        salt = base64.b64decode(sentinel['Salt'])
        try:
            Fernet(self._get_fernet_key(salt)).decrypt(sentinel['Key'].encode())
        except InvalidToken:
            raise ValueError(
                "[KeyManager] Wrong master password. Cannot decrypt Token.key."
            )

    def _read_keys_from_file(self, skip_validation=False) -> list:
        if os.path.exists(self.token_file_path) and os.path.getsize(self.token_file_path) > 0:
            with open(self.token_file_path, 'r') as token_file:
                data = json.load(token_file)
            if not skip_validation:
                return [k for k in data if k['Name'] != self._VALIDATION_NAME]
            return data
        return []

    def _write_keys_to_file(self, keys: list):
        # Always preserve the validation entry at the front
        existing = self._read_keys_from_file(skip_validation=True)
        sentinel = next((k for k in existing if k['Name'] == self._VALIDATION_NAME), None)
        if sentinel is None:
            sentinel = self._create_validation_entry()
        payload = [sentinel] + [k for k in keys if k['Name'] != self._VALIDATION_NAME]
        with open(self.token_file_path, 'w') as token_file:
            json.dump(payload, token_file, indent=2)

    def get(self, item) -> str | None:
        """
        Find the item and return the decrypted value.
        Returns None if item not found or master password is wrong.

        Parameters:
            item (str): The item name.
        """
        keys_data = self._read_keys_from_file()
        for key_data in keys_data:
            if key_data['Name'] == item:
                if 'Salt' not in key_data:
                    logging.error(f"[KeyManager][get] '{item}' uses old format. Re-run --setup to re-add it.")
                    return None
                salt = base64.b64decode(key_data['Salt'])
                cipher_key = self._get_fernet_key(salt)
                try:
                    return Fernet(cipher_key).decrypt(key_data['Key'].encode()).decode('utf-8')
                except InvalidToken:
                    logging.error(f"[KeyManager][get] Failed to decrypt '{item}'. Wrong master password?")
                    return None
        return None

    def list(self) -> list:
        """
        List the names of all saved records.

        Returns:
            list: The list of item names.
        """
        return [key_data['Name'] for key_data in self._read_keys_from_file()]  # sentinel already filtered

    def add(self, item, token=None):
        """
        Add a new item and save it encrypted.
        Returns None without adding if the item already exists.

        Parameters:
            item (str): The item name.
            token (str): Value to store. If None, prompts the user.
        """
        if self.exists(item):
            logging.error(f"[KeyManager][add] '{item}' already exists. Use 'update' to update it.")
            return None

        secret = str(token) if token is not None else self._get_pass(f"[KeyManager][add] Enter value for '{item}': ")

        salt = os.urandom(16)
        cipher = Fernet(self._get_fernet_key(salt)).encrypt(secret.encode())

        keys_data = self._read_keys_from_file()
        keys_data.append({
            'Name': item,
            'Key': cipher.decode('utf-8'),
            'Salt': base64.b64encode(salt).decode('utf-8')
        })
        self._write_keys_to_file(keys_data)
        return cipher

    def update(self, item, token=None):
        """
        Update an existing item with a new encrypted value.
        Returns None without updating if the item does not exist.

        Parameters:
            item (str): The item name.
            token (str): New value to store. If None, prompts the user.
        """
        if not self.exists(item):
            logging.error(f"[KeyManager][update] '{item}' does not exist. Use 'add' to add it.")
            return None

        secret = str(token) if token is not None else self._get_pass(f"[KeyManager][update] Enter new value for '{item}': ")

        salt = os.urandom(16)
        cipher = Fernet(self._get_fernet_key(salt)).encrypt(secret.encode())

        keys_data = self._read_keys_from_file()
        for key_data in keys_data:
            if key_data['Name'] == item:
                key_data['Key'] = cipher.decode('utf-8')
                key_data['Salt'] = base64.b64encode(salt).decode('utf-8')
                break

        self._write_keys_to_file(keys_data)
        return cipher

    def remove(self, item):
        """
        Remove an item from the key store.

        Parameters:
            item (str): The item name.
        """
        if not self.exists(item):
            logging.error(f"[KeyManager][remove] '{item}' does not exist.")
            return

        logging.info(f"[KeyManager][remove] Removing '{item}'.")
        keys_data = [k for k in self._read_keys_from_file() if k['Name'] != item]
        self._write_keys_to_file(keys_data)

    def exists(self, item) -> bool:
        """
        Check if an item exists in the key store.

        Parameters:
            item (str): The item name.

        Returns:
            bool: True if the item exists, False otherwise.
        """
        return any(k['Name'] == item for k in self._read_keys_from_file())


if __name__ == "__main__":
    key_manager = KeyManager()
    print('KeyManager example usage. Key = "my_item"')

    key_manager.add("my_item")

    value = key_manager.get("my_item")
    print(f"Decrypted value: {value}")

    print("All item names:", key_manager.list())

    key_manager.update("my_item")
    value = key_manager.get("my_item")
    print(f"Updated decrypted value: {value}")

    key_manager.remove("my_item")
    print("Final item list:", key_manager.list())
