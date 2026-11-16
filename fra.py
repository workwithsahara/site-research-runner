"""Finds Saudi and Qatar recruitment agencies that mention Filipino workers, from their own public pages.
Results go to a private sheet tab. Nothing found is printed in the logs."""
import datetime
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

import dns.resolver
import requests
from bs4 import BeautifulSoup

import scraper as s
import store

SAUDI = ["Riyadh", "Jeddah", "Dammam", "Khobar", "Mecca", "Medina", "Taif", "Abha", "Tabuk", "Buraidah", "Jubail", "Yanbu", "Hail", "Najran", "Jazan", "Al Ahsa", "Khamis Mushait", "Unaizah", "Hafar Al Batin", "Arar"]
QATAR = ["Doha", "Al Wakrah", "Al Khor", "Lusail", "Umm Salal", "Al Rayyan", "Mesaieed", "Dukhan", "Al Shamal", "Madinat Khalifa"]
SAUDI_T = ["recruitment office {c} Filipino domestic workers", "manpower recruitment agency {c} Philippines workers",
           "{c} recruitment agency hire Filipino skilled workers", "{c} musaned licensed recruitment office Filipino",
           "{c} company job order Filipino workers", "{c} maid agency Filipina housemaid", "{c} recruitment office Philippines accredited",
           "{c} manpower supply company Filipino workers contact"]
QATAR_T = ["recruitment agency {c} Filipino domestic workers", "manpower supply company {c} Filipino workers",
           "{c} recruitment office Philippines skilled workers", "{c} company hiring Filipino workers job order",
           "{c} maid agency Filipina housemaid", "{c} licensed recruitment agency Philippines contact"]
ARABIC = ["مكتب استقدام عمالة فلبينية {c}", "استقدام خادمات فلبينيات {c}", "شركة استقدام من الفلبين {c}", "مكتب استقدام عمالة منزلية الفلبين"]
AR_SA = {"Riyadh": "الرياض", "Jeddah": "جدة", "Dammam": "الدمام", "Khobar": "الخبر", "Mecca": "مكة", "Medina": "المدينة المنورة", "Taif": "الطائف", "Abha": "أبها", "Tabuk": "تبوك", "Buraidah": "بريدة"}
AR_QA = {"Doha": "الدوحة", "Al Wakrah": "الوكرة", "Al Khor": "الخور", "Lusail": "لوسيل", "Al Rayyan": "الريان"}
GENERIC = ["Saudi recruitment agency looking for Philippine agency partnership", "Qatar recruitment agency looking for Philippine agency partnership",
           "Saudi manpower agency Filipino domestic workers accredited POLO", "Qatar recruitment office accredited MWO Filipino workers",
           "Saudi recruitment agency Filipino housemaid", "Qatar manpower supply Filipino skilled workers"]

COLS = ["Date found", "Agency", "Website", "Country", "City", "Email", "Email domain receives mail", "Hires for",
        "Open job order signals", "Seeks Philippine partner agencies", "Licence or verification clue", "Licence number on site", "Pages read"]

DH = re.compile(r"domestic (?:worker|helper|staff)|house ?maid|\bmaids?\b|household (?:service )?worker|\bhsw\b|nanny|housekeeper", re.I)
SK = re.compile(r"skilled|technician|engineer|nurse|welder|electrician|mechanic|construction|hospitality|chef|manpower supply|labou?r supply|plumber|carpenter|steel|operator", re.I)
FIL = re.compile(r"filipino|filipina|philippine|pinoy|\bofw\b|manila|\u0641\u0644\u0628\u064a\u0646|\u0627\u0644\u0641\u0644\u0628\u064a\u0646", re.I)
JO = re.compile(r"job order|vacanc|urgent|now hiring|we (?:are )?(?:need|hiring|looking)|required|demand|openings?|positions? available|requirement", re.I)
PART = re.compile(r"partner|collaborat|philippine agenc|agenc(?:y|ies) (?:in|from) the philippines|accredited agenc|sub-?agent|looking for (?:a )?(?:philippine|filipino)", re.I)
LIC = re.compile(r"(?:licen[cs]e|licen[cs]ed|musaned|commercial registration|\bcr\b|ministry of (?:human resources|labou?r)|mwo|polo)[^.\n]{0,70}", re.I)
SA_W = re.compile(r"saudi|\bksa\b|riyadh|jeddah|dammam|khobar|mecca|makkah|medina|madinah|taif|abha|tabuk|jubail|yanbu", re.I)
QA_W = re.compile(r"qatar|doha|wakrah|al khor|lusail|rayyan", re.I)
PH_AGENCY = re.compile(r"migrant workers office|philippine embassy|department of migrant workers|dmw\.gov|\bpoea\b|\bdmw\b[^.]{0,40}licen[cs]e|licen[cs]e no\.?\s*[a-z]{2,4}-?\d", re.I)
GULF_PHONE = re.compile(r"(?:\+|00)\s?(966|974)[\s\-]?\(?0?\)?[\s\-]?(\d{1,2})[\s\-]?(\d{3})[\s\-]?(\d{3,4})")
WA = re.compile(r"(?:wa\.me/|whatsapp\.com/send\?phone=)(\+?\d{8,15})", re.I)
LICNUM = re.compile(r"(?:licen[cs]e|musaned|\u0631\u062e\u0635\u0629)[^0-9]{0,25}(\d{6,12})", re.I)
LINKS = ("contact", "about", "job", "vacan", "career", "hire", "order", "service", "recruit", "demand", "partner", "apply", "worker")

