from src.key_objects import KeyManager


key_manager = KeyManager()
key_manager.load_keys("some password", "/home/bakobi/.commune/key")
keys = key_manager.get_keys()
