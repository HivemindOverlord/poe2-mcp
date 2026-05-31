# Changelog

All notable changes to this project will be documented in this file.
Format based on Path of Building changelog style, adapted for MCP tooling.

> **Community Project**: This is an independent, fan-made project built out of love for Path of Exile 2. Not affiliated with or endorsed by Grinding Gear Games.

---

## Version 1.0.4 (2026-05-31) - stat_descriptions ships; explain_mechanic stops fabricating

Trust-recovery release. Driven by HivemindOverlord's 2026-05-31 Claude Desktop session feedback: "explain_mechanic confidently stated 'crits do NOT guarantee ignite' ... contradicting a wiki line. I can't adjudicate ... outputs read like authoritative documentation but may be hand-authored interpretation." Root cause: `src/knowledge/poe2_mechanics.py` was wiki-derived hand-authored content masquerading as extracted data — the single largest data-policy hypocrisy in the repo.

Fix path: extract the game's own canonical stat description text from `.csd` files, ship it as a tracked dataset, rewire `explain_mechanic` to use it as primary source with the hand-authored module demoted to a clearly-labeled fallback.

--- Game Data ---
* Ship `data/game/stat_descriptions/` (#98). 16,533 canonical game-shipped stat descriptions extracted from 18 `.csd` files (UTF-16-LE, PoB-compatible Compiled Stat Description grammar). Headline counts: `stat_descriptions.csd` 10,716 / `skill_stat_descriptions.csd` 1,899 / `atlas_stat_descriptions.csd` 1,354 / `gem_stat_descriptions.csd` 1,334 / `passive_skill_stat_descriptions.csd` 208 / others <200 each. v1: English-only templates (other 8 languages tracked in `languages_available` field, deferred to v2). Per-record schema preserves variant range conditions + display handlers (`divide_by_ten_1dp_if_required`, `negate`, etc.) verbatim. `version.json` bumped to `data-v0.5.0-r8`.
* Add `src/data/game_data.py` helpers for the new dataset (#99): `find_stat_description(stat_id)` for exact-match lookup with source provenance tagging, `search_stat_descriptions(query, fields=("stat_id","template"))` for substring recovery (the "did you mean" layer). Module-level caching avoids re-reading the 9 MB payload per request. Also filled in missing `SKILL_GEMS_JSON` / `SKILL_GEMS_META` path constants.
* Refresh `data/game/README.md` for the new dataset + skill_gems-now-shipped state (#103). `datasets_pending_0_5_reextract` is empty.

--- MCP Tools ---
* Rewire `explain_mechanic` to two-tier lookup (#101). **Tier 1**: canonical `data/game/stat_descriptions/` text with source file + line + .csd provenance — game-shipped strings, not interpretation. **Tier 2**: hand-authored `src/knowledge/poe2_mechanics.py` summaries, now returned with EXPLICIT disclaimer ("community interpretation of wiki sources, not extracted game text. Cross-reference against the in-game tooltip for balance-sensitive numbers"). Auto-attaches Tier 1 cross-refs when a Tier 2 query also matches stat_ids. Substring queries return "did you mean" stat_id suggestions instead of bare not-founds.
* Make `mechanic_name` parameter OPTIONAL (#101). Fixes the dead-end-by-design contradiction in the previous handler ("Use this tool without arguments to see available mechanics" — but the param was required). Calling with no arguments now returns a two-tier overview with sample query shapes.
* Defensive fix: `_handle_explain_mechanic` no longer crashes with `AttributeError: 'NoneType' object has no attribute 'get_mechanic'` when `self.mechanics_kb` fails to initialize (#101). Falls through gracefully to Tier 1b substring search.

--- Testing ---
* `tests/test_stat_descriptions.py` (#100). 21 tests covering the new dataset + helpers — file shape, manifest drift checks (metadata.json count == data list length, version.json count matches, sum-of-per-file == index totals), per-record schema, `find_stat_description` proven against the proliferation entry the user couldn't find, `search_stat_descriptions` recovery layer locked in.

--- Documentation ---
* `docs/AI_ASSISTANT_GUIDE.md` updated for the new behavior (#102). New §6 workflow section showing all three `explain_mechanic` query shapes (exact stat_id / mechanic name / substring), plus a "when to trust which tier" guidance block telling LLM clients explicitly: Tier 1 is canonical; Tier 2 is community interpretation; if Tier 2 contradicts the in-game tooltip, trust the tooltip and file a bug.

--- Proven end-to-end fix for the user-reported gap ---
The proliferation/spread/Wildfire content gap from the Claude Desktop session is closed at the data layer (the canonical strings were in the game blob the whole time):
```
support_ignite_proliferation_radius
  -> "[Ignite|Ignites] inflicted by Supported Skills [AilmentSpread|Spread]
      to other enemies that stay within {0} metre for 1 second"
support_elemental_proliferation_damage_+%_final
  -> "Supported Skills deal {0}% more Damage"
support_ignite_prolif_ignite_effect_+%_final
  -> "{0}% more Magnitude of Ignite inflicted with Supported Skills"
```

--- Known Issues (carried over from 1.0.3) ---
* CRITICAL #4: poe.ninja builds-list / ladder SPA migration broke `compare_to_top_players` and HTML-scrape fallback (#61).
* **NEW — Gap H (CRITICAL)** surfaced by MCP eval batch 3 (#97): a single resolver-init bug breaks ≥5 passive-tree handlers (`list_all_keystones`, `list_all_notables`, and others). Error: "Passive tree resolver not initialized. PSG database may be missing." Same fix pattern as PR #94 / #101 — point resolver at `data/game/passive_tree/tree.json` instead of the missing `.psg` blob. Next handler-side PR.

--- Pending P2 / P3 / P5 follow-ups (from same user feedback) ---
* **P2**: fuzzy-match + did-you-mean for `inspect_keystone` / `inspect_support_gem` / `inspect_spell_gem` (the `search_*` recovery pattern from PR #101 generalized to other lookup handlers).
* **P3**: data-source / version-verified banner on every numeric response across handlers.
* **P5**: server-side `calculate_character_dps(character_data)` MCP handler so "optimization" means more than "we hand you the formula and you compute."

---

## Version 1.0.3 (2026-05-31) - skill_gems shipped + zero-coverage gap sweep

Follow-up to 1.0.2 the same day. Closes the last 0.5-pending dataset (`skill_gems`), adds the operator/AI-facing docs that were missing across the repo, and lands ~200 new tests filling zero-coverage gaps on load-bearing pure-function modules.

--- Game Data ---
* Ship `data/game/skill_gems/skill_gems.json` (#91). 872 gems extracted from PathOfBuilding-PoE2 `origin/dev @ 9c2bf0316` (patch-day 2026-05-30 commit). 100% gem→effect join rate via `grantedEffectId`. Schema v1: gem metadata (tier, tags, requirements, naturalMaxLevel) + granted_effect (levels with cost/crit_chance/level_requirement, stat_sets with base_effectiveness). 1.6 MB output. `version.json` bumped to `data-v0.5.0-r7`; `datasets_pending_0_5_reextract` is now empty. v1 deliberately defers full Lua `statMap` / `baseFlags` / `constantStats` / `stats` extraction (needs structural Lua parser; tracked for v2)
* Refresh `data/game/README.md` for the 0.5-r5 dataset state (#82). Removed stale "pending re-extract" markers on ascendancies/support_gems/stats; per-dataset table replaces the prose status block

--- Documentation ---
* Add `docs/AI_ASSISTANT_GUIDE.md` (#81). Onboarding doc for AI clients (Claude/ChatGPT/Cursor/Windsurf etc.) — tool surface, parameter alias quirks, game-data sources, known failure modes (incl. CRITICAL #4), common LLM mistakes, workflow patterns
* Add `docs/EXTRACTION_PIPELINE.md` (#84). End-to-end data/game/ regeneration walkthrough — LibBundle3 + pythonnet setup, the 0.5-era gotchas (CoreCLR runtime, parsePaths=False workaround, balance/ subdir, mods row size growth 661→677, ascendancy offset 44), lifecycle checklist for new patches
* Add `docs/SKILL_GEMS_PORT_AUDIT.md` (#85). Scout for the (then-)pending extractor port — PoB2 source shape, existing extractor gaps, recommended schema, open questions. Set up the work that #91 then delivered
* Add `web/README.md` (#86). First README for the standalone Svelte 5 + Vite Timeless Jewel Seed Calculator subproject — tech stack, dev/build/deploy commands, GitHub Pages auto-deploy workflow walkthrough

--- Testing ---
* Add `tests/test_game_data.py` (#83). 19 tests covering the `src/data/game_data.py` base API (path constants, get_version, load_*() helpers, load_metadata, describe). Notable: `test_load_stats_record_count_matches_version_manifest` catches drift between `stats.json` and `version.json` on re-extract
* Add `tests/test_mods_spec.py` (#87). 48 tests for `src/parsers/specifications/mods_spec.py` (central binary parser used by every mod tool). Locks in PR #68's 0.5 row-size relaxation as an explicit regression guard
* Add `tests/test_characters_spec.py` (#88). 27 tests for `src/parsers/specifications/characters_spec.py` (poe.ninja class → PSG starting-node resolution). Cross-consistency tests catch silent drift between `POE_NINJA_CLASS_TO_STARTING_NODE` and `PSG_STARTING_NODES`. Locks in the "poe.ninja calls Druid 'Sorceress'" quirk
* Add `tests/test_defense_calculator.py` (#89). 37 tests for `src/calculator/defense_calculator.py`. Regression guards on the PoE2-vs-PoE1 constants (block cap 50% not 75%, ES recharge 12.5%/s not 20%, ES delay 4s not 2s)
* Add `tests/test_game_data_helpers.py` (#90). 26 tests for the convenience helpers added by PR #80 (find_ascendancies_by_base_class, find_mods_by_stat_id, get_keystones, etc.). Direct continuation of scope deferred from #83
* Add `tests/test_spell_dps_calculator.py` (#92). 41 tests for `src/calculator/spell_dps_calculator.py` (last unmonitored calculator). Anchored to docstring examples; locks in `more` multipliers stacking multiplicatively (not additively — common subtle-correctness trap)

--- Known Issues (carried over from 1.0.2) ---
* CRITICAL #4: poe.ninja builds-list / ladder SPA migration broke `compare_to_top_players` and HTML-scrape fallback (#61). Underlying fix needs the new poe.ninja endpoint reverse-engineered

---

## Version 1.0.2 (2026-05-31) - Patch 0.5 game data + MCP usability sweep

Follow-up to 1.0.1. Where 1.0.1 was non-extraction code compat for the 0.5 patch, 1.0.2 ships the actual extracted 0.5 game data + MCP-handler improvements + accuracy work surfaced during a fresh end-to-end MCP evaluation.

--- Game Data (canonical layout) ---
* Establish `data/game/{dataset}/` repo-as-source-of-truth layout (#69). 5 datasets shipped: mods (16,788 records), passive_tree (9,605 nodes, 82 keystones, 2,151 notables), support_gems (680), ascendancies (37 — including NEW 0.5 Spirit Walker + Martial Artist), stats (26,943 stat IDs). Closes #53 (pip install empty database).
* Inline-resolve `stat_id` strings on every non-empty mod stat entry (#75). 24,632 entries enriched. Consumers no longer need to load `stats.json` separately to resolve `stat_key` references.
* Fix ascendancy `display_name` field — use canonical offset 44 instead of longest-string heuristic (#71). 23 active ascendancies all correctly named.

--- MCP Tools ---
* Add `check_tree_freshness` self-diagnostic tool (#76). Compares local `data/game/version.json` patch_version against poe.ninja's current `PassiveTree` tag from index-state. Reports current / behind / ahead / unable. Pure change-detection per data policy. Tool count: 39 → 40.
* Rewrite `search_mods_by_stat` (#73). Was returning 0 results for "life regeneration" despite 16,788 mods in DB. Now tokenizes the query and searches mod_id + display_name + resolved stat_id strings. Verified: "life regeneration" goes from 0 hits to 173 hits (117 mod_id + 56 stat cross-reference).
* Accept alias parameter names on `inspect_keystone` (`name`), `inspect_spell_gem` (`name`, `gem_name`), `validate_support_combination` (`support_gem_names`, `names`) via `oneOf` in inputSchema (#73). AI-friendliness fix from the May eval.
* SPA-aware character-fetch error templates on `analyze_character` and `compare_to_top_players` (#74). Surfaces the CRITICAL #4 (#61) poe.ninja SPA migration cause up front instead of sending users on a wild-goose chase through profile-privacy and account-format settings. Closes #55 (@dsakura).

--- API ---
* Auto-discover league slug from index-state when `LEAGUE_MAPPINGS` is stale (#62, in 1.0.1 retro). Future leagues work as soon as poe.ninja indexes them, without needing a static map update.

--- Knowledge ---
* Add `Runic Ward` `explain_mechanic` entry (#64, in 1.0.1 retro). PRELIMINARY — numeric mechanics not bundled (waiting on .datc64 mechanics extraction). Documents what we know, what's pending.

--- Documentation ---
* Split Claude Desktop config in README into pip-install (`"command": "poe2-mcp"`) vs source-install (`launch.py`) sub-options (#72). Closes #52.

--- Known Issues (carried over from 1.0.1) ---
* CRITICAL #4: poe.ninja builds-list / ladder SPA migration broke `compare_to_top_players` and HTML-scrape fallback (#61). Per-character JSON API still works for characters in the snapshot; #74 + #65 surface the cause to users instead of silent fail. Underlying fix needs the new poe.ninja endpoint reverse-engineered.
* `skill_gems` dataset not yet in `data/game/` — blocked on PoB2 community shipping 0.5 `tree.json` upstream (verified daily; still not landed as of 2026-05-31). Current pre-0.5 skill data in `data/pob_active_skills.json`.

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
