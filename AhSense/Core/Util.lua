local _, ns = ...

local Util = {}
ns.Util = Util

function Util.CopyList(values)
    local copy = {}
    if not values then
        return copy
    end

    for index, value in ipairs(values) do
        copy[index] = value
    end
    return copy
end

function Util.CopyTable(value)
    local copy = {}
    if type(value) ~= "table" then
        return copy
    end

    for key, item in pairs(value) do
        copy[key] = item
    end
    return copy
end

function Util.ItemIDFromLink(itemLink)
    if type(itemLink) ~= "string" then
        return nil
    end

    local itemID = itemLink:match("item:(%d+)")
    return itemID and tonumber(itemID) or nil
end

function Util.FormatMoney(copper)
    if type(copper) ~= "number" then
        return "-"
    end

    local sign = ""
    if copper < 0 then
        sign = "-"
        copper = math.abs(copper)
    end

    if GetMoneyString then
        return sign .. GetMoneyString(copper, true)
    end

    local gold = math.floor(copper / 10000)
    local silver = math.floor((copper % 10000) / 100)
    local copperOnly = copper % 100
    return string.format("%s%dg %ds %dc", sign, gold, silver, copperOnly)
end

function Util.ItemLabel(itemID, fallbackName)
    if fallbackName and fallbackName ~= "" then
        return fallbackName
    end

    local itemInfo = C_Item and C_Item.GetItemInfo and C_Item.GetItemInfo(itemID)
    if itemInfo then
        return itemInfo
    end

    return "Item " .. tostring(itemID)
end

function Util.IsAuctionHouseContext()
    return AuctionHouseFrame and AuctionHouseFrame:IsShown()
end
