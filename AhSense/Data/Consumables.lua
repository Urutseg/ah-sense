local _, ns = ...

ns.Ontology.AddGroup("midnight-silvermoon-health-potions", {
    category = "consumable_family",
    confidence_tier = "tier1",
    passive_eligible = false,
    rationale = "Same Midnight potion across item-level variants",
    hint = "Comparable consumables available",
    items = {
        {
            itemID = 241304,
            name = "Silvermoon Health Potion",
        },
        {
            itemID = 241305,
            name = "Silvermoon Health Potion",
        },
    },
})

ns.Ontology.AddGroup("midnight-lightfused-mana-potions", {
    category = "consumable_family",
    confidence_tier = "tier1",
    passive_eligible = false,
    rationale = "Same Midnight mana potion across item-level variants",
    hint = "Comparable consumables available",
    items = {
        {
            itemID = 241300,
            name = "Lightfused Mana Potion",
        },
        {
            itemID = 241301,
            name = "Lightfused Mana Potion",
        },
    },
})
