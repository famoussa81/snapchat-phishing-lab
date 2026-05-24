# 🔬 Snapchat Phishing Lab — Étude Purple Team

**Version :** 1.0  
**Usage :** Étude de sensibilisation utilisateur — recherches éthiques uniquement  
**Avertissement :** Utilisation UNIQUEMENT sur des cibles explicitement autorisées et consentantes.

---

## ⚠️ AVERTISSEMENT LÉGAL

```
🚨 INTERDIT STRICTEMENT :
  - Tester un site/service sans autorisation écrite du propriétaire
  - Capturer des données appartenant à de vrais utilisateurs
  - Diffuser les identifiants collectés
  - Utiliser cette infrastructure contre de vraies cibles

✅ AUTORISÉ UNIQUEMENT :
  - Tests sur soi-même
  - Tests sur personnes consentantes (contrat de consentement signé)
  - Recherche académique en environnement isolé
  - Étude de sensibilisation avec debriefing complet
```

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Installation en 60 secondes](#installation-en-60-secondes)
4. [Structure du projet](#structure-du-projet)
5. [Configuration](#configuration)
6. [Utilisation pas à pas](#utilisation-pas-à-pas)
7. [Métriques et Analyse](#métriques-et-analyse)
8. [Cadre éthique RGPD](#cadre-éthique-rgpd)
9. [Extensibilité](#extensibilité)
10. [Dépannage](#dépannage)

---

## Vue d'ensemble

Stack de phishing **éducatif / purple team** pour étudier les réactions d'utilisateurs
face à une attaque simulée :

- ✅ Clone réaliste de la page de login Snapchat
- ✅ Capture comportementale (temps de réaction, clics, autofill)
- ✅ Stockage anonymisé SQLite
- ✅ Dashboard statistique intégré (`/api/report`)
- ✅ Formulaire de consentement RGPD intégré
- ✅ Page de debriefing systématique
- ✅ Aucune donnée réelle Snapchat utilisée — jamais
- ✅ 100% open-source, 100% contrôlable

---

## Prérequis

| Outil | Raison |
|-------|--------|
| Python 3.8+ | Moteur du serveur Flask |
| pip | Gestionnaire de paquets |
| Un navigateur (Chrome/Firefox) | Pour les tests |
| Ngrok *(optionnel)* | Expose sur Internet (tests externes) |

### Installation sur WSL

```bash
sudo apt update
sudo apt install python3 python3-pip -y
pip3 install --user -r requirements.txt
```

---

## Installation en 60 secondes

```bash
cd ~/Desktop/snapchat-phishing-lab
pip3 install -r requirements.txt --break-system-packages
python3 generate.py                    # Clone la page Snapchat
python3 main.py                        # Lance le serveur
```

Ouverte le navigateur sur **http://localhost:5000**

---

## Structure du projet

```
snapchat-phishing-lab/
│
├── 📄 main.py                  ← Serveur Flask + capture + API + dashboard
├── 📄 generate.py               ← Cloneur de page Snapchat
├── 📄 requirements.txt          ← Dépendances Python
├── 📄 consent_RGDP.fr.md        ← Formulaire de consentement RGPD officiel
├── 📄 debrief_template.md       ← Guide de debriefing pour le chercheur
├── 📄 README.md                 ← Ce fichier
│
├── 📁 templates/                ← Pages HTML serveur
│   ├── index.html               ← Page d'accueil (consentement + checklist)
│   ├── login.html               ← Page de login clonée (générée par generate.py)
│   ├── redirect.html            ← Page "succès" avant redirection vers vrai Snapchat
│   └── debrief.html             ← Page de debriefing post-test
│
├── 📁 static/                   ← Ressources clonées (CSS/JS/images)
│   ├── css/
│   ├── js/
│   └── images/
│
└── 🗄️ captured_credentials.db   ← Base SQLite (stockage local des captures)
```

---

## Configuration

Édite la section `CONFIG` dans `main.py` :

```python
CONFIG = {
    "SERVER_PORT": 5000,           # Port d'écoute du serveur
    "USE_HTTPS": False,            # True + certificats pour plus de réalisme
    "CAPTURE_DB": "captured_credentials.db",
    "SESSION_TTL_MINUTES": 60,
    "TOKEN_VALIDITY_DAYS": 30,
}
```

### Générer un certificat SSL auto-signé (realisme sur le lab)

```bash
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem -out cert.pem -days 365 \
  -subj "/C=FR/ST=Paris/L=Paris/O=PurpleTeamLab/CN=localhost"
```

Puis `USE_HTTPS: True`

### Exposer sur Internet (Ngrok)

```bash
ngrok http 5000
```

Utilise l'URL publique Ngrok pour partager le lab avec des participants externes.
L'URL change à chaque redémarrage — utilise `ngrok http 5000 --subdomain snapchat-lab` pour une URL fixe (plan Ngrok requis).

---

## Utilisation pas à pas

### Étape 1 — Cloner la page Snapchat

```bash
python3 generate.py
```

Résultat : `templates/login.html` est créé avec un clone des ressources (CSS, JS, images).

> **Note :** Si Snapchat modifie sa page de login (mise à jour du site), relance `generate.py`
> pour re-cloner la nouvelle version.

### Étape 2 — Lancer le serveur

```bash
python3 main.py
```

Output attendu :

```
╔══════════════════════════════════════════════════════════╗
║     SNAPCHAT PHISHING LAB — PURPLE TEAM RESEARCH         ║
╠══════════════════════════════════════════════════════════╣
║  📊 Dashboard : http://localhost:5000/api/report         ║
║  📤 Export data : http://localhost:5000/export           ║
║  🔄 Reset : http://localhost:5000/reset                  ║
╚══════════════════════════════════════════════════════════╝
```

### Étape 3 — Passer un participant

1. Ouvrir `http://localhost:5000`
2. Vérifier que le consentement est coché ✅
3. Cliquer "Commencer l'étude"
4. **Observer** ce que fait le participant
   - Remplit-il le formulaire ?
   - Vérifie-t-il l'URL ?
   - Quel temps de réaction ?
5. Redirection automatique vers `accounts.snapchat.com` après 2s
6. Débriefing : expliquer la supercherie, remplir `debrief_template.md`

### Étape 4 — Analyser les résultats

```bash
# Voir le dashboard
curl http://localhost:5000/api/report
# {"total_sessions": 15, "total_captures": 7, "conversion_rate_pct": 46.67, ...}

# Export CSV
curl http://localhost:5000/export | python3 -m json.tool > results.json
```

### Étape 5 — Réinitialiser pour une nouvelle session

```bash
# Réinitialise la base (à faire entre chaque nouveau lot de tests)
curl http://localhost:5000/reset
# Données réinitialisées
```

---

## Métriques et Analyse

### Dashboard (`/api/report`)

```json
{
  "total_sessions": 42,       // Nombre de participants ayant vu le lab
  "total_captures": 18,       // Nombre ayant saisi des identifiants
  "conversion_rate_pct": 42.86, // Taux de conversion phishing
  "daily_stats": [
    {"date": "2026-05-25", "count": 12},
    {"date": "2026-05-24", "count": 6}
  ]
}
```

### Export (`/export`)

Données anonymisées au format JSON :

```json
[
  {
    "participant_id": "P20260525-A1B2",
    "username_length": 12,
    "password_length": 8,
    "ip": "192.168.1.42",
    "user_agent": "Mozilla/5.0 ...",
    "timestamp": "2026-05-25 14:32:01",
    "consent": true,
    "debriefed": false
  }
]
```

### Tableau de bord de métriques à mesurer

| Métrique | Comment la mesurer | Objectif |
|----------|-------------------|----------|
| Taux de conversion | `total_captures / total_sessions × 100` | 20–40% (phishing crédible) |
| Temps avant soumission | Timestamp page → timestamp POST | < 8s = haut risque |
| Taux de vérification URL | Comportement JS (focus sur barre d'adresse) | >30% = bon niveau de méfiance |
| Taux d'identification post-test | Questionnaire debrief | >50% = sensibilisation efficace |
| Segmentation par âge/niveau technique | Questionnaire pré-test | Identifier les profils à risque |

---

## Cadre éthique RGPD

### ✅ Ce qui est autorisé

- ✅ Tests sur toi-même et personnes consentantes explicitement
- ✅ Formulaire de consentement signé AVANT le début du test
- ✅ Environnement de recherche isolé, pas de données externes
- ✅ Anonymisation systématique, pas de diffusion
- ✅ Debriefing systématique APRÈS chaque test
- ✅ Suppression des données après 12 mois maximum

### ❌ Ce qui est interdit

- ❌ Tester sans consentement écrit préalable
- ❌ Collecter des données personnelles sensibles (nom, adresse, numéro)
- ❌ Vérifier les identifiants capturés contre de vrais services
- ❌ Diffuser les résultats de manière à identifier un participant
- ❌ Réutiliser cette infrastructure pour d'autres cibles sans autorisation

### 📄 Formulaire de consentement

Voir `consent_RGDP.fr.md` pour le texte officiel.
Imprimez et faites signer une copie pour chaque participant **avant** le début du test.

---

## Extensibilité

### Ajouter un nouveau scénario

1. Créer `templates/nouveau_scenario.html` (ex: notification de sécurité)
2. Ajouter la route dans `main.py` :

```python
@app.route('/notification')
def security_notification():
    if 'participant_id' not in session:
        return redirect(url_for('index'))
    log_event("SCENARIO_NOTIFICATION", session['participant_id'])
    return render_template('notification.html', 
                         participant_id=session['participant_id'])
```

3. Ajouter une capture dédiée :

```python
@app.route('/notification-click', methods=['POST'])
def capture_notification():
    log_event("NOTIFICATION_CLICK", session.get('participant_id'))
    return jsonify({"captured": True})
```

4. Ajouter à la route `/login` POST un marqueur identifiant le scénario d'origine

### Intégrer un outil de questionnaire post-test

- **Google Forms** : ajouter le lien dans `templates/debrief.html`
- **Typeform** : embed direct
- **Limesurvey auto-hébergé** : pour 100% de contrôle

### Sauvegarde / Restauration

```bash
cp captured_credentials.db backups/backup_$(date +%Y%m%d_%H%M).db
ls backups/  # Lister les backups
restore_from="backups/backup_20260525_1400.db"
cp "$restore_from" captured_credentials.db
```

---

## Dépannage

| Problème | Diagnostic | Solution |
|----------|-----------|----------|
| La page ne charge pas | Flask non installé ? | `pip3 install flask` |
| Erreur téléchargement Snapchat | Snapchat bloque les requêtes Python | Le `User-Agent` dans `generate.py` est déjà réaliste. Essayer via un VPN ou avec `curl` d'abord. |
| login.html ne s'affiche pas | `generate.py` pas lancé | `python3 generate.py` → vérifie le message `[✓] login.html généré` |
| Erreur SQLite | Base corrompue | `rm captured_credentials.db && python3 main.py` |
| HTTPS ne marche pas | Certificats manquants | Générer avec `openssl` comme ci-dessus |
| Le JS de tracking ne capture rien | Navigateur bloque le script | Vérifier la console du navigateur (F12) → les logs `[LAB]` doivent apparaître |
| Les participants ne sont pas redirigés vers Snapchat | `generate.py` pas de domaine cible | Vérifie la `SNAPCHAT_LOGIN_URL` dans `generate.py` |

---

## 🔗 Endpoints API

| Point | Méthode | Rôle |
|-------|---------|------|
| `POST /api/consent` | `{participant_id: "..."}` | Enregistre le consentement |
| `GET /api/report` | — | Dashboard statistique |
| `GET /export` | — | Export anonymisé JSON |
| `GET /reset` | — | Purge toute la base |

---

**License :** MIT — Usage éthique uniquement  
**Auteur :** Famoussa — Purple Team Research  
**Dernière mise à jour :** Mai 2026
