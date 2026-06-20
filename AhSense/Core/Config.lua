local _, ns = ...

local Config = {
    passiveConfidence = "tier1",
    queryCooldownSeconds = 0.75,
    queryThrottleWindowSeconds = 10,
    maxQueriesPerThrottleWindow = 10,
    priceCacheTtlSeconds = 300,
    maxQueryItems = 12,
}

ns.Config = Config

local module = {}

function module:OnAddonLoaded()
    AhSenseDB.enabled = AhSenseDB.enabled ~= false
    AhSenseDB.passiveHints = AhSenseDB.passiveHints ~= false
    AhSenseDB.debug = AhSenseDB.debug == true
end

ns.RegisterModule("Config", module)
