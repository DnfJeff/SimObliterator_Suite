"""
NBRS Chunk - Neighbors Data
Port of FreeSO's tso.files/Formats/IFF/Chunks/NBRS.cs

NBRS defines all neighbors (Sims) in a neighborhood with their attributes,
relationships, and person data. Used for spawning visitors and phone calls.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer


@dataclass
class Neighbour:
    """A single neighbor/Sim in the neighborhood."""
    unknown1: int = 1
    version: int = 0xA  # 0x4 or 0xA
    unknown3: int = 9
    name: str = ""
    mystery_zero: int = 0
    person_mode: int = 0  # 0/5/9
    person_data: Optional[list[int]] = None  # 88 shorts of person attributes
    
    neighbor_id: int = 0
    guid: int = 0
    unknown_neg_one: int = -1
    
    relationships: dict[int, list[int]] = field(default_factory=dict)
    
    # Runtime
    runtime_index: int = 0
    
    def __str__(self) -> str:
        return self.name or f"Neighbor #{self.neighbor_id}"


@register_chunk("NBRS")
@dataclass
class NBRS(IffChunk):
    """
    Neighbors chunk - all Sims in the neighborhood.
    Maps to: FSO.Files.Formats.IFF.Chunks.NBRS
    """
    version: int = 0x49
    entries: list[Neighbour] = field(default_factory=list)
    neighbor_by_id: dict[int, Neighbour] = field(default_factory=dict)
    default_neighbor_by_guid: dict[int, int] = field(default_factory=dict)
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read NBRS chunk from stream."""
        _pad = io.read_uint32()
        self.version = io.read_uint32()
        magic = io.read_cstring(4, trim_null=False)  # "SRBN"
        count = io.read_uint32()
        
        self.entries = []
        self.neighbor_by_id = {}
        self.default_neighbor_by_guid = {}
        
        for _ in range(count):
            if not io.has_more:
                break
            
            neigh = self._read_neighbor(io)
            if neigh is None:
                continue
                
            self.entries.append(neigh)
            
            if neigh.unknown1 > 0:
                self.neighbor_by_id[neigh.neighbor_id] = neigh
                self.default_neighbor_by_guid[neigh.guid] = neigh.neighbor_id
        
        # Sort by ID and assign runtime indices
        self.entries.sort(key=lambda x: x.neighbor_id)
        for i, entry in enumerate(self.entries):
            entry.runtime_index = i
    
    def _read_neighbor(self, io: 'IoBuffer') -> Optional[Neighbour]:
        """Read a single neighbor entry."""
        neigh = Neighbour()
        
        neigh.unknown1 = io.read_int32()
        if neigh.unknown1 != 1:
            return None  # Not a valid neighbor entry; return None, not empty object
        
        neigh.version = io.read_int32()
        
        if neigh.version == 0xA:
            neigh.unknown3 = io.read_int32()
        
        # Read null-terminated name with padding
        neigh.name = io.read_null_terminated_string()
        if len(neigh.name) % 2 == 0:
            io.read_byte()  # Padding byte
        
        neigh.mystery_zero = io.read_int32()
        neigh.person_mode = io.read_int32()
        
        # Read person data if present
        if neigh.person_mode > 0:
            size = 0xA0 if neigh.version == 0x4 else 0x200
            neigh.person_data = []
            
            for i in range(0, size, 2):
                if len(neigh.person_data) >= 88:
                    # Skip remaining bytes
                    io.read_bytes(size - i)
                    break
                neigh.person_data.append(io.read_int16())
        
        neigh.neighbor_id = io.read_int16()
        neigh.guid = io.read_uint32()
        neigh.unknown_neg_one = io.read_int32()
        
        # Read relationships
        num_relationships = io.read_int32()
        neigh.relationships = {}
        
        for _ in range(num_relationships):
            _key_count = io.read_int32()  # Always 1
            key = io.read_int32()
            
            values = []
            value_count = io.read_int32()
            for _ in range(value_count):
                values.append(io.read_int32())
            
            neigh.relationships[key] = values
        
        return neigh
    
    def get_neighbor(self, neighbor_id: int) -> Optional[Neighbour]:
        """Get a neighbor by their ID."""
        return self.neighbor_by_id.get(neighbor_id)
    
    def get_neighbor_by_guid(self, guid: int) -> Optional[Neighbour]:
        """Get a neighbor by their GUID."""
        neighbor_id = self.default_neighbor_by_guid.get(guid)
        if neighbor_id is not None:
            return self.neighbor_by_id.get(neighbor_id)
        return None
    
    def get_free_id(self) -> int:
        """Find the lowest available neighbor ID."""
        new_id = 1
        for entry in self.entries:
            if entry.neighbor_id == new_id:
                new_id += 1
            elif entry.neighbor_id > new_id:
                break
        return new_id
    
    @property
    def num_neighbors(self) -> int:
        """Number of neighbors in the chunk."""
        return len(self.entries)
    
    def __len__(self) -> int:
        return len(self.entries)
    
    def __iter__(self):
        return iter(self.entries)
    
    def __str__(self) -> str:
        return f"NBRS #{self.chunk_id}: {self.chunk_label} ({self.num_neighbors} neighbors)"
    
    def summary(self) -> str:
        """Get a summary of all neighbors."""
        lines = [f"NBRS #{self.chunk_id}: {self.num_neighbors} neighbors"]
        for n in self.entries[:20]:  # Limit output
            lines.append(f"  [{n.neighbor_id}] {n.name} (GUID: 0x{n.guid:08X})")
        if len(self.entries) > 20:
            lines.append(f"  ... and {len(self.entries) - 20} more")
        return "\n".join(lines)
