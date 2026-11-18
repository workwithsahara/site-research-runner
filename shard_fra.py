"""Runs one shard of the Gulf agency search. Env: SHARD (0-based), SHARDS, FRA_TARGET (total agencies wanted)."""
import os

SHARDS = max(1, int(os.environ.get("SHARDS", "1")))
SHARD = int(os.environ.get("SHARD", "0")) % SHARDS
TOTAL = int(os.environ.get("FRA_TARGET", "1200"))
os.environ["FRA_TARGET"] = str(-(-TOTAL // SHARDS))

import sheetretry  # noqa: E402,F401
import scraper  # noqa: E402
import search  # noqa: E402
import store  # noqa: E402
import fresh  # noqa: E402

import fra  # noqa: E402

fra.SAUDI.extend(["Qatif", "Hofuf", "Sakaka", "Bisha", "Al Baha", "Rabigh", "Buraydah", "Dhahran", "Al Kharj", "Al Majmaah", "Dawadmi",
                  "Wadi ad-Dawasir", "Sharurah", "Al Qunfudhah", "Khafji", "Ras Tanura", "Ar Rass", "Al Mubarraz", "Hafar Al Batin"])
fra.QATAR.extend(["Al Sadd", "West Bay", "Al Gharafa", "Al Daayen", "Umm Said", "Mesaimeer", "Old Airport", "The Pearl", "Al Muntazah", "Bin Mahmoud"])
fra.AR_SA.update({"Qatif": "القطيف", "Hofuf": "الهفوف", "Al Kharj": "الخرج", "Hail": "حائل", "Najran": "نجران", "Jazan": "جازان",
                  "Al Baha": "الباحة", "Sakaka": "سكاكا", "Bisha": "بيشة", "Dhahran": "الظهران", "Yanbu": "ينبع", "Jubail": "الجبيل"})
fra.AR_QA.update({"Umm Salal": "أم صلال", "Mesaieed": "مسيعيد", "Al Daayen": "الدعين", "Al Gharafa": "الغرافة", "Al Sadd": "السد", "Al Wakrah": "الوكرة"})
EXTRA_T = ["{c} musaned recruitment office contact us", "{c} recruitment agency contact us email Filipino", "{c} housemaid agency Philippines",
           "{c} manpower company Filipino domestic worker visa", "{c} company careers Filipino staff hiring agency",
           "{c} Philippines recruitment partner agency contact", "{c} recruitment office Filipino workers whatsapp",
           "{c} staffing agency foreign workers Philippines India", "{c} maid recruitment office domestic workers Philippines Indonesia"]
fra.GENERIC.extend(["UAE recruitment agency looking for Philippine agency partnership", "Dubai manpower agency Filipino domestic workers contact whatsapp",
                    "Kuwait recruitment office Filipino domestic workers contact", "Oman recruitment agency Filipino workers contact",
                    "Bahrain recruitment agency Filipino domestic workers contact", "Abu Dhabi recruitment agency Filipino workers whatsapp"])
fra.SAUDI_T.extend(EXTRA_T)
fra.QATAR_T.extend(EXTRA_T)
fra.ARABIC.extend(["مكتب استقدام {c} تواصل معنا", "شركة استقدام عمالة منزلية {c}", "استقدام عمالة من الفلبين {c} واتساب", "مكتب خدم {c} الفلبين",
                   "مكتب استقدام معتمد مساند {c}", "ارقام مكاتب الاستقدام في {c}", "تراخيص مكاتب الاستقدام {c}",
                   "استقدام عاملات منزليات {c} الفلبين", "مكتب توظيف عمالة اجنبية {c}", "شركة استقدام سائقين وعمال {c} الفلبين",
                   "مكتب استقدام {c} عاملة فلبينية", "شركة خدمات عمالة {c} اتصل بنا", "دليل مكاتب الاستقدام {c}"])


def build(day, rnd=0):
    ar, en = [], []
    for names in (fra.AR_AE, fra.AR_KW, fra.AR_OM, fra.AR_BH, fra.AR_SA, fra.AR_QA):
        keys = list(names)
        for k in range(len(keys)):
            for n, a in enumerate(fra.ARABIC):
                ar.append(a.format(c=names[keys[(day * 3 + n + k + rnd * 7) % len(keys)]]) + " | FRA")
    # Saudi and Qatar searches are used up, so the other Gulf countries go first
    for cities, temps in ((fra.UAE, fra.QATAR_T), (fra.KUWAIT, fra.QATAR_T), (fra.OMAN, fra.QATAR_T), (fra.BAHRAIN, fra.QATAR_T),
                          (fra.SAUDI, fra.SAUDI_T), (fra.QATAR, fra.QATAR_T)):
        for k in range(len(cities)):
            for n, t in enumerate(temps):
                en.append(t.format(c=cities[(day * 3 + n + k + rnd * 7) % len(cities)]) + " | FRA")
    # Five wordings of every search (email, contact number, directory...) so the searches keep reaching sites not checked yet
    suf_en = ["", " email", " contact number"]
    suf_ar = ["", " واتساب", " رقم الهاتف", " ايميل"]
    en = [q.replace(" | FRA", s + " | FRA") for s in suf_en for q in en]
    ar = [q.replace(" | FRA", s + " | FRA") for s in suf_ar for q in ar]
    out = [g + " | FRA" for g in fra.GENERIC] if rnd == 0 else []
    for i in range(max(len(ar), len(en))):  # English searches first, Arabic mixed in, so both kinds run every round
        if i < len(en):
            out.append(en[i])
        if i < len(ar) and i % 2 == 0:
            out.append(ar[i])
    return out


fra.build_queries = lambda day, rnd=0: [q for i, q in enumerate(build(day, rnd)) if i % SHARDS == SHARD]

_st = []


def _checked():
    if not _st:
        _st.append(store.Store())
    st = _st[0]
    done, _ = fra.done_set(st.read_table("FRA Checked"))
    return done | {(r.get("Website", "") or "").lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/") for r in st.read_table("FRA Leads")}


_fresh = fresh.Fresh(_checked) if store.configured() else None


def _discover(queries, session, *a, **k):
    found = search.discover(queries, session, *a, **k)
    return _fresh.filter(found) if _fresh else found


scraper.discover = _discover

if __name__ == "__main__":
    print(f"Shard {SHARD + 1} of {SHARDS}, target {os.environ['FRA_TARGET']} agencies", flush=True)
    fra.main()
