"""City-level searches. 'roofing contractor Tulsa OK' finds small local owner-run businesses far better than a state name,
and there are hundreds of cities, so the supply of searches does not run out."""
US_CITIES = """Houston TX|Dallas TX|Austin TX|San Antonio TX|Fort Worth TX|El Paso TX|Plano TX|Lubbock TX|Amarillo TX|Corpus Christi TX|Phoenix AZ|Tucson AZ|Mesa AZ|Scottsdale AZ|Chandler AZ|Los Angeles CA|San Diego CA|San Jose CA|Sacramento CA|Fresno CA|Irvine CA|Oakland CA|Bakersfield CA|Riverside CA|Santa Barbara CA|Chicago IL|Naperville IL|Springfield IL|Peoria IL|Rockford IL|New York NY|Buffalo NY|Rochester NY|Albany NY|Syracuse NY|Long Island NY|Miami FL|Orlando FL|Tampa FL|Jacksonville FL|Fort Lauderdale FL|Tallahassee FL|Sarasota FL|Naples FL|Pensacola FL|Atlanta GA|Savannah GA|Augusta GA|Columbus GA|Charlotte NC|Raleigh NC|Greensboro NC|Durham NC|Asheville NC|Wilmington NC|Nashville TN|Memphis TN|Knoxville TN|Chattanooga TN|Louisville KY|Lexington KY|Indianapolis IN|Fort Wayne IN|Evansville IN|Columbus OH|Cleveland OH|Cincinnati OH|Toledo OH|Akron OH|Dayton OH|Detroit MI|Grand Rapids MI|Ann Arbor MI|Lansing MI|Milwaukee WI|Madison WI|Green Bay WI|Minneapolis MN|Saint Paul MN|Duluth MN|Des Moines IA|Cedar Rapids IA|Omaha NE|Lincoln NE|Kansas City MO|Saint Louis MO|Springfield MO|Wichita KS|Topeka KS|Oklahoma City OK|Tulsa OK|Little Rock AR|Fayetteville AR|New Orleans LA|Baton Rouge LA|Lafayette LA|Jackson MS|Birmingham AL|Huntsville AL|Mobile AL|Montgomery AL|Charleston SC|Columbia SC|Greenville SC|Richmond VA|Virginia Beach VA|Norfolk VA|Roanoke VA|Baltimore MD|Annapolis MD|Washington DC|Wilmington DE|Philadelphia PA|Pittsburgh PA|Harrisburg PA|Allentown PA|Newark NJ|Jersey City NJ|Princeton NJ|Trenton NJ|Boston MA|Worcester MA|Springfield MA|Hartford CT|New Haven CT|Providence RI|Portland ME|Burlington VT|Manchester NH|Seattle WA|Spokane WA|Tacoma WA|Portland OR|Eugene OR|Salem OR|Boise ID|Salt Lake City UT|Provo UT|Denver CO|Colorado Springs CO|Boulder CO|Fort Collins CO|Albuquerque NM|Santa Fe NM|Las Vegas NV|Reno NV|Billings MT|Missoula MT|Cheyenne WY|Fargo ND|Sioux Falls SD|Anchorage AK|Honolulu HI|Charleston WV|Morgantown WV""".split("|")
EXTRA = {
    "Australia": ["Penrith", "Parramatta", "Central Coast", "Toowoomba", "Launceston", "Mackay", "Rockhampton", "Albury", "Wagga Wagga", "Mandurah", "Bunbury", "Logan", "Ipswich", "Frankston", "Dandenong"],
    "Canada": ["Surrey", "Burnaby", "Richmond BC", "Brampton", "Markham", "Oakville", "Waterloo", "Kitchener", "Windsor", "London ON", "Barrie", "Kingston", "Guelph", "Abbotsford", "Nanaimo", "Red Deer", "Lethbridge", "Moncton", "St Johns", "Sudbury"],
    "United Kingdom": ["Norwich", "Exeter", "York", "Bath", "Brighton", "Plymouth", "Swansea", "Aberdeen", "Dundee", "Derby", "Stoke", "Wolverhampton", "Coventry", "Milton Keynes", "Ipswich", "Peterborough", "Northampton", "Bournemouth", "Hull", "Sunderland"],
    "New Zealand": ["Rotorua", "Whangarei", "Nelson", "Invercargill", "New Plymouth", "Gisborne", "Hastings", "Lower Hutt", "Porirua", "Timaru"],
}


def city_lists(run_cities):
    out = {"USA": US_CITIES}
    for c, lst in run_cities.items():
        out[c] = list(dict.fromkeys(lst + EXTRA.get(c, [])))
    return out


def make_expander(run_cities):
    lists = city_lists(run_cities)

    def expand_queries(queries, today, *a, **k):
        day = today.toordinal()
        parsed = []
        for q in queries:
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
                extra = "" if corp or k_ % 2 == 0 else " family owned"
                out.append(f"{base} {city}{extra} |{industry}")
        return out

    return expand_queries


BIG = ("eventbrite.", "thesaurus.", "realmadrid.", "samsclub.", "olivegarden.", "jimmyjohns.", "mcalistersdeli.", "zola.", "weddingwire.",
       "theknot.", "ezcater.", "independent.", "businessinsider.", "business.com", "openstax.", "tropicalsmoothie", "tripadvisor.", "yelp.",
       "facebook.", "linkedin.", "instagram.", "yellowpages.", "mapquest.", "walmart.", "target.com", "costco.", "homedepot.", "lowes.",
       "mcdonalds.", "starbucks.", "subway.", "dominos.", "pizzahut.", "kfc.", "wikipedia.", "reddit.", "quora.", "medium.com", "forbes.",
       "healthline.", "webmd.", "mayoclinic.", "clevelandclinic.", "nih.gov", "hopkinsmedicine.", "kp.org", "aarp.", "bankofamerica.",
       "chase.com", "wellsfargo.", "usbank.", "statefarm.", "geico.", "progressive.", "allstate.", "libertymutual.", "nationwide.",
       "remax.", "century21.", "kw.com", "coldwellbanker.", "zillow.", "redfin.", "realtor.com", "trulia.", "apartments.com", "airbnb.",
       "booking.com", "expedia.", "kayak.", "orbitz.", "etsy.", "shopify.", "wix.com", "squarespace.", "wordpress.", "godaddy.",
       "nextdoor.", "groupon.", "angi.", "homeadvisor.", "thumbtack.", "porch.", "bark.com", "checkatrade.", "trustatrader.", "ratedpeople.",
       "gumtree.", "yell.com", "thomsonlocal.", "hotfrog.", "truelocal.", "yellowpages.com.au", "oneflare.", "hipages.", "serviceseeking.",
       "canpages.", "yellowpages.ca", "homestars.", "trustedpros.", "bbb.org", "chamberofcommerce.", "manta.", "superpages.", "citysearch.")
