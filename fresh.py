"""Shards keep re-checking sites that another shard already did. This re-reads the shared list of checked sites
every few minutes and drops those from each batch of search results before they are fetched."""
import time


class Fresh:
    def __init__(self, loader, every=150):
        self.loader, self.every, self.known, self.last = loader, every, set(), 0.0

    def refresh(self):
        if time.time() - self.last > self.every:
            try:
                self.known = {d.strip().lower() for d in self.loader() if d}
            except Exception:
                pass
            self.last = time.time()

    def filter(self, pairs):
        self.refresh()
        return [p for p in pairs if p[0].lower().replace("www.", "") not in self.known]
