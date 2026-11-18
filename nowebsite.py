"""No Website Leads: small businesses listed on Hotfrog with an email address but no website of their own.
Free sources only. Each shard takes its own slice of the searches. Env: SHARD, SHARDS, TARGET, MAX_SECONDS."""
import datetime
import json
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

SHARDS = max(1, int(os.environ.get("SHARDS", "1")))
SHARD = int(os.environ.get("SHARD", "0")) % SHARDS
TARGET = int(os.environ.get("TARGET", "400"))
MAX_SECONDS = int(os.environ.get("MAX_SECONDS", "20000"))
WORKERS = int(os.environ.get("WORKERS", "6"))
API = "https://sheets.googleapis.com/v4/spreadsheets"
LEADS_TAB = "No Website Leads"
CHECKED_TAB = "No Website Checked"
COLUMNS = ["#", "Date found", "Business", "Country", "City", "Industry", "Email", "Email type", "Phone", "Address",
           "Has website", "Has social media", "Social links", "Can they pay", "Why this score", "Source page"]
SITES = {"Australia": "https://www.hotfrog.com.au", "United Kingdom": "https://www.hotfrog.co.uk",
         "Canada": "https://www.hotfrog.ca", "New Zealand": "https://www.hotfrog.co.nz", "United States": "https://www.hotfrog.com"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HEAD = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s().\-]{7,16}\d)")
FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "icloud.com", "aol.com", "yahoo.com.au", "bigpond.com",
             "bigpond.net.au", "optusnet.com.au", "hotmail.co.uk", "yahoo.co.uk", "btinternet.com", "sky.com", "me.com", "msn.com",
             "protonmail.com", "xtra.co.nz", "shaw.ca", "rogers.com", "sympatico.ca", "telus.net", "ymail.com"}
GENERIC = {"info", "contact", "hello", "admin", "office", "enquiries", "enquiry", "sales", "support", "service", "services", "mail",
           "bookings", "booking", "accounts", "team", "reception", "general", "hi", "help", "orders", "inquiries", "inquiry", "customerservice"}
SOCIAL = ("facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com", "tiktok.com", "youtube.com", "pinterest.com")
NOT_SITE = ("hotfrog", "google.", "gstatic", "here.com", "centralindex", "apple.com", "w3.org", "schema.org", "bing.com", "cloudflare",
            "googletagmanager", "mailto:", "tel:", "javascript:")
STRONG = {"Home services", "Health", "Accounting", "Design and build", "Automotive"}
MEDIUM = {"Beauty salon", "Fitness", "Pet services", "Education", "Events and weddings", "Restaurant and cafe", "Local business", "Travel"}
STREET_RE = re.compile(r"\b\d{1,5}\s+[A-Za-z]")


def email_type(email):
    local = email.split("@")[0].lower()
    return "Shared" if local in GENERIC else "Personal"


def pay_score(industry, phone, address, desc_len, etype):
    pts = 2 if industry in STRONG else (1 if industry in MEDIUM else 0)
    why = [f"{industry} is a {'higher' if pts == 2 else 'mid'} paying trade"]
    if phone:
        pts += 1
        why.append("phone listed")
    if address and STREET_RE.search(address):
        pts += 1
        why.append("street address listed")
    if desc_len > 120:
        pts += 1
        why.append("wrote a full business profile")
    label = "Strong" if pts >= 5 else ("Medium" if pts >= 3 else "Weak")
    return label, "; ".join(why) + ". No review data on this directory"


