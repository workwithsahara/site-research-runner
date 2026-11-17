"""Shows what Bing and Yahoo really return from this runner for a few searches (hosts only)."""
import time
from urllib.parse import quote_plus

import requests

import search

QS = ["Riyadh recruitment agency contact us email Filipino", "Qatar housemaid recruitment office Filipino workers",
      "مكتب استقدام عمالة منزلية الفلبين", "roofing contractor Tulsa Oklahoma"]
URLS = [("bing_en", "https://www.bing.com/search?q={q}&setlang=en&cc=us"),
        ("bing_noloc", "https://www.bing.com/search?q={q}"),
        ("bing_ar", "https://www.bing.com/search?q={q}&setlang=ar&cc=sa"),
        ("yahoo", "https://search.yahoo.com/search?p={q}&n=30")]
s = requests.Session()
for q in QS:
    print("QUERY", q, flush=True)
    for name, tpl in URLS:
        try:
            r = s.get(tpl.format(q=quote_plus(q)), timeout=20, headers={"User-Agent": search.SEARCH_UA, "Accept-Language": "en-US,en;q=0.9"})
            hosts = search.result_hosts(r.text, 12)
            print(f"  {name} {r.status_code} blocks={r.text.count('b_algo')} {hosts}", flush=True)
        except Exception as e:
            print(f"  {name} error {type(e).__name__}", flush=True)
        time.sleep(1.5)
