local _, ns = ...

-- Tier 1 vendor-supplied reagents with explicit vendor evidence. Midnight rows
-- are curated from normal recipe reagents and modified-crafting category items
-- in research/ontology-review/vendor-reagent-candidates.md.

local function AddVendorMapping(itemID, name, vendorPrice, rationale)
    ns.Ontology.AddEntry(itemID, {
        name = name,
        category = "vendor_mapping",
        confidence_tier = "tier1",
        passive_eligible = true,
        rationale = rationale,
        hint = "Vendor alternative exists",
        vendorPrice = vendorPrice,
        alternatives = {
            {
                itemID = itemID,
                name = name,
                confidence_tier = "tier1",
                passive_eligible = true,
                rationale = rationale,
                vendorPrice = vendorPrice,
            },
        },
    })
end

-- Evergreen profession supplies.
AddVendorMapping(3371, "Crystal Vial", 500, "Available from many trade supply vendors")
AddVendorMapping(38682, "Enchanting Vellum", 1000, "Available from enchanting supply vendors")

-- Midnight profession vendor reagents.
AddVendorMapping(240990, "Sunglass Vial", 27500, "Purchased from tradeskill vendors at lower quality")
AddVendorMapping(240991, "Sunglass Vial", 27500, "Purchased from tradeskill vendors")
AddVendorMapping(243060, "Luminant Flux", 3000, "Sold by Blacksmithing vendors")
AddVendorMapping(242642, "Thalassian Herbs", 1225, "Sold by vendors for Quel'Thalas cooking recipes")
AddVendorMapping(242645, "Ripened Vegetable Assortment", 1125, "Sold by vendors for Quel'Thalas cooking recipes")
AddVendorMapping(242646, "Pouch of Spices", 1075, "Sold by vendors for Quel'Thalas cooking recipes")
AddVendorMapping(242641, "Cooking Spirits", 1010, "Sold by vendors for Quel'Thalas cooking recipes")
AddVendorMapping(242647, "Tavern Fixings", 1000, "Sold by vendors for Quel'Thalas cooking recipes")
AddVendorMapping(242643, "A Big Ol' Stick of Butter", 860, "Sold by vendors for Quel'Thalas cooking recipes")
AddVendorMapping(242644, "Mana-Wyrm Essence", 770, "Sold by vendors for Quel'Thalas cooking recipes")
AddVendorMapping(253302, "Malleable Wireframe", 2105, "Can be purchased from vendors for Engineering recipes")
AddVendorMapping(253303, "Pile of Junk", 2105, "Can be purchased from vendors for Engineering recipes")
AddVendorMapping(245882, "Thalassian Songwater", 3595, "Can be purchased from vendors for Inscription recipes")
AddVendorMapping(245881, "Lexicologist's Vellum", 2105, "Can be purchased from vendors for Inscription recipes")
AddVendorMapping(251691, "Embroidery Floss", 700, "Sold by Tailoring vendors")
AddVendorMapping(251665, "Silverleaf Thread", 700, "Sold by Tailoring vendors")
