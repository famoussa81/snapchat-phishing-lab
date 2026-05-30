# 🚀 Snapchat Phishing Lab — Purple Team Research

**Version :** 4.0 (Agentic Orchestration)  
**Auteur :** Famoussa  
**Objectif :** Étude comportementale et sensibilisation au phishing.

---

## ⚠️ Avertissement Légal
**CE PROJET EST DESTINÉ À UN USAGE ÉTHIQUE ET ÉDUCATIF UNIQUEMENT.**
- ❌ Interdit sur des cibles réelles sans consentement.
- ❌ Interdit de diffuser des données collectées.
- ✅ Autorisé en environnement sandbox / laboratoire.

---

## 🛠️ Installation Rapide (One-Click Setup)

Le projet utilise désormais un script d'automatisation pour éviter toute configuration manuelle fastidieuse.

### ⚡ Installation sur Windows
1. **Cloner le repo :**
   ```powershell
   git clone https://github.com/famoussa81/snapchat-phishing-lab.git
   cd snapchat-phishing-lab
   ```
2. **Lancer l'installateur :**
   ```powershell
   .\setup.ps1
   ```
   *Le script installe Python venv, les dépendances et Playwright.*

---

## 🎮 Guide d'Utilisation

L'accès se fait désormais via le **Mission Control Orchestrator** (`main.py`).

### 🚀 Lancer le Lab
```powershell
python main.py start
```
**Ce qui se passe automatiquement :**
1. Initialisation de la base de données.
2. Lancement du serveur Flask.
3. Ouverture d'un tunnel **Cloudflare** automatique.
4. Génération d'une **matrice de liens** pour tous vos scénarios (Cadeau, Sécurité, etc.).

### 🔄 Commandes Utiles
| Commande | Action |
| :--- | :--- |
| `python main.py start` | Lance le serveur + Tunnel + Génère les liens |
| `python main.py update` | Met à jour le code via Git et les dépendances |
| `python main.py info` | Affiche les guidelines et infos projet |
| `python main.py help` | Affiche l'aide complète |

---

## 📡 Architecture & Flux de Données

### 🔗 Matrice d'Appâts (Baits)
Le serveur gère plusieurs points d'entrée pour maximiser le taux de conversion :
- **Lien Racine (`/`)** $\rightarrow$ Jeu "Classement Secret" (Psychologie de groupe).
- **Sénario Cadeau** $\rightarrow$ Appât basé sur la récompense.
- **Sénario Sécurité** $\rightarrow$ Appât basé sur l'urgence/peur.
- **Sénario Snapchat+** $\rightarrow$ Appât basé sur le prestige.

### 📊 Flux de Capture
`Lien Cloudflare` $\rightarrow$ `Appât` $\rightarrow$ `Page Login Clone` $\rightarrow$ `Capture DB` $\rightarrow$ `Redirection Réelle`.

---

## 📁 Structure du Projet
- `setup.ps1` : 📦 Installateur automatique.
- `main.py` : 🧠 Orchestrateur & Serveur.
- `app/` : ⚙️ Logique backend (API, DB, Routes).
- `templates/` : 🎨 Clones de pages & Scénarios.
- `static/` : 🖼️ Assets (CSS-JS-Images) clones.
- `requirements.txt` : 📜 Liste des dépendances.
- `.gitignore` : 🛡️ Protection des données sensibles.

---
**© 2026 Famoussa — Purple Team Researcher**
