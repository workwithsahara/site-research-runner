"""Private storage in the Google Sheet (tabs Checked, Review, Runs). Nothing about leads is kept in this repository."""
import datetime
import json
import os
from urllib.parse import quote

API = "https://sheets.googleapis.com/v4/spreadsheets"
TABS = {
    "Checked": ["Domain", "Date", "Result"],
    "Review": ["Date found", "Company", "Website", "Owner or founder (public)", "Email", "Phone", "Industry",
               "Based in", "Why it did not pass"],
    "Runs": ["Finished (UTC)", "New leads", "Sites checked", "Stopped because"],
    "FRA Leads": ["Date found", "Agency", "Website", "Country", "City", "Email", "Hires for",
                  "Open job order signals", "Seeks Philippine partner agencies", "Licence or verification clue", "Pages read"],
    "FRA Checked": ["Domain", "Date", "Result"],
}


def configured():
    return bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") and os.environ.get("SHEET_ID"))


class Store:
    def __init__(self):
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account
        info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        self.s = AuthorizedSession(creds)
        self.sid = os.environ["SHEET_ID"]
        self.leads_tab = os.environ.get("SHEET_TAB", "Leads")
        self._ensure()

    def _url(self, tab, rng):
        return f"{API}/{self.sid}/values/{quote(tab + '!' + rng, safe='')}"

    def _ensure(self):
        m = self.s.get(f"{API}/{self.sid}", params={"fields": "sheets.properties(title)"})
        m.raise_for_status()
        have = {x["properties"]["title"] for x in m.json()["sheets"]}
        missing = [t for t in TABS if t not in have]
        if missing:
            b = self.s.post(f"{API}/{self.sid}:batchUpdate",
                            json={"requests": [{"addSheet": {"properties": {"title": t}}} for t in missing]})
            b.raise_for_status()
            for t in missing:
                u = self.s.put(self._url(t, "A1"), params={"valueInputOption": "RAW"}, json={"values": [TABS[t]]})
                u.raise_for_status()

    def _read(self, tab, rng="A:Z"):
        r = self.s.get(self._url(tab, rng))
        r.raise_for_status()
        return r.json().get("values", [])

    def _append(self, tab, rows):
        if not rows:
            return
        a = self.s.post(self._url(tab, "A1") + ":append",
                        params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                        json={"values": rows})
        a.raise_for_status()

    def read_checked(self):
        return {(r[0] or "").strip().lower() for r in self._read("Checked", "A:A")[1:] if r}

    def read_leads(self):
        rows = self._read(self.leads_tab, "A:Z")
        if not rows:
            return []
        head = rows[0]
        return [dict(zip(head, r + [""] * (len(head) - len(r)))) for r in rows[1:] if any(r)]

    def add_checked(self, rows):
        self._append("Checked", rows)

    def add_review(self, rows):
        self._append("Review", rows)

    def last_finished(self):
        vals = [r[0] for r in self._read("Runs", "A:A")[1:] if r and r[0]]
        if not vals:
            return None
        return datetime.datetime.strptime(vals[-1], "%Y-%m-%dT%H:%M:%SZ")

    def add_run(self, new, checked, stop):
        now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self._append("Runs", [[now, new, checked, stop]])

    def read_domains(self, tab):
        return {(r[0] or "").strip().lower() for r in self._read(tab, "A:A")[1:] if r}

    def read_table(self, tab):
        rows = self._read(tab, "A:Z")
        if not rows:
            return []
        head = rows[0]
        return [dict(zip(head, r + [""] * (len(head) - len(r)))) for r in rows[1:] if any(r)]

    def add_rows(self, tab, rows):
        self._append(tab, rows)
