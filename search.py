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
    ("bing", "https://www.bing.com/search?q={q}&setlang=en&cc=us"),
    ("yahoo1", "https://search.yahoo.com/search?p={q}"),
    ("yahoo2", "https://search.yahoo.com/search?p={q}&b=11"),
    ("yahoo3", "https://search.yahoo.com/search?p={q}&b=21"),
    ("yahoo4", "https://search.yahoo.com/search?p={q}&b=31"),
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
    # Only the real result links, not sidebars, related searches or ads. Plain pages fall back to every link.
    anchors = soup.select("li.b_algo h2 a, li.b_algo .b_title a, div.algo h3 a, div.algo .compTitle a, .compTitle h3 a, h3.title a")
    anchors = [a for a in anchors if a.get("href")] or soup.find_all("a", href=True)[:12]
    for a in anchors:
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


STATS = {}


def _stat(name, key, n=1):
    st = STATS.setdefault(name, {"req": 0, "ok": 0, "hosts": 0, "blocked": 0})
    st[key] += n


def stats_line():
    return "search stats: " + ", ".join(f"{k} {v['req']} req {v['ok']} ok {v['hosts']} hosts {v['blocked']} blocked" for k, v in STATS.items())


def search_hosts(words, session, per_query=30):
    """Asks every source that is not cooling down (Bing page 1 and Yahoo pages 1-4) and merges what they find."""
    for _ in range(30):
        now = time.time()
        ready = [e for e in ENGINES if _state[e[0]]["until"] <= now]
        if not ready:
            time.sleep(min(15, max(1.0, min(st["until"] for st in _state.values()) - now)))
            continue
        merged = []
        for name, tpl in ready:
            _stat(name, "req")
            try:
                r = session.get(tpl.format(q=quote_plus(words.strip())), timeout=20,
                                headers={"User-Agent": SEARCH_UA, "Accept-Language": "en-US,en;q=0.9"})
            except requests.RequestException:
                _stat(name, "blocked")
                cool(name, True)
                continue
            time.sleep(0.7)
            if r.status_code != 200:
                _stat(name, "blocked")
                cool(name, r.status_code in (403, 429))  # 5xx from Yahoo comes and goes, only a short pause
                continue
            hosts = result_hosts(r.text, per_query)
            if not hosts:
                low = r.text.lower()[:4000]
                hard = any(k in low for k in ("captcha", "unusual traffic", "verify you are", "are you a robot", "blocked"))
                _stat(name, "blocked" if hard else "ok")
                cool(name, hard)
                continue
            _state[name]["strikes"] = 0
            _stat(name, "ok")
            _stat(name, "hosts", len(hosts))
            merged += [h for h in hosts if h not in merged]
        if merged:
            return merged
    return []


def discover(queries, session, per_query=30):
    """Each query is 'search words | Industry'. Returns (host, industry) pairs."""
    found = []
    for q in queries:
        words, _, industry = q.partition("|")
        for host in search_hosts(words, session, per_query):
            if host and not any(b in host for b in SKIP):
                found.append((host, industry.strip()))
    return found
