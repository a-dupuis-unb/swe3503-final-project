import base64
import os
from typing import Union, Any
import json

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def generate_key() -> bytes:
    """
    Generate a new encryption key for AES-256-GCM.
    
    Returns:
        bytes: A 32-byte key suitable for AES-256-GCM encryption.
    """
    return AESGCM.generate_key(bit_length=256)


def encrypt_key_with_master_key(user_key: bytes, master_key: str) -> str:
    """
    Encrypt a user's encryption key with the master key using Fernet.
    
    Args:
        user_key (bytes): The user's encryption key to be encrypted.
        master_key (str): The master key used for encryption.
        
    Returns:
        str: Encrypted key as a base64-encoded string.
    """
    # Derive a Fernet key from the master key
    salt = b'static_salt_for_key_derivation'  # In production, use a unique salt per application
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    fernet_key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    
    # Use Fernet for encrypting the user key
    f = Fernet(fernet_key)
    encrypted_key = f.encrypt(user_key)
    return encrypted_key.decode('utf-8')


def decrypt_key_with_master_key(encrypted_key: str, master_key: str) -> bytes:
    """
    Decrypt a user's encryption key with the master key.
    
    Args:
        encrypted_key (str): The encrypted user key as a base64-encoded string.
        master_key (str): The master key used for decryption.
        
    Returns:
        bytes: The decrypted user encryption key.
    """
    # Derive the same Fernet key from the master key
    salt = b'static_salt_for_key_derivation'  # Use the same salt as encrypt_key_with_master_key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    fernet_key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    
    # Use Fernet for decrypting the user key
    f = Fernet(fernet_key)
    decrypted_key = f.decrypt(encrypted_key.encode('utf-8'))
    return decrypted_key


def encrypt_to_string(data: Any, key: bytes) -> str:
    """
    Encrypt data using AES-256-GCM and return as a base64 encoded string.
    
    Args:
        data (Any): The data to encrypt (will be converted to JSON).
        key (bytes): The 32-byte AES-256-GCM key.
        
    Returns:
        str: The encrypted data as a base64-encoded string with nonce prepended.
    """
    # Convert data to JSON string and then to bytes
    data_bytes = json.dumps(data).encode('utf-8')
    
    # Generate a random 96-bit IV/nonce (12 bytes)
    nonce = os.urandom(12)
    
    # Create an AESGCM instance with the key
    aesgcm = AESGCM(key)
    
    # Encrypt the data
    # We're using an empty associated_data here, but in real applications 
    # you might want to include some context data
    ciphertext = aesgcm.encrypt(nonce, data_bytes, associated_data=b'')
    
    # Combine nonce and ciphertext, and encode as base64
    encrypted_data = base64.b64encode(nonce + ciphertext).decode('utf-8')
    
    return encrypted_data


def decrypt_to_string(encrypted_data: str, key: bytes) -> str:
    """
    Decrypt data encrypted with AES-256-GCM and return as a string.
    
    Args:
        encrypted_data (str): The encrypted data as a base64-encoded string.
        key (bytes): The 32-byte AES-256-GCM key.
        
    Returns:
        str: The decrypted data as a string.
    """
    # Decode the base64 string to get combined nonce and ciphertext
    decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
    
    # Extract nonce (first 12 bytes) and ciphertext
    nonce = decoded_data[:12]
    ciphertext = decoded_data[12:]
    
    # Create an AESGCM instance with the key
    aesgcm = AESGCM(key)
    
    # Decrypt the data
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=b'')
    
    # Convert bytes to JSON and then parse
    result = json.loads(plaintext.decode('utf-8'))
    
    # If the result is a string, return it directly, otherwise convert it back to JSON
    if isinstance(result, str):
        return result
    return json.dumps(result)


def decrypt_to_numeric(encrypted_data: str, key: bytes) -> Union[int, float]:
    """
    Decrypt data encrypted with AES-256-GCM and return as a numeric value.
    
    Args:
        encrypted_data (str): The encrypted data as a base64-encoded string.
        key (bytes): The 32-byte AES-256-GCM key.
        
    Returns:
        Union[int, float]: The decrypted data as a numeric value.
    """
    # Decode and decrypt using the decrypt_to_string function
    decrypted_str = decrypt_to_string(encrypted_data, key)
    
    # Convert string to numeric value
    try:
        # Try converting to int first
        return int(decrypted_str)
    except ValueError:
        # If not an int, try converting to float
        return float(decrypted_str)

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


