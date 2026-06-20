local _, ns = ...

local AuctionHouse = {
    cache = {},
    pending = {},
    queryHistory = {},
    lastQueryAt = 0,
    lastRequest = nil,
}

ns.AuctionHouse = AuctionHouse

local function CanQuery()
    return C_AuctionHouse and C_AuctionHouse.SearchForItemKeys
end

local function ItemIDFromItemKey(itemKey)
    if type(itemKey) ~= "table" then
        return nil
    end

    return itemKey.itemID or itemKey.itemId
end

local function ItemLevelFromItemKey(itemKey)
    if type(itemKey) ~= "table" then
        return nil
    end

    return itemKey.itemLevel
end

local function CacheKey(value, itemLevel)
    if type(value) == "table" then
        local itemID = ItemIDFromItemKey(value)
        local level = ItemLevelFromItemKey(value)
        if itemID and level then
            return tostring(itemID) .. ":" .. tostring(level)
        end

        return itemID and tostring(itemID) or nil
    end

    if type(value) == "number" and itemLevel then
        return tostring(value) .. ":" .. tostring(itemLevel)
    end

    return type(value) == "number" and tostring(value) or nil
end

local function QueryLabel(queryItem)
    if queryItem.itemLevel then
        return tostring(queryItem.itemID) .. ":" .. tostring(queryItem.itemLevel)
    end

    return tostring(queryItem.itemID)
end

local function MakeItemKey(queryItem)
    local itemID = type(queryItem) == "table" and queryItem.itemID or queryItem
    local itemLevel = type(queryItem) == "table" and queryItem.itemLevel or nil

    if C_AuctionHouse and C_AuctionHouse.MakeItemKey then
        local ok, itemKey = pcall(C_AuctionHouse.MakeItemKey, itemID, itemLevel, 0, 0)
        if ok and itemKey then
            return itemKey
        end

        ok, itemKey = pcall(C_AuctionHouse.MakeItemKey, itemID, itemLevel)
        if ok and itemKey then
            return itemKey
        end
    end

    return { itemID = itemID, itemLevel = itemLevel, itemSuffix = 0, battlePetSpeciesID = 0 }
end

local function AddQueryItem(queryItems, seen, item, itemLevel)
    if not item or type(item.itemID) ~= "number" then
        return
    end

    local key = CacheKey(item.itemID, itemLevel)
    if not key or seen[key] then
        return
    end

    seen[key] = true
    table.insert(queryItems, {
        itemID = item.itemID,
        name = item.name,
        itemLevel = itemLevel,
    })
end

local function AddQueryItemsForRecommendationItem(queryItems, seen, item)
    if type(item) ~= "table" then
        return
    end

    if item.itemLevels and #item.itemLevels > 0 then
        for _, itemLevel in ipairs(item.itemLevels) do
            AddQueryItem(queryItems, seen, item, itemLevel)
        end
        return
    end

    AddQueryItem(queryItems, seen, item)
end

local function LimitQueryItems(queryItems)
    local limited = {}
    for index, queryItem in ipairs(queryItems) do
        if index > ns.Config.maxQueryItems then
            break
        end

        table.insert(limited, queryItem)
    end

    return limited
end

local function Debug(message)
    ns.Debug("AuctionHouse: " .. tostring(message))
end

local function JoinQueryItems(queryItems)
    local parts = {}
    for _, queryItem in ipairs(queryItems or {}) do
        table.insert(parts, QueryLabel(queryItem))
    end

    return table.concat(parts, ", ")
end

local function IsCacheFresh(cached, now)
    if not cached or type(cached.updatedAt) ~= "number" then
        return false
    end

    return now - cached.updatedAt <= ns.Config.priceCacheTtlSeconds
end

local function GetFreshCachedEntry(value, itemLevel)
    local key = CacheKey(value, itemLevel)
    local cached = key and AuctionHouse.cache[key] or nil
    if not IsCacheFresh(cached, GetTime and GetTime() or 0) then
        return nil
    end

    return cached
end

local function PruneExpiredCache(now)
    for key, cached in pairs(AuctionHouse.cache) do
        if not IsCacheFresh(cached, now) then
            AuctionHouse.cache[key] = nil
        end
    end
end

local function HasFreshPrices(queryItems, now)
    if #queryItems == 0 then
        return false
    end

    for _, queryItem in ipairs(queryItems) do
        local cached = AuctionHouse.cache[CacheKey(queryItem.itemID, queryItem.itemLevel)]
        if not IsCacheFresh(cached, now) then
            return false
        end
    end

    return true
end

local function HasPendingQuery(queryItems)
    for _, queryItem in ipairs(queryItems) do
        local key = CacheKey(queryItem.itemID, queryItem.itemLevel)
        if key and AuctionHouse.pending[key] then
            return true
        end
    end

    return false
end

