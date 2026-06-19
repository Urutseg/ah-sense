local _, ns = ...

local Tooltip = {}
ns.Tooltip = Tooltip

local function AddHintLine(tooltip, itemID)
    if not AhSenseDB or AhSenseDB.enabled == false or not ns.Util.IsAuctionHouseContext() then
        return
    end

    local hint = ns.Recommendations.GetPassiveHint(itemID)
    if not hint then
        return
    end

    tooltip:AddLine("|cff7fbfffAH Sense:|r " .. hint, 0.75, 0.9, 1)
end

local function HandleTooltip(tooltip, data)
    local itemID = data and data.id
    if not itemID and tooltip.GetItem then
        local _, itemLink = tooltip:GetItem()
        itemID = ns.Util.ItemIDFromLink(itemLink)
    end

    if itemID then
        AddHintLine(tooltip, itemID)
    end
end

local module = {}

function module:OnPlayerLogin()
    if TooltipDataProcessor and Enum and Enum.TooltipDataType and Enum.TooltipDataType.Item then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, HandleTooltip)
        return
    end

    if GameTooltip and GameTooltip.HookScript then
        GameTooltip:HookScript("OnTooltipSetItem", function(tooltip)
            HandleTooltip(tooltip)
        end)
    end
end

ns.RegisterModule("Tooltip", module)
