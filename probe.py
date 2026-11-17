"""Shows what deeper Bing and Yahoo result pages return from this runner (hosts only)."""
import time
from urllib.parse import quote_plus

import requests

import search

QS = ["مكتب استقدام عمالة منزلية الفلبين", "مكتب استقدام الرياض واتساب", "roofing contractor Tulsa Oklahoma"]
URLS = [("bing_p1", "https://www.bing.com/search?q={q}"),
        ("bing_p2", "https://www.bing.com/search?q={q}&first=11"),
        ("bing_p3", "https://www.bing.com/search?q={q}&first=21"),
        ("bing_p4", "https://www.bing.com/search?q={q}&first=31"),
        ("yahoo_p1", "https://search.yahoo.com/search?p={q}"),
        ("yahoo_p2", "https://search.yahoo.com/search?p={q}&b=11"),
        ("yahoo_p3", "https://search.yahoo.com/search?p={q}&b=21")]
s = requests.Session()
for q in QS:
    print("QUERY", q.encode("unicode_escape").decode() if not q.isascii() else q, flush=True)
    for name, tpl in URLS:
        try:
            r = s.get(tpl.format(q=quote_plus(q)), timeout=20, headers={"User-Agent": search.SEARCH_UA, "Accept-Language": "en-US,en;q=0.9"})
            hosts = search.result_hosts(r.text, 12)
            print(f"  {name} {r.status_code} {hosts}", flush=True)
        except Exception as e:
            print(f"  {name} error {type(e).__name__}", flush=True)
        time.sleep(1.5)
