# Game Data Extraction Pipeline

This document describes how `data/game/` is regenerated when a new PoE2 patch ships. It targets contributors who need to update game data and AI assistants helping with extraction work.

For the format of the binary files themselves, see `docs/DATC64_FORMAT.md`. For what the resulting datasets look like and where consumers read them, see `data/game/README.md`.

---

## 1. Pipeline overview

```
PoE2 Steam install (Bundles2/_.index.bin + .bundle.bin chunks)
            │
            │  scripts/extract_poe2_data.py
            │  (LibBundle3 .NET assembly via pythonnet)
            ▼
data/extracted/data/                                    [gitignored]
            │   raw .datc64 blobs, including:
            │     ├── balance/mods.datc64
            │     ├── passive_skill_tree/*.datc64
            │     ├── ascendancy.datc64
            │     ├── stats.datc64
            │     └── ...
            │
            │  scripts/extract_<dataset>_v2.py
            │  (per-dataset parser → JSON)
            ▼
data/game/<dataset>/<dataset>.json + metadata.json      [committed]
data/game/version.json                                  [committed]
```

`data/extracted/` is **gitignored** — raw binary blobs do not enter git. The structured JSON under `data/game/` is what ships to users.

## 2. Prerequisites (one-time)

Run `scripts/setup_game_data_extraction.py` to inventory / download:

- **LibBundle3 + LibGGPK3** (.NET assemblies, win-x64) into `tools/win-x64/`.
- Optionally: `BundleExporter.exe`, `ggpk-tool` (Rust), `poe-dat-export` (npm) — fallback paths if the .NET route fails.

Python:

```bash
pip install pythonnet>=3.0
```

