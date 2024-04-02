import json
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
import base64

def encrypt_json(json_data: dict, password: str) -> dict:
    """
    Encrypts a JSON object using the AES-GCM encryption algorithm.

    Parameters:
        json_data (dict): The JSON object to be encrypted.
        password (str): The password used to generate the encryption key.

    Returns:
        dict: A dictionary containing the encrypted data, including the salt, initialization vector (IV), ciphertext, and tag.

    Raises:
        None

    Algorithm:
        1. Convert the JSON object to a string.
        2. Generate a random salt and derive the encryption key using PBKDF2.
        3. Prepare the AES-GCM cipher with the derived key.
        4. Encrypt the JSON string and generate the authentication tag.
        5. Prepare the output dictionary with the base64-encoded salt, IV, ciphertext, and tag.
        6. Return the encrypted data dictionary.

    Note:
        - The AES block size is 16 bytes.
        - The derived key length is 32 bytes.
        - The PBKDF2 iteration count is 1 million.
        - The cipher mode is GCM (Galois/Counter Mode).
        - The encrypted data is represented as a dictionary with the following keys:
            - 'salt': The base64-encoded salt.
            - 'iv': The base64-encoded initialization vector (IV).
            - 'ciphertext': The base64-encoded ciphertext.
            - 'tag': The base64-encoded authentication tag.

    Example:
        >>> data = {'name': 'John', 'age': 30}
        >>> password = 'my_password'
        >>> encrypt_json(data, password)
        {'salt': '...', 'iv': '...', 'ciphertext': '...', 'tag': '...'}
    """
    # Convert the JSON object to a string
    json_str = json.dumps(json_data)
    json_bytes = json_str.encode()

    # Generate salt and key
    salt = get_random_bytes(16)  # AES block size
    key = PBKDF2(password, salt, dkLen=32, count=1000000)  # 1 million iterations

    # Prepare cipher
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(json_bytes)

    # Prepare output (salt, iv, ciphertext, tag)
    encrypted_data = {
        'salt': base64.b64encode(salt).decode('utf-8'),
        'iv': base64.b64encode(cipher.nonce).decode('utf-8'),
        'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
        'tag': base64.b64encode(tag).decode('utf-8')
    }
    return encrypted_data


def decrypt_json(encrypted_data: dict, password: str) -> dict:
    """
    Decrypts a JSON object that was encrypted with AES-256-GCM using the provided password.

    Args:
        encrypted_data (dict): A dictionary containing the salt, iv, ciphertext, and tag of the encrypted data.
        password (str): The password used to decrypt the data.

    Returns:
        dict: The decrypted JSON object.

    Raises:
        ValueError: If the decryption process fails.
    """
    # Decode the database
    salt: bytes = base64.b64decode(encrypted_data['salt'])
    iv: bytes = base64.b64decode(encrypted_data['iv'])
    ciphertext: bytes = base64.b64decode(encrypted_data['ciphertext'])
    tag: bytes = base64.b64decode(encrypted_data['tag'])

    # Regenerate the key
    key: bytes = PBKDF2(password, salt, dkLen=32, count=1000000)  # Must match the encryption

    # Decrypt
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    decrypted_bytes: bytes = cipher.decrypt_and_verify(ciphertext, tag)
    decrypted_str: str = decrypted_bytes.decode()

    # Convert string back to JSON
    json_data: dict = json.loads(decrypted_str)

    return json_data


