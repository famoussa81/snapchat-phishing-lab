import requests

GEOIP_CACHE = {}


def geoip(ip):
    if ip in GEOIP_CACHE:
        return GEOIP_CACHE[ip]
    if ip == '127.0.0.1' or ip.startswith('192.168.') or ip.startswith('10.'):
        GEOIP_CACHE[ip] = 'Local'
        return 'Local'
    try:
        r = requests.get(f'http://ip-api.com/json/{ip}?fields=country,countryCode', timeout=2)
        if r.status_code == 200:
            d = r.json()
            country = d.get('country', 'Unknown')
            GEOIP_CACHE[ip] = country
            return country
    except:
        pass
    GEOIP_CACHE[ip] = 'Unknown'
    return 'Unknown'
