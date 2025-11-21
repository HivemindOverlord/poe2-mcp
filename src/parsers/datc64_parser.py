"""
Path of Exile 2 .datc64 Binary Format Parser

Based on reverse engineering and analysis of PyPoE's .dat parser.
Adapted for PoE2's .datc64 format (64-bit variant).
"""

import struct
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any, BinaryIO, List, Optional, Tuple, Union


# Magic number that separates table data from variable-length data section
DAT_MAGIC_NUMBER = b'\xBB\xbb\xBB\xbb\xBB\xbb\xBB\xbb'


# Special null value patterns in PoE dat files
NULL_VALUES_64BIT = {
    0xFEFEFEFEFEFEFEFE,  # 64-bit FEFE pattern
    0xFEFEFEFE,          # 32-bit FEFE pattern (in 64-bit field)
    0xFFFFFFFF,          # 32-bit all F's
    0xFFFFFFFFFFFFFFFF,  # 64-bit all F's
    0xA6,                # Seen in achievements.datc64
    0xA600000000000000,  # Extended A6 pattern
}


class DataType(IntEnum):
    """Data type identifiers for .datc64 columns."""
    # Primitive value types (stored in table section)
    BOOL = 1
    BYTE = 2
    UBYTE = 3
    SHORT = 4
    USHORT = 5
    INT = 6
    UINT = 7
    LONG = 8
    ULONG = 9
    FLOAT = 10
    DOUBLE = 11

    # Pointer types (point to data section)
    STRING = 20          # ref|string - pointer to UTF-16 string in data section
    POINTER = 21         # ref|X - pointer to single value in data section
    POINTER_LIST = 22    # ref|list|X - pointer to list (count, offset)


@dataclass
class ColumnSpec:
    """
    Specification for a single column in a .datc64 table.

    This is required because .datc64 files don't contain column type information
    in their headers - types must be known in advance or reverse-engineered.
    """
    name: str
    data_type: DataType
    # For POINTER_LIST, specifies the type of list elements
    element_type: Optional[DataType] = None


@dataclass
class ParsedValue:
    """
    A parsed value from the .datc64 file.

    Tracks both the value and metadata about where it came from.
    """
    value: Any
    offset: int
    size: int
    data_type: DataType


