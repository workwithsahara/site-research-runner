"""Site checker for small-business research.

Rules:
- Target countries: US, Canada, Australia, UK, New Zealand. Small teams only.
- Tier A: email PROVEN owner-direct (found on the company's own pages, never guessed).
- Tier B: phone-first. Owner named and phone present, email is a general inbox, labelled as such.
- A lead must show at least one visible gap we can help with (website or social).
- Shopify stores are only ever offered LAYA 365, never a website.
- Only leads that pass everything are kept. Near misses go to a review file with the reason.
"""
import csv
import datetime
import html
import json
import os
import re
import time
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

import personalize

UA = "Mozilla/5.0 (compatible; LAYALeadResearch/1.0)"
DELAY = float(os.environ.get("CRAWL_DELAY", "1.5"))
TIMEOUT = 15
MAX_PAGES = 6
HIGH_TICKET_MEDIAN = float(os.environ.get("HIGH_TICKET_MEDIAN", "400"))
HIGH_TICKET_MAX = float(os.environ.get("HIGH_TICKET_MAX", "1000"))

COLUMNS = [
    "#", "Company", "Website", "First name", "Owner or founder (public)", "Phone",
    "Email", "Email note", "Industry", "Based in", "Size signal", "Visible gap",
    "Offer to pitch", "Fits your criteria", "Ask on first call", "Date found",
    "Personalized", "Why this line", "Lead tier", "Role to apply for", "Email 1 sent", "Email 2 sent", "Responded", "General email (info/support)", "Email type",
]
ALLOWED = {"United States", "Canada", "Australia", "United Kingdom", "New Zealand"}
COUNTRY_TLD = [(".co.uk", "United Kingdom"), (".org.uk", "United Kingdom"), (".uk", "United Kingdom"),
               (".com.au", "Australia"), (".au", "Australia"), (".co.nz", "New Zealand"),
               (".nz", "New Zealand"), (".ca", "Canada")]
PREFIX_COUNTRY = {"+44": "United Kingdom", "+61": "Australia", "+64": "New Zealand"}
INTL_RE = re.compile(r"(?<!\d)(\+(?:44|61|64)[\s.\-]?(?:\(0\))?[\s.\-]?\d[\d\s.\-]{6,12}\d)")
BUILDERS = (("wixstatic.com", "Wix"), ("wix.com", "Wix"), ("weebly.com", "Weebly"),
            ("godaddysites.com", "GoDaddy"), ("img1.wsimg.com", "GoDaddy"), ("jimdo", "Jimdo"))
FORM_HINTS = ("hsforms", "typeform", "jotform", "calendly", "formstack", "wufoo", "gravityforms", "wpforms")
SOCIAL_RE = re.compile(r"(facebook|instagram|linkedin)\.com/(?!sharer|share|tr\?|tr/|plugins|dialog|login)([A-Za-z0-9_.\-/]{2,})", re.I)
MAX_HEADCOUNT = int(os.environ.get("MAX_HEADCOUNT", "25"))
MAX_TEAM_LAYA = int(os.environ.get("MAX_TEAM", "8"))


def clean_phone(raw):
    return re.sub(r"\s+", " ", raw).strip(" .-")


CC = {"Australia": "61", "New Zealand": "64", "United Kingdom": "44", "United States": "1", "Canada": "1"}


def fmt_phone(p, country=""):
    """US/Canada: 646-706-5330. Everyone else: +61 4xx xxx xxx (always with the country code, never US style)."""
    d = re.sub(r"\D", "", p)
    cc = CC.get(country, "")
    if cc == "1" or (not cc and (not p.strip().startswith("+") or (d.startswith("1") and len(d) == 11))):
        if len(d) == 11 and d.startswith("1"):
            d = d[1:]
        if len(d) == 10:
            return f"{d[:3]}-{d[3:6]}-{d[6:]}"
        return p
    if not cc:
        return p
    nat = d[len(cc):] if (d.startswith(cc) and len(d) > len(cc) + 6) else d
    if nat.startswith("0") and not nat.startswith(("0800", "0508", "0900")):
        nat = nat[1:]
    if nat.startswith(("1300", "1800", "0800", "0508")) and len(nat) in (10,):
        return f"{nat[:4]} {nat[4:7]} {nat[7:]}"
    if len(nat) == 6 and nat.startswith("13"):
        return f"{nat[:2]} {nat[2:4]} {nat[4:]}"
    if cc == "61" and len(nat) == 9:
        return f"+61 {nat[0]} {nat[1:5]} {nat[5:]}" if nat[0] != "4" else f"+61 {nat[:3]} {nat[3:6]} {nat[6:]}"
    if cc == "64" and 8 <= len(nat) <= 10:
        return f"+64 {nat[:2]} {nat[2:5]} {nat[5:]}" if nat[0] == "2" else f"+64 {nat[0]} {nat[1:4]} {nat[4:]}"
    if cc == "44" and len(nat) == 10:
        return f"+44 {nat[:2]} {nat[2:6]} {nat[6:]}" if nat[0] in "2" else f"+44 {nat[:4]} {nat[4:7]} {nat[7:]}"
    return "+" + cc + " " + nat


