# Seller Surface Design Notes

Seller-side AhSense should restore missing comparison context across selling
interfaces, not replace the selling interface.

## Product Posture

- Keep seller guidance advisory, explainable, and conservative.
- Do not post, undercut, cancel, or silently change a price.
- Show evidence near the selling moment; move detail into an explicit surface.
- Prefer high-confidence omissions over noisy warnings.
- Treat Blizzard Auction House, Auctionator, TSM, and Auctioneer as surfaces
  over the same seller evaluation model.

## Core Flow

1. Player opens a sell surface and selects an item to post.
2. AhSense detects the sell context: item, item key or quality, quantity, and
   current intended unit price when available.
3. The seller evaluator finds the curated comparison group and performs targeted
   Auction House queries for the item and documented equivalents.
4. If the intended price is dominated by a comparable listing, AhSense shows a
   small advisory signal in the active sell surface.
5. Hovering the signal shows one short explanation.
6. Clicking the signal opens the sidecar for full evidence and optional manual
   price-fill actions.

## Surfaces

### Advisory Signal

The advisory signal is the default seller-side surface. It should be tiny and
portable enough to attach to Blizzard Auction House or supported addon sell UIs.

Examples:

- `Comparable listing lower`
- `Higher-quality variant lower`
- `Similar utility listed lower`

Use restrained amber styling. Avoid red error treatment, blocking dialogs, or
animated urgency. A subtle border, badge, or icon near the item or price field is
preferred over a large inline panel.

Tooltip copy stays one short explanation:

- `A higher-quality variant is currently listed below your unit price.`
- `A comparable item from the same reviewed group is listed lower.`

### Sidecar Panel

The sidecar is the explicit detail surface. It should be closed by default, not
necessarily disabled by default. A high-confidence advisory can invite the user
to open it.

The sidecar should include:

- the item being posted and intended unit price
- same-item quality or item-level ladder when relevant
- curated equivalent item comparisons when relevant
- lowest observed comparable price
- rationale and confidence tier
- timestamp or freshness of live data
- explicit manual price-fill controls when technically safe

The sidecar should not become a replacement sell tab or market terminal.

### Optional Price Fill

Price-fill controls are allowed only as explicit user actions. They may fill a
price field but must never post the auction or silently alter the user's price.

Preferred labels:

- `Use reference price`
- `Fill selected price`
- `Match selected row`

Avoid undercut framing.

## Official Auction House Wrinkle

The Blizzard sell tab already exposes some same-item quality-tier context by
showing current postings across tiers and positioning the player's item in the
price ladder. AhSense should not duplicate that as a large panel by default.

The stronger value is universal context:

- same-item quality comparisons in addon sell UIs that omit Blizzard's ladder
- curated cross-item alternatives with similar utility
- consistent explanation and confidence language across sell surfaces

For Blizzard UI, the advisory may be quieter because some evidence is already
visible. For Auctionator, TSM, Auctioneer, and other supported sell surfaces, the
same advisory can close the missing-awareness gap.

## Architecture Direction

Separate seller behavior into:

- a shared seller evaluator that understands item groups, intended unit price,
  dominance rules, and explanation data
- surface adapters that detect sell contexts and attach the tiny advisory signal
  to each supported UI
- one shared sidecar panel for detailed evidence

Surface adapters should degrade gracefully. If a supported addon changes its
frame layout, AhSense should hide that adapter's advisory instead of anchoring
incorrectly or blocking the seller flow.

## Open Validation Questions

- Which supported addon sell UIs expose item, quality or item key, quantity, and
  intended unit price reliably?
- Can AhSense fill addon price fields safely without protected-action or taint
  issues?
- How often do targeted seller queries collide with other AH addons' own query
  behavior?
- Does the advisory signal feel helpful or noisy in rapid-posting workflows?
- Should high-confidence seller advisories be default-on with the sidecar closed,
  or should the entire seller layer be opt-in for the first release?