def parse_detail(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.select_one("h1")
    name = re.sub(r"\s+", " ", h1.get_text(" ", strip=True)).strip() if h1 else ""
    if not name and soup.title:
        name = re.sub(r"\s+", " ", soup.title.get_text(" ", strip=True)).split(" - ")[0].split(" | ")[0].strip()
    mails = [a.get("href", "")[7:].split("?")[0].strip() for a in soup.select('a[href^="mailto:"]')]
    mails = [m for m in mails if EMAIL_RE.fullmatch(m) and "hotfrog" not in m.lower()]
    email = mails[0] if mails else ""
    tel = soup.select_one('a[href^="tel:"]')
    phone = tel.get("href", "")[4:].strip() if tel else ""
    addr_el = soup.select_one('[class*="address"]')
    address = re.sub(r"\s+", " ", addr_el.get_text(" ", strip=True)).split(" Show map")[0].strip() if addr_el else ""
    desc_el = soup.select_one('[class*="description"], [class*="entity-desc"]')
    desc_len = len(desc_el.get_text(" ", strip=True)) if desc_el else 0
    site, socials = "", []
    for a in soup.select('a[href^="http"]'):
        h = a.get("href", "")
        low = h.lower()
        host = (urlparse(h).hostname or "").lower()
        if any(host == x or host.endswith("." + x) for x in SOCIAL):
            if "hotfrog" not in low and h not in socials:
                socials.append(h)
            continue
        if any(x in low for x in NOT_SITE):
            continue
        if not site:
            site = h
    return {"name": name, "email": email, "phone": phone, "address": address, "desc_len": desc_len, "site": site, "socials": socials}


def domain_has_site(domain, session):
    """True when the email's own domain serves a real web page (the business has a site Hotfrog does not list)."""
    for scheme in ("https://", "http://"):
        try:
            r = session.get(scheme + domain, timeout=8, headers=HEAD, allow_redirects=True)
            if r.status_code < 400 and len(r.text) > 600:
                return True
        except Exception:
            continue
    return False


class Sheet:
    def __init__(self):
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account
        info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        creds = service_account.Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        self.s = AuthorizedSession(creds)
        self.sid = os.environ["SHEET_ID"]
        self._ensure()

    def _u(self, tab, rng):
        return f"{API}/{self.sid}/values/{quote(tab + '!' + rng, safe='')}"

    def _ensure(self):
        m = self.s.get(f"{API}/{self.sid}", params={"fields": "sheets.properties(title)"})
        m.raise_for_status()
        have = {x["properties"]["title"] for x in m.json()["sheets"]}
        want = {LEADS_TAB: COLUMNS, CHECKED_TAB: ["Source page", "Date", "Result"]}
        for t, head in want.items():
            if t not in have:
                b = self.s.post(f"{API}/{self.sid}:batchUpdate", json={"requests": [{"addSheet": {"properties": {"title": t}}}]})
                if b.status_code >= 400 and "already exists" not in b.text:
                    b.raise_for_status()
                u = self.s.put(self._u(t, "A1"), params={"valueInputOption": "RAW"}, json={"values": [head]})
                u.raise_for_status()

    def col(self, tab, letter):
        for attempt in range(4):
            r = self.s.get(self._u(tab, f"{letter}:{letter}"))
            if r.status_code == 429:
                time.sleep(20 * (attempt + 1))
                continue
            r.raise_for_status()
            return [(v[0] if v else "").strip().lower() for v in r.json().get("values", [])[1:]]
        return []

    def append(self, tab, rows):
        if not rows:
            return
        for attempt in range(5):
            a = self.s.post(self._u(tab, "A1") + ":append", params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
                            json={"values": rows})
            if a.status_code in (429, 500, 503):
                time.sleep(15 * (attempt + 1))
                continue
            a.raise_for_status()
            return


def queries(day):
    import run
    import shard_more
    pairs = [(ind, n) for ind, ns in shard_more.NICHES.items() for n in ns]
    out = []
    for country in SITES:
        for city in run.CITIES.get(country, []):
            for ind, n in pairs:
                out.append((country, city, ind, n))
    random.Random(day).shuffle(out)
    return out


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def listing_links(session, base, city, niche, page):
    for q in (slug(niche), quote(niche.lower())):
        url = f"{base}/search/{slug(city)}/{q}" + (f"?page={page}" if page > 1 else "")
        try:
            r = session.get(url, timeout=25, headers=HEAD)
        except Exception:
            return [], -1
        if r.status_code != 200:
            if r.status_code in (403, 429):
                return [], r.status_code
            continue
        links = []
        for a in BeautifulSoup(r.text, "html.parser").select('a[href*="/company/"]'):
            h = urljoin(base, a.get("href", "").split("?")[0])
            if h not in links:
                links.append(h)
        if links:
            return links, 200
    return [], 200


def main():
    started = time.time()
    today = datetime.date.today()
    stamp = today.isoformat()
    sh = Sheet()
    session = requests.Session()
    checked = set(sh.col(CHECKED_TAB, "A"))
    emails_have = set(sh.col(LEADS_TAB, "G"))
    n_rows = len(sh.col(LEADS_TAB, "A"))
    print(f"shard {SHARD}/{SHARDS}: {len(checked)} pages checked, {n_rows} leads in the tab", flush=True)
    kept = looked = blocked = searches = 0
    why_not = {}
    DEBUG = []
    qs = queries(today.toordinal())
    for qi, (country, city, ind, niche) in enumerate(qs):
        if qi % SHARDS != SHARD:
            continue
        if time.time() - started > MAX_SECONDS or kept >= TARGET:
            break
        base = SITES[country]
        for page in (1, 2, 3):
            links, code = listing_links(session, base, city, niche, page)
            searches += 1
            if code in (403, 429):
                blocked += 1
                time.sleep(30)
                break
            fresh = [l for l in links if l.lower() not in checked]
            if not links:
                break
            if fresh:
                checked.update(l.lower() for l in fresh)
                def work(u):
                    time.sleep(random.uniform(0.5, 1.5))
                    try:
                        r = session.get(u, timeout=25, headers=HEAD)
                        d = parse_detail(r.text, u) if r.status_code == 200 else None
                        if not d or not d["name"]:
                            if len(DEBUG) < 4:
                                DEBUG.append((u[-50:], r.status_code, len(r.text), re.sub(r"\s+", " ", r.text[:150])))
                        return u, d, r.status_code
                    except Exception as ex:
                        if len(DEBUG) < 4:
                            DEBUG.append((u[-50:], type(ex).__name__))
                        return u, None, -1
                with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                    res = list(ex.map(work, fresh))
                new_rows, chk = [], []
                fresh_emails = set(sh.col(LEADS_TAB, "G")) if res else set()
                for u, d, st in res:
                    looked += 1
                    if not d or not d["name"]:
                        why_not[f"page error {st}"] = why_not.get(f"page error {st}", 0) + 1
                        if st in (403, 429):
                            blocked += 1
                        continue
                    result = "kept"
                    if not d["email"]:
                        result = "no email"
                    elif d["site"]:
                        result = "has website"
                    elif d["email"].lower() in emails_have or d["email"].lower() in fresh_emails:
                        result = "duplicate"
                    else:
                        dom = d["email"].split("@")[1].lower()
                        if dom not in FREE_MAIL and domain_has_site(dom, session):
                            result = "has website (email domain)"
                    if result == "kept":
                        et = email_type(d["email"])
                        label, why = pay_score(ind, d["phone"], d["address"], d["desc_len"], et)
                        if label == "Weak":
                            result = "weak payer"
                        else:
                            n_rows += 1
                            kept += 1
                            emails_have.add(d["email"].lower())
                            new_rows.append([n_rows, stamp, d["name"], country, city, ind, d["email"], et,
                                             ("'" + d["phone"]) if d["phone"][:1] in "+=-@" else d["phone"], d["address"],
                                             "No", "Yes" if d["socials"] else "No", ", ".join(d["socials"][:3]), label, why, u])
                    why_not[result] = why_not.get(result, 0) + 1
                    chk.append([u, stamp, result])
                sh.append(LEADS_TAB, new_rows)
                sh.append(CHECKED_TAB, chk)
                print(f"shard {SHARD}: searches {searches}, pages looked at {looked}, kept {kept}, blocked {blocked} | {why_not} | {DEBUG}", flush=True)
            if len(links) < 8:
                break
    print(f"shard {SHARD} done: kept {kept}, looked at {looked}, searches {searches}, blocked {blocked}", flush=True)


if __name__ == "__main__":
    main()
