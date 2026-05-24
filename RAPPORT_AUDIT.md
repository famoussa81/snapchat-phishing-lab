# 📋 Rapport d'Audit — Snapchat Phishing Lab

**Date** : 2026-05-24  
**État** : ⚠️ Lab fonctionnel mais INCOMPLET — plusieurs bugs bloquants  
**Destination** : Agent de développement / équipe Purple Team

---

## 1. 🔴 PROBLÈMES CRITIQUES (bloquants)

### 1.1 Formulaire `<form>` → React intercepte la soumission
- `<form class="Login_form__u_9g5" method="POST" action="/login">` ajouté ✅
- **MAIS** React SPA intercepte quand même le submit vers `/v2/login`
- Le POST Flask ne reçoit pas les données (ou reçoit des tableaux vides)
- **Impact** : les identifiants ne sont pas capturés, les mots de passe sont vides

### 1.2 Script de capture JavaScript ne fonctionne pas correctement
- Le JS tente d'intercepter le submit mais React a aussi un listener sur le bouton
- La course d'événements fait que React gagne et envoie vers `/v2/captcha`
- `/v2/captcha` n'existe pas sur le serveur → 404 ou crash
- **Fix nécessaire** : intercepter au clic sur le bouton Next (pas sur form submit), puis `setTimeout` → capturer → laisser React continuer

### 1.3 Après soumission → redirection vers `/v2/captcha` au lieu de `/reset`
- Le POST arrive à `/login` Flask mais React a déjà changé l'URL
- Le navigateur affiche `http://localhost:5000/v2/captcha?...` → 404
- La page `redirect.html` n'est jamais affichée
- **Fix** : soit ajouter une route proxy `/v2/*` vers `accounts.snapchat.com`, soit interrompre React avant qu'il ne redirige

### 1.4 Seulement l'étape 1 du login est clonée
- Le vrai Snapchat est SPA en **2 étapes** :
  1. `accountIdentifier` → Next
  2. `password` → Log In
- Notre clone n'a que l'étape 1
- Les mots de passe sont TOUJOURS vides dans les captures
- **Fix** : capturer aussi la page `/v2/welcome` du vrai Snapchat avec Playwright, et ajouter une étape 2 dans le lab

---

## 2. 🟡 PROBLÈMES VISUELS / FIDÉLITÉ AU VRAI SITE

| Problème | État | Action |
|----------|------|--------|
| Bordure du champ trop épaisse par défaut (`border:1px solid #000`) | ⚠️ Corrigé partiellement | Passer `border:1px solid transparent` + focus `#000` |
| Couleur bouton Next : `var(--blue-300)` bleu au lieu de jaune | ✅ Corrigé | `background:#FFFC00` — vérifier si le jaune est pas trop saturé |
| Footer : texte brut sans colonnes stylées | ⚠️ CSS ajouté mais partiel | Re-styler avec display:flex + gap + police Avenir |
| Bouton Google mélange anglais/français | ℹ️ Normal (détection langue navigateur) | Accepter ou forcer anglais pour cohérence |
| Artefact `<p id="__next-route-announcer__">` en haut à gauche | ⚠️ Non corrigé | Masquer avec `clip:rect(0,0,0,0)` ou `display:none` |
| Sélecteur de langue en `<select>` HTML natif | ⚠️ Non corrigé | Remplacer par un `<div>` personnalisé style Snapchat |
| Lien "Use phone number instead" : couleur pas exacte | ℹ️ Mineur | `#1a73e8` au lieu de bleu Snapchat personnalisé |
| Formulaire trop "collé" en haut de la page | ⚠️ Non corrigé | Ajouter `margin/padding` au conteneur parent |

---

## 3. 🟠 DÉFICIENCES FONCTIONNELLES

### 3.1 Clone incomplet — pas d'étape 2 (mot de passe)
- `generate.py` ne capture que `/accounts/login` (étape 1)
- Il faut aussi capturer la page de mot de passe (page 2 du flux Snapchat)
- Sans ça, l'étude ne mesure que l'étape 1, pas l'étape 2

### 3.2 Redirection réaliste manquante
- Après capture, le participant est redirigé vers `/reset` → page de fin visible
- Cela trahit immédiatement que c'est un lab, pas le vrai Snapchat
- **Fix** : rediriger vers `https://snapchat.com` (vrai site) après capture

### 3.3 Aucune variante d'attaque
- Seul le scénario "login standard" est disponible
- Manque :
  - MFA / double authentification (code SMS factice)
  - "Quelqu'un s'est connecté depuis un nouvel appareil"
  - "Votre compte est verrouillé"
  - Abonnement Snapchat+ (vol de CB)
  - Concours/gagnant factice

### 3.4 Tracking comportemental incomplet
Non mesuré :
- Temps de réflexion avant soumission
- Nombre de re-saisie du champ
- Time-to-first-click, time-to-submit
- Heatmap des clics
- Scroll depth

