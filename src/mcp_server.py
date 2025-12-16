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

# Setup logging to both file and stderr (for Claude Desktop logs)
import sys

# Configure logging to stderr for Claude Desktop
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG for detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),  # Log to stderr for Claude Desktop
    ]
)
logger = logging.getLogger(__name__)

# Also log to stderr directly for immediate visibility
def debug_log(message):
    """Direct logging to stderr for Claude Desktop"""
    print(f"[MCP-SERVER] {message}", file=sys.stderr, flush=True)

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

        # Passive Tree Resolver (for poe.ninja node ID resolution)
        self.passive_tree_resolver: Optional[PassiveTreeResolver] = None

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
                cache_manager=self.cache_manager,
                rate_limiter=self.rate_limiter
            )
            logger.info("PoE API client initialized")

            # Initialize character fetcher
            self.char_fetcher = CharacterFetcher(
                cache_manager=self.cache_manager,
                rate_limiter=self.rate_limiter
            )
            logger.info("Character fetcher initialized")

            # Initialize trade API
            if settings.ENABLE_TRADE_INTEGRATION:
                self.trade_api = TradeAPI(
                    cache_manager=self.cache_manager,
                    rate_limiter=self.rate_limiter
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
                cache_manager=self.cache_manager,
                rate_limiter=self.rate_limiter
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
            self.mechanics_kb = PoE2MechanicsKnowledgeBase(db_manager=self.db_manager)  # Pass db_manager for .datc64 access
            self.gear_comparator = GearComparator()
            self.damage_scaling_analyzer = DamageScalingAnalyzer()
            self.content_readiness_checker = ContentReadinessChecker()
            logger.info("Enhancement features initialized (gem synergy, mechanics KB, etc.)")
            debug_log("Enhancement features ready: gem synergy calculator, mechanics knowledge base, gear comparator, damage scaling analyzer, content readiness checker")

            # Initialize AI components
            if settings.ENABLE_AI_INSIGHTS:
                self.query_handler = QueryHandler()
                self.recommendation_engine = RecommendationEngine(
                    db_manager=self.db_manager
                )
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
            elif name == "health_check":
                return await self._handle_health_check(arguments)
            elif name == "clear_cache":
                return await self._handle_clear_cache(arguments)
            elif name == "setup_trade_auth":
                return await self._handle_setup_trade_auth(arguments)
            # KNOWLEDGE TOOLS (4 tools)
            elif name == "get_formula":
                return await self._handle_get_formula(arguments)
            elif name == "explain_mechanic":
                return await self._handle_explain_mechanic(arguments)
            elif name == "validate_support_combination":
                return await self._handle_validate_support_combination(arguments)
            elif name == "validate_build_constraints":
                return await self._handle_validate_build_constraints(arguments)
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
            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            debug_log(f"TOOL ERROR in {name}: {e}")
            logger.error(f"Error in tool {name}: {e}")
            import traceback
            debug_log(f"Traceback:\n{traceback.format_exc()}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

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
                    description="Fetch PoE2 character data from poe.ninja API. Returns raw character stats, gear, skills, and passives for Claude to analyze.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {
                                "type": "string",
                                "description": "Path of Exile account name"
                            },
                            "character": {
                                "type": "string",
                                "description": "Character name to fetch"
                            },
                            "league": {
                                "type": "string",
                                "description": "League name (e.g., 'Abyss', 'Standard')",
                                "default": "Abyss"
                            }
                        },
                        "required": ["account", "character"]
                    }
                ),
                # Compare to top players
                types.Tool(
                    name="compare_to_top_players",
                    description="Fetch top ladder players using the same skills for comparison. Returns raw data about what high-performers do differently.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_name": {
                                "type": "string",
                                "description": "PoE account name"
                            },
                            "character_name": {
                                "type": "string",
                                "description": "Character name to compare"
                            },
                            "league": {
                                "type": "string",
                                "description": "League name",
                                "default": "Standard"
                            },
                            "top_player_limit": {
                                "type": "integer",
                                "description": "Number of top players to fetch",
                                "default": 10
                            }
                        },
                        "required": ["account_name", "character_name"]
                    }
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
                                "description": "Item name or type to search"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Additional filters (rarity, item_class, etc.)"
                            }
                        },
                        "required": ["query"]
                    }
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
                                "default": "Standard"
                            },
                            "character_needs": {
                                "type": "object",
                                "description": "What the character needs (resistances, life, ES, item_slots)"
                            },
                            "max_price_chaos": {
                                "type": "integer",
                                "description": "Maximum price in chaos orbs"
                            }
                        },
                        "required": ["league", "character_needs"]
                    }
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
                                "description": "Name of the support gem"
                            }
                        },
                        "required": ["support_name"]
                    }
                ),
                types.Tool(
                    name="inspect_spell_gem",
                    description="Get complete data for a spell gem including tags, base damage, cast time, mana/spirit cost.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spell_name": {
                                "type": "string",
                                "description": "Name of the spell gem"
                            }
                        },
                        "required": ["spell_name"]
                    }
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
                                "description": "Filter by tags"
                            },
                            "max_spirit": {
                                "type": "integer",
                                "description": "Maximum spirit cost"
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["name", "spirit_cost", "damage_multiplier"],
                                "default": "name"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50
                            }
                        }
                    }
                ),
                types.Tool(
                    name="list_all_spells",
                    description="List all spell gems with optional filtering by element, tags, damage.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_element": {
                                "type": "string",
                                "enum": ["fire", "cold", "lightning", "physical", "chaos"]
                            },
                            "filter_tags": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "min_damage": {
                                "type": "number"
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["name", "base_damage", "cast_time", "dps"],
                                "default": "name"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50
                            }
                        }
                    }
                ),

                # Path of Building Integration
                types.Tool(
                    name="import_pob",
                    description="Import a Path of Building build code. Returns parsed build data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pob_code": {
                                "type": "string",
                                "description": "Path of Building build code (base64)"
                            }
                        },
                        "required": ["pob_code"]
                    }
                ),
                types.Tool(
                    name="export_pob",
                    description="Export character data to Path of Building format.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": "Character data to export"
                            }
                        },
                        "required": ["character_data"]
                    }
                ),
                types.Tool(
                    name="get_pob_code",
                    description="Fetch a ready-to-use PoB code from poe.ninja for a character.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {
                                "type": "string",
                                "description": "Account name"
                            },
                            "character": {
                                "type": "string",
                                "description": "Character name"
                            }
                        },
                        "required": ["account", "character"]
                    }
                ),

                # System Tools
                types.Tool(
                    name="health_check",
                    description="Run diagnostic checks on the MCP server (database, API, config).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "verbose": {
                                "type": "boolean",
                                "default": False
                            }
                        }
                    }
                ),
                types.Tool(
                    name="clear_cache",
                    description="Clear all cached data (memory, SQLite, Redis).",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="setup_trade_auth",
                    description="Set up trade API authentication by extracting POESESSID via browser login.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "headless": {
                                "type": "boolean",
                                "default": False
                            }
                        }
                    }
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
                                "description": "Formula type: dps, ehp, armor, resistance, spirit, stun, crit, conversion, dot, block. Leave empty to list all."
                            }
                        }
                    }
                ),

                # Mechanic Explanations
                types.Tool(
                    name="explain_mechanic",
                    description="Explain PoE2 game mechanics (ailments, crowd control, damage scaling, etc.). Returns detailed explanations with formulas.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "mechanic_name": {
                                "type": "string",
                                "description": "Mechanic to explain (e.g., 'freeze', 'stun', 'critical strike')"
                            }
                        },
                        "required": ["mechanic_name"]
                    }
                ),

                # Validation
                types.Tool(
                    name="validate_support_combination",
                    description="Check if support gems are compatible. Detects conflicts like Faster+Slower Projectiles.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "support_gems": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Support gem names to validate"
                            }
                        },
                        "required": ["support_gems"]
                    }
                ),
                types.Tool(
                    name="validate_build_constraints",
                    description="Validate build against game constraints (resistances, spirit, mana reservation).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": "Character stats to validate"
                            }
                        },
                        "required": ["character_data"]
                    }
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
                                "description": "List of allocated passive node IDs from poe.ninja"
                            },
                            "target_notable": {
                                "type": "string",
                                "description": "Optional: Name of a notable to find path to"
                            },
                            "find_recommendations": {
                                "type": "boolean",
                                "description": "Whether to find nearest unallocated notables",
                                "default": True
                            }
                        },
                        "required": ["node_ids"]
                    }
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
                                "description": "poe.ninja profile URL (e.g., https://poe.ninja/poe2/profile/AccountName/character/CharacterName)"
                            }
                        },
                        "required": ["url"]
                    }
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
                                "description": "Filter keystones by stat text (e.g., 'life', 'crit', 'leech')"
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["name", "stat_count"],
                                "default": "name"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="inspect_keystone",
                    description="Get complete details for a specific keystone by name, including all stats and effects.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keystone_name": {
                                "type": "string",
                                "description": "Name of the keystone (e.g., 'Chaos Inoculation', 'Vaal Pact')"
                            }
                        },
                        "required": ["keystone_name"]
                    }
                ),
                types.Tool(
                    name="list_all_notables",
                    description="List all notable passive nodes. Notables are medium-power passives that define build paths.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_stat": {
                                "type": "string",
                                "description": "Filter notables by stat text (e.g., 'projectile', 'fire', 'attack')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number to return",
                                "default": 100
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["name", "stat_count"],
                                "default": "name"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="inspect_passive_node",
                    description="Get complete details for any passive node by name or ID. Works for keystones, notables, and small nodes.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_name": {
                                "type": "string",
                                "description": "Name of the passive node"
                            },
                            "node_id": {
                                "type": "integer",
                                "description": "Numeric ID of the passive node (alternative to name)"
                            }
                        }
                    }
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
                                "description": "Filter by item type (e.g., 'Sword', 'Helmet', 'Ring')"
                            },
                            "filter_name": {
                                "type": "string",
                                "description": "Filter by name substring"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 100
                            }
                        }
                    }
                ),
                types.Tool(
                    name="inspect_base_item",
                    description="Get complete details for a specific base item type.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "item_name": {
                                "type": "string",
                                "description": "Name of the base item"
                            }
                        },
                        "required": ["item_name"]
                    }
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
                                "description": "Mod ID (e.g., 'IncreasedLife5', 'FireResist3')"
                            }
                        },
                        "required": ["mod_id"]
                    }
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
                                "enum": ["PREFIX", "SUFFIX", "IMPLICIT", "CORRUPTED"]
                            },
                            "filter_stat": {
                                "type": "string",
                                "description": "Filter by stat keyword (e.g., 'life', 'fire', 'resistance')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of mods to return",
                                "default": 50
                            }
                        }
                    }
                ),
                types.Tool(
                    name="search_mods_by_stat",
                    description="Search for mods that grant a specific stat effect. Returns all mods matching the stat keyword.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "stat_keyword": {
                                "type": "string",
                                "description": "Stat keyword to search for (e.g., 'fire resistance', 'increased life', 'physical damage')"
                            },
                            "generation_type": {
                                "type": "string",
                                "description": "Optional: Filter by generation type (PREFIX, SUFFIX, IMPLICIT, CORRUPTED)",
                                "enum": ["PREFIX", "SUFFIX", "IMPLICIT", "CORRUPTED"]
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 50
                            }
                        },
                        "required": ["stat_keyword"]
                    }
                ),
                types.Tool(
                    name="get_mod_tiers",
                    description="Get all tier variations of a mod family (e.g., IncreasedLife1-13). Shows progression from T1 to highest tier with level requirements and values.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "mod_base": {
                                "type": "string",
                                "description": "Base mod name without tier number (e.g., 'IncreasedLife', 'FireResist')"
                            }
                        },
                        "required": ["mod_base"]
                    }
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
                                "description": "List of mod IDs to validate (e.g., ['Strength1', 'FireResist3', 'AddedLightningDamage5'])"
                            },
                            "item_level": {
                                "type": "integer",
                                "description": "Item level to check mod requirements against",
                                "default": 83
                            }
                        },
                        "required": ["mod_ids"]
                    }
                ),
                types.Tool(
                    name="get_available_mods",
                    description="Get all mods that could roll on an item type. Filter by generation type (PREFIX/SUFFIX) and level requirements.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "generation_type": {
                                "type": "string",
                                "description": "Filter by generation type: PREFIX or SUFFIX",
                                "enum": ["PREFIX", "SUFFIX"]
                            },
                            "max_level": {
                                "type": "integer",
                                "description": "Maximum level requirement (filters mods you can't roll yet)",
                                "default": 100
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of mods to return",
                                "default": 100
                            }
                        },
                        "required": ["generation_type"]
                    }
                )
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
                    mimeType="application/json"
                ),
                types.Resource(
                    uri="poe2://game-data/passives",
                    name="Passive Tree",
                    description="Complete passive skill tree data",
                    mimeType="application/json"
                ),
                types.Resource(
                    uri="poe2://game-data/skills",
                    name="Skill Gems",
                    description="All skill gem data",
                    mimeType="application/json"
                )
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
                            required=True
                        )
                    ]
                ),
                types.Prompt(
                    name="optimize_for_goal",
                    description="Goal-specific build optimization",
                    arguments=[
                        types.PromptArgument(
                            name="goal",
                            description="Optimization goal (dps, defense, etc.)",
                            required=True
                        )
                    ]
                )
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
                account_name=account,
                character_name=character,
                league=args.get("league", "Abyss")
            )

            if not character_data:
                # Enhanced error message with debugging info
                error_msg = f"""# Character Fetch Failed

**Character:** {character}
**Account:** {account}

## URLs Attempted:
1. https://poe.ninja/poe2/builds/character/{account}/{character}
2. https://poe.ninja/builds/character/{account}/{character}
3. Official PoE ladder API
4. Direct web scraping

## Common Issues:

### 1. Profile Privacy
- Your character profile must be PUBLIC
- Check: https://www.pathofexile.com/account/view-profile/{account}/characters
- Go to Privacy Settings and ensure characters are visible

### 2. Account Name Format
Try these variations:
- Just the account name: `{account.split('-')[0] if '-' in account else account.split('#')[0] if '#' in account else account}`
- With discriminator: `{account}-####` or `{account}#####`
- Check your exact account name at https://www.pathofexile.com/account

### 3. Character Name
- Ensure exact spelling (case-sensitive)
- No extra spaces
- Character must be in the current league

### 4. poe.ninja Indexing
- New characters may take 1-2 hours to appear on poe.ninja
- Very low-level characters might not be indexed
- Try the official PoE website directly to verify the character exists

## Debug Steps:
1. Visit: https://poe.ninja/poe2/builds/character/{account}/{character}
2. If you see "Character not found", the issue is with poe.ninja indexing
3. If you see your character there, report this as a bug with the MCP server

## Alternative:
If the character is on the ladder, try `compare_to_top_players` instead.
"""
                return [types.TextContent(
                    type="text",
                    text=error_msg
                )]

            # Calculate actual stats instead of using stub build_scorer
            analysis = {
                "overall_score": 0.0,
                "tier": "Unknown",
                "strengths": [],
                "weaknesses": [],
                "dps": character_data.get("dps", 0),
                "ehp": 0,
                "defense_rating": 0.0
            }

            # Calculate EHP if calculator is available
            if self.ehp_calculator:
                try:
                    # Import with fallback for both direct and module execution
                    try:
                        from .calculator.ehp_calculator import DefensiveStats, ThreatProfile, DamageType
                    except ImportError:
                        from src.calculator.ehp_calculator import DefensiveStats, ThreatProfile, DamageType

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

                    logger.info(f"[ANALYZE_CHAR] Calculating EHP with Life: {life}, ES: {energy_shield}")

                    defensive_stats = DefensiveStats(
                        life=life,
                        energy_shield=energy_shield,
                        armor=armor,
                        evasion=evasion,
                        block_chance=block_chance,
                        fire_res=fire_res,
                        cold_res=cold_res,
                        lightning_res=lightning_res,
                        chaos_res=chaos_res
                    )

                    # Calculate average EHP across damage types
                    threat = ThreatProfile(expected_hit_size=1000.0)
                    phys_result = self.ehp_calculator.calculate_ehp(defensive_stats, DamageType.PHYSICAL, threat)
                    fire_result = self.ehp_calculator.calculate_ehp(defensive_stats, DamageType.FIRE, threat)
                    cold_result = self.ehp_calculator.calculate_ehp(defensive_stats, DamageType.COLD, threat)
                    lightning_result = self.ehp_calculator.calculate_ehp(defensive_stats, DamageType.LIGHTNING, threat)

                    # Use average EHP from results
                    avg_ehp = (phys_result.effective_hp + fire_result.effective_hp +
                               cold_result.effective_hp + lightning_result.effective_hp) / 4
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
                analysis["strengths"].append(f"Good defensive pool ({total_pool:,.0f} combined life+ES)")
            elif total_pool < 4000:
                analysis["weaknesses"].append(f"Low defensive pool ({total_pool:,.0f} combined life+ES)")

            # Check resistances (poe.ninja format uses camelCase)
            fire_res = stats.get("fireResistance", 0) or 0
            cold_res = stats.get("coldResistance", 0) or 0
            lightning_res = stats.get("lightningResistance", 0) or 0

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
                    character_data,
                    analysis
                )

            # Resolve passive tree node IDs to full data
            passive_analysis = None
            if self.passive_tree_resolver:
                try:
                    passive_ids = character_data.get('passive_tree', [])
                    if passive_ids:
                        passive_analysis = self.passive_tree_resolver.analyze_build(passive_ids)
                        logger.info(f"[ANALYZE_CHAR] Resolved {passive_analysis.total_nodes} passive nodes")
                except Exception as e:
                    logger.warning(f"[ANALYZE_CHAR] Passive tree resolution failed: {e}")

            # Format response
            response = self._format_character_analysis(character_data, analysis, recommendations, passive_analysis)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Character analysis failed: {e}")
            return [types.TextContent(
                type="text",
                text=f"Analysis failed: {str(e)}"
            )]

    async def _handle_nl_query(self, args: dict) -> List[types.TextContent]:
        """Handle natural language query"""
        query = args["query"]
        character_context = args.get("character_context")

        if not self.query_handler:
            return [types.TextContent(
                type="text",
                text="AI insights are not enabled. Please set ENABLE_AI_INSIGHTS=true and provide an API key."
            )]

        try:
            response = await self.query_handler.handle_query(
                query,
                character_context
            )

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"NL query failed: {e}")
            return [types.TextContent(
                type="text",
                text=f"Query failed: {str(e)}"
            )]

    async def _handle_optimize_gear(self, args: dict) -> List[types.TextContent]:
        """Handle gear optimization"""
        character_data = args["character_data"]
        budget = args.get("budget", "medium")
        goal = args.get("goal", "balanced")

        try:
            recommendations = await self.gear_optimizer.optimize(
                character_data,
                budget=budget,
                goal=goal
            )

            response = self._format_gear_recommendations(recommendations)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Gear optimization failed: {str(e)}"
            )]

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
                goal=goal
            )

            response = self._format_passive_recommendations(recommendations)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Passive optimization failed: {str(e)}"
            )]

    async def _handle_optimize_skills(self, args: dict) -> List[types.TextContent]:
        """Handle skill optimization"""
        character_data = args["character_data"]
        goal = args.get("goal", "balanced")

        try:
            recommendations = await self.skill_optimizer.optimize(
                character_data,
                goal=goal
            )

            response = self._format_skill_recommendations(recommendations)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Skill optimization failed: {str(e)}"
            )]

    async def _handle_compare_builds(self, args: dict) -> List[types.TextContent]:
        """Handle build comparison"""
        builds = args["builds"]
        metrics = args.get("comparison_metrics", ["overall_score", "dps", "defense"])

        try:
            comparison = await self.build_scorer.compare_builds(builds, metrics)
            response = self._format_build_comparison(comparison)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Build comparison failed: {str(e)}"
            )]

    async def _handle_import_pob(self, args: dict) -> List[types.TextContent]:
        """Handle PoB import"""
        pob_code = args["pob_code"]

        if not self.pob_importer:
            return [types.TextContent(
                type="text",
                text="Path of Building import is not enabled."
            )]

        try:
            build_data = await self.pob_importer.import_build(pob_code)
            return [types.TextContent(
                type="text",
                text=f"Successfully imported build:\n{json.dumps(build_data, indent=2)}"
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"PoB import failed: {str(e)}"
            )]

    async def _handle_export_pob(self, args: dict) -> List[types.TextContent]:
        """Handle PoB export"""
        character_data = args["character_data"]

        if not self.pob_exporter:
            return [types.TextContent(
                type="text",
                text="Path of Building export is not enabled."
            )]

        try:
            pob_code = await self.pob_exporter.export_build(character_data)
            return [types.TextContent(
                type="text",
                text=f"Path of Building Code:\n{pob_code}\n\nCopy this code and import it in Path of Building."
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"PoB export failed: {str(e)}"
            )]

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
                    actual_code = pob_code.get("pob") or pob_code.get("code") or pob_code.get("build")
                    if actual_code:
                        pob_code = actual_code
                    else:
                        # Return the structure so user can see what was returned
                        return [types.TextContent(
                            type="text",
                            text=f"PoB API returned unexpected format:\n{json.dumps(pob_code, indent=2)}"
                        )]

                return [types.TextContent(
                    type="text",
                    text=f"Path of Building Code for {character}:\n\n{pob_code}\n\nCopy this code and import it in Path of Building."
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Could not fetch PoB code for {character}. Character may not exist on poe.ninja or the PoB API may not have data for this character."
                )]

        except Exception as e:
            logger.error(f"Error fetching PoB code: {e}", exc_info=True)
            return [types.TextContent(
                type="text",
                text=f"Failed to fetch PoB code: {str(e)}"
            )]

    async def _handle_search_items(self, args: dict) -> List[types.TextContent]:
        """Handle item search using .datc64 game database"""
        query = args["query"]
        filters = args.get("filters", {})

        try:
            items = await self.db_manager.search_items(query, filters)

            if not items:
                return [types.TextContent(
                    type="text",
                    text=f"No items found matching '{query}'"
                )]

            response = f"Found {len(items)} items matching '{query}':\n\n"

            for item in items[:10]:  # Limit to 10 results
                name = item.get('name', 'Unknown')
                item_class = item.get('item_class', 'Unknown')
                base_type = item.get('base_type', '')
                width = item.get('width', 1)
                height = item.get('height', 1)
                drop_level = item.get('drop_level', 0)

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
            return [types.TextContent(
                type="text",
                text=f"Item search failed: {str(e)}"
            )]

    async def _handle_calculate_dps(self, args: dict) -> List[types.TextContent]:
        """Handle DPS calculation"""
        character_data = args["character_data"]
        include_buffs = args.get("include_buffs", True)

        try:
            from calculator.damage_calc import DamageCalculator
            calc = DamageCalculator(self.db_manager)

            dps_breakdown = await calc.calculate_dps(
                character_data,
                include_buffs=include_buffs
            )

            response = self._format_dps_breakdown(dps_breakdown)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"DPS calculation failed: {str(e)}"
            )]

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
                account_name,
                character_name,
                league
            )

            if not user_character:
                # Enhanced error message
                error_msg = f"""# Character Fetch Failed

**Character:** {character_name}
**Account:** {account_name}
**League:** {league}

## Troubleshooting:

### 1. Check Profile Privacy
Visit: https://www.pathofexile.com/account/view-profile/{account_name}/characters
- Ensure characters are set to PUBLIC in privacy settings
- If the page shows "Profile not found", your account name is incorrect

### 2. Verify Account Name Format
The account name might need to be in a specific format:
- Try without discriminator: `{account_name.split('-')[0] if '-' in account_name else account_name.split('#')[0] if '#' in account_name else account_name}`
- Try with dash: `AccountName-1234`
- Try with hash: `AccountName#1234`

### 3. Check poe.ninja
Try manually: https://poe.ninja/poe2/builds/character/{account_name}/{character_name}
- If it works there, report this as a bug
- If not, the character isn't indexed yet (wait 1-2 hours after playing)

### 4. Verify League Name
Current league: **{league}**
- For Abyss league, try: "Rise of the Abyssal" or "Abyss"
- For Standard, use: "Standard"

## Next Steps:
1. Verify the URLs above work in your browser
2. Check that the character is level 2+ (very low characters aren't indexed)
3. Try the `analyze_character` tool with the same parameters for more details
"""
                return [types.TextContent(
                    type="text",
                    text=error_msg
                )]

            # Perform comparison
            logger.info("Comparing to top players...")
            comparison = await self.top_player_fetcher.compare_with_top_players(
                user_character,
                league=league,
                min_level=min_level,
                comparison_focus="dps",
                top_player_limit=top_player_limit
            )

            if not comparison.get("success"):
                return [types.TextContent(
                    type="text",
                    text=comparison.get("message", "Comparison failed")
                )]

            # Format response
            response = self._format_player_comparison(comparison)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Comparison failed: {e}", exc_info=True)
            return [types.TextContent(
                type="text",
                text=f"Comparison failed: {str(e)}"
            )]

    async def _handle_search_trade_items(self, args: dict) -> List[types.TextContent]:
        """Handle trade item search"""
        league = args.get("league", "Standard")
        character_needs = args.get("character_needs", {})
        max_price_chaos = args.get("max_price_chaos")

        if not self.trade_api:
            return [types.TextContent(
                type="text",
                text="Trade integration is not enabled. Please set ENABLE_TRADE_INTEGRATION=true in your config."
            )]

        if not settings.POESESSID:
            return [types.TextContent(
                type="text",
                text="Trade search requires POESESSID cookie. Please set it up:\n\n"
                     "**AUTOMATED SETUP (Recommended - 2 minutes):**\n\n"
                     "Use the `setup_trade_auth` tool to automatically configure authentication.\n"
                     "Just run it and log in when the browser opens - the tool will handle the rest!\n\n"
                     "Example: \"Set up trade authentication\" or \"Use the setup_trade_auth tool\"\n\n"
                     "**Requirements:**\n"
                     "- Playwright must be installed: `pip install playwright`\n"
                     "- Chromium must be downloaded: `playwright install chromium`\n\n"
                     "**Manual Setup (Fallback):**\n"
                     "1. Visit https://www.pathofexile.com/trade in your browser\n"
                     "2. Log in to your account\n"
                     "3. Open DevTools (F12) → Application → Cookies\n"
                     "4. Find 'POESESSID' cookie and copy its value\n"
                     "5. Add to .env: POESESSID=your_cookie_value\n"
                     "6. Restart MCP server"
            )]

        try:
            logger.info(f"Searching trade market for upgrades in {league}...")

            # Perform search
            results = await self.trade_api.search_for_upgrades(
                league=league,
                character_needs=character_needs,
                max_price_chaos=max_price_chaos
            )

            if not results:
                return [types.TextContent(
                    type="text",
                    text=f"No items found matching your criteria in {league}. Try:\n"
                         "- Increasing your budget\n"
                         "- Broadening search criteria\n"
                         "- Checking if the league name is correct"
                )]

            # Format response
            response = self._format_trade_search_results(results, character_needs, max_price_chaos)

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Trade search failed: {e}", exc_info=True)
            return [types.TextContent(
                type="text",
                text=f"Trade search failed: {str(e)}\n\n"
                     "If you see authentication errors, your POESESSID cookie may have expired.\n\n"
                     "**To refresh:** Use the `setup_trade_auth` tool to get a new cookie.\n"
                     "Or manually update POESESSID in your .env file and restart the server."
            )]

    async def _handle_detect_weaknesses(self, args: dict) -> List[types.TextContent]:
        """Handle character weakness detection"""
        try:
            if not self.weakness_detector:
                return [types.TextContent(
                    type="text",
                    text="Weakness detector not initialized"
                )]

            # Support two modes: fetch from API or use provided data
            if "account" in args and "character" in args:
                # Mode 1: Fetch character from API
                account = args["account"]
                character = args["character"]

                character_data = await self.char_fetcher.get_character(
                    account_name=account,
                    character_name=character,
                    league=args.get("league", "Abyss")
                )

                # DEBUG: Log immediately after fetch
                if character_data:
                    logger.info(f"[WEAKNESS] Got character_data with keys: {list(character_data.keys())}")
                    logger.info(f"[WEAKNESS] life: {character_data.get('life')}, ES: {character_data.get('energy_shield')}")
                else:
                    logger.warning(f"[WEAKNESS] character_data is None/empty!")

                if not character_data:
                    return [types.TextContent(
                        type="text",
                        text=f"Could not fetch character '{character}' for account '{account}'. Check if profile is public."
                    )]
            else:
                # Mode 2: Use provided character_data (for testing)
                character_data = args.get("character_data", {})
                if not character_data:
                    return [types.TextContent(
                        type="text",
                        text="Either provide 'account' and 'character' to fetch from API, or provide 'character_data' for testing."
                    )]

            # Convert character data to CharacterData format
            from .analyzer.weakness_detector import CharacterData

            # DEBUG: Log what we're getting
            logger.info(f"[WEAKNESS_DETECTOR] character_data keys: {list(character_data.keys())}")
            logger.info(f"[WEAKNESS_DETECTOR] life value: {character_data.get('life', 'KEY_MISSING')}")
            logger.info(f"[WEAKNESS_DETECTOR] energy_shield value: {character_data.get('energy_shield', 'KEY_MISSING')}")
            logger.info(f"[WEAKNESS_DETECTOR] fire_res value: {character_data.get('fire_res', 'KEY_MISSING')}")
            logger.info(f"[WEAKNESS_DETECTOR] source value: {character_data.get('source', 'KEY_MISSING')}")

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
                equipped_items={}
            )

            # Detect weaknesses
            weaknesses = self.weakness_detector.detect_all_weaknesses(char)

            # Format response
            if not weaknesses:
                response = "# Character Weakness Analysis\n\n✓ No critical weaknesses detected!"
            else:
                response = f"# Character Weakness Analysis\n\n🔍 Found {len(weaknesses)} weaknesses:\n\n"

                for i, weakness in enumerate(weaknesses, 1):
                    priority_icon = "🔴" if weakness.priority >= 90 else "🟡" if weakness.priority >= 70 else "🟢"
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
            return [types.TextContent(
                type="text",
                text=f"Weakness detection failed: {str(e)}"
            )]

    async def _handle_evaluate_upgrade(self, args: dict) -> List[types.TextContent]:
        """Handle gear upgrade evaluation"""
        try:
            current_gear = args.get("current_gear", {})
            upgrade_gear = args.get("upgrade_gear", {})
            base_stats = args.get("base_character_stats", {})
            price_chaos = args.get("price_chaos")

            if not self.gear_evaluator:
                return [types.TextContent(
                    type="text",
                    text="Gear evaluator not initialized"
                )]

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
            return [types.TextContent(
                type="text",
                text=f"Gear evaluation failed: {str(e)}"
            )]

    async def _handle_calculate_ehp(self, args: dict) -> List[types.TextContent]:
        """Handle EHP calculation"""
        try:
            if not self.ehp_calculator:
                return [types.TextContent(
                    type="text",
                    text="EHP calculator not initialized"
                )]

            # Support two modes: fetch from API or use provided data
            if "account" in args and "character" in args:
                # Mode 1: Fetch character from API
                account = args["account"]
                character = args["character"]

                character_data = await self.char_fetcher.get_character(
                    account_name=account,
                    character_name=character,
                    league=args.get("league", "Abyss")
                )

                if not character_data:
                    return [types.TextContent(
                        type="text",
                        text=f"Could not fetch character '{character}' for account '{account}'. Check if profile is public."
                    )]
            else:
                # Mode 2: Use provided character_data (for testing)
                character_data = args.get("character_data", {})
                if not character_data:
                    return [types.TextContent(
                        type="text",
                        text="Either provide 'account' and 'character' to fetch from API, or provide 'character_data' for testing."
                    )]

            # Convert to DefensiveStats format
            from .calculator.ehp_calculator import DefensiveStats, DamageType, ThreatProfile

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
                phys_taken_as_elemental=character_data.get("phys_taken_as_elemental", 0)
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
            return [types.TextContent(
                type="text",
                text=f"EHP calculation failed: {str(e)}"
            )]

    async def _handle_analyze_spirit(self, args: dict) -> List[types.TextContent]:
        """Handle Spirit usage analysis"""
        try:
            if not self.spirit_calculator:
                return [types.TextContent(
                    type="text",
                    text="Spirit calculator not initialized"
                )]

            # Support two modes: fetch from API or use provided data
            if "account" in args and "character" in args:
                # Mode 1: Fetch character from API
                account = args["account"]
                character = args["character"]

                character_data = await self.char_fetcher.get_character(
                    account_name=account,
                    character_name=character,
                    league=args.get("league", "Abyss")
                )

                if not character_data:
                    return [types.TextContent(
                        type="text",
                        text=f"Could not fetch character '{character}' for account '{account}'. Check if profile is public."
                    )]
            else:
                # Mode 2: Use provided character_data (for testing)
                character_data = args.get("character_data", {})
                if not character_data:
                    return [types.TextContent(
                        type="text",
                        text="Either provide 'account' and 'character' to fetch from API, or provide 'character_data' for testing."
                    )]

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
            return [types.TextContent(
                type="text",
                text=f"Spirit analysis failed: {str(e)}"
            )]

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
                    league=args.get("league", "Abyss")
                )

                if not character_data:
                    return [types.TextContent(
                        type="text",
                        text=f"Could not fetch character '{character}' for account '{account}'. Check if profile is public."
                    )]
            else:
                # Mode 2: Use provided character_data (for testing)
                character_data = args.get("character_data", {})
                if not character_data:
                    return [types.TextContent(
                        type="text",
                        text="Either provide 'account' and 'character' to fetch from API, or provide 'character_data' for testing."
                    )]

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
                response += "🟢 **Good Resistance** - Large health pool provides natural stun defense\n"
                response += "  → Harder to fill Heavy Stun meter\n"
                response += "  → Light Stun threshold is high\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Stun analysis failed: {e}", exc_info=True)
            return [types.TextContent(
                type="text",
                text=f"Stun analysis failed: {str(e)}"
            )]

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
                    league=args.get("league", "Abyss")
                )

                if not character_data:
                    return [types.TextContent(
                        type="text",
                        text=f"Could not fetch character '{character}' for account '{account}'. Check if profile is public."
                    )]
            else:
                # Mode 2: Use provided character_data (for testing)
                character_data = args.get("character_data", {})
                if not character_data:
                    return [types.TextContent(
                        type="text",
                        text="Either provide 'account' and 'character' to fetch from API, or provide 'character_data' for testing."
                    )]

            # Run all analysis systems
            response = "# Comprehensive Build Optimization\n\n"
            response += f"**Focus:** {focus.title()}\n\n"

            # 1. Weakness Detection
            if self.weakness_detector:
                response += "## ⚠️ Critical Weaknesses\n\n"
                weakness_result = await self._handle_detect_weaknesses({"character_data": character_data})
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
                spirit_result = await self._handle_analyze_spirit({"character_data": character_data})
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
            return [types.TextContent(
                type="text",
                text=f"Optimization analysis failed: {str(e)}"
            )]

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
                        result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                        tables = result.fetchall()
                        response += f"✓ Database connected ({len(tables)} tables found)\n"
                        successes.append("Database connected")

                        # Check for items table
                        if any('items' in str(table) for table in tables):
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
            if hasattr(settings, 'POESESSID') and settings.POESESSID:
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
                            league="Abyss"
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
                            response += f"- Energy Shield: {test_char.get('energy_shield', 'MISSING')}\n"
                            response += f"- Fire Res: {test_char.get('fire_res', 'MISSING')}\n"
                            response += f"- Cold Res: {test_char.get('cold_res', 'MISSING')}\n"
                            response += f"- Lightning Res: {test_char.get('lightning_res', 'MISSING')}\n"
                            response += "\n**Stats Location:**\n"
                            response += f"- Stats at top level: {all(k in test_char for k in ['life', 'energy_shield'])}\n"
                            response += f"- Has 'stats' dict: {'stats' in test_char}\n"

                            if 'stats' in test_char:
                                response += f"- Stats dict has life: {'life' in test_char['stats']}\n"

                            # Check for code version markers
                            if test_char.get('source') == 'poe.ninja API':
                                response += "\n**✓ Using NEW poe.ninja API code**\n"
                                successes.append("New API code active")
                            else:
                                response += f"\n**⚠ Unexpected source: {test_char.get('source')}**\n"
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
            return [types.TextContent(
                type="text",
                text=f"Health check failed with error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            )]

    async def _handle_clear_cache(self, args: dict) -> List[types.TextContent]:
        """Clear all caches (in-memory, SQLite, Redis)"""
        try:
            response = "# Cache Clear Operation\n\n"
            cleared = []
            errors = []

            # Clear character fetcher cache
            if self.char_fetcher and hasattr(self.char_fetcher, 'cache_manager'):
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
            if self.char_fetcher and hasattr(self.char_fetcher, 'ninja_api'):
                ninja_api = self.char_fetcher.ninja_api
                if ninja_api and hasattr(ninja_api, 'cache_manager'):
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
            return [types.TextContent(
                type="text",
                text=f"Cache clear failed with error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            )]

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
                return [types.TextContent(
                    type="text",
                    text="Error: spell_name or skill_name is required"
                )]

            debug_log(f"Finding best supports for {spell_name} (goal: {goal}, spirit: {max_spirit})")

            # Find best combinations
            results = self.gem_synergy_calculator.find_best_combinations(
                spell_name=spell_name.lower(),
                max_spirit=max_spirit,
                num_supports=num_supports,
                optimization_goal=goal,
                top_n=top_n
            )

            if not results:
                return [types.TextContent(
                    type="text",
                    text=f"No support gem combinations found for '{spell_name}'. The spell may not be in the database or no compatible supports exist."
                )]

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
            return [types.TextContent(
                type="text",
                text=f"Error analyzing support gems: {str(e)}"
            )]

    async def _handle_explain_mechanic(self, args: dict) -> List[types.TextContent]:
        """Explain a PoE2 game mechanic"""
        try:
            mechanic_name = args.get("mechanic_name", "").lower()

            if not mechanic_name:
                # Show available mechanics from the mechanics dictionary
                response = "# Available PoE2 Mechanics\n\n"
                response += "**Common mechanics to ask about:**\n"
                response += "- Ailments: freeze, chill, ignite, shock, poison, bleed\n"
                response += "- Damage: critical strike, damage conversion, penetration\n"
                response += "- Defense: armor, evasion, energy shield, block, deflect\n"
                response += "- Crowd Control: stun, knockback, taunt\n"
                response += "- Resources: mana, life, energy shield, spirit\n"
                response += "- Other: accuracy, attack speed, cast speed\n\n"
                response += "**Usage:** Call this tool with a mechanic name (e.g., 'freeze', 'stun', 'critical strike')"
                return [types.TextContent(type="text", text=response)]

            debug_log(f"Explaining mechanic: {mechanic_name}")

            # Try direct lookup first
            mechanic = self.mechanics_kb.get_mechanic(mechanic_name)

            # If not found, try search
            if not mechanic:
                search_results = self.mechanics_kb.search_mechanics(mechanic_name)
                if search_results:
                    mechanic = search_results[0]

            # If still not found, try answering as a question
            if not mechanic:
                answer = self.mechanics_kb.answer_question(mechanic_name)
                if answer:
                    return [types.TextContent(type="text", text=answer)]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"Mechanic '{mechanic_name}' not found. Use this tool without arguments to see available mechanics."
                    )]

            # Format explanation
            response = self.mechanics_kb.format_mechanic_explanation(mechanic)

            # Enhance with official .datc64 clientstrings if available
            try:
                official_strings = await self.mechanics_kb.get_official_terminology(mechanic.name)
                if official_strings:
                    official_text = self.mechanics_kb.enhance_explanation_with_official_text(mechanic, official_strings)
                    response += official_text
            except Exception as e:
                logger.debug(f"Could not fetch official terminology: {e}")

            logger.info(f"Explained mechanic: {mechanic_name}")
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error explaining mechanic: {e}", exc_info=True)
            return [types.TextContent(
                type="text",
                text=f"Error explaining mechanic: {str(e)}"
            )]

    async def _handle_get_formula(self, args: dict) -> List[types.TextContent]:
        """Get a PoE2 calculation formula for Claude to use"""
        try:
            from .knowledge.formulas import get_formula, get_all_formula_names, FORMULAS

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
                return [types.TextContent(
                    type="text",
                    text=f"Unknown formula: {formula_type}\n\nAvailable formulas: {', '.join(get_all_formula_names())}"
                )]

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
            return [types.TextContent(
                type="text",
                text=f"Error getting formula: {str(e)}"
            )]

    async def _handle_compare_items(self, args: dict) -> List[types.TextContent]:
        """Compare two items"""
        try:
            item_a = args.get("item_a")
            item_b = args.get("item_b")
            character_data = args.get("character_data")
            build_goal = args.get("build_goal", "balanced")

            if not item_a or not item_b:
                return [types.TextContent(
                    type="text",
                    text="Error: Both item_a and item_b are required"
                )]

            debug_log(f"Comparing items (goal: {build_goal})")

            # Compare items
            report = self.gear_comparator.compare_items(
                item_a=item_a,
                item_b=item_b,
                character_data=character_data,
                build_goal=build_goal
            )

            # Format response
            response = self.gear_comparator.format_full_report(report)

            logger.info(f"Compared items: {item_a.get('name', 'Item A')} vs {item_b.get('name', 'Item B')}")
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error comparing items: {e}", exc_info=True)
            return [types.TextContent(
                type="text",
                text=f"Error comparing items: {str(e)}"
            )]

    async def _handle_analyze_damage_scaling(self, args: dict) -> List[types.TextContent]:
        """Analyze damage scaling bottlenecks"""
        try:
            character_data = args.get("character_data")
            skill_type = args.get("skill_type", "spell")

            if not character_data:
                return [types.TextContent(
                    type="text",
                    text="Error: character_data is required"
                )]

            debug_log(f"Analyzing damage scaling (skill_type: {skill_type})")

            # Analyze scaling
            recommendations = self.damage_scaling_analyzer.analyze_scaling(
                character_data=character_data,
                skill_type=skill_type
            )

            # Format response
            response = self.damage_scaling_analyzer.format_recommendations(recommendations)

            logger.info(f"Analyzed damage scaling for {skill_type}")
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error analyzing damage scaling: {e}", exc_info=True)
            return [types.TextContent(
                type="text",
                text=f"Error analyzing damage scaling: {str(e)}"
            )]

    async def _handle_check_content_readiness(self, args: dict) -> List[types.TextContent]:
        """Check if character is ready for specific content"""
        try:
            character_data = args.get("character_data")
            content = args.get("content")

            if not character_data or not content:
                return [types.TextContent(
                    type="text",
                    text="Error: Both character_data and content are required"
                )]

            debug_log(f"Checking content readiness for: {content}")

            # Check readiness
            report = self.content_readiness_checker.check_readiness(
                character_data=character_data,
                content=content
            )

            # Format response
            response = self.content_readiness_checker.format_report(report)

            logger.info(f"Content readiness check: {content} - {report.readiness.value}")
            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error checking content readiness: {e}", exc_info=True)
            return [types.TextContent(
                type="text",
                text=f"Error checking content readiness: {str(e)}"
            )]

    async def _handle_setup_trade_auth(self, args: dict) -> List[types.TextContent]:
        """Set up trade API authentication using browser automation"""
        try:
            headless = args.get("headless", False)

            # Check if playwright is installed
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                return [types.TextContent(
                    type="text",
                    text="❌ Playwright not installed!\n\n"
                         "**Installation Required:**\n"
                         "```bash\n"
                         "pip install playwright\n"
                         "playwright install chromium\n"
                         "```\n\n"
                         "After installing, use this tool again to set up authentication.\n\n"
                         "**Note:** Playwright downloads ~100MB Chromium browser (one-time)"
                )]

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
                    headless=headless,
                    args=['--start-maximized'] if not headless else []
                )

                # Create context
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080} if not headless else None
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
                            if cookie['name'] == 'POESESSID':
                                session_cookie = cookie['value']
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
                        return [types.TextContent(
                            type="text",
                            text=response + "\n\n❌ **Timeout:** Login took longer than 5 minutes.\n\n"
                                 "Please use this tool again and complete login faster."
                        )]

                    # Close browser
                    await browser.close()
                    response += "✓ Browser closed\n\n"

                    # Save to .env
                    response += "**Saving to .env file...**\n"

                    env_lines = []
                    poesessid_found = False

                    if env_file.exists():
                        with open(env_file, 'r', encoding='utf-8') as f:
                            env_lines = f.readlines()

                        # Update existing POESESSID
                        for i, line in enumerate(env_lines):
                            if line.strip().startswith('POESESSID='):
                                env_lines[i] = f'POESESSID={session_cookie}\n'
                                poesessid_found = True
                                break

                    # Add new POESESSID if not found
                    if not poesessid_found:
                        if env_lines and not env_lines[-1].endswith('\n'):
                            env_lines.append('\n')
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        env_lines.append(f'\n# Path of Exile Trade Site Session Cookie\n')
                        env_lines.append(f'# Obtained: {timestamp}\n')
                        env_lines.append(f'POESESSID={session_cookie}\n')

                    # Write back
                    with open(env_file, 'w', encoding='utf-8') as f:
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
            return [types.TextContent(
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
                     f"Traceback:\n```\n{traceback.format_exc()}\n```"
            )]

    # ============================================================================
    # TIER 1 VALIDATION TOOL HANDLERS
    # ============================================================================

    async def _handle_validate_support_combination(self, args: dict) -> List[types.TextContent]:
        """Validate if support gems can work together"""
        try:
            support_gems = args.get("support_gems", [])

            if not support_gems:
                return [types.TextContent(
                    type="text",
                    text="Error: support_gems list is required"
                )]

            # Use gem synergy calculator's validation method
            result = self.gem_synergy_calculator.validate_combination(support_gems)

            if result["valid"]:
                response = f"Valid combination: {', '.join(support_gems)}\n\n"
                response += f"Reason: {result['reason']}"
            else:
                response = f"Invalid combination\n\n"
                response += f"Reason: {result['reason']}\n\n"
                if result['conflicts']:
                    response += "Conflicting pairs:\n"
                    for conflict_a, conflict_b in result['conflicts']:
                        response += f"  - {conflict_a} + {conflict_b}\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error validating support combination: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_inspect_support_gem(self, args: dict) -> List[types.TextContent]:
        """Inspect complete details of a support gem (uses FreshDataProvider SSoT)"""
        try:
            support_name = args.get("support_name")

            if not support_name:
                return [types.TextContent(
                    type="text",
                    text="Error: support_name is required"
                )]

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

            if not support_data:
                return [types.TextContent(
                    type="text",
                    text=f"Support gem '{support_name}' not found in database"
                )]

            # Format response
            response = f"# {support_data.get('name', support_name)}\n\n"

            # Basic info
            if support_data.get('tags'):
                response += f"**Tags**: {', '.join(support_data['tags'])}\n"

            if support_data.get('tier'):
                response += f"**Tier**: {support_data['tier']}\n"

            if support_data.get('acquisition'):
                response += f"**Acquisition**: {support_data['acquisition']}\n\n"

            # Requirements
            reqs = support_data.get('requirements', {})
            if reqs:
                req_parts = []
                if 'level' in reqs:
                    req_parts.append(f"Level {reqs['level']}")
                if 'str' in reqs:
                    req_parts.append(f"{reqs['str']} Str")
                if 'dex' in reqs:
                    req_parts.append(f"{reqs['dex']} Dex")
                if 'int' in reqs:
                    req_parts.append(f"{reqs['int']} Int")
                if req_parts:
                    response += f"**Requirements**: {', '.join(req_parts)}\n\n"

            # Costs
            spirit_cost = support_data.get('spirit_cost', 0)
            if spirit_cost:
                response += f"**Spirit Cost**: {spirit_cost}\n"

            cost_multi = support_data.get('cost_multiplier')
            if cost_multi:
                response += f"**Cost Multiplier**: {cost_multi}%\n\n"

            # Effects (the meat of the support)
            effects = support_data.get('effects', {})
            if effects:
                response += "**Effects**:\n"
                for effect_name, effect_value in effects.items():
                    # Format effect names nicely
                    formatted_name = effect_name.replace('_', ' ').title()
                    if isinstance(effect_value, bool):
                        response += f"- {formatted_name}\n"
                    else:
                        response += f"- {formatted_name}: {effect_value}\n"
                response += "\n"

            # Compatibility
            req_tags = support_data.get('compatible_with', [])
            if req_tags:
                response += f"**Compatible With**: {', '.join(req_tags)}\n"

            # Restrictions
            restrictions = support_data.get('restrictions', [])
            if restrictions:
                response += f"**Restrictions**: {', '.join(restrictions)}\n"

            # Incompatibilities
            incomp = support_data.get('incompatible_with', [])
            if incomp:
                response += f"**Incompatible With**: {', '.join(incomp)}\n"

            # Notes
            notes = support_data.get('notes')
            if notes:
                response += f"\n**Notes**: {notes}\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting support gem: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_inspect_spell_gem(self, args: dict) -> List[types.TextContent]:
        """Inspect complete details of a spell gem (uses pob_complete_skills.json with full per-level data)"""
        try:
            spell_name = args.get("spell_name")

            if not spell_name:
                return [types.TextContent(
                    type="text",
                    text="Error: spell_name is required"
                )]

            # Load from pob_complete_skills.json (has full per-level stats, statSets, constantStats)
            pob_skills_file = Path(__file__).parent.parent / 'data' / 'pob_complete_skills.json'

            if not pob_skills_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: pob_complete_skills.json not found"
                )]

            with open(pob_skills_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Search for spell by name (case-insensitive) or ID
            spell_data = None
            spell_id = None
            skills = data.get('skills', {})

            for skill_id_candidate, skill in skills.items():
                if not isinstance(skill, dict):
                    continue
                # Check if name matches or ID matches
                skill_name = skill.get('name', '')
                if (skill_name.lower() == spell_name.lower() or
                    skill_id_candidate.lower() == spell_name.lower() or
                    spell_name.lower() in skill_name.lower()):
                    spell_data = skill
                    spell_id = skill_id_candidate
                    break

            if not spell_data:
                return [types.TextContent(
                    type="text",
                    text=f"Spell gem '{spell_name}' not found in PoB database"
                )]

            # Format response
            response = f"# {spell_data.get('name', spell_name)}\n\n"
            response += f"**ID**: {spell_id}\n"

            # Description
            if spell_data.get('description'):
                response += f"**Description**: {spell_data['description']}\n\n"

            # Skill types (tags)
            if spell_data.get('skillTypes'):
                response += f"**Skill Types**: {', '.join(spell_data['skillTypes'])}\n"

            # Weapon types
            if spell_data.get('weaponTypes'):
                response += f"**Weapon Types**: {', '.join(spell_data['weaponTypes'])}\n"

            # Cast time
            if spell_data.get('castTime'):
                response += f"**Cast Time**: {spell_data['castTime']}s\n\n"

            # Per-level stats (show L1, L10, L20)
            levels = spell_data.get('levels', {})
            if levels:
                response += "**Per-Level Stats**:\n"
                for level_key in ['1', '10', '20']:
                    if level_key in levels:
                        level_data = levels[level_key]
                        response += f"\nLevel {level_key}:\n"

                        # Level requirement
                        if 'levelRequirement' in level_data:
                            response += f"  - Level Requirement: {level_data['levelRequirement']}\n"

                        # Base multiplier
                        if 'baseMultiplier' in level_data:
                            response += f"  - Base Multiplier: {level_data['baseMultiplier']:.2f}\n"

                        # Mana/resource cost
                        if 'cost' in level_data:
                            costs = level_data['cost']
                            cost_parts = [f"{k}: {v}" for k, v in costs.items()]
                            response += f"  - Cost: {', '.join(cost_parts)}\n"

                        # Crit chance
                        if 'critChance' in level_data:
                            response += f"  - Crit Chance: {level_data['critChance']}%\n"

                        # Cooldown
                        if 'cooldown' in level_data:
                            response += f"  - Cooldown: {level_data['cooldown']}s\n"

                response += "\n"

            # StatSets (damage effectiveness, constantStats)
            stat_sets = spell_data.get('statSets', [])
            if stat_sets:
                response += "**Stat Sets**:\n"
                for i, stat_set in enumerate(stat_sets):
                    label = stat_set.get('label', f'Set {i+1}')
                    response += f"\n{label}:\n"

                    # Damage effectiveness
                    if 'baseEffectiveness' in stat_set:
                        base_eff = stat_set['baseEffectiveness']
                        incr_eff = stat_set.get('incrementalEffectiveness', 0)
                        response += f"  - Base Effectiveness: {base_eff}%\n"
                        if incr_eff:
                            response += f"  - Incremental Effectiveness: {incr_eff}% per level\n"

                    # Constant stats (built-in modifiers)
                    const_stats = stat_set.get('constantStats', [])
                    if const_stats:
                        response += f"  - Built-in Modifiers:\n"
                        for stat in const_stats[:10]:  # Limit to first 10
                            if isinstance(stat, list) and len(stat) >= 2:
                                stat_id, value = stat[0], stat[1]
                                response += f"    - {stat_id}: {value}\n"
                        if len(const_stats) > 10:
                            response += f"    - ... and {len(const_stats) - 10} more\n"

                response += "\n"

            # Quality stats
            quality_stats = spell_data.get('qualityStats', [])
            if quality_stats:
                response += "**Quality Stats**:\n"
                for stat in quality_stats:
                    if isinstance(stat, list) and len(stat) >= 2:
                        stat_id, value = stat[0], stat[1]
                        response += f"  - {stat_id}: {value} per 1% quality\n"
                response += "\n"

            response += f"**Data Source**: pob_complete_skills.json (Path of Building, {data.get('metadata', {}).get('extraction_date', 'Unknown date')})\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting spell gem: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_list_all_supports(self, args: dict) -> List[types.TextContent]:
        """List all support gems with filtering and sorting (uses FreshDataProvider SSoT)"""
        try:
            filter_tags = args.get("filter_tags", [])
            min_spirit = args.get("min_spirit")
            max_spirit = args.get("max_spirit")
            sort_by = args.get("sort_by", "name")
            limit = args.get("limit", 50)

            # Use FreshDataProvider as Single Source of Truth
            fresh_provider = get_fresh_data_provider()
            support_gems = fresh_provider.get_all_support_gems()

            # Extract and filter supports
            all_supports = []
            for support_id, support_data in support_gems.items():
                if not isinstance(support_data, dict) or 'display_name' not in support_data:
                    continue

                spirit_cost = support_data.get('spirit_cost', 0) or 0

                # Apply filters
                if filter_tags:
                    support_tags = [t.lower() for t in support_data.get('tags', [])]
                    if not any(ft.lower() in support_tags for ft in filter_tags):
                        continue

                if min_spirit is not None and spirit_cost < min_spirit:
                    continue
                if max_spirit is not None and spirit_cost > max_spirit:
                    continue

                # Get key effects for display
                effects = support_data.get('effects', {})
                effect_summary = ""
                if effects:
                    # Show first 2 most important effects
                    key_effects = []
                    for k, v in list(effects.items())[:2]:
                        if isinstance(v, bool):
                            key_effects.append(k.replace('_', ' ').title())
                        else:
                            key_effects.append(f"{k.replace('_', ' ').title()}: {v}")
                    effect_summary = ", ".join(key_effects)

                all_supports.append({
                    'name': support_data['display_name'],
                    'tags': support_data.get('tags', []),
                    'tier': support_data.get('tier', '?'),
                    'spirit_cost': spirit_cost,
                    'effect_summary': effect_summary
                })

            # Sort
            if sort_by == "spirit_cost":
                all_supports.sort(key=lambda x: x['spirit_cost'])
            elif sort_by == "tier":
                all_supports.sort(key=lambda x: (x['tier'] if isinstance(x['tier'], int) else 99, x['name']))
            else:  # name
                all_supports.sort(key=lambda x: x['name'])

            # Limit
            all_supports = all_supports[:limit]

            # Format response
            response = f"# Support Gems ({len(all_supports)} results)\n\n"
            for sup in all_supports:
                response += f"**{sup['name']}** (Tier {sup['tier']})\n"
                response += f"  Spirit: {sup['spirit_cost']}, Tags: {', '.join(sup['tags'][:3])}\n"
                if sup['effect_summary']:
                    response += f"  Effects: {sup['effect_summary']}\n"
                response += "\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing supports: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_list_all_spells(self, args: dict) -> List[types.TextContent]:
        """List all spell/active skill gems with filtering and sorting (uses pob_complete_skills.json)"""
        try:
            filter_element = args.get("filter_element")
            filter_tags = args.get("filter_tags", [])
            min_damage = args.get("min_damage")
            sort_by = args.get("sort_by", "name")
            limit = args.get("limit", 50)

            # Load from pob_complete_skills.json (has complete data)
            pob_skills_file = Path(__file__).parent.parent / 'data' / 'pob_complete_skills.json'

            if not pob_skills_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: pob_complete_skills.json not found"
                )]

            with open(pob_skills_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract and filter spells
            all_spells = []
            skills = data.get('skills', {})

            for skill_id, skill_data in skills.items():
                if not isinstance(skill_data, dict):
                    continue

                # Skip support gems and hidden skills
                if skill_data.get('hidden'):
                    continue

                name = skill_data.get('name', skill_id)
                skill_types = skill_data.get('skillTypes', [])

                # Apply tag filter if provided
                if filter_tags:
                    if not any(tag.lower() in [st.lower() for st in skill_types] for tag in filter_tags):
                        continue

                # Get level 20 stats (or highest available)
                levels = skill_data.get('levels', {})
                level_20_data = levels.get('20', levels.get('1', {}))

                # Get cast time
                cast_time = skill_data.get('castTime', 0)

                # Get base multiplier at level 20
                base_mult = level_20_data.get('baseMultiplier', 0)

                # Get mana cost at level 20
                cost = level_20_data.get('cost', {})
                mana_cost = cost.get('Mana', 0)

                # Detect element from skill types
                element = 'Physical'
                for st in skill_types:
                    if st in ['Fire', 'Cold', 'Lightning', 'Chaos']:
                        element = st
                        break

                # Apply element filter if provided
                if filter_element and element.lower() != filter_element.lower():
                    continue

                all_spells.append({
                    'name': name,
                    'id': skill_id,
                    'element': element,
                    'tags': skill_types,
                    'base_multiplier': base_mult,
                    'cast_time': cast_time,
                    'mana_cost': mana_cost
                })

            # Sort
            if sort_by == "base_damage" or sort_by == "base_multiplier":
                all_spells.sort(key=lambda x: x['base_multiplier'], reverse=True)
            elif sort_by == "cast_time":
                all_spells.sort(key=lambda x: x['cast_time'] if x['cast_time'] > 0 else 999)
            elif sort_by == "mana_cost":
                all_spells.sort(key=lambda x: x['mana_cost'], reverse=True)
            else:  # name
                all_spells.sort(key=lambda x: x['name'])

            # Limit
            all_spells = all_spells[:limit]

            # Format response
            response = f"# Spell Gems ({len(all_spells)} results)\n\n"
            for spell in all_spells:
                mult_str = f"{spell['base_multiplier']:.1f}x" if spell['base_multiplier'] > 0 else "N/A"
                cast_str = f"{spell['cast_time']:.2f}s" if spell['cast_time'] > 0 else "N/A"
                mana_str = f"{spell['mana_cost']}" if spell['mana_cost'] > 0 else "N/A"

                response += f"**{spell['name']}** ({spell['element']})\n"
                response += f"  Base Mult: {mult_str}, Cast: {cast_str}, Mana: {mana_str}\n"
                response += f"  Tags: {', '.join(spell['tags'][:4])}\n\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing spells: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

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
                return [types.TextContent(
                    type="text",
                    text="Error: spell_name is required"
                )]

            # Call with trace enabled
            result = self.gem_synergy_calculator.find_best_combinations(
                spell_name=spell_name,
                max_spirit=max_spirit,
                num_supports=num_supports,
                optimization_goal=goal,
                return_trace=True
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
                if trace['compatible_supports']:
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
                return [types.TextContent(
                    type="text",
                    text="Error: Trace data not available"
                )]

        except Exception as e:
            logger.error(f"Error tracing support selection: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_trace_dps_calculation(self, args: dict) -> List[types.TextContent]:
        """Trace step-by-step DPS calculation"""
        try:
            spell_name = args.get("spell_name")
            support_gems = args.get("support_gems", [])
            character_mods = args.get("character_mods", {})
            max_spirit = args.get("max_spirit", 100)

            if not spell_name:
                return [types.TextContent(
                    type="text",
                    text="Error: spell_name is required"
                )]

            if not support_gems:
                return [types.TextContent(
                    type="text",
                    text="Error: support_gems list is required"
                )]

            # Get trace
            trace = self.gem_synergy_calculator.trace_dps_calculation(
                spell_name=spell_name,
                support_names=support_gems,
                character_mods=character_mods,
                max_spirit=max_spirit
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
                if sup['more_damage'] != 0:
                    response += f"+{sup['more_damage']}% more damage "
                if sup['less_damage'] != 0:
                    response += f"{sup['less_damage']}% less damage "
                if sup['increased_damage'] != 0:
                    response += f"+{sup['increased_damage']}% increased damage "
                response += f"(Spirit: {sup['spirit_cost']})\n"
            response += "\n"

            # Spirit
            spirit = trace["spirit"]
            response += f"## Spirit Budget\n"
            response += f"- Total: {spirit['total']} / {spirit['available']}\n"
            if spirit['overflow'] > 0:
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
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_validate_build_constraints(self, args: dict) -> List[types.TextContent]:
        """Comprehensive build validation"""
        try:
            character_data = args.get("character_data", {})

            if not character_data:
                return [types.TextContent(
                    type="text",
                    text="Error: character_data is required"
                )]

            violations = []

            # Check resistances
            for res_type in ["fire_res", "cold_res", "lightning_res"]:
                res_value = character_data.get(res_type, 0)
                if res_value < -60:
                    violations.append({
                        "severity": "CRITICAL",
                        "category": "Resistances",
                        "message": f"{res_type.replace('_', ' ').title()} is below minimum (-60%): {res_value}%"
                    })
                elif res_value < 75:
                    violations.append({
                        "severity": "HIGH",
                        "category": "Resistances",
                        "message": f"{res_type.replace('_', ' ').title()} is below cap (75%): {res_value}%"
                    })
                elif res_value > 90:
                    violations.append({
                        "severity": "MEDIUM",
                        "category": "Resistances",
                        "message": f"{res_type.replace('_', ' ').title()} exceeds hard cap (90%): {res_value}%"
                    })

            # Check spirit
            spirit = character_data.get("spirit", 0)
            spirit_reserved = character_data.get("spirit_reserved", 0)
            if spirit_reserved > spirit:
                violations.append({
                    "severity": "CRITICAL",
                    "category": "Spirit",
                    "message": f"Spirit overflow: {spirit_reserved} reserved > {spirit} available"
                })

            # NOTE: PoE2 uses Spirit system, not mana reservation
            # Mana reservation validation removed - it's a PoE1 mechanic

            # Check life/ES
            life = character_data.get("life", 0)
            es = character_data.get("energy_shield", 0)
            level = character_data.get("level", 1)

            expected_min_life = 300 + (level * 50)  # Rough guideline
            if life + es < expected_min_life:
                violations.append({
                    "severity": "HIGH",
                    "category": "Survivability",
                    "message": f"Combined Life+ES ({life + es}) below recommended for level {level} ({expected_min_life})"
                })

            # Format response
            response = "# Build Constraint Validation\n\n"

            if not violations:
                response += "✓ **All constraints satisfied**\n\n"
                response += "No issues detected with:\n"
                response += "- Resistances (within -60% to 90% range)\n"
                response += "- Spirit allocation\n"
                response += "- Mana reservation\n"
                response += "- Survivability baseline\n"
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

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error validating build constraints: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_analyze_passive_tree(self, args: dict) -> List[types.TextContent]:
        """Analyze passive tree allocation with pathfinding and recommendations"""
        try:
            if not self.passive_tree_resolver:
                return [types.TextContent(
                    type="text",
                    text="Error: Passive tree resolver not initialized. PSG database may be missing."
                )]

            node_ids = args.get("node_ids", [])
            target_notable = args.get("target_notable")
            find_recommendations = args.get("find_recommendations", True)

            if not node_ids:
                return [types.TextContent(
                    type="text",
                    text="Error: node_ids is required (list of allocated passive node IDs)"
                )]

            # Analyze the build
            analysis = self.passive_tree_resolver.analyze_build(
                node_ids,
                find_recommendations=find_recommendations
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
                        response += f"**Distance:** {best_path.distance} nodes from your current build\n\n"
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
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_import_poe_ninja_url(self, args: dict) -> List[types.TextContent]:
        """Import and analyze a character from a poe.ninja URL"""
        import re

        url = args.get("url", "")

        # Parse poe.ninja URL formats:
        # https://poe.ninja/poe2/profile/AccountName/character/CharacterName
        # https://poe.ninja/poe2/builds/character/AccountName/CharacterName
        patterns = [
            r'poe\.ninja/poe2/profile/([^/]+)/character/([^/?\s]+)',
            r'poe\.ninja/poe2/builds/character/([^/]+)/([^/?\s]+)',
            r'poe\.ninja/builds/character/([^/]+)/([^/?\s]+)',
        ]

        account = None
        character = None

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                account = match.group(1)
                character = match.group(2)
                break

        if not account or not character:
            return [types.TextContent(
                type="text",
                text=f"""# URL Parse Error

Could not extract account and character from URL.

**URL provided:** `{url}`

**Expected formats:**
- `https://poe.ninja/poe2/profile/AccountName/character/CharacterName`
- `https://poe.ninja/poe2/builds/character/AccountName/CharacterName`

**Example:**
`https://poe.ninja/poe2/profile/Tomawar40-2671/character/TomawarTheFourth`
"""
            )]

        # Now fetch and analyze using existing handler
        return await self._handle_analyze_character({
            "account": account,
            "character": character,
            "league": "Abyss"
        })

    # ============================================================================
    # PASSIVE TREE DATA HANDLERS (4 new handlers)
    # ============================================================================

    async def _handle_list_all_keystones(self, args: dict) -> List[types.TextContent]:
        """List all keystone passive nodes with full stats"""
        try:
            if not self.passive_tree_resolver:
                return [types.TextContent(
                    type="text",
                    text="Error: Passive tree resolver not initialized. PSG database may be missing."
                )]

            filter_stat = args.get("filter_stat", "").lower()
            sort_by = args.get("sort_by", "name")

            # Get keystones from PassiveTreeResolver (has full stats)
            keystones = self.passive_tree_resolver.get_all_keystones()

            # Filter by stat text if provided
            if filter_stat:
                keystones = [
                    k for k in keystones
                    if k and any(filter_stat in stat.lower() for stat in k.stats)
                ]

            # Sort
            if sort_by == "stat_count":
                keystones.sort(key=lambda k: -len(k.stats) if k else 0)
            else:  # name
                keystones.sort(key=lambda k: k.name if k else "")

            # Format response
            response = f"# All Keystones ({len(keystones)} total)\n\n"
            response += "Keystones are powerful build-defining passives with major tradeoffs.\n\n"

            for keystone in keystones:
                if not keystone:
                    continue
                response += f"## {keystone.name}\n"
                for stat in keystone.stats:
                    response += f"- {stat}\n"
                response += "\n"

            if not keystones:
                response += "*No keystones found matching filter.*\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing keystones: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_inspect_keystone(self, args: dict) -> List[types.TextContent]:
        """Get complete details for a specific keystone"""
        try:
            if not self.passive_tree_resolver:
                return [types.TextContent(
                    type="text",
                    text="Error: Passive tree resolver not initialized. PSG database may be missing."
                )]

            keystone_name = args.get("keystone_name", "").strip()

            if not keystone_name:
                return [types.TextContent(
                    type="text",
                    text="Error: keystone_name is required"
                )]

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
                # List available keystones
                available = [k.name for k in keystones if k][:10]
                return [types.TextContent(
                    type="text",
                    text=f"# Keystone Not Found\n\nNo keystone matching '{keystone_name}'.\n\n**Available keystones (sample):**\n" +
                         "\n".join(f"- {name}" for name in available)
                )]

            # Format detailed response
            response = f"# {found.name}\n\n"
            response += f"**Type:** Keystone\n"
            response += f"**Node ID:** {found.node_id}\n\n"
            response += "## Stats\n"
            for stat in found.stats:
                response += f"- {stat}\n"

            if found.connections:
                response += f"\n**Connected to {len(found.connections)} nodes**\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting keystone: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_list_all_notables(self, args: dict) -> List[types.TextContent]:
        """List all notable passive nodes"""
        try:
            if not self.passive_tree_resolver:
                return [types.TextContent(
                    type="text",
                    text="Error: Passive tree resolver not initialized. PSG database may be missing."
                )]

            filter_stat = args.get("filter_stat", "").lower()
            limit = args.get("limit", 100)
            sort_by = args.get("sort_by", "name")

            # Get notables from PassiveTreeResolver
            notables = self.passive_tree_resolver.get_all_notables()

            # Filter by stat text if provided
            if filter_stat:
                notables = [
                    n for n in notables
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
                return [types.TextContent(
                    type="text",
                    text="Error: Passive tree resolver not initialized. PSG database may be missing."
                )]

            node_name = args.get("node_name", "").strip()
            node_id = args.get("node_id")

            if not node_name and node_id is None:
                return [types.TextContent(
                    type="text",
                    text="Error: Either node_name or node_id is required"
                )]

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
                return [types.TextContent(
                    type="text",
                    text=f"# Node Not Found\n\nNo passive node matching '{node_name or node_id}'.\n\nTry using `list_all_keystones` or `list_all_notables` to find available nodes."
                )]

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

            # Filter and format
            items_list = []
            for item_id, item_data in base_items.items():
                name = item_data.get('name', item_id)

                # Apply filters
                if filter_type and filter_type not in item_id.lower() and filter_type not in name.lower():
                    continue
                if filter_name and filter_name not in name.lower():
                    continue

                items_list.append({
                    'id': item_id,
                    'name': name
                })

            # Sort by name
            items_list.sort(key=lambda x: x['name'])

            # Limit
            total_count = len(items_list)
            items_list = items_list[:limit]

            # Format response
            response = f"# Base Item Types ({len(items_list)} shown, {total_count} total)\n\n"

            # Group by type prefix for better organization
            current_prefix = ""
            for item in items_list:
                # Extract category from ID
                parts = item['id'].split('/')
                prefix = parts[0] if len(parts) > 1 else ""
                if prefix != current_prefix:
                    current_prefix = prefix
                    if prefix:
                        response += f"\n## {prefix.replace('Metadata', '').replace('Items', '').strip()}\n"

                response += f"- **{item['name']}** (`{item['id']}`)\n"

            if not items_list:
                response += "*No base items found matching filters.*\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing base items: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_inspect_base_item(self, args: dict) -> List[types.TextContent]:
        """Get complete details for a specific base item"""
        try:
            item_name = args.get("item_name", "").strip()

            if not item_name:
                return [types.TextContent(
                    type="text",
                    text="Error: item_name is required"
                )]

            # Get base items from FreshDataProvider
            fresh_provider = get_fresh_data_provider()
            base_items = fresh_provider.get_all_base_items()

            # Search by name (case-insensitive)
            found = None
            found_id = None
            item_name_lower = item_name.lower()

            for item_id, item_data in base_items.items():
                name = item_data.get('name', '')
                if name.lower() == item_name_lower or item_name_lower in item_id.lower():
                    found = item_data
                    found_id = item_id
                    break

            # Try partial match
            if not found:
                for item_id, item_data in base_items.items():
                    name = item_data.get('name', '')
                    if item_name_lower in name.lower():
                        found = item_data
                        found_id = item_id
                        break

            if not found:
                return [types.TextContent(
                    type="text",
                    text=f"# Base Item Not Found\n\nNo base item matching '{item_name}'.\n\nTry using `list_all_base_items` to see available items."
                )]

            # Format detailed response
            response = f"# {found.get('name', found_id)}\n\n"
            response += f"**Internal ID:** `{found_id}`\n"

            # Show all available fields
            for key, value in found.items():
                if key not in ('name', 'id', 'row_index'):
                    response += f"**{key.replace('_', ' ').title()}:** {value}\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting base item: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # ============================================================================
    # MOD DATA TOOLS HANDLERS
    # ============================================================================

    async def _handle_inspect_mod(self, args: dict) -> List[types.TextContent]:
        """Get complete details for a specific mod"""
        try:
            mod_id = args.get("mod_id", "").strip()

            if not mod_id:
                return [types.TextContent(
                    type="text",
                    text="Error: mod_id is required"
                )]

            # Load mods from JSON file
            mods_file = DATA_DIR / "poe2_mods_extracted.json"
            if not mods_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: Mod database not found. File poe2_mods_extracted.json is missing."
                )]

            with open(mods_file, 'r', encoding='utf-8') as f:
                mods_data = json.load(f)

            # Search for mod by ID (case-insensitive)
            found = None
            mod_id_lower = mod_id.lower()

            for mod in mods_data.get('mods', []):
                if mod.get('mod_id', '').lower() == mod_id_lower:
                    found = mod
                    break

            # Try partial match if exact not found
            if not found:
                for mod in mods_data.get('mods', []):
                    if mod_id_lower in mod.get('mod_id', '').lower():
                        found = mod
                        break

            if not found:
                return [types.TextContent(
                    type="text",
                    text=f"# Mod Not Found\n\nNo mod matching '{mod_id}'.\n\nTry using `list_all_mods` or `search_mods_by_stat` to find mods."
                )]

            # Format detailed response
            response = f"# {found['mod_id']}\n\n"
            response += f"**Generation Type:** {found.get('generation_type_name', 'Unknown')}\n"
            response += f"**Level Requirement:** {found.get('level_requirement', 0)}\n"
            response += f"**Min Value:** {found.get('min_value', 0)}\n"
            response += f"**Max Value:** {found.get('max_value', 0)}\n"
            response += f"**Domain Flag:** {found.get('domain_flag', 0)}\n\n"

            # Show stats
            if found.get('stats'):
                response += "## Stats\n"
                for stat in found['stats']:
                    response += f"- Slot {stat['slot']}: Index={stat['stat_index']}, Value={stat['stat_value']}\n"
                response += "\n"

            # Show strings if available
            if found.get('strings'):
                response += "## String References\n"
                for key, value in found['strings'].items():
                    response += f"- {key}: {value}\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting mod: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_list_all_mods(self, args: dict) -> List[types.TextContent]:
        """List all mods with filtering"""
        try:
            generation_type = args.get("generation_type")
            filter_stat = args.get("filter_stat", "").strip().lower()
            limit = args.get("limit", 50)

            # Load mods from JSON file
            mods_file = DATA_DIR / "poe2_mods_extracted.json"
            if not mods_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: Mod database not found. File poe2_mods_extracted.json is missing."
                )]

            with open(mods_file, 'r', encoding='utf-8') as f:
                mods_data = json.load(f)

            # Filter mods
            filtered_mods = []
            for mod in mods_data.get('mods', []):
                # Apply generation type filter
                if generation_type and mod.get('generation_type_name') != generation_type:
                    continue

                # Apply stat filter (search in mod_id)
                if filter_stat and filter_stat not in mod.get('mod_id', '').lower():
                    continue

                filtered_mods.append(mod)

            # Sort by level requirement
            filtered_mods.sort(key=lambda m: m.get('level_requirement', 0))

            # Apply limit
            filtered_mods = filtered_mods[:limit]

            # Format response
            metadata = mods_data.get('metadata', {})
            response = f"# Mods Database\n\n"
            response += f"**Total in database:** {metadata.get('total_mods', 0)}\n"
            response += f"**Filtered results:** {len(filtered_mods)}\n"

            if generation_type:
                response += f"**Filter:** {generation_type}\n"
            if filter_stat:
                response += f"**Stat keyword:** '{filter_stat}'\n"

            response += f"\n## Mods (showing {len(filtered_mods)})\n\n"

            for mod in filtered_mods:
                response += f"### {mod['mod_id']}\n"
                response += f"- Type: {mod.get('generation_type_name', 'Unknown')}\n"
                response += f"- Level: {mod.get('level_requirement', 0)}\n"
                response += f"- Value: {mod.get('min_value', 0)} - {mod.get('max_value', 0)}\n\n"

            if len(filtered_mods) >= limit:
                response += f"\n*Showing first {limit} results. Use limit parameter to see more.*\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing mods: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_search_mods_by_stat(self, args: dict) -> List[types.TextContent]:
        """Search for mods by stat keyword"""
        try:
            stat_keyword = args.get("stat_keyword", "").strip().lower()
            generation_type = args.get("generation_type")
            limit = args.get("limit", 50)

            if not stat_keyword:
                return [types.TextContent(
                    type="text",
                    text="Error: stat_keyword is required"
                )]

            # Load mods from JSON file
            mods_file = DATA_DIR / "poe2_mods_extracted.json"
            if not mods_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: Mod database not found. File poe2_mods_extracted.json is missing."
                )]

            with open(mods_file, 'r', encoding='utf-8') as f:
                mods_data = json.load(f)

            # Search for mods matching the stat keyword
            matching_mods = []
            for mod in mods_data.get('mods', []):
                mod_id = mod.get('mod_id', '').lower()

                # Check if stat keyword is in mod_id
                if stat_keyword not in mod_id:
                    continue

                # Apply generation type filter
                if generation_type and mod.get('generation_type_name') != generation_type:
                    continue

                matching_mods.append(mod)

            # Sort by level requirement
            matching_mods.sort(key=lambda m: m.get('level_requirement', 0))

            # Apply limit
            matching_mods = matching_mods[:limit]

            # Format response
            response = f"# Mods Search: '{stat_keyword}'\n\n"
            response += f"**Found:** {len(matching_mods)} mods\n"

            if generation_type:
                response += f"**Filter:** {generation_type}\n"

            response += f"\n## Results\n\n"

            if not matching_mods:
                response += "*No mods found matching your search.*\n"
                response += "\nTry different keywords like:\n"
                response += "- 'life' for life mods\n"
                response += "- 'fire' for fire-related mods\n"
                response += "- 'resist' for resistance mods\n"
                response += "- 'damage' for damage mods\n"
            else:
                for mod in matching_mods:
                    response += f"### {mod['mod_id']}\n"
                    response += f"- Type: {mod.get('generation_type_name', 'Unknown')}\n"
                    response += f"- Level: {mod.get('level_requirement', 0)}\n"
                    response += f"- Value: {mod.get('min_value', 0)}"
                    if mod.get('max_value', 0) > 0:
                        response += f" - {mod.get('max_value', 0)}"
                    response += "\n\n"

            if len(matching_mods) >= limit:
                response += f"\n*Showing first {limit} results. Use limit parameter to see more.*\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error searching mods by stat: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_mod_tiers(self, args: dict) -> List[types.TextContent]:
        """Get all tiers of a mod family"""
        try:
            mod_base = args.get("mod_base", "").strip()

            if not mod_base:
                return [types.TextContent(
                    type="text",
                    text="Error: mod_base is required"
                )]

            # Load mods from JSON file
            mods_file = DATA_DIR / "poe2_mods_extracted.json"
            if not mods_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: Mod database not found. File poe2_mods_extracted.json is missing."
                )]

            with open(mods_file, 'r', encoding='utf-8') as f:
                mods_data = json.load(f)

            # Find all mods matching the base name
            tier_mods = []
            mod_base_lower = mod_base.lower()

            for mod in mods_data.get('mods', []):
                mod_id = mod.get('mod_id', '')
                mod_id_lower = mod_id.lower()

                # Check if this mod belongs to the family
                # Match pattern: base name followed by optional number
                if mod_id_lower.startswith(mod_base_lower):
                    # Extract the part after base name
                    suffix = mod_id[len(mod_base):]
                    # Check if it's empty or a number
                    if not suffix or suffix.isdigit():
                        tier_mods.append(mod)

            if not tier_mods:
                return [types.TextContent(
                    type="text",
                    text=f"# No Mod Tiers Found\n\nNo mods found with base name '{mod_base}'.\n\nTry using `list_all_mods` to browse available mods."
                )]

            # Sort by level requirement (which usually correlates with tier)
            tier_mods.sort(key=lambda m: m.get('level_requirement', 0))

            # Format response
            response = f"# Mod Tiers: {mod_base}\n\n"
            response += f"**Total tiers found:** {len(tier_mods)}\n"

            # Show generation type if consistent
            gen_types = set(m.get('generation_type_name') for m in tier_mods)
            if len(gen_types) == 1:
                response += f"**Generation Type:** {gen_types.pop()}\n"

            response += "\n## Tier Progression\n\n"

            for i, mod in enumerate(tier_mods, 1):
                tier_label = f"T{i}"
                response += f"### {tier_label}: {mod['mod_id']}\n"
                response += f"- Level Requirement: {mod.get('level_requirement', 0)}\n"
                response += f"- Value: {mod.get('min_value', 0)}"
                if mod.get('max_value', 0) > 0:
                    response += f" - {mod.get('max_value', 0)}"
                response += "\n"
                response += f"- Type: {mod.get('generation_type_name', 'Unknown')}\n\n"

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
                return [types.TextContent(
                    type="text",
                    text="Error: mod_ids list is required"
                )]

            # Load mods from JSON file
            mods_file = DATA_DIR / "poe2_mods_extracted.json"
            if not mods_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: Mod database not found. File poe2_mods_extracted.json is missing."
                )]

            with open(mods_file, 'r', encoding='utf-8') as f:
                mods_data = json.load(f)

            # Create a lookup dictionary
            mods_by_id = {m['mod_id']: m for m in mods_data.get('mods', [])}

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
                mod_id = mod.get('mod_id', '')
                # Extract family by removing trailing digits
                family = mod_id.rstrip('0123456789')
                if not family:
                    family = mod_id

                if family in families_seen:
                    conflict_mod = families_seen[family]
                    conflicts.append((conflict_mod, mod_id))
                    errors.append(f"Mod family conflict: {conflict_mod} and {mod_id} are both from '{family}' family")
                else:
                    families_seen[family] = mod_id

            # Check prefix/suffix counts
            prefix_count = sum(1 for m in found_mods if m.get('generation_type_name') == 'PREFIX')
            suffix_count = sum(1 for m in found_mods if m.get('generation_type_name') == 'SUFFIX')
            implicit_count = sum(1 for m in found_mods if m.get('generation_type_name') == 'IMPLICIT')
            corrupted_count = sum(1 for m in found_mods if m.get('generation_type_name') == 'CORRUPTED')

            MAX_PREFIXES = 3
            MAX_SUFFIXES = 3
            MAX_IMPLICITS = 2

            if prefix_count > MAX_PREFIXES:
                errors.append(f"Too many prefixes: {prefix_count} (max {MAX_PREFIXES})")

            if suffix_count > MAX_SUFFIXES:
                errors.append(f"Too many suffixes: {suffix_count} (max {MAX_SUFFIXES})")

            if implicit_count > MAX_IMPLICITS:
                warnings.append(f"High implicit count: {implicit_count} (typical max {MAX_IMPLICITS})")

            # Check level requirements
            for mod in found_mods:
                mod_level = mod.get('level_requirement', 0)
                if mod_level > item_level:
                    warnings.append(f"{mod.get('mod_id')} requires ilvl {mod_level}, item is ilvl {item_level}")

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
        """Get all mods that could roll on an item by generation type"""
        try:
            generation_type = args.get("generation_type", "").upper()
            max_level = args.get("max_level", 100)
            limit = min(args.get("limit", 100), 200)  # Cap at 200

            if generation_type not in ["PREFIX", "SUFFIX"]:
                return [types.TextContent(
                    type="text",
                    text="Error: generation_type must be 'PREFIX' or 'SUFFIX'"
                )]

            # Load mods from JSON file
            mods_file = DATA_DIR / "poe2_mods_extracted.json"
            if not mods_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: Mod database not found. File poe2_mods_extracted.json is missing."
                )]

            with open(mods_file, 'r', encoding='utf-8') as f:
                mods_data = json.load(f)

            # Filter mods
            available_mods = []
            for mod in mods_data.get('mods', []):
                if mod.get('generation_type_name') != generation_type:
                    continue
                if mod.get('level_requirement', 0) > max_level:
                    continue
                available_mods.append(mod)

            # Sort by level requirement
            available_mods.sort(key=lambda m: m.get('level_requirement', 0))

            # Group by mod family for better presentation
            families = {}
            for mod in available_mods:
                mod_id = mod.get('mod_id', '')
                family = mod_id.rstrip('0123456789')
                if not family:
                    family = mod_id

                if family not in families:
                    families[family] = []
                families[family].append(mod)

            # Apply limit to families
            limited_families = list(families.items())[:limit]

            # Format response
            response = f"# Available {generation_type} Mods\n\n"
            response += f"**Total families:** {len(families)}\n"
            response += f"**Total mods:** {len(available_mods)}\n"
            response += f"**Max level filter:** {max_level}\n\n"

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

    def _format_character_analysis(self, character_data: dict, analysis: dict, recommendations: str, passive_analysis=None) -> str:
        """Format character analysis response"""
        response = f"""# Character Analysis: {character_data.get('name', 'Unknown')}

## Basic Info
- Class: {character_data.get('class', 'Unknown')}
- Level: {character_data.get('level', '?')}
- Ascendancy: {character_data.get('ascendancy', 'None')}

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
"""

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

            if not passive_analysis.is_connected:
                response += "- WARNING: Build has disconnected nodes!\n"

            # Show nearest unallocated notables
            if passive_analysis.nearest_notables:
                response += "\n### Nearest Unallocated Notables\n"
                for node, dist in passive_analysis.nearest_notables[:5]:
                    response += f"- {node.name} ({dist} nodes away)\n"
                    if node.stats:
                        response += f"  - {node.stats[0]}\n"

        if recommendations:
            response += f"\n## AI Recommendations\n{recommendations}"

        return response

    def _format_gear_recommendations(self, recommendations: dict) -> str:
        """Format gear recommendations"""
        response = "# Gear Optimization Recommendations\n\n"

        priority_upgrades = recommendations.get('priority_upgrades', [])
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

        allocations = recommendations.get('suggested_allocations', [])
        if allocations:
            response += "## Suggested Allocations\n"
            for node in allocations:
                response += f"- {node['name']}: {node['benefit']}\n"

        respecs = recommendations.get('suggested_respecs', [])
        if respecs:
            response += "\n## Suggested Respecs\n"
            for respec in respecs:
                response += f"- Remove {respec['current']}, allocate {respec['suggested']}\n"
                response += f"  Benefit: {respec['benefit']}\n"

        return response

    def _format_skill_recommendations(self, recommendations: dict) -> str:
        """Format skill recommendations"""
        response = "# Skill Setup Optimization\n\n"

        setups = recommendations.get('suggested_setups', [])
        for i, setup in enumerate(setups, 1):
            response += f"## Setup {i}: {setup['skill_name']}\n"
            response += f"Links: {', '.join(setup['supports'])}\n"
            response += f"Priority: {setup['priority']}\n\n"

        return response

    def _format_build_comparison(self, comparison: dict) -> str:
        """Format build comparison"""
        response = "# Build Comparison\n\n"

        for metric in comparison.get('metrics', []):
            response += f"## {metric['name']}\n"
            for build_result in metric['results']:
                response += f"- {build_result['build_name']}: {build_result['value']}\n"
            response += "\n"

        return response

    def _format_dps_breakdown(self, breakdown: dict) -> str:
        """Format DPS breakdown"""
        response = f"""# DPS Breakdown

## Total DPS: {breakdown.get('total_dps', 0):,.0f}

## Damage by Type
"""
        for dmg_type, amount in breakdown.get('by_type', {}).items():
            response += f"- {dmg_type}: {amount:,.0f} ({amount/breakdown.get('total_dps', 1)*100:.1f}%)\n"

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
            usage_pct = (count / pool.get('count', 1)) * 100
            response += f"- **{unique}**: Used by {usage_pct:.0f}% of top players\n"

        response += f"""

### Your Current Uniques
{self._format_list([f"{slot}: {item}" for slot, item in gear_comp.get("user_uniques", {}).items()])}

## 💎 Skill Setup Analysis

### Popular Support Gems (Top Players)
"""
        common_supports = skill_comp.get("common_supports_in_top_players", {})
        for support, count in list(common_supports.items())[:8]:
            usage_pct = (count / pool.get('count', 1)) * 100
            response += f"- **{support}**: {usage_pct:.0f}% usage rate\n"

        response += f"""

### Your Main Skills
{self._format_list(skill_comp.get("user_main_skills", []))}

## 📊 Stat Comparison

### Key Stats vs Top Players
"""

        important_stats = ["life", "energyShield", "mana", "fireResistance", "coldResistance", "lightningResistance"]
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

    def _format_trade_search_results(self, results: Dict[str, List[Dict]], character_needs: Dict, max_price: Optional[int]) -> str:
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
                        notification_options=notification_opts,
                        experimental_capabilities={}
                    )
                )

                debug_log("Running MCP server...")
                await self.server.run(
                    read_stream,
                    write_stream,
                    init_options
                )
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
