import os
from cryptography.fernet import Fernet
import json
from dotenv import load_dotenv

load_dotenv()

def get_cipher():
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY not found in .env")
    # Clean up the key string if it was surrounded by quotes and b'' in .env
    key = key.strip('"').strip("'")
    if key.startswith("b'") and key.endswith("'"):
        key = key[2:-1]
    return Fernet(key.encode('utf-8'))

def encrypt_embedding(embedding_list):
    """Encrypts a list of floats (embedding)"""
    cipher = get_cipher()
    # Convert embedding to JSON string then to bytes
    embedding_bytes = json.dumps(embedding_list).encode('utf-8')
    encrypted_data = cipher.encrypt(embedding_bytes)
    return encrypted_data

def decrypt_embedding(encrypted_data):
    """Decrypts bytes into a list of floats"""
    cipher = get_cipher()
    decrypted_bytes = cipher.decrypt(encrypted_data)
    embedding_list = json.loads(decrypted_bytes.decode('utf-8'))
    return embedding_list
