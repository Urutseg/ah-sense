local _, ns = ...

local AuctionHouse = {
    cache = {},
    pending = {},
    lastQueryAt = 0,
}

ns.AuctionHouse = AuctionHouse

local function CanQuery()
    return C_AuctionHouse and C_AuctionHouse.SearchForItemKeys
end

local function MakeItemKey(itemID)
    if C_AuctionHouse and C_AuctionHouse.MakeItemKey then
        local ok, itemKey = pcall(C_AuctionHouse.MakeItemKey, itemID)
        if ok and itemKey then
            return itemKey
        end
    end

    return { itemID = itemID }
end

local function ItemIDFromItemKey(itemKey)
    if type(itemKey) ~= "table" then
        return nil
    end

    return itemKey.itemID or itemKey.itemId
end

local function AddUniqueItemID(itemIDs, seen, itemID)
    if type(itemID) ~= "number" or seen[itemID] then
        return
    end

    seen[itemID] = true
    table.insert(itemIDs, itemID)
end

function AuctionHouse.GetCachedPrice(itemID)
    local cached = AuctionHouse.cache[itemID]
    return cached and cached.price or nil
end

function AuctionHouse.RequestAlternatives(itemID)
    if not CanQuery() then
        return false, "Auction House data is unavailable"
    end

    local now = GetTime and GetTime() or 0
    if now - AuctionHouse.lastQueryAt < ns.Config.queryCooldownSeconds then
        return false, "Auction House query cooldown active"
    end

    local alternativeIDs = ns.Recommendations.GetAlternativeItemIDs(itemID)
    if #alternativeIDs == 0 then
        return false, "No known alternatives"
    end

    local itemIDs = {}
    local seen = {}
    AddUniqueItemID(itemIDs, seen, itemID)
    for _, alternativeID in ipairs(alternativeIDs) do
        AddUniqueItemID(itemIDs, seen, alternativeID)
    end

    local keys = {}
    for index, alternativeID in ipairs(itemIDs) do
        if index > ns.Config.maxQueryItems then
            break
        end
        table.insert(keys, MakeItemKey(alternativeID))
    end

    if #keys == 0 then
        return false, "No queryable item keys"
    end

    AuctionHouse.pending[itemID] = true
    AuctionHouse.lastQueryAt = now

    local ok = pcall(C_AuctionHouse.SearchForItemKeys, keys, {}, false)
    if not ok then
        AuctionHouse.pending[itemID] = nil
        return false, "Auction House query failed"
    end

    return true
end

function AuctionHouse.RecordCommodityPrice(itemID, price)
    if type(itemID) ~= "number" or type(price) ~= "number" then
        return
    end

    AuctionHouse.cache[itemID] = {
        price = price,
        updatedAt = GetTime and GetTime() or 0,
    }

    if ns.ComparisonPanel and ns.ComparisonPanel.Refresh then
        ns.ComparisonPanel.Refresh()
    end
end

local module = {}

function module:OnRegister()
    ns.events:RegisterEvent("COMMODITY_SEARCH_RESULTS_UPDATED")
    ns.events:RegisterEvent("ITEM_SEARCH_RESULTS_UPDATED")
end

function module:COMMODITY_SEARCH_RESULTS_UPDATED(itemID)
    if not C_AuctionHouse or not C_AuctionHouse.GetCommoditySearchResultsQuantity or not C_AuctionHouse.GetCommoditySearchResultInfo then
        return
    end

    local quantity = C_AuctionHouse.GetCommoditySearchResultsQuantity(itemID)
    if not quantity or quantity <= 0 then
        return
    end

    local result = C_AuctionHouse.GetCommoditySearchResultInfo(itemID, 1)
    if result and result.unitPrice then
        AuctionHouse.RecordCommodityPrice(itemID, result.unitPrice)
    end
end

function module:ITEM_SEARCH_RESULTS_UPDATED(itemKey)
    if not C_AuctionHouse or not C_AuctionHouse.GetItemSearchResultsQuantity or not C_AuctionHouse.GetItemSearchResultInfo then
        return
    end

    local itemID = ItemIDFromItemKey(itemKey)
    if not itemID then
        return
    end

    local quantity = C_AuctionHouse.GetItemSearchResultsQuantity(itemKey)
    if not quantity or quantity <= 0 then
        return
    end

    local lowestPrice
    for index = 1, quantity do
        local result = C_AuctionHouse.GetItemSearchResultInfo(itemKey, index)
        local price = result and (result.buyoutAmount or result.minPrice)
        if price and price > 0 and (not lowestPrice or price < lowestPrice) then
            lowestPrice = price
        end
    end

    if lowestPrice then
        AuctionHouse.RecordCommodityPrice(itemID, lowestPrice)
    end
end

ns.RegisterModule("AuctionHouse", module)
