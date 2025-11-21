"""
Test script for .datc64 parser.

Tests the parser on simple .datc64 files with known structures.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers import Datc64Parser, ColumnSpec, DataType


def test_actiontypes():
    """
    Test parsing actiontypes.datc64.

    Based on analysis:
    - Row count: 910
    - Record length: 14 bytes
    - First row bytes: 08 00 00 00 00 00 00 00 41 4c 01 00 00 00

    Likely structure (14 bytes):
    - 8 bytes: unknown (could be ID or flags)
    - 6 bytes: ??? (not aligned to 8)

    Let's try: uint64 + uint32 + uint16
    """
    print("=" * 80)
    print("Testing actiontypes.datc64")
    print("=" * 80)

    data_dir = Path(__file__).parent.parent / "data" / "extracted" / "data"
    file_path = data_dir / "actiontypes.datc64"

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    parser = Datc64Parser()

    # First, just parse the header
    print("\nParsing header...")
    header = parser.parse_header(file_path)
    print(f"  Rows: {header['row_count']}")
    print(f"  Record length: {header['record_length']} bytes")
    print(f"  Data section size: {header['data_section_size']} bytes")

    # Try different column interpretations
    print("\n\nAttempt 1: uint64 + uint32 + uint16")
    try:
        columns = [
            ColumnSpec("unknown1", DataType.ULONG),   # 8 bytes
            ColumnSpec("unknown2", DataType.UINT),    # 4 bytes
            ColumnSpec("unknown3", DataType.USHORT),  # 2 bytes
        ]
        calc_len = parser.calculate_record_length(columns)
        print(f"  Calculated length: {calc_len} bytes (expected {header['record_length']})")

        if calc_len == header['record_length']:
            rows = parser.parse_file(file_path, columns)
            print(f"  Successfully parsed {len(rows)} rows")
            print(f"\n  First 5 rows:")
            for i, row in enumerate(rows[:5]):
                print(f"    Row {i}: {row}")
        else:
            print("  Length mismatch!")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n\nAttempt 2: uint64 + uint48 (as 6 bytes)")
    try:
        # 14 bytes could be: 8 + 6
        # Let's try reading as: uint64 + ubyte[6]
        columns = [
            ColumnSpec("unknown1", DataType.ULONG),  # 8 bytes
            ColumnSpec("unknown2", DataType.UBYTE),  # 1 byte
            ColumnSpec("unknown3", DataType.UBYTE),  # 1 byte
            ColumnSpec("unknown4", DataType.UBYTE),  # 1 byte
            ColumnSpec("unknown5", DataType.UBYTE),  # 1 byte
            ColumnSpec("unknown6", DataType.UBYTE),  # 1 byte
            ColumnSpec("unknown7", DataType.UBYTE),  # 1 byte
        ]
        calc_len = parser.calculate_record_length(columns)
        print(f"  Calculated length: {calc_len} bytes (expected {header['record_length']})")

        if calc_len == header['record_length']:
            rows = parser.parse_file(file_path, columns)
            print(f"  Successfully parsed {len(rows)} rows")
            print(f"\n  First 5 rows:")
            for i, row in enumerate(rows[:5]):
                # Format the bytes as hex
                byte_str = ' '.join(f"{row[f'unknown{j+2}']:02x}" for j in range(6))
                print(f"    Row {i}: unknown1={row['unknown1']}, bytes=[{byte_str}]")
        else:
            print("  Length mismatch!")
    except Exception as e:
        print(f"  Error: {e}")


def test_simple_string_table():
    """
    Create a simple test to verify string reading works.

    We'll manually test with actiontypes since we saw "GroundSlam" in the data.
    Record length 14 suggests: possibly a pointer (8) + something (6)
    """
    print("\n" + "=" * 80)
    print("Testing string pointer interpretation")
    print("=" * 80)

    data_dir = Path(__file__).parent.parent / "data" / "extracted" / "data"
    file_path = data_dir / "actiontypes.datc64"

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    parser = Datc64Parser()
    header = parser.parse_header(file_path)

    print("\nAttempt: STRING + uint32 + uint16")
    try:
        columns = [
            ColumnSpec("name", DataType.STRING),      # 8 bytes (pointer)
            ColumnSpec("unknown1", DataType.UINT),    # 4 bytes
            ColumnSpec("unknown2", DataType.USHORT),  # 2 bytes
        ]
        calc_len = parser.calculate_record_length(columns)
        print(f"  Calculated length: {calc_len} bytes (expected {header['record_length']})")

        if calc_len == header['record_length']:
            rows = parser.parse_file(file_path, columns)
            print(f"  Successfully parsed {len(rows)} rows")
            print(f"\n  First 10 rows:")
            for i, row in enumerate(rows[:10]):
                print(f"    Row {i}: name='{row['name']}', unknown1={row['unknown1']}, unknown2={row['unknown2']}")
        else:
            print("  Length mismatch!")
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main test runner."""
    print("DATC64 Parser Test Suite")
    print("=" * 80)
    print()

    test_actiontypes()
    test_simple_string_table()

    print("\n" + "=" * 80)
    print("Tests complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
