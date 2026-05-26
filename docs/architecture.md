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
- Optional compatibility layers for other addons or price sources

## Performance Posture

Future implementation should favor targeted queries, caching, throttling, and graceful degradation. Compatibility with common Auction House and crafting addons is a design constraint.
