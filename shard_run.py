"""Runs one shard of the LAYA site research. Several shards run side by side, each on its own runner,
each taking its own slice of the searches. Env: SHARD (0-based), SHARDS, TARGET_PER_DAY (total passing leads wanted)."""
import os
from concurrent.futures import ThreadPoolExecutor

import requests

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
import shard_more  # noqa: E402

import run  # noqa: E402

_st = []


def _checked():
    if not _st:
        _st.append(store.Store())
    return _st[0].read_checked()


_fresh = fresh.Fresh(_checked) if store.configured() else None


_pool = ThreadPoolExecutor(2)
_cache = {}
_order = {"list": [], "pos": {}}
_calls = [0]
CHUNK = int(os.environ.get("QUERY_CHUNK", "5"))


def _fetch(queries):
    return search.discover(queries, requests.Session())


def _discover(queries, session, *a, **k):
    """Searches the next group of queries in the background while the current group of sites is being checked."""
    fut = _cache.pop(tuple(queries), None)
    found = fut.result() if fut else search.discover(queries, session)
    pos = _order["pos"].get(queries[0]) if queries else None
    if pos is not None:
        nxt = _order["list"][pos + len(queries): pos + len(queries) + CHUNK]
        if nxt:
            _cache[tuple(nxt)] = _pool.submit(_fetch, nxt)
    _calls[0] += 1
    if _calls[0] % 10 == 0:
        print(search.stats_line(), flush=True)
    return _fresh.filter(found) if _fresh else found


scraper.discover = _discover
run.BAD_HOSTS = run.BAD_HOSTS + shard_queries.BIG
_expand = shard_more.make_expander(run.CITIES)


def _expand_shard(queries, today, *a, **k):
    out = [q for i, q in enumerate(_expand(queries, today)) if i % SHARDS == SHARD]
    _order["list"] = out
    _order["pos"] = {q: i for i, q in reversed(list(enumerate(out)))}
    return out


run.expand_queries = _expand_shard

if __name__ == "__main__":
    print(f"Shard {SHARD + 1} of {SHARDS}, target {os.environ['TARGET_PER_DAY']} passing leads", flush=True)
    run.main()