### 3.5 Database — credentials en CLAIR
- SQLite sans chiffrement
- Les mots de passe sont lisibles en clair dans `captured_credentials.db`
- **Fix** : chiffrement AES-256 des champs username/password, ou utiliser SQLCipher

### 3.6 Export des résultats
- `/export` retourne du JSON mais n'écrit pas sur disque
- Pas de dossier `results/` avec sauvegardes horodatées
- Pas de format CSV pour analyse

### 3.7 Endpoints sans authentification
- `/reset` purger toute la base → accessible publiquement
- `/export` expose toutes les données → pas de clé API/admin
- **Fix** : ajouter `?key=SECRET_KEY_RESET` sur les routes sensibles

---

## 4. 🟢 POINTS POSITIFS (marchent déjà)

```
✅ Page de consentement RGPD fonctionnelle
✅ Capture du champ accountIdentifier (étape 1) → DB SQLite
✅ Dashboard /api/report → statistiques JSON
✅ Génération d'ID de participant anonymes
✅ Logging des événements (SESSION_START, CONSENT_GIVEN, LOGIN_ATTEMPT, CAPTURE)
✅ Page de debriefing post-expérience
✅ Redirection réaliste vers snapchat.com (base fonctionne)
✅ Script generate.py avec Playwright → capture page rendue (pas statique)
✅ Assets (CSS/JS/images) servis localement, plus de dépendance CDN externe
✅ Flask avec session cookies HTTPOnly
✅ Captures testées : P20260524-082E86ED → "test_purple_team" capturé ✅
```

---

## 5. 📝 TODO PAR PRIORITÉ (pour l'agent)

### Priorité 1 — Bug bloquant capture
1. Corriger le script de capture JS (intercepter au `click` sur le bouton, pas sur `form.submit`, puis `setTimeout(500)` → capture → laisser React continuer)
2. Si React gagne, ajouter un flag `__submitted = true` + `e.stopImmediatePropagation()` dans le listener `useCapture: true`
3. Ajouter la route `/api/capture` comme endpoint principal (ne pas utiliser `/login` POST du tout pour la capture, laisser le JS envoyer vers `/api/capture` puis le SPA continuer vers vrai Snapchat)

### Priorité 2 — Redirection réaliste
4. Après capture réussie, rediriger vers `https://snapchat.com` (pas `/reset`)
5. Montrer `/redirect.html` seulement si la capture a échoué
6. Arrêter de faire rediriger React vers `/v2/captcha` sur notre serveur

### Priorité 3 — Étape 2 (mot de passe)
7. Mettre à jour `generate.py` pour capturer aussi l'étape 2 (page `/v2/welcome` ou l'URL après Next)
8. Ajouter la 2ème page dans `templates/` 
9. Mettre à jour les routes Flask pour gérer l'étape 2
10. Tester un flux complet : accountIdentifier → password → capture réelle des deux champs

### Priorité 4 — Fidélité visuelle
11. Masquer l'accessibility announcer (`#__next-route-announcer__`) avec CSS
12. Re-styler le footer avec display:flex + colonnes
13. Remplacer le `<select>` langue par un `<div>` custom
14. Ajuster la marge du titre et du formulaire (trop collé en haut)
15. Vérifier que toutes les polices sont bien Avenir Next

### Priorité 5 — Scénarios additionnels
16. Ajouter scénario "MFA factice" → page demandant un code à 6 chiffres
17. Ajouter scénario "notification sécurité" → "Quelqu'un s'est connecté depuis [ville]"
18. Ajouter scénario "snapchat+" → demande de carte bancaire
19. Ajouter scénario "oubli de mot de passe" → demande d'email de récupération

### Priorité 6 — Sécurité & Données
20. Chiffrer la DB SQLite avec SQLCipher ou chiffrement AES des champs
21. Ajouter `?key=XXX` sur `/reset` et `/export`
22. Purge automatique des données après date limite de l'étude
23. Ajouter validation JavaScript côté client (empêcher soumission vide)

### Priorité 7 — Analyse & Export
24. Dashboard visuel HTML avec Chart.js ou Plotly
25. Export CSV horodaté dans dossier `results/`
26. Script Python `analyse_resultats.py` avec Pandas
27. Génération PDF de rapport automatique

---

## 6. FICHE TECHNIQUE RAPIDE

```
Lab path       : /mnt/c/Users/Lenovo-PC/Desktop/snapchat-phishing-lab/
Serveur        : Flask 5000 (localhost seulement, pas d'exposition externe)
Base de données: SQLite — captured_credentials.db
                Tables : captured_credentials + experiment_log
Page clonée    : https://accounts.snapchat.com/accounts/login (étape 1 seulement)
Taille clone   : ~106 KB HTML + ~12 MB JS + ~200 KB CSS (total ~13 MB)
Clone fait avec: Playwright (chromium headless) → page React/Next.js rendue
Assets         : Tous servis localement (static/css/, static/js/, static/images/)
```

---

*Rapport généré automatiquement — Version 1.0 — 2026-05-24*