STREET_WORDS = r"(?:Street|St|Avenue|Ave|Road|Rd|Blvd|Boulevard|Drive|Dr|Lane|Ln|Way|Suite|Ste|Floor|Fl|Highway|Hwy)"


def clean_city(raw):
    raw = raw.strip()
    parts = re.split(r"\b" + STREET_WORDS + r"\b\.?\s*", raw)
    if len(parts) > 1:
        raw = re.sub(r"^(?:North|South|East|West|N|S|E|W)\b\.?\s+", "", parts[-1].strip())
    return raw


def lead_phones(pages, texts, country):
    out, seen = [], set()

    def add(p):
        key = re.sub(r"\D", "", p)[-9:]
        if key and key not in seen:
            seen.add(key)
            out.append(fmt_phone(clean_phone(p), country))

    for h, t in zip(pages.values(), texts):
        for m in re.finditer(r"tel:([+\d\-\s().%]+)", h):
            raw = unquote(m.group(1)).strip()
            if 9 <= len(re.sub(r"\D", "", raw)) <= 15:
                add(raw)
        if country in ("United States", "Canada", ""):
            for p in extract_phones(h):
                add(p)
        for m in INTL_RE.finditer(t):
            add(m.group(1))
    return out


def social_found(pages):
    found = set()
    for h in pages.values():
        for m in SOCIAL_RE.finditer(h):
            found.add(m.group(1).lower())
    return found


def visible_gaps(pages, home_html, home_soup, platform, year=None):
    year = year or datetime.date.today().year
    gaps = []
    if not home_soup.find("meta", attrs={"name": "viewport"}):
        gaps.append("no mobile viewport tag")
    low = home_html.lower()
    for sig, name in BUILDERS:
        if sig in low:
            gaps.append(f"{name} builder site")
            break
    text = BeautifulSoup(home_html, "html.parser").get_text(" ")
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d\d)", home_html + " " + text, re.I)]
    if years and max(years) <= year - 3:
        gaps.append(f"footer says {max(years)}")
    alllow = " ".join(pages.values()).lower()
    if "<form" not in alllow and not any(k in alllow for k in FORM_HINTS):
        gaps.append("no inquiry form found")
    return gaps


def offer_for(platform, gaps, socials):
    no_social = not socials
    if platform == "Shopify":
        return ("LAYA 365", gaps, no_social) if no_social else ("", gaps, no_social)
    parts = []
    if gaps:
        parts.append("Website")
    if no_social:
        parts.append("LAYA 365")
    return (" + ".join(parts), gaps, no_social)


def lead_gap_text(gaps, socials, platform):
    out = list(gaps) if platform != "Shopify" else []
    if not socials:
        out.append("no Facebook, Instagram or LinkedIn link on the site")
    return "; ".join(out)


