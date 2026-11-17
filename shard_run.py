"""Runs one shard of the LAYA site research. Several shards run side by side, each on its own runner,
each taking its own slice of the searches. Env: SHARD (0-based), SHARDS, TARGET_PER_DAY (total passing leads wanted)."""
import os

SHARDS = max(1, int(os.environ.get("SHARDS", "1")))
SHARD = int(os.environ.get("SHARD", "0")) % SHARDS
TOTAL = int(os.environ.get("TARGET_PER_DAY", "800"))
os.environ["TARGET_PER_DAY"] = str(-(-TOTAL // SHARDS))  # each shard's share of the passing-leads target

import sheetretry  # noqa: E402,F401
import scraper  # noqa: E402
import search  # noqa: E402
import store  # noqa: E402
import fresh  # noqa: E402
import shard_queries  # noqa: E402

import run  # noqa: E402

_st = []


def _checked():
    if not _st:
        _st.append(store.Store())
    return _st[0].read_checked()


_fresh = fresh.Fresh(_checked) if store.configured() else None


def _discover(queries, session, *a, **k):
    found = search.discover(queries, session, *a, **k)
    return _fresh.filter(found) if _fresh else found


scraper.discover = _discover
run.BAD_HOSTS = run.BAD_HOSTS + shard_queries.BIG
_expand = shard_queries.make_expander(run.CITIES)
run.expand_queries = lambda queries, today, *a, **k: [q for i, q in enumerate(_expand(queries, today)) if i % SHARDS == SHARD]

if __name__ == "__main__":
    print(f"Shard {SHARD + 1} of {SHARDS}, target {os.environ['TARGET_PER_DAY']} passing leads", flush=True)
    run.main()