MAX_SECONDS = int(os.environ.get("MAX_SECONDS", "17000"))
TARGET = int(os.environ.get("FRA_TARGET", "500"))
WORKERS = int(os.environ.get("WORKERS", "6"))


def build_queries(day):
    out = []
    for names in (AR_SA, AR_QA):
        keys = list(names)
        for n, a in enumerate(ARABIC):
            for k in range(3):
                c = names[keys[(day * 3 + n + k) % len(keys)]]
                out.append(a.format(c=c) + " | FRA")
    for cities, temps, tag in ((SAUDI, SAUDI_T, "Saudi"), (QATAR, QATAR_T, "Qatar")):
        for n, t in enumerate(temps):
            for k in range(6 if tag == "Saudi" else 4):
                out.append(t.format(c=cities[(day * 6 + n * 3 + k) % len(cities)]) + " | FRA")
    return [g + " | FRA" for g in GENERIC] + out


def fmt_gulf(m):
    cc, a, b, c = m.groups()
    return f"+{cc} {a} {b} {c}".strip()


def evaluate(domain, pages):
    """pages: list of (url, raw_html). Returns (row_dict or None, reason)."""
    texts, raws = [], []
    for u, raw in pages:
        raws.append(raw)
        texts.append(BeautifulSoup(raw, "html.parser").get_text(" "))
    text = " ".join(texts)
    if domain.endswith(".ph") or ".com.ph" in domain:
        return None, "Philippine agency"
    if PH_AGENCY.search(text):
        return None, "Philippine agency"
    sa, qa = len(SA_W.findall(text)), len(QA_W.findall(text))
    if domain.endswith(".sa"):
        sa += 5
    if domain.endswith(".qa"):
        qa += 5
    phones, wa = [], []
    for raw in raws:
        for m in GULF_PHONE.finditer(raw):
            phones.append(fmt_gulf(m))
            if m.group(1) == "966":
                sa += 1
            else:
                qa += 1
        wa += [("+" + x.lstrip("+")) for x in WA.findall(raw)]
    has_phone = bool(phones)
    mail_gulf = any(e.endswith((".sa", ".qa")) for e in s.extract_emails("".join(raws)))
    if not has_phone and not mail_gulf and not domain.endswith((".sa", ".qa")):
        return None, "no Saudi or Qatar number or domain"
    if sa < 2 and qa < 2:
        return None, "not Saudi or Qatar"
    if not FIL.search(text):
        return None, "no mention of Filipino workers"
    emails = set()
    for raw in raws:
        emails |= s.extract_emails(raw)
    emails = sorted(e for e in emails if not e.endswith((".gov", ".gov.sa")))
    phones = list(dict.fromkeys(phones))
    wa = list(dict.fromkeys(wa))
    if not emails:
        return None, "no email found"
    own = [e for e in emails if e.split("@")[-1].replace("www.", "") in domain or domain in e.split("@")[-1]]
    emails = (own + [e for e in emails if e not in own])
    dh, sk = bool(DH.search(text)), len(SK.findall(text)) >= 2
    hires = "Both" if dh and sk else "Domestic helpers" if dh else "Skilled" if sk else "Unclear"
    sents = re.split(r"[.\n|•]+", re.sub(r"\s+", " ", text))
    clean = [re.sub(r"[^\x20-\x7e]", "", x).strip() for x in sents]
    sig = [x[:120] for x in clean if JO.search(x) and 15 < len(x) < 400 and (re.search(r"\d", x) or SK.search(x) or DH.search(x))][:3]
    lic = LIC.search(text)
    country = "Saudi Arabia" if sa >= qa else "Qatar"
    cities = SAUDI if country == "Saudi Arabia" else QATAR
    city = next((c for c in cities if re.search(c, text, re.I)), "")
    ln = LICNUM.search(text)
    return {"licnum": ln.group(1) if ln else "", "emails": emails[:3], "phones": phones[:2], "wa": wa[:1], "hires": hires, "signals": sig,
            "partner": "Yes" if PART.search(text) else "Not stated", "licence": (lic.group(0).strip()[:100] if lic else ""),
            "country": country, "city": city, "pages": len(pages)}, "ok"