def generate_key() -> bytes:
    """
    Generate a random encryption key suitable for AES-256-GCM.
    
    Returns:
        bytes: A 32-byte random key
    """
    return os.urandom(32)  # 32 bytes = 256 bits


def encrypt_data(key: bytes, data: str) -> str:
    """
    Encrypt data using AES-256-GCM.
    
    Args:
        key: 32-byte encryption key
        data: String data to encrypt
    
    Returns:
        str: Base64-encoded encrypted data with nonce
    """
    # Convert string data to bytes
    data_bytes = data.encode('utf-8')
    
    # Generate a random 96-bit IV/nonce (12 bytes)
    nonce = os.urandom(12)
    
    # Create an AES-GCM cipher with the provided key
    cipher = AESGCM(key)
    
    # Encrypt the data
    ciphertext = cipher.encrypt(nonce, data_bytes, None)
    
    # Combine nonce and ciphertext for storage
    encrypted_data = nonce + ciphertext
    
    # Return base64 encoded string for easy storage
    return base64.b64encode(encrypted_data).decode('utf-8')


def decrypt_data(key: bytes, encrypted_data: str) -> str:
    """
    Decrypt data using AES-256-GCM.
    
    Args:
        key: 32-byte encryption key
        encrypted_data: Base64-encoded encrypted data with nonce
    
    Returns:
        str: Decrypted data as string
    """
    # Decode the base64 encoded encrypted data
    encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
    
    # Extract nonce (first 12 bytes) and ciphertext
    nonce = encrypted_bytes[:12]
    ciphertext = encrypted_bytes[12:]
    
    # Create AES-GCM cipher with the provided key
    cipher = AESGCM(key)
    
    # Decrypt the data
    plaintext = cipher.decrypt(nonce, ciphertext, None)
    
    # Return the decrypted data as a string
    return plaintext.decode('utf-8')


def encrypt_key(master_key: bytes, user_key: bytes) -> str:
    """
    Encrypt a user's encryption key with a master key.
    
    Args:
        master_key: The master encryption key (32 bytes)
        user_key: The user's encryption key to encrypt (32 bytes)
    
    Returns:
        str: Base64-encoded encrypted user key
    """
    # Use the same AES-GCM encryption function
    return encrypt_data(master_key, base64.b64encode(user_key).decode('utf-8'))


def decrypt_key(master_key: bytes, encrypted_user_key: str) -> bytes:
    """
    Decrypt a user's encryption key using the master key.
    
    Args:
        master_key: The master encryption key (32 bytes)
        encrypted_user_key: Base64-encoded encrypted user key
    
    Returns:
        bytes: Decrypted user encryption key
    """
    # Decrypt the encrypted user key
    decrypted_key_b64 = decrypt_data(master_key, encrypted_user_key)
    
    # Convert from base64 string back to bytes
    return base64.b64decode(decrypted_key_b64.encode('utf-8'))


def derive_key_from_password(password: str, salt: bytes = None) -> tuple:
    """
    Derive an encryption key from a password using PBKDF2.
    Useful for generating a key from a user's password.
    
    Args:
        password: User password
        salt: Salt for key derivation (generated if not provided)
    
    Returns:
        tuple: (derived_key, salt)
    """
    if salt is None:
        salt = os.urandom(16)
    
    # Use PBKDF2 to derive a key from the password
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes = 256 bits
        salt=salt,
        iterations=100000,  # Recommended minimum is 100,000
        backend=default_backend()
    )
    
    # Derive key from password
    key = kdf.derive(password.encode('utf-8'))
    
    return key, salt


def bytes_to_base64_str(data: bytes) -> str:
    """
    Convert bytes to a base64-encoded string.
    
    Args:
        data: Bytes to convert
    
    Returns:
        str: Base64-encoded string
    """
    return base64.b64encode(data).decode('utf-8')


def base64_str_to_bytes(data_str: str) -> bytes:
    """
    Convert a base64-encoded string back to bytes.
    
    Args:
        data_str: Base64-encoded string
    
    Returns:
        bytes: Decoded bytes
    """
    return base64.b64decode(data_str.encode('utf-8'))

