"""
CFP Parser - Compressed Floating Point Animation Data

Parses .cfp files containing compressed animation frame data.
Based on FreeSO's CFPCodec.cs and TheSimsOpenTechDoc Part IV.

CFP Compression (~7:1 ratio):
  - 0xFF + 4 bytes = Raw IEEE float
  - 0xFE + 2 bytes = Repeat count (value N+1 times)
  - 0x00-0x79, 0x85-0xFC = Delta encoding

Delta formula (Dave Baum):
  f(x) = 3.9676×10⁻¹⁰ × (x-126)³ × |x-126|
"""

import struct
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import math

from .bcf import Animation, Vector3, Quaternion


# Pre-computed delta table
def _compute_delta_table() -> List[float]:
    """Compute delta lookup table for CFP decompression."""
    table = [0.0] * 256
    for i in range(256):
        x = i - 126
        # f(x) = 3.9676e-10 * (x-126)^3 * |x-126|
        table[i] = 3.9676e-10 * (x ** 3) * abs(x)
    return table

DELTA_TABLE = _compute_delta_table()


@dataclass
class CFPData:
    """Decompressed CFP animation data."""
    translations: List[Vector3] = field(default_factory=list)
    rotations: List[Quaternion] = field(default_factory=list)


class CFPReader:
    """
    Parser for CFP (Compressed Floating Point) animation files.
    
    Usage:
        reader = CFPReader()
        cfp = reader.read_file("animations.cfp")
        
        # Enrich an animation from BCF with frame data
        reader.enrich_animation(animation, cfp_data)
    """
    
    def __init__(self):
        self.pos = 0
        self.data = b""
    
    def read_file(self, filepath: str) -> Optional[bytes]:
        """Read CFP file, return raw bytes for selective decompression."""
        with open(filepath, 'rb') as f:
            return f.read()
    
    def decompress_floats(self, data: bytes, count: int, offset: int = 0) -> List[float]:
        """
        Decompress a sequence of floats from CFP data.
        
        Args:
            data: CFP file bytes
            count: Number of floats to decompress
            offset: Starting byte offset in data
            
        Returns:
            List of decompressed float values
        """
        self.data = data
        self.pos = offset
        
        result = []
        prev_value = 0.0
        
        while len(result) < count and self.pos < len(self.data):
            code = self.data[self.pos]
            self.pos += 1
            
            if code == 0xFF:
                # Raw float
                value = struct.unpack('<f', self.data[self.pos:self.pos + 4])[0]
                self.pos += 4
                result.append(value)
                prev_value = value
                
            elif code == 0xFE:
                # Repeat previous
                repeat_count = struct.unpack('<H', self.data[self.pos:self.pos + 2])[0]
                self.pos += 2
                for _ in range(repeat_count + 1):
                    if len(result) >= count:
                        break
                    result.append(prev_value)
                    
            elif code in (0xFD, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F,
                          0x80, 0x81, 0x82, 0x83, 0x84):
                # Reserved/special codes - treat as raw
                value = struct.unpack('<f', self.data[self.pos:self.pos + 4])[0]
                self.pos += 4
                result.append(value)
                prev_value = value
                
            else:
                # Delta encoding
                delta = DELTA_TABLE[code]
                value = prev_value + delta
                result.append(value)
                prev_value = value
        
        return result
    
    def decompress_vectors(self, data: bytes, count: int, offset: int = 0) -> List[Vector3]:
        """
        Decompress translation vectors (X, Y, Z sequences).
        
        CFP stores all X values, then all Y values, then all Z values.
        Coordinate conversion: Z is negated for DirectX -> WebGL handedness.
        """
        if count == 0:
            return []
        
        # Each component stored separately
        xs = self.decompress_floats(data, count, offset)
        
        # Calculate next offset (tricky - need to track position)
        self.data = data
        self.pos = offset
        self._skip_compressed(count)
        offset_y = self.pos
        
        ys = self.decompress_floats(data, count, offset_y)
        
        self._skip_compressed(count)
        offset_z = self.pos
        
        zs = self.decompress_floats(data, count, offset_z)
        
        vectors = []
        for i in range(min(len(xs), len(ys), len(zs))):
            # Negate Z for coordinate system conversion (per VitaMoo)
            vectors.append(Vector3(xs[i], ys[i], -zs[i]))
        
        return vectors
    
    def decompress_quaternions(self, data: bytes, count: int, offset: int = 0) -> List[Quaternion]:
        """
        Decompress rotation quaternions (W, X, Y, Z sequences).
        
        Coordinate conversion: W is negated for DirectX -> WebGL handedness.
        """
        if count == 0:
            return []
        
        ws = self.decompress_floats(data, count, offset)
        
        self.data = data
        self.pos = offset
        self._skip_compressed(count)
        offset_x = self.pos
        
        xs = self.decompress_floats(data, count, offset_x)
        
        self._skip_compressed(count)
        offset_y = self.pos
        
        ys = self.decompress_floats(data, count, offset_y)
        
        self._skip_compressed(count)
        offset_z = self.pos
        
        zs = self.decompress_floats(data, count, offset_z)
        
        quats = []
        for i in range(min(len(ws), len(xs), len(ys), len(zs))):
            # Negate W for coordinate system conversion (per VitaMoo)
            q = Quaternion(-ws[i], xs[i], ys[i], zs[i])
            quats.append(q.normalize())
        
        return quats
    
    def _skip_compressed(self, count: int):
        """Skip over compressed float data without storing values."""
        values_read = 0
        
        while values_read < count and self.pos < len(self.data):
            code = self.data[self.pos]
            self.pos += 1
            
            if code == 0xFF:
                self.pos += 4
                values_read += 1
            elif code == 0xFE:
                repeat = struct.unpack('<H', self.data[self.pos:self.pos + 2])[0]
                self.pos += 2
                values_read += repeat + 1
            elif code in (0xFD, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F,
                          0x80, 0x81, 0x82, 0x83, 0x84):
                self.pos += 4
                values_read += 1
            else:
                values_read += 1
    
    def enrich_animation(self, anim: Animation, cfp_data: bytes,
                         translation_offset: int, rotation_offset: int):
        """
        Fill animation with decompressed frame data from CFP.
        
        Args:
            anim: Animation object from BCF (has motion headers)
            cfp_data: Raw CFP file bytes
            translation_offset: Byte offset for translation data
            rotation_offset: Byte offset for rotation data
        """
        # Count total frames needed
        total_translations = 0
        total_rotations = 0
        
        for motion in anim.motions:
            if motion.has_translation:
                total_translations += motion.frame_count * 3  # X, Y, Z
            if motion.has_rotation:
                total_rotations += motion.frame_count * 4  # W, X, Y, Z
        
        # Decompress all at once
        if total_translations > 0:
            anim.translations = self.decompress_vectors(
                cfp_data, total_translations // 3, translation_offset
            )
        
        if total_rotations > 0:
            anim.rotations = self.decompress_quaternions(
                cfp_data, total_rotations // 4, rotation_offset
            )


