"""
CATS Chunk - Cat-Related Data
Port of FreeSO's tso.files/Formats/IFF/Chunks/CATS.cs

CATS contains cat-specific behavioral or property data, 
likely related to pet interactions introduced in the Unleashed expansion.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('CATS')
@dataclass
class CATS(IffChunk):
    """
    Cat-related data chunk - contains pet cat behavior flags and properties.
    
    Introduced in the Unleashed expansion for pet-related interactions
    and behaviors specific to cats.
    """
    data: bytes = field(default_factory=bytes)
    cat_flags: int = 0
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read CATS chunk."""
        # Try to read flags if present
        try:
            pos = stream.position
            self.cat_flags = stream.read_uint32()
            # Store remaining data after flags
            self.data = stream.read_bytes(stream.remaining())
        except Exception:
            # Fall back to reading all as data
            stream.position = pos
            self.data = stream.read_bytes(stream.remaining())
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write CATS chunk."""
        if self.cat_flags != 0:
            stream.write_uint32(self.cat_flags)
        if self.data:
            stream.write_bytes(self.data)
        return True
    
    def is_cat_enabled(self, flag_bit: int) -> bool:
        """Check if a specific cat feature flag is enabled."""
        return bool(self.cat_flags & (1 << flag_bit))
