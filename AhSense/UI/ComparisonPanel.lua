local _, ns = ...

local ComparisonPanel = {}
ns.ComparisonPanel = ComparisonPanel

local frame
local rows = {}
local currentItem = {}

local function ClearRows()
    for _, row in ipairs(rows) do
        row.button:Hide()
        row.price:SetText("")
        row.difference:SetText("")
        row.rationale:SetText("")
    end
end

local function VariantLabel(name, itemLevel)
    if itemLevel then
        return name .. " iLvl " .. tostring(itemLevel)
    end

    return name
end

local function GetItemDisplay(itemID, fallbackName, itemLevel)
    local name, link, icon
    if C_Item and C_Item.GetItemInfo then
        local itemQuality, itemLevel, itemMinLevel, itemType, itemSubType
        local itemStackCount, itemEquipLoc
        name, link, itemQuality, itemLevel, itemMinLevel, itemType, itemSubType,
            itemStackCount, itemEquipLoc, icon = C_Item.GetItemInfo(itemID)
    elseif GetItemInfo then
        local itemQuality, itemLevel, itemMinLevel, itemType, itemSubType
        local itemStackCount, itemEquipLoc
        name, link, itemQuality, itemLevel, itemMinLevel, itemType, itemSubType,
            itemStackCount, itemEquipLoc, icon = GetItemInfo(itemID)
    end

    if not icon and C_Item and C_Item.GetItemIconByID then
        icon = C_Item.GetItemIconByID(itemID)
    end

    name = name or fallbackName or ("Item " .. tostring(itemID))
    return VariantLabel(name, itemLevel), link, icon
end

local function BuildItemKey(itemID, itemLevel, cached)
    if cached and cached.itemKey then
        return cached.itemKey
    end

    return {
        itemID = itemID,
        itemLevel = itemLevel,
        itemSuffix = 0,
        battlePetSpeciesID = 0,
    }
end

local function TrySetItemKeyTooltip(itemKey)
    if type(itemKey) ~= "table" then
        return false
    end

    local attempts = {}

    if GameTooltip.SetItemKey then
        table.insert(attempts, function()
            GameTooltip:SetItemKey(itemKey)
        end)
        table.insert(attempts, function()
            GameTooltip:SetItemKey(itemKey.itemID, itemKey.itemLevel, itemKey.itemSuffix or 0, itemKey.battlePetSpeciesID or 0)
        end)
        table.insert(attempts, function()
            GameTooltip:SetItemKey(itemKey.itemID, itemKey.itemLevel)
        end)
    end

    if C_TooltipInfo and GameTooltip.ProcessInfo then
        local function processInfo(tooltipInfo)
            if TooltipUtil and TooltipUtil.SurfaceArgs then
                TooltipUtil.SurfaceArgs(tooltipInfo)
            end

            GameTooltip:ProcessInfo(tooltipInfo)
        end

        if C_TooltipInfo.GetItemKey then
            table.insert(attempts, function()
                processInfo(C_TooltipInfo.GetItemKey(itemKey))
            end)
            table.insert(attempts, function()
                processInfo(C_TooltipInfo.GetItemKey(
                    itemKey.itemID,
                    itemKey.itemLevel,
                    itemKey.itemSuffix or 0,
                    itemKey.battlePetSpeciesID or 0
                ))
            end)
        end

        if C_TooltipInfo.GetItemByItemKey then
            table.insert(attempts, function()
                processInfo(C_TooltipInfo.GetItemByItemKey(itemKey))
            end)
        end
    end

    for _, attempt in ipairs(attempts) do
        GameTooltip:ClearLines()
        local ok = pcall(attempt)
        if ok and GameTooltip:NumLines() > 0 then
            return true
        end
    end

    GameTooltip:ClearLines()
    return false
end

