# Path of Exile 2 Build Optimizer MCP

A comprehensive Model Context Protocol (MCP) server for Path of Exile 2 character analysis and optimization. Provides 34 MCP tools for AI-powered build analysis, gear optimization, passive tree recommendations, and build scoring through Claude Desktop.

## Overview

This project provides an MCP server that integrates with Claude Desktop to offer intelligent character analysis and optimization through natural language queries. It fetches data from poe.ninja, official PoE API, and maintains a local game database with skill gems, passive trees, and item data.

## Key Features

### 34 MCP Tools Available

**Character Analysis**
- `analyze_character` - Comprehensive character analysis with defensive stats, skills, gear
- `import_poe_ninja_url` - Import characters directly from poe.ninja profile URLs
- `nl_query` - Natural language queries about your build
- `detect_weaknesses` - Identify build vulnerabilities and issues
- `compare_to_top_players` - Compare your build to ladder leaders

**Calculators**
- `calculate_dps` - Damage per second calculations
- `calculate_ehp` - Effective HP with all defensive layers
- `analyze_spirit` - Spirit resource management (PoE2 system)
- `analyze_stun` - Stun threshold mechanics
- `analyze_damage_scaling` - Damage scaling efficiency

**Optimization**
- `optimize_gear` - Budget-aware gear upgrade recommendations
- `optimize_passives` - Passive tree pathing and node selection
- `optimize_skills` - Gem setup optimization
- `find_best_supports` - Support gem recommendations
- `optimize_metrics` - Overall build optimization

**Comparison**
- `compare_builds` - Compare two builds
- `compare_items` - Compare item stats
- `evaluate_upgrade` - Evaluate potential upgrades

**Validation (New in PR #16)**
- `validate_support_combination` - Check if supports work together
- `inspect_support_gem` - View complete support gem data
- `inspect_spell_gem` - View complete spell gem data
- `list_all_supports` - Enumerate available support gems
- `list_all_spells` - Enumerate available spell gems

**Debugging**
- `trace_support_selection` - Debug support gem selection logic
- `trace_dps_calculation` - Step-by-step DPS calculation breakdown
- `validate_build_constraints` - Validate build against game rules

**Trade & PoB**
- `search_items` - Search item database
- `search_trade_items` - Search official trade site (requires auth)
- `import_pob` - Import Path of Building codes
- `export_pob` - Export to PoB format

**Knowledge**
- `explain_mechanic` - Explain PoE2 game mechanics
- `check_content_readiness` - Check boss/content viability
- `health_check` - Server status
- `clear_cache` - Clear cached data

### Local Game Database
- 4,975+ passive tree nodes with connections
- 335+ ascendancy nodes (99% coverage)
- Complete skill gem database from PoB2
- Support gem effects and interactions
- Base items and unique items

### Multi-Source Character Fetching
1. poe.ninja API (primary)
2. poe.ninja SSE/model API (fallback)
3. Official PoE ladder API (fallback)
4. Direct HTML scraping (last resort)

## Quick Start

### Prerequisites
- Python 3.9+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/HivemindOverlord/poe2-mcp.git
cd poe2-mcp

# Install Python dependencies
pip install -r requirements.txt

# Launch the MCP server (handles database initialization)
python launch.py
```

### Claude Desktop Integration

Add to your Claude Desktop configuration (`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "poe2-optimizer": {
      "command": "python",
      "args": ["C:/path/to/poe2-mcp/launch.py"],
      "env": {}
    }
  }
}
```

### Running the Server Standalone

```bash
# Recommended: Use launch script (handles setup)
python launch.py

# Or run directly
python src/mcp_server.py
```

## Trade API Authentication

The MCP server can search the official Path of Exile trade site to recommend gear upgrades. This requires authentication to prevent bot abuse.

### Automated Setup (Recommended - 2 Minutes)

```bash
# Install Playwright (one-time setup)
pip install playwright
playwright install chromium

