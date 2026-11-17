"""Runs one shard of the LAYA site research. Several shards run side by side, each on its own runner,
each taking its own slice of the searches. Env: SHARD (0-based), SHARDS, TARGET_PER_DAY (total passing leads wanted)."""
import os

SHARDS = max(1, int(os.environ.get("SHARDS", "1")))
SHARD = int(os.environ.get("SHARD", "0")) % SHARDS
TOTAL = int(os.environ.get("TARGET_PER_DAY", "800"))
os.environ["TARGET_PER_DAY"] = str(-(-TOTAL // SHARDS))  # each shard's share of the passing-leads target

import scraper  # noqa: E402
import search  # noqa: E402

scraper.discover = search.discover

import run  # noqa: E402

_expand = run.expand_queries
run.expand_queries = lambda queries, today, *a, **k: [q for i, q in enumerate(_expand(queries, today, *a, **k)) if i % SHARDS == SHARD]

if __name__ == "__main__":
    print(f"Shard {SHARD + 1} of {SHARDS}, target {os.environ['TARGET_PER_DAY']} passing leads", flush=True)
    run.main()
