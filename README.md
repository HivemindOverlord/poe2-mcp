# Path of Exile 2 Build Optimizer MCP

A Model Context Protocol (MCP) server for Path of Exile 2 character analysis and optimization. Provides 32 MCP tools for AI-powered build analysis, passive tree analysis, item mod validation, support gem validation, and Path of Building integration.

## What is This?

This is an **MCP server** - a backend service that gives AI assistants (like Claude, ChatGPT, Cursor, etc.) the ability to analyze your Path of Exile 2 characters and provide optimization recommendations.

**What it does:**
- Fetches your character data from poe.ninja
- Analyzes defensive stats, skills, gear, and passive tree
- Validates support gem combinations (prevents invalid recommendations)
- Inspects spell and support gem data
- Imports/exports Path of Building codes
- Compares your build to top ladder players
- Explains PoE2 game mechanics

**What you need:**
- An AI assistant that supports MCP (Claude Desktop, ChatGPT Desktop, Cursor, Windsurf, etc.)
- Python 3.9+ installed
- Your PoE2 character on poe.ninja (public profile)

## Quick Start

### 1. Install

```bash
git clone https://github.com/HivemindOverlord/poe2-mcp.git
cd poe2-mcp
pip install -r requirements.txt
```

### 2. Connect to Your AI Assistant

Choose your platform below:

---

## Claude Desktop Integration

### Option A: Manual Configuration (Recommended for Development)

Edit your Claude Desktop config file:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this server (replace the path with your actual installation path):

**Windows:**
```json
{
  "mcpServers": {
    "poe2-optimizer": {
      "command": "python",
      "args": ["C:\\Users\\YourName\\poe2-mcp\\launch.py"],
      "env": {}
    }
  }
}
```

**macOS/Linux:**
```json
{
  "mcpServers": {
    "poe2-optimizer": {
      "command": "python3",
      "args": ["/Users/YourName/poe2-mcp/launch.py"],
      "env": {}
    }
  }
}
```

Restart Claude Desktop. The server will appear in your MCP tools.

### Option B: Create a .mcpb Bundle (For Distribution)

MCP Bundles (.mcpb) allow one-click installation. This is **experimental for Python projects** because dependencies must be bundled.

```bash
# Install the bundle CLI
npm install -g @anthropic-ai/mcpb

# In the poe2-mcp directory
mcpb init    # Creates manifest.json (set server.type = "python")
mcpb pack    # Creates poe2-optimizer.mcpb
```

**Important for Python bundles:**
- You must bundle all dependencies in `server/lib/` or include a `venv/`
- Set `PYTHONPATH` in manifest's `mcp_config.env`
- Bundle size will be large (~100MB+ with dependencies)

**Bundle structure:**
```
poe2-optimizer.mcpb (ZIP)
├── manifest.json       # Bundle metadata (server.type = "python")
├── server/
│   ├── launch.py       # Entry point
│   ├── src/            # Source code
│   ├── data/           # Game database
│   └── lib/            # Bundled Python packages
└── icon.png (optional)
```

