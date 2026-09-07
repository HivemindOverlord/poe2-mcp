-- MCP Bridge for Path of Building (PoE2)
-- https://github.com/HivemindOverlord/poe2-mcp
--
-- v2.0.0 -- transport rewritten for current PoB (verified against 0.23.1).
--
-- WHY THIS WAS REWRITTEN
-- The 1.1.0 transport did accept + receive + send inline inside one frame, using a
-- blocking-with-timeout socket, and ignored the return value of client:send(). On
-- current PoB that stalls the render loop outright: a large reply (get_full_calcs
-- returns ~800 keys) exceeds the socket buffer, send() partial-writes, the unsent
-- remainder is dropped, and the peer waits forever for a terminator that never
-- arrives -- leaving sockets in CloseWait and the frame loop wedged at ~0% CPU.
--
-- This version never blocks. Sockets are strictly non-blocking and each connection
-- is a small state machine advanced one slice per frame:
--     accept -> READING (accumulate until newline) -> dispatch -> WRITING (drain
--     partial sends across frames) -> close
-- so no single frame can ever wait on a peer.
--
-- PoB 0.23.1 integration notes (read from Modules/Build.lua):
--   * buildMode:OnFrame handles self.buildFlag SYNCHRONOUSLY -- it calls
--     calcsTab:BuildOutput() then RefreshStatList() in the same frame. There is no
--     build coroutine, so setting buildFlag is safe; what is NOT safe is calling
--     PoB rebuild helpers (e.g. configTab:BuildModList()) directly from our hook,
--     which runs before main:OnFrame. Mutations are therefore queued and applied
--     after PoB's own OnFrame has completed (see runDeferred).

local scriptPath = GetScriptPath()
local addonPath = scriptPath .. "/Addons/MCPBridge"

local socket = require("socket")
local dkjson = require("dkjson")

dofile(addonPath .. "/config.lua")
dofile(addonPath .. "/commands.lua")

local config = MCPConfig

local MCPBridge = {
    server = nil,
    running = false,
    lastError = nil,
    startTime = nil,
    requestCount = 0,
    clients = {},          -- active connection state machines
    pendingActions = {},   -- queued mutations, drained after PoB's OnFrame
    inPoll = false,
    inDeferred = false,
}

-- Bounded per-frame work so a big reply can never monopolise the render loop.
local MAX_ACCEPTS_PER_FRAME = 4
local MAX_CLIENTS = 16
local WRITE_CHUNK = 32768
local CLIENT_TIMEOUT_SEC = 30

-------------------------------------------------------------------------------
-- Logging: ConPrintf only reaches PoB's in-app console, which is useless for
-- diagnosing a wedge from outside. Mirror to a file next to the addon.
-------------------------------------------------------------------------------
local logPath = addonPath .. "/mcpbridge.log"
local function log(fmt, ...)
    local ok, msg = pcall(string.format, fmt, ...)
    if not ok then msg = tostring(fmt) end
    ConPrintf("[MCPBridge] %s", msg)
    if config.LOG_TO_FILE then
        local f = io.open(logPath, "a")
        if f then
            f:write(os.date("%H:%M:%S "), msg, "\n")
            f:close()
        end
    end
end
MCPBridge.log = log

-------------------------------------------------------------------------------
-- Deferred mutation queue
-------------------------------------------------------------------------------
function MCPBridge.defer(fn)
    table.insert(MCPBridge.pendingActions, fn)
end

function MCPBridge.runDeferred()
    if MCPBridge.inDeferred or #MCPBridge.pendingActions == 0 then return end
    MCPBridge.inDeferred = true
    local queue = MCPBridge.pendingActions
    MCPBridge.pendingActions = {}
    for _, fn in ipairs(queue) do
        local ok, err = pcall(fn)
        if not ok then log("deferred action error: %s", tostring(err)) end
    end
    MCPBridge.inDeferred = false
end

-------------------------------------------------------------------------------
-- Server lifecycle
-------------------------------------------------------------------------------
function MCPBridge.start()
    if MCPBridge.running then return true end

    local server, err = socket.bind(config.HOST, config.PORT)
    if not server then
        for offset = 1, 3 do
            server, err = socket.bind(config.HOST, config.PORT + offset)
            if server then
                log("port %d busy, using %d", config.PORT, config.PORT + offset)
                config.PORT = config.PORT + offset
                break
            end
        end
    end
    if not server then
        MCPBridge.lastError = err
        log("failed to bind: %s", tostring(err))
        return false
    end

    server:settimeout(0)  -- strictly non-blocking accept
    MCPBridge.server = server
    MCPBridge.running = true
    MCPBridge.startTime = os.time()
    log("listening on %s:%d (v%s)", config.HOST, config.PORT, config.VERSION)
    return true
end

function MCPBridge.stop()
    for _, c in ipairs(MCPBridge.clients) do
        pcall(function() c.sock:close() end)
    end
    MCPBridge.clients = {}
    if MCPBridge.server then
        pcall(function() MCPBridge.server:close() end)
        MCPBridge.server = nil
    end
    MCPBridge.running = false
    log("stopped")
end

-------------------------------------------------------------------------------
-- Request dispatch (pure: takes a request line, returns a response string)
-------------------------------------------------------------------------------
local function encodeError(id, code, message)
    local ok, s = pcall(dkjson.encode, {
        jsonrpc = "2.0", id = id,
        error = { code = code, message = tostring(message) },
    })
    if not ok or type(s) ~= "string" then
        return '{"jsonrpc":"2.0","id":null,"error":{"code":-32603,"message":"encode failed"}}'
    end
    return s
end

