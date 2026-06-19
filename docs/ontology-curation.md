# Ontology Curation Guide

The ontology is curated product data, not generated truth. The local item DB can
suggest candidates, but every shipped entry must be manually reviewed before it
appears in `AhSense/Data/*.lua`.

## Review Goal

Only keep recommendations that are relevant to current gameplay, explainable to
a player, and unlikely to create false confidence. Missing a recommendation is
acceptable. Showing a wrong passive hint is not.

## Evidence Checklist

Before adding or keeping an ontology entry, verify:

- The item IDs and names match the current local item DB or an in-game item.
- For quality-tiered or item-level variant groups, live AH item-key levels have
  been checked in game. Do not rely on generic item links or static preview
  levels alone.
- The items are relevant to the current expansion priority documented in
  `docs/ontology.md`.
- The group boundary is narrow enough to explain in one sentence.
- The rationale names real evidence, such as vendor supply, same item across
  quality or item-level variants, same profession slot, or exact utility match.
- The items can plausibly appear on the Auction House. Bind-on-pickup items are
  irrelevant for AhSense recommendations and must not ship in ontology groups.
- Fleeting potion and flask variants are temporary cauldron-created items, not
  normal Auction House candidates, and must not ship in ontology groups.
- The recommendation does not depend on class, spec, encounter, simulation,
  embellishment, proc behavior, or player preference.
- The entry has `confidence_tier`, `passive_eligible`, and `rationale`.

## Confidence Tiers

Use `tier1` only when the relationship is high-confidence and easy to audit.
Examples:

- vendor or fixed-cost alternative with a known price
- same named consumable across quality or item-level variants
- same profession, same profession-equipment role, same broad quality band
- exact recipe or utility substitute

Use `tier2` when the relationship may be useful but should require explicit
user action. Examples:

- same profession but different equipment role
- same consumable category but not the same named item
- similar utility where live AH prices may matter more than static data

Do not ship `tier3` behavior. Remove or defer entries involving spec-sensitive
gear, trinkets, proc effects, PvP edge cases, transmog value, or optimization.

## Passive Hint Rules

`passive_eligible = true` is stricter than `confidence_tier = "tier1"`.

Only mark an entry passive eligible when all are true:

- It is Tier 1.
- A vendor or fixed-cost alternative exists, or the utility match is identical.
- The lower-cost case is expected to be obvious in normal AH usage.
- The hint can be stated in one non-judgmental line.
- A reviewer would be comfortable showing it without opening the panel.

When in doubt, keep `passive_eligible = false`. Active-mode recommendations can
still appear in `/ahs <itemID>` without adding tooltip clutter.

## Curation Workflow

1. Start from `docs/research-data.md` and query the local SQLite database.
2. Build a short candidate list, grouped by narrow evidence.
3. Check candidate item IDs in game when possible.
4. Add only reviewed candidates to `AhSense/Data/*.lua`.
5. Give every group a specific rationale, not a generic category label.
6. Run the validation checks below.
7. Test at least one item per changed group in game with `/ahs <itemID>`.

## Rectifying Bad Entries

If an entry looks wrong in game:

- Remove it if the relationship is false, ambiguous, outdated, or irrelevant.
- Demote it to `tier2` if it may still be useful but needs explicit inspection.
- Set `passive_eligible = false` if the data is useful but too noisy for a
  tooltip.
- Narrow the group if only some items share the claimed rationale.
- Rewrite the rationale if the recommendation is correct but not explainable.

Do not keep an entry merely because the database grouped it cleanly. The local
database is input evidence, not approval.

## Validation Checks

Run these after ontology edits:

```powershell
rg -n "confidence_tier|passive_eligible|rationale" AhSense\Data
rg -n "Better|Best|Correct|scam|should buy|overpriced" AhSense docs
npx --package luaparse luaparse AhSense\Data\Ontology.lua
```

Also inspect `AhSense/AhSense.toc` when adding data files so load order remains
`Ontology.lua` before curated data modules.

For Auction House item-key, item-level, or tooltip issues, use
`docs/auction-house-runtime-notes.md` before changing runtime code or ontology
variant levels.

## In-Game Smoke Tests

For each changed group:

- `/ahs <itemID>` opens the panel.
- The panel rationale matches the evidence.
- Active-only groups do not add passive tooltip lines.
- Passive vendor hints appear only in Auction House item tooltips.
- No errors appear in chat or BugSack/BugGrabber.
- Rapid repeated `/ahs` calls report cooldown behavior instead of query spam.
- Item-level variant tooltips match the real Auction House row tooltip; generic
  wrong-tier item links are not acceptable fallbacks.
