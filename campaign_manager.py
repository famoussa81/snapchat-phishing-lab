import os
import sys
import sqlite3
import json
import time
import uuid
import threading
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    from config import CONFIG
except ImportError:
    CONFIG = {}

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    R = Fore.RED
    G = Fore.GREEN
    Y = Fore.YELLOW
    C = Fore.CYAN
    M = Fore.MAGENTA
    B = Fore.BLUE
    X = Fore.RESET
    D = Style.DIM
except ImportError:
    R = G = Y = C = M = B = X = D = ""

CAMPAIGN_DB = os.path.join(BASE_DIR, "campaigns.db")

def init_campaign_db():
    conn = sqlite3.connect(CAMPAIGN_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns (
        id TEXT PRIMARY KEY,
        name TEXT,
        template TEXT,
        subject TEXT,
        smtp_server TEXT,
        status TEXT DEFAULT 'draft',
        targets_count INTEGER DEFAULT 0,
        sent_count INTEGER DEFAULT 0,
        opened_count INTEGER DEFAULT 0,
        clicked_count INTEGER DEFAULT 0,
        created_at TEXT,
        scheduled_at TEXT,
        sent_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS campaign_targets (
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        email TEXT,
        first_name TEXT,
        last_name TEXT,
        custom_data TEXT,
        sent INTEGER DEFAULT 0,
        opened INTEGER DEFAULT 0,
        clicked INTEGER DEFAULT 0,
        sent_at TEXT,
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
    )''')
    conn.commit()
    conn.close()

class Campaign:
    def __init__(self, name=None, template=None, subject=None, smtp_server=None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.template = template
        self.subject = subject
        self.smtp_server = smtp_server
        self.status = 'draft'
        self.targets = []
        self.targets_count = 0
        self.sent_count = 0
        self.opened_count = 0
        self.clicked_count = 0
        self.created_at = datetime.now().isoformat()
        self.scheduled_at = None
        self.sent_at = None

    def add_target(self, email, first_name="", last_name="", custom_data=None):
        target = {
            'id': str(uuid.uuid4()),
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'custom_data': custom_data or {},
            'sent': 0,
            'opened': 0,
            'clicked': 0
        }
        self.targets.append(target)
        self.targets_count = len(self.targets)
        return target

    def import_csv(self, filepath):
        count = 0
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip()
                if not email:
                    continue
                first_name = row.get('first_name', row.get('firstname', '')).strip()
                last_name = row.get('last_name', row.get('lastname', '')).strip()
                custom = {k: v for k, v in row.items() if k not in ('email', 'first_name', 'last_name', 'firstname', 'lastname')}
                self.add_target(email, first_name, last_name, custom)
                count += 1
        return count

    def load_targets_from_db(self):
        conn = sqlite3.connect(CAMPAIGN_DB)
        c = conn.cursor()
        c.execute("SELECT * FROM campaign_targets WHERE campaign_id=?", (self.id,))
        rows = c.fetchall()
        columns = [desc[0] for desc in c.description]
        self.targets = []
        for row in rows:
            target = dict(zip(columns, row))
            target['custom_data'] = json.loads(target.get('custom_data') or '{}')
            self.targets.append(target)
        self.targets_count = len(self.targets)
        conn.close()

    def save_to_db(self):
        conn = sqlite3.connect(CAMPAIGN_DB)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO campaigns
            (id, name, template, subject, smtp_server, status, targets_count, sent_count, opened_count, clicked_count, created_at, scheduled_at, sent_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (self.id, self.name, self.template, self.subject, self.smtp_server,
             self.status, self.targets_count, self.sent_count, self.opened_count,
             self.clicked_count, self.created_at, self.scheduled_at, self.sent_at))
        for t in self.targets:
            c.execute('''INSERT OR REPLACE INTO campaign_targets
                (id, campaign_id, email, first_name, last_name, custom_data, sent, opened, clicked, sent_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (t['id'], self.id, t['email'], t['first_name'], t['last_name'],
                 json.dumps(t.get('custom_data', {})), t.get('sent', 0),
                 t.get('opened', 0), t.get('clicked', 0), t.get('sent_at')))
        conn.commit()
        conn.close()

    @staticmethod
    def load_from_db(campaign_id):
        conn = sqlite3.connect(CAMPAIGN_DB)
        c = conn.cursor()
        c.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return None
        columns = [desc[0] for desc in c.description]
        data = dict(zip(columns, row))
        camp = Campaign()
        camp.id = data['id']
        camp.name = data['name']
        camp.template = data['template']
        camp.subject = data['subject']
        camp.smtp_server = data['smtp_server']
        camp.status = data['status']
        camp.targets_count = data['targets_count']
        camp.sent_count = data['sent_count']
        camp.opened_count = data['opened_count']
        camp.clicked_count = data['clicked_count']
        camp.created_at = data['created_at']
        camp.scheduled_at = data['scheduled_at']
        camp.sent_at = data['sent_at']
        camp.load_targets_from_db()
        conn.close()
        return camp

    @staticmethod
    def list_all():
        conn = sqlite3.connect(CAMPAIGN_DB)
        c = conn.cursor()
        c.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
        rows = c.fetchall()
        columns = [desc[0] for desc in c.description]
        campaigns = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return campaigns

EMAIL_TEMPLATES = {
    "alerte_securite": {
        "subject": "Alerte de securite - Connexion suspecte detectee",
        "html": """<html><body style="font-family:Arial;background:#f5f5f5;padding:20px">
<div style="max-width:600px;margin:auto;background:white;border-radius:8px;padding:30px">
<div style="text-align:center;margin-bottom:20px">
<img src="https://accounts.snapchat.com/accounts/static/images/ghost/snapchat_logo.png" alt="Snapchat" width="120"/></div>
<h2 style="color:#fffc00;">Alerte de securite</h2>
<p>Bonjour {first_name},</p>
<p>Nous avons detecte une tentative de connexion suspecte a votre compte Snapchat depuis un nouvel appareil.</p>
<p><strong>Details de la connexion:</strong></p>
<ul>
<li>Appareil: {device_info}</li>
<li>Localisation approximative: {location}</li>
<li>Date: {date}</li>
</ul>
<p>Si ce n'etait pas vous, veuillez verifier votre compte immediatement:</p>
<div style="text-align:center;margin:25px 0">
<a href="{phishing_link}" style="background:#fffc00;color:#000;padding:12px 30px;border-radius:4px;text-decoration:none;font-weight:bold">Verifier mon compte</a></div>
<p style="color:#999;font-size:12px">Snapchat Inc., 2772 Donald Douglas Loop North, Santa Monica, CA 90405</p></div></body></html>"""
    },
    "snapchat_plus": {
        "subject": "Votre abonnement Snapchat+ est expire",
        "html": """<html><body style="font-family:Arial;background:#f5f5f5;padding:20px">
<div style="max-width:600px;margin:auto;background:white;border-radius:8px;padding:30px">
<div style="text-align:center;margin-bottom:20px">
<img src="https://accounts.snapchat.com/accounts/static/images/ghost/snapchat_logo.png" alt="Snapchat" width="120"/></div>
<h2 style="color:#fffc00;">Snapchat+ - Renouvellement</h2>
<p>Salut {first_name},</p>
<p>Votre abonnement Snapchat+ arrive a expiration le {expiry_date}.</p>
<p>Pour continuer a profiter de vos fonctionnalites exclusives:</p>
<ul>
<li>Story Rewatch Count</li>
<li>Best Friends Forever</li>
<li>Snapchat Plus Badge</li>
<li>Priorite des stories</li>
</ul>
<div style="text-align:center;margin:25px 0">
<a href="{phishing_link}" style="background:#fffc00;color:#000;padding:12px 30px;border-radius:4px;text-decoration:none;font-weight:bold">Reactiver mon abonnement</a></div>
<p style="color:#999;font-size:12px">Snapchat Inc., 2772 Donald Douglas Loop North, Santa Monica, CA 90405</p></div></body></html>"""
    },
    "verif_compte": {
        "subject": "Action requise: Verifiez votre compte Snapchat",
        "html": """<html><body style="font-family:Arial;background:#f5f5f5;padding:20px">
<div style="max-width:600px;margin:auto;background:white;border-radius:8px;padding:30px">
<div style="text-align:center;margin-bottom:20px">
<img src="https://accounts.snapchat.com/accounts/static/images/ghost/snapchat_logo.png" alt="Snapchat" width="120"/></div>
<h2 style="color:#fffc00;">Verification de compte</h2>
<p>Cher {first_name},</p>
<p>Pour des raisons de securite, nous vous demandons de verifier votre compte Snapchat.</p>
<p>Veuillez cliquer sur le lien ci-dessous pour confirmer votre identite:</p>
<div style="text-align:center;margin:25px 0">
<a href="{phishing_link}" style="background:#fffc00;color:#000;padding:12px 30px;border-radius:4px;text-decoration:none;font-weight:bold">Verifier mon identite</a></div>
<p style="color:#999;font-size:12px">Snapchat Inc., 2772 Donald Douglas Loop North, Santa Monica, CA 90405</p></div></body></html>"""
    },
    "compte_desactive": {
        "subject": "Votre compte Snapchat a ete desactive",
        "html": """<html><body style="font-family:Arial;background:#f5f5f5;padding:20px">
<div style="max-width:600px;margin:auto;background:white;border-radius:8px;padding:30px">
<div style="text-align:center;margin-bottom:20px">
<img src="https://accounts.snapchat.com/accounts/static/images/ghost/snapchat_logo.png" alt="Snapchat" width="120"/></div>
<h2 style="color:#fffc00;">Compte desactive</h2>
<p>Bonjour {first_name},</p>
<p>Votre compte Snapchat a ete temporairement desactive suite a une violation presumee de nos conditions d'utilisation.</p>
<p>Si vous pensez qu'il s'agit d'une erreur, vous pouvez faire appel:</p>
<div style="text-align:center;margin:25px 0">
<a href="{phishing_link}" style="background:#fffc00;color:#000;padding:12px 30px;border-radius:4px;text-decoration:none;font-weight:bold">Faire appel</a></div>
<p style="color:#999;font-size:12px">Snapchat Inc., 2772 Donald Douglas Loop North, Santa Monica, CA 90405</p></div></body></html>"""
    },
    "nouvel_appareil": {
        "subject": "Nouvel appareil connecte a votre compte",
        "html": """<html><body style="font-family:Arial;background:#f5f5f5;padding:20px">
<div style="max-width:600px;margin:auto;background:white;border-radius:8px;padding:30px">
<div style="text-align:center;margin-bottom:20px">
<img src="https://accounts.snapchat.com/accounts/static/images/ghost/snapchat_logo.png" alt="Snapchat" width="120"/></div>
<h2 style="color:#fffc00;">Nouvel appareil detecte</h2>
<p>Bonjour {first_name},</p>
<p>Un nouvel appareil a ete connecte a votre compte Snapchat.</p>
<p><strong>Appareil:</strong> {device_name}</p>
<p><strong>Navigateur:</strong> {browser}</p>
<p><strong>IP:</strong> {ip_address}</p>
<p>Si vous ne reconnaissez pas cet appareil, securisez votre compte:</p>
<div style="text-align:center;margin:25px 0">
<a href="{phishing_link}" style="background:#fffc00;color:#000;padding:12px 30px;border-radius:4px;text-decoration:none;font-weight:bold">Securiser mon compte</a></div>
<p style="color:#999;font-size:12px">Snapchat Inc., 2772 Donald Douglas Loop North, Santa Monica, CA 90405</p></div></body></html>"""
    }
}

SMTP_SERVERS = {
    "gmail": {"host": "smtp.gmail.com", "port": 587, "use_tls": True},
    "outlook": {"host": "smtp-mail.outlook.com", "port": 587, "use_tls": True},
    "yahoo": {"host": "smtp.mail.yahoo.com", "port": 587, "use_tls": True},
    "local_25": {"host": "127.0.0.1", "port": 25, "use_tls": False},
    "local_587": {"host": "127.0.0.1", "port": 587, "use_tls": False}
}

def send_email_to_target(target, campaign, smtp_user, smtp_pass, phishing_link):
    template = EMAIL_TEMPLATES.get(campaign.template)
    if not template:
        return False
    html = template['html'].format(
        first_name=target['first_name'] or 'Utilisateur',
        phishing_link=phishing_link,
        device_info="iPhone 15 Pro, iOS 18.3",
        location="Paris, France",
        date=datetime.now().strftime("%d/%m/%Y %H:%M"),
        expiry_date=(datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y"),
        device_name="Chrome sur Windows 11",
        browser="Chrome 120.0",
        ip_address="192.168.1.100"
    )
    subject = template['subject']
    if campaign.subject:
        subject = campaign.subject
    msg = MIMEMultipart('alternative')
    msg['From'] = smtp_user
    msg['To'] = target['email']
    msg['Subject'] = subject
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    try:
        server_config = SMTP_SERVERS.get(campaign.smtp_server, SMTP_SERVERS['local_25'])
        if server_config['use_tls']:
            server = smtplib.SMTP(server_config['host'], server_config['port'], timeout=10)
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
        else:
            server = smtplib.SMTP(server_config['host'], server_config['port'], timeout=10)
        server.sendmail(smtp_user, [target['email']], msg.as_string())
        server.quit()
        return True
    except Exception:
        return False

def send_bulk(campaign_id, smtp_user, smtp_pass, phishing_link, delay=1):
    camp = Campaign.load_from_db(campaign_id)
    if not camp:
        return
    camp.status = 'sending'
    camp.save_to_db()
    sent = 0
    failed = 0
    total = len(camp.targets)
    for target in camp.targets:
        if target.get('sent'):
            sent += 1
            continue
        success = send_email_to_target(target, camp, smtp_user, smtp_pass, phishing_link)
        if success:
            target['sent'] = 1
            target['sent_at'] = datetime.now().isoformat()
            sent += 1
        else:
            failed += 1
        camp.sent_count = sent
        camp.save_to_db()
        time.sleep(delay)
    camp.status = 'completed' if failed == 0 else 'partial'
    camp.sent_at = datetime.now().isoformat()
    camp.save_to_db()

class CampaignScheduler:
    def __init__(self):
        self.timers = []

    def schedule(self, campaign_id, send_at, smtp_user, smtp_pass, phishing_link, delay=1):
        now = datetime.now()
        if isinstance(send_at, str):
            send_at = datetime.fromisoformat(send_at)
        delay_sec = (send_at - now).total_seconds()
        if delay_sec < 0:
            return False
        def _send():
            send_bulk(campaign_id, smtp_user, smtp_pass, phishing_link, delay)
            conn = sqlite3.connect(CAMPAIGN_DB)
            c = conn.cursor()
            c.execute("UPDATE campaigns SET scheduled_at=? WHERE id=?", (send_at.isoformat(), campaign_id))
            conn.commit()
            conn.close()
        t = threading.Timer(delay_sec, _send)
        t.daemon = True
        t.start()
        self.timers.append(t)
        return True

    def cancel_all(self):
        for t in self.timers:
            t.cancel()
        self.timers = []

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print(f"""{Y}
  +========================================+
  |        SNAPCHAT PHISHING LAB           |
  |         Campaign Manager v1.0          |
  +========================================+
    """)

def interactive_menu():
    while True:
        clear_screen()
        print_banner()
        print(f"{C}[1]{X} Create campaign")
        print(f"{C}[2]{X} List campaigns")
        print(f"{C}[3]{X} Launch campaign now")
        print(f"{C}[4]{X} Import targets from CSV")
        print(f"{C}[5]{X} Schedule campaign")
        print(f"{C}[6]{X} Campaign stats")
        print(f"{C}[0]{X} Back")
        print()
        choice = input(f"{Y}> {X}").strip()
        if choice == '1':
            print(f"\n{G}[+] Create Campaign{X}")
            name = input("Campaign name: ").strip()
            print("\nTemplates:")
            for i, k in enumerate(EMAIL_TEMPLATES, 1):
                print(f"  {i}. {k}")
            t_idx = input("Template number: ").strip()
            try:
                t_key = list(EMAIL_TEMPLATES.keys())[int(t_idx)-1]
            except Exception:
                print(f"{R}Invalid choice{X}")
                input("Press Enter...")
                continue
            print("\nSMTP Servers:")
            for i, k in enumerate(SMTP_SERVERS, 1):
                print(f"  {i}. {k}")
            s_idx = input("SMTP server number: ").strip()
            try:
                s_key = list(SMTP_SERVERS.keys())[int(s_idx)-1]
            except Exception:
                print(f"{R}Invalid choice{X}")
                input("Press Enter...")
                continue
            subject = input("Custom subject (optional): ").strip()
            camp = Campaign(name=name, template=t_key, subject=subject or None, smtp_server=s_key)
            camp.save_to_db()
            print(f"{G}[+] Campaign '{name}' created with ID: {camp.id}{X}")
            input("Press Enter...")
        elif choice == '2':
            camps = Campaign.list_all()
            if not camps:
                print(f"{Y}[!] No campaigns yet{X}")
            else:
                for c in camps:
                    print(f"  {C}{c['id'][:8]}...{X} | {c['name']} | {c['status']} | {c['targets_count']} targets | {c['sent_count']} sent")
            input("Press Enter...")
        elif choice == '3':
            camps = Campaign.list_all()
            if not camps:
                print(f"{Y}[!] No campaigns{X}")
                input("Press Enter...")
                continue
            for i, c in enumerate(camps, 1):
                print(f"  {i}. {c['name']} ({c['status']})")
            idx = input("Campaign number: ").strip()
            try:
                camp_data = camps[int(idx)-1]
            except Exception:
                print(f"{R}Invalid{X}")
                input("Press Enter...")
                continue
            smtp_user = input("SMTP username: ").strip()
            smtp_pass = input("SMTP password: ").strip()
            ph_link = input("Phishing link: ").strip()
            try:
                delay = int(input("Delay between emails (seconds) [1]: ").strip() or "1")
            except Exception:
                delay = 1
            print(f"{G}[+] Launching campaign...{X}")
            send_bulk(camp_data['id'], smtp_user, smtp_pass, ph_link, delay)
            print(f"{G}[+] Campaign finished{X}")
            input("Press Enter...")
        elif choice == '4':
            camps = Campaign.list_all()
            if not camps:
                print(f"{Y}[!] No campaigns{X}")
                input("Press Enter...")
                continue
            for i, c in enumerate(camps, 1):
                print(f"  {i}. {c['name']}")
            idx = input("Campaign number: ").strip()
            try:
                camp_data = camps[int(idx)-1]
            except Exception:
                print(f"{R}Invalid{X}")
                input("Press Enter...")
                continue
            csv_path = input("CSV file path: ").strip()
            camp = Campaign.load_from_db(camp_data['id'])
            count = camp.import_csv(csv_path)
            camp.save_to_db()
            print(f"{G}[+] Imported {count} targets{X}")
            input("Press Enter...")
        elif choice == '5':
            camps = Campaign.list_all()
            if not camps:
                print(f"{Y}[!] No campaigns{X}")
                input("Press Enter...")
                continue
            for i, c in enumerate(camps, 1):
                print(f"  {i}. {c['name']} ({c['status']})")
            idx = input("Campaign number: ").strip()
            try:
                camp_data = camps[int(idx)-1]
            except Exception:
                print(f"{R}Invalid{X}")
                input("Press Enter...")
                continue
            dt_str = input("Send date/time (YYYY-MM-DD HH:MM): ").strip()
            try:
                send_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            except Exception:
                print(f"{R}Invalid date format{X}")
                input("Press Enter...")
                continue
            smtp_user = input("SMTP username: ").strip()
            smtp_pass = input("SMTP password: ").strip()
            ph_link = input("Phishing link: ").strip()
            scheduler = CampaignScheduler()
            scheduler.schedule(camp_data['id'], send_at, smtp_user, smtp_pass, ph_link)
            print(f"{G}[+] Campaign scheduled for {dt_str}{X}")
            input("Press Enter...")
        elif choice == '6':
            camps = Campaign.list_all()
            if not camps:
                print(f"{Y}[!] No campaigns{X}")
                input("Press Enter...")
                continue
            for i, c in enumerate(camps, 1):
                print(f"  {i}. {c['name']}")
            idx = input("Campaign number: ").strip()
            try:
                camp_data = camps[int(idx)-1]
            except Exception:
                print(f"{R}Invalid{X}")
                input("Press Enter...")
                continue
            camp = Campaign.load_from_db(camp_data['id'])
            print(f"\n{C}Campaign Stats{X}")
            print(f"  Name: {camp.name}")
            print(f"  Status: {camp.status}")
            print(f"  Template: {camp.template}")
            print(f"  Total targets: {camp.targets_count}")
            print(f"  Sent: {camp.sent_count}")
            print(f"  Opened: {camp.opened_count}")
            print(f"  Clicked: {camp.clicked_count}")
            print(f"  Created: {camp.created_at}")
            if camp.scheduled_at:
                print(f"  Scheduled: {camp.scheduled_at}")
            if camp.sent_at:
                print(f"  Sent at: {camp.sent_at}")
            input("Press Enter...")
        elif choice == '0':
            break

if __name__ == "__main__":
    init_campaign_db()
    interactive_menu()
