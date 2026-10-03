import os
from cryptography.fernet import Fernet

FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise RuntimeError("FERNET_KEY env var must be set (use a 32-byte base64 key)")

fernet = Fernet(FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY)

def encrypt_secret(plaintext: str) -> str:
    return fernet.encrypt(plaintext.encode()).decode()

def decrypt_secret(token: str) -> str:
    if not token:
        return None
    return fernet.decrypt(token.encode()).decode()
