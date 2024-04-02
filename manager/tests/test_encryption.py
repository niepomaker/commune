# Example usage
json_obj = {"name": "John", "age": 30, "city": "New York"}
password = "mysecurepassword"

encrypted = encrypt_json(json_obj, password)
print("Encrypted Data:", encrypted)

decrypted = decrypt_json(encrypted, password)
print("Decrypted JSON:", decrypted)``