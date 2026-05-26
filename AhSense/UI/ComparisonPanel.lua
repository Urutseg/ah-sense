local _, ns = ...

local ComparisonPanel = {}
ns.ComparisonPanel = ComparisonPanel

local frame
local rows = {}

local function ClearRows()
    for _, row in ipairs(rows) do
        for _, cell in ipairs(row) do
            cell:SetText("")
        end
    end
end

local function CreatePanel()
    if frame then
        return frame
    end

    frame = CreateFrame("Frame", "AhSenseComparisonPanel", UIParent, "BasicFrameTemplateWithInset")
    frame:SetSize(520, 260)
    frame:SetPoint("CENTER")
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    frame:Hide()

    frame.title = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
    frame.title:SetPoint("LEFT", frame.TitleBg, "LEFT", 8, 0)
    frame.title:SetText("Auction House Sense")

    local headers = { "Item", "Price", "Difference", "Rationale" }
    local offsets = { 18, 205, 305, 390 }
    for index, label in ipairs(headers) do
        local header = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        header:SetPoint("TOPLEFT", frame, "TOPLEFT", offsets[index], -36)
        header:SetText(label)
    end

    frame.status = frame:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    frame.status:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 16, 14)
    frame.status:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -16, 14)
    frame.status:SetJustifyH("LEFT")

    for rowIndex = 1, 6 do
        local y = -58 - ((rowIndex - 1) * 28)
        rows[rowIndex] = {}
        for colIndex = 1, 4 do
            local cell = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
            cell:SetPoint("TOPLEFT", frame, "TOPLEFT", offsets[colIndex], y)
            cell:SetWidth(colIndex == 1 and 170 or colIndex == 4 and 110 or 78)
            cell:SetJustifyH("LEFT")
            cell:SetText("")
            rows[rowIndex][colIndex] = cell
        end
    end

    return frame
end

local function SetRow(index, alternative)
    local row = rows[index]
    if not row then
        return
    end

    local price = ns.AuctionHouse.GetCachedPrice(alternative.itemID) or alternative.vendorPrice
    local currentPrice = ns.AuctionHouse.GetCachedPrice(ComparisonPanel.currentItemID)
    local difference = "-"
    if currentPrice and price then
        difference = ns.Util.FormatMoney(currentPrice - price)
    elseif alternative.vendorPrice then
        difference = "Vendor"
    elseif not price then
        difference = "Pending"
    end

    row[1]:SetText(ns.Util.ItemLabel(alternative.itemID, alternative.name))
    row[2]:SetText(ns.Util.FormatMoney(price))
    row[3]:SetText(difference)
    row[4]:SetText(alternative.rationale or "Evidence available")
end

function ComparisonPanel.ShowForItemID(itemID)
    local recommendation = ns.Recommendations.GetForItem(itemID)
    local panel = CreatePanel()
    ComparisonPanel.currentItemID = itemID

    ClearRows()

    if not recommendation then
        panel.status:SetText("No reliable alternatives found.")
        panel:Show()
        return
    end

    panel.title:SetText("AH Sense: " .. ns.Util.ItemLabel(itemID, recommendation.name))

    local requested, message = ns.AuctionHouse.RequestAlternatives(itemID)
    for index, alternative in ipairs(recommendation.alternatives) do
        if index > #rows then
            break
        end
        SetRow(index, alternative)
    end

    panel.status:SetText(requested and "Targeted Auction House query requested." or (message or "Using curated evidence."))
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
    for index, alternative in ipairs(recommendation.alternatives) do
        if index > #rows then
            break
        end
        SetRow(index, alternative)
    end

    frame.status:SetText("Prices updated from targeted Auction House results.")
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