def compress_floats(values: List[float]) -> bytes:
    """
    Compress a list of floats to CFP format.
    
    Simple implementation - uses 0xFF for all values (no delta encoding).
    Produces larger but compatible output.
    """
    result = bytearray()
    
    i = 0
    while i < len(values):
        # Check for repeats - need at least 3 same values to benefit from repeat encoding
        repeat_count = 0
        while (i + repeat_count + 1 < len(values) and 
               values[i + repeat_count + 1] == values[i] and
               repeat_count < 65535):
            repeat_count += 1
        
        if repeat_count >= 2:
            # Use repeat encoding: write first value, then repeat code
            # 0xFE with N means repeat the previous value N+1 more times
            result.append(0xFF)
            result.extend(struct.pack('<f', values[i]))
            result.append(0xFE)
            result.extend(struct.pack('<H', repeat_count - 1))  # N+1 repetitions = repeat_count
            i += repeat_count + 1
        else:
            # Raw float
            result.append(0xFF)
            result.extend(struct.pack('<f', values[i]))
            i += 1
    
    return bytes(result)


# Test
if __name__ == "__main__":
    # Test delta table
    print("Delta table samples:")
    for code in [0, 63, 126, 189, 252]:
        print(f"  Code {code}: delta = {DELTA_TABLE[code]:.6e}")
    
    # Test compression round-trip
    test_values = [1.0, 1.0, 1.0, 2.0, 3.0, 3.5]
    compressed = compress_floats(test_values)
    print(f"\nOriginal: {len(test_values) * 4} bytes")
    print(f"Compressed: {len(compressed)} bytes")
    
    reader = CFPReader()
    decompressed = reader.decompress_floats(compressed, len(test_values))
    print(f"Decompressed: {decompressed}")
