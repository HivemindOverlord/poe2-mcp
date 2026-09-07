-- MCP Bridge Command Handlers for Path of Building (PoE2)
-- https://github.com/HivemindOverlord/poe2-mcp
--
-- This module defines all command handlers that can be invoked via the MCP bridge.
-- Each handler receives a params table and returns (result, errorMessage).

MCPCommands = {}

-------------------------------------------------------------------------------
-- HELPER FUNCTIONS
-------------------------------------------------------------------------------

-- Get the active build instance (works in both live PoB and headless modes)
-- In live PoB: build global OR launch.main.modes["BUILD"]
-- In headless: build global from HeadlessWrapper
local function getActiveBuild()
    -- First try the global build variable (works in headless and sometimes live)
    if build and build.calcsTab then
        return build
    end

    -- Try launch.main.modes["BUILD"] (live PoB structure)
    if launch and launch.main and launch.main.modes then
        local buildMode = launch.main.modes["BUILD"]
        if buildMode and buildMode.calcsTab then
            return buildMode
        end
    end

    -- Fallback: check if launch.main itself is the build (some PoB versions)
    if launch and launch.main and launch.main.calcsTab then
        return launch.main
    end

    return nil
end

-- Check if a build is currently loaded
local function hasBuildLoaded()
    return getActiveBuild() ~= nil
end

-- Force calculation refresh if build has pending changes
-- Returns: activeBuild, errorMessage
local function ensureBuildReady()
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    -- If buildFlag is set, calculations need to be rebuilt
    if activeBuild.buildFlag then
        -- Force calculation refresh
        if activeBuild.calcsTab and activeBuild.calcsTab.BuildOutput then
            activeBuild.calcsTab:BuildOutput()
        end
        activeBuild.buildFlag = false
    end

    return activeBuild, nil
end

-- Trigger a frame update cycle (for async operations)
-- This is a no-op stub - in live PoB, the main loop handles this automatically
-- The bridge.lua hooks OnFrame which runs after each frame
local function triggerUpdate()
    -- TRUE no-op in live PoB. Setting build.buildFlag = true (done by each
    -- command) is enough: PoB's own frame loop recalculates on the next frame.
    --
    -- We must NOT call runCallback("OnFrame") here: poll() runs INSIDE OnFrame,
    -- so re-entering OnFrame from here is reentrancy that deadlocks PoB's frame
    -- loop (observed as a 0-CPU freeze that takes the bridge down with it).
end

-- Get the main application object for mode switching
local function getMainObject()
    -- In live PoB, launch.main handles mode switching
    if launch and launch.main then
        return launch.main
    end

    -- Legacy/headless fallback
    if mainObject then
        return mainObject.main or mainObject
    end

    return nil
end

-- Make a value JSON-safe before it goes to dkjson: keep scalars + plain nested
-- tables, drop functions/userdata/threads, depth-limit, and break cycles. PoB's
-- raw calc output tables contain functions and circular references that make
-- dkjson throw (-> empty response) or hang (-> wedged bridge), so any command
-- returning raw output MUST pass it through this first.
local function jsonSafe(v, depth, seen)
    local t = type(v)
    if t == "number" or t == "string" or t == "boolean" then
        return v
    elseif t == "table" then
        if depth > 6 then return "<max depth>" end
        if seen[v] then return "<cycle>" end
        seen[v] = true
        local out = {}
        for k, val in pairs(v) do
            if type(k) == "string" or type(k) == "number" then
                local sv = jsonSafe(val, depth + 1, seen)
                if sv ~= nil then out[k] = sv end
            end
        end
        seen[v] = nil
        return out
    end
    return nil  -- functions, userdata, threads: drop
end

-------------------------------------------------------------------------------
-- SYSTEM COMMANDS
-------------------------------------------------------------------------------

-- Ping: Simple health check
function MCPCommands.ping(params)
    local activeBuild = getActiveBuild()
    return {
        status = "ok",
        version = MCPConfig.VERSION,
        pob_version = launch and launch.versionNumber or "unknown",
        build_loaded = activeBuild ~= nil,
        build_name = activeBuild and activeBuild.buildName or nil,
        uptime = MCPBridge and MCPBridge.getStatus().uptime or 0
    }
end

-- Get server status
function MCPCommands.status(params)
    return MCPBridge.getStatus()
end

-------------------------------------------------------------------------------
-- BUILD COMMANDS
-------------------------------------------------------------------------------

