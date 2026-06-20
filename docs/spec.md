# WoW Auction House Sense — Product Spec v0.1

## Product Summary

A lightweight World of Warcraft addon that helps players:

* avoid overpriced Auction House purchases
* discover functionally similar alternatives
* avoid posting items at unrealistic prices

The addon is **not**:

* a goblin/flipping tool
* a TSM competitor
* a full-market scanner
* an automation suite

The addon **is**:

* a contextual “shopping assistant”
* a market sanity layer
* a curated economic commonsense system

Core philosophy:

* show data, not judgment
* integrate into existing AH behavior
* minimize UI clutter
* prioritize trust over coverage

---

# Core User Stories

## Buyer-side

### Story B1 — Vendor Trap Prevention

As a buyer,
when I hover or search an item listed far above vendor price,
I want to know it can be purchased from a vendor cheaper.

Example:

* AH listing: 450g
* Vendor price: 12g

Expected outcome:

* player avoids wasteful purchase

---

### Story B2 — Similar Consumable Alternatives

As a buyer,
when viewing a consumable,
I want to see cheaper comparable consumables with similar utility.

Example:

* Flask A: +500 stat, 1200g
* Flask B: +450 stat, 220g

Expected outcome:

* player discovers cheaper “good enough” alternative

---

### Story B3 — Comparable Profession Tools

As a crafter,
when viewing profession equipment,
I want to see equivalent tools/accessories with similar bonuses.

Example:

* Tool A: +18 skill, 9000g
* Tool B: +18 skill, 1200g

Expected outcome:

* player avoids fake scarcity pricing

---

## Seller-side

### Story S1 — Posting Sanity Check

As a seller,
when posting an item,
I want to know whether nearby alternatives dominate my listing.

Example:

* player posts inferior item for 9000g
* addon notices superior alternative already listed for 2000g

Expected outcome:

* seller avoids repeated expired auctions

---

# Explicit Non-Goals (Important)

These are intentionally OUT OF SCOPE.

## No:

* automated buying
* automated undercutting
* flipping/sniping workflows
* mailbox automation
* inventory optimization
* profit maximization systems
* market prediction
* AI/ML recommendation engine
* server infrastructure (initially)
* desktop companion app (initially)
* global full-market scans
* real-time economy monitoring
* transmog valuation
* spec-accurate gear optimization
* simcraft-like calculations

---

# UX Philosophy

## Primary design principle:

“Contextual assistance, not dashboard takeover.”

The addon should:

* augment existing workflows
* avoid visual noise
* avoid giant panels
* avoid “spreadsheet UI”

---

# UX Model

## Passive Mode

Minimal signal only.

Examples:

* `🔁 Alternatives available`
* `🏪 Vendor alternative exists`
* `⚑ Comparable items cheaper`

No large automatic panels.

---

## Active Mode

User explicitly requests deeper comparison.

Possible triggers:

* click hint line
* small AH button
* optional hotkey

Then:

* fetch live alternative pricing
* show comparison panel

---

# UI Components

## 1. AH Tooltip Hint

Minimal inline signal.

Examples:

* `🔁 3 comparable alternatives`
* `🏪 Vendor version available`
* `⚑ Similar listings much cheaper`

IMPORTANT:

* one line maximum by default
* no paragraphs
* no hard judgment language

---

## 2. Alternative Comparison Panel

Opened explicitly by user.

Contains:

* alternative item list
* live prices
* savings estimate
* reason for recommendation

Example columns:

* Item
* Price
* Difference
* Rationale

---

## 3. Sell-side Advisory

Integrated into posting UI.

Examples:

* `⚑ Comparable item currently listed for less`
* `⚑ Vendor alternative exists`
* `⚑ Similar item family saturated`

Must:

* avoid blocking user
* avoid red error styling
* remain advisory only
* work as a portable layer across Blizzard Auction House and supported addon
  sell UIs where practical
* keep the passive surface tiny; full detail belongs in an explicit sidecar

Seller assistance should restore missing comparison context across selling
interfaces. The Blizzard sell tab already exposes some same-item quality-tier
pricing context, while common addon sell UIs may omit that ladder. AhSense should
use a shared seller evaluator, small surface-specific advisory signals, and one
shared sidecar panel for evidence.

Allowed only on explicit user action:

* opening the sidecar explanation
* filling a price field from a selected reference row, if technically safe

Not allowed:

* silently changing the user's price
* automatically undercutting
* posting or canceling auctions

---

# Technical Architecture

## Architecture Type

Initial architecture:

# Fully client-side

No:

* web backend
* desktop app
* external sync

Optional future integrations:

* Oribos Exchange
* TSM price sources

---

# Data Sources

## Static Data (shipped with addon)

Curated equivalence ontology:

* consumable families
* profession tool equivalence
* vendor mappings
* safe gear clusters

Stored as Lua tables.

Updated:

* manually
* patch-by-patch

---

## Live Data

Use:

* `C_AuctionHouse.SearchForItemKeys`

DO NOT:

* rely on full scans
* perform market-wide crawling

Runtime model:

1. user enters relevant AH interaction
2. addon identifies equivalence cluster
3. targeted live queries executed
4. comparison generated

---

# Ontology Design

## Key Insight

Ontology quality is the product quality.

Initial ontology should prioritize:

* high-confidence equivalence
* low false positives
* explainability

---

# Ontology Confidence Tiers

## Tier 1 — High Confidence

