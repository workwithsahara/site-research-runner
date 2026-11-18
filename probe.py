"""Probe 2: Yellow Pages listings: how many have no website, and do detail pages show emails?"""
import re
import time
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

import search

EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
s = requests.Session()
H = {"User-Agent": search.SEARCH_UA, "Accept-Language": "en-US,en;q=0.9"}
SEARCHES = [("plumber", "Austin, TX"), ("hair salon", "Denver, CO"), ("dog groomer", "Portland, OR"), ("electrician", "Tampa, FL"),
            ("landscaping", "Columbus, OH"), ("dentist", "Phoenix, AZ"), ("auto repair", "Atlanta, GA")]
total = nosite = with_rev = 0
detail = []
for what, where in SEARCHES:
    u = f"https://www.yellowpages.com/search?search_terms={quote_plus(what)}&geo_location_terms={quote_plus(where)}"
    try:
        r = s.get(u, timeout=25, headers=H)
    except Exception as ex:
        print(what, where, "error", type(ex).__name__, flush=True)
        continue
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select("div.result, div.v-card")
    n = ns = 0
    for c in cards:
        name = c.select_one("a.business-name")
        if not name:
            continue
        n += 1
        site = c.select_one("a.track-visit-website")
        phone = c.select_one("div.phones, .phone")
        rev = c.select_one("span.count, .rating .count")
        yrs = c.select_one(".years-in-business .count, .years-in-business")
        if not site:
            ns += 1
            detail.append(urljoin("https://www.yellowpages.com", name.get("href", "")))
            if ns <= 2:
                print("  NOSITE:", name.get_text(strip=True)[:40], "|", phone.get_text(strip=True) if phone else None, "| rev", rev.get_text(strip=True) if rev else None, "| yrs", yrs.get_text(" ", strip=True)[:25] if yrs else None, flush=True)
    total += n
    nosite += ns
    print(f"{what} {where}: status={r.status_code} cards={len(cards)} named={n} no_website={ns}", flush=True)
    time.sleep(2)
print(f"TOTAL listings={total} no_website={nosite}", flush=True)
print("--- detail pages of no-website listings", flush=True)
got = 0
for u in detail[:14]:
    try:
        r = s.get(u, timeout=25, headers=H)
        soup = BeautifulSoup(r.text, "html.parser")
        mail = [a.get("href", "")[7:] for a in soup.select('a[href^="mailto:"]')]
        social = [a.get("href") for a in soup.select('a[href*="facebook.com"], a[href*="instagram.com"]') if "yellowpages" not in a.get("href", "")]
        got += bool(mail)
        print(u[-60:], r.status_code, "mailto", mail[:2], "social", social[:2], flush=True)
    except Exception as ex:
        print(u[-60:], "error", type(ex).__name__, flush=True)
    time.sleep(1.5)
print("detail pages with email:", got, flush=True)
print("--- other countries", flush=True)
for u in ["https://www.yellowpages.ca/search/si/1/plumber/Toronto+ON", "https://www.yellowpages.com.au/search/listings?clue=plumber&locationClue=Sydney+NSW",
          "https://www.yell.com/s/plumbers-leeds.html", "https://www.thomsonlocal.com/search/plumbers/leeds", "https://www.localsearch.com.au/find/plumber/sydney-nsw",
          "https://www.finda.co.nz/plumber/auckland", "https://www.hotfrog.com.au/search/sydney/plumber", "https://www.hotfrog.co.uk/search/london/plumber"]:
    try:
        r = s.get(u, timeout=25, headers=H)
        print(u[:70], r.status_code, "len", len(r.text), "emails", len(EMAIL.findall(r.text)), flush=True)
    except Exception as ex:
        print(u[:70], "error", type(ex).__name__, flush=True)
    time.sleep(1)
