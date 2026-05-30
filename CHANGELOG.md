# Changelog

All notable changes to this project will be documented in this file.
Format based on Path of Building changelog style, adapted for MCP tooling.

> **Community Project**: This is an independent, fan-made project built out of love for Path of Exile 2. Not affiliated with or endorsed by Grinding Gear Games.

---

## Version 1.0.1 (2026-05-30) - Patch 0.5 "Return of the Ancients" Compatibility

Compatibility updates for PoE2 Patch 0.5 (released 2026-05-29). Code-level fixes that work without re-extracted game data. Local passive tree and item mod data remain stale pending `.datc64` re-extraction; see Known Issues below.

--- API ---
* Add Runes of Aldur league (+ HC/SSF/HCSSF variants) to `LEAGUE_MAPPINGS` (#59). Slugs confirmed via `/poe2/api/data/index-state`: `runesofaldur`, `runesofaldurhc`, `runesofaldurssf`, `runesofaldurhcssf`
* Update default league from stale "Abyss" to "Runes of Aldur" on `get_character` and `_scrape_character_page` (#59)
* Auto-discover league slug from index-state when `LEAGUE_MAPPINGS` is stale, so future leagues work before the static map is updated (#62)

--- Calculators ---
* Stub `runic_ward` field on `DefensiveStats` for PoE2 0.5 Verisium Runeforging defense layer (#59). Not yet layered into mitigation; requires local extraction

--- Knowledge ---
* Add `Martial Artist` (Monk) and `Spirit Walker` (Huntress) to `ASCENDANCY_TO_CLASS` (#59). Class mapping only; node data pending re-extraction
* Commit `src/parsers/ascendancy_resolver.py` as a tracked module (#59). Was previously imported by `mcp_server.py` but untracked, so fresh checkouts would fail to import

--- Bug Fixes ---
* Fix pip console entry-point `poe2-mcp` invoking async `main()` without `asyncio.run()` (#60). Closes #56 (@MagicJoseph)

--- Documentation ---
* Correct README tool count from 32 to 39 and document the live Path of Building bridge (`pob_*` tools) (#58)

--- Infrastructure ---
* Bump vite 7.3.1 to 7.3.3 in /web (#50, dependabot)
* Bump postcss 8.5.6 to 8.5.14 in /web (#51, dependabot)

--- Known Issues (extraction-dependent, not in this release) ---
* CRITICAL: poe.ninja builds-list / ladder SPA migration broke `compare_to_top_players` and the HTML-scrape fallback (#61). Per-character JSON API still works but returns 404 for characters not present in the snapshot version (excludes freshly-rolled characters)
* Local passive tree pre-0.5: 16.21% miss rate measured vs poe.ninja's `PassiveTree-0.5` asset (4,480 nodes; local 4,094). Pending `.datc64` re-extraction
* Ascendancy node data stale for 6 reworked ascendancies + 2 new ones; mapping in place, node data pending re-extraction
* Item mod DB missing Runic Ward / Runeforging mods; pending re-extraction
* `runic_ward` field exists on `DefensiveStats` but is not layered into `calculate_ehp`; pending mechanics extraction

---

## Version 1.0.0 (2025-12-16) - First Major Release

The first stable release of the PoE2 Build Optimizer MCP server. Provides 32 MCP tools for AI-powered character analysis and build optimization.

--- Core Features ---
* 32 registered MCP tools for character analysis, validation, and optimization
* Multi-source character fetching (poe.ninja, official API, HTML scrape fallback)
* Path of Building import/export support
* Comprehensive game mechanics knowledge base

--- MCP Tools ---
* Character analysis: `analyze_character`, `compare_to_top_players`, `import_poe_ninja_url`
* Validation tools: `validate_support_combination`, `validate_build_constraints`
* Gem inspection: `inspect_support_gem`, `inspect_spell_gem`, `list_all_supports`, `list_all_spells`
* Passive tree: `list_all_keystones`, `inspect_keystone`, `list_all_notables`, `inspect_passive_node`
* Base items: `list_all_base_items`, `inspect_base_item`
* Item mods: `inspect_mod`, `list_all_mods`, `search_mods_by_stat`, `get_mod_tiers`, `validate_item_mods`
* Path of Building: `import_pob`, `export_pob`, `get_pob_code`
* Knowledge: `explain_mechanic`, `get_formula`

--- Token Optimization ---
* Pagination support with `limit` (default 20) and `offset` parameters
* Detail level filtering (`summary`, `standard`, `full`) for response verbosity control
* Compact output format with abbreviated JSON keys for programmatic consumption

--- Data Sources ---
* 4,975+ passive tree nodes with full stat text
* 335+ ascendancy nodes (99% coverage)
* 14,269 item modifiers (prefixes, suffixes, implicits)
* Complete skill gem data from Path of Building
* Support gem effects and interaction data

--- Infrastructure ---
* SQLite database with async support (aiosqlite)
* Multi-tier caching (memory -> Redis optional -> SQLite)
* Rate limiting with exponential backoff
* Comprehensive test suite

---

## Prior Development History

See git commits before 2025-12-16 for development history leading to v1.0.0.
