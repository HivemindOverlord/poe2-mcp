"""
.datc64 Binary Format Analysis Tool

Analyzes Path of Exile 2 .datc64 files to reverse engineer the binary format.
"""

import struct
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

DAT_MAGIC_NUMBER = b'\xBB\xbb\xBB\xbb\xBB\xbb\xBB\xbb'


def hexdump(data: bytes, offset: int = 0, length: int = 256, width: int = 16) -> str:
    """
    Create a hexdump view of binary data.

    Args:
        data: Binary data to dump
        offset: Starting offset
        length: Number of bytes to dump
        width: Bytes per line

    Returns:
        Formatted hexdump string
    """
    lines = []
    end = min(offset + length, len(data))

    for i in range(offset, end, width):
        # Offset
        line = f"{i:08x}  "

        # Hex bytes
        hex_part = ""
        ascii_part = ""
        for j in range(width):
            if i + j < end:
                byte = data[i + j]
                hex_part += f"{byte:02x} "
                ascii_part += chr(byte) if 32 <= byte < 127 else "."
            else:
                hex_part += "   "

        line += hex_part + " |" + ascii_part + "|"
        lines.append(line)

    return "\n".join(lines)


def analyze_header(file_path: Path) -> dict:
    """
    Analyze the header of a .datc64 file.

    Based on PyPoE's .dat format:
    - First 4 bytes: row count (uint32 little-endian)
    - Magic number somewhere in file marks data section start
    """
    with open(file_path, 'rb') as f:
        data = f.read()

    file_size = len(data)

    # Read row count
    row_count = struct.unpack('<I', data[0:4])[0]

    # Find magic number
    magic_offset = data.find(DAT_MAGIC_NUMBER)

    if magic_offset == -1:
        # No magic number found - might be different format
        magic_offset = None
        table_length = None
        record_length = None
        data_section_size = None
    else:
        table_length = magic_offset - 4  # Subtract header
        record_length = table_length // row_count if row_count > 0 else 0
        data_section_size = file_size - magic_offset - 8  # Subtract magic number

    return {
        'file_path': str(file_path),
        'file_size': file_size,
        'row_count': row_count,
        'magic_offset': magic_offset,
        'table_offset': 4,
        'table_length': table_length,
        'record_length': record_length,
        'data_section_offset': magic_offset + 8 if magic_offset else None,
        'data_section_size': data_section_size,
    }


def detect_patterns(file_path: Path, info: dict) -> dict:
    """
    Detect patterns in the file structure.
    """
    with open(file_path, 'rb') as f:
        data = f.read()

    patterns = {}

    # Check if there's data before magic number (table section)
    if info['magic_offset']:
        table_data = data[4:info['magic_offset']]

        # Look for common null patterns
        patterns['null_patterns'] = []
        for pattern in [b'\xFE\xFE\xFE\xFE', b'\x00\x00\x00\x00', b'\xFF\xFF\xFF\xFF']:
            count = table_data.count(pattern)
            if count > 0:
                patterns['null_patterns'].append({
                    'pattern': pattern.hex(),
                    'count': count
                })

        # Check for potential string pointers (offsets into data section)
        if info['record_length'] and info['record_length'] >= 4:
            # Sample first row
            first_row = table_data[0:info['record_length']]
            patterns['first_row_hex'] = first_row.hex()

    return patterns


