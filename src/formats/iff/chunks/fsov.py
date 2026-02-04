"""
FSOV Chunk - FreeSO Version/Data Container
Port of FreeSO's tso.files/Formats/IFF/Chunks/FSOV.cs

A simple container for FSOV data. If present, normal TS1 IFF loading is subverted.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


FSOV_CURRENT_VERSION = 1


@register_chunk('FSOV')
@dataclass
class FSOV(IffChunk):
    """
    FreeSO version data container.
    Stores version + raw byte data for FreeSO-specific purposes.
    """
    version: int = FSOV_CURRENT_VERSION
    data: bytes = field(default_factory=bytes)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read FSOV chunk."""
        self.version = stream.read_int32()
        length = stream.read_int32()
        self.data = stream.read_bytes(length)
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write FSOV chunk."""
        stream.write_int32(self.version)
        stream.write_int32(len(self.data))
        stream.write_bytes(self.data)
        return True
