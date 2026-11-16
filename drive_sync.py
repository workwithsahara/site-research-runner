"""Append new leads to a Google Sheet in Drive. Never adds a website already in the sheet."""
import json
import os
from urllib.parse import quote, urlparse

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

API = "https://sheets.googleapis.com/v4/spreadsheets"


def _dom(u):
    u = (u or "").strip().lower()
    return urlparse(u if "//" in u else "//" + u).netloc.replace("www.", "")


def append_new(rows, cols):
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    sess = AuthorizedSession(creds)
    sid = os.environ["SHEET_ID"]
    meta = sess.get(f"{API}/{sid}", params={"fields": "sheets.properties(sheetId,title)"})
    meta.raise_for_status()
    sheets = [s["properties"] for s in meta.json()["sheets"]]
    titles = [s["title"] for s in sheets]
    tab = os.environ.get("SHEET_TAB") or titles[0]
    if tab not in titles:
        if len(sheets) == 1 and titles[0] not in ("Repo 1", "Repo 2"):
            req = {"updateSheetProperties": {"properties": {"sheetId": sheets[0]["sheetId"], "title": tab},
                                              "fields": "title"}}
        else:
            req = {"addSheet": {"properties": {"title": tab}}}
        b = sess.post(f"{API}/{sid}:batchUpdate", json={"requests": [req]})
        b.raise_for_status()
    r = sess.get(f"{API}/{sid}/values/{quote(tab + '!A:Z', safe='')}")
    r.raise_for_status()
    existing = [row for row in r.json().get("values", []) if any(row)]
    if len(existing) == 1 and existing[0] != cols:
        # only a stale header row so far: refresh it to the current columns
        u = sess.put(f"{API}/{sid}/values/{quote(tab + '!A1', safe='')}",
                     params={"valueInputOption": "RAW"}, json={"values": [cols]})
        u.raise_for_status()
        existing = [cols]
    values = []
    if not existing:
        values.append(cols)
    website_idx = cols.index("Website")
    have = {_dom(v[website_idx]) for v in existing[1:] if len(v) > website_idx}
    n = max(len(existing) - 1, 0)
    added = 0
    for row in rows:
        if _dom(row["Website"]) in have:
            continue
        n += 1
        out = [row.get(c, "") for c in cols]
        out = [("'" + v if isinstance(v, str) and v[:1] in ("+", "=", "-", "@") else v) for v in out]  # keeps +61 numbers as text
        out[0] = n
        values.append(out)
        have.add(_dom(row["Website"]))
        added += 1
    if not added:
        return 0
    a = sess.post(f"{API}/{sid}/values/{quote(tab + '!A1', safe='')}:append",
                  params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
                  json={"values": values})
    a.raise_for_status()
    return added
