# Research Data Hook

This document is the durable pointer to local generated data that should be used
for AhSense ontology research. The generated database files are intentionally not
tracked by git, but they may exist in this workspace for future chat sessions.

## Current Local Database

- Primary SQLite database: `research/item-db/midnight-research.sqlite`
- Raw API payload archive: `research/item-db/midnight-research.raw.jsonl`
- Endpoint manifest: `research/item-db/endpoints.midnight.example.json`
- Importer: `tools/bnet_item_import.py`
- Profession importer: `tools/bnet_profession_import.py`
- Ontology review tool: `tools/ontology_review.py`
- Focus: Midnight-first item candidates from Battle.net Game Data APIs
- Last known import shape: 1,428 normalized item rows from item IDs
  `240000-280000`, with 1,428 enriched per-item detail payloads

Treat this database as research input only. Do not ship generated rows directly
in the addon. Curate explainable, confidence-tiered groups into `AhSense/Data`
after reviewing the local data.

## Enriched Schema Notes

The importer uses Battle.net item search for candidate discovery, then calls the
per-item Game Data endpoint for each item. The detail payload exposes
`preview_item` data that is useful for high-confidence ontology work.

Useful normalized tables:

- `items` - one row per item, including class/subclass, inventory type, quality,
  item level, required level, price fields, binding, description,
  `limit_category`, `stat_signature`, `spell_ids_json`, `equip_use_text`,
  required profession fields, and preserved search `raw_json`
- `item_details` - one raw per-item detail payload per item for auditability
- `item_stats` - one row per preview stat, including profession stats such as
  Ingenuity, Multicraft, Resourcefulness, and Crafting Speed
- `item_spells` - spell IDs, spell names, and readable item-provided spell text
  such as `Equip: +18 Midnight Blacksmithing Skill`
- `professions` - profession index/detail rows from the official Profession API
- `profession_skill_tiers` - imported Midnight profession skill-tier payloads
- `profession_recipe_categories` - recipe category names within skill tiers
- `recipes` - official recipe detail payloads, including descriptions and any
  crafted item reference exposed by the API
- `recipe_reagents` - recipe reagent item IDs, names, and quantities; useful for
  proving that an item is used as a reagent before considering vendor ontology
- `recipe_modified_crafting_slots` - recipe optional/reagent slot references
- `modified_crafting_categories`, `modified_crafting_slot_types`, and
  `modified_crafting_slot_type_categories` - official Modified Crafting API
  metadata and compatible category relationships

Observed useful Battle.net detail fields:

- `preview_item.stats`
- `preview_item.spells`
- `preview_item.requirements.skill`
- `preview_item.inventory_type`
- `preview_item.limit_category`
- `preview_item.bonus_list`
- item or preview `description`
- recipe `reagents`
- recipe `modified_crafting_slots`
- modified-crafting slot type `compatible_categories`

Observed limitations:

- The API provides item-provided spell references and descriptions, but the
  probed `/data/wow/spell/{id}` endpoint returned 404 for Midnight profession
  bonus spell IDs. Treat `item_spells.description` as the reliable normalized
  text and keep `item_details.raw_json` for audit.
- Broad tooltip rendering is not exposed as complete tooltip lines. The closest
  official source is `preview_item` plus item `description`.
- Vendor NPC references were not observed in item payloads. Some reagent item
  descriptions do explicitly say `Sold by vendors`, `Sold by <profession>
  vendors`, or `Can be purchased from vendors`; this is stronger evidence than
  `purchase_price` alone and should be combined with `recipe_reagents` before
  creating vendor-reagent review candidates. Descriptions that mention other
  currencies, account binding, or bind-on-acquire sources are not passive
  vendor-trap candidates.
- Bind-on-pickup items are not useful for AhSense ontology groups because they
  cannot appear on the Auction House.
- Fleeting potion and flask variants are temporary cauldron-created items, so
  they are excluded from Auction House ontology candidates.
- No separate crafting quality or reagent quality field was observed in the
  current candidate detail payloads. Quality and `bonus_list` are preserved for
  review, but quality-tier equivalence still needs human validation.

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

