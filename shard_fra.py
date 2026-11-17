"""Runs one shard of the Gulf agency search. Env: SHARD (0-based), SHARDS, FRA_TARGET (total agencies wanted)."""
import os

SHARDS = max(1, int(os.environ.get("SHARDS", "1")))
SHARD = int(os.environ.get("SHARD", "0")) % SHARDS
TOTAL = int(os.environ.get("FRA_TARGET", "1200"))
os.environ["FRA_TARGET"] = str(-(-TOTAL // SHARDS))

import sheetretry  # noqa: E402,F401
import scraper  # noqa: E402
import search  # noqa: E402

scraper.discover = search.discover

import fra  # noqa: E402

_build = fra.build_queries
fra.build_queries = lambda day, rnd=0: [q for i, q in enumerate(_build(day, rnd)) if i % SHARDS == SHARD]

if __name__ == "__main__":
    print(f"Shard {SHARD + 1} of {SHARDS}, target {os.environ['TARGET_PER_DAY'] if False else os.environ['FRA_TARGET']} agencies", flush=True)
    fra.main()
