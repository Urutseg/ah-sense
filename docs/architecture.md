# Architecture Notes

Auction House Sense starts as a fully client-side World of Warcraft addon.

## Initial Boundaries

- No backend service
- No desktop companion app
- No external sync requirement
- No full Auction House scan behavior
- No automated buy, sell, undercut, mailbox, or inventory workflows

## Local Research Data

The shipped addon remains client-side and static, but development can use a
local generated Battle.net item database for ontology research. Future sessions
should check `docs/research-data.md` before adding curated data under
`AhSense/Data`.

## Future Module Areas

- Core addon lifecycle and configuration
- Static ontology data
- Targeted Auction House queries
- Tooltip hint surface
- Explicit comparison panel
- Posting UI advisory surface
- Seller-side evaluator, surface adapters, and shared sidecar panel
- Optional compatibility layers for other addons or price sources

## Performance Posture

Future implementation should favor targeted queries, caching, throttling, and graceful degradation. Compatibility with common Auction House and crafting addons is a design constraint.

## Seller Surface Direction

Seller assistance should be implemented as a portable sanity layer rather than a
replacement selling interface. A shared seller evaluator should detect dominated
listings from curated comparison groups and targeted live pricing. Thin surface
adapters can attach a small advisory signal to Blizzard Auction House and
supported addon sell UIs, with one shared sidecar panel for explanation.

The addon must not post, undercut, cancel, or silently adjust prices. Any price
fill behavior must be an explicit user action and must leave final posting to
the player.

## Runtime AH Notes

Auction House item-key behavior has important edge cases for crafted
item-level variants and tooltips. Before changing targeted queries, comparison
panel rows, or tooltip rendering, read `docs/auction-house-runtime-notes.md`.
