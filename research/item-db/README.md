# Item Research Database

This directory is for local, generated Battle.net item data used while building
the AhSense ontology. Generated `.sqlite` and `.jsonl` files are ignored by git.

Current product reality is treated as Midnight-first:

- prioritize Midnight expansion items when choosing endpoints and ontology work
- keep earlier-expansion data only when it falls out naturally from broad API
  pulls
- do not spend dedicated effort on old-expansion coverage when it conflicts
  with current gameplay assumptions

## Import Flow

1. Copy `.env.example` to `.env` and fill in `BN_CLIENT_ID` and
   `BN_CLIENT_SECRET`.
2. Copy or edit `endpoints.midnight.example.json` with the exact Battle.net API
   endpoints you want to pull.
3. Run:

```powershell
python tools\bnet_item_import.py --endpoints research\item-db\endpoints.midnight.example.json --max-workers 16
```

The importer stores normalized item rows in SQLite and raw endpoint payloads for
later ontology research. Use `--enrich-details` to fetch per-item detail
payloads and normalize preview stats, spell/equip text, profession
requirements, descriptions, limit categories, and bonus lists. It does not
change shipped addon data.

Large search endpoints should use `range` slicing. The Battle.net search API can
cap broad result sets, so the Midnight manifest narrows by item ID range and
then fetches pages in parallel within each slice.

The current Battle.net API calls succeed with `Authorization: Bearer ...`; the
importer defaults to header auth and stores redacted URLs in the import log.
