local _, ns = ...

-- Active-only profession equipment groups reviewed from
-- research/ontology-review/profession-equipment-equivalent-candidates.md.
-- These are practical comparison candidates, not strict substitutes.

local function AddProfessionGroup(groupID, profession, role, items)
    ns.Ontology.AddGroup(groupID, {
        category = "profession_tool",
        confidence_tier = "tier2",
        passive_eligible = false,
        rationale = "Same " .. profession .. " profession and same " .. role
            .. "; skill and secondary profession stats may differ",
        hint = "Comparable profession item available",
        items = items,
    })
end

AddProfessionGroup("midnight-fishing-profession-tool", "Fishing", "profession tool", {
    { itemID = 244711, name = "Farstrider Hobbyist Rod" },
    { itemID = 244712, name = "Sin'dorei Angler's Rod" },
})

AddProfessionGroup("midnight-alchemy-apron", "Midnight Alchemy", "apron/body profession accessory", {
    { itemID = 239641, name = "Bright Linen Alchemy Apron" },
    { itemID = 239635, name = "Elegant Artisan's Alchemy Coveralls" },
})

AddProfessionGroup("midnight-alchemy-headwear", "Midnight Alchemy", "headwear profession accessory", {
    { itemID = 244620, name = "Chemist's Cap" },
    { itemID = 244626, name = "Sin'dorei Alchemist's Hat" },
})

AddProfessionGroup("midnight-alchemy-profession-tool", "Midnight Alchemy", "profession tool", {
    { itemID = 245777, name = "Hobbyist Alchemist's Mixing Rod" },
    { itemID = 245778, name = "Sin'dorei Alchemist's Mixing Rod" },
})

AddProfessionGroup("midnight-blacksmithing-toolbox", "Midnight Blacksmithing", "toolbox profession accessory", {
    { itemID = 237948, name = "Thalassian Blacksmith's Toolbox" },
    { itemID = 237952, name = "Sun-Blessed Blacksmith's Toolbox" },
})

AddProfessionGroup("midnight-blacksmithing-apron", "Midnight Blacksmithing", "apron/body profession accessory", {
    { itemID = 244627, name = "Apprentice Smith's Apron" },
    { itemID = 244628, name = "Sin'dorei Forgemaster's Cover" },
})

AddProfessionGroup("midnight-blacksmithing-profession-tool", "Midnight Blacksmithing", "profession tool", {
    { itemID = 238013, name = "Thalassian Blacksmith's Hammer" },
    { itemID = 238018, name = "Sun-Blessed Blacksmith's Hammer" },
})

AddProfessionGroup("midnight-cooking-headwear", "Midnight Cooking", "headwear profession accessory", {
    { itemID = 239642, name = "Chef's Bright Linen Cooking Chapeau" },
    { itemID = 239636, name = "Elegant Artisan's Cooking Hat" },
})

AddProfessionGroup("midnight-cooking-profession-tool", "Midnight Cooking", "profession tool", {
    { itemID = 245779, name = "Hobbyist Rolling Pin" },
    { itemID = 245780, name = "Sin'dorei Rolling Pin" },
})

AddProfessionGroup("midnight-enchanting-headwear", "Midnight Enchanting", "headwear profession accessory", {
    { itemID = 239643, name = "Bright Linen Enchanting Hat" },
    { itemID = 239637, name = "Elegant Artisan's Enchanting Hat" },
})

AddProfessionGroup("midnight-enchanting-focus", "Midnight Enchanting", "focus profession accessory", {
    { itemID = 240956, name = "Silvermoon Focusing Shard" },
    { itemID = 240960, name = "Sin'dorei Enchanter's Crystal" },
})

AddProfessionGroup("midnight-enchanting-profession-tool", "Midnight Enchanting", "profession tool", {
    { itemID = 244175, name = "Runed Refulgent Copper Rod" },
    { itemID = 244176, name = "Runed Brilliant Silver Rod" },
})

AddProfessionGroup("midnight-engineering-handwear", "Midnight Engineering", "handwear profession accessory", {
    { itemID = 244618, name = "Tinker's Handguard" },
    { itemID = 244624, name = "Sin'dorei Engineer's Gloves" },
})

AddProfessionGroup("midnight-engineering-headwear", "Midnight Engineering", "headwear profession accessory", {
    { itemID = 244709, name = "Junker's Junk Visor" },
    { itemID = 244710, name = "Sin'dorei Headlamp" },
})

AddProfessionGroup("midnight-engineering-profession-tool", "Midnight Engineering", "profession tool", {
    { itemID = 244717, name = "Junker's Multitool" },
    { itemID = 244718, name = "Turbo-Junker's Multitool v1" },
})

AddProfessionGroup("midnight-herbalism-headwear", "Midnight Herbalism", "headwear profession accessory", {
    { itemID = 239645, name = "Bright Linen Herbalism Hat" },
    { itemID = 239639, name = "Elegant Artisan's Herbalism Hat" },
})

AddProfessionGroup("midnight-herbalism-bag", "Midnight Herbalism", "bag profession accessory", {
    { itemID = 244615, name = "Eversong Botanist's Satchel" },
    { itemID = 244621, name = "Sin'dorei Herbalist's Backpack" },
})

