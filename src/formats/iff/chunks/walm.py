"""
WALm/FLRm Chunks - Wall and Floor Mappings
Port of FreeSO's tso.files/Formats/IFF/Chunks/WALm.cs

Maps walls/floors in ARRY chunks to resources in other IFF files.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@dataclass
class WALmEntry:
    """A single wall/floor mapping entry."""
    name: str = ""
    unknown: int = 1  # Usually 1 - possibly index in IFF
    id: int = 0       # Resource ID (byte)
    unknown2: bytes = field(default_factory=bytes)  # Variable length based on chunk ID


@register_chunk('WALm')
@dataclass
class WALm(IffChunk):
    """
    Wall mapping chunk.
    Maps walls in ARRY chunks to wall resources in external IFF files.
    """
    entries: List[WALmEntry] = field(default_factory=list)
    walm_version: int = 0
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read WALm chunk."""
        zero = stream.read_int32()
        self.walm_version = stream.read_int32()  # Should be 0
        magic = stream.read_int32()  # "mLAW" or "mRLF"
        count = stream.read_int32()
        
        self.entries = []
        for _ in range(count):
            entry = WALmEntry()
            entry.name = stream.read_null_terminated_string()
            # Pad to short width
            if len(entry.name) % 2 == 0:
                stream.read_byte()
            entry.unknown = stream.read_int32()
            entry.id = stream.read_byte()
            # Size depends on chunk ID - older format (id 0) has less data
            extra_size = 5 + self.chunk_id * 2
            entry.unknown2 = stream.read_bytes(extra_size)
            self.entries.append(entry)
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write WALm chunk."""
        stream.write_int32(0)
        stream.write_int32(self.walm_version)
        stream.write_int32(0x57414C6D)  # "WALm" 
        stream.write_int32(len(self.entries))
        
        for entry in self.entries:
            stream.write_null_terminated_string(entry.name)
            if len(entry.name) % 2 == 0:
                stream.write_byte(0)  # Padding
            stream.write_int32(entry.unknown)
            stream.write_byte(entry.id)
            stream.write_bytes(entry.unknown2)
        
        return True


@register_chunk('FLRm')
@dataclass
class FLRm(WALm):
    """
    Floor mapping chunk - exact duplicate of WALm format.
    Maps floors in ARRY chunks to floor resources in external IFF files.
    """
    # No difference from WALm
    pass
