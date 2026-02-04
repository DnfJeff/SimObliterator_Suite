"""
MTEX Chunk - Mesh Texture
Port of FreeSO's tso.files/Formats/IFF/Chunks/MTEX.cs

Texture data for 3D meshes. Can be jpg, png, or bmp format.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('MTEX')
@dataclass
class MTEX(IffChunk):
    """
    Mesh texture chunk.
    Stores raw texture data (jpg/png/bmp) for 3D mesh rendering.
    """
    data: bytes = field(default_factory=bytes)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read MTEX chunk - store all remaining bytes."""
        pos = stream.position
        stream.seek(0, 2)  # Seek to end
        end = stream.position
        stream.seek(pos)
        self.data = stream.read_bytes(end - pos)
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write MTEX chunk."""
        stream.write_bytes(self.data)
        return True
    
    def get_format(self) -> str:
        """Detect image format from magic bytes."""
        if len(self.data) < 4:
            return "unknown"
        
        # PNG magic: 89 50 4E 47
        if self.data[:4] == b'\x89PNG':
            return "png"
        # JPEG magic: FF D8 FF
        if self.data[:3] == b'\xff\xd8\xff':
            return "jpeg"
        # BMP magic: 42 4D
        if self.data[:2] == b'BM':
            return "bmp"
        
        return "unknown"
