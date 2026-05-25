local _, ns = ...

ns.Ontology.AddGroup("khaz-algar-blacksmith-toolboxes", {
    category = "profession_tool",
    confidence = "tier1",
    rationale = "Same Blacksmithing accessory role",
    hint = "Comparable profession item available",
    items = {
        {
            itemID = 222487,
            name = "Proficient Blacksmith's Toolbox",
        },
        {
            itemID = 222495,
            name = "Artisan Blacksmith's Toolbox",
        },
    },
})
