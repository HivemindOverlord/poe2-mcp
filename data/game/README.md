# `data/game/` — Canonical PoE2 Game Data

This directory is the **repo-as-source-of-truth** for game data the MCP consumes at runtime. Each dataset lives in its own folder. Both `git pull` and `pip install poe2-mcp` deliver this data to users — no separate download step, no GitHub Releases zip lifecycle.

## Layout

```
data/game/
├── version.json                  # Global manifest: patch version, datasets, revisions
├── README.md                     # This file
├── mods/
│   ├── mods.json                 # 16,788 mod records (0.5) — stat_ids inline-resolved
│   └── metadata.json             # Extraction provenance + SHA-256
├── passive_tree/
│   ├── tree.json                 # 9,605 passive tree nodes (0.5)
│   └── metadata.json
├── ascendancies/
│   ├── ascendancies.json         # 37 ascendancies (23 active, incl. NEW 0.5 Spirit Walker + Martial Artist)
│   └── metadata.json
├── support_gems/
│   ├── support_gems.json         # 680 support gems
│   └── metadata.json
├── stats/
│   ├── stats.json                # 26,943 canonical stat IDs (row_index → stat_id)
│   └── metadata.json
├── skill_gems/
│   ├── skill_gems.json           # 872 gems joined from PoB2's Gems.lua + Skills/*.lua (v1)
│   └── metadata.json
└── stat_descriptions/
    ├── index.json                # file inventory + per-file counts
    ├── metadata.json
    └── <name>_stat_descriptions.json (x18)   # 16,533 canonical game-shipped stat templates
```

Each dataset folder has at minimum a data JSON and a `metadata.json` describing what's inside, when it was extracted, and a SHA-256 for integrity. The `record_count` and per-dataset notes in the global `version.json` are the authoritative summary; the layout block above is informational.

## How to use this data from code

Import the canonical paths from `src/data/game_data.py` rather than hardcoding strings:

```python
from src.data.game_data import MODS_JSON, PASSIVE_TREE_JSON
import json

mods = json.loads(MODS_JSON.read_text(encoding="utf-8"))
tree = json.loads(PASSIVE_TREE_JSON.read_text(encoding="utf-8"))
```

That way the layout can move without touching every caller.

## Data policy

**All data in this directory is extracted exclusively from the maintainer's licensed PoE2 install** via the in-repo extraction pipeline (`scripts/extract_poe2_data.py` → per-dataset sub-extractors). **No third-party wiki / scraped data is bundled here.** See `CLAUDE.md` "Data Source Policy" for the full rule.

We ship **structured data** (mods, tree nodes, gem effects, stats) only. We do **NOT** ship **game assets** (images, audio, models, textures). This is the same boundary PoB / poeDB / poe.ninja / mobalytics have operated within for years.

## Lifecycle

When a patch ships:

1. HivemindMinion runs `scripts/extract_poe2_data.py` against the patched local Steam install (extracts `.datc64` blobs to `data/extracted/` — that subdirectory stays gitignored; raw blobs don't enter git).
2. Per-dataset sub-extractors transform the relevant `.datc64` files into JSON and write them here under `data/game/{dataset}/`.
3. `metadata.json` and the global `version.json` are regenerated with fresh extraction timestamps, record counts, and SHA-256s.
4. The diff is reviewed and committed. Users get the update on next `git pull` (source installs) or next `pip install --upgrade poe2-mcp` (pip installs).

The previous GitHub Releases zip distribution model (`src/data/data_distributor.py`, `scripts/publish_data_release.py` from PR #66) is now redundant for the canonical path and will be repurposed or removed in a follow-up — it stays no-op-functional in the meantime.

## Current 0.5 status

See `version.json` `datasets` (delivered) and `datasets_pending_0_5_reextract` (blockers + interim file locations).

As of `data-v0.5.0-r8` (2026-05-31), `datasets_pending_0_5_reextract` is empty — every dataset has shipped:

| Dataset | 0.5-fresh? | Notes |
|---|---|---|
| `mods` | YES | 16,788 records, stat_ids inline-resolved (no separate stats.json load needed at read time) |
| `passive_tree` | YES | 9,605 nodes |
| `ascendancies` | YES | 37 records, includes new Patch 0.5 Spirit Walker (Huntress) + Martial Artist (Monk) |
| `support_gems` | YES | 680 records |
| `stats` | YES | 26,943 canonical stat IDs |
| `skill_gems` | YES | 872 gems extracted from PoB2 `origin/dev @ 9c2bf0316` (Gems.lua + Skills/*.lua joined view, since PR #91). v1 schema; full Lua `statMap` / `constantStats` / `qualityStats` deferred to v2. |
| `stat_descriptions` | YES | 16,533 canonical game-shipped stat templates across 18 source `.csd` files (since PR #98). English-only in v1; other 8 languages deferred. This is the authoritative source `explain_mechanic` reads from (PR #101). |

