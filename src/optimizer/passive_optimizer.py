"""Passive tree optimization"""

import logging
import json
from typing import Dict, Any, List
from pathlib import Path

try:
    from ..config import DATA_DIR
except ImportError:
    from src.config import DATA_DIR

logger = logging.getLogger(__name__)


class PassiveOptimizer:
    """Optimizes passive tree allocation using merged passive tree data"""

    def __init__(self, db_manager) -> None:
        self.db_manager = db_manager
        self.passive_tree_extractor = None
        self._merged_passive_tree = None

    def _initialize_extractor(self):
        """Lazy initialize the passive tree extractor"""
        if self.passive_tree_extractor is None:
            try:
                from ..parsers import PassiveTreeExtractor, get_all_keystones, get_all_notables
                self.passive_tree_extractor = PassiveTreeExtractor(self.db_manager)
                self.get_all_keystones = get_all_keystones
                self.get_all_notables = get_all_notables
                logger.info("Passive tree extractor initialized in PassiveOptimizer")
            except Exception as e:
                logger.warning(f"Failed to initialize passive tree extractor: {e}")

    def _load_merged_passive_tree(self) -> Dict[str, Any]:
        """Load merged passive tree data with human-readable stats"""
        if self._merged_passive_tree is not None:
            return self._merged_passive_tree

        try:
            merged_tree_path = DATA_DIR / "merged_passive_tree.json"
            if not merged_tree_path.exists():
                logger.warning("merged_passive_tree.json not found, falling back to extractor")
                return {}

            with open(merged_tree_path, 'r', encoding='utf-8') as f:
                self._merged_passive_tree = json.load(f)
                logger.info(f"Loaded {len(self._merged_passive_tree)} passive nodes from merged tree")
                return self._merged_passive_tree
        except Exception as e:
            logger.error(f"Failed to load merged passive tree: {e}")
            return {}

    def _get_keystones(self) -> List[Dict[str, Any]]:
        """Get all keystone passives from merged tree"""
        merged_tree = self._load_merged_passive_tree()
        keystones = []

        for node_id, node_data in merged_tree.items():
            if node_data.get('is_keystone', False):
                keystones.append({
                    'id': node_id,
                    'name': node_data.get('name', ''),
                    'stats': node_data.get('stats', []),
                    'stats_source': node_data.get('stats_source', 'unknown'),
                    'is_keystone': True
                })

        return keystones

    def _get_notables(self) -> List[Dict[str, Any]]:
        """Get all notable passives from merged tree"""
        merged_tree = self._load_merged_passive_tree()
        notables = []

        for node_id, node_data in merged_tree.items():
            if node_data.get('is_notable', False):
                notables.append({
                    'id': node_id,
                    'name': node_data.get('name', ''),
                    'stats': node_data.get('stats', []),
                    'stats_source': node_data.get('stats_source', 'unknown'),
                    'is_notable': True
                })

        return notables

    async def optimize(
        self,
        character_data: Dict[str, Any],
        available_points: int = 0,
        allow_respec: bool = False,
        goal: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Generate passive tree recommendations using merged passive tree data.
        Prioritizes nodes with PoB stats (higher quality/coverage).
        """
        # Try to load merged passive tree first (has better stat coverage)
        merged_tree = self._load_merged_passive_tree()

        if merged_tree:
            logger.info("Using merged passive tree for optimization")
            keystones = self._get_keystones()
            notables = self._get_notables()
        else:
            # Fallback to extractor if merged tree not available
            logger.info("Falling back to passive tree extractor")
            self._initialize_extractor()

            if not self.passive_tree_extractor:
                # Final fallback to dummy data
                return {
                    "suggested_allocations": [
                        {"name": "Key Damage Node", "benefit": "+12% increased damage"}
                    ],
                    "suggested_respecs": [] if not allow_respec else [
                        {"current": "Lesser Node", "suggested": "Better Node", "benefit": "+8% more damage"}
                    ],
                    "data_source": "Fallback (passive tree data unavailable)"
                }

            keystones = self.get_all_keystones()
            notables = self.get_all_notables()

        # Extract character class and current build focus
        char_class = character_data.get("class", "").lower()

        # Recommend based on goal
        suggested_allocations = []

        if goal == "defense":
            # Prioritize defensive keystones and notables
            defensive_nodes = [n for n in keystones + notables if self._is_defensive_dict(n)]
            for node in defensive_nodes[:available_points]:
                suggested_allocations.append({
                    "name": node.get('name', ''),
                    "type": "Keystone" if node.get('is_keystone') else "Notable",
                    "benefit": ", ".join(node.get('stats', [])[:3]) if node.get('stats') else "Defensive bonuses",
                    "stats_source": node.get('stats_source', 'unknown')
                })

        elif goal == "damage":
            # Prioritize offensive keystones and notables
            offensive_nodes = [n for n in keystones + notables if self._is_offensive_dict(n)]
            for node in offensive_nodes[:available_points]:
                suggested_allocations.append({
                    "name": node.get('name', ''),
                    "type": "Keystone" if node.get('is_keystone') else "Notable",
                    "benefit": ", ".join(node.get('stats', [])[:3]) if node.get('stats') else "Damage bonuses",
                    "stats_source": node.get('stats_source', 'unknown')
                })

        else:  # balanced
            # Mix of keystones and notables
            all_priority_nodes = keystones[:2] + notables[:available_points-2] if len(keystones) >= 2 else keystones + notables
            for node in all_priority_nodes[:available_points]:
                suggested_allocations.append({
                    "name": node.get('name', ''),
                    "type": "Keystone" if node.get('is_keystone') else "Notable",
                    "benefit": ", ".join(node.get('stats', [])[:3]) if node.get('stats') else "Various bonuses",
                    "stats_source": node.get('stats_source', 'unknown')
                })

        return {
            "suggested_allocations": suggested_allocations,
            "suggested_respecs": [],  # TODO: Implement respec logic with node value comparison
            "total_points_recommended": len(suggested_allocations),
            "data_source": "merged_passive_tree.json (76.3% stats coverage)" if merged_tree else "passive_tree_extractor"
        }

    def _is_defensive(self, node) -> bool:
        """Check if node provides defensive bonuses (for extractor objects)"""
        stats_text = " ".join(node.stats).lower()
        defensive_keywords = ["life", "resistance", "armour", "armor", "evasion", "energy shield",
                              "block", "deflect", "stun", "immunity", "regeneration"]
        return any(kw in stats_text for kw in defensive_keywords)

    def _is_offensive(self, node) -> bool:
        """Check if node provides offensive bonuses (for extractor objects)"""
        stats_text = " ".join(node.stats).lower()
        offensive_keywords = ["damage", "critical", "attack speed", "cast speed", "accuracy",
                              "penetration", "multiplier", "chaos", "fire", "cold", "lightning", "physical"]
        return any(kw in stats_text for kw in offensive_keywords)

    def _is_defensive_dict(self, node: Dict[str, Any]) -> bool:
        """Check if node provides defensive bonuses (for dict objects)"""
        stats = node.get('stats', [])
        if not stats:
            return False
        stats_text = " ".join(stats).lower()
        defensive_keywords = ["life", "resistance", "armour", "armor", "evasion", "energy shield",
                              "block", "deflect", "stun", "immunity", "regeneration"]
        return any(kw in stats_text for kw in defensive_keywords)

    def _is_offensive_dict(self, node: Dict[str, Any]) -> bool:
        """Check if node provides offensive bonuses (for dict objects)"""
        stats = node.get('stats', [])
        if not stats:
            return False
        stats_text = " ".join(stats).lower()
        offensive_keywords = ["damage", "critical", "attack speed", "cast speed", "accuracy",
                              "penetration", "multiplier", "chaos", "fire", "cold", "lightning", "physical"]
        return any(kw in stats_text for kw in offensive_keywords)
