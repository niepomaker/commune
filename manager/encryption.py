import json
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
import base64

def encrypt_json(json_data, password):
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

def decrypt_json(encrypted_data, password):
    # Decode the database
    salt = base64.b64decode(encrypted_data['salt'])
    iv = base64.b64decode(encrypted_data['iv'])
    ciphertext = base64.b64decode(encrypted_data['ciphertext'])
    tag = base64.b64decode(encrypted_data['tag'])

    # Regenerate the key
    key = PBKDF2(password, salt, dkLen=32, count=1000000)  # Must match the encryption

    # Decrypt
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    decrypted_bytes = cipher.decrypt_and_verify(ciphertext, tag)
    decrypted_str = decrypted_bytes.decode()

    # Convert string back to JSON
    json_data = json.loads(decrypted_str)

    return json_data

# Example usage
json_obj = {"name": "John", "age": 30, "city": "New York"}
password = "mysecurepassword"

encrypted = encrypt_json(json_obj, password)
print("Encrypted Data:", encrypted)

decrypted = decrypt_json(encrypted, password)
print("Decrypted JSON:", decrypted)
