from commune import Module 
import os
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Union
from abc import ABC, abstractmethod

from manager.encryption import encrypt_json, decrypt_json
from manager.commune_queries import get_free_balance


from dotenv import load_dotenv



load_dotenv()

c = Module()


class KeyConfigModel(BaseModel):
    crypto_type: str
    seed_hex: str
    derive_path: Optional[str]
    path: str
    ss58_format: int
    public_key: str
    private_key: str
    mnemonic: str
    ss58_address: str


class AbstractKey(ABC):
    @abstractmethod
    def __init__(self):
        pass
    @abstractmethod
    def key2address(self) -> Dict[str, str]:
        """Returns a dictionary with the name and ss58 address for the key"""

    @abstractmethod
    def key2mnemonic(self) -> Dict[str, str]:
        """Returns a dictionary with the name and mnemonic for the key. Requires authorization"""

    @abstractmethod
    def key2path(self) -> Dict[str, str]:
        """Returns a dictionary with the name and path for the key. Requires authorization"""

    @abstractmethod
    def free_balance(self) -> float:
        """Returns the free balance for the key"""

    @abstractmethod
    def staked_balance(self) -> float:
        """Returns the staked balance for the key"""

    @abstractmethod
    def module_information(self) -> float:
        """Returns the module information for the key"""

    @abstractmethod
    def encrypt(self) -> str:
        """Returns the encrypted key"""

    @abstractmethod
    def decrypt(self) -> str:
        """Returns the decrypted key"""

        
class CommuneKey(KeyConfigModel, AbstractKey):
    def __init__(
        self,
        config: Optional[KeyConfigModel]=None,
        **kwargs
        ):
        super().__init__(**config.model_dump() if config else {}, **kwargs)
        self.crypto_type=config.crypto_type if config else kwargs["crypto_type"]
        self.seed_hex=config.seed_hex if config else kwargs["seed_hex"]
        self.derive_path=config.derive_path if config else kwargs["derive_path"]
        self.path=config.path if config else kwargs["path"]
        self.ss58_format=config.ss58_format if config else kwargs["ss58_format"]
        self.public_key=config.public_key if config else kwargs["public_key"]
        self.private_key=config.private_key if config else kwargs["private_key"]
        self.mnemonic=config.mnemonic if config else kwargs["mnemonic"]
        self.ss58_address=config.ss58_address if config else kwargs["ss58_address"]
        self.name = self.path.split("/")[-1].split(".")[0]
        

    def key2address(self) -> Dict[str, str]:
        return {
            self.name: self.ss58_address
        }

    def key2mnemonic(self) -> Dict[str, str]:
        return {
            self.name: self.mnemonic
        }

    def key2path(self) -> Dict[str, str]:
        return {
            self.name: self.path
        }

    def free_balance(
        self, 
        keyname: Optional[str]=None,
        address: Optional[str]=None,
        keys: Optional[Dict[str, str]]=None
        ) -> float:
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

    def encrypt(self) -> str:
        return ""

    def decrypt(self) -> str:
        return ""


class KeyManager:
    def __init__(self):
        self.keyring: Dict[str, CommuneKey] = {}
        self.key2ss58address: Dict[str, str] = {}
        self.key2mnemonic: Dict[str, str] = {}

    def load_keys(self, path: str):
        self.parse_system_keys(path)

    def get_keys(self) -> Dict[str, str]:
        return self.key2ss58address

    
    
    def parse_system_keys(self, key_path: str):
        files = os.listdir(key_path)
        for file in files:
            filename = file.split(".")[0]
            if filename == "" or filename is None:
                filename = "none"
            file_path = Path(os.path.join(key_path, file))
            if file_path.suffix == ".json":
                data: Dict = json.loads(file_path.read_text(encoding="utf-8"))
                self.keyring[filename] = data["data"]
                self.key2ss58address[filename] = data["ss58_address"]
                self.key2mnemonic[filename] = data["mnemonic"]
    