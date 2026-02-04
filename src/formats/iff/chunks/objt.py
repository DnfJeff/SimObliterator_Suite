"""
OBJT Chunk - Object Type Information
Port of FreeSO's tso.files/Formats/IFF/Chunks/OBJT.cs

Contains all object types used on a lot with version information.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional
from enum import IntEnum

from ..base import IffChunk, register_chunk
from .objd import OBJDType

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@dataclass
class OBJTEntry:
    """A single object type entry."""
    guid: int = 0               # Object GUID
    unknown1a: int = 0          # Likely number of attributes
    init_tree_version: int = 0  # Init tree version
    unknown2a: int = 0          # OBJD version?
    main_tree_version: int = 0  # Main tree version
    type_id: int = 0            # Type ID (1-based, matches index usually)
    objd_type: OBJDType = OBJDType.UNKNOWN
    name: str = ""
    extra_data: int = 0         # v3+ extra field
    
    def __str__(self) -> str:
        return f"{self.type_id}: {self.name} ({self.guid:08x})"


@register_chunk('OBJT')
@register_chunk('objt')  # Lowercase variant in house files
@dataclass
class OBJT(IffChunk):
    """
    Object type information chunk.
    Lists all object types used on a lot with version tracking.
    """
    entries: List[OBJTEntry] = field(default_factory=list)
    objt_version: int = 2
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read OBJT chunk."""
        zero = stream.read_int32()
        self.objt_version = stream.read_int32()  # Should be 2 or 3
        magic = stream.read_int32()  # "tjbo" (OBJT backwards)
        
        self.entries = []
        
        while stream.has_more:
            entry = OBJTEntry()
            entry.guid = stream.read_uint32()
            
            if entry.guid == 0:
                break
            
            entry.unknown1a = stream.read_uint16()
            entry.init_tree_version = stream.read_uint16()
            entry.unknown2a = stream.read_uint16()
            entry.main_tree_version = stream.read_uint16()
            entry.type_id = stream.read_uint16()
            entry.objd_type = OBJDType(stream.read_uint16())
            entry.name = stream.read_null_terminated_string()
            
            # Pad to short width
            if len(entry.name) % 2 == 0:
                stream.read_byte()
            
            # Version 3+ has extra int32
            if self.objt_version > 2:
                entry.extra_data = stream.read_int32()
            
            self.entries.append(entry)
    
    def get_by_guid(self, guid: int) -> Optional[OBJTEntry]:
        """Find entry by GUID."""
        for entry in self.entries:
            if entry.guid == guid:
                return entry
        return None
    
    def get_by_type_id(self, type_id: int) -> Optional[OBJTEntry]:
        """Find entry by type ID."""
        for entry in self.entries:
            if entry.type_id == type_id:
                return entry
        return None
    
    def __len__(self) -> int:
        return len(self.entries)