To enrich an existing database without re-running search:

```powershell
python tools\bnet_item_import.py --endpoints research\item-db\endpoints.midnight.example.json --database research\item-db\midnight-research.sqlite --jsonl research\item-db\midnight-research.raw.jsonl --details-only --max-workers 16
```

To rebuild and enrich in one pass:

```powershell
python tools\bnet_item_import.py --endpoints research\item-db\endpoints.midnight.example.json --database research\item-db\midnight-research.sqlite --jsonl research\item-db\midnight-research.raw.jsonl --enrich-details --max-workers 16
```

To add official Profession API, Recipe API, and Modified Crafting API data for
Midnight skill tiers:

```powershell
python tools\bnet_profession_import.py --database research\item-db\midnight-research.sqlite --jsonl research\item-db\midnight-professions.raw.jsonl --max-workers 16
```

This stores ignored research-only rows in the same SQLite database and enriches
recipe reagent item details so vendor-reagent candidates can be queried without
shipping generated data.

## Useful Queries

Modern profession equipment candidates:

```powershell
python -c "import sqlite3; con=sqlite3.connect('research/item-db/midnight-research.sqlite'); [print(row) for row in con.execute('select item_id,name,item_subclass_name,level,required_level,quality_type from items where item_class_id=19 and required_level >= 68 order by item_subclass_name,item_id')]"
```

Profession-equipment equivalence candidates by profession, slot, stat
signature, and equip text:

```powershell
python -c "import sqlite3; con=sqlite3.connect('research/item-db/midnight-research.sqlite'); [print(row) for row in con.execute('select required_profession_name,inventory_type_name,limit_category,stat_signature,equip_use_text,group_concat(item_id || \":\" || name, \" | \") from items where item_class_id=19 and required_profession_name is not null group by required_profession_name,inventory_type_name,limit_category,stat_signature,equip_use_text having count(*) > 1 order by required_profession_name,inventory_type_name')]"
```

Profession stats for a specific item:

```powershell
python -c "import sqlite3; con=sqlite3.connect('research/item-db/midnight-research.sqlite'); [print(row) for row in con.execute('select stat_type,stat_name,stat_value,display_string from item_stats where item_id=246537 order by stat_type')]"
```

Spell/equip text for ontology rationale:

```powershell
python -c "import sqlite3; con=sqlite3.connect('research/item-db/midnight-research.sqlite'); [print(row) for row in con.execute('select item_id,spell_id,spell_name,description from item_spells where description is not null order by item_id,spell_id limit 50')]"
```

Consumable families with ontology potential:

```powershell
python -c "import sqlite3; con=sqlite3.connect('research/item-db/midnight-research.sqlite'); [print(row) for row in con.execute('select item_subclass_name,count(*) from items where item_class_id=0 group by item_subclass_name order by item_subclass_name')]"
```

Quick schema check:

```powershell
python -c "import sqlite3; con=sqlite3.connect('research/item-db/midnight-research.sqlite'); [print(row) for row in con.execute('pragma table_info(items)')]"
```

Recipe reagents with direct vendor text:

```powershell
python -c "import sqlite3; con=sqlite3.connect('research/item-db/midnight-research.sqlite'); [print(row) for row in con.execute(\"select rr.reagent_item_id,i.name,i.purchase_price,i.description,count(distinct rr.recipe_id) from recipe_reagents rr join items i on i.item_id=rr.reagent_item_id where (i.description like '%Sold by%vendors%' or i.description like '%Can be purchased from vendors%') and (i.binding_type is null or i.binding_type != 'ON_ACQUIRE') group by rr.reagent_item_id order by count(distinct rr.recipe_id) desc\")]"
```

## Curation Rule

The database can suggest candidates, but the addon ontology still requires:

- a conservative group boundary
- an explicit rationale
- a confidence tier
- a low false-positive risk for passive hints

Use `docs/ontology-review-tool.md` for the local review UI and Lua draft export
workflow.
