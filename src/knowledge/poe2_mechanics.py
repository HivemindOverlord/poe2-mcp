"""
Path of Exile 2 Mechanics Knowledge Base

Comprehensive explanations of game mechanics with calculations.
Answers common player questions about how things work.

VERIFIED FOR POE2 - December 2025
Sources: poe2wiki.net, poewiki.net, maxroll.gg, official forums
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MechanicCategory(Enum):
    """Categories of game mechanics"""
    DAMAGE = "damage"
    DEFENSE = "defense"
    AILMENTS = "ailments"
    CROWD_CONTROL = "crowd_control"
    RESOURCES = "resources"
    SCALING = "scaling"
    INTERACTION = "interaction"


@dataclass
class MechanicExplanation:
    """Explanation of a game mechanic"""
    name: str
    category: MechanicCategory
    short_description: str
    detailed_explanation: str
    how_it_works: str
    calculation_formula: Optional[str] = None
    examples: List[str] = None
    common_questions: Dict[str, str] = None
    related_mechanics: List[str] = None
    important_notes: List[str] = None
    changed_from_poe1: Optional[str] = None

    def __post_init__(self) -> None:
        if self.examples is None:
            self.examples = []
        if self.common_questions is None:
            self.common_questions = {}
        if self.related_mechanics is None:
            self.related_mechanics = []
        if self.important_notes is None:
            self.important_notes = []


class PoE2MechanicsKnowledgeBase:
    """
    Comprehensive mechanics knowledge base for PoE2

    VERIFIED FOR POE2 - All mechanics have been researched and corrected
    from official sources and community wikis.

    Usage:
        >>> kb = PoE2MechanicsKnowledgeBase()
        >>> poison_info = kb.get_mechanic("poison")
        >>> print(poison_info.detailed_explanation)
    """

    def __init__(self, db_manager=None) -> None:
        self.mechanics: Dict[str, MechanicExplanation] = {}
        self.db_manager = db_manager
        self._clientstrings_cache = {}
        self._initialize_mechanics()

    def _initialize_mechanics(self):
        """Initialize all mechanics explanations - VERIFIED FOR POE2"""

        # =====================================================================
        # DAMAGING AILMENTS
        # =====================================================================

        self.mechanics['poison'] = MechanicExplanation(
            name="Poison",
            category=MechanicCategory.AILMENTS,
            short_description="Chaos DoT based on physical and chaos damage - DEFAULT STACK LIMIT OF 1",
            detailed_explanation="""
Poison is a damaging ailment that deals Chaos damage over time. In PoE2, poison has a
DEFAULT STACK LIMIT OF 1 - this is a MAJOR change from PoE1 where poison could stack
infinitely.

Multiple poison instances CAN exist on a target, each with their own duration, but only
the highest damage instance(s) will actually deal damage, up to your stack limit.

To make poison builds work in PoE2, you need sources that increase your poison stack
limit, such as the Escalating Poison Support gem.
""",
            how_it_works="""
1. You deal physical and/or chaos damage with a hit that has poison chance
2. If poison is applied, it deals 20% of the hit's combined physical + chaos damage per second
3. Base poison duration is 2 seconds
4. DEFAULT STACK LIMIT: 1 - only the strongest poison deals damage
5. Multiple poisons can exist but only up to your stack limit actually deal damage
6. Poison damage BYPASSES Energy Shield (damages life directly)
7. Escalating Poison Support adds +1 to your poison stack limit
""",
            calculation_formula="""
Poison DPS per stack = 20% of (Physical + Chaos damage of the hit)
Total Poison Duration = 2 seconds base x (1 + increased duration modifiers)
Active Stacks = min(Total Poisons Applied, Your Stack Limit)

Example (with default stack limit of 1):
- You hit for 1000 physical + 500 chaos = 1500 total
- Poison DPS = 0.20 x 1500 = 300 chaos DPS
- Over 2 seconds = 600 total chaos damage
- If you apply 5 poisons, only the STRONGEST ONE deals damage

Example (with Escalating Poison - stack limit 2):
- Same hit, but now 2 poisons deal damage
- 2 x 300 = 600 DPS (if both stacks are equal strength)
""",
            examples=[
                "Default: 5 poison applications = only 1 deals damage (strongest)",
                "With Escalating Poison: 5 applications = 2 deal damage",
                "Pathfinder ascendancy and passives can increase stack limit further",
                "Poison bypasses ES - great against ES-heavy enemies"
            ],
            common_questions={
                "Does poison stack in PoE2?": "By default NO - you have a stack limit of 1. You need Escalating Poison Support or other sources to increase the limit.",
                "What increases poison stack limit?": "Escalating Poison Support (+1), certain passives, Pathfinder ascendancy nodes, and some unique items.",
                "Can all damage types poison?": "By default, only physical and chaos damage contribute to poison. Special modifiers can allow other damage types.",
                "Does poison work with Energy Shield builds?": "Yes! Poison bypasses ES entirely, making it effective against ES-heavy enemies.",
                "Is poison good in PoE2?": "Poison builds require investment in stack limit to be effective. With proper scaling, they can deal massive damage."
            },
            related_mechanics=['bleed', 'ignite', 'chaos_damage', 'escalating_poison'],
            important_notes=[
                "DEFAULT STACK LIMIT OF 1 - This is NOT like PoE1!",
                "Escalating Poison Support is almost mandatory for poison builds",
                "Poison damage = 20% of phys+chaos per second (not 30% like PoE1)",
                "Duration is 2 seconds base",
                "Bypasses Energy Shield completely",
                "Multiple instances can exist but only strongest up to limit deals damage"
            ],
            changed_from_poe1="""
MAJOR CHANGES from PoE1:
- Default stack limit is now 1 (was infinite in PoE1)
- Base damage is 20% per second (was 30% in PoE1)
- Duration is 2 seconds (was 2 seconds in PoE1 - unchanged)
- Need Escalating Poison or other sources to stack effectively
- Poison builds require different gear/passive choices than PoE1
"""
        )

        self.mechanics['bleed'] = MechanicExplanation(
            name="Bleed",
            category=MechanicCategory.AILMENTS,
            short_description="Physical DoT that deals more damage when target moves",
            detailed_explanation="""
