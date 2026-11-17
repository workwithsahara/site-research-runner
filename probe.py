"""Looks closer at Google basic HTML, Dogpile and Startpage from this runner: do they return real result links?"""
import re
import time
from urllib.parse import quote_plus, unquote, urlparse

import requests

import search

UA = search.SEARCH_UA
UA2 = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
EN = "plumber Austin Texas"
AR = "مكتب استقدام الرياض"
URLS = [
    ("google_gbv1", "https://www.google.com/search?q={q}&gbv=1&hl=en&num=20"),
    ("google_plain", "https://www.google.com/search?q={q}&hl=en&num=20"),
    ("google_p2_gbv1", "https://www.google.com/search?q={q}&gbv=1&hl=en&start=10"),
    ("dogpile", "https://www.dogpile.com/serp?q={q}"),
    ("startpage", "https://www.startpage.com/sp/search?query={q}"),
]
s = requests.Session()


def hosts_from(html):
    out = []
    for u in re.findall(r'/url\?q=(https?://[^&"]+)', html) + re.findall(r'href="(https?://[^"]+)"', html):
        h = (urlparse(unquote(u)).hostname or "").lower().replace("www.", "")
        if h and h not in out and not any(x in h for x in ("google", "gstatic", "dogpile", "startpage", "system1", "cookielaw", "unpkg")):
            out.append(h)
    return out


for q in (EN, AR):
    print("QUERY", q.encode("unicode_escape").decode() if not q.isascii() else q, flush=True)
    for name, tpl in URLS:
        for ua_name, ua in (("ua1", UA), ("ua2", UA2)):
            try:
                r = s.get(tpl.format(q=quote_plus(q)), timeout=25, headers={"User-Agent": ua, "Accept-Language": "en-US,en;q=0.9"})
                t = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
                hs = hosts_from(r.text)
                flags = [w for w in ("unusual traffic", "captcha", "enablejs", "consent", "sorry") if w in r.text.lower()]
                print(f"{name} {ua_name} {r.status_code} len={len(r.text)} title={(t.group(1).strip()[:50] if t else None)!r} flags={flags} hosts={len(hs)} {hs[:8]}", flush=True)
            except Exception as e:
                print(f"{name} {ua_name} error {type(e).__name__}", flush=True)
            time.sleep(2)
