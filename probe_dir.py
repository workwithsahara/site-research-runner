"""Small test of one free directory: how many listings have no website, recent reviews and a readable email. Prints counts only."""
import collections, datetime, random, re, time
import requests
from bs4 import BeautifulSoup

BASE = "https://www.yellowpages.com.au"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "en-AU,en;q=0.9"}
CATS = ["plumbers", "hairdressers", "electricians", "driving-lessons-schools", "accountants", "painters-decorators"]
SUBS = ["parramatta-nsw-2150", "richmond-vic-3121", "fremantle-wa-6160", "southport-qld-4215", "adelaide-sa-5000", "prospect-sa-5082"]
S = requests.Session()
S.headers.update(UA)
C = collections.Counter()


def get(url):
    try:
        r = S.get(url, timeout=25)
        C[f"http_{r.status_code}"] += 1
        return r if r.status_code == 200 else None
    except Exception as e:
        C["err_" + type(e).__name__] += 1
        return None


def cf_decode(h):
    try:
        k = int(h[:2], 16)
        return "".join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h), 2))
    except Exception:
        return ""


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    site = False
    for a in soup.find_all("a", href=True):
        t = a.get_text(" ", strip=True).lower()
        h = a["href"]
        if ("visit website" in t or t == "website" or "other link" in t) and h.startswith("http") and "yellowpages" not in h:
            site = True
    email = ""
    for tag in soup.find_all(attrs={"data-cfemail": True}):
        email = cf_decode(tag["data-cfemail"])
    for a in soup.find_all("a", href=True):
        if "email-protection#" in a["href"] and not email:
            email = cf_decode(a["href"].split("#")[-1])
        if a["href"].startswith("mailto:") and not email:
            email = a["href"][7:].split("?")[0]
    dates = []
    for d in re.findall(r"\b(\d{2})/(\d{2})/(\d{4})\b", text):
        try:
            dates.append(datetime.date(int(d[2]), int(d[1]), int(d[0])))
        except ValueError:
            pass
    abn = bool(re.search(r"ABN\D{0,12}\d{2}\s?\d{3}\s?\d{3}\s?\d{3}", text))
    phone = bool(soup.select_one("a[href^='tel:']"))
    return site, email, dates, abn, phone


def main():
    random.seed(7)
    links = set()
    for cat in CATS:
        for sub in SUBS:
            r = get(f"{BASE}/find/{cat}/{sub}")
            time.sleep(1)
            if not r:
                continue
            C["listing_pages_ok"] += 1
            for a in BeautifulSoup(r.text, "html.parser").find_all("a", href=True):
                if "/bpp/" in a["href"]:
                    links.add(a["href"].split("?")[0] if a["href"].startswith("http") else BASE + a["href"].split("?")[0])
    print("STAT businesses found on listing pages:", len(links))
    sample = random.sample(sorted(links), min(250, len(links)))
    cutoff = datetime.date.today() - datetime.timedelta(days=730)
    for u in sample:
        r = get(u)
        time.sleep(0.7)
        if not r:
            continue
        site, email, dates, abn, phone = parse(r.text)
        C["details_read"] += 1
        C["has_site"] += site
        if site:
            continue
        C["no_site"] += 1
        C["no_site_phone"] += phone
        C["no_site_abn"] += abn
        C["no_site_has_reviews"] += bool(dates)
        recent = [d for d in dates if d >= cutoff]
        C["no_site_review_last_2y"] += bool(recent)
        C["no_site_3plus_reviews"] += len(dates) >= 3
        C["no_site_email_readable"] += bool(email)
        if email and recent:
            C["no_site_email_and_recent_review"] += 1
            if abn:
                C["no_site_email_recent_abn"] += 1
    for k in sorted(C):
        print("STAT", k, C[k])


main()
