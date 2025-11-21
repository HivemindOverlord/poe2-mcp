"""
Test suite for .datc64 parser.
"""

import pytest
import struct
from pathlib import Path
from src.parsers import (
    Datc64Parser,
    ColumnSpec,
    DataType,
    DAT_MAGIC_NUMBER,
)


@pytest.fixture
def parser():
    """Create a parser instance."""
    return Datc64Parser()


@pytest.fixture
def sample_data_dir():
    """Get path to extracted game data."""
    return Path(__file__).parent.parent / "data" / "extracted" / "data"


class TestPrimitiveReaders:
    """Test primitive type reading functions."""

    def test_read_int32(self, parser):
        """Test int32 reading."""
        data = struct.pack('<i', -12345)
        value, offset = parser.read_int32(data, 0)
        assert value == -12345
        assert offset == 4

    def test_read_uint32(self, parser):
        """Test uint32 reading."""
        data = struct.pack('<I', 0xDEADBEEF)
        value, offset = parser.read_uint32(data, 0)
        assert value == 0xDEADBEEF
        assert offset == 4

    def test_read_int64(self, parser):
        """Test int64 reading."""
        data = struct.pack('<q', -9876543210)
        value, offset = parser.read_int64(data, 0)
        assert value == -9876543210
        assert offset == 8

    def test_read_uint64(self, parser):
        """Test uint64 reading."""
        data = struct.pack('<Q', 0x123456789ABCDEF0)
        value, offset = parser.read_uint64(data, 0)
        assert value == 0x123456789ABCDEF0
        assert offset == 8

    def test_read_bool(self, parser):
        """Test boolean reading."""
        # True
        data = struct.pack('<?', True)
        value, offset = parser.read_bool(data, 0)
        assert value is True
        assert offset == 1

        # False
        data = struct.pack('<?', False)
        value, offset = parser.read_bool(data, 0)
        assert value is False
        assert offset == 1

    def test_read_float(self, parser):
        """Test float reading."""
        data = struct.pack('<f', 3.14159)
        value, offset = parser.read_float(data, 0)
        assert pytest.approx(value, 0.0001) == 3.14159
        assert offset == 4

    def test_read_double(self, parser):
        """Test double reading."""
        data = struct.pack('<d', 2.718281828459045)
        value, offset = parser.read_double(data, 0)
        assert pytest.approx(value, 0.00000001) == 2.718281828459045
        assert offset == 8

    def test_read_string(self, parser):
        """Test UTF-16 string reading."""
        # Create a UTF-16 LE string with null terminator
        test_string = "Act1"
        data = test_string.encode('utf-16-le') + b'\x00\x00\x00\x00'

        value, size = parser.read_string(data, 0)
        assert value == test_string
        assert size == len(test_string) * 2 + 4  # UTF-16 + null terminator

    def test_read_string_empty(self, parser):
        """Test reading empty string."""
        data = b'\x00\x00\x00\x00'
        value, size = parser.read_string(data, 0)
        assert value == ''
        assert size == 4

    def test_read_string_with_spaces(self, parser):
        """Test reading string with spaces and special chars."""
        test_string = "Something dark awaits"
        data = test_string.encode('utf-16-le') + b'\x00\x00\x00\x00'

        value, size = parser.read_string(data, 0)
        assert value == test_string


class TestHeaderParsing:
    """Test header parsing functionality."""

    def test_parse_header_acts(self, parser, sample_data_dir):
        """Test parsing acts.datc64 header."""
        file_path = sample_data_dir / "acts.datc64"

        if not file_path.exists():
            pytest.skip(f"Test file not found: {file_path}")

        header = parser.parse_header(file_path)

        assert header['row_count'] == 7
        assert header['table_offset'] == 4
        assert header['record_length'] == 149
        assert header['magic_offset'] > 0
        assert header['data_section_offset'] == header['magic_offset'] + 8
        assert header['file_size'] > 0

    def test_parse_header_actiontypes(self, parser, sample_data_dir):
        """Test parsing actiontypes.datc64 header."""
        file_path = sample_data_dir / "actiontypes.datc64"

        if not file_path.exists():
            pytest.skip(f"Test file not found: {file_path}")

        header = parser.parse_header(file_path)

        assert header['row_count'] == 910
        assert header['record_length'] == 14
        assert header['magic_offset'] > 0

    def test_magic_number_missing(self, parser, tmp_path):
        """Test that missing magic number raises error."""
        # Create a file without magic number
        test_file = tmp_path / "no_magic.datc64"
        with open(test_file, 'wb') as f:
            f.write(struct.pack('<I', 5))  # Row count
            f.write(b'\x00' * 100)  # Some data without magic

        with pytest.raises(ValueError, match="Magic number not found"):
            parser.parse_header(test_file)


