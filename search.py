"""Finds sites through several free search engines in rotation.
When one engine blocks this runner it is paused for a while and the next engine takes over,
so one blocked engine no longer stops a whole run. Only counts are ever printed."""
import base64
import time
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup

SEARCH_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/124.0 Safari/537.36")
ENGINES = [
    ("ddg", "https://html.duckduckgo.com/html/?q={q}"),
    ("bing", "https://www.bing.com/search?q={q}&count=30&setlang=en"),
    ("mojeek", "https://www.mojeek.com/search?q={q}"),
    ("brave", "https://search.brave.com/search?q={q}&source=web"),
    ("yahoo", "https://search.yahoo.com/search?p={q}&n=30"),
    ("ddglite", "https://lite.duckduckgo.com/lite/?q={q}"),
]
ENGINE_HOSTS = ("duckduckgo.", "bing.", "microsoft.", "mojeek.", "brave.", "yahoo.", "yimg.", "oath.", "w3.org",
                "google.", "gstatic.", "startpage.", "msn.")
SKIP = ("amazon.", "ebay.", "facebook.", "youtube.", "reddit.", "wikipedia.", "pinterest.", "yelp.", "google.",
        "indeed.", "linkedin.", "glassdoor.", "ziprecruiter.", "monster.", "reed.co.uk", "totaljobs.", "seek.com",
        "cv-library.", "jooble.", "instagram.", "twitter.", "x.com", "clutch.co", "trustpilot.", "mapquest.",
        "merriam-webster.", "dictionary.", "vocabulary.", "thefreedictionary.", "bing.", "bbb.org", "yellowpages.", "zoominfo.",
        "crunchbase.", "apollo.io", "owler.", "dnb.com", "manta.com", "comparably.", "ambitionbox.", "craigslist.", "tiktok.",
        "quora.", "medium.com", "forbes.", "inc.com", "gov.", ".gov", "salary.com", "payscale.", "simplyhired.", "careerbuilder.", "lensa.")

_state = {name: {"until": 0.0, "strikes": 0} for name, _ in ENGINES}
_turn = [0]


def real_url(href):
    """Search engines wrap result links; unwrap them to the real address."""
    if not href:
        return ""
    if "uddg=" in href:
        return unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
    if "/RU=" in href:
        return unquote(href.split("/RU=", 1)[1].split("/RK=", 1)[0])
    if "bing.com/ck/a" in href:
        u = parse_qs(urlparse(href).query).get("u", [""])[0]
        if u.startswith("a1"):
            try:
                raw = u[2:] + "=" * (-len(u[2:]) % 4)
                return base64.urlsafe_b64decode(raw).decode("utf-8", "ignore")
            except Exception:
                return ""
    return href


def result_hosts(html_text, limit):
    soup = BeautifulSoup(html_text, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        url = real_url(a["href"])
        if not url.startswith("http"):
            continue
        host = urlparse(url).netloc.lower().replace("www.", "")
        if not host or any(h in host for h in ENGINE_HOSTS):
            continue
        if host not in out:
            out.append(host)
        if len(out) >= limit:
            break
    return out


def cool(name, hard):
    st = _state[name]
    st["strikes"] += 1
    wait = min(60 * (2 ** (st["strikes"] - 1)), 1200) if hard else min(30 * st["strikes"], 300)
    st["until"] = time.time() + wait


def search_hosts(words, session, per_query=15):
    for _ in range(40):
        now = time.time()
        order = [ENGINES[(_turn[0] + i) % len(ENGINES)] for i in range(len(ENGINES))]
        ready = [e for e in order if _state[e[0]]["until"] <= now]
        if not ready:
            time.sleep(min(15, max(1.0, min(st["until"] for st in _state.values()) - now)))
            continue
        name, tpl = ready[0]
        _turn[0] = (_turn[0] + 1) % len(ENGINES)
        try:
            r = session.get(tpl.format(q=quote_plus(words.strip())), timeout=20,
                            headers={"User-Agent": SEARCH_UA, "Accept-Language": "en-US,en;q=0.9"})
        except requests.RequestException:
            cool(name, True)
            continue
        time.sleep(1.0)
        if r.status_code != 200:
            cool(name, True)
            continue
        hosts = result_hosts(r.text, per_query)
        if not hosts:
            low = r.text.lower()[:4000]
            cool(name, any(k in low for k in ("captcha", "unusual traffic", "verify you are", "are you a robot", "blocked")))
            continue
        _state[name]["strikes"] = 0
        return hosts
    return []


def discover(queries, session, per_query=15):
    """Each query is 'search words | Industry'. Returns (host, industry) pairs."""
    found = []
    for q in queries:
        words, _, industry = q.partition("|")
        for host in search_hosts(words, session, per_query):
            if host and not any(b in host for b in SKIP):
                found.append((host, industry.strip()))
    return found
