"""Tests other search engines and business directories from this runner: status code and distinct outside hosts found."""
import re
import time
from urllib.parse import quote_plus, urlparse

import requests

import search

UA = search.SEARCH_UA
EN = "plumber Austin Texas"
AR = "مكتب استقدام الرياض"
ENGINES = [
    ("aol", "https://search.aol.com/aol/search?q={q}"),
    ("aol2", "https://search.aol.com/aol/search?q={q}&b=11"),
    ("startpage", "https://www.startpage.com/sp/search?query={q}"),
    ("qwant_lite", "https://lite.qwant.com/?q={q}"),
    ("ecosia", "https://www.ecosia.org/search?q={q}"),
    ("yandex", "https://yandex.com/search/?text={q}"),
    ("marginalia", "https://search.marginalia.nu/search?query={q}"),
    ("ask", "https://www.ask.com/web?q={q}"),
    ("dogpile", "https://www.dogpile.com/serp?q={q}"),
    ("searx_be", "https://searx.be/search?q={q}&format=html"),
    ("searx_tiekoetter", "https://searx.tiekoetter.com/search?q={q}"),
    ("google", "https://www.google.com/search?q={q}&num=20"),
]
DIRS = [
    ("hotfrog", "https://www.hotfrog.com/search/texas/austin/plumbers"),
    ("yellowpages", "https://www.yellowpages.com/austin-tx/plumbers"),
    ("superpages", "https://www.superpages.com/search?search_terms=plumber&geo_location_terms=Austin%2C+TX"),
    ("chamberofcommerce", "https://www.chamberofcommerce.com/united-states/texas/austin/plumber"),
    ("bbb", "https://www.bbb.org/search?find_text=plumber&find_loc=Austin%2C+TX"),
    ("yelp", "https://www.yelp.com/search?find_desc=plumber&find_loc=Austin%2C+TX"),
    ("manta", "https://www.manta.com/search?search_source=nav&search=plumber&city=Austin&state=TX"),
    ("cylex", "https://www.cylex.us.com/s?q=plumber&c=Austin&z=TX"),
    ("yp_sa", "https://www.yellowpages.com.sa/en/search?what=recruitment+office"),
    ("kompass_sa", "https://sa.kompass.com/searchCompanies?text=recruitment"),
    ("yp_qa", "https://www.qatar-yellowpages.com/search?what=recruitment"),
]
HREF = re.compile(r'href=["\'](https?://[^"\'#\s]+)', re.I)
s = requests.Session()


def outside(html, own):
    hosts = []
    for u in HREF.findall(html):
        h = (urlparse(u).hostname or "").lower().replace("www.", "")
        if h and own not in h and h not in hosts and not any(x in h for x in ("google", "bing", "yahoo", "microsoft", "facebook", "w3.org", "schema.org", "gstatic", "cloudflare", "apple.com", "twitter", "instagram", "youtube", "linkedin")):
            hosts.append(h)
    return hosts


def go(name, url, own):
    try:
        r = s.get(url, timeout=25, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        hosts = outside(r.text, own)
        print(f"{name} {r.status_code} len={len(r.text)} outside_hosts={len(hosts)} {hosts[:6]}", flush=True)
    except Exception as e:
        print(f"{name} error {type(e).__name__}", flush=True)
    time.sleep(1.5)


for q in (EN, AR):
    print("QUERY", q.encode("unicode_escape").decode() if not q.isascii() else q, flush=True)
    for name, tpl in ENGINES:
        own = urlparse(tpl).hostname.replace("www.", "").split(".")[-2]
        go(name, tpl.format(q=quote_plus(q)), own)
print("DIRECTORIES", flush=True)
for name, url in DIRS:
    go(name, url, urlparse(url).hostname.replace("www.", "").split(".")[-2])