local function ShowItemTooltip(owner, itemID, fallbackName, itemLevel)
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")

    local name, link = GetItemDisplay(itemID, fallbackName, itemLevel)
    if itemLevel then
        local cached = ns.AuctionHouse.GetCachedEntry and ns.AuctionHouse.GetCachedEntry(itemID, itemLevel)
        if TrySetItemKeyTooltip(BuildItemKey(itemID, itemLevel, cached)) then
            GameTooltip:Show()
            return
        elseif cached and cached.link then
            GameTooltip:SetHyperlink(cached.link)
        else
            GameTooltip:Hide()
            return
        end
    elseif link then
        GameTooltip:SetHyperlink(link)
    elseif GameTooltip.SetItemByID then
        GameTooltip:SetItemByID(itemID)
    else
        GameTooltip:AddLine(name)
        GameTooltip:AddLine("Item ID: " .. tostring(itemID), 0.7, 0.7, 0.7)
    end

    GameTooltip:Show()
end

local function OpenItemLink(itemID, fallbackName, itemLevel)
    if itemLevel then
        local cached = ns.AuctionHouse.GetCachedEntry and ns.AuctionHouse.GetCachedEntry(itemID, itemLevel)
        local link = cached and cached.link
        if link and IsModifiedClick and IsModifiedClick("CHATLINK") and ChatEdit_InsertLink then
            ChatEdit_InsertLink(link)
        elseif link and SetItemRef then
            SetItemRef(link, link, "LeftButton")
        end
        return
    end

    local name, link = GetItemDisplay(itemID, fallbackName, itemLevel)
    if not link then
        return
    end

    if IsModifiedClick and IsModifiedClick("CHATLINK") and ChatEdit_InsertLink then
        ChatEdit_InsertLink(link)
    elseif SetItemRef then
        SetItemRef(link, link, "LeftButton")
    end
end

local function CreateItemButton(parent, width)
    local button = CreateFrame("Button", nil, parent)
    button:SetSize(width, 24)

    button.icon = button:CreateTexture(nil, "ARTWORK")
    button.icon:SetSize(20, 20)
    button.icon:SetPoint("LEFT", button, "LEFT", 0, 0)
    button.icon:SetTexture(134400)

    button.text = button:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    button.text:SetPoint("LEFT", button.icon, "RIGHT", 6, 0)
    button.text:SetPoint("RIGHT", button, "RIGHT", 0, 0)
    button.text:SetJustifyH("LEFT")
    button.text:SetWordWrap(false)

    button:SetScript("OnEnter", function(self)
        if self.itemID then
            ShowItemTooltip(self, self.itemID, self.fallbackName, self.itemLevel)
        end
    end)
    button:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)
    button:SetScript("OnClick", function(self)
        if self.itemID then
            OpenItemLink(self.itemID, self.fallbackName, self.itemLevel)
        end
    end)

    return button
end

local function SetItemButton(button, itemID, fallbackName, itemLevel)
    local name, _, icon = GetItemDisplay(itemID, fallbackName, itemLevel)
    button.itemID = itemID
    button.fallbackName = fallbackName
    button.itemLevel = itemLevel
    button.icon:SetTexture(icon or 134400)
    button.text:SetText(name)
    button:Show()
end

