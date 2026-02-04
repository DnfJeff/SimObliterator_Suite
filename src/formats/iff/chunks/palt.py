"""
PALT Chunk - Color Palettes
Port of FreeSO's tso.files/Formats/IFF/Chunks/PALT.cs
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Tuple, List

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


# Simple RGB tuple type for colors
Color = Tuple[int, int, int]


@register_chunk('PALT')
@dataclass
class PALT(IffChunk):
    """
    Color palette chunk - holds 256 RGB colors for indexed sprites.
    Used by SPR and SPR2 chunks for color lookup.
    """
    colors: List[Color] = field(default_factory=list)
    references: int = 0  # Reference count for runtime use
    
    @classmethod
    def from_color(cls, color: Color) -> 'PALT':
        """Create a PALT filled with a single color."""
        palt = cls()
        palt.colors = [color] * 256
        return palt
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read PALT chunk from stream."""
        version = stream.read_uint32()
        num_entries = stream.read_uint32()
        reserved = stream.read_bytes(8)  # 8 bytes reserved
        
        self.colors = []
        for _ in range(num_entries):
            r = stream.read_byte()
            g = stream.read_byte()
            b = stream.read_byte()
            self.colors.append((r, g, b))
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write PALT chunk to stream."""
        stream.write_uint32(0)  # version
        stream.write_uint32(len(self.colors))
        stream.write_bytes(bytes(8))  # reserved
        
        for r, g, b in self.colors:
            stream.write_byte(r)
            stream.write_byte(g)
            stream.write_byte(b)
        
        return True
    
    def pal_match(self, data: List[Tuple[int, int, int, int]]) -> bool:
        """
        Check if this palette matches the colors in an RGBA image.
        Alpha=0 pixels are ignored (transparent).
        """
        for i, (r, g, b, a) in enumerate(data):
            if i >= len(self.colors):
                return True
            if a != 0:
                pr, pg, pb = self.colors[i]
                if (r, g, b) != (pr, pg, pb):
                    return False
        return True
    
    def __getitem__(self, index: int) -> Color:
        """Get color at index."""
        return self.colors[index]
    
    def __len__(self) -> int:
        return len(self.colors)