You also need a .NET 6+ runtime installed on the host. The pipeline does NOT use .NET Framework 4 — see [§5 Gotchas](#5-gotchas) for why.

The PoE2 Steam install is located by checking common paths and the `POE2_PATH` environment variable. Default search list (see `find_poe2_bundles2()` in `scripts/extract_poe2_data.py`):

```
C:\Program Files (x86)\Steam\steamapps\common\Path of Exile 2\Bundles2
C:\Program Files\Steam\steamapps\common\Path of Exile 2\Bundles2
D:\Steam\steamapps\common\Path of Exile 2\Bundles2
D:\SteamLibrary\steamapps\common\Path of Exile 2\Bundles2
```

## 3. Stage 1 — raw extraction (`extract_poe2_data.py`)

```bash
python scripts/extract_poe2_data.py
```

What it does:

1. Sets `pythonnet.set_runtime("coreclr")` **before** importing `clr` — must happen at process start.
2. Loads `tools/win-x64/LibBundle3.dll` via `clr.AddReference`.
3. Constructs `DriveBundleFactory(Bundles2/)` and `Index(_.index.bin, parsePaths=False, factory)`.
4. Calls `index.ParsePaths()` (lenient mode) separately, then `index.BuildTree(ignoreNullPath=True)`.
5. Walks to the `Data` subtree and calls `index.Extract(data_node, out_dir, None)`.
6. Output lands in `data/extracted/data/...`.

Fallback path (if pythonnet doesn't work): the script can launch `tools/win-x64/VisualGGPK3.exe` for manual extraction via GUI — `extract_with_subprocess()` in the same file.

## 4. Stage 2 — per-dataset extractors

Each dataset has its own `scripts/extract_<dataset>_v2.py` that consumes the raw blobs under `data/extracted/` and writes JSON into `data/game/<dataset>/`. The `_v2` suffix marks these as rewrites against the **current** `src/parsers/specifications/` API — older `extract_*.py` siblings (no `_v2`) import symbols that no longer exist.

The shipped per-dataset extractors (all gitignored under `scripts/extract_*.py`):

| Dataset | Extractor | Source blob | Output |
|---|---|---|---|
| `mods` | `extract_mods_datc64_v2.py` | `data/extracted/data/balance/mods.datc64` | `data/game/mods/mods.json` + `metadata.json` |
| `ascendancies` | `extract_ascendancies_v2.py` | `data/extracted/data/ascendancy.datc64` | `data/game/ascendancies/ascendancies.json` + `metadata.json` |
| `stats` | `extract_stats_v2.py` | `data/extracted/data/stats.datc64` | `data/game/stats/stats.json` + `metadata.json` |
| `passive_tree` | (existing pipeline pre-0.5) | various passive_skill_tree blobs | `data/game/passive_tree/tree.json` + `metadata.json` |
| `support_gems` | (existing pipeline pre-0.5) | gem blobs | `data/game/support_gems/support_gems.json` + `metadata.json` |
| `skill_gems` | `extract_skill_gems_v2.py` | PoB2 `origin/dev` `src/Data/Gems.lua` + `src/Data/Skills/*.lua` | `data/game/skill_gems/skill_gems.json` + `metadata.json` |
| `stat_descriptions` | `extract_stat_descriptions.py` | `data/extracted/Data/statdescriptions/*.csd` (18 files, UTF-16-LE) | `data/game/stat_descriptions/index.json` + `metadata.json` + 18 per-source JSON files |

Most extractors follow the same shape:

1. Read the raw `.datc64` (header → rows → magic → data section, see `docs/DATC64_FORMAT.md`).
2. Use the spec in `src/parsers/specifications/<dataset>_spec.py` to interpret fixed-width row fields.
3. Resolve variable-length data (UTF-16 strings, lists) from the data section using table-section pointers.
4. Write structured JSON.
5. Write `metadata.json` with: `dataset`, `filename`, `patch_version`, `extracted_at` (UTC ISO 8601), `source_file`, `source_bytes`, `source_row_count`, `source_row_size`, `extractor`, `record_count`, `sha256` of the output, plus dataset-specific `schema_notes`.

**Two exceptions** that follow different patterns because their sources aren't `.datc64`:

- **`skill_gems`** sources from the PoB2 community repo's Lua data, not the game directly. The extractor uses `git -C <pob_repo> show origin/dev:src/Data/...` to read the canonical Lua text without touching the local PoB checkout, then regex-parses Gems.lua entries and Skills/*.lua effect tables, joining via `grantedEffectId`. v1 schema is the joined gem-metadata-plus-granted-effect view; full Lua `statMap` / `constantStats` / `qualityStats` are deferred to v2 (need a structural Lua parser). See `docs/SKILL_GEMS_PORT_AUDIT.md` for the scout that informed the design.

- **`stat_descriptions`** sources from `.csd` files (Compiled Stat Description format — UTF-16-LE plain text using PoB's parser-compatible grammar that GGG ships alongside the .datc64 tables). The extractor walks the 18 root-level `.csd` files, parses each `description ... lang "..."` block, captures English variants verbatim (range conditions + display handlers like `divide_by_ten_1dp_if_required` preserved as a list — consumers apply if interpreting numbers), and outputs one JSON per source file plus an index. 16,533 descriptions, ~9 MB output. v1 ships English only; other 8 languages tracked in `languages_available` field but not extracted (size). This is the dataset `explain_mechanic` reads from since PR #101 — replacing hand-authored wiki interpretation with the game's own canonical text.

After all per-dataset extractors run, **regenerate `data/game/version.json`** with the new `data_revision`, `released_as` tag, `extracted_at`, and per-dataset `record_count` summary.

## 5. Gotchas

These are non-obvious failure modes that have bitten the pipeline before. Read before re-extracting.

### CoreCLR runtime must be set before `clr` import

```python
import pythonnet
pythonnet.set_runtime("coreclr")  # <-- BEFORE any `import clr` anywhere
```

Default pythonnet uses .NET Framework 4.0, which can't load LibBundle3 (built against .NET 6+ with Default Interface Methods). Symptom: `TypeLoadException` on `clr.AddReference(LibBundle3.dll)`.

### `parsePaths=True` throws on 0.5 index

LibBundle3 v2.7.2 AND v2.7.5 both raise `"Parsing path failed for 5 files"` when the `Index` constructor is called with `parsePaths=True` against the 0.5 `_.index.bin`. Workaround:

```python
index = Index(str(index_path), False, factory)  # parsePaths=False
try:
    index.ParsePaths()  # lenient mode
except Exception:
    pass  # 5 files unparseable — covered by ignoreNullPath below
root = index.BuildTree(True)  # ignoreNullPath=True
```

### Path drift in 0.5 — `balance/` subdir added

In 0.5, `mods.datc64` moved from `data/extracted/data/mods.datc64` to `data/extracted/data/balance/mods.datc64`. Per-dataset extractors built before 0.5 will fail to find their source blob. If you write a new sub-extractor, walk the extracted tree rather than hardcoding the historic flat path.

### Row size growth — `mods.datc64` 661 → 677 bytes in 0.5

Patch 0.5 added Runeforging mod columns, bumping each row from 661 to 677 bytes. `parse_mod_row` in `src/parsers/specifications/mods_spec.py` was relaxed from `len(row) != MOD_ROW_SIZE` to `len(row) < MOD_ROW_SIZE` to accept the wider rows while still rejecting truncated ones. Any spec change in a future patch needs the same treatment.

### Ascendancy `display_name` lives at offset 44

Earlier extractor versions used a heuristic ("longest string in the row's pointed-to data") to pick display name, which incorrectly surfaced art-asset paths and flavor text. The canonical display name is at fixed offset 44 in the ascendancy row — `extract_ascendancies_v2.py` uses that and the result is clean across all 37 rows. Don't reinvent the heuristic.

### Mods stat_ids are inline-resolved

As of `data-v0.5.0-r5`, every non-empty stat entry in `data/game/mods/mods.json` carries a resolved `stat_id` string inline (cross-referenced from `data/game/stats/`). Consumers MUST NOT need a separate `stats.json` load just to resolve stat-key references on mods. New extractors should preserve this property.

## 6. Lifecycle when a patch ships

1. **Steam patches the install.** Verify by checking the mtime on `Bundles2/_.index.bin`.
2. **Re-run stage 1** (`scripts/extract_poe2_data.py`) — populates / refreshes `data/extracted/data/`.
3. **Re-run each per-dataset stage 2 extractor** — overwrites `data/game/<dataset>/{<dataset>.json, metadata.json}`.
4. **Update `data/game/version.json`** — bump `data_revision`, set new `released_as` (e.g. `data-v0.5.0-r6`), update `patch_version` / `patch_name` / `patch_released` if it's a new patch, refresh per-dataset `record_count` / notes.
5. **Diff review.** Sanity-check record-count deltas vs the patch notes (a patch that added 200 mods should bump `mods.record_count` by roughly that much; a 100-mod drop is a red flag).
6. **Update `data/game/README.md`** — the "Current 0.5 status" table should match `version.json`.
7. **Tests:** `pytest tests/test_game_data.py` — catches obvious shape/manifest drift (e.g., `stats.json` count not matching `version.json`).
8. **Commit** as one logical change. Users get the update on `git pull` (source installs) or `pip install --upgrade poe2-mcp` (pip installs).

## 7. What's NOT in this pipeline

- **Game assets** (PNG/DDS/audio/3D models) — out of scope. We ship structured data only, matching the boundary PoB / poeDB / poe.ninja / mobalytics have operated within for years.
- **Character / build data** — fetched live from poe.ninja, never extracted from local game files.
- **Trade-API data** — separate flow, requires GGG OAuth (currently blocked, see `search_trade_items` notes).
- **PoB2 skill/gem data** — sourced from the PathOfBuilding-PoE2 community repo, not from `.datc64`. The `skill_gems` dataset extractor port is pending; PoB2 upstream shipped 0.5 `Gems.lua` + `tree.lua` on 2026-05-29 (patch day).

---

## See also

- `CLAUDE.md` — "Data Source Policy" (the binding rule)
- `docs/DATC64_FORMAT.md` — binary format reference
- `data/game/README.md` — consumer-facing layout reference
- `data/game/version.json` — authoritative dataset summary
- `src/data/game_data.py` — Python accessor for everything in `data/game/`
