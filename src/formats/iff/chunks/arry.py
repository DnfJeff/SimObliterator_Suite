"""
ARRY Chunk - Array Data
Port of FreeSO's tso.files/Formats/IFF/Chunks/ARRY.cs

Contains 2D array data for lot terrain, floors, walls, etc.
Uses RLE compression for storage.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from enum import IntEnum

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


class ARRYType(IntEnum):
    """Array data type - determines bytes per element."""
    RLE_FLOOR = 1    # Floors, ground, grass, flags, pool, water
    OBJECTS = 2      # Object data
    RLE_ALT = 4      # Altitude data
    RLE_WALLS = 8    # Wall data


@register_chunk('ARRY')
@register_chunk('Arry')  # Lowercase variant in house files
@dataclass
class ARRY(IffChunk):
    """
    Array data chunk.
    Stores 2D grid data for lot terrain, floors, walls, and objects.
    Uses RLE compression for efficient storage.
    """
    width: int = 0
    height: int = 0
    arry_type: ARRYType = ARRYType.RLE_FLOOR
    data: bytes = field(default_factory=bytes)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read ARRY chunk with RLE decompression."""
        zero = stream.read_int32()
        self.width = stream.read_int32()
        self.height = stream.read_int32()
        self.arry_type = ARRYType(stream.read_int32())
        unknown = stream.read_int32()
        
        data_byte_size = int(self.arry_type)
        total_size = self.width * self.height * data_byte_size
        self.data = bytearray(total_size)
        
        current_position = 0
        
        while stream.has_more and current_position < total_size:
            # RLE format:
            # Bit 15 set: skip/fill mode
            # Bit 15 clear: raw data mode
            flre = stream.read_uint16()
            if flre == 0:
                break
            
            raw_fill = (flre & 0x8000) == 0
            
            if raw_fill:
                # Raw data mode - read 'flre' bytes directly
                for i in range(flre):
                    if not stream.has_more or current_position >= total_size:
                        return
                    self.data[current_position] = stream.read_byte()
                    current_position += 1
                # Pad to 16-bit alignment
                if (flre & 1) == 1:
                    stream.read_byte()
            else:
                # Skip/fill mode
                last_position = current_position
                current_position += flre & 0x7FFF
                current_position = current_position % total_size
                
                if current_position == 0:
                    return
                
                # Fill byte (padded to 16 bits)
                pad = stream.read_byte()
                stream.read_byte()  # Padding
                
                # Fill the skipped area
                while last_position < current_position:
                    self.data[last_position] = pad
                    last_position += 1
                
                if not stream.has_more:
                    return
                
                # Check for more raw data
                size = stream.read_int16()
                if (size & 0x8000) != 0:
                    stream.seek(-2, 1)  # Back up - it's another skip marker
                    continue
                
                # Read raw data
                for i in range(size):
                    if current_position >= total_size:
                        break
                    self.data[current_position] = stream.read_byte()
                    current_position += 1
                    current_position = current_position % total_size
                
                # Pad to 16-bit alignment
                if (size & 1) == 1:
                    stream.read_byte()
        
        self.data = bytes(self.data)
    
    @property
    def byte_size(self) -> int:
        """Bytes per element."""
        return int(self.arry_type)
    
    def get_value(self, x: int, y: int) -> int:
        """Get value at position."""
        stride = self.byte_size
        index = (y * self.width + x) * stride
        if index + stride > len(self.data):
            return 0
        
        # Read value based on stride
        result = 0
        for i in range(stride):
            result |= self.data[index + i] << (i * 8)
        return result
    
    def get_transposed_data(self) -> bytes:
        """Get data with X/Y axes transposed."""
        stride = self.byte_size
        result = bytearray(len(self.data))
        
        for i in range(0, len(self.data), stride):
            div_i = i // stride
            x = div_i % self.width
            y = div_i // self.width
            target_index = y * stride + x * stride * self.width
            
            for j in range(stride):
                if target_index + j < len(result) and i + j < len(self.data):
                    result[target_index + j] = self.data[i + j]
        
        return bytes(result)
    
    def debug_print(self) -> str:
        """Print array as text grid for debugging."""
        lines = []
        stride = self.byte_size
        index = 0
        
        for y in range(self.height):
            row = []
            for x in range(self.width):
                if index < len(self.data):
                    val = self.data[index]
                    if val == 0:
                        row.append("  .")
                    else:
                        row.append(f"{val:3d}")
                index += stride
            lines.append("".join(row))
        
        return "\n".join(lines)
