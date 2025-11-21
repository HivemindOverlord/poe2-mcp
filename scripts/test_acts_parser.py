"""
Test parser on acts.datc64 - a simpler file with confirmed strings.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers import Datc64Parser, ColumnSpec, DataType


def test_acts():
    """
    Test parsing acts.datc64.

    From earlier analysis:
    - 7 rows
    - Record length: 149 bytes
    - First row hex (partial):
      08 00 00 00 00 00 00 00 14 00 00 00 00 00 00 00
      01 00 00 00 14 00 00 00 00 00 00 00 14 00 00 00
      ...

    Column 0+1 was identified as: List pointer (count=8, offset=20)
    Data at offset 0 in data section: "Act1" (UTF-16: 41 00 63 00 74 00 31 00)

    Let's try to parse just the beginning.
    """
    print("=" * 80)
    print("Testing acts.datc64")
    print("=" * 80)

    data_dir = Path(__file__).parent.parent / "data" / "extracted" / "data"
    file_path = data_dir / "acts.datc64"

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    parser = Datc64Parser()
    header = parser.parse_header(file_path)

    print(f"\nHeader info:")
    print(f"  Rows: {header['row_count']}")
    print(f"  Record length: {header['record_length']} bytes")
    print(f"  Data section size: {header['data_section_size']} bytes")

    # From analysis: first field is a list pointer (count=8, offset=20)
    # Let's try parsing first few fields
    print("\n\nAttempt 1: POINTER_LIST + ... (just test the list)")
    try:
        # Just parse the first column to test
        columns = [
            ColumnSpec("list_field", DataType.POINTER_LIST),  # 16 bytes (count + offset)
        ]
        # We need to pad to 149 bytes somehow - let's add filler columns
        remaining = 149 - 16
        # Add as ulongs (8 bytes each)
        for i in range(remaining // 8):
            columns.append(ColumnSpec(f"unknown{i}", DataType.ULONG))

        # Handle remainder
        remainder = remaining % 8
        if remainder >= 4:
            columns.append(ColumnSpec(f"unknown_uint", DataType.UINT))
            remainder -= 4
        if remainder >= 2:
            columns.append(ColumnSpec(f"unknown_ushort", DataType.USHORT))
            remainder -= 2
        if remainder >= 1:
            columns.append(ColumnSpec(f"unknown_ubyte", DataType.UBYTE))

        calc_len = parser.calculate_record_length(columns)
        print(f"  Calculated length: {calc_len} bytes (expected {header['record_length']})")

        if calc_len == header['record_length']:
            rows = parser.parse_file(file_path, columns)
            print(f"  Successfully parsed {len(rows)} rows")
            print(f"\n  First row list field: {rows[0]['list_field']}")
            print(f"    (count, offset) = {rows[0]['list_field']}")
        else:
            print(f"  Length mismatch! Got {calc_len}, expected {header['record_length']}")

    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()

    # Now let's try to read the string at offset 0
    print("\n\nManual string reading test:")
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        data_section = data[header['data_section_offset']:]
        print(f"  Data section starts at offset {header['data_section_offset']}")
        print(f"  First 64 bytes (hex): {data_section[:64].hex()}")

        # Try reading string at offset 0
        string, size = parser.read_string(data_section, 0)
        print(f"\n  String at offset 0: '{string}' (size: {size} bytes)")

        # Try reading string at offset 20 (from list pointer)
        string, size = parser.read_string(data_section, 20)
        print(f"  String at offset 20: '{string}' (size: {size} bytes)")

    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_acts()
