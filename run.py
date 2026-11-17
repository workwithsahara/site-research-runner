"""Runner: finds sites from searches, checks each one on its own pages, and writes passing results to the private sheet.
Everything that identifies a business stays in the sheet. Logs only show counts."""
import datetime
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests

import scraper as s
import store

COLS = s.COLUMNS
TARGET_PER_RUN = int(os.environ.get("TARGET_PER_DAY", "800"))
MAX_SITES = int(os.environ.get("MAX_STORES", "20000"))
WORKERS = int(os.environ.get("WORKERS", "8"))
MAX_SECONDS = int(os.environ.get("MAX_SECONDS", str(5 * 3600 + 40 * 60)))
QUERY_CHUNK = int(os.environ.get("QUERY_CHUNK", "5"))

STATES = ["Alabama", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
          "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
          "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
          "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
          "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
          "Washington", "West Virginia", "Wisconsin", "Wyoming"]
BAD_HOSTS = ("verizon.", "usatoday.", "nytimes.", "forbes.", "cnn.", "bbb.org", "houzz.", "angi.", "thumbtack.", "wired.",
             "indeed.", "glassdoor.", "ziprecruiter.", "monster.", "randstad.", "adecco.", "manpower", "kellyservices.", "roberthalf.",
             "hays.", "michaelpage.", "robertwalters.", "kornferry.", "heidrick.", "spencerstuart.", "teksystems.")


CITIES = {
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast", "Canberra", "Geelong", "Newcastle",
                  "Wollongong", "Hobart", "Sunshine Coast", "Fremantle", "Ballarat", "Bendigo", "Townsville", "Cairns", "Darwin"],
    "Canada": ["Toronto", "Vancouver", "Calgary", "Ottawa", "Montreal", "Edmonton", "Winnipeg", "Mississauga", "Halifax",
               "Victoria", "Saskatoon", "Regina", "Hamilton", "London Ontario", "Kelowna", "Quebec City"],
    "United Kingdom": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Bristol", "Edinburgh", "Liverpool", "Sheffield",
                       "Newcastle", "Nottingham", "Leicester", "Cardiff", "Belfast", "Southampton", "Reading", "Cambridge", "Oxford"],
    "New Zealand": ["Auckland", "Wellington", "Christchurch", "Hamilton", "Tauranga", "Dunedin", "Napier", "Palmerston North", "Queenstown"],
}


def expand_queries(queries, today, variants=int(os.environ.get("VARIANTS", "30"))):
    """Same searches return the same sites every day. A US state or a city that changes daily gives fresh results."""
    day = today.toordinal()
    out = []
    for n, q in enumerate(queries):
        out.append(q)
        words, sep, industry = q.partition("|")
        words = words.strip()
        if words.endswith("USA"):
            base = re.sub(r"\s+USA$", "", words)
            for k in range(variants):
                out.append(base + " " + STATES[(day * variants + n * 7 + k) % len(STATES)] + sep + industry)
        for country, cities in CITIES.items():
            if words.endswith(country):
                base = words[: -len(country)].strip()
                for k in range(variants):
                    out.append(base + " " + cities[(day * variants + n * 3 + k) % len(cities)] + sep + industry)
    return out


def bad_host(d):
    return d.endswith((".gov", ".edu", ".mil")) or any(b in d for b in BAD_HOSTS)


def dom(url):
    u = (url or "").strip().lower()
    return urlparse(u if "//" in u else "//" + u).netloc.replace("www.", "")


def phone_key(p):
    d = re.sub(r"\D", "", p or "")
    return d[-9:] if len(d) >= 9 else ""


def is_duplicate(row, master):
    d, e, p = dom(row["Website"]), row.get("Email", "").lower(), phone_key(row.get("Phone", ""))
    for m in master:
        if dom(m["Website"]) == d:
            return True
        if e and m.get("Email", "").lower() == e:
            return True
        if p and phone_key(m.get("Phone", "")) == p:
            return True
    return False


def work(sd):
    try:
        res, err = s.analyze_site(sd["domain"], requests.Session(), sd["industry"], sd["headcount"],
                                  sd["country"], sd["locality"], sd["company"])
        return sd, res, err, None
    except Exception as e:
        return sd, None, None, e


