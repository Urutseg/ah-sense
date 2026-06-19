# Ontology Notes

Ontology quality is the core product quality.

## Initial Data Families

- Vendor mappings
- Consumable families
- Profession tool equivalence

## Expansion Priority

Current ontology work is Midnight-first. Earlier expansion items may appear when
they are inexpensive side effects of broad data pulls, but they should not get
dedicated implementation effort unless they are still relevant to modern
Auction House behavior.

Generated Battle.net API research data belongs under `research/item-db` and must
remain separate from the shipped addon ontology until a group is curated,
explainable, and assigned a confidence tier.

Use `docs/research-data.md` as the entry point for the current local item
database, schema notes, refresh command, and starter queries.

Use `docs/ontology-curation.md` before adding, promoting, demoting, or removing
shipped ontology entries.

## Confidence Tiers

Tier 1 recommendations are high-confidence and eligible for passive hints.

Tier 2 recommendations are medium-confidence and should require explicit user action before display.

Tier 3 areas are deferred until the trust risk is better understood.

Passive hint eligibility is explicit. A Tier 1 entry still needs
`passive_eligible = true`; current Midnight consumable and profession-equipment
seed groups stay active-mode only until vendor or fixed-cost evidence is
strong enough for passive display.

## Required Rationale

Every future recommendation must expose a reason such as:

- Vendor item
- Same consumable category
- Same profession bonus
- Exact recipe substitute

Black-box recommendations are out of scope.
