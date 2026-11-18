"""Probe 3: Hotfrog search and detail page structure (emails, websites, reviews)."""
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import search

EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
s = requests.Session()
H = {"User-Agent": search.SEARCH_UA, "Accept-Language": "en-US,en;q=0.9"}
for base, path in [("https://www.hotfrog.com.au", "/search/sydney/plumber"), ("https://www.hotfrog.com", "/search/austin/plumber"),
                   ("https://www.hotfrog.co.uk", "/search/london/hairdresser"), ("https://www.hotfrog.ca", "/search/toronto/plumber"),
                   ("https://www.hotfrog.co.nz", "/search/auckland/plumber")]:
    try:
        r = s.get(base + path, timeout=25, headers=H)
    except Exception as ex:
        print(base, "error", type(ex).__name__, flush=True)
        continue
    soup = BeautifulSoup(r.text, "html.parser")
    links = [a.get("href") for a in soup.select('a[href*="/company/"]')]
    print(base, r.status_code, "len", len(r.text), "emails", len(EMAIL.findall(r.text)), "company links", len(set(links)), flush=True)
    if base.endswith(".com.au"):
        txt = soup.get_text(" ", strip=True)
        m = EMAIL.search(txt)
        if m:
            print("  TEXT AROUND EMAIL:", txt[max(0, m.start() - 300):m.end() + 200].encode("ascii", "ignore").decode(), flush=True)
        card = soup.select_one('a[href*="/company/"]')
        if card:
            par = card
            for _ in range(4):
                par = par.parent or par
            print("  CARD HTML:", str(par)[:1800].encode("ascii", "ignore").decode(), flush=True)
        seen = []
        for h in links:
            if h and h not in seen:
                seen.append(h)
        for h in seen[:3]:
            d = s.get(urljoin(base, h), timeout=25, headers=H)
            ds = BeautifulSoup(d.text, "html.parser")
            dt = ds.get_text(" ", strip=True)
            print("  DETAIL", h[:70], d.status_code, "emails", EMAIL.findall(d.text)[:3], "mailto", len(ds.select('a[href^="mailto:"]')),
                  "website links", [a.get("href") for a in ds.select('a[href^="http"]') if "hotfrog" not in a.get("href", "") and "google" not in a.get("href", "")][:4], flush=True)
            print("  DETAILTEXT:", dt[:700].encode("ascii", "ignore").decode(), flush=True)
            time.sleep(1.5)
    time.sleep(2)
