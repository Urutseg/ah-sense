local _, ns = ...

local RecommendationService = {}
ns.Recommendations = RecommendationService

function RecommendationService.GetForItem(itemID)
    if not AhSenseDB or AhSenseDB.enabled == false then
        return nil
    end

    local entry = ns.Ontology.GetEntry(itemID)
    if not entry then
        return nil
    end

    return {
        itemID = itemID,
        name = entry.name,
        category = entry.category,
        confidence = entry.confidence,
        rationale = entry.rationale,
        hint = entry.hint,
        alternatives = ns.Util.CopyList(entry.alternatives),
    }
end

function RecommendationService.GetPassiveHint(itemID)
    if not AhSenseDB or AhSenseDB.passiveHints == false then
        return nil
    end

    local recommendation = RecommendationService.GetForItem(itemID)
    if not recommendation or not ns.Ontology.IsPassiveEligible(recommendation) then
        return nil
    end

    local count = #recommendation.alternatives
    if count == 0 then
        return nil
    end

    return recommendation.hint or "Alternative available"
end

function RecommendationService.GetAlternativeItemIDs(itemID)
    local recommendation = RecommendationService.GetForItem(itemID)
    local itemIDs = {}
    if not recommendation then
        return itemIDs
    end

    for _, alternative in ipairs(recommendation.alternatives) do
        if alternative.itemID and alternative.itemID ~= itemID then
            table.insert(itemIDs, alternative.itemID)
        end
    end

    return itemIDs
end
