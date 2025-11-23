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
    from .config import settings
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
except ImportError:
    # Fallback for direct execution
    from src.config import settings
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

    def _register_tools(self):
        """Register MCP tools"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List all available tools"""
            return [
                types.Tool(
                    name="analyze_character",
                    description="Analyze a PoE2 character by account and character name. Fetches real data from poe.ninja API and returns comprehensive build analysis.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {
                                "type": "string",
                                "description": "Path of Exile account name"
                            },
                            "character": {
                                "type": "string",
                                "description": "Character name to analyze"
                            },
                            "league": {
                                "type": "string",
                                "description": "League name (e.g., 'Abyss', 'Standard')",
                                "default": "Abyss"
                            },
                            "include_recommendations": {
                                "type": "boolean",
                                "description": "Include AI-powered recommendations",
                                "default": True
                            }
                        },
                        "required": ["account", "character"]
                    }
                ),
                types.Tool(
                    name="natural_language_query",
                    description="Ask questions about builds in natural language. Examples: 'How can I increase my DPS?', 'What gear should I upgrade?'",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language question about the build"
                            },
                            "character_context": {
                                "type": "object",
                                "description": "Character data for context (optional)"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="optimize_gear",
                    description="Get gear upgrade recommendations with budget tiers and priority ranking",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": "Character data to optimize"
                            },
                            "budget": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "unlimited"],
                                "description": "Budget tier for recommendations",
                                "default": "medium"
                            },
                            "goal": {
                                "type": "string",
                                "enum": ["dps", "defense", "balanced", "boss_damage", "clear_speed"],
                                "description": "Optimization goal",
                                "default": "balanced"
                            }
                        },
                        "required": ["character_data"]
                    }
                ),
                types.Tool(
                    name="optimize_passive_tree",
                    description="Optimize passive skill tree allocation with respec recommendations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": "Character data with current passive tree"
                            },
                            "available_points": {
                                "type": "integer",
                                "description": "Number of unallocated passive points"
                            },
                            "allow_respec": {
                                "type": "boolean",
                                "description": "Allow passive tree respec suggestions",
                                "default": False
                            },
                            "goal": {
                                "type": "string",
                                "enum": ["damage", "defense", "utility", "balanced"],
                                "description": "Optimization priority",
                                "default": "balanced"
                            }
                        },
                        "required": ["character_data"]
                    }
                ),
                types.Tool(
                    name="optimize_skills",
                    description="Optimize skill gem setup and links",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": "Character data with current skill setup"
                            },
                            "goal": {
                                "type": "string",
                                "enum": ["dps", "clear_speed", "single_target", "balanced"],
                                "description": "Optimization goal",
                                "default": "balanced"
                            }
                        },
                        "required": ["character_data"]
                    }
                ),
                types.Tool(
                    name="compare_builds",
                    description="Compare multiple builds and highlight differences",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "builds": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "List of builds to compare"
                            },
                            "comparison_metrics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Metrics to compare (dps, defense, cost, etc.)",
                                "default": ["overall_score", "dps", "defense"]
                            }
                        },
                        "required": ["builds"]
                    }
                ),
                types.Tool(
                    name="import_pob",
                    description="Import a Path of Building build code for analysis",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pob_code": {
                                "type": "string",
                                "description": "Path of Building build code (base64 encoded)"
                            }
                        },
                        "required": ["pob_code"]
                    }
                ),
                types.Tool(
                    name="export_pob",
                    description="Export character to Path of Building format",
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
                    description="Get Path of Building import code for a character from poe.ninja. Fetches a ready-to-use PoB code that can be imported into Path of Building application.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {
                                "type": "string",
                                "description": "Path of Exile account name"
                            },
                            "character": {
                                "type": "string",
                                "description": "Character name"
                            }
                        },
                        "required": ["account", "character"]
                    }
                ),
                types.Tool(
                    name="search_items",
                    description="Search for items in the game database",
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
                    name="calculate_dps",
                    description="Calculate detailed DPS breakdown for a character",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": "Character data for DPS calculation"
                            },
                            "include_buffs": {
                                "type": "boolean",
                                "description": "Include temporary buffs in calculation",
                                "default": True
                            }
                        },
                        "required": ["character_data"]
                    }
                ),
                types.Tool(
                    name="compare_to_top_players",
                    description="Compare your character against top ladder players using the same skills. Identifies what high-DPS players do differently in terms of gear, passives, and skill setups.",
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
                                "description": "League name (default: Standard)",
                                "default": "Standard"
                            },
                            "min_level": {
                                "type": "integer",
                                "description": "Minimum level of players to compare against (default: your level)"
                            },
                            "top_player_limit": {
                                "type": "integer",
                                "description": "Number of top players to compare against (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["account_name", "character_name"]
                    }
                ),
                types.Tool(
                    name="search_trade_items",
                    description="Search Path of Exile 2 trade market for items that improve your character. Finds gear to address deficiencies like missing resistances, low life/ES, or needed stats. Requires POESESSID cookie (use setup_trade_auth tool first).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "league": {
                                "type": "string",
                                "description": "League name (e.g., 'Abyss', 'Standard')",
                                "default": "Standard"
                            },
                            "character_needs": {
                                "type": "object",
                                "description": "Character deficiencies to address",
                                "properties": {
                                    "missing_resistances": {
                                        "type": "object",
                                        "description": "Resistances to fix (e.g., {\"fire\": 10, \"cold\": 15})"
                                    },
                                    "needs_life": {
                                        "type": "boolean",
                                        "description": "Whether character needs more life"
                                    },
                                    "needs_es": {
                                        "type": "boolean",
                                        "description": "Whether character needs more energy shield"
                                    },
                                    "item_slots": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Which item slots to search (charm, amulet, helmet, etc.)"
                                    }
                                }
                            },
                            "max_price_chaos": {
                                "type": "integer",
                                "description": "Maximum price in chaos orbs (optional)"
                            }
                        },
                        "required": ["league", "character_needs"]
                    }
                ),
                # PHASE 1-3 CALCULATOR TOOLS
                types.Tool(
                    name="detect_character_weaknesses",
                    description="Automatically detect build weaknesses including resistance gaps, low life/ES, Spirit overflow, overcapped stats, and missing defense layers. Returns prioritized list with actionable recommendations. Supports two modes: provide account/character to fetch from API, or provide character_data for testing.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "Account name (use with 'character')"},
                            "character": {"type": "string", "description": "Character name (use with 'account')"},
                            "league": {
                                "type": "string",
                                "description": "League name (e.g., 'Abyss', 'Standard')",
                                "default": "Abyss"
                            },
                            "character_data": {
                                "type": "object",
                                "description": "Character stats (alternative to account/character for testing)",
                                "properties": {
                                    "level": {"type": "number"},
                                    "class": {"type": "string"},
                                    "life": {"type": "number"},
                                    "energy_shield": {"type": "number"},
                                    "fire_res": {"type": "number"},
                                    "cold_res": {"type": "number"},
                                    "lightning_res": {"type": "number"},
                                    "chaos_res": {"type": "number"}
                                }
                            },
                            "severity_filter": {
                                "type": "string",
                                "enum": ["all", "critical", "high", "medium"],
                                "description": "Filter by severity level",
                                "default": "all"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="evaluate_gear_upgrade",
                    description="Evaluate the exact value of a gear upgrade. Calculates EHP changes, resistance impact, and priority score. Returns upgrade recommendation (STRONG_UPGRADE/UPGRADE/SKIP/DOWNGRADE).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "Account name"},
                            "character": {"type": "string", "description": "Character name"},
                            "item_slot": {
                                "type": "string",
                                "enum": ["helmet", "body", "gloves", "boots", "amulet", "ring", "belt", "weapon", "charm"],
                                "description": "Item slot to evaluate"
                            },
                            "upgrade_stats": {
                                "type": "object",
                                "description": "Stats of the potential upgrade item"
                            },
                            "price_chaos": {"type": "number", "description": "Price in chaos orbs (optional)"}
                        },
                        "required": ["account", "character", "item_slot", "upgrade_stats"]
                    }
                ),
                types.Tool(
                    name="calculate_character_ehp",
                    description="Calculate Effective Health Pool for all damage types (physical, fire, cold, lightning, chaos). Uses PoE2 formulas including layered defenses, armor scaling, and chaos double-damage vs ES. Supports two modes: provide account/character to fetch from API, or provide character_data for testing.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "Account name (use with 'character')"},
                            "character": {"type": "string", "description": "Character name (use with 'account')"},
                            "league": {
                                "type": "string",
                                "description": "League name (e.g., 'Abyss', 'Standard')",
                                "default": "Abyss"
                            },
                            "character_data": {
                                "type": "object",
                                "description": "Character stats (alternative to account/character for testing)",
                                "properties": {
                                    "life": {"type": "number"},
                                    "energy_shield": {"type": "number"},
                                    "fire_res": {"type": "number"},
                                    "cold_res": {"type": "number"},
                                    "lightning_res": {"type": "number"},
                                    "chaos_res": {"type": "number"},
                                    "armor": {"type": "number"},
                                    "evasion": {"type": "number"},
                                    "block_chance": {"type": "number"}
                                }
                            },
                            "expected_hit_size": {
                                "type": "number",
                                "description": "Expected incoming hit size for armor calculations",
                                "default": 1000
                            }
                        }
                    }
                ),
                types.Tool(
                    name="analyze_spirit_usage",
                    description="Analyze PoE2 Spirit system usage. Detects overflow, shows reservations, suggests optimizations. Returns current Spirit status and recommendations. Supports two modes: provide account/character to fetch from API, or provide character_data for testing.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "Account name (use with 'character')"},
                            "character": {"type": "string", "description": "Character name (use with 'account')"},
                            "character_data": {
                                "type": "object",
                                "description": "Character stats (alternative to account/character for testing)",
                                "properties": {
                                    "spirit": {"type": "number"},
                                    "spirit_reserved": {"type": "number"}
                                }
                            }
                        }
                    }
                ),
                types.Tool(
                    name="analyze_stun_vulnerability",
                    description="Analyze character's vulnerability to PoE2 stun mechanics (Light Stun and Heavy Stun). Supports two modes: provide account/character to fetch from API, or provide character_data for testing.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "Account name (use with 'character')"},
                            "character": {"type": "string", "description": "Character name (use with 'account')"},
                            "character_data": {
                                "type": "object",
                                "description": "Character stats (alternative to account/character for testing)",
                                "properties": {
                                    "life": {"type": "number"},
                                    "energy_shield": {"type": "number"}
                                }
                            },
                            "enemy_damage": {
                                "type": "number",
                                "description": "Enemy hit damage for analysis",
                                "default": 500
                            }
                        }
                    }
                ),
                types.Tool(
                    name="optimize_build_metrics",
                    description="Comprehensive build optimization using all calculators. Supports two modes: provide account/character to fetch from API, or provide character_data for testing. Combines weakness detection, EHP calculation, spirit analysis, and stun vulnerability.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "Account name (use with 'character')"},
                            "character": {"type": "string", "description": "Character name (use with 'account')"},
                            "league": {"type": "string", "description": "League name", "default": "Standard"},
                            "character_data": {
                                "type": "object",
                                "description": "Character stats (alternative to account/character for testing)",
                                "properties": {
                                    "level": {"type": "number"},
                                    "class": {"type": "string"},
                                    "life": {"type": "number"},
                                    "energy_shield": {"type": "number"},
                                    "mana": {"type": "number"},
                                    "spirit": {"type": "number"},
                                    "spirit_reserved": {"type": "number"},
                                    "fire_res": {"type": "number"},
                                    "cold_res": {"type": "number"},
                                    "lightning_res": {"type": "number"},
                                    "chaos_res": {"type": "number"},
                                    "armor": {"type": "number"},
                                    "evasion": {"type": "number"},
                                    "block_chance": {"type": "number"}
                                }
                            },
                            "budget_chaos": {
                                "type": "number",
                                "description": "Budget for upgrades in chaos orbs",
                                "default": 100
                            },
                            "focus": {
                                "type": "string",
                                "enum": ["defense", "offense", "balanced"],
                                "description": "Optimization focus",
                                "default": "balanced"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="health_check",
                    description="Run diagnostic checks on the MCP server to verify all systems are operational. Checks database status, API connectivity, calculator initialization, and configuration validity.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "verbose": {
                                "type": "boolean",
                                "description": "Show detailed diagnostic information",
                                "default": False
                            }
                        }
                    }
                ),
                # NEW ENHANCEMENT FEATURES
                types.Tool(
                    name="find_best_supports",
                    description="Find the best support gem combinations for a spell. Calculates optimal DPS based on support gem synergy, considers spirit costs, and provides detailed analysis. Uses real support gem database.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spell_name": {
                                "type": "string",
                                "description": "Name of the spell gem (e.g., 'Fireball', 'Arc', 'Freezing Pulse')"
                            },
                            "max_spirit": {
                                "type": "integer",
                                "description": "Maximum spirit available for supports",
                                "default": 100
                            },
                            "num_supports": {
                                "type": "integer",
                                "description": "Number of support gems to find (1-6)",
                                "default": 5
                            },
                            "goal": {
                                "type": "string",
                                "enum": ["dps", "efficiency", "balanced", "utility"],
                                "description": "Optimization goal: dps (maximum damage), efficiency (damage per spirit), balanced, or utility",
                                "default": "dps"
                            },
                            "top_n": {
                                "type": "integer",
                                "description": "Number of top combinations to return",
                                "default": 5
                            }
                        },
                        "required": ["spell_name"]
                    }
                ),
                types.Tool(
                    name="explain_mechanic",
                    description="Explain Path of Exile 2 game mechanics in detail. Covers ailments (freeze, shock, chill, ignite), crowd control (stun, heavy stun), damage scaling, critical strikes, spirit system, and more. Includes formulas and examples.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "mechanic_name": {
                                "type": "string",
                                "description": "Name of mechanic to explain (e.g., 'freeze', 'stun', 'critical strike', 'spirit'). Can also be a question like 'How does freeze work?'"
                            }
                        },
                        "required": ["mechanic_name"]
                    }
                ),
                types.Tool(
                    name="compare_items",
                    description="Compare two items to determine which is better for your build. Analyzes offense, defense, resistances, and utility stats. Provides detailed reasoning and confidence score. Supports build goal customization (dps/defense/balanced).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "item_a": {
                                "type": "object",
                                "description": "First item to compare (include name and stats)"
                            },
                            "item_b": {
                                "type": "object",
                                "description": "Second item to compare (include name and stats)"
                            },
                            "character_data": {
                                "type": "object",
                                "description": "Current character stats for context (optional but recommended)"
                            },
                            "build_goal": {
                                "type": "string",
                                "enum": ["dps", "defense", "balanced"],
                                "description": "Build goal for comparison",
                                "default": "balanced"
                            }
                        },
                        "required": ["item_a", "item_b"]
                    }
                ),
                types.Tool(
                    name="analyze_damage_scaling",
                    description="Analyze ALL damage scaling vectors and identify bottlenecks. Examines increased damage (diminishing returns), more multipliers (support gems), critical strike scaling, added flat damage, cast/attack speed. Provides prioritized recommendations for damage improvements.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": "Character damage stats and modifiers"
                            },
                            "skill_type": {
                                "type": "string",
                                "enum": ["spell", "attack", "dot"],
                                "description": "Type of skill being analyzed",
                                "default": "spell"
                            }
                        },
                        "required": ["character_data"]
                    }
                ),
                types.Tool(
                    name="check_content_readiness",
                    description="Check if character is ready for specific content (campaign, maps T1-T16+, endgame bosses, pinnacle bosses). Validates life, EHP, resistances, DPS requirements. Identifies critical gaps and provides upgrade priorities.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": "Character stats to evaluate"
                            },
                            "content": {
                                "type": "string",
                                "enum": ["campaign", "early_maps", "mid_maps", "high_maps", "pinnacle_maps", "normal_bosses", "pinnacle_bosses"],
                                "description": "Content to check readiness for"
                            }
                        },
                        "required": ["character_data", "content"]
                    }
                ),
                types.Tool(
                    name="clear_cache",
                    description="Clear all cached character data (in-memory, SQLite, Redis). Use this when character data seems stale or after code updates.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="setup_trade_auth",
                    description="Set up Path of Exile trade API authentication by opening a browser and automatically extracting your session cookie. This is required before using search_trade_items. The tool will open a browser window where you log into pathofexile.com, then automatically detect and save your POESESSID cookie. Takes 2-3 minutes.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "headless": {
                                "type": "boolean",
                                "description": "Run browser in headless mode (not recommended - you need to see login page)",
                                "default": False
                            }
                        }
                    }
                ),
                # TIER 1 VALIDATION TOOLS
                types.Tool(
                    name="validate_support_combination",
                    description="Validate if support gems can work together. Checks for incompatibilities like Faster+Slower Projectiles. Returns validation result with detailed conflict information.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "support_gems": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of support gem names to validate"
                            }
                        },
                        "required": ["support_gems"]
                    }
                ),
                types.Tool(
                    name="inspect_support_gem",
                    description="View complete details for a support gem including tags, effects, incompatibilities, and spirit cost. Useful for verifying data quality and understanding gem mechanics.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "support_name": {
                                "type": "string",
                                "description": "Name of the support gem to inspect"
                            }
                        },
                        "required": ["support_name"]
                    }
                ),
                types.Tool(
                    name="inspect_spell_gem",
                    description="View complete details for a spell gem including tags, base damage, cast time, mana cost, and spirit cost. Useful for comparing spells and verifying data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spell_name": {
                                "type": "string",
                                "description": "Name of the spell gem to inspect"
                            }
                        },
                        "required": ["spell_name"]
                    }
                ),
                types.Tool(
                    name="list_all_supports",
                    description="List all available support gems with filtering and sorting options. Returns support names, tags, spirit costs, and damage multipliers.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by tags (e.g., ['projectile', 'fire'])"
                            },
                            "min_spirit": {
                                "type": "integer",
                                "description": "Minimum spirit cost filter"
                            },
                            "max_spirit": {
                                "type": "integer",
                                "description": "Maximum spirit cost filter"
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["name", "spirit_cost", "damage_multiplier"],
                                "description": "Sort results by field",
                                "default": "name"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 50
                            }
                        }
                    }
                ),
                types.Tool(
                    name="list_all_spells",
                    description="List all available spell gems with filtering and sorting options. Returns spell names, elements, tags, base damage, and cast times.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_element": {
                                "type": "string",
                                "enum": ["fire", "cold", "lightning", "physical", "chaos"],
                                "description": "Filter by element type"
                            },
                            "filter_tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by tags (e.g., ['projectile', 'aoe'])"
                            },
                            "min_damage": {
                                "type": "number",
                                "description": "Minimum average base damage filter"
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["name", "base_damage", "cast_time", "dps"],
                                "description": "Sort results by field",
                                "default": "name"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 50
                            }
                        }
                    }
                ),
                # TIER 2 DEBUGGING TOOLS
                types.Tool(
                    name="trace_support_selection",
                    description="Trace how find_best_supports selected support gems. Shows filtering steps, number of combinations tested, and why specific supports were chosen.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spell_name": {
                                "type": "string",
                                "description": "Name of the spell gem"
                            },
                            "max_spirit": {
                                "type": "integer",
                                "description": "Maximum spirit available",
                                "default": 100
                            },
                            "num_supports": {
                                "type": "integer",
                                "description": "Number of support gems to find",
                                "default": 5
                            },
                            "goal": {
                                "type": "string",
                                "enum": ["dps", "efficiency", "balanced"],
                                "description": "Optimization goal",
                                "default": "dps"
                            }
                        },
                        "required": ["spell_name"]
                    }
                ),
                types.Tool(
                    name="trace_dps_calculation",
                    description="Show step-by-step DPS calculation math for a spell + support combination. Breaks down base damage, more multipliers, increased modifiers, and final DPS.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spell_name": {
                                "type": "string",
                                "description": "Name of the spell gem"
                            },
                            "support_gems": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of support gem names"
                            },
                            "character_mods": {
                                "type": "object",
                                "description": "Character modifiers (increased_damage, etc.)",
                                "default": {}
                            },
                            "max_spirit": {
                                "type": "integer",
                                "description": "Maximum spirit available",
                                "default": 100
                            }
                        },
                        "required": ["spell_name", "support_gems"]
                    }
                ),
                types.Tool(
                    name="validate_build_constraints",
                    description="Comprehensive build validation checking all game constraints: resistances, spirit overflow, mana reservation, stat requirements, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "character_data": {
                                "type": "object",
                                "description": "Complete character stats and configuration"
                            }
                        },
                        "required": ["character_data"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
            """Handle tool calls"""
            debug_log(f"Tool called: {name}")
            debug_log(f"Arguments: {arguments}")
            try:
                if name == "analyze_character":
                    return await self._handle_analyze_character(arguments)
                elif name == "natural_language_query":
                    return await self._handle_nl_query(arguments)
                elif name == "optimize_gear":
                    return await self._handle_optimize_gear(arguments)
                elif name == "optimize_passive_tree":
                    return await self._handle_optimize_passives(arguments)
                elif name == "optimize_skills":
                    return await self._handle_optimize_skills(arguments)
                elif name == "compare_builds":
                    return await self._handle_compare_builds(arguments)
                elif name == "import_pob":
                    return await self._handle_import_pob(arguments)
                elif name == "export_pob":
                    return await self._handle_export_pob(arguments)
                elif name == "get_pob_code":
                    return await self._handle_get_pob_code(arguments)
                elif name == "search_items":
                    return await self._handle_search_items(arguments)
                elif name == "calculate_dps":
                    return await self._handle_calculate_dps(arguments)
                elif name == "compare_to_top_players":
                    return await self._handle_compare_to_top_players(arguments)
                elif name == "search_trade_items":
                    return await self._handle_search_trade_items(arguments)
                # PHASE 1-3 CALCULATOR HANDLERS
                elif name == "detect_character_weaknesses":
                    return await self._handle_detect_weaknesses(arguments)
                elif name == "evaluate_gear_upgrade":
                    return await self._handle_evaluate_upgrade(arguments)
                elif name == "calculate_character_ehp":
                    return await self._handle_calculate_ehp(arguments)
                elif name == "analyze_spirit_usage":
                    return await self._handle_analyze_spirit(arguments)
                elif name == "analyze_stun_vulnerability":
                    return await self._handle_analyze_stun(arguments)
                elif name == "optimize_build_metrics":
                    return await self._handle_optimize_metrics(arguments)
                elif name == "health_check":
                    return await self._handle_health_check(arguments)
                elif name == "clear_cache":
                    return await self._handle_clear_cache(arguments)
                # NEW ENHANCEMENT HANDLERS
                elif name == "find_best_supports":
                    return await self._handle_find_best_supports(arguments)
                elif name == "explain_mechanic":
                    return await self._handle_explain_mechanic(arguments)
                elif name == "compare_items":
                    return await self._handle_compare_items(arguments)
                elif name == "analyze_damage_scaling":
                    return await self._handle_analyze_damage_scaling(arguments)
                elif name == "check_content_readiness":
                    return await self._handle_check_content_readiness(arguments)
                elif name == "setup_trade_auth":
                    return await self._handle_setup_trade_auth(arguments)
                # TIER 1 VALIDATION TOOLS
                elif name == "validate_support_combination":
                    return await self._handle_validate_support_combination(arguments)
                elif name == "inspect_support_gem":
                    return await self._handle_inspect_support_gem(arguments)
                elif name == "inspect_spell_gem":
                    return await self._handle_inspect_spell_gem(arguments)
                elif name == "list_all_supports":
                    return await self._handle_list_all_supports(arguments)
                elif name == "list_all_spells":
                    return await self._handle_list_all_spells(arguments)
                # TIER 2 DEBUGGING TOOLS
                elif name == "trace_support_selection":
                    return await self._handle_trace_support_selection(arguments)
                elif name == "trace_dps_calculation":
                    return await self._handle_trace_dps_calculation(arguments)
                elif name == "validate_build_constraints":
                    return await self._handle_validate_build_constraints(arguments)
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
                    from .calculator.ehp_calculator import DefensiveStats, ThreatProfile, DamageType

                    # DEBUG: Log the stats we're using
                    logger.info(f"[ANALYZE_CHAR] Calculating EHP with Life: {character_data.get('life')}, ES: {character_data.get('energy_shield')}")

                    defensive_stats = DefensiveStats(
                        life=character_data.get("life", 0),
                        energy_shield=character_data.get("energy_shield", 0),
                        armor=character_data.get("armor", 0),
                        evasion=character_data.get("evasion", 0),
                        block_chance=character_data.get("block_chance", 0),
                        fire_res=character_data.get("fire_res", 0),
                        cold_res=character_data.get("cold_res", 0),
                        lightning_res=character_data.get("lightning_res", 0),
                        chaos_res=character_data.get("chaos_res", 0)
                    )

                    # Calculate average EHP across damage types
                    threat = ThreatProfile(damage_type=DamageType.PHYSICAL, hit_damage=1000)
                    phys_ehp = self.ehp_calculator.calculate_ehp(defensive_stats, threat)

                    threat = ThreatProfile(damage_type=DamageType.FIRE, hit_damage=1000)
                    fire_ehp = self.ehp_calculator.calculate_ehp(defensive_stats, threat)

                    threat = ThreatProfile(damage_type=DamageType.COLD, hit_damage=1000)
                    cold_ehp = self.ehp_calculator.calculate_ehp(defensive_stats, threat)

                    threat = ThreatProfile(damage_type=DamageType.LIGHTNING, hit_damage=1000)
                    lightning_ehp = self.ehp_calculator.calculate_ehp(defensive_stats, threat)

                    # Use average EHP
                    analysis["ehp"] = int((phys_ehp + fire_ehp + cold_ehp + lightning_ehp) / 4)
                    logger.info(f"[ANALYZE_CHAR] Calculated EHP: {analysis['ehp']}")

                    # Simple defense rating based on life+ES pool
                    total_pool = character_data.get("life", 0) + character_data.get("energy_shield", 0)
                    if total_pool > 0:
                        analysis["defense_rating"] = min(1.0, total_pool / 8000)
                        logger.info(f"[ANALYZE_CHAR] Defense rating: {analysis['defense_rating']}")

                except Exception as e:
                    logger.error(f"[ANALYZE_CHAR] EHP calculation failed: {e}", exc_info=True)
                    # Set a fallback EHP based on raw pool
                    total_pool = character_data.get("life", 0) + character_data.get("energy_shield", 0)
                    analysis["ehp"] = total_pool
                    logger.info(f"[ANALYZE_CHAR] Using fallback EHP: {total_pool}")
            else:
                logger.warning("[ANALYZE_CHAR] ehp_calculator not available!")

            # Identify strengths/weaknesses based on actual stats
            life = character_data.get("life", 0)
            es = character_data.get("energy_shield", 0)
            total_pool = life + es

            if total_pool > 6000:
                analysis["strengths"].append(f"Good defensive pool ({total_pool:,.0f} combined life+ES)")
            elif total_pool < 4000:
                analysis["weaknesses"].append(f"Low defensive pool ({total_pool:,.0f} combined life+ES)")

            # Check resistances
            fire_res = character_data.get("fire_res", 0)
            cold_res = character_data.get("cold_res", 0)
            lightning_res = character_data.get("lightning_res", 0)

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

            # Format response
            response = self._format_character_analysis(character_data, analysis, recommendations)

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
                response += "- Defense: armor, evasion, energy shield, block, dodge\n"
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
        """Inspect complete details of a support gem"""
        try:
            support_name = args.get("support_name")

            if not support_name:
                return [types.TextContent(
                    type="text",
                    text="Error: support_name is required"
                )]

            # Load support gems database
            supports_file = Path(__file__).parent.parent / 'data' / 'poe2_support_gems_database.json'

            if not supports_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: Support gems database not found"
                )]

            with open(supports_file, 'r') as f:
                data = json.load(f)

            # Search for support (case-insensitive)
            support_data = None
            for support_id, sup_data in data.items():
                if support_id == 'metadata':
                    continue
                if isinstance(sup_data, dict) and sup_data.get('name', '').lower() == support_name.lower():
                    support_data = sup_data
                    break

            if not support_data:
                return [types.TextContent(
                    type="text",
                    text=f"Support gem '{support_name}' not found in database"
                )]

            # Format response
            response = f"# {support_data.get('name', support_name)}\n\n"

            if support_data.get('tags'):
                response += f"**Tags**: {', '.join(support_data['tags'])}\n\n"

            level_20 = support_data.get('level_20', {})
            if level_20.get('spirit_cost'):
                response += f"**Spirit Cost (L20)**: {level_20['spirit_cost']}\n\n"

            # Check for damage multiplier
            if support_data.get('damage_multiplier'):
                dmg_multi = support_data['damage_multiplier']
                if isinstance(dmg_multi, dict) and 'level_20' in dmg_multi:
                    response += f"**Damage Multiplier (L20)**: {dmg_multi['level_20']}%\n\n"

            # Incompatibilities
            incomp = support_data.get('incompatible_with', [])
            if incomp:
                response += f"**Incompatible With**: {', '.join(incomp)}\n\n"
            else:
                response += "**Incompatible With**: None (Database may be incomplete)\n\n"

            # Required tags
            req_tags = support_data.get('compatible_with', [])
            if req_tags:
                response += f"**Compatible With**: {', '.join(req_tags)}\n\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting support gem: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_inspect_spell_gem(self, args: dict) -> List[types.TextContent]:
        """Inspect complete details of a spell gem"""
        try:
            spell_name = args.get("spell_name")

            if not spell_name:
                return [types.TextContent(
                    type="text",
                    text="Error: spell_name is required"
                )]

            # Load spell gems database
            spells_file = Path(__file__).parent.parent / 'data' / 'poe2_spell_gems_database.json'

            if not spells_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: Spell gems database not found"
                )]

            with open(spells_file, 'r') as f:
                data = json.load(f)

            # Search for spell (case-insensitive)
            spell_data = None
            for category, spells in data.items():
                if category == 'metadata':
                    continue
                for spell_id, sp_data in spells.items():
                    if isinstance(sp_data, dict) and sp_data.get('name', '').lower() == spell_name.lower():
                        spell_data = sp_data
                        break
                if spell_data:
                    break

            if not spell_data:
                return [types.TextContent(
                    type="text",
                    text=f"Spell gem '{spell_name}' not found in database"
                )]

            # Format response
            response = f"# {spell_data.get('name', spell_name)}\n\n"

            if spell_data.get('element'):
                response += f"**Element**: {spell_data['element']}\n\n"

            if spell_data.get('tags'):
                response += f"**Tags**: {', '.join(spell_data['tags'])}\n\n"

            level_20 = spell_data.get('level_20', {})

            if level_20.get('damage_min') is not None and level_20.get('damage_max') is not None:
                avg_dmg = (level_20['damage_min'] + level_20['damage_max']) / 2
                response += f"**Base Damage (L20)**: {level_20['damage_min']}-{level_20['damage_max']} (avg: {avg_dmg:.1f})\n\n"

            if level_20.get('cast_time'):
                response += f"**Cast Time (L20)**: {level_20['cast_time']}s\n\n"
                if level_20.get('damage_min'):
                    dps = avg_dmg / level_20['cast_time']
                    response += f"**Base DPS (L20)**: {dps:.1f}\n\n"

            if level_20.get('mana_cost'):
                response += f"**Mana Cost (L20)**: {level_20['mana_cost']}\n\n"

            if level_20.get('spirit_cost'):
                response += f"**Spirit Cost (L20)**: {level_20['spirit_cost']}\n\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error inspecting spell gem: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_list_all_supports(self, args: dict) -> List[types.TextContent]:
        """List all support gems with filtering and sorting"""
        try:
            filter_tags = args.get("filter_tags", [])
            min_spirit = args.get("min_spirit")
            max_spirit = args.get("max_spirit")
            sort_by = args.get("sort_by", "name")
            limit = args.get("limit", 50)

            # Load support gems database
            supports_file = Path(__file__).parent.parent / 'data' / 'poe2_support_gems_database.json'

            if not supports_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: Support gems database not found"
                )]

            with open(supports_file, 'r') as f:
                data = json.load(f)

            # Extract and filter supports
            all_supports = []
            for support_id, support_data in data.items():
                if support_id == 'metadata':
                    continue
                if not isinstance(support_data, dict) or 'name' not in support_data:
                    continue

                level_20 = support_data.get('level_20', {})
                spirit_cost = level_20.get('spirit_cost', 0) or 0

                # Apply filters
                if filter_tags:
                    support_tags = [t.lower() for t in support_data.get('tags', [])]
                    if not any(ft.lower() in support_tags for ft in filter_tags):
                        continue

                if min_spirit is not None and spirit_cost < min_spirit:
                    continue
                if max_spirit is not None and spirit_cost > max_spirit:
                    continue

                # Get damage multiplier
                dmg_multi = support_data.get('damage_multiplier', {})
                if isinstance(dmg_multi, dict):
                    dmg_multi_val = dmg_multi.get('level_20', 100)
                else:
                    dmg_multi_val = dmg_multi or 100

                all_supports.append({
                    'name': support_data['name'],
                    'tags': support_data.get('tags', []),
                    'spirit_cost': spirit_cost,
                    'damage_multiplier': dmg_multi_val
                })

            # Sort
            if sort_by == "spirit_cost":
                all_supports.sort(key=lambda x: x['spirit_cost'])
            elif sort_by == "damage_multiplier":
                all_supports.sort(key=lambda x: x['damage_multiplier'], reverse=True)
            else:  # name
                all_supports.sort(key=lambda x: x['name'])

            # Limit
            all_supports = all_supports[:limit]

            # Format response
            response = f"# Support Gems ({len(all_supports)} results)\n\n"
            response += f"{'Name':<35} {'Spirit':<10} {'Dmg Multi':<12} {'Tags'}\n"
            response += "-" * 100 + "\n"

            for sup in all_supports:
                tags_str = ', '.join(sup['tags'][:3])
                response += f"{sup['name']:<35} {sup['spirit_cost']:<10} {sup['damage_multiplier']:<12} {tags_str}\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error listing supports: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def _handle_list_all_spells(self, args: dict) -> List[types.TextContent]:
        """List all spell gems with filtering and sorting"""
        try:
            filter_element = args.get("filter_element")
            filter_tags = args.get("filter_tags", [])
            min_damage = args.get("min_damage")
            sort_by = args.get("sort_by", "name")
            limit = args.get("limit", 50)

            # Load spell gems database
            spells_file = Path(__file__).parent.parent / 'data' / 'poe2_spell_gems_database.json'

            if not spells_file.exists():
                return [types.TextContent(
                    type="text",
                    text="Error: Spell gems database not found"
                )]

            with open(spells_file, 'r') as f:
                data = json.load(f)

            # Extract and filter spells
            all_spells = []
            for category, spells in data.items():
                if category == 'metadata':
                    continue
                for spell_id, spell_data in spells.items():
                    if not isinstance(spell_data, dict) or 'name' not in spell_data:
                        continue

                    level_20 = spell_data.get('level_20', {})
                    dmg_min = level_20.get('damage_min')
                    dmg_max = level_20.get('damage_max')
                    cast_time = level_20.get('cast_time')

                    if dmg_min is not None and dmg_max is not None:
                        avg_dmg = (dmg_min + dmg_max) / 2
                    else:
                        avg_dmg = 0

                    # Apply filters
                    if filter_element:
                        if spell_data.get('element', '').lower() != filter_element.lower():
                            continue

                    if filter_tags:
                        spell_tags = [t.lower() for t in spell_data.get('tags', [])]
                        if not any(ft.lower() in spell_tags for ft in filter_tags):
                            continue

                    if min_damage is not None and avg_dmg < min_damage:
                        continue

                    # Calculate DPS
                    if cast_time and cast_time > 0 and avg_dmg > 0:
                        dps = avg_dmg / cast_time
                    else:
                        dps = 0

                    all_spells.append({
                        'name': spell_data['name'],
                        'element': spell_data.get('element', 'N/A'),
                        'tags': spell_data.get('tags', []),
                        'base_damage': avg_dmg,
                        'cast_time': cast_time or 0,
                        'dps': dps
                    })

            # Sort
            if sort_by == "base_damage":
                all_spells.sort(key=lambda x: x['base_damage'], reverse=True)
            elif sort_by == "cast_time":
                all_spells.sort(key=lambda x: x['cast_time'])
            elif sort_by == "dps":
                all_spells.sort(key=lambda x: x['dps'], reverse=True)
            else:  # name
                all_spells.sort(key=lambda x: x['name'])

            # Limit
            all_spells = all_spells[:limit]

            # Format response
            response = f"# Spell Gems ({len(all_spells)} results)\n\n"
            response += f"{'Name':<30} {'Element':<12} {'Base Dmg':<12} {'Cast Time':<12} {'DPS':<10}\n"
            response += "-" * 100 + "\n"

            for spell in all_spells:
                dmg_str = f"{spell['base_damage']:.1f}" if spell['base_damage'] > 0 else "N/A"
                cast_str = f"{spell['cast_time']:.2f}s" if spell['cast_time'] > 0 else "N/A"
                dps_str = f"{spell['dps']:.1f}" if spell['dps'] > 0 else "N/A"
                response += f"{spell['name']:<30} {spell['element']:<12} {dmg_str:<12} {cast_str:<12} {dps_str:<10}\n"

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

            # Check mana reservation
            mana = character_data.get("mana", 0)
            mana_reserved = character_data.get("mana_reserved", 0)
            if mana > 0:
                reservation_pct = (mana_reserved / mana) * 100
                if reservation_pct >= 100:
                    violations.append({
                        "severity": "CRITICAL",
                        "category": "Mana",
                        "message": f"Mana reservation at or above 100%: {reservation_pct:.1f}%"
                    })
                elif reservation_pct > 95:
                    violations.append({
                        "severity": "HIGH",
                        "category": "Mana",
                        "message": f"Mana reservation very high: {reservation_pct:.1f}%"
                    })

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

    def _format_character_analysis(self, character_data: dict, analysis: dict, recommendations: str) -> str:
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
