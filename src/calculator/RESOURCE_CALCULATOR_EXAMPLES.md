# Resource Calculator Examples

## Overview
The `resource_calculator.py` module handles all Path of Exile 2 resource calculations, including the **NEW Spirit system**.

## Quick Start

```python
from calculator.resource_calculator import (
    ResourceCalculator,
    AttributeStats,
    ResourceModifiers,
    ResourceType
)

# Create character attributes
attributes = AttributeStats(strength=100, dexterity=80, intelligence=120)

# Initialize calculator for level 50 character
calc = ResourceCalculator(character_level=50, attributes=attributes)
```

## Life Calculation

```python
# Simple life calculation (no modifiers)
max_life = calc.calculate_maximum_life()
print(f"Base Life: {max_life}")

# Life with modifiers
life_mods = ResourceModifiers(
    flat_bonus=50,           # +50 life from gear
    increased_percent=150,   # 150% increased life
    more_multipliers=[1.10]  # 10% more life
)
max_life = calc.calculate_maximum_life(life_mods)
print(f"Modified Life: {max_life}")
```

**Formula**: `28 + (12 × level) + (2 × strength) + flat → × (1 + increased%) × more`

## Mana Calculation

```python
# Mana with modifiers
mana_mods = ResourceModifiers(
    flat_bonus=30,
    increased_percent=80
)
max_mana = calc.calculate_maximum_mana(mana_mods)

# Calculate mana regeneration
mana_regen = calc.calculate_mana_regeneration(
    maximum_mana=max_mana,
    increased_regen_percent=100,  # 100% increased regen
    flat_regen_per_second=10       # +10 mana/s
)
print(f"Mana: {max_mana}, Regen: {mana_regen}/s")
```

**Formula**: `34 + (4 × level) + (2 × intelligence) + flat → × (1 + increased%) × more`

## Energy Shield Calculation

```python
# ES (only from gear, no base)
es_mods = ResourceModifiers(
    flat_bonus=250,          # ES from gear
    increased_percent=200    # 200% increased ES
)
max_es = calc.calculate_maximum_energy_shield(es_mods)
print(f"Energy Shield: {max_es}")
```

## Spirit Calculation (NEW in PoE2)

Spirit is a **new resource in Path of Exile 2** that limits permanent effects:
- Permanent minions (Raise Zombie, Summon Skeleton, etc.)
- Persistent auras (Purity of Fire, Determination, etc.)
- Meta-gems

### Calculate Maximum Spirit

```python
# Spirit modifiers (rare!)
spirit_mods = ResourceModifiers(
    flat_bonus=50,          # +50 spirit from gear
    increased_percent=15    # 15% increased spirit (very rare!)
)
max_spirit = calc.calculate_maximum_spirit(spirit_mods)
print(f"Maximum Spirit: {max_spirit}")
```

**Formula**: `100 (base from quests) + flat → × (1 + increased%) × more`

### Add Spirit Reservations

```python
# Add permanent minion
calc.add_spirit_reservation(
    name="Raise Zombie",
    base_cost=25,
    support_multipliers=[1.5]  # 50% support multiplier
)
# Final cost: 25 × 1.5 = 38 Spirit

# Add skeleton with 2 supports
calc.add_spirit_reservation(
    name="Summon Skeleton",
    base_cost=20,
    support_multipliers=[1.4, 1.3]  # Two support gems
)
# Final cost: 20 × 1.4 × 1.3 = 37 Spirit (rounded up)

# Add aura
calc.add_spirit_reservation(
    name="Purity of Fire",
    base_cost=30
)
# Final cost: 30 Spirit
```

### Check Spirit Status

```python
# Calculate reserved and available Spirit
reserved = calc.calculate_spirit_reserved()
available = calc.calculate_spirit_available(max_spirit)

print(f"Reserved: {reserved}")
print(f"Available: {available}")

# Check for Spirit overflow
is_overflow, overflow_amt, active = calc.check_spirit_overflow(max_spirit)
if is_overflow:
    print(f"WARNING: Over-reserved by {overflow_amt}!")
    print(f"Active reservations: {active}")
```

