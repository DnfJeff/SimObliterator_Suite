"""
GLOB Chunk - Semi-Global File Reference
Port of FreeSO's tso.files/Formats/IFF/Chunks/GLOB.cs

GLOB holds the filename of a semi-global IFF file used by this object.
Semi-globals contain shared behaviors and resources.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk("GLOB")
@dataclass
class GLOB(IffChunk):
    """
    Semi-global file reference chunk.
    Maps to: FSO.Files.Formats.IFF.Chunks.GLOB
    """
    name: str = ""
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read GLOB chunk from stream."""
        # First byte could be pascal string length or start of null-terminated string
        first_byte = io.read_byte()
        
        if first_byte < 48:  # Less than ASCII '0', treat as pascal string length
            self.name = io.read_cstring(first_byte, trim_null=True)
        else:
            # It's a null-terminated string, first byte is part of the name
            chars = [chr(first_byte)]
            while io.has_more:
                byte = io.read_byte()
                if byte == 0:
                    break
                chars.append(chr(byte))
            self.name = ''.join(chars)
    
    def write(self, iff: 'IffFile', io: 'IoWriter') -> bool:
        """Write GLOB chunk to stream."""
        # Write as pascal string (length byte + chars)
        name_bytes = self.name.encode('ascii', errors='replace')
        io.write_byte(len(name_bytes))
        io.write_bytes(name_bytes)
        return True
    
    def __str__(self) -> str:
        return f"GLOB #{self.chunk_id}: {self.name}"
