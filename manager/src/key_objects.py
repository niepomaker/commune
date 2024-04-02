from commune.module import Module 
import os
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Union
from abc import ABC, abstractmethod

from src.encryption import encrypt_json, decrypt_json
from src.commune_queries import get_free_balance
from getpass import getpass
from dotenv import load_dotenv


load_dotenv()

c = Module()


class KeyConfigModel(BaseModel):
    """
    A pydantic model for storing key configurations.
    """
    crypto_type: str
    """
    The cryptographic algorithm used to generate the key pair.
    """
    seed_hex: str
    """
    The seed used to generate the key pair in hexadecimal format.
    """
    derive_path: Optional[str]
    """
    The derivation path used to derive the key pair from the seed, if applicable.
    """
    path: str
    """
    The location of the key file.
    """
    ss58_format: Union[str, int]
    """
    The ss58 address format of the key.
    """
    public_key: str
    """
    The public key of the key pair in hexadecimal format.
    """
    private_key: str
    """
    The private key of the key pair in hexadecimal format.
    """
    mnemonic: str
    """
    The mnemonic seed phrase used to generate the key pair.
    """
    ss58_address: str
    """
    The ss58 address of the key.
    """


class AbstractKey(ABC):
    """Abstract base class for key objects."""

    @abstractmethod
    def __init__(self):
        """Abstract initializer."""
        pass

    @abstractmethod
    def key2address(self) -> Dict[str, str]:
        """Returns a dictionary with the name and ss58 address for the key."""

    @abstractmethod
    def key2mnemonic(self) -> Dict[str, str]:
        """Returns a dictionary with the name and mnemonic for the key. Requires authorization."""

    @abstractmethod
    def key2path(self) -> Dict[str, str]:
        """Returns a dictionary with the name and path for the key. Requires authorization."""

    @abstractmethod
    def free_balance(self) -> float:
        """Returns the free balance for the key."""

    @abstractmethod
    def staked_balance(self) -> float:
        """Returns the staked balance for the key."""

    @abstractmethod
    def module_information(self) -> float:
        """Returns the module information for the key."""


        
class CommuneKey(KeyConfigModel, AbstractKey):
    def __init__(
        self,
        crypto_type,
        seed_hex,
        derive_path,
        path,
        ss58_format,
        public_key,
        private_key,
        mnemonic,
        ss58_address,
        ):
        """
        Initializes the object with the given configuration parameters.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            None
        """
        super().__init__(
            crypto_type = crypto_type,
            seed_hex = seed_hex,
            derive_path = derive_path,
            path = path,
            ss58_format = ss58_format,
            public_key = public_key,
            private_key = private_key,
            mnemonic = mnemonic,
            ss58_address = ss58_address,
            )
        self.name = self.path.split("/")[-1].split(".")[0],        

    def key2address(self) -> Dict[str, str]:
        """
        Returns a dictionary mapping the name of the object to its corresponding SS58 address.

        :return: A dictionary with the object name as the key and the SS58 address as the value.
        :rtype: Dict[str, str]
        """
        return {
            self.name: self.ss58_address
        }

    def key2mnemonic(self) -> Dict[str, str]:
        """
        Generates a dictionary that maps the name of the object to its mnemonic.

        Returns:
            Dict[str, str]: A dictionary where the keys are the names of the object and the values are the corresponding mnemonics.
        """
        return {
            self.name: self.mnemonic
        }

    def key2path(self) -> Dict[str, str]:
        """
        Returns a dictionary mapping the name of the object to its path.

        :return: A dictionary with the object's name as the key and its path as the value.
        :rtype: Dict[str, str]
        """
        return {
            self.name: self.path
        }

    def free_balance(
        self, 
        keyname: Optional[str]=None,
        address: Optional[str]=None,
        keys: Optional[Dict[str, str]]=None
        ) -> float:
        """
        Calculates the free balance of a given key.

        Args:
            keyname (Optional[str]): The name of the key to calculate the balance for.
            address (Optional[str]): The address of the key to calculate the balance for.
            keys (Optional[Dict[str, str]]): A dictionary of keys and their corresponding addresses.

        Returns:
            float: The free balance of the key.
        
        Raises:
            ValueError: If the key is not found or if the keys are not found.
            Exception: If an unexpected error occurs.
        """
        key = keyname if keyname else address
        keys = keys if keys else self.key2address()
        result: float = 0.0
        if not key:
            raise ValueError("Key not found")
        if not keys:
            raise ValueError("Keys not found")
        try:
            result = get_free_balance(key, keys)[1]
        except ValueError as e:
            raise ValueError("Key not found") from e 
        except Exception as e:
            raise e from e
        return result

    def staked_balance(self) -> float:
        return 0

    def module_information(self) -> float:
        return 0


