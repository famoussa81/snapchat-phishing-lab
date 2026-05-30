import os
import json
import requests

GEOIP_CACHE = {}
GEOIP_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".geoip_cache.json"
)


def _load_disk_cache():
    if not os.path.exists(GEOIP_CACHE_FILE):
        return {}
    try:
        with open(GEOIP_CACHE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def _save_disk_cache():
    try:
        with open(GEOIP_CACHE_FILE, "w") as f:
            json.dump(GEOIP_CACHE, f, indent=2)
    except:
        pass


def geoip(ip):
    if ip in GEOIP_CACHE:
        return GEOIP_CACHE[ip]
    disk = _load_disk_cache()
    if ip in disk:
        GEOIP_CACHE[ip] = disk[ip]
        return disk[ip]
    if ip == '127.0.0.1' or ip.startswith('192.168.') or ip.startswith('10.'):
        GEOIP_CACHE[ip] = 'Local'
        _save_disk_cache()
        return 'Local'
    country = _lookup_ip(ip)
    GEOIP_CACHE[ip] = country
    _save_disk_cache()
    return country


def _lookup_ip(ip):
    providers = [
        _lookup_ipapi,
        _lookup_freeipapi,
        _lookup_ipwhois,
    ]
    for provider in providers:
        try:
            result = provider(ip)
            if result and result != 'Unknown':
                return result
        except:
            continue
    return 'Unknown'


def _lookup_ipapi(ip):
    r = requests.get(
        f'http://ip-api.com/json/{ip}?fields=country,countryCode',
        timeout=3
    )
    if r.status_code == 200:
        d = r.json()
        return d.get('country', 'Unknown')
    return 'Unknown'


def _lookup_freeipapi(ip):
    r = requests.get(f'https://freeipapi.com/api/json/{ip}', timeout=3)
    if r.status_code == 200:
        d = r.json()
        return d.get('countryName', 'Unknown')
    return 'Unknown'


def _lookup_ipwhois(ip):
    r = requests.get(f'https://ipwho.is/{ip}?fields=country', timeout=3)
    if r.status_code == 200:
        d = r.json()
        if d.get('success'):
            return d.get('country', 'Unknown')
    return 'Unknown'
