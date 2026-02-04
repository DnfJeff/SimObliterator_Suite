"""
POSI - Object Position Chunk (minimal stub)

This chunk stores the initial position and rotation of an object instance.
Not all objects have this chunk - positions are often stored in the neighborhood
or lot files instead.

Based on The Sims Open Tech Documentation references to position data.
"""

from dataclasses import dataclass
from typing import Optional
from ..base import IffChunk, register_chunk

try:
    from ...utils.binary import IoBuffer, ByteOrder
except ImportError:
    from utils.binary import IoBuffer, ByteOrder


@register_chunk('POSI')
@dataclass
class POSI(IffChunk):
    """
    Object Position chunk - stores initial position and rotation.
    
    This chunk is rarely used in standard game files. Position data is typically
    stored in lot or neighborhood files instead. Included for completeness.
    
    Typical structure (if used):
    - X position (float)
    - Y position (float)  
    - Z position (float)
    - Rotation/direction (varies)
    """
    
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: int = 0
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Parse POSI chunk."""
        try:
            # Try to read as 3 floats + rotation
            if stream.remaining_bytes >= 16:
                self.x = stream.read_float()
                self.y = stream.read_float()
                self.z = stream.read_float()
                self.rotation = stream.read_uint32()
                self.chunk_processed = True
            elif stream.remaining_bytes >= 12:
                # Try 3 floats only
                self.x = stream.read_float()
                self.y = stream.read_float()
                self.z = stream.read_float()
                self.chunk_processed = True
            else:
                # Not enough data - store raw
                self.chunk_processed = False
        except Exception:
            self.chunk_processed = False
    
    def write(self, iff: 'IffFile', stream) -> bool:
        """Write POSI chunk - not implemented."""
        return False  # Read-only
    
    def __str__(self) -> str:
        return f"POSI: ({self.x:.1f}, {self.y:.1f}, {self.z:.1f}) rot={self.rotation}"
