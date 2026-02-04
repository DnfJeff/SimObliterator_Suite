"""
TRCN Chunk - BCON Constant Labels
Port of FreeSO's tso.files/Formats/IFF/Chunks/TRCN.cs

Provides human-readable labels and metadata for BCON constants.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@dataclass
class TRCNEntry:
    """A single BCON constant label entry."""
    flags: int = 0
    unknown: int = 0
    label: str = ""
    comment: str = ""
    range_enabled: int = 0  # v1+ only
    low_range: int = 0
    high_range: int = 100
    
    def read(self, stream: 'IoBuffer', version: int, odd: bool):
        """Read entry from stream."""
        self.flags = stream.read_int32()
        self.unknown = stream.read_int32()
        
        # String format differs by version
        if version > 1:
            self.label = stream.read_variable_length_pascal_string()
        else:
            self.label = stream.read_null_terminated_string()
            # Alignment padding for v0/v1
            if (len(self.label) % 2 == 0) != odd:
                stream.read_byte()
        
        if version > 1:
            self.comment = stream.read_variable_length_pascal_string()
        else:
            self.comment = stream.read_null_terminated_string()
            # Alignment padding
            if len(self.comment) % 2 == 0:
                stream.read_byte()
        
        # Range info (v1+)
        if version > 0:
            self.range_enabled = stream.read_byte()
            self.low_range = stream.read_int16()
            self.high_range = stream.read_int16()
    
    def write(self, stream: 'IoWriter'):
        """Write entry to stream."""
        stream.write_int32(self.flags)
        stream.write_int32(self.unknown)
        stream.write_variable_length_pascal_string(self.label)
        stream.write_variable_length_pascal_string(self.comment)
        stream.write_byte(self.range_enabled)
        stream.write_int16(self.low_range)
        stream.write_int16(self.high_range)


@register_chunk('TRCN')
@dataclass
class TRCN(IffChunk):
    """
    BCON constant labels chunk.
    Provides names, comments, and valid ranges for BCON values.
    Matches BCON chunk with same resource ID.
    """
    version: int = 0
    entries: List[TRCNEntry] = field(default_factory=list)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read TRCN chunk from stream."""
        zero = stream.read_int32()
        self.version = stream.read_int32()
        magic = stream.read_int32()  # "NCRT" or similar
        count = stream.read_int32()
        
        self.entries = []
        for i in range(count):
            entry = TRCNEntry()
            # odd parameter is for alignment quirk in v0/v1
            entry.read(stream, self.version, i > 0 and self.version > 0)
            self.entries.append(entry)
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write TRCN chunk to stream (always v2)."""
        stream.write_int32(0)  # zero
        stream.write_int32(2)  # version 2
        stream.write_int32(0)  # magic (could be "NCRT")
        stream.write_int32(len(self.entries))
        
        for entry in self.entries:
            entry.write(stream)
        
        return True
    
    def get_label(self, index: int) -> str:
        """Get label for constant at index."""
        if 0 <= index < len(self.entries):
            return self.entries[index].label
        return f"const{index}"
    
    def get_comment(self, index: int) -> str:
        """Get comment for constant at index."""
        if 0 <= index < len(self.entries):
            return self.entries[index].comment
        return ""
    
    def __len__(self) -> int:
        return len(self.entries)
    
    def __getitem__(self, index: int) -> TRCNEntry:
        return self.entries[index]
