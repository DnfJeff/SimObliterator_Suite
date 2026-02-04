"""
XXXX Chunk - Filler/Padding Resource
Port of FreeSO's tso.files/Formats/IFF/Chunks/XXXX.cs

XXXX is used as a filler chunk created during in-place edits of IFF files.
These chunks should be safely ignored during parsing.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('XXXX')
@dataclass
class XXXX(IffChunk):
    """
    Filler/padding chunk - created during in-place edits of IFF files.
    
    When an IFF chunk is resized and doesn't fit in its original location,
    the original space is marked with an XXXX chunk to maintain file structure.
    
    Safe to ignore during parsing and can be removed during file optimization.
    """
    data: bytes = field(default_factory=bytes)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read XXXX chunk - just store raw data."""
        # Read all remaining bytes for this chunk
        self.data = stream.read_bytes(stream.remaining())
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write XXXX chunk - output the raw data."""
        if self.data:
            stream.write_bytes(self.data)
        return True
    
    def is_filler(self) -> bool:
        """Identify this as a filler chunk."""
        return True
