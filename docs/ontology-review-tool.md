# Ontology Review Tool

`tools/ontology_review.py` is a local-only development tool for turning the
enriched research database into reviewed Lua ontology drafts. It is not part of
the addon and does not add a runtime dependency.

The tool is intentionally review-by-verdict: app logic generates transparent
candidates, and the reviewer answers:

- `Yes, ship it`
- `No, reject it`
- `Show Wowhead links`

Review state and generated drafts are written under `research/ontology-review/`,
which is ignored by git.

## Validate

Run validation through `uv`:

```powershell
uv run python tools\ontology_review.py validate
```

Validation checks that `research/item-db/midnight-research.sqlite` has the
enriched schema required for candidate generation, then reports the generated
candidate count.

The generator excludes bind-on-pickup rows because those items cannot appear on
the Auction House and are irrelevant to addon recommendations.

## Review UI

Start the local offline review app:

```powershell
uv run python tools\ontology_review.py serve
```

Open:

```text
http://127.0.0.1:8765
```

The UI shows one candidate at a time with item IDs, Wowhead links, proposed
Lua fields, and an evidence trace explaining the match.

## Candidate Rules

Initial rules:

- `profession_exact_utility_match` - same profession, quality, item level,
  required level, stat signature, spell IDs, and equip text.
- `consumable_same_name_spell_variants` - same consumable name and item-provided
  spell across item-level variants.
- `consumable_same_spell_family` - same item-provided spell across differently
  named potions or flasks; generated as Tier 2 and flagged for human review.

All generated candidates default to `passive_eligible = false`. Passive hints
still require stricter vendor, fixed-cost, or identical-utility evidence.

The current addon schema allows one ontology group per item. Export fails if
approved candidates overlap, so choose either a broader same-spell family or the
narrower same-name groups before promoting Lua.

## Export Lua Drafts

After approving candidates in the UI, export drafts:

```powershell
uv run python tools\ontology_review.py export-lua
```

or use `Export Lua Drafts` in the UI.

Draft files are written to:

- `research/ontology-review/generated/Consumables.lua`
- `research/ontology-review/generated/ProfessionTools.lua`

Review the drafts before manually promoting entries into `AhSense/Data/*.lua`.
