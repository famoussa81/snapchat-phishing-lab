# Snapchat Phishing Lab — Purple Team

**Version :** 2.0  
**Usage :** Etude de sensibilisation utilisateur — recherches ethiques uniquement

## Avertissement legal

INTERDIT STRICTEMENT :
- Tester un site/service sans autorisation ecrite du proprietaire
- Capturer des donnees appartenant a de vrais utilisateurs
- Diffuser les identifiants collectes
- Utiliser cette infrastructure contre de vraies cibles

AUTORISE UNIQUEMENT :
- Tests sur soi-meme
- Tests sur personnes consentantes (contrat de consentement signe)
- Recherche academique en environnement isole
- Etude de sensibilisation avec debriefing complet

## Prerequis

- Python 3.8+
- pip

## Installation

```
pip install -r requirements.txt
python launcher.py
```

## Structure

```
snapchat-phishing-lab/
├── launcher.py              ← Interface menu interactif + Cloudflare tunnel
├── main.py                  ← Serveur Flask + routes + API + capture DB
├── requirements.txt         ← Dependances
├── templates/
│   ├── bait.html            ← Page d'appat Snapchat+ (point d'entree /)
│   ├── login.html           ← Clone page email Snapchat (capture)
│   ├── password.html        ← Clone page mot de passe Snapchat (capture)
│   ├── redirect.html        ← Ecran de transition apres capture
│   └── debrief.html         ← Page de debriefing post-test
├── static/css/              ← Styles clones (CSS Snapchat)
├── static/js/               ← Scripts clones (JS Snapchat)
├── static/images/           ← Icons et favicons
├── captured_credentials.db  ← Base SQLite (creee au premier lancement)
└── cloudflared.exe          ← Binaire tunnel Cloudflare (auto-download)
```

## Utilisation

1. `python launcher.py`
2. Menu : [1] Lancer le serveur local
3. Menu : [3] Lancer + tunnel Cloudflare (expose sur internet)
4. Envoyer l'URL Cloudflare aux participants
5. Observer les captures en temps reel via [4] Watch Live

Le flux : `/` (appat Snapchat+) → `/login` (clone email) → `/password` (clone mot de passe) → `/debrief`

## Configuration

Variables d'environnement (optionnelles) :
- `SNAPCHAT_LAB_ADMIN_KEY` : Cle admin pour les endpoints /reset, /export, /v2/*
- `SNAPCHAT_LAB_DASHBOARD_PW` : Mot de passe du tableau de bord (launcher)

HTTPS : Active par defaut (certificat auto-signe genere via cryptography).
Desactiver avec `USE_HTTPS: False` dans main.py.

## Endpoints API

| Point | Methode | Role |
|-------|---------|------|
| `GET /` | — | Page d'appat Snapchat+ |
| `GET /login` | — | Clone page email |
| `GET /password` | — | Clone page mot de passe |
| `GET /debrief` | — | Debriefing post-test |
| `POST /api/capture` | JSON | Capture des identifiants + fingerprints |
| `GET /api/report` | — | Dashboard statistique |
| `GET /api/log` | POST | Tracking (vues, clics) |
| `POST /api/consent` | JSON | Enregistre consentement |
| `GET /export?key=ADMIN_KEY` | — | Export anonymise JSON |
| `GET /reset?key=ADMIN_KEY` | GET/POST | Reinitialisation (confirmation requise) |

## Licence

MIT — Usage ethique uniquement