local function PruneQueryHistory(now)
    local window = ns.Config.queryThrottleWindowSeconds
    local writeIndex = 1
    for readIndex = 1, #AuctionHouse.queryHistory do
        local timestamp = AuctionHouse.queryHistory[readIndex]
        if now - timestamp <= window then
            AuctionHouse.queryHistory[writeIndex] = timestamp
            writeIndex = writeIndex + 1
        end
    end

    for index = writeIndex, #AuctionHouse.queryHistory do
        AuctionHouse.queryHistory[index] = nil
    end
end

local function CanStartQuery(now)
    if now - AuctionHouse.lastQueryAt < ns.Config.queryCooldownSeconds then
        return false, "Auction House query cooldown active"
    end

    PruneQueryHistory(now)
    if #AuctionHouse.queryHistory >= ns.Config.maxQueriesPerThrottleWindow then
        return false, "Auction House query throttle active"
    end

    return true
end

local function RecordQueryStart(now)
    AuctionHouse.lastQueryAt = now
    table.insert(AuctionHouse.queryHistory, now)
end

local function TrackRequest(rootItemID, queryItems, options)
    options = options or {}
    local request = {
        rootItemID = rootItemID,
        queryItems = ns.Util.CopyList(queryItems),
        pending = {},
        itemIDs = {},
        requestedAt = GetTime and GetTime() or 0,
        fromCache = options.fromCache == true,
        reusedPending = options.reusedPending == true,
    }

    for _, queryItem in ipairs(queryItems) do
        request.itemIDs[queryItem.itemID] = true
        local key = CacheKey(queryItem.itemID, queryItem.itemLevel)
        if key then
            if options.markPending then
                request.pending[key] = true
                AuctionHouse.pending[key] = true
            elseif AuctionHouse.pending[key] then
                request.pending[key] = true
            end
        end
    end

    AuctionHouse.lastRequest = request
    if options.markPending then
        Debug("querying item keys: " .. JoinQueryItems(queryItems))
    elseif options.fromCache then
        Debug("using cached item keys: " .. JoinQueryItems(queryItems))
    elseif options.reusedPending then
        Debug("reusing pending item-key request: " .. JoinQueryItems(queryItems))
    end
end

local function ClearPending(value)
    local key = CacheKey(value)
    if not key then
        return
    end

    AuctionHouse.pending[key] = nil

    local request = AuctionHouse.lastRequest
    if request and request.pending then
        request.pending[key] = nil
    end
end

local function NotifyPriceUpdate()
    if ns.ComparisonPanel and ns.ComparisonPanel.Refresh then
        ns.ComparisonPanel.Refresh()
    end
end

local function IsPendingItem(value)
    local key = CacheKey(value)
    return key and AuctionHouse.pending[key] == true
end

local function IsRequestedItemID(itemID)
    local request = AuctionHouse.lastRequest
    return request and request.itemIDs and request.itemIDs[itemID] == true
end

function AuctionHouse.GetCachedPrice(value, itemLevel)
    local cached = GetFreshCachedEntry(value, itemLevel)
    return cached and cached.price or nil
end

function AuctionHouse.GetCachedEntry(value, itemLevel)
    return GetFreshCachedEntry(value, itemLevel)
end

function AuctionHouse.GetLastRequestStatus(itemID)
    local request = AuctionHouse.lastRequest
    if not request or request.rootItemID ~= itemID then
        return nil
    end

    local found = 0
    local pending = 0
    for _, queryItem in ipairs(request.queryItems) do
        local key = CacheKey(queryItem.itemID, queryItem.itemLevel)
        if key and IsCacheFresh(AuctionHouse.cache[key], GetTime and GetTime() or 0) then
            found = found + 1
        elseif key and request.pending[key] then
            pending = pending + 1
        end
    end

    return {
        total = #request.queryItems,
        found = found,
        pending = pending,
        requestedAt = request.requestedAt,
        fromCache = request.fromCache,
        reusedPending = request.reusedPending,
    }
end

function AuctionHouse.RequestAlternatives(itemID)
    if not CanQuery() then
        return false, "Auction House data is unavailable"
    end

    local now = GetTime and GetTime() or 0
    PruneExpiredCache(now)

    local recommendation = ns.Recommendations.GetForItem(itemID)
    if not recommendation or #recommendation.alternatives == 0 then
        return false, "No known alternatives"
    end

    local queryItems = {}
    local seen = {}
    AddQueryItemsForRecommendationItem(queryItems, seen, recommendation)
    for _, alternative in ipairs(recommendation.alternatives) do
        AddQueryItemsForRecommendationItem(queryItems, seen, alternative)
    end
    queryItems = LimitQueryItems(queryItems)

    local keys = {}
    for _, queryItem in ipairs(queryItems) do
        table.insert(keys, MakeItemKey(queryItem))
    end

    if #keys == 0 then
        return false, "No queryable item keys"
    end

    if HasFreshPrices(queryItems, now) then
        TrackRequest(itemID, queryItems, { fromCache = true })
        return false, "Using recent AH prices"
    end

    if HasPendingQuery(queryItems) then
        TrackRequest(itemID, queryItems, { reusedPending = true })
        return false, "Auction House query already pending"
    end

    local canStart, throttleMessage = CanStartQuery(now)
    if not canStart then
        return false, throttleMessage
    end

    TrackRequest(itemID, queryItems, { markPending = true })
    RecordQueryStart(now)

    local ok = pcall(C_AuctionHouse.SearchForItemKeys, keys, {})
    if not ok then
        for _, queryItem in ipairs(queryItems) do
            ClearPending(queryItem)
        end
        return false, "Auction House query failed"
    end

    return true
