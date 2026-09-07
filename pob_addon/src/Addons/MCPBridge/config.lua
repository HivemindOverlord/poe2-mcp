-- MCP Bridge Configuration
-- https://github.com/HivemindOverlord/poe2-mcp

-- Global (NOT local): commands.lua reads MCPConfig as a global, and bridge.lua
-- reads `local config = MCPConfig`. Declaring this local left both nil, which
-- silently aborted bridge.lua at the first config access (autostart block) and
-- meant the TCP server never bound. This is the fix that makes the bridge work.
MCPConfig = {}

-- Network settings
MCPConfig.HOST = "127.0.0.1"  -- Only accept local connections (security)
MCPConfig.PORT = 49085        -- Default port for MCP communication
MCPConfig.TIMEOUT = 0         -- Non-blocking (0 = immediate return)
MCPConfig.READ_TIMEOUT = 0.5  -- Seconds to wait for client data (kept short so a
                              -- slow/dead client can never freeze a PoB frame for long)

-- Feature flags
MCPConfig.ENABLED = true      -- Master enable/disable
MCPConfig.LOG_COMMANDS = true -- Log received commands to console
MCPConfig.AUTO_START = true   -- Start server automatically on PoB launch
MCPConfig.LOG_TO_FILE = false -- Also mirror the log to Addons/MCPBridge/mcpbridge.log.
                              -- Off by default; turn on when diagnosing, since ConPrintf
                              -- only reaches PoB's in-app console and is invisible to an
                              -- external client watching a hung bridge.

-- Version info
MCPConfig.VERSION = "2.0.0"
MCPConfig.MIN_POB_VERSION = "2.0.0"

return MCPConfig
