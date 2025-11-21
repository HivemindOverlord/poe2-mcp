"""
Path of Exile 2 Mechanics Knowledge Base

Comprehensive explanations of game mechanics with calculations.
Answers common player questions about how things work.

Author: Claude
Date: 2025-10-24
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


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

    def __post_init__(self):
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

    Usage:
        >>> kb = PoE2MechanicsKnowledgeBase()
        >>> freeze_info = kb.get_mechanic("freeze")
        >>> print(freeze_info.detailed_explanation)
    """

    def __init__(self):
        self.mechanics: Dict[str, MechanicExplanation] = {}
        self._initialize_mechanics()

    def _initialize_mechanics(self):
        """Initialize all mechanics explanations"""

        # AILMENTS
        self.mechanics['freeze'] = MechanicExplanation(
            name="Freeze",
            category=MechanicCategory.AILMENTS,
            short_description="Prevents all actions for a duration based on damage dealt",
            detailed_explanation="""
Freeze is a cold-based ailment that completely immobilizes enemies, preventing them from
taking any actions including moving, attacking, or using skills. Freeze duration is based
on the amount of cold damage dealt relative to the enemy's maximum life.

In PoE2, freeze is one of the most powerful defensive mechanics when built correctly,
as it can completely shut down dangerous enemies before they can act.
""",
            how_it_works="""
1. You deal cold damage to an enemy
2. If the cold damage is at least 5% of the enemy's maximum life, they are frozen
3. Freeze duration = (Cold Damage / Enemy Max Life) × Base Duration (2 seconds)
4. Multiple freeze applications from the same source do not stack - only the longest freeze applies
5. Enemies build freeze buildup which must be reduced to 0 before they can act again
""",
            calculation_formula="""
Freeze Duration (seconds) = (Cold Damage Dealt / Enemy Maximum Life) × 2.0 × (1 + Increased Freeze Duration)

Minimum threshold: Cold damage must be at least 5% of enemy max life to freeze

Example:
- Enemy has 10,000 life
- You deal 1,500 cold damage
- Base freeze = (1500 / 10000) × 2.0 = 0.3 seconds
- With 50% increased freeze duration: 0.3 × 1.5 = 0.45 seconds
""",
            examples=[
                "Boss with 1,000,000 life hit for 50,000 cold damage = 0.1 second freeze",
                "Normal enemy with 5,000 life hit for 2,500 cold damage = 1.0 second freeze",
                "Multiple small hits can keep enemies permanently frozen if applied fast enough"
            ],
            common_questions={
                "Does freeze work on bosses?": "Yes, but they have much higher life so freeze duration is very short unless you deal massive cold damage.",
                "Can I freeze with non-cold damage?": "No, only cold damage can freeze. However, you can convert other damage types to cold.",
                "Does freeze stop damage over time effects?": "No, DoTs continue to damage frozen enemies.",
                "Can I shatter frozen enemies?": "Yes, killing a frozen enemy shatters them, which can trigger additional effects and prevents on-death effects."
            },
            related_mechanics=['chill', 'shatter', 'hypothermia', 'cold_damage'],
            important_notes=[
                "Freeze is calculated per hit, not cumulative",
                "Bosses have 70% less freeze duration",
                "Freeze prevents all actions including movement skills",
                "Frozen enemies can still be targeted and hit"
            ],
            changed_from_poe1="""
PoE2 freeze mechanics are substantially different from PoE1:
- Freeze buildup system instead of instant freeze
- Duration based more heavily on % of enemy life
- Freeze is generally more accessible but shorter duration on bosses
"""
        )

        self.mechanics['shock'] = MechanicExplanation(
            name="Shock",
            category=MechanicCategory.AILMENTS,
            short_description="Increases damage taken by shocked enemies",
            detailed_explanation="""
Shock is a lightning-based ailment that causes enemies to take increased damage from all sources.
The magnitude of the shock is based on the lightning damage dealt relative to the enemy's maximum life.

Shock is one of the best damage multipliers in the game because it affects ALL damage, not just
your own, making it excellent for party play and damage over time builds.
""",
            how_it_works="""
1. You deal lightning damage to an enemy
2. Shock magnitude = (Lightning Damage / Enemy Max Life) × 100, capped at 50%
3. Minimum shock is 5% increased damage taken (0.25% of enemy life in lightning damage)
4. Shocked enemies take increased damage from ALL sources
5. Shock duration is 4 seconds base
6. New shocks replace old shocks if they're stronger
""",
            calculation_formula="""
Shock Magnitude = min(50%, (Lightning Damage / Enemy Max Life) × 100)

Minimum to shock: Lightning damage must be at least 0.25% of enemy max life

Example:
- Enemy has 100,000 life
- You deal 5,000 lightning damage in one hit
- Shock magnitude = (5000 / 100000) × 100 = 5%
- Enemy takes 5% increased damage from all sources for 4 seconds
""",
            examples=[
                "10,000 lightning damage to enemy with 100,000 life = 10% shock",
                "Maximum shock is 50% increased damage taken (very hard to reach on bosses)",
                "Even a 5% shock is valuable for overall DPS increase"
            ],
            common_questions={
                "Does shock affect my allies' damage?": "Yes! Shock affects all damage the enemy takes, making it great for party play.",
                "Can I shock with non-lightning damage?": "No, only lightning damage can shock (unless you have special modifiers).",
                "Does shock affect damage over time?": "Yes, shocked enemies take increased DoT damage too.",
                "Can I shock bosses?": "Yes, but they have high life so shock magnitude is usually lower."
            },
            related_mechanics=['electrocute', 'lightning_damage', 'ailment_threshold'],
            important_notes=[
                "Shock affects ALL damage types (physical, elemental, chaos, DoT)",
                "Shock magnitude is capped at 50%",
                "Multiple shock sources do not stack - only strongest shock applies",
                "Shock is one of the best support mechanics for party play"
            ],
            changed_from_poe1="""
PoE2 shock is similar to PoE1 but with some changes:
- Slightly different scaling calculations
- More emphasis on hitting shock thresholds
- Shock effect is more visible and impactful
"""
        )

        self.mechanics['stun'] = MechanicExplanation(
            name="Stun",
            category=MechanicCategory.CROWD_CONTROL,
            short_description="Interrupts enemy actions based on damage dealt",
            detailed_explanation="""
Stun is a core combat mechanic in PoE2 that interrupts enemy actions. There are two types:
- Light Stun: Brief interrupt, builds up Heavy Stun threshold
- Heavy Stun: Long interrupt, completely stops the enemy

Stun is crucial for both offense (interrupting dangerous attacks) and defense (preventing
yourself from being stunned).
""",
            how_it_works="""
1. When you hit an enemy for significant damage (relative to their life), they may be stunned
2. Light Stun: Occurs on hits dealing 10%+ of enemy max life
   - 0.35 second interrupt
   - Builds Heavy Stun threshold by 20%
3. Heavy Stun: Occurs when Heavy Stun threshold reaches 100%
   - 2.0 second interrupt
   - Resets Heavy Stun threshold to 0%
4. Heavy Stun threshold decays by 100% per second when not being hit
""",
            calculation_formula="""
Light Stun Threshold = 10% of enemy maximum life
Heavy Stun Buildup = 20% per Light Stun

Example:
- Enemy has 10,000 life
- Light stun threshold = 1,000 damage
- You hit for 1,500 damage = Light Stun + 20% Heavy Stun buildup
- After 5 Light Stuns (100% buildup) = Heavy Stun triggers

Stun Avoidance:
Your Stun Threshold = Maximum Life × (1 - Stun Avoidance Modifier)
Higher stun threshold = harder to stun you
""",
            examples=[
                "Boss with 1,000,000 life needs 100,000 damage hits to Light Stun",
                "5 consecutive heavy hits will trigger Heavy Stun on most enemies",
                "Fast-hitting builds can keep enemies permanently stunned"
            ],
            common_questions={
                "Can I stun bosses?": "Yes, but they have very high stun thresholds. You need massive hits or stun-focused builds.",
                "What's the difference between stun and freeze?": "Stun is from any damage and gives shorter interrupts. Freeze is cold-only and prevents all actions completely.",
                "How do I avoid being stunned?": "Increase maximum life, get stun avoidance modifiers, or use energy shield (ES doesn't count for stun threshold).",
                "Do multiple small hits cause stun?": "No, each hit must individually meet the stun threshold. Small hits don't accumulate."
            },
            related_mechanics=['heavy_stun', 'stun_threshold', 'interrupt', 'poise'],
            important_notes=[
                "Stun is calculated per hit, not based on total DPS",
                "Heavy Stun threshold decays rapidly, so consistent hits are needed",
                "Energy Shield characters have lower effective stun threshold",
                "Stun can interrupt dangerous boss mechanics"
            ],
            changed_from_poe1="""
PoE2 stun system is completely redesigned:
- Two-tier system (Light + Heavy) instead of single stun
- Buildup mechanic for Heavy Stun
- More interactive and visible in combat
- Stun avoidance works differently
"""
        )

        self.mechanics['crit'] = MechanicExplanation(
            name="Critical Strike",
            category=MechanicCategory.DAMAGE,
            short_description="Deals extra damage based on critical strike multiplier",
            detailed_explanation="""
Critical strikes are hits that deal significantly more damage than normal hits. In PoE2,
critical strike mechanics have been reworked to be more accessible and impactful.

Critical strikes are one of the primary ways to scale damage to very high levels, especially
when combined with crit multiplier and increased crit chance.
""",
            how_it_works="""
1. Each hit rolls against your critical strike chance
2. If it crits, damage is multiplied by your critical strike multiplier
3. Base crit multiplier in PoE2 is +100% (200% total damage)
4. Critical strike multiplier is additive: +100% base + modifiers
5. Critical strikes can apply ailments more effectively
6. Crit chance is rolled per skill use, not per projectile
""",
            calculation_formula="""
Critical Damage = Base Damage × (1 + Base Crit Bonus + Added Crit Bonus) × (1 + Increased Crit Damage)

PoE2 Base: +100% damage on crit (200% total)

Example:
- Base hit: 1,000 damage
- Base crit multiplier: +100% (+50% from gear)
- Total multiplier: 1 + 1.5 = 2.5x
- Critical hit: 1,000 × 2.5 = 2,500 damage

Expected DPS with crits:
- Base: 1,000 DPS
- 50% crit chance, 2.5x multiplier
- Expected DPS = 1000 × (1 - 0.5) + 1000 × 0.5 × 2.5 = 1,750 DPS
""",
            examples=[
                "50% crit chance with 250% multiplier = 1.75x average damage",
                "75% crit chance with 300% multiplier = 2.25x average damage",
                "100% crit chance is possible but requires heavy investment"
            ],
            common_questions={
                "Is crit better than non-crit?": "It depends. Crit requires investment but scales extremely well. Non-crit is more consistent.",
                "Can spells crit?": "Yes, spells can crit just like attacks.",
                "Does crit work with damage over time?": "No, DoT cannot crit. Only hits can crit.",
                "What's a good crit chance?": "30-50% is decent, 70%+ is excellent, 100% is endgame optimization."
            },
            related_mechanics=['crit_multiplier', 'crit_chance', 'ailment_crit', 'lucky_crits'],
            important_notes=[
                "PoE2 base crit multiplier is +100% (not +150% like PoE1)",
                "Crit chance is capped at 100%",
                "Critical strikes have higher ailment chance and magnitude",
                "Investing in crit requires both chance AND multiplier"
            ],
            changed_from_poe1="""
PoE2 crit changes:
- Base crit multiplier reduced from +150% to +100%
- Crit multiplier is now additive (simpler math)
- More accessible crit chance on gear and tree
- Crit builds are more viable early game
"""
        )

        self.mechanics['spirit'] = MechanicExplanation(
            name="Spirit",
            category=MechanicCategory.RESOURCES,
            short_description="Resource for activating permanent aura-like gems",
            detailed_explanation="""
Spirit is a NEW resource in PoE2 used to activate permanent effects like auras, heralds,
and some persistent buffs. Unlike mana reservation in PoE1, Spirit is a separate resource
that doesn't affect your mana pool.

Managing Spirit effectively is crucial for maximizing your character's power through
permanent buffs and effects.
""",
            how_it_works="""
1. You gain Spirit from gear, passives, and certain uniques
2. Each permanent skill (aura, herald, etc.) reserves a fixed amount of Spirit
3. Reserved Spirit reduces your available Spirit but doesn't regenerate
4. You can only use skills if you have enough available Spirit
5. Deactivating skills immediately frees up their Spirit cost
6. Spirit is NOT affected by mana modifiers
""",
            calculation_formula="""
Available Spirit = Maximum Spirit - Reserved Spirit

Example:
- Maximum Spirit: 100
- Aura A: 30 Spirit
- Aura B: 40 Spirit
- Available: 100 - 30 - 40 = 30 Spirit remaining
- Can activate one more 30-Spirit skill, but not a 31-Spirit skill
""",
            examples=[
                "Start with ~50 Spirit from tree/gear",
                "Each major aura costs 20-40 Spirit",
                "Typical build runs 2-3 Spirit skills with 80-100 maximum Spirit",
                "Can't activate skills if you exceed your Spirit cap"
            ],
            common_questions={
                "How do I get more Spirit?": "From gear (especially amulets and rare items), passive tree, and certain uniques.",
                "What happens if I lose Spirit from removing gear?": "Your skills deactivate if you no longer have enough Spirit.",
                "Is Spirit like mana reservation?": "Similar concept but separate resource. Spirit doesn't affect your mana.",
                "How much Spirit do I need?": "Depends on your build. 80-100 Spirit is typical for 2-3 auras."
            },
            related_mechanics=['auras', 'heralds', 'permanent_buffs', 'resource_management'],
            important_notes=[
                "Spirit is NEW in PoE2 - didn't exist in PoE1",
                "Spirit is a hard cap - you can't exceed it with temporary modifiers",
                "Optimize Spirit by choosing high-value skills",
                "Support gems can reduce Spirit cost"
            ],
            changed_from_poe1="""
Spirit is completely new in PoE2:
- Replaces mana reservation for permanent effects
- Separate resource from mana
- More deterministic (fixed costs, not percentages)
- Easier to plan around
"""
        )

        # DAMAGE SCALING
        self.mechanics['increased_vs_more'] = MechanicExplanation(
            name="Increased vs More Damage",
            category=MechanicCategory.SCALING,
            short_description="Understanding additive vs multiplicative damage scaling",
            detailed_explanation="""
This is THE most important concept for understanding damage scaling in PoE2.
'Increased' modifiers are additive with each other, while 'More' modifiers are multiplicative.

Understanding this distinction is crucial for making good gear and passive tree choices.
""",
            how_it_works="""
1. All 'Increased' modifiers add together into one multiplier
   - Example: 50% increased + 30% increased + 20% increased = 100% increased
   - Final multiplier: 1.0 + 1.0 = 2.0x

2. All 'More' modifiers multiply separately
   - Example: 30% more × 25% more × 20% more
   - Final multiplier: 1.3 × 1.25 × 1.2 = 1.95x

3. 'More' multipliers apply AFTER 'Increased'
   - Base damage × (1 + Total Increased) × (More 1) × (More 2) × ...
""",
            calculation_formula="""
Final Damage = Base × (1 + ΣIncreased) × Π(1 + More)

Example:
- Base: 100 damage
- Increased: 50% + 30% + 20% = 100% increased
- More: 30% more, 25% more
- Calculation: 100 × (1 + 1.0) × 1.3 × 1.25
- Result: 100 × 2.0 × 1.3 × 1.25 = 325 damage

Why More is better:
- 100% increased damage = 2x multiplier
- 50% more damage = 1.5x multiplier
- But if you already have 200% increased, adding 100% more increased = 3.0x → 4.0x (33% gain)
- While adding 50% more = 3.0x × 1.5 = 4.5x multiplier (50% gain!)
""",
            examples=[
                "If you have 300% increased damage, adding 50% more is better than adding 100% increased",
                "First 100% increased damage doubles your damage, but more 'increased' has diminishing returns",
                "Support gems with 'more' multipliers are usually best for DPS"
            ],
            common_questions={
                "Is 'more' always better than 'increased'?": "Usually yes, especially if you already have lots of 'increased'. But 'more' modifiers often come with downsides.",
                "Do 'more' and 'increased' stack?": "Yes, they stack multiplicatively (more after increased).",
                "Why does my damage barely increase when I add more 'increased'?": "Diminishing returns. 'Increased' modifiers add together, so each additional one is less impactful.",
                "Should I take 'more' modifiers with downsides?": "Usually yes if the downside is manageable. 30% more damage is huge."
            },
            related_mechanics=['damage_scaling', 'diminishing_returns', 'support_gems'],
            important_notes=[
                "This applies to ALL modifiers: damage, cast speed, area, etc.",
                "'More' is always multiplicative, 'Increased' is always additive",
                "Read gem and item text carefully - the wording matters!",
                "Most builds have 200-500% 'increased' damage total"
            ],
            changed_from_poe1="""
Same mechanic as PoE1 - this is a core PoE concept.
Understanding this is essential for both PoE1 and PoE2.
"""
        )

        # Add more mechanics as needed...

    def get_mechanic(self, name: str) -> Optional[MechanicExplanation]:
        """Get explanation for a specific mechanic"""
        return self.mechanics.get(name.lower())

    def search_mechanics(self, query: str) -> List[MechanicExplanation]:
        """Search for mechanics matching a query"""
        results = []
        query_lower = query.lower()

        for mechanic in self.mechanics.values():
            # Search in name, description, and explanation
            if (query_lower in mechanic.name.lower() or
                query_lower in mechanic.short_description.lower() or
                query_lower in mechanic.detailed_explanation.lower()):
                results.append(mechanic)

        return results

    def get_by_category(self, category: MechanicCategory) -> List[MechanicExplanation]:
        """Get all mechanics in a specific category"""
        return [m for m in self.mechanics.values() if m.category == category]

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
                    lines.append(f"• {note}")

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

        # Search through all common questions
        for mechanic in self.mechanics.values():
            for q, a in mechanic.common_questions.items():
                if question_lower in q.lower() or q.lower() in question_lower:
                    return f"**{mechanic.name} - {q}**\n\n{a}\n\nFor more details, see the full {mechanic.name} explanation."

        return None


if __name__ == "__main__":
    # Demo
    kb = PoE2MechanicsKnowledgeBase()

    print("Path of Exile 2 Mechanics Knowledge Base")
    print("=" * 80)
    print()

    # Show freeze mechanic
    freeze = kb.get_mechanic("freeze")
    if freeze:
        print(kb.format_mechanic_explanation(freeze))
        print()

    # Answer a question
    print("\n" + "=" * 80)
    print("Question: Does freeze work on bosses?")
    print("=" * 80)
    answer = kb.answer_question("Does freeze work on bosses?")
    if answer:
        print(answer)
