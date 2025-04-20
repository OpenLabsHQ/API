import base64
import os
from typing import Dict, Tuple

from argon2.low_level import Type, hash_secret_raw
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ed25519
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

# RSA Key Generation
def generate_rsa_key_pair() -> Tuple[str, str]:
    """Generate an RSA key pair and return base64 encoded strings."""
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    public_key = private_key.public_key()

    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Encode to base64 for storage
    private_b64 = base64.b64encode(private_pem).decode("utf-8")
    public_b64 = base64.b64encode(public_pem).decode("utf-8")

    return private_b64, public_b64

# ed25519 Key Generation
def generate_ed25519_key_pair() -> Tuple[str, str]:
    """Generate an ed25519 key pair and return base64 encoded strings."""
    private_key = ed25519.Ed25519PrivateKey.generate()

    public_key = private_key.public_key()

    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public keyin OpenSSH format
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )

    # Decode bytes to strings
    private_key_str = private_pem.decode("utf-8")
    public_key_str = public_pem.decode("utf-8")

    return private_key_str, public_key_str

# Master Key Generation using Argon2
def generate_master_key(
    password: str, salt: bytes | None = None
) -> Tuple[bytes, bytes]:
    """Generate a master key using Argon2 from a password."""
    if salt is None:
        salt = os.urandom(16)

    # Generate a raw hash to use as a key
    key = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=3,  # Number of iterations
        memory_cost=65536,  # Memory usage in kibibytes (64 MB)
        parallelism=4,  # Number of parallel threads
        hash_len=32,  # Length of the hash
        type=Type.ID,  # Argon2id variant
    )

    return key, salt


# Encrypt the RSA private key with the master key
def encrypt_private_key(private_key_b64: str, master_key: bytes) -> str:
    """Encrypt the RSA private key using the master key."""
    private_key_bytes = base64.b64decode(private_key_b64)

    # Create a Fernet instance with the master key
    fernet_key = base64.urlsafe_b64encode(master_key)
    fernet = Fernet(fernet_key)

    # Encrypt the private key
    encrypted_key = fernet.encrypt(private_key_bytes)

    # Encode to base64 for storage and return
    return base64.b64encode(encrypted_key).decode("utf-8")


# Decrypt the RSA private key with the master key
def decrypt_private_key(encrypted_key_b64: str, master_key: bytes) -> str:
    """Decrypt the RSA private key using the master key."""
    encrypted_key = base64.b64decode(encrypted_key_b64)

    # Create a Fernet instance with the master key
    fernet_key = base64.urlsafe_b64encode(master_key)
    fernet = Fernet(fernet_key)

    # Decrypt the private key
    private_key_bytes = fernet.decrypt(encrypted_key)

    # Encode to base64 and return
    return base64.b64encode(private_key_bytes).decode("utf-8")


# Encrypt data with RSA public key
def encrypt_with_public_key(
    data: Dict[str, str], public_key_b64: str
) -> Dict[str, str]:
    """Encrypt a dictionary of string data using the RSA public key."""
    public_key_bytes = base64.b64decode(public_key_b64)
    loaded_key: RSAPublicKey = serialization.load_pem_public_key(  # type: ignore
        public_key_bytes, backend=default_backend()
    )
    public_key = loaded_key

    encrypted_data = {}

    for key, value in data.items():
        if value:  # Only encrypt non-empty values
            # Convert string to bytes
            value_bytes = value.encode("utf-8")

            # Encrypt with public key
            encrypted_value = public_key.encrypt(
                value_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            # Encode to base64 for storage
            encrypted_data[key] = base64.b64encode(encrypted_value).decode("utf-8")
        else:
            encrypted_data[key] = ""  # Keep empty values as empty

    return encrypted_data


# Decrypt data with RSA private key
def decrypt_with_private_key(
    encrypted_data: Dict[str, str], private_key_b64: str
) -> Dict[str, str]:
    """Decrypt a dictionary of encrypted data using the RSA private key."""
    private_key_bytes = base64.b64decode(private_key_b64)
    loaded_key: RSAPrivateKey = serialization.load_pem_private_key(  # type: ignore
        private_key_bytes, password=None, backend=default_backend()
    )
    private_key = loaded_key

    decrypted_data = {}

    for key, value in encrypted_data.items():
        if value:  # Only decrypt non-empty values
            # Decode from base64
            encrypted_value = base64.b64decode(value)

            # Decrypt with private key
            decrypted_value = private_key.decrypt(
                encrypted_value,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            decrypted_data[key] = decrypted_value.decode("utf-8")
        else:
            decrypted_data[key] = ""  # Keep empty values as empty

    return decrypted_data