-- Get current build as XML or PoB code
function MCPCommands.get_build(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    local format = params.format or "xml"
    local xmlText = activeBuild:SaveDB("code")

    if not xmlText then
        return nil, "Failed to generate build XML"
    end

    if format == "code" then
        local deflated = Deflate(xmlText)
        if not deflated then
            return nil, "Failed to compress build (Deflate not available)"
        end
        local encoded = common.base64.encode(deflated)
        local code = encoded:gsub("+", "-"):gsub("/", "_")
        return {
            code = code,
            format = "pob_code",
            name = activeBuild.buildName or "Unnamed"
        }
    else
        return {
            xml = xmlText,
            format = "xml",
            name = activeBuild.buildName or "Unnamed"
        }
    end
end

-- Load a build from XML or PoB code
function MCPCommands.load_build(params)
    local xmlText

    if params.code then
        -- Decode PoB code to XML
        local decoded = common.base64.decode(params.code:gsub("-", "+"):gsub("_", "/"))
        if not decoded then
            return nil, "Failed to decode base64"
        end
        xmlText = Inflate(decoded)
        if not xmlText then
            return nil, "Failed to decompress build (Inflate not available)"
        end
    elseif params.xml then
        xmlText = params.xml
    else
        return nil, "Missing 'code' or 'xml' parameter"
    end

    local buildName = params.name or "MCP Import"

    -- Get main application for mode switching
    local main = getMainObject()
    if not main then
        return nil, "Cannot access PoB main object - is PoB fully initialized?"
    end

    -- Load the build via SetMode
    -- SetMode(mode, subMode, buildName, buildXML)
    -- This queues the mode change for next frame
    if main.SetMode then
        main:SetMode("BUILD", false, buildName, xmlText)
    else
        return nil, "SetMode not available on main object"
    end

    -- Trigger update cycle
    triggerUpdate()

    -- Note: Due to async nature of SetMode, build may not be immediately available
    -- Caller should verify with ping() or get_calcs() after a brief delay
    return {
        success = true,
        name = buildName,
        note = "Build load queued. Use ping() to verify build_loaded status."
    }
end

-- Create a new empty build
function MCPCommands.new_build(params)
    local buildName = params.name or "MCP New Build"

    -- Get main application for mode switching
    local main = getMainObject()
    if not main then
        return nil, "Cannot access PoB main object - is PoB fully initialized?"
    end

    -- Create new build via SetMode (no XML = new build)
    if main.SetMode then
        main:SetMode("BUILD", false, buildName)
    else
        return nil, "SetMode not available on main object"
    end

    -- Trigger update cycle
    triggerUpdate()

    return {
        success = true,
        name = buildName,
        note = "New build created. Use ping() to verify build_loaded status."
    }
end

-------------------------------------------------------------------------------
-- DIRECT BUILD MANIPULATION COMMANDS
-------------------------------------------------------------------------------

-- Load build XML directly into existing build (faster, no mode switch)
-- This is faster than load_build() when you already have a build loaded
function MCPCommands.load_build_direct(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded - use load_build() first or open a build in PoB"
    end

    local xmlText
    if params.code then
        -- Decode PoB code to XML
        local decoded = common.base64.decode(params.code:gsub("-", "+"):gsub("_", "/"))
        if not decoded then
            return nil, "Failed to decode base64"
        end
        xmlText = Inflate(decoded)
        if not xmlText then
            return nil, "Failed to decompress build (Inflate not available)"
        end
    elseif params.xml then
        xmlText = params.xml
    else
        return nil, "Missing 'code' or 'xml' parameter"
    end

    -- Load directly into existing build
    local loadResult = activeBuild:LoadDB(xmlText, "MCP Direct Import")
    if loadResult == false then
        return nil, "Failed to load build XML - invalid format or version mismatch"
    end

    -- Force recalculation
    if activeBuild.buildFlag then
        if activeBuild.calcsTab and activeBuild.calcsTab.BuildOutput then
            activeBuild.calcsTab:BuildOutput()
        end
        activeBuild.buildFlag = false
    end

    return {
        success = true,
        name = activeBuild.buildName or "Unknown",
        method = "direct"
    }
end

-- Force full calculation refresh
function MCPCommands.recalculate(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    if not activeBuild.calcsTab then
        return nil, "Build has no calcsTab - calculation not available"
    end

    -- Force rebuild by setting buildFlag
    activeBuild.buildFlag = true

    -- Perform calculation
    if activeBuild.calcsTab.BuildOutput then
        activeBuild.calcsTab:BuildOutput()
    end
    activeBuild.buildFlag = false

    -- Also rebuild config if available
    if activeBuild.configTab and activeBuild.configTab.BuildModList then
        activeBuild.configTab:BuildModList()
    end

    return {
        success = true,
        message = "Calculations refreshed"
    }
end

-------------------------------------------------------------------------------
-- CALCULATION COMMANDS
-------------------------------------------------------------------------------

-- Get calculation output (DPS, defenses, etc.)
function MCPCommands.get_calcs(params)
    -- Ensure build is ready and calculations are current
    local activeBuild, err = ensureBuildReady()
    if not activeBuild then
        return nil, err
    end

    if not activeBuild.calcsTab then
        return nil, "Build has no calcsTab - calculation not available"
    end

    local output = activeBuild.calcsTab.mainOutput or {}
    local calcsOutput = activeBuild.calcsTab.calcsOutput or {}

    -- Compile key stats
    local result = {
        -- Character info
        level = activeBuild.characterLevel,
        class = activeBuild.spec and activeBuild.spec.curClassName,
        ascendancy = activeBuild.spec and activeBuild.spec.curAscendClassName,

        -- Offensive stats
        TotalDPS = output.TotalDPS,
        CombinedDPS = output.CombinedDPS,
        AverageDamage = output.AverageDamage,
        Speed = output.Speed,
        CritChance = output.CritChance,
        CritMultiplier = output.CritMultiplier,
        HitChance = output.HitChance,
        Accuracy = output.Accuracy,

        -- Defensive stats
        Life = output.Life,
        LifeRegen = output.LifeRegen,
        LifeRegenPercent = output.LifeRegenPercent,
        EnergyShield = output.EnergyShield,
        EnergyShieldRegen = output.EnergyShieldRegen,
        Mana = output.Mana,
        ManaRegen = output.ManaRegen,
        Armour = output.Armour,
        Evasion = output.Evasion,
        PhysicalDamageReduction = output.PhysicalDamageReduction,
        SpellSuppressionChance = output.SpellSuppressionChance,
        BlockChance = output.BlockChance,
        SpellBlockChance = output.SpellBlockChance,

        -- Resistances
        FireResist = output.FireResist,
        FireResistOverCap = output.FireResistOverCap,
        ColdResist = output.ColdResist,
        ColdResistOverCap = output.ColdResistOverCap,
        LightningResist = output.LightningResist,
        LightningResistOverCap = output.LightningResistOverCap,
        ChaosResist = output.ChaosResist,
        ChaosResistOverCap = output.ChaosResistOverCap,

        -- Resources
        Spirit = output.Spirit,
        SpiritReserved = output.SpiritReserved,
        SpiritReservedPercent = output.SpiritReservedPercent,

        -- Attributes
        Str = output.Str,
        Dex = output.Dex,
        Int = output.Int,

        -- Max hits (from calcsOutput)
        PhysicalMaximumHitTaken = calcsOutput.PhysicalMaximumHitTaken,
        FireMaximumHitTaken = calcsOutput.FireMaximumHitTaken,
        ColdMaximumHitTaken = calcsOutput.ColdMaximumHitTaken,
        LightningMaximumHitTaken = calcsOutput.LightningMaximumHitTaken,
        ChaosMaximumHitTaken = calcsOutput.ChaosMaximumHitTaken,
    }

    return result
end

-- Get full raw output (for advanced analysis)
function MCPCommands.get_raw_output(params)
    local activeBuild, err = ensureBuildReady()
    if not activeBuild then
        return nil, err
    end

    if not activeBuild.calcsTab then
        return nil, "Build has no calcsTab - calculation not available"
    end

    return {
        mainOutput = jsonSafe(activeBuild.calcsTab.mainOutput, 0, {}),
        calcsOutput = jsonSafe(activeBuild.calcsTab.calcsOutput, 0, {})
    }
end

-- Get comprehensive calculations (mainOutput + calcsOutput merged)
function MCPCommands.get_full_calcs(params)
    local activeBuild, err = ensureBuildReady()
    if not activeBuild then
        return nil, err
    end

    if not activeBuild.calcsTab then
        return nil, "Build has no calcsTab - calculation not available"
    end

    local mainOutput = activeBuild.calcsTab.mainOutput or {}
    local calcsOutput = activeBuild.calcsTab.calcsOutput or {}

    -- Merge both outputs for comprehensive data
    local result = {
        -- Character metadata
        build_name = activeBuild.buildName,
        level = activeBuild.characterLevel,
        class = activeBuild.spec and activeBuild.spec.curClassName,
        ascendancy = activeBuild.spec and activeBuild.spec.curAscendClassName,

        -- All mainOutput values (sanitised: drops functions/cycles)
        main = jsonSafe(mainOutput, 0, {}),

        -- All calcsOutput values (detailed breakdown, sanitised)
        calcs = jsonSafe(calcsOutput, 0, {}),

        -- Key aggregated stats for quick access
        summary = {
            -- Offense
            total_dps = mainOutput.TotalDPS,
            combined_dps = mainOutput.CombinedDPS,
            crit_chance = mainOutput.CritChance,
            crit_multi = mainOutput.CritMultiplier,
            hit_chance = mainOutput.HitChance,

            -- Defense
            life = mainOutput.Life,
            energy_shield = mainOutput.EnergyShield,
            armour = mainOutput.Armour,
            evasion = mainOutput.Evasion,
            block = mainOutput.BlockChance,
            spell_block = mainOutput.SpellBlockChance,

            -- Resistances (capped)
            fire_res = mainOutput.FireResist,
            cold_res = mainOutput.ColdResist,
            lightning_res = mainOutput.LightningResist,
            chaos_res = mainOutput.ChaosResist,

            -- Resources
            mana = mainOutput.Mana,
            spirit = mainOutput.Spirit,
            spirit_reserved = mainOutput.SpiritReserved
        }
    }

    return result
end

-- Get DPS breakdown per skill group
function MCPCommands.get_skill_dps(params)
    local activeBuild, err = ensureBuildReady()
    if not activeBuild then
        return nil, err
    end

    if not activeBuild.skillsTab then
        return nil, "Build has no skillsTab"
    end

    if not activeBuild.calcsTab then
        return nil, "Build has no calcsTab - calculation not available"
    end

    local skills = {}
    local mainOutput = activeBuild.calcsTab.mainOutput or {}

    -- Get DPS for each skill group
    for i, socketGroup in ipairs(activeBuild.skillsTab.socketGroupList) do
        local skillInfo = {
            index = i,
            label = socketGroup.label or "",
            slot = socketGroup.slot,
            enabled = socketGroup.enabled,
            is_main = (i == activeBuild.mainSocketGroup),
            gems = {}
        }

        -- List gems in this group
        for j, gem in ipairs(socketGroup.gemList) do
            table.insert(skillInfo.gems, {
                name = gem.nameSpec,
                level = gem.level,
                quality = gem.quality,
                enabled = gem.enabled
            })
        end

        -- If this is the main skill, it has the DPS from mainOutput
        if skillInfo.is_main then
            skillInfo.dps = {
                total = mainOutput.TotalDPS,
                combined = mainOutput.CombinedDPS,
                average_hit = mainOutput.AverageDamage,
                speed = mainOutput.Speed,
                crit_chance = mainOutput.CritChance,
                crit_multi = mainOutput.CritMultiplier
            }
        end

        table.insert(skills, skillInfo)
    end

    return {
        skills = skills,
        main_skill_index = activeBuild.mainSocketGroup
    }
end

-- Get focused defense stats
function MCPCommands.get_defense_stats(params)
    local activeBuild, err = ensureBuildReady()
    if not activeBuild then
        return nil, err
    end

    if not activeBuild.calcsTab then
        return nil, "Build has no calcsTab - calculation not available"
    end

    local output = activeBuild.calcsTab.mainOutput or {}
    local calcsOutput = activeBuild.calcsTab.calcsOutput or {}

    return {
        -- Health pools
        life = {
            total = output.Life,
            regen = output.LifeRegen,
            regen_percent = output.LifeRegenPercent,
            leech_rate = output.LifeLeechRate,
            leech_max = output.MaxLifeLeechRate
        },
        energy_shield = {
            total = output.EnergyShield,
            regen = output.EnergyShieldRegen,
            recharge = output.EnergyShieldRecharge,
            recharge_delay = output.EnergyShieldRechargeDelay
        },
        mana = {
            total = output.Mana,
            unreserved = output.ManaUnreserved,
            regen = output.ManaRegen,
            reserved = output.ManaReserved,
            reserved_percent = output.ManaReservedPercent
        },

        -- Mitigation
        armour = {
            total = output.Armour,
            phys_reduction = output.PhysicalDamageReduction
        },
        evasion = {
            total = output.Evasion,
            chance = output.EvadeChance
        },
        block = {
            attack = output.BlockChance,
            spell = output.SpellBlockChance
        },
        suppression = {
            chance = output.SpellSuppressionChance,
            effect = output.SpellSuppressionEffect
        },

        -- Resistances (with overcap)
        resistances = {
            fire = { current = output.FireResist, overcap = output.FireResistOverCap },
            cold = { current = output.ColdResist, overcap = output.ColdResistOverCap },
            lightning = { current = output.LightningResist, overcap = output.LightningResistOverCap },
            chaos = { current = output.ChaosResist, overcap = output.ChaosResistOverCap }
        },

        -- Maximum hit taken
        max_hit = {
            physical = calcsOutput.PhysicalMaximumHitTaken,
            fire = calcsOutput.FireMaximumHitTaken,
            cold = calcsOutput.ColdMaximumHitTaken,
            lightning = calcsOutput.LightningMaximumHitTaken,
            chaos = calcsOutput.ChaosMaximumHitTaken
        },

        -- Stun/recovery
        stun = {
            threshold = output.StunThreshold,
            duration = output.StunDuration,
            recovery = output.StunRecovery
        }
    }
end

-------------------------------------------------------------------------------
-- SKILL COMMANDS
-------------------------------------------------------------------------------

-- Get all skill groups
function MCPCommands.get_skills(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    if not activeBuild.skillsTab then
        return nil, "Build has no skillsTab"
    end

    local skillGroups = {}
    for i, socketGroup in ipairs(activeBuild.skillsTab.socketGroupList) do
        local gems = {}
        for j, gemInstance in ipairs(socketGroup.gemList) do
            table.insert(gems, {
                name = gemInstance.nameSpec,
                level = gemInstance.level,
                quality = gemInstance.quality,
                enabled = gemInstance.enabled,
                skillId = gemInstance.skillId
            })
        end
        table.insert(skillGroups, {
            index = i,
            slot = socketGroup.slot,
            label = socketGroup.label,
            enabled = socketGroup.enabled,
            isMainGroup = (i == activeBuild.mainSocketGroup),
            gems = gems
        })
    end

    return {
        skillGroups = skillGroups,
        mainSocketGroup = activeBuild.mainSocketGroup
    }
end

-- Add or replace a skill group
function MCPCommands.set_skill_group(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    if not activeBuild.skillsTab then
        return nil, "Build has no skillsTab"
    end

    local skillText = params.skills
    if not skillText then
        return nil, "Missing 'skills' parameter"
    end

    -- Clear existing skills if requested. This PoB has no DeleteSocketGroup;
    -- socketGroupList is a plain array, so clear it with table.remove.
    if params.replace_all then
        local list = activeBuild.skillsTab.socketGroupList
        for i = #list, 1, -1 do
            table.remove(list, i)
        end
    end

    -- Paste the new skill group
    -- Format: "SkillName Level/Quality\nSupportName Level/Quality\n..."
    activeBuild.skillsTab:PasteSocketGroup(skillText)
    -- Make the newly added group the main skill so Average Hit / DPS reflect it.
    if params.set_main and #activeBuild.skillsTab.socketGroupList > 0 then
        activeBuild.mainSocketGroup = #activeBuild.skillsTab.socketGroupList
    end
    activeBuild.buildFlag = true
    triggerUpdate()

    return {
        success = true,
        group_count = #activeBuild.skillsTab.socketGroupList,
        main_socket_group = activeBuild.mainSocketGroup
    }
end

-- Set which socket group is the "main" skill (drives Average Hit / DPS output)
function MCPCommands.set_main_skill_group(params)
    local activeBuild = getActiveBuild()
    if not activeBuild or not activeBuild.skillsTab then
        return nil, "No build loaded"
    end
    local idx = params.index
    if not idx or idx < 1 or idx > #activeBuild.skillsTab.socketGroupList then
        return nil, "Invalid socket group index"
    end
    -- Mutate on the deferred queue, never inside the poll/OnFrame prologue.
    -- Doing it inline strands PoB's incremental build coroutine (0-CPU freeze).
    MCPBridge.defer(function()
        activeBuild.mainSocketGroup = idx
        activeBuild.buildFlag = true
    end)
    return { success = true, main_socket_group = idx, applied = "deferred" }
end

-- Set the character level (and disable auto-level) to control the passive budget
function MCPCommands.set_character_level(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end
    local level = params.level
    if not level or level < 1 or level > 100 then
        return nil, "Level must be 1-100"
    end
    activeBuild.characterLevel = level
    activeBuild.characterLevelAutoMode = false
    if activeBuild.controls and activeBuild.controls.characterLevel then
        activeBuild.controls.characterLevel:SetText(tostring(level))
    end
    activeBuild.buildFlag = true
    triggerUpdate()
    return { success = true, level = level }
end

-- Search the FULL passive tree for nodes whose stats match keyword(s).
-- Uses PoB's own tree data. Returns id/name/type/stats for allocation targets.
function MCPCommands.search_tree_nodes(params)
    local activeBuild = getActiveBuild()
    if not activeBuild or not activeBuild.spec then
        return nil, "No build loaded"
    end
    local keywords = params.keywords
    if type(keywords) == "string" then keywords = { keywords } end
    if not keywords or #keywords == 0 then
        return nil, "Missing 'keywords'"
    end
    for i, k in ipairs(keywords) do keywords[i] = k:lower() end

    local notablesOnly = params.notables_only
    local limit = params.limit or 200
    local results = {}

    for id, node in pairs(activeBuild.spec.nodes) do
        -- Skip class/ascendancy starts, ascendancy nodes, sockets, masteries
        local skip = node.ascendancyName or node.type == "ClassStart"
            or node.type == "AscendClassStart" or node.type == "Socket"
            or node.type == "Mastery" or node.isAscendancyStart
        if notablesOnly and not (node.isNotable or node.type == "Keystone") then
            skip = true
        end
        if not skip and node.sd and #node.sd > 0 then
            local blob = table.concat(node.sd, " "):lower()
            local matched = false
            for _, k in ipairs(keywords) do
                if blob:find(k, 1, true) then matched = true break end
            end
            if matched then
                table.insert(results, {
                    id = id,
                    name = node.dn or node.name,
                    type = node.type,
                    isNotable = node.isNotable or false,
                    isKeystone = (node.type == "Keystone"),
                    allocated = node.alloc or false,
                    reachable = (node.path ~= nil) or (node.alloc or false),
                    distance = node.path and #node.path or nil,
                    stats = node.sd
                })
            end
        end
        if #results >= limit then break end
    end

    return { count = #results, nodes = results }
end

-------------------------------------------------------------------------------
-- PASSIVE TREE COMMANDS
-------------------------------------------------------------------------------

-- Get allocated passive nodes
function MCPCommands.get_passive_tree(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    if not activeBuild.spec then
        return nil, "Build has no spec"
    end

    local allocatedNodes = {}
    for nodeId, node in pairs(activeBuild.spec.allocNodes) do
        table.insert(allocatedNodes, {
            id = nodeId,
            name = node.name,
            type = node.type,
            isKeystone = node.isKeystone,
            isNotable = node.isNotable,
            isAscendancyStart = node.isAscendancyStart,
            ascendancyName = node.ascendancyName,
            stats = node.sd
        })
    end

    return {
        class = activeBuild.spec.curClassName,
        classId = activeBuild.spec.curClassId,
        ascendancy = activeBuild.spec.curAscendClassName,
        ascendancyId = activeBuild.spec.curAscendClassId,
        nodes = allocatedNodes,
        totalPoints = activeBuild.spec:CountAllocNodes()
    }
end

-- Allocate or deallocate a passive node
function MCPCommands.set_passive_node(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    if not activeBuild.spec then
        return nil, "Build has no spec"
    end

    local nodeId = params.node_id
    if not nodeId then
        return nil, "Missing 'node_id' parameter"
    end

    local allocate = params.allocate
    if allocate == nil then
        allocate = true
    end

    -- AllocNode/DeallocNode expect the node OBJECT, not the id. They also
    -- auto-path (AllocNode allocates the whole shortest path) and rebuild
    -- dependencies, so the tree stays valid and connected.
    local node = activeBuild.spec.nodes[nodeId]
    if not node then
        return nil, "Unknown node id: " .. tostring(nodeId)
    end

    if allocate then
        if not node.path and not node.alloc then
            return nil, "Node " .. tostring(nodeId) .. " is not reachable from the allocated tree"
        end
        activeBuild.spec:AllocNode(node)
    else
        activeBuild.spec:DeallocNode(node)
    end

    activeBuild.spec:AddUndoState()
    activeBuild.buildFlag = true
    triggerUpdate()

    return {
        success = true,
        allocated_points = activeBuild.spec:CountAllocNodes()
    }
end

-------------------------------------------------------------------------------
-- ITEM COMMANDS
-------------------------------------------------------------------------------

-- Get equipped items
function MCPCommands.get_items(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    if not activeBuild.itemsTab then
        return nil, "Build has no itemsTab"
    end

    local items = {}
    local slots = activeBuild.itemsTab.slots or {}

    for slotName, slot in pairs(slots) do
        local item = slot.selItemId and activeBuild.itemsTab.items[slot.selItemId]
        if item then
            table.insert(items, {
                slot = slotName,
                id = slot.selItemId,
                name = item.name,
                rarity = item.rarity,
                base = item.baseName,
                levelReq = item.levelReq,
                -- Include raw item text for full details
                rawText = item.raw
            })
        end
    end

    return { items = items }
end

-------------------------------------------------------------------------------
-- CONFIG COMMANDS
-------------------------------------------------------------------------------

-- Set custom modifiers
function MCPCommands.set_custom_mods(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    if not activeBuild.configTab then
        return nil, "Build has no configTab"
    end

    local mods = params.mods or ""
    -- BuildModList is a PoB rebuild helper: defer it out of the poll prologue.
    MCPBridge.defer(function()
        activeBuild.configTab.input.customMods = mods
        activeBuild.configTab:BuildModList()
        activeBuild.buildFlag = true
    end)

    return { success = true, applied = "deferred" }
end

-- Get custom modifiers
function MCPCommands.get_custom_mods(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    if not activeBuild.configTab then
        return nil, "Build has no configTab"
    end

    return {
        mods = activeBuild.configTab.input.customMods or ""
    }
end

-- Set configuration option
function MCPCommands.set_config(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    if not activeBuild.configTab then
        return nil, "Build has no configTab"
    end

    for key, value in pairs(params) do
        if key ~= "method" and key ~= "id" then
            activeBuild.configTab.input[key] = value
        end
    end

    activeBuild.configTab:BuildModList()
    triggerUpdate()

    return { success = true }
end

-- Get configuration options
function MCPCommands.get_config(params)
    local activeBuild = getActiveBuild()
    if not activeBuild then
        return nil, "No build loaded"
    end

    if not activeBuild.configTab then
        return nil, "Build has no configTab"
    end

    return {
        config = activeBuild.configTab.input
    }
end

-------------------------------------------------------------------------------
-- COMPARISON COMMANDS
-------------------------------------------------------------------------------

-- Compare current build with a snapshot (returns stat differences)
function MCPCommands.compare_with_snapshot(params)
    local activeBuild, err = ensureBuildReady()
    if not activeBuild then
        return nil, err
    end

    if not activeBuild.calcsTab then
        return nil, "Build has no calcsTab - calculation not available"
    end

    local snapshot = params.snapshot
    if not snapshot then
        return nil, "Missing 'snapshot' parameter (previous calcs)"
    end

    local current = MCPCommands.get_calcs({})
    if not current then
        return nil, "Failed to get current calculations"
    end

    local diff = {}
    for key, value in pairs(current) do
        if type(value) == "number" and snapshot[key] then
            local oldVal = snapshot[key]
            local delta = value - oldVal
            local pct = oldVal ~= 0 and (delta / oldVal * 100) or 0
            if math.abs(delta) > 0.001 then
                diff[key] = {
                    old = oldVal,
                    new = value,
                    delta = delta,
                    percent = pct
                }
            end
        end
    end

    return { diff = diff }
end

-------------------------------------------------------------------------------
-- CHARACTER IMPORT (Path of Exile API) — drives PoB's own ImportTab so the MCP
-- can import a character without touching the mouse/UI. Async downloads finish
-- on later frames, so the client polls import_get_state between steps.
-------------------------------------------------------------------------------

-- Kick off the character-list download for the current account/realm.
function MCPCommands.import_download_list(params)
    local b = getActiveBuild()
    if not b or not b.importTab then return nil, "No build/importTab" end
    b.importTab:DownloadCharacterList()
    return { success = true }
end

-- Poll import state: mode, status text, and the retrieved character list.
function MCPCommands.import_get_state(params)
    local b = getActiveBuild()
    if not b or not b.importTab then return nil, "No build/importTab" end
    local it = b.importTab
    local chars = {}
    if it.controls and it.controls.charSelect and it.controls.charSelect.list then
        for i, entry in ipairs(it.controls.charSelect.list) do
            table.insert(chars, { index = i, name = entry.label, detail = entry.detail })
        end
    end
    local status = it.charImportStatus
    if type(status) == "function" then status = "(dynamic)" end
    return {
        mode = it.charImportMode,
        status = tostring(status),
        sel_index = it.controls and it.controls.charSelect and it.controls.charSelect.selIndex,
        characters = chars
    }
end

-- Select a character by name from the retrieved list.
function MCPCommands.import_select_char(params)
    local b = getActiveBuild()
    if not b or not b.importTab then return nil, "No build/importTab" end
    local it = b.importTab
    if not (it.controls and it.controls.charSelect and it.controls.charSelect.list) then
        return nil, "No character list (call import_download_list first)"
    end
    local name = params.name
    for i, entry in ipairs(it.controls.charSelect.list) do
        if entry.label == name then
            it.controls.charSelect.selIndex = i
            return { success = true, selected = name, index = i }
        end
    end
    return nil, "Character not found: " .. tostring(name)
end

-- Run an import for the selected character. what = "tree" or "items".
-- Import "tree" BEFORE "items": importing a passive tree while a minion skill
-- is the main skill crashes PoB (RefreshSkillSelectControls -> nil minion list).
function MCPCommands.import_run(params)
    local b = getActiveBuild()
    if not b or not b.importTab then return nil, "No build/importTab" end
    local what = params.what
    if what == "tree" then
        b.importTab:DownloadPassiveTree()
    elseif what == "items" then
        b.importTab:DownloadItems()
    else
        return nil, "what must be 'tree' or 'items'"
    end
    b.buildFlag = true
    return { success = true, started = what }
end

-- Replace an existing socket group's gems IN PLACE (keeps the group's slot and
-- the rest of the build, e.g. corpse-generating skills, intact). Lets the MCP
-- swap support gems and measure the delta without clearing the whole build.
-- params.gems = list of { name, level, quality }.
function MCPCommands.set_group_gems(params)
    local b = getActiveBuild()
    if not b or not b.skillsTab then return nil, "No build/skillsTab" end
    local group = b.skillsTab.socketGroupList[params.index]
    if not group then return nil, "Invalid group index: " .. tostring(params.index) end
    if type(params.gems) ~= "table" then return nil, "Missing 'gems' list" end

    local newGems = {}
    for _, g in ipairs(params.gems) do
        table.insert(newGems, {
            nameSpec = g.name,
            level = g.level or 20,
            quality = g.quality or 0,
            enabled = true,
            count = 1,
            enableGlobal1 = true,
            enableGlobal2 = true,
        })
    end
    -- Apply on the deferred queue: ProcessSocketGroup is a PoB rebuild helper and
    -- must not be called from the poll prologue (see bridge.lua header).
    group.gemList = newGems
    MCPBridge.defer(function()
        b.skillsTab:ProcessSocketGroup(group)
        b.buildFlag = true
    end)

    -- Resolution happens inside the deferred ProcessSocketGroup, i.e. after this
    -- reply is already on the wire, so we cannot report gemData validity here --
    -- doing so would always read nil and look like every gem failed. Callers should
    -- confirm with get_skills (or just read the recalculated stats) on a later frame.
    local requested = {}
    for _, gem in ipairs(group.gemList) do
        table.insert(requested, { name = gem.nameSpec, level = gem.level, quality = gem.quality })
    end
    return {
        success = true,
        index = params.index,
        applied = "deferred",
        gems = requested,
        note = "names resolve on apply; verify with get_skills next frame",
    }
end

-- Set a configTab input by key (e.g. corpse life / enemy settings for Detonate
-- Dead). params: { key = "...", value = <bool|number|string> }.
function MCPCommands.set_config_input(params)
    local b = getActiveBuild()
    if not b or not b.configTab then return nil, "No build/configTab" end
    local k, v = params.key, params.value
    MCPBridge.defer(function()
        b.configTab.input[k] = v
        b.configTab:BuildModList()
        b.buildFlag = true
    end)
    return { success = true, key = k, value = v, applied = "deferred" }
end

-------------------------------------------------------------------------------
-- INTROSPECTION & PRECISION (the things a reasoning agent wants: see PoB's
-- real state, target the exact skill/part, and not guess at config/fields).
-------------------------------------------------------------------------------

-- Set which active skill (+ skill part) within a group is the DISPLAYED main
-- skill. Essential for trigger / multi-stage skills (e.g. Bitter Dead's Cold
-- DoT): PoB otherwise displays the trigger gem (0 damage) instead of the real
-- damaging skill, so its DPS reads as 0.
function MCPCommands.set_displayed_skill(params)
    local b = getActiveBuild()
    if not b or not b.skillsTab then return nil, "No build/skillsTab" end
    local group = b.skillsTab.socketGroupList[params.group_index]
    if not group then return nil, "Invalid group index: " .. tostring(params.group_index) end
    b.mainSocketGroup = params.group_index
    if params.skill_index then group.mainActiveSkill = params.skill_index end
    if params.part and group.displaySkillList and group.displaySkillList[group.mainActiveSkill or 1] then
        local inst = group.displaySkillList[group.mainActiveSkill or 1].activeEffect.srcInstance
        if inst then inst.skillPart = params.part end
    end
    b.buildFlag = true
    triggerUpdate()
    return { success = true, group = params.group_index, mainActiveSkill = group.mainActiveSkill }
end

-- List the active skills (and their parts) in a group, so the caller knows what
-- set_displayed_skill can target.
function MCPCommands.get_skill_parts(params)
    local b = getActiveBuild()
    if not b or not b.skillsTab then return nil, "No build/skillsTab" end
    local group = b.skillsTab.socketGroupList[params.group_index]
    if not group then return nil, "Invalid group index" end
    local skills = {}
    if group.displaySkillList then
        for i, activeSkill in ipairs(group.displaySkillList) do
            local ge = activeSkill.activeEffect and activeSkill.activeEffect.grantedEffect
            local parts = {}
            if ge and ge.parts then
                for pi, part in ipairs(ge.parts) do table.insert(parts, part.name or ("part" .. pi)) end
            end
            table.insert(skills, {
                index = i,
                name = ge and ge.name,
                is_main = (i == group.mainActiveSkill),
                parts = parts,
                skillTypes = activeSkill.skillTypes and true or nil
            })
        end
    end
    return { group = params.group_index, mainActiveSkill = group.mainActiveSkill, skills = skills }
end

-- Return ONLY the requested output fields (avoids dumping the whole mainOutput
-- table, which overflowed get_full_calcs). keys = list of field names; omit for
-- a curated damage/DoT default set.
function MCPCommands.get_output(params)
    local activeBuild, err = ensureBuildReady()
    if not activeBuild then return nil, err end
    local out = activeBuild.calcsTab.mainOutput or {}
    local result = {}
    local keys = params.keys
    if not keys then
        keys = { "TotalDPS","CombinedDPS","FullDPS","AverageDamage","Speed","CritChance",
                 "WithDotDPS","TotalDotDPS","TotalDot","BleedDPS","IgniteDPS","PoisonDPS",
                 "Life","EnergyShield","Mana" }
    end
    -- mainOutput values can be tables holding functions/cycles; dkjson hangs on
    -- those and wedges the bridge. The module's own rule: sanitise raw output.
    for _, k in ipairs(keys) do result[k] = jsonSafe(out[k], 0, {}) end
    return result
end

-- Full DPS: PoB's sum of all damaging skills incl. triggered DoTs, with the
-- contributing per-skill list (name / dps / source / part) when available.
function MCPCommands.get_full_dps(params)
    local activeBuild, err = ensureBuildReady()
    if not activeBuild then return nil, err end
    local out = activeBuild.calcsTab.mainOutput or {}
    local skills = {}
    local list = out.SkillDPS or out.FullDPSSkills
    if type(list) == "table" then
        for _, sk in ipairs(list) do
            table.insert(skills, {
                name = sk.stat or sk.name,
                dps = sk.dps,
                part = sk.skillPart,
                source = sk.source or sk.trigger
            })
        end
    end
    return { FullDPS = out.FullDPS, TotalDPS = out.TotalDPS, ConfigError = out.FullDPS == nil and "FullDPS not enabled? toggle 'Calculate Full DPS' in config" or nil, skills = skills }
end

-- Enumerate PoB's available config options (var / type / label) + current value
-- so the caller can discover settings (e.g. corpse life, enemy level) instead of
-- grepping PoB's source. Optional filter substring.
function MCPCommands.list_config_options(params)
    local b = getActiveBuild()
    if not b or not b.configTab then return nil, "No build/configTab" end
    local ok, varList = pcall(LoadModule, "Modules/ConfigOptions")
    if not ok or type(varList) ~= "table" then return nil, "Could not load ConfigOptions" end
    local filter = params.filter and params.filter:lower() or nil
    local opts = {}
    for _, v in ipairs(varList) do
        if type(v) == "table" and v.var and v.label then
            local label = tostring(v.label):gsub("%^%x%x%x%x%x%x", ""):gsub("%^%d", "")
            if not filter or label:lower():find(filter, 1, true) or v.var:lower():find(filter, 1, true) then
                table.insert(opts, { var = v.var, type = v.type, label = label, value = b.configTab.input[v.var] })
            end
        end
        if #opts >= (params.limit or 400) then break end
    end
    return { count = #opts, options = opts }
end

-- Reset the passive tree to just the class start (keeps class/ascendancy start
-- nodes). For a clean respec — then reallocate with set_passive_node.
function MCPCommands.reset_tree(params)
    local b = getActiveBuild()
    if not b or not b.spec then return nil, "No build/spec" end
    b.spec:ResetNodes()
    b.spec:BuildAllDependsAndPaths()
    b.spec:AddUndoState()
    b.buildFlag = true
    triggerUpdate()
    return { success = true, allocated_points = b.spec:CountAllocNodes() }
end

-- Explain WHY an output stat is what it is: PoB's modifier-by-modifier
-- breakdown (the lines shown when you click a stat in the Calcs tab). This is
-- the reasoning-transparency capability: instead of trusting a number, see how
-- it was derived. params.stat = e.g. "Life", "AverageDamage", "TotalDPS".
function MCPCommands.get_stat_breakdown(params)
    local b = getActiveBuild()
    if not b or not b.calcsTab then return nil, "No build/calcsTab" end
    -- Breakdowns live on the CALCS-mode env (calcsEnv), not mainEnv. BuildOutput
    -- builds both, so any prior get_calcs/recalc populates this.
    local env = b.calcsTab.calcsEnv
    if not env or not env.player then return nil, "No calc env (call get_calcs/recalc first)" end
    local actor = (params.minion and env.minion) or env.player
    -- Breakdowns live in two places: defensive/attribute stats (Life, resists)
    -- on the actor breakdown; offensive stats (AverageHit, AverageDamage, DPS)
    -- on the MAIN SKILL breakdown. Check both.
    local sources = {}
    if actor and actor.breakdown then table.insert(sources, actor.breakdown) end
    if actor and actor.mainSkill and actor.mainSkill.breakdown then
        table.insert(sources, actor.mainSkill.breakdown)
    end
    if #sources == 0 then return nil, "No breakdown data on actor" end

    local bd
    for _, src in ipairs(sources) do
        if src[params.stat] then bd = src[params.stat]; break end
    end
    if not bd then
        local avail = {}
        for _, src in ipairs(sources) do
            for k in pairs(src) do
                if type(k) == "string" then table.insert(avail, k) end
            end
        end
        table.sort(avail)
        return { stat = params.stat, found = false,
                 hint = "no breakdown for that exact key; pick one of available[]",
                 available = avail }
    end

    -- Flatten the breakdown structure into readable lines. Walk ONLY this stat's
    -- breakdown table (bounded), depth-limited, stripping PoB colour codes.
    local function clean(s)
        return (s:gsub("%^%x%x%x%x%x%x", ""):gsub("%^%d", ""))
    end
    local lines = {}
    local seen = {}
    local function walk(t, depth)
        if depth > 5 or seen[t] then return end
        seen[t] = true
        for _, key in ipairs({ "label", "name", "desc", "text" }) do
            if type(t[key]) == "string" and #t[key] > 0 then
                table.insert(lines, clean(t[key]))
            end
        end
        for _, v in ipairs(t) do
            if type(v) == "string" then
                if #v > 0 then table.insert(lines, clean(v)) end
            elseif type(v) == "table" then
                walk(v, depth + 1)
            end
        end
    end
    walk(bd, 0)
    return { stat = params.stat, found = true, lines = lines }
end

ConPrintf("[MCPBridge] Commands module loaded (%d commands)", (function()
    local count = 0
    for _ in pairs(MCPCommands) do count = count + 1 end
    return count
end)())
