"""
Data providers for PoE2 game data.

Canonical source: `data/game/` (this repo, tracked). Each dataset lives in
its own folder with a JSON + metadata.json. See data/game/README.md.

Import canonical paths from `game_data`:

    from src.data.game_data import MODS_JSON, PASSIVE_TREE_JSON, load_mods
    mods = load_mods()

Legacy providers, in priority order:
1. Local raw extraction (FreshDataProvider): reads from data/extracted/
   (gitignored — raw .datc64 dumps the user populated via
   scripts/extract_poe2_data.py).
2. Releases-bundle distributor (data_distributor): downloads zip bundle
   from this repo's GitHub Releases. Currently no-op because no data-*
   release is published — the canonical path is now data/game/ in-repo
   (PR #66's distributor will be repurposed or removed in a follow-up).

Per CLAUDE.md data policy, all sources trace back to extraction from a
licensed PoE2 install. No third-party wiki / scraped data.
"""

from .fresh_data_provider import FreshDataProvider, get_fresh_data_provider
from . import data_distributor
from . import game_data

__all__ = [
    'FreshDataProvider',
    'get_fresh_data_provider',
    'data_distributor',
    'game_data',
]
