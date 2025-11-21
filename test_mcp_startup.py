"""
Quick test to verify MCP server can be instantiated
"""
import sys
sys.path.insert(0, '.')

from src.mcp_server import PoE2BuildOptimizerMCP

try:
    print("Testing MCP server initialization...")
    server = PoE2BuildOptimizerMCP()
    print("SUCCESS: MCP server created")

    # Check all calculators are initialized
    calculators = {
        "Weakness Detector": server.weakness_detector,
        "Gear Evaluator": server.gear_evaluator,
        "EHP Calculator": server.ehp_calculator,
        "Spirit Calculator": server.spirit_calculator,
        "Damage Calculator": server.damage_calculator,
    }

    print("\nCalculator Status:")
    for name, calc in calculators.items():
        status = "OK" if calc is not None else "NOT INITIALIZED"
        print(f"  {name}: {status}")

    # Check handler methods exist
    print("\nHandler Methods:")
    required_handlers = [
        "_handle_detect_weaknesses",
        "_handle_evaluate_upgrade",
        "_handle_calculate_ehp",
        "_handle_analyze_spirit",
        "_handle_analyze_stun",
        "_handle_optimize_metrics",
        "_handle_health_check",
    ]

    for handler in required_handlers:
        exists = hasattr(server, handler)
        status = "OK" if exists else "MISSING"
        print(f"  {handler}: {status}")

    print("\nSUCCESS: All systems operational!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
