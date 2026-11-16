"""Decides whether a scheduled run should start: only when the last finished run ended more than 24 hours ago."""
import datetime
import os

import store


def main():
    go = True
    if os.environ.get("EVENT") == "schedule" and store.configured():
        try:
            last = store.Store().last_finished()
            if last and (datetime.datetime.utcnow() - last) < datetime.timedelta(hours=24):
                go = False
        except Exception as e:
            print("gate error", type(e).__name__)
            go = False
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"go={'true' if go else 'false'}\n")
    print("start run:", go)


if __name__ == "__main__":
    main()