# Run the authentication helper
python scripts/setup_trade_auth.py
```

**What happens:**
1. Browser opens to pathofexile.com/trade
2. You log in with your account (supports 2FA)
3. Script automatically detects login and extracts your session cookie
4. Cookie is saved to `.env` file
5. Done! Trade search now works

**See `TRADE_AUTH_SETUP_GUIDE.md` for:**
- Detailed step-by-step guide
- Troubleshooting common issues
- Security information
- Cookie expiration details

### Manual Setup (Fallback)

If the automated method doesn't work:

1. Visit https://www.pathofexile.com/trade in your browser
2. Log in to your account
3. Press F12 to open DevTools
4. Go to Application → Cookies → pathofexile.com
5. Find the `POESESSID` cookie
6. Copy its value (32-character string)
7. Add to your `.env` file: `POESESSID=your_cookie_value_here`

## Usage

### Via Web Interface

1. Navigate to `http://localhost:3000`
2. Enter your account name and character name
3. Click "Analyze Character"
4. Review recommendations and optimization suggestions

### Via MCP Protocol

```python
from mcp_client import PoE2MCPClient

async with PoE2MCPClient() as client:
    # Analyze character
    analysis = await client.analyze_character(
        account="YourAccount",
        character="YourCharacter"
    )

    # Get natural language recommendations
    response = await client.query(
        "How can I improve my boss damage while staying tanky?"
    )

    print(response)
```

### Via Command Line

```bash
# Quick character analysis
python cli.py analyze --account YourAccount --character YourCharacter

# Natural language query
python cli.py query "What gear upgrades should I prioritize?"

# Build comparison
python cli.py compare build1.json build2.json

# Export to Path of Building
python cli.py export --account YourAccount --character YourCharacter --output build.pob
```

## Architecture

### Core Components

```
src/
├── mcp_server.py           # Main MCP server
├── api/
│   ├── poe_api.py          # Official PoE API client
│   ├── poe2db_scraper.py   # poe2db.tw data scraper
│   ├── rate_limiter.py     # API rate limiting
│   └── cache_manager.py    # Multi-tier caching
├── database/
│   ├── models.py           # SQLAlchemy models
│   ├── manager.py          # Database manager
│   └── migrations/         # Alembic migrations
├── calculator/
│   ├── damage_calc.py      # DPS calculations
│   ├── defense_calc.py     # Defense calculations
│   ├── modifier_calc.py    # Modifier calculations
│   └── build_scorer.py     # Build quality scoring
├── optimizer/
│   ├── gear_optimizer.py   # Gear optimization
│   ├── passive_optimizer.py # Passive tree optimization
│   ├── skill_optimizer.py  # Skill setup optimization
│   └── trade_advisor.py    # Trade recommendations
├── ai/
│   ├── query_handler.py    # Natural language processing
│   ├── recommendation_engine.py # AI recommendations
│   └── context_manager.py  # Conversation context
└── pob/
    ├── importer.py         # PoB import
    ├── exporter.py         # PoB export
    └── xml_parser.py       # PoB XML handling
```

### Web Interface

```
web/
├── src/
│   ├── components/
│   │   ├── CharacterImporter.tsx
│   │   ├── PassiveTree.tsx
│   │   ├── GearRecommendations.tsx
│   │   ├── BuildComparison.tsx
│   │   └── NLQueryInterface.tsx
│   ├── api/
│   │   └── client.ts       # API client
│   ├── state/
│   │   └── store.ts        # State management
│   └── utils/
│       └── calculations.ts  # Client-side calcs
├── public/
│   └── assets/             # Static assets
└── package.json
```

## Database Schema

### Core Tables

- **items**: All item bases and types
- **modifiers**: Item modifiers and their values
- **passive_nodes**: Passive tree nodes
- **passive_connections**: Tree node connections
- **skills**: Skill gems data
- **supports**: Support gem data
- **uniques**: Unique item data
- **ascendancies**: Ascendancy classes
- **crafting**: Crafting bench recipes