AddProfessionGroup("midnight-herbalism-profession-tool", "Midnight Herbalism", "profession tool", {
    { itemID = 238009, name = "Thalassian Sickle" },
    { itemID = 238014, name = "Sun-Blessed Sickle" },
})

AddProfessionGroup("midnight-inscription-eyewear", "Midnight Inscription", "eyewear profession accessory", {
    { itemID = 240953, name = "Bold Biographer's Bifocals" },
    { itemID = 240957, name = "Sin'dorei Scribe's Spectacles" },
})

AddProfessionGroup("midnight-inscription-focus", "Midnight Inscription", "focus profession accessory", {
    { itemID = 240954, name = "Fantastic Font Focuser" },
    { itemID = 240958, name = "Improved Right-Handed Magnifying Glass" },
})

AddProfessionGroup("midnight-inscription-profession-tool", "Midnight Inscription", "profession tool", {
    { itemID = 245775, name = "Hobbyist Scribe's Quill" },
    { itemID = 245776, name = "Sin'dorei Quill" },
})

AddProfessionGroup("midnight-jewelcrafting-eyewear", "Midnight Jewelcrafting", "eyewear profession accessory", {
    { itemID = 240955, name = "Silvermoon Loupes" },
    { itemID = 240959, name = "Sin'dorei Jeweler's Loupes" },
})

AddProfessionGroup("midnight-jewelcrafting-apron", "Midnight Jewelcrafting", "apron/body profession accessory", {
    { itemID = 244629, name = "Apprentice Jeweler's Apron" },
    { itemID = 244630, name = "Sin'dorei Jeweler's Cover" },
})

AddProfessionGroup("midnight-jewelcrafting-profession-tool", "Midnight Jewelcrafting", "profession tool", {
    { itemID = 244713, name = "Farstrider Clampers" },
    { itemID = 244714, name = "Sin'dorei Clampers" },
})

AddProfessionGroup("midnight-leatherworking-toolset", "Midnight Leatherworking", "toolset profession accessory", {
    { itemID = 237947, name = "Thalassian Leatherworker's Toolset" },
    { itemID = 237951, name = "Sun-Blessed Leatherworker's Toolset" },
})

AddProfessionGroup("midnight-leatherworking-smock", "Midnight Leatherworking", "smock/body profession accessory", {
    { itemID = 244619, name = "Hideworker's Cover" },
    { itemID = 244625, name = "Sin'dorei Leathershaper's Smock" },
})

AddProfessionGroup("midnight-leatherworking-profession-tool", "Midnight Leatherworking", "profession tool", {
    { itemID = 238012, name = "Thalassian Leatherworker's Knife" },
    { itemID = 238017, name = "Sun-Blessed Leatherworker's Knife" },
})

AddProfessionGroup("midnight-mining-headwear", "Midnight Mining", "headwear profession accessory", {
    { itemID = 244715, name = "Farstrider Hardhat" },
    { itemID = 244716, name = "Sin'dorei Gilded Hardhat" },
})

AddProfessionGroup("midnight-mining-bag", "Midnight Mining", "bag profession accessory", {
    { itemID = 244719, name = "Farstrider Rock Satchel" },
    { itemID = 244720, name = "Junker's Big Ol' Bag" },
})

AddProfessionGroup("midnight-mining-profession-tool", "Midnight Mining", "profession tool", {
    { itemID = 238010, name = "Thalassian Pickaxe" },
    { itemID = 238015, name = "Sun-Blessed Pickaxe" },
})

AddProfessionGroup("midnight-skinning-bag", "Midnight Skinning", "bag profession accessory", {
    { itemID = 244616, name = "Skinner's Backpack" },
    { itemID = 244622, name = "Sin'dorei Hunter's Pack" },
})

AddProfessionGroup("midnight-skinning-headwear", "Midnight Skinning", "headwear profession accessory", {
    { itemID = 244617, name = "Skinner's Cap" },
    { itemID = 244623, name = "Eversong Hunter's Headcover" },
})

AddProfessionGroup("midnight-skinning-profession-tool", "Midnight Skinning", "profession tool", {
    { itemID = 238011, name = "Thalassian Skinning Knife" },
    { itemID = 238016, name = "Sun-Blessed Skinning Knife" },
})

AddProfessionGroup("midnight-tailoring-needles", "Midnight Tailoring", "needle-set profession accessory", {
    { itemID = 237946, name = "Thalassian Needle Set" },
    { itemID = 237950, name = "Sun-Blessed Needle Set" },
})

AddProfessionGroup("midnight-tailoring-robe", "Midnight Tailoring", "robe profession accessory", {
    { itemID = 239646, name = "Bright Linen Tailoring Robe" },
    { itemID = 239640, name = "Elegant Artisan's Tailoring Robe" },
})

AddProfessionGroup("midnight-tailoring-profession-tool", "Midnight Tailoring", "profession tool", {
    { itemID = 244707, name = "Farstrider Fabric Cutters" },
    { itemID = 244708, name = "Sin'dorei Snippers" },
})
