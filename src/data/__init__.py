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
2. Releases-bundle distributor (data_distributor): downloads the poe2-data.zip
   bundle from this repo's GitHub Releases (active as of the data-v0.5.0-1
   release). Used for fresh-install bootstrap and permissioned upgrades.
3. Update orchestration (update_manager): unified data + code freshness check
   with a consent model (notify by default; POE2_MCP_AUTO_UPDATE=1 to auto-apply).
   Backs the check_for_updates MCP tool.

Per CLAUDE.md data policy, all sources trace back to extraction from a
licensed PoE2 install. No third-party wiki / scraped data.
"""

from . import data_distributor, game_data, update_manager
from .fresh_data_provider import FreshDataProvider, get_fresh_data_provider

__all__ = [
    "FreshDataProvider",
    "get_fresh_data_provider",
    "data_distributor",
    "game_data",
    "update_manager",
]
