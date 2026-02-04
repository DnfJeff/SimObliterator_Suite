"""
BMP/PNG Chunks - Bitmap Image Data
Port of FreeSO's tso.files/Formats/IFF/Chunks/BMP.cs and PNG.cs

These chunks hold raw image data in BMP or PNG format.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('BMP_')
@dataclass
class BMP(IffChunk):
    """
    Bitmap image chunk - holds raw BMP data.
    The data can be loaded by image libraries.
    """
    data: bytes = field(default_factory=bytes)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read BMP chunk - just store all remaining bytes."""
        # Read all remaining data in the stream
        pos = stream.position
        stream.seek(0, 2)  # Seek to end
        end = stream.position
        stream.seek(pos)
        self.data = stream.read_bytes(end - pos)
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write BMP chunk."""
        stream.write_bytes(self.data)
        return True


@register_chunk('PNG_')
@dataclass  
class PNG(BMP):
    """
    PNG image chunk - exact duplicate of BMP format.
    Holds raw PNG data instead of BMP.
    """
    # No difference from BMP - just different chunk type
    pass
