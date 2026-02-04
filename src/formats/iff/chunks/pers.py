"""
pers Chunk - Person-Related Metadata
Port of FreeSO's tso.files/Formats/IFF/Chunks/pers.cs

pers contains person/Sim-specific metadata and properties.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('pers')
@dataclass
class pers(IffChunk):
    """
    Person-related metadata chunk - contains Sim-specific properties.
    
    Stores personality traits, person type data, and other Sim-specific
    metadata that may be referenced from behavior or interaction code.
    """
    data: bytes = field(default_factory=bytes)
    person_type: int = 0
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read pers chunk."""
        # Try to read person type if present
        try:
            pos = stream.position
            self.person_type = stream.read_uint32()
            # Store remaining data after type
            self.data = stream.read_bytes(stream.remaining())
        except Exception:
            # Fall back to reading all as data
            stream.position = pos
            self.data = stream.read_bytes(stream.remaining())
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write pers chunk."""
        if self.person_type != 0:
            stream.write_uint32(self.person_type)
        if self.data:
            stream.write_bytes(self.data)
        return True
