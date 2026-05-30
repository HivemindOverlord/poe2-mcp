# `data/game/` — Canonical PoE2 Game Data

This directory is the **repo-as-source-of-truth** for game data the MCP consumes at runtime. Each dataset lives in its own folder. Both `git pull` and `pip install poe2-mcp` deliver this data to users — no separate download step, no GitHub Releases zip lifecycle.

## Layout

```
data/game/
├── version.json            # Global manifest: patch version, datasets, revisions
├── README.md               # This file
├── mods/
│   ├── mods.json           # Mod records (~17k mods in 0.5)
│   └── metadata.json       # Extraction provenance + SHA-256
├── passive_tree/
│   ├── tree.json           # Passive tree nodes (~10k nodes in 0.5)
│   └── metadata.json
├── ascendancies/           # (pending 0.5 re-extract)
├── support_gems/           # (pending 0.5 re-extract)
├── stats/                  # (pending 0.5 re-extract)
└── ...
```

Each dataset folder has at minimum a data JSON and a `metadata.json` describing what's inside, when it was extracted, and a SHA-256 for integrity.

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

See `version.json` `datasets` (delivered) and `datasets_pending_0_5_reextract` (blockers + interim file locations). At time of writing: **mods** and **passive_tree** are 0.5-fresh; **ascendancies / support_gems / stats / skill_gems** are pending.
