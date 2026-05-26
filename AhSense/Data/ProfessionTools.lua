local _, ns = ...

ns.Ontology.AddGroup("midnight-herbalism-epic-headwear", {
    category = "profession_tool",
    confidence_tier = "tier1",
    passive_eligible = false,
    rationale = "Same Midnight Herbalism profession headwear role",
    hint = "Comparable profession item available",
    items = {
        {
            itemID = 246515,
            name = "Super Elegant Artisan's Herbalism Hat",
        },
        {
            itemID = 267060,
            name = "Thalassian Herbalist's Cowl",
        },
    },
})
