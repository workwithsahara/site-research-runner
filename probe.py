"""Probe: can Bing snippets and Facebook pages give email, phone and 'no website' facts for small local businesses?"""
import re
import time
from urllib.parse import quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup

import search

UA = search.SEARCH_UA
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}")
s = requests.Session()
H = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
QS = ["plumber Austin Texas facebook email", "hair salon Leeds facebook page phone email", "barber Brisbane facebook contact email",
      "site:facebook.com plumber Denver email", "site:facebook.com dog groomer Perth email"]
fb = []
for q in QS:
    try:
        r = s.get("https://www.bing.com/search?q=" + quote_plus(q) + "&setlang=en", timeout=25, headers=H)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select("li.b_algo")
        n_e = n_p = n_fb = 0
        for it in items:
            a = it.select_one("h2 a")
            href = a.get("href", "") if a else ""
            text = it.get_text(" ", strip=True)
            e, p = EMAIL.findall(text), PHONE.findall(text)
            host = (urlparse(href).hostname or "")
            n_e += bool(e); n_p += bool(p)
            if "facebook.com" in host or "instagram.com" in host:
                n_fb += 1
                fb.append(href)
                print("  FB:", href[:90], "| email", e[:1], "| phone", p[:1], "|", text[:160].encode("ascii", "ignore").decode(), flush=True)
        print(f"Q={q!r} status={r.status_code} items={len(items)} with_email={n_e} with_phone={n_p} facebook={n_fb}", flush=True)
    except Exception as ex:
        print("Q", q, "error", type(ex).__name__, flush=True)
    time.sleep(2)
print("--- fetch facebook pages directly", flush=True)
for u in fb[:6]:
    for variant in (u, u.replace("www.facebook.com", "mbasic.facebook.com")):
        try:
            r = s.get(variant, timeout=25, headers=H)
            t = r.text
            print(variant[:80], r.status_code, "len", len(t), "emails", EMAIL.findall(t)[:2], "phones", PHONE.findall(t)[:2], "login" if "login" in t.lower()[:3000] else "", flush=True)
        except Exception as ex:
            print(variant[:80], "error", type(ex).__name__, flush=True)
        time.sleep(1)
print("--- directories", flush=True)
for u in ["https://www.yelp.com/search?find_desc=plumber&find_loc=Austin%2C+TX", "https://www.yellowpages.com/search?search_terms=plumber&geo_location_terms=Austin%2C+TX",
          "https://www.yell.com/s/plumbers-leeds.html", "https://www.hotfrog.com/search/austin/plumber", "https://www.cylex.us.com/s?q=plumber&c=Austin&z=&p=1&dst=&sUrl=&cUrl=",
          "https://www.manta.com/search?search_source=nav&search=plumber&city=Austin&state=TX", "https://www.bbb.org/search?find_country=USA&find_text=plumber&find_loc=Austin%2C%20TX"]:
    try:
        r = s.get(u, timeout=25, headers=H)
        t = r.text
        print(u[:60], r.status_code, "len", len(t), "emails", len(EMAIL.findall(t)), "phones", len(PHONE.findall(t)), flush=True)
    except Exception as ex:
        print(u[:60], "error", type(ex).__name__, flush=True)
    time.sleep(1)
