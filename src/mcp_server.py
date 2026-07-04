#!/usr/bin/env python3
"""
Path of Exile 2 Build Optimizer MCP Server
Main server implementation with MCP protocol support
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Import with fallback for both direct and module execution
try:
    from .config import settings, DATA_DIR
    from .database.manager import DatabaseManager
    from .api.poe_api import PoEAPIClient
    from .api.rate_limiter import RateLimiter
    from .api.cache_manager import CacheManager
    from .api.character_fetcher import CharacterFetcher
    from .api.trade_api import TradeAPI
    from .calculator.build_scorer import BuildScorer
    from .optimizer.gear_optimizer import GearOptimizer
    from .optimizer.passive_optimizer import PassiveOptimizer
    from .optimizer.skill_optimizer import SkillOptimizer
    from .analyzer.top_player_fetcher import TopPlayerFetcher
    from .analyzer.character_comparator import CharacterComparator
    from .analyzer.weakness_detector import WeaknessDetector
    from .analyzer.gear_evaluator import GearEvaluator
    from .calculator.ehp_calculator import EHPCalculator
    from .calculator.spirit_calculator import SpiritCalculator
    from .calculator.damage_calculator import DamageCalculator
    from .ai.query_handler import QueryHandler
    from .ai.recommendation_engine import RecommendationEngine
    from .pob.importer import PoBImporter
    from .pob.exporter import PoBExporter

    # New enhancement features
    from .optimizer.gem_synergy_calculator import GemSynergyCalculator
    from .knowledge.poe2_mechanics import PoE2MechanicsKnowledgeBase
    from .analyzer.gear_comparator import GearComparator
    from .analyzer.damage_scaling_analyzer import DamageScalingAnalyzer
    from .analyzer.content_readiness_checker import ContentReadinessChecker

    # Passive tree resolver for poe.ninja node ID resolution
    from .parsers.passive_tree_resolver import PassiveTreeResolver

    # Fresh data provider - Single Source of Truth
    from .data.fresh_data_provider import get_fresh_data_provider

    # Local live-game readers (Client.txt log + client config INI)
    from .api.client_log_reader import ClientLogReader
    from .api.game_config_reader import GameConfigReader
except ImportError:
    # Fallback for direct execution
    from src.config import settings, DATA_DIR
    from src.database.manager import DatabaseManager
    from src.api.poe_api import PoEAPIClient
    from src.api.rate_limiter import RateLimiter
    from src.api.cache_manager import CacheManager
    from src.api.character_fetcher import CharacterFetcher
    from src.api.trade_api import TradeAPI
    from src.calculator.build_scorer import BuildScorer
    from src.optimizer.gear_optimizer import GearOptimizer
    from src.optimizer.passive_optimizer import PassiveOptimizer
    from src.optimizer.skill_optimizer import SkillOptimizer
    from src.analyzer.top_player_fetcher import TopPlayerFetcher
    from src.analyzer.character_comparator import CharacterComparator
    from src.analyzer.weakness_detector import WeaknessDetector
    from src.analyzer.gear_evaluator import GearEvaluator
    from src.calculator.ehp_calculator import EHPCalculator
    from src.calculator.spirit_calculator import SpiritCalculator
    from src.calculator.damage_calculator import DamageCalculator
    from src.ai.query_handler import QueryHandler
    from src.ai.recommendation_engine import RecommendationEngine
    from src.pob.importer import PoBImporter
    from src.pob.exporter import PoBExporter

    # New enhancement features
    from src.optimizer.gem_synergy_calculator import GemSynergyCalculator
    from src.knowledge.poe2_mechanics import PoE2MechanicsKnowledgeBase
    from src.analyzer.gear_comparator import GearComparator
    from src.analyzer.damage_scaling_analyzer import DamageScalingAnalyzer
    from src.analyzer.content_readiness_checker import ContentReadinessChecker

    # Passive tree resolver for poe.ninja node ID resolution
    from src.parsers.passive_tree_resolver import PassiveTreeResolver

    # Fresh data provider - Single Source of Truth
    from src.data.fresh_data_provider import get_fresh_data_provider

    # Local live-game readers (Client.txt log + client config INI)
    from src.api.client_log_reader import ClientLogReader
    from src.api.game_config_reader import GameConfigReader

# Setup logging to both file and stderr (for Claude Desktop logs)
import sys

# Configure logging to stderr for Claude Desktop
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG for detailed logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),  # Log to stderr for Claude Desktop
    ],
)
logger = logging.getLogger(__name__)


# Also log to stderr directly for immediate visibility
def debug_log(message):
    """Direct logging to stderr for Claude Desktop"""
    print(f"[MCP-SERVER] {message}", file=sys.stderr, flush=True)


# Shared text-search helpers (P2 / #115). Lives in a separate module so test
# files can import the helper without triggering full mcp_server init.
try:
    from .text_search import did_you_mean
except ImportError:
    from src.text_search import did_you_mean

# Provenance banner helper (P3 / #116). Lightweight module — safe to import
# at module top.
try:
    from .provenance import (
        format_banner as format_provenance,
        CANONICAL,
        COMPUTED,
        INTERPRETED,
        EXTERNAL,
    )
except ImportError:
    from src.provenance import (
        format_banner as format_provenance,
        CANONICAL,
        COMPUTED,
        INTERPRETED,
        EXTERNAL,
    )

# Mod-data helpers (#118). Inline-stat_id-aware extraction from mods.json.
try:
    from .mod_data import (
        iter_resolved_stats as _iter_resolved_stats,
        load_stat_lookup as _load_stat_lookup,
        mod_value_range as _mod_value_range,
        canonical_mods_path as _canonical_mods_path,
        legacy_mods_path as _legacy_mods_path,
        load_spawn_tags as _load_spawn_tags,
        available_spawn_tags as _available_spawn_tags,
        normalize_item_class as _normalize_item_class,
    )
except ImportError:
    from src.mod_data import (
        iter_resolved_stats as _iter_resolved_stats,
        load_stat_lookup as _load_stat_lookup,
        mod_value_range as _mod_value_range,
        canonical_mods_path as _canonical_mods_path,
        legacy_mods_path as _legacy_mods_path,
        load_spawn_tags as _load_spawn_tags,
        available_spawn_tags as _available_spawn_tags,
        normalize_item_class as _normalize_item_class,
    )


debug_log("=== PoE2 Build Optimizer MCP Server ===")
debug_log(f"Python version: {sys.version}")
debug_log(f"Working directory: {Path.cwd()}")
debug_log(f"Script location: {__file__}")


class PoE2BuildOptimizerMCP:
    """
    Main MCP server for Path of Exile 2 build optimization
    Provides AI-powered build recommendations through MCP protocol
    """

    def __init__(self) -> None:
        self.server = Server("poe2-build-optimizer")
        self.db_manager: Optional[DatabaseManager] = None
        self.poe_api: Optional[PoEAPIClient] = None
        self.cache_manager: Optional[CacheManager] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.char_fetcher: Optional[CharacterFetcher] = None
        self.trade_api: Optional[TradeAPI] = None

        # Analyzers and Optimizers
        self.build_scorer: Optional[BuildScorer] = None
        self.gear_optimizer: Optional[GearOptimizer] = None
        self.passive_optimizer: Optional[PassiveOptimizer] = None
        self.skill_optimizer: Optional[SkillOptimizer] = None

        # Comparison System
        self.top_player_fetcher: Optional[TopPlayerFetcher] = None
        self.comparator: Optional[CharacterComparator] = None

        # Phase 1-3 Calculators and Analyzers
        self.weakness_detector: Optional[WeaknessDetector] = None
        self.gear_evaluator: Optional[GearEvaluator] = None
        self.ehp_calculator: Optional[EHPCalculator] = None
        self.spirit_calculator: Optional[SpiritCalculator] = None
        self.damage_calculator: Optional[DamageCalculator] = None

        # New Enhancement Features
        self.gem_synergy_calculator: Optional[GemSynergyCalculator] = None
        self.mechanics_kb: Optional[PoE2MechanicsKnowledgeBase] = None
        self.gear_comparator: Optional[GearComparator] = None
        self.damage_scaling_analyzer: Optional[DamageScalingAnalyzer] = None
        self.content_readiness_checker: Optional[ContentReadinessChecker] = None

        # AI Components
        self.query_handler: Optional[QueryHandler] = None
        self.recommendation_engine: Optional[RecommendationEngine] = None

        # Path of Building
        self.pob_importer: Optional[PoBImporter] = None
        self.pob_exporter: Optional[PoBExporter] = None
        # Live PoB bridge client (lazy — only built when a pob_* tool is called)
        self.pob_client = None

        # Passive Tree Resolver (for poe.ninja node ID resolution)
        self.passive_tree_resolver: Optional[PassiveTreeResolver] = None

        # Local live-game readers (no API — read the running client's files)
        self.client_log_reader: Optional[ClientLogReader] = None
        self.game_config_reader: Optional[GameConfigReader] = None

        # Conversation context
        self.conversation_contexts: Dict[str, Any] = {}

        self._register_tools()
        self._register_resources()
        self._register_prompts()

    async def initialize(self):
        """Initialize all server components"""
        try:
            debug_log("Starting server initialization...")
            logger.info("Initializing PoE2 Build Optimizer MCP Server...")

            # Initialize database
            debug_log("Initializing database manager...")
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            logger.info("Database initialized")
            debug_log("Database initialization complete")

            # Initialize cache
            debug_log("Initializing cache manager...")
            self.cache_manager = CacheManager()
            await self.cache_manager.initialize()
            logger.info("Cache manager initialized")
            debug_log("Cache manager initialization complete")

            # Initialize rate limiter
            self.rate_limiter = RateLimiter()
            logger.info("Rate limiter initialized")

            # Initialize API client
            self.poe_api = PoEAPIClient(
                cache_manager=self.cache_manager, rate_limiter=self.rate_limiter
            )
            logger.info("PoE API client initialized")

            # Initialize character fetcher
            self.char_fetcher = CharacterFetcher(
                cache_manager=self.cache_manager, rate_limiter=self.rate_limiter
            )
            logger.info("Character fetcher initialized")

            # Initialize trade API
            if settings.ENABLE_TRADE_INTEGRATION:
                self.trade_api = TradeAPI(
                    cache_manager=self.cache_manager, rate_limiter=self.rate_limiter
                )
                logger.info("Trade API initialized")

            # Initialize calculators and optimizers
            self.build_scorer = BuildScorer(self.db_manager)
            self.gear_optimizer = GearOptimizer(self.db_manager)
            self.passive_optimizer = PassiveOptimizer(self.db_manager)
            self.skill_optimizer = SkillOptimizer(self.db_manager)
            logger.info("Optimizers initialized")

            # Initialize comparison system
            self.top_player_fetcher = TopPlayerFetcher(
                cache_manager=self.cache_manager, rate_limiter=self.rate_limiter
            )
            self.comparator = CharacterComparator()
            logger.info("Comparison system initialized")

            # Initialize Phase 1-3 calculators and analyzers
            self.weakness_detector = WeaknessDetector()
            self.gear_evaluator = GearEvaluator()
            self.ehp_calculator = EHPCalculator()
            self.spirit_calculator = SpiritCalculator()
            self.damage_calculator = DamageCalculator()
            logger.info("Advanced calculators and analyzers initialized")

            # Initialize new enhancement features
            self.gem_synergy_calculator = GemSynergyCalculator()
            # Load support gems from SQLite database (authoritative source with display names)
            support_gem_count = await self.gem_synergy_calculator.load_support_gems_from_database(
                self.db_manager
            )
            if support_gem_count > 0:
                logger.info(
                    f"GemSynergyCalculator: Loaded {support_gem_count} support gems from database"
                )
            self.mechanics_kb = PoE2MechanicsKnowledgeBase(
                db_manager=self.db_manager
            )  # Pass db_manager for .datc64 access
            self.gear_comparator = GearComparator()
            self.damage_scaling_analyzer = DamageScalingAnalyzer()
            self.content_readiness_checker = ContentReadinessChecker()
            logger.info("Enhancement features initialized (gem synergy, mechanics KB, etc.)")
            debug_log(
                "Enhancement features ready: gem synergy calculator, mechanics knowledge base, gear comparator, damage scaling analyzer, content readiness checker"
            )

            # Initialize AI components
            if settings.ENABLE_AI_INSIGHTS:
                self.query_handler = QueryHandler()
                self.recommendation_engine = RecommendationEngine(db_manager=self.db_manager)
                logger.info("AI components initialized")

            # Initialize PoB components
            if settings.ENABLE_POB_EXPORT:
                self.pob_importer = PoBImporter()
                self.pob_exporter = PoBExporter()
                logger.info("Path of Building components initialized")

            # Initialize Passive Tree Resolver for poe.ninja node ID resolution
            try:
                self.passive_tree_resolver = PassiveTreeResolver()
                node_count = self.passive_tree_resolver.get_node_count()
                logger.info(f"Passive tree resolver initialized ({node_count} nodes)")
                debug_log(f"Passive tree resolver loaded {node_count} nodes")
            except Exception as e:
                logger.warning(f"Passive tree resolver initialization failed (non-critical): {e}")

            # Initialize local live-game readers (Client.txt + config INI).
            # These are cheap, file-based, and degrade gracefully when the game
            # isn't installed at a known path (is_available() == False).
            try:
                self.client_log_reader = ClientLogReader()
                self.game_config_reader = GameConfigReader()
                log_found = self.client_log_reader.is_available()
                cfg_found = self.game_config_reader.is_available()
                logger.info(
                    f"Local game readers initialized (Client.txt: "
                    f"{'found' if log_found else 'not found'}, "
                    f"config: {'found' if cfg_found else 'not found'})"
                )
            except Exception as e:
                logger.warning(f"Local game reader init failed (non-critical): {e}")

            logger.info("PoE2 Build Optimizer MCP Server initialized successfully")

        except Exception as e:
            debug_log(f"INITIALIZATION ERROR: {e}")
            logger.error(f"Failed to initialize server: {e}")
            import traceback

            debug_log(f"Traceback:\n{traceback.format_exc()}")
            raise

    async def cleanup(self):
        """Cleanup server resources"""
        try:
            logger.info("Cleaning up server resources...")

            if self.trade_api:
                await self.trade_api.close()

            if self.cache_manager:
                await self.cache_manager.close()

            if self.db_manager:
                await self.db_manager.close()

            logger.info("Server cleanup complete")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def handle_call_tool(self, name: str, arguments: dict) -> List[types.TextContent]:
        """
        Public method for handling tool calls (used by integration tests and MCP SDK)
        Dispatches to the appropriate internal handler

        Args:
            name: Tool name
            arguments: Tool arguments dictionary

        Returns:
            List of TextContent responses
        """
        debug_log(f"Tool called: {name}")
        debug_log(f"Arguments: {arguments}")

        try:
            # DATA ACCESS TOOLS (14 tools)
            if name == "analyze_character":
                return await self._handle_analyze_character(arguments)
            elif name == "search_items":
                return await self._handle_search_items(arguments)
            elif name == "search_trade_items":
                return await self._handle_search_trade_items(arguments)
            elif name == "compare_to_top_players":
                return await self._handle_compare_to_top_players(arguments)
            elif name == "inspect_support_gem":
                return await self._handle_inspect_support_gem(arguments)
            elif name == "inspect_spell_gem":
                return await self._handle_inspect_spell_gem(arguments)
            elif name == "list_all_supports":
                return await self._handle_list_all_supports(arguments)
            elif name == "list_all_spells":
                return await self._handle_list_all_spells(arguments)
            elif name == "import_pob":
                return await self._handle_import_pob(arguments)
            elif name == "export_pob":
                return await self._handle_export_pob(arguments)
            elif name == "get_pob_code":
                return await self._handle_get_pob_code(arguments)
            elif name == "pob_status":
                return await self._handle_pob_status(arguments)
            elif name == "pob_install_addon":
                return await self._handle_pob_install_addon(arguments)
            elif name == "pob_get_passive_tree":
                return await self._handle_pob_get_passive_tree(arguments)
            elif name == "pob_get_build":
                return await self._handle_pob_get_build(arguments)
            elif name == "pob_load_build":
                return await self._handle_pob_load_build(arguments)
            elif name == "pob_get_calcs":
                return await self._handle_pob_get_calcs(arguments)
            elif name == "health_check":
                return await self._handle_health_check(arguments)
            elif name == "clear_cache":
                return await self._handle_clear_cache(arguments)
            elif name == "check_tree_freshness":
                return await self._handle_check_tree_freshness(arguments)
            elif name == "check_for_updates":
                return await self._handle_check_for_updates(arguments)
            elif name == "setup_trade_auth":
                return await self._handle_setup_trade_auth(arguments)
            # KNOWLEDGE TOOLS (4 tools)
            elif name == "get_formula":
                return await self._handle_get_formula(arguments)
            elif name == "explain_mechanic":
                return await self._handle_explain_mechanic(arguments)
            elif name == "find_stat_sources":
                return await self._handle_find_stat_sources(arguments)
            elif name == "calculate_character_dps":
                return await self._handle_calculate_character_dps(arguments)
            elif name == "validate_support_combination":
                return await self._handle_validate_support_combination(arguments)
            elif name == "validate_build_constraints":
                return await self._handle_validate_build_constraints(arguments)
            elif name == "reconcile_defensive_stats":
                return await self._handle_reconcile_defensive_stats(arguments)
            elif name == "analyze_passive_tree":
                return await self._handle_analyze_passive_tree(arguments)
            elif name == "import_poe_ninja_url":
                return await self._handle_import_poe_ninja_url(arguments)
            # PASSIVE TREE DATA TOOLS (4 new tools)
            elif name == "list_all_keystones":
                return await self._handle_list_all_keystones(arguments)
            elif name == "inspect_keystone":
                return await self._handle_inspect_keystone(arguments)
            elif name == "list_all_notables":
                return await self._handle_list_all_notables(arguments)
            elif name == "inspect_passive_node":
                return await self._handle_inspect_passive_node(arguments)
            # BASE ITEM DATA TOOLS (2 new tools)
            elif name == "list_all_base_items":
                return await self._handle_list_all_base_items(arguments)
            elif name == "inspect_base_item":
                return await self._handle_inspect_base_item(arguments)
            # MOD DATA TOOLS (4 new tools)
            elif name == "inspect_mod":
                return await self._handle_inspect_mod(arguments)
            elif name == "list_all_mods":
                return await self._handle_list_all_mods(arguments)
            elif name == "search_mods_by_stat":
                return await self._handle_search_mods_by_stat(arguments)
            elif name == "get_mod_tiers":
                return await self._handle_get_mod_tiers(arguments)
            # MOD VALIDATION TOOLS (Tier 2)
            elif name == "validate_item_mods":
                return await self._handle_validate_item_mods(arguments)
            elif name == "get_available_mods":
                return await self._handle_get_available_mods(arguments)
            # LOCAL LIVE-GAME TOOLS (read the running client's local files)
            elif name == "get_live_game_state":
                return await self._handle_get_live_game_state(arguments)
            elif name == "get_game_config":
                return await self._handle_get_game_config(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            debug_log(f"TOOL ERROR in {name}: {e}")
            logger.error(f"Error in tool {name}: {e}")
            import traceback

            debug_log(f"Traceback:\n{traceback.format_exc()}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    def _register_tools(self):
        """Register MCP tools"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List all available tools - 18 focused MCP tools

            MCP Philosophy: MCP = Data Access Layer, Claude = Intelligence Layer
            These tools provide data Claude cannot access natively. Claude handles
            all analysis, optimization, and calculation using the formulas provided.
            """
            return [
                # ============================================
                # DATA ACCESS TOOLS (14 tools)
                # ============================================
                # Character Data Access
                types.Tool(
                    name="analyze_character",
                    description=(
                        "Fetch PoE2 character data from poe.ninja API. Returns raw "
                        "character stats, gear, skills, and passives for Claude to "
                        "analyze. The response includes the raw `passive_node_ids` "
                        "array (plus `unresolved_node_ids` against the local tree) "
                        "so analyze_passive_tree can be chained directly (#149)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {
                                "type": "string",
                                "description": "Path of Exile account name",
                            },
                            "character": {
                                "type": "string",
                                "description": "Character name to fetch",
                            },
                            "league": {
                                "type": "string",
                                "description": "League name (e.g., 'Abyss', 'Standard')",
                                "default": "Abyss",
                            },
                        },
                        "required": ["account", "character"],
                    },
                ),
                # Compare to top players
                types.Tool(
                    name="compare_to_top_players",
                    description="Fetch top ladder players using the same skills for comparison. Returns raw data about what high-performers do differently.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_name": {"type": "string", "description": "PoE account name"},
                            "character_name": {
                                "type": "string",
                                "description": "Character name to compare",
                            },
                            "league": {
                                "type": "string",
                                "description": "League name",
                                "default": "Standard",
                            },
                            "top_player_limit": {
                                "type": "integer",
                                "description": "Number of top players to fetch",
                                "default": 10,
                            },
                        },
                        "required": ["account_name", "character_name"],
                    },
                ),
                # Database Searches
                types.Tool(
                    name="search_items",
                    description="Search the local game database for items by name, type, or filters.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Item name or type to search",
                            },
                            "filters": {
                                "type": "object",
                                "description": "Additional filters (rarity, item_class, etc.)",
                            },
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="search_trade_items",
                    description="Search the official PoE2 trade site for items. Requires POESESSID (use setup_trade_auth first).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "league": {
                                "type": "string",
                                "description": "League name",
                                "default": "Standard",
                            },
                            "character_needs": {
                                "type": "object",
                                "description": "What the character needs (resistances, life, ES, item_slots)",
                            },
                            "max_price_chaos": {
                                "type": "integer",
                                "description": "Maximum price in chaos orbs",
                            },
                        },
                        "required": ["league", "character_needs"],
                    },
                ),
                # Gem Inspection
                types.Tool(
                    name="inspect_support_gem",
                    description="Get complete data for a support gem including tags, effects, incompatibilities, spirit cost.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "support_name": {
                                "type": "string",
                                "description": "Name of the support gem",
                            }
                        },
                        "required": ["support_name"],
                    },
                ),
                types.Tool(
                    name="inspect_spell_gem",
                    description="Get complete data for a spell gem including tags, base damage, cast time, mana/spirit cost.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spell_name": {
                                "type": "string",
                                "description": "Name of the spell gem (e.g. 'Shred', 'Fireball')",
                            },
                            "name": {"type": "string", "description": "Alias for spell_name"},
                            "gem_name": {"type": "string", "description": "Alias for spell_name"},
                        },
                    },
                ),
                types.Tool(
                    name="list_all_supports",
                    description="List all support gems with optional filtering by tags, spirit cost, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by tags",
                            },
                            "max_spirit": {"type": "integer", "description": "Maximum spirit cost"},
                            "sort_by": {
                                "type": "string",
                                "enum": ["name", "spirit_cost", "damage_multiplier"],
                                "default": "name",
                            },
                            "limit": {"type": "integer", "default": 50},
                        },
                    },
                ),
                types.Tool(
                    name="list_all_spells",
                    description="List all spell gems with optional filtering by element, tags, damage.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_element": {
                                "type": "string",
                                "enum": ["fire", "cold", "lightning", "physical", "chaos"],
                            },
                            "filter_tags": {"type": "array", "items": {"type": "string"}},
                            "min_damage": {"type": "number"},
                            "sort_by": {
                                "type": "string",
                                "enum": ["name", "base_damage", "cast_time", "dps"],
                                "default": "name",
                            },
                            "limit": {"type": "integer", "default": 50},
                        },
                    },
                ),
                # Path of Building Integration
                types.Tool(
                    name="import_pob",
                    description="Import a Path of Building build. Accepts a local file path (most reliable — a saved .xml build or a .txt containing the share code, auto-detected), raw uncompressed PoB XML, or an inline base64 share code. Provide exactly one of the three inputs. Returns parsed build data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pob_file_path": {
                                "type": "string",
                                "description": "Path to a local file containing the PoB build — either raw XML or a base64 share code (auto-detected). Preferred over pob_code: long codes corrupt easily when passed inline.",
                            },
                            "pob_xml": {
                                "type": "string",
                                "description": "Raw uncompressed Path of Building XML",
                            },
                            "pob_code": {
                                "type": "string",
                                "description": "Path of Building share code (base64 + zlib). Whitespace/newlines and URL-safe base64 are tolerated.",
                            },
                        },
                        "required": [],
                    },
                ),
                types.Tool(
                    name="export_pob",
                    description="Export character data to Path of Building format.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": "Character data to export",
                            }
                        },
                        "required": ["character_data"],
                    },
                ),
                types.Tool(
                    name="get_pob_code",
                    description="Fetch a ready-to-use PoB code from poe.ninja for a character.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "Account name"},
                            "character": {"type": "string", "description": "Character name"},
                        },
                        "required": ["account", "character"],
                    },
                ),
                # Live Path of Building Bridge (TCP to a running PoB instance)
                types.Tool(
                    name="pob_status",
                    description="Check the live Path of Building bridge: whether PoB (PoE2) is installed, whether the MCP Bridge addon is deployed and Launch.lua is patched, and whether a running PoB is reachable on 127.0.0.1:49085 right now. Use this first before other pob_* tools.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "port": {
                                "type": "integer",
                                "description": "Bridge port (default 49085)",
                                "default": 49085,
                            }
                        },
                        "required": [],
                    },
                ),
                types.Tool(
                    name="pob_install_addon",
                    description="Install the MCP Bridge addon into the local Path of Building (PoE2) so the live bridge works. Auto-detects the PoB install (or pass pob_path), copies the addon, and patches Launch.lua (with a backup). The user must restart PoB afterward. Idempotent.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pob_path": {
                                "type": "string",
                                "description": "Path to the PoB install root (folder containing src/Launch.lua). Auto-detected if omitted.",
                            }
                        },
                        "required": [],
                    },
                ),
                types.Tool(
                    name="pob_get_passive_tree",
                    description="Pull the allocated passive tree from the build currently open in a running Path of Building: class, ascendancy, every allocated node (id, name, keystone/notable flags, stats) and total points. Requires PoB running with the bridge addon and a build loaded.",
                    inputSchema={"type": "object", "properties": {}, "required": []},
                ),
                types.Tool(
                    name="pob_get_build",
                    description="Pull the build currently open in a running Path of Building as a PoB share code (default) or raw XML. Use 'code' to get a copy-pasteable share code.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "format": {
                                "type": "string",
                                "enum": ["code", "xml"],
                                "description": "'code' for a PoB share code, 'xml' for raw build XML",
                                "default": "code",
                            }
                        },
                        "required": [],
                    },
                ),
                types.Tool(
                    name="pob_load_build",
                    description="Load a build into a running Path of Building so the user can see it. Accepts a PoB share code (preferred — what players paste) or raw XML. PoB must be running with the bridge addon.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "PoB share code (base64+zlib) to load",
                            },
                            "xml": {
                                "type": "string",
                                "description": "Raw PoB build XML (alternative to code)",
                            },
                            "name": {
                                "type": "string",
                                "description": "Display name for the loaded build",
                                "default": "MCP Build",
                            },
                        },
                        "required": [],
                    },
                ),
                types.Tool(
                    name="pob_get_calcs",
                    description="Pull computed stats (DPS, Life/ES, resistances, attributes, max hit taken) from PoB's own calculation engine for the build currently open in a running Path of Building.",
                    inputSchema={"type": "object", "properties": {}, "required": []},
                ),
                # System Tools
                types.Tool(
                    name="health_check",
                    description="Run diagnostic checks on the MCP server (database, API, config).",
                    inputSchema={
                        "type": "object",
                        "properties": {"verbose": {"type": "boolean", "default": False}},
                    },
                ),
                types.Tool(
                    name="clear_cache",
                    description="Clear all cached data (memory, SQLite, Redis).",
                    inputSchema={"type": "object", "properties": {}},
                ),
                types.Tool(
                    name="check_tree_freshness",
                    description="Self-diagnostic: compare local game-data version (data/game/version.json) against poe.ninja's current PassiveTree tag from index-state. Reports whether your local data/game/ datasets are up to date with the live patch, or behind. Strict change-detection only — does not download or modify any data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "verbose": {
                                "type": "boolean",
                                "default": False,
                                "description": "Include full index-state snapshot list and per-dataset breakdown",
                            }
                        },
                    },
                ),
                types.Tool(
                    name="check_for_updates",
                    description=(
                        "Check whether newer game data or server code is available, and "
                        "optionally apply it WITH THE USER'S PERMISSION. Reports both layers: "
                        "game-data bundle (GitHub Releases) and code (git fast-forward for "
                        "source installs, or reinstall guidance for packaged/.mcpb installs). "
                        "By default it only reports (no changes). Pass apply=true to grant "
                        "explicit consent and apply pending updates now. Standing policy can "
                        "also be set via POE2_MCP_AUTO_UPDATE=1 (auto) or "
                        "POE2_MCP_NO_DATA_FETCH=1 / POE2_MCP_NO_CODE_CHECK=1 (off)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "apply": {
                                "type": "boolean",
                                "default": False,
                                "description": "Apply pending updates now (explicit consent). Default false = report only.",
                            },
                            "layer": {
                                "type": "string",
                                "enum": ["all", "data", "code"],
                                "default": "all",
                                "description": "Which layer to check/apply. Default 'all'.",
                            },
                        },
                    },
                ),
                types.Tool(
                    name="setup_trade_auth",
                    description="Set up trade API authentication by extracting POESESSID via browser login.",
                    inputSchema={
                        "type": "object",
                        "properties": {"headless": {"type": "boolean", "default": False}},
                    },
                ),
                # ============================================
                # KNOWLEDGE TOOLS (4 tools)
                # ============================================
                # Formulas - Claude does the math
                types.Tool(
                    name="get_formula",
                    description="Get PoE2 calculation formulas for Claude to use. Covers DPS, EHP, armor, resistance, spirit, stun, crit, conversion, DoT, block. Claude performs calculations using these formulas.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "formula_type": {
                                "type": "string",
                                "description": "Formula type: dps, ehp, armor, resistance, spirit, stun, crit, conversion, dot, block. Leave empty to list all.",
                            }
                        },
                    },
                ),
                # Mechanic Explanations
                types.Tool(
                    name="explain_mechanic",
                    description=(
                        "Explain PoE2 game mechanics or look up a stat_id. PRIMARY source: "
                        "data/game/stat_descriptions/ (canonical game-shipped text, "
                        "16,533 entries extracted from .csd). FALLBACK: hand-authored "
                        "summaries in src/knowledge/poe2_mechanics.py (clearly labeled as "
                        "community interpretation in the response). Call without "
                        "mechanic_name to see what's available."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "mechanic_name": {
                                "type": "string",
                                "description": (
                                    "Mechanic name (e.g. 'freeze', 'ignite proliferation'), "
                                    "or a stat_id (e.g. 'support_ignite_proliferation_radius'), "
                                    "or a substring to search (e.g. 'proliferation'). "
                                    "Omit entirely to see overview + sample suggestions."
                                ),
                            },
                            "cluster": {
                                "type": "boolean",
                                "description": (
                                    "Cluster-dump mode: return ALL related stat_ids "
                                    "(root + per-skill canonical) AND the skills/"
                                    "passives/mods that grant each, in one call — "
                                    "instead of chaining substring searches. "
                                    "Default false."
                                ),
                            },
                        },
                        "required": [],
                    },
                ),
                types.Tool(
                    name="find_stat_sources",
                    description=(
                        "Reverse lookup: which skills, passive/ascendancy nodes, and "
                        "item mods grant or reference a stat. Accepts a stat_id, a "
                        "stat_id substring, or stat text (e.g. 'withered', "
                        "'spell_minimum_base_fire_damage', 'chance to Shock'). Sources: "
                        "skill_gems_v2 statSets (1,249 skills), psg_passive_nodes "
                        "(keystones/notables/smalls), ascendancy notables (when local "
                        "data present), and the canonical mods table."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "stat_id, stat_id substring, or stat text fragment",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max results per source category (default 15)",
                            },
                        },
                        "required": ["query"],
                    },
                ),
                # Server-side DPS calculation (P5)
                types.Tool(
                    name="calculate_character_dps",
                    description=(
                        "Compute spell DPS server-side using PoE2 formulas. "
                        "Accepts an aggregated set of modifiers (sum of increased %, "
                        "list of more multipliers, added flat damage, crit, cast speed, "
                        "optional enemy resistances) and returns a structured DPS "
                        "breakdown — base damage, increased/more multipliers, crit "
                        "expected hit, post-resistance final, casts/sec, DPS. The math "
                        "lives in src/calculator/spell_dps_calculator.py and is the "
                        "single source of truth. Use this instead of asking the AI to "
                        "do the math in its head."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spell_name": {
                                "type": "string",
                                "description": (
                                    "Spell name (e.g. 'Ice Nova', 'Fireball', 'Spark'). "
                                    "Looked up first in the built-in SPELL_DATABASE "
                                    "(arc/spark/fireball), then in data/game/skill_gems/"
                                    "skill_gems_v2.json (~1,249 spells, post-#119). "
                                    "If neither resolves, supply spell_stats."
                                ),
                            },
                            "gem_level": {
                                "type": "integer",
                                "description": (
                                    "Gem level for the v2 lookup (1..40, clamped). "
                                    "Defaults to 20, PoB's natural-max for most "
                                    "player skills. Ignored when using SPELL_DATABASE "
                                    "or spell_stats."
                                ),
                            },
                            "spell_stats": {
                                "type": "object",
                                "description": (
                                    "Override spell base stats. Shape: "
                                    "{base_damage_min, base_damage_max, "
                                    "damage_effectiveness, base_crit_chance, "
                                    "base_cast_time, damage_types (list)}."
                                ),
                            },
                            "increased_spell_damage": {
                                "type": "number",
                                "description": "Sum of all %increased spell damage (additive). Default 0.",
                            },
                            "more_multipliers": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": (
                                    "List of %more damage multipliers (each applied "
                                    "multiplicatively). E.g. [25, 30, 20] for three "
                                    "support gems giving +25/+30/+20%."
                                ),
                            },
                            "added_damage": {
                                "type": "object",
                                "description": (
                                    "Flat added damage by type. Shape: "
                                    "{fire, cold, lightning, chaos, physical}. "
                                    "All default to 0."
                                ),
                            },
                            "increased_cast_speed": {
                                "type": "number",
                                "description": "Sum of all %increased cast speed. Default 0.",
                            },
                            "increased_crit_chance": {
                                "type": "number",
                                "description": "Sum of all %increased crit chance. Default 0.",
                            },
                            "added_crit_bonus": {
                                "type": "number",
                                "description": (
                                    "Crit damage bonus. PoE2 base is 100 (= 2x on crit). "
                                    "Default 100."
                                ),
                            },
                            "increased_crit_damage": {
                                "type": "number",
                                "description": "Sum of all %increased crit damage. Default 0.",
                            },
                            "max_mana": {
                                "type": "number",
                                "description": "Maximum mana pool (for Archmage). Default 0.",
                            },
                            "has_archmage": {
                                "type": "boolean",
                                "description": "Whether Archmage support is active. Default false.",
                            },
                            "enemy": {
                                "type": "object",
                                "description": (
                                    "Enemy defensive stats. Shape: "
                                    "{fire_resistance, cold_resistance, "
                                    "lightning_resistance, chaos_resistance, "
                                    "physical_resistance, fire_exposure, "
                                    "cold_exposure, lightning_exposure, "
                                    "fire_penetration, cold_penetration, "
                                    "lightning_penetration, is_shocked}. "
                                    "Defaults to a target dummy (all zeros)."
                                ),
                            },
                            "dot": {
                                "type": "object",
                                "description": (
                                    "Optional damage-over-time layer (#159). When present, "
                                    "the response adds ailment/skill-DoT breakdowns and "
                                    "total_sustained_dps (hit + DoT). Shape: "
                                    "{ailments: [{type: 'ignite'|'poison'|'bleed', "
                                    "chance (0-100, default 100), increased_magnitude, "
                                    "more_multipliers (list), increased_duration, "
                                    "stack_limit (poison; default 1), enemy_moving (bleed), "
                                    "aggravated (bleed)}], "
                                    "skill_dot: {base_dps (REQUIRED — e.g. Essence Drain's "
                                    "base chaos DPS at gem level; the 0.5 extraction lacks "
                                    "absolute DoT base values so the caller supplies it), "
                                    "damage_type (default 'chaos'), increased, "
                                    "more_multipliers, uptime (0-1, default 1)}, "
                                    "hit_damage_by_type: optional {fire, cold, lightning, "
                                    "chaos, physical} override of the expected hit's type "
                                    "split — otherwise derived from spell base type + added "
                                    "damage}. PoE2 ailment math: ignite 20%/s of fire hit "
                                    "for 4s; poison 20%/s of phys+chaos for 2s (stack limit "
                                    "applies); bleed 15%/s of phys for 5s, x2 while moving/"
                                    "aggravated. Non-stacking ailments cap at 1 active."
                                ),
                            },
                        },
                        "required": [],
                    },
                ),
                # Validation
                types.Tool(
                    name="validate_support_combination",
                    description=(
                        "Check if support gems are compatible with each other and with "
                        "the target spell. Hard conflicts (Faster+Slower Projectiles, "
                        "Concentrated Effect+Increased AoE) mark the combination "
                        "invalid. Semantic conflicts (Added Fire Damage on a cold-only "
                        "spell, Minion Damage on a non-minion skill) are surfaced as "
                        "WARNINGS — the AI can still recommend the combo but knows "
                        "it's wasted unless there's conversion."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "support_gems": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Support gem names to validate (e.g. ['Rage', 'Brutality'])",
                            },
                            "support_gem_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Alias for support_gems",
                            },
                            "names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Alias for support_gems",
                            },
                            "spell_name": {
                                "type": "string",
                                "description": (
                                    "Optional target spell name (e.g. 'Ice Nova', "
                                    "'Fireball'). When supplied, the spell's tags "
                                    "are read from data/game/skill_gems/ and "
                                    "checked against each support's name-pattern "
                                    "damage-type requirements. Catches recommendations "
                                    "like 'Added Fire Damage' on a cold-tagged spell."
                                ),
                            },
                        },
                    },
                ),
                types.Tool(
                    name="validate_build_constraints",
                    description=(
                        "Validate build against game constraints (resistances, "
                        "spirit, survivability baseline). Fields not provided "
                        "are SKIPPED and reported as such — never validated as "
                        "zero. Explicit null values are treated as absent."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": (
                                    "Character stats to validate. Accepted shapes: "
                                    "resistances as flat {fire_resistance, "
                                    "cold_resistance, lightning_resistance, "
                                    "chaos_resistance}, legacy {fire_res, ...}, or "
                                    "nested {resistances: {fire, cold, lightning, "
                                    "chaos}}; survivability as {life, energy_shield} "
                                    "or combined {life_plus_es}; plus {spirit, "
                                    "spirit_reserved, level}. All numeric; null = "
                                    "not provided."
                                ),
                            }
                        },
                        "required": ["character_data"],
                    },
                ),
                types.Tool(
                    name="reconcile_defensive_stats",
                    description=(
                        "Run the local EHP/defense calculators on a poe.ninja "
                        "charModel and diff each headline stat (effective HP, "
                        "per-element max hits) against poe.ninja's own computed "
                        "defensiveStats — a per-stat delta table with tolerance "
                        "flags. Use to detect drift/bugs in the local calculators "
                        "against a live oracle (issue #139 harness; was never "
                        "registered as a tool until #154)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "char_model": {
                                "type": "object",
                                "description": (
                                    "A poe.ninja charModel dict (or just its "
                                    "defensiveStats sub-dict). Obtain via "
                                    "analyze_character's raw data or the profile API."
                                ),
                            },
                            "tolerance_pct": {
                                "type": "object",
                                "description": (
                                    "Optional per-stat tolerance overrides in percent, "
                                    'e.g. {"effective_hp": 10}. Default 15% per stat.'
                                ),
                            },
                        },
                        "required": ["char_model"],
                    },
                ),
                # Passive Tree Analysis Tool
                types.Tool(
                    name="analyze_passive_tree",
                    description="Analyze passive tree allocation, find paths to notables, and get recommendations. Resolves poe.ninja node IDs to full passive data including names, stats, and connections.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_ids": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "List of allocated passive node IDs from poe.ninja",
                            },
                            "target_notable": {
                                "type": "string",
                                "description": "Optional: Name of a notable to find path to",
                            },
                            "find_recommendations": {
                                "type": "boolean",
                                "description": "Whether to find nearest unallocated notables",
                                "default": True,
                            },
                        },
                        "required": ["node_ids"],
                    },
                ),
                # URL Import Tool
                types.Tool(
                    name="import_poe_ninja_url",
                    description="Import and analyze a character directly from a poe.ninja profile URL. Parses the URL to extract account and character, then fetches full character data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "poe.ninja profile URL (e.g., https://poe.ninja/poe2/profile/AccountName/character/CharacterName)",
                            }
                        },
                        "required": ["url"],
                    },
                ),
                # ============================================
                # PASSIVE TREE DATA TOOLS (4 new tools)
                # ============================================
                types.Tool(
                    name="list_all_keystones",
                    description="List all keystone passive nodes with their full stats. Keystones are powerful build-defining passives with major tradeoffs.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_stat": {
                                "type": "string",
                                "description": "Filter keystones by stat text (e.g., 'life', 'crit', 'leech')",
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["name", "stat_count"],
                                "default": "name",
                            },
                        },
                    },
                ),
                types.Tool(
                    name="inspect_keystone",
                    description="Get complete details for a specific keystone by name, including all stats and effects.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keystone_name": {
                                "type": "string",
                                "description": "Name of the keystone (e.g., 'Chaos Inoculation', 'Vaal Pact', 'Resolute Technique')",
                            },
                            "name": {"type": "string", "description": "Alias for keystone_name"},
                        },
                    },
                ),
                types.Tool(
                    name="list_all_notables",
                    description="List all notable passive nodes. Notables are medium-power passives that define build paths.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_stat": {
                                "type": "string",
                                "description": "Filter notables by stat text (e.g., 'projectile', 'fire', 'attack')",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number to return",
                                "default": 100,
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["name", "stat_count"],
                                "default": "name",
                            },
                        },
                    },
                ),
                types.Tool(
                    name="inspect_passive_node",
                    description="Get complete details for any passive node by name or ID. Works for keystones, notables, and small nodes.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_name": {
                                "type": "string",
                                "description": "Name of the passive node",
                            },
                            "node_id": {
                                "type": "integer",
                                "description": "Numeric ID of the passive node (alternative to name)",
                            },
                        },
                    },
                ),
                # ============================================
                # BASE ITEM DATA TOOLS (2 new tools)
                # ============================================
                types.Tool(
                    name="list_all_base_items",
                    description="List all base item types in the game (weapons, armor, accessories).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_type": {
                                "type": "string",
                                "description": "Filter by item type (e.g., 'Sword', 'Helmet', 'Ring')",
                            },
                            "filter_name": {
                                "type": "string",
                                "description": "Filter by name substring",
                            },
                            "limit": {"type": "integer", "default": 100},
                        },
                    },
                ),
                types.Tool(
                    name="inspect_base_item",
                    description="Get complete details for a specific base item type.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "item_name": {"type": "string", "description": "Name of the base item"}
                        },
                        "required": ["item_name"],
                    },
                ),
                # MOD DATA TOOLS (4 new tools)
                types.Tool(
                    name="inspect_mod",
                    description="Get complete details for a specific mod by ID, including generation type, level requirement, and stat values.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "mod_id": {
                                "type": "string",
                                "description": "Mod ID (e.g., 'IncreasedLife5', 'FireResist3')",
                            }
                        },
                        "required": ["mod_id"],
                    },
                ),
                types.Tool(
                    name="list_all_mods",
                    description="List all mods with optional filtering by generation type (PREFIX, SUFFIX, IMPLICIT, CORRUPTED) and stat keywords.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "generation_type": {
                                "type": "string",
                                "description": "Filter by generation type: PREFIX, SUFFIX, IMPLICIT, or CORRUPTED",
                                "enum": ["PREFIX", "SUFFIX", "IMPLICIT", "CORRUPTED"],
                            },
                            "filter_stat": {
                                "type": "string",
                                "description": "Filter by stat keyword (e.g., 'life', 'fire', 'resistance')",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of mods to return",
                                "default": 50,
                            },
                        },
                    },
                ),
                types.Tool(
                    name="search_mods_by_stat",
                    description="Search for mods that grant a specific stat effect. Returns all mods matching the stat keyword.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "stat_keyword": {
                                "type": "string",
                                "description": "Stat keyword to search for (e.g., 'fire resistance', 'increased life', 'physical damage')",
                            },
                            "generation_type": {
                                "type": "string",
                                "description": "Optional: Filter by generation type (PREFIX, SUFFIX, IMPLICIT, CORRUPTED)",
                                "enum": ["PREFIX", "SUFFIX", "IMPLICIT", "CORRUPTED"],
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 50,
                            },
                        },
                        "required": ["stat_keyword"],
                    },
                ),
                types.Tool(
                    name="get_mod_tiers",
                    description="Get all tier variations of a mod family (e.g., IncreasedLife1-13). Shows progression from T1 to highest tier with level requirements and values.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "mod_base": {
                                "type": "string",
                                "description": "Base mod name without tier number (e.g., 'IncreasedLife', 'FireResist')",
                            }
                        },
                        "required": ["mod_base"],
                    },
                ),
                # TIER 2 MOD VALIDATION TOOLS
                types.Tool(
                    name="validate_item_mods",
                    description="Validate if a set of mods can legally exist on an item. Checks for mod family conflicts (can't have 2 tiers of same mod), prefix/suffix limits, and generation type rules.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "mod_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of mod IDs to validate (e.g., ['Strength1', 'FireResist3', 'AddedLightningDamage5'])",
                            },
                            "item_level": {
                                "type": "integer",
                                "description": "Item level to check mod requirements against",
                                "default": 83,
                            },
                        },
                        "required": ["mod_ids"],
                    },
                ),
                types.Tool(
                    name="get_available_mods",
                    description="Get all mods that could roll on an item type. Filter by generation type (PREFIX/SUFFIX), item base class (e.g. Wand, Ring, Body Armour), and level requirements.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "generation_type": {
                                "type": "string",
                                "description": "Filter by generation type: PREFIX or SUFFIX",
                                "enum": ["PREFIX", "SUFFIX"],
                            },
                            "item_class": {
                                "type": "string",
                                "description": (
                                    "Optional: item base class / slot to filter by "
                                    "(e.g. 'Wand', 'Sceptre', 'Ring', 'Amulet', "
                                    "'Belt', 'Helmet', 'Gloves', 'Boots', "
                                    "'Body Armour', 'Shield', 'Quiver', 'Focus'). "
                                    "Matches the mod's SpawnTags. Omit for all item types."
                                ),
                            },
                            "max_level": {
                                "type": "integer",
                                "description": "Maximum level requirement (filters mods you can't roll yet)",
                                "default": 100,
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of mods to return",
                                "default": 100,
                            },
                        },
                        "required": ["generation_type"],
                    },
                ),
                # ============================================
                # LOCAL LIVE-GAME TOOLS (read the running client's local files)
                # ============================================
                types.Tool(
                    name="get_live_game_state",
                    description=(
                        "Read the player's CURRENT in-game state from the local "
                        "PoE2 client log (Client.txt) while the game is running. "
                        "Returns the live character name, class/ascendancy, level, "
                        "current area (internal code + monster level + instance seed), "
                        "instance server, recent death count, and AFK status. "
                        "Purely local file read — no API, no network. This is the "
                        "primary fallback for character identity now that poe.ninja "
                        "is unavailable for patch 0.5. Returns available=false if the "
                        "game is not installed at a known path."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_recent_events": {
                                "type": "boolean",
                                "description": "Also return the recent parsed event stream (level-ups, zone changes, deaths, whispers).",
                                "default": False,
                            },
                            "event_limit": {
                                "type": "integer",
                                "description": "Max recent events to return when include_recent_events is true.",
                                "default": 25,
                            },
                            "log_path": {
                                "type": "string",
                                "description": "Optional explicit path to Client.txt (overrides auto-discovery).",
                            },
                        },
                    },
                ),
                types.Tool(
                    name="get_game_config",
                    description=(
                        "Read the player's local PoE2 client settings "
                        "(poe2_production_Config.ini). Returns gateway, input mode "
                        "(wasd vs click-to-move — affects build/skill recommendations), "
                        "current act, display resolution, renderer, framerate cap, and "
                        "GPU. Purely local file read. NOTE: account_name is empty under "
                        "Steam authentication — use get_live_game_state for character "
                        "identity. Set full=true for the complete raw config."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "full": {
                                "type": "boolean",
                                "description": "Return the complete raw config (all sections) instead of the build-relevant summary.",
                                "default": False,
                            },
                            "config_path": {
                                "type": "string",
                                "description": "Optional explicit path to poe2_production_Config.ini (overrides auto-discovery).",
                            },
                        },
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
            """Handle tool calls (MCP SDK callback - delegates to class method)"""
            return await self.handle_call_tool(name, arguments)

    def _register_resources(self):
        """Register MCP resources"""

        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            """List available resources"""
            return [
                types.Resource(
                    uri="poe2://game-data/items",
                    name="Item Database",
                    description="Complete PoE2 item database",
                    mimeType="application/json",
                ),
                types.Resource(
                    uri="poe2://game-data/passives",
                    name="Passive Tree",
                    description="Complete passive skill tree data",
                    mimeType="application/json",
                ),
                types.Resource(
                    uri="poe2://game-data/skills",
                    name="Skill Gems",
                    description="All skill gem data",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource data"""
            if uri == "poe2://game-data/items":
                items = await self.db_manager.get_all_items()
                return json.dumps(items, indent=2)
            elif uri == "poe2://game-data/passives":
                passives = await self.db_manager.get_passive_tree()
                return json.dumps(passives, indent=2)
            elif uri == "poe2://game-data/skills":
                skills = await self.db_manager.get_all_skills()
                return json.dumps(skills, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")

    def _register_prompts(self):
        """Register MCP prompts"""

        @self.server.list_prompts()
        async def handle_list_prompts() -> List[types.Prompt]:
            """List available prompts"""
            return [
                types.Prompt(
                    name="analyze_build",
                    description="Comprehensive build analysis prompt",
                    arguments=[
                        types.PromptArgument(
                            name="character_data",
                            description="Character data to analyze",
                            required=True,
                        )
                    ],
                ),
                types.Prompt(
                    name="optimize_for_goal",
                    description="Goal-specific build optimization",
                    arguments=[
                        types.PromptArgument(
                            name="goal",
                            description="Optimization goal (dps, defense, etc.)",
                            required=True,
                        )
                    ],
                ),
            ]

    # Tool Implementation Methods

    async def _handle_analyze_character(self, args: dict) -> List[types.TextContent]:
        """Handle character analysis"""
        account = args["account"]
        character = args["character"]
        include_recommendations = args.get("include_recommendations", True)

        try:
            # Fetch character data using the new API-based fetcher
            character_data = await self.char_fetcher.get_character(
                account_name=account, character_name=character, league=args.get("league", "Abyss")
            )

            if not character_data:
                # Build the actual URLs attempted from the league + account + character.
                # Slug derivation matches PoeNinjaAPI._get_league_slug (LEAGUE_MAPPINGS
                # with lower+replace-spaces fallback) so the displayed URLs reflect what
                # the fetcher actually tried.
                league_arg = args.get("league", "Standard")
                league_slug = league_arg.lower().replace(" ", "")
                profile_url = (
                    f"https://poe.ninja/poe2/builds/{league_slug}/character/{account}/{character}"
                )

                # CRITICAL #4 context — see issue #61. poe.ninja migrated to a
                # client-side rendered Astro SPA at/around Patch 0.5 (2026-05-29).
                # Both per-character data paths can fail without it being the user's
                # fault: (a) JSON API returns 404 for characters not in the current
                # snapshot version, (b) HTML scrape returns a 200 SPA shell with no
                # embedded data. Surface this UP-FRONT so users don't waste time
                # tweaking profile-privacy and account-format settings that aren't
                # actually the problem.
                error_msg = f"""# Character Fetch Failed

**Character:** {character}
**Account:** {account}
**League:** {league_arg}

## :warning: Likely cause: poe.ninja SPA migration (Patch 0.5)

As of Patch 0.5 "Return of the Ancients" (2026-05-29), poe.ninja migrated their builds and character pages to a client-side rendered SPA. The endpoints this tool relies on either return 404 (for characters not in the current snapshot version) or return an SPA shell with no embedded data. **If your character page loads fine in your browser but the MCP can't fetch it, this is almost certainly the cause** — not a problem with your account or character settings.

Tracked at https://github.com/HivemindOverlord/poe2-mcp/issues/61.

## How to verify it's the SPA migration vs your config

1. Open your character's profile page in a browser: <{profile_url}>
2. If the page loads with your character data visible → **SPA migration** (#61); nothing you can do on your end until poe.ninja's new endpoint shape is reverse-engineered
3. If the page shows "Character not found" → your character isn't on poe.ninja's ladder/indexer; jump to the next-steps checklist below

## Next-steps checklist (only if your browser ALSO can't see the character)

- **Profile must be public** — check https://www.pathofexile.com/account/view-profile/{account}/characters
- **Account name format** — try without discriminator (`{account.split('-')[0] if '-' in account else account.split('#')[0] if '#' in account else account}`) and with (`{account}`)
- **Character name** — case-sensitive, no extra spaces, must be in current league
- **poe.ninja indexing delay** — new characters take 1-2 hours to appear; very low-level characters may never index

## Don't bother with these (also broken by #61)

- `compare_to_top_players` — same SPA migration breaks ladder enumeration
- `import_poe_ninja_url` — wraps `analyze_character`; same failure
"""
                return [types.TextContent(type="text", text=error_msg)]

            # Calculate actual stats instead of using stub build_scorer
            analysis = {
                "overall_score": 0.0,
                "tier": "Unknown",
                "strengths": [],
                "weaknesses": [],
                "dps": character_data.get("dps", 0),
                "ehp": 0,
                "defense_rating": 0.0,
            }

            # Calculate EHP if calculator is available
            if self.ehp_calculator:
                try:
                    # Import with fallback for both direct and module execution
                    try:
                        from .calculator.ehp_calculator import (
                            DefensiveStats,
                            ThreatProfile,
                            DamageType,
                        )
                    except ImportError:
                        from src.calculator.ehp_calculator import (
                            DefensiveStats,
                            ThreatProfile,
                            DamageType,
                        )

                    # Get stats from the nested stats object (poe.ninja format uses camelCase)
                    stats = character_data.get("stats", {})
                    life = stats.get("life", 0) or 0
                    energy_shield = stats.get("energyShield", 0) or 0
                    armor = stats.get("armour", 0) or 0
                    evasion = stats.get("evasionRating", 0) or 0
                    block_chance = stats.get("blockChance", 0) or 0
                    fire_res = stats.get("fireResistance", 0) or 0
                    cold_res = stats.get("coldResistance", 0) or 0
                    lightning_res = stats.get("lightningResistance", 0) or 0
                    chaos_res = stats.get("chaosResistance", 0) or 0

                    logger.info(
                        f"[ANALYZE_CHAR] Calculating EHP with Life: {life}, ES: {energy_shield}"
                    )

                    defensive_stats = DefensiveStats(
                        life=life,
                        energy_shield=energy_shield,
                        armor=armor,
                        evasion=evasion,
                        block_chance=block_chance,
                        fire_res=fire_res,
                        cold_res=cold_res,
                        lightning_res=lightning_res,
                        chaos_res=chaos_res,
                    )

                    # Calculate average EHP across damage types
                    threat = ThreatProfile(expected_hit_size=1000.0)
                    phys_result = self.ehp_calculator.calculate_ehp(
                        defensive_stats, DamageType.PHYSICAL, threat
                    )
                    fire_result = self.ehp_calculator.calculate_ehp(
                        defensive_stats, DamageType.FIRE, threat
                    )
                    cold_result = self.ehp_calculator.calculate_ehp(
                        defensive_stats, DamageType.COLD, threat
                    )
                    lightning_result = self.ehp_calculator.calculate_ehp(
                        defensive_stats, DamageType.LIGHTNING, threat
                    )

                    # Use average EHP from results
                    avg_ehp = (
                        phys_result.effective_hp
                        + fire_result.effective_hp
                        + cold_result.effective_hp
                        + lightning_result.effective_hp
                    ) / 4
                    analysis["ehp"] = int(avg_ehp)
                    logger.info(f"[ANALYZE_CHAR] Calculated EHP: {analysis['ehp']}")

                    # Simple defense rating based on life+ES pool
                    total_pool = life + energy_shield
                    if total_pool > 0:
                        analysis["defense_rating"] = min(1.0, total_pool / 8000)
                        logger.info(f"[ANALYZE_CHAR] Defense rating: {analysis['defense_rating']}")

                except Exception as e:
                    logger.error(f"[ANALYZE_CHAR] EHP calculation failed: {e}", exc_info=True)
                    # Set a fallback EHP based on raw pool
                    stats = character_data.get("stats", {})
                    total_pool = (stats.get("life", 0) or 0) + (stats.get("energyShield", 0) or 0)
                    analysis["ehp"] = total_pool
                    logger.info(f"[ANALYZE_CHAR] Using fallback EHP: {total_pool}")
            else:
                logger.warning("[ANALYZE_CHAR] ehp_calculator not available!")

            # Identify strengths/weaknesses based on actual stats (from nested stats object)
            stats = character_data.get("stats", {})
            life = stats.get("life", 0) or 0
            es = stats.get("energyShield", 0) or 0
            total_pool = life + es

            if total_pool > 6000:
                analysis["strengths"].append(
                    f"Good defensive pool ({total_pool:,.0f} combined life+ES)"
                )
            elif total_pool < 4000:
                analysis["weaknesses"].append(
                    f"Low defensive pool ({total_pool:,.0f} combined life+ES)"
                )

            # Check resistances (poe.ninja format uses camelCase)
            fire_res = stats.get("fireResistance", 0) or 0
            cold_res = stats.get("coldResistance", 0) or 0
            lightning_res = stats.get("lightningResistance", 0) or 0
            chaos_res = stats.get("chaosResistance", 0) or 0

            # Store resistances in analysis for display
            analysis["resistances"] = {
                "fire": fire_res,
                "cold": cold_res,
                "lightning": lightning_res,
                "chaos": chaos_res,
            }

            if fire_res >= 75 and cold_res >= 75 and lightning_res >= 75:
                analysis["strengths"].append("All elemental resistances capped")
            else:
                uncapped = []
                if fire_res < 75:
                    uncapped.append(f"Fire: {fire_res}")
                if cold_res < 75:
                    uncapped.append(f"Cold: {cold_res}")
                if lightning_res < 75:
                    uncapped.append(f"Lightning: {lightning_res}")
                analysis["weaknesses"].append(f"Uncapped resistances ({', '.join(uncapped)})")

            # Warn about dangerously low chaos resistance
            if chaos_res < 0:
                analysis["weaknesses"].append(f"Negative chaos resistance ({chaos_res}%)")
            elif chaos_res < 30:
                analysis["weaknesses"].append(f"Low chaos resistance ({chaos_res}%)")

            # Simple tier calculation
            score = 0.0
            if total_pool > 6000:
                score += 0.3
            if fire_res >= 75 and cold_res >= 75 and lightning_res >= 75:
                score += 0.3
            if character_data.get("dps", 0) > 100000:
                score += 0.4

            analysis["overall_score"] = score

            if score >= 0.8:
                analysis["tier"] = "S"
            elif score >= 0.6:
                analysis["tier"] = "A"
            elif score >= 0.4:
                analysis["tier"] = "B"
            elif score >= 0.2:
                analysis["tier"] = "C"
            else:
                analysis["tier"] = "D"

            # Generate recommendations if requested
            recommendations = ""
            if include_recommendations and self.recommendation_engine:
                recommendations = await self.recommendation_engine.generate_recommendations(
                    character_data, analysis
                )

            # Resolve passive tree node IDs to full data
            passive_analysis = None
            if self.passive_tree_resolver:
                try:
                    passive_ids = character_data.get("passive_tree", [])
                    if passive_ids:
                        passive_analysis = self.passive_tree_resolver.analyze_build(passive_ids)
                        logger.info(
                            f"[ANALYZE_CHAR] Resolved {passive_analysis.total_nodes} passive nodes"
                        )
                except Exception as e:
                    logger.warning(f"[ANALYZE_CHAR] Passive tree resolution failed: {e}")

            # Format response
            response = self._format_character_analysis(
                character_data, analysis, recommendations, passive_analysis
            )

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Character analysis failed: {e}")
            return [types.TextContent(type="text", text=f"Analysis failed: {str(e)}")]

    async def _handle_nl_query(self, args: dict) -> List[types.TextContent]:
        """Handle natural language query"""
        query = args["query"]
        character_context = args.get("character_context")

        if not self.query_handler:
            return [
                types.TextContent(
                    type="text",
                    text="AI insights are not enabled. Please set ENABLE_AI_INSIGHTS=true and provide an API key.",
                )
            ]

        try:
            response = await self.query_handler.handle_query(query, character_context)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"NL query failed: {e}")
            return [types.TextContent(type="text", text=f"Query failed: {str(e)}")]

    async def _handle_optimize_gear(self, args: dict) -> List[types.TextContent]:
        """Handle gear optimization"""
        character_data = args["character_data"]
        budget = args.get("budget", "medium")
        goal = args.get("goal", "balanced")

        try:
            recommendations = await self.gear_optimizer.optimize(
                character_data, budget=budget, goal=goal
            )

            response = self._format_gear_recommendations(recommendations)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Gear optimization failed: {str(e)}")]

    async def _handle_optimize_passives(self, args: dict) -> List[types.TextContent]:
        """Handle passive tree optimization"""
        character_data = args["character_data"]
        available_points = args.get("available_points", 0)
        allow_respec = args.get("allow_respec", False)
        goal = args.get("goal", "balanced")

        try:
            recommendations = await self.passive_optimizer.optimize(
                character_data,
                available_points=available_points,
                allow_respec=allow_respec,
                goal=goal,
            )

            response = self._format_passive_recommendations(recommendations)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Passive optimization failed: {str(e)}")]

    async def _handle_optimize_skills(self, args: dict) -> List[types.TextContent]:
        """Handle skill optimization"""
        character_data = args["character_data"]
        goal = args.get("goal", "balanced")

        try:
            recommendations = await self.skill_optimizer.optimize(character_data, goal=goal)

            response = self._format_skill_recommendations(recommendations)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Skill optimization failed: {str(e)}")]

    async def _handle_compare_builds(self, args: dict) -> List[types.TextContent]:
        """Handle build comparison"""
        builds = args["builds"]
        metrics = args.get("comparison_metrics", ["overall_score", "dps", "defense"])

        try:
            comparison = await self.build_scorer.compare_builds(builds, metrics)
            response = self._format_build_comparison(comparison)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Build comparison failed: {str(e)}")]

    async def _handle_import_pob(self, args: dict) -> List[types.TextContent]:
        """Handle PoB import — from a local file, raw XML, or an inline share code"""
        pob_file_path = args.get("pob_file_path")
        pob_xml = args.get("pob_xml")
        pob_code = args.get("pob_code")

        if not self.pob_importer:
            return [types.TextContent(type="text", text="Path of Building import is not enabled.")]

        if not (pob_file_path or pob_xml or pob_code):
            return [
                types.TextContent(
                    type="text",
                    text=(
                        "No build input provided. Pass one of:\n"
                        "- `pob_file_path` — path to a local file with the build "
                        "(raw XML or share code; most reliable)\n"
                        "- `pob_xml` — raw uncompressed PoB XML\n"
                        "- `pob_code` — inline base64 share code"
                    ),
                )
            ]

        try:
            if pob_file_path:
                path = Path(pob_file_path).expanduser()
                if not path.is_file():
                    return [
                        types.TextContent(
                            type="text", text=f"PoB import failed: file not found: {path}"
                        )
                    ]
                build_data = await self.pob_importer.import_from_file(str(path))
                source = f"file `{path}`"
            elif pob_xml:
                build_data = await self.pob_importer.import_xml(pob_xml)
                source = "raw XML"
            else:
                build_data = await self.pob_importer.import_build(pob_code)
                source = "share code"

            return [
                types.TextContent(
                    type="text",
                    text=f"Successfully imported build from {source}:\n{json.dumps(build_data, indent=2)}",
                )
            ]

        except Exception as e:
            return [types.TextContent(type="text", text=f"PoB import failed: {str(e)}")]

    async def _handle_export_pob(self, args: dict) -> List[types.TextContent]:
        """Handle PoB export"""
        character_data = args["character_data"]

        if not self.pob_exporter:
            return [types.TextContent(type="text", text="Path of Building export is not enabled.")]

        try:
            pob_code = await self.pob_exporter.export_build(character_data)
            return [
                types.TextContent(
                    type="text",
                    text=f"Path of Building Code:\n{pob_code}\n\nCopy this code and import it in Path of Building.",
                )
            ]

        except Exception as e:
            return [types.TextContent(type="text", text=f"PoB export failed: {str(e)}")]

    async def _handle_get_pob_code(self, args: dict) -> List[types.TextContent]:
        """Get PoB code from poe.ninja"""
        account = args["account"]
        character = args["character"]

        try:
            # Fetch PoB code from poe.ninja hidden API
            pob_code = await self.char_fetcher.ninja_api.get_pob_import(account, character)

            if pob_code:
                # If it's a dict (full API response), try to extract the code
                if isinstance(pob_code, dict):
                    actual_code = (
                        pob_code.get("pob") or pob_code.get("code") or pob_code.get("build")
                    )
                    if actual_code:
                        pob_code = actual_code
                    else:
                        # Return the structure so user can see what was returned
                        return [
                            types.TextContent(
                                type="text",
                                text=f"PoB API returned unexpected format:\n{json.dumps(pob_code, indent=2)}",
                            )
                        ]

                return [
                    types.TextContent(
                        type="text",
                        text=f"Path of Building Code for {character}:\n\n{pob_code}\n\nCopy this code and import it in Path of Building.",
                    )
                ]
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Could not fetch PoB code for {character}. Character may not exist on poe.ninja or the PoB API may not have data for this character.",
                    )
                ]

        except Exception as e:
            logger.error(f"Error fetching PoB code: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Failed to fetch PoB code: {str(e)}")]

    # =========================================================================
    # Live Path of Building Bridge handlers (TCP to a running PoB instance)
    # =========================================================================

    def _get_pob_client(self, port: int = 49085):
        """
        Lazily build/cache the live PoB bridge client, discovering the bound
        port. The addon falls back from 49085 to 49086-49088 when 49085 is busy,
        so a hardwired port can miss a running bridge.
        """
        try:
            from .pob.client import PoBClient
        except ImportError:
            from src.pob.client import PoBClient
        # Reuse the cached client only while it's still reachable.
        if self.pob_client is not None and self.pob_client.is_connected():
            return self.pob_client
        # Scan the fallback range; fall back to a default-port object so callers
        # still get a clean "not reachable" error when PoB isn't running.
        self.pob_client = PoBClient.find_bridge() or PoBClient(port=port)
        return self.pob_client

    async def _handle_pob_status(self, args: dict) -> List[types.TextContent]:
        """Report PoB install / addon / live-bridge reachability."""
        try:
            port = int(args.get("port", 49085))
            try:
                from .pob import installer
            except ImportError:
                from src.pob import installer
            status = await asyncio.to_thread(installer.get_bridge_status, "127.0.0.1", port)

            lines = ["Path of Building bridge status:"]
            lines.append(
                f"  PoB installed: {status['pob_installed']}"
                + (f" ({status['pob_path']})" if status.get("pob_path") else "")
            )
            lines.append(f"  Addon deployed: {status['addon_installed']}")
            lines.append(f"  Launch.lua patched: {status['launch_patched']}")
            _bport = status.get("bridge_port") or port
            lines.append(f"  Bridge reachable (port {_bport}): {status['bridge_reachable']}")
            if status.get("ping"):
                ping = status["ping"]
                lines.append(
                    f"  PoB version: {ping.get('pob_version')}, "
                    f"build loaded: {ping.get('build_loaded')}"
                    + (f" ('{ping.get('build_name')}')" if ping.get("build_name") else "")
                )
            if not status["bridge_reachable"]:
                if status["addon_installed"]:
                    lines.append(
                        "  -> Addon installed but PoB isn't running (or not reachable). Start PoB."
                    )
                elif status["pob_installed"] and not status["launch_patched"]:
                    # Distinguish "never installed" from "PoB updated and wiped the
                    # Launch.lua hook". In the latter the addon files still exist;
                    # auto-repair so the addon survives PoB updates.
                    deploy = await asyncio.to_thread(
                        installer.is_addon_installed, Path(status["pob_path"])
                    )
                    if deploy.get("files_present"):
                        repair = await asyncio.to_thread(
                            installer.ensure_installed, Path(status["pob_path"])
                        )
                        if repair.get("action") == "repatched":
                            lines.append(
                                "  -> PoB updated and removed the addon hook; "
                                "I re-applied it automatically. Restart PoB."
                            )
                        else:
                            lines.append(f"  -> Auto-repair: {repair.get('message')}")
                    else:
                        lines.append(
                            "  -> Addon not installed. Use pob_install_addon, then restart PoB."
                        )
                else:
                    lines.append(
                        "  -> Addon not installed. Use pob_install_addon, then restart PoB."
                    )
            return [types.TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            logger.error(f"pob_status error: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_pob_install_addon(self, args: dict) -> List[types.TextContent]:
        """Install the bridge addon into the local PoB."""
        try:
            try:
                from .pob import installer
            except ImportError:
                from src.pob import installer
            pob_path = args.get("pob_path")
            result = await asyncio.to_thread(
                installer.install_addon,
                Path(pob_path) if pob_path else None,
            )
            prefix = "Installed" if result.get("success") else "Install failed"
            text = f"{prefix}: {result.get('message')}"
            if result.get("pob_path"):
                text += f"\n  PoB: {result['pob_path']}"
            if result.get("launch_patch"):
                text += f"\n  Launch.lua: {result['launch_patch']}"
            return [types.TextContent(type="text", text=text)]
        except Exception as e:
            logger.error(f"pob_install_addon error: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_pob_get_passive_tree(self, args: dict) -> List[types.TextContent]:
        """Pull allocated passive tree from a running PoB."""
        try:
            client = self._get_pob_client()
            tree = await asyncio.to_thread(client.get_passive_tree)
            nodes = tree.get("nodes", [])
            header = (
                f"Passive tree from PoB - class {tree.get('class')}, "
                f"ascendancy {tree.get('ascendancy')}, "
                f"{tree.get('totalPoints')} points, {len(nodes)} allocated nodes:"
            )
            return [types.TextContent(type="text", text=header + "\n" + json.dumps(tree, indent=2))]
        except Exception as e:
            logger.error(f"pob_get_passive_tree error: {e}", exc_info=True)
            return [
                types.TextContent(
                    type="text",
                    text=f"Error pulling passive tree (is PoB running with a build loaded? "
                    f"Try pob_status): {str(e)}",
                )
            ]

    async def _handle_pob_get_build(self, args: dict) -> List[types.TextContent]:
        """Pull the current build from a running PoB as code or xml."""
        try:
            fmt = args.get("format", "code")
            client = self._get_pob_client()
            result = await asyncio.to_thread(client.get_build, fmt)
            if fmt == "code":
                return [
                    types.TextContent(
                        type="text",
                        text=f"PoB share code for '{result.get('name', 'build')}':\n\n{result.get('code', '')}",
                    )
                ]
            return [
                types.TextContent(
                    type="text",
                    text=f"PoB build XML for '{result.get('name', 'build')}':\n\n{result.get('xml', '')}",
                )
            ]
        except Exception as e:
            logger.error(f"pob_get_build error: {e}", exc_info=True)
            return [
                types.TextContent(
                    type="text",
                    text=f"Error pulling build (is PoB running? Try pob_status): {str(e)}",
                )
            ]

    async def _handle_pob_load_build(self, args: dict) -> List[types.TextContent]:
        """Load a build (code or xml) into a running PoB."""
        try:
            code = args.get("code")
            xml = args.get("xml")
            name = args.get("name", "MCP Build")
            if not code and not xml:
                return [
                    types.TextContent(
                        type="text", text="Provide a PoB 'code' (share code) or 'xml' to load."
                    )
                ]
            client = self._get_pob_client()
            result = await asyncio.to_thread(client.load_build, xml, code, name)
            return [
                types.TextContent(
                    type="text",
                    text=f"Loaded build '{name}' into Path of Building. {result.get('note', '')}".strip(),
                )
            ]
        except Exception as e:
            logger.error(f"pob_load_build error: {e}", exc_info=True)
            return [
                types.TextContent(
                    type="text",
                    text=f"Error loading build (is PoB running? Try pob_status): {str(e)}",
                )
            ]

    async def _handle_pob_get_calcs(self, args: dict) -> List[types.TextContent]:
        """Pull computed stats from PoB's calc engine."""
        try:
            client = self._get_pob_client()
            calcs = await asyncio.to_thread(client.get_calcs)
            return [
                types.TextContent(
                    type="text", text="PoB calculation output:\n" + json.dumps(calcs, indent=2)
                )
            ]
        except Exception as e:
            logger.error(f"pob_get_calcs error: {e}", exc_info=True)
            return [
                types.TextContent(
                    type="text",
                    text=f"Error pulling calcs (is PoB running with a build loaded? "
                    f"Try pob_status): {str(e)}",
                )
            ]

    async def _handle_search_items(self, args: dict) -> List[types.TextContent]:
        """Handle item search using .datc64 game database"""
        query = args["query"]
        filters = args.get("filters", {})

        try:
            items = await self.db_manager.search_items(query, filters)

            if not items:
                return [types.TextContent(type="text", text=f"No items found matching '{query}'")]

            response = f"Found {len(items)} items matching '{query}':\n\n"

            for item in items[:10]:  # Limit to 10 results
                name = item.get("name", "Unknown")
                item_class = item.get("item_class", "Unknown")
                base_type = item.get("base_type", "")
                width = item.get("width", 1)
                height = item.get("height", 1)
                drop_level = item.get("drop_level", 0)

                response += f"- {name}\n"
                response += f"  Class: {item_class}\n"
                if base_type:
                    response += f"  Base: {base_type}\n"
                response += f"  Size: {width}x{height}"
                if drop_level > 0:
                    response += f" | Drop Level: {drop_level}"
                response += "\n\n"

            if len(items) > 10:
                response += f"... and {len(items) - 10} more results\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"search_items error: {e}")
            return [types.TextContent(type="text", text=f"Item search failed: {str(e)}")]

    async def _handle_calculate_dps(self, args: dict) -> List[types.TextContent]:
        """Handle DPS calculation"""
        character_data = args["character_data"]
        include_buffs = args.get("include_buffs", True)

        try:
            from calculator.damage_calc import DamageCalculator

            calc = DamageCalculator(self.db_manager)

            dps_breakdown = await calc.calculate_dps(character_data, include_buffs=include_buffs)

            response = self._format_dps_breakdown(dps_breakdown)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(type="text", text=f"DPS calculation failed: {str(e)}")]

    async def _handle_compare_to_top_players(self, args: dict) -> List[types.TextContent]:
        """Handle comparison to top players"""
        account_name = args["account_name"]
        character_name = args["character_name"]
        league = args.get("league", "Standard")
        min_level = args.get("min_level")
        top_player_limit = args.get("top_player_limit", 10)

        try:
            # Fetch user's character
            logger.info(f"Fetching character {character_name} for comparison...")
            user_character = await self.char_fetcher.get_character(
                account_name, character_name, league
            )

            if not user_character:
                # Same SPA-migration-aware template as _handle_analyze_character.
                # Most failures here are NOT user-config issues — they're poe.ninja's
                # post-0.5 SPA migration (#61). Surface that up front.
                league_slug = league.lower().replace(" ", "")
                profile_url = f"https://poe.ninja/poe2/builds/{league_slug}/character/{account_name}/{character_name}"
                error_msg = f"""# Character Fetch Failed

**Character:** {character_name}
**Account:** {account_name}
**League:** {league}

## :warning: Likely cause: poe.ninja SPA migration (Patch 0.5)

poe.ninja migrated their builds/character pages to a client-side rendered SPA at/around Patch 0.5 (2026-05-29). Endpoints this tool uses either return 404 (for characters not in the snapshot) or an SPA shell with no embedded data. **If the page below loads in your browser, the problem is on poe.ninja's side**, not your account or character settings. Tracked at https://github.com/HivemindOverlord/poe2-mcp/issues/61.

## Verify it's the SPA migration vs your config

1. Open: <{profile_url}>
2. Loads with character data → SPA migration (#61); no MCP-side fix until poe.ninja's new endpoint shape is reverse-engineered
3. Shows "Character not found" → your character isn't on poe.ninja's ladder yet; continue with the next-steps checklist

## Next-steps checklist (only if your browser ALSO can't see the character)

- **Profile must be public** — check https://www.pathofexile.com/account/view-profile/{account_name}/characters
- **Account name format** — try without discriminator (`{account_name.split('-')[0] if '-' in account_name else account_name.split('#')[0] if '#' in account_name else account_name}`) and with (`{account_name}`)
- **League name** — make sure it matches the league your character is on (current: **{league}**)
- **poe.ninja indexing delay** — new characters take 1-2 hours; very low-level characters may never index
"""
                return [types.TextContent(type="text", text=error_msg)]

            # Perform comparison via the recovered protobuf ladder API (#61).
            # The old snapshot-based top_player_fetcher path died in the 0.5
            # Astro migration; LadderClient speaks the new columnar protobuf
            # search endpoint directly.
            try:
                from .api.poe_ninja_ladder import LadderClient
            except ImportError:
                from src.api.poe_ninja_ladder import LadderClient

            logger.info("Comparing to top players via ladder search (#61 revival)...")
            league_slug = self.char_fetcher._to_poe_ninja_league_slug(league)
            # Ladder 'class' filter takes the ascendancy name when ascended
            ladder_class = user_character.get("ascendancy") or user_character.get("class")

            ladder = LadderClient(rate_limiter=self.char_fetcher.rate_limiter)
            try:
                rows = await ladder.top_builds(league_slug, class_name=ladder_class, sort="level")
                if not rows:
                    # Class filter may not match (e.g. unascended) — fall back to global page
                    rows = await ladder.top_builds(league_slug, sort="level")
            finally:
                await ladder.close()

            if not rows:
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            f"# Comparison Unavailable\n\nThe ladder search returned no rows "
                            f"for league '{league}' (slug '{league_slug}'). The league may "
                            f"not be indexed, or poe.ninja changed the endpoint again — "
                            f"check https://github.com/HivemindOverlord/poe2-mcp/issues/61."
                        ),
                    )
                ]

            if min_level:
                rows = [
                    r
                    for r in rows
                    if isinstance(r.get("level"), int) and r["level"] >= int(min_level)
                ]
            top = rows[: int(top_player_limit) if top_player_limit else 10]

            def _median(key):
                vals = sorted(r[key] for r in rows if isinstance(r.get(key), (int, float)))
                return vals[len(vals) // 2] if vals else None

            stats = user_character.get("stats") or {}
            mine = {
                "level": user_character.get("level"),
                "life": stats.get("life"),
                "energyshield": stats.get("energyShield"),
            }
            med = {k: _median(k) for k in ("level", "life", "energyshield")}

            response = f"# Top-Player Comparison: {character_name}\n\n"
            response += f"**Cohort**: top {len(rows)} `{ladder_class}` builds in {league} "
            response += f"(of the full ladder page, sorted by level)\n\n"
            response += "## You vs the cohort median\n"
            response += f"| Stat | You | Median | Delta |\n|---|---|---|---|\n"
            for key, label in (
                ("level", "Level"),
                ("life", "Life"),
                ("energyshield", "Energy Shield"),
            ):
                m, c = mine.get(key), med.get(key)
                delta = (
                    (m - c) if isinstance(m, (int, float)) and isinstance(c, (int, float)) else None
                )
                delta_s = f"{delta:+}" if delta is not None else "—"
                response += f"| {label} | {m if m is not None else '—'} | {c if c is not None else '—'} | {delta_s} |\n"

            response += f"\n## Top {len(top)} {ladder_class} builds\n"
            for i, r in enumerate(top, 1):
                response += (
                    f"{i}. **{r.get('name', '?')}** (lvl {r.get('level', '?')}) — "
                    f"life {r.get('life', '—')}, ES {r.get('energyshield', '—')}, "
                    f"EHP {r.get('ehp', '—')}, DPS {r.get('dps', '—')}\n"
                )
            response += (
                "\n*Use `analyze_character` on any name above for the full build. "
                "Data: poe.ninja builds search (protobuf API recovered in #61).*"
            )

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Comparison failed: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Comparison failed: {str(e)}")]

    async def _handle_search_trade_items(self, args: dict) -> List[types.TextContent]:
        """Handle trade item search"""
        league = args.get("league", "Standard")
        character_needs = args.get("character_needs", {})
        max_price_chaos = args.get("max_price_chaos")

        if not self.trade_api:
            return [
                types.TextContent(
                    type="text",
                    text="Trade integration is not enabled. Please set ENABLE_TRADE_INTEGRATION=true in your config.",
                )
            ]

        if not settings.POESESSID:
            return [
                types.TextContent(
                    type="text",
                    text="Trade search requires POESESSID cookie. Please set it up:\n\n"
                    "**AUTOMATED SETUP (Recommended - 2 minutes):**\n\n"
                    "Use the `setup_trade_auth` tool to automatically configure authentication.\n"
                    "Just run it and log in when the browser opens - the tool will handle the rest!\n\n"
                    'Example: "Set up trade authentication" or "Use the setup_trade_auth tool"\n\n'
                    "**Requirements:**\n"
                    "- Playwright must be installed: `pip install playwright`\n"
                    "- Chromium must be downloaded: `playwright install chromium`\n\n"
                    "**Manual Setup (Fallback):**\n"
                    "1. Visit https://www.pathofexile.com/trade in your browser\n"
                    "2. Log in to your account\n"
                    "3. Open DevTools (F12) → Application → Cookies\n"
                    "4. Find 'POESESSID' cookie and copy its value\n"
                    "5. Add to .env: POESESSID=your_cookie_value\n"
                    "6. Restart MCP server",
                )
            ]

        try:
            logger.info(f"Searching trade market for upgrades in {league}...")

            # Perform search
            results = await self.trade_api.search_for_upgrades(
                league=league, character_needs=character_needs, max_price_chaos=max_price_chaos
            )

            if not results:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No items found matching your criteria in {league}. Try:\n"
                        "- Increasing your budget\n"
                        "- Broadening search criteria\n"
                        "- Checking if the league name is correct",
                    )
                ]

            # Format response
            response = self._format_trade_search_results(results, character_needs, max_price_chaos)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Trade search failed: {e}", exc_info=True)
            return [
                types.TextContent(
                    type="text",
                    text=f"Trade search failed: {str(e)}\n\n"
                    "If you see authentication errors, your POESESSID cookie may have expired.\n\n"
                    "**To refresh:** Use the `setup_trade_auth` tool to get a new cookie.\n"
                    "Or manually update POESESSID in your .env file and restart the server.",
                )
            ]

    async def _handle_detect_weaknesses(self, args: dict) -> List[types.TextContent]:
        """Handle character weakness detection"""
        try:
            if not self.weakness_detector:
                return [types.TextContent(type="text", text="Weakness detector not initialized")]

            # Support two modes: fetch from API or use provided data
            if "account" in args and "character" in args:
                # Mode 1: Fetch character from API
                account = args["account"]
                character = args["character"]

                character_data = await self.char_fetcher.get_character(
                    account_name=account,
                    character_name=character,
                    league=args.get("league", "Abyss"),
                )

                # DEBUG: Log immediately after fetch
                if character_data:
                    logger.info(
                        f"[WEAKNESS] Got character_data with keys: {list(character_data.keys())}"
                    )
                    logger.info(
                        f"[WEAKNESS] life: {character_data.get('life')}, ES: {character_data.get('energy_shield')}"
                    )
                else:
                    logger.warning(f"[WEAKNESS] character_data is None/empty!")

                if not character_data:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Could not fetch character '{character}' for account '{account}'. Check if profile is public.",
                        )
                    ]
            else:
                # Mode 2: Use provided character_data (for testing)
                character_data = args.get("character_data", {})
                if not character_data:
                    return [
                        types.TextContent(
                            type="text",
                            text="Either provide 'account' and 'character' to fetch from API, or provide 'character_data' for testing.",
                        )
                    ]

            # Convert character data to CharacterData format
            try:
                from .analyzer.weakness_detector import CharacterData
            except ImportError:
                from src.analyzer.weakness_detector import CharacterData

            # DEBUG: Log what we're getting
            logger.info(f"[WEAKNESS_DETECTOR] character_data keys: {list(character_data.keys())}")
            logger.info(
                f"[WEAKNESS_DETECTOR] life value: {character_data.get('life', 'KEY_MISSING')}"
            )
            logger.info(
                f"[WEAKNESS_DETECTOR] energy_shield value: {character_data.get('energy_shield', 'KEY_MISSING')}"
            )
            logger.info(
                f"[WEAKNESS_DETECTOR] fire_res value: {character_data.get('fire_res', 'KEY_MISSING')}"
            )
            logger.info(
                f"[WEAKNESS_DETECTOR] source value: {character_data.get('source', 'KEY_MISSING')}"
            )

            char = CharacterData(
                level=character_data.get("level", 1),
                character_class=character_data.get("class", "Unknown"),
                life=character_data.get("life", 0),
                energy_shield=character_data.get("energy_shield", 0),
                mana=character_data.get("mana", 0),
                spirit_max=character_data.get("spirit", 0),
                spirit_reserved=character_data.get("spirit_reserved", 0),
                strength=character_data.get("strength", 0),
                dexterity=character_data.get("dexterity", 0),
                intelligence=character_data.get("intelligence", 0),
                armor=character_data.get("armor", 0),
                evasion=character_data.get("evasion", 0),
                block_chance=character_data.get("block_chance", 0),
                fire_res=character_data.get("fire_res", 0),
                cold_res=character_data.get("cold_res", 0),
                lightning_res=character_data.get("lightning_res", 0),
                chaos_res=character_data.get("chaos_res", 0),
                total_dps=character_data.get("dps"),
                equipped_items={},
            )

            # Detect weaknesses
            weaknesses = self.weakness_detector.detect_all_weaknesses(char)

            # Format response
            if not weaknesses:
                response = "# Character Weakness Analysis\n\n✓ No critical weaknesses detected!"
            else:
                response = (
                    f"# Character Weakness Analysis\n\n🔍 Found {len(weaknesses)} weaknesses:\n\n"
                )

                for i, weakness in enumerate(weaknesses, 1):
                    priority_icon = (
                        "🔴"
                        if weakness.priority >= 90
                        else "🟡" if weakness.priority >= 70 else "🟢"
                    )
                    response += f"## {i}. {priority_icon} {weakness.title}\n\n"
                    response += f"**Category:** {weakness.category.value}\n"
                    response += f"**Priority:** {weakness.priority}/100\n"
                    response += f"**Current Value:** {weakness.current_value}\n"
                    response += f"**Recommended:** {weakness.recommended_value}\n\n"
                    response += f"**Impact:** {weakness.description}\n\n"
                    response += f"**How to Fix:**\n"
                    for rec in weakness.recommendations:
                        response += f"- {rec}\n"
                    response += "\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Weakness detection failed: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Weakness detection failed: {str(e)}")]

    async def _handle_evaluate_upgrade(self, args: dict) -> List[types.TextContent]:
        """Handle gear upgrade evaluation"""
        try:
            current_gear = args.get("current_gear", {})
            upgrade_gear = args.get("upgrade_gear", {})
            base_stats = args.get("base_character_stats", {})
            price_chaos = args.get("price_chaos")

            if not self.gear_evaluator:
                return [types.TextContent(type="text", text="Gear evaluator not initialized")]

            # Note: GearEvaluator would need proper implementation of evaluate_upgrade
            # For now, provide a placeholder response
            response = f"""# Gear Upgrade Evaluation

## Current Gear
{self._format_gear_stats(current_gear)}

## Proposed Upgrade
{self._format_gear_stats(upgrade_gear)}

## Analysis
This feature requires full implementation of stat comparison logic.
Consider:
- EHP changes (physical, fire, cold, lightning, chaos)
- DPS impact
- Resistance changes
- Special mod effects

**Price:** {price_chaos} chaos (if specified)
"""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Gear evaluation failed: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Gear evaluation failed: {str(e)}")]

    async def _handle_calculate_ehp(self, args: dict) -> List[types.TextContent]:
        """Handle EHP calculation"""
        try:
            if not self.ehp_calculator:
                return [types.TextContent(type="text", text="EHP calculator not initialized")]

            # Support two modes: fetch from API or use provided data
            if "account" in args and "character" in args:
                # Mode 1: Fetch character from API
                account = args["account"]
                character = args["character"]

                character_data = await self.char_fetcher.get_character(
                    account_name=account,
                    character_name=character,
                    league=args.get("league", "Abyss"),
                )

                if not character_data:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Could not fetch character '{character}' for account '{account}'. Check if profile is public.",
                        )
                    ]
            else:
                # Mode 2: Use provided character_data (for testing)
                character_data = args.get("character_data", {})
                if not character_data:
                    return [
                        types.TextContent(
                            type="text",
                            text="Either provide 'account' and 'character' to fetch from API, or provide 'character_data' for testing.",
                        )
                    ]

            # Convert to DefensiveStats format
            try:
                from .calculator.ehp_calculator import DefensiveStats, DamageType, ThreatProfile
            except ImportError:
                from src.calculator.ehp_calculator import DefensiveStats, DamageType, ThreatProfile

            stats = DefensiveStats(
                life=character_data.get("life", 0),
                energy_shield=character_data.get("energy_shield", 0),
                fire_res=character_data.get("fire_res", 0),
                cold_res=character_data.get("cold_res", 0),
                lightning_res=character_data.get("lightning_res", 0),
                chaos_res=character_data.get("chaos_res", 0),
                armor=character_data.get("armor", 0),
                evasion=character_data.get("evasion", 0),
                block_chance=character_data.get("block_chance", 0),
                phys_taken_as_elemental=character_data.get("phys_taken_as_elemental", 0),
            )

            # Calculate EHP for all damage types
            damage_types = [
                (DamageType.PHYSICAL, "Physical"),
                (DamageType.FIRE, "Fire"),
                (DamageType.COLD, "Cold"),
                (DamageType.LIGHTNING, "Lightning"),
                (DamageType.CHAOS, "Chaos"),
            ]

            # Create default threat profile
            threat = ThreatProfile(expected_hit_size=1000.0, attacker_accuracy=2000.0)

            response = "# Effective Health Pool Analysis\n\n"
            response += f"**Raw Pool:** {stats.life:,.0f} Life + {stats.energy_shield:,.0f} ES = {stats.life + stats.energy_shield:,.0f} total\n\n"
            response += "## EHP by Damage Type\n\n"

            raw_pool = stats.life + stats.energy_shield

            for damage_type, name in damage_types:
                ehp_result = self.ehp_calculator.calculate_ehp(stats, damage_type, threat)
                ehp = ehp_result.effective_hp
                multiplier = ehp / raw_pool if raw_pool > 0 else 0

                status = "🔴" if ehp < 5000 else "🟡" if ehp < 8000 else "🟢"
                response += f"{status} **{name}:** {ehp:,.0f} EHP ({multiplier:.2f}x raw pool)\n"

            response += "\n## Legend\n"
            response += "- 🟢 Good (8,000+ EHP)\n"
            response += "- 🟡 Moderate (5,000-8,000 EHP)\n"
            response += "- 🔴 Low (<5,000 EHP)\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"EHP calculation failed: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"EHP calculation failed: {str(e)}")]

    async def _handle_analyze_spirit(self, args: dict) -> List[types.TextContent]:
        """Handle Spirit usage analysis"""
        try:
            if not self.spirit_calculator:
                return [types.TextContent(type="text", text="Spirit calculator not initialized")]

            # Support two modes: fetch from API or use provided data
            if "account" in args and "character" in args:
                # Mode 1: Fetch character from API
                account = args["account"]
                character = args["character"]

                character_data = await self.char_fetcher.get_character(
                    account_name=account,
                    character_name=character,
                    league=args.get("league", "Abyss"),
                )

                if not character_data:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Could not fetch character '{character}' for account '{account}'. Check if profile is public.",
                        )
                    ]
            else:
                # Mode 2: Use provided character_data (for testing)
                character_data = args.get("character_data", {})
                if not character_data:
                    return [
                        types.TextContent(
                            type="text",
                            text="Either provide 'account' and 'character' to fetch from API, or provide 'character_data' for testing.",
                        )
                    ]

            spirit_max = character_data.get("spirit", 100)
            spirit_reserved = character_data.get("spirit_reserved", 0)
            spirit_free = spirit_max - spirit_reserved

            response = f"""# Spirit Usage Analysis

## Current Spirit Status
- **Maximum Spirit:** {spirit_max}
- **Reserved:** {spirit_reserved}
- **Free:** {spirit_free}
- **Usage:** {(spirit_reserved / spirit_max * 100):.1f}% allocated

## Recommendations

"""

            if spirit_free > 50:
                response += "✓ You have plenty of free Spirit available\n"
                response += "  → Consider adding more auras or persistent buffs\n"
                response += "  → Summon additional minions\n"
                response += "  → Enable utility reservations\n"
            elif spirit_free > 20:
                response += "⚠ Moderate Spirit remaining\n"
                response += "  → Room for one more small aura/buff\n"
                response += "  → Be careful not to overflow\n"
            elif spirit_free > 0:
                response += "⚠ Low Spirit remaining\n"
                response += "  → At capacity, avoid additional reservations\n"
            else:
                response += "🔴 Spirit overflow! You're over capacity\n"
                response += "  → Disable some auras/buffs immediately\n"
                response += "  → Unsummon some minions\n"
                response += "  → Consider passive nodes that increase Spirit\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Spirit analysis failed: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Spirit analysis failed: {str(e)}")]

    async def _handle_analyze_stun(self, args: dict) -> List[types.TextContent]:
        """Handle stun vulnerability analysis"""
        try:
            # Support two modes: fetch from API or use provided data
            if "account" in args and "character" in args:
                # Mode 1: Fetch character from API
                account = args["account"]
                character = args["character"]

                character_data = await self.char_fetcher.get_character(
                    account_name=account,
                    character_name=character,
                    league=args.get("league", "Abyss"),
                )

                if not character_data:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Could not fetch character '{character}' for account '{account}'. Check if profile is public.",
                        )
                    ]
            else:
                # Mode 2: Use provided character_data (for testing)
                character_data = args.get("character_data", {})
                if not character_data:
                    return [
                        types.TextContent(
                            type="text",
                            text="Either provide 'account' and 'character' to fetch from API, or provide 'character_data' for testing.",
                        )
                    ]

            # Calculate stun thresholds
            life = character_data.get("life", 0)
            es = character_data.get("energy_shield", 0)
            total_pool = life + es

            # PoE2 stun mechanics
            light_stun_threshold = total_pool * 0.15  # 15% of pool
            heavy_stun_meter = 100  # Fills to 100%
            primed_threshold = 50  # 50% meter = primed

            response = f"""# Stun Vulnerability Analysis

## Your Defense Pool
- Life: {life:,.0f}
- Energy Shield: {es:,.0f}
- **Total Pool:** {total_pool:,.0f}

## Stun Thresholds (PoE2)

### Light Stun (Chance-based)
- **Threshold:** {light_stun_threshold:,.0f} damage (15% of pool)
- Causes brief interrupt and 15% action speed reduction

### Heavy Stun (Buildup)
- **Meter fills to:** {heavy_stun_meter}%
- At {primed_threshold}%-99%: **PRIMED** state (vulnerable to Crushing Blow)
- At 100%: **STUNNED** for 3 seconds

### Crushing Blow
- Occurs when: Primed + Light Stun would trigger
- Effect: Instant stun regardless of threshold

## Assessment
"""

            if total_pool < 3000:
                response += "🔴 **Very Vulnerable** - Low health pool makes you easy to stun\n"
                response += "  → Increase Life and/or Energy Shield\n"
                response += "  → Consider stun avoidance/recovery gear\n"
            elif total_pool < 6000:
                response += "🟡 **Moderate Risk** - Average stun resistance\n"
                response += "  → Watch for hard-hitting enemies\n"
                response += "  → Stun recovery speed helps\n"
            else:
                response += (
                    "🟢 **Good Resistance** - Large health pool provides natural stun defense\n"
                )
                response += "  → Harder to fill Heavy Stun meter\n"
                response += "  → Light Stun threshold is high\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Stun analysis failed: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Stun analysis failed: {str(e)}")]

    async def _handle_optimize_metrics(self, args: dict) -> List[types.TextContent]:
        """Handle comprehensive build metrics optimization"""
        try:
            focus = args.get("focus", "balanced")  # "offense", "defense", "balanced"

            # Support two modes: fetch from API or use provided data
            if "account" in args and "character" in args:
                # Mode 1: Fetch character from API
                account = args["account"]
                character = args["character"]

                character_data = await self.char_fetcher.get_character(
                    account_name=account,
                    character_name=character,
                    league=args.get("league", "Abyss"),
                )

                if not character_data:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Could not fetch character '{character}' for account '{account}'. Check if profile is public.",
                        )
                    ]
            else:
                # Mode 2: Use provided character_data (for testing)
                character_data = args.get("character_data", {})
                if not character_data:
                    return [
                        types.TextContent(
                            type="text",
                            text="Either provide 'account' and 'character' to fetch from API, or provide 'character_data' for testing.",
                        )
                    ]

            # Run all analysis systems
            response = "# Comprehensive Build Optimization\n\n"
            response += f"**Focus:** {focus.title()}\n\n"

            # 1. Weakness Detection
            if self.weakness_detector:
                response += "## ⚠️ Critical Weaknesses\n\n"
                weakness_result = await self._handle_detect_weaknesses(
                    {"character_data": character_data}
                )
                if weakness_result and weakness_result[0].text:
                    # Extract just the weaknesses section
                    weakness_text = weakness_result[0].text
                    if "# Character Weaknesses" in weakness_text:
                        weakness_text = weakness_text.split("# Character Weaknesses", 1)[1]
                    response += weakness_text + "\n\n"

            # 2. EHP Analysis
            if self.ehp_calculator:
                response += "## 🛡️ Defensive Analysis\n\n"
                ehp_result = await self._handle_calculate_ehp({"character_data": character_data})
                if ehp_result and ehp_result[0].text:
                    ehp_text = ehp_result[0].text
                    if "# Effective Health Pool Analysis" in ehp_text:
                        ehp_text = ehp_text.split("# Effective Health Pool Analysis", 1)[1]
                    response += ehp_text + "\n\n"

            # 3. Spirit Optimization
            if self.spirit_calculator and "spirit" in character_data:
                response += "## ✨ Spirit Optimization\n\n"
                spirit_result = await self._handle_analyze_spirit(
                    {"character_data": character_data}
                )
                if spirit_result and spirit_result[0].text:
                    spirit_text = spirit_result[0].text
                    if "# Spirit Usage Analysis" in spirit_text:
                        spirit_text = spirit_text.split("# Spirit Usage Analysis", 1)[1]
                    response += spirit_text + "\n\n"

            # 4. Stun Vulnerability
            if "life" in character_data and "energy_shield" in character_data:
                response += "## 💫 Stun Vulnerability\n\n"
                stun_result = await self._handle_analyze_stun({"character_data": character_data})
                if stun_result and stun_result[0].text:
                    stun_text = stun_result[0].text
                    if "# Stun Vulnerability Analysis" in stun_text:
                        stun_text = stun_text.split("# Stun Vulnerability Analysis", 1)[1]
                    response += stun_text + "\n\n"

            # 5. Focus-Specific Recommendations
            response += f"## 🎯 {focus.title()} Recommendations\n\n"

            if focus == "offense":
                response += "**Priority:** Maximize damage output\n\n"
                response += "1. **Weapon Upgrade** - Highest priority for DPS\n"
                response += "2. **Increase Critical Strike** - Both chance and multiplier\n"
                response += "3. **Add Penetration** - Elemental or physical based on build\n"
                response += "4. **Damage Auras** - Use free Spirit for Hatred/Wrath/Anger\n"
                response += "5. **More Multipliers** - Support gems and passive nodes\n"
            elif focus == "defense":
                response += "**Priority:** Maximize survivability\n\n"
                response += "1. **Cap Resistances** - CRITICAL: Get to 75% fire/cold/lightning\n"
                response += "2. **Increase Life/ES Pool** - Aim for 6,000+ combined\n"
                response += "3. **Add Defense Layers** - Armor, Evasion, or Block\n"
                response += "4. **Defensive Auras** - Grace, Determination, or Discipline\n"
                response += "5. **Stun Immunity** - Unwavering Stance or high stun threshold\n"
            else:  # balanced
                response += "**Priority:** Balance offense and defense\n\n"
                response += "1. **Fix Critical Weaknesses** - Negative resistances first!\n"
                response += "2. **Baseline Defense** - 5k+ EHP, capped res\n"
                response += "3. **Damage Scaling** - Focus on biggest multipliers\n"
                response += "4. **Spirit Efficiency** - Balanced aura setup\n"
                response += "5. **Incremental Upgrades** - Prioritize cost-effective improvements\n"

            response += "\n---\n\n"
            response += "*This is a comprehensive analysis combining all calculator systems.*\n"
            response += "*For detailed breakdowns, use the individual analysis tools.*\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Optimization analysis failed: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Optimization analysis failed: {str(e)}")]

    async def _handle_health_check(self, args: dict) -> List[types.TextContent]:
        """Handle MCP server health check"""
        try:
            verbose = args.get("verbose", False)
            issues = []
            warnings = []
            successes = []

            response = "# MCP Server Health Check\n\n"

            # Check 1: Calculator Initialization
            response += "## Calculator Systems\n\n"
            calculators = {
                "Weakness Detector": self.weakness_detector,
                "Gear Evaluator": self.gear_evaluator,
                "EHP Calculator": self.ehp_calculator,
                "Spirit Calculator": self.spirit_calculator,
                "Damage Calculator": self.damage_calculator,
            }

            for name, calc in calculators.items():
                if calc is not None:
                    response += f"✓ {name}: Initialized\n"
                    successes.append(f"{name} operational")
                else:
                    response += f"✗ {name}: NOT initialized\n"
                    issues.append(f"{name} not initialized")

            # Check 2: Database Status
            response += "\n## Database Status\n\n"
            if self.db_manager:
                try:
                    # Try to query the database
                    async with self.db_manager.async_session() as session:
                        # Check if we can connect
                        from sqlalchemy import text

                        result = await session.execute(
                            text("SELECT name FROM sqlite_master WHERE type='table'")
                        )
                        tables = result.fetchall()
                        response += f"✓ Database connected ({len(tables)} tables found)\n"
                        successes.append("Database connected")

                        # Check for items table
                        if any("items" in str(table) for table in tables):
                            result = await session.execute(text("SELECT COUNT(*) FROM items"))
                            count = result.scalar()
                            if count and count > 0:
                                response += f"✓ Items table populated: {count:,} items\n"
                                successes.append(f"Database has {count} items")
                            else:
                                response += "⚠ Items table exists but is EMPTY\n"
                                warnings.append("Items database empty - run populate_database.py")
                        else:
                            response += "✗ Items table NOT FOUND\n"
                            issues.append("Items table missing")

                except Exception as e:
                    response += f"✗ Database error: {str(e)}\n"
                    issues.append(f"Database error: {e}")
            else:
                response += "✗ Database manager NOT initialized\n"
                issues.append("Database manager not initialized")

            # Check 3: Trade API Configuration
            response += "\n## Trade API Status\n\n"
            if hasattr(settings, "POESESSID") and settings.POESESSID:
                response += f"✓ POESESSID configured ({len(settings.POESESSID)} characters)\n"
                successes.append("Trade API cookie configured")
            else:
                response += "⚠ POESESSID NOT configured (trade features unavailable)\n"
                response += "  → Use the `setup_trade_auth` tool to configure\n"
                warnings.append("POESESSID not set - use setup_trade_auth tool")

            if self.trade_api:
                response += "✓ Trade API client initialized\n"
                successes.append("Trade API operational")
            else:
                response += "✗ Trade API NOT initialized\n"
                issues.append("Trade API not initialized")

            # Check 4: Character Fetcher
            response += "\n## Character Fetcher Status\n\n"
            if self.char_fetcher:
                response += "✓ Character fetcher initialized\n"
                successes.append("Character fetcher operational")

                if verbose:
                    response += "\n### Character Fetcher Diagnostic\n\n"
                    response += "Testing with known character: DoesFireWorkGoodNow\n\n"

                    try:
                        test_char = await self.char_fetcher.get_character(
                            account_name="Tomawar40-2671",
                            character_name="DoesFireWorkGoodNow",
                            league="Abyss",
                        )

                        if test_char:
                            response += "**Fetch Result:** SUCCESS ✓\n\n"
                            response += "**Data Structure:**\n"
                            response += f"- Name: {test_char.get('name', 'MISSING')}\n"
                            response += f"- Class: {test_char.get('class', 'MISSING')}\n"
                            response += f"- Level: {test_char.get('level', 'MISSING')}\n"
                            response += f"- Source: {test_char.get('source', 'MISSING')}\n"
                            response += "\n**Critical Stats:**\n"
                            response += f"- Life: {test_char.get('life', 'MISSING')}\n"
                            response += (
                                f"- Energy Shield: {test_char.get('energy_shield', 'MISSING')}\n"
                            )
                            response += f"- Fire Res: {test_char.get('fire_res', 'MISSING')}\n"
                            response += f"- Cold Res: {test_char.get('cold_res', 'MISSING')}\n"
                            response += (
                                f"- Lightning Res: {test_char.get('lightning_res', 'MISSING')}\n"
                            )
                            response += "\n**Stats Location:**\n"
                            response += f"- Stats at top level: {all(k in test_char for k in ['life', 'energy_shield'])}\n"
                            response += f"- Has 'stats' dict: {'stats' in test_char}\n"

                            if "stats" in test_char:
                                response += (
                                    f"- Stats dict has life: {'life' in test_char['stats']}\n"
                                )

                            # Check for code version markers
                            if test_char.get("source") == "poe.ninja API":
                                response += "\n**✓ Using NEW poe.ninja API code**\n"
                                successes.append("New API code active")
                            else:
                                response += (
                                    f"\n**⚠ Unexpected source: {test_char.get('source')}**\n"
                                )
                                warnings.append("May be using old fetcher code")
                        else:
                            response += "**Fetch Result:** FAILED ✗\n"
                            response += "Could not fetch test character\n"
                            warnings.append("Character fetcher test failed")

                    except Exception as e:
                        response += f"**Fetch Error:** {str(e)}\n"
                        warnings.append(f"Character fetch error: {e}")

                    response += "\nSupported account formats:\n"
                    response += "- Format 1: 'AccountName'\n"
                    response += "- Format 2: 'AccountName#1234'\n"
                    response += "- Format 3: 'AccountName-1234'\n"
            else:
                response += "✗ Character fetcher NOT initialized\n"
                issues.append("Character fetcher not initialized")

            # Check 5: MCP Tool Handlers
            response += "\n## MCP Tool Handlers\n\n"
            required_handlers = [
                "_handle_analyze_character",
                "_handle_detect_weaknesses",
                "_handle_evaluate_upgrade",
                "_handle_calculate_ehp",
                "_handle_analyze_spirit",
                "_handle_analyze_stun",
                "_handle_optimize_metrics",
                "_handle_search_trade_items",
            ]

            missing_handlers = []
            for handler_name in required_handlers:
                if hasattr(self, handler_name):
                    if verbose:
                        response += f"✓ {handler_name}\n"
                else:
                    response += f"✗ {handler_name} MISSING\n"
                    missing_handlers.append(handler_name)
                    issues.append(f"Handler {handler_name} not found")

            if not missing_handlers:
                response += f"\n✓ All {len(required_handlers)} critical handlers present\n"
                successes.append("All handlers operational")

            # Summary
            response += "\n## Summary\n\n"
            response += f"- **Successes:** {len(successes)}\n"
            response += f"- **Warnings:** {len(warnings)}\n"
            response += f"- **Critical Issues:** {len(issues)}\n\n"

            if len(issues) == 0 and len(warnings) == 0:
                response += "🟢 **STATUS: ALL SYSTEMS OPERATIONAL**\n"
            elif len(issues) == 0:
                response += "🟡 **STATUS: OPERATIONAL WITH WARNINGS**\n"
                response += "\nWarnings:\n"
                for warning in warnings:
                    response += f"- {warning}\n"
            else:
                response += "🔴 **STATUS: CRITICAL ISSUES DETECTED**\n"
                response += "\nCritical Issues:\n"
                for issue in issues:
                    response += f"- {issue}\n"

                response += "\n### Recommended Actions:\n"
                if "Database" in str(issues):
                    response += "1. Check database connection and initialization\n"
                    response += "2. Verify database file exists\n"
                    response += "3. Run database population script if needed\n"

                if "Handler" in str(issues):
                    response += "1. Verify all handler methods are implemented\n"
                    response += "2. Check for import errors in the MCP server\n"

                if "Calculator" in str(issues):
                    response += "1. Check calculator module imports\n"
                    response += "2. Verify calculator initialization in __init__\n"

            # Verbose diagnostics
            if verbose:
                response += "\n## Detailed Diagnostics\n\n"
                response += f"- Python version: {sys.version.split()[0]}\n"
                response += f"- MCP server class: {self.__class__.__name__}\n"
                response += f"- Settings module loaded: {bool(settings)}\n"
                response += f"- Debug logging: {settings.DEBUG if hasattr(settings, 'DEBUG') else 'Unknown'}\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            import traceback

            return [
                types.TextContent(
                    type="text",
                    text=f"Health check failed with error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}",
                )
            ]

    async def _handle_check_tree_freshness(self, args: dict) -> List[types.TextContent]:
        """Self-diagnostic: compare local data/game/version.json against poe.ninja's current PassiveTree tag.

        Strict change-detection only — fetches /poe2/api/data/index-state for the
        PassiveTree version tag, compares to our local patch_version, reports
        current/behind/ahead/unable. Does NOT download or modify any data; pure
        diagnostic so users know whether they need to `git pull` for fresher
        data/game/ datasets.

        Per the project data policy in CLAUDE.md, poe.ninja is allowed for
        character/change-detection ONLY, not game-data sourcing. This tool is
        the canonical change-detection use case.
        """
        try:
            verbose = args.get("verbose", False)
            response = "# Game Data Freshness Check\n\n"

            # 1. Read local data/game/version.json (canonical) — falls back to
            #    legacy data/version.json (from data_distributor) if newer file
            #    isn't present
            game_version_file = DATA_DIR / "game" / "version.json"
            legacy_version_file = DATA_DIR / "version.json"
            local_version = None
            local_source = None
            if game_version_file.exists():
                try:
                    local_version = json.loads(game_version_file.read_text(encoding="utf-8"))
                    local_source = str(game_version_file.relative_to(DATA_DIR.parent))
                except Exception as e:
                    response += f":warning: Failed to parse {game_version_file}: {e}\n\n"
            elif legacy_version_file.exists():
                try:
                    local_version = json.loads(legacy_version_file.read_text(encoding="utf-8"))
                    local_source = str(legacy_version_file.relative_to(DATA_DIR.parent))
                except Exception as e:
                    response += f":warning: Failed to parse {legacy_version_file}: {e}\n\n"

            local_patch = (local_version or {}).get("patch_version", "(unknown)")
            local_rev = (local_version or {}).get("released_as") or (local_version or {}).get(
                "data_revision", "(unknown)"
            )

            response += f"## Local\n\n"
            response += f"- **Source:** `{local_source or '(no version manifest found)'}`\n"
            response += f"- **Patch:** `{local_patch}`\n"
            response += f"- **Revision:** `{local_rev}`\n"
            if local_version:
                ds = local_version.get("datasets") or {}
                if ds:
                    response += f"- **Datasets:** {', '.join(ds.keys())}\n"
            response += "\n"

            # 2. Probe poe.ninja index-state for the live PassiveTree tag
            response += "## Live (poe.ninja index-state)\n\n"
            live_passive_tree = None
            live_league_name = None
            live_league_slug = None
            try:
                import httpx

                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c:
                    r = await c.get(
                        "https://poe.ninja/poe2/api/data/index-state",
                        headers={
                            "User-Agent": "poe2-mcp/check_tree_freshness",
                            "Accept": "application/json",
                        },
                    )
                    if r.status_code != 200:
                        response += f":warning: index-state returned HTTP {r.status_code}; can't verify freshness.\n\n"
                    else:
                        idx = r.json()
                        # Find the FIRST non-private-league snapshot with a passiveTree tag
                        # (private leagues have weird names; main league is what users care about)
                        for snap in idx.get("snapshotVersions", []):
                            pt = snap.get("passiveTree")
                            url = (snap.get("url") or "").lower()
                            # Skip private-league slugs (pattern: pl#####)
                            if pt and not url.startswith("pl"):
                                live_passive_tree = pt
                                live_league_name = snap.get("name")
                                live_league_slug = snap.get("url")
                                break
                        if not live_passive_tree:
                            response += (
                                ":warning: No PassiveTree tag found in index-state snapshots.\n\n"
                            )
            except Exception as e:
                response += (
                    f":warning: Could not reach poe.ninja index-state: {type(e).__name__}: {e}\n\n"
                )
                response += "(Are you offline? Is poe.ninja down? Check connectivity.)\n\n"

            if live_passive_tree:
                response += (
                    f"- **Current league:** {live_league_name} (slug: `{live_league_slug}`)\n"
                )
                response += f"- **PassiveTree tag:** `{live_passive_tree}`\n\n"

            # 3. Verdict
            response += "## Verdict\n\n"
            if not local_version:
                response += ":x: **Cannot verify** — no local version manifest found at `data/game/version.json` or `data/version.json`.\n\n"
                response += "Fix: pull the latest from main (`git pull`) or run `python -m src.data.data_distributor` to fetch the data bundle from GitHub Releases.\n"
            elif not live_passive_tree:
                response += ":grey_question: **Cannot fully verify** — local patch `{local_patch}` is loaded, but the live PassiveTree tag from poe.ninja couldn't be fetched. Local data may or may not be current; try again later.\n".format(
                    local_patch=local_patch
                )
            else:
                # Normalize: live is "PassiveTree-0.5" → "0.5"; local is "0.5" (just the patch)
                live_normalized = live_passive_tree.replace("PassiveTree-", "")
                if str(local_patch) == live_normalized:
                    response += f":white_check_mark: **Current.** Your local data ({local_source}) matches the live patch (`{live_passive_tree}`).\n"
                else:
                    # Determine if behind or ahead based on simple float compare
                    try:
                        local_f = float(local_patch)
                        live_f = float(live_normalized)
                        if local_f < live_f:
                            response += f":warning: **Behind by patch.** Local is `{local_patch}`, live is `{live_normalized}`.\n\n"
                            response += "Fix: `git pull` to fetch the latest `data/game/` files HivemindMinion has extracted for the new patch.\n"
                        else:
                            response += f":grey_question: **Ahead of live?** Local is `{local_patch}`, live is `{live_normalized}`. This is unusual — possibly local extraction of an unreleased patch.\n"
                    except ValueError:
                        response += f":grey_question: **Version mismatch (non-numeric).** Local: `{local_patch}`. Live: `{live_normalized}`. Manual inspection needed.\n"

            # 4. Verbose mode: dump full index-state snapshot summary
            if verbose and live_passive_tree:
                try:
                    response += "\n## Verbose: index-state snapshots\n\n"
                    snaps = (idx or {}).get("snapshotVersions", [])
                    response += f"| Name | Slug | PassiveTree |\n|---|---|---|\n"
                    for snap in snaps[:20]:
                        response += f"| {snap.get('name', '?')} | `{snap.get('url', '?')}` | `{snap.get('passiveTree', '-')}` |\n"
                    if len(snaps) > 20:
                        response += f"\n*(+{len(snaps) - 20} more snapshots)*\n"
                except Exception:
                    pass

            return [types.TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"check_tree_freshness failed: {e}", exc_info=True)
            return [
                types.TextContent(
                    type="text", text=f"check_tree_freshness encountered an error: {str(e)}"
                )
            ]

    async def _handle_check_for_updates(self, args: dict) -> List[types.TextContent]:
        """Report (and optionally apply, with consent) pending data/code updates.

        Default is report-only. ``apply=true`` is the user's explicit consent to
        apply updates right now. See src/data/update_manager.py for the model.
        """
        try:
            apply = bool(args.get("apply", False))
            layer = args.get("layer", "all")
            try:
                from src.data import update_manager as um
            except ImportError:
                from data import update_manager as um  # direct-exec fallback

            # Network + git calls are blocking; keep the event loop responsive.
            status = await asyncio.to_thread(um.get_update_status, True)

            response = "# Update Check\n\n"
            response += f"**Update available:** {'yes' if status['update_available'] else 'no'}\n"
            response += f"**Recommended:** {status['recommended_action']}\n\n"

            d = status["data"]
            response += "## Game Data\n\n"
            response += f"- Local bundle: `{d['local_tag'] or '(none — bootstrap)'}`\n"
            response += f"- Latest release: `{d['latest_tag'] or '(unknown)'}`\n"
            response += f"- Consent policy: `{d['consent_mode']}`\n"
            response += f"- Status: {d['reason']}\n\n"

            c = status["code"]
            response += "## Server Code\n\n"
            response += f"- Install kind: `{c['install_kind']}`\n"
            response += f"- Current: `{c['current'] or '(unknown)'}`\n"
            response += f"- Latest: `{c['latest'] or '(unknown)'}`\n"
            response += f"- Self-applicable: {'yes' if c['can_self_apply'] else 'no'}\n"
            response += f"- Status: {c['reason']}\n\n"

            if apply and status["update_available"]:
                response += "## Applying (consent granted via apply=true)\n\n"
                do_data = layer in ("all", "data")
                do_code = layer in ("all", "code")
                results = await asyncio.to_thread(um.apply_updates, True, do_data, do_code)
                if results.get("data") is not None:
                    r = results["data"]
                    response += f"- Data: {'OK' if r['ok'] else 'FAILED'} — {r['message']}\n"
                if results.get("code") is not None:
                    r = results["code"]
                    response += f"- Code: {'OK' if r['ok'] else 'FAILED'} — {r['message']}\n"
                if c["install_kind"] != "git" and c["update_available"]:
                    response += (
                        "\n> Note: a running packaged (.mcpb) install can't replace its own "
                        "code. Reinstall the newer `.mcpb` in Claude Desktop to update code.\n"
                    )
                if results.get("data") and results["data"]["ok"]:
                    response += "\n*Data applied. Restart the MCP server to load the new data.*\n"
            elif apply:
                response += "_Nothing to apply — already current._\n"
            elif status["update_available"]:
                response += "_Report only. Re-run with `apply=true` to apply with your consent._\n"

            return [types.TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"check_for_updates failed: {e}", exc_info=True)
            return [
                types.TextContent(
                    type="text", text=f"check_for_updates encountered an error: {str(e)}"
                )
            ]

    async def _handle_clear_cache(self, args: dict) -> List[types.TextContent]:
        """Clear all caches (in-memory, SQLite, Redis)"""
        try:
            response = "# Cache Clear Operation\n\n"
            cleared = []
            errors = []

            # Clear character fetcher cache
            if self.char_fetcher and hasattr(self.char_fetcher, "cache_manager"):
                cache_mgr = self.char_fetcher.cache_manager
                if cache_mgr:
                    try:
                        # Get stats before clearing
                        stats_before = await cache_mgr.get_statistics()

                        # Clear all cache tiers
                        await cache_mgr.clear()

                        response += "## Character Fetcher Cache\n\n"
                        response += f"✓ Cleared L1 (Memory): {stats_before.get('l1_memory_items', 0)} items\n"
                        response += f"✓ Cleared L3 (SQLite): {stats_before.get('l3_sqlite_items', 0)} items\n"
                        if cache_mgr.redis_client:
                            response += "✓ Cleared L2 (Redis)\n"
                        cleared.append("Character cache")
                    except Exception as e:
                        response += f"✗ Error clearing character cache: {str(e)}\n"
                        errors.append(f"Character cache: {e}")
                else:
                    response += "⚠ Character fetcher has no cache manager\n"
            else:
                response += "⚠ Character fetcher not initialized\n"

            # Clear poe.ninja API cache
            if self.char_fetcher and hasattr(self.char_fetcher, "ninja_api"):
                ninja_api = self.char_fetcher.ninja_api
                if ninja_api and hasattr(ninja_api, "cache_manager"):
                    cache_mgr = ninja_api.cache_manager
                    if cache_mgr:
                        try:
                            await cache_mgr.clear()
                            response += "\n## poe.ninja API Cache\n\n"
                            response += "✓ Cleared API cache\n"
                            cleared.append("API cache")
                        except Exception as e:
                            response += f"✗ Error clearing API cache: {str(e)}\n"
                            errors.append(f"API cache: {e}")

            # Summary
            response += "\n## Summary\n\n"
            if cleared:
                response += f"✅ Successfully cleared {len(cleared)} cache layer(s):\n"
                for item in cleared:
                    response += f"- {item}\n"

            if errors:
                response += f"\n⚠️ {len(errors)} error(s) occurred:\n"
                for error in errors:
                    response += f"- {error}\n"

            if not cleared and not errors:
                response += "⚠️ No caches found to clear\n"

            response += "\n**Next Steps:**\n"
            response += "- Character data will be fetched fresh from poe.ninja API\n"
            response += "- Run `health_check verbose:true` to verify new data\n"
            response += "- Re-run your tests to confirm stats appear correctly\n"

            logger.info(f"Cache cleared - {len(cleared)} layers cleared, {len(errors)} errors")

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Cache clear failed: {e}", exc_info=True)
            import traceback

            return [
                types.TextContent(
                    type="text",
                    text=f"Cache clear failed with error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}",
                )
            ]

    # NEW ENHANCEMENT FEATURE HANDLERS

    async def _handle_find_best_supports(self, args: dict) -> List[types.TextContent]:
        """Find best support gem combinations for a spell"""
        try:
            # Accept both spell_name and skill_name for compatibility
            spell_name = args.get("spell_name") or args.get("skill_name")
            max_spirit = args.get("max_spirit", 100)
            num_supports = args.get("num_supports", 5)
            goal = args.get("goal", "dps")
            top_n = args.get("top_n", 5)

            if not spell_name:
                return [
                    types.TextContent(
                        type="text", text="Error: spell_name or skill_name is required"
                    )
                ]

            debug_log(
                f"Finding best supports for {spell_name} (goal: {goal}, spirit: {max_spirit})"
            )

            # Find best combinations
            results = self.gem_synergy_calculator.find_best_combinations(
                spell_name=spell_name.lower(),
                max_spirit=max_spirit,
                num_supports=num_supports,
                optimization_goal=goal,
                top_n=top_n,
            )

            if not results:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No support gem combinations found for '{spell_name}'. The spell may not be in the database or no compatible supports exist.",
                    )
                ]

            # Format response
            response = f"# Best Support Gem Combinations for {spell_name.title()}\n\n"
            response += f"**Optimization Goal:** {goal.title()}\n"
            response += f"**Max Spirit:** {max_spirit}\n"
            response += f"**Number of Supports:** {num_supports}\n\n"
            response += "---\n\n"

            for i, result in enumerate(results, 1):
                response += self.gem_synergy_calculator.format_result(result, detailed=(i == 1))
                if i < len(results):
                    response += "\n---\n\n"

            logger.info(f"Found {len(results)} support combinations for {spell_name}")
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error finding best supports: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error analyzing support gems: {str(e)}")]

    async def _handle_explain_mechanic(self, args: dict) -> List[types.TextContent]:
        """Explain a PoE2 game mechanic — canonical game text first, fallback to legacy.

        Tier 1 (PRIMARY): data/game/stat_descriptions/ — game-shipped .csd text,
        16,533 entries, source-tagged for provenance. find_stat_description() for
        exact stat_id match, search_stat_descriptions() for substring recovery.

        Tier 2 (FALLBACK): src/knowledge/poe2_mechanics.py — hand-authored
        summaries (community interpretation of wiki sources). Useful for
        high-level concepts like "ignite" / "rage" that aren't single stat_ids.
        Responses from this tier are clearly labeled as such so the caller knows
        the provenance.

        Closes HivemindOverlord's 2026-05-31 feedback re: explain_mechanic
        returning hand-authored interpretation dressed up as authoritative data.
        """
        # Local import to avoid circulars during module load + to keep the
        # handler's dependency on data helpers explicit
        from src.data.game_data import (
            find_stat_description,
            search_stat_descriptions,
            find_per_skill_stat_description,
            search_per_skill_stat_descriptions,
        )

        try:
            raw_query = (args.get("mechanic_name") or "").strip()
            mechanic_name = raw_query.lower()

            # ---- No query: overview + sample suggestions from both tiers ----
            if not mechanic_name:
                response = "# PoE2 Mechanic / Stat Description Lookup\n\n"
                response += (
                    "Call this tool with `mechanic_name` set to either:\n"
                    "- A mechanic name: `freeze`, `ignite`, `stun`, `critical strike`\n"
                    "- A stat_id: `support_ignite_proliferation_radius`, "
                    "`base_chance_to_ignite_%`\n"
                    "- A substring to search: `proliferation`, `spread`, `regeneration`\n\n"
                )
                response += "## Tier 1 — canonical game text\n"
                response += (
                    "16,533 root-level + 1,240 per-skill stat descriptions "
                    "extracted from .csd files. Lookup is exact-match on stat_id "
                    "(consulted across both sources), with substring fuzzy match "
                    "as fallback (returns 'did you mean' suggestions).\n\n"
                )
                response += "## Tier 2 — hand-authored summaries\n"
                response += (
                    "High-level mechanic explanations (ignite/freeze/rage/etc.) "
                    "with formulas and common-questions. Returned when no exact "
                    "stat_id matches.\n\n"
                )
                response += "**Data source**: data/game/stat_descriptions/ + src/knowledge/poe2_mechanics.py\n"
                return [types.TextContent(type="text", text=response)]

            debug_log(f"Explaining mechanic: {mechanic_name}")

            # ---- Cluster-dump mode (#159 field feedback): everything related
            #      to the query in ONE call — stat_ids + granting sources ----
            if args.get("cluster"):
                return await self._handle_mechanic_cluster_dump(raw_query)

            # ---- Tier 1a: exact stat_id match in the canonical dataset ----
            exact = find_stat_description(raw_query)
            if exact:
                response = self._format_stat_description_response(exact, raw_query)
                logger.info(f"Explained via Tier 1 exact: {raw_query}")
                return [types.TextContent(type="text", text=response)]

            # ---- Tier 1a-bis: exact match in per-skill stat descriptions ----
            # Some stat_ids only exist in the specific_skill_stat_descriptions/
            # subtree (e.g. skill-specific damage tags). Consult the per-skill
            # bundle before falling through to the hand-authored Tier 2 so we
            # preserve "canonical game text" provenance whenever possible.
            per_skill_exact = find_per_skill_stat_description(raw_query)
            if per_skill_exact:
                # Same formatter as Tier 1a — the record shape is identical
                # except `source_skill` replaces `source_file`. The formatter
                # picks up source_csd which is set on both paths, and we tag
                # the skill key for added provenance.
                response = self._format_stat_description_response(per_skill_exact, raw_query)
                if per_skill_exact.get("source_skill"):
                    response = response.replace(
                        "Canonical game-shipped text",
                        f"Canonical game-shipped text (per-skill bundle, "
                        f"skill: `{per_skill_exact['source_skill']}`)",
                    )
                logger.info(f"Explained via Tier 1a-bis (per-skill): {raw_query}")
                return [types.TextContent(type="text", text=response)]

            # ---- Tier 2: legacy hand-authored mechanics (high-level concepts) ----
            # Try this BEFORE Tier 1b (substring search) because for queries like
            # "ignite" or "freeze" the legacy entry gives a fuller answer than
            # the dozens of stat_id substring matches would.
            # Defensive: mechanics_kb may not be initialized (lazy / failed
            # init / smoke-test path) — treat as "no Tier 2 available" and
            # fall through to Tier 1b substring search.
            mechanic = None
            qa_answer = None
            if self.mechanics_kb is not None:
                mechanic = self.mechanics_kb.get_mechanic(mechanic_name)
                if not mechanic:
                    search_results = self.mechanics_kb.search_mechanics(mechanic_name)
                    if search_results:
                        mechanic = search_results[0]
                if not mechanic:
                    qa_answer = self.mechanics_kb.answer_question(mechanic_name)
            if qa_answer:
                # Wrap with provenance disclaimer
                response = (
                    "> **Source**: hand-authored summary in "
                    "`src/knowledge/poe2_mechanics.py` — community "
                    "interpretation of wiki sources, not extracted game text. "
                    "Cross-reference against the in-game tooltip for "
                    "balance-sensitive numbers.\n\n"
                )
                response += qa_answer
                return [types.TextContent(type="text", text=response)]

            if mechanic:
                response = (
                    "> **Source**: hand-authored summary in "
                    "`src/knowledge/poe2_mechanics.py` — community "
                    "interpretation of wiki sources, not extracted game text. "
                    "Cross-reference against the in-game tooltip for "
                    "balance-sensitive numbers.\n\n"
                )
                response += self.mechanics_kb.format_mechanic_explanation(mechanic)

                try:
                    official_strings = await self.mechanics_kb.get_official_terminology(
                        mechanic.name
                    )
                    if official_strings:
                        official_text = self.mechanics_kb.enhance_explanation_with_official_text(
                            mechanic, official_strings
                        )
                        response += official_text
                except Exception as e:
                    logger.debug(f"Could not fetch official terminology: {e}")

                # If the query also matches stat_ids in Tier 1, surface them as
                # cross-refs so users can see the canonical entries
                t1_hits = search_stat_descriptions(raw_query, limit=5)
                if t1_hits:
                    response += "\n\n## Related canonical stat descriptions (Tier 1)\n"
                    for h in t1_hits:
                        response += f"- `{h['primary_stat_id']}` ({h['source_csd']})\n"
                    response += (
                        "\nQuery any of these stat_ids directly for the exact "
                        "game-shipped text.\n"
                    )

                logger.info(f"Explained via Tier 2: {mechanic_name}")
                return [types.TextContent(type="text", text=response)]

            # ---- Tier 1b: substring search across the canonical dataset ----
            # Augmented to also search the per-skill bundle (#129) — that's
            # +1,240 descriptions vs the root-level 16,533. Both sources tagged
            # with source_csd, so the response shows where each hit came from.
            t1_hits = search_stat_descriptions(raw_query, limit=10)
            per_skill_hits = search_per_skill_stat_descriptions(raw_query, limit=10)
            combined_hits = (t1_hits or []) + (per_skill_hits or [])
            if combined_hits:
                # Trim to top 12 across both sources to keep the response tight
                combined_hits = combined_hits[:12]
                response = f"# Suggestions for `{raw_query}`\n\n"
                response += (
                    f"No exact match in either tier. Found "
                    f"{len(combined_hits)} stat_id"
                    f"{'s' if len(combined_hits) != 1 else ''} matching that "
                    f"substring across the canonical dataset (root + per-skill). "
                    f"Query any of these directly for its full description:\n\n"
                )
                for h in combined_hits:
                    template = (h.get("primary_template") or "").replace("\n", " ")
                    if len(template) > 120:
                        template = template[:117] + "..."
                    source_marker = h.get("source_csd", "?")
                    response += (
                        f"- **`{h['primary_stat_id']}`** "
                        f"({source_marker}, matched on {h['match_field']})\n"
                    )
                    if template:
                        response += f"  > {template}\n"
                response += (
                    f"\n**Data source**: data/game/stat_descriptions/ — "
                    f"16,533 root-level + 1,240 per-skill canonical descriptions.\n"
                )
                return [types.TextContent(type="text", text=response)]

            # ---- Tier 1c: BM25 lexical ranking (#177). Substring match found
            #      nothing, but the query may be a morphological variant
            #      (wither/withered) or multi-word phrase that substring can't
            #      bridge. Stemmed BM25 over the canonical corpus catches those
            #      with zero new deps and no model. ----
            try:
                from .data.lexical_search import search_stat_descriptions_ranked
            except ImportError:
                from src.data.lexical_search import search_stat_descriptions_ranked
            ranked = search_stat_descriptions_ranked(raw_query, k=10)
            if ranked:
                response = f"# Lexical matches for `{raw_query}`\n\n"
                response += (
                    f"No exact or substring match, but BM25 ranking over the "
                    f"canonical stat descriptions (stemmed — handles "
                    f"wither/withered, slow/slows) found {len(ranked)} relevant "
                    f"stat_id{'s' if len(ranked) != 1 else ''}. Query any directly "
                    f"for its full description:\n\n"
                )
                for h in ranked:
                    template = (h.get("template") or "").replace("\n", " ")
                    if len(template) > 120:
                        template = template[:117] + "..."
                    response += f"- **`{h['stat_id']}`** (score {h['score']})\n"
                    if template:
                        response += f"  > {template}\n"
                response += (
                    "\n**Tier**: BM25 lexical (Tier 1c, #177) over "
                    "data/game/stat_descriptions/. For true paraphrase beyond "
                    "word-stem matching, refine the query toward in-game terms.\n"
                )
                return [types.TextContent(type="text", text=response)]

            # ---- Total miss: helpful failure with all-tier exhaustion noted ----
            return [
                types.TextContent(
                    type="text",
                    text=(
                        f"No match for `{raw_query}` in any tier:\n"
                        f"- Tier 1a (root canonical stat_descriptions, 16,533 entries): "
                        f"no exact stat_id match\n"
                        f"- Tier 1a-bis (per-skill canonical descriptions, 1,240 entries "
                        f"from specific_skill_stat_descriptions/): no exact match\n"
                        f"- Tier 1b (substring search across both canonical sources): "
                        f"no matches\n"
                        f"- Tier 1c (BM25 lexical ranking): no relevant matches\n"
                        f"- Tier 2 (hand-authored mechanics): no match by name, search, or Q&A\n\n"
                        f"Try a broader substring (`proliferation` instead of "
                        f"`fire_proliferation_radius_multiplier`), or call this tool "
                        f"without arguments to see what categories are available."
                    ),
                )
            ]

        except Exception as e:
            logger.error(f"Error explaining mechanic: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error explaining mechanic: {str(e)}")]

    def _format_stat_description_response(self, record: dict, query: str) -> str:
        """Format a Tier 1 stat_description record as the explain_mechanic response.

        Includes the canonical game-shipped template, variant range conditions,
        handler chain, multi-stat cross-refs, and a provenance line. This is the
        opposite-of-hand-authored: every field is sourced.
        """
        primary_stat = record.get("primary_stat_id")
        all_stats = record.get("stat_ids") or []
        primary_template = record.get("primary_template") or ""
        variants = record.get("variants") or []
        source_csd = record.get("source_csd", "?")
        source_file = record.get("source_file", "?")
        source_line = record.get("source_line")

        response = f"# `{primary_stat}`\n\n"

        if primary_template:
            response += "## Game text (canonical)\n"
            # Render newlines as-is so the markdown shows the multi-line tooltip shape
            response += primary_template.replace("\\n", "\n") + "\n\n"

        if len(all_stats) > 1:
            response += "## Shared description with\n"
            for sid in all_stats[1:]:
                response += f"- `{sid}`\n"
            response += "\n"

        if len(variants) > 1:
            response += f"## Variants ({len(variants)})\n"
            response += (
                "Different display text by stat value range. `#` = default/any, "
                "`1`/`10` = exact value, `1|#` = >=1, `#|0` = <=0.\n\n"
            )
            for i, v in enumerate(variants):
                rng = v.get("range", "?")
                tmpl = (v.get("template") or "").replace("\\n", " ")
                if len(tmpl) > 200:
                    tmpl = tmpl[:197] + "..."
                handlers = v.get("handlers") or []
                response += f"**Range `{rng}`**: {tmpl}\n"
                if handlers:
                    response += f"  - Handlers: `{' '.join(handlers)}`\n"
                response += "\n"

        response += (
            f"---\n"
            f"**Data source**: `data/game/stat_descriptions/{source_file}` "
            f"line {source_line} (extracted from `data/extracted/Data/statdescriptions/{source_csd}`)\n"
            f"**Provenance**: Canonical game-shipped text (UTF-16 .csd, "
            f"PoE2 0.5). Not hand-authored interpretation.\n"
        )
        return response

    async def _handle_calculate_character_dps(self, args: dict) -> List[types.TextContent]:
        """Server-side spell DPS calculation. P5 / Issue #114.

        The MCP-as-math-engine principle: the AI passes pre-aggregated modifiers
        (sum of %increased, list of %more, flat added damage, crit fields,
        cast speed, optional enemy resistances), the server runs the canonical
        PoE2 formula in src/calculator/spell_dps_calculator.py, and returns
        the structured breakdown. No mental math, no AI rounding errors, no
        forgotten multipliers.
        """
        try:
            try:
                from .calculator.spell_dps_calculator import (
                    SpellDPSCalculator,
                    SpellStats,
                    CharacterModifiers,
                    EnemyStats,
                )
                from .calculator.v2_spell_db import resolve_spell_from_v2
                from .data.game_data import get_version
            except ImportError:
                from src.calculator.spell_dps_calculator import (
                    SpellDPSCalculator,
                    SpellStats,
                    CharacterModifiers,
                    EnemyStats,
                )
                from src.calculator.v2_spell_db import resolve_spell_from_v2
                from src.data.game_data import get_version

            calc = SpellDPSCalculator()

            # ---- Resolve spell ----
            spell_name = (args.get("spell_name") or "").strip()
            spell_stats_override = args.get("spell_stats") or {}
            gem_level = int(args.get("gem_level") or 20)

            if spell_stats_override:
                spell = SpellStats(
                    name=spell_stats_override.get("name") or spell_name or "custom",
                    base_damage_min=float(spell_stats_override.get("base_damage_min", 0)),
                    base_damage_max=float(spell_stats_override.get("base_damage_max", 0)),
                    damage_effectiveness=float(
                        spell_stats_override.get("damage_effectiveness", 1.0)
                    ),
                    base_crit_chance=float(spell_stats_override.get("base_crit_chance", 0)),
                    base_cast_time=float(spell_stats_override.get("base_cast_time", 1.0)),
                    damage_types=list(spell_stats_override.get("damage_types") or []),
                )
                spell_source = "caller-supplied spell_stats"
            elif spell_name:
                key = spell_name.lower()
                if key in calc.SPELL_DATABASE:
                    spell = calc.SPELL_DATABASE[key]
                    spell_source = f"built-in SPELL_DATABASE[{key!r}]"
                else:
                    # Fall back to skill_gems_v2 lookup (#119, ~1,249 spells).
                    v2 = resolve_spell_from_v2(spell_name, gem_level=gem_level)
                    if v2 is None:
                        available = ", ".join(sorted(calc.SPELL_DATABASE.keys()))
                        return [
                            types.TextContent(
                                type="text",
                                text=(
                                    f"Spell '{spell_name}' not in the built-in "
                                    f"database ({available}) and not resolvable "
                                    f"from data/game/skill_gems/skill_gems_v2.json "
                                    f"either (or the v2 file isn't shipped in "
                                    f"this checkout). For exotic spells or "
                                    f"unsupported scaling layouts, pass "
                                    f"`spell_stats` with base_damage_min/max, "
                                    f"base_crit_chance, base_cast_time, "
                                    f"damage_types."
                                ),
                            )
                        ]
                    v2_meta = v2.pop("_v2_meta", {})
                    spell = SpellStats(
                        name=v2["name"],
                        base_damage_min=v2["base_damage_min"],
                        base_damage_max=v2["base_damage_max"],
                        damage_effectiveness=v2["damage_effectiveness"],
                        base_crit_chance=v2["base_crit_chance"],
                        base_cast_time=v2["base_cast_time"],
                        damage_types=v2["damage_types"],
                    )
                    spell_source = (
                        f"data/game/skill_gems/skill_gems_v2.json -> "
                        f"{v2_meta.get('skill_id')} statset "
                        f"'{v2_meta.get('statset_label')}' @ gem_level={gem_level}"
                    )
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            "Error: provide spell_name (lookup) or spell_stats (custom). "
                            "Built-in spells: "
                            + ", ".join(sorted(calc.SPELL_DATABASE.keys()))
                            + ". Or any of ~1,249 spells from data/game/skill_gems/skill_gems_v2.json."
                        ),
                    )
                ]

            # ---- Build character modifiers ----
            added = args.get("added_damage") or {}
            char_mods = CharacterModifiers(
                increased_spell_damage=float(args.get("increased_spell_damage", 0)),
                increased_cast_speed=float(args.get("increased_cast_speed", 0)),
                increased_crit_damage=float(args.get("increased_crit_damage", 0)),
                more_multipliers=[float(m) for m in (args.get("more_multipliers") or [])],
                added_fire=float(added.get("fire", 0)),
                added_cold=float(added.get("cold", 0)),
                added_lightning=float(added.get("lightning", 0)),
                added_chaos=float(added.get("chaos", 0)),
                added_physical=float(added.get("physical", 0)),
                added_crit_bonus=float(args.get("added_crit_bonus", 100)),
                increased_crit_chance=float(args.get("increased_crit_chance", 0)),
                maximum_mana=float(args.get("max_mana", 0)),
                has_archmage=bool(args.get("has_archmage", False)),
            )

            # ---- Build enemy stats ----
            enemy_in = args.get("enemy") or {}
            enemy = EnemyStats(
                fire_resistance=float(enemy_in.get("fire_resistance", 0)),
                cold_resistance=float(enemy_in.get("cold_resistance", 0)),
                lightning_resistance=float(enemy_in.get("lightning_resistance", 0)),
                chaos_resistance=float(enemy_in.get("chaos_resistance", 0)),
                physical_resistance=float(enemy_in.get("physical_resistance", 0)),
                fire_exposure=float(enemy_in.get("fire_exposure", 0)),
                cold_exposure=float(enemy_in.get("cold_exposure", 0)),
                lightning_exposure=float(enemy_in.get("lightning_exposure", 0)),
                fire_penetration=float(enemy_in.get("fire_penetration", 0)),
                cold_penetration=float(enemy_in.get("cold_penetration", 0)),
                lightning_penetration=float(enemy_in.get("lightning_penetration", 0)),
                is_shocked=bool(enemy_in.get("is_shocked", False)),
            )

            # ---- Run the math ----
            result = calc.calculate_dps(spell, char_mods, enemy)

            # ---- DoT layer (#159) — optional `dot` block ----
            dot_in = args.get("dot") or {}
            dot_section: list = []
            dot_totals = None
            if dot_in:
                try:
                    from .calculator.dot_calculator import (
                        DoTCalculator,
                        AilmentInput,
                        SkillDoTInput,
                        split_expected_hit_by_type,
                    )
                except ImportError:
                    from src.calculator.dot_calculator import (
                        DoTCalculator,
                        AilmentInput,
                        SkillDoTInput,
                        split_expected_hit_by_type,
                    )

                dot_calc = DoTCalculator()
                breakdown = result.get("breakdown") or {}

                # Hit damage by type: explicit override, else attribute the
                # crit-weighted expected hit (pre-resistance — ailment
                # magnitude is based on unmitigated damage dealt).
                hit_by_type = {
                    k.lower(): float(v_)
                    for k, v_ in (dot_in.get("hit_damage_by_type") or {}).items()
                }
                if not hit_by_type:
                    hit_by_type = split_expected_hit_by_type(
                        expected_hit=float(breakdown.get("expected_hit", 0.0)),
                        base_damage=float(breakdown.get("base_damage", 0.0)),
                        primary_type=(spell.damage_types[0] if spell.damage_types else None),
                        added_by_type={
                            "fire": char_mods.added_fire,
                            "cold": char_mods.added_cold,
                            "lightning": char_mods.added_lightning,
                            "chaos": char_mods.added_chaos,
                            "physical": char_mods.added_physical,
                        },
                        damage_effectiveness=spell.damage_effectiveness,
                    )

                hits_per_second = float(result.get("casts_per_second", 0.0))

                ailment_results = []
                for a in dot_in.get("ailments") or []:
                    ailment_results.append(
                        dot_calc.calculate_ailment_dot(
                            AilmentInput(
                                ailment=str(a.get("type", "")),
                                chance_pct=float(a.get("chance", 100)),
                                increased_magnitude=float(a.get("increased_magnitude", 0)),
                                more_multipliers=[
                                    float(m) for m in (a.get("more_multipliers") or [])
                                ],
                                increased_duration=float(a.get("increased_duration", 0)),
                                stack_limit=int(a.get("stack_limit", 1)),
                                enemy_moving=bool(a.get("enemy_moving", False)),
                                aggravated=bool(a.get("aggravated", False)),
                            ),
                            hit_damage_by_type=hit_by_type,
                            hits_per_second=hits_per_second,
                            enemy=enemy,
                        )
                    )

                skill_dot_result = None
                sd = dot_in.get("skill_dot") or {}
                if sd:
                    skill_dot_result = dot_calc.calculate_skill_dot(
                        SkillDoTInput(
                            base_dps=float(sd.get("base_dps", 0)),
                            damage_type=str(sd.get("damage_type", "chaos")),
                            increased=float(sd.get("increased", 0)),
                            more_multipliers=[float(m) for m in (sd.get("more_multipliers") or [])],
                            uptime=float(sd.get("uptime", 1.0)),
                        ),
                        enemy=enemy,
                    )

                dot_totals = dot_calc.combine(
                    hit_dps=float(result.get("total_dps", 0.0)),
                    ailment_results=ailment_results,
                    skill_dot_result=skill_dot_result,
                )

                # Render the DoT section
                dot_section.append("## Damage over Time")
                for r in ailment_results:
                    if "error" in r:
                        dot_section.append(f"- ⚠️ {r['error']}")
                        continue
                    dot_section.append(
                        f"- **{r['ailment']}** ({r['damage_type']}): "
                        f"{r['sustained_dps']} sustained DPS "
                        f"({r['dps_per_stack']}/stack × {r['expected_active_stacks']} "
                        f"avg stacks, {r['duration_seconds']}s duration, "
                        f"{r['applications_per_second']} applications/s)"
                    )
                if skill_dot_result:
                    dot_section.append(
                        f"- **Skill DoT** ({skill_dot_result['damage_type']}): "
                        f"{skill_dot_result['sustained_dps']} sustained DPS "
                        f"({skill_dot_result['dps_at_full_uptime']} at full uptime "
                        f"× {skill_dot_result['uptime']} uptime)"
                    )
                dot_section.append("")
                dot_section.append(
                    f"**Sustained totals**: hit {dot_totals['hit_dps']} + "
                    f"DoT {dot_totals['dot_dps']} = "
                    f"**{dot_totals['total_sustained_dps']} total sustained DPS**"
                )
                dot_section.append("")

            # ---- Format response ----
            v = get_version() or {}
            lines = []
            lines.append(f"# {spell.name} DPS")
            lines.append("")
            lines.append(f"- **Total DPS**: {result.get('total_dps', 0)}")
            lines.append(f"- **Average hit**: {result.get('average_hit', 0)}")
            lines.append(f"- **Casts/sec**: {result.get('casts_per_second', 0)}")
            lines.append(f"- **Crit chance**: {result.get('crit_chance', 0)}%")
            lines.append("")

            breakdown = result.get("breakdown") or {}
            if breakdown:
                lines.append("## Breakdown")
                lines.append(f"- Base damage: {breakdown.get('base_damage', 0)}")
                lines.append(f"- Added damage: {breakdown.get('added_damage', 0)}")
                lines.append(f"- After increased: {breakdown.get('after_increased', 0)}")
                lines.append(f"- After more: {breakdown.get('after_more', 0)}")
                lines.append(f"- Expected hit (crit-weighted): {breakdown.get('expected_hit', 0)}")
                lines.append(f"- After resistance: {breakdown.get('after_resistance', 0)}")
                mults = breakdown.get("multipliers") or {}
                if mults:
                    lines.append("")
                    lines.append("**Multipliers applied:**")
                    lines.append(f"- Increased: ×{mults.get('increased', 1.0)}")
                    lines.append(f"- More (multiplicative): ×{mults.get('more', 1.0)}")
                    lines.append(f"- Crit: ×{mults.get('crit', 1.0)}")
                lines.append("")

            if dot_section:
                lines.extend(dot_section)

            if result.get("error"):
                lines.append(f"⚠️  **Calculator error**: {result['error']}")
                lines.append("")

            lines.append("---")
            lines.append(
                f"**Source**: {spell_source} → "
                f"`src/calculator/spell_dps_calculator.py::SpellDPSCalculator.calculate_dps`. "
                f"Math is canonical (PoE2 formula); spell base stats from the built-in "
                f"database are CURRENT-AS-OF-AUTHORING — verify against patch notes if "
                f"results look off."
            )
            if v:
                lines.append(
                    f"**Data version**: {v.get('released_as', '?')} "
                    f"(extracted {v.get('extracted_at', '?')})"
                )
            return [types.TextContent(type="text", text="\n".join(lines))]

        except Exception as e:
            logger.error(f"calculate_character_dps error: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error in calculate_character_dps: {e}")]

    async def _handle_mechanic_cluster_dump(self, raw_query: str) -> List[types.TextContent]:
        """Cluster-dump mode for explain_mechanic (field-feedback wish).

        One call returns: every canonical stat_id matching the query
        (root + per-skill), each with its template AND the skills that
        grant it, plus passive/ascendancy/mod sources matching the query
        text — replacing the chain of substring searches the reporter had
        to run to rebuild a mechanic's system by hand.
        """
        from src.data.game_data import (
            search_stat_descriptions,
            search_per_skill_stat_descriptions,
        )

        try:
            from .data.stat_source_index import get_stat_source_index
        except ImportError:
            from src.data.stat_source_index import get_stat_source_index

        try:
            index = get_stat_source_index()

            t1_hits = search_stat_descriptions(raw_query, limit=20) or []
            per_skill_hits = search_per_skill_stat_descriptions(raw_query, limit=20) or []
            sources = index.find_sources(raw_query, limit_per_source=15)

            lines = [f"# Cluster dump: `{raw_query}`", ""]

            # --- Stat ids with templates and granting skills ---
            combined = (t1_hits + per_skill_hits)[:25]
            if combined:
                lines.append(f"## Canonical stat_ids ({len(combined)} shown)")
                for h in combined:
                    template = (h.get("primary_template") or "").replace("\n", " ")
                    if len(template) > 110:
                        template = template[:107] + "..."
                    stat_id = h["primary_stat_id"]
                    lines.append(f"- **`{stat_id}`** ({h.get('source_csd', '?')})")
                    if template:
                        lines.append(f"  > {template}")
                    granting = index.skills_granting_stat(stat_id)
                    if granting:
                        shown = ", ".join(granting[:8])
                        more = f" (+{len(granting) - 8} more)" if len(granting) > 8 else ""
                        lines.append(f"  Granted by skills: {shown}{more}")
                lines.append("")
            else:
                lines.append("## Canonical stat_ids")
                lines.append("No stat_ids match that substring.")
                lines.append("")

            # --- Source matches on the query text itself ---
            if sources["skills"]:
                lines.append("## Skills carrying matching stat_ids")
                for stat_id, skills in sources["skills"].items():
                    lines.append(f"- `{stat_id}`: {', '.join(skills[:8])}")
                lines.append("")
            if sources["passive_nodes"]:
                lines.append("## Passive tree nodes")
                for n in sources["passive_nodes"]:
                    lines.append(f"- **{n['name']}** ({n['kind']}): {'; '.join(n['stats'][:3])}")
                lines.append("")
            if sources["ascendancy_nodes"]:
                lines.append("## Ascendancy notables")
                for n in sources["ascendancy_nodes"]:
                    lines.append(
                        f"- **{n['name']}** ({n['ascendancy']}/{n['base_class']}): "
                        f"{'; '.join(n['stats'][:3])}"
                    )
                lines.append("")
            elif not sources["ascendancy_data_available"]:
                lines.append(
                    "*Ascendancy node data not available in this checkout "
                    "(data/complete_models/all_ascendancies.json is a local-only artifact).*"
                )
                lines.append("")
            if sources["mods"]:
                lines.append("## Item mods")
                for stat_id, mods in sources["mods"].items():
                    names = ", ".join(
                        f"{m['display_name']} ({m['generation_type']})"
                        for m in mods[:6]
                        if m.get("display_name")
                    )
                    lines.append(f"- `{stat_id}`: {names}")
                lines.append("")

            lines.append("---")
            lines.append(
                "**Sources**: data/game/stat_descriptions/ (canonical text), "
                "data/game/skill_gems/skill_gems_v2.json (skill statSets), "
                "data/psg_passive_nodes.json (passive tree), "
                "data/game/mods/mods.json (item mods). "
                "Use `find_stat_sources` for a focused reverse lookup on one stat."
            )
            return [types.TextContent(type="text", text="\n".join(lines))]

        except Exception as e:
            logger.error(f"Cluster dump error: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error in cluster dump: {str(e)}")]

    async def _handle_find_stat_sources(self, args: dict) -> List[types.TextContent]:
        """Reverse lookup: which skills/passives/ascendancies/mods grant stat X.

        The field-feedback gap this closes: the reporter could find every
        infusion scaling stat_id but never WHAT spawns the effect — the
        granting source was unqueryable.
        """
        try:
            from .data.stat_source_index import get_stat_source_index
        except ImportError:
            from src.data.stat_source_index import get_stat_source_index

        try:
            query = (args.get("query") or "").strip()
            if not query:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: provide `query` — a stat_id, stat_id substring, or stat text fragment.",
                    )
                ]
            limit = int(args.get("limit") or 15)

            # Run the (synchronous, CPU-bound) index lookup in a worker thread
            # under a hard timeout. A single pathological query must never hang
            # the whole MCP session — it returns a graceful error instead
            # (field bug #4, 2026-06-16).
            index = get_stat_source_index()
            loop = asyncio.get_event_loop()
            try:
                sources = await asyncio.wait_for(
                    loop.run_in_executor(None, index.find_sources, query, limit),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                logger.error(f"find_stat_sources timed out for query={query!r}")
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            f"Error: stat-source lookup for `{query}` exceeded 15s "
                            "and was aborted. Try a more specific substring."
                        ),
                    )
                ]

            total = (
                len(sources["skills"])
                + len(sources["mods"])
                + len(sources["passive_nodes"])
                + len(sources["ascendancy_nodes"])
            )
            lines = [f"# Stat sources for `{query}`", ""]

            if total == 0:
                lines.append(
                    "No skills, passive nodes, ascendancy notables, or item mods "
                    "match that query. Try a broader substring (`wither` instead "
                    "of `withered_on_hit_for_2_seconds_%_chance`), or "
                    "`explain_mechanic` with `cluster: true` for the wide net."
                )
            else:
                if sources["skills"]:
                    lines.append(f"## Skills ({len(sources['skills'])} matching stat_ids)")
                    for stat_id, skills in sources["skills"].items():
                        shown = ", ".join(skills[:10])
                        more = f" (+{len(skills) - 10} more)" if len(skills) > 10 else ""
                        lines.append(f"- `{stat_id}`")
                        lines.append(f"  {shown}{more}")
                    lines.append("")
                if sources["passive_nodes"]:
                    lines.append(f"## Passive tree nodes ({len(sources['passive_nodes'])})")
                    for n in sources["passive_nodes"]:
                        lines.append(
                            f"- **{n['name']}** ({n['kind']}): {'; '.join(n['stats'][:3])}"
                        )
                    lines.append("")
                if sources["ascendancy_nodes"]:
                    lines.append(f"## Ascendancy notables ({len(sources['ascendancy_nodes'])})")
                    for n in sources["ascendancy_nodes"]:
                        lines.append(
                            f"- **{n['name']}** ({n['ascendancy']}/{n['base_class']}): "
                            f"{'; '.join(n['stats'][:3])}"
                        )
                    lines.append("")
                if sources["mods"]:
                    lines.append(f"## Item mods ({len(sources['mods'])} matching stat_ids)")
                    for stat_id, mods in sources["mods"].items():
                        # display_name is empty for IMPLICITs on uniques /
                        # monsters / maps — fall back to the descriptive mod_id
                        # so the player still gets an actionable source label
                        # instead of a blank entry (field bug, 2026-06-16).
                        names = ", ".join(
                            f"{m.get('display_name') or m.get('mod_id') or '?'} "
                            f"({m.get('generation_type') or '?'})"
                            for m in mods[:6]
                        )
                        extra = f" (+{len(mods) - 6} more)" if len(mods) > 6 else ""
                        lines.append(f"- `{stat_id}`: {names}{extra}")
                    lines.append("")

            if not sources["ascendancy_data_available"]:
                lines.append(
                    "*Note: ascendancy node data unavailable in this checkout — "
                    "data/complete_models/all_ascendancies.json is a local-only artifact.*"
                )
                lines.append("")

            lines.append("---")
            lines.append(
                "**Sources**: skill_gems_v2 statSets (skills), psg_passive_nodes "
                "(passives, stat-text match), all_ascendancies (notables, when "
                "present), canonical mods table (stat_id match)."
            )
            return [types.TextContent(type="text", text="\n".join(lines))]

        except Exception as e:
            logger.error(f"find_stat_sources error: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error in find_stat_sources: {str(e)}")]

    async def _handle_get_formula(self, args: dict) -> List[types.TextContent]:
        """Get a PoE2 calculation formula for Claude to use"""
        try:
            try:
                from .knowledge.formulas import get_formula, get_all_formula_names, FORMULAS
            except ImportError:
                from src.knowledge.formulas import get_formula, get_all_formula_names, FORMULAS

            formula_type = args.get("formula_type", "").lower().strip()

            if not formula_type:
                # Return list of all available formulas
                response = "# Available PoE2 Calculation Formulas\n\n"
                response += "Use these formulas to perform calculations. MCP provides the formulas, you do the math.\n\n"

                for name, data in FORMULAS.items():
                    response += f"## {name}\n"
                    response += f"**{data['name']}**\n"
                    response += f"```\n{data['formula']}\n```\n\n"

                response += "\n**Usage:** Call `get_formula` with a formula_type (e.g., 'dps', 'ehp', 'armor')"
                return [types.TextContent(type="text", text=response)]

            # Get specific formula
            formula_data = get_formula(formula_type)

            if "error" in formula_data:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Unknown formula: {formula_type}\n\nAvailable formulas: {', '.join(get_all_formula_names())}",
                    )
                ]

            # Format comprehensive formula response
            response = f"# {formula_data['name']}\n\n"
            response += f"## Formula\n```\n{formula_data['formula']}\n```\n\n"

            if "expanded" in formula_data:
                response += f"## Expanded Form\n```\n{formula_data['expanded']}\n```\n\n"

            response += "## Variables\n"
            for var_name, var_desc in formula_data.get("variables", {}).items():
                response += f"- **{var_name}**: {var_desc}\n"

            if "calculation_order" in formula_data:
                response += "\n## Calculation Order\n"
                for step in formula_data["calculation_order"]:
                    response += f"{step}\n"

            if "key_rules" in formula_data:
                response += "\n## Key Rules\n"
                for rule in formula_data["key_rules"]:
                    response += f"- {rule}\n"

            if "reference_table" in formula_data:
                response += f"\n## Reference Table\n```\n{formula_data['reference_table']}\n```\n"

            if "example" in formula_data:
                example = formula_data["example"]
                response += f"\n## Example\n"
                response += f"**Scenario:** {example.get('scenario', 'N/A')}\n\n"
                if "calculation" in example:
                    response += f"**Calculation:**\n```\n{example['calculation']}\n```\n"
                if "result" in example:
                    response += f"**Result:** {example['result']}\n"

            logger.info(f"Returned formula: {formula_type}")
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error getting formula: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error getting formula: {str(e)}")]

    async def _handle_compare_items(self, args: dict) -> List[types.TextContent]:
        """Compare two items"""
        try:
            item_a = args.get("item_a")
            item_b = args.get("item_b")
            character_data = args.get("character_data")
            build_goal = args.get("build_goal", "balanced")

            if not item_a or not item_b:
                return [
                    types.TextContent(
                        type="text", text="Error: Both item_a and item_b are required"
                    )
                ]

            debug_log(f"Comparing items (goal: {build_goal})")

            # Compare items
            report = self.gear_comparator.compare_items(
                item_a=item_a, item_b=item_b, character_data=character_data, build_goal=build_goal
            )

            # Format response
            response = self.gear_comparator.format_full_report(report)

            logger.info(
                f"Compared items: {item_a.get('name', 'Item A')} vs {item_b.get('name', 'Item B')}"
            )
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error comparing items: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error comparing items: {str(e)}")]

    async def _handle_analyze_damage_scaling(self, args: dict) -> List[types.TextContent]:
        """Analyze damage scaling bottlenecks"""
        try:
            character_data = args.get("character_data")
            skill_type = args.get("skill_type", "spell")

            if not character_data:
                return [types.TextContent(type="text", text="Error: character_data is required")]

            debug_log(f"Analyzing damage scaling (skill_type: {skill_type})")

            # Analyze scaling
            recommendations = self.damage_scaling_analyzer.analyze_scaling(
                character_data=character_data, skill_type=skill_type
            )

            # Format response
            response = self.damage_scaling_analyzer.format_recommendations(recommendations)

            logger.info(f"Analyzed damage scaling for {skill_type}")
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error analyzing damage scaling: {e}", exc_info=True)
            return [
                types.TextContent(type="text", text=f"Error analyzing damage scaling: {str(e)}")
            ]

    async def _handle_check_content_readiness(self, args: dict) -> List[types.TextContent]:
        """Check if character is ready for specific content"""
        try:
            character_data = args.get("character_data")
            content = args.get("content")

            if not character_data or not content:
                return [
                    types.TextContent(
                        type="text", text="Error: Both character_data and content are required"
                    )
                ]

            debug_log(f"Checking content readiness for: {content}")

            # Check readiness
            report = self.content_readiness_checker.check_readiness(
                character_data=character_data, content=content
            )

            # Format response
            response = self.content_readiness_checker.format_report(report)

            logger.info(f"Content readiness check: {content} - {report.readiness.value}")
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error checking content readiness: {e}", exc_info=True)
            return [
                types.TextContent(type="text", text=f"Error checking content readiness: {str(e)}")
            ]

    async def _handle_setup_trade_auth(self, args: dict) -> List[types.TextContent]:
        """Set up trade API authentication using browser automation"""
        try:
            headless = args.get("headless", False)

            # Check if playwright is installed
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                return [
                    types.TextContent(
                        type="text",
                        text="❌ Playwright not installed!\n\n"
                        "**Installation Required:**\n"
                        "```bash\n"
                        "pip install playwright\n"
                        "playwright install chromium\n"
                        "```\n\n"
                        "After installing, use this tool again to set up authentication.\n\n"
                        "**Note:** Playwright downloads ~100MB Chromium browser (one-time)",
                    )
                ]

            logger.info("Starting trade authentication setup...")

            # Import necessary modules
            from pathlib import Path
            from datetime import datetime

            base_dir = Path(__file__).parent.parent
            env_file = base_dir / ".env"

            response = "# Trade API Authentication Setup\n\n"
            response += "**Starting browser automation...**\n\n"

            async with async_playwright() as p:
                # Launch browser
                response += "✓ Browser launched\n"
                browser = await p.chromium.launch(
                    headless=headless, args=["--start-maximized"] if not headless else []
                )

                # Create context
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080} if not headless else None
                )
                page = await context.new_page()

                try:
                    # Navigate to trade site
                    logger.info("Opening browser to pathofexile.com/trade...")
                    await page.goto("https://www.pathofexile.com/trade2/search/poe2/Standard")
                    response += "✓ Browser opened to pathofexile.com/trade\n\n"
                    logger.info("Waiting for user to log in...")

                    # Wait for user to log in
                    max_wait = 300  # 5 minutes
                    check_interval = 2  # Check every 2 seconds
                    session_cookie = None

                    for i in range(0, max_wait, check_interval):
                        await asyncio.sleep(check_interval)

                        # Get cookies
                        cookies = await context.cookies()

                        # Look for POESESSID
                        for cookie in cookies:
                            if cookie["name"] == "POESESSID":
                                session_cookie = cookie["value"]
                                break

                        if session_cookie:
                            response += f"✅ **SUCCESS! Session cookie detected!**\n"
                            response += f"- Cookie length: {len(session_cookie)} characters\n"
                            response += f"- First 20 chars: {session_cookie[:20]}...\n\n"
                            break

                        # Progress indicator (log only)
                        if i % 10 == 0 and i > 0:
                            logger.info(f"Still waiting for login... ({i}s elapsed)")

                    if not session_cookie:
                        await browser.close()
                        return [
                            types.TextContent(
                                type="text",
                                text=response
                                + "\n\n❌ **Timeout:** Login took longer than 5 minutes.\n\n"
                                "Please use this tool again and complete login faster.",
                            )
                        ]

                    # Close browser
                    await browser.close()
                    response += "✓ Browser closed\n\n"

                    # Save to .env
                    response += "**Saving to .env file...**\n"

                    env_lines = []
                    poesessid_found = False

                    if env_file.exists():
                        with open(env_file, "r", encoding="utf-8") as f:
                            env_lines = f.readlines()

                        # Update existing POESESSID
                        for i, line in enumerate(env_lines):
                            if line.strip().startswith("POESESSID="):
                                env_lines[i] = f"POESESSID={session_cookie}\n"
                                poesessid_found = True
                                break

                    # Add new POESESSID if not found
                    if not poesessid_found:
                        if env_lines and not env_lines[-1].endswith("\n"):
                            env_lines.append("\n")
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        env_lines.append(f"\n# Path of Exile Trade Site Session Cookie\n")
                        env_lines.append(f"# Obtained: {timestamp}\n")
                        env_lines.append(f"POESESSID={session_cookie}\n")

                    # Write back
                    with open(env_file, "w", encoding="utf-8") as f:
                        f.writelines(env_lines)

                    response += f"✓ Saved to: {env_file}\n"
                    response += "✓ Variable: POESESSID\n\n"

                    response += "## ✅ Authentication Complete!\n\n"
                    response += "**Next Steps:**\n"
                    response += "1. Restart the MCP server for changes to take effect\n"
                    response += "2. Use `search_trade_items` tool to find gear upgrades\n\n"
                    response += "**Important Notes:**\n"
                    response += "- Cookie expires when you log out or after ~30 days\n"
                    response += "- If trade searches stop working, use this tool again\n"
                    response += "- Keep your .env file private (don't commit to git)\n"

                    logger.info("Trade authentication setup completed successfully")
                    return [types.TextContent(type="text", text=response)]

                except Exception as e:
                    await browser.close()
                    raise e

        except Exception as e:
            logger.error(f"Trade auth setup failed: {e}", exc_info=True)
            import traceback

            return [
                types.TextContent(
                    type="text",
                    text=f"❌ **Setup Failed**\n\n"
                    f"Error: {str(e)}\n\n"
                    f"**Troubleshooting:**\n"
                    f"- Make sure Playwright is installed: `pip install playwright`\n"
                    f"- Install Chromium: `playwright install chromium`\n"
                    f"- Check the full error above for details\n\n"
                    f"**Manual Fallback:**\n"
                    f"1. Visit https://www.pathofexile.com/trade in your browser\n"
                    f"2. Log in to your account\n"
                    f"3. Press F12 → Application → Cookies\n"
                    f"4. Find POESESSID and copy its value\n"
                    f"5. Add to .env: POESESSID=your_cookie_value\n\n"
                    f"Traceback:\n```\n{traceback.format_exc()}\n```",
                )
            ]

    # ============================================================================
    # TIER 1 VALIDATION TOOL HANDLERS
    # ============================================================================

    async def _handle_validate_support_combination(self, args: dict) -> List[types.TextContent]:
        """Validate if support gems can work together. Accepts support_gems, support_gem_names, or names (aliases). Optional spell_name unlocks damage-type-conflict detection (#117)."""
        try:
            support_gems = (
                args.get("support_gems") or args.get("support_gem_names") or args.get("names") or []
            )
            spell_name = args.get("spell_name")

            if not support_gems:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: support_gems (or alias: support_gem_names, names) list is required",
                    )
                ]

            # Use gem synergy calculator's validation method
            result = self.gem_synergy_calculator.validate_combination(
                support_gems, spell_name=spell_name
            )

            if result["valid"]:
                response = f"Valid combination: {', '.join(support_gems)}\n\n"
                response += f"Reason: {result['reason']}"
            else:
                response = f"Invalid combination\n\n"
                response += f"Reason: {result['reason']}\n\n"
                if result["conflicts"]:
                    response += "Conflicting pairs:\n"
                    for conflict_a, conflict_b in result["conflicts"]:
                        response += f"  - {conflict_a} + {conflict_b}\n"

            # Semantic warnings (#117) — surface even when valid=True
            warnings = result.get("warnings") or []
            if warnings:
                response += "\n\n**Warnings (semantic conflicts):**\n"
                for w in warnings:
                    response += f"- {w['message']}\n"
                if result.get("spell_tags") is not None:
                    response += f"\nSpell tags consulted: {result['spell_tags']}\n"

            response += "\n" + format_provenance(
                COMPUTED,
                source=(
                    "src/optimizer/gem_synergy_calculator.py::validate_combination "
                    "(name-pattern damage-type rules vs canonical skill_gems tags)"
                ),
            )
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error validating support combination: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_inspect_support_gem(self, args: dict) -> List[types.TextContent]:
        """Inspect complete details of a support gem (uses FreshDataProvider SSoT)"""
        try:
            support_name = args.get("support_name")

            if not support_name:
                return [types.TextContent(type="text", text="Error: support_name is required")]

            # Use FreshDataProvider as Single Source of Truth
            fresh_provider = get_fresh_data_provider()

            # Search for support (case-insensitive)
            support_data = fresh_provider.get_support_gem_by_name(support_name)

            # Also try direct ID match
            if not support_data:
                support_data = fresh_provider.get_support_gem(support_name)

            # Try search if still not found
            if not support_data:
                results = fresh_provider.search_support_gems(support_name)
                if results:
                    support_data = results[0]

            # --- Tier 2 fallback: skill_gems.json (gem_type='Support') ---
            # PR #94 wired inspect_spell_gem similarly. Some support gems (e.g.
            # Wildfire) only exist in the PoB2-sourced skill_gems dataset and
            # not in the .datc64-extracted support_gems table. Translate the
            # skill_gems schema into the legacy shape this handler's formatter
            # already understands.
            tier2_source_note = None
            if not support_data:
                new_dataset_file = (
                    Path(__file__).parent.parent
                    / "data"
                    / "game"
                    / "skill_gems"
                    / "skill_gems.json"
                )
                if new_dataset_file.exists():
                    with open(new_dataset_file, "r", encoding="utf-8") as f:
                        new_data = json.load(f)
                    needle = support_name.lower()
                    for gem in new_data.get("skill_gems", []):
                        if gem.get("gem_type") != "Support":
                            continue
                        name = (gem.get("name") or "").lower()
                        gid = (gem.get("gem_id") or "").lower()
                        vid = (gem.get("variant_id") or "").lower()
                        if needle == name or needle == vid or needle in gid or needle in name:
                            r = gem.get("requirements") or {}
                            support_data = {
                                "name": gem.get("name"),
                                "tags": gem.get("tags") or [],
                                "tier": gem.get("tier"),
                                "requirements": {
                                    "str": r.get("str", 0),
                                    "dex": r.get("dex", 0),
                                    "int": r.get("int", 0),
                                },
                                # spirit_cost / cost_multiplier / effects /
                                # compatible_with / restrictions /
                                # incompatible_with are NOT in the v1
                                # skill_gems schema — leave unset so the
                                # formatter just skips them.
                                "notes": (
                                    f"Tier-2 fallback record from "
                                    f"data/game/skill_gems/ (gem_type='Support'). "
                                    f"Some support-gem fields (spirit_cost, "
                                    f"effects, compatibility) are NOT extracted "
                                    f"in skill_gems v1 — query the .datc64 "
                                    f"support_gems dataset directly for those "
                                    f"if the gem is also present there."
                                ),
                            }
                            tier2_source_note = (
                                "**Data Source**: data/game/skill_gems/skill_gems.json "
                                "(Tier-2 fallback — gem not in data/game/support_gems/; "
                                "see notes field for v1 schema gaps).\n"
                            )
                            break

            if not support_data:
                # Did-you-mean suggestions (P2 / #115). Search both canonical
                # support_gems and skill_gems (Tier-2) name pools.
                pool = []
                try:
                    for gem in fresh_provider.get_all_support_gems().values():
                        n = gem.get("display_name") or gem.get("name")
                        if n:
                            pool.append(n)
                except Exception:
                    pass
                # Also pull Support-typed names from skill_gems
                new_dataset_file = (
                    Path(__file__).parent.parent
                    / "data"
                    / "game"
                    / "skill_gems"
                    / "skill_gems.json"
                )
                if new_dataset_file.exists():
                    try:
                        with open(new_dataset_file, "r", encoding="utf-8") as f:
                            sg_data = json.load(f)
                        for gem in sg_data.get("skill_gems", []):
                            if gem.get("gem_type") == "Support":
                                n = gem.get("name")
                                if n:
                                    pool.append(n)
                    except Exception:
                        pass
                suggestions = did_you_mean(support_name, pool, k=5)
                if suggestions:
                    response = (
                        f"# Support Gem Not Found\n\n"
                        f"No exact match for '{support_name}'. Did you mean:\n\n"
                    )
                    for name in suggestions:
                        response += f"- {name}\n"
                    response += (
                        f"\nCall ``inspect_support_gem`` with one of these "
                        f"names for full stats.\n"
                    )
                else:
                    response = (
                        f"Support gem '{support_name}' not found in "
                        f"data/game/support_gems/ (.datc64 extract) or "
                        f"data/game/skill_gems/ (PoB2 gem_type='Support'), "
                        f"and no close name candidates. ``list_all_supports`` "
                        f"will enumerate every support.\n"
                    )
                return [types.TextContent(type="text", text=response)]

            # Format response
            response = f"# {support_data.get('name', support_name)}\n\n"

            # Basic info
            if support_data.get("tags"):
                response += f"**Tags**: {', '.join(support_data['tags'])}\n"

            if support_data.get("tier"):
                response += f"**Tier**: {support_data['tier']}\n"

            if support_data.get("acquisition"):
                response += f"**Acquisition**: {support_data['acquisition']}\n\n"

            # Requirements
            reqs = support_data.get("requirements", {})
            if reqs:
                req_parts = []
                if "level" in reqs:
                    req_parts.append(f"Level {reqs['level']}")
                if "str" in reqs:
                    req_parts.append(f"{reqs['str']} Str")
                if "dex" in reqs:
                    req_parts.append(f"{reqs['dex']} Dex")
                if "int" in reqs:
                    req_parts.append(f"{reqs['int']} Int")
                if req_parts:
                    response += f"**Requirements**: {', '.join(req_parts)}\n\n"

            # Costs
            spirit_cost = support_data.get("spirit_cost", 0)
            if spirit_cost:
                response += f"**Spirit Cost**: {spirit_cost}\n"

            cost_multi = support_data.get("cost_multiplier")
            if cost_multi:
                response += f"**Cost Multiplier**: {cost_multi}%\n\n"

            # Effects (the meat of the support)
            effects = support_data.get("effects", {})
            if effects:
                response += "**Effects**:\n"
                for effect_name, effect_value in effects.items():
                    # Format effect names nicely
                    formatted_name = effect_name.replace("_", " ").title()
                    if isinstance(effect_value, bool):
                        response += f"- {formatted_name}\n"
                    else:
                        response += f"- {formatted_name}: {effect_value}\n"
                response += "\n"

            # Compatibility
            req_tags = support_data.get("compatible_with", [])
            if req_tags:
                response += f"**Compatible With**: {', '.join(req_tags)}\n"

            # Restrictions
            restrictions = support_data.get("restrictions", [])
            if restrictions:
                response += f"**Restrictions**: {', '.join(restrictions)}\n"

            # Incompatibilities
            incomp = support_data.get("incompatible_with", [])
            if incomp:
                response += f"**Incompatible With**: {', '.join(incomp)}\n"

            # Notes
            notes = support_data.get("notes")
            if notes:
                response += f"\n**Notes**: {notes}\n"

            # Tier 2 provenance line (only set when we fell back to skill_gems)
            if tier2_source_note:
                response += f"\n{tier2_source_note}"

            source = (
                "data/game/skill_gems/skill_gems.json (Tier-2 fallback)"
                if tier2_source_note
                else "data/game/support_gems/support_gems.json"
            )
            response += "\n" + format_provenance(CANONICAL, source=source)
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting support gem: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_inspect_spell_gem(self, args: dict) -> List[types.TextContent]:
        """Inspect complete details of a spell gem. Accepts spell_name, name, or gem_name (aliases).

        Prefers the fresh data/game/skill_gems/skill_gems.json (Patch 0.5, from PoB2 dev).
        Falls back to legacy data/pob_complete_skills.json (Dec 2025) for fields the v1
        dataset doesn't yet extract (e.g. baseMultiplier, constantStats, statMap).
        """
        try:
            spell_name = args.get("spell_name") or args.get("name") or args.get("gem_name")

            if not spell_name:
                return [
                    types.TextContent(
                        type="text", text="Error: spell_name (or alias: name, gem_name) is required"
                    )
                ]

            # --- Tier 1: try the fresh 0.5 dataset ---
            new_dataset_file = (
                Path(__file__).parent.parent / "data" / "game" / "skill_gems" / "skill_gems.json"
            )
            new_dataset_meta = (
                Path(__file__).parent.parent / "data" / "game" / "skill_gems" / "metadata.json"
            )

            spell_data = None
            spell_id = None
            data_source_note = ""

            if new_dataset_file.exists():
                with open(new_dataset_file, "r", encoding="utf-8") as f:
                    new_data = json.load(f)
                needle = spell_name.lower()
                for gem in new_data.get("skill_gems", []):
                    name = (gem.get("name") or "").lower()
                    gid = (gem.get("gem_id") or "").lower()
                    vid = (gem.get("variant_id") or "").lower()
                    if needle == name or needle == vid or needle in gid or needle in name:
                        # Translate the new schema into the legacy-shaped dict the
                        # rest of this handler already understands. Saves a rewrite.
                        ge = gem.get("granted_effect") or {}
                        # Normalize levels: keys are strings in JSON already
                        normalized_levels = {}
                        for lvl_key, lvl in (ge.get("levels") or {}).items():
                            entry = {}
                            if "level_requirement" in lvl:
                                entry["levelRequirement"] = lvl["level_requirement"]
                            if "crit_chance" in lvl:
                                entry["critChance"] = lvl["crit_chance"]
                            if "cooldown" in lvl:
                                entry["cooldown"] = lvl["cooldown"]
                            if "cost" in lvl and isinstance(lvl["cost"], dict):
                                c = lvl["cost"]
                                entry["cost"] = {c.get("type", "Mana"): c.get("value", 0)}
                            # Spirit reservation (campaign C1b): present since
                            # the 0.5-current refresh (data-v0.5.0-r11)
                            if "spirit_reservation_flat" in lvl:
                                entry["spiritReservationFlat"] = lvl["spirit_reservation_flat"]
                            if "reservation_flat" in lvl:
                                entry["reservationFlat"] = lvl["reservation_flat"]
                            normalized_levels[lvl_key] = entry
                        normalized_stat_sets = []
                        for ss in ge.get("stat_sets") or []:
                            normalized_stat_sets.append(
                                {
                                    "label": ss.get("label"),
                                    "baseEffectiveness": ss.get("base_effectiveness"),
                                    "incrementalEffectiveness": ss.get("incremental_effectiveness"),
                                }
                            )
                        spell_data = {
                            "name": gem.get("name"),
                            "description": None,  # not in v1 schema
                            "skillTypes": ge.get("skill_types") or [],
                            "castTime": ge.get("cast_time"),
                            "levels": normalized_levels,
                            "statSets": normalized_stat_sets,
                            "qualityStats": [],  # not in v1 schema
                            "_new_dataset_extras": {
                                "gem_id": gem.get("gem_id"),
                                "variant_id": gem.get("variant_id"),
                                "gem_type": gem.get("gem_type"),
                                "tier": gem.get("tier"),
                                "natural_max_level": gem.get("natural_max_level"),
                                "requirements": gem.get("requirements"),
                                "weapon_requirements": gem.get("weapon_requirements"),
                                "tags": gem.get("tags") or [],
                                "tag_string": gem.get("tag_string"),
                                "additional_stat_sets": gem.get("additional_stat_sets") or [],
                            },
                        }
                        spell_id = gem.get("gem_id") or gem.get("variant_id")
                        # Build the data-source note from metadata.json if available
                        commit_ref = "PoB2 dev"
                        extracted_at = "?"
                        if new_dataset_meta.exists():
                            try:
                                with open(new_dataset_meta, "r", encoding="utf-8") as mf:
                                    meta = json.load(mf)
                                commit_ref = (meta.get("source_commit") or commit_ref)[:12]
                                extracted_at = meta.get("extracted_at", extracted_at)
                            except Exception:
                                pass
                        data_source_note = (
                            f"**Data Source**: data/game/skill_gems/skill_gems.json "
                            f"(PoB2 origin/dev @ {commit_ref}, extracted {extracted_at})\n"
                        )
                        break

            # --- Tier 2: fall back to legacy pob_complete_skills.json ---
            if spell_data is None:
                pob_skills_file = Path(__file__).parent.parent / "data" / "pob_complete_skills.json"

                if not pob_skills_file.exists():
                    return [
                        types.TextContent(
                            type="text",
                            text=(
                                f"Spell gem '{spell_name}' not found in data/game/skill_gems/ "
                                "and no legacy pob_complete_skills.json fallback available."
                            ),
                        )
                    ]

                with open(pob_skills_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Search for spell by name (case-insensitive) or ID
                skills = data.get("skills", {})

                for skill_id_candidate, skill in skills.items():
                    if not isinstance(skill, dict):
                        continue
                    skill_name = skill.get("name", "")
                    if (
                        skill_name.lower() == spell_name.lower()
                        or skill_id_candidate.lower() == spell_name.lower()
                        or spell_name.lower() in skill_name.lower()
                    ):
                        spell_data = skill
                        spell_id = skill_id_candidate
                        break

                if not spell_data:
                    # Did-you-mean suggestions (P2 / #115). Pool names from
                    # both skill_gems and the legacy file.
                    pool = []
                    if new_dataset_file.exists():
                        try:
                            with open(new_dataset_file, "r", encoding="utf-8") as f:
                                sg = json.load(f)
                            for gem in sg.get("skill_gems", []):
                                # Skip supports — inspect_support_gem handles those.
                                if gem.get("gem_type") == "Support":
                                    continue
                                n = gem.get("name")
                                if n:
                                    pool.append(n)
                        except Exception:
                            pass
                    for skill in skills.values():
                        if isinstance(skill, dict):
                            n = skill.get("name")
                            if n:
                                pool.append(n)
                    suggestions = did_you_mean(spell_name, pool, k=5)
                    if suggestions:
                        response = (
                            f"# Spell Gem Not Found\n\n"
                            f"No exact match for '{spell_name}'. Did you mean:\n\n"
                        )
                        for name in suggestions:
                            response += f"- {name}\n"
                        response += (
                            f"\nCall ``inspect_spell_gem`` with one of these "
                            f"names for full stats.\n"
                        )
                    else:
                        response = (
                            f"Spell gem '{spell_name}' not found in either "
                            f"data/game/skill_gems/ or data/pob_complete_skills.json, "
                            f"and no close name candidates. ``list_all_spells`` "
                            f"will enumerate every spell.\n"
                        )
                    return [types.TextContent(type="text", text=response)]

                data_source_note = (
                    f"**Data Source**: data/pob_complete_skills.json "
                    f"(Path of Building legacy data, "
                    f"{data.get('metadata', {}).get('extraction_date', 'Unknown date')} "
                    f"— pre-0.5; not yet in data/game/skill_gems/)\n"
                )

            # --- Tier 1c: v2 enrichment ---
            # When skill_gems_v2.json carries a record for this spell, merge in
            # the rich numeric data the v1 join view doesn't have: per-statSet
            # constantStats, per-level damage arrays, and qualityStats. This is
            # purely additive — if v2 lookup misses we keep the v1 view.
            v2_skill: Optional[Dict[str, Any]] = None
            try:
                try:
                    from .calculator.v2_spell_db import get_v2_skill_record
                except ImportError:
                    from src.calculator.v2_spell_db import get_v2_skill_record
                v2_skill = get_v2_skill_record(spell_name)
            except Exception:
                v2_skill = None

            if v2_skill:
                # qualityStats: the v1 join view leaves these empty; v2 carries
                # them as a list of [stat_id, per_quality_value] pairs.
                if v2_skill.get("qualityStats"):
                    spell_data["qualityStats"] = v2_skill["qualityStats"]

                # statSets enrichment: v1 ships {label, baseEffectiveness,
                # incrementalEffectiveness}. v2 adds {constantStats, stats,
                # levels (per-level damage arrays)}. Align by index — both
                # extractions order statSets the same way (PoB source order).
                v2_statsets = v2_skill.get("statSets") or []
                v1_statsets = spell_data.get("statSets") or []
                for i, ss in enumerate(v1_statsets):
                    if i < len(v2_statsets):
                        v2_ss = v2_statsets[i]
                        if isinstance(v2_ss, dict):
                            for k in (
                                "constantStats",
                                "stats",
                                "levels",
                                "damageIncrementalEffectiveness",
                            ):
                                if v2_ss.get(k) is not None and ss.get(k) is None:
                                    ss[k] = v2_ss[k]
                # If v1 had no statSets at all, fall back to v2's directly
                if not v1_statsets and v2_statsets:
                    spell_data["statSets"] = v2_statsets

                # Stamp the enrichment source so the response note reflects it.
                if data_source_note:
                    data_source_note = data_source_note.rstrip() + (
                        " + data/game/skill_gems/skill_gems_v2.json "
                        "(constantStats / per-level damage / qualityStats enrichment)\n"
                    )

            # Format response
            response = f"# {spell_data.get('name', spell_name)}\n\n"
            response += f"**ID**: {spell_id}\n"

            # Description
            if spell_data.get("description"):
                response += f"**Description**: {spell_data['description']}\n\n"

            # Gem metadata block — only from new dataset (Gems.lua-sourced)
            extras = spell_data.get("_new_dataset_extras")
            if extras:
                response += "**Gem Metadata** (PoB2 Gems.lua):\n"
                if extras.get("gem_type"):
                    response += f"  - Gem Type: {extras['gem_type']}\n"
                if extras.get("tier") is not None:
                    response += f"  - Tier: {extras['tier']}\n"
                if extras.get("natural_max_level") is not None:
                    response += f"  - Natural Max Level: {extras['natural_max_level']}\n"
                if extras.get("requirements"):
                    r = extras["requirements"]
                    response += (
                        f"  - Requirements: Str {r.get('str', 0)}, "
                        f"Dex {r.get('dex', 0)}, Int {r.get('int', 0)}\n"
                    )
                if extras.get("weapon_requirements"):
                    response += f"  - Weapon Requirements: {extras['weapon_requirements']}\n"
                if extras.get("tag_string"):
                    response += f"  - Tag String: {extras['tag_string']}\n"
                if extras.get("tags"):
                    response += f"  - Tags: {', '.join(extras['tags'])}\n"
                if extras.get("additional_stat_sets"):
                    response += (
                        f"  - Additional Stat Sets: {', '.join(extras['additional_stat_sets'])}\n"
                    )
                response += "\n"

            # Skill types (tags)
            if spell_data.get("skillTypes"):
                response += f"**Skill Types**: {', '.join(spell_data['skillTypes'])}\n"

            # Weapon types
            if spell_data.get("weaponTypes"):
                response += f"**Weapon Types**: {', '.join(spell_data['weaponTypes'])}\n"

            # Cast time
            if spell_data.get("castTime"):
                response += f"**Cast Time**: {spell_data['castTime']}s\n\n"

            # Per-level stats (show L1, L10, L20)
            levels = spell_data.get("levels", {})
            if levels:
                response += "**Per-Level Stats**:\n"
                for level_key in ["1", "10", "20"]:
                    if level_key in levels:
                        level_data = levels[level_key]
                        response += f"\nLevel {level_key}:\n"

                        # Level requirement
                        if "levelRequirement" in level_data:
                            response += f"  - Level Requirement: {level_data['levelRequirement']}\n"

                        # Base multiplier
                        if "baseMultiplier" in level_data:
                            response += f"  - Base Multiplier: {level_data['baseMultiplier']:.2f}\n"

                        # Mana/resource cost
                        if "cost" in level_data:
                            costs = level_data["cost"]
                            cost_parts = [f"{k}: {v}" for k, v in costs.items()]
                            response += f"  - Cost: {', '.join(cost_parts)}\n"

                        # Spirit reservation (persistent skills / meta gems —
                        # campaign C1b; the answer to "what does this reserve")
                        if "spiritReservationFlat" in level_data:
                            response += (
                                f"  - Spirit Reservation: {level_data['spiritReservationFlat']}\n"
                            )
                        if "reservationFlat" in level_data:
                            response += f"  - Reservation: {level_data['reservationFlat']}\n"

                        # Crit chance
                        if "critChance" in level_data:
                            response += f"  - Crit Chance: {level_data['critChance']}%\n"

                        # Cooldown
                        if "cooldown" in level_data:
                            response += f"  - Cooldown: {level_data['cooldown']}s\n"

                response += "\n"

            # StatSets (damage effectiveness, constantStats)
            stat_sets = spell_data.get("statSets", [])
            # Drop entries where both label and baseEffectiveness are unset — these are
            # placeholder slots in the v1 skill_gems schema; surfacing them as "None: None%"
            # is noise. The legacy pob_complete_skills.json doesn't have this problem.
            stat_sets = [
                s
                for s in stat_sets
                if s.get("label") is not None or s.get("baseEffectiveness") is not None
            ]
            if stat_sets:
                response += "**Stat Sets**:\n"
                for i, stat_set in enumerate(stat_sets):
                    label = stat_set.get("label") or f"Set {i+1}"
                    response += f"\n{label}:\n"

                    # Damage effectiveness
                    base_eff = stat_set.get("baseEffectiveness")
                    if base_eff is not None:
                        # Round noisy floats from the v1 extractor (e.g. 1.5199999809265)
                        try:
                            base_eff_disp = round(float(base_eff), 4)
                        except (TypeError, ValueError):
                            base_eff_disp = base_eff
                        response += f"  - Base Effectiveness: {base_eff_disp}\n"
                        incr_eff = stat_set.get("incrementalEffectiveness")
                        if incr_eff:
                            try:
                                incr_eff_disp = round(float(incr_eff), 4)
                            except (TypeError, ValueError):
                                incr_eff_disp = incr_eff
                            response += (
                                f"  - Incremental Effectiveness: {incr_eff_disp} per level\n"
                            )

                    # Constant stats (built-in modifiers) — from v2 enrichment
                    # or legacy pob_complete_skills.json.
                    const_stats = stat_set.get("constantStats", [])
                    if const_stats:
                        response += f"  - Built-in Modifiers:\n"
                        for stat in const_stats[:10]:  # Limit to first 10
                            if isinstance(stat, list) and len(stat) >= 2:
                                stat_id, value = stat[0], stat[1]
                                response += f"    - {stat_id}: {value}\n"
                        if len(const_stats) > 10:
                            response += f"    - ... and {len(const_stats) - 10} more\n"

                    # Per-level scaling stats — list of names from the v2 stats
                    # field, paired with sampled damage values at L1 / L10 / L20
                    # from the v2 levels[] array. Skipped silently when v2
                    # enrichment didn't fire.
                    v2_stats_list = stat_set.get("stats") or []
                    v2_levels = stat_set.get("levels") or []
                    if v2_stats_list and v2_levels:
                        response += f"  - Per-Level Scaling Stats:\n"
                        # Sample levels 1 / 10 / 20 (lua 1-indexed -> py 0/9/19)
                        sample_indices = [(1, 0), (10, 9), (20, 19)]
                        for stat_idx, stat_name in enumerate(v2_stats_list[:6]):
                            samples: List[str] = []
                            # Each level entry is a dict {"1": val, "2": val, ...}
                            # where the string-keyed positional index maps to the
                            # stats[] list position (1-indexed).
                            stat_key = str(stat_idx + 1)
                            for game_level, idx in sample_indices:
                                if idx < len(v2_levels):
                                    entry = v2_levels[idx]
                                    if isinstance(entry, dict) and stat_key in entry:
                                        samples.append(f"L{game_level}={entry[stat_key]}")
                            if samples:
                                response += f"    - {stat_name}: " + ", ".join(samples) + "\n"
                            else:
                                response += f"    - {stat_name}\n"
                        if len(v2_stats_list) > 6:
                            response += f"    - ... and {len(v2_stats_list) - 6} more\n"

                response += "\n"

            # Quality stats
            quality_stats = spell_data.get("qualityStats", [])
            if quality_stats:
                response += "**Quality Stats**:\n"
                for stat in quality_stats:
                    if isinstance(stat, list) and len(stat) >= 2:
                        stat_id, value = stat[0], stat[1]
                        response += f"  - {stat_id}: {value} per 1% quality\n"
                response += "\n"

            response += data_source_note

            # Provenance banner: source already in data_source_note above,
            # but make the tier explicit + add the data-version stamp.
            response += "\n" + format_provenance(
                CANONICAL, source="data/game/skill_gems/skill_gems.json"
            )
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting spell gem: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_list_all_supports(self, args: dict) -> List[types.TextContent]:
        """List all support gems with filtering, sorting, pagination, and output format options."""
        try:
            from src.utils.response_formatter import (
                PaginationMeta,
                filter_fields,
                format_list_response,
                SUPPORT_GEM_FIELDS,
                compact_json,
            )

            filter_tags = args.get("filter_tags", [])
            min_spirit = args.get("min_spirit")
            max_spirit = args.get("max_spirit")
            sort_by = args.get("sort_by", "name")
            limit = args.get("limit", 20)
            offset = args.get("offset", 0)
            detail = args.get("detail", "standard")
            output_format = args.get("format", "markdown")

            # Use FreshDataProvider as Single Source of Truth
            fresh_provider = get_fresh_data_provider()
            support_gems = fresh_provider.get_all_support_gems()

            # Extract and filter supports
            all_supports = []
            for support_id, support_data in support_gems.items():
                if not isinstance(support_data, dict) or "display_name" not in support_data:
                    continue

                spirit_cost = support_data.get("spirit_cost", 0) or 0

                # Apply filters
                if filter_tags:
                    support_tags = [t.lower() for t in (support_data.get("tags") or [])]
                    if not any(ft.lower() in support_tags for ft in filter_tags):
                        continue

                if min_spirit is not None and spirit_cost < min_spirit:
                    continue
                if max_spirit is not None and spirit_cost > max_spirit:
                    continue

                # Get key effects for display
                effects = support_data.get("effects", {})
                effect_summary = ""
                if effects:
                    key_effects = []
                    for k, v in list(effects.items())[:2]:
                        if isinstance(v, bool):
                            key_effects.append(k.replace("_", " ").title())
                        else:
                            key_effects.append(f"{k.replace('_', ' ').title()}: {v}")
                    effect_summary = ", ".join(key_effects)

                all_supports.append(
                    {
                        "name": support_data["display_name"],
                        "tags": support_data.get("tags") or [],
                        "tier": support_data.get("tier", "?"),
                        "spirit_cost": spirit_cost,
                        "effect_summary": effect_summary,
                        "effects": effects,
                        "compatible_with": support_data.get("compatible_with", []),
                        "requirements": support_data.get("requirements", {}),
                        "acquisition": support_data.get("acquisition", ""),
                    }
                )

            # Sort
            if sort_by == "spirit_cost":
                all_supports.sort(key=lambda x: x["spirit_cost"])
            elif sort_by == "tier":
                all_supports.sort(
                    key=lambda x: (x["tier"] if isinstance(x["tier"], int) else 99, x["name"])
                )
            else:
                all_supports.sort(key=lambda x: x["name"])

            # Pagination
            total = len(all_supports)
            paginated = all_supports[offset : offset + limit]
            meta = PaginationMeta(total=total, limit=limit, offset=offset, showing=len(paginated))

            # Filter by detail level
            filtered = [filter_fields(s, detail, SUPPORT_GEM_FIELDS) for s in paginated]

            # Format response
            if output_format == "compact":
                response = compact_json({"results": filtered, "meta": meta.to_dict()})
            else:
                response = format_list_response(
                    filtered,
                    meta,
                    "Support Gems",
                    item_formatter=lambda s: self._format_support_item(s, detail),
                )

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing supports: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    def _format_support_item(self, sup: dict, detail: str) -> str:
        """Format a single support gem for markdown output."""
        if detail == "summary":
            return f"- {sup.get('name', 'Unknown')} (T{sup.get('tier', '?')})\n"

        result = f"**{sup.get('name', 'Unknown')}** (Tier {sup.get('tier', '?')})\n"
        if detail in ("standard", "full"):
            result += f"  Spirit: {sup.get('spirit_cost', 0)}, Tags: {', '.join((sup.get('tags') or [])[:3])}\n"
            if sup.get("effect_summary"):
                result += f"  Effects: {sup['effect_summary']}\n"
        if detail == "full" and sup.get("effects"):
            result += f"  Full Effects: {sup['effects']}\n"
        result += "\n"
        return result

    async def _handle_list_all_spells(self, args: dict) -> List[types.TextContent]:
        """List all spell/active skill gems with filtering, sorting, pagination, and output format options.

        Prefers the fresh data/game/skill_gems/skill_gems.json (Patch 0.5). Falls back
        to legacy data/pob_complete_skills.json (Dec 2025) if the new dataset is missing.
        """
        try:
            from src.utils.response_formatter import (
                PaginationMeta,
                filter_fields,
                format_list_response,
                SPELL_GEM_FIELDS,
                compact_json,
            )

            filter_element = args.get("filter_element")
            filter_tags = args.get("filter_tags", [])
            min_damage = args.get("min_damage")
            sort_by = args.get("sort_by", "name")
            limit = args.get("limit", 20)
            offset = args.get("offset", 0)
            detail = args.get("detail", "standard")
            output_format = args.get("format", "markdown")

            all_spells = []

            # --- Tier 1: prefer the fresh 0.5 dataset ---
            new_dataset_file = (
                Path(__file__).parent.parent / "data" / "game" / "skill_gems" / "skill_gems.json"
            )

            if new_dataset_file.exists():
                with open(new_dataset_file, "r", encoding="utf-8") as f:
                    new_data = json.load(f)
                # Active-spell selection: gem_type == 'Spell' (PoB2's own categorization).
                # This is intentionally narrower than the old "any gem with cast_time" —
                # it matches the dataset's authoritative Gems.lua classification.
                for gem in new_data.get("skill_gems", []):
                    if gem.get("gem_type") != "Spell":
                        continue
                    ge = gem.get("granted_effect") or {}
                    skill_types = ge.get("skill_types") or []

                    if filter_tags:
                        if not any(
                            tag.lower() in [st.lower() for st in skill_types] for tag in filter_tags
                        ):
                            continue

                    element = "Physical"
                    for st in skill_types:
                        if st in ["Fire", "Cold", "Lightning", "Chaos"]:
                            element = st
                            break
                    if filter_element and element.lower() != filter_element.lower():
                        continue

                    levels = ge.get("levels") or {}
                    # Pick the highest available level (20 is the typical PoB cap)
                    lvl20 = levels.get("20") or levels.get("1") or {}
                    cost = lvl20.get("cost") or {}
                    # v1 schema: cost is {type: 'Mana', value: N}
                    mana_cost = cost.get("value", 0) if cost.get("type") == "Mana" else 0

                    all_spells.append(
                        {
                            "name": gem.get("name"),
                            "id": gem.get("gem_id") or gem.get("variant_id"),
                            "element": element,
                            "tags": skill_types,
                            "base_multiplier": 0,  # not in v1 schema
                            "cast_time": ge.get("cast_time") or 0,
                            "mana_cost": mana_cost,
                            "description": "",  # not in v1 schema
                            "skill_types": skill_types,
                            "levels": levels,
                        }
                    )

            # --- Tier 2: legacy fallback if new dataset missing or empty ---
            if not all_spells:
                pob_skills_file = Path(__file__).parent.parent / "data" / "pob_complete_skills.json"

                if not pob_skills_file.exists():
                    return [
                        types.TextContent(
                            type="text",
                            text=(
                                "Error: neither data/game/skill_gems/skill_gems.json "
                                "nor data/pob_complete_skills.json available"
                            ),
                        )
                    ]

                with open(pob_skills_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                skills = data.get("skills", {})

                for skill_id, skill_data in skills.items():
                    if not isinstance(skill_data, dict):
                        continue
                    if skill_data.get("hidden"):
                        continue

                    name = skill_data.get("name", skill_id)
                    skill_types = skill_data.get("skillTypes", [])

                    if filter_tags:
                        if not any(
                            tag.lower() in [st.lower() for st in skill_types] for tag in filter_tags
                        ):
                            continue

                    levels = skill_data.get("levels", {})
                    level_20_data = levels.get("20", levels.get("1", {}))
                    cast_time = skill_data.get("castTime", 0)
                    base_mult = level_20_data.get("baseMultiplier", 0)
                    cost = level_20_data.get("cost", {})
                    mana_cost = cost.get("Mana", 0)

                    element = "Physical"
                    for st in skill_types:
                        if st in ["Fire", "Cold", "Lightning", "Chaos"]:
                            element = st
                            break

                    if filter_element and element.lower() != filter_element.lower():
                        continue

                    all_spells.append(
                        {
                            "name": name,
                            "id": skill_id,
                            "element": element,
                            "tags": skill_types,
                            "base_multiplier": base_mult,
                            "cast_time": cast_time,
                            "mana_cost": mana_cost,
                            "description": skill_data.get("description", ""),
                            "skill_types": skill_types,
                            "levels": levels,
                        }
                    )

            # Sort
            if sort_by == "base_damage" or sort_by == "base_multiplier":
                all_spells.sort(key=lambda x: x["base_multiplier"], reverse=True)
            elif sort_by == "cast_time":
                all_spells.sort(key=lambda x: x["cast_time"] if x["cast_time"] > 0 else 999)
            elif sort_by == "mana_cost":
                all_spells.sort(key=lambda x: x["mana_cost"], reverse=True)
            else:
                all_spells.sort(key=lambda x: x["name"])

            # Pagination
            total = len(all_spells)
            paginated = all_spells[offset : offset + limit]
            meta = PaginationMeta(total=total, limit=limit, offset=offset, showing=len(paginated))

            # Filter by detail level
            filtered = [filter_fields(s, detail, SPELL_GEM_FIELDS) for s in paginated]

            # Format response
            if output_format == "compact":
                response = compact_json({"results": filtered, "meta": meta.to_dict()})
            else:
                response = format_list_response(
                    filtered,
                    meta,
                    "Spell Gems",
                    item_formatter=lambda s: self._format_spell_item(s, detail),
                )

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing spells: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    def _format_spell_item(self, spell: dict, detail: str) -> str:
        """Format a single spell gem for markdown output."""
        if detail == "summary":
            return f"- {spell.get('name', 'Unknown')} ({spell.get('element', 'Physical')})\n"

        mult_str = (
            f"{spell.get('base_multiplier', 0):.1f}x"
            if spell.get("base_multiplier", 0) > 0
            else "N/A"
        )
        cast_str = f"{spell.get('cast_time', 0):.2f}s" if spell.get("cast_time", 0) > 0 else "N/A"
        mana_str = f"{spell.get('mana_cost', 0)}" if spell.get("mana_cost", 0) > 0 else "N/A"

        result = f"**{spell.get('name', 'Unknown')}** ({spell.get('element', 'Physical')})\n"
        result += f"  Base Mult: {mult_str}, Cast: {cast_str}, Mana: {mana_str}\n"
        if spell.get("tags"):
            result += f"  Tags: {', '.join(spell['tags'][:4])}\n"
        result += "\n"
        return result

    # ============================================================================
    # TIER 2 DEBUGGING TOOL HANDLERS
    # ============================================================================

    async def _handle_trace_support_selection(self, args: dict) -> List[types.TextContent]:
        """Trace how support gems were selected"""
        try:
            spell_name = args.get("spell_name")
            max_spirit = args.get("max_spirit", 100)
            num_supports = args.get("num_supports", 5)
            goal = args.get("goal", "dps")

            if not spell_name:
                return [types.TextContent(type="text", text="Error: spell_name is required")]

            # Call with trace enabled
            result = self.gem_synergy_calculator.find_best_combinations(
                spell_name=spell_name,
                max_spirit=max_spirit,
                num_supports=num_supports,
                optimization_goal=goal,
                return_trace=True,
            )

            if isinstance(result, dict) and "trace" in result:
                trace = result["trace"]
                results = result["results"]

                response = f"# Support Selection Trace: {spell_name}\n\n"

                if not trace["spell_found"]:
                    response += f"X Spell '{spell_name}' not found in database\n"
                    return [types.TextContent(type="text", text=response)]

                response += f"**Optimization Goal**: {trace['optimization_goal']}\n\n"

                response += "## Step 1: Compatible Support Filtering\n"
                response += f"- Found {trace['compatible_supports_count']} compatible supports\n"
                if trace["compatible_supports"]:
                    response += f"- Examples: {', '.join(trace['compatible_supports'][:10])}\n"
                response += "\n"

                response += "## Step 2: Combination Generation\n"
                response += f"- Total combinations tested: {trace['total_combinations']:,}\n"
                response += f"- Valid combinations: {trace['valid_combinations']:,}\n"
                response += f"- Invalid combinations (incompatible gems): {trace['invalid_combinations']:,}\n"
                response += f"- Filtered by spirit budget: {trace['spirit_filtered']:,}\n"
                response += "\n"

                response += "## Step 3: Top Result\n"
                if results:
                    top = results[0]
                    response += f"- Best DPS: {trace.get('top_result_dps', top.total_dps):.1f}\n"
                    response += f"- Support combination: {', '.join(top.support_names)}\n"
                    response += f"- Spirit cost: {top.total_spirit}\n"
                else:
                    response += "- No valid combinations found\n"

                return [types.TextContent(type="text", text=response)]
            else:
                return [types.TextContent(type="text", text="Error: Trace data not available")]

        except Exception as e:
            logger.error(f"Error tracing support selection: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_trace_dps_calculation(self, args: dict) -> List[types.TextContent]:
        """Trace step-by-step DPS calculation"""
        try:
            spell_name = args.get("spell_name")
            support_gems = args.get("support_gems", [])
            character_mods = args.get("character_mods", {})
            max_spirit = args.get("max_spirit", 100)

            if not spell_name:
                return [types.TextContent(type="text", text="Error: spell_name is required")]

            if not support_gems:
                return [types.TextContent(type="text", text="Error: support_gems list is required")]

            # Get trace
            trace = self.gem_synergy_calculator.trace_dps_calculation(
                spell_name=spell_name,
                support_names=support_gems,
                character_mods=character_mods,
                max_spirit=max_spirit,
            )

            response = f"# DPS Calculation Trace: {spell_name}\n\n"

            if not trace["valid"]:
                response += "## Errors\n"
                for error in trace["errors"]:
                    response += f"- X {error}\n"
                return [types.TextContent(type="text", text=response)]

            # Spell info
            spell = trace["spell"]
            response += f"## Spell: {spell['name']}\n"
            response += f"- Base damage: {spell['base_damage_min']}-{spell['base_damage_max']}\n"
            response += f"- Cast time: {spell['cast_time']}s\n\n"

            # Supports
            response += "## Supports\n"
            for sup in trace["supports"]:
                response += f"- {sup['name']}: "
                if sup["more_damage"] != 0:
                    response += f"+{sup['more_damage']}% more damage "
                if sup["less_damage"] != 0:
                    response += f"{sup['less_damage']}% less damage "
                if sup["increased_damage"] != 0:
                    response += f"+{sup['increased_damage']}% increased damage "
                response += f"(Spirit: {sup['spirit_cost']})\n"
            response += "\n"

            # Spirit
            spirit = trace["spirit"]
            response += f"## Spirit Budget\n"
            response += f"- Total: {spirit['total']} / {spirit['available']}\n"
            if spirit["overflow"] > 0:
                response += f"- Warning: Overflow: {spirit['overflow']}\n"
            response += "\n"

            # Calculations
            calc = trace["calculations"]
            response += "## DPS Calculation Steps\n\n"

            response += f"**Step 1: Base Damage**\n"
            response += f"- Average: {calc['base_damage_avg']:.1f}\n\n"

            response += f"**Step 2: More Multipliers (multiplicative)**\n"
            for step in calc["more_multipliers"]:
                response += f"- {step['support_name']}: x{step['net_multiplier']:.3f} -> cumulative: x{step['cumulative']:.3f}\n"
            response += f"- Total more multiplier: x{calc['more_total']:.3f}\n\n"

            response += f"**Step 3: Increased Modifiers (additive)**\n"
            response += f"- Character increased: +{calc['increased_char']:.1f}%\n"
            response += f"- Support increased: +{calc['increased_supports']:.1f}%\n"
            response += f"- Total increased multiplier: x{calc['increased_total']:.3f}\n\n"

            response += f"**Step 4: Final Damage Per Cast**\n"
            response += f"- {calc['base_damage_avg']:.1f} x {calc['more_total']:.3f} x {calc['increased_total']:.3f} = {calc['final_damage_per_cast']:.1f}\n\n"

            response += f"**Step 5: DPS**\n"
            response += f"- {calc['final_damage_per_cast']:.1f} / {calc['cast_time']:.2f}s = **{calc['final_dps']:.1f} DPS**\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error tracing DPS calculation: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    @staticmethod
    def _coerce_optional_number(value) -> Optional[float]:
        """Null-tolerant numeric read (#153): explicit null, booleans, and
        non-numeric garbage all coerce to None instead of raising later."""
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _resolve_resistance(self, data: dict, element: str) -> Optional[float]:
        """Resolve a resistance under any of the three common shapes (#152):
        flat ``fire_resistance``, legacy ``fire_res``, nested
        ``resistances.fire``. Returns None when genuinely absent."""
        nested = data.get("resistances")
        candidates = (
            data.get(f"{element}_resistance"),
            data.get(f"{element}_res"),
            nested.get(element) if isinstance(nested, dict) else None,
        )
        for candidate in candidates:
            num = self._coerce_optional_number(candidate)
            if num is not None:
                return num
        return None

    async def _handle_validate_build_constraints(self, args: dict) -> List[types.TextContent]:
        """Comprehensive build validation.

        #152: resistances accepted under flat/legacy/nested key shapes;
        fields that are absent are reported as SKIPPED, never validated
        as silent zeros. #153: explicit nulls are treated as absent —
        no TypeError on comparisons.
        """
        try:
            character_data = args.get("character_data", {})

            if not character_data:
                return [types.TextContent(type="text", text="Error: character_data is required")]

            violations = []
            skipped = []

            # ---- Resistances (#152: three accepted shapes; absent = skipped) ----
            for element in ("fire", "cold", "lightning"):
                res_value = self._resolve_resistance(character_data, element)
                label = f"{element.title()} Res"
                if res_value is None:
                    skipped.append(f"{label} (not provided)")
                    continue
                if res_value < -60:
                    violations.append(
                        {
                            "severity": "CRITICAL",
                            "category": "Resistances",
                            "message": f"{label} is below minimum (-60%): {res_value:g}%",
                        }
                    )
                elif res_value < 75:
                    violations.append(
                        {
                            "severity": "HIGH",
                            "category": "Resistances",
                            "message": f"{label} is below cap (75%): {res_value:g}%",
                        }
                    )
                elif res_value > 90:
                    violations.append(
                        {
                            "severity": "MEDIUM",
                            "category": "Resistances",
                            "message": f"{label} exceeds hard cap (90%): {res_value:g}%",
                        }
                    )

            # Chaos res: floor check only — PoE2 builds commonly run low/negative
            # chaos res by choice; only the -60% floor is a hard violation.
            chaos_res = self._resolve_resistance(character_data, "chaos")
            if chaos_res is None:
                skipped.append("Chaos Res (not provided)")
            elif chaos_res < -60:
                violations.append(
                    {
                        "severity": "CRITICAL",
                        "category": "Resistances",
                        "message": f"Chaos Res is below minimum (-60%): {chaos_res:g}%",
                    }
                )

            # ---- Spirit (#153: null-tolerant) ----
            spirit = self._coerce_optional_number(character_data.get("spirit"))
            spirit_reserved = self._coerce_optional_number(character_data.get("spirit_reserved"))
            if spirit is None or spirit_reserved is None:
                skipped.append("Spirit allocation (spirit/spirit_reserved not provided)")
            elif spirit_reserved > spirit:
                violations.append(
                    {
                        "severity": "CRITICAL",
                        "category": "Spirit",
                        "message": f"Spirit overflow: {spirit_reserved:g} reserved > {spirit:g} available",
                    }
                )

            # NOTE: PoE2 uses Spirit system, not mana reservation
            # Mana reservation validation removed - it's a PoE1 mechanic

            # ---- Life/ES survivability baseline (absent = skipped, not zero) ----
            life = self._coerce_optional_number(character_data.get("life"))
            es = self._coerce_optional_number(character_data.get("energy_shield"))
            combined_direct = self._coerce_optional_number(character_data.get("life_plus_es"))
            level = self._coerce_optional_number(character_data.get("level")) or 1

            if life is None and es is None and combined_direct is None:
                skipped.append(
                    "Survivability baseline (life/energy_shield/life_plus_es not provided)"
                )
            else:
                combined = (
                    combined_direct if combined_direct is not None else (life or 0.0) + (es or 0.0)
                )
                expected_min_life = 300 + (level * 50)  # Rough guideline
                if combined < expected_min_life:
                    violations.append(
                        {
                            "severity": "HIGH",
                            "category": "Survivability",
                            "message": f"Combined Life+ES ({combined:g}) below recommended for level {level:g} ({expected_min_life:g})",
                        }
                    )

            # Format response
            response = "# Build Constraint Validation\n\n"

            if not violations:
                response += "✓ **All provided constraints satisfied**\n\n"
                response += "No issues detected in the checks that ran.\n"
            else:
                # Group by severity
                critical = [v for v in violations if v["severity"] == "CRITICAL"]
                high = [v for v in violations if v["severity"] == "HIGH"]
                medium = [v for v in violations if v["severity"] == "MEDIUM"]

                response += f"**Found {len(violations)} constraint violations**\n\n"

                if critical:
                    response += "## X CRITICAL Issues\n"
                    for v in critical:
                        response += f"- [{v['category']}] {v['message']}\n"
                    response += "\n"

                if high:
                    response += "## Warning HIGH Priority Issues\n"
                    for v in high:
                        response += f"- [{v['category']}] {v['message']}\n"
                    response += "\n"

                if medium:
                    response += "## Info MEDIUM Priority Issues\n"
                    for v in medium:
                        response += f"- [{v['category']}] {v['message']}\n"
                    response += "\n"

            # #152: never silently ignore fields — say exactly what was skipped
            if skipped:
                response += "## Skipped (not provided — NOT validated as zero)\n"
                for s in skipped:
                    response += f"- {s}\n"
                response += (
                    "\nAccepted field shapes: flat (`fire_resistance`), legacy "
                    "(`fire_res`), or nested (`resistances.fire`); `life` + "
                    "`energy_shield` or combined `life_plus_es`; `spirit` + "
                    "`spirit_reserved`; `level`. Explicit `null` = not provided.\n"
                )

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error validating build constraints: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_reconcile_defensive_stats(self, args: dict) -> List[types.TextContent]:
        """Reconcile local EHP/defense calcs against poe.ninja's defensiveStats
        oracle. The harness shipped in PR #144 but was never registered as an
        MCP tool (#154) — this is the wiring."""
        try:
            try:
                from .calculator.reconcile_poe_ninja import (
                    reconcile_defensive_stats,
                    format_report,
                )
            except ImportError:
                from src.calculator.reconcile_poe_ninja import (
                    reconcile_defensive_stats,
                    format_report,
                )

            char_model = args.get("char_model")
            if not char_model or not isinstance(char_model, dict):
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            "Error: char_model (object) is required — a poe.ninja "
                            "charModel dict or its defensiveStats sub-dict."
                        ),
                    )
                ]

            tolerance_pct = args.get("tolerance_pct") or None
            report = reconcile_defensive_stats(char_model, tolerance_pct=tolerance_pct)

            lines = ["# Defensive Stats Reconciliation", ""]
            lines.append("```")
            lines.append(format_report(report))
            lines.append("```")
            lines.append("")
            verdict = (
                "✓ All stats within tolerance"
                if report.all_within_tolerance
                else "✗ One or more stats OUTSIDE tolerance — local calculator drift suspected"
            )
            lines.append(f"**Verdict**: {verdict}")
            if report.skipped:
                lines.append(f"**Skipped** (absent from oracle): {', '.join(report.skipped)}")
            lines.append("")
            lines.append(
                "**Source**: src/calculator/reconcile_poe_ninja.py (#139 harness) — "
                "oracle values come from poe.ninja's own computed defensiveStats "
                "for this exact build (character data, policy-compliant)."
            )
            return [types.TextContent(type="text", text="\n".join(lines))]

        except Exception as e:
            logger.error(f"reconcile_defensive_stats error: {e}", exc_info=True)
            return [
                types.TextContent(type="text", text=f"Error in reconcile_defensive_stats: {str(e)}")
            ]

    async def _handle_analyze_passive_tree(self, args: dict) -> List[types.TextContent]:
        """Analyze passive tree allocation with pathfinding and recommendations"""
        try:
            if not self.passive_tree_resolver:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Passive tree resolver not initialized. PSG database may be missing.",
                    )
                ]

            node_ids = args.get("node_ids", [])
            target_notable = args.get("target_notable")
            find_recommendations = args.get("find_recommendations", True)

            if not node_ids:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: node_ids is required (list of allocated passive node IDs)",
                    )
                ]

            # Analyze the build
            analysis = self.passive_tree_resolver.analyze_build(
                node_ids, find_recommendations=find_recommendations
            )

            # Build response
            response = f"""# Passive Tree Analysis

## Summary
- **Total Nodes Allocated:** {analysis.total_nodes}
- **Starting Class:** {analysis.class_start or 'Unknown'}
- **Build Connected:** {'Yes' if analysis.is_connected else 'NO - Disconnected nodes detected!'}

## Keystones ({len(analysis.keystones)})
"""
            if analysis.keystones:
                for node in analysis.keystones:
                    response += f"### {node.name}\n"
                    for stat in node.stats:
                        response += f"- {stat}\n"
                    response += "\n"
            else:
                response += "*None allocated*\n"

            response += f"\n## Notables ({len(analysis.notables)})\n"
            if analysis.notables:
                for node in analysis.notables:
                    response += f"### {node.name}\n"
                    for stat in node.stats[:3]:  # Limit to first 3 stats
                        response += f"- {stat}\n"
                    response += "\n"
            else:
                response += "*None allocated*\n"

            response += f"\n## Small Nodes ({len(analysis.small_nodes)})\n"
            # Group small nodes by name
            small_by_name = {}
            for node in analysis.small_nodes:
                small_by_name.setdefault(node.name, []).append(node)

            for name, nodes in sorted(small_by_name.items(), key=lambda x: -len(x[1])):
                stat_preview = nodes[0].stats[0] if nodes[0].stats else "No stats"
                response += f"- {len(nodes)}x {name}: {stat_preview}\n"

            if analysis.jewel_sockets:
                response += f"\n## Jewel Sockets ({len(analysis.jewel_sockets)})\n"
                for node in analysis.jewel_sockets:
                    response += f"- Socket at ({node.x:.0f}, {node.y:.0f})\n"

            # Pathfinding to target notable
            if target_notable:
                response += f"\n## Path to '{target_notable}'\n"
                # Find the notable by name
                all_notables = self.passive_tree_resolver.get_all_notables()
                target_node = None
                for notable in all_notables:
                    if notable and notable.name.lower() == target_notable.lower():
                        target_node = notable
                        break

                if target_node:
                    # Find path from current build
                    best_path = None
                    best_start = None
                    for allocated in node_ids:
                        path = self.passive_tree_resolver.find_path(allocated, target_node.node_id)
                        if path and (best_path is None or path.distance < best_path.distance):
                            best_path = path
                            best_start = allocated

                    if best_path:
                        response += (
                            f"**Distance:** {best_path.distance} nodes from your current build\n\n"
                        )
                        response += "**Path:**\n"
                        for i, node in enumerate(best_path.nodes):
                            in_build = "*" if node.node_id in node_ids else " "
                            response += f"{in_build} {i+1}. {node.name} ({node.node_type})\n"

                        response += f"\n**{target_node.name} Stats:**\n"
                        for stat in target_node.stats:
                            response += f"- {stat}\n"
                    else:
                        response += f"*No path found to {target_notable}*\n"
                else:
                    response += f"*Notable '{target_notable}' not found in database*\n"

            # Recommendations
            if find_recommendations and analysis.nearest_notables:
                response += "\n## Nearest Unallocated Notables\n"
                for node, dist in analysis.nearest_notables[:5]:
                    response += f"\n### {node.name} ({dist} nodes away)\n"
                    for stat in node.stats[:2]:
                        response += f"- {stat}\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error analyzing passive tree: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_import_poe_ninja_url(self, args: dict) -> List[types.TextContent]:
        """Import and analyze a character from a poe.ninja URL"""
        try:
            from .api.poe_ninja_api import parse_poe_ninja_url
        except ImportError:
            from src.api.poe_ninja_api import parse_poe_ninja_url

        url = args.get("url", "")
        parsed = parse_poe_ninja_url(url)

        if not parsed:
            return [
                types.TextContent(
                    type="text",
                    text=f"""# URL Parse Error

Could not extract account and character from URL.

**URL provided:** `{url}`

**Expected formats:**
- `https://poe.ninja/poe2/profile/AccountName/LeagueSlug/character/CharacterName`
- `https://poe.ninja/poe2/profile/AccountName/character/CharacterName`
- `https://poe.ninja/poe2/builds/LeagueSlug/character/AccountName/CharacterName`
- `https://poe.ninja/poe2/builds/character/AccountName/CharacterName`

**Example:**
`https://poe.ninja/poe2/profile/Tomawar40-2671/runesofaldur/character/TomawarTheFourth`
""",
                )
            ]

        # Prefer the display name resolved from the URL's league slug; fall
        # back to the raw slug for leagues we don't know yet (the fetcher's
        # slug normalisation passes it through unchanged), then to the
        # current league.
        league = parsed["league"] or parsed["league_slug"] or "Runes of Aldur"

        return await self._handle_analyze_character(
            {"account": parsed["account"], "character": parsed["character"], "league": league}
        )

    # ============================================================================
    # PASSIVE TREE DATA HANDLERS (4 new handlers)
    # ============================================================================

    async def _handle_list_all_keystones(self, args: dict) -> List[types.TextContent]:
        """List all keystone passive nodes with pagination, detail levels, and format options."""
        try:
            from src.utils.response_formatter import (
                PaginationMeta,
                filter_fields,
                format_list_response,
                KEYSTONE_FIELDS,
                compact_json,
            )

            if not self.passive_tree_resolver:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Passive tree resolver not initialized. PSG database may be missing.",
                    )
                ]

            filter_stat = args.get("filter_stat", "").lower()
            sort_by = args.get("sort_by", "name")
            limit = args.get("limit", 20)
            offset = args.get("offset", 0)
            detail = args.get("detail", "standard")
            output_format = args.get("format", "markdown")

            # Get keystones from PassiveTreeResolver
            keystones = self.passive_tree_resolver.get_all_keystones()

            # Filter by stat text if provided
            if filter_stat:
                keystones = [
                    k
                    for k in keystones
                    if k and any(filter_stat in stat.lower() for stat in k.stats)
                ]

            # Sort
            if sort_by == "stat_count":
                keystones.sort(key=lambda k: -len(k.stats) if k else 0)
            else:
                keystones.sort(key=lambda k: k.name if k else "")

            # Convert to dicts for processing
            keystone_dicts = []
            for k in keystones:
                if not k:
                    continue
                keystone_dicts.append(
                    {
                        "name": k.name,
                        "node_id": getattr(k, "node_id", None),
                        "stats": list(k.stats) if k.stats else [],
                        "reminder_text": getattr(k, "reminder_text", ""),
                        "ascendancy_name": getattr(k, "ascendancy_name", ""),
                        "flavour_text": getattr(k, "flavour_text", ""),
                    }
                )

            # Pagination
            total = len(keystone_dicts)
            paginated = keystone_dicts[offset : offset + limit]
            meta = PaginationMeta(total=total, limit=limit, offset=offset, showing=len(paginated))

            # Filter by detail level
            filtered = [filter_fields(k, detail, KEYSTONE_FIELDS) for k in paginated]

            # Format response
            if output_format == "compact":
                response = compact_json({"results": filtered, "meta": meta.to_dict()})
            else:
                response = format_list_response(
                    filtered,
                    meta,
                    "Keystones",
                    item_formatter=lambda k: self._format_keystone_item(k, detail),
                )

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing keystones: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    def _format_keystone_item(self, keystone: dict, detail: str) -> str:
        """Format a single keystone for markdown output."""
        if detail == "summary":
            return f"- {keystone.get('name', 'Unknown')}\n"

        result = f"## {keystone.get('name', 'Unknown')}\n"
        if keystone.get("stats"):
            for stat in keystone["stats"]:
                result += f"- {stat}\n"
        result += "\n"
        return result

    async def _handle_inspect_keystone(self, args: dict) -> List[types.TextContent]:
        """Get complete details for a specific keystone. Accepts keystone_name or name (alias)."""
        try:
            if not self.passive_tree_resolver:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Passive tree resolver not initialized. PSG database may be missing.",
                    )
                ]

            keystone_name = (args.get("keystone_name") or args.get("name") or "").strip()

            if not keystone_name:
                return [
                    types.TextContent(
                        type="text", text="Error: keystone_name (or alias: name) is required"
                    )
                ]

            # Search for keystone by name (case-insensitive)
            keystones = self.passive_tree_resolver.get_all_keystones()
            found = None
            for k in keystones:
                if k and k.name.lower() == keystone_name.lower():
                    found = k
                    break

            # Try partial match if exact match not found
            if not found:
                for k in keystones:
                    if k and keystone_name.lower() in k.name.lower():
                        found = k
                        break

            if not found:
                # Did-you-mean suggestions (P2 / #115). Substring + fuzzy match
                # over all keystone names instead of returning a random sample.
                all_names = [k.name for k in keystones if k]
                suggestions = did_you_mean(keystone_name, all_names, k=5)
                if suggestions:
                    response = (
                        f"# Keystone Not Found\n\n"
                        f"No exact match for '{keystone_name}'. Did you mean:\n\n"
                    )
                    for name in suggestions:
                        response += f"- {name}\n"
                    response += (
                        f"\nCall ``inspect_keystone`` with one of these names " f"for full stats.\n"
                    )
                else:
                    response = (
                        f"# Keystone Not Found\n\n"
                        f"No keystone matching '{keystone_name}' and no close "
                        f"name candidates. ``list_all_keystones`` will enumerate "
                        f"every keystone in the local passive tree.\n"
                    )
                return [types.TextContent(type="text", text=response)]

            # Format detailed response
            response = f"# {found.name}\n\n"
            response += f"**Type:** Keystone\n"
            response += f"**Node ID:** {found.node_id}\n\n"
            response += "## Stats\n"
            for stat in found.stats:
                response += f"- {stat}\n"

            if found.connections:
                response += f"\n**Connected to {len(found.connections)} nodes**\n"

            response += "\n" + format_provenance(
                CANONICAL, source="data/game/passive_tree/tree.json"
            )
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting keystone: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_list_all_notables(self, args: dict) -> List[types.TextContent]:
        """List all notable passive nodes"""
        try:
            if not self.passive_tree_resolver:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Passive tree resolver not initialized. PSG database may be missing.",
                    )
                ]

            filter_stat = args.get("filter_stat", "").lower()
            limit = args.get("limit", 100)
            sort_by = args.get("sort_by", "name")

            # Get notables from PassiveTreeResolver
            notables = self.passive_tree_resolver.get_all_notables()

            # Filter by stat text if provided
            if filter_stat:
                notables = [
                    n
                    for n in notables
                    if n and any(filter_stat in stat.lower() for stat in n.stats)
                ]

            # Sort
            if sort_by == "stat_count":
                notables.sort(key=lambda n: -len(n.stats) if n else 0)
            else:  # name
                notables.sort(key=lambda n: n.name if n else "")

            # Limit results
            total_count = len(notables)
            notables = notables[:limit]

            # Format response
            response = f"# Notable Passives ({len(notables)} shown, {total_count} total)\n\n"

            for notable in notables:
                if not notable:
                    continue
                response += f"### {notable.name}\n"
                for stat in notable.stats[:3]:  # Limit stats shown
                    response += f"- {stat}\n"
                if len(notable.stats) > 3:
                    response += f"- *(+{len(notable.stats) - 3} more stats)*\n"
                response += "\n"

            if not notables:
                response += "*No notables found matching filter.*\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing notables: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_inspect_passive_node(self, args: dict) -> List[types.TextContent]:
        """Get complete details for any passive node"""
        try:
            if not self.passive_tree_resolver:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Passive tree resolver not initialized. PSG database may be missing.",
                    )
                ]

            node_name = args.get("node_name", "").strip()
            node_id = args.get("node_id")

            if not node_name and node_id is None:
                return [
                    types.TextContent(
                        type="text", text="Error: Either node_name or node_id is required"
                    )
                ]

            found = None

            # Search by ID first if provided
            if node_id is not None:
                found = self.passive_tree_resolver.resolve(node_id)

            # Search by name if not found by ID
            if not found and node_name:
                # Check keystones
                for k in self.passive_tree_resolver.get_all_keystones():
                    if k and k.name.lower() == node_name.lower():
                        found = k
                        break

                # Check notables
                if not found:
                    for n in self.passive_tree_resolver.get_all_notables():
                        if n and n.name.lower() == node_name.lower():
                            found = n
                            break

                # Try partial match
                if not found:
                    all_keystones = self.passive_tree_resolver.get_all_keystones()
                    all_notables = self.passive_tree_resolver.get_all_notables()
                    for node in all_keystones + all_notables:
                        if node and node_name.lower() in node.name.lower():
                            found = node
                            break

            if not found:
                return [
                    types.TextContent(
                        type="text",
                        text=f"# Node Not Found\n\nNo passive node matching '{node_name or node_id}'.\n\nTry using `list_all_keystones` or `list_all_notables` to find available nodes.",
                    )
                ]

            # Format detailed response
            response = f"# {found.name}\n\n"
            response += f"**Type:** {found.node_type.title()}\n"
            response += f"**Node ID:** {found.node_id}\n"

            if found.x != 0 or found.y != 0:
                response += f"**Position:** ({found.x:.0f}, {found.y:.0f})\n"

            response += "\n## Stats\n"
            if found.stats:
                for stat in found.stats:
                    response += f"- {stat}\n"
            else:
                response += "*No stats*\n"

            if found.connections:
                response += f"\n## Connections\n"
                response += f"Connected to {len(found.connections)} adjacent nodes.\n"

            response += "\n" + format_provenance(
                CANONICAL, source="data/game/passive_tree/tree.json"
            )
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting passive node: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # ============================================================================
    # BASE ITEM DATA HANDLERS (2 new handlers)
    # ============================================================================

    async def _handle_list_all_base_items(self, args: dict) -> List[types.TextContent]:
        """List all base item types"""
        try:
            filter_type = args.get("filter_type", "").lower()
            filter_name = args.get("filter_name", "").lower()
            limit = args.get("limit", 100)

            # Get base items from FreshDataProvider
            fresh_provider = get_fresh_data_provider()
            base_items = fresh_provider.get_all_base_items()

            items_list = []
            source_label = "data/game/ (FreshDataProvider)"

            if base_items:
                for item_id, item_data in base_items.items():
                    name = item_data.get("name", item_id)

                    # Apply filters
                    if (
                        filter_type
                        and filter_type not in item_id.lower()
                        and filter_type not in name.lower()
                    ):
                        continue
                    if filter_name and filter_name not in name.lower():
                        continue

                    items_list.append({"id": item_id, "name": name, "type": ""})
            else:
                # Fallback: the FreshDataProvider base-item set is empty when the
                # raw baseitemtypes.datc64 is absent and complete_models carries
                # no base items. Use the curated items DB (same source as
                # search_items) so the tool works instead of returning nothing.
                source_label = "items database (db_manager)"
                try:
                    db_items = await self.db_manager.get_all_items()
                except Exception as e:
                    db_items = []
                    logger.warning(f"Base-item DB fallback failed: {e}")
                for it in db_items:
                    name = (it.get("name") or "").strip()
                    itype = (it.get("type") or "").strip()
                    if not name:
                        continue
                    if (
                        filter_type
                        and filter_type not in itype.lower()
                        and filter_type not in name.lower()
                    ):
                        continue
                    if filter_name and filter_name not in name.lower():
                        continue
                    items_list.append({"id": name, "name": name, "type": itype})

            # Sort by name
            items_list.sort(key=lambda x: x["name"])

            # Limit
            total_count = len(items_list)
            items_list = items_list[:limit]

            # Format response
            response = f"# Base Item Types ({len(items_list)} shown, {total_count} total)\n\n"

            # Group by type prefix (metadata IDs) for better organization
            current_prefix = ""
            for item in items_list:
                parts = item["id"].split("/")
                prefix = parts[0] if len(parts) > 1 else ""
                if prefix != current_prefix:
                    current_prefix = prefix
                    if prefix:
                        response += (
                            f"\n## {prefix.replace('Metadata', '').replace('Items', '').strip()}\n"
                        )

                type_suffix = f" — *{item['type']}*" if item.get("type") else ""
                response += f"- **{item['name']}**{type_suffix} (`{item['id']}`)\n"

            if not items_list:
                response += "*No base items found matching filters.*\n"
            else:
                response += f"\n*Source: {source_label}*\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing base items: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_inspect_base_item(self, args: dict) -> List[types.TextContent]:
        """Get complete details for a specific base item"""
        try:
            item_name = args.get("item_name", "").strip()

            if not item_name:
                return [types.TextContent(type="text", text="Error: item_name is required")]

            # Get base items from FreshDataProvider
            fresh_provider = get_fresh_data_provider()
            base_items = fresh_provider.get_all_base_items()

            # Search by name (case-insensitive)
            found = None
            found_id = None
            item_name_lower = item_name.lower()

            for item_id, item_data in base_items.items():
                name = item_data.get("name", "")
                if name.lower() == item_name_lower or item_name_lower in item_id.lower():
                    found = item_data
                    found_id = item_id
                    break

            # Try partial match
            if not found:
                for item_id, item_data in base_items.items():
                    name = item_data.get("name", "")
                    if item_name_lower in name.lower():
                        found = item_data
                        found_id = item_id
                        break

            # Fallback: FreshDataProvider base-item set empty/missing the item.
            # Query the curated items DB (same source as search_items) so the
            # tool returns real data with correct display names.
            if not found:
                try:
                    db_matches = await self.db_manager.search_items(item_name)
                except Exception as e:
                    db_matches = []
                    logger.warning(f"Base-item DB fallback failed: {e}")
                if db_matches:
                    # Prefer an exact (case-insensitive) name match, else first.
                    best = next(
                        (m for m in db_matches if (m.get("name", "")).lower() == item_name_lower),
                        db_matches[0],
                    )
                    response = f"# {best.get('name', item_name)}\n\n"
                    for key, value in best.items():
                        if value in (None, "", 0):
                            continue
                        response += f"**{key.replace('_', ' ').title()}:** {value}\n"
                    response += "\n*Source: items database (db_manager)*\n"
                    return [types.TextContent(type="text", text=response)]

            if not found:
                return [
                    types.TextContent(
                        type="text",
                        text=f"# Base Item Not Found\n\nNo base item matching '{item_name}'.\n\nTry using `list_all_base_items` to see available items.",
                    )
                ]

            # Format detailed response
            response = f"# {found.get('name', found_id)}\n\n"
            response += f"**Internal ID:** `{found_id}`\n"

            # Show all available fields
            for key, value in found.items():
                if key not in ("name", "id", "row_index"):
                    response += f"**{key.replace('_', ' ').title()}:** {value}\n"

            response += "\n" + format_provenance(
                CANONICAL, source="data/game/base_items/ (via FreshDataProvider)"
            )
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting base item: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # ============================================================================
    # MOD DATA TOOLS HANDLERS
    # ============================================================================

    async def _handle_inspect_mod(self, args: dict) -> List[types.TextContent]:
        """Get complete details for a specific mod.

        Reads inline-resolved stat_id from data/game/mods/mods.json (#118).
        Stats list uses {stat_id, min_value, max_value, is_empty} per-entry;
        the older slot/stat_index/stat_value shape no longer exists.
        """
        try:
            mod_id = args.get("mod_id", "").strip()

            if not mod_id:
                return [types.TextContent(type="text", text="Error: mod_id is required")]

            # Prefer canonical data/game/mods/, fall back to legacy path.
            mods_file = _canonical_mods_path(DATA_DIR)
            if not mods_file.exists():
                mods_file = _legacy_mods_path(DATA_DIR)
            if not mods_file.exists():
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Mod database not found. Run `git pull` or scripts/extract_mods_datc64_v2.py.",
                    )
                ]

            with open(mods_file, "r", encoding="utf-8") as f:
                mods_data = json.load(f)

            # Search for mod by ID (case-insensitive)
            found = None
            mod_id_lower = mod_id.lower()

            for mod in mods_data.get("mods", []):
                if mod.get("mod_id", "").lower() == mod_id_lower:
                    found = mod
                    break

            # Try partial match if exact not found
            if not found:
                for mod in mods_data.get("mods", []):
                    if mod_id_lower in mod.get("mod_id", "").lower():
                        found = mod
                        break

            if not found:
                return [
                    types.TextContent(
                        type="text",
                        text=f"# Mod Not Found\n\nNo mod matching '{mod_id}'.\n\nTry using `list_all_mods` or `search_mods_by_stat` to find mods.",
                    )
                ]

            # Format detailed response
            response = f"# {found['mod_id']}\n\n"
            if found.get("display_name"):
                response += f"**Display Name:** *{found['display_name']}*\n"
            response += f"**Generation Type:** {found.get('generation_type_name', 'Unknown')}\n"
            response += f"**Level Requirement:** {found.get('level_requirement', 0)}\n"
            if "domain" in found:
                response += f"**Domain:** {found.get('domain', 0)}\n"
            response += "\n"

            # Show stats — inline-stat_id-aware (#118). Falls back to
            # stat_lookup only when an older record lacks inline stat_id.
            stat_lookup = _load_stat_lookup(DATA_DIR)
            resolved = _iter_resolved_stats(found, stat_lookup=stat_lookup)
            if resolved:
                response += "## Stats\n"
                for r in resolved:
                    src_marker = "" if r["from_inline"] else " *(via stat_lookup fallback)*"
                    if r["min_value"] == r["max_value"]:
                        response += f"- `{r['stat_id']}`: {r['min_value']}{src_marker}\n"
                    else:
                        response += f"- `{r['stat_id']}`: {r['min_value']} to {r['max_value']}{src_marker}\n"
                response += "\n"
            elif found.get("stats"):
                # All stats were is_empty — record is a structural/sentinel mod
                response += "## Stats\n*(no resolvable stats — all entries marked empty)*\n\n"

            response += "\n" + format_provenance(
                CANONICAL, source=f"{mods_file.relative_to(DATA_DIR.parent).as_posix()}"
            )
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting mod: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_list_all_mods(self, args: dict) -> List[types.TextContent]:
        """List all mods with filtering, pagination, detail levels, and format options."""
        try:
            from src.utils.response_formatter import (
                PaginationMeta,
                filter_fields,
                format_list_response,
                MOD_FIELDS,
                compact_json,
            )

            generation_type = args.get("generation_type")
            filter_stat = args.get("filter_stat", "").strip().lower()
            limit = args.get("limit", 20)
            offset = args.get("offset", 0)
            detail = args.get("detail", "standard")
            output_format = args.get("format", "markdown")

            # Prefer canonical data/game/mods/, fall back to legacy path (#118).
            mods_file = _canonical_mods_path(DATA_DIR)
            if not mods_file.exists():
                mods_file = _legacy_mods_path(DATA_DIR)
            if not mods_file.exists():
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Mod database not found. Run `git pull` or scripts/extract_mods_datc64_v2.py.",
                    )
                ]

            with open(mods_file, "r", encoding="utf-8") as f:
                mods_data = json.load(f)

            # Stat lookup is a no-op fallback for modern inline-stat_id dumps,
            # but keeps filter_stat working against older extractions too.
            stat_lookup = _load_stat_lookup(DATA_DIR) if filter_stat else None

            # Filter mods. filter_stat matches the mod_id OR any resolved
            # stat_id — previously it only checked mod_id, so a stat-id query
            # like "convert_to_fire" returned 0 results even though the mods
            # exist (field bug, 2026-06-16). Now it agrees with
            # find_stat_sources, which keys on stat_id.
            filtered_mods = []
            for mod in mods_data.get("mods", []):
                if generation_type and mod.get("generation_type_name") != generation_type:
                    continue
                if filter_stat:
                    if filter_stat in mod.get("mod_id", "").lower():
                        pass  # mod_id match
                    elif any(
                        filter_stat in r["stat_id"].lower()
                        for r in _iter_resolved_stats(mod, stat_lookup=stat_lookup)
                    ):
                        pass  # stat_id match
                    else:
                        continue
                filtered_mods.append(mod)

            # Sort by level requirement
            filtered_mods.sort(key=lambda m: m.get("level_requirement", 0))

            # Pagination
            total = len(filtered_mods)
            paginated = filtered_mods[offset : offset + limit]
            meta = PaginationMeta(total=total, limit=limit, offset=offset, showing=len(paginated))

            # Filter by detail level
            filtered = [filter_fields(m, detail, MOD_FIELDS) for m in paginated]

            # Format response
            if output_format == "compact":
                response = compact_json({"results": filtered, "meta": meta.to_dict()})
            else:
                response = format_list_response(
                    filtered,
                    meta,
                    "Mods",
                    item_formatter=lambda m: self._format_mod_item(m, detail),
                )

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing mods: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    def _format_mod_item(self, mod: dict, detail: str) -> str:
        """Format a single mod for markdown output.

        Value range is now read from the first non-empty entry in stats[]
        (the canonical schema), not top-level min_value/max_value (which
        don't exist in current extractions — #118).
        """
        if detail == "summary":
            return f"- {mod.get('mod_id', 'Unknown')} ({mod.get('generation_type_name', '?')})\n"

        result = f"### {mod.get('mod_id', 'Unknown')}"
        if mod.get("display_name"):
            result += f" — *{mod['display_name']}*"
        result += "\n"
        result += f"- Type: {mod.get('generation_type_name', 'Unknown')}\n"
        if detail in ("standard", "full"):
            result += f"- Level: {mod.get('level_requirement', 0)}\n"
            rng = _mod_value_range(mod)
            if rng is not None:
                if rng["min"] == rng["max"]:
                    result += f"- Value: {rng['min']}\n"
                else:
                    result += f"- Value: {rng['min']} to {rng['max']}\n"
            if detail == "full":
                # Surface stat_ids in full-detail mode (#118 inline-aware)
                resolved = _iter_resolved_stats(mod)
                if resolved:
                    stat_ids = [r["stat_id"] for r in resolved]
                    result += f"- Stats: {', '.join(stat_ids)}\n"
        result += "\n"
        return result

    async def _handle_search_mods_by_stat(self, args: dict) -> List[types.TextContent]:
        """Search for mods by stat keyword.

        Searches across THREE surfaces (any match qualifies):
        1. mod_id (engine identifier, e.g. 'LifeRegeneration1')
        2. display_name (in-game suffix/prefix, e.g. 'of Recovery')
        3. resolved stat_id strings via cross-reference (e.g. 'base_life_regeneration_rate_per_second')

        The query is also tokenized — multi-word inputs like 'life regeneration'
        match across word boundaries AND against snake_case stat IDs.

        Reads from data/game/mods/ + data/game/stats/ canonical layout (PR #69/#70).
        Falls back to legacy data/poe2_mods_extracted.json if data/game/ isn't
        populated yet (eg fresh checkout before first git pull of game data).
        """
        try:
            stat_keyword = (
                args.get("stat_keyword") or args.get("query") or args.get("keyword") or ""
            )
            stat_keyword = stat_keyword.strip().lower()
            generation_type = args.get("generation_type")
            limit = args.get("limit", 50)

            if not stat_keyword:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: stat_keyword (or alias: query, keyword) is required",
                    )
                ]

            # Tokenize the query — split on whitespace/underscore so 'life regeneration'
            # matches snake_case stat IDs like 'base_life_regeneration_rate_per_second'.
            tokens = [t for t in stat_keyword.replace("_", " ").split() if t]

            # Canonical data path first, legacy fallback
            game_mods_file = DATA_DIR / "game" / "mods" / "mods.json"
            legacy_mods_file = DATA_DIR / "poe2_mods_extracted.json"
            if game_mods_file.exists():
                mods_source = game_mods_file
            elif legacy_mods_file.exists():
                mods_source = legacy_mods_file
            else:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Mod database not found. Run `git pull` to fetch data/game/mods/, or run scripts/extract_mods_datc64_v2.py locally.",
                    )
                ]

            with open(mods_source, "r", encoding="utf-8") as f:
                mods_data = json.load(f)

            # Build stat_key -> stat_id lookup from data/game/stats/ when available.
            # This is what lets us search by stat description rather than just mod_id.
            stats_file = DATA_DIR / "game" / "stats" / "stats.json"
            stat_lookup: Dict[int, str] = {}
            if stats_file.exists():
                try:
                    with open(stats_file, "r", encoding="utf-8") as f:
                        stats_data = json.load(f)
                    for entry in stats_data.get("stats", []):
                        stat_lookup[entry["row_index"]] = entry["stat_id"]
                except Exception as e:
                    logger.warning(f"search_mods: failed to load stats lookup: {e}")

            def matches(text: str) -> bool:
                """True if every query token appears in the lowercased text."""
                if not text:
                    return False
                lc = text.lower()
                return all(t in lc for t in tokens)

            matching_mods = []
            for mod in mods_data.get("mods", []):
                # Apply generation type filter first (cheap)
                if generation_type and mod.get("generation_type_name") != generation_type:
                    continue

                mod_id = mod.get("mod_id", "")
                display_name = mod.get("display_name", "")

                # Surface 1: mod_id
                if matches(mod_id):
                    matching_mods.append(mod)
                    continue
                # Surface 2: display_name
                if display_name and matches(display_name):
                    matching_mods.append(mod)
                    continue
                # Surface 3: inline stat_ids (#118), with stat_lookup as fallback
                resolved = _iter_resolved_stats(mod, stat_lookup=stat_lookup or None)
                if resolved:
                    stat_ids_text = " ".join(r["stat_id"] for r in resolved)
                    if matches(stat_ids_text):
                        matching_mods.append(mod)
                        continue

            # Sort by level requirement
            matching_mods.sort(key=lambda m: m.get("level_requirement", 0))

            total_found = len(matching_mods)
            matching_mods = matching_mods[:limit]

            response = f"# Mods Search: '{stat_keyword}'\n\n"
            response += f"**Found:** {total_found} mods"
            if total_found > limit:
                response += f" (showing first {limit})"
            response += "\n"
            response += f"**Source:** `{mods_source.relative_to(DATA_DIR.parent)}`"
            if stat_lookup:
                response += f" + stat cross-reference ({len(stat_lookup):,} stat IDs)"
            response += "\n"

            if generation_type:
                response += f"**Filter:** {generation_type}\n"

            response += f"\n## Results\n\n"

            if not matching_mods:
                response += "*No mods found matching your search.*\n\n"
                response += "Tips:\n"
                response += "- Multi-word queries are tokenized — 'life regeneration' matches mods where both words appear\n"
                response += "- Searches mod_id, display_name, AND resolved stat IDs (when stats data is available)\n"
                response += "- Try shorter keywords: 'life', 'fire', 'resist', 'damage'\n"
            else:
                for mod in matching_mods:
                    response += f"### {mod['mod_id']}"
                    if mod.get("display_name"):
                        response += f" — *{mod['display_name']}*"
                    response += "\n"
                    response += f"- Type: {mod.get('generation_type_name', 'Unknown')}\n"
                    response += f"- Level: {mod.get('level_requirement', 0)}\n"
                    # Surface stat IDs — inline first, stat_lookup fallback (#118)
                    resolved = _iter_resolved_stats(mod, stat_lookup=stat_lookup or None)
                    if resolved:
                        sids = [r["stat_id"] for r in resolved]
                        response += f"- Stats: {', '.join(sids)}\n"
                    response += "\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error searching mods by stat: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_mod_tiers(self, args: dict) -> List[types.TextContent]:
        """Get all tiers of a mod family.

        Reads inline-resolved stat values from data/game/mods/mods.json (#118).
        """
        try:
            mod_base = args.get("mod_base", "").strip()

            if not mod_base:
                return [types.TextContent(type="text", text="Error: mod_base is required")]

            # Prefer canonical data/game/mods/, fall back to legacy path (#118).
            mods_file = _canonical_mods_path(DATA_DIR)
            if not mods_file.exists():
                mods_file = _legacy_mods_path(DATA_DIR)
            if not mods_file.exists():
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Mod database not found. Run `git pull` or scripts/extract_mods_datc64_v2.py.",
                    )
                ]

            with open(mods_file, "r", encoding="utf-8") as f:
                mods_data = json.load(f)

            # Find all mods matching the base name
            tier_mods = []
            mod_base_lower = mod_base.lower()

            for mod in mods_data.get("mods", []):
                mod_id = mod.get("mod_id", "")
                mod_id_lower = mod_id.lower()

                # Check if this mod belongs to the family
                # Match pattern: base name followed by optional number
                if mod_id_lower.startswith(mod_base_lower):
                    # Extract the part after base name
                    suffix = mod_id[len(mod_base) :]
                    # Check if it's empty or a number
                    if not suffix or suffix.isdigit():
                        tier_mods.append(mod)

            if not tier_mods:
                return [
                    types.TextContent(
                        type="text",
                        text=f"# No Mod Tiers Found\n\nNo mods found with base name '{mod_base}'.\n\nTry using `list_all_mods` to browse available mods.",
                    )
                ]

            # Sort by level requirement (which usually correlates with tier)
            tier_mods.sort(key=lambda m: m.get("level_requirement", 0))

            # Format response
            response = f"# Mod Tiers: {mod_base}\n\n"
            response += f"**Total tiers found:** {len(tier_mods)}\n"

            # Show generation type if consistent
            gen_types = set(m.get("generation_type_name") for m in tier_mods)
            if len(gen_types) == 1:
                response += f"**Generation Type:** {gen_types.pop()}\n"

            response += "\n## Tier Progression\n\n"

            for i, mod in enumerate(tier_mods, 1):
                tier_label = f"T{i}"
                response += f"### {tier_label}: {mod['mod_id']}"
                if mod.get("display_name"):
                    response += f" — *{mod['display_name']}*"
                response += "\n"
                response += f"- Level Requirement: {mod.get('level_requirement', 0)}\n"
                # Value range from canonical inline schema (#118)
                rng = _mod_value_range(mod)
                if rng is not None:
                    if rng["min"] == rng["max"]:
                        response += f"- Value: {rng['min']}\n"
                    else:
                        response += f"- Value: {rng['min']} to {rng['max']}\n"
                response += f"- Type: {mod.get('generation_type_name', 'Unknown')}\n\n"

            response += "\n" + format_provenance(
                CANONICAL,
                source=f"{mods_file.relative_to(DATA_DIR.parent).as_posix()}",
            )
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error getting mod tiers: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # ============================================================================
    # TIER 2 MOD VALIDATION TOOL HANDLERS
    # ============================================================================

    async def _handle_validate_item_mods(self, args: dict) -> List[types.TextContent]:
        """Validate if a set of mods can legally exist on an item"""
        try:
            mod_ids = args.get("mod_ids", [])
            item_level = args.get("item_level", 83)

            if not mod_ids:
                return [types.TextContent(type="text", text="Error: mod_ids list is required")]

            # Load mods from JSON file
            mods_file = DATA_DIR / "poe2_mods_extracted.json"
            if not mods_file.exists():
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Mod database not found. File poe2_mods_extracted.json is missing.",
                    )
                ]

            with open(mods_file, "r", encoding="utf-8") as f:
                mods_data = json.load(f)

            # Create a lookup dictionary
            mods_by_id = {m["mod_id"]: m for m in mods_data.get("mods", [])}

            # Validate mods and collect info
            errors = []
            warnings = []
            conflicts = []
            found_mods = []
            not_found = []

            for mod_id in mod_ids:
                if mod_id in mods_by_id:
                    found_mods.append(mods_by_id[mod_id])
                else:
                    not_found.append(mod_id)
                    errors.append(f"Mod not found: {mod_id}")

            if not_found:
                # Still continue validation with found mods
                pass

            # Check mod family conflicts (can't have 2 tiers of same mod family)
            families_seen = {}
            for mod in found_mods:
                mod_id = mod.get("mod_id", "")
                # Extract family by removing trailing digits
                family = mod_id.rstrip("0123456789")
                if not family:
                    family = mod_id

                if family in families_seen:
                    conflict_mod = families_seen[family]
                    conflicts.append((conflict_mod, mod_id))
                    errors.append(
                        f"Mod family conflict: {conflict_mod} and {mod_id} are both from '{family}' family"
                    )
                else:
                    families_seen[family] = mod_id

            # Check prefix/suffix counts
            prefix_count = sum(1 for m in found_mods if m.get("generation_type_name") == "PREFIX")
            suffix_count = sum(1 for m in found_mods if m.get("generation_type_name") == "SUFFIX")
            implicit_count = sum(
                1 for m in found_mods if m.get("generation_type_name") == "IMPLICIT"
            )
            corrupted_count = sum(
                1 for m in found_mods if m.get("generation_type_name") == "CORRUPTED"
            )

            MAX_PREFIXES = 3
            MAX_SUFFIXES = 3
            MAX_IMPLICITS = 2

            if prefix_count > MAX_PREFIXES:
                errors.append(f"Too many prefixes: {prefix_count} (max {MAX_PREFIXES})")

            if suffix_count > MAX_SUFFIXES:
                errors.append(f"Too many suffixes: {suffix_count} (max {MAX_SUFFIXES})")

            if implicit_count > MAX_IMPLICITS:
                warnings.append(
                    f"High implicit count: {implicit_count} (typical max {MAX_IMPLICITS})"
                )

            # Check level requirements
            for mod in found_mods:
                mod_level = mod.get("level_requirement", 0)
                if mod_level > item_level:
                    warnings.append(
                        f"{mod.get('mod_id')} requires ilvl {mod_level}, item is ilvl {item_level}"
                    )

            # Determine overall validity
            is_valid = len(errors) == 0

            # Format response
            response = "# Mod Validation Result\n\n"
            response += f"**Valid:** {'YES' if is_valid else 'NO'}\n"
            response += f"**Item Level:** {item_level}\n\n"

            response += "## Mod Counts\n"
            response += f"- Prefixes: {prefix_count}/{MAX_PREFIXES}\n"
            response += f"- Suffixes: {suffix_count}/{MAX_SUFFIXES}\n"
            if implicit_count > 0:
                response += f"- Implicits: {implicit_count}\n"
            if corrupted_count > 0:
                response += f"- Corrupted: {corrupted_count}\n"
            response += "\n"

            if errors:
                response += "## ERRORS\n"
                for error in errors:
                    response += f"- {error}\n"
                response += "\n"

            if warnings:
                response += "## Warnings\n"
                for warning in warnings:
                    response += f"- {warning}\n"
                response += "\n"

            if conflicts:
                response += "## Conflicts\n"
                for mod1, mod2 in conflicts:
                    response += f"- {mod1} conflicts with {mod2}\n"
                response += "\n"

            if found_mods:
                response += "## Validated Mods\n"
                for mod in found_mods:
                    response += f"- {mod.get('mod_id')}: {mod.get('generation_type_name')} (Level {mod.get('level_requirement', 0)})\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error validating item mods: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_available_mods(self, args: dict) -> List[types.TextContent]:
        """Get all mods that could roll on an item by generation type.

        Optional `item_class` (e.g. "Wand", "ring", "body_armour") filters to
        mods whose SpawnTags include that slot — the Bug 3 fix. Backed by
        data/game/mods/spawn_tags.json (membership-based eligibility).
        """
        try:
            generation_type = args.get("generation_type", "").upper()
            max_level = args.get("max_level", 100)
            limit = min(args.get("limit", 100), 200)  # Cap at 200
            item_class_raw = (args.get("item_class") or "").strip()

            if generation_type not in ["PREFIX", "SUFFIX"]:
                return [
                    types.TextContent(
                        type="text", text="Error: generation_type must be 'PREFIX' or 'SUFFIX'"
                    )
                ]

            # Resolve the optional item-class filter against the SpawnTags map.
            spawn_tags = {}
            item_class = ""
            if item_class_raw:
                spawn_tags = _load_spawn_tags(DATA_DIR)
                if not spawn_tags:
                    return [
                        types.TextContent(
                            type="text",
                            text=(
                                "Error: item_class filtering needs data/game/mods/"
                                "spawn_tags.json, which is absent. Update to a data "
                                "release that includes it (or run "
                                "scripts/extract_mod_spawn_tags.py)."
                            ),
                        )
                    ]
                item_class = _normalize_item_class(item_class_raw)
                valid = set(_available_spawn_tags(DATA_DIR))
                if item_class not in valid:
                    # Suggest the equipment-relevant tags rather than the full set.
                    equip = [
                        t
                        for t in sorted(valid)
                        if any(
                            k in t
                            for k in (
                                "wand",
                                "sceptre",
                                "staff",
                                "bow",
                                "mace",
                                "axe",
                                "sword",
                                "dagger",
                                "claw",
                                "spear",
                                "flail",
                                "crossbow",
                                "quiver",
                                "focus",
                                "shield",
                                "ring",
                                "amulet",
                                "belt",
                                "helmet",
                                "glove",
                                "boot",
                                "armour",
                            )
                        )
                    ]
                    return [
                        types.TextContent(
                            type="text",
                            text=(
                                f"Error: unknown item_class '{item_class_raw}'. "
                                f"Try one of these spawn tags:\n" + ", ".join(equip)
                            ),
                        )
                    ]

            # Load mods from JSON file
            mods_file = DATA_DIR / "poe2_mods_extracted.json"
            if not mods_file.exists():
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Mod database not found. File poe2_mods_extracted.json is missing.",
                    )
                ]

            with open(mods_file, "r", encoding="utf-8") as f:
                mods_data = json.load(f)

            # Filter mods
            available_mods = []
            for mod in mods_data.get("mods", []):
                if mod.get("generation_type_name") != generation_type:
                    continue
                if mod.get("level_requirement", 0) > max_level:
                    continue
                if item_class:
                    tags = spawn_tags.get(mod.get("mod_id", ""))
                    if not tags or item_class not in tags:
                        continue
                available_mods.append(mod)

            # Sort by level requirement
            available_mods.sort(key=lambda m: m.get("level_requirement", 0))

            # Group by mod family for better presentation
            families = {}
            for mod in available_mods:
                mod_id = mod.get("mod_id", "")
                family = mod_id.rstrip("0123456789")
                if not family:
                    family = mod_id

                if family not in families:
                    families[family] = []
                families[family].append(mod)

            # Apply limit to families
            limited_families = list(families.items())[:limit]

            # Format response
            response = f"# Available {generation_type} Mods\n\n"
            if item_class:
                response += f"**Item class filter:** `{item_class}` (SpawnTags membership)\n"
            response += f"**Total families:** {len(families)}\n"
            response += f"**Total mods:** {len(available_mods)}\n"
            response += f"**Max level filter:** {max_level}\n\n"
            if item_class and not available_mods:
                response += (
                    f"*No {generation_type} mods roll on `{item_class}`. "
                    "Check the tag spelling, or this slot may only take "
                    "implicits/uniques for this stat.*\n"
                )

            response += "## Mod Families\n\n"

            for family, mods in limited_families:
                highest_tier = mods[-1]  # Last one has highest level
                response += f"### {family}\n"
                response += f"- Tiers: {len(mods)}\n"
                response += f"- Level range: {mods[0].get('level_requirement', 0)} - {highest_tier.get('level_requirement', 0)}\n"
                response += f"- Best tier: {highest_tier.get('mod_id')}\n\n"

            if len(families) > limit:
                response += f"\n*Showing {limit} of {len(families)} families. Increase limit to see more.*\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error getting available mods: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_live_game_state(self, args: dict) -> List[types.TextContent]:
        """Read current in-game state from the local PoE2 client log (Client.txt).

        Local file read only — no API. Surfaces live character/level/area so the
        AI knows who/where the player is without poe.ninja (broken for 0.5).
        """
        try:
            include_events = args.get("include_recent_events", False)
            event_limit = min(int(args.get("event_limit", 25)), 200)
            log_path = args.get("log_path")

            # Honor an explicit path override; otherwise use the shared reader
            # built at init (falls back to a fresh one if init was skipped).
            reader = self.client_log_reader
            if log_path or reader is None:
                reader = ClientLogReader(log_path=log_path)

            if not reader.is_available():
                response = (
                    "# Live Game State\n\n"
                    ":warning: **Client.txt not found.** The game log could not be "
                    "located at any known install path.\n\n"
                    "- The game may not be installed, or is in a custom location.\n"
                    "- Pass `log_path` pointing at `...\\Path of Exile 2\\logs\\Client.txt`.\n"
                )
                return [types.TextContent(type="text", text=response)]

            state = reader.get_current_state()

            response = "# Live Game State\n\n"
            response += "*Source: local PoE2 client log (Client.txt) — no network*\n\n"
            response += f"- **Character:** {state.get('character') or '(unknown)'}\n"
            response += (
                f"- **Class / Ascendancy:** {state.get('ascendancy_or_class') or '(unknown)'}\n"
            )
            response += f"- **Level:** {state.get('level') if state.get('level') is not None else '(unknown)'}\n"

            area_code = state.get("area_code")
            if area_code:
                response += (
                    f"- **Current area:** `{area_code}` "
                    f"(monster level {state.get('area_level')}, seed {state.get('area_seed')})\n"
                )
                response += "  *(area code is the game's internal id, not the display name)*\n"
            else:
                response += "- **Current area:** (unknown)\n"

            if state.get("instance_server"):
                response += f"- **Instance server:** {state['instance_server']}\n"
            if state.get("afk") is not None:
                response += f"- **AFK:** {'ON' if state['afk'] else 'OFF'}\n"
            response += f"- **Deaths (recent window):** {state.get('deaths_in_window', 0)}\n"
            response += f"- **Last log event:** {state.get('last_event_time') or '(none)'}\n"
            response += f"- **Events scanned:** {state.get('event_count', 0)}\n"
            response += f"\n*Log: `{state.get('log_path')}`*\n"

            if include_events:
                events = reader.get_recent_events(limit=event_limit)
                response += f"\n## Recent events ({len(events)})\n\n"
                for ev in events:
                    parts = [f"`{ev['timestamp']}`", f"**{ev['kind']}**"]
                    detail = {
                        k: v for k, v in ev.items() if k not in ("timestamp", "kind", "log_level")
                    }
                    parts.append(", ".join(f"{k}={v}" for k, v in detail.items()))
                    response += "- " + " — ".join(p for p in parts if p) + "\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error reading live game state: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_game_config(self, args: dict) -> List[types.TextContent]:
        """Read the local PoE2 client config INI (poe2_production_Config.ini).

        Local file read only. Provides playstyle/context (input mode, current
        act, display, GPU). account_name is intentionally surfaced even though
        Steam auth usually leaves it blank.
        """
        try:
            full = args.get("full", False)
            config_path = args.get("config_path")

            reader = self.game_config_reader
            if config_path or reader is None:
                reader = GameConfigReader(config_path=config_path)

            if not reader.is_available():
                response = (
                    "# Game Config\n\n"
                    ":warning: **poe2_production_Config.ini not found** at any known "
                    "path.\n\n- Pass `config_path` to "
                    "`...\\Documents\\My Games\\Path of Exile 2\\poe2_production_Config.ini`.\n"
                )
                return [types.TextContent(type="text", text=response)]

            if full:
                raw = reader.read_all()
                response = "# Game Config (full)\n\n"
                response += f"*Source: `{reader.config_path}`*\n\n"
                for section, kv in raw.items():
                    response += f"## [{section}]\n\n"
                    for k, v in kv.items():
                        response += f"- `{k}` = {v}\n"
                    response += "\n"
                return [types.TextContent(type="text", text=response)]

            s = reader.get_summary()
            response = "# Game Config\n\n"
            response += (
                "*Source: local PoE2 client config (poe2_production_Config.ini) — no network*\n\n"
            )
            response += f"- **Account name:** {s.get('account_name') or '(empty)'}\n"
            if s.get("account_name_note"):
                response += f"  *({s['account_name_note']})*\n"
            response += f"- **Gateway:** {s.get('gateway') or '(unknown)'}\n"
            response += f"- **Input mode:** {s.get('input_mode') or '(unknown)'} *(wasd vs click-to-move)*\n"
            response += f"- **Current act:** {s.get('current_act_environment') or '?'}"
            if s.get("current_act_hint"):
                response += f" *({s['current_act_hint']})*"
            response += "\n"
            response += f"- **Resolution:** {s.get('resolution') or '(unknown)'}\n"
            response += f"- **Renderer:** {s.get('renderer') or '(unknown)'}\n"
            response += f"- **Upscale:** {s.get('upscale') or '(none)'}\n"
            fps_cap = s.get("framerate_limit")
            fps_on = s.get("framerate_limit_enabled")
            response += f"- **Framerate cap:** {fps_cap} ({'enabled' if fps_on == 'true' else 'disabled'})\n"
            response += f"- **GPU:** {s.get('gpu') or '(unknown)'}\n"
            response += f"\n*Config: `{s.get('config_path')}`*\n"
            response += (
                "\n*Tip: use `get_live_game_state` for live character identity (Client.txt).*\n"
            )

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error reading game config: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # ============================================================================
    # FORMATTING METHODS
    # ============================================================================

    def _format_gear_stats(self, gear: dict) -> str:
        """Format gear stats for display"""
        if not gear:
            return "*No gear data provided*"

        result = ""
        for key, value in gear.items():
            result += f"- {key}: {value}\n"
        return result

    # Formatting Methods

    def _format_character_analysis(
        self, character_data: dict, analysis: dict, recommendations: str, passive_analysis=None
    ) -> str:
        """Format character analysis response"""
        # Format ascendancy display - show "Not Selected" if None
        ascendancy = character_data.get("ascendancy")
        ascendancy_display = ascendancy if ascendancy else "Not Selected"

        response = f"""# Character Analysis: {character_data.get('name', 'Unknown')}

## Basic Info
- Class: {character_data.get('class', 'Unknown')}
- Level: {character_data.get('level', '?')}
- Ascendancy: {ascendancy_display}

## Build Score
- Overall Score: {analysis.get('overall_score', 0):.2f}/1.00
- Build Tier: {analysis.get('tier', 'Unknown')}

## Strengths
{self._format_list(analysis.get('strengths', []))}

## Weaknesses
{self._format_list(analysis.get('weaknesses', []))}

## Key Metrics
- DPS: {analysis.get('dps', 0):,.0f}
- Effective HP: {analysis.get('ehp', 0):,.0f}
- Defense Rating: {analysis.get('defense_rating', 0):.2f}/1.00
{self._format_resistances(analysis.get('resistances', {}))}"""

        # Add passive tree analysis if available
        if passive_analysis:
            response += f"""
## Passive Tree ({passive_analysis.total_nodes} nodes allocated)
"""
            if passive_analysis.class_start:
                response += f"- Starting Class: {passive_analysis.class_start}\n"

            if passive_analysis.keystones:
                response += f"- Keystones ({len(passive_analysis.keystones)}): "
                response += ", ".join(n.name for n in passive_analysis.keystones) + "\n"

            if passive_analysis.notables:
                response += f"- Notables ({len(passive_analysis.notables)}): "
                response += ", ".join(n.name for n in passive_analysis.notables) + "\n"

            if passive_analysis.jewel_sockets:
                response += f"- Jewel Sockets: {len(passive_analysis.jewel_sockets)}\n"

            response += f"- Small Nodes: {len(passive_analysis.small_nodes)}\n"

            if passive_analysis.tree_region:
                response += f"- Tree Region: {passive_analysis.tree_region}\n"

            if not passive_analysis.is_connected:
                response += "- WARNING: Build has disconnected nodes!\n"

            if passive_analysis.connectivity_note:
                response += f"- {passive_analysis.connectivity_note}\n"

            # Show nearest unallocated notables
            if passive_analysis.nearest_notables:
                response += "\n### Nearest Unallocated Notables\n"
                for node, dist in passive_analysis.nearest_notables[:5]:
                    response += f"- {node.name} ({dist} nodes away)\n"
                    if node.stats:
                        response += f"  - {node.stats[0]}\n"

        # #149: surface the RAW allocated node-id array so downstream tools
        # (analyze_passive_tree) can be chained on real characters instead of
        # the caller having to fabricate 80+ integers. Rendered even when the
        # summary analysis above is unavailable — the ids come straight from
        # the fetched character data.
        raw_tree = character_data.get("passive_tree")
        raw_node_ids = (
            raw_tree.get("allocated_nodes") if isinstance(raw_tree, dict) else raw_tree
        ) or []
        node_ids = sorted(
            int(n)
            for n in raw_node_ids
            if isinstance(n, int) or (isinstance(n, str) and n.isdigit())
        )
        if node_ids:
            response += f"\n### Passive Node IDs ({len(node_ids)})\n"
            response += f"`passive_node_ids`: {node_ids}\n"
            if self.passive_tree_resolver:
                unresolved = [n for n in node_ids if self.passive_tree_resolver.resolve(n) is None]
                response += f"`unresolved_node_ids` (absent from local tree): {unresolved}\n"
            response += "Feed `passive_node_ids` directly into `analyze_passive_tree`.\n"

        # Add skill gems section
        skills_section = self._format_skills_section(character_data)
        if skills_section:
            response += skills_section

        # Add gear section
        gear_section = self._format_equipment_section(character_data)
        if gear_section:
            response += gear_section

        # Add charms section (PoE2 triggered items)
        charms_section = self._format_charms_section(character_data)
        if charms_section:
            response += charms_section

        if recommendations:
            response += f"\n## AI Recommendations\n{recommendations}"

        return response

    @staticmethod
    def _format_item_entry(item: dict, slot_label: str) -> str:
        """Render one equipment item as a markdown block (header + key mods)."""
        name = item.get("name", "") or item.get("type_line", "Unknown Item")
        type_line = item.get("type_line", "")
        rarity = item.get("rarity", "Normal")
        corrupted = " (Corrupted)" if item.get("corrupted") else ""
        if isinstance(rarity, int):
            rarity = {0: "Normal", 1: "Magic", 2: "Rare", 3: "Unique"}.get(rarity, "Unknown")

        out = f"\n### {slot_label}: {name if rarity == 'Unique' else (name or type_line)}{corrupted}\n"
        if type_line and type_line != name:
            out += f"*{type_line}*\n"

        # mods shape varies: poe.ninja route = {implicit,explicit}; PoB route = flat list
        mods = item.get("mods") or {}
        max_mods = 5
        if isinstance(mods, dict):
            shown = 0
            for m in (mods.get("implicit") or [])[:2]:
                out += f"- {m} (implicit)\n"
                shown += 1
            for m in (mods.get("explicit") or [])[: max_mods - shown]:
                out += f"- {m}\n"
        elif isinstance(mods, list):
            for m in mods[:max_mods]:
                out += f"- {m}\n"
        return out

    def _format_equipment_section(self, character_data: dict) -> str:
        """Format equipped gear from character data.

        Weapon-set aware (#183 importer tag): items on weapon set 2
        ("Weapon 1/2 Swap") are rendered in a SEPARATE 'Weapon Set 2
        (swap)' section, never flattened into the active gear — because
        only one weapon set is active at a time, so a swap-set weapon's
        stats do NOT apply alongside set-1 gear. Conflating them is the
        bug that produced wrong build analysis (a swap staff's chaos read
        as if active during set-1 casting).
        """
        items = character_data.get("items", [])
        if not items:
            return ""

        response = "\n## Equipment\n"

        # Partition swap-set (weapon_set == 2) weapons out of the active gear.
        swap_items = [i for i in items if i.get("weapon_set") == 2]
        active_items = [i for i in items if i.get("weapon_set") != 2]
        if swap_items:
            response += (
                "*This build uses weapon swap. Only one weapon set is active at "
                "a time - Weapon Set 2 stats below do NOT apply while Set 1 is "
                "equipped.*\n"
            )

        # Define slot order for organized display
        slot_order = [
            "Weapon",
            "Offhand",
            "Helm",
            "BodyArmour",
            "Gloves",
            "Boots",
            "Belt",
            "Amulet",
            "Ring",
            "Ring2",
            "Flask",
            "Charm",
        ]

        # Group items by slot
        by_slot = {}
        for item in active_items:
            # `or` (not .get default): cached/older records carry an explicit
            # slot: null, which .get's default does not cover
            slot = item.get("slot") or "Unknown"
            # Normalize slot names
            if "weapon" in slot.lower():
                slot = "Weapon"
            elif "offhand" in slot.lower() or "shield" in slot.lower():
                slot = "Offhand"
            elif "helm" in slot.lower():
                slot = "Helm"
            elif "body" in slot.lower() or "armour" in slot.lower():
                slot = "BodyArmour"
            elif "glove" in slot.lower():
                slot = "Gloves"
            elif "boot" in slot.lower():
                slot = "Boots"
            elif "belt" in slot.lower():
                slot = "Belt"
            elif "amulet" in slot.lower():
                slot = "Amulet"
            elif "ring" in slot.lower():
                if "Ring" in by_slot:
                    slot = "Ring2"
                else:
                    slot = "Ring"
            elif "flask" in slot.lower():
                slot = "Flask"
            elif "charm" in slot.lower():
                slot = "Charm"

            by_slot.setdefault(slot, []).append(item)

        # Display items in order
        for slot in slot_order:
            if slot not in by_slot:
                continue
            for item in by_slot[slot]:
                response += self._format_item_entry(item, slot)

        # Show any remaining slots not in order
        for slot, slot_items in by_slot.items():
            if slot not in slot_order:
                for item in slot_items:
                    name = item.get("name", "") or item.get("type_line", "Unknown")
                    response += f"\n### {slot}: {name}\n"

        # Weapon Set 2 (swap) — rendered separately so its stats are never
        # read as active alongside the set-1 gear above.
        if swap_items:
            response += "\n## Weapon Set 2 (swap)\n"
            for item in swap_items:
                slot = item.get("slot") or "Weapon (swap)"
                response += self._format_item_entry(item, slot)

        return response

    def _format_charms_section(self, character_data: dict) -> str:
        """Format equipped charms from character data (PoE2 triggered items)"""
        charms = character_data.get("charms", [])
        if not charms:
            return ""

        response = "\n## Charms\n"
        response += "*Charms are triggered items that activate on specific conditions*\n"

        for i, charm in enumerate(charms, 1):
            name = charm.get("name", "") or charm.get("type_line", "Unknown Charm")
            type_line = charm.get("type_line", "")
            rarity = charm.get("rarity", 0)
            corrupted = " (Corrupted)" if charm.get("corrupted") else ""

            # Format rarity display
            if isinstance(rarity, int):
                rarity_map = {0: "Normal", 1: "Magic", 2: "Rare", 3: "Unique"}
                rarity_str = rarity_map.get(rarity, "Unknown")
            else:
                rarity_str = str(rarity)

            # Build charm header
            if rarity_str == "Unique":
                response += f"\n### Charm {i}: {name}{corrupted}\n"
            else:
                response += f"\n### Charm {i}: {name or type_line}{corrupted}\n"

            if type_line and type_line != name:
                response += f"*{type_line}*\n"

            # Show mods
            mods = charm.get("mods", {})
            if isinstance(mods, dict):
                if mods.get("implicit"):
                    for mod in mods["implicit"]:
                        response += f"- {mod} (implicit)\n"
                if mods.get("explicit"):
                    for mod in mods["explicit"]:
                        response += f"- {mod}\n"
            elif isinstance(mods, list):
                # Handle case where mods is just a list
                for mod in mods:
                    response += f"- {mod}\n"

        return response

    def _format_gear_recommendations(self, recommendations: dict) -> str:
        """Format gear recommendations"""
        response = "# Gear Optimization Recommendations\n\n"

        priority_upgrades = recommendations.get("priority_upgrades", [])
        for i, upgrade in enumerate(priority_upgrades[:5], 1):
            response += f"{i}. **{upgrade['slot']}** (Priority: {upgrade['priority']})\n"
            response += f"   Current: {upgrade.get('current_item', 'Empty')}\n"
            response += f"   Suggested: {upgrade['suggested_item']}\n"
            response += f"   Estimated Improvement: +{upgrade['improvement_estimate']:.1%}\n"
            response += f"   Estimated Cost: {upgrade['estimated_cost']}\n\n"

        return response

    def _format_passive_recommendations(self, recommendations: dict) -> str:
        """Format passive tree recommendations"""
        response = "# Passive Tree Optimization\n\n"

        allocations = recommendations.get("suggested_allocations", [])
        if allocations:
            response += "## Suggested Allocations\n"
            for node in allocations:
                response += f"- {node['name']}: {node['benefit']}\n"

        respecs = recommendations.get("suggested_respecs", [])
        if respecs:
            response += "\n## Suggested Respecs\n"
            for respec in respecs:
                response += f"- Remove {respec['current']}, allocate {respec['suggested']}\n"
                response += f"  Benefit: {respec['benefit']}\n"

        return response

    def _format_skill_recommendations(self, recommendations: dict) -> str:
        """Format skill recommendations"""
        response = "# Skill Setup Optimization\n\n"

        setups = recommendations.get("suggested_setups", [])
        for i, setup in enumerate(setups, 1):
            response += f"## Setup {i}: {setup['skill_name']}\n"
            response += f"Links: {', '.join(setup['supports'])}\n"
            response += f"Priority: {setup['priority']}\n\n"

        return response

    def _format_build_comparison(self, comparison: dict) -> str:
        """Format build comparison"""
        response = "# Build Comparison\n\n"

        for metric in comparison.get("metrics", []):
            response += f"## {metric['name']}\n"
            for build_result in metric["results"]:
                response += f"- {build_result['build_name']}: {build_result['value']}\n"
            response += "\n"

        return response

    def _format_dps_breakdown(self, breakdown: dict) -> str:
        """Format DPS breakdown"""
        response = f"""# DPS Breakdown

## Total DPS: {breakdown.get('total_dps', 0):,.0f}

## Damage by Type
"""
        for dmg_type, amount in breakdown.get("by_type", {}).items():
            response += (
                f"- {dmg_type}: {amount:,.0f} ({amount/breakdown.get('total_dps', 1)*100:.1f}%)\n"
            )

        response += f"""
## Modifiers Applied
- Increased Damage: +{breakdown.get('increased_damage', 0):.1f}%
- More Damage: +{breakdown.get('more_damage', 0):.1f}%
- Critical Strike Chance: {breakdown.get('crit_chance', 0):.1f}%
- Critical Strike Multiplier: {breakdown.get('crit_multi', 0):.0f}%
"""

        return response

    def _format_list(self, items: List[str]) -> str:
        """Format a list of strings as markdown"""
        return "\n".join(f"- {item}" for item in items) if items else "None identified"

    def _format_resistances(self, resistances: dict) -> str:
        """Format resistances as a display section"""
        if not resistances:
            return ""

        fire = resistances.get("fire", 0)
        cold = resistances.get("cold", 0)
        lightning = resistances.get("lightning", 0)
        chaos = resistances.get("chaos", 0)

        # Format with cap indicators
        def format_res(value, cap=75):
            if value >= cap:
                return f"{value}% (capped)"
            elif value < 0:
                return f"{value}% (NEGATIVE)"
            else:
                return f"{value}%"

        return f"""
## Resistances
- Fire: {format_res(fire)}
- Cold: {format_res(cold)}
- Lightning: {format_res(lightning)}
- Chaos: {format_res(chaos)}
"""

    def _format_skills_section(self, character_data: dict) -> str:
        """Format skill gems and their support links from character data"""
        skills = character_data.get("skills", [])
        skill_dps = character_data.get("skill_dps", [])

        if not skills and not skill_dps:
            return ""

        response = "\n## Skill Gems\n"

        # Create a DPS lookup by skill name for quick reference
        dps_lookup = {}
        for dps_entry in skill_dps:
            name = dps_entry.get("skill_name", "")
            if name:
                dps_lookup[name.lower()] = dps_entry

        # Process each skill group
        for i, skill in enumerate(skills):
            # Handle different possible structures from poe.ninja
            # Structure 1: poe.ninja format with 'allGems' array (first = main, rest = supports)
            # Structure 2: skill has 'gems' array with main + supports
            # Structure 3: skill has 'name' directly
            # Structure 4: skill has 'dps' array with skill info

            all_gems = skill.get("allGems", [])
            gems = skill.get("gems", [])
            skill_name = skill.get("name") or ""
            slot = skill.get("slot") or skill.get("socketGroup") or ""
            dps_entries = skill.get("dps", [])

            # Structure 1: poe.ninja 'allGems' format (most common)
            if all_gems:
                # First gem is the main skill, rest are supports
                main_gem = all_gems[0] if all_gems else {}
                main_name = main_gem.get("name", "Unknown Skill")
                support_gems = [g.get("name", "") for g in all_gems[1:] if g.get("name")]

                # Get DPS from the skill's dps array
                dps_str = ""
                if dps_entries:
                    for d in dps_entries:
                        dps_val = d.get("dps", 0)
                        if dps_val:
                            dps_str = f" ({dps_val:,.0f} DPS)"
                            break

                response += f"\n### {main_name}{dps_str}\n"
                if support_gems:
                    response += f"**Supports:** {', '.join(support_gems)}\n"
                else:
                    response += "(No supports)\n"

            # Structure 2: Generic 'gems' array with isSupport flags
            elif gems:
                main_gems = []
                support_gems = []

                for gem in gems:
                    gem_name = gem.get("name", gem.get("skillGem", ""))
                    gem_level = gem.get("level", gem.get("gemLevel", ""))
                    gem_quality = gem.get("quality", gem.get("gemQuality", 0))
                    is_support = gem.get("isSupport", gem.get("support", False))

                    # Detect support gems by name if not explicitly marked
                    if not is_support and "support" in gem_name.lower():
                        is_support = True

                    gem_info = gem_name
                    if gem_level:
                        gem_info += f" (Lv{gem_level}"
                        if gem_quality:
                            gem_info += f"/{gem_quality}%"
                        gem_info += ")"

                    if is_support:
                        support_gems.append(gem_info)
                    else:
                        main_gems.append(gem_info)

                # Output this skill group
                if main_gems or support_gems:
                    slot_label = f" [{slot}]" if slot else ""
                    response += f"\n### Skill Setup {i+1}{slot_label}\n"

                    if main_gems:
                        response += f"**Main Skill:** {', '.join(main_gems)}\n"

                        # Add DPS if available
                        for main in main_gems:
                            main_base = main.split(" (")[0].lower()
                            if main_base in dps_lookup:
                                dps_data = dps_lookup[main_base]
                                total_dps = dps_data.get("total_dps", 0)
                                if total_dps:
                                    response += f"**DPS:** {total_dps:,.0f}\n"
                                break

                    if support_gems:
                        response += f"**Supports:** {', '.join(support_gems)}\n"

            # Structure 3: Just a skill name
            elif skill_name:
                response += f"\n### {skill_name}\n"

                # Check for DPS data
                if skill_name.lower() in dps_lookup:
                    dps_data = dps_lookup[skill_name.lower()]
                    total_dps = dps_data.get("total_dps", 0)
                    dot_dps = dps_data.get("dot_dps", 0)
                    if total_dps:
                        response += f"- Hit DPS: {total_dps:,.0f}\n"
                    if dot_dps:
                        response += f"- DoT DPS: {dot_dps:,.0f}\n"

            # Structure 4: Only 'dps' entries
            elif dps_entries:
                for dps_entry in dps_entries:
                    dps_name = dps_entry.get("name", "Unknown Skill")
                    total_dps = dps_entry.get("dps", 0)
                    response += f"\n### {dps_name}\n"
                    if total_dps:
                        response += f"- DPS: {total_dps:,.0f}\n"

        # If we only have skill_dps but no detailed skills array
        if not skills and skill_dps:
            response += "\n### Calculated Skill DPS\n"
            for dps_entry in skill_dps:
                name = dps_entry.get("skill_name", "Unknown")
                total = dps_entry.get("total_dps", 0)
                dot = dps_entry.get("dot_dps", 0)
                response += f"- **{name}**: "
                if total:
                    response += f"{total:,.0f} DPS"
                if dot:
                    response += f" + {dot:,.0f} DoT"
                response += "\n"

        return response

    def _format_player_comparison(self, comparison: dict) -> str:
        """Format comparison to top players"""
        user_char = comparison.get("user_character", {})
        pool = comparison.get("comparison_pool", {})
        gear_comp = comparison.get("gear_comparison", {})
        skill_comp = comparison.get("skill_comparison", {})
        stat_comp = comparison.get("stat_comparison", {})
        key_diffs = comparison.get("key_differences", [])
        recommendations = comparison.get("recommendations", [])

        response = f"""# Comparison to Top Players: {user_char.get('name', 'Unknown')}

## Comparison Summary
- **Your Level**: {user_char.get('level', 0)}
- **Players Analyzed**: {pool.get('count', 0)} top players
- **Average Level**: {pool.get('avg_level', 0):.0f}
- **Level Range**: {pool.get('level_range', (0, 0))[0]} - {pool.get('level_range', (0, 0))[1]}

## ⚠️ Critical Differences
{self._format_list(key_diffs[:5])}

## 🎯 Top Recommendations
"""

        for rec in recommendations[:5]:
            priority = rec.get("priority", "Medium")
            category = rec.get("category", "General")
            text = rec.get("recommendation", "")
            response += f"\n### [{priority}] {category}\n{text}\n"

        response += f"""

## 🔧 Gear Analysis

### Popular Unique Items (Top Players)
"""
        popular_uniques = gear_comp.get("popular_uniques", {})
        for unique, count in list(popular_uniques.items())[:8]:
            usage_pct = (count / pool.get("count", 1)) * 100
            response += f"- **{unique}**: Used by {usage_pct:.0f}% of top players\n"

        response += f"""

### Your Current Uniques
{self._format_list([f"{slot}: {item}" for slot, item in gear_comp.get("user_uniques", {}).items()])}

## 💎 Skill Setup Analysis

### Popular Support Gems (Top Players)
"""
        common_supports = skill_comp.get("common_supports_in_top_players", {})
        for support, count in list(common_supports.items())[:8]:
            usage_pct = (count / pool.get("count", 1)) * 100
            response += f"- **{support}**: {usage_pct:.0f}% usage rate\n"

        response += f"""

### Your Main Skills
{self._format_list(skill_comp.get("user_main_skills", []))}

## 📊 Stat Comparison

### Key Stats vs Top Players
"""

        important_stats = [
            "life",
            "energyShield",
            "mana",
            "fireResistance",
            "coldResistance",
            "lightningResistance",
        ]
        for stat in important_stats:
            if stat in stat_comp:
                data = stat_comp[stat]
                user_val = data.get("user", 0)
                avg_val = data.get("average", 0)
                percentile = data.get("percentile", 0)

                status = "✅" if percentile >= 50 else "⚠️" if percentile >= 25 else "❌"
                response += f"- {status} **{stat}**: {user_val} (avg: {avg_val:.0f}, percentile: {percentile}%)\n"

        response += f"""

## 🏆 Top Performers

"""
        top_performers = comparison.get("top_performers", [])
        for i, performer in enumerate(top_performers[:3], 1):
            response += f"{i}. **{performer.get('name')}** (Level {performer.get('level')})\n"
            stats = performer.get("stats", {})
            response += f"   - Life: {stats.get('life', 0):,} | ES: {stats.get('es', 0):,}\n"

        response += f"""

## 💡 Action Items

**Immediate Priorities:**
"""
        for rec in recommendations[:3]:
            if rec.get("priority") in ["Critical", "High"]:
                response += f"1. {rec.get('recommendation')}\n"

        response += """

---
*Comparison based on ladder rankings and skill similarity*
"""

        return response

    def _format_trade_search_results(
        self, results: Dict[str, List[Dict]], character_needs: Dict, max_price: Optional[int]
    ) -> str:
        """Format trade search results"""
        response = "# Trade Market Search Results\n\n"

        # Add search criteria
        response += "## Search Criteria\n"
        missing_res = character_needs.get("missing_resistances", {})
        if missing_res:
            res_str = ", ".join([f"{k.title()}: +{v}%" for k, v in missing_res.items()])
            response += f"- **Missing Resistances**: {res_str}\n"

        if character_needs.get("needs_life"):
            response += "- **Needs**: More Life\n"
        if character_needs.get("needs_es"):
            response += "- **Needs**: More Energy Shield\n"

        if max_price:
            response += f"- **Max Budget**: {max_price} chaos orbs\n"

        response += "\n"

        # Format each item type
        total_items = sum(len(items) for items in results.values())
        response += f"**Found {total_items} items across {len(results)} categories**\n\n"

        # Charms
        if "charms" in results and results["charms"]:
            response += "## Resistance Charms\n\n"
            for i, item in enumerate(results["charms"][:8], 1):
                response += self._format_trade_item(i, item)

        # Amulets
        if "amulets" in results and results["amulets"]:
            response += "\n## Amulets (with Spell Levels)\n\n"
            for i, item in enumerate(results["amulets"][:5], 1):
                response += self._format_trade_item(i, item)

        # Helmets
        if "helmets" in results and results["helmets"]:
            response += "\n## Helmets (Life/ES + Resistances)\n\n"
            for i, item in enumerate(results["helmets"][:5], 1):
                response += self._format_trade_item(i, item)

        response += "\n---\n"
        response += "\n**How to Purchase:**\n"
        response += "1. Whisper the seller in-game (copy their account name)\n"
        response += "2. Verify the item stats match what you need\n"
        response += "3. Complete the trade\n"
        response += "4. Re-check your resistances are capped after equipping\n"

        return response

    def _format_trade_item(self, index: int, item: Dict) -> str:
        """Format a single trade item"""
        name = item.get("name") or item.get("type", "Unknown")
        item_type = item.get("type", "")
        ilvl = item.get("item_level", 0)
        corrupted = " [CORRUPTED]" if item.get("corrupted") else ""

        # Price
        price = item.get("price", {})
        price_amount = price.get("amount", "?")
        price_currency = price.get("currency", "chaos")

        # Seller
        seller = item.get("seller", {})
        seller_name = seller.get("account", "Unknown")
        online = "ONLINE" if seller.get("online") else "Offline"
        online_emoji = "🟢" if seller.get("online") else "🔴"

        result = f"**[{index}] {name}**{corrupted}\n"
        result += f"- Type: {item_type} (iLvl {ilvl})\n"
        result += f"- Price: **{price_amount} {price_currency}**\n"
        result += f"- Seller: {seller_name} [{online_emoji} {online}]\n"

        # Mods
        explicit_mods = item.get("explicit_mods", [])
        implicit_mods = item.get("implicit_mods", [])

        if implicit_mods:
            result += "- Implicit:\n"
            for mod in implicit_mods[:2]:
                result += f"  - {mod}\n"

        if explicit_mods:
            result += "- Explicit:\n"
            for mod in explicit_mods[:4]:
                result += f"  - {mod}\n"
            if len(explicit_mods) > 4:
                result += f"  - ... and {len(explicit_mods) - 4} more\n"

        result += "\n"
        return result

    async def run(self):
        """Run the MCP server"""
        try:
            debug_log("Starting server run() method...")
            await self.initialize()

            debug_log("Initialization complete, starting MCP protocol...")
            logger.info("Starting PoE2 Build Optimizer MCP Server...")

            debug_log("Creating stdio server...")
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                debug_log("stdio server created successfully")

                # Create notification options
                debug_log("Creating notification options...")
                notification_opts = NotificationOptions()

                debug_log("Creating initialization options...")
                init_options = InitializationOptions(
                    server_name="poe2-build-optimizer",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=notification_opts, experimental_capabilities={}
                    ),
                )

                debug_log("Running MCP server...")
                await self.server.run(read_stream, write_stream, init_options)
                debug_log("MCP server run completed")

        except Exception as e:
            debug_log(f"SERVER ERROR: {e}")
            logger.error(f"Server error: {e}")
            import traceback

            debug_log(f"Traceback:\n{traceback.format_exc()}")
            raise
        finally:
            debug_log("Running cleanup...")
            await self.cleanup()
            debug_log("Cleanup complete")


async def main():
    """Main entry point"""
    debug_log("=== main() function called ===")
    try:
        debug_log("Creating PoE2BuildOptimizerMCP instance...")
        server = PoE2BuildOptimizerMCP()
        debug_log("Server instance created, calling run()...")
        await server.run()
        debug_log("Server run() completed")
    except Exception as e:
        debug_log(f"MAIN ERROR: {e}")
        import traceback

        debug_log(f"Traceback:\n{traceback.format_exc()}")
        raise


def cli() -> None:
    """Synchronous wrapper around the async main() for the pip console entry-point.

    Without this, the `poe2-mcp` script generated from pyproject.toml's
    [project.scripts] would call main() directly, receive a coroutine, never
    await it, and exit immediately with a RuntimeWarning. See issue #56.
    """
    asyncio.run(main())


if __name__ == "__main__":
    debug_log("=== __main__ entry point ===")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        debug_log("Server interrupted by user")
    except Exception as e:
        debug_log(f"FATAL ERROR in __main__: {e}")
        import traceback

        debug_log(f"Traceback:\n{traceback.format_exc()}")
        sys.exit(1)