def _collapse(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def clean_company(soup, domain):
    """Business name: prefer site name tags, then a title piece that matches the domain, never a tagline."""
    stem = domain.lower().replace("www.", "").split(".")[0]
    cands = []
    for attrs in ({"property": "og:site_name"}, {"name": "application-name"}):
        t = soup.find("meta", attrs=attrs)
        if t and t.get("content"):
            cands.append(t["content"].strip())
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string or "")
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                if isinstance(d.get("@graph"), list):
                    stack.extend(d["@graph"])
                if d.get("name") and str(d.get("@type", "")) and re.search(r"Organization|LocalBusiness|Agency|Service", str(d.get("@type"))):
                    cands.append(str(d["name"]).strip())
            elif isinstance(d, list):
                stack.extend(d)
    if soup.title:
        for piece in re.split(r"\s*[|\u2013\u2014\u00b7:]\s*|\s+-\s+", soup.title.get_text(strip=True)):
            if piece.strip():
                cands.append(piece.strip())
    cands = [c for c in cands if 2 <= len(c) <= 60 and not re.search(r"(?i)just a moment|access denied|attention required|403|404|forbidden|home$|^home", c)]
    for c in cands:
        cc = _collapse(c)
        if cc and len(stem) >= 4 and (stem in cc or cc in stem):
            return c
    return stem.replace("-", " ").title()


def analyze_site(domain, session, industry="", headcount=None, hint_country="", locality="", company=""):
    base = "https://" + domain.strip().lower().replace("https://", "").replace("http://", "").strip("/")
    if not robots_ok(base, session):
        return None, "blocked by robots.txt"
    home = get(base, session)
    if not home or home.status_code != 200:
        return None, "site not reachable"
    pages = {base: home.text}
    soup = BeautifulSoup(home.text, "html.parser")
    for a in soup.find_all("a", href=True):
        if len(pages) >= MAX_PAGES:
            break
        u = urljoin(base + "/", a["href"]).split("#")[0]
        if urlparse(u).netloc.replace("www.", "") == urlparse(base).netloc.replace("www.", "") \
                and CTA_PAGE.search(urlparse(u).path) and u not in pages:
            r = get(u, session)
            if r and r.status_code == 200:
                pages[u] = r.text
    texts = [BeautifulSoup(h, "html.parser").get_text(" ") for h in pages.values()]
    alltext = " ".join(texts)
    own_domain = urlparse(base).netloc.replace("www.", "")
    platform = detect_platform(home.text)
    owner = ""
    for t in texts:
        owner = find_owner(t, own_domain)
        if owner:
            break
    emails = set()
    for h in pages.values():
        emails |= extract_emails(h)
    label = own_domain.split(".")[0]
    emails = {e for e in emails if label in e.split("@")[1]}
    direct, general = [], []
    for e in sorted(emails):
        ok, n = email_proven(e, owner, texts)
        (direct if ok else general).append((e, n))

    country = hint_country
    if not country:
        for suffix, c in COUNTRY_TLD:
            if own_domain.endswith(suffix):
                country = c
                break
    addr = ADDR_RE.search(alltext)
    city = clean_city(addr.group(1)) if addr else ""
    based = (f"{city}, {addr.group(2)}" if city else addr.group(2)) if addr else ""
    phones = lead_phones(pages, texts, country)
    if not country:
        for p in phones:
            if p.replace(" ", "").startswith(tuple(PREFIX_COUNTRY)):
                country = PREFIX_COUNTRY[p.replace(" ", "")[:3]]
                break
    if not country and phones and (addr or "$" in alltext or "USD" in alltext):
        country = "United States"
    team = count_team(texts)
    big = BIG_RE.search(alltext)
    socials = social_found(pages)
    gaps = visible_gaps(pages, home.text, soup, platform)
    offer, gaps, no_social = offer_for(platform, gaps, socials)

    fails = []
    if country not in ALLOWED:
        fails.append(f"country not in target list ({country or 'not confirmed'})")
    if headcount and headcount > MAX_HEADCOUNT:
        fails.append(f"headcount {headcount} is over {MAX_HEADCOUNT}")
    if not owner:
        fails.append("no owner named on public pages")
    if not phones:
        fails.append("no phone")
    if direct:
        tier = "A: owner email proven, reach the owner by email and phone"
    elif general:
        generic = general[0][1].startswith("general inbox")
        tier = ("B: phone-first, email is a general inbox (not owner-direct)" if generic
                else "B: phone-first, email is not proven to be the owner's")
    else:
        tier = ""
        fails.append("no email found on site")
    if team > MAX_TEAM_LAYA:
        fails.append(f"not an A fit, team looks large ({team} named staff with titles)")
    if big:
        fails.append(f"not an A fit, big-company wording on site ('{big.group(0)}')")
    if not offer:
        fails.append("no visible gap to pitch" if platform != "Shopify" else "Shopify store already shows social links")

    email, email_note = (direct[0] if direct else ("", general[0][1] if general else "no email found on site"))
    general_email = ", ".join(e for e, _ in general) if not direct else ""
    name = company or clean_company(soup, domain)
    first = owner.split()[0] if owner else ""
    line, why = personalize.personalize(name, first, industry, alltext)
    gap_text = lead_gap_text(gaps, socials, platform)
    row = {
        "Company": name, "Website": base, "First name": first, "Owner or founder (public)": owner,
        "Phone": phones[0] if phones else "", "Email": email, "Email note": email_note,
        "Industry": industry or "Unsorted", "Based in": based or locality or country,
        "Size signal": f"{headcount} employees (Clay estimate), " if headcount else "",
        "Visible gap": gap_text, "Offer to pitch": offer,
        "Fits your criteria": (f"{country}, owner named, " + ("proven owner email" if tier.startswith("A") else ("general inbox only, call the owner first" if "general inbox" in tier else "email not proven to be the owner's, call the owner first"))
                               + f", small team ({team} titled staff on site), visible gap found (fit signals only, not proof)") if not fails else "; ".join(fails),
        "Ask on first call": personalize.ask_on_call(industry),
        "Personalized": line, "Why this line": why, "Lead tier": tier,
        "Role to apply for": personalize.role_for(industry, offer, gaps, no_social, alltext),
        "General email (info/support)": general_email,
        "Email type": "Personal" if direct else ("Shared" if general else ""),
    }
    row["Size signal"] += f"{team} named staff with titles on site. Revenue not verified, check on first call"
    return (row, fails), None