end

function AuctionHouse.ClearCache()
    AuctionHouse.cache = {}
    AuctionHouse.pending = {}
    AuctionHouse.lastRequest = nil
end

function AuctionHouse.PruneCache()
    PruneExpiredCache(GetTime and GetTime() or 0)
end

function AuctionHouse.RecordPrice(value, price, source, link)
    local key = CacheKey(value)
    local itemID = type(value) == "table" and ItemIDFromItemKey(value) or value
    if not key or type(itemID) ~= "number" or type(price) ~= "number" then
        return
    end

    ClearPending(value)
    AuctionHouse.cache[key] = {
        itemID = itemID,
        itemLevel = type(value) == "table" and ItemLevelFromItemKey(value) or nil,
        price = price,
        updatedAt = GetTime and GetTime() or 0,
        source = source,
        link = link,
        itemKey = type(value) == "table" and ns.Util.CopyTable(value) or nil,
    }

    Debug("cached " .. key .. " at " .. ns.Util.FormatMoney(price) .. " from " .. tostring(source))
    NotifyPriceUpdate()
end

AuctionHouse.RecordCommodityPrice = AuctionHouse.RecordPrice

local function ReadBrowseResults()
    if not C_AuctionHouse or not C_AuctionHouse.GetBrowseResults then
        return
    end

    local results = C_AuctionHouse.GetBrowseResults()
    if type(results) ~= "table" then
        Debug("browse results unavailable")
        return
    end

    Debug("browse results received: " .. tostring(#results))
    for _, result in ipairs(results) do
        local price = result and result.minPrice
        local itemID = result and result.itemKey and ItemIDFromItemKey(result.itemKey)
        local link = result and (result.itemLink or result.link or result.hyperlink)
        if result and result.itemKey and price and price > 0 and (IsPendingItem(result.itemKey) or IsRequestedItemID(itemID)) then
            AuctionHouse.RecordPrice(result.itemKey, price, "browse", link)
        end
    end
end

local module = {}

function module:OnRegister()
    ns.events:RegisterEvent("AUCTION_HOUSE_BROWSE_RESULTS_UPDATED")
    ns.events:RegisterEvent("AUCTION_HOUSE_BROWSE_RESULTS_ADDED")
    ns.events:RegisterEvent("COMMODITY_SEARCH_RESULTS_UPDATED")
    ns.events:RegisterEvent("ITEM_SEARCH_RESULTS_UPDATED")
    ns.events:RegisterEvent("AUCTION_HOUSE_CLOSED")
end

function module:AUCTION_HOUSE_BROWSE_RESULTS_UPDATED()
    ReadBrowseResults()
end

function module:AUCTION_HOUSE_BROWSE_RESULTS_ADDED()
    ReadBrowseResults()
end

function module:COMMODITY_SEARCH_RESULTS_UPDATED(itemID)
    if not C_AuctionHouse or not C_AuctionHouse.GetCommoditySearchResultInfo then
        return
    end

    if not IsPendingItem(itemID) then
        return
    end

    local quantity
    if C_AuctionHouse.GetNumCommoditySearchResults then
        quantity = C_AuctionHouse.GetNumCommoditySearchResults(itemID)
    elseif C_AuctionHouse.GetCommoditySearchResultsQuantity then
        quantity = C_AuctionHouse.GetCommoditySearchResultsQuantity(itemID)
    end

    if not quantity or quantity <= 0 then
        return
    end

    local result = C_AuctionHouse.GetCommoditySearchResultInfo(itemID, 1)
    if result and result.unitPrice then
        AuctionHouse.RecordPrice(itemID, result.unitPrice, "commodity-search", result.itemLink or result.link or result.hyperlink)
    end
end

function module:ITEM_SEARCH_RESULTS_UPDATED(itemKey)
    if not C_AuctionHouse or not C_AuctionHouse.GetItemSearchResultInfo then
        return
    end

    local itemID = ItemIDFromItemKey(itemKey)
    if not itemID then
        return
    end

    if not IsPendingItem(itemKey) then
        return
    end

    local quantity
    if C_AuctionHouse.GetNumItemSearchResults then
        quantity = C_AuctionHouse.GetNumItemSearchResults(itemKey)
    elseif C_AuctionHouse.GetItemSearchResultsQuantity then
        quantity = C_AuctionHouse.GetItemSearchResultsQuantity(itemKey)
    end

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
        AuctionHouse.RecordPrice(itemKey, lowestPrice, "item-search")
    end
end

function module:AUCTION_HOUSE_CLOSED()
    AuctionHouse.pending = {}
    AuctionHouse.lastRequest = nil
    AuctionHouse.PruneCache()
end

ns.RegisterModule("AuctionHouse", module)
