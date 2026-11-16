# site-research-runner

Checks small-business websites for public contact details and writes the results to a private Google Sheet.

- `queries.txt`: search phrases, one per line (`words | Industry`).
- `run.py`: runs the searches in small chunks, checks each site on its own pages, saves results after every batch.
- `store.py`: keeps the list of already checked sites in the sheet, so a site is never checked twice.
- `gate.py`: lets a scheduled run start only when the last run finished more than 24 hours ago.

Nothing found by the runner is stored in this repository or printed in the logs. Settings are repository secrets:
`GOOGLE_SERVICE_ACCOUNT_JSON` and `SHEET_ID`.
