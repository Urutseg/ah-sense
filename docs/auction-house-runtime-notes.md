# Auction House Runtime Notes

These notes capture live-client Auction House behavior that is easy to forget
when working from static item data or generic item links.

## Item Keys And Item Levels

For crafted profession equipment and other quality-tiered items, the Auction
House distinguishes variants by `itemKey.itemLevel`, not by the generic item ID
alone. Generic item links such as `item:239643` may resolve to a low or default
version and are not reliable for comparing quality tiers.

Observed Retail browse result shape:

```lua
{
    itemKey = {
        itemID = 239643,
        itemLevel = 186,
        itemSuffix = 0,
        battlePetSpeciesID = 0,
    },
    totalQuantity = 2,
    minPrice = 98000000,
    containsOwnerItem = false,
}
```

Implications:

- Cache AH prices by `itemID:itemLevel` when an item-key level exists.
- Query known variants as item keys, not only as bare item IDs.
- Show variant labels using AH item level, for example
  `Bright Linen Enchanting Hat iLvl 186`.
- Do not infer variant item levels from Battle.net preview level, required
  level, quality name, or chat-link display text unless the value has been
  confirmed against live AH results.

For the Midnight enchanting headwear group, the live AH rows confirmed these
variant item levels:

```lua
{ itemID = 239643, name = "Bright Linen Enchanting Hat", itemLevels = { 180, 186, 192, 199, 206 } }
{ itemID = 239637, name = "Elegant Artisan's Enchanting Hat", itemLevels = { 212, 218, 225, 232, 239 } }
```

## Browse Results And Price Caching

`C_AuctionHouse.GetBrowseResults()` can provide usable prices through
`result.minPrice`, but it does not necessarily include a hyperlink or complete
tooltip payload. Treat the `itemKey` as the durable identity and preserve it in
the cache for later UI rendering.

Category browsing can return unrelated items. AhSense should only cache browse
results when either:

- the exact item key is pending from the current targeted request, or
- the item ID belongs to the currently requested recommendation group.

This keeps normal AH browsing from turning the addon into a broad scanner or
polluting the comparison cache with unrelated rows.

## Tooltips For Item-Key Variants

Do not use `GameTooltip:SetHyperlink()` with a generic item link for item-level
variants. It can display the wrong quality tier. Also do not synthesize a fake
metadata tooltip; if the addon cannot render the real item-key tooltip, hiding
the tooltip is more honest than showing partial or misleading item data.

The comparison panel should try real item-key tooltip paths, currently:

```lua
GameTooltip:SetItemKey(itemKey)
GameTooltip:SetItemKey(itemKey.itemID, itemKey.itemLevel, itemKey.itemSuffix or 0, itemKey.battlePetSpeciesID or 0)
GameTooltip:SetItemKey(itemKey.itemID, itemKey.itemLevel)
```

On modern Retail clients, also try tooltip-data processing when available:

```lua
local tooltipInfo = C_TooltipInfo.GetItemKey(itemKey)
TooltipUtil.SurfaceArgs(tooltipInfo)
GameTooltip:ProcessInfo(tooltipInfo)
```

Accept a tooltip attempt only when it succeeds and `GameTooltip:NumLines() > 0`.
If all item-key tooltip attempts fail, hide the tooltip for that variant rather
than falling back to generic item metadata.

## Useful In-Game Probes

When item-level or tooltip behavior is uncertain, collect live data from the AH
instead of guessing from static sources.

Dump a browse result:

```lua
/dump C_AuctionHouse.GetBrowseResults()[5]
```

Dump only the item key:

```lua
/dump C_AuctionHouse.GetBrowseResults()[5].itemKey
```

Check direct item-key tooltip rendering:

```lua
/run local k=C_AuctionHouse.GetBrowseResults()[5].itemKey; GameTooltip:SetOwner(UIParent,"ANCHOR_CURSOR"); GameTooltip:ClearLines(); local ok,err=pcall(function() GameTooltip:SetItemKey(k) end); print("SetItemKey table", ok, err, GameTooltip:NumLines()); GameTooltip:Show()
```

Check argument-form item-key tooltip rendering:

```lua
/run local k=C_AuctionHouse.GetBrowseResults()[5].itemKey; GameTooltip:SetOwner(UIParent,"ANCHOR_CURSOR"); GameTooltip:ClearLines(); local ok,err=pcall(function() GameTooltip:SetItemKey(k.itemID,k.itemLevel,k.itemSuffix,k.battlePetSpeciesID) end); print("SetItemKey args", ok, err, GameTooltip:NumLines()); GameTooltip:Show()
```

If those fail on a future Retail build, inspect `C_TooltipInfo` helpers in-game
before changing addon behavior.

## Smoke Test Checklist

For item-level variant groups:

- Open the AH and browse or search until the real rows are visible.
- Run `/ahs <itemID>` for one item in the group.
- Confirm the panel lists all expected item-level variants.
- Confirm prices appear for rows that have live AH results.
- Hover several rows and verify the tooltip item level and stats match the AH
  row tooltip.
- Click behavior must not open or insert a generic wrong-tier item link. If no
  exact link is available, doing nothing is acceptable.
