"""US ZIP code searches: a niche plus a ZIP code returns the businesses of one neighbourhood, which city searches never reach."""
import shard_more


def zip_queries(day, total=60000):
    pairs = [(ind, n) for ind, ns in shard_more.NICHES.items() for n in ns]
    out = []
    for i in range(total):
        ind, n = pairs[(i * 7 + day) % len(pairs)]
        z = 1001 + (day * 12347 + i * 7717) % 98900
        out.append(f"{n} {z:05d} |{ind}")
    return out


def wrap(expand):
    """Two ZIP searches for every city search, so every shard gets both kinds."""
    def expanded(queries, today, *a, **k):
        out = expand(queries, today, *a, **k)
        zips = zip_queries(today.toordinal())
        mixed, i, j = [], 0, 0
        while i < len(out) or j < len(zips):
            for _ in range(2):
                if j < len(zips):
                    mixed.append(zips[j])
                    j += 1
            if i < len(out):
                mixed.append(out[i])
                i += 1
        return mixed
    return expanded