class Datc64Parser:
    """
    Parser for Path of Exile 2 .datc64 binary format.

    .datc64 files are structured as:
    1. Header (4 bytes): row count (uint32 little-endian)
    2. Table section: fixed-width rows
    3. Magic number: \\xBB\\xbb\\xBB\\xbb\\xBB\\xbb\\xBB\\xbb
    4. Data section: variable-length data (strings, lists, etc.)

    The table section contains fixed-width rows with primitive types and pointers.
    Pointers reference offsets in the data section.

    Example:
        parser = Datc64Parser()
        header = parser.parse_header(file_path)
        print(f"File has {header['row_count']} rows")

        # With column specifications
        columns = [
            ColumnSpec("id", DataType.ULONG),
            ColumnSpec("name", DataType.STRING),
        ]
        rows = parser.parse_file(file_path, columns)
    """

    # Size in bytes for each primitive type
    TYPE_SIZES = {
        DataType.BOOL: 1,
        DataType.BYTE: 1,
        DataType.UBYTE: 1,
        DataType.SHORT: 2,
        DataType.USHORT: 2,
        DataType.INT: 4,
        DataType.UINT: 4,
        DataType.LONG: 8,
        DataType.ULONG: 8,
        DataType.FLOAT: 4,
        DataType.DOUBLE: 8,
        DataType.STRING: 8,      # Pointer (64-bit offset)
        DataType.POINTER: 8,     # Pointer (64-bit offset)
        DataType.POINTER_LIST: 16,  # Count (64-bit) + Offset (64-bit)
    }

    # Struct format strings for unpacking
    TYPE_FORMATS = {
        DataType.BOOL: '?',
        DataType.BYTE: 'b',
        DataType.UBYTE: 'B',
        DataType.SHORT: 'h',
        DataType.USHORT: 'H',
        DataType.INT: 'i',
        DataType.UINT: 'I',
        DataType.LONG: 'q',
        DataType.ULONG: 'Q',
        DataType.FLOAT: 'f',
        DataType.DOUBLE: 'd',
    }

    def __init__(self):
        """Initialize the parser."""
        self._data: bytes = b''
        self._data_section_offset: int = 0

    def parse_header(self, file_path: Union[str, Path]) -> dict:
        """
        Parse only the header of a .datc64 file.

        Args:
            file_path: Path to the .datc64 file

        Returns:
            Dictionary with header information:
            - file_size: Total file size in bytes
            - row_count: Number of rows in the table
            - magic_offset: Offset where magic number was found
            - table_offset: Offset where table data starts (always 4)
            - table_length: Length of table section in bytes
            - record_length: Length of each row in bytes
            - data_section_offset: Offset where variable data starts
            - data_section_size: Size of variable data section
        """
        with open(file_path, 'rb') as f:
            data = f.read()

        file_size = len(data)
        row_count = struct.unpack('<I', data[0:4])[0]
        magic_offset = data.find(DAT_MAGIC_NUMBER)

        if magic_offset == -1:
            raise ValueError(f"Magic number not found in {file_path}")

        table_offset = 4
        table_length = magic_offset - table_offset
        record_length = table_length // row_count if row_count > 0 else 0
        data_section_offset = magic_offset + len(DAT_MAGIC_NUMBER)
        data_section_size = file_size - data_section_offset

        return {
            'file_size': file_size,
            'row_count': row_count,
            'magic_offset': magic_offset,
            'table_offset': table_offset,
            'table_length': table_length,
            'record_length': record_length,
            'data_section_offset': data_section_offset,
            'data_section_size': data_section_size,
        }

    def read_int32(self, data: bytes, offset: int) -> Tuple[int, int]:
        """
        Read a signed 32-bit integer.

        Args:
            data: Binary data
            offset: Offset to read from

        Returns:
            Tuple of (value, new_offset)
        """
        value = struct.unpack('<i', data[offset:offset+4])[0]
        return value, offset + 4

    def read_uint32(self, data: bytes, offset: int) -> Tuple[int, int]:
        """
        Read an unsigned 32-bit integer.

        Args:
            data: Binary data
            offset: Offset to read from

        Returns:
            Tuple of (value, new_offset)
        """
        value = struct.unpack('<I', data[offset:offset+4])[0]
        return value, offset + 4

    def read_int64(self, data: bytes, offset: int) -> Tuple[int, int]:
        """
        Read a signed 64-bit integer.

        Args:
            data: Binary data
            offset: Offset to read from

        Returns:
            Tuple of (value, new_offset)
        """
        value = struct.unpack('<q', data[offset:offset+8])[0]
        return value, offset + 8

    def read_uint64(self, data: bytes, offset: int) -> Tuple[int, int]:
        """
        Read an unsigned 64-bit integer.

        Args:
            data: Binary data
            offset: Offset to read from

        Returns:
            Tuple of (value, new_offset)
        """
        value = struct.unpack('<Q', data[offset:offset+8])[0]
        return value, offset + 8

    def read_bool(self, data: bytes, offset: int) -> Tuple[bool, int]:
        """
        Read a boolean value.

        Args:
            data: Binary data
            offset: Offset to read from

        Returns:
            Tuple of (value, new_offset)
        """
        value = struct.unpack('<?', data[offset:offset+1])[0]
        return value, offset + 1

    def read_float(self, data: bytes, offset: int) -> Tuple[float, int]:
        """
        Read a 32-bit float.

        Args:
            data: Binary data
            offset: Offset to read from

        Returns:
            Tuple of (value, new_offset)
        """
        value = struct.unpack('<f', data[offset:offset+4])[0]
        return value, offset + 4

    def read_double(self, data: bytes, offset: int) -> Tuple[float, int]:
        """
        Read a 64-bit double.

        Args:
            data: Binary data
            offset: Offset to read from

        Returns:
            Tuple of (value, new_offset)
        """
        value = struct.unpack('<d', data[offset:offset+8])[0]
        return value, offset + 8

    def read_string(self, data: bytes, offset: int) -> Tuple[str, int]:
        """
        Read a UTF-16 null-terminated string from the data section.

        Strings in .datc64 are stored in the data section and referenced by pointers.
        They are UTF-16 little-endian encoded and null-terminated with \\x00\\x00\\x00\\x00.

        Args:
            data: Binary data (should be data section)
            offset: Offset in data section where string starts

        Returns:
            Tuple of (decoded_string, bytes_consumed)
        """
        # Find the null terminator (\x00\x00\x00\x00)
        end_offset = data.find(b'\x00\x00\x00\x00', offset)

        if end_offset == -1:
            # No null terminator found - read to end
            end_offset = len(data)

        # Handle case where string starts at the null terminator (empty string)
        if offset == end_offset:
            return '', 4

        # UTF-16 strings must be multiples of 2 bytes
        # Adjust end_offset if needed
        while (end_offset - offset) % 2:
            end_offset = data.find(b'\x00\x00\x00\x00', end_offset + 1)
            if end_offset == -1:
                end_offset = len(data)
                break

        string_data = data[offset:end_offset]

        try:
            decoded = string_data.decode('utf-16-le')
        except UnicodeDecodeError as e:
            # If decoding fails, return hex representation
            decoded = f"<DECODE ERROR: {string_data.hex()}>"

        # Return string and size including null terminator
        size = end_offset - offset + 4
        return decoded, size

    def read_value(self, data: bytes, offset: int, data_type: DataType,
                   data_section: Optional[bytes] = None) -> Tuple[Any, int]:
        """
        Read a value of the specified type.

        Args:
            data: Binary data to read from
            offset: Offset to start reading
            data_type: Type of value to read
            data_section: Data section bytes (for pointers/strings)

        Returns:
            Tuple of (value, new_offset)
        """
        if data_type == DataType.BOOL:
            return self.read_bool(data, offset)
        elif data_type == DataType.BYTE:
            value = struct.unpack('<b', data[offset:offset+1])[0]
            return value, offset + 1
        elif data_type == DataType.UBYTE:
            value = struct.unpack('<B', data[offset:offset+1])[0]
            return value, offset + 1
        elif data_type == DataType.SHORT:
            value = struct.unpack('<h', data[offset:offset+2])[0]
            return value, offset + 2
        elif data_type == DataType.USHORT:
            value = struct.unpack('<H', data[offset:offset+2])[0]
            return value, offset + 2
        elif data_type == DataType.INT:
            return self.read_int32(data, offset)
        elif data_type == DataType.UINT:
            return self.read_uint32(data, offset)
        elif data_type == DataType.LONG:
            return self.read_int64(data, offset)
        elif data_type == DataType.ULONG:
            return self.read_uint64(data, offset)
        elif data_type == DataType.FLOAT:
            return self.read_float(data, offset)
        elif data_type == DataType.DOUBLE:
            return self.read_double(data, offset)
        elif data_type == DataType.STRING:
            if data_section is None:
                raise ValueError("data_section required for STRING type")
            # Read pointer to string
            ptr_offset, new_offset = self.read_uint64(data, offset)
            if ptr_offset in NULL_VALUES_64BIT or ptr_offset == 0:
                return None, new_offset
            # Read string from data section
            string_val, _ = self.read_string(data_section, ptr_offset)
            return string_val, new_offset
        elif data_type == DataType.POINTER:
            # Read pointer value
            ptr_offset, new_offset = self.read_uint64(data, offset)
            if ptr_offset in NULL_VALUES_64BIT or ptr_offset == 0:
                return None, new_offset
            # Return the pointer value (caller can use it to read from data section)
            return ptr_offset, new_offset
        elif data_type == DataType.POINTER_LIST:
            # Read count and offset
            count, _ = self.read_uint64(data, offset)
            list_offset, new_offset = self.read_uint64(data, offset + 8)
            if list_offset in NULL_VALUES_64BIT or count == 0:
                return [], new_offset
            # Return tuple of (count, offset) - caller can use to read list
            return (count, list_offset), new_offset
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

    def parse_file(self, file_path: Union[str, Path],
                   columns: List[ColumnSpec]) -> List[dict]:
        """
        Parse a .datc64 file with known column specifications.

        Args:
            file_path: Path to the .datc64 file
            columns: List of column specifications

        Returns:
            List of dictionaries, one per row, with column names as keys

        Example:
            columns = [
                ColumnSpec("id", DataType.ULONG),
                ColumnSpec("name", DataType.STRING),
                ColumnSpec("value", DataType.INT),
            ]
            rows = parser.parse_file("acts.datc64", columns)
            for row in rows:
                print(row['id'], row['name'], row['value'])
        """
        # Read file
        with open(file_path, 'rb') as f:
            self._data = f.read()

        # Parse header
        header = self.parse_header(file_path)

        # Calculate expected record length
        expected_length = sum(self.TYPE_SIZES[col.data_type] for col in columns)
        if expected_length != header['record_length']:
            raise ValueError(
                f"Column specifications don't match record length: "
                f"expected {expected_length}, got {header['record_length']}"
            )

        # Extract sections
        table_data = self._data[4:header['magic_offset']]
        data_section = self._data[header['data_section_offset']:]
        self._data_section_offset = header['data_section_offset']

        # Parse rows
        rows = []
        for row_num in range(header['row_count']):
            row_offset = row_num * header['record_length']
            row_dict = {}

            offset = row_offset
            for col in columns:
                value, offset = self.read_value(
                    table_data,
                    offset,
                    col.data_type,
                    data_section
                )
                row_dict[col.name] = value

            rows.append(row_dict)

        return rows

    @staticmethod
    def calculate_record_length(columns: List[ColumnSpec]) -> int:
        """
        Calculate the expected record length for a list of columns.

        Args:
            columns: List of column specifications

        Returns:
            Total length in bytes
        """
        return sum(Datc64Parser.TYPE_SIZES[col.data_type] for col in columns)
