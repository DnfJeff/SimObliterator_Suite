"""Clean binary I/O utilities for IFF parsing."""

import struct
from enum import Enum
from typing import BinaryIO
from io import BytesIO


class ByteOrder(Enum):
    """Byte order enum for struct packing/unpacking."""
    BIG_ENDIAN = ">"
    LITTLE_ENDIAN = "<"


class IoBuffer:
    """Binary reader with endian support."""
    
    def __init__(self, stream: BinaryIO, byte_order: ByteOrder = ByteOrder.LITTLE_ENDIAN):
        self.stream = stream
        self.byte_order = byte_order
    
    @classmethod
    def from_bytes(cls, data: bytes, byte_order: ByteOrder = ByteOrder.LITTLE_ENDIAN) -> 'IoBuffer':
        """Create from bytes."""
        return cls(BytesIO(data), byte_order)
    
    @classmethod
    def from_file(cls, filepath: str, byte_order: ByteOrder = ByteOrder.LITTLE_ENDIAN) -> 'IoBuffer':
        """Create from file path."""
        with open(filepath, 'rb') as f:
            data = f.read()
        return cls.from_bytes(data, byte_order)
    
    @property
    def position(self) -> int:
        """Current position in stream."""
        return self.stream.tell()
    
    @position.setter
    def position(self, value: int):
        """Seek to position."""
        self.stream.seek(value)
    
    @property
    def has_more(self) -> bool:
        """Check if there are more bytes to read."""
        current = self.stream.tell()
        self.stream.seek(0, 2)  # Seek to end
        end = self.stream.tell()
        self.stream.seek(current)  # Seek back
        return current < end
    
    def has_bytes(self, num_bytes: int) -> bool:
        """Check if there are at least num_bytes remaining."""
        current = self.stream.tell()
        self.stream.seek(0, 2)  # Seek to end
        end = self.stream.tell()
        self.stream.seek(current)  # Seek back
        return (end - current) >= num_bytes
    
    def skip(self, num_bytes: int):
        """Skip bytes from current position."""
        self.stream.seek(num_bytes, 1)
    
    def seek(self, offset: int, whence: int = 0):
        """Seek in stream (whence: 0=start, 1=current, 2=end)."""
        self.stream.seek(offset, whence)
    
    def read_bytes(self, count: int) -> bytes:
        """Read raw bytes."""
        return self.stream.read(count)
    
    def read_byte(self) -> int:
        """Read single byte (0-255)."""
        return self.stream.read(1)[0]
    
    def read_uint8(self) -> int:
        """Read unsigned 8-bit integer."""
        return self.read_byte()
    
    def read_sbyte(self) -> int:
        """Read signed byte (-128 to 127)."""
        return struct.unpack('b', self.stream.read(1))[0]
    
    def read_uint16(self) -> int:
        """Read unsigned 16-bit integer."""
        fmt = f"{self.byte_order.value}H"
        return struct.unpack(fmt, self.stream.read(2))[0]
    
    def read_int16(self) -> int:
        """Read signed 16-bit integer."""
        fmt = f"{self.byte_order.value}h"
        return struct.unpack(fmt, self.stream.read(2))[0]
    
    def read_uint32(self) -> int:
        """Read unsigned 32-bit integer."""
        fmt = f"{self.byte_order.value}I"
        return struct.unpack(fmt, self.stream.read(4))[0]
    
    def read_int32(self) -> int:
        """Read signed 32-bit integer."""
        fmt = f"{self.byte_order.value}i"
        return struct.unpack(fmt, self.stream.read(4))[0]
    
    def read_float(self) -> float:
        """Read 32-bit float."""
        fmt = f"{self.byte_order.value}f"
        return struct.unpack(fmt, self.stream.read(4))[0]
    
    def read_double(self) -> float:
        """Read 64-bit double."""
        fmt = f"{self.byte_order.value}d"
        return struct.unpack(fmt, self.stream.read(8))[0]
    
    def read_cstring(self, length: int, trim_null: bool = True) -> str:
        """Read fixed-length ASCII string."""
        data = self.stream.read(length)
        result = data.decode('ascii', errors='replace')
        if trim_null:
            null_idx = result.find('\0')
            if null_idx != -1:
                result = result[:null_idx]
        return result
    
    def read_pascal_string(self) -> str:
        """Read length-prefixed string (1 byte length)."""
        length = self.read_byte()
        return self.read_cstring(length, trim_null=True)
    
    def write_bytes(self, data: bytes):
        """Write raw bytes."""
        self.stream.write(data)
    
    def write_byte(self, value: int):
        """Write single byte."""
        self.stream.write(struct.pack('B', value))
    
    def write_uint16(self, value: int):
        """Write unsigned 16-bit integer."""
        fmt = f"{self.byte_order.value}H"
        self.stream.write(struct.pack(fmt, value))
    
    def write_uint32(self, value: int):
        """Write unsigned 32-bit integer."""
        fmt = f"{self.byte_order.value}I"
        self.stream.write(struct.pack(fmt, value))
