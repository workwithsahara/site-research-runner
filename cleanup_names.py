"""One-off tidy: blanks first names that are not real names and removes the matching name from the Personalized line."""
import re
import names
from store import Store


def col(n):
    s = ""
    n += 1
    while n:
        n, rem = divmod(n - 1, 26)
        s = chr(65 + rem) + s
    return s


def main():
    st = Store()
    rows = st._read(st.leads_tab, "A:Z")
    head = rows[0]
    iD, iE, iQ = head.index("First name"), head.index("Owner or founder (public)"), head.index("Personalized")
    data = []
    cleared = fixed = 0
    for i, r in enumerate(rows[1:], start=2):
        r = r + [""] * (len(head) - len(r))
        d, e, q = r[iD].strip(), r[iE].strip(), r[iQ]
        newq = None
        if d and names.first_name(e) != d:
            data.append({"range": f"{st.leads_tab}!{col(iD)}{i}", "values": [[""]]})
            cleared += 1
            if q.startswith(d + ", "):
                rest = q[len(d) + 2:]
                newq = rest[:1].upper() + rest[1:]
        elif not d:
            m = re.match(r"^([A-Za-z'\-]+), ((?:I came across|I noticed).*)$", q, re.S)
            if m and not names.real_first_name(m.group(1)):
                newq = m.group(2)
        if newq is not None:
            data.append({"range": f"{st.leads_tab}!{col(iQ)}{i}", "values": [[newq]]})
            fixed += 1
    for k in range(0, len(data), 200):
        res = st.s.post(f"https://sheets.googleapis.com/v4/spreadsheets/{st.sid}/values:batchUpdate",
                        json={"valueInputOption": "RAW", "data": data[k:k + 200]})
        res.raise_for_status()
    print(f"first names cleared: {cleared}, Personalized lines fixed: {fixed}, rows read: {len(rows) - 1}")


if __name__ == "__main__":
    main()