class KeyManager:
    """
    Class for managing keys stored on the system.

    Attributes:
        keyring (Dict[str, Dict[str, str]]): A dictionary of keys and their corresponding data.
        key2ss58address (Dict[str, str]): A dictionary of keys and their corresponding SS58 addresses.
        key2mnemonic (Dict[str, str]): A dictionary of keys and their corresponding mnemonic phrases.
    """

    def __init__(self):
        self.keyring: Dict[str, Dict[str, str]] = {}
        self.key2ss58address: Dict[str, str] = {}
        self.key2mnemonic: Dict[str, str] = {}

    def load_keys(self, password: str,  path: str) -> None:
        """
        Load keys from the system.

        Args:
            password (str): The password to decrypt the keys with.
            path (str): The path to the key folder.
        """
        self.parse_system_keys(password, path)

    def get_keys(self) -> Dict[str, str]:
        """
        Returns a dictionary of keys and their corresponding SS58 addresses.

        :return: A dictionary of keys and their corresponding SS58 addresses.
        :rtype: Dict[str, str]
        """
        return self.key2ss58address

    def parse_system_keys(self, password: str, key_path: str="~/.commune/key") -> None:
        """
        Parse the keys stored on the system.

        Args:
            password (str): The password to decrypt the keys with.
            key_path (str): The path to the key folder.
        """
        if not password:
            getpass("Please enter your password: ")
        files = os.listdir(key_path)
        for file in files:
            filename = file.split(".")[0]
            if filename == "" or filename is None:
                filename = "none"
            file_path = Path(os.path.join(key_path, file))
            if file_path.suffix == ".json":
                data: Dict = json.loads(file_path.read_text(encoding="utf-8"))
                data = json.loads(data["data"])
                try:
                    key = CommuneKey(
                        path=data["path"],
                        crypto_type=data["crypto_type"],
                        ss58_address=data["ss58_address"],
                        mnemonic=data["mnemonic"],
                        derive_path=data["derive_path"],
                        private_key=data["private_key"],
                        public_key=data["public_key"],
                        seed_hex=data["seed_hex"],
                        ss58_format=data["ss58_format"]                        
                    )
                except Exception as e:
                    raise e

                self.keyring[filename] = self.encrypt(filename, password)
                self.key2ss58address[filename] = key.ss58_address
                self.key2mnemonic[filename] = key.mnemonic

    def encrypt(self, keyname: str, password: str) -> Dict[str, str]:
        """
        Encrypt a key.

        Args:
            keyname (str): The name of the key to encrypt.
            password (str): The password to encrypt the key with.

        Returns:
            Dict[str, str]: The encrypted key.
        """
        keyring: Union[Dict[str, str], CommuneKey] = self.keyring[keyname]
        if isinstance(keyring, CommuneKey):
            self.keyring[keyname] = keyring.model_dump()
        return encrypt_json(self.keyring[keyname], password)

    def decrypt(self, keyname: str, password: str) -> Dict[str, str]:
        """
        Decrypt a key.

        Args:
            keyname (str): The name of the key to decrypt.
            password (str): The password to decrypt the key with.

        Returns:
            Dict[str, str]: The decrypted key.
        """
        keyring = self.keyring[keyname]
        if isinstance(keyring, CommuneKey):
            self.keyring[keyname] = keyring.model_dump()
        return decrypt_json(self.keyring[keyname], password)

        


    if __name__ == "__main__":
        key_manager = KeyManager()
        key_manager.load_keys("password", "~/.commune/key")
        print(key_manager.get_keys())