Bleed (Bleeding) is a damaging ailment that deals physical damage over time.
It has a unique mechanic where damage increases by 100% while the target is moving.

Like poison, bleed does NOT stack by default - multiple bleeds can exist but only
the highest damage one deals damage. The Crimson Dance keystone changes this.

Bleed can ONLY be applied by hits that damage Life - hits blocked entirely by
Energy Shield cannot cause bleed.
""",
            how_it_works="""
1. You deal physical damage with a hit that has bleed chance
2. Bleed only applies if the hit damages LIFE (not just ES)
3. Bleed deals 15% of hit's physical damage per second for 5 seconds
4. While target is MOVING: bleed deals 100% MORE damage (30%/sec)
5. Does NOT stack - only highest damage bleed deals damage
6. Bleed damage BYPASSES Energy Shield
7. Aggravated Bleed: Always deals the 'moving' damage regardless of movement
""",
            calculation_formula="""
Bleed DPS (stationary) = 15% of Physical Hit Damage per second
Bleed DPS (moving) = 30% of Physical Hit Damage per second (100% more)
Total Duration = 5 seconds base
Total Damage = 75% (stationary) or 150% (moving) of hit over 5 seconds

Example:
- You hit for 2000 physical damage
- Bleed DPS (stationary) = 0.15 x 2000 = 300 physical DPS
- Bleed DPS (moving) = 0.30 x 2000 = 600 physical DPS
- Total damage over 5 seconds: 1500 (stationary) or 3000 (moving)

NOTE: PoE2 does NOT have the Crimson Dance keystone. Bleed does not stack.
""",
            examples=[
                "Single big hit bleed is the only viable approach in PoE2 (no stacking)",
                "Moving enemies take double bleed damage - use knockback/terrain",
                "Aggravated Bleed makes bleed always deal 'moving' damage",
                "Bleed bypasses both Energy Shield AND Armor"
            ],
            common_questions={
                "Does bleed stack in PoE2?": "NO! PoE2 does not have Crimson Dance. Only the strongest bleed deals damage.",
                "Why doesn't my bleed apply through ES?": "Bleed only applies when hits damage Life. ES must be depleted first.",
                "Is Aggravated Bleed worth it?": "Yes for consistent damage, especially against stationary bosses.",
                "Does armor reduce bleed damage?": "No! Armor only affects hits. Bleed bypasses armor entirely.",
                "What happened to Crimson Dance?": "Crimson Dance does NOT exist in PoE2. Bleed cannot stack."
            },
            related_mechanics=['poison', 'ignite', 'physical_damage', 'aggravated_bleed'],
            important_notes=[
                "Only applies from hits that damage LIFE",
                "Bypasses Energy Shield AND Armor for the DoT",
                "100% more damage while target moves - huge damage boost",
                "Does NOT stack - only strongest bleed deals damage",
                "Crimson Dance does NOT exist in PoE2",
                "Aggravated Bleed = always 'moving' damage"
            ],
            changed_from_poe1="""
MAJOR CHANGES from PoE1:
- Crimson Dance keystone DOES NOT EXIST in PoE2
- Bleed CANNOT stack in PoE2 (no 8-stack builds possible)
- Base damage is 15% per second (75% total over 5 seconds)
- Moving bonus is 100% more (doubles to 30%/s)
- Still requires hitting Life to apply
- Focus on big single hits, not attack speed
"""
        )

        self.mechanics['ignite'] = MechanicExplanation(
            name="Ignite",
            category=MechanicCategory.AILMENTS,
            short_description="Fire DoT based on fire damage dealt",
            detailed_explanation="""
Ignite is a damaging ailment that deals fire damage over time. In PoE2, ignite
uses the new ailment threshold system for determining application chance.

Ignite does NOT stack - only the highest damage ignite deals damage. This means
big single hits are generally better for ignite builds than many small hits.
""",
            how_it_works="""
1. You deal fire damage with a hit
2. Chance to ignite based on: (Fire Damage / Enemy Ailment Threshold) x 25%
3. Base ignite chance is 25% per 100% of ailment threshold dealt
4. Ignite deals 20% of the fire damage per second (80% total over 4 seconds)
5. Base duration is 4 seconds
6. Does NOT stack - only strongest ignite deals damage
7. New ignites replace old ones if they would deal more total damage
""",
            calculation_formula="""
Ignite Chance = 25% x (Fire Damage Dealt / Enemy Ailment Threshold)
Ignite DPS = 20% of Fire Hit Damage per second
Total Duration = 4 seconds base
Total Ignite Damage = Fire Hit x 0.20 x 4 = 80% of hit over 4 seconds

Example:
- Enemy has 10,000 ailment threshold (usually = max life)
- You hit for 5,000 fire damage
- Ignite chance = 25% x (5000/10000) = 12.5% chance to ignite
- If ignited: 5000 x 0.20 = 1000 fire DPS for 4 seconds
- Total damage: 5000 fire hit + 4000 ignite = 9,000 total

Critical strikes increase the fire damage dealt, indirectly increasing ignite damage.
""",
            examples=[
                "Big fire hits work best for ignite (no stacking)",
                "Flameblast charged up = massive single ignite",
                "Chance scales with damage dealt vs enemy threshold",
                "Boss with high threshold = lower ignite chance per hit"
            ],
            common_questions={
                "Does ignite stack?": "No. Only the highest damage ignite deals damage. Use big hits.",
                "Why does my ignite chance vary?": "Ignite chance depends on damage dealt vs enemy ailment threshold. Bigger hits = higher chance.",
                "Do crits guarantee ignite?": "NO! In PoE2, crits do NOT guarantee ailments. They just deal more damage, which increases chance.",
                "Is ignite good for bossing?": "Can be, but bosses have high thresholds. Need big damage investment.",
                "What affects ignite damage?": "Fire damage, DoT multipliers, ignite effect modifiers. NOT spell damage after the hit."
            },
            related_mechanics=['poison', 'bleed', 'fire_damage', 'ailment_threshold'],
            important_notes=[
                "Does NOT stack - only strongest ignite deals damage",
                "Crits do NOT guarantee ignite in PoE2",
                "Chance based on damage vs ailment threshold (usually enemy max life)",
                "20% of fire damage per second for 4 seconds = 80% of hit as DoT",
                "Big single hits are better than many small hits for ignite"
            ],
            changed_from_poe1="""
