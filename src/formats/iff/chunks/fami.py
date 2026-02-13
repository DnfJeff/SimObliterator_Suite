"""
FAMI Chunk - Family Data
Port of FreeSO's tso.files/Formats/IFF/Chunks/FAMI.cs

FAMI defines a single family in the neighborhood with properties like
budget, house assignment, and member GUIDs.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


# Family flags (Unknown field)
FAMI_IN_HOUSE = 1
FAMI_UNKNOWN_2 = 2
FAMI_UNKNOWN_4 = 4
FAMI_USER_CREATED = 8
FAMI_IN_CAS = 16


@register_chunk("FAMI")
@dataclass
class FAMI(IffChunk):
    """
    Family data chunk - defines a household.
    Maps to: FSO.Files.Formats.IFF.Chunks.FAMI
    """
    version: int = 0x9
    house_number: int = 0
    family_number: int = 0  # Unique ID, -1 for townies
    budget: int = 0
    value_in_arch: int = 0  # Value of architecture/house
    family_friends: int = 0
    unknown: int = 0  # Flags: 1=in house, 8=user created, 16=in CAS
    family_guids: list[int] = field(default_factory=list)
    
    # Runtime only - don't save
    runtime_subset: list[int] = field(default_factory=list)
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read FAMI chunk from stream."""
        _pad = io.read_uint32()
        self.version = io.read_uint32()
        magic = io.read_cstring(4, trim_null=False)  # "IMAF"
        
        self.house_number = io.read_int32()
        self.family_number = io.read_int32()
        self.budget = io.read_int32()
        self.value_in_arch = io.read_int32()
        self.family_friends = io.read_int32()
        self.unknown = io.read_int32()
        
        num_members = io.read_int32()
        self.family_guids = []
        for _ in range(num_members):
            self.family_guids.append(io.read_uint32())
        
        # Try to read trailing zeros (some versions have 3, some have 4)
        try:
            for _ in range(4):
                if not io.has_more:
                    break
                io.read_int32()
        except Exception:
            pass
    
    def write(self, iff: 'IffFile', io: 'IoWriter') -> bool:
        """Write FAMI chunk to stream."""
        io.write_uint32(0)  # Padding
        io.write_uint32(self.version)
        io.write_bytes(b'IMAF')  # Magic
        
        io.write_int32(self.house_number)
        io.write_int32(self.family_number)
        io.write_int32(self.budget)
        io.write_int32(self.value_in_arch)
        io.write_int32(self.family_friends)
        io.write_int32(self.unknown)
        
        io.write_int32(len(self.family_guids))
        for guid in self.family_guids:
            io.write_uint32(guid)
        
        # Write 4 trailing zeros
        for _ in range(4):
            io.write_int32(0)
        
        return True
    
    def select_whole_family(self):
        """Select all family members for runtime."""
        self.runtime_subset = list(self.family_guids)
    
    def select_one_member(self, guid: int):
        """Select a single family member for runtime."""
        self.runtime_subset = [guid]
    
    @property
    def is_townie(self) -> bool:
        """Check if this is a townie family (no house)."""
        return self.family_number == -1
    
    @property
    def is_user_created(self) -> bool:
        """Check if family was created by user in CAS."""
        return bool(self.unknown & FAMI_USER_CREATED)
    
    @property
    def is_in_house(self) -> bool:
        """Check if family is currently in a house."""
        return bool(self.unknown & FAMI_IN_HOUSE)
    
    @property
    def num_members(self) -> int:
        """Number of family members."""
        return len(self.family_guids)
    
    def __str__(self) -> str:
        status = "townie" if self.is_townie else f"house {self.house_number}"
        return f"FAMI #{self.chunk_id}: {self.chunk_label} ({self.num_members} members, {status}, ${self.budget})"
