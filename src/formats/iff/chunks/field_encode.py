"""
IffFieldEncode - Bit-packed Field Decoder
Port of FreeSO's tso.files/Formats/IFF/Chunks/IffFieldEncode.cs

Used by CARR and OBJM to read bit-packed compressed data.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple
import struct

if TYPE_CHECKING:
    from ....utils.binary import IoBuffer


@dataclass
class IffFieldEncode:
    """
    Reads values from a field-encoded (bit-packed) stream.
    Used for compressed data in CARR and OBJM chunks.
    """
    io: 'IoBuffer'
    bit_pos: int = 0
    cur_byte: int = 0
    odd: bool = False
    stream_end: bool = False
    
    # Width tables for different data types
    WIDTHS_16 = [5, 8, 13, 16]
    WIDTHS_32 = [6, 11, 21, 32]
    WIDTHS_BYTE = [2, 4, 6, 8]
    
    def __init__(self, io: 'IoBuffer', odd_offset: bool = False):
        """Initialize with IoBuffer."""
        self.io = io
        self.cur_byte = io.read_byte()
        self.odd = not odd_offset
        self.bit_pos = 0
        self.stream_end = False
    
    def _read_bit(self) -> int:
        """Read a single bit."""
        result = (self.cur_byte & (1 << (7 - self.bit_pos))) >> (7 - self.bit_pos)
        self.bit_pos += 1
        
        if self.bit_pos > 7:
            self.bit_pos = 0
            if self.io.has_more:
                self.cur_byte = self.io.read_byte()
                self.odd = not self.odd
            else:
                self.cur_byte = 0
                self.odd = not self.odd
                self.stream_end = True
        
        return result
    
    def _read_bits(self, n: int) -> int:
        """Read n bits."""
        total = 0
        for i in range(n):
            total += self._read_bit() << ((n - i) - 1)
        return total
    
    def _read_field(self, widths: list) -> int:
        """Read a field-encoded value."""
        if self._read_bit() == 0:
            return 0
        
        code = self._read_bits(2)
        width = widths[code]
        value = self._read_bits(width)
        
        # Sign extend
        value |= -(value & (1 << (width - 1)))
        
        return value
    
    def read_byte(self) -> int:
        """Read field-encoded byte."""
        return self._read_field(self.WIDTHS_BYTE) & 0xFF
    
    def read_int16(self) -> int:
        """Read field-encoded signed 16-bit."""
        val = self._read_field(self.WIDTHS_16)
        if val > 0x7FFF:
            val -= 0x10000
        return val
    
    def read_uint16(self) -> int:
        """Read field-encoded unsigned 16-bit."""
        return self._read_field(self.WIDTHS_16) & 0xFFFF
    
    def read_int32(self) -> int:
        """Read field-encoded signed 32-bit."""
        val = self._read_field(self.WIDTHS_32)
        if val > 0x7FFFFFFF:
            val -= 0x100000000
        return val
    
    def read_uint32(self) -> int:
        """Read field-encoded unsigned 32-bit."""
        return self._read_field(self.WIDTHS_32) & 0xFFFFFFFF
    
    def read_float(self) -> float:
        """Read field-encoded float."""
        data = self.read_uint32()
        # Reinterpret as float
        return struct.unpack('f', struct.pack('I', data))[0]
    
    def read_string(self, next_field: bool = False) -> str:
        """Read null-terminated string from stream."""
        # Align to byte boundary
        if self.bit_pos == 0:
            self.io.seek(-1, 1)  # Seek back
            self.odd = not self.odd
        
        result = self.io.read_null_terminated_string()
        
        # 2-byte alignment padding
        if (len(result) % 2 == 0) == (not self.odd):
            self.io.read_byte()
        
        self.bit_pos = 8  # Force next read to get new byte
        
        if next_field and self.io.has_more:
            self.cur_byte = self.io.read_byte()
            self.odd = True
            self.bit_pos = 0
        else:
            self.odd = False
        
        return result
    
    def interrupt(self):
        """Interrupt reading and align position."""
        if self.bit_pos == 0:
            self.io.seek(-1, 1)
    
    def mark_stream(self) -> Tuple[int, int, bool, int]:
        """Mark current position for later revert."""
        return (self.bit_pos, self.cur_byte, self.odd, self.io.position)
    
    def revert_to_mark(self, mark: Tuple[int, int, bool, int]):
        """Revert to marked position."""
        self.stream_end = False
        self.bit_pos = mark[0]
        self.cur_byte = mark[1]
        self.odd = mark[2]
        self.io.position = mark[3]
    
    def bit_debug_til(self, skip_position: int) -> str:
        """Read and return remaining bits as debug string until skip_position."""
        result = []
        
        # Remaining bits in current byte
        while self.bit_pos > 0 and self.bit_pos < 8 and not self.stream_end:
            result.append(str(self._read_bit()))
        
        # Remaining bytes
        while self.io.position < skip_position and self.io.has_more:
            byte = self.io.read_byte()
            result.append(f" {byte:02x}")
        
        return ''.join(result)