Safe recommendations only.

Examples:

* vendor equivalents
* exact profession utility
* same consumable family
* exact recipe substitutes

Allowed:

* automatic passive hints

---

## Tier 2 — Medium Confidence

Reasonable practical substitutes.

Examples:

* same slot
* same primary stat
* nearby ilvl

Allowed:

* active-mode only initially

---

## Tier 3 — Dangerous / Deferred

NOT IMPLEMENTED initially.

Examples:

* trinkets
* proc gear
* embellishments
* transmog
* spec-sensitive optimization
* PvP edge cases

---

# Recommendation Philosophy

The addon must:

* show evidence
* avoid authoritative claims

Preferred wording:

* “Comparable”
* “Alternative”
* “Similar utility”
* “Lower-cost option”

Avoid:

* “Better”
* “Best”
* “Correct”
* “Overpriced scam”
* “You should buy”

---

# Explainability Requirements

Every recommendation must expose rationale.

Examples:

* “Same profession bonus”
* “Same consumable category”
* “Nearby item level and primary stat”
* “Vendor item”

Black-box recommendations are forbidden.

---

# Trust Model

Trust is the critical product asset.

Rules:

* false positives worse than missing recommendations
* conservative matching preferred
* uncertainty must be surfaced honestly

Allowed:

* “No reliable alternatives found”

Not allowed:

* fake confidence

---

# Performance Constraints

Must:

* avoid FPS spikes
* avoid full AH scans
* avoid query spam

Must coexist with:

* TSM
* Auctionator
* CraftSim

Use:

* throttling checks
* lightweight runtime queries
* caching

---

# Major Open Questions / Uncertainties

These are NOT solved.

Codex agent should treat them as research/design areas, not implementation assumptions.

---

## OQ1 — Best interaction trigger

Unknown:

* tooltip click?
* AH-side button?
* right-click menu?
* hover affordance?

Need experimentation.

---

## OQ2 — Tooltip clutter tolerance

Unknown:

* how much augmentation players tolerate
* conflicts with TSM/Auctionator/CraftSim

Need real UI prototypes.

---

## OQ3 — Equivalence granularity

Unknown:

* how broad clusters should be
* where users perceive “similar” vs “wrong recommendation”

Critical trust risk.

---

## OQ4 — Live query batching

Unknown:

* practical AH throttle behavior under:

  * TSM
  * Auctionator
  * heavy realms
  * multiple addons querying simultaneously

Needs runtime testing.

---

## OQ5 — Seller advisory usefulness

Unknown:

* whether sellers appreciate advisory
* or perceive it as annoying/noisy

May need opt-in. Initial research should compare default-on tiny advisories with
the sidecar closed against a fully opt-in seller layer. It should also validate
whether supported addon sell UIs hide comparison context that Blizzard's sell
tab already provides.

---

## OQ6 — Gear comparison viability

Still uncertain.

Questions:

* can simple heuristics produce acceptable trust?
* are casual players satisfied with approximate equivalence?

Potentially dangerous feature area.

---

## OQ7 — Patch maintenance burden

Unknown:

* how much manual ontology maintenance required per patch
* whether community contributions become necessary

---

## OQ8 — Dependency strategy

Unknown whether addon should:

* remain standalone forever
* optionally integrate TSM
* integrate Oribos Exchange
* support external data later

---

# Recommended MVP

## MVP Scope

ONLY:

* vendor arbitrage
* consumable family alternatives
* profession tool comparisons

NO gear initially.

---

# MVP Success Criteria

Success means:

* users avoid obviously bad purchases
* recommendations feel trustworthy
* UI feels lightweight
* no major performance complaints
* no dependency on TSM

NOT:

* full economy intelligence
* perfect recommendations
* universal coverage

---

# Suggested Internal Data Structure

Example concept only:

```lua
Ontology = {
  [itemID] = {
    category = "profession_tool",
    confidence = "high",
    alternatives = {
      12345,
      67890
    },
    rationale = {
      type = "same_profession_bonus"
    }
  }
}
```

---

# Suggested Roadmap

## Phase 1 — Foundation

* ontology format
* tooltip hint prototype
* SearchForItemKeys integration
* vendor mappings
* consumable equivalence
* simple comparison panel

Goal:
prove usefulness + trust

---

## Phase 2 — Seller Assistance

* shared seller evaluator for dominated listing detection
* portable advisory signals for Blizzard Auction House and supported addon sell
  UIs
* shared seller sidecar for explanation and comparisons
* explicit manual price-fill controls if technically safe
* lightweight caching
* optional historical pricing

Goal:
support casual sellers

---

## Phase 3 — Expanded Ontology

* safe gear equivalence
* profession ecosystem coverage
* more consumable families
* optional community-maintained ontology

Goal:
broader utility without trust collapse

---

## Phase 4 — Optional Ecosystem Integration

Potential:

* Oribos Exchange integration
* TSM compatibility layer
* external ontology tooling

NOT required for core addon value.

---

# Engineering Guidance for Codex Agent

Prioritize:

* modular ontology system
* UI experimentation
* explainability
* conservative recommendations
* low runtime overhead

Avoid:

* premature AI systems
* complex ranking algorithms
* large UI frameworks
* market-wide scans
* speculative architecture

The addon should feel:

* calm
* trustworthy
* lightweight
* informative
* non-goblin-oriented

Not:

* like a financial terminal
* like TSM-lite
* like an automation engine.
