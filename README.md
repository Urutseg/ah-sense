# Auction House Sense

Auction House Sense is a lightweight World of Warcraft addon concept for contextual Auction House assistance.

The product goal is to help players avoid obvious bad purchases, discover conservative alternatives, and receive non-blocking seller-side sanity hints without becoming a full market scanner or automation tool.

## Current Status

This repository now contains a Phase 1 MVP spine: addon lifecycle modules, a conservative Lua ontology, small high-confidence seed data, a guarded targeted Auction House query adapter, one-line tooltip hints, and an explicit comparison panel.

## Scope

MVP focus:

- Vendor alternative hints
- Consumable family alternatives
- Profession tool comparisons

Out of scope for the initial product:

- Automated buying or posting
- Full-market scans
- Flipping, sniping, or profit-maximization workflows
- Gear optimization
- Server, desktop companion, or external sync dependencies

## Repository Layout

- `AhSense/` - addon folder intended to be installed under `Interface/AddOns/AhSense`
- `AhSense/AhSense.toc` - addon metadata
- `AhSense/Core/` - addon lifecycle, configuration, recommendation, and Auction House query modules
- `AhSense/Data/` - curated ontology and seed vendor, consumable, and profession-tool data
- `AhSense/UI/` - tooltip hint and comparison panel modules
- `AhSense/Integrations/` - future optional compatibility layers
- `docs/` - design notes for architecture, ontology, and releases
- `docs/spec.md` - product specification
- `docs/research-data.md` - local Battle.net item database hook for ontology work

## Development Notes

The project should stay fully client-side until there is a clear reason to add external services. Recommendations must be explainable, conservative, and advisory.

Ontology research is Midnight-first. Local Battle.net item pulls can be stored
under `research/item-db` with `tools/bnet_item_import.py`; generated databases
and raw payloads are intentionally ignored by git. See `docs/research-data.md`
before adding or expanding ontology groups.

## License

License is not selected yet.
