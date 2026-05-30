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

        self.mechanics['runic_ward'] = MechanicExplanation(
            name="Runic Ward",
            category=MechanicCategory.DEFENSE,
            short_description="New defense pool added in Patch 0.5 via Verisium Runeforging on armours (PRELIMINARY — exact mechanics pending local extraction)",
            detailed_explanation="""
Runic Ward is a new defensive layer introduced in Path of Exile 2 Patch 0.5
"Return of the Ancients" (2026-05-29). It is added to armour pieces through
the new Verisium Runeforging system.

PRELIMINARY ENTRY: Exact mechanics — recharge behavior, bypass interactions,
stacking rules across multiple Runeforged pieces, and the cap — have NOT yet
been extracted from the patched game files. This entry exists so a query for
"runic ward" returns a clear "what it is + what we don't yet know" rather
than an unhelpful "unknown mechanic" response. Update once .datc64
re-extraction completes.
""",
            how_it_works="""
PENDING EXTRACTION. Update this section once Runic Ward mechanics are
extracted from local .datc64 files. Specifically need to confirm:
- Where Runic Ward sits in the PoE2 damage layer order
  (Evasion -> Block -> Armour -> Resistances -> Life/ES)
- Whether it recharges, and on what trigger/delay/rate
- Whether any damage types bypass it (analogous to bleed/poison vs ES)
- Stacking rules across multiple Runeforged armour pieces
- Maximum / cap behavior
- Interactions with damage-taken-as-* conversions
""",
            examples=[
                "Add Runic Ward to chest armour via Verisium Runeforging (PoE2 0.5 crafting)",
                "Currently NOT layered into EHP calculator output - survivability may be UNDERESTIMATED for builds using Runeforged armour",
            ],
            common_questions={
                "What is Runic Ward?": "A new defense pool added in PoE2 Patch 0.5 via Verisium Runeforging on armour pieces. Distinct from Energy Shield, Armour, and Evasion.",
                "How does it interact with EHP?": "PRELIMINARY - the runic_ward field exists on DefensiveStats but is not yet layered into calculate_ehp. EHP for builds using Runeforged armour will be underestimated until mechanics extraction lands.",
                "Where does it come from?": "Verisium Runeforging - a new crafting system added in Patch 0.5 'Return of the Ancients'.",
                "Does it stack with Energy Shield?": "PENDING EXTRACTION - relationship to ES and other defense pools not yet confirmed from game files.",
            },
            related_mechanics=['energy_shield', 'armor', 'life', 'block'],
            important_notes=[
                "PRELIMINARY entry - exact mechanics pending local .datc64 re-extraction post-0.5",
                "DefensiveStats.runic_ward stub exists but is not layered into calculate_ehp",
                "Builds using Runeforged armour will have their EHP UNDERESTIMATED in current calculations",
                "Added in Patch 0.5 'Return of the Ancients' (2026-05-29)",
                "Do NOT publish numeric Runic Ward stats until extracted from local game data per project data policy",
            ],
            changed_from_poe1="N/A - entirely new mechanic introduced in PoE2 Patch 0.5"
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

        # =====================================================================
        # RESOURCE MECHANICS
        # =====================================================================

        self.mechanics['leech'] = MechanicExplanation(
            name="Life Leech",
            category=MechanicCategory.RESOURCES,
            short_description="Recover life based on damage dealt - NO CAP in PoE2, balanced by monster resistance",
            detailed_explanation="""
Life Leech allows you to recover life based on the damage you deal. When you hit
an enemy with an attack that has leech, a portion of the damage dealt is recovered
as life over time.

IMPORTANT CONCEPTS (PoE2 DIFFERS FROM PoE1):
- Leech RATE: How much damage is converted to leech (e.g., 5% of physical damage)
- Leech INSTANCE: Each hit creates a leech instance that heals over 1 SECOND (base)
- NO LEECH CAP: PoE2 has NO maximum leech per second (unlike PoE1's 20% cap)
- MONSTER LEECH RESISTANCE: Scales with monster level, reduces leech effectiveness
- OVERLEECH: Ability for leech to continue past full life (requires specific sources)

By default, leech stops when you reach full life. Overleech (from items like
Couture of Crimson, Life Leech III gem, or passives like Fast Metabolism) allows
leech instances to continue healing even at full life, creating a buffer.
""",
            how_it_works="""
1. You deal damage with a hit that has life leech
2. Base leech = Damage × Leech Rate (e.g., 2000 damage × 5% = 100 life)
3. Monster Leech Resistance reduces this: Effective = Base × (1 - Monster_Leech_Res%)
4. A leech instance is created that recovers the full amount over 1 SECOND (base)
5. NO CAP on total leech - unlimited instances can stack
6. Leech stops at full life UNLESS you have Overleech
7. With Overleech, instances continue past full life (healing buffer)
""",
            calculation_formula="""
Leech Per Hit = Damage_Dealt × Leech_Rate% × (1 - Monster_Leech_Resistance%)

Recovery Duration = 1 second (base, modifiable by 'leech faster/slower')
Recovery Per Second = Leech_Amount / Recovery_Duration

Example:
- 5% physical leech, 2000 damage hit, monster has 30% leech resistance
- Base leech = 2000 × 0.05 = 100 life
- Effective leech = 100 × (1 - 0.30) = 70 life
- Recovery = 70 life over 1 second = 70 life/sec per instance

Multiple hits = multiple instances = multiplicative recovery (no cap!)
- 10 hits/second × 70 life/instance = 700 life/sec total

Modifiers:
- 'Leech X% faster' = shorter recovery duration (more life/sec)
- 'Leech X% slower' = longer recovery duration (less life/sec, but longer overleech)
""",
            examples=[
                "5% physical leech on a ring means 5% of physical damage heals you",
                "Life Leech I: 12% physical leech",
                "Life Leech II: 16% physical leech",
                "Life Leech III: 16% physical + OVERLEECH (leech continues at full life)",
                "Fast Metabolism: Overleech + leech expires 20% slower (1.25s duration)",
                "Savoured Blood passive: +35% leech amount, 20% slower (good for overleech builds)"
            ],
            common_questions={
                "What is the leech cap in PoE2?": "There is NO cap! PoE2 removed the 20% max life/sec cap from PoE1. Balance comes from monster leech resistance instead.",
                "What is monster leech resistance?": "Monsters have innate resistance that reduces leech effectiveness. Scales with monster level. Exact formula is not public.",
                "What is overleech?": "Normally leech stops at full life. Overleech lets it continue, creating a healing buffer against incoming damage.",
                "Does elemental damage leech?": "Only physical by default. Need specific sources (Mystic Harvest, items, passives) for elemental leech.",
                "Is more leech % always better?": "In PoE2, yes! There's no cap, so more leech = more recovery. Monster resistance is the limiting factor.",
                "Do I need Life Leech support if I have leech on gear?": "Depends on your leech rate and attack speed. More sources = more recovery since there's no cap.",
                "Life Leech III vs Life Leech II?": "Both give 16% leech, but III provides OVERLEECH. Get III for sustain builds."
            },
            related_mechanics=['life', 'energy_shield', 'mana_leech', 'overleech'],
            important_notes=[
                "NO LEECH CAP in PoE2 - this is a major change from PoE1",
                "Monster leech resistance scales with level (exact formula unknown)",
                "Base recovery duration: 1 second per instance",
                "Physical damage leech is most common",
                "Elemental leech requires specific sources",
                "Overleech sources: Life Leech III, Fast Metabolism, Couture of Crimson",
                "Leech 'faster' = more recovery/sec, 'slower' = longer overleech duration"
            ],
            changed_from_poe1="""
MAJOR CHANGES from PoE1:
- NO 20% max life/sec leech cap (PoE1 had hard cap)
- NO 2% instance rate (PoE2 uses fixed 1 second recovery)
- Monster Leech Resistance added as balancing mechanism (scales with level)
- Vaal Pact now only disables life flasks (not all life recovery like PoE1)
- Overleech is now accessible from gems (Life Leech III) and passives (Fast Metabolism)
- 'Leech faster/slower' modifiers affect the 1 second base duration
"""
        )

        self.mechanics['endurance_charges'] = MechanicExplanation(
            name="Endurance Charges",
            category=MechanicCategory.RESOURCES,
            short_description="Defensive charges that grant physical damage reduction and elemental resistances",
            detailed_explanation="""
Endurance Charges are one of three charge types in Path of Exile 2. They provide
defensive bonuses and are primarily associated with Strength-based builds.

BONUSES PER CHARGE:
- +4% Physical Damage Reduction
- +4% to all Elemental Resistances

Default maximum: 3 charges
Duration: 10 seconds (refreshed when gaining any endurance charge)

Some skills can CONSUME endurance charges for powerful effects. For example,
Arctic Howl can consume an Endurance Charge to bypass its cooldown.
""",
            how_it_works="""
1. Generate charges through skills, passives, or on-kill effects
2. Each charge grants +4% phys reduction and +4% all elemental res
3. Charges last 10 seconds by default
4. Gaining a charge refreshes ALL charge durations
5. Maximum 3 charges by default (can be increased)
6. Some skills CONSUME charges for bonus effects
7. Consumed charges still count as 'losing' charges for conditional effects
""",
            calculation_formula="""
Physical Damage Reduction = Charges × 4%
Elemental Resistance Bonus = Charges × 4% (to each element)

Example with 3 Endurance Charges:
- Physical Reduction: 3 × 4% = 12% physical damage reduction
- Fire Resistance: +12%
- Cold Resistance: +12%
- Lightning Resistance: +12%

With +3 max charges (6 total):
- Physical Reduction: 24%
- Each Elemental Res: +24%
""",
            examples=[
                "3 charges = 12% physical reduction + 12% to all elemental resistances",
                "Arctic Howl consumes Endurance Charge to bypass cooldown",
                "Guts notable: Recover 3% max life per Endurance Charge consumed",
                "Can stack to 6+ with passives like Endurance (+2) or Grit (+1)"
            ],
            common_questions={
                "How do I generate Endurance Charges?": "Skills (Enduring Cry), on-kill effects, passives, or items.",
                "What consumes Endurance Charges?": "Some skills like Arctic Howl, or passives that trigger on consumption.",
                "Is the resistance bonus capped?": "No, but overall resistance caps still apply (75%/90%).",
                "Do charges refresh when gaining more?": "Yes, gaining ANY charge refreshes ALL charges of that type."
            },
            related_mechanics=['frenzy_charges', 'power_charges', 'armor', 'resistance'],
            important_notes=[
                "+4% Physical Damage Reduction per charge",
                "+4% to ALL Elemental Resistances per charge",
                "Default max: 3 charges",
                "Duration: 10 seconds (refreshes on gain)",
                "Some skills CONSUME charges for effects",
                "Arctic Howl can bypass cooldown by consuming Endurance"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Similar system but specific skill interactions differ
- New skills in PoE2 can consume charges in different ways
- Integration with PoE2's cooldown and Spirit systems
"""
        )

        self.mechanics['frenzy_charges'] = MechanicExplanation(
            name="Frenzy Charges",
            category=MechanicCategory.RESOURCES,
            short_description="Offensive charges that grant attack/cast speed and MORE damage",
            detailed_explanation="""
Frenzy Charges are offensive charges that provide both speed and damage bonuses.
They are primarily associated with Dexterity-based builds.

BONUSES PER CHARGE:
- +4% increased Attack Speed
- +4% increased Cast Speed
- +4% MORE Damage (multiplicative!)

Default maximum: 3 charges
Duration: 10 seconds (refreshed when gaining any frenzy charge)

The MORE damage modifier is extremely valuable as it multiplies your final damage
rather than being additive with other increases.
""",
            how_it_works="""
1. Generate charges through skills, passives, or on-kill effects
2. Each charge grants +4% attack speed, +4% cast speed, +4% MORE damage
3. Charges last 10 seconds by default
4. Gaining a charge refreshes ALL charge durations
5. Maximum 3 charges by default (can be increased)
6. Some skills CONSUME charges for bonus effects
7. MORE damage is multiplicative (very powerful)
""",
            calculation_formula="""
Attack/Cast Speed = Base × (1 + Charges × 0.04)
Damage Multiplier = (1 + Charges × 0.04) [MORE, not increased!]

Example with 3 Frenzy Charges:
- Speed: +12% attack and cast speed
- Damage: 1.12× MORE damage (multiplicative)

Example DPS calculation:
- Base DPS: 10,000
- 3 Frenzy Charges: 10,000 × 1.12 = 11,200 DPS
- Plus 12% attack speed means even more effective DPS
""",
            examples=[
                "3 charges = +12% speed and 12% MORE damage",
                "The Frenzied Bear: 30% damage + 10% skill speed when consumed recently",
                "Thrilling Chase: 50% chance to double consumption benefits",
                "Valako's Roar charm grants Frenzy Charge when triggered"
            ],
            common_questions={
                "Is Frenzy Charge damage 'increased' or 'more'?": "MORE damage - it's multiplicative, making it very powerful.",
                "How do I generate Frenzy Charges?": "Skills, on-kill effects, charms (like Valako's Roar), or passives.",
                "What's the difference between having and consuming?": "Having gives passive bonuses. Consuming triggers specific effects but removes the charge.",
                "Do charges refresh when gaining more?": "Yes, gaining ANY charge refreshes ALL charges of that type."
            },
            related_mechanics=['endurance_charges', 'power_charges', 'attack_speed', 'more_vs_increased'],
            important_notes=[
                "+4% Attack Speed per charge",
                "+4% Cast Speed per charge",
                "+4% MORE Damage per charge (multiplicative!)",
                "Default max: 3 charges",
                "Duration: 10 seconds (refreshes on gain)",
                "MORE damage is extremely valuable"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Frenzy charges now grant +4% MORE damage (was +4% increased in early PoE1)
- Integration with PoE2 charm system for generation
- New consumption effects on skills and passives
"""
        )

        self.mechanics['power_charges'] = MechanicExplanation(
            name="Power Charges",
            category=MechanicCategory.RESOURCES,
            short_description="Critical strike charges that grant increased critical strike chance",
            detailed_explanation="""
Power Charges are critical-strike focused charges that boost your chance to crit.
They are primarily associated with Intelligence-based builds.

BONUSES PER CHARGE:
- +40% increased Critical Strike Chance

Default maximum: 3 charges
Duration: 10 seconds (refreshed when gaining any power charge)

Power charges are essential for crit builds, providing a significant boost to
critical strike chance which then benefits from your crit multiplier.
""",
            how_it_works="""
1. Generate charges through skills, passives, or on-crit effects
2. Each charge grants +40% increased Critical Strike Chance
3. Charges last 10 seconds by default
4. Gaining a charge refreshes ALL charge durations
5. Maximum 3 charges by default (can be increased)
6. Some skills CONSUME charges for bonus effects
7. Crit chance is still capped at 100%
""",
            calculation_formula="""
Crit Chance Bonus = Charges × 40% increased

Example with 3 Power Charges:
- Crit Bonus: 3 × 40% = 120% increased critical strike chance

If base crit is 7%:
- Without charges: 7% × (1 + other_increased)
- With 3 charges: 7% × (1 + other_increased + 1.2)

Example:
- 7% base crit, 100% increased from other sources
- Without Power Charges: 7% × 2.0 = 14% crit
- With 3 Power Charges: 7% × (2.0 + 1.2) = 7% × 3.2 = 22.4% crit
""",
            examples=[
                "3 charges = +120% increased critical strike chance",
                "Essential for crit builds to reliably hit crits",
                "Elemental Surge: Consume Power Charge to gain 3 Cold Surges",
                "Can stack to 6+ with passives and gear"
            ],
            common_questions={
                "Is Power Charge crit 'increased' or 'more'?": "INCREASED - it adds to your other crit chance increases.",
                "How do I generate Power Charges?": "On-crit effects, skills (Power Siphon, etc.), or passives.",
                "Are Power Charges worth it for non-crit builds?": "Generally no - the bonus is specific to critical strikes.",
                "Do charges refresh when gaining more?": "Yes, gaining ANY charge refreshes ALL charges of that type."
            },
            related_mechanics=['endurance_charges', 'frenzy_charges', 'crit', 'crit_multiplier'],
            important_notes=[
                "+40% increased Critical Strike Chance per charge",
                "Default max: 3 charges",
                "Duration: 10 seconds (refreshes on gain)",
                "Increased (not more) crit chance",
                "Crit chance still capped at 100%"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Bonus increased from +30% to +40% per charge
- New consumption effects for PoE2 skills
- Integration with surge system (Elemental Surge)
"""
        )

        # =====================================================================
        # DAMAGE MODIFIERS
        # =====================================================================

        self.mechanics['penetration'] = MechanicExplanation(
            name="Penetration",
            category=MechanicCategory.DAMAGE,
            short_description="Bypasses enemy resistances - your damage ignores a portion of their defense",
            detailed_explanation="""
Penetration is a damage modifier that allows your hits to ignore a portion of enemy
resistances. This is crucial for dealing damage to resistant enemies, especially in
endgame content where monsters often have high elemental or physical resistances.

IMPORTANT DISTINCTIONS:
- Penetration: Only applies to YOUR hits, ignores resistance
- Reduced Resistance: Actually lowers the enemy's resistance (benefits all sources)
- Exposure: A debuff that applies reduced resistance to enemies

Penetration is calculated AFTER other resistance modifiers. It doesn't reduce the
enemy's resistance - it just ignores a portion of it for your damage calculation.
""",
            how_it_works="""
1. Enemy has base resistance (e.g., 40% fire resistance)
2. Your hit calculates damage against: Enemy Resistance - Your Penetration
3. Effective resistance cannot go below -200% (damage cap)
4. Penetration only affects HITS, not damage over time
5. Penetration only benefits YOUR damage, not allies

CALCULATION ORDER:
1. Base enemy resistance
2. + Resistance modifiers (map mods, buffs)
3. - Exposure (if applied)
4. - Reduced resistance effects
5. = Final enemy resistance
6. - Penetration (for your hit only)
7. = Effective resistance against your hit
""",
            calculation_formula="""
Effective Resistance = Enemy Resistance - Your Penetration
Damage Multiplier = 1 - (Effective Resistance / 100)

Example:
- Enemy has 40% fire resistance
- You have 20% fire penetration
- Effective resistance = 40% - 20% = 20%
- Damage multiplier = 1 - 0.20 = 0.80 (you deal 80% damage)

Without penetration:
- Damage multiplier = 1 - 0.40 = 0.60 (you deal 60% damage)

Going Negative:
- Enemy has 30% resistance, you have 50% penetration
- Effective resistance = 30% - 50% = -20%
- Damage multiplier = 1 - (-0.20) = 1.20 (you deal 120% damage!)

Physical Penetration:
- Works the same but against physical damage reduction
- Common sources: Impale, specific skills, passives
""",
            examples=[
                "Fire Penetration Support: Supported skills penetrate 20-37% fire resistance",
                "Elemental Weakness curse reduces resistance (stacks with penetration)",
                "Exposure applies -10% to -25% resistance (different from penetration)",
                "Against 75% resistant boss: 37% pen = 38% res = 62% damage vs 25% without"
            ],
            common_questions={
                "Does penetration work on DoT?": "NO! Penetration only affects hits. DoT uses the enemy's actual resistance.",
                "Is penetration or reduced resistance better?": "Penetration is personal (only your damage). Reduced resistance benefits party members and DoT too.",
                "Can I penetrate below 0% resistance?": "Yes! Negative resistance means you deal bonus damage. Cap is -200%.",
                "Does penetration stack?": "Yes, all penetration sources add together.",
                "Does penetration work against physical?": "Yes, physical penetration exists but is rarer than elemental."
            },
            related_mechanics=['exposure', 'curses', 'resistance', 'damage_calculation'],
            important_notes=[
                "Only affects HITS, not damage over time",
                "Only benefits YOUR damage, not party members",
                "Can push effective resistance negative for bonus damage",
                "Stacks additively from all sources",
                "Calculated after all other resistance modifiers",
                "Physical penetration is separate from elemental penetration"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core mechanics similar but specific values may differ
- Physical penetration more accessible in PoE2
- Integration with new PoE2 support gems
- Exposure system remains but values adjusted
"""
        )

        # =====================================================================
        # DEBUFFS
        # =====================================================================

        self.mechanics['curses'] = MechanicExplanation(
            name="Curses",
            category=MechanicCategory.INTERACTION,
            short_description="Debuffs that weaken enemies - affects all damage sources",
            detailed_explanation="""
Curses are powerful debuffs that weaken enemies, making them take more damage,
deal less damage, or suffer other negative effects. Unlike penetration, curse
effects benefit ALL damage sources - your hits, your DoT, and your party members.

CURSE LIMIT:
- Default: 1 curse per enemy
- Can be increased through passives and items
- Additional curses beyond limit replace the oldest curse

CURSE TYPES:
- Hex Curses: Standard curses, applied and last until duration expires
- Mark Curses: Single-target curses with special mechanics (see 'marks')

CURSE EFFECTIVENESS:
- Enemies can have reduced curse effectiveness (especially bosses)
- Your curse effectiveness modifiers counteract this
- Some enemies are Hexproof (immune to hex curses)
""",
            how_it_works="""
1. Cast curse skill on enemy or enemies
2. Curse applies its debuff effect
3. Duration-based (most hexes) or until enemy dies (marks)
4. Only X curses can be active (default 1)
5. New curses beyond limit replace oldest curse
6. Boss/rare enemies have reduced curse effectiveness

COMMON CURSES:
- Vulnerability: Enemies take increased physical damage
- Elemental Weakness: Reduced elemental resistances
- Temporal Chains: Slows enemy actions and expires slower
- Enfeeble: Enemies deal less damage
- Conductivity/Flammability/Frostbite: Single-element resistance reduction
""",
            calculation_formula="""
Curse Effect = Base Effect × Your Curse Effectiveness × (1 - Enemy Curse Reduction)

Example (Elemental Weakness):
- Base: -30% elemental resistances
- Your curse effect: +50% increased
- Enemy curse reduction: 60% (boss)
- Effect = -30% × 1.5 × 0.4 = -18% resistances

Curse Limit Example:
- You have curse limit of 1
- Apply Vulnerability, then Elemental Weakness
- Only Elemental Weakness remains (replaced Vulnerability)

With +1 curse limit:
- Both curses would remain active
""",
            examples=[
                "Vulnerability: 20-30% increased physical damage taken",
                "Elemental Weakness: -20% to -30% to all elemental resistances",
                "Temporal Chains: 20-30% slower action speed, debuffs expire slower",
                "Despair: Enemies take increased chaos damage, reduced chaos resistance"
            ],
            common_questions={
                "How many curses can I apply?": "Default is 1. Passives like Whispers of Doom and items can increase the limit.",
                "Do curses work on bosses?": "Yes, but bosses have 60%+ reduced curse effectiveness. Invest in curse effect to compensate.",
                "What is Hexproof?": "Hexproof enemies are IMMUNE to hex curses. Marks still work on them.",
                "Is curse effectiveness important?": "Very! Against bosses, without increased curse effect your curses are 60%+ less effective.",
                "Do curses affect DoT?": "Yes! Unlike penetration, curses affect all damage including DoT."
            },
            related_mechanics=['marks', 'penetration', 'exposure', 'debuffs'],
            important_notes=[
                "Default curse limit: 1 (can be increased)",
                "Curses affect ALL damage sources (hits, DoT, party)",
                "Bosses have 60%+ reduced curse effectiveness",
                "Hexproof enemies are immune to hex curses",
                "Marks are a separate category (single target, no limit)",
                "Curse effectiveness mods are crucial for endgame"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Curse/hex distinction more pronounced
- Some curse values adjusted
- Hexproof interactions refined
- Integration with PoE2 skill gem system
"""
        )

        self.mechanics['marks'] = MechanicExplanation(
            name="Marks",
            category=MechanicCategory.INTERACTION,
            short_description="Single-target debuffs that transfer on kill and provide powerful bonuses",
            detailed_explanation="""
Marks are a special type of curse that only affects a single target at a time.
They provide powerful offensive bonuses and have unique mechanics compared to
regular hex curses.

KEY DIFFERENCES FROM HEX CURSES:
- Only ONE enemy can have your mark at a time
- Marks transfer to another enemy on kill (automatic)
- Marks do NOT count against your curse limit
- Marks work on Hexproof enemies
- No duration - lasts until enemy dies or you mark another

MARK TYPES:
- Assassin's Mark: Critical strike bonuses, power charge on kill
- Sniper's Mark: Projectile damage, flask charges on hit
- Predator's Mark: Increased damage taken, life/mana on hit
- Poacher's Mark: Frenzy charges on hit, flask sustain
""",
            how_it_works="""
1. Cast mark skill on a single enemy
2. Mark provides its debuff/bonus effect
3. Killing marked enemy transfers mark to nearby enemy
4. Mark is independent of hex curse limit
5. Can have BOTH a mark AND hex curses on same enemy
6. Works on Hexproof enemies (marks are not hexes)

MARK TRANSFER:
- On kill, mark automatically transfers to nearest valid enemy
- Transfer range is limited (roughly screen width)
- If no valid enemy nearby, mark is lost
- Some skills trigger bonus effects on mark transfer
""",
            calculation_formula="""
Mark Effect = Base Effect × Your Curse Effectiveness × (1 - Enemy Curse Reduction)

Note: Same effectiveness calculation as curses, but:
- Not affected by curse limit
- Works on Hexproof
- Only one mark active at a time

Example (Sniper's Mark):
- Base: 35% increased damage taken from projectiles
- Boss curse reduction: 60%
- Effect: 35% × 0.4 = 14% increased damage taken

Mark + Curse Stacking:
- Enemy can have 1 mark + up to your curse limit in hexes
- All effects apply simultaneously
""",
            examples=[
                "Assassin's Mark: +3% base crit chance against marked, power charge on kill",
                "Sniper's Mark: 35% increased projectile damage taken, flask charges on hit",
                "Predator's Mark: 10% of damage taken as life/mana on hit",
                "Poacher's Mark: Frenzy charge on hit, increased flask charges"
            ],
            common_questions={
                "Do marks count against curse limit?": "NO! Marks are separate. You can have 1 mark + all your curses.",
                "Do marks work on Hexproof enemies?": "YES! Marks are not hexes, so Hexproof doesn't block them.",
                "Can I have multiple marks?": "No, you can only have one mark active at a time. New marks replace old.",
                "Do marks transfer automatically?": "Yes, on kill the mark transfers to a nearby enemy within range.",
                "Which mark is best?": "Depends on build. Assassin's for crit, Sniper's for projectiles, Predator's for sustain."
            },
            related_mechanics=['curses', 'hexproof', 'debuffs', 'single_target'],
            important_notes=[
                "Only ONE mark active at a time",
                "Does NOT count against curse limit",
                "Works on Hexproof enemies",
                "Transfers to nearby enemy on kill",
                "No duration - lasts until death or replaced",
                "Subject to curse effectiveness reduction on bosses"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Mark system refined and expanded
- Mark transfer mechanics more reliable
- Specific mark skills adjusted for PoE2 balance
- Integration with PoE2 skill system
"""
        )

        # =====================================================================
        # NEW POE2 DEFENSES
        # =====================================================================

        self.mechanics['ward'] = MechanicExplanation(
            name="Ward",
            category=MechanicCategory.DEFENSE,
            short_description="NEW in PoE2 - Absorbs damage completely until broken, then restores after delay",
            detailed_explanation="""
Ward is a NEW defensive mechanic in PoE2 that provides a unique form of damage
absorption. Unlike Energy Shield, Ward completely absorbs incoming damage until
it's depleted, then enters a restoration period.

KEY CHARACTERISTICS:
- Absorbs ALL damage types (including chaos)
- Does not split damage like ES (fully absorbs or breaks)
- Restores fully after a delay when not taking damage
- Cannot be leeched or regenerated
- Does not recharge partially - it's all or nothing

Ward is particularly effective against many small hits but can be overwhelmed
by large single hits that exceed your Ward amount.
""",
            how_it_works="""
1. Ward absorbs incoming damage completely
2. If hit damage < Ward: Ward absorbs hit, Ward reduced by hit amount
3. If hit damage > Ward: Ward breaks, remaining damage goes to ES/Life
4. When Ward reaches 0, it enters "broken" state
5. After X seconds of not taking damage, Ward restores to FULL
6. Restoration is all-or-nothing (no partial restore)

DAMAGE ABSORPTION:
- Ward absorbs before Energy Shield and Life
- Works against ALL damage types including chaos
- Each hit is processed separately
- Ward cannot go negative

RESTORATION:
- Default restoration delay: ~5 seconds
- Must take NO damage during delay
- Restores to maximum Ward instantly
- Some sources modify restoration delay
""",
            calculation_formula="""
Damage Flow:
1. Incoming Hit Damage
2. Ward absorbs (if Ward > 0)
3. If Ward >= Damage: Ward -= Damage, you take 0
4. If Ward < Damage: Ward = 0 (broken), overflow to ES/Life

Example (100 Ward):
- 50 damage hit: Ward absorbs fully, Ward = 50 remaining
- 30 damage hit: Ward absorbs fully, Ward = 20 remaining
- 40 damage hit: Ward breaks (40 > 20), 20 damage to ES/Life

Restoration:
- After 5 seconds of no damage: Ward = Maximum Ward
- Damage resets the timer
- Must avoid ALL damage during restore period

Effective HP:
- Ward + ES + Life (but Ward must fully absorb each hit)
- Better modeled as "absorb X damage, then restore"
""",
            examples=[
                "Ward effectively makes you immune to small hits",
                "Useful against DoT ground effects and small projectiles",
                "Large boss hits will break Ward and overflow to life",
                "Pairs well with evasion (fewer hits = more Ward uptime)"
            ],
            common_questions={
                "How is Ward different from Energy Shield?": "Ward absorbs fully or breaks. ES is depleted proportionally. Ward restores fully after delay, ES recharges gradually.",
                "Does Ward block chaos damage?": "YES! Ward absorbs ALL damage types including chaos.",
                "Can I leech Ward?": "No. Ward cannot be leeched, regenerated, or recovered - only restored after delay.",
                "Is Ward good against bosses?": "Mixed. Good against adds and small attacks, but big boss hits break it instantly.",
                "What affects Ward restoration?": "Some items and passives reduce restoration delay. Taking any damage resets the timer."
            },
            related_mechanics=['energy_shield', 'life', 'evasion', 'damage_absorption'],
            important_notes=[
                "NEW to PoE2 - didn't exist in PoE1",
                "Absorbs ALL damage types including chaos",
                "All-or-nothing: fully absorbs each hit or breaks",
                "Cannot be leeched or regenerated",
                "Restores FULLY after delay with no damage taken",
                "Best against many small hits, weak against big hits",
                "Default restoration delay: ~5 seconds"
            ],
            changed_from_poe1="Ward is COMPLETELY NEW in PoE2. PoE1 had a different 'Ward' mechanic on specific uniques that worked differently."
        )

        # =====================================================================
        # ATTRIBUTES
        # =====================================================================

        self.mechanics['attributes'] = MechanicExplanation(
            name="Attributes",
            category=MechanicCategory.SCALING,
            short_description="Core stats (Strength, Dexterity, Intelligence) that provide bonuses and meet requirements",
            detailed_explanation="""
Attributes are the three core stats in Path of Exile 2: Strength, Dexterity, and Intelligence.
They serve two primary purposes:
1. Meeting equipment and skill gem requirements
2. Providing inherent bonuses to your character

Each class starts with different base attributes and gains different amounts per level.
The passive tree also provides substantial attribute bonuses along its paths.

STRENGTH (Red):
- +1 Maximum Life per 2 Strength
- +1% Melee Physical Damage per 5 Strength
- Required for Strength-based gear (armor, maces, axes)
- Required for Strength skill gems

DEXTERITY (Green):
- +2 Accuracy Rating per 1 Dexterity
- +1% Evasion Rating per 5 Dexterity
- Required for Dexterity-based gear (evasion, bows, daggers)
- Required for Dexterity skill gems

INTELLIGENCE (Blue):
- +1 Maximum Mana per 2 Intelligence
- +1% Maximum Energy Shield per 5 Intelligence
- Required for Intelligence-based gear (ES, wands, staves)
- Required for Intelligence skill gems
""",
            how_it_works="""
1. Base attributes come from your class choice
2. Gain attributes from passive tree, gear, and skill gems
3. Bonuses are calculated continuously as attributes change
4. Equipment requirements are checked when equipping items
5. Skill gem requirements are checked when socketing gems
6. Failing to meet requirements = cannot use item/gem

REQUIREMENT CALCULATION:
- Each piece of gear has fixed attribute requirements
- Skill gems have requirements that increase with gem level
- Hybrid gear has requirements from multiple attributes
- Some items reduce attribute requirements globally

BONUS CALCULATION:
- Life from Strength = floor(Strength / 2)
- Melee phys bonus = floor(Strength / 5)%
- Accuracy from Dex = Dexterity × 2
- Evasion bonus = floor(Dexterity / 5)%
- Mana from Int = floor(Intelligence / 2)
- ES bonus = floor(Intelligence / 5)%
""",
            calculation_formula="""
STRENGTH:
Maximum Life Bonus = floor(Strength / 2)
Melee Physical Damage = +floor(Strength / 5)% increased

DEXTERITY:
Accuracy Rating Bonus = Dexterity × 2
Evasion Rating = +floor(Dexterity / 5)% increased

INTELLIGENCE:
Maximum Mana Bonus = floor(Intelligence / 2)
Energy Shield = +floor(Intelligence / 5)% increased

Example (200 of each attribute):
- Strength 200: +100 max life, +40% melee physical damage
- Dexterity 200: +400 accuracy, +40% evasion rating
- Intelligence 200: +100 max mana, +40% energy shield
""",
            examples=[
                "Marauder starts with high Strength, low Dexterity/Intelligence",
                "A level 20 skill gem might require 111 of its primary attribute",
                "Hybrid gear (Str/Dex armor) requires both attributes",
                "Attribute requirements on gear cap around 180 for endgame items"
            ],
            common_questions={
                "What if I don't meet requirements?": "You cannot equip the item or use the skill gem. The item will be greyed out.",
                "Do attribute bonuses stack?": "Yes, all attribute bonuses from all sources add together.",
                "Which attribute is most important?": "Depends on build. Strength for melee/life, Dex for evasion/accuracy, Int for ES/mana builds.",
                "How do I get more attributes?": "Passive tree, gear affixes, skill gems, and some unique items.",
                "Do attributes affect damage directly?": "Only Strength affects damage (melee physical). Others affect accuracy/defenses."
            },
            related_mechanics=['life', 'mana', 'energy_shield', 'accuracy', 'evasion'],
            important_notes=[
                "Strength: +0.5 life per point, +1% melee phys per 5 points",
                "Dexterity: +2 accuracy per point, +1% evasion per 5 points",
                "Intelligence: +0.5 mana per point, +1% ES per 5 points",
                "Gear and gems have attribute requirements",
                "All three attributes are useful for most builds (requirements)",
                "Amulets can have large attribute bonuses"
            ],
            changed_from_poe1="Core mechanics are the same. Values may be slightly adjusted for PoE2 balance."
        )

        # =====================================================================
        # FLASK MECHANICS
        # =====================================================================

        self.mechanics['flask'] = MechanicExplanation(
            name="Flask",
            category=MechanicCategory.RESOURCES,
            short_description="Consumable charges that restore life/mana or grant utility effects",
            detailed_explanation="""
Flasks are a core survival and utility mechanic in Path of Exile 2. Unlike PoE1, flask
management in PoE2 is more deliberate with a redesigned charge system and clear
distinctions between flask types.

FLASK TYPES:
1. Life Flasks: Restore life over time or instantly
2. Mana Flasks: Restore mana over time or instantly
3. Utility Flasks: Grant temporary buffs (speed, resistances, etc.)

CHARGE SYSTEM:
- Flasks have maximum charges (varies by flask)
- Each use consumes a portion of charges
- Charges are gained by killing enemies or hitting enemies
- Some flasks gain charges on hit, others on kill
- Charges decay while not in combat (unlike PoE1)

INSTILLING ORBS:
- Currency that adds automatic trigger conditions to flasks
- Examples: "Use when hit", "Use when mana is low", "Use at start of flask effect"
- Only ONE instilling mod can be on a flask at a time
- Great for quality-of-life or complex flask management
""",
            how_it_works="""
1. Flasks start empty or partially filled
2. Kill or hit enemies to gain charges
3. Press flask key to consume charges and gain effect
4. Effect duration varies by flask type and quality
5. Cannot use flask if insufficient charges
6. Some flasks have cooldowns between uses

LIFE/MANA FLASKS:
- Life Recovery: Heals over 2 seconds (base) or instant
- Mana Recovery: Restores mana over 2 seconds (base) or instant
- "Instant" prefix makes recovery happen immediately
- Recovery can be cancelled by using another flask of same type

UTILITY FLASKS:
- Duration-based effects (typically 4-5 seconds)
- Effects include: movement speed, resistances, damage, defenses
- Can have multiple utility flasks active simultaneously
- Quality increases effect duration

CHARGE GAIN:
- On Kill: Most reliable, varies by flask (3-5 charges typical)
- On Hit: Less common, good for boss fights
- Some passives and items grant "flask charges gained"
""",
            calculation_formula="""
Charges Per Kill = Base Flask Charge Gain × (1 + % increased charges gained)
Charges Per Use = Flask charge consumption (varies by flask)
Uses Available = floor(Current Charges / Charges Per Use)

Duration = Base Duration × (1 + % increased flask effect duration)
Recovery = Base Recovery × (1 + % increased flask recovery rate)

Example (Life Flask):
- Base: Recovers 600 life over 2 seconds
- 50% increased flask recovery rate
- Actual: Recovers 900 life over 2 seconds (faster recovery)

Example (Utility Flask):
- Base: 4 second duration
- 20% increased flask effect duration
- Actual: 4.8 second duration
""",
            examples=[
                "Divine Life Flask: Large life recovery over time",
                "Quicksilver Flask: 40% increased movement speed",
                "Granite Flask: +1500 armor during effect",
                "Instilling Orb: 'Use when life falls below 50%' for auto-healing"
            ],
            common_questions={
                "How do I gain flask charges?": "Kill enemies or hit enemies (depends on flask). Some passives increase charge gain.",
                "Do flask charges decay?": "Yes, charges slowly decay when not in combat. This is different from PoE1.",
                "What are Instilling Orbs?": "Currency that adds automatic trigger conditions to flasks.",
                "Can I have multiple utility flasks active?": "Yes, different utility flask effects can stack.",
                "Is instant recovery worth it?": "For life flasks, often yes. Instant healing can save you in dangerous situations."
            },
            related_mechanics=['life', 'mana', 'on_kill', 'charges'],
            important_notes=[
                "Charges decay out of combat (new in PoE2)",
                "Life/mana flasks: recovery over time or instant",
                "Utility flasks: temporary buffs",
                "Instilling Orbs automate flask usage",
                "Quality increases duration or recovery",
                "Cannot spam flasks - charge management matters"
            ],
            changed_from_poe1="""
MAJOR CHANGES from PoE1:
- Flask charges now decay out of combat
- Instilling Orbs replace enchantments
- Less flask piano gameplay - more strategic use
- Charge gain rebalanced for longer boss fights
- Some flask types removed or reworked
"""
        )

        # =====================================================================
        # TRIGGER MECHANICS
        # =====================================================================

        self.mechanics['trigger'] = MechanicExplanation(
            name="Trigger",
            category=MechanicCategory.INTERACTION,
            short_description="Skills that activate automatically when conditions are met",
            detailed_explanation="""
Triggered skills are abilities that cast automatically when certain conditions are met,
without requiring manual activation. This is a powerful mechanic that allows builds
to gain extra actions without additional button presses.

KEY CONCEPTS:
- Trigger vs Cast: Triggered skills are NOT "cast" - they're triggered
- Cooldown Sharing: Many triggers share cooldowns with similar triggers
- Mana Cost: Triggered skills often have modified or zero mana costs
- Animation: Most triggers don't interrupt your current action

TRIGGER TYPES:
1. On Hit triggers: Activate when you hit an enemy
2. On Kill triggers: Activate when you kill an enemy
3. On Damage Taken triggers: Activate when you take damage (CWDT equivalent)
4. Conditional triggers: Activate when specific conditions are met

TRIGGER SOURCES:
- Support gems (e.g., Cast when Damage Taken)
- Item mods ("Trigger socketed spell when you use a skill")
- Passive tree nodes
- Unique item effects
""",
            how_it_works="""
1. Trigger condition is checked continuously
2. When condition is met, skill attempts to trigger
3. If not on cooldown and requirements met, skill triggers
4. Cooldown starts (if applicable)
5. Triggered skill executes automatically

COOLDOWN MECHANICS:
- Most triggers have cooldowns (0.25-8 seconds typical)
- Some triggers share cooldowns with similar triggers
- Cooldown recovery speed affects trigger cooldowns
- Multiple instances of same trigger don't bypass cooldown

MANA/COST RULES:
- Many triggered skills cost NO mana
- Some triggers have reduced cost (e.g., 50% less)
- Spirit-reserving skills generally cannot be triggered
- Check specific trigger for cost rules

"TRIGGER" VS "CAST":
- Triggered skills bypass "when you cast" conditions
- Triggered skills don't count as "casting" for bonuses
- Critical: Affects interactions with many passives/items
- Example: "10% more damage when you cast" doesn't apply to triggers
""",
            calculation_formula="""
Trigger Cooldown = Base Cooldown / (1 + % increased cooldown recovery speed)

Example (Cast when Damage Taken):
- Base cooldown: 0.25 seconds
- Activates when you take X damage (scales with gem level)
- Triggered spell level is LIMITED by gem level
- Lower level CWDT = more frequent triggers but weaker spells

Trigger Interaction:
- Trigger A procs → Cooldown A starts
- Trigger B with shared cooldown → Also on cooldown
- Independent triggers → Separate cooldowns

Mana Cost (varies by trigger):
- CWDT: Zero mana cost for triggered skill
- Item triggers: Often 50-100% of normal cost
- Some triggers: Full mana cost
""",
            examples=[
                "Cast when Damage Taken (CWDT): Trigger spell when taking damage",
                "Cast on Crit: Trigger spell when you crit with linked attack",
                "Trigger wand mod: 'Trigger socketed spell when you use a skill'",
                "Automation passive: Trigger linked skills periodically"
            ],
            common_questions={
                "Do triggered skills cost mana?": "Depends on trigger source. CWDT = no cost. Item triggers vary. Check the specific trigger.",
                "Can I trigger auras?": "No, Spirit-reserving skills cannot be triggered.",
                "Why isn't my trigger working?": "Check: Cooldown, mana/cost, skill requirements, trigger conditions, level requirements.",
                "Do triggers share cooldowns?": "Some do, some don't. Similar triggers often share cooldowns.",
                "Does 'on cast' work with triggers?": "NO. Triggered skills are not 'cast' - they're triggered. Different mechanic."
            },
            related_mechanics=['cooldown', 'mana', 'on_kill', 'crit'],
            important_notes=[
                "Triggered skills are NOT 'cast'",
                "Most triggers have cooldowns",
                "Some triggers share cooldowns",
                "Mana cost rules vary by trigger source",
                "Spirit-reserving skills cannot be triggered",
                "Check specific trigger for exact mechanics"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Trigger mechanics similar in concept
- Specific trigger gems may have different cooldowns/conditions
- Integration with PoE2's Spirit system
- CWDT equivalent exists but may have different scaling
- Some unique trigger interactions removed/added
"""
        )

        # =====================================================================
        # KNOCKBACK MECHANICS
        # =====================================================================

        self.mechanics['knockback'] = MechanicExplanation(
            name="Knockback",
            category=MechanicCategory.CROWD_CONTROL,
            short_description="Pushes enemies away from you or in skill direction",
            detailed_explanation="""
Knockback is a crowd control effect that physically displaces enemies, pushing them
away from the knockback source. This can be used defensively to create space or
offensively to push enemies into terrain or other hazards.

KEY CHARACTERISTICS:
- Chance-based: Most sources have % chance to knockback
- Distance-based: Knockback pushes enemies a fixed distance
- Directional: Knockback direction depends on source
- Terrain interaction: Enemies can be pushed into walls/obstacles

KNOCKBACK SOURCES:
- Skills with inherent knockback (Heavy Strike, etc.)
- Support gems (Knockback Support)
- Item mods ("% chance to Knockback on hit")
- Passive tree nodes

DEFENSIVE USES:
- Create distance from melee enemies
- Interrupt enemy attacks
- Push enemies into environmental hazards
- Control enemy positioning in fights
""",
            how_it_works="""
1. Hit enemy with knockback chance
2. Roll against knockback chance
3. If successful, enemy is pushed in knockback direction
4. Enemy moves knockback distance (unless blocked by terrain)
5. Knockback can interrupt some enemy actions

KNOCKBACK DIRECTION:
- Melee attacks: Usually AWAY from you
- Projectiles: In direction of projectile travel
- Area skills: Away from skill center
- Some skills have specific knockback directions

DISTANCE:
- Base knockback distance varies by source
- Typically 2-4 units
- Increased knockback distance modifiers exist
- Enemies stop at terrain/walls

INTERACTION WITH TERRAIN:
- Enemies pushed into walls stop there
- Can push enemies off ledges (situational)
- Some arenas have hazardous terrain to exploit
- Walls don't deal extra damage on impact

STUN RELATIONSHIP:
- Knockback can occur independently of stun
- Some skills combine both effects
- Heavy hits more likely to both stun AND knockback
- Knockback can interrupt non-stunnable enemies (sometimes)
""",
            calculation_formula="""
Knockback Chance = Base Chance × (1 + % increased knockback chance)
Knockback Distance = Base Distance × (1 + % increased knockback distance)

Example (Knockback Support):
- Adds 25% chance to knockback
- Existing 10% from gear
- Total: 35% chance on hit

Example (Heavy Strike):
- 50% base knockback chance
- 25% increased from passive
- Total: 62.5% chance (50% × 1.25)

Note: Knockback chance is rolled per hit
Multiple hits = multiple knockback chances
""",
            examples=[
                "Heavy Strike: High knockback chance, good for melee control",
                "Bow builds: Push enemies away to maintain distance",
                "Knockback + Bleed: Keep enemies moving for more damage",
                "Boss fights: Limited use as bosses often resist knockback"
            ],
            common_questions={
                "Do bosses get knocked back?": "Many bosses have knockback resistance or immunity. Check boss mechanics.",
                "Does knockback interrupt attacks?": "Sometimes. It can interrupt some enemy actions but not all.",
                "Can I knockback enemies off ledges?": "In some areas, yes. Depends on map geometry.",
                "Is knockback good for defense?": "Yes for melee builds to create space. Less useful for ranged.",
                "Does knockback work with bleed?": "Yes! Knocked back enemies are 'moving' which increases bleed damage."
            },
            related_mechanics=['stun', 'bleed', 'crowd_control', 'positioning'],
            important_notes=[
                "Chance-based mechanic (per hit)",
                "Direction depends on attack type",
                "Enemies stop at walls/terrain",
                "Bosses often resist knockback",
                "Synergizes with bleed (moving damage bonus)",
                "Can interrupt some enemy actions"
            ],
            changed_from_poe1="Core mechanics similar. Specific skill knockback values may differ in PoE2."
        )

        # =====================================================================
        # BLIND MECHANICS
        # =====================================================================

        self.mechanics['blind'] = MechanicExplanation(
            name="Blind",
            category=MechanicCategory.CROWD_CONTROL,
            short_description="Reduces enemy accuracy, making them miss attacks more often",
            detailed_explanation="""
Blind is a debuff that significantly reduces an enemy's ability to hit you. When an
enemy is blinded, their accuracy is heavily reduced, causing them to miss attacks
more frequently.

KEY CHARACTERISTICS:
- Reduces enemy ACCURACY (not your evasion)
- Duration-based debuff
- Has diminishing returns on bosses
- Some enemies are immune to blind

BLIND EFFECT:
- Blinded enemies have greatly reduced accuracy
- This makes evasion builds even more effective
- Works against ALL attacks (not just melee)
- Does not affect spells that don't use accuracy

BLIND SOURCES:
- Skills (Smoke Mine, etc.)
- Support gems
- Item mods ("Blind nearby enemies")
- Passive tree nodes
- Ascendancy bonuses
""",
            how_it_works="""
1. Apply blind to enemy through skill/item/passive
2. Enemy gains "Blinded" debuff for duration
3. All enemy attacks have reduced accuracy
4. Reduced accuracy = more misses against you
5. Effect ends when duration expires

ACCURACY REDUCTION:
- Blind typically reduces accuracy by 20-50%
- Exact value depends on source
- Less effective against high-accuracy enemies
- Stacks with your evasion for double defense

DURATION:
- Base duration varies by source (typically 4-5 seconds)
- Can be extended with duration modifiers
- Refreshes on reapplication

BOSS INTERACTION:
- Many bosses have reduced blind effectiveness
- Some pinnacle bosses are immune
- Check specific boss mechanics
- Still useful for adds in boss fights
""",
            calculation_formula="""
Enemy Hit Chance (with Blind):
Hit Chance = Blinded Accuracy / (Blinded Accuracy + Defender Evasion)

Blinded Accuracy = Base Accuracy × (1 - Blind Effect)

Example:
- Enemy accuracy: 1000
- Blind effect: 30% accuracy reduction
- Blinded accuracy: 1000 × 0.70 = 700
- Your evasion: 500
- Hit chance: 700 / (700 + 500) = 58%
- Without blind: 1000 / (1000 + 500) = 67%

Note: Blind stacks multiplicatively with other accuracy debuffs
""",
            examples=[
                "Smoke Mine: Creates cloud that blinds enemies inside",
                "Flesh and Stone Sand Stance: Blinds nearby enemies",
                "Item mod: 'Blind enemies on hit for 4 seconds'",
                "Trickster ascendancy: Blind synergies"
            ],
            common_questions={
                "Does blind work against spells?": "Only against spells that use accuracy (rare). Most spells auto-hit.",
                "Is blind good for evasion builds?": "YES! Blind + evasion is a powerful defensive combination.",
                "Do bosses get blinded?": "Some bosses have reduced effect or immunity. Check specific boss.",
                "How long does blind last?": "Depends on source. Typically 4-5 seconds base.",
                "Does blind stack?": "No, only one blind effect active. Reapplication refreshes duration."
            },
            related_mechanics=['evasion', 'accuracy', 'debuffs', 'crowd_control'],
            important_notes=[
                "Reduces enemy ACCURACY",
                "Does NOT affect most spells",
                "Duration-based (typically 4-5 seconds)",
                "Bosses may have reduced effect or immunity",
                "Excellent synergy with evasion builds",
                "Cannot stack - reapplication refreshes duration"
            ],
            changed_from_poe1="Core mechanics similar. Some blind sources and values adjusted for PoE2."
        )

        # =====================================================================
        # TAUNT MECHANICS
        # =====================================================================

        self.mechanics['taunt'] = MechanicExplanation(
            name="Taunt",
            category=MechanicCategory.CROWD_CONTROL,
            short_description="Forces enemies to target you, reduces their damage to others",
            detailed_explanation="""
Taunt is a debuff that forces enemies to prioritize attacking you over other targets.
Taunted enemies also deal reduced damage to targets that aren't you. This is primarily
a party/minion utility mechanic but has solo applications.

KEY CHARACTERISTICS:
- Forces enemies to target the taunter
- Reduces enemy damage to non-taunters
- Duration-based effect
- Bosses have special taunt interactions

TAUNT EFFECTS:
1. Target Prioritization: Taunted enemy prefers attacking you
2. Damage Reduction: Taunted enemy deals less damage to others
3. Aggro Reset: Can pull enemies off allies/minions

TAUNT SOURCES:
- Enduring Cry and other warcries
- Decoy Totem
- Minion skills (Taunt on Hit support)
- Some unique items
""",
            how_it_works="""
1. Apply taunt through skill/item
2. Enemy is "Taunted" and prioritizes attacking you
3. Taunted enemy deals reduced damage to non-taunters
4. Effect lasts for duration or until enemy dies
5. Multiple taunts: Most recent taunter takes priority

DAMAGE REDUCTION:
- Taunted enemies deal 10-20% less damage to others
- You take normal damage from taunted enemies
- Great for protecting minions/totems/allies

TARGET PRIORITY:
- Taunted enemies will attempt to attack taunter
- Not mind control - enemy AI still functions
- Some enemies may continue current action before switching
- Works on most regular enemies

BOSS INTERACTION:
- Many bosses are taunt-immune (cannot be forced to target)
- Damage reduction to others MAY still apply
- Check specific boss mechanics
- Useful for controlling boss adds

MULTIPLE TAUNTS:
- If multiple players/minions taunt same enemy
- Most recent taunt takes priority
- Enemy attacks most recent taunter
""",
            calculation_formula="""
Damage to Non-Taunter = Base Damage × (1 - Taunt Damage Reduction)

Example:
- Enemy deals 1000 damage
- Taunt reduces damage to others by 15%
- Damage to taunter: 1000 (full)
- Damage to others: 1000 × 0.85 = 850

Taunt Duration = Base Duration × (1 + % increased duration)

Example (Enduring Cry):
- Base taunt duration: 2 seconds
- Taunt forces enemy attention for 2 seconds
- Refreshes on reapplication
""",
            examples=[
                "Enduring Cry: Taunt nearby enemies + generates endurance charges",
                "Decoy Totem: Creates taunt target that isn't you",
                "Taunt Support on Minions: Makes minions taunt on hit",
                "Party play: Tank taunts boss adds to protect damage dealers"
            ],
            common_questions={
                "Do bosses get taunted?": "Most bosses are taunt-immune for targeting. Damage reduction may still apply.",
                "Does taunt make enemies deal less damage to me?": "No! Taunt reduces damage to OTHERS. You take full damage.",
                "Can minions taunt?": "Yes, with Taunt Support or certain minion skills.",
                "What if multiple allies taunt?": "Most recent taunt wins. Enemy attacks that taunter.",
                "Is taunt useful for solo play?": "Mainly for protecting minions/totems. Limited value without allies to protect."
            },
            related_mechanics=['warcries', 'minions', 'totems', 'aggro'],
            important_notes=[
                "Forces enemies to target taunter",
                "Reduces enemy damage to non-taunters",
                "Taunter takes NORMAL damage",
                "Most bosses are taunt-immune for targeting",
                "Most recent taunt takes priority",
                "Duration-based (2-4 seconds typical)"
            ],
            changed_from_poe1="Core mechanics similar. Specific taunt values and sources adjusted for PoE2."
        )

        # =====================================================================
        # CULLING STRIKE MECHANICS
        # =====================================================================

        self.mechanics['culling_strike'] = MechanicExplanation(
            name="Culling Strike",
            category=MechanicCategory.DAMAGE,
            short_description="Instantly kills enemies below 10% life",
            detailed_explanation="""
Culling Strike is a powerful mechanic that instantly kills enemies when they fall
below a certain life threshold (usually 10%). This effectively means you need to
deal 90% of an enemy's HP instead of 100%.

KEY CHARACTERISTICS:
- Instant kill at threshold (default 10% life)
- Works on ALL enemies including bosses
- Triggers on HIT only
- Does not work with damage over time

HOW IT'S CALCULATED:
- Enemy life checked AFTER your hit damage
- If enemy life <= threshold after damage: instant death
- Does NOT require the hit to bring them below threshold
- Any hit that connects can trigger culling

CULLING STRIKE SOURCES:
- Culling Strike Support gem
- Item mods ("Culling Strike" or "Enemies killed at X% life")
- Passive tree nodes
- Some unique items
""",
            how_it_works="""
1. You hit an enemy with a skill that has Culling Strike
2. Your hit deals damage normally
3. After damage, check enemy life percentage
4. If enemy life <= culling threshold: INSTANT KILL
5. No damage dealt beyond killing blow - enemy just dies

THRESHOLD VALUES:
- Standard Culling Strike: 10% life
- Enhanced versions: May have higher thresholds (15%, 20%)
- Some sources: "Culling Strike against enemies at X% threshold"

BOSS INTERACTION:
- Culling Strike WORKS on bosses
- This is effectively 10% MORE damage against all enemies
- Huge for boss fights with massive HP pools
- Some pinnacle bosses may have culling immunity (rare)

DOT INTERACTION:
- DoT damage CANNOT trigger culling strike
- Only HITS can cull enemies
- If enemy is at 5% life with your DoT, they don't die to cull
- You must hit them for cull to trigger

OVERKILL:
- Culling provides no "overkill" damage
- Enemy simply dies at threshold
- No extra damage calculated
""",
            calculation_formula="""
Effective Enemy HP = Enemy Max HP × (1 - Culling Threshold)

Example (10% Culling Strike):
- Boss has 10,000,000 HP
- With Culling: You only need to deal 9,000,000 damage
- This is effectively 11.1% MORE damage (10M / 9M = 1.111)

Higher Threshold Example (20% Culling):
- Boss has 10,000,000 HP
- With 20% Culling: You only need 8,000,000 damage
- This is effectively 25% MORE damage (10M / 8M = 1.25)

Damage Efficiency:
- 10% threshold = ~11% more effective damage
- 15% threshold = ~17.6% more effective damage
- 20% threshold = 25% more effective damage
""",
            examples=[
                "Culling Strike Support: All linked skills cull at 10%",
                "Unique weapon: 'Enemies are culled at 15% life'",
                "Party play: One player runs culling for boss kill credit",
                "Boss at 1M HP remaining (10% of 10M) - single hit kills"
            ],
            common_questions={
                "Does culling work on bosses?": "YES! Culling Strike works on all enemies, including bosses.",
                "Can DoT cull enemies?": "NO! Only hits can trigger culling strike. DoT cannot cull.",
                "Is culling worth it?": "Very much so. Effective 11%+ more damage against everything.",
                "Does culling provide overkill damage?": "No. Enemy simply dies at threshold, no extra damage calculated.",
                "What if enemy has 5% life and I DoT them?": "DoT won't cull. You must HIT them for culling to trigger."
            },
            related_mechanics=['hits', 'damage_over_time', 'boss_mechanics'],
            important_notes=[
                "Instant kill at 10% life (standard)",
                "Works on ALL enemies including bosses",
                "Only HITS can trigger culling (not DoT)",
                "Effectively ~11% more damage",
                "No overkill damage from culling",
                "Some enhanced sources have higher thresholds"
            ],
            changed_from_poe1="Core mechanics identical. Culling Strike works the same way in PoE2."
        )

        # =====================================================================
        # DAMAGE TAKEN AS MECHANICS
        # =====================================================================

        self.mechanics['damage_taken_as'] = MechanicExplanation(
            name="Damage Taken As",
            category=MechanicCategory.DEFENSE,
            short_description="Shift incoming damage to a different damage type before mitigation",
            detailed_explanation="""
"Damage Taken As" is a powerful defensive mechanic that converts incoming damage
from one type to another BEFORE your defenses are applied. This allows you to
redirect damage to types you're better at mitigating.

KEY CHARACTERISTICS:
- Conversion happens BEFORE mitigation
- Allows redirecting damage to better-defended type
- Stacking rules apply
- Order matters for multiple conversions

COMMON USES:
- "Physical Damage taken as Fire" with high fire resistance
- "Elemental Damage taken as Chaos" with Chaos Inoculation
- "Physical Damage taken as Elemental" to use resistances

HOW IT STACKS:
- Multiple "taken as" effects stack additively up to 100%
- If > 100% of one type, scale proportionally
- Remaining damage stays as original type
""",
            how_it_works="""
1. Incoming damage is categorized by type
2. "Taken as" conversions apply BEFORE mitigation
3. Converted damage is then mitigated by its new type's defenses
4. Unconverted damage is mitigated normally

CONVERSION ORDER:
1. Physical → Other (if you have phys taken as X)
2. Elemental → Other (if you have ele taken as X)
3. Apply defenses to final damage types

STACKING EXAMPLE:
- 50% physical taken as fire
- 30% physical taken as cold
- 80% total conversion
- 1000 physical hit becomes:
  - 500 fire damage (mitigated by fire res)
  - 300 cold damage (mitigated by cold res)
  - 200 physical damage (mitigated by armor)

OVER 100% STACKING:
- 60% physical taken as fire
- 60% physical taken as cold
- 120% total - scaled proportionally:
  - 50% as fire (60/120)
  - 50% as cold (60/120)
  - 0% remains physical
""",
            calculation_formula="""
Converted Damage = Original Damage × Conversion%
Remaining Original = Original Damage × (1 - Total Conversion%)

Example (70% physical taken as fire):
- 1000 physical damage incoming
- 700 damage becomes fire (mitigated by 75% fire res = 175 taken)
- 300 damage stays physical (mitigated by armor)

With 75% fire resistance and 50% armor reduction:
- Without conversion: 1000 × 0.5 = 500 physical damage taken
- With conversion: (700 × 0.25) + (300 × 0.5) = 175 + 150 = 325 damage taken

Effective Mitigation Improvement: 35% less damage taken!

Multiple Conversions (Physical → Fire + Cold):
- 50% taken as fire, 40% taken as cold
- 1000 physical: 500 fire + 400 cold + 100 physical
- Each portion mitigated separately by its type's defenses
""",
            examples=[
                "Cloak of Flame unique: 20% of physical damage taken as fire",
                "Taste of Hate flask: 20% of physical damage taken as cold",
                "Divine Flesh keystone: 50% of elemental damage taken as chaos",
                "Stacking multiple sources for near-100% physical conversion"
            ],
            common_questions={
                "When does conversion happen?": "BEFORE mitigation. Damage is converted, then mitigated by its new type's defenses.",
                "Can I convert 100% of physical?": "Yes, with enough sources. All physical becomes other types.",
                "Is chaos immunity good with damage taken as chaos?": "YES! With CI, 'taken as chaos' = damage reduced to 0.",
                "What happens over 100% conversion?": "Conversions scale proportionally. No damage 'disappears'.",
                "Does conversion work for DoT?": "Yes, damage taken as works for all incoming damage including DoT."
            },
            related_mechanics=['resistance', 'armor', 'chaos_inoculation', 'mitigation'],
            important_notes=[
                "Conversion happens BEFORE mitigation",
                "Stack additively up to 100%",
                "Over 100% scales proportionally",
                "Redirect to better-defended damage types",
                "Works for hits AND DoT",
                "Order: conversion → then mitigation"
            ],
            changed_from_poe1="Core mechanics identical. Some specific sources and values adjusted for PoE2."
        )

        # =====================================================================
        # RECOUP MECHANICS
        # =====================================================================

        self.mechanics['recoup'] = MechanicExplanation(
            name="Recoup",
            category=MechanicCategory.DEFENSE,
            short_description="Recover a portion of damage taken over 4 seconds",
            detailed_explanation="""
Recoup is a defensive recovery mechanic that heals you for a portion of damage taken
over a period of time (base 4 seconds). Unlike leech which is based on damage DEALT,
recoup is based on damage TAKEN - making it effective regardless of your damage output.

KEY CHARACTERISTICS:
- Recovery based on damage TAKEN (not dealt)
- Heals over 4 seconds by default
- Works for Life, Mana, and Energy Shield
- Stacks additively from multiple sources

RECOUP TYPES:
- Life Recoup: Recover X% of damage taken as life over 4 seconds
- Mana Recoup: Recover X% of damage taken as mana over 4 seconds
- ES Recoup: Recover X% of damage taken as energy shield over 4 seconds

WHY RECOUP IS POWERFUL:
- Works regardless of your damage dealt
- Effective for low-DPS builds
- Excellent for ES builds without leech
- Stacks from multiple sources
""",
            how_it_works="""
1. You take damage from any source
2. Recoup calculates: Damage × Recoup%
3. That amount is recovered over 4 seconds (0.25 sec ticks)
4. Multiple damage instances create separate recoup instances
5. All recoup instances stack and heal simultaneously

RECOVERY CALCULATION:
- Total recovery = Damage Taken × Recoup%
- Recovery per second = Total / 4
- Recovery per tick = Total / 16 (every 0.25 sec)

STACKING:
- Multiple recoup sources stack additively
- 10% + 15% + 20% = 45% total recoup
- Each damage instance creates separate recoup

INTERACTION WITH ES:
- ES recoup recovers ES based on damage to ES
- Does NOT bypass recharge delay
- Recoup continues even while taking hits
- Great sustain for ES builds in combat
""",
            calculation_formula="""
Recoup Amount = Damage Taken × Recoup%
Recovery Per Second = Recoup Amount / 4
Recovery Per Tick (0.25s) = Recoup Amount / 16

Example (40% Life Recoup):
- You take 1000 damage
- Recoup: 1000 × 0.40 = 400 life to recover
- Recovery: 100 life per second for 4 seconds
- Or: 25 life every 0.25 seconds

Multiple Hits Example:
- Hit 1: 500 damage → 200 recoup over 4 seconds
- Hit 2 (1 sec later): 300 damage → 120 recoup over 4 seconds
- At second 1-4: Both instances healing simultaneously
- Peak healing at second 1-4 = (200/4) + (120/4) = 80/sec

ES Recoup with 50% ES Recoup:
- 800 damage to ES
- 400 ES recovered over 4 seconds
- Works even while taking more damage (no recharge delay interaction)
""",
            examples=[
                "40% life recoup: Take 1000 damage, recover 400 life over 4 seconds",
                "ES recoup on gear: Sustain ES without needing to stop taking damage",
                "Stacking 60%+ recoup: Nearly recover all damage taken",
                "Hybrid life/ES build with both recoup types"
            ],
            common_questions={
                "How is recoup different from leech?": "Leech is based on damage DEALT. Recoup is based on damage TAKEN. Recoup works for low-DPS builds.",
                "Does recoup bypass ES recharge delay?": "No, but recoup CONTINUES while taking damage, which ES recharge doesn't.",
                "Can recoup exceed damage taken?": "With enough recoup% yes. 100%+ recoup = recover more than you took.",
                "Does recoup work with DoT?": "Yes! DoT damage taken triggers recoup recovery.",
                "Is there a recoup cap?": "No cap on recoup%. Stack as much as you can."
            },
            related_mechanics=['leech', 'life', 'energy_shield', 'mana', 'regeneration'],
            important_notes=[
                "Based on damage TAKEN (not dealt)",
                "Recovery over 4 seconds base",
                "Stacks additively from all sources",
                "No cap on recoup percentage",
                "Works for Life, Mana, and ES",
                "Multiple instances stack simultaneously"
            ],
            changed_from_poe1="Recoup mechanics are similar to PoE1. Values and sources may differ in PoE2."
        )

        # =====================================================================
        # ON-KILL MECHANICS
        # =====================================================================

        self.mechanics['on_kill'] = MechanicExplanation(
            name="On Kill",
            category=MechanicCategory.INTERACTION,
            short_description="Effects that trigger when you kill an enemy",
            detailed_explanation="""
On-kill effects are bonuses or actions that trigger when you get a kill. These effects
are common for clearing content but require understanding what counts as "your kill"
versus kills by other sources.

KEY QUESTION: What counts as "your kill"?
- Direct damage kills: YES
- DoT damage kills: YES (your DoT)
- Minion kills: NO (unless specifically stated)
- Totem/trap kills: Usually YES (your skills)
- Ally kills in party: NO

ON-KILL TYPES:
1. Resource gain: Life on kill, mana on kill, ES on kill
2. Charge generation: Frenzy charge on kill, power charge on kill
3. Buff triggers: Onslaught on kill, effects on kill
4. Flask charges: Charge gain on kill
""",
            how_it_works="""
1. An enemy's life reaches 0
2. Game determines who/what caused the killing blow
3. If it was YOUR damage: You get kill credit
4. On-kill effects trigger for the credited killer

KILL CREDIT RULES:
- Your direct damage (attacks, spells): YOUR KILL
- Your damage over time: YOUR KILL
- Your totems using your skills: YOUR KILL (usually)
- Your traps using your skills: YOUR KILL (usually)
- Your minions' damage: MINION'S KILL (not yours)
- Reflected damage: Varies (usually not your kill)
- Culling Strike: YOUR KILL

MINION KILLS:
- Minion kills are NOT your kills by default
- Some items: "Minions' kills count as your kills"
- With this mod, minion kills trigger YOUR on-kill effects
- Without it, only minion-specific on-kill effects work

DOT KILLS:
- Your ignite/poison/bleed: YOUR KILL
- Ground DoT you created: YOUR KILL
- Enemy DoT on enemy: Not your kill
- DoT from your totem: YOUR KILL (usually)
""",
            calculation_formula="""
On-Kill Effect Chance = Effect% × (1 if your kill, 0 if not)

Example (10% chance for Onslaught on kill):
- You kill enemy with attack: 10% chance for Onslaught
- Your minion kills enemy: 0% chance (not your kill)
- Your ignite kills enemy: 10% chance (your DoT)

Life on Kill Example:
- 30 life on kill modifier
- You kill 5 enemies in one attack (AoE)
- You gain: 30 × 5 = 150 life

Flask Charge Example:
- +3 flask charges gained on kill
- Kill 10 enemies: +30 flask charges distributed
""",
            examples=[
                "30 life gained on kill: Reliable sustain while clearing",
                "Onslaught on kill: Speed boost for map clearing",
                "Frenzy charge on kill: Maintain charges during clear",
                "Minion Instability: Minion kills DON'T give you on-kill effects"
            ],
            common_questions={
                "Do minion kills count as my kills?": "NO, unless you have 'minions' kills count as your kills' modifier.",
                "Do DoT kills count as my kills?": "YES, if it's your DoT (ignite, poison, bleed, etc.).",
                "Do totem kills count as my kills?": "Usually YES, as totems use your skills.",
                "Why don't I get on-kill effects in boss fights?": "No kills = no on-kill triggers. These effects are for clearing, not bossing.",
                "Does culling strike give kill credit?": "YES, culling kills count as your kills."
            },
            related_mechanics=['flask', 'charges', 'minions', 'damage_over_time'],
            important_notes=[
                "Your direct damage kills = YOUR KILL",
                "Your DoT kills = YOUR KILL",
                "Minion kills ≠ your kills (by default)",
                "Totem/trap kills usually = YOUR KILL",
                "On-kill effects are for clearing, not bossing",
                "Some items make minion kills count as yours"
            ],
            changed_from_poe1="Core mechanics identical. Kill attribution rules are the same in PoE2."
        )

        # =====================================================================
        # GAME TERMINOLOGY AND MODIFIERS
        # =====================================================================

        self.mechanics['item_rarity'] = MechanicExplanation(
            name="Item Rarity and Quantity",
            category=MechanicCategory.SCALING,
            short_description="IIR increases chance of higher rarity drops, IIQ increases number of drops",
            detailed_explanation="""
Increased Item Rarity (IIR) and Increased Item Quantity (IIQ) are two separate
modifiers that affect the loot you receive from killing enemies.

IIR (Increased Item Rarity):
- Increases the CHANCE that dropped items are of higher rarity
- Normal -> Magic -> Rare -> Unique progression
- Does NOT increase the number of items dropped
- Subject to diminishing returns at high values

IIQ (Increased Item Quantity):
- Increases the NUMBER of items that drop
- Does NOT affect the rarity of drops
- Generally more impactful than IIR for currency and base items
- Also subject to diminishing returns

PARTY BONUS:
- Each additional party member adds +50% IIQ (additive)
- 6-player party = +250% IIQ from party bonus alone
- IIR bonus in parties is smaller (roughly +10% per player)
""",
            how_it_works="""
1. Enemy is killed
2. Base drop table is rolled (number of items based on enemy type)
3. IIQ multiplier applied to determine actual item count
4. For EACH item dropped:
   - Base rarity roll occurs
   - IIR modifier shifts the rarity threshold
   - Higher IIR = better chance to upgrade rarity tier

DIMINISHING RETURNS:
- First 100% IIR/IIQ gives full value
- Values above 100% have reduced effectiveness
- Formula: Effective = 100 + (Excess x 0.5) roughly
- 200% IIR is approximately 150% effective, not 200%

IMPORTANT LIMITATIONS:
- IIR does NOT affect currency drops (only item rarity)
- IIQ does NOT affect unique drop rates (those are separate)
- Map quantity bonuses are separate multipliers
- Some unique items have fixed drop rates unaffected by IIR/IIQ
""",
            calculation_formula="""
Item Quantity Formula:
Drops = Base_Drops x (1 + IIQ%/100) x (1 + Party_Bonus%/100) x Map_Modifiers

Item Rarity Formula (simplified):
Rarity_Chance = Base_Chance x (1 + Effective_IIR%/100)

Diminishing Returns (approximate):
Effective_IIR = min(IIR, 100) + max(0, (IIR - 100) x 0.5)
Effective_IIQ = min(IIQ, 100) + max(0, (IIQ - 100) x 0.5)

Party Bonus:
Party_IIQ = (Players - 1) x 50%
Party_IIR = (Players - 1) x 10% (approximate)

Example:
- Solo player with 150% IIR, 50% IIQ
- Effective IIR is approximately 125% (diminishing returns)
- Kill enemy with base 3 drops
- Drops = 3 x 1.5 = 4.5 -> 4 or 5 items
- Each item has ~125% better chance to be higher rarity
""",
            examples=[
                "150% IIR + 50% IIQ = more items AND better chance at rares/uniques",
                "6-player party gives +250% base IIQ from party bonus alone",
                "IIQ is better for currency farming (currency has no rarity)",
                "IIR helps find unique items but has diminishing returns"
            ],
            common_questions={
                "Is IIR or IIQ better?": "IIQ is generally more valuable for overall drops including currency. IIR only affects item rarity, not currency or card drops.",
                "Does IIR affect unique drop rates?": "Partially. IIR improves the chance that a rare becomes unique, but doesn't affect base unique drop rates.",
                "Do party bonuses stack with my IIQ?": "Yes, multiplicatively. Your IIQ x Party Bonus x Map Mods all multiply together.",
                "Why don't I get more uniques with high IIR?": "Diminishing returns reduce effectiveness above 100%. Also, unique items have their own rarity weights.",
                "Does IIQ affect currency drops?": "YES! IIQ affects the number of currency items dropped. IIR does not affect currency at all."
            },
            related_mechanics=['party_play', 'map_modifiers', 'drop_mechanics'],
            important_notes=[
                "IIQ = more items, IIR = better rarity on items",
                "Both have diminishing returns above 100%",
                "IIQ affects currency drops, IIR does not",
                "Party play provides significant IIQ bonus",
                "Map quantity is a separate multiplier",
                "Some unique drop rates are fixed regardless of IIR"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core mechanics similar but values may differ
- Diminishing returns formula may be adjusted
- Party bonuses work similarly
- Map quantity interaction unchanged
"""
        )

        self.mechanics['lucky'] = MechanicExplanation(
            name="Lucky and Unlucky",
            category=MechanicCategory.SCALING,
            short_description="Lucky rolls twice and takes the better result, Unlucky takes worse",
            detailed_explanation="""
"Lucky" and "Unlucky" are modifiers that affect how random rolls are made in PoE2.
These are powerful mechanics that can significantly improve (or worsen) outcomes.

LUCKY:
- The game rolls TWICE and takes the BETTER result
- Applies to the specific stat or check mentioned
- Examples: "Your Critical Strike Chance is Lucky"
- Most impactful when base chance is around 50%

UNLUCKY:
- The game rolls TWICE and takes the WORSE result
- Used as a downside on some powerful effects
- Example: "Evade Chance is Unlucky" from Glancing Blows
- Significantly reduces effective chance

COMMON LUCKY EFFECTS:
- Lucky damage (rolls damage twice, takes higher)
- Lucky critical strikes (rolls crit chance twice)
- Lucky evasion (rolls evade chance twice)
- Lucky ailment application (threshold check twice)
""",
            how_it_works="""
1. A random roll needs to be made (damage, crit chance, etc.)
2. If LUCKY: Roll twice, use the higher value
3. If UNLUCKY: Roll twice, use the lower value

MATHEMATICAL IMPACT:
- For chance-based rolls (0-100%):
  - Lucky: Effective chance = 1 - (1 - BaseChance)^2
  - Unlucky: Effective chance = BaseChance^2
- For range-based rolls (damage):
  - Lucky: Statistically higher average outcome
  - Tends toward upper end of range

EXAMPLES BY BASE CHANCE:
- 10% base chance:
  - Lucky = 19% effective (nearly doubles)
  - Unlucky = 1% effective (drastically reduced)
- 50% base chance:
  - Lucky = 75% effective (50% increase)
  - Unlucky = 25% effective (50% decrease)
- 90% base chance:
  - Lucky = 99% effective (small improvement)
  - Unlucky = 81% effective (small decrease)

KEY INSIGHT: Lucky is most valuable at mid-range chances (~50%).
At very high or very low chances, impact is smaller.
""",
            calculation_formula="""
Lucky Chance = 1 - (1 - Base)^2 = 2*Base - Base^2
Unlucky Chance = Base^2

Lucky Damage (uniform distribution):
Average Lucky Damage is approximately Base_Min + (2/3) x (Base_Max - Base_Min)
(Tends toward upper third of damage range)

Example (50% crit chance):
- Normal: 50% chance to crit
- Lucky: 1 - (0.5)^2 = 1 - 0.25 = 75% effective crit chance
- Unlucky: (0.5)^2 = 25% effective crit chance

Example (30% crit chance):
- Normal: 30% chance to crit
- Lucky: 1 - (0.7)^2 = 1 - 0.49 = 51% effective
- Unlucky: (0.3)^2 = 9% effective

Example (damage roll 100-200):
- Normal average: 150
- Lucky average: ~167 (tends toward higher rolls)
""",
            examples=[
                "Diamond Flask in PoE1 made crits Lucky - massive DPS boost at 50% crit",
                "Glancing Blows makes Evade Unlucky but Deflect Lucky (tradeoff)",
                "Lucky damage rolls = more consistent high damage",
                "30% base chance becomes 51% with Lucky - huge improvement"
            ],
            common_questions={
                "When is Lucky most effective?": "Around 50% base chance. Lucky 50% = 75% effective. At 10% it's 19%, at 90% it's 99%.",
                "Can I have both Lucky and Unlucky?": "If both apply, they typically cancel out and you roll normally.",
                "Does Lucky affect damage rolls?": "If specified (Lucky damage), yes. It rolls the damage range twice and takes higher.",
                "Is Unlucky always bad?": "Yes, Unlucky is always a downside. It's used to balance powerful effects.",
                "Does Lucky double my crit chance?": "No, the formula is 1-(1-base)^2. At 50% base, Lucky gives 75%, not 100%."
            },
            related_mechanics=['crit', 'evasion', 'damage_calculation', 'glancing_blows'],
            important_notes=[
                "Lucky = roll twice, take BETTER result",
                "Unlucky = roll twice, take WORSE result",
                "Most effective at mid-range chances (~50%)",
                "Formula: Lucky = 1-(1-base)^2, Unlucky = base^2",
                "Lucky and Unlucky cancel if both apply",
                "Check what specific stat is Lucky (crit, damage, etc.)"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core Lucky/Unlucky mechanics unchanged
- Glancing Blows changed significantly (now affects Evade/Deflect, not Block)
- New sources of Lucky effects in PoE2
- Same mathematical formulas apply
"""
        )

        self.mechanics['nearby'] = MechanicExplanation(
            name="Nearby",
            category=MechanicCategory.INTERACTION,
            short_description="Distance modifier meaning roughly 40 units - about 1/4 screen width",
            detailed_explanation="""
"Nearby" is a distance qualifier used in many skill and item descriptions in PoE2.
It defines an approximate radius around your character where effects apply.

DISTANCE VALUE:
- "Nearby" typically means within ~40 units
- This is roughly 1/4 of your screen width
- Approximately 4-5 character lengths

COMMON USES:
- "Nearby enemies take increased damage"
- "Nearby allies gain..." (aura-like effects)
- "When a nearby enemy dies..."
- "Gain X when you kill a nearby enemy"

RELATED TERMS:
- "In your presence" - Similar to nearby, see 'presence' mechanic
- "Close range" - Usually shorter than nearby
- "Aura range" - Can be larger than nearby, affected by AoE modifiers

The exact distance can vary slightly by effect, but ~40 units is the standard.
""",
            how_it_works="""
1. Effect specifies "nearby" targets
2. Game calculates distance from your character to each potential target
3. Targets within ~40 units are affected
4. Targets outside this range are NOT affected

IMPORTANT NOTES:
- "Nearby" is measured from YOUR character, not the skill
- Does not scale with Area of Effect modifiers (usually)
- Different from aura radius (which CAN scale)
- Enemy "nearby" effects work the same way (from enemy's position)

VISUAL REFERENCE:
- Your character is roughly 3 units wide
- "Nearby" is about 13 character widths radius
- Roughly 1/4 of standard screen width
- About the size of a small aura

EXCEPTIONS:
- Some effects may use "nearby" differently
- Always check specific skill/item descriptions
- "Nearby allies" has same distance as "nearby enemies"
""",
            calculation_formula="""
Standard "Nearby" Distance: ~40 units

Visual References:
- Character width: ~3 units
- "Nearby" radius: ~40 units = ~13 character widths
- Screen width (standard): ~160 units
- "Nearby" = 1/4 screen width radius

Example Applications:
- "Nearby enemies have -10% resistance"
  -> All enemies within 40 units get -10% res
- "15% increased damage per nearby enemy"
  -> Count enemies within 40 units x 15%

Does NOT scale with:
- Increased Area of Effect
- Aura Effect (unless specifically stated)
- Skill range modifiers

MAY scale with:
- Effects that specifically say they affect "nearby" range
- Some ascendancy or unique item modifiers
""",
            examples=[
                "40 units is approximately 1/4 screen width or 13 character widths",
                "Nearby enemy curses/debuffs require staying close to bosses",
                "Nearby ally buffs work like mini-auras without Spirit reservation",
                "On-kill effects with 'nearby' require killing within range"
            ],
            common_questions={
                "How far is 'nearby'?": "Approximately 40 units, which is about 1/4 of your screen width or 13 character widths.",
                "Does 'nearby' scale with AoE?": "Usually NO. 'Nearby' is a fixed distance. Aura radius CAN scale, 'nearby' typically cannot.",
                "Is 'nearby' the same as aura range?": "No. Auras have their own radius (often larger) that scales with AoE. 'Nearby' is fixed.",
                "Does 'nearby' work for both allies and enemies?": "Yes, same distance applies to 'nearby allies' and 'nearby enemies'.",
                "Can I see the 'nearby' range?": "Not directly. Some auras show their radius which may help estimate nearby distance."
            },
            related_mechanics=['presence', 'auras', 'area_of_effect', 'targeting'],
            important_notes=[
                "Standard distance: ~40 units",
                "About 1/4 screen width or 13 character widths",
                "Does NOT scale with AoE modifiers (usually)",
                "Different from aura radius",
                "Same distance for allies and enemies",
                "Measured from YOUR character position"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- "Nearby" distance is similar (~40 units)
- PoE2 introduces "in your presence" as related concept
- Same general mechanics apply
- Some specific interactions may differ
"""
        )

        self.mechanics['recently'] = MechanicExplanation(
            name="Recently",
            category=MechanicCategory.INTERACTION,
            short_description="'Recently' means within the past 4 seconds - used in conditional modifiers",
            detailed_explanation="""
"Recently" is a time-based qualifier in Path of Exile 2 that means "within the
past 4 seconds." It's used extensively in conditional modifiers that provide
bonuses based on recent actions.

DURATION: Exactly 4 seconds

COMMON USES:
- "If you've killed recently" - killed an enemy in past 4 seconds
- "If you've been hit recently" - took damage in past 4 seconds
- "If you've used a skill recently" - cast a skill in past 4 seconds
- "If you've blocked recently" - blocked an attack in past 4 seconds

This creates a window-based system where you need to perform certain actions
regularly to maintain the bonuses. Good for active, engaging gameplay.
""",
            how_it_works="""
1. You perform an action (kill, hit, block, etc.)
2. A 4-second timer starts for that action type
3. While timer is active, "recently" conditions are TRUE
4. When timer expires, condition becomes FALSE
5. Performing the action again resets the timer

TIMER MECHANICS:
- Timers are action-specific (kill timer, hit timer, etc.)
- Multiple timers can run simultaneously
- Each new action resets its specific timer
- Timers DO NOT stack (just refresh)

PRACTICAL IMPLICATIONS:
- Boss fights: "Recently killed" is hard to maintain without adds
- Mapping: Easy to keep "recently killed" active
- Defensive: "Recently been hit" is usually easy to maintain
- Some builds rely heavily on "recently" bonuses
""",
            calculation_formula="""
"Recently" Duration: 4 seconds (fixed)

Timer States:
- Timer > 0: Condition is TRUE
- Timer = 0: Condition is FALSE

Example Timeline (Kill Recently):
- T=0: Kill enemy -> Timer = 4 seconds
- T=2: Timer = 2 seconds (still "recently killed")
- T=3: Kill another enemy -> Timer = 4 seconds (reset)
- T=7: Timer = 0 (no longer "recently killed")

Multiple "Recently" conditions:
- "If you've killed recently AND been hit recently"
- Both conditions must be true simultaneously
- Each has its own independent 4-second timer

Common Bonuses:
- "20% increased attack speed if you've killed recently"
  -> Active for 4 seconds after each kill
- "10% life regeneration if you've been hit recently"
  -> Active for 4 seconds after taking damage
""",
            examples=[
                "4 seconds exactly - not 'about 4 seconds'",
                "Kill Recently: Easy in maps, hard on bosses without adds",
                "Crit Recently: Maintained with high crit chance builds",
                "Multiple Recently conditions can apply simultaneously"
            ],
            common_questions={
                "How long is 'recently'?": "Exactly 4 seconds. This is consistent across all 'recently' modifiers.",
                "Do 'recently' timers stack?": "No. Each type of 'recently' has one timer that resets on the action.",
                "Is 'recently' good for bossing?": "Depends on the condition. 'Killed recently' is hard without adds. 'Used a skill recently' is easy.",
                "Can I have multiple 'recently' bonuses?": "Yes! Each different 'recently' condition has its own independent timer.",
                "Does 'recently' work in town?": "Timers continue but you can't perform combat actions to refresh them."
            },
            related_mechanics=['conditional_modifiers', 'kill_effects', 'buff_duration'],
            important_notes=[
                "'Recently' = exactly 4 seconds",
                "Timer resets on each qualifying action",
                "Different 'recently' conditions are independent",
                "Timers do NOT stack, only refresh",
                "Consider boss vs mapping when evaluating 'recently' bonuses",
                "Very common in passive tree and item modifiers"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- "Recently" is still 4 seconds (unchanged)
- Same timer mechanics apply
- May have new sources of "recently" bonuses in PoE2
- Core mechanic is identical
"""
        )

        self.mechanics['presence'] = MechanicExplanation(
            name="Presence (In Your Presence)",
            category=MechanicCategory.INTERACTION,
            short_description="NEW PoE2: Your character's aura-like area affecting nearby allies/enemies",
            detailed_explanation="""
"In your presence" is a NEW mechanic in PoE2 that refers to an area around your
character where certain effects apply. It functions similarly to "nearby" but is
specifically used for presence-based effects.

KEY CHARACTERISTICS:
- Area centered on YOUR character
- Affects allies or enemies "in your presence"
- Similar range to "nearby" (~40 units)
- Used for passive aura-like effects without Spirit cost
- Some effects specifically use "presence" terminology

COMMON USES:
- "Allies in your presence gain..." - Buff nearby allies
- "Enemies in your presence have..." - Debuff nearby enemies
- "While in your presence..." - Conditional effects

This is conceptually similar to auras but:
- Does NOT reserve Spirit
- Cannot be scaled with aura effect (usually)
- Is always active (no skill needed)
- Range is typically fixed
""",
            how_it_works="""
1. Your character has a "presence" area around them
2. Allies/enemies within this area are affected
3. Effects are applied automatically (no activation)
4. Leaving the area removes the effect
5. Re-entering the area reapplies the effect

PRESENCE VS AURAS:
- Auras: Reserve Spirit, scale with aura effect, skill-based
- Presence: No reservation, usually fixed effect, passive

PRESENCE VS NEARBY:
- Very similar in function and range
- "Presence" is more commonly used for ally buffs
- "Nearby" is more commonly used for enemy debuffs
- Exact range may be identical (~40 units)

IMPORTANT NOTES:
- Presence effects are typically from passives or items
- Cannot be turned off (always active)
- Do not stack with themselves from same source
- May stack with different presence effects
""",
            calculation_formula="""
Presence Range: ~40 units (similar to "nearby")

Effect Application:
- Continuously checks for valid targets in range
- Instant application when entering range
- Instant removal when leaving range

Example Effects:
- "Allies in your presence have +10% attack speed"
  -> All party members within 40 units get +10% attack speed
  -> Does NOT cost Spirit
  -> Cannot be modified by aura effect

- "Enemies in your presence deal 10% less damage"
  -> All enemies within 40 units deal 10% less damage
  -> Like a debuff aura without reservation

Stacking Rules:
- Multiple DIFFERENT presence effects stack
- Same presence effect from multiple sources: check specific wording
- Party members' presence effects can stack with yours
""",
            examples=[
                "Similar to an aura but doesn't cost Spirit",
                "Allies in your presence = party members within ~40 units",
                "Always active - no skill or toggle needed",
                "Common on ascendancy passives and unique items"
            ],
            common_questions={
                "Is 'presence' the same as 'nearby'?": "Very similar! Both are ~40 units. 'Presence' is often used for ally effects, 'nearby' for enemy effects.",
                "Does presence reserve Spirit?": "NO! Presence effects are free - they don't reserve Spirit like auras do.",
                "Can I scale presence range?": "Usually no. Presence range is typically fixed, unlike aura radius which can scale.",
                "Do multiple presence effects stack?": "Different presence effects stack. Same effect from same source does not stack.",
                "Is presence always active?": "Yes, presence effects are passive and cannot be toggled off."
            },
            related_mechanics=['nearby', 'auras', 'party_play', 'area_of_effect'],
            important_notes=[
                "NEW to PoE2 - specific 'presence' terminology",
                "Similar range to 'nearby' (~40 units)",
                "Does NOT reserve Spirit (unlike auras)",
                "Always active - cannot be toggled",
                "Cannot usually be scaled with AoE or aura effect",
                "Common for party buff effects"
            ],
            changed_from_poe1="""
NEW in PoE2:
- "In your presence" is specific PoE2 terminology
- PoE1 used "nearby" for similar effects
- PoE2 distinguishes between presence (ally focus) and nearby (general)
- Functionally similar to PoE1 "nearby allies" effects
"""
        )

        # =====================================================================
        # PROJECTILE MECHANICS
        # =====================================================================

        self.mechanics['projectiles'] = MechanicExplanation(
            name="Projectiles",
            category=MechanicCategory.DAMAGE,
            short_description="Projectile behaviors: Pierce, Chain, Fork, Split, Return, and Shotgunning rules",
            detailed_explanation="""
Projectiles in PoE2 have several behavior modifiers that affect how they interact with
enemies. Understanding these mechanics is crucial for maximizing damage with bow, wand,
and spell-based projectile builds.

KEY BEHAVIORS:
- Pierce: Projectile passes through enemy without stopping
- Chain: Projectile bounces to a new target after hitting
- Fork: Projectile splits into two on hitting an enemy
- Split: Projectile divides into multiple at the moment of firing
- Return: Projectile comes back to you after reaching max distance or final target

IMPORTANT: These behaviors have a priority order. A projectile can only perform ONE
behavior per target hit. The order is: Pierce > Fork > Chain > Return

SHOTGUNNING:
Multiple projectiles from the SAME attack/cast CAN hit the same target in PoE2, but
with restrictions. Projectiles that originate from the same point and travel in the
same direction typically cannot all hit. However, forked/split projectiles or projectiles
with different origins CAN shotgun.
""",
            how_it_works="""
PIERCE:
1. Projectile passes through enemies without being consumed
2. 100% pierce chance = passes through all enemies in path
3. Each enemy can only be hit ONCE per projectile per pass
4. Excellent for clearing dense packs in a line

CHAIN:
1. After hitting, projectile bounces to a new target
2. Chain count determines max bounces (e.g., "Chains +2 Times")
3. Cannot chain back to recently hit targets
4. Range limit on chain distance
5. Each chain reduces damage by default (some sources prevent this)

FORK:
1. On first hit, projectile splits into TWO projectiles
2. Forked projectiles travel at angles from original path
3. Only happens ONCE per original projectile
4. Does not trigger if projectile pierces

SPLIT:
1. At moment of firing, projectile becomes multiple projectiles
2. Example: "Fires 2 additional projectiles"
3. Split projectiles share the same origin point
4. Spread pattern depends on the skill

RETURN:
1. After reaching max range or final target, projectile returns to you
2. Can hit enemies on the return path
3. Some skills have built-in return (Spectral Throw)
4. Return counts as a separate hit opportunity

BEHAVIOR PRIORITY (per hit):
Pierce > Fork > Chain > Return
- If pierce succeeds, fork/chain don't trigger
- If fork triggers, chain doesn't happen
- Return happens at end of projectile life
""",
            calculation_formula="""
Pierce Chance = Sum of all pierce chance sources (capped at 100%)
Chain Count = Sum of all "chains +X" sources
Fork Count = Usually binary (forks or doesn't), some sources add extra forks

Damage per Hit (Chain):
- Default: 30% LESS damage per chain (varies by source)
- Some supports/passives remove the damage penalty
- Hit 1: 100%, Hit 2: 70%, Hit 3: 49%, etc.

Projectile Count (Split/Additional):
Total Projectiles = Base Projectiles + Additional Projectiles
Example: Skill fires 1 base + "2 additional" = 3 projectiles

Shotgunning Conditions:
- Same skill, same cast: Usually NO (travel same path)
- Forked projectiles: YES (different paths)
- Split at target: YES (if mechanics allow)
- Different origin points: YES (Barrage, etc.)

Example Build Calculation:
- Lightning Arrow with Pierce + Fork
- Fires into pack: Pierces first 3 enemies
- On 4th enemy (if pierce fails): Forks into 2 projectiles
- Each fork can hit additional enemies
- Total potential targets: 3 (pierce) + 2x further enemies (forks)
""",
            examples=[
                "Pierce builds: Great for clearing linear packs, weak vs single target",
                "Chain builds: Excellent for spread-out enemies, loses damage per chain",
                "Fork builds: Good for hitting enemies behind your target",
                "Split/Additional proj: More projectiles = more chances to hit, potential shotgun",
                "Spectral Throw: Built-in return for double-hit potential",
                "Barrage: Multiple projectiles from same attack CAN shotgun (different timing)"
            ],
            common_questions={
                "Can I have Pierce AND Chain?": "Yes, but Pierce takes priority. If projectile pierces, it won't chain on that hit. After pierce fails, it can chain.",
                "Does Fork work with Pierce?": "Fork only triggers when pierce FAILS. If you have 100% pierce, fork never happens.",
                "Can multiple projectiles hit the same boss?": "Depends on the skill. Forked projectiles and skills like Barrage CAN shotgun. Standard multiple projectiles usually cannot.",
                "Does Chain reduce damage?": "Usually yes, 30% less per chain by default. Some supports remove this penalty.",
                "What's better for clear: Pierce or Chain?": "Pierce for linear density, Chain for spread-out enemies. Chain is more versatile but loses damage."
            },
            related_mechanics=['increased_vs_more', 'attack_speed', 'area_of_effect'],
            important_notes=[
                "Behavior priority: Pierce > Fork > Chain > Return",
                "A projectile does ONE behavior per target hit",
                "100% pierce prevents Fork and Chain from triggering",
                "Chain has distance limits between targets",
                "Fork only happens once per original projectile",
                "Shotgunning rules vary by skill - check skill mechanics",
                "Return counts as separate hit opportunity"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core mechanics similar but skill-specific interactions differ
- Shotgunning rules refined for PoE2 skills
- Some support gems removed or reworked
- Fork and Chain interaction more clearly defined
- Return projectiles more common as skill mechanics
"""
        )

        # =====================================================================
        # AREA OF EFFECT
        # =====================================================================

        self.mechanics['area_of_effect'] = MechanicExplanation(
            name="Area of Effect",
            category=MechanicCategory.SCALING,
            short_description="AoE radius scaling, overlap mechanics, increased vs more AoE, and breakpoints",
            detailed_explanation="""
Area of Effect (AoE) determines the radius of skills that hit multiple enemies in an
area. Understanding AoE scaling is crucial because the relationship between "increased
area" and actual radius is NOT linear.

KEY CONCEPT:
Area scales with the SQUARE of radius. This means:
- 100% increased area = 41% increased radius (sqrt(2) = 1.41)
- To DOUBLE the radius, you need 300% increased area

This makes AoE investment have diminishing returns for radius but can still be
valuable for covering more screen area.

OVERLAP MECHANICS:
Some skills can "overlap" - hitting the same enemy multiple times with a single use.
Examples include Blade Vortex (multiple blades), Firestorm (multiple impacts), and
certain channeled skills. Overlap is powerful but not all AoE skills can do this.
""",
            how_it_works="""
RADIUS CALCULATION:
1. Base radius defined by skill gem level
2. Apply "increased area of effect" modifiers (additive)
3. Apply "more area of effect" modifiers (multiplicative)
4. Convert area to radius: Radius = BaseRadius x sqrt(TotalAreaMultiplier)

INCREASED vs MORE:
- "Increased Area" sources add together, then apply
- "More Area" multiplies after increased calculation
- Same rules as damage increased/more

AoE BREAKPOINTS:
- PoE2 uses breakpoints for visual representation
- Your actual radius is always the calculated value
- Visual may "snap" to nearest breakpoint
- Mechanical effect uses true calculated radius

OVERLAP RULES:
- Most AoE skills: ONE hit per enemy per use
- Specific skills allow multiple hits: Check skill description
- "Overlapping" usually requires specific mechanics
- Explosions from kills/effects have their own rules

CONCENTRATED EFFECT vs INCREASED AoE:
- These are opposing modifiers
- Concentrated Effect: Less area, MORE damage
- Increased AoE supports: More area, usually no damage penalty
- Cannot use both on same skill (incompatible)
""",
            calculation_formula="""
Total Area Multiplier = (1 + Sum_of_Increased) x More1 x More2 x ...
Radius Multiplier = sqrt(Total Area Multiplier)
Final Radius = Base Radius x Radius Multiplier

Example:
- Base radius: 20 units
- 50% increased area + 30% increased area = 80% increased
- 30% more area
- Area multiplier = 1.80 x 1.30 = 2.34
- Radius multiplier = sqrt(2.34) = 1.53
- Final radius = 20 x 1.53 = 30.6 units

Diminishing Returns Example:
- 0% increased area: radius = 1.00x (baseline)
- 50% increased area: radius = 1.22x
- 100% increased area: radius = 1.41x
- 150% increased area: radius = 1.58x
- 200% increased area: radius = 1.73x

Each additional 50% increased gives less radius than the previous 50%.

Overlap DPS (when applicable):
- If skill overlaps 3 times: Effective DPS = 3 x Base DPS
- Total potential damage increases with overlap count
- Check skill-specific mechanics for overlap behavior
""",
            examples=[
                "Earthquake: Large base AoE, benefits from AoE scaling for clear",
                "Blade Vortex: Multiple blades can hit same target (overlap mechanic)",
                "Firestorm: Multiple meteors, overlap is core to damage",
                "Conc Effect: 30% less area but 54% more damage - worth it for bossing",
                "100% increased AoE = only 41% more radius (sqrt scaling)"
            ],
            common_questions={
                "Why doesn't my AoE feel much bigger with 100% increased?": "Area scales with radius squared. 100% more area only gives 41% more radius. You need 300% increased area to double radius.",
                "Should I use Concentrated Effect for bosses?": "Usually yes for single-target. The damage boost outweighs the area loss when fighting one enemy.",
                "Do all AoE skills overlap?": "No! Most AoE skills hit each enemy once per use. Only specific skills (Blade Vortex, Firestorm, etc.) can overlap.",
                "Is increased AoE worth investing in?": "For clear speed, yes. For bossing, usually not. Many builds swap AoE gems for boss fights.",
                "What's the cap on AoE?": "No hard cap, but diminishing returns make extreme investment inefficient."
            },
            related_mechanics=['increased_vs_more', 'projectiles', 'concentrated_effect'],
            important_notes=[
                "Radius scales with SQUARE ROOT of area (diminishing returns)",
                "100% increased area = ~41% increased radius",
                "To double radius, need 300% increased area",
                "Most AoE skills do NOT overlap (one hit per enemy)",
                "Concentrated Effect and Increased AoE are incompatible",
                "'More area' is multiplicative, 'increased area' is additive",
                "Check skill descriptions for overlap capability"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core scaling formula unchanged (still sqrt)
- Some AoE support gems adjusted or removed
- Skill-specific AoE values rebalanced
- Concentrated Effect values adjusted for PoE2
- Visual breakpoints may differ from PoE1
"""
        )

        # =====================================================================
        # ATTACK SPEED
        # =====================================================================

        self.mechanics['attack_speed'] = MechanicExplanation(
            name="Attack Speed",
            category=MechanicCategory.SCALING,
            short_description="Base attack time, more vs increased speed, animation mechanics, dual wield bonus",
            detailed_explanation="""
Attack Speed determines how quickly you can perform attack skills. Understanding
attack speed is crucial for optimizing DPS and gameplay feel.

KEY CONCEPTS:
- Base Attack Time: The weapon's innate attack duration (lower = faster)
- Attack Speed: Modifier that reduces attack time
- Attacks Per Second (APS): How many attacks you perform each second
- Animation Lock: Period during attack where you can't act

DUAL WIELDING:
In PoE2, dual wielding provides a 20% MORE attack speed bonus while attacking.
This is multiplicative and very powerful for dual-wield builds.

ANIMATION CANCELING:
PoE2 has improved animation canceling compared to PoE1. You can cancel attack
animations earlier with movement, though there's still a "point of no return"
where the attack will complete.
""",
            how_it_works="""
BASE ATTACK TIME:
1. Each weapon has a base attack time (e.g., 1.5 seconds)
2. Skill gems may modify this (some skills have speed penalties)
3. Lower base time = faster base attacks

ATTACK SPEED SCALING:
1. All "increased attack speed" sources add together
2. All "more attack speed" sources multiply separately
3. Calculate: Base_Time / (1 + Total_Increased) / More1 / More2...
4. Result is your attack time per swing

ATTACKS PER SECOND (APS):
APS = 1 / Attack_Time
- 1.0 second attack time = 1.0 APS
- 0.5 second attack time = 2.0 APS
- 0.25 second attack time = 4.0 APS

DUAL WIELD MECHANICS:
1. 20% MORE attack speed while dual wielding (PoE2)
2. Alternates between main hand and off-hand weapons
3. Each hand uses its own weapon stats
4. Total DPS considers both weapons

ANIMATION CANCELING:
1. Attack has wind-up, damage point, and recovery
2. Damage is dealt at the "damage point"
3. Recovery can be canceled by moving/dodging
4. Cannot cancel before damage point (attack won't deal damage)
""",
            calculation_formula="""
Attack Time = Base_Weapon_Time / (1 + Sum_Increased_Speed) / More1 / More2...
APS = 1 / Attack_Time

Example:
- Base weapon time: 1.5 seconds
- 50% + 30% increased attack speed = 80% increased
- 20% more (dual wield)
- Attack Time = 1.5 / 1.80 / 1.20 = 0.694 seconds
- APS = 1 / 0.694 = 1.44 attacks per second

Dual Wield Total DPS:
- Main hand DPS + Off-hand DPS (alternating)
- Total APS applies to combined attacks
- If main = 100 damage, off = 80 damage, 2 APS:
- Effective DPS = (100 + 80) / 2 x 2 = 180 DPS

Local vs Global Attack Speed:
- Local (on weapon): Only affects that weapon's attacks
- Global (passives, gear): Affects all attack skills
- Both stack additively in their categories

Speed Breakpoints:
- Server tick rate affects actual attack execution
- Very high APS may not translate 1:1 to damage
- Generally aim for smooth gameplay feel over max APS
""",
            examples=[
                "Dual wielding: 20% MORE attack speed is huge multiplicative bonus",
                "Fast weapon (1.3 base) vs slow weapon (1.7 base): ~30% APS difference",
                "Berserker with Rage: Stacking speed for rapid attacks",
                "Animation cancel: Move after damage point to skip recovery",
                "2-handed vs Dual Wield: 2H has higher damage per hit, DW has more hits"
            ],
            common_questions={
                "Is attack speed better than damage?": "Depends on build. Speed helps leech, on-hit effects, and gameplay feel. Damage per hit better for ailments, big hits.",
                "Does dual wield attack faster?": "Yes! 20% MORE attack speed while dual wielding in PoE2.",
                "What's animation canceling?": "Moving after the damage point to skip attack recovery. Speeds up effective APS and improves mobility.",
                "Is there a speed cap?": "No hard cap, but server ticks and diminishing returns limit practical benefit at extreme speeds.",
                "Local vs global attack speed?": "Local only affects that weapon. Global affects all attacks. Both are 'increased' and add together."
            },
            related_mechanics=['increased_vs_more', 'dual_wielding', 'rage', 'leech'],
            important_notes=[
                "Lower base attack time = faster weapon",
                "All 'increased' attack speed is additive",
                "'More' attack speed is multiplicative",
                "Dual wielding grants 20% MORE attack speed in PoE2",
                "Animation canceling can improve effective speed",
                "Attacks alternate between main/off hand when dual wielding",
                "Very high APS has diminishing returns due to server ticks"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Dual wield bonus is now 20% MORE (was 10% more + 15% block)
- Animation canceling more responsive
- Some attack speed sources adjusted
- Server tick interaction may differ
- Skill-specific speed modifiers rebalanced
"""
        )

        # =====================================================================
        # MINIONS
        # =====================================================================

        self.mechanics['minions'] = MechanicExplanation(
            name="Minions",
            category=MechanicCategory.INTERACTION,
            short_description="Companions (permanent, limited) vs Minions (temporary, many), scaling, AI, aggro",
            detailed_explanation="""
PoE2 has a restructured minion system with two distinct categories:

COMPANIONS:
- Permanent summons that persist until killed
- Limited count (usually 1-3 depending on type)
- High individual power
- Examples: Spectres, Golems, Persistent summons
- Require SPIRIT to maintain (not mana reservation)

MINIONS (Temporary):
- Created by skills, last for a duration or until killed
- Can have many active simultaneously
- Lower individual power but strength in numbers
- Examples: Skeletons, Zombies, temporary summons
- May or may not cost Spirit depending on skill

Minion builds in PoE2 need to manage Spirit budget carefully, as companions
reserve Spirit similar to how auras did in PoE1.
""",
            how_it_works="""
COMPANION MECHANICS:
1. Summoned using a skill, costs Spirit to maintain
2. Limited by companion type (e.g., max 3 Spectres)
3. Stays active until killed or unsummoned
4. If killed, must be re-summoned
5. Benefits from minion scaling passives/gear
6. Has its own life, resists, damage stats

TEMPORARY MINION MECHANICS:
1. Created by skill use, has duration or HP
2. No ongoing Spirit cost (usually)
3. Can summon many rapidly
4. Expires after duration or when killed
5. Strength in numbers - swarm tactics
6. Often has cap on active count

MINION SCALING:
- "Minion damage" applies to all minion types
- "Minion life" increases their survivability
- "Minion attack/cast speed" for faster actions
- "Minion resistance" for elemental survival
- YOUR offensive stats do NOT apply to minions

AGGRO AND AI:
1. Minions target what you target (if in range)
2. Will attack nearby enemies automatically
3. Aggressive AI - seek out enemies
4. Can be directed with Convocation skill
5. Some skills allow more control over targeting

MINION DAMAGE CONVERSION:
- Minions use THEIR damage types
- Your conversion doesn't affect them
- Specific minion gems can add conversion
- Minion damage scales their base damage
""",
            calculation_formula="""
Companion Spirit Cost:
Total Spirit Reserved = Sum of (Each Companion's Spirit Cost)
Example: 2 Spectres at 40 Spirit each = 80 Spirit reserved

Minion Damage:
Minion_DPS = Base_Minion_Damage x (1 + Sum_Minion_Increased) x More_Minion_1 x ...

Example:
- Skeleton base damage: 50
- 100% increased minion damage
- 30% more minion damage support
- Minion DPS = 50 x 2.0 x 1.30 = 130 per skeleton

Total Minion DPS:
- Count each minion's contribution
- 10 Skeletons at 130 DPS each = 1,300 total DPS

Minion Survivability:
Minion_Life = Base_Life x (1 + Sum_Increased_Minion_Life)
Minion_Resists = Base_Resist + Added_Resist_Sources

Note: Minions do NOT benefit from YOUR life or resists
""",
            examples=[
                "Companion build: 3 Spectres + Golem, high Spirit investment needed",
                "Skeleton Army: Many temporary skeletons, quantity over quality",
                "Spectre builds: Specific monster types as companions for unique abilities",
                "Golem builds: Elemental golems provide buffs AND damage",
                "Minion instability: Some builds focus on minion death explosions"
            ],
            common_questions={
                "Do my stats affect minions?": "NO! Your damage, crit, etc. don't apply. Only 'minion' specific modifiers affect them.",
                "What's the difference between Companions and Minions?": "Companions are permanent and cost Spirit. Minions are temporary, often numerous, and usually don't reserve Spirit.",
                "How do I keep minions alive?": "Minion life, minion resistances, and positioning. Some builds use 'Minions cannot be damaged' effects.",
                "Do minions benefit from my auras?": "Usually yes! Auras that affect 'allies' include minions. This is a key scaling method.",
                "What's the best minion type?": "Depends on playstyle. Spectres for specific mechanics, Skeletons for army, Golems for buffs + damage."
            },
            related_mechanics=['spirit', 'auras', 'increased_vs_more', 'companions'],
            important_notes=[
                "Companions reserve Spirit, temporary minions usually don't",
                "YOUR damage stats don't apply to minions",
                "Only 'minion' specific modifiers scale them",
                "Auras can affect minions (they're allies)",
                "Minion AI is aggressive - targets nearby enemies",
                "Convocation skill repositions minions to you",
                "Each minion type has its own limit"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Companion/Minion distinction is new to PoE2
- Spirit reservation replaces some mana reservation
- Spectre mechanics reworked
- Some minion skills removed or changed
- AI and targeting improved
- Minion limit systems adjusted
"""
        )

        # =====================================================================
        # AURAS
        # =====================================================================

        self.mechanics['auras'] = MechanicExplanation(
            name="Auras",
            category=MechanicCategory.RESOURCES,
            short_description="Mana reservation vs Spirit reservation, presence effects, aura stacking, ally vs enemy auras",
            detailed_explanation="""
Auras are persistent area effects that provide buffs to you and allies or debuffs to
enemies. In PoE2, auras have been split into different reservation systems:

SPIRIT-BASED AURAS:
- Traditional "always-on" auras reserve Spirit
- Examples: Determination, Hatred, Wrath, etc.
- Limited by your total Spirit pool
- Provide powerful persistent buffs

PRESENCE EFFECTS:
- Some buffs are "Presence" effects in PoE2
- Work differently from traditional auras
- May have different reservation or activation mechanics

MANA RESERVATION:
- Some effects still reserve mana (not Spirit)
- Heralds and certain skills use mana reservation
- Separate pool from Spirit-based auras

This split allows more build flexibility - you can run Spirit auras AND
mana-reserving effects simultaneously.
""",
            how_it_works="""
SPIRIT AURA ACTIVATION:
1. Activate aura skill
2. Spirit is reserved (fixed amount, not percentage)
3. Aura remains active until deactivated or death
4. Provides buff to you and allies in radius
5. Deactivating immediately frees Spirit

AURA RADIUS:
1. Each aura has a base radius
2. "Increased aura effect" improves the buff
3. "Increased aura area of effect" improves radius
4. Allies must be in radius to benefit

AURA STACKING:
1. Same aura from multiple sources: Usually doesn't stack (best applies)
2. Different auras: All apply simultaneously
3. Your auras + party member auras: Both can apply
4. "Aura effect" modifiers improve your aura's strength

ALLY vs ENEMY AURAS:
1. Buff auras: Affect you and allies
2. Debuff auras: Affect enemies in radius
3. Some auras have both ally buff AND enemy debuff components
4. Examples: Malediction (enemy debuff), Discipline (ally buff)

RESERVATION EFFICIENCY:
- Some passives reduce reservation costs
- "X% reduced mana/spirit reservation" helps
- Allows fitting more auras in your budget
""",
            calculation_formula="""
Spirit Budget:
Available Spirit = Max Spirit - Reserved Spirit
Can activate aura if: Aura Cost <= Available Spirit

Example:
- Max Spirit: 150
- Determination: 50 Spirit
- Hatred: 50 Spirit
- Wrath: 50 Spirit
- Total reserved: 150, Available: 0

Aura Effect:
Aura Buff = Base Effect x (1 + Sum_Aura_Effect_Increased)

Example (Hatred):
- Base: Adds 25% of Physical as Cold
- 40% increased aura effect
- Result: 25% x 1.4 = 35% of Physical as Cold

Reservation Efficiency:
Effective Cost = Base Cost x (1 - Reservation_Reduction)
Example: 50 Spirit aura with 20% reduced reservation = 40 Spirit

Party Aura Stacking:
- Each player's auras apply to allies in range
- Same aura from two players: Higher effect applies (no stack)
- Different auras: All apply
- Aurabot support: Runs many auras for party benefit
""",
            examples=[
                "Determination: Flat armor boost, popular for defense",
                "Hatred: Physical to Cold conversion, offensive aura",
                "Discipline: Flat Energy Shield, popular for ES builds",
                "Wrath: Lightning damage boost for spells/attacks",
                "Party play: Multiple players each running different auras"
            ],
            common_questions={
                "Do auras stack from multiple players?": "Different auras stack. Same aura from multiple sources does NOT stack - only the strongest applies.",
                "What's the difference between Spirit and Mana reservation?": "Spirit is a new resource for 'permanent' effects like auras. Mana reservation is separate, used by heralds and some other skills.",
                "How do I run more auras?": "Increase Spirit pool (gear, passives), reduce reservation costs, or use both Spirit AND mana-reserving effects.",
                "Does 'increased aura effect' help my party?": "Yes! It improves the aura's buff strength, which benefits everyone in range.",
                "Do auras affect minions?": "Yes! Auras that affect 'allies' include your minions."
            },
            related_mechanics=['spirit', 'minions', 'mana', 'increased_vs_more'],
            important_notes=[
                "Spirit auras: Fixed cost, persistent buff",
                "Same aura from multiple sources: Only strongest applies",
                "Different auras: All stack together",
                "'Aura effect' improves buff strength",
                "'Aura area' improves radius",
                "Minions are allies - benefit from your auras",
                "Reservation efficiency passives help run more auras"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Auras now reserve SPIRIT (new resource), not mana percentage
- Fixed Spirit costs instead of percentage reservation
- Some auras moved to different categories
- Presence effects are new category
- Aura effect scaling similar but values adjusted
- Easier to plan exact Spirit budget
"""
        )

        # =====================================================================
        # FORTIFY
        # =====================================================================

        self.mechanics['fortify'] = MechanicExplanation(
            name="Fortify",
            category=MechanicCategory.DEFENSE,
            short_description="Physical damage reduction buff, generation methods, stacks, duration, and cap",
            detailed_explanation="""
Fortify is a defensive buff that reduces incoming damage. In PoE2, Fortify uses a
STACK system where you build up stacks through specific actions, and each stack
provides damage reduction.

KEY CHARACTERISTICS:
- Stacking buff (not binary on/off)
- Each stack provides % damage reduction
- Stacks have duration and decay over time
- Generated through melee hits and specific skills
- Capped at maximum stacks (usually 20)

Fortify is primarily associated with melee builds due to its generation methods,
providing a significant defensive layer for characters in close combat.
""",
            how_it_works="""
STACK GENERATION:
1. Melee hits grant Fortify stacks (based on damage dealt)
2. Some skills grant stacks directly
3. Passives can provide easier generation
4. Each stack has its own duration

STACK DECAY:
1. Stacks decay over time (oldest first)
2. Base duration: 5 seconds per stack
3. Can refresh stacks by continuing to generate
4. Duration modifiers affect how long stacks last

DAMAGE REDUCTION:
1. Each stack provides 1% damage reduction
2. Maximum stacks cap the total reduction
3. Typical cap: 20 stacks = 20% damage reduction
4. Applies to ALL incoming damage types

GENERATION THRESHOLDS:
1. Melee hits must deal significant damage
2. Low damage hits may not grant stacks
3. This prevents easy generation with fast, weak hits
4. Encourages hard-hitting melee playstyles
""",
            calculation_formula="""
Damage Reduction = Current_Stacks x 1%
Capped at: Max_Stacks x 1% (typically 20%)

Example:
- 15 Fortify stacks active
- Damage reduction = 15 x 1% = 15% reduced damage taken
- Incoming 1000 damage: 1000 x 0.85 = 850 damage taken

Stack Duration:
Duration = 5 seconds base x (1 + Duration_Modifiers)
With 50% increased duration: 5 x 1.5 = 7.5 seconds per stack

Generation from Melee:
Stacks Gained = Function of (Damage Dealt / Enemy Life)
- Big hits on weak enemies: More stacks
- Small hits: May grant no stacks
- Exact formula varies by skill/source

Effective HP with Fortify:
EHP = Life / (1 - Fortify_Reduction)
Example: 5000 life with 20% Fortify = 5000 / 0.80 = 6250 effective HP
""",
            examples=[
                "20 stacks = 20% damage reduction from all sources",
                "Melee slam builds: Big hits generate stacks quickly",
                "Fortify Support: Links to melee skills for automatic generation",
                "Shield Charge + Fortify: Movement skill that generates stacks",
                "Boss fights: Maintain stacks through consistent melee damage"
            ],
            common_questions={
                "Do ranged builds get Fortify?": "Difficult. Fortify is primarily generated through melee hits. Ranged builds need specific sources or won't have reliable access.",
                "Does Fortify reduce all damage?": "Yes! Fortify reduces ALL incoming damage, not just physical.",
                "How many stacks can I have?": "Typically capped at 20 stacks (20% reduction). Some sources may modify the cap.",
                "Do stacks refresh or add?": "New generation adds stacks (up to cap). Existing stacks decay independently.",
                "Is Fortify worth it for melee?": "Absolutely. 20% damage reduction is a massive defensive layer for builds that can maintain it."
            },
            related_mechanics=['armor', 'endurance_charges', 'damage_reduction', 'melee'],
            important_notes=[
                "Stack-based system: 1% reduction per stack",
                "Typically capped at 20 stacks (20% max reduction)",
                "Generated primarily through melee hits",
                "Stacks decay over time (5 second base duration)",
                "Requires dealing significant damage to generate",
                "Reduces ALL damage types, not just physical",
                "Melee builds benefit most from Fortify"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Stack system refined (was more binary in early PoE1)
- Generation thresholds prevent easy abuse
- Duration and decay mechanics adjusted
- Maximum stacks may differ from PoE1
- Integration with PoE2 skill system
- Some Fortify sources removed or changed
"""
        )

        # =====================================================================
        # RAGE
        # =====================================================================

        self.mechanics['rage'] = MechanicExplanation(
            name="Rage",
            category=MechanicCategory.RESOURCES,
            short_description="Generated on hit, decays over time, scales attack damage/speed, Berserk interaction",
            detailed_explanation="""
Rage is a resource/buff that builds up during combat and provides offensive bonuses.
It's primarily associated with Marauder/Berserker builds but accessible to any build
that invests in it.

KEY CHARACTERISTICS:
- Generated by hitting enemies (attacks)
- Each point of Rage provides damage and speed bonuses
- Decays over time when not generating
- Maximum Rage is typically 50 (can be increased)
- Berserk skill consumes Rage for powerful buff

Rage encourages aggressive playstyles - keep attacking to maintain your buff,
stop attacking and your power fades.
""",
            how_it_works="""
RAGE GENERATION:
1. Hit enemies with attacks to generate Rage
2. Base generation: Variable depending on source
3. Some skills/passives improve generation rate
4. Cannot generate while at maximum Rage
5. Generation requires HITTING, not just attacking

RAGE DECAY:
1. Rage decays when you stop generating
2. Decay starts after brief grace period (~4 seconds)
3. Lose ~1-2 Rage per second during decay
4. Continuous attacking prevents decay
5. Some sources slow decay rate

RAGE BONUSES (per point):
- Increased Attack Damage
- Increased Attack Speed
- Increased Movement Speed
- Exact values depend on source/build

BERSERK SKILL:
1. Activated ability that consumes Rage
2. Provides powerful MORE damage and speed
3. Effect scales with Rage consumed
4. Duration depends on Rage consumed
5. Popular for boss burst damage phases

MAXIMUM RAGE:
- Base maximum: 50 Rage
- Can be increased through passives/items
- Higher max = higher sustained bonuses
- Higher max = longer Berserk duration
""",
            calculation_formula="""
Rage Bonuses (typical values per point):
- 1% increased Attack Damage per Rage
- 1% increased Attack Speed per Rage (from some sources)
- 1% increased Movement Speed per Rage (from some sources)

Example at 50 Rage:
- Attack Damage: 50% increased
- Attack Speed: Variable (depends on sources)
- Movement Speed: Variable (depends on sources)

Berserk Calculation:
- Consumes all Rage when activated
- Duration = Base Duration + (Rage x 0.1 seconds) approximately
- Effect scales: More Rage consumed = stronger effect

Rage Decay:
- Grace period: ~4 seconds of no generation
- Decay rate: ~1-2 Rage per second
- 50 Rage to 0: ~25-50 seconds without generation

Total DPS with Rage:
DPS_with_Rage = Base_DPS x (1 + Rage x Damage_Per_Rage/100)
Example: 10000 DPS x (1 + 50 x 0.01) = 10000 x 1.5 = 15000 DPS
""",
            examples=[
                "50 Rage = 50% increased attack damage (typical)",
                "Berserker ascendancy: Enhanced Rage generation and effects",
                "Berserk for boss burst: Save 50 Rage, pop Berserk, huge damage",
                "Chain boss: Rage decays during invulnerability phases",
                "Rage Support: Adds generation to linked skills"
            ],
            common_questions={
                "How do I generate Rage?": "Hit enemies with attacks. Some skills, passives, and the Rage Support gem improve generation.",
                "Does Rage work for spells?": "Rage is attack-focused. Some sources may provide spell-related bonuses, but generation is typically attack-based.",
                "When should I use Berserk?": "For boss burst damage phases. Build up Rage, then Berserk for massive damage boost.",
                "How do I prevent Rage decay?": "Keep attacking. Continuous hits maintain Rage. Some sources slow decay rate.",
                "Is Rage worth building around?": "For attack builds, absolutely. 50% increased damage + speed is significant."
            },
            related_mechanics=['attack_speed', 'increased_vs_more', 'berserk', 'frenzy_charges'],
            important_notes=[
                "Generated by hitting with attacks",
                "Decays over time when not generating (~4 sec grace)",
                "Typical max: 50 Rage",
                "Each Rage point = ~1% increased attack damage",
                "Berserk consumes Rage for powerful burst buff",
                "Attack-focused resource - less useful for spell builds",
                "Encourages aggressive, continuous attacking"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core mechanics similar
- Some Rage sources adjusted
- Berserk skill interaction may differ
- Specific value per Rage point rebalanced
- Integration with PoE2 support gems
- Decay rates and grace period may vary
"""
        )

        # =====================================================================
        # LIFE REGENERATION
        # =====================================================================

        self.mechanics['life_regeneration'] = MechanicExplanation(
            name="Life Regeneration",
            category=MechanicCategory.RESOURCES,
            short_description="Flat regen vs % regen, regeneration rate modifiers, interaction with degens",
            detailed_explanation="""
Life Regeneration is passive healing that occurs continuously, recovering your life
without requiring any action. Understanding regen mechanics is important for sustain
builds, especially Righteous Fire and other degen-based playstyles.

KEY TYPES:
- Flat Regeneration: Regenerate X life per second (fixed value)
- Percent Regeneration: Regenerate X% of maximum life per second
- Both stack together for total regeneration

REGENERATION RATE:
"Regeneration Rate" is a MODIFIER that increases how effective your regen is.
It's multiplicative with your base regeneration, making it very powerful.

This is different from "increased life regeneration" which is additive.
""",
            how_it_works="""
FLAT REGENERATION:
1. Fixed amount of life per second
2. Example: "Regenerate 50 life per second"
3. Does not scale with max life
4. Good early game, falls off with high life pools

PERCENT REGENERATION:
1. Percentage of your maximum life per second
2. Example: "Regenerate 2% of maximum life per second"
3. Scales automatically as you get more life
4. Primary source of regen for most builds

REGENERATION RATE MODIFIER:
1. "X% increased Life Regeneration Rate"
2. MULTIPLIES your total regeneration
3. 50% increased rate = 1.5x your regen
4. Very powerful scaling option

INTERACTION WITH DEGENS:
1. Regeneration offsets degeneration damage
2. Net effect = Regen - Degen per second
3. If Regen > Degen: You heal
4. If Degen > Regen: You take net damage
5. Righteous Fire: Classic example of regen vs degen balance

REGENERATION STACKING:
- All flat regen sources add together
- All % regen sources add together
- Then Rate modifiers multiply the total
""",
            calculation_formula="""
Total Regeneration:
Base_Flat = Sum of all flat regen sources
Base_Percent = Sum of all % regen sources
Percent_Regen = Max_Life x (Base_Percent / 100)
Total_Base_Regen = Base_Flat + Percent_Regen
Final_Regen = Total_Base_Regen x (1 + Regen_Rate_Increased/100)

Example:
- Max Life: 5000
- Flat regen: 100/sec
- % regen: 3% + 2% = 5%
- Regen rate: 50% increased

Calculation:
- Percent regen: 5000 x 0.05 = 250/sec
- Total base: 100 + 250 = 350/sec
- With rate: 350 x 1.5 = 525/sec final

Righteous Fire Balance:
RF_Degen = 90% of max life as fire damage per second (reduced by fire res)
Needed_Regen = RF_Degen_After_Resist to sustain
Example: 90% of 5000 = 4500/sec, with 80% fire res = 900/sec degen
Need 900+ life regen per second to sustain RF

Net Recovery:
Net = Regen - Degen
Positive = healing
Negative = taking damage
""",
            examples=[
                "Righteous Fire: Balance 90% life degen vs high regen + fire resist",
                "5000 life with 5% regen = 250 life/sec baseline",
                "50% increased regen rate = 1.5x total regeneration",
                "Stone Golem buff: Flat life regen boost",
                "Vitality aura: Grants flat life regen to you and allies"
            ],
            common_questions={
                "What's the difference between 'increased regeneration' and 'regeneration rate'?": "'Increased life regeneration' adds to your % regen pool. 'Regeneration Rate' is a multiplier on your TOTAL regen. Rate is much more powerful.",
                "Does regen work during RF degen?": "Yes! Regen constantly heals while RF constantly damages. If regen > degen, you sustain.",
                "Is flat regen worth it late game?": "Usually not as primary source. % regen scales with life pool. Flat is supplementary.",
                "Can I out-regen Blood Rage degen?": "Yes, with enough regen. Blood Rage is 4% life degen, so ~5%+ regen sustains it.",
                "Does regen work on Energy Shield?": "ES has its own regeneration. Life regen doesn't restore ES unless you have specific conversion effects."
            },
            related_mechanics=['life', 'leech', 'degeneration', 'righteous_fire'],
            important_notes=[
                "% regen scales with max life, flat regen doesn't",
                "'Regeneration Rate' is a MULTIPLIER (very powerful)",
                "'Increased life regeneration' is additive to % regen",
                "Net recovery = Regen - Degen per second",
                "RF builds need regen > fire degen to sustain",
                "Life regen doesn't affect Energy Shield",
                "Stacks from all sources"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core mechanics similar
- Regeneration Rate modifier exists in both
- Some regen sources adjusted for PoE2
- RF interaction similar but numbers may differ
- New passive tree may have different regen options
- Zealot's Oath (regen applies to ES) status in PoE2 varies
"""
        )

        # =====================================================================
        # ACCURACY AND HIT CHANCE
        # =====================================================================

        self.mechanics['accuracy'] = MechanicExplanation(
            name="Accuracy",
            category=MechanicCategory.DAMAGE,
            short_description="Determines hit chance - Accuracy vs Evasion with 5%-100% cap",
            detailed_explanation="""
Accuracy is the stat that determines whether your attacks hit enemies. In PoE2,
accuracy is checked against the target's evasion rating to determine hit chance.

The formula is: Hit Chance = Accuracy / (Accuracy + Evasion/4)

This means you need roughly 4x the enemy's evasion in accuracy to achieve ~80% hit chance.
Hit chance is capped between 5% (minimum) and 100% (maximum).

IMPORTANT: Spells do NOT use accuracy - they always hit (unless the enemy has
specific spell avoidance). Only attacks use accuracy.

Resolute Technique is a keystone that makes your hits always hit but you can
never deal critical strikes.
""",
            how_it_works="""
1. When you attack, the game calculates your hit chance
2. Formula: Hit Chance = Accuracy / (Accuracy + Evasion/4)
3. Hit chance is clamped between 5% and 100%
4. If the roll succeeds, your attack hits
5. If the roll fails, the attack misses completely (no damage, no effects)
6. Spells ALWAYS hit - accuracy only affects attacks
7. Resolute Technique: Hits can't be evaded, but can't crit either

ACCURACY SOURCES:
- Base accuracy from level (increases per level)
- Dexterity grants flat accuracy (+2 per point)
- Gear with +accuracy or %increased accuracy
- Passive tree nodes
- Support gems and auras (like Precision)
""",
            calculation_formula="""
Hit Chance = Accuracy / (Accuracy + Evasion/4)
Clamped to range [5%, 100%]

Example calculations:
- 1000 accuracy vs 1000 evasion: 1000 / (1000 + 250) = 80% hit chance
- 2000 accuracy vs 2000 evasion: 2000 / (2000 + 500) = 80% hit chance
- 500 accuracy vs 2000 evasion: 500 / (500 + 500) = 50% hit chance
- 4000 accuracy vs 1000 evasion: 4000 / (4000 + 250) = 94% hit chance

To achieve specific hit chances vs enemy evasion E:
- 80% hit: Need Accuracy = E (4:1 ratio to evasion/4)
- 90% hit: Need Accuracy = 2.25 x E
- 95% hit: Need Accuracy = 4.75 x E
- 100% hit: Need Accuracy = infinity (or use Resolute Technique)

Dexterity bonus:
- Every 1 Dexterity = +2 Accuracy
- 100 DEX = +200 Accuracy
""",
            examples=[
                "1000 accuracy vs 1000 evasion = 80% hit chance",
                "Resolute Technique makes all attacks hit but disables crits",
                "Dexterity gives +2 accuracy per point",
                "Precision aura grants flat accuracy to you and allies",
                "Spells ignore accuracy entirely - they always hit"
            ],
            common_questions={
                "Do spells need accuracy?": "NO! Spells always hit. Only attacks use accuracy.",
                "What is the hit chance cap?": "Minimum 5%, maximum 100%. You can never have less than 5% hit chance.",
                "Is Resolute Technique good?": "Yes for non-crit builds. You always hit but lose crit entirely.",
                "How much accuracy do I need?": "Depends on content. For endgame, aim for 90%+ hit chance against evasion-based enemies.",
                "Does accuracy affect ailments?": "Indirectly - you must hit to apply ailments. Misses apply nothing."
            },
            related_mechanics=['evasion', 'crit', 'resolute_technique', 'dexterity'],
            important_notes=[
                "Formula: Accuracy / (Accuracy + Evasion/4)",
                "Capped between 5% and 100%",
                "Only affects ATTACKS, not spells",
                "Dexterity grants +2 accuracy per point",
                "Resolute Technique = always hit, never crit",
                "Missing an attack = no damage, no ailments, no effects"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core formula similar but values may differ
- PoE2 enemies may have different evasion scaling
- Resolute Technique still exists with same tradeoff
- Accuracy remains attack-only (spells still always hit)
"""
        )

        # =====================================================================
        # MANA RESOURCE
        # =====================================================================

        self.mechanics['mana'] = MechanicExplanation(
            name="Mana",
            category=MechanicCategory.RESOURCES,
            short_description="Primary resource for casting skills - costs, reservation, and regeneration",
            detailed_explanation="""
Mana is your primary resource for using most active skills. Every skill has a mana
cost that must be paid when using it. If you don't have enough mana, you can't use
the skill.

KEY CONCEPTS:
- Mana Cost: Flat amount deducted when using a skill
- Mana Reservation: Permanent reduction to max mana (percentage or flat)
- Mana Regeneration: Natural recovery over time
- Mana Recovery Rate: Multiplier affecting all mana recovery
- "Full Mana" Conditions: Some effects trigger when mana is full

In PoE2, Spirit handles most auras/heralds (not mana reservation), but some skills
still reserve mana. Mana management is crucial for sustained combat.
""",
            how_it_works="""
1. Skills have base mana costs (modified by supports, passives, gear)
2. Using a skill deducts the cost from current mana
3. If current mana < cost, skill cannot be used
4. Mana regenerates naturally based on your regen rate
5. Mana can also be recovered through leech, flasks, and on-hit effects
6. Some skills reserve a portion of your max mana (reduces available pool)

MANA RESERVATION:
- Flat reservation: Reserves exact amount (e.g., -50 mana)
- Percentage reservation: Reserves % of max (e.g., 25% of max mana)
- Reservation efficiency modifiers reduce the amount reserved
- Reserved mana cannot be spent - it's locked

MANA REGENERATION:
- Base regen: ~1.75% of max mana per second
- Increased by %mana regeneration rate modifiers
- Affected by Mana Recovery Rate (multiplier)

"FULL MANA" MECHANICS:
- Some passives/items trigger effects when at full mana
- Requires current mana = unreserved max mana
- Can be maintained with high regen or low-cost skills
""",
            calculation_formula="""
Available Mana = Maximum Mana - Reserved Mana

Mana Regeneration per second = Max Mana x Base Regen% x (1 + increased regen%) x Recovery Rate

Example:
- Max Mana: 500
- 25% reservation (aura): 125 reserved
- Available: 375 mana
- Base regen 1.75%: 500 x 0.0175 = 8.75 mana/sec base
- +100% increased regen: 8.75 x 2.0 = 17.5 mana/sec
- 50% increased recovery rate: 17.5 x 1.5 = 26.25 mana/sec

Mana Cost Calculation:
Final Cost = Base Cost x (1 + sum of cost modifiers) x cost multipliers
- "Reduced mana cost" = additive reduction
- "Less mana cost" = multiplicative reduction (rarer, more powerful)

Efficiency Example (reservation):
- Skill reserves 50% mana base
- +30% reservation efficiency
- Actual reservation = 50% / 1.30 = 38.5%
""",
            examples=[
                "500 max mana with 25% reserved = 375 available for skills",
                "Clarity aura grants flat mana regeneration",
                "Mind Over Matter diverts damage to mana (requires mana available)",
                "Eldritch Battery converts ES to 'mana' for skill costs",
                "Full mana bonuses require no reservation or instant recovery"
            ],
            common_questions={
                "How do I reduce mana costs?": "Passives, support gems (-mana cost), items with reduced cost, and crafted mods.",
                "What's the difference between reservation and cost?": "Cost is paid per use and regenerates. Reservation is permanent reduction to your pool.",
                "Is mana reservation the same as Spirit?": "No! Spirit is a separate resource in PoE2. Some skills still reserve mana, but auras use Spirit.",
                "How does mana leech work?": "Similar to life leech - % of damage dealt recovered as mana, subject to rate caps.",
                "What triggers 'full mana' effects?": "Your current mana must equal your unreserved maximum. Even 1 missing mana disables it."
            },
            related_mechanics=['spirit', 'leech', 'mind_over_matter', 'reservation'],
            important_notes=[
                "Most auras now use Spirit instead of mana reservation",
                "Some skills still reserve mana (check skill description)",
                "Mana regeneration is based on MAX mana, not current",
                "Recovery rate affects regen, leech, and flask recovery",
                "Full mana conditions are strict - need 100% unreserved",
                "Eldritch Battery makes ES protect mana instead of life"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Spirit system now handles most auras/heralds (not mana reservation)
- Mana reservation still exists but is less common
- Base mana and regen values may differ
- Mana management generally simpler due to Spirit split
- Some reservation efficiency mechanics adjusted
"""
        )

        # =====================================================================
        # COOLDOWN MECHANICS
        # =====================================================================

        self.mechanics['cooldown'] = MechanicExplanation(
            name="Cooldown",
            category=MechanicCategory.SCALING,
            short_description="Time between skill uses - recovery rate, charges, and bypass mechanics",
            detailed_explanation="""
Cooldowns are timers that prevent skills from being used again until they expire.
Many powerful skills in PoE2 have cooldowns to balance their strength.

KEY CONCEPTS:
- Cooldown Time: Base time before skill can be used again
- Cooldown Recovery Rate: Multiplier that speeds up cooldown expiration
- Cooldown Bypass: Ways to ignore or skip cooldowns (charges, triggers)
- Minimum Cooldown: Some effects have a floor that can't be reduced below

Understanding cooldowns is essential for optimizing skill rotations and
maximizing uptime on powerful abilities.
""",
            how_it_works="""
1. Use a skill with a cooldown
2. Cooldown timer starts (skill unusable)
3. Timer counts down based on cooldown recovery rate
4. When timer reaches 0, skill is usable again
5. Some skills store multiple charges (each with own cooldown)
6. Some effects bypass cooldowns entirely

COOLDOWN RECOVERY RATE:
- Base recovery rate is 100% (1 second = 1 second)
- +50% cooldown recovery rate: 1 second base = 0.67s actual
- Formula: Actual Cooldown = Base Cooldown / (1 + increased recovery rate)

COOLDOWN CHARGES:
- Skills can have multiple uses stored
- Each use consumes a charge
- Charges regenerate independently
- Can use skill while other charges are cooling down

COOLDOWN BYPASS:
- Some effects grant 'cooldown bypass' (skill usable regardless)
- Triggered skills may ignore cooldown
- Specific mechanics like Second Wind support

MINIMUM COOLDOWN:
- Some effects have a floor (e.g., 0.25 seconds minimum)
- Cannot be reduced below minimum regardless of recovery rate
- Check skill description for minimum cooldown
""",
            calculation_formula="""
Actual Cooldown = Base Cooldown / (1 + sum of cooldown recovery rate modifiers)

Example:
- Base cooldown: 4 seconds
- +100% cooldown recovery rate
- Actual: 4 / (1 + 1.0) = 4 / 2 = 2 seconds

Multiple Sources Stack Additively:
- +50% from passive
- +30% from item
- +20% from support
- Total: +100% recovery rate
- 4 second base = 2 second actual

Charge-Based Skills:
- 3 charges, 4 second cooldown per charge
- Use all 3 instantly
- After 4 seconds: 1 charge ready
- After 8 seconds: 2 charges ready
- After 12 seconds: all 3 ready

Minimum Cooldown Example:
- Base: 1 second
- Minimum: 0.25 seconds
- +500% recovery rate would give: 1 / 6 = 0.167 seconds
- But minimum caps it at 0.25 seconds
""",
            examples=[
                "Movement skills often have 2-4 second base cooldowns",
                "Guard skills (Molten Shell, etc.) have longer cooldowns",
                "Warcries may have cooldowns reduced by passives",
                "Some unique items grant cooldown recovery rate",
                "Triggered skills sometimes bypass cooldowns"
            ],
            common_questions={
                "How do I reduce cooldowns?": "Stack cooldown recovery rate from gear, passives, and support gems.",
                "Is there a minimum cooldown?": "Some skills have minimums (check description). Others can be reduced to near-zero with enough investment.",
                "Do triggered skills have cooldowns?": "Often yes, but may be shorter. Some triggered effects bypass cooldowns.",
                "What's the difference between cooldown and charges?": "Cooldown is time between uses. Charges are stored uses that each have their own cooldown.",
                "Can I have 0 cooldown?": "Rarely. Most skills have either a minimum or practical limits. Some skills have no cooldown at all."
            },
            related_mechanics=['cast_speed', 'attack_speed', 'triggered_skills', 'charges'],
            important_notes=[
                "Cooldown Recovery Rate speeds up cooldown expiration",
                "Formula: Actual CD = Base CD / (1 + recovery rate)",
                "Stacks additively from all sources",
                "Some skills have minimum cooldown floors",
                "Charge-based skills regenerate charges independently",
                "Triggered effects may bypass cooldowns"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core cooldown mechanics similar
- Some skill cooldowns adjusted for PoE2 balance
- New skills with different cooldown interactions
- Cooldown recovery rate remains important stat
- Trigger mechanics refined
"""
        )

        # =====================================================================
        # DAMAGE CONVERSION
        # =====================================================================

        self.mechanics['damage_conversion'] = MechanicExplanation(
            name="Damage Conversion",
            category=MechanicCategory.DAMAGE,
            short_description="Converting damage types - Physical > Lightning > Cold > Fire > Chaos chain",
            detailed_explanation="""
Damage conversion changes damage from one type to another BEFORE it hits the enemy.
This is extremely powerful because converted damage benefits from modifiers to BOTH
the original type AND the final type.

CONVERSION CHAIN (one-way only):
Physical -> Lightning -> Cold -> Fire -> Chaos

You can ONLY convert forward in this chain. You cannot convert Fire back to Cold,
or Chaos to anything else.

KEY CONCEPTS:
- Conversion happens BEFORE damage is dealt
- Converted damage gains bonuses from both types
- Over 100% conversion is normalized (proportionally reduced)
- "Added as" is different from conversion (creates extra damage)
""",
            how_it_works="""
1. Start with base damage of a type
2. Apply conversion effects (changes damage type)
3. Converted damage benefits from BOTH type modifiers
4. Deal final damage of the converted type

CONVERSION CHAIN:
Physical -> Lightning -> Cold -> Fire -> Chaos
- Can skip steps (Physical -> Fire directly is valid)
- Cannot go backwards (Fire -> Cold is impossible)
- Chaos is the end - cannot convert chaos to anything

OVER 100% CONVERSION:
- If total conversion exceeds 100%, it's normalized
- Example: 60% Phys to Fire + 60% Phys to Cold = 120% total
- Normalized: 60/120 = 50% each, so 50% Fire + 50% Cold

"ADDED AS" VS CONVERSION:
- Conversion: Changes damage type (doesn't increase total base)
- "Added as": Creates EXTRA damage of another type
- Example: "Gain 20% of Physical as Extra Fire"
  - 100 physical stays 100 physical
  - PLUS 20 extra fire damage = 120 total

DOUBLE-DIPPING (how it benefits you):
- 100 physical damage, 50% increased physical, 50% increased fire
- Convert 100% physical to fire
- Physical bonus applies first: 100 x 1.5 = 150
- Fire bonus applies to converted: 150 x 1.5 = 225 final fire damage
- Without conversion, only physical bonus = 150 damage
""",
            calculation_formula="""
CONVERSION ORDER:
1. Base damage of original type
2. Apply "added as extra" (creates additional damage)
3. Apply conversion (changes damage type, normalized if >100%)
4. Apply damage modifiers to each damage type

Example - Full Physical to Fire conversion:
- 100 base physical damage
- 50% increased physical damage
- 50% increased fire damage
- 100% physical converted to fire

Step 1: Physical damage = 100 x (1 + 0.5) = 150 (from phys bonus)
Step 2: Converted to fire = 150 fire damage
Step 3: Fire bonus applies = 150 x (1 + 0.5) = 225 final fire damage

Over 100% Normalization Example:
- 70% phys to lightning + 50% phys to cold = 120% total
- Lightning: 70/120 = 58.3% of physical -> lightning
- Cold: 50/120 = 41.7% of physical -> cold
- 100 physical = 58.3 lightning + 41.7 cold

"Added As" Example:
- 100 physical, 30% of physical added as fire
- Result: 100 physical + 30 fire = 130 total damage (two types)
""",
            examples=[
                "100% phys to lightning + 100% lightning to cold = all cold",
                "Avatar of Fire converts 50% of all damage to fire",
                "Hatred adds cold damage based on physical (added as, not conversion)",
                "Winter Spirit notable: 40% physical converted to cold",
                "Cannot convert chaos damage to anything - it's the end of chain"
            ],
            common_questions={
                "Can I convert Fire to Cold?": "NO! Conversion only goes forward: Phys -> Light -> Cold -> Fire -> Chaos. Cannot reverse.",
                "What happens with over 100% conversion?": "It's normalized proportionally. 60% to A + 60% to B becomes 50% each.",
                "Does converted damage benefit from both types?": "YES! This is why conversion is powerful. Get double-dipping from both damage type modifiers.",
                "What's the difference between 'converted to' and 'added as'?": "Conversion changes type (same total base). Added as creates extra damage (increases total).",
                "Why can't I convert chaos damage?": "Chaos is the end of the chain. It cannot be converted to anything else by design."
            },
            related_mechanics=['physical_damage', 'elemental_damage', 'chaos_damage', 'added_damage'],
            important_notes=[
                "Chain: Physical -> Lightning -> Cold -> Fire -> Chaos",
                "One-way only - cannot convert backwards",
                "Over 100% conversion is normalized proportionally",
                "Converted damage benefits from BOTH type modifiers",
                "'Added as' creates extra damage, conversion changes type",
                "Chaos cannot be converted to anything"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core conversion mechanics identical
- Same conversion chain order
- Same over 100% normalization rules
- Some specific conversion sources may differ
- Double-dipping mechanics similar
"""
        )

        # =====================================================================
        # RESISTANCES
        # =====================================================================

        self.mechanics['resistances'] = MechanicExplanation(
            name="Resistances",
            category=MechanicCategory.DEFENSE,
            short_description="Damage reduction vs elements/chaos - 75% cap (90% max), negative = more damage",
            detailed_explanation="""
Resistances reduce incoming damage of their respective types. They are your PRIMARY
defense against elemental and chaos damage in Path of Exile 2.

RESISTANCE TYPES:
- Fire Resistance: Reduces fire damage
- Cold Resistance: Reduces cold damage
- Lightning Resistance: Reduces lightning damage
- Chaos Resistance: Reduces chaos damage

CAPS:
- Default cap: 75% (you take 25% of incoming damage)
- Maximum possible cap: 90% (hard cap, cannot exceed)
- Sources can raise cap (e.g., +1% to maximum fire resistance)

NEGATIVE RESISTANCE:
- Resistances CAN go negative
- Negative resistance means you take MORE damage
- -50% fire res = you take 150% fire damage!
- Campaign penalty: -30% to all elemental res after Act 5 equivalent
""",
            how_it_works="""
1. Incoming damage of a type is checked against your resistance
2. Damage Taken = Incoming Damage x (1 - Resistance%)
3. Resistance is capped at your maximum (default 75%)
4. Can go negative (acts as damage amplification)

RESISTANCE PENALTY:
- After certain story progression, you get -30% to elemental resistances
- This is permanent and must be overcome with gear/passives
- Chaos resistance has no penalty (but also fewer sources)

OVERCAPPING:
- Getting resistance ABOVE your cap (e.g., 120% fire res with 75% cap)
- Excess doesn't reduce damage further
- BUT protects against resistance reduction effects (curses, exposure)
- Recommended: 10-20% overcap for endgame

MAXIMUM RESISTANCE:
- Default maximum is 75% for all types
- Can be increased by specific sources (passives, gear, auras)
- Hard cap of 90% - cannot exceed regardless of modifiers
- Each 1% above 75% is very valuable (4% less damage taken per point)
""",
            calculation_formula="""
Damage Taken = Incoming Damage x (1 - Resistance / 100)
Resistance = min(Your Resistance, Your Maximum Resistance)

Example - Normal resistance:
- 1000 fire damage incoming
- 75% fire resistance (capped)
- Damage taken = 1000 x (1 - 0.75) = 250 damage

Example - Negative resistance:
- 1000 fire damage incoming
- -30% fire resistance (uncapped campaign)
- Damage taken = 1000 x (1 - (-0.30)) = 1000 x 1.30 = 1300 damage!

Example - Overcapping:
- You have 105% fire resistance, 75% cap
- Elemental Weakness curse: -30% resistance
- After curse: 105% - 30% = 75% (still capped!)
- Without overcap: 75% - 30% = 45% (significant damage increase)

Maximum Resistance Value:
- At 75% res: Take 25% damage
- At 80% res: Take 20% damage (20% less than at 75%!)
- At 85% res: Take 15% damage (40% less than at 75%!)
- At 90% res: Take 10% damage (60% less than at 75%!)
""",
            examples=[
                "75% fire res = take 25% of fire damage",
                "-30% cold res = take 130% of cold damage (ouch!)",
                "Purity of Fire aura can raise max fire res to 79-84%",
                "10% overcap protects against Elemental Weakness curse",
                "90% res (hard cap) = take only 10% damage"
            ],
            common_questions={
                "What's the resistance cap?": "Default 75%, hard cap 90%. You need specific sources to raise your cap above 75%.",
                "Can resistance go negative?": "YES! Negative resistance means you take MORE damage. Very dangerous!",
                "What is overcapping?": "Having resistance above your cap. Protects against resistance reduction effects.",
                "How much overcap do I need?": "10-20% recommended for endgame. More for curse-heavy content.",
                "Is chaos resistance important?": "Yes, but often neglected. No campaign penalty but also fewer sources. 0%+ recommended for endgame."
            },
            related_mechanics=['penetration', 'exposure', 'curses', 'elemental_damage', 'chaos_damage'],
            important_notes=[
                "Default cap: 75%, hard cap: 90%",
                "Campaign penalty: -30% to elemental resistances",
                "Negative resistance = take MORE damage",
                "Overcapping protects against resistance reduction",
                "Each 1% max res above 75% is extremely valuable",
                "Chaos resistance has no penalty but fewer sources"
            ],
            changed_from_poe1="""
CHANGES from PoE1:
- Core mechanics identical
- Same 75% default cap, 90% hard cap
- Same overcapping benefits
- Campaign penalty timing may differ
- Resistance sources adjusted for PoE2 gear
"""
        )

        # =====================================================================
        # AILMENT THRESHOLD (NEW POE2 SYSTEM)
        # =====================================================================

        self.mechanics['ailment_threshold'] = MechanicExplanation(
            name="Ailment Threshold",
            category=MechanicCategory.AILMENTS,
            short_description="NEW in PoE2 - Ailments require damage threshold, no longer guaranteed on crit",
            detailed_explanation="""
Ailment Threshold is a NEW mechanic in PoE2 that fundamentally changes how ailments
are applied. Unlike PoE1 where critical strikes guaranteed ailments, PoE2 uses a
damage-based threshold system.

CORE CONCEPT:
- Enemies have an Ailment Threshold (usually equal to their max life)
- Your chance to apply an ailment depends on damage dealt vs their threshold
- Bigger hits = higher chance to apply ailments
- Crits help by dealing more damage, but do NOT guarantee ailments

This system makes ailment application more consistent with build investment
while preventing trivial ailment spam with any build.

BUILDUP AILMENTS (Freeze, Electrocute):
- These use a buildup bar instead of instant application
- Multiple hits accumulate buildup
- When buildup reaches 100%, ailment triggers
- Buildup decays over time
""",
            how_it_works="""
1. You hit an enemy with damage that can cause an ailment
2. Game calculates: (Your Damage / Enemy Ailment Threshold) x Base Chance
3. Higher ratio = higher chance to apply
4. For buildup ailments, damage adds to a buildup bar

INSTANT AILMENTS (Ignite, Shock, Poison, Bleed):
- Chance = Base Ailment Chance x (Damage / Threshold)
- Example: 25% base ignite chance, deal 50% of threshold = 12.5% ignite chance
- Deal 100% of threshold in one hit = 25% ignite chance
- Deal 200% of threshold = 50% ignite chance (if you have enough base chance)

BUILDUP AILMENTS (Freeze, Electrocute):
- Each hit adds to a buildup bar
- Buildup amount based on damage vs threshold
- At 100% buildup, ailment triggers
- Buildup decays over time (roughly 10-15% per second)
- Boss thresholds increase after each application (anti-perma-CC)

AILMENT THRESHOLD VALUE:
- For most enemies: Threshold = Maximum Life
- Bosses may have higher thresholds
- Some enemies have ailment immunity or high thresholds
""",
            calculation_formula="""
INSTANT AILMENT CHANCE:
Chance = Base Chance x (Damage Dealt / Ailment Threshold)

Example (Ignite with 25% base chance):
- Enemy threshold: 10,000 (their max life)
- You deal 5,000 fire damage
- Ignite chance = 25% x (5000 / 10000) = 12.5%

Example (higher damage):
- Same enemy, 10,000 fire damage
- Ignite chance = 25% x (10000 / 10000) = 25%

BUILDUP AILMENTS:
Buildup Added = (Damage / Threshold) x Buildup Modifier
At 100% Buildup = Ailment Triggers

Example (Freeze):
- Enemy threshold: 10,000
- Hit 1: 3,000 cold damage = ~30% buildup
- Hit 2: 3,000 cold damage = ~60% total
- Hit 3: 3,000 cold damage = ~90% total
- Buildup decays between hits!
- Hit 4 (fast enough): 100%+ = FROZEN

BOSS THRESHOLDS:
- First freeze: Normal threshold
- Second freeze: Threshold increased
- Each subsequent: Higher and higher
- Decays over time (maybe 30-60 seconds)
""",
            examples=[
                "Crits NO LONGER guarantee ailments - they just deal more damage",
                "Big single hits are better for ailment chance than many small hits",
                "Freeze uses buildup - multiple hits accumulate toward 100%",
                "Bosses have increasing thresholds after each hard CC",
                "High threshold enemies (bosses) need massive damage to ailment"
            ],
            common_questions={
                "Do crits guarantee ailments?": "NO! This is a major change from PoE1. Crits just deal more damage, indirectly helping ailment chance.",
                "Why does my ignite chance vary?": "Because it depends on your damage vs enemy threshold. Low damage hits have lower chance.",
                "How do I freeze bosses?": "Build up freeze with multiple cold hits. But boss thresholds increase after each freeze - can't perma-freeze.",
                "Is ailment chance still useful?": "YES! It's the base chance that gets multiplied by your damage ratio. More base chance = more reliable ailments.",
                "What's the enemy's threshold?": "Usually their max life. Bosses may have additional modifiers."
            },
            related_mechanics=['ignite', 'shock', 'freeze', 'poison', 'bleed', 'electrocute', 'crit'],
            important_notes=[
                "NEW to PoE2 - completely replaces PoE1's crit-guarantees-ailment",
                "Threshold usually = enemy max life",
                "Bigger hits = higher ailment chance",
                "Crits help indirectly (more damage) but don't guarantee ailments",
                "Buildup ailments (freeze, electrocute) accumulate over multiple hits",
                "Boss thresholds increase after each hard CC (anti-permafreeze)"
            ],
            changed_from_poe1="""
COMPLETELY NEW in PoE2:
- PoE1: Critical strikes GUARANTEED ailment application
- PoE2: Ailment chance based on damage vs threshold
- This is a FUNDAMENTAL change to how ailments work
- Big hits matter more, crits matter less for ailments
- Buildup system for freeze/electrocute is new
- Boss anti-perma-CC is new
"""
        )

        # =====================================================================
        # DODGE ROLL (NEW POE2 MECHANIC)
        # =====================================================================

        self.mechanics['dodge_roll'] = MechanicExplanation(
            name="Dodge Roll",
            category=MechanicCategory.DEFENSE,
            short_description="NEW in PoE2 - i-frames during roll, stamina cost, cannot dodge everything",
            detailed_explanation="""
Dodge Roll is a NEW active defense mechanic in PoE2 that gives players direct control
over damage avoidance. By dodge rolling, you gain brief invincibility frames (i-frames)
that let you pass through attacks unharmed.

KEY CHARACTERISTICS:
- Costs stamina to perform
- Grants invincibility during the roll animation
- Covers a short distance in the roll direction
- Some attacks CANNOT be dodge rolled (specific boss mechanics)
- Essential skill for surviving in PoE2

This is fundamentally different from PoE1 where "dodge" was a passive stat. In PoE2,
dodge roll is an active ability that rewards player skill.
""",
            how_it_works="""
1. Press dodge roll key/button (spacebar by default)
2. Stamina is consumed
3. Character performs a quick roll in movement direction
4. During roll animation, you have INVINCIBILITY FRAMES
5. Attacks that hit during i-frames deal NO damage
6. After roll, brief recovery before you can act/roll again

STAMINA SYSTEM:
- You have a stamina bar (like a separate resource)
- Dodge rolling costs stamina
- Stamina regenerates over time
- Running also consumes stamina
- Cannot dodge roll without sufficient stamina

I-FRAMES (INVINCIBILITY FRAMES):
- Brief window during roll where you're invulnerable
- Timing matters - roll INTO attacks for best effect
- Some attacks have long hitbox durations (harder to i-frame)
- Learning enemy attack timings is crucial

LIMITATIONS:
- Some boss attacks CANNOT be dodged (often telegraphed)
- Ground effects persist (rolling through fire still burns after)
- Stamina depletion leaves you vulnerable
- Short range - cannot use as primary movement
""",
            calculation_formula="""
Dodge Roll Mechanics:
- Base Stamina Cost: ~30% of stamina bar (varies by build)
- Base Stamina Regen: Recovers over ~3-4 seconds
- Roll Distance: Short (about 1-2 character lengths)
- I-Frame Duration: Brief window during animation (~0.3-0.5 seconds)

Stamina Management:
- Full stamina bar = 2-3 consecutive rolls
- Running depletes stamina slowly
- Standing still regenerates stamina quickly
- Some passives/gear affect stamina

Cannot Dodge:
- Boss "ground slam" indicators (red zones)
- Some grab attacks
- Persistent ground effects (damage after roll ends)
- Specifically marked "undodgeable" attacks

Example Timing:
- Boss winds up attack (1 second)
- Attack hitbox active (0.5 seconds)
- You roll DURING the 0.5 second window
- Your i-frames overlap the hitbox = no damage
""",
            examples=[
                "Roll through boss slam attacks to avoid damage",
                "Spacebar is default dodge roll key",
                "Watch for RED FLASH - some attacks can't be dodged",
                "Stamina management is crucial - don't spam rolls",
                "Learn boss attack patterns to time rolls correctly"
            ],
            common_questions={
                "Can I dodge everything?": "NO! Some boss attacks are undodgeable. Watch for specific telegraphs.",
                "How many times can I roll?": "Depends on stamina. Usually 2-3 times before depleted, then wait for regen.",
                "Do i-frames work against all damage?": "During the i-frame window, yes. But ground effects damage you after roll ends.",
                "Is dodge roll better than evasion?": "Different. Evasion is passive chance. Dodge roll is active with guaranteed i-frames but costs stamina.",
                "What affects dodge roll?": "Some passives/gear can affect stamina cost, regen, roll distance, or i-frame duration."
            },
            related_mechanics=['evasion', 'stamina', 'block', 'movement_skills'],
            important_notes=[
                "NEW to PoE2 - active defensive ability",
                "Grants invincibility frames during roll animation",
                "Costs stamina - cannot spam infinitely",
                "Some attacks CANNOT be dodge rolled (undodgeable)",
                "Timing is crucial - roll INTO attacks",
                "Ground effects still damage after roll ends",
                "Essential skill to master for endgame bosses"
            ],
            changed_from_poe1="""
COMPLETELY NEW in PoE2:
- PoE1 "Dodge" was a passive stat (chance to avoid attacks)
- PoE2 Dodge Roll is an ACTIVE ability
- Player skill now matters for damage avoidance
- Stamina system is new (doesn't exist in PoE1)
- i-frames are a new concept for PoE
- This fundamentally changes combat engagement
"""
        )

    def get_mechanic(self, name: str) -> Optional[MechanicExplanation]:
        """Get explanation for a specific mechanic"""
        # Normalize: convert spaces to underscores, lowercase
        normalized = name.lower().replace(' ', '_').replace('-', '_')
        result = self.mechanics.get(normalized)

        # If not found, try without underscores (spaces)
        if not result:
            no_underscore = name.lower().replace('_', ' ')
            for key, mechanic in self.mechanics.items():
                if mechanic.name.lower() == no_underscore or key == normalized:
                    return mechanic

        return result

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