MAJOR CHANGES from PoE1:
- Crits NO LONGER guarantee ignite!
- Uses ailment threshold system for chance calculation
- Base damage and duration similar to PoE1
- Still doesn't stack (same as PoE1)
- Threshold-based chance is new to PoE2
"""
        )

        # =====================================================================
        # ELEMENTAL AILMENTS (NON-DAMAGING)
        # =====================================================================

        self.mechanics['freeze'] = MechanicExplanation(
            name="Freeze",
            category=MechanicCategory.AILMENTS,
            short_description="Completely stops target actions for up to 4 seconds",
            detailed_explanation="""
Freeze is a cold-based ailment that completely stops enemies from acting. In PoE2,
freeze uses a BUILDUP system - you build up freeze with cold damage until it triggers.

Unlike PoE1, freeze in PoE2 PAUSES enemy actions rather than interrupting them.
When freeze ends, enemies resume whatever they were doing.

Freeze is independent from Chill - they are separate ailments with different effects.
""",
            how_it_works="""
1. Deal cold damage to build up Freeze on the target
2. When Freeze buildup reaches 100%, target is Frozen
3. Frozen targets cannot move or act for up to 4 seconds
4. Freeze PAUSES actions - enemy resumes when freeze ends
5. Does NOT interrupt current actions (unlike Electrocute)
6. Boss freeze thresholds INCREASE after each freeze application
7. Buildup decays over time if not maintained
""",
            calculation_formula="""
Freeze Buildup = Based on Cold Damage vs Enemy Ailment Threshold
When Buildup reaches 100% = Freeze triggers
Base Freeze Duration = Up to 4 seconds (based on buildup amount)

Boss Mechanic:
- Each freeze on a boss increases the threshold for the next freeze
- Threshold decays over time, allowing re-freezing after waiting
- Cannot perma-freeze bosses like in PoE1

Example:
- Enemy threshold: 10,000
- You deal 3,000 cold damage = ~30% freeze buildup
- Next hit 3,000 more = ~60% total buildup
- Next hit 3,000 more = ~90% buildup
- Next hit triggers freeze
""",
            examples=[
                "Build up freeze with multiple cold hits",
                "Bosses have increasing freeze thresholds - can't perma-freeze",
                "Freeze PAUSES boss attacks - they resume casting after freeze",
                "Shatter frozen enemies on kill for on-death immunity"
            ],
            common_questions={
                "Can I perma-freeze bosses?": "No. Boss freeze thresholds increase after each freeze, requiring more and more damage.",
                "Does freeze interrupt boss attacks?": "No! Freeze PAUSES actions. Boss will resume casting when freeze ends.",
                "Is freeze different from chill?": "Yes! Freeze stops actions completely. Chill only slows. They're independent.",
                "Do crits guarantee freeze?": "No. Crits help by dealing more damage, but don't guarantee freeze in PoE2.",
                "How do I shatter enemies?": "Kill a frozen enemy. Shatter prevents on-death effects."
            },
            related_mechanics=['chill', 'cold_damage', 'shatter', 'ailment_threshold'],
            important_notes=[
                "Uses BUILDUP system - not instant freeze",
                "PAUSES actions (doesn't interrupt) - enemies resume after",
                "Boss thresholds INCREASE after each freeze",
                "Independent from Chill",
                "Base duration up to 4 seconds",
                "Crits do NOT guarantee freeze in PoE2"
            ],
            changed_from_poe1="""
MAJOR CHANGES from PoE1:
- Uses buildup system instead of instant freeze
- PAUSES actions instead of interrupting them
- Boss thresholds increase with each freeze (anti-perma-freeze)
- Crits don't guarantee freeze
- More accessible but harder to maintain on bosses
"""
        )

        self.mechanics['chill'] = MechanicExplanation(
            name="Chill",
            category=MechanicCategory.AILMENTS,
            short_description="Slows target action speed by up to 50%",
            detailed_explanation="""
Chill is a cold-based ailment that slows enemy action speed. Unlike freeze,
chill is applied by ANY cold damage and is independent from freeze buildup.

Chill magnitude (slow amount) scales with cold damage dealt relative to
enemy ailment threshold, up to a maximum of 50% slow.
""",
            how_it_works="""
1. Any cold damage hit applies Chill
2. Chill magnitude = Based on cold damage vs enemy threshold
3. Maximum chill effect is 50% reduced action speed
4. Base chill duration is 2 seconds
5. Stronger chills replace weaker ones
6. Independent from Freeze - can have both active
""",
            calculation_formula="""
Chill Magnitude = (Cold Damage / Ailment Threshold) x scaling factor
Maximum Chill = 50% reduced action speed
Base Duration = 2 seconds

Example:
- Deal 5,000 cold damage to enemy with 10,000 threshold
- Chill magnitude roughly = 25-30% slow
- Bigger cold hits = stronger chill (up to 50%)
""",
            examples=[
                "Any cold damage applies chill automatically",
                "Big cold hits = stronger slow (up to 50%)",
                "Chill is separate from freeze - can have both",
                "2 second duration, refreshes on new cold hits"
            ],
            common_questions={
                "How do I apply chill?": "Any cold damage automatically applies chill. No special chance needed.",
                "What's the max chill effect?": "50% reduced action speed.",
                "Is chill the same as freeze?": "No! Chill slows, freeze stops completely. They're independent ailments.",
                "Does chill work on bosses?": "Yes, but effect may be reduced on some bosses."
            },
            related_mechanics=['freeze', 'cold_damage', 'action_speed'],
            important_notes=[
                "Applied by ANY cold damage automatically",
                "Max slow is 50%",
                "2 second base duration",
                "Independent from Freeze",
                "Scales with damage dealt"
            ],
            changed_from_poe1="Similar to PoE1 but with ailment threshold scaling."
        )

        self.mechanics['shock'] = MechanicExplanation(
            name="Shock",
            category=MechanicCategory.AILMENTS,
            short_description="Target takes 20% increased damage from all sources",
            detailed_explanation="""