def discover(queries, session, per_query=15):
    """Free discovery through DuckDuckGo's HTML results. Best effort, may be rate limited.
    Each query is 'search words | Industry'. Returns (host, industry) pairs."""
    found = []
    skip = ("amazon.", "ebay.", "facebook.", "youtube.", "reddit.", "wikipedia.", "pinterest.", "yelp.", "google.",
            "indeed.", "linkedin.", "glassdoor.", "ziprecruiter.", "monster.", "reed.co.uk", "totaljobs.", "seek.com",
            "cv-library.", "jooble.", "instagram.", "twitter.", "x.com", "clutch.co", "trustpilot.", "mapquest.",
            "merriam-webster.", "dictionary.", "vocabulary.", "thefreedictionary.", "bing.", "bbb.org", "yellowpages.", "zoominfo.",
            "crunchbase.", "apollo.io", "owler.", "dnb.com", "manta.com", "comparably.", "ambitionbox.", "craigslist.", "tiktok.",
            "quora.", "medium.com", "forbes.", "inc.com", "gov.", ".gov", "salary.com", "payscale.", "simplyhired.", "careerbuilder.", "lensa.")
    for q in queries:
        words, _, industry = q.partition("|")
        hrefs = []
        r = get("https://html.duckduckgo.com/html/?q=" + quote_plus(words.strip()), session)
        if r and r.status_code == 200:
            for a in BeautifulSoup(r.text, "html.parser").select("a.result__a")[:per_query]:
                href = a.get("href", "")
                if "uddg=" in href:
                    href = unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
                hrefs.append(href)
        for href in hrefs:
            host = urlparse(href).netloc.replace("www.", "")
            if host and not any(b in host for b in skip):
                found.append((host, industry.strip()))
    return found


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def parse_seed(line):
    """domain | Industry | headcount | Country | Locality | Company name (everything after domain is optional)."""
    f = [x.strip() for x in line.split("|")] + [""] * 6
    hc = int(f[2]) if f[2].isdigit() else None
    return {"domain": f[0].lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/"),
            "industry": f[1], "headcount": hc, "country": f[3], "locality": f[4], "company": f[5]}


