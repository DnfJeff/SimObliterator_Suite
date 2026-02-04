"""
BCON Chunk - Constants
Port of FreeSO's tso.files/Formats/IFF/Chunks/BCON.cs

BCON holds numeric constants that behavior code (BHAV) can reference.
Labels for these constants are stored in TRCN chunks with matching IDs.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer


@register_chunk("BCON")
@dataclass
class BCON(IffChunk):
    """
    Constants chunk - numeric values for behavior code.
    Maps to: FSO.Files.Formats.IFF.Chunks.BCON
    """
    flags: int = 0
    constants: list[int] = field(default_factory=list)
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read BCON chunk from stream."""
        num = io.read_byte()
        self.flags = io.read_byte()
        
        self.constants = []
        for _ in range(num):
            self.constants.append(io.read_uint16())
    
    def get_constant(self, index: int) -> int:
        """Get a constant by index."""
        if 0 <= index < len(self.constants):
            return self.constants[index]
        return 0
    
    def set_constant(self, index: int, value: int):
        """Set a constant value."""
        if 0 <= index < len(self.constants):
            self.constants[index] = value & 0xFFFF
    
    def __len__(self) -> int:
        return len(self.constants)
    
    def __getitem__(self, index: int) -> int:
        return self.constants[index]
    
    def __setitem__(self, index: int, value: int):
        self.constants[index] = value & 0xFFFF
    
    def __str__(self) -> str:
        return f"BCON #{self.chunk_id}: {self.chunk_label} ({len(self.constants)} constants)"
