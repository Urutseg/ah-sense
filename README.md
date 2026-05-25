# Auction House Sense

Auction House Sense is a lightweight World of Warcraft addon concept for contextual Auction House assistance.

The product goal is to help players avoid obvious bad purchases, discover conservative alternatives, and receive non-blocking seller-side sanity hints without becoming a full market scanner or automation tool.

## Current Status

This repository currently contains project scaffolding only. Addon behavior, Lua modules, UI, and data tables have not been implemented yet.

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
- `AhSense/Core/` - future addon lifecycle and shared runtime modules
- `AhSense/Data/` - future curated ontology and vendor mapping data
- `AhSense/UI/` - future tooltip, AH, and posting UI modules
- `AhSense/Integrations/` - future optional compatibility layers
- `docs/` - design notes for architecture, ontology, and releases
- `docs/spec.md` - product specification

## Development Notes

The project should stay fully client-side until there is a clear reason to add external services. Recommendations must be explainable, conservative, and advisory.

## License

License is not selected yet.
