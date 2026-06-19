local _, ns = ...

local Ontology = {
    entries = {},
    groups = {},
    validationErrors = {},
    confidence = {
        tier1 = {
            label = "High confidence",
        },
        tier2 = {
            label = "Medium confidence",
        },
        tier3 = {
            label = "Deferred",
        },
    },
}

ns.Ontology = Ontology

local function IsBlank(value)
    return value == nil or value == ""
end

local function AddValidationError(message)
    table.insert(Ontology.validationErrors, message)
    if ns.Debug then
        ns.Debug(message)
    end
end

local function ConfidenceTier(value)
    return value.confidence_tier or value.confidence
end

local function ValidateRequiredFields(scope, value)
    if IsBlank(value.category) then
        return false, scope .. " missing category"
    end

    local confidenceTier = ConfidenceTier(value)
    if IsBlank(confidenceTier) then
        return false, scope .. " missing confidence_tier"
    end

    if not Ontology.confidence[confidenceTier] then
        return false, scope .. " has unknown confidence_tier: " .. tostring(confidenceTier)
    end

    if IsBlank(value.rationale) then
        return false, scope .. " missing rationale"
    end

    return true
end

local function NormalizeAlternative(alternative, fallbackRationale)
    if type(alternative) ~= "table" then
        return nil
    end

    local normalized = ns.Util.CopyTable(alternative)
    normalized.confidence_tier = ConfidenceTier(normalized) or "tier2"
    normalized.confidence = normalized.confidence_tier
    normalized.passive_eligible = normalized.passive_eligible == true
    normalized.rationale = normalized.rationale or fallbackRationale
    return normalized
end

local function CopyItemKeyFields(target, source)
    if source.itemLevels then
        target.itemLevels = ns.Util.CopyList(source.itemLevels)
    end
end

local function NormalizeEntry(itemID, entry)
    entry.itemID = itemID
    entry.confidence_tier = ConfidenceTier(entry)
    entry.confidence = entry.confidence_tier
    entry.passive_eligible = entry.passive_eligible == true
    entry.alternatives = entry.alternatives or {}
    CopyItemKeyFields(entry, entry)

    for index, alternative in ipairs(entry.alternatives) do
        entry.alternatives[index] = NormalizeAlternative(alternative, entry.rationale)
    end

    return entry
end

function Ontology.AddEntry(itemID, entry)
    if type(itemID) ~= "number" or type(entry) ~= "table" then
        return
    end

    local isValid, reason = ValidateRequiredFields("Entry " .. tostring(itemID), entry)
    if not isValid then
        AddValidationError(reason)
        return false, reason
    end

    Ontology.entries[itemID] = NormalizeEntry(itemID, entry)
    return true
end

function Ontology.AddGroup(groupID, group)
    if type(groupID) ~= "string" or type(group) ~= "table" then
        return
    end

    local isValid, reason = ValidateRequiredFields("Group " .. groupID, group)
    if not isValid then
        AddValidationError(reason)
        return false, reason
    end

    group.id = groupID
    group.confidence_tier = ConfidenceTier(group)
    group.confidence = group.confidence_tier
    group.passive_eligible = group.passive_eligible == true
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
                        confidence_tier = other.confidence_tier or other.confidence or group.confidence_tier,
                        passive_eligible = (other.passive_eligible == true or group.passive_eligible == true)
                            and (other.confidence_tier or other.confidence or group.confidence_tier) == "tier1",
                        groupID = groupID,
                        itemLevels = other.itemLevels,
                    })
                end
            end

            Ontology.AddEntry(itemID, {
                name = item.name,
                category = group.category,
                confidence_tier = item.confidence_tier or item.confidence or group.confidence_tier,
                passive_eligible = (item.passive_eligible == true or group.passive_eligible == true)
                    and (item.confidence_tier or item.confidence or group.confidence_tier) == "tier1",
                rationale = item.rationale or group.rationale,
                hint = group.hint,
                alternatives = alternatives,
                groupID = groupID,
                itemLevels = item.itemLevels,
            })
        end
    end

    return true
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

    return entryOrAlternative.confidence_tier == "tier1" and entryOrAlternative.passive_eligible == true
end