class TestColumnCalculation:
    """Test column length calculation."""

    def test_calculate_simple_columns(self, parser):
        """Test calculating length for simple column types."""
        columns = [
            ColumnSpec("id", DataType.ULONG),      # 8
            ColumnSpec("value", DataType.INT),      # 4
            ColumnSpec("flag", DataType.BOOL),      # 1
        ]
        length = parser.calculate_record_length(columns)
        assert length == 8 + 4 + 1

    def test_calculate_with_pointers(self, parser):
        """Test calculating length with pointer types."""
        columns = [
            ColumnSpec("name", DataType.STRING),          # 8 (pointer)
            ColumnSpec("list", DataType.POINTER_LIST),    # 16 (count + offset)
            ColumnSpec("ptr", DataType.POINTER),          # 8 (pointer)
        ]
        length = parser.calculate_record_length(columns)
        assert length == 8 + 16 + 8


class TestFileParsing:
    """Test full file parsing with column specifications."""

    def test_parse_simple_structure(self, parser, sample_data_dir):
        """Test parsing a file with known structure."""
        file_path = sample_data_dir / "actiontypes.datc64"

        if not file_path.exists():
            pytest.skip(f"Test file not found: {file_path}")

        # actiontypes.datc64 has 14-byte records
        columns = [
            ColumnSpec("field1", DataType.ULONG),    # 8
            ColumnSpec("field2", DataType.UINT),     # 4
            ColumnSpec("field3", DataType.USHORT),   # 2
        ]

        rows = parser.parse_file(file_path, columns)

        assert len(rows) == 910
        assert all('field1' in row for row in rows)
        assert all('field2' in row for row in rows)
        assert all('field3' in row for row in rows)

    def test_parse_with_mismatched_columns(self, parser, sample_data_dir):
        """Test that mismatched column specs raise error."""
        file_path = sample_data_dir / "acts.datc64"

        if not file_path.exists():
            pytest.skip(f"Test file not found: {file_path}")

        # acts.datc64 has 149-byte records, this only adds up to 12
        columns = [
            ColumnSpec("field1", DataType.ULONG),    # 8
            ColumnSpec("field2", DataType.UINT),     # 4
        ]

        with pytest.raises(ValueError, match="don't match record length"):
            parser.parse_file(file_path, columns)

    def test_parse_acts_partial(self, parser, sample_data_dir):
        """Test parsing acts.datc64 with partial column spec."""
        file_path = sample_data_dir / "acts.datc64"

        if not file_path.exists():
            pytest.skip(f"Test file not found: {file_path}")

        # Build column spec to match 149 bytes
        columns = [ColumnSpec("list_field", DataType.POINTER_LIST)]  # 16 bytes

        # Pad with ulongs
        remaining = 149 - 16
        for i in range(remaining // 8):
            columns.append(ColumnSpec(f"unknown{i}", DataType.ULONG))

        # Handle remainder
        remainder = remaining % 8
        if remainder >= 4:
            columns.append(ColumnSpec("unknown_uint", DataType.UINT))
            remainder -= 4
        if remainder >= 2:
            columns.append(ColumnSpec("unknown_ushort", DataType.USHORT))
            remainder -= 2
        if remainder >= 1:
            columns.append(ColumnSpec("unknown_ubyte", DataType.UBYTE))

        rows = parser.parse_file(file_path, columns)

        assert len(rows) == 7
        # First row should have list pointer (8, 20) based on analysis
        assert rows[0]['list_field'] == (8, 20)


class TestStringParsing:
    """Test string parsing in real files."""

    def test_read_act1_string(self, parser, sample_data_dir):
        """Test reading 'Act1' string from acts.datc64."""
        file_path = sample_data_dir / "acts.datc64"

        if not file_path.exists():
            pytest.skip(f"Test file not found: {file_path}")

        header = parser.parse_header(file_path)

        with open(file_path, 'rb') as f:
            data = f.read()

        data_section = data[header['data_section_offset']:]

        # String at offset 0 should be "Act1"
        string, size = parser.read_string(data_section, 0)
        assert string == "Act1"

    def test_null_string_pointer(self, parser):
        """Test that null pointer returns None for strings."""
        data = struct.pack('<Q', 0)  # Null pointer
        value, offset = parser.read_value(
            data, 0, DataType.STRING,
            data_section=b''
        )
        assert value is None
        assert offset == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
