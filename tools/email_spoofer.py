import os
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE, "output_emails")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEMPLATES = {
    "1": {
        "name": "Alerte de securite Snapchat",
        "subject": "Alerte de securite - Nouvelle connexion detectee",
        "sender": "security@snapchat.com",
        "body": """Bonjour,

Nous avons detecte une tentative de connexion suspecte à votre compte Snapchat depuis un nouvel appareil.

Localisation approximative : Paris, France
Date : {date}
Navigateur : Chrome / Windows

Si vous n'etes pas à l'origine de cette connexion, securisez votre compte immediatement :

{lien}

Equipe securite Snapchat
(c) Snapchat Security
"""
    },
    "2": {
        "name": "Snapchat+ - Acces anticipe gratuit",
        "subject": "Vous avez ete selectionne pour Snapchat+ gratuit !",
        "sender": "snapchat-plus@snapchat.com",
        "body": """Felicitations !

Vous faites partie des 1 000 utilisateurs selectionnes pour tester Snapchat+ en avant-premiere, totalement gratuitement pendant 3 mois.

- Stickers exclusifs
- Vues illimitees des stories
- Badge Snapchat+ verifie
- Replay illimite

Activez votre acces ici (offre limitee) :

{lien}

L'offre expire dans 48h.
Snapchat+ Team
"""
    },
    "3": {
        "name": "Verification compte requise",
        "subject": "Action requise - Verification de votre compte Snapchat",
        "sender": "support@snapchat.com",
        "body": """Bonjour,

Suite à une mise à jour de nos conditions d'utilisation, nous vous demandons de verifier votre compte pour continuer à utiliser Snapchat sans interruption.

Votre compte sera suspendu dans 24h si vous ne confirmez pas votre identite.

Verifier mon compte : {lien}

Merci de votre comprehension,
L'equipe Snapchat
"""
    },
    "4": {
        "name": "Compte desactive - Reactivation",
        "subject": "Votre compte Snapchat a ete desactive",
        "sender": "appeals@snapchat.com",
        "body": """Bonjour,

Votre compte Snapchat a ete temporairement desactive suite à une violation presumee de nos conditions d'utilisation.

Pour faire appel de cette decision et reactiver votre compte, veuillez confirmer votre identite :

{lien}

Delai de recours : 7 jours
Equipe integrite Snapchat
"""
    },
    "5": {
        "name": "Snapchat - Nouvel appareil connecte",
        "subject": "Nouvel appareil connecte à votre compte",
        "sender": "no-reply@snapchat.com",
        "body": """Bonjour {pseudo},

Un nouvel appareil s'est connecte à votre compte Snapchat :

Appareil : iPhone 15 Pro
Position approximative : {ville}
Il y a quelques minutes

Si c'etait vous, ignorez ce message.
Si ce n'etait pas vous, securisez votre compte :

{lien}

L'equipe Snapchat
"""
    }
}


def generate_eml(template_id, lien="http://localhost:8080", pseudo="Utilisateur", ville="Paris", destinataire=None):
    tpl = TEMPLATES.get(template_id)
    if not tpl:
        return None, "Template introuvable"

    body = tpl["body"].format(
        date=datetime.now().strftime("%d/%m/%Y à %H:%M"),
        lien=lien,
        pseudo=pseudo,
        ville=ville
    )

    msg = MIMEMultipart()
    exp = tpl["sender"]
    if destinataire:
        msg["To"] = destinataire
    else:
        msg["To"] = "cible@exemple.com"
    msg["From"] = f"{tpl['name']} <{exp}>"
    msg["Subject"] = tpl["subject"]
    msg.attach(MIMEText(body, "plain", "utf-8"))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_id = template_id
    filename = f"email_{safe_id}_{ts}.eml"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(msg.as_string())

    return filepath, body


def preview_template(template_id, lien="http://localhost:8080", pseudo="Utilisateur", ville="Paris"):
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
        "from": f"{tpl['name']} <{tpl['sender']}>",
        "subject": tpl["subject"],
        "body": body
    }


def interactive_menu():
    from colorama import init, Fore, Style
    init()
    R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN; M = Fore.MAGENTA; X = Style.RESET_ALL; D = Style.DIM

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(f"\n  {M}╔══════════════════════════════════════════════╗{X}")
        print(f"  {M}║      GENERATEUR .EML — Purple Team          ║{X}")
        print(f"  {M}╚══════════════════════════════════════════════╝{X}")
        print(f"  {D}Genere des fichiers .eml prets à ouvrir{X}")
        print(f"  {D}L'envoi reel necessite un service SMTP tiers.{X}")
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

        tpl = TEMPLATES[choix]
        os.system("cls" if os.name == "nt" else "clear")
        print(f"\n  {C}APERCU DU TEMPLATE :{X}")
        print(f"  {D}De :{X} {tpl['sender']}")
        print(f"  {D}Objet :{X} {tpl['subject']}")
        print(f"  {D}Message :{X}")
        print(f"  {Y}{tpl['body'].format(date='[DATE]', lien='[LIEN]', pseudo='[PSEUDO]', ville='[VILLE]')}{X}")
        print()

        lien = input(f"  {C}Lien du lab {D}(defaut: http://localhost:8080){X} > ").strip() or "http://localhost:8080"
        pseudo = input(f"  {C}Pseudo {D}(optionnel){X} > ").strip() or "Utilisateur"
        ville = input(f"  {C}Ville {D}(optionnel){X} > ").strip() or "Paris"
        destinataire = input(f"  {C}Email cible {D}(optionnel, pour le champ To){X} > ").strip()

        filepath, body = generate_eml(choix, lien, pseudo, ville, destinataire or None)

        if filepath:
            print(f"\n  {G}Fichier .eml genere :{X}")
            print(f"    {Y}{filepath}{X}")
            print(f"  {D}Ouvre-le avec Outlook / Thunderbird / ton navigateur.{X}")
        else:
            print(f"\n  {R}Erreur : {body}{X}")

        ouvrir = input(f"\n  {Y}Ouvrir le dossier ? (o/N){X} > ").strip().lower()
        if ouvrir == "o":
            if os.name == "nt":
                os.startfile(OUTPUT_DIR)
            else:
                os.system(f"xdg-open {OUTPUT_DIR}")

        input(f"\n  {D}[Appuie sur Entree]{X}")


def generate_bulk(targets, subject, body_template, url, campaign_id=None):
    results = []
    generated = 0

    for t in targets:
        try:
            tracking_params = ""
            if campaign_id and t.get('id'):
                tracking_params = "?cid={}&tid={}".format(campaign_id, t['id'])
            full_url = url + tracking_params

            body = body_template.format(
                pseudo=t.get('pseudo', 'Utilisateur'),
                ville=t.get('ville', 'Paris'),
                lien=full_url,
                date=datetime.now().strftime("%d/%m/%Y à %H:%M")
            )

            msg = MIMEMultipart()
            from_email = t.get('from_email', 'security@snapchat.com')
            from_name = t.get('from_name', 'Snapchat')
            msg["From"] = "{} <{}>".format(from_name, from_email)
            msg["To"] = t["email"]
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = "email_bulk_{}_{}.eml".format(t.get('id', 'x'), ts)
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(msg.as_string())

            results.append({"email": t["email"], "file": filepath, "ok": True})
            generated += 1
        except Exception as e:
            results.append({"email": t["email"], "ok": False, "error": str(e)})

    return generated, len(targets) - generated, results


if __name__ == "__main__":
    interactive_menu()