def main():
    started = time.time()
    today = datetime.date.today()
    stamp = today.isoformat()
    session = requests.Session()
    st = store.Store() if store.configured() else None
    checked = st.read_checked() if st else set()
    leads = st.read_leads() if st else []
    in_sheet = {dom(r.get("Website", "")) for r in leads}
    print(f"Loaded {len(checked)} checked sites and {len(leads)} leads from the sheet", flush=True)

    seen, new_rows, pending = set(), [], []
    state = {"done": 0, "errors": 0, "stop": "ran out of sites to check"}

    def enqueue(items):
        q = []
        for sd in items:
            d = sd["domain"]
            if not d or d in seen or d in checked or d in in_sheet or bad_host(d):
                continue
            seen.add(d)
            q.append(sd)
        return q

    def process(todo):
        """Check sites in parallel batches and save after each batch. False means stop everything."""
        step = WORKERS * 4
        for i in range(0, len(todo), step):
            if len(new_rows) >= TARGET_PER_RUN:
                state["stop"] = "reached the target"
                return False
            if time.time() - started > MAX_SECONDS:
                state["stop"] = "hit the time limit"
                return False
            if state["done"] >= MAX_SITES:
                state["stop"] = "checked the maximum number of sites"
                return False
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                results = list(ex.map(work, todo[i:i + step]))
            b_checked, b_review, b_new = [], [], []
            for sd, res, err, exc in results:
                d = sd["domain"]
                state["done"] += 1
                if exc:
                    state["errors"] += 1
                    continue
                if err or not res:
                    checked.add(d)
                    b_checked.append([d, stamp, "skipped"])
                    continue
                row, fails = res
                if not fails and len(new_rows) + len(b_new) >= TARGET_PER_RUN:
                    continue  # target reached, leave this one for the next run
                row["Date found"] = stamp
                checked.add(d)
                if fails:
                    b_checked.append([d, stamp, "review"])
                    b_review.append([stamp, row.get("Company", ""), row.get("Website", ""), row.get("Owner or founder (public)", ""),
                                     row.get("Email", ""), row.get("Phone", ""), row.get("Industry", ""), row.get("Based in", ""),
                                     "; ".join(fails)])
                elif is_duplicate(row, leads + new_rows + b_new):
                    b_checked.append([d, stamp, "duplicate"])
                else:
                    b_checked.append([d, stamp, "lead"])
                    b_new.append(row)
            new_rows.extend(b_new)
            pending.extend(b_new)
            if st:
                try:
                    st.add_checked(b_checked)
                    st.add_review(b_review)
                    if pending:
                        import drive_sync
                        drive_sync.append_new(pending, COLS)
                        pending.clear()
                except Exception as e:
                    print("sheet save problem:", type(e).__name__, flush=True)
            print(f"checked {state['done']} sites, {len(new_rows)} new leads so far, {state['errors']} errors", flush=True)
        return True

    # seed list from Clay and government registers first (domain | Industry | headcount | Country | Locality | Company)
    seeds = [s.parse_seed(l) for l in s.read_lines("seeds.txt")]
    seeds = [x for x in seeds if x["domain"]]
    if seeds:
        q = enqueue(seeds)
        print(f"seed list: {len(seeds)} entries, {len(q)} not checked yet", flush=True)
        if not process(q):
            seeds = None
    # searches in small chunks, checking what each chunk finds before searching again
    qs = expand_queries(s.read_lines("queries.txt"), today)
    chunk = QUERY_CHUNK
    for j in range(0, len(qs) if seeds is not None else 0, chunk):
        if time.time() - started > MAX_SECONDS:
            state["stop"] = "hit the time limit"
            break
        found = s.discover(qs[j:j + chunk], session)
        q = enqueue([{"domain": h, "industry": ind, "headcount": None, "country": "", "locality": "", "company": ""}
                     for h, ind in found])
        print(f"searches {j + 1}-{min(j + chunk, len(qs))} of {len(qs)}: {len(q)} new sites", flush=True)
        if not process(q):
            break

    if st:
        try:
            st.add_run(len(new_rows), state["done"], state["stop"])
        except Exception as e:
            print("run log problem:", type(e).__name__, flush=True)
    print(f"DONE new leads {len(new_rows)}, sites checked {state['done']}, stopped because {state['stop']}", flush=True)


if __name__ == "__main__":
    main()
