"""Makes every Google Sheets call patient. Ten shards write to one sheet, and Google answers 429 (too many
requests) when they all write at once; instead of crashing, each call waits a random while and tries again."""
import random
import time

from google.auth.transport.requests import AuthorizedSession

_orig = AuthorizedSession.request


def _patient(self, method, url, *a, **k):
    for attempt in range(10):
        r = _orig(self, method, url, *a, **k)
        if r.status_code not in (429, 500, 502, 503, 504):
            return r
        time.sleep(min(15 * (attempt + 1), 90) + random.uniform(0, 20))
    return r


AuthorizedSession.request = _patient