See [mcpb documentation](https://github.com/modelcontextprotocol/mcpb) for manifest.json format.

> **Recommendation:** For development, use manual configuration (Option A). Only create .mcpb bundles for distributing to end users who don't have Python installed.

---

## Other AI Platforms

MCP is an open standard supported by multiple AI platforms:

### OpenAI ChatGPT Desktop
ChatGPT desktop app supports MCP servers. Configuration varies by version - check OpenAI's documentation for current setup instructions.

### Cursor AI
Cursor supports MCP via SSE protocol. Add to your Cursor settings:
```json
{
  "mcp": {
    "servers": {
      "poe2-optimizer": {
        "command": "python",
        "args": ["/path/to/poe2-mcp/launch.py"]
      }
    }
  }
}
```

### Windsurf
Windsurf has a built-in MCP Plugin Store. You can either:
- Search for "poe2" in the plugin store (if published)
- Manually add the server path in settings

### Claude Code (CLI)
```bash
# In your project directory
claude mcp add poe2-optimizer python /path/to/poe2-mcp/launch.py
```

### Other Compatible Clients
- Zed Editor
- Replit
- Codeium
- Sourcegraph
- Microsoft Semantic Kernel
- Salesforce Agentforce

Check each platform's documentation for MCP server configuration.

---

## Available Tools (32 Registered)

Once connected, you can ask your AI assistant to use these tools:

### Character Analysis
| Tool | Description |
|------|-------------|
| `analyze_character` | Full character analysis (defenses, skills, gear, passives) |
| `import_poe_ninja_url` | Import character from poe.ninja URL directly |
| `compare_to_top_players` | Compare your build to ladder leaders |
| `analyze_passive_tree` | Analyze allocated passive nodes |

### Validation & Inspection
| Tool | Description |
|------|-------------|
| `validate_support_combination` | Check if support gems work together |
| `validate_build_constraints` | Validate build against game rules |
| `inspect_support_gem` | View complete support gem data |
| `inspect_spell_gem` | View complete spell gem data |
| `list_all_supports` | List all available support gems |
| `list_all_spells` | List all available spell gems |

### Passive Tree Data
| Tool | Description |
|------|-------------|
| `list_all_keystones` | List all keystones with full stats |
| `inspect_keystone` | Get complete keystone details by name |
| `list_all_notables` | List all notable passives with stats |
| `inspect_passive_node` | Get details for any passive node |

### Base Item Data
| Tool | Description |
|------|-------------|
| `list_all_base_items` | List all base item types |
| `inspect_base_item` | Get details for a specific base item |

### Item Mod Data
| Tool | Description |
|------|-------------|
| `inspect_mod` | Get complete details for a specific mod by ID |
| `list_all_mods` | List mods with filtering by type (PREFIX/SUFFIX/IMPLICIT) |
| `search_mods_by_stat` | Search for mods by keyword (e.g., "fire", "life") |
| `get_mod_tiers` | Show all tier variations of a mod family |
| `validate_item_mods` | Check if mods can legally exist together on an item |
| `get_available_mods` | List all mods available for a generation type |

### Path of Building
| Tool | Description |
|------|-------------|
| `import_pob` | Import Path of Building code |
| `export_pob` | Export build to PoB format |
| `get_pob_code` | Get PoB code for a character |

### Trade & Items
| Tool | Description |
|------|-------------|
| `search_items` | Search local item database |
| `search_trade_items` | Search official trade site (requires auth) |
| `setup_trade_auth` | Set up trade site authentication |

### Knowledge & Utility
| Tool | Description |
|------|-------------|
| `explain_mechanic` | Explain PoE2 game mechanics |
| `get_formula` | Get calculation formulas |
| `health_check` | Check server status |
| `clear_cache` | Clear cached data |

> **Note:** Additional tools (DPS calculator, EHP calculator, optimizers) have handlers implemented but are not yet registered. These may be enabled in future updates.

---

## Example Usage

Once configured, just talk to your AI naturally:

> "Analyze my character TomawarTheFourth from account Tomawar"

> "Import this poe.ninja URL: https://poe.ninja/poe2/builds/char/..."

> "Can I use Faster Projectiles and Slower Projectiles together?" (uses `validate_support_combination`)

> "Show me all support gems that work with projectiles" (uses `list_all_supports`)

> "What keystones are available for life builds?" (uses `list_all_keystones`)

> "Tell me about Chaos Inoculation" (uses `inspect_keystone`)

> "Compare my build to top Witchhunter players"

> "Explain how armor works in PoE2"

> "What prefixes can roll on items?" (uses `get_available_mods`)

> "Show me all tiers of the Strength mod" (uses `get_mod_tiers`)

> "Can Strength1 and Strength2 exist on the same item?" (uses `validate_item_mods`)

> "Search for fire resistance mods" (uses `search_mods_by_stat`)

The AI will use the appropriate tools automatically.

---

## Trade API Authentication (Optional)

For `search_trade_items` to work, you need to authenticate with pathofexile.com:

```bash
pip install playwright
playwright install chromium
python scripts/setup_trade_auth.py
```

This opens a browser for you to log in, then saves your session cookie.

---

## Local Game Database

The server includes a local database with:
- 4,975+ passive tree nodes
- 335+ ascendancy nodes (99% coverage)
- 14,269 item modifiers (2,252 prefixes, 2,037 suffixes, 8,930 implicits)
- Complete skill gem data from Path of Building
- Support gem effects and interactions
- Base items and unique items

Data is loaded from `data/` directory on startup.

---

## Architecture

```
poe2-mcp/
├── launch.py              # Entry point
├── src/
│   ├── mcp_server.py      # Main MCP server (32 tools registered)
│   ├── api/               # External API clients
│   │   ├── poe_ninja_api.py
│   │   ├── character_fetcher.py
│   │   └── rate_limiter.py
│   ├── analyzer/          # Analysis components
│   │   ├── character_analyzer.py
│   │   └── weakness_detector.py
│   ├── calculator/        # Numeric calculations
│   │   ├── ehp_calculator.py
│   │   ├── spirit_calculator.py
│   │   └── stun_calculator.py
│   ├── data/              # Data providers
│   │   ├── mod_data_provider.py
│   │   └── fresh_data_provider.py
│   ├── optimizer/         # Optimization engines
│   │   ├── gear_optimizer.py
│   │   └── gem_synergy_calculator.py
│   ├── parsers/           # Data parsers
│   │   ├── passive_tree_resolver.py
│   │   └── specifications/  # Datc64 format specifications
│   ├── knowledge/         # Game mechanics knowledge base
│   │   └── poe2_mechanics.py
│   └── database/          # SQLite database
│       ├── models.py
│       └── manager.py
├── data/                  # Game data files
│   ├── psg_passive_nodes.json
│   ├── poe2_support_gems_database.json
│   └── poe2_mods_extracted.json
└── tests/                 # Test suite
```

---

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Running the Server Directly
```bash
python launch.py
# or
python src/mcp_server.py
```

### Key Files
- `src/mcp_server.py` - MCP server with 32 registered tools
- `src/data/mod_data_provider.py` - Item mod data access layer
- `src/calculator/ehp_calculator.py` - EHP calculations
- `src/optimizer/gem_synergy_calculator.py` - Support gem logic
- `data/psg_passive_nodes.json` - Passive tree database
- `data/poe2_mods_extracted.json` - Item modifier database (14,269 mods)

---

## Troubleshooting

### "Server not found" in Claude Desktop
- Check the path in config is absolute (not relative)
- Ensure Python is in your PATH
- Try running `python launch.py` manually to see errors

### "No character found"
- Your character must be on poe.ninja (public ladder)
- Character name is case-sensitive
- Try the full poe.ninja URL with `import_poe_ninja_url`

### Tools return empty results
- Database may need initialization: `python launch.py` handles this
- Check `data/` directory exists with JSON files

---

## Credits

Data sources:
- [poe.ninja](https://poe.ninja) - Character data and builds
- [Path of Building (PoE2)](https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2) - Skill data
- [Path of Grinding](https://pathofgrinding.com) - Passive tree data

MCP Protocol:
- [Model Context Protocol](https://modelcontextprotocol.io)
- [mcpb Bundle Format](https://github.com/modelcontextprotocol/mcpb)

---

## License

Private project for personal use.

---

**[Report Issues](https://github.com/HivemindOverlord/poe2-mcp/issues)**
