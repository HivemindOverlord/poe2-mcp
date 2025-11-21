# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Path of Exile 2 Build Optimizer MCP Server - Provides 26 MCP tools for AI-powered character analysis, gear optimization, passive tree recommendations, and build scoring through natural language queries. Integrates with official PoE API, poe.ninja, and maintains a local game database.

## Running and Testing

### Quick Start
```bash
# Launch the MCP server (recommended - handles setup automatically)
python launch.py

# Or run the server directly
python src/mcp_server.py
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_character_fetcher.py

# Run with verbose output
pytest -v

# Test specific character (uses live data)
python analyze_my_character.py
```

### Database Management
```bash
# Initialize database (automatic on first run)
python -c "from src.database.manager import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().initialize())"

# Populate with game data from poe2db.tw and poe.ninja
python scripts/populate_database.py

# Reinitialize database (drops all tables)
python scripts/reinit_database.py

# Scrape support gems
python scripts/scrape_poe2db_supports.py
```

### Trade API Authentication
```bash
# Install Playwright (one-time setup)
pip install playwright
playwright install chromium

# Run automated authentication helper
python scripts/setup_trade_auth.py
```

## Core Architecture

### MCP Server (src/mcp_server.py)
The 3260-line main server implements 26 MCP tools through handler methods:
- Tools registered in `_register_tools()` (line ~283)
- Each tool has a corresponding `async def _handle_TOOLNAME(self, args)` method (lines 1075-2702)
- All handlers return `List[types.TextContent]` and must catch exceptions (never raise to MCP layer)
- Server uses stdio communication protocol for Claude Desktop integration

### 26 MCP Tools Available
Core analysis: `analyze_character`, `nl_query`, `calculate_dps`, `detect_weaknesses`, `compare_to_top_players`
Optimization: `optimize_gear`, `optimize_passives`, `optimize_skills`, `optimize_metrics`, `find_best_supports`
Calculators: `calculate_ehp`, `analyze_spirit`, `analyze_stun`, `analyze_damage_scaling`
Comparison: `compare_builds`, `compare_items`, `evaluate_upgrade`
Trade: `search_items`, `search_trade_items`, `setup_trade_auth`
PoB: `import_pob`, `export_pob`, `get_pob_code`
Knowledge: `explain_mechanic`, `check_content_readiness`
System: `health_check`, `clear_cache`

### Data Flow Architecture
```
User Query → MCP Tool Handler → Component Layer → Data Layer → Response

Component Layers:
1. API Layer (src/api/): External data fetching
   - character_fetcher.py: Multi-source fallback (poe.ninja → SSE API → official API → HTML scrape)
   - poe_ninja_api.py: Ladder, builds, economy data
   - trade_api.py: Official trade site integration
   - rate_limiter.py: Token bucket + adaptive backoff
   - cache_manager.py: L1 (memory) → L2 (Redis optional) → L3 (SQLite)

2. Analyzer Layer (src/analyzer/): Intelligence and insights
   - character_analyzer.py: Overall character evaluation
   - weakness_detector.py: Identifies build vulnerabilities
   - gear_evaluator.py: Item quality assessment
   - top_player_fetcher.py: Meta comparison
   - character_comparator.py: Build vs build analysis
   - damage_scaling_analyzer.py: Scaling efficiency
   - content_readiness_checker.py: Boss/content viability
   - archetype_classifier.py: Build classification
   - build_success_predictor.py: Success probability

3. Calculator Layer (src/calculator/): Numeric computations
   - damage_calculator.py: DPS calculations
   - defense_calculator.py: Mitigation calculations
   - ehp_calculator.py: Effective HP
   - spirit_calculator.py: Spirit resource system
   - stun_calculator.py: Stun threshold mechanics
   - build_scorer.py: Overall build quality
   - resource_calculator.py: Mana/ES/Life calculations
   - spell_dps_calculator.py: Spell-specific DPS

4. Optimizer Layer (src/optimizer/): Recommendations
   - gear_optimizer.py: Budget-aware gear suggestions
   - passive_optimizer.py: Tree pathing and node selection
   - skill_optimizer.py: Gem setup optimization
   - gem_synergy_calculator.py: Support gem interactions

5. Knowledge Layer (src/knowledge/): Game mechanics
   - poe2_mechanics.py: Comprehensive mechanic explanations

6. Database Layer (src/database/): Persistent storage
   - models.py: SQLAlchemy ORM (items, passives, skills, builds)
   - manager.py: Async operations with aiosqlite
```

## Critical Implementation Patterns

### Async-First Architecture
**Everything is async** - this is non-negotiable:
```python
# Database operations
async with db.async_session() as session:
    result = await session.execute(query)

# API calls
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# MCP handlers
async def _handle_analyze_character(self, args: dict) -> List[types.TextContent]:
    # All I/O must be awaited
```

