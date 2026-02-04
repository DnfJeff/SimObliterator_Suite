"""
FSOM Chunk - Floor Sort Object Mesh
Port of FreeSO's tso.files/Formats/IFF/Chunks/FSOM.cs

IFF chunk wrapper for FSOM (3D mesh) data. Data is GZip compressed.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
import gzip
from io import BytesIO

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('FSOM')
@dataclass
class FSOM(IffChunk):
    """
    Floor sort object mesh chunk.
    Stores GZip-compressed 3D mesh data for object rendering.
    """
    data: bytes = field(default_factory=bytes)
    _decompressed: bytes = field(default_factory=bytes, repr=False)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read FSOM chunk - store compressed data."""
        pos = stream.position
        stream.seek(0, 2)
        end = stream.position
        stream.seek(pos)
        self.data = stream.read_bytes(end - pos)
        self._decompressed = b''
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write FSOM chunk."""
        stream.write_bytes(self.data)
        return True
    
    def get_decompressed(self) -> bytes:
        """Get decompressed mesh data."""
        if not self._decompressed and self.data:
            try:
                self._decompressed = gzip.decompress(self.data)
            except Exception:
                # Data might not be compressed
                self._decompressed = self.data
        return self._decompressed
    
    def set_data(self, data: bytes, compress: bool = True):
        """Set mesh data, optionally compressing it."""
        if compress:
            self.data = gzip.compress(data)
        else:
            self.data = data
        self._decompressed = data if not compress else b''
