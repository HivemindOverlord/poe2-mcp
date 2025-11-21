# Spirit System Quick Reference (PoE2)

## What is Spirit?

**Spirit** is a NEW resource in Path of Exile 2 that limits permanent summons and auras.

```
Think of Spirit as "minion/aura slots" - each permanent effect costs Spirit
```

## Key Differences from Mana Reservation

| Aspect | Spirit (NEW) | Mana Reservation (Old) |
|--------|--------------|------------------------|
| Base Amount | 100 (from quests) | Scales with level |
| Used For | Minions, some auras | Most auras, heralds |
| Scaling | Very hard | Easy (gear, passives) |
| Mechanic | Flat costs | % or flat reservation |

## Formula

```python
# Maximum Spirit
Max_Spirit = 100 (base) + flat_from_gear + flat_from_passives
Final_Spirit = Max_Spirit × (1 + increased%)

# Spirit Cost (per minion/aura)
Cost = base_cost × support_multiplier_1 × support_multiplier_2 × ...
# Always rounded UP

# Available Spirit
Available = Maximum - sum(all_costs)
```

## Example Calculation

```python
# Character has:
Max_Spirit = 100 (base) + 50 (gear) + 30 (passives) = 180

# Summons:
Raise_Zombie = 25 × 1.5 (support) = 38 Spirit
Skeleton = 20 × 1.4 × 1.3 (2 supports) = 37 Spirit
Golem = 30 (no support) = 30 Spirit

# Total
Reserved = 38 + 37 + 30 = 105
Available = 180 - 105 = 75 Spirit ✓ OK
```

## Code Usage

### Basic Setup
```python
from calculator.resource_calculator import ResourceCalculator, AttributeStats

calc = ResourceCalculator(level=70, attributes=AttributeStats(150, 100, 120))
max_spirit = calc.calculate_maximum_spirit()  # 100
```

### Add Reservations
```python
# Add a minion with 1 support
calc.add_spirit_reservation(
    name="Raise Zombie",
    base_cost=25,
    support_multipliers=[1.5]  # Minion Damage Support
)

# Add minion with multiple supports
calc.add_spirit_reservation(
    name="Summon Skeleton",
    base_cost=20,
    support_multipliers=[1.4, 1.3]  # Two supports
)

# Add aura (no supports)
calc.add_spirit_reservation(
    name="Purity of Fire",
    base_cost=30
)
```

### Check Status
```python
# How much Spirit is reserved?
reserved = calc.calculate_spirit_reserved()

# How much is available?
available = calc.calculate_spirit_available(max_spirit)

# Am I over-reserved?
is_overflow, overflow_amt, active = calc.check_spirit_overflow(max_spirit)

if is_overflow:
    print(f"ERROR: Over by {overflow_amt} Spirit!")
    print(f"Active: {active}")
```

### Manage Reservations
```python
# Disable a minion temporarily
calc.toggle_spirit_reservation("Raise Zombie")

# Remove completely
calc.remove_spirit_reservation("Purity of Fire")

# Get detailed breakdown
details = calc.get_spirit_reservation_details()
for d in details:
    print(f"{d['name']}: {d['base_cost']} → {d['final_cost']}")
```

## Common Patterns

### Pattern 1: Validate Build
```python
def validate_necromancer_build(calc, max_spirit):
    # Add all planned summons
    calc.add_spirit_reservation("Zombie", 25, [1.5])
    calc.add_spirit_reservation("Skeleton", 20, [1.4, 1.3])
    calc.add_spirit_reservation("Golem", 30)

    # Check if valid
    overflow, amt, _ = calc.check_spirit_overflow(max_spirit)
    if overflow:
        print(f"Build invalid! Need {amt} more Spirit")
        return False
    return True
```

### Pattern 2: Optimize Supports
```python
def optimize_supports(base_cost, max_budget, supports):
    """Find which supports fit in budget."""
    costs = []
    for num_supports in range(len(supports) + 1):
        cost = base_cost
        for mult in supports[:num_supports]:
            cost *= mult
        costs.append(int(cost + 0.999999))

    # Find max supports that fit
    for i in range(len(costs) - 1, -1, -1):
        if costs[i] <= max_budget:
            return i, costs[i]
    return 0, base_cost
```

### Pattern 3: Calculate Budget
```python
def calculate_spirit_budget(max_spirit, required_reservations):
    """Calculate remaining Spirit for optional summons."""
    required_total = sum(r.calculate_cost() for r in required_reservations)
    remaining = max_spirit - required_total

    print(f"Required: {required_total}/{max_spirit}")
    print(f"Budget for optional: {remaining}")

    return remaining
```

## Support Multipliers Reference

### Common Support Gems (Examples)
- **Minion Damage**: 1.3×
- **Minion Life**: 1.4×
- **Minion Speed**: 1.25×
- **Elemental Damage with Minions**: 1.35×
- **Feeding Frenzy**: 1.4×

### Stacking Calculation
```python
# Example: Zombie with 3 supports
base = 25
supports = [1.3, 1.4, 1.25]  # Damage, Life, Speed

final = 25 × 1.3 × 1.4 × 1.25
     = 25 × 2.275
     = 56.875
     = 57 Spirit (rounded up)
```

## Spirit Sources

### Quest Rewards
```
Base: 100 Spirit (from completing campaign quests)
```

### Gear Affixes
```
Prefix: +15 to Maximum Spirit
Suffix: 8% increased Maximum Spirit (RARE!)

Example: Ring with +15 Spirit → +15 max
Example: Amulet with +20 Spirit, 5% increased → +20 × 1.05 = +21 max
```

### Passive Tree
```
Notable: +10 Spirit
Notable: +15 Spirit
Notable: 10% increased Spirit (RARE!)
```

