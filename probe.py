"""Probe 4: does Bing give new hosts on result pages 2 to 4, and do Gulf directories load from this runner?"""
import re
import time
from urllib.parse import quote_plus, unquote, urlparse

import requests

import search

H = {"User-Agent": search.SEARCH_UA, "Accept-Language": "en-US,en;q=0.9"}
s = requests.Session()
QS = ["recruitment agency Riyadh Filipino domestic workers contact email", "مكتب استقدام الرياض الفلبين", "manpower supply company Doha Qatar recruitment contact"]
SKIP = ("bing.", "microsoft.", "msn.", "google.", "facebook.", "youtube.", "linkedin.", "wikipedia.")


def hosts(html):
    out = []
    for h in re.findall(r'<li class="b_algo".*?<a[^>]+href="(https?://[^"]+)"', html, re.S):
        host = (urlparse(unquote(h)).hostname or "").lower().replace("www.", "")
        if host and host not in out and not any(x in host for x in SKIP):
            out.append(host)
    return out


for q in QS:
    seen = set()
    for first in (1, 11, 21, 31, 41):
        try:
            r = s.get("https://www.bing.com/search?q=" + quote_plus(q) + f"&first={first}&setlang=en", timeout=25, headers=H)
            hs = hosts(r.text)
            new = [h for h in hs if h not in seen]
            seen.update(hs)
            print(f"{q[:40].encode('unicode_escape').decode()!r} first={first} status={r.status_code} hosts={len(hs)} new={len(new)} {new[:5]}", flush=True)
        except Exception as ex:
            print("error", type(ex).__name__, flush=True)
        time.sleep(2)
print("--- directories", flush=True)
for u in ["https://www.yellowpages.com.sa/", "https://www.saudiyellowpages.com/", "https://www.yellowpages.qa/", "https://www.qatarYellowpages.com/", "https://www.hotfrog.ae/search/dubai/recruitment",
          "https://www.hotfrog.com.sa/", "https://sa.kompass.com/", "https://qa.kompass.com/", "https://www.cylex.com.sa/", "https://www.yellow-pages.qa/",
          "https://www.2findlocal.com/", "https://www.infobel.com/en/saudi_arabia", "https://www.infobel.com/en/qatar", "https://www.europages.com/", "https://www.exportersindia.com/",
          "https://dir.qatar.ae/", "https://www.zawya.com/", "https://www.arabianbusiness.com/"]:
    try:
        r = s.get(u, timeout=20, headers=H)
        print(u[:60], r.status_code, "len", len(r.text), flush=True)
    except Exception as ex:
        print(u[:60], "error", type(ex).__name__, flush=True)
    time.sleep(1)