local function CreatePanel()
    if frame then
        return frame
    end

    frame = CreateFrame("Frame", "AhSenseComparisonPanel", UIParent, "BasicFrameTemplateWithInset")
    frame:SetSize(820, 430)
    frame:SetPoint("CENTER")
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    frame:Hide()

    frame.title = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
    frame.title:SetPoint("LEFT", frame.TitleBg, "LEFT", 8, 0)
    frame.title:SetText("AH Sense Comparison")

    frame.currentLabel = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    frame.currentLabel:SetPoint("TOPLEFT", frame, "TOPLEFT", 18, -36)
    frame.currentLabel:SetText("Current item")

    currentItem.button = CreateItemButton(frame, 300)
    currentItem.button:SetPoint("TOPLEFT", frame, "TOPLEFT", 18, -56)

    currentItem.price = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    currentItem.price:SetPoint("TOPLEFT", frame, "TOPLEFT", 340, -58)
    currentItem.price:SetWidth(110)
    currentItem.price:SetJustifyH("LEFT")

    currentItem.note = frame:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    currentItem.note:SetPoint("TOPLEFT", frame, "TOPLEFT", 470, -58)
    currentItem.note:SetWidth(320)
    currentItem.note:SetJustifyH("LEFT")
    currentItem.note:SetText("Baseline for comparison")

    local headers = { "Auction item", "Price", "Compared to current", "Evidence" }
    local offsets = { 18, 340, 460, 610 }
    for index, label in ipairs(headers) do
        local header = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        header:SetPoint("TOPLEFT", frame, "TOPLEFT", offsets[index], -96)
        header:SetText(label)
    end

    frame.status = frame:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    frame.status:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 16, 14)
    frame.status:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -16, 14)
    frame.status:SetJustifyH("LEFT")

    for rowIndex = 1, 10 do
        local y = -118 - ((rowIndex - 1) * 28)
        local row = {}
        row.button = CreateItemButton(frame, 300)
        row.button:SetPoint("TOPLEFT", frame, "TOPLEFT", offsets[1], y + 2)

        row.price = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        row.price:SetPoint("TOPLEFT", frame, "TOPLEFT", offsets[2], y)
        row.price:SetWidth(90)
        row.price:SetJustifyH("LEFT")

        row.difference = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        row.difference:SetPoint("TOPLEFT", frame, "TOPLEFT", offsets[3], y)
        row.difference:SetWidth(130)
        row.difference:SetJustifyH("LEFT")

        row.rationale = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        row.rationale:SetPoint("TOPLEFT", frame, "TOPLEFT", offsets[4], y)
        row.rationale:SetWidth(185)
        row.rationale:SetJustifyH("LEFT")
        row.rationale:SetWordWrap(true)

        rows[rowIndex] = row
    end

    return frame
end

local function SetCurrentItem(itemID, name, itemLevels)
    if itemLevels and #itemLevels > 0 then
        currentItem.button:Hide()
        currentItem.price:SetText("")
        currentItem.note:SetText("Current item variants are listed below.")
        return
    end

    SetItemButton(currentItem.button, itemID, name)

    local price = ns.AuctionHouse.GetCachedPrice(itemID)
    if price then
        currentItem.price:SetText(ns.Util.FormatMoney(price))
    elseif itemLevels and #itemLevels > 0 then
        currentItem.price:SetText("See variants")
    else
        currentItem.price:SetText("Checking AH")
    end
end

local function AddVariantRows(output, item, evidence)
    if item.itemLevels and #item.itemLevels > 0 then
        for _, itemLevel in ipairs(item.itemLevels) do
            table.insert(output, {
                itemID = item.itemID,
                name = item.name,
                itemLevel = itemLevel,
                rationale = evidence,
            })
        end
        return
    end

    table.insert(output, {
        itemID = item.itemID,
        name = item.name,
        rationale = evidence,
    })
end

local function BuildRows(recommendation)
    local output = {}
    AddVariantRows(output, recommendation, "Current item variant")
    for _, alternative in ipairs(recommendation.alternatives) do
        AddVariantRows(output, alternative, "Same profession slot")
    end

    return output
end

local function LowestCurrentPrice(recommendation)
    local lowestPrice
    if recommendation.itemLevels and #recommendation.itemLevels > 0 then
        for _, itemLevel in ipairs(recommendation.itemLevels) do
            local price = ns.AuctionHouse.GetCachedPrice(recommendation.itemID, itemLevel)
            if price and (not lowestPrice or price < lowestPrice) then
                lowestPrice = price
            end
        end
        return lowestPrice
    end

    return ns.AuctionHouse.GetCachedPrice(recommendation.itemID)
end

local function DifferenceText(currentPrice, alternativePrice)
    if not currentPrice or not alternativePrice then
        return "Waiting"
    end

    local difference = currentPrice - alternativePrice
    if difference > 0 then
        return "Saves " .. ns.Util.FormatMoney(difference)
    elseif difference < 0 then
        return "Costs " .. ns.Util.FormatMoney(math.abs(difference)) .. " more"
    end

    return "Same price"
end