### Manage Reservations

```python
# Toggle reservation on/off
calc.toggle_spirit_reservation("Raise Zombie")  # Disable
calc.toggle_spirit_reservation("Raise Zombie")  # Re-enable

# Remove reservation
calc.remove_spirit_reservation("Purity of Fire")

# Get detailed breakdown
details = calc.get_spirit_reservation_details()
for detail in details:
    print(f"{detail['name']}: {detail['base_cost']} → {detail['final_cost']}")
    print(f"  Multipliers: {detail['support_multipliers']}")
    print(f"  Status: {'Active' if detail['enabled'] else 'Disabled'}")
```

## Accuracy Calculation

```python
accuracy = calc.calculate_accuracy(
    flat_bonus=300,       # +300 accuracy from gear
    increased_percent=50  # 50% increased accuracy
)
print(f"Accuracy: {accuracy}")

# Calculate hit chance vs enemy evasion
from calculator.resource_calculator import calculate_hit_chance

hit_chance = calculate_hit_chance(
    attacker_accuracy=accuracy,
    defender_evasion=2000
)
print(f"Hit chance: {hit_chance}%")
```

**Formula**: `(6 × level) + (6 × dexterity) + flat → × (1 + increased%)`

## Attribute Bonuses

```python
bonuses = calc.get_attribute_bonuses()
print(f"Life from Strength: +{bonuses['life_from_strength']}")
print(f"Mana from Intelligence: +{bonuses['mana_from_intelligence']}")
print(f"Accuracy from Dexterity: +{bonuses['accuracy_from_dexterity']}")
```

**Bonuses**:
- Strength: +2 Life per point
- Dexterity: +6 Accuracy per point
- Intelligence: +2 Mana per point

## Resource Pools

```python
# Create a resource pool with automatic calculation
life_pool = calc.create_resource_pool(
    ResourceType.LIFE,
    modifiers=life_mods
)

print(f"Maximum: {life_pool.maximum}")
print(f"Current: {life_pool.current}")
print(f"Unreserved: {life_pool.unreserved_maximum}")

# Add reservations
life_pool.reserved_percent = 35  # 35% reserved for auras
print(f"Available: {life_pool.unreserved_maximum}")
```

## Complete Character Summary

```python
# Get all resources in one call
summary = calc.calculate_all_resources(
    life_mods=life_mods,
    mana_mods=mana_mods,
    es_mods=es_mods,
    spirit_mods=spirit_mods
)

# Access nested data
print(f"Life: {summary['resources']['life']['maximum']}")
print(f"Mana: {summary['resources']['mana']['maximum']}")
print(f"ES: {summary['resources']['energy_shield']['maximum']}")
print(f"Spirit: {summary['resources']['spirit']['maximum']}")
print(f"Spirit Available: {summary['resources']['spirit']['available']}")
print(f"Accuracy: {summary['accuracy']['rating']}")

# Check for Spirit problems
if summary['resources']['spirit']['is_overflowing']:
    print("WARNING: Spirit overflow!")
    overflow = summary['resources']['spirit']['overflow_amount']
    print(f"Need to free up {overflow} Spirit")
```

## Spirit System Details

### What is Spirit?
Spirit is a **new resource in Path of Exile 2** that replaces mana reservation for certain mechanics:

1. **Permanent Minions**: Zombies, Skeletons, Spectres, Golems, etc.
2. **Persistent Auras**: Some auras now use Spirit instead of mana
3. **Meta-Gems**: Special gems that provide persistent benefits

### How to Get More Spirit

1. **Quest Rewards**: Base 100 Spirit from storyline quests
2. **Gear**: Spirit rolls on items (similar to life/mana)
3. **Passive Tree**: Spirit nodes on the skill tree
4. **Increased Spirit %**: Very rare but powerful modifier

### Spirit vs Mana Reservation

