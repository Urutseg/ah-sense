local _, ns = ...

local Ontology = {
    entries = {},
    groups = {},
    confidence = {
        tier1 = {
            passiveHintEligible = true,
            label = "High confidence",
        },
        tier2 = {
            passiveHintEligible = false,
            label = "Medium confidence",
        },
    },
}

ns.Ontology = Ontology

local function NormalizeEntry(itemID, entry)
    entry.itemID = itemID
    entry.alternatives = entry.alternatives or {}
    entry.confidence = entry.confidence or "tier1"
    entry.rationale = entry.rationale or "Evidence-backed alternative"
    return entry
end

function Ontology.AddEntry(itemID, entry)
    if type(itemID) ~= "number" or type(entry) ~= "table" then
        return
    end

    Ontology.entries[itemID] = NormalizeEntry(itemID, entry)
end

function Ontology.AddGroup(groupID, group)
    if type(groupID) ~= "string" or type(group) ~= "table" then
        return
    end

    group.id = groupID
    group.confidence = group.confidence or "tier1"
    group.rationale = group.rationale or "Comparable utility"
    group.items = group.items or {}
    Ontology.groups[groupID] = group

    for _, item in ipairs(group.items) do
        local itemID = item.itemID
        if itemID then
            local alternatives = {}
            for _, other in ipairs(group.items) do
                if other.itemID and other.itemID ~= itemID then
                    table.insert(alternatives, {
                        itemID = other.itemID,
                        name = other.name,
                        rationale = other.rationale or group.rationale,
                        confidence = other.confidence or group.confidence,
                        groupID = groupID,
                    })
                end
            end

            Ontology.AddEntry(itemID, {
                name = item.name,
                category = group.category,
                confidence = item.confidence or group.confidence,
                rationale = item.rationale or group.rationale,
                hint = group.hint,
                alternatives = alternatives,
                groupID = groupID,
            })
        end
    end
end

function Ontology.GetEntry(itemID)
    return Ontology.entries[itemID]
end

function Ontology.GetAlternatives(itemID)
    local entry = Ontology.GetEntry(itemID)
    if not entry then
        return {}
    end

    return ns.Util.CopyList(entry.alternatives)
end

function Ontology.IsPassiveEligible(entryOrAlternative)
    if not entryOrAlternative then
        return false
    end

    local confidence = Ontology.confidence[entryOrAlternative.confidence]
    return confidence and confidence.passiveHintEligible == true
end