local function StatusText(itemID, requested, message)
    local status = ns.AuctionHouse.GetLastRequestStatus and ns.AuctionHouse.GetLastRequestStatus(itemID)
    if status then
        if status.fromCache then
            return "Using recent AH prices for " .. tostring(status.found) .. " of "
                .. tostring(status.total) .. " known items."
        end

        if status.reusedPending then
            return "AH price check already in progress for " .. tostring(status.total) .. " known items."
        end

        if status.found == 0 and status.pending > 0 then
            return "Checking AH prices for " .. tostring(status.total) .. " known items..."
        end

        return "Live AH prices found for " .. tostring(status.found) .. " of "
            .. tostring(status.total) .. " known items."
    end

    if requested then
        return "Checking AH prices for known alternatives..."
    end

    return message or "Using curated evidence."
end

local function SetRow(index, rowItem, recommendation)
    local row = rows[index]
    if not row then
        return
    end

    local price = ns.AuctionHouse.GetCachedPrice(rowItem.itemID, rowItem.itemLevel) or rowItem.vendorPrice
    local currentPrice = LowestCurrentPrice(recommendation)
    local isCurrentItem = rowItem.itemID == recommendation.itemID
    local difference = isCurrentItem and "Current variant" or rowItem.vendorPrice and not currentPrice and "Vendor price"
        or DifferenceText(currentPrice, price)

    SetItemButton(row.button, rowItem.itemID, rowItem.name, rowItem.itemLevel)
    row.price:SetText(ns.Util.FormatMoney(price))
    row.difference:SetText(difference)
    row.rationale:SetText(rowItem.rationale or "Curated alternative")
end

function ComparisonPanel.ShowForItemID(itemID)
    local recommendation = ns.Recommendations.GetForItem(itemID)
    local panel = CreatePanel()
    ComparisonPanel.currentItemID = itemID

    ClearRows()

    if not recommendation then
        currentItem.button:Hide()
        currentItem.price:SetText("")
        currentItem.note:SetText("")
        panel.status:SetText("No reliable alternatives found.")
        panel:Show()
        return
    end

    panel.title:SetText("AH Sense: " .. ns.Util.ItemLabel(itemID, recommendation.name))
    currentItem.note:SetText(recommendation.rationale or "Baseline for comparison")
    SetCurrentItem(itemID, recommendation.name, recommendation.itemLevels)

    local requested, message = ns.AuctionHouse.RequestAlternatives(itemID)
    local rowItems = BuildRows(recommendation)
    for index, rowItem in ipairs(rowItems) do
        if index > #rows then
            break
        end
        SetRow(index, rowItem, recommendation)
    end

    panel.status:SetText(StatusText(itemID, requested, message))
    panel:Show()
end

function ComparisonPanel.Refresh()
    if not frame or not frame:IsShown() or not ComparisonPanel.currentItemID then
        return
    end

    local recommendation = ns.Recommendations.GetForItem(ComparisonPanel.currentItemID)
    if not recommendation then
        return
    end

    ClearRows()
    SetCurrentItem(ComparisonPanel.currentItemID, recommendation.name, recommendation.itemLevels)
    local rowItems = BuildRows(recommendation)
    for index, rowItem in ipairs(rowItems) do
        if index > #rows then
            break
        end
        SetRow(index, rowItem, recommendation)
    end

    frame.status:SetText(StatusText(ComparisonPanel.currentItemID, false))
end

local module = {}

function module:OnAddonLoaded()
    SLASH_AHSENSE1 = "/ahs"
    SLASH_AHSENSE2 = "/ahsense"
    SlashCmdList.AHSENSE = function(input)
        local command, value = strsplit(" ", input or "")
        if command == "debug" then
            AhSenseDB.debug = not AhSenseDB.debug
            print("AH Sense debug: " .. tostring(AhSenseDB.debug))
            return
        end

        local itemID = tonumber(value or command)
        if itemID then
            ComparisonPanel.ShowForItemID(itemID)
            return
        end

        print("AH Sense: use /ahs <itemID> to open the comparison panel.")
    end
end

ns.RegisterModule("ComparisonPanel", module)