def infer_column_types(file_path: Path, info: dict) -> None:
    """
    Attempt to infer column types by analyzing the first few rows.
    """
    if not info['magic_offset'] or not info['record_length']:
        print("\n  Cannot infer columns without valid table structure")
        return

    with open(file_path, 'rb') as f:
        data = f.read()

    data_section_start = info['data_section_offset']
    table_data = data[4:info['magic_offset']]
    data_section = data[data_section_start:]

    print(f"\nColumn Type Inference (Record length: {info['record_length']} bytes):")

    # Analyze first row in detail
    first_row = table_data[0:info['record_length']]

    # Try to identify columns by looking at 8-byte chunks (64-bit pointers)
    offset = 0
    col_num = 0

    while offset < info['record_length']:
        # Try reading as 64-bit values
        if offset + 8 <= info['record_length']:
            val_u64 = struct.unpack('<Q', first_row[offset:offset+8])[0]
            val_i64 = struct.unpack('<q', first_row[offset:offset+8])[0]

            # Check if it could be a pointer into data section
            is_pointer = (0 < val_u64 < info['data_section_size'])

            # Check if null
            is_null = val_u64 in (0, 0xFEFEFEFEFEFEFEFE, 0xA6, 0xA600000000000000)

            print(f"\n  Col {col_num} @ offset {offset}:")
            print(f"    u64: {val_u64} (0x{val_u64:016x})")

            if is_pointer and offset + 16 <= info['record_length']:
                # Could be part of a list pointer (count, offset)
                next_val = struct.unpack('<Q', first_row[offset+8:offset+16])[0]
                if 0 < next_val < info['data_section_size']:
                    print(f"    Likely: List pointer (count={val_u64}, offset={next_val})")

                    # Try to read from data section
                    if next_val + val_u64 * 8 <= info['data_section_size']:
                        print(f"      Data section read:")
                        sample = data_section[next_val:next_val + min(64, val_u64 * 8)]
                        print(f"      {sample.hex()[:128]}")
                    offset += 8  # Advance past both values
                    col_num += 1
                    continue

            if is_pointer:
                # Could be string pointer
                try:
                    # Try reading UTF-16 string from data section
                    string_offset = val_u64
                    end_offset = data_section.find(b'\x00\x00\x00\x00', string_offset)
                    if end_offset != -1 and end_offset - string_offset < 1000:
                        string_data = data_section[string_offset:end_offset]
                        if len(string_data) % 2 == 0:
                            try:
                                decoded = string_data.decode('utf-16-le')
                                if decoded.isprintable() or any(c in decoded for c in '\n\r\t '):
                                    print(f"    Likely: String pointer -> '{decoded[:50]}'")
                                else:
                                    print(f"    Possibly: Data pointer (offset={val_u64})")
                            except:
                                print(f"    Possibly: Data pointer (offset={val_u64})")
                        else:
                            print(f"    Possibly: Data pointer (offset={val_u64})")
                    else:
                        print(f"    Possibly: Data pointer (offset={val_u64})")
                except:
                    print(f"    Possibly: Data pointer (offset={val_u64})")

            elif is_null:
                print(f"    Likely: Null value (special pattern)")

            else:
                # Check as uint32 values
                val_u32_1 = struct.unpack('<I', first_row[offset:offset+4])[0]
                val_u32_2 = struct.unpack('<I', first_row[offset+4:offset+8])[0]
                print(f"    u32[0]: {val_u32_1}, u32[1]: {val_u32_2}")
                print(f"    Likely: Integer value")

        offset += 8
        col_num += 1


def compare_files(files: list[Path]) -> None:
    """
    Compare multiple .datc64 files to find common patterns.
    """
    print("=" * 80)
    print("DATC64 FORMAT ANALYSIS")
    print("=" * 80)
    print()

    for file_path in files:
        print(f"\n{'=' * 80}")
        print(f"File: {file_path.name}")
        print(f"{'=' * 80}")

        info = analyze_header(file_path)

        print(f"\nHeader Information:")
        print(f"  File size:           {info['file_size']:,} bytes")
        print(f"  Row count:           {info['row_count']}")
        print(f"  Magic number offset: {info['magic_offset']} (0x{info['magic_offset']:x})" if info['magic_offset'] else "  Magic number offset: NOT FOUND")

        if info['magic_offset']:
            print(f"  Table offset:        {info['table_offset']}")
            print(f"  Table length:        {info['table_length']} bytes")
            print(f"  Record length:       {info['record_length']} bytes")
            print(f"  Data section offset: {info['data_section_offset']}")
            print(f"  Data section size:   {info['data_section_size']} bytes")

        # Read file for hex dumps
        with open(file_path, 'rb') as f:
            data = f.read()

        print(f"\nFirst 256 bytes (header + table start):")
        print(hexdump(data, 0, 256))

        if info['magic_offset'] and info['data_section_offset']:
            print(f"\nMagic number region:")
            magic_start = max(0, info['magic_offset'] - 32)
            print(hexdump(data, magic_start, 64))

            print(f"\nData section start:")
            print(hexdump(data, info['data_section_offset'], 128))

        # Pattern detection
        patterns = detect_patterns(file_path, info)
        if patterns:
            print(f"\nPattern Detection:")
            if 'null_patterns' in patterns and patterns['null_patterns']:
                print("  Null patterns found:")
                for p in patterns['null_patterns']:
                    print(f"    {p['pattern']}: {p['count']} occurrences")

            if 'first_row_hex' in patterns:
                print(f"\n  First row (hex):")
                first_row_hex = patterns['first_row_hex']
                # Print in chunks of 32 chars (16 bytes)
                for i in range(0, len(first_row_hex), 32):
                    chunk = first_row_hex[i:i+32]
                    # Add spaces between bytes
                    spaced = ' '.join(chunk[j:j+2] for j in range(0, len(chunk), 2))
                    print(f"    {spaced}")

        # Column type inference
        infer_column_types(file_path, info)

        print()


def main():
    """Main entry point."""
    data_dir = Path(__file__).parent.parent / "data" / "extracted" / "data"

    # Analyze simple files first
    test_files = [
        "acts.datc64",
        "actiontypes.datc64",
        "achievements.datc64",
    ]

    files_to_analyze = []
    for filename in test_files:
        file_path = data_dir / filename
        if file_path.exists():
            files_to_analyze.append(file_path)
        else:
            print(f"Warning: {filename} not found")

    if not files_to_analyze:
        print("No files found to analyze!")
        return

    compare_files(files_to_analyze)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
