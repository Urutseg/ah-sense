# Milestone 1 Implementation Order

1. Issue #1: Define addon module architecture and lifecycle
2. Issue #2: Design conservative ontology schema
3. Issue #3: Seed vendor alternative mappings
4. Issue #4: Seed consumable family alternatives
5. Issue #5: Seed profession tool equivalence groups
6. Issue #6: Build targeted Auction House query adapter
7. Issue #7: Prototype one-line Auction House tooltip hints
8. Issue #8: Build active comparison panel MVP
9. Issue #9: Validate MVP trust and performance guardrails

This order keeps runtime foundations ahead of data, data ahead of live Auction House calls, and live calls ahead of UI surfaces.

## Validation Notes

- Passive hints are gated to Tier 1 ontology entries with explicit `passive_eligible = true`.
- Midnight consumable and profession-equipment groups are curated from the local item DB, but remain active-mode only until fixed-cost or vendor evidence supports passive hints.
- Auction House calls are targeted to the current item plus known alternatives and limited by cooldown plus maximum item count.
- No full-market scan, external sync, automation, buy, sell, or undercut workflow is introduced.
- Tooltip hints are one line and only appear while the Auction House frame is visible.
- The comparison panel opens only from an explicit slash command or direct addon API call.

## Current Curated Seeds

- Vendor mappings: evergreen `Crystal Vial` and `Enchanting Vellum`, plus a reviewed Midnight profession reagent pool from normal recipe reagents and modified-crafting category items in `research/ontology-review/vendor-reagent-candidates.md`; passive eligible because these have explicit vendor-supply evidence.
- Consumable families: reviewed Midnight potion, flask, and phial rank variants plus active-only Well Fed food-profile groups from `outputs/midnight-consumable-equivalents/midnight_consumable_equivalents.xlsx`; active only because magnitude, serving type, and restore caveats can matter.
- Profession tools: active-only Midnight profession-equipment groups by profession and exact equipment role from `research/ontology-review/profession-equipment-equivalent-candidates.md`; two accessory slots are split into separate groups instead of treated as interchangeable. No passive hints because skill values, quality, and secondary profession stats can differ. Bind-on-acquire, placeholder, and unverified common-rod rows remain excluded.

## Follow-up Runtime Checks

- Test tooltip clutter alongside TSM, Auctionator, and CraftSim.
- Confirm `C_AuctionHouse.SearchForItemKeys` throttle behavior on a live realm.
- Record any FPS impact during repeated Auction House hover and comparison-panel use.
- Review seeded item coverage before release; coverage is intentionally small for MVP trust.
