local _, ns = ...

ns.Ontology.AddGroup("algari-healing-potions", {
    category = "consumable_family",
    confidence = "tier1",
    rationale = "Same healing potion across quality ranks",
    hint = "Comparable consumables available",
    items = {
        {
            itemID = 211878,
            name = "Algari Healing Potion",
        },
        {
            itemID = 211879,
            name = "Algari Healing Potion",
        },
        {
            itemID = 211880,
            name = "Algari Healing Potion",
        },
    },
})

ns.Ontology.AddGroup("bountiful-phials", {
    category = "consumable_family",
    confidence = "tier1",
    rationale = "Same phial family and utility profile",
    hint = "Comparable phials available",
    items = {
        {
            itemID = 212314,
            name = "Phial of Bountiful Seasons",
        },
        {
            itemID = 212315,
            name = "Phial of Bountiful Seasons",
        },
        {
            itemID = 212316,
            name = "Phial of Bountiful Seasons",
        },
    },
})