### MCP Tool Handler Pattern
All tool handlers must follow this exact pattern:
```python
async def _handle_TOOLNAME(self, args: dict) -> List[types.TextContent]:
    try:
        # Extract args
        param = args.get("param_name")

        # Perform operations (all async)
        result = await self.component.do_work(param)

        # Format response
        return [types.TextContent(
            type="text",
            text=formatted_result
        )]
    except Exception as e:
        logger.error(f"Tool error: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]
```

**Never raise exceptions to MCP layer** - always catch and return error TextContent.

### Dual Import Pattern
All modules support both direct execution and module import:
```python
try:
    from .config import settings  # Module import
except ImportError:
    from src.config import settings  # Direct execution
```

### Multi-Source Character Fetching
character_fetcher.py implements 4-tier fallback:
1. poe.ninja API (primary, fastest)
2. poe.ninja SSE/model API (fallback)
3. Official PoE ladder API (fallback)
4. Direct HTML scraping (last resort)

Each tier has independent error handling and logging. Cache bypasses all tiers on hit.

### Rate Limiting Strategy
- PoE Official API: 10 req/min with exponential backoff (max 32x)
- poe2db.tw: 30 req/min with 1-hour cache
- poe.ninja: 20 req/min
- All API clients accept `RateLimiter` instance
- Adaptive backoff on consecutive failures

### Configuration Hierarchy
1. Environment variables (.env) - highest priority
2. config.yaml - default values
3. Pydantic BaseSettings in src/config.py merges both
4. Feature flags control AI, PoB export, trade integration

## Adding New Features

### Adding a New MCP Tool
1. Add tool definition in `_register_tools()` around line 283
2. Add handler dispatch in `handle_call_tool()` around line 1050
3. Implement handler following pattern above
4. Initialize any required components in `__init__()` around line 145

### Adding New Analyzer/Calculator/Optimizer
1. Create class in appropriate `src/*/NEW_component.py`
2. Constructor must accept `DatabaseManager` instance
3. All methods async, return dicts/dataclasses
4. Initialize in `PoE2BuildOptimizerMCP.__init__()`
5. Call from tool handler or other components

### Adding Database Models
1. Define in `src/database/models.py` inheriting from `Base`
2. Use `Column(DateTime, default=datetime.utcnow)` for timestamps
3. Index frequently queried fields
4. JSON columns for flexible nested data
5. Create migration: `alembic revision --autogenerate -m "description"`
6. Apply: `alembic upgrade head`

## Key Components Reference

### Spirit System (New PoE2 Resource)
See `src/calculator/SPIRIT_SYSTEM_QUICK_REFERENCE.md` for mechanics.
Calculator in `src/calculator/spirit_calculator.py`.

### Stun Mechanics
Comprehensive stun calculations in `src/calculator/stun_calculator.py`.
See `docs/STUN_CALCULATOR.md` for usage.

### Resource Calculator
Handles mana, ES, life calculations.
See `src/calculator/README_RESOURCE_CALCULATOR.md` and `RESOURCE_CALCULATOR_EXAMPLES.md`.

### PoE2 Mechanics Knowledge Base
`src/knowledge/poe2_mechanics.py` contains comprehensive game mechanics:
- Damage types and conversions
- Defense layers (armor, evasion, block, ES)
- Ailments (ignite, shock, freeze, chill, poison, bleed)
- Crowd control (stun, knockback)
- Resource systems (mana, ES, life, spirit)
- Scaling formulas

Used by `explain_mechanic` MCP tool for natural language mechanic explanations.

## Development Workflow

### Logging Pattern
```python
logger.info("Operation started")  # File logging (logs/poe2_optimizer.log)
debug_log("Details")  # stderr for Claude Desktop visibility
```

### Testing Pattern
- In-memory SQLite for database tests: `sqlite:///:memory:`
- Mock API responses to avoid rate limiting
- Use `pytest.mark.asyncio` for async tests
- Never use demo/dummy data - always test with real characters

### Common Pitfalls
1. Forgetting async/await on I/O operations
2. Raising exceptions in MCP tool handlers (must catch and return error)
3. Missing rate limiter on new API clients
4. Hardcoding paths (use BASE_DIR, DATA_DIR from config.py)
5. Assuming Redis available (memory cache is default)
6. Using `datetime.now()` instead of `datetime.utcnow()` in models

## File Organization

- `src/`: All Python source code (see architecture above)
- `data/`: SQLite databases (auto-created)
- `cache/`: Response caches (auto-created)
- `logs/`: Application logs (auto-created)
- `tests/`: Test suite
- `scripts/`: Database population and utilities
- `docs/`: Component documentation
- Root `*.py`: Standalone scripts (analyze_my_character.py, launch.py, etc.)

## Windows-Specific Notes

- UTF-8 encoding set in launch.py for PoE special characters
- `sys.stderr` used for Claude Desktop visible output (MCP protocol redirects this)
- `pathlib.Path` for cross-platform compatibility
- Never use demo/dummy data for testing (per project rules)
