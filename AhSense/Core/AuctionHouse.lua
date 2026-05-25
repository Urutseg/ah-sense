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

    local itemIDs = ns.Recommendations.GetAlternativeItemIDs(itemID)
    if #itemIDs == 0 then
        return false, "No known alternatives"
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
end

local module = {}

function module:OnRegister()
    ns.events:RegisterEvent("COMMODITY_SEARCH_RESULTS_UPDATED")
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

ns.RegisterModule("AuctionHouse", module)
