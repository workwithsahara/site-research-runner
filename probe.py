"""Checks whether OpenStreetMap Overpass is reachable from this runner and how many business websites it returns."""
import time

import requests

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
             "https://overpass.private.coffee/api/interpreter"]
QUERIES = {
    "saudi_employment_agency": '[out:json][timeout:60];area["ISO3166-1"="SA"]->.a;(nwr["office"="employment_agency"](area.a););out tags 2000;',
    "qatar_employment_agency": '[out:json][timeout:60];area["ISO3166-1"="QA"]->.a;(nwr["office"="employment_agency"](area.a););out tags 2000;',
    "saudi_recruit_name": '[out:json][timeout:60];area["ISO3166-1"="SA"]->.a;(nwr["name"~"recruit|استقدام|manpower",i](area.a););out tags 2000;',
    "us_plumber_tx": '[out:json][timeout:60];area["ISO3166-2"="US-TX"]->.a;(nwr["craft"="plumber"]["website"](area.a););out tags 300;',
}
for name, q in QUERIES.items():
    for ep in ENDPOINTS:
        try:
            r = requests.post(ep, data={"data": q}, timeout=90, headers={"User-Agent": "site-research-runner/1.0"})
            if r.status_code != 200:
                print(name, ep, r.status_code, flush=True)
                time.sleep(3)
                continue
            els = r.json().get("elements", [])
            sites = [e["tags"].get("website") or e["tags"].get("contact:website") for e in els]
            sites = [x for x in sites if x]
            print(name, ep, "elements", len(els), "with website", len(sites), sites[:5], flush=True)
            break
        except Exception as e:
            print(name, ep, "error", type(e).__name__, flush=True)
    time.sleep(5)
