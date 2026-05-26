# Research Data Hook

This document is the durable pointer to local generated data that should be used
for AhSense ontology research. The generated database files are intentionally not
tracked by git, but they may exist in this workspace for future chat sessions.

## Current Local Database

- Primary SQLite database: `research/item-db/midnight-research.sqlite`
- Raw API payload archive: `research/item-db/midnight-research.raw.jsonl`
- Endpoint manifest: `research/item-db/endpoints.midnight.example.json`
- Importer: `tools/bnet_item_import.py`
- Focus: Midnight-first item candidates from Battle.net Game Data APIs
- Last known import shape: 1,428 normalized item rows from item IDs
  `240000-280000`

Treat this database as research input only. Do not ship generated rows directly
in the addon. Curate explainable, confidence-tiered groups into `AhSense/Data`
after reviewing the local data.

## When To Use It

Use the local database before working on:

- Midnight consumable families
- Midnight profession equipment equivalence
- vendor-sold item candidates when Battle.net exposes useful price fields
- ontology naming, grouping, and confidence rationale

Old-expansion data should only be used when it appears as a side effect and is
still relevant to modern Auction House behavior.

## Refresh Command

```powershell
python tools\bnet_item_import.py --endpoints research\item-db\endpoints.midnight.example.json --database research\item-db\midnight-research.sqlite --jsonl research\item-db\midnight-research.raw.jsonl --max-workers 16
```

The importer reads `.env` for Battle.net credentials and defaults to
`Authorization: Bearer ...` header auth. Generated `.sqlite` and `.jsonl` files
are ignored by git.

## Useful Queries

Modern profession equipment candidates:

```powershell
python -c "import sqlite3; con=sqlite3.connect('research/item-db/midnight-research.sqlite'); [print(row) for row in con.execute('select item_id,name,item_subclass_name,level,required_level,quality_type from items where item_class_id=19 and required_level >= 68 order by item_subclass_name,item_id')]"
```

Consumable families with ontology potential:

```powershell
python -c "import sqlite3; con=sqlite3.connect('research/item-db/midnight-research.sqlite'); [print(row) for row in con.execute('select item_subclass_name,count(*) from items where item_class_id=0 group by item_subclass_name order by item_subclass_name')]"
```

Quick schema check:

```powershell
python -c "import sqlite3; con=sqlite3.connect('research/item-db/midnight-research.sqlite'); [print(row) for row in con.execute('pragma table_info(items)')]"
```

## Curation Rule

The database can suggest candidates, but the addon ontology still requires:

- a conservative group boundary
- an explicit rationale
- a confidence tier
- a low false-positive risk for passive hints