local function dispatch(line)
    local okDecode, command = pcall(dkjson.decode, line)
    if not okDecode or type(command) ~= "table" then
        return encodeError(nil, -32700, "Parse error: invalid JSON")
    end
    if not command.method then
        return encodeError(command.id, -32600, "Invalid request: missing method")
    end

    MCPBridge.requestCount = MCPBridge.requestCount + 1
    if config.LOG_COMMANDS then
        log("-> %s (id=%s)", tostring(command.method), tostring(command.id))
    end

    local handler = MCPCommands[command.method]
    if not handler then
        return encodeError(command.id, -32601, "Method not found: " .. tostring(command.method))
    end

    local ok, result, errMsg = pcall(handler, command.params or {})
    if not ok then
        log("!! handler %s threw: %s", tostring(command.method), tostring(result))
        return encodeError(command.id, -32603, "Internal error: " .. tostring(result))
    end
    if errMsg then
        return encodeError(command.id, -32000, errMsg)
    end

    -- Encoding is the other historic wedge point: dkjson throws or spins on
    -- functions/cycles. Guard it, and never emit a half-serialised body.
    local okEnc, encoded = pcall(dkjson.encode, { jsonrpc = "2.0", id = command.id, result = result })
    if not okEnc or type(encoded) ~= "string" then
        log("!! encode failed for %s: %s", tostring(command.method), tostring(encoded))
        return encodeError(command.id, -32603, "Result encoding failed (non-serialisable value)")
    end
    return encoded
end

-------------------------------------------------------------------------------
-- Per-frame connection pump
-------------------------------------------------------------------------------
local function advanceClient(c, now)
    if now - c.started > CLIENT_TIMEOUT_SEC then
        log("client timed out in state %s", c.state)
        return false
    end

    if c.state == "READING" then
        -- Non-blocking read; "timeout" simply means nothing yet, try next frame.
        local chunk, err, partial = c.sock:receive(4096)
        local data = chunk or partial
        if data and #data > 0 then
            c.inbuf = c.inbuf .. data
        end
        if err == "closed" then return false end

        local nl = c.inbuf:find("\n", 1, true)
        if nl then
            local line = c.inbuf:sub(1, nl - 1):gsub("\r$", "")
            c.outbuf = dispatch(line) .. "\n"
            c.sent = 0
            c.state = "WRITING"
        elseif #c.inbuf > 1048576 then
            c.outbuf = encodeError(nil, -32600, "Request too large") .. "\n"
            c.sent = 0
            c.state = "WRITING"
        end
    end

    if c.state == "WRITING" then
        -- send() returns the index of the last byte written; on a partial write it
        -- reports how far it got in the 3rd return. Resume from there next frame.
        local stop = math.min(c.sent + WRITE_CHUNK, #c.outbuf)
        local sent, err, lastSent = c.sock:send(c.outbuf, c.sent + 1, stop)
        if sent then
            c.sent = sent
        elseif err == "timeout" and lastSent then
            c.sent = lastSent
        elseif err == "closed" then
            return false
        end
        if c.sent >= #c.outbuf then
            return false  -- complete; close cleanly
        end
    end

    return true
end

function MCPBridge.poll()
    if not MCPBridge.running or not MCPBridge.server then return end
    -- A rebuild can pump frames; never re-enter.
    if MCPBridge.inPoll or MCPBridge.inDeferred then return end
    MCPBridge.inPoll = true

    local now = os.time()

    for _ = 1, MAX_ACCEPTS_PER_FRAME do
        if #MCPBridge.clients >= MAX_CLIENTS then break end
        local client = MCPBridge.server:accept()
        if not client then break end
        client:settimeout(0)  -- strictly non-blocking
        table.insert(MCPBridge.clients, {
            sock = client, state = "READING", inbuf = "", outbuf = "", sent = 0, started = now,
        })
    end

    for i = #MCPBridge.clients, 1, -1 do
        local c = MCPBridge.clients[i]
        local ok, keep = pcall(advanceClient, c, now)
        if not ok then
            log("!! client pump error: %s", tostring(keep))
            keep = false
        end
        if not keep then
            pcall(function() c.sock:close() end)
            table.remove(MCPBridge.clients, i)
        end
    end

    MCPBridge.inPoll = false
end

function MCPBridge.getStatus()
    return {
        running = MCPBridge.running,
        port = config.PORT,
        host = config.HOST,
        uptime = MCPBridge.startTime and (os.time() - MCPBridge.startTime) or 0,
        requests = MCPBridge.requestCount,
        clients = #MCPBridge.clients,
        lastError = MCPBridge.lastError,
        version = config.VERSION,
    }
end

-------------------------------------------------------------------------------
-- Frame hook
-------------------------------------------------------------------------------
local originalOnFrame = launch.OnFrame
launch.OnFrame = function(self)
    if config.ENABLED then pcall(MCPBridge.poll) end

    if originalOnFrame then originalOnFrame(self) end

    -- Apply queued mutations only after PoB's own frame is done, so its tabs are
    -- in a consistent state and buildFlag schedules a clean rebuild next frame.
    if config.ENABLED then pcall(MCPBridge.runDeferred) end
end

local originalOnExit = launch.OnExit
launch.OnExit = function(self)
    pcall(MCPBridge.stop)
    if originalOnExit then originalOnExit(self) end
end

if config.AUTO_START and config.ENABLED then
    local startAttempted = false
    local realPoll = MCPBridge.poll
    MCPBridge.poll = function()
        if not startAttempted then
            startAttempted = true
            MCPBridge.start()
        end
        if MCPBridge.running then
            MCPBridge.poll = realPoll
            return realPoll()
        end
    end
end

_G.MCPBridge = MCPBridge
log("module loaded (v%s, transport v2)", config.VERSION)
