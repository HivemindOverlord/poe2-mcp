"""
PoE2 Calculation Formulas

This module provides calculation formulas for Claude to use when analyzing builds.
MCP provides the formulas; Claude performs the calculations.

VERIFIED FOR POE2 - January 2026
"""

from typing import Any, Dict, List, Optional

# =============================================================================
# FORMULA DEFINITIONS
# =============================================================================

FORMULAS: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # DPS CALCULATIONS
    # =========================================================================
    "dps": {
        "name": "Damage Per Second (DPS)",
        "formula": "DPS = Base_Damage × (1 + sum(Increased%)) × product(1 + More%) × Attack_Speed × Crit_Multi_Factor",
        "expanded": """
DPS = Base × Increased × More × Speed × Crit

Where:
- Increased = (1 + sum of all "increased" modifiers)
- More = (1 + more1) × (1 + more2) × ... (each "more" multiplies separately)
- Crit_Multi_Factor = 1 + (Crit_Chance × (Crit_Multi - 1))
""",
        "variables": {
            "Base_Damage": "Weapon damage or spell base damage (from gem level)",
            "Increased%": "All 'increased' modifiers are ADDITIVE with each other",
            "More%": "Each 'more' modifier is MULTIPLICATIVE (applied separately)",
            "Attack_Speed": "Attacks per second (or cast speed for spells)",
            "Crit_Chance": "Chance to critically strike (0.0 to 1.0, capped at 1.0)",
            "Crit_Multi": "Critical strike multiplier (default 1.5 = 150%)",
        },
        "calculation_order": [
            "1. Calculate base damage (weapon + flat added damage)",
            "2. Sum ALL 'increased' modifiers (additive)",
            "3. Apply increased: Base × (1 + increased_sum)",
            "4. Apply each 'more' multiplier separately (multiplicative)",
            "5. Apply attack/cast speed",
            "6. Apply effective crit multiplier",
        ],
        "key_rules": [
            "'Increased' modifiers ADD together, then multiply once",
            "'More' modifiers each MULTIPLY separately",
            "100% increased + 50% increased = 150% increased (one 2.5× multiplier)",
            "50% more + 30% more = 1.5 × 1.3 = 1.95× (two separate multipliers)",
            "Crit chance is capped at 100%",
        ],
        "example": {
            "scenario": "Skill with 100 base damage, 200% increased, 50% more, 30% more, 2.0 APS, 50% crit, 200% multi",
            "calculation": """
Base: 100
Increased: 100 × (1 + 2.0) = 300
More #1: 300 × 1.5 = 450
More #2: 450 × 1.3 = 585
Speed: 585 × 2.0 = 1170
Crit Factor: 1 + (0.5 × (2.0 - 1)) = 1.5
Final: 1170 × 1.5 = 1755 DPS
""",
            "result": "1,755 DPS",
        },
    },
    # =========================================================================
    # EFFECTIVE HP
    # =========================================================================
    "ehp": {
        "name": "Effective Hit Pool (EHP)",
        "formula": "EHP = Life × (1 / (1 - Total_Damage_Reduction))",
        "expanded": """
For physical damage:
EHP_Physical = Life / (1 - Armor_Reduction) / (1 - Other_Phys_Reduction)

For elemental damage:
EHP_Elemental = Life / (1 - Resistance/100)

Combined (approximate):
EHP ≈ Life × Armor_Factor × Resistance_Factor × Other_Mitigation
""",
        "variables": {
            "Life": "Maximum life pool",
            "Armor_Reduction": "Physical damage reduction from armor (vs specific hit size)",
            "Resistance": "Elemental resistance (capped at 90% in PoE2)",
            "Other_Mitigation": "Additional damage reduction sources (fortify, endurance charges, etc.)",
        },
        "calculation_order": [
            "1. Calculate armor reduction for expected hit size",
            "2. Calculate resistance reduction",
            "3. Calculate other mitigation layers",
            "4. Combine multiplicatively: EHP = Life / ((1-r1) × (1-r2) × ...)",
        ],
        "key_rules": [
            "Damage reduction sources are multiplicative, not additive",
            "50% reduction + 50% reduction = 75% total (not 100%)",
            "Formula: 1 - (1-0.5) × (1-0.5) = 1 - 0.25 = 0.75",
            "Armor effectiveness varies by hit size",
            "Resistance cap is 90% in PoE2 (was 75% base in PoE1)",
        ],
        "example": {
            "scenario": "3000 life, 50% armor reduction (vs 1000 hit), 75% fire resistance",
            "calculation": """
Physical EHP vs 1000 hit:
EHP = 3000 / (1 - 0.50) = 3000 / 0.50 = 6000

Fire EHP:
EHP = 3000 / (1 - 0.75) = 3000 / 0.25 = 12000
""",
            "result": "6,000 Physical EHP / 12,000 Fire EHP",
        },
    },
    # =========================================================================
    # ARMOR
    # =========================================================================
    "armor": {
        "name": "Armor Physical Damage Reduction",
        "formula": "Reduction = Armor / (Armor + 10 × Incoming_Damage)",
        "expanded": """
Physical Damage Reduction = Armor / (Armor + 10 × Hit)
Capped at 90% maximum

Rule of thumb:
- 5× hit in armor = 33% reduction
- 10× hit in armor = 50% reduction
- 20× hit in armor = 66% reduction
""",
        "variables": {
            "Armor": "Total armor rating",
            "Incoming_Damage": "Size of the physical hit before reduction",
            "Reduction": "Percentage of physical damage mitigated (0.0 to 0.9)",
        },
        "key_rules": [
            "Armor is MORE effective against small hits",
            "Armor is LESS effective against big hits",
            "90% cap on damage reduction",
            "Only reduces HITS, not DoT (bleed, etc.)",
            "Works against physical spells too",
            "Formula changed from 12× to 10× in patch 0.1.1",
        ],
        "reference_table": """
Hit Size | Armor for 50% | Armor for 66%
---------|---------------|---------------
100      | 1,000         | 2,000
500      | 5,000         | 10,000
1,000    | 10,000        | 20,000
2,000    | 20,000        | 40,000
5,000    | 50,000        | 100,000
""",
        "example": {
            "scenario": "10,000 armor vs 1,000 physical hit",
            "calculation": """
Reduction = 10000 / (10000 + 10 × 1000)
         = 10000 / (10000 + 10000)
         = 10000 / 20000
         = 0.50 (50%)

Damage taken = 1000 × (1 - 0.50) = 500
""",
            "result": "50% reduction, 500 damage taken",
        },
    },
    # =========================================================================
    # RESISTANCE
    # =========================================================================
    "resistance": {
        "name": "Elemental Resistance",
        "formula": "Damage_Taken = Incoming × (1 - Resistance/100)",
        "expanded": """
Effective Resistance = min(Base_Res + Bonus_Res, Max_Res) - Penetration

Where:
- Base_Res = sum of all resistance sources
- Max_Res = 75% default, can be increased to 90% cap
- Penetration = enemy penetration (reduces YOUR resistance)
""",
        "variables": {
            "Resistance": "Total elemental resistance percentage",
            "Max_Resistance": "Maximum resistance (75% default, 90% hard cap)",
            "Penetration": "Enemy resistance penetration",
            "Exposure": "Debuff that reduces resistance (stacks additively)",
        },
        "key_rules": [
            "Default cap is 75%",
            "Hard cap is 90% (cannot exceed)",
            "Negative resistance means taking MORE damage",
            "-60% chaos resistance = 160% chaos damage taken",
            "Penetration applies AFTER your resistance calculation",
            "Each 1% max res above cap is very valuable",
        ],
        "reference_table": """
Resistance | Damage Multiplier | EHP Multiplier
-----------|-------------------|----------------
-60%       | 1.60× (160%)      | 0.625×
0%         | 1.00× (100%)      | 1.0×
50%        | 0.50× (50%)       | 2.0×
75%        | 0.25× (25%)       | 4.0×
80%        | 0.20× (20%)       | 5.0×
90%        | 0.10× (10%)       | 10.0×
""",
        "example": {
            "scenario": "1000 fire damage hit, 75% fire resistance",
            "calculation": """
Damage = 1000 × (1 - 75/100)
       = 1000 × (1 - 0.75)
       = 1000 × 0.25
       = 250 fire damage taken
""",
            "result": "250 fire damage taken (75% mitigated)",
        },
    },
    # =========================================================================
    # LEECH
    # =========================================================================
    "leech": {
        "name": "Life Leech",
        "formula": "Leech_Per_Hit = Damage_Dealt × Leech_Rate%",
        "expanded": """
Leech Recovery Rate:
- Each leech instance heals over time
- Default: 2% of max life per second PER INSTANCE
- Total leech rate capped at 20% of max life per second

Overleech:
- Normally, leech stops when you reach full life
- Overleech allows leech to continue past full life
- Creates a 'buffer' of incoming healing
""",
        "variables": {
            "Damage_Dealt": "Damage dealt by the hit (after all calculations)",
            "Leech_Rate": "Percentage of damage leeched (e.g., 5% = 0.05)",
            "Instance_Rate": "How fast each leech instance heals (default 2%/sec of max life)",
            "Max_Leech_Rate": "Maximum total leech per second (default 20% of max life)",
            "Overleech": "Whether leech continues past full life",
        },
        "calculation_order": [
            "1. Calculate damage dealt by hit",
            "2. Apply leech rate: Leech_Amount = Damage × Leech%",
            "3. Create leech instance (heals over time)",
            "4. Sum all active leech instances",
            "5. Cap at max leech rate (20% of max life/sec default)",
            "6. If overleech: continue healing past full life",
        ],
        "key_rules": [
            "Leech is based on DAMAGE DEALT, not damage before mitigation",
            "Default instance rate: 2% of max life per second",
            "Default max rate cap: 20% of max life per second",
            "Without overleech, leech stops at full life",
            "Overleech creates healing buffer above max life",
            "Physical damage leech is most common (some items/gems)",
            "Elemental damage leech requires specific sources",
        ],
        "reference_table": """
Max Life | 20% Leech Cap/sec | Time to Full (from 0%)
---------|-------------------|------------------------
1,000    | 200/sec           | 5.0 seconds
2,000    | 400/sec           | 5.0 seconds
3,000    | 600/sec           | 5.0 seconds
5,000    | 1,000/sec         | 5.0 seconds

Note: With enough damage and leech %, you'll always hit the cap.
More leech % doesn't help once capped - need faster leech rate.
""",
        "example": {
            "scenario": "5% physical leech, 2000 damage hit, 3000 max life",
            "calculation": """
Leech amount = 2000 × 0.05 = 100 life
Instance rate = 3000 × 0.02 = 60 life/sec
Instance duration = 100 / 60 = 1.67 seconds

If hitting rapidly, instances stack:
5 hits = 5 instances = 300 life/sec
But capped at 20%: 3000 × 0.20 = 600 life/sec max
""",
            "result": "100 life per hit, capped at 600 life/sec recovery",
        },
    },
    # =========================================================================
    # SPIRIT
    # =========================================================================
    "spirit": {
        "name": "Spirit Resource",
        "formula": "Available_Spirit = Base_Spirit + Gear_Spirit + Passive_Spirit - Reserved_Spirit",
        "expanded": """
Spirit is a PoE2-specific resource that limits how many persistent skills you can run.

Skills that reserve Spirit:
- Auras (Herald of Ash, etc.)
- Minions (Wolf Pack, etc.)
- Some buff skills

Spirit Sources:
- Gear (weapons, amulets, body armor can roll Spirit)
- Passive tree nodes
- Base spirit from level/class
""",
        "variables": {
            "Base_Spirit": "Spirit from level/class",
            "Gear_Spirit": "Spirit from equipped items",
            "Passive_Spirit": "Spirit from passive tree",
            "Reserved_Spirit": "Spirit used by active auras/minions",
        },
        "key_rules": [
            "Spirit is a HARD LIMIT - can't reserve more than you have",
            "Different from mana reservation (which is percentage-based)",
            "Minions and auras compete for the same Spirit pool",
            "Higher level gems often cost more Spirit",
            "Spirit appears on weapons, amulets, body armor, focus items",
        ],
        "example": {
            "scenario": "100 base spirit, +50 from gear, Herald (30) + Wolf Pack (45)",
            "calculation": """
Total Spirit = 100 + 50 = 150
Reserved = 30 + 45 = 75
Remaining = 150 - 75 = 75 Spirit available
""",
            "result": "75 Spirit remaining for additional skills",
        },
    },
    # =========================================================================
    # STUN
    # =========================================================================
    "stun": {
        "name": "Stun Mechanics",
        "formula": "Stun_Chance = Damage / (Damage + Stun_Threshold)",
        "expanded": """
Stun Threshold = Max_Life × (1 + Stun_Threshold_Increases)

Stun occurs when:
- Hit damage exceeds stun threshold check
- Random roll based on damage vs threshold
""",
        "variables": {
            "Damage": "Hit damage BEFORE mitigation",
            "Stun_Threshold": "Target's stun threshold (based on max life)",
            "Max_Life": "Target's maximum life",
            "Stun_Duration": "How long the stun lasts",
        },
        "key_rules": [
            "Stun is checked BEFORE damage mitigation",
            "Higher life = harder to stun",
            "Stun threshold increases make you harder to stun",
            "Stun avoidance/immunity exists on gear and passives",
            "Bosses often have stun immunity phases",
        ],
        "example": {
            "scenario": "500 damage hit vs target with 1000 stun threshold",
            "calculation": """
Stun Chance = 500 / (500 + 1000)
            = 500 / 1500
            = 0.33 (33%)
""",
            "result": "33% chance to stun",
        },
    },
    # =========================================================================
    # CRITICAL STRIKES
    # =========================================================================
    "crit": {
        "name": "Critical Strike",
        "formula": "Effective_Crit = Base_Crit × (1 + Increased_Crit%)",
        "expanded": """
Critical Strike Multiplier effect:
Crit_DPS_Factor = 1 + (Crit_Chance × (Crit_Multi - 1))

Where Crit_Chance is capped at 100% (1.0)
""",
        "variables": {
            "Base_Crit": "Skill or weapon base critical strike chance",
            "Increased_Crit": "Sum of all 'increased critical strike chance' modifiers",
            "Crit_Multi": "Critical strike multiplier (default 150%)",
            "Lucky_Crits": "Roll twice, take higher (from Diamond Flask or other sources)",
        },
        "key_rules": [
            "Crit chance is capped at 100%",
            "Base crit varies by skill/weapon (5% to 10% common)",
            "Increased crit is ADDITIVE with itself",
            "Crit multi default is 150% (1.5×)",
            "Lucky crits effectively square your miss chance",
            "Elemental Overload alternative: no crit multi but damage bonus",
        ],
        "reference_table": """
Crit Chance | Crit Multi | Effective DPS Multiplier
------------|------------|-------------------------
5%          | 150%       | 1.025× (+2.5%)
25%         | 150%       | 1.125× (+12.5%)
50%         | 150%       | 1.25× (+25%)
50%         | 200%       | 1.50× (+50%)
75%         | 200%       | 1.75× (+75%)
100%        | 200%       | 2.00× (+100%)
100%        | 300%       | 3.00× (+200%)
""",
        "example": {
            "scenario": "7% base crit, 500% increased crit, 200% crit multi",
            "calculation": """
Effective Crit = 7% × (1 + 5.0) = 7% × 6 = 42%
Capped at 100%, so Crit = 42%

DPS Factor = 1 + (0.42 × (2.0 - 1))
           = 1 + (0.42 × 1.0)
           = 1.42 (+42% effective DPS)
""",
            "result": "42% crit chance, 1.42× DPS multiplier",
        },
    },
    # =========================================================================
    # DAMAGE CONVERSION
    # =========================================================================
    "conversion": {
        "name": "Damage Conversion",
        "formula": "Converted = Base_Damage × Conversion%",
        "expanded": """
Conversion order (hardcoded):
Physical → Lightning → Cold → Fire → Chaos

Rules:
- Conversion happens BEFORE 'increased' modifiers
- Converted damage benefits from BOTH original and new type modifiers
- Over 100% conversion is normalized
- 'Added as' is separate from conversion
""",
        "variables": {
            "Base_Damage": "Original damage before conversion",
            "Conversion%": "Percentage converted to new type",
            "Added_As": "Extra damage added as another type (not conversion)",
        },
        "key_rules": [
            "Conversion is one-way only (follows the chain)",
            "Physical → Lightning → Cold → Fire → Chaos",
            "Cannot convert backwards (Fire cannot become Cold)",
            "Converted damage gains bonuses from BOTH types",
            "'Added as X' is NOT conversion - it's extra damage",
            "Over 100% conversion normalizes proportionally",
        ],
        "example": {
            "scenario": "100 physical, 50% converted to cold, +50% phys, +100% cold",
            "calculation": """
Base: 100 physical
After conversion: 50 physical, 50 cold

Physical portion: 50 × (1 + 0.5) = 75
Cold portion: 50 × (1 + 0.5 + 1.0) = 125
(Cold gets BOTH phys and cold bonuses)

Total: 75 + 125 = 200 damage
""",
            "result": "200 total damage (75 phys + 125 cold)",
        },
    },
    # =========================================================================
    # DAMAGE OVER TIME
    # =========================================================================
    "dot": {
        "name": "Damage Over Time (DoT)",
        "formula": "DoT_DPS = Base_DoT × (1 + Increased_DoT%) × (1 + More_DoT%)",
        "expanded": """
DoT does NOT crit (unless specifically stated)
DoT does NOT benefit from attack/cast speed
DoT has its own 'increased' and 'more' modifiers
""",
        "variables": {
            "Base_DoT": "Base damage per second of the DoT",
            "Duration": "How long the DoT lasts",
            "Increased_DoT": "Sum of increased DoT damage modifiers",
            "More_DoT": "More DoT damage multipliers",
        },
        "key_rules": [
            "DoT cannot crit by default",
            "DoT damage is separate from hit damage",
            "DoT ignores armor (physical DoT still does physical damage type)",
            "DoT benefits from 'damage over time' modifiers",
            "Ailment DoTs (ignite, poison, bleed) scale differently",
            "Poison/Ignite/Bleed have their own specific formulas",
        ],
        "example": {
            "scenario": "100 base DoT, 200% increased DoT, 50% more DoT",
            "calculation": """
DoT = 100 × (1 + 2.0) × (1 + 0.5)
    = 100 × 3.0 × 1.5
    = 450 DPS
""",
            "result": "450 DoT DPS",
        },
    },
    # =========================================================================
    # BLOCK
    # =========================================================================
    "block": {
        "name": "Block Chance",
        "formula": "Block_Chance = Base_Block + Increased_Block",
        "expanded": """
Block completely negates a hit (in PoE2, may have partial block)
Spell block is separate from attack block
Shield is primary source of block
""",
        "variables": {
            "Base_Block": "Block from shield or other sources",
            "Increased_Block": "Additional block chance",
            "Max_Block": "Block cap (usually 75%)",
            "Spell_Block": "Separate chance to block spells",
        },
        "key_rules": [
            "Block is checked before damage calculation",
            "Blocked hits deal 0 damage (full block)",
            "Attack block and spell block are separate",
            "Block cap is typically 75%",
            "Glancing Blows: double block chance but take 65% damage on block",
            "Recovery on block exists (life/ES gained when blocking)",
        ],
        "example": {
            "scenario": "30% base block (shield), +20% block from passives",
            "calculation": """
Total Block = 30% + 20% = 50%
Capped at 75%, so Block = 50%

With 50% block: Half of incoming attacks are negated
""",
            "result": "50% attack block chance",
        },
    },
    # =========================================================================
    # CHARGES
    # =========================================================================
    "charges": {
        "name": "Charge Mechanics (Endurance, Frenzy, Power)",
        "formula": "Bonus = Charges × Bonus_Per_Charge",
        "expanded": """
Three charge types with different bonuses:

ENDURANCE CHARGES:
- +4% Physical Damage Reduction per charge
- +4% to all Elemental Resistances per charge
- Default max: 3 charges

FRENZY CHARGES:
- +4% increased Attack Speed per charge
- +4% increased Cast Speed per charge
- +4% MORE Damage per charge
- Default max: 3 charges

POWER CHARGES:
- +40% increased Critical Strike Chance per charge
- Default max: 3 charges
""",
        "variables": {
            "Charges": "Current number of charges",
            "Max_Charges": "Maximum charges (default 3, can be increased)",
            "Duration": "Charge duration (default 10 seconds)",
            "Generation": "How charges are gained (skills, on-kill, on-hit)",
        },
        "key_rules": [
            "Charges expire after duration (default 10 sec)",
            "Gaining a charge refreshes ALL charges of that type",
            "Max charges can be increased by passives/gear",
            "Some skills CONSUME charges for bonus effects",
            "Charge generation varies (on-kill, on-hit, on-crit, skills)",
        ],
        "reference_table": """
Charges | Endurance (Phys Red) | Frenzy (More Dmg) | Power (Crit)
--------|---------------------|-------------------|-------------
1       | 4% phys red, +4% res | 4% more damage    | +40% crit
2       | 8% phys red, +8% res | 8% more damage    | +80% crit
3       | 12% phys red, +12% res | 12% more damage | +120% crit
6       | 24% phys red, +24% res | 24% more damage | +240% crit
""",
        "example": {
            "scenario": "3 Frenzy charges with 1000 base DPS",
            "calculation": """
Frenzy bonus: 3 × 4% = 12% MORE damage
DPS = 1000 × (1 + 0.12) = 1120 DPS

Also: +12% attack speed, +12% cast speed
""",
            "result": "1,120 DPS (+12%), +12% attack/cast speed",
        },
    },
    # =========================================================================
    # ACCURACY
    # =========================================================================
    "accuracy": {
        "name": "Accuracy and Hit Chance",
        "formula": "Hit_Chance = Accuracy / (Accuracy + (Enemy_Evasion / 4))",
        "expanded": """
Hit Chance is calculated as:
Hit% = Attacker_Accuracy / (Attacker_Accuracy + Defender_Evasion/4)

Capped at 100% (always hit) and floored at 5% (always 5% minimum)
""",
        "variables": {
            "Accuracy": "Your accuracy rating",
            "Enemy_Evasion": "Target's evasion rating",
            "Hit_Chance": "Probability of hitting (5% to 100%)",
            "Level_Penalty": "Higher level enemies have more evasion",
        },
        "key_rules": [
            "Attacks can miss, spells always hit (unless dodged)",
            "Minimum hit chance is 5%",
            "Maximum hit chance is 100%",
            "Resolute Technique: Always hit but never crit",
            "Accuracy scales with Dexterity",
            "Level difference affects effective evasion",
        ],
        "example": {
            "scenario": "2000 accuracy vs enemy with 1000 evasion",
            "calculation": """
Hit Chance = 2000 / (2000 + 1000/4)
           = 2000 / (2000 + 250)
           = 2000 / 2250
           = 0.889 (88.9%)
""",
            "result": "88.9% chance to hit",
        },
    },
}


def get_formula(formula_type: str) -> Dict[str, Any]:
    """
    Get a specific formula by type.

    Args:
        formula_type: The formula identifier (e.g., 'dps', 'ehp', 'armor')

    Returns:
        Formula data dict or {'error': 'message'} if not found
    """
    formula_type = formula_type.lower().strip()

    if formula_type in FORMULAS:
        return FORMULAS[formula_type]

    # Try fuzzy matching
    for key in FORMULAS:
        if formula_type in key or key in formula_type:
            return FORMULAS[key]

    return {"error": f"Formula '{formula_type}' not found"}


def get_all_formula_names() -> List[str]:
    """Get list of all available formula types."""
    return list(FORMULAS.keys())


def get_formulas_by_category(category: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all formulas in a category.

    Categories: damage, defense, resources, utility
    """
    category_map = {
        "damage": ["dps", "crit", "conversion", "dot"],
        "defense": ["ehp", "armor", "resistance", "block", "evasion"],
        "resources": ["leech", "spirit", "charges"],
        "utility": ["stun", "accuracy"],
    }

    category = category.lower().strip()
    if category not in category_map:
        return {}

    return {key: FORMULAS[key] for key in category_map[category] if key in FORMULAS}