Shock is a lightning-based ailment that causes enemies to take increased damage.
In PoE2, shock is a FLAT 20% increased damage taken - it does NOT scale with
damage dealt like in PoE1.

Shock affects ALL damage the enemy takes, making it excellent for party play
and builds that deal multiple damage types.
""",
            how_it_works="""
1. Deal lightning damage with shock chance
2. Shock chance = 25% per 100% of ailment threshold dealt
3. Shocked enemies take 20% INCREASED damage from ALL sources
4. This is a FLAT 20% - does not scale with damage dealt
5. Base shock duration is 4 seconds
6. Shock does not stack - only one shock can be active
""",
            calculation_formula="""
Shock Chance = 25% x (Lightning Damage / Ailment Threshold)
Shock Effect = FLAT 20% increased damage taken
Duration = 4 seconds base

THIS IS NOT LIKE POE1:
- PoE1: Shock magnitude scaled with damage (up to 50%)
- PoE2: Shock is always 20% (flat, doesn't scale)

Example:
- Enemy has 10,000 threshold
- You deal 4,000 lightning = 10% chance to shock
- If shocked: enemy takes 20% increased damage from everything
""",
            examples=[
                "Flat 20% damage increase - doesn't scale with damage",
                "Affects ALL damage types (physical, elemental, DoT)",
                "Great for party play - everyone benefits",
                "4 second duration, can be refreshed"
            ],
            common_questions={
                "Does shock scale with damage in PoE2?": "NO! Shock is a flat 20% in PoE2. This is different from PoE1.",
                "Does shock affect DoT damage?": "Yes! All damage the enemy takes is increased by 20%.",
                "Can I stack multiple shocks?": "No. Only one shock can be active at a time.",
                "Is shock worth investing in?": "20% more damage is significant, especially for party play."
            },
            related_mechanics=['electrocute', 'lightning_damage', 'ailment_threshold'],
            important_notes=[
                "FLAT 20% increased damage taken - does NOT scale",
                "This is different from PoE1 where shock scaled up to 50%",
                "Affects ALL damage types",
                "4 second duration",
                "Does not stack"
            ],
            changed_from_poe1="""
MAJOR CHANGE from PoE1:
- PoE1: Shock scaled from 5% to 50% based on damage dealt
- PoE2: Shock is a FLAT 20% (does not scale)
- This is a significant nerf to big-hit shock builds
- But makes shock more consistent and accessible
"""
        )

        self.mechanics['electrocute'] = MechanicExplanation(
            name="Electrocute",
            category=MechanicCategory.AILMENTS,
            short_description="NEW in PoE2 - Hard CC that stops target actions for 5 seconds",
            detailed_explanation="""
Electrocute is a NEW ailment in PoE2 that provides hard crowd control for
lightning builds. Unlike Shock (which is a damage multiplier), Electrocute
completely stops enemy actions similar to Freeze.

IMPORTANT: Not all lightning damage can electrocute! Only specific skills
and effects have electrocute capability. Regular lightning damage only shocks.
""",
            how_it_works="""
1. Use a skill or effect that has Electrocute capability
2. Build up Electrocute similar to Freeze buildup
3. When buildup reaches 100%, target is Electrocuted
4. Electrocuted targets cannot act for up to 5 seconds
5. Unlike Freeze, Electrocute INTERRUPTS current actions
6. Boss thresholds increase after each electrocute
""",
            calculation_formula="""
Electrocute Buildup = Lightning Damage vs Threshold (from specific skills only)
Base Duration = Up to 5 seconds
Effect = Target cannot perform any actions

NOT ALL LIGHTNING CAN ELECTROCUTE:
- Regular lightning damage = only Shock
- Specific skills/supports = can Electrocute
- Check skill descriptions for "Electrocute" keyword
""",
            examples=[
                "Lightning equivalent of Freeze for crowd control",
                "Only specific skills can electrocute (not all lightning)",
                "5 second base duration (longer than freeze's 4 seconds)",
                "INTERRUPTS actions (unlike freeze which pauses)"
            ],
            common_questions={
                "Can any lightning damage electrocute?": "NO! Only specific skills and effects. Regular lightning only shocks.",
                "How is electrocute different from shock?": "Shock = 20% damage taken debuff. Electrocute = hard CC that stops actions.",
                "How is electrocute different from freeze?": "Both stop actions, but electrocute INTERRUPTS while freeze PAUSES.",
                "What skills can electrocute?": "Check skill descriptions - only skills mentioning 'Electrocute' can apply it."
            },
            related_mechanics=['shock', 'freeze', 'lightning_damage'],
            important_notes=[
                "NEW to PoE2 - didn't exist in PoE1",
                "Only specific skills can Electrocute",
                "Regular lightning damage only Shocks",
                "5 second duration (longer than freeze)",
                "INTERRUPTS actions (doesn't pause like freeze)",
                "Boss thresholds increase after each electrocute"
            ],
            changed_from_poe1="Electrocute is completely NEW in PoE2. PoE1 only had Shock for lightning."
        )

        # =====================================================================
        # CROWD CONTROL
        # =====================================================================

        self.mechanics['stun'] = MechanicExplanation(
            name="Stun",
            category=MechanicCategory.CROWD_CONTROL,
            short_description="Two-tier system: Light Stun (brief) and Heavy Stun (long)",
            detailed_explanation="""
PoE2 has a completely redesigned stun system with TWO tiers:
- Light Stun: Brief interrupt, builds toward Heavy Stun
- Heavy Stun: Long interrupt when buildup reaches 100%

This creates more interactive combat where you can build up to big stuns
on dangerous enemies.
""",
            how_it_works="""
LIGHT STUN:
1. Chance based on damage dealt vs enemy stun threshold
2. 100% chance when hit = 100% of enemy max life
3. Physical damage has 50% MORE light stun chance
4. Player melee has 50% MORE light stun chance (stacks)
5. Brief interrupt effect

HEAVY STUN:
1. Builds up from hits (separate from light stun)
2. When buildup reaches 100%, Heavy Stun triggers
3. Heavy Stun = several seconds of being unable to act
4. Buildup decays over time if not maintained
5. PLAYERS CANNOT BE HEAVY STUNNED

BOSS MECHANIC:
- "Primed for Stun" at 40% buildup (normal), 50% (magic), 60% (rare), 70% (unique)
- Crushing Blows instantly trigger Heavy Stun on Primed enemies
""",
            calculation_formula="""
Light Stun Chance = (Hit Damage / Stun Threshold) x 100%
- Physical hits: 50% more chance
- Player melee: 50% more chance (multiplicative)
- Min 15% chance or treated as 0%

Heavy Stun Buildup = Accumulates from hits
- Triggers at 100% buildup
- Decays over time

Player Stun Threshold = Maximum Life x (1 + stun avoidance)
Players have 50% more stun threshold per light stun in past 4 seconds
""",
            examples=[
                "Physical melee hits have 125% more stun chance (1.5 x 1.5)",
                "Build up heavy stun with consistent hits",
                "Look for 'Primed for Stun' indicator on enemies",
                "Use Crushing Blows to instantly heavy stun primed enemies"
            ],
            common_questions={
                "Can I be Heavy Stunned?": "No. Players can only receive Light Stuns.",
                "What is 'Primed for Stun'?": "When enemy has 40-70% heavy stun buildup. Crushing Blows instant-stun primed enemies.",
                "How do I stun bosses?": "Build up heavy stun with consistent damage. Use Crushing Blow when primed.",
                "Does stun threshold scale with life?": "Yes. Higher life = higher stun threshold = harder to stun."
            },
            related_mechanics=['heavy_stun', 'light_stun', 'crushing_blow', 'poise'],
            important_notes=[
                "Two-tier system: Light Stun and Heavy Stun",
                "Players CANNOT be Heavy Stunned",
                "Physical and melee have bonus stun chance",
                "Heavy Stun buildup decays over time",
                "Crushing Blows trigger instant Heavy Stun on Primed enemies",
                "Player stun threshold increases after being stunned recently"
            ],
            changed_from_poe1="""
COMPLETELY REDESIGNED from PoE1:
- Two-tier system (Light + Heavy) is new
- Heavy Stun buildup mechanic is new
- Players cannot be Heavy Stunned
- "Primed for Stun" indicator is new
- Crushing Blow mechanic is new
- Much more interactive than PoE1's simple stun system
"""
        )

        # =====================================================================
        # DEFENSES
        # =====================================================================

        self.mechanics['armor'] = MechanicExplanation(
            name="Armor",
            category=MechanicCategory.DEFENSE,
            short_description="Reduces physical damage from hits - better against small hits",
            detailed_explanation="""
Armor provides physical damage reduction from all hits (attacks and spells).
The key thing to understand is that armor is MORE effective against small hits
and LESS effective against large hits.

This means armor is excellent against many small hits but struggles against
big slams and boss attacks.
""",
            how_it_works="""
1. Armor reduces physical damage from HITS only (not DoT)
2. Reduction = Armor / (Armor + 10 x Damage)
3. Maximum reduction is capped at 90%
4. More effective against small hits, less effective against big hits
5. Does NOT reduce bleed damage (only the initial hit)

RULE OF THUMB (post-patch 0.1.1):
- 5x damage in armor = 33% reduction
- 10x damage in armor = 50% reduction
- 20x damage in armor = 66% reduction
""",
            calculation_formula="""
Physical Damage Reduction = Armor / (Armor + 10 x Incoming Damage)
Capped at 90% maximum reduction

Examples (post-patch 0.1.1 formula):
- 100 damage hit, 500 armor: 500/(500+1000) = 33% reduction
- 100 damage hit, 1000 armor: 1000/(1000+1000) = 50% reduction
- 100 damage hit, 2000 armor: 2000/(2000+1000) = 66% reduction

- 1000 damage hit, 5000 armor: 5000/(5000+10000) = 33% reduction
- 1000 damage hit, 10000 armor: 10000/(10000+10000) = 50% reduction
""",
            examples=[
                "Great against trash mobs with many small hits",
                "Struggles against boss slams - need other defenses too",
                "Does NOT reduce bleed DoT",
                "Physical spells are also reduced by armor"
            ],
            common_questions={
                "Does armor reduce bleed?": "No. Armor only affects the initial hit. Bleed DoT is not reduced.",
                "Is armor good against bosses?": "It helps, but big boss hits overwhelm armor. Layer with other defenses.",
                "Does armor work against spells?": "Yes! Physical spells are reduced by armor.",
                "How much armor do I need?": "Depends on content. 10k+ for endgame, but always layer defenses."
            },
            related_mechanics=['evasion', 'block', 'physical_damage_reduction'],
            important_notes=[
                "Only reduces HITS, not DoT",
                "More effective against small hits",
                "90% cap on damage reduction",
                "Formula: Armor / (Armor + 10 x Damage)",
                "Layer with other defenses for big hits"
            ],
            changed_from_poe1="Formula changed in patch 0.1.1 from 12x to 10x multiplier, making armor more effective."
        )

        self.mechanics['evasion'] = MechanicExplanation(
            name="Evasion",
            category=MechanicCategory.DEFENSE,
            short_description="Chance to completely avoid ALL hits (except boss red-flash skills)",
            detailed_explanation="""
Evasion gives you a chance to completely avoid damage from enemy attacks.
When you evade, you take zero damage from that hit.

In PoE2, evasion works against ALL types of hits including area damage!
This is a MAJOR change from PoE1 where Acrobatics was needed for area evasion.

The only exception: Boss skills with a RED FLASH cannot be evaded.
""",
            how_it_works="""
1. Evasion rating vs enemy accuracy determines evade chance
2. Higher evasion = higher chance to evade
3. Works against ALL hits: strikes, projectiles, AND area damage
4. EXCEPTION: Boss skills with red flash indicator CANNOT be evaded
5. Acrobatics keystone was REMOVED - functionality is now baseline
6. Uses entropy system - not pure RNG
""",
            calculation_formula="""
Evade Chance = Based on (Your Evasion / Enemy Accuracy)
Higher monster level = higher accuracy needed to evade

The exact formula hasn't been fully published, but:
- Significantly more evasion than monster accuracy = high evade chance
- Equal evasion to accuracy = roughly 50% evade
- Less evasion than accuracy = low evade chance

CANNOT EVADE: Boss skills with red flash indicator
""",
            examples=[
                "Complete damage avoidance when you evade",
                "Works against ALL hits including area damage in PoE2",
                "Watch for RED FLASH on boss skills - those cannot be evaded",
                "Evasion is much stronger in PoE2 than PoE1"
            ],
            common_questions={
                "Does evasion work against spells?": "Yes! In PoE2, evasion works against ALL hits including spells.",
                "Can I evade area damage?": "YES! In PoE2, evasion works against area damage by default. Acrobatics was removed.",
                "What is Acrobatics?": "Acrobatics was REMOVED in patch 0.3.0. Its functionality is now baseline evasion.",
                "What can't I evade?": "Boss skills with a red flash indicator cannot be evaded. You must dodge roll these.",
                "Is evasion reliable?": "Uses entropy system for consistency. Very strong in PoE2."
            },
            related_mechanics=['armor', 'block', 'dodge_roll', 'deflect'],
            important_notes=[
                "Complete damage avoidance on evade",
                "Works against ALL hits including area damage",
                "CANNOT evade boss red-flash skills",
                "Acrobatics keystone was REMOVED in 0.3.0",
                "Uses entropy system for consistency",
                "Much stronger than PoE1 evasion"
            ],
            changed_from_poe1="""
MAJOR CHANGES from PoE1:
- Evasion now works against ALL hits including area damage
- Acrobatics keystone REMOVED - functionality integrated into base evasion
- Works against spells in PoE2
- Cannot evade boss red-flash skills (must dodge roll)
- Significantly stronger defense layer than in PoE1
"""
        )

        self.mechanics['energy_shield'] = MechanicExplanation(
            name="Energy Shield",
            category=MechanicCategory.DEFENSE,
            short_description="Extra HP pool that recharges - absorbs all damage except bleed/poison",
            detailed_explanation="""
Energy Shield (ES) is an additional hit point pool that sits on top of your life.
Damage goes to ES first before reaching life. ES naturally recharges after
not taking damage for a short time.

Important: Poison and Bleed BYPASS Energy Shield and damage life directly!

NOTE: In PoE2, Chaos Inoculation grants immunity to BOTH chaos AND bleed/poison!
This makes CI much more viable for ES builds than in PoE1.
""",
            how_it_works="""
1. ES is an extra HP pool above your life
2. Damage is taken from ES before life
3. EXCEPTION: Poison and Bleed bypass ES, damage life directly
4. ES starts recharging 2 seconds after last damage taken
5. Recharge rate is 33.3% of maximum ES per second (base)
6. Any damage interrupts the recharge
""",
            calculation_formula="""
Effective HP = Life + Energy Shield (against non-bypass damage)

Recharge:
- Delay: 2 seconds after last damage
- Rate: 33.3% of max ES per second (base)
- Interrupted by any damage taken

Bypass:
- Poison damage bypasses ES
- Bleed damage bypasses ES
- Some special effects bypass ES

PoE2 CHAOS INOCULATION:
- Immune to chaos damage
- Immune to BLEED (NEW in PoE2!)
- Immune to POISON (NEW in PoE2!)
- Life set to 1
""",
            examples=[
                "Bleed/poison bypass ES - use CI for immunity in PoE2",
                "Recharges for free - don't need flasks",
                "2 second delay after damage before recharge starts",
                "CI in PoE2 = chaos + bleed + poison immunity (life = 1)"
            ],
            common_questions={
                "Does bleed hurt through ES?": "Yes! Bleed bypasses ES. Use Chaos Inoculation for immunity in PoE2.",
                "Does poison hurt through ES?": "Yes! Poison bypasses ES. Use Chaos Inoculation for immunity in PoE2.",
                "How fast does ES recharge?": "33.3% per second base, after 2 second delay.",
                "Is ES better than life?": "Different tradeoffs. ES recharges but is bypassed by bleed/poison without CI.",
                "What does CI do in PoE2?": "Chaos Inoculation in PoE2 grants immunity to chaos, bleed, AND poison. Life = 1."
            },
            related_mechanics=['life', 'chaos_inoculation', 'recharge', 'leech'],
            important_notes=[
                "Poison and Bleed BYPASS ES (unless you have CI)",
                "Recharges after 2 seconds of no damage",
                "Base recharge rate: 33.3% per second",
                "Damage is taken from ES before life",
                "PoE2 CI = chaos + bleed + poison immunity (life = 1)"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Chaos Inoculation now grants BLEED immunity (NEW!)
- Chaos Inoculation now grants POISON immunity (NEW!)
- This makes CI much more viable for ES builds in PoE2
- ES recharge mechanics similar to PoE1
"""
        )

        self.mechanics['block'] = MechanicExplanation(
            name="Block",
            category=MechanicCategory.DEFENSE,
            short_description="Chance to completely block strikes and projectiles (not area)",
            detailed_explanation="""
Block gives you a chance to completely negate incoming damage from strikes and
projectiles. When you block, you take zero damage and prevent any ailments
that hit would have applied.

Block requires a shield (25% base) or dual wielding (20% base) and is capped at 50%.

NOTE: Glancing Blows in PoE2 works DIFFERENTLY than PoE1. It now affects
Evade/Deflect mechanics, not Block.
""",
            how_it_works="""
1. Shield provides base 25% block chance
2. Dual wielding provides base 20% block chance
3. Block is capped at 50% maximum
4. Successful block = zero damage taken
5. Blocked hits cannot apply ailments
6. Does NOT work against area damage by default
""",
            calculation_formula="""
Block Chance = Base (25% shield, 20% dual wield) + modifiers
Capped at 50%

On successful block:
- Take 0 damage
- No ailments applied

NOTE: Glancing Blows in PoE2 affects Evade/Deflect, NOT Block!
- Makes Evade chance Unlucky
- Makes Deflect chance Lucky
""",
            examples=[
                "50% block cap - solid defense layer",
                "Shields provide 25% base block",
                "Blocks prevent ailments too",
                "Glancing Blows in PoE2 affects Evade/Deflect, not Block"
            ],
            common_questions={
                "What's the block cap?": "50% maximum block chance.",
                "Can I block spells?": "Yes, if you have spell block chance from sources like shields or passives.",
                "Does block work against area damage?": "Not by default. Some items/passives add this.",
                "What is Glancing Blows in PoE2?": "In PoE2, Glancing Blows makes Evade Unlucky and Deflect Lucky. It no longer affects block.",
                "What is Deflect?": "Deflect is a new mechanic in PoE2 separate from block. Glancing Blows interacts with it."
            },
            related_mechanics=['armor', 'evasion', 'deflect', 'spell_block'],
            important_notes=[
                "50% cap on block chance",
                "Successful block = 0 damage AND no ailments",
                "Does NOT work against area by default",
                "Shield = 25% base, Dual wield = 20% base",
                "Glancing Blows in PoE2 affects Evade/Deflect, NOT block"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Block core mechanics similar
- Glancing Blows COMPLETELY CHANGED - now affects Evade/Deflect, not Block
- Deflect is a new mechanic in PoE2
"""
        )

        # =====================================================================
        # RESOURCES
        # =====================================================================

        self.mechanics['spirit'] = MechanicExplanation(
            name="Spirit",
            category=MechanicCategory.RESOURCES,
            short_description="NEW resource for permanent skills (auras, heralds, minions)",
            detailed_explanation="""
Spirit is a NEW resource in PoE2 that powers permanent skills like auras,
heralds, and persistent minions. Unlike PoE1's mana reservation, Spirit is
a completely separate resource that doesn't affect your mana pool.

Spirit has fixed costs (not percentages) making it easier to plan your build.
""",
            how_it_works="""
1. Spirit is gained from gear, passives, and uniques
2. Permanent skills reserve a fixed amount of Spirit
3. Spirit reservation does NOT affect mana
4. Can only activate skills if you have enough available Spirit
5. Deactivating skills immediately frees the Spirit
6. Support gems can modify Spirit costs
""",
            calculation_formula="""
Available Spirit = Maximum Spirit - Reserved Spirit

Example:
- Maximum Spirit: 100
- Aura: 30 Spirit
- Herald: 25 Spirit
- Reserved: 55 Spirit
- Available: 45 Spirit

Fixed costs mean you know exactly what you can run.
""",
            examples=[
                "Auras cost fixed Spirit amounts (not percentages)",
                "Amulets are a major source of Spirit",
                "Plan your permanent skills around Spirit budget",
                "Support gems can reduce Spirit costs"
            ],
            common_questions={
                "What gives Spirit?": "Gear (especially amulets), passives, and some uniques.",
                "Is Spirit like mana reservation?": "Similar purpose but separate resource. Doesn't affect mana pool.",
                "What uses Spirit?": "Auras, heralds, persistent minions, and some other permanent effects.",
                "Can I increase Spirit?": "Yes, through gear, passives, and uniques."
            },
            related_mechanics=['auras', 'heralds', 'mana', 'reservation'],
            important_notes=[
                "NEW to PoE2 - didn't exist in PoE1",
                "Separate from mana - doesn't affect mana pool",
                "Fixed costs, not percentages",
                "Plan around Spirit budget for permanent skills",
                "Support gems can modify Spirit costs"
            ],
            changed_from_poe1="""
Spirit is COMPLETELY NEW in PoE2:
- Replaces percentage-based mana reservation
- Is a separate resource from mana
- Has fixed costs instead of percentages
- Much easier to plan and budget
"""
        )

        # =====================================================================
        # DAMAGE SCALING
        # =====================================================================

        self.mechanics['increased_vs_more'] = MechanicExplanation(
            name="Increased vs More Damage",
            category=MechanicCategory.SCALING,
            short_description="Additive (increased) vs Multiplicative (more) damage scaling",
            detailed_explanation="""
This is THE most important damage scaling concept in Path of Exile.

- "Increased" modifiers are ADDITIVE with each other
- "More" modifiers are MULTIPLICATIVE with everything

Understanding this is crucial for optimizing damage.
""",
            how_it_works="""
1. All "Increased" modifiers add together first
   - 50% + 30% + 20% increased = 100% increased = 2.0x multiplier

2. All "More" modifiers multiply separately
   - 30% more x 20% more = 1.3 x 1.2 = 1.56x multiplier

3. Order of operations:
   Base Damage x (1 + Sum of Increased) x (More 1) x (More 2) x ...

The KEY insight: If you already have lots of "increased" damage,
adding more "increased" has diminishing returns. "More" multipliers
always give their full multiplicative benefit.
""",
            calculation_formula="""
Final Damage = Base x (1 + TotalIncreased%) x More1 x More2 x More3...

Example:
- Base: 100 damage
- Increased: 50% + 30% + 20% = 100% increased
- More: 30% more, 20% more
- Calculation: 100 x 2.0 x 1.3 x 1.2 = 312 damage

Why More is powerful:
- If you have 200% increased, adding 100% more = 3.0x -> 4.0x (33% gain)
- Adding 50% more instead = 3.0x x 1.5 = 4.5x (50% gain!)
""",
            examples=[
                "Support gems with 'more damage' are very powerful",
                "Stacking 'increased' has diminishing returns",
                "Check wording carefully - 'more' vs 'increased' matters",
                "This applies to ALL modifiers: damage, speed, area, etc."
            ],
            common_questions={
                "Is 'more' always better?": "Usually, especially if you have lots of 'increased' already.",
                "How do 'less' modifiers work?": "'Less' is multiplicative reduction, 'reduced' is additive reduction.",
                "Does this apply to defense?": "Yes! The same logic applies to all modifiers in PoE.",
                "Why does my damage barely increase?": "Probably diminishing returns from stacking 'increased' modifiers."
            },
            related_mechanics=['damage_calculation', 'support_gems', 'passive_tree'],
            important_notes=[
                "Increased = additive, More = multiplicative",
                "This is CORE to understanding PoE damage",
                "Applies to ALL modifier types, not just damage",
                "Read gem and item text carefully",
                "More multipliers are almost always worth taking"
            ],
            changed_from_poe1="Same system as PoE1. This is a core PoE mechanic."
        )

        self.mechanics['crit'] = MechanicExplanation(
            name="Critical Strike",
            category=MechanicCategory.DAMAGE,
            short_description="Hits that deal bonus damage based on critical multiplier",
            detailed_explanation="""
Critical strikes deal bonus damage based on your critical strike multiplier.
In PoE2, the base crit multiplier is +100% (so crits deal 200% damage).

IMPORTANT: In PoE2, critical strikes do NOT guarantee ailments like they
did in PoE1. Crits just deal more damage, which indirectly helps ailment
application through the threshold system.
""",
            how_it_works="""
1. Each hit rolls against your critical strike chance
2. If successful, damage is multiplied by your crit multiplier
3. Base crit multiplier in PoE2 is +100% (200% damage)
4. Crits do NOT guarantee ailments (unlike PoE1!)
5. Crit chance is capped at 100%
6. Crit multiplier has no cap
""",
            calculation_formula="""
Critical Hit Damage = Base Damage x (1 + Crit Multiplier)
Base Crit Multiplier = +100% (200% damage)

Expected Damage:
DPS = Base x [(1 - CritChance) + (CritChance x CritMultiplier)]

Example:
- Base: 1000 damage
- 50% crit chance, +150% crit multi (250% damage on crit)
- Expected: 1000 x [0.5 + (0.5 x 2.5)] = 1000 x 1.75 = 1750 DPS
""",
            examples=[
                "Base crit multi is +100% in PoE2 (lower than PoE1's +150%)",
                "Crits do NOT guarantee ailments in PoE2",
                "Need both crit chance AND multiplier for crit builds",
                "Crit chance caps at 100%"
            ],
            common_questions={
                "Do crits guarantee ailments?": "NO! This changed from PoE1. Crits just deal more damage.",
                "What's the base crit multiplier?": "+100% in PoE2 (was +150% in PoE1).",
                "Is crit cap still 100%?": "Yes, crit chance is capped at 100%.",
                "Is crit worth building?": "Yes, if you invest in both chance and multiplier."
            },
            related_mechanics=['crit_chance', 'crit_multiplier', 'ailments'],
            important_notes=[
                "Base crit multiplier is +100% (not +150% like PoE1)",
                "Crits do NOT guarantee ailments in PoE2",
                "Crit chance capped at 100%",
                "Need investment in both chance and multiplier",
                "Crits affect hits only, not DoT"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Base crit multiplier reduced from +150% to +100%
- Crits NO LONGER guarantee ailment application
- Crit builds need to invest more for ailments
- Overall crit is more balanced/accessible
"""
        )

    def get_mechanic(self, name: str) -> Optional[MechanicExplanation]:
        """Get explanation for a specific mechanic"""
        return self.mechanics.get(name.lower())

    def search_mechanics(self, query: str) -> List[MechanicExplanation]:
        """Search for mechanics matching a query"""
        results = []
        query_lower = query.lower()

        for mechanic in self.mechanics.values():
            if (query_lower in mechanic.name.lower() or
                query_lower in mechanic.short_description.lower() or
                query_lower in mechanic.detailed_explanation.lower()):
                results.append(mechanic)

        return results

    def get_by_category(self, category: MechanicCategory) -> List[MechanicExplanation]:
        """Get all mechanics in a specific category"""
        return [m for m in self.mechanics.values() if m.category == category]

    def list_all_mechanics(self) -> List[str]:
        """List all available mechanics"""
        return list(self.mechanics.keys())

    def format_mechanic_explanation(self, mechanic: MechanicExplanation, include_all: bool = True) -> str:
        """Format a mechanic explanation as readable text"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"{mechanic.name.upper()}")
        lines.append("=" * 80)
        lines.append(f"Category: {mechanic.category.value}")
        lines.append(f"\n{mechanic.short_description}")
        lines.append("\n" + "-" * 80)
        lines.append("DETAILED EXPLANATION")
        lines.append("-" * 80)
        lines.append(mechanic.detailed_explanation)

        lines.append("\n" + "-" * 80)
        lines.append("HOW IT WORKS")
        lines.append("-" * 80)
        lines.append(mechanic.how_it_works)

        if mechanic.calculation_formula:
            lines.append("\n" + "-" * 80)
            lines.append("CALCULATION")
            lines.append("-" * 80)
            lines.append(mechanic.calculation_formula)

        if include_all:
            if mechanic.examples:
                lines.append("\n" + "-" * 80)
                lines.append("EXAMPLES")
                lines.append("-" * 80)
                for i, example in enumerate(mechanic.examples, 1):
                    lines.append(f"{i}. {example}")

            if mechanic.common_questions:
                lines.append("\n" + "-" * 80)
                lines.append("COMMON QUESTIONS")
                lines.append("-" * 80)
                for question, answer in mechanic.common_questions.items():
                    lines.append(f"\nQ: {question}")
                    lines.append(f"A: {answer}")

            if mechanic.important_notes:
                lines.append("\n" + "-" * 80)
                lines.append("IMPORTANT NOTES")
                lines.append("-" * 80)
                for note in mechanic.important_notes:
                    lines.append(f"* {note}")

            if mechanic.changed_from_poe1:
                lines.append("\n" + "-" * 80)
                lines.append("CHANGES FROM POE1")
                lines.append("-" * 80)
                lines.append(mechanic.changed_from_poe1)

            if mechanic.related_mechanics:
                lines.append("\n" + "-" * 80)
                lines.append(f"RELATED: {', '.join(mechanic.related_mechanics)}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    def answer_question(self, question: str) -> Optional[str]:
        """Answer a specific question about mechanics"""
        question_lower = question.lower()

        for mechanic in self.mechanics.values():
            for q, a in mechanic.common_questions.items():
                if question_lower in q.lower() or q.lower() in question_lower:
                    return f"**{mechanic.name} - {q}**\n\n{a}\n\nFor more details, see the full {mechanic.name} explanation."

        return None


if __name__ == "__main__":
    kb = PoE2MechanicsKnowledgeBase()

    print("Path of Exile 2 Mechanics Knowledge Base")
    print("VERIFIED FOR POE2 - December 2025")
    print("=" * 80)
    print()

    print("Available mechanics:")
    for name in kb.list_all_mechanics():
        mechanic = kb.get_mechanic(name)
        print(f"  - {name}: {mechanic.short_description}")

    print()
    print("=" * 80)
    print("Example: Poison mechanic")
    print("=" * 80)
    poison = kb.get_mechanic("poison")
    if poison:
        print(kb.format_mechanic_explanation(poison, include_all=False))
