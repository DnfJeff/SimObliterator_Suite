"""
FWAV Chunk - Sound Event Names
Port of FreeSO's tso.files/Formats/IFF/Chunks/FWAV.cs

This chunk holds the name of a sound event that an object uses.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('FWAV')
@dataclass
class FWAV(IffChunk):
    """
    Sound event name chunk.
    Contains a single null-terminated string naming a sound event.
    """
    name: str = ""
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read FWAV chunk from stream."""
        self.name = stream.read_null_terminated_string()
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write FWAV chunk to stream."""
        stream.write_null_terminated_string(self.name)
        return True
    
    def __str__(self) -> str:
        return f"FWAV #{self.chunk_id}: {self.name}"