def fetch(domain, session):
    base = None
    for scheme in ("https://", "http://"):
        r = s.get(scheme + domain, session)
        if r is not None and r.status_code == 200 and r.text:
            base = r.url
            home = r
            break
    if base is None:
        return None, "site did not load"
    if not s.robots_ok(base.rstrip("/"), session):
        return None, "robots disallow"
    pages = [(base, home.text)]
    soup = BeautifulSoup(home.text, "html.parser")
    seen = {base}
    for a in soup.find_all("a", href=True):
        u = urljoin(base, a["href"]).split("#")[0]
        if urlparse(u).netloc.replace("www.", "") != domain or u in seen:
            continue
        if any(k in u.lower() or k in a.get_text(" ").lower() for k in LINKS):
            seen.add(u)
            if len(pages) < 7:
                r = s.get(u, session)
                if r is not None and r.status_code == 200 and r.text:
                    pages.append((u, r.text))
    return pages, "ok"


def mx_ok(email):
    host = email.split("@")[-1]
    try:
        return bool(len(dns.resolver.resolve(host, "MX", lifetime=6)))
    except Exception:
        try:
            return bool(len(dns.resolver.resolve(host, "A", lifetime=6)))
        except Exception:
            return False


def work(domain):
    try:
        session = requests.Session()
        pages, why = fetch(domain, session)
        if pages is None:
            return domain, None, why, ""
        res, why = evaluate(domain, pages)
        if res:
            res["mx"] = mx_ok(res["emails"][0])
            if not res["mx"]:
                return domain, None, "email domain cannot receive mail", ""
        name = s.clean_company(BeautifulSoup(pages[0][1], "html.parser"), domain) if res else ""
        return domain, res, why, name
    except Exception as e:
        return domain, None, "error " + type(e).__name__, ""


def main():
    started = time.time()
    day = datetime.date.today().toordinal()
    stamp = datetime.date.today().isoformat()
    st = store.Store()
    checked = st.read_domains("FRA Checked")
    have_rows = st.read_table("FRA Leads")
    have_c = {e.strip().lower() for r in have_rows for e in (r.get("Email", "") or "").split(",") if e.strip()}
    in_sheet = {(r.get("Website", "") or "").lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/") for r in have_rows}
    print(f"Loaded {len(checked)} checked and {len(have_rows)} agencies from the sheet", flush=True)
    session = requests.Session()
    qs = build_queries(day)
    new = done = 0
    seen = set()
    for i in range(0, len(qs), 4):
        if new >= TARGET or time.time() - started > MAX_SECONDS:
            break
        pairs = s.discover(qs[i:i + 4], session)
        todo = []
        for host, _ in pairs:
            d = host.lower().replace("www.", "")
            if d and d not in seen and d not in checked and d not in in_sheet:
                seen.add(d)
                todo.append(d)
        print(f"searches {i + 1}-{min(i + 4, len(qs))} of {len(qs)}: {len(todo)} new sites", flush=True)
        if not todo:
            continue
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            results = list(ex.map(work, todo))
        rows, crows = [], []
        for d, res, why, name in results:
            done += 1
            if res is None:
                crows.append([d, stamp, why])
                continue
            if any(e in have_c for e in res["emails"]):
                crows.append([d, stamp, "duplicate email"])
                continue
            have_c |= set(res["emails"])
            crows.append([d, stamp, "saved"])
            rows.append([stamp, name or d, "https://" + d, res["country"], res["city"], ", ".join(res["emails"]),
                         "Yes", res["hires"], " | ".join(res["signals"]),
                         res["partner"], res["licence"], res["licnum"], res["pages"]])
        st.add_rows("FRA Leads", rows)
        st.add_rows("FRA Checked", crows)
        new += len(rows)
        print(f"checked {done} sites, {new} agencies saved so far", flush=True)
    print(f"DONE agencies saved {new}, sites checked {done}", flush=True)


if __name__ == "__main__":
    main()