GENERIC_LOCALS = {
    "info", "support", "sales", "contact", "team", "hello", "hi", "help", "admin",
    "service", "customerservice", "customercare", "orders", "order", "care",
    "office", "mail", "enquiries", "inquiries", "webmaster", "billing", "shop",
    "store", "press", "media", "marketing", "careers", "jobs", "returns", "feedback",
    "noreply", "no-reply", "accounts", "wholesale", "dealers",
}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s.\-]?)?\(?([2-9]\d{2})\)?[\s.\-]?([2-9]\d{2})[\s.\-]?(\d{4})(?!\d)")
ROLE = r"(?:Co-?\s?Founder|Founder|Owner|CEO|President|Managing Director|Managing Partner|Principal)"
NAME = r"[A-Z][a-z]{1,15}(?:\s+[A-Z][a-z'\-]{1,20})?"
OWNER_PATTERNS = [
    re.compile(r"\b(?i:I'?m|I am|My name is|Hi,? I'?m|Hello,? I'?m)\s+(" + NAME + r")[^.\n]{0,100}?\b(?i:" + ROLE + r")"),
    re.compile(r"(" + NAME + r")\s*[,\-|:–\u2014]?\s*\(?\s*" + ROLE + r"\b"),
    re.compile(r"\b" + ROLE + r"\s*[:\-|,]\s*(" + NAME + r")"),
    re.compile(r"\b(?i:Founded|Owned|Started|Run)\s+(?i:by)\s+(" + NAME + r")"),
]
NAME_STOP = {"The", "Our", "We", "This", "Your", "Meet", "About", "Contact", "Team", "Hi", "Hello",
             "Welcome", "Customer", "Family", "Company", "Store", "Shop", "Read", "More", "And",
             "Is", "At", "In", "Of", "For", "With", "Chief", "Executive", "Vice", "Sales",
             "Competitors", "Price", "Before", "Vacation", "Institute", "Golfers", "Using", "Master",
             "Craftsman", "Co", "Founder", "Owner", "Best", "Top", "Free", "New", "Shipping", "Order",
             "Operated", "Visionary", "Leadership", "Beginning", "Guide", "Video", "Camping", "Truck",
             "Focus", "Global", "Original", "Care", "Provider", "Repair", "From", "Living", "Group",
             "Industries", "Industrial", "Brands", "Brand", "Products", "Services", "Solutions", "Inc",
             "Llc", "Sarl", "Ltd", "Corp", "Corporation", "Customer", "Experts", "Specialists", "Digital", "Assets", "Talent", "Search", "Recruitment", "Technology", "Finance", "Partners", "Consulting", "Capital", "Data", "International", "Staffing", "Resourcing", "Associates", "Managing", "Director", "Principal", "Senior", "Recruiter", "Consultant", "Team", "Leader", "Head", "Business", "Development", "Supplier", "Direct", "People", "Plugin", "Advisory", "Agency", "Careers", "Employer", "Employment", "Hiring", "Jobs", "Job", "Marketing", "Operations", "Project", "Support", "Specialist", "Executive"}
US_STATES = "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split()
ADDR_RE = re.compile(r"([A-Z][A-Za-z.\- ]{2,30}),\s*(" + "|".join(US_STATES) + r")\b\s*\d{5}")
CTA_PAGE = re.compile(r"about|team|contact|story|who-we-are|meet|founder|our-", re.I)


def get(url, session):
    try:
        r = session.get(url, timeout=TIMEOUT, headers={"User-Agent": UA}, allow_redirects=True)
        time.sleep(DELAY)
        return r
    except requests.RequestException:
        return None


def robots_ok(base, session):
    try:
        r = session.get(urljoin(base, "/robots.txt"), timeout=TIMEOUT, headers={"User-Agent": UA})
        if r.status_code != 200:
            return True
        rp = RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp.can_fetch(UA, base + "/")
    except requests.RequestException:
        return True


def decode_cf(hexstr):
    try:
        key = int(hexstr[:2], 16)
        return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))
    except ValueError:
        return ""


def extract_emails(raw_html):
    """Only emails literally present on the page. Never guessed."""
    found = set()
    for m in re.finditer(r"data-cfemail=\"([0-9a-fA-F]+)\"", raw_html):
        e = decode_cf(m.group(1))
        if "@" in e:
            found.add(e.lower())
    for m in re.finditer(r"/cdn-cgi/l/email-protection#([0-9a-fA-F]+)", raw_html):
        e = decode_cf(m.group(1))
        if "@" in e:
            found.add(e.lower())
    text = html.unescape(raw_html)
    for m in re.finditer(r"mailto:([^\"'?>\s]+)", text, re.I):
        found.add(unquote(m.group(1)).strip().lower())
    for m in EMAIL_RE.finditer(BeautifulSoup(text, "html.parser").get_text(" ")):
        found.add(m.group(0).lower())
    bad_ext = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
    return {e for e in found if EMAIL_RE.fullmatch(e) and not e.endswith(bad_ext)
            and "sentry" not in e and "example" not in e and "wixpress" not in e}