### User Tables

- **saved_builds**: User-saved builds
- **build_snapshots**: Historical build versions
- **optimization_history**: Past optimizations

## API Integration

### Official PoE API

- Character data retrieval
- Account information
- Ladder rankings (with rate limiting)
- Stash tab data (optional)

### Rate Limiting Strategy

```python
# Configurable rate limits
RATE_LIMITS = {
    'official_api': {
        'requests_per_minute': 10,
        'burst': 3,
        'backoff': 'exponential'
    },
    'poe2db': {
        'requests_per_minute': 30,
        'cache_duration': 3600  # 1 hour
    }
}
```

### Caching Strategy

1. **L1 Cache**: In-memory (5 minutes)
2. **L2 Cache**: Redis (1 hour)
3. **L3 Cache**: SQLite (persistent)

## AI Integration

### Natural Language Queries

```python
# Example queries
queries = [
    "How can I increase my lightning damage?",
    "What's the best chest armor for my budget?",
    "Should I respec for more defense?",
    "Which passive nodes give the most DPS?",
    "How do I transition to CI?",
    "What uniques work well with my build?"
]
```

### Context-Aware Responses

The AI maintains context about:
- Current character state
- Previous questions
- Build goals
- Budget constraints
- Playstyle preferences

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_calculator.py

# Run with coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Configuration

Configuration is managed via environment variables and `config.yaml`:

```yaml
# config.yaml
server:
  host: 127.0.0.1
  port: 8080
  workers: 4

database:
  url: sqlite:///data/poe2_optimizer.db
  pool_size: 10

api:
  poe_api_rate_limit: 10
  poe2db_rate_limit: 30
  enable_caching: true

ai:
  provider: anthropic  # or openai
  model: claude-sonnet-4-20250514
  max_tokens: 4096
  temperature: 0.7

web:
  port: 3000
  enable_build_sharing: true
  max_saved_builds_per_user: 50

features:
  enable_trade_integration: true
  enable_pob_export: true
  enable_ai_insights: true
```

## Security & Privacy

- **No Credential Storage**: Uses OAuth flow for PoE account access
- **Local-First**: All character data cached locally
- **Optional Cloud Sync**: Encrypted cloud backup (opt-in)
- **Rate Limit Enforcement**: Prevents API abuse
- **Data Encryption**: All saved builds encrypted at rest

## Performance

- **Sub-second Analysis**: Most character analyses complete in <500ms
- **Parallel Calculations**: Multi-threaded build calculations
- **Intelligent Caching**: Reduces API calls by 90%+
- **WebSocket Updates**: Real-time updates without polling
- **CDN Assets**: Static assets served via CDN

## Contributing

This is a personal project, but contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Roadmap

### Completed
- [x] MCP server foundation with 34 tools
- [x] Character analysis from poe.ninja
- [x] Local game database (passives, skills, items)
- [x] API integration with multi-tier fallback
- [x] EHP, Spirit, Stun calculators
- [x] DPS calculations
- [x] Gear/passive/skill optimization
- [x] Path of Building import/export
- [x] Trade site integration (optional)
- [x] Validation tools for AI recommendations
- [x] poe.ninja URL import

### In Progress
- [ ] Web interface MVP
- [ ] Complete ascendancy data from game files
- [ ] Support gem incompatibility database

### Future
- [ ] Build sharing
- [ ] Meta trend analysis
- [ ] Mobile companion app

## License

Private project for personal use.

## Credits

Built with data from:
- [poe.ninja](https://poe.ninja) - Character data, builds, and economy data
- [Path of Building (PoE2 Fork)](https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2) - Skill gems and passive tree data
- [Path of Grinding](https://pathofgrinding.com) - Passive tree node database
- Path of Exile 2 by Grinding Gear Games

---

**Built for the PoE2 community** | [Report Issues](https://github.com/HivemindOverlord/poe2-mcp/issues)
