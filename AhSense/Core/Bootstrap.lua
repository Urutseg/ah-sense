local ADDON_NAME, ns = ...

ns.name = ADDON_NAME
ns.version = C_AddOns and C_AddOns.GetAddOnMetadata(ADDON_NAME, "Version") or "0.0.0-dev"
ns.modules = ns.modules or {}
ns.events = CreateFrame("Frame")
ns.isReady = false

local function Dispatch(event, ...)
    for _, module in ipairs(ns.modules) do
        local handler = module[event]
        if handler then
            handler(module, ...)
        end
    end
end

function ns.RegisterModule(name, module)
    module.name = name
    table.insert(ns.modules, module)
    if module.OnRegister then
        module:OnRegister()
    end
end

function ns.Debug(message)
    if AhSenseDB and AhSenseDB.debug then
        print("|cff7fbfffAhSense|r " .. tostring(message))
    end
end

ns.events:RegisterEvent("ADDON_LOADED")
ns.events:RegisterEvent("PLAYER_LOGIN")
ns.events:SetScript("OnEvent", function(_, event, ...)
    if event == "ADDON_LOADED" then
        local loadedName = ...
        if loadedName ~= ADDON_NAME then
            return
        end

        AhSenseDB = AhSenseDB or {}
        Dispatch("OnAddonLoaded")
        return
    end

    if event == "PLAYER_LOGIN" then
        ns.isReady = true
        Dispatch("OnPlayerLogin")
    end
end)
