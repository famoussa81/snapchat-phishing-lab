"""
╔══════════════════════════════════════════════════════════════╗
║  QR CODE GENERATOR — Purple Team Tool                       ║
║  Génère des QR codes à partager sur les réseaux             ║
║  Usage: python tools/qr_generator.py                        ║
╚══════════════════════════════════════════════════════════════╝
"""
import os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE, "output_qr")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_qr(url, filename=None, fill_color="black", back_color="white"):
    """Génère un QR code et le sauvegarde."""
    try:
        import qrcode
        from PIL import Image, ImageDraw
    except ImportError:
        print("  Installation de qrcode...")
        os.system(f"{sys.executable} -m pip install qrcode[pil]")
        import qrcode
        from PIL import Image, ImageDraw

    if not filename:
        filename = "qrcode_lab.png"

    filepath = os.path.join(OUTPUT_DIR, filename)

    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGB")

    # Ajouter un logo Snapchat au centre
    try:
        img = img.resize((600, 600))
        draw = ImageDraw.Draw(img)
        # Petit cercle blanc au centre
        center = 300
        draw.ellipse([center - 30, center - 30, center + 30, center + 30],
                     fill="white", outline="black", width=3)
    except:
        pass

    img.save(filepath, "PNG")
    return filepath


def make_styled_qr(url, scenario="classic"):
    """Génère un QR code stylisé selon le scénario."""
    styles = {
        "classic": {"color": "black", "file": "qrcode_classic.png"},
        "snapchat": {"color": "#FFFC00", "file": "qrcode_snapchat.png"},
        "pink": {"color": "#FF3366", "file": "qrcode_pink.png"},
        "gold": {"color": "#FFD700", "file": "qrcode_gold.png"},
    }
    style = styles.get(scenario, styles["classic"])
    return generate_qr(url, filename=style["file"], fill_color=style["color"])


def interactive_menu():
    """Menu interactif pour générer des QR codes."""
    from colorama import init, Fore, Style
    init()
    R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN; M = Fore.MAGENTA; X = Style.RESET_ALL; D = Style.DIM

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(f"\n  {M}╔══════════════════════════════════════════════╗{X}")
        print(f"  {M}║       QR CODE GENERATOR — Purple Team       ║{X}")
        print(f"  {M}╚══════════════════════════════════════════════╝{X}")
        print()
        print(f"  {C}STYLES DISPONIBLES :{X}")
        print(f"    {G}[1]{X} Classique (noir sur blanc)")
        print(f"    {Y}[2]{X} Snapchat (jaune)")
        print(f"    {M}[3]{X} Rose")
        print(f"    {Y}[4]{X} Or")
        print(f"    {D}[0]{X} Retour")
        print()

        choix = input(f"  {G}└─>{X} ").strip()
        if choix == "0":
            return

        styles_map = {"1": "classic", "2": "snapchat", "3": "pink", "4": "gold"}
        if choix not in styles_map:
            continue

        url = input(f"  {C}URL du lab {D}(defaut: http://localhost:8080){X} > ").strip() or "http://localhost:8080"

        filepath = make_styled_qr(url, styles_map[choix])
        print(f"\n  {G}✓ QR code généré : {filepath}{X}")
        print(f"  {D}  Contient : {url}{X}")

        # Afficher dans le terminal
        try:
            from PIL import Image
            img = Image.open(filepath)
            w, h = img.size
            print(f"  {D}  Dimensions : {w}x{h}px{X}")
        except:
            pass

        # Option pour ouvrir
        ouvrir = input(f"\n  {Y}Ouvrir le dossier ? (o/N){X} > ").strip().lower()
        if ouvrir == "o":
            if os.name == "nt":
                os.startfile(OUTPUT_DIR)
            else:
                os.system(f"xdg-open {OUTPUT_DIR}")

        input(f"\n  {D}[Appuie sur Entrée]{X}")


if __name__ == "__main__":
    interactive_menu()
