"""Quick diagnostic: how does each search engine answer from a GitHub runner? Prints status codes and counts only."""
import time
from urllib.parse import quote_plus

import requests

import search

ENGINES = list(search.ENGINES) + [
    ("startpage", "https://www.startpage.com/do/search?q={q}"),
    ("ecosia", "https://www.ecosia.org/search?q={q}"),
    ("ask", "https://www.ask.com/web?q={q}"),
    ("dogpile", "https://www.dogpile.com/serp?q={q}"),
    ("yandex", "https://yandex.com/search/?text={q}"),
    ("marginalia", "https://search.marginalia.nu/search?query={q}"),
    ("qwant", "https://www.qwant.com/?q={q}&t=web"),
    ("gigablast", "https://www.gigablast.com/search?q={q}"),
    ("searxbe", "https://searx.be/search?q={q}&format=html"),
    ("metager", "https://metager.org/meta/meta.ger3?eingabe={q}"),
    ("google", "https://www.google.com/search?q={q}&num=30&hl=en"),
    ("bing_cc", "https://www.bing.com/search?q={q}&cc=us&count=50"),
]
QUERIES = ["roofing contractor Tulsa OK family owned", "dental clinic Leeds", "hair salon Perth", "recruitment agency Denver CO",
           "مكتب استقدام الرياض", "Riyadh recruitment office Filipino domestic workers", "plumber Boise ID", "accountant Calgary"]
s = requests.Session()
for name, tpl in ENGINES:
    out = []
    for q in QUERIES:
        try:
            r = s.get(tpl.format(q=quote_plus(q)), timeout=20, headers={"User-Agent": search.SEARCH_UA, "Accept-Language": "en-US,en;q=0.9"})
            hosts = search.result_hosts(r.text, 30)
            out.append(f"{r.status_code}:{len(hosts)}")
        except Exception as e:
            out.append(type(e).__name__)
        time.sleep(1.5)
    print(f"{name:12s} " + " ".join(out), flush=True)
