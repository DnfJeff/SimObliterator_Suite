"""
THMB Chunk - Thumbnail Parameters
Port of FreeSO's tso.files/Formats/IFF/Chunks/THMB.cs

Contains dimensions and offset data for lot thumbnails.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('THMB')
@dataclass
class THMB(IffChunk):
    """
    Thumbnail parameters chunk.
    Defines dimensions and offsets for lot thumbnail rendering.
    """
    width: int = 0
    height: int = 0
    base_y_off: int = 0  # Base Y offset
    x_off: int = 0       # X offset (usually 0)
    add_y_off: int = 0   # Additional Y offset (difference between roofed/unroofed)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read THMB chunk."""
        self.width = stream.read_int32()
        self.height = stream.read_int32()
        self.base_y_off = stream.read_int32()
        self.x_off = stream.read_int32()
        self.add_y_off = stream.read_int32()
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write THMB chunk."""
        stream.write_int32(self.width)
        stream.write_int32(self.height)
        stream.write_int32(self.base_y_off)
        stream.write_int32(self.x_off)
        stream.write_int32(self.add_y_off)
        return True