def extract_phones(raw_html):
    phones = []
    for m in re.finditer(r"tel:([+\d\-\s().]+)", raw_html):
        p = PHONE_RE.search(m.group(1))
        if p:
            phones.append("-".join(p.groups()))
    text = BeautifulSoup(raw_html, "html.parser").get_text(" ")
    for p in PHONE_RE.finditer(text):
        phones.append("-".join(p.groups()))
    seen, out = set(), []
    for p in phones:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def find_owner(text, domain=""):
    dkey = re.sub(r"[^a-z]", "", domain.lower().split(".")[0]) if domain else ""
    for pat in OWNER_PATTERNS:
        for m in pat.finditer(text):
            name = m.group(1).strip()
            parts = [p.strip("-'") for p in name.split()]
            if not parts or parts[0] in NAME_STOP:
                continue
            fullkey = re.sub(r"[^a-z]", "", name.lower())
            if dkey and len(fullkey) > 4 and (fullkey in dkey or dkey in fullkey):
                continue  # looks like the brand name, not a person
            if len(parts) > 1 and parts[1] in NAME_STOP:
                parts = parts[:1]
            cand = " ".join(parts[:2])
            return cand
    return ""


def norm(s):
    return re.sub(r"[^a-z]", "", s.lower())


def email_proven(email, owner, page_texts):
    """Return (is_owner_direct, note). No guessing: the address must exist on the site."""
    local, _, domain = email.partition("@")
    base = local.split("+")[0]
    if norm(base) in GENERIC_LOCALS or re.sub(r"\d", "", base) in GENERIC_LOCALS:
        return False, "general inbox, not owner-direct"
    if not owner:
        return False, "personal-looking address but no owner name found to tie it to"
    parts = owner.lower().split()
    first, last = norm(parts[0]), norm(parts[-1]) if len(parts) > 1 else ""
    n = norm(base)
    candidates = {first}
    if last:
        candidates |= {last, first + last, first[0] + last, first + last[0], last + first[0], last + first}
    if n in candidates:
        return True, "owner-direct, address on the store's own page and matches owner name"
    for t in page_texts:
        for m in re.finditer(re.escape(email), t, re.I):
            before = t[max(0, m.start() - 120): m.start()]
            idx = before.lower().rfind(parts[0])
            if idx < 0:
                continue
            seg = before[idx:]
            if re.search(ROLE, seg, re.I) and not re.search(r"[.!?]\s", seg):
                return True, "owner-direct, address sits right after owner name and title on the page"
    return False, "address found but not tied to the owner on the page"


def detect_platform(raw):
    low = raw.lower()
    if "cdn.shopify.com" in low or "shopify-digital-wallet" in low or "/cdn/shop/" in low:
        return "Shopify"
    if "bigcommerce" in low:
        return "BigCommerce"
    if "woocommerce" in low or "wp-content/plugins/woocommerce" in low:
        return "WooCommerce"
    return ""


TEAM_RE = re.compile(
    r"([A-Z][a-z]{1,15}\s+[A-Z][a-z'\-]{1,20})\s*[,\-|:–\u2014]?\s*"
    r"(?:[A-Z][a-z]+\s+){0,2}(?:Manager|Director|VP|Vice President|Specialist|Coordinator|"
    r"Representative|Associate|Technician|Designer|Engineer|Advisor|Consultant|Supervisor)")
BIG_RE = re.compile(r"\b(NYSE|NASDAQ|Fortune 500|publicly traded|franchise opportunit\w+|"
                    r"\d{3,}\+? (?:employees|team members)|locations nationwide)\b", re.I)
MAX_TEAM = int(os.environ.get("MAX_TEAM", "7"))


def count_team(texts):
    names = set()
    for t in texts:
        for m in TEAM_RE.finditer(t):
            names.add(m.group(1).lower())
    return len(names)



