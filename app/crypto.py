import base64
import hashlib
from cryptography.fernet import Fernet
from .config import CONFIG


def _get_fernet():
    key = base64.urlsafe_b64encode(hashlib.sha256(CONFIG["ADMIN_KEY"].encode()).digest())
    return Fernet(key)


def encrypt_password(password):
    if not password:
        return password
    try:
        return _get_fernet().encrypt(password.encode()).decode()
    except:
        return password


def decrypt_password(encrypted):
    if not encrypted:
        return encrypted
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except:
        return encrypted
