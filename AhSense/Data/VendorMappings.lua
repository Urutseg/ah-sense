local _, ns = ...

-- Small Tier 1 set: obvious vendor-supplied trade goods that should never need
-- speculative market interpretation.
ns.Ontology.AddEntry(3371, {
    name = "Crystal Vial",
    category = "vendor_mapping",
    confidence_tier = "tier1",
    passive_eligible = true,
    rationale = "Vendor-sold trade good",
    hint = "Vendor alternative exists",
    vendorPrice = 500,
    alternatives = {
        {
            itemID = 3371,
            name = "Crystal Vial",
            confidence_tier = "tier1",
            passive_eligible = true,
            rationale = "Available from many trade supply vendors",
            vendorPrice = 500,
        },
    },
})

ns.Ontology.AddEntry(38682, {
    name = "Enchanting Vellum",
    category = "vendor_mapping",
    confidence_tier = "tier1",
    passive_eligible = true,
    rationale = "Vendor-sold profession supply",
    hint = "Vendor alternative exists",
    vendorPrice = 900,
    alternatives = {
        {
            itemID = 38682,
            name = "Enchanting Vellum",
            confidence_tier = "tier1",
            passive_eligible = true,
            rationale = "Available from enchanting supply vendors",
            vendorPrice = 900,
        },
    },
})