### Calculation with All Sources
```python
from calculator.resource_calculator import ResourceModifiers

spirit_mods = ResourceModifiers(
    flat_bonus=80,        # +80 from gear and passives
    increased_percent=15  # 15% increased (very rare!)
)

max_spirit = calc.calculate_maximum_spirit(spirit_mods)
# = (100 + 80) × 1.15
# = 180 × 1.15
# = 207 Spirit
```

## Troubleshooting

### Problem: Spirit Overflow
```python
# Symptom
overflow, amt, active = calc.check_spirit_overflow(max_spirit)
# overflow=True, amt=25

# Solutions:
1. Get more Spirit from gear/passives
2. Remove support gems from minions
3. Unsummon one minion
4. Use lower-cost alternatives
```

### Problem: Not Enough Summons
```python
# Symptom
max_spirit = 100
reserved = 30  # Only one minion
available = 70  # But can't fit another 25-cost minion with supports

# Solution:
# Calculate actual cost with supports first
test_reservation = SpiritReservation("Test", 25, [1.5, 1.4])
actual_cost = test_reservation.calculate_cost()  # 53
# Won't fit! Need to remove a support or get more Spirit
```

### Problem: Wrong Support Multipliers
```python
# WRONG: Using additive
cost = 25 × (1.3 + 1.4)  # NO!

# CORRECT: Multiplicative
cost = 25 × 1.3 × 1.4  # YES!
```

## Integration Examples

### With Build Planner
```python
class NecromancerBuild:
    def __init__(self, level, strength, dex, intel):
        attrs = AttributeStats(strength, dex, intel)
        self.calc = ResourceCalculator(level, attrs)

    def plan_minions(self, spirit_from_gear):
        spirit_mods = ResourceModifiers(flat_bonus=spirit_from_gear)
        self.max_spirit = self.calc.calculate_maximum_spirit(spirit_mods)

        # Add planned minions
        self.calc.add_spirit_reservation("Zombie", 25, [1.5])
        self.calc.add_spirit_reservation("Skeleton", 20, [1.4, 1.3])

        # Validate
        return not self.calc.check_spirit_overflow(self.max_spirit)[0]
```

### With Gear Optimizer
```python
def find_required_spirit_on_gear(reservations, base_spirit=100):
    """Calculate how much +Spirit needed from gear."""
    total_cost = sum(r.calculate_cost() for r in reservations)
    required = total_cost - base_spirit

    if required <= 0:
        return 0, "No gear Spirit needed"

    # Assume avg +15 Spirit per item
    items_needed = (required + 14) // 15

    return required, f"Need {required} Spirit ({items_needed} items @ +15 each)"
```

## Best Practices

### 1. Plan Before You Build
```python
# Calculate costs BEFORE equipping
for minion in planned_minions:
    cost = calculate_with_supports(minion)
    print(f"{minion}: {cost} Spirit")

total = sum(costs)
print(f"Total needed: {total}")
```

### 2. Track Support Multipliers
```python
# Keep a reference of your support gems
support_setup = {
    'Zombie': [1.5, 1.3],      # Damage, Life
    'Skeleton': [1.4, 1.3],     # Life, Speed
    'Golem': []                 # No supports
}

# Use consistently
for name, base_cost in minions.items():
    calc.add_spirit_reservation(name, base_cost, support_setup[name])
```

### 3. Leave Buffer Room
```python
# Don't use 100% of Spirit
max_spirit = 180
safety_buffer = 20

usable_spirit = max_spirit - safety_buffer  # 160
# Now plan with 160, not 180
```

### 4. Test Incrementally
```python
# Add reservations one at a time
calc.add_spirit_reservation("Zombie", 25, [1.5])
print(f"Available: {calc.calculate_spirit_available(max_spirit)}")

calc.add_spirit_reservation("Skeleton", 20, [1.4, 1.3])
print(f"Available: {calc.calculate_spirit_available(max_spirit)}")

# If overflow, back out last addition
if calc.check_spirit_overflow(max_spirit)[0]:
    calc.remove_spirit_reservation("Skeleton")
```

## FAQ

**Q: Can Spirit go negative?**
A: Technically yes (overflow), but you can't summon if you don't have enough Spirit.

**Q: Does increased% Spirit work like increased% life?**
A: Yes! It's additive and calculated the same way.

**Q: Do support multipliers round?**
A: Final cost rounds UP to nearest integer.

**Q: Can I unreserve Spirit?**
A: Yes, unsummon the minion or disable the aura.

**Q: Is there a Spirit reservation efficiency stat?**
A: Not in base PoE2 (unlike mana reservation efficiency in PoE1).

**Q: What happens if I remove a support gem?**
A: Spirit cost decreases immediately. Recalculate with new multipliers.

## Cheat Sheet

```python
# QUICK REFERENCE

# Create calculator
calc = ResourceCalculator(level, AttributeStats(str, dex, int))

# Get max Spirit
max_spirit = calc.calculate_maximum_spirit(mods)

# Add reservation
calc.add_spirit_reservation(name, base_cost, [mult1, mult2])

# Check status
reserved = calc.calculate_spirit_reserved()
available = calc.calculate_spirit_available(max_spirit)
overflow, amt, active = calc.check_spirit_overflow(max_spirit)

# Manage
calc.toggle_spirit_reservation(name)    # On/off
calc.remove_spirit_reservation(name)    # Delete
calc.get_spirit_reservation_details()   # Details

# Cost calculation
cost = base × mult1 × mult2 × mult3
final_cost = int(cost + 0.999999)  # Round up
```

---

**Remember**: Spirit is about making CHOICES. You can't have everything!