| Aspect | Spirit | Mana Reservation |
|--------|--------|------------------|
| Base Amount | 100 (fixed) | Scales with level |
| Used For | Minions, some auras | Most auras, heralds |
| Calculation | Flat costs × multipliers | % or flat |
| Recovery | N/A (not spent) | Unreserve on disable |

### Common Spirit Costs (Examples)

- **Raise Zombie**: 20-30 Spirit
- **Summon Skeleton**: 15-25 Spirit
- **Summon Golem**: 25-35 Spirit
- **Auras (Spirit-based)**: 20-40 Spirit

*Note: Actual costs may vary based on gem level and game balance*

### Support Gem Multipliers

Support gems increase Spirit costs:
- **Minion Damage Support**: 1.3× multiplier
- **Minion Life Support**: 1.4× multiplier
- **Multiple supports stack multiplicatively**

Example:
```python
base_cost = 25
supports = [1.3, 1.4]  # Two supports
final_cost = 25 × 1.3 × 1.4 = 46 Spirit (rounded up)
```

## Error Handling

```python
from calculator.resource_calculator import AttributeStats, ResourceCalculator

# Validation errors
try:
    # Negative attributes not allowed
    bad_attrs = AttributeStats(strength=-10, dexterity=50, intelligence=50)
except ValueError as e:
    print(f"Error: {e}")

try:
    # Level must be 1-100
    bad_calc = ResourceCalculator(character_level=150, attributes=attributes)
except ValueError as e:
    print(f"Error: {e}")
```

## Best Practices

1. **Always check Spirit overflow** before committing to a build
2. **Use logging** to debug resource calculations
3. **Update reservations** when changing support gems
4. **Consider Spirit efficiency** when choosing support gems
5. **Plan Spirit budget** early in character planning

## Logging

```python
import logging

# Enable debug logging to see calculation details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now all calculations will be logged
calc = ResourceCalculator(50, attributes)
calc.calculate_maximum_life()  # Will log base, increased%, final
```

## Integration Example

```python
# Complete build planner integration
class BuildPlanner:
    def __init__(self, level: int, strength: int, dex: int, intel: int):
        attrs = AttributeStats(strength=strength, dexterity=dex, intelligence=intel)
        self.calc = ResourceCalculator(level, attrs)

    def add_minion(self, name: str, cost: int, supports: List[float]):
        self.calc.add_spirit_reservation(name, cost, supports)

    def validate_spirit(self, max_spirit: int) -> bool:
        overflow, amt, active = self.calc.check_spirit_overflow(max_spirit)
        if overflow:
            print(f"Cannot summon all minions! Over by {amt} Spirit")
            print(f"Active: {active}")
            return False
        return True

    def get_summary(self):
        return self.calc.calculate_all_resources()

# Usage
planner = BuildPlanner(level=70, strength=150, dex=100, intel=200)
planner.add_minion("Raise Zombie", 25, [1.5, 1.3])
planner.add_minion("Summon Skeleton", 20, [1.5])

if planner.validate_spirit(max_spirit=180):
    print("Build is valid!")
    summary = planner.get_summary()
```

## PoE2 vs PoE1 Differences

| Resource | PoE1 Formula | PoE2 Formula | Change |
|----------|--------------|--------------|--------|
| Life | 38 + 12×level | **28 + 12×level** | -10 base |
| Mana | 34 + 6×level | **34 + 4×level** | -2 per level |
| Spirit | N/A | **NEW: 100 + gear** | New mechanic |
| Accuracy | 2×level + 2×dex | **6×level + 6×dex** | 3× increase |

## Performance Notes

- All calculations are O(1) except Spirit reservations (O(n) where n = number of reservations)
- Spirit overflow check is cached-friendly
- Use `calculate_all_resources()` for batch calculations
- Logging can be disabled for production performance

## Testing

Run the built-in test suite:
```bash
python src/calculator/resource_calculator.py
```

This will run comprehensive tests and output detailed results.
