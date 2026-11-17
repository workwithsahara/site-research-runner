"""More search variety for the LAYA shards: extra US cities, different wording per round and extra niches,
so searches keep reaching sites that were not checked yet instead of the same big results again."""
import shard_queries

US_MORE = """Frisco TX|McKinney TX|Round Rock TX|Georgetown TX|Katy TX|Sugar Land TX|The Woodlands TX|Waco TX|Tyler TX|Midland TX|Odessa TX|Abilene TX|Laredo TX|McAllen TX|Brownsville TX|Gilbert AZ|Glendale AZ|Peoria AZ|Flagstaff AZ|Yuma AZ|Anaheim CA|Long Beach CA|Pasadena CA|Santa Rosa CA|Stockton CA|Modesto CA|Palm Springs CA|Temecula CA|Carlsbad CA|San Luis Obispo CA|Redding CA|Chico CA|Visalia CA|Elk Grove CA|Aurora IL|Joliet IL|Champaign IL|Bloomington IL|Yonkers NY|White Plains NY|Utica NY|Binghamton NY|Ithaca NY|Boca Raton FL|West Palm Beach FL|Fort Myers FL|Gainesville FL|Ocala FL|Daytona Beach FL|Lakeland FL|Clearwater FL|St Petersburg FL|Cape Coral FL|Alpharetta GA|Marietta GA|Roswell GA|Macon GA|Athens GA|Cary NC|Fayetteville NC|Winston-Salem NC|High Point NC|Murfreesboro TN|Franklin TN|Clarksville TN|Bowling Green KY|Carmel IN|South Bend IN|Lafayette IN|Dublin OH|Youngstown OH|Canton OH|Kalamazoo MI|Flint MI|Troy MI|Eau Claire WI|Appleton WI|Kenosha WI|Rochester MN|Bloomington MN|St Cloud MN|Davenport IA|Sioux City IA|Iowa City IA|Independence MO|Columbia MO|Joplin MO|Overland Park KS|Olathe KS|Norman OK|Broken Arrow OK|Shreveport LA|Gulfport MS|Tuscaloosa AL|Auburn AL|Rock Hill SC|Myrtle Beach SC|Chesapeake VA|Alexandria VA|Arlington VA|Fairfax VA|Frederick MD|Bethesda MD|Lancaster PA|Reading PA|Scranton PA|State College PA|Cherry Hill NJ|Edison NJ|Hoboken NJ|Stamford CT|Danbury CT|Cambridge MA|Lowell MA|Nashua NH|Bangor ME|Bellevue WA|Vancouver WA|Olympia WA|Bend OR|Medford OR|Meridian ID|Nampa ID|Ogden UT|St George UT|Lakewood CO|Aurora CO|Pueblo CO|Henderson NV|Santa Clara CA|Rapid City SD|Bismarck ND|Great Falls MT|Casper WY|Fairbanks AK""".split("|")
shard_queries.US_CITIES[:] = list(dict.fromkeys(shard_queries.US_CITIES + US_MORE))

MODS = ["", " family owned", " locally owned", " top rated", " official site", " best", " small business",
        " contact us", " about us", " reviews", " near me", " services"]
MODS_CORP = ["", " contact us", " about us", " our team", " services", " staffing solutions", " small business", " locally owned"]

NICHES = {
    "Home services": ["plumber", "electrician", "landscaping company", "pest control", "pressure washing", "carpet cleaning", "house painter",
                      "garage door repair", "fence contractor", "tree service", "window cleaning", "handyman", "moving company", "locksmith",
                      "junk removal", "flooring installer", "concrete contractor", "solar installer", "gutter cleaning", "appliance repair",
                      "pool service", "house cleaning service", "kitchen remodeling", "plumbing and heating"],
    "Education": ["tutoring center", "driving school", "music school", "dance studio", "language school", "test prep center"],
    "Fitness": ["yoga studio", "martial arts school", "pilates studio", "crossfit gym", "boxing gym"],
    "Restaurant and cafe": ["bakery", "catering company", "food truck", "coffee roaster", "brewery", "juice bar"],
    "Beauty salon": ["tattoo studio", "massage therapist", "nail salon", "hair salon", "waxing studio", "day spa"],
    "Health": ["acupuncture clinic", "optometrist", "naturopath", "podiatrist", "dermatology clinic", "counseling practice"],
    "Pet services": ["veterinary clinic", "dog groomer", "dog trainer", "pet boarding"],
    "Local business": ["funeral home", "print shop", "sign company", "florist", "bike shop", "self storage", "dry cleaner", "jewelry store"],
    "Accounting": ["bookkeeping service", "tax preparer", "financial advisor", "payroll service"],
    "Design and build": ["architect", "landscape architect", "web design studio", "video production company", "branding agency"],
    "Events and weddings": ["wedding planner", "DJ service", "party rental", "event venue", "photo booth rental"],
    "Automotive": ["car detailing", "auto repair shop", "tire shop", "towing company", "car wash", "auto body shop"],
    "Travel": ["tour operator", "bed and breakfast", "boutique hotel", "campground"],
}
EXTRA_Q = [f"{n} {c} |{ind}" for ind, ns in NICHES.items() for n in ns for c in ("USA", "Australia", "Canada", "United Kingdom", "New Zealand")]


def make_expander(run_cities):
    lists = shard_queries.city_lists(run_cities)

    def expand_queries(queries, today, *a, **k):
        day = today.toordinal()
        parsed = []
        for q in list(queries) + EXTRA_Q:
            words, sep, industry = q.partition("|")
            words = words.strip()
            for country, cities in lists.items():
                if words.endswith(country):
                    parsed.append((words[: -len(country)].strip(), industry, cities, industry.strip() in ("Recruitment", "Agency")))
                    break
        out = []
        rounds = max(len(c) for _, _, c, _ in parsed) if parsed else 0
        for k_ in range(rounds):
            for n, (base, industry, cities, corp) in enumerate(parsed):
                city = cities[(day * 11 + n * 5 + k_) % len(cities)]
                mods = MODS_CORP if corp else MODS
                out.append(f"{base} {city}{mods[(k_ + n) % len(mods)]} |{industry}")
        return out

    return expand_queries
