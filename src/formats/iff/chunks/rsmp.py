"""
rsmp - Resource Map Chunk

The rsmp chunk provides a table of contents for fast resource lookup within an IFF file.
It indexes all other resources by type and ID, enabling O(1) access instead of sequential scanning.

Structure:
- Header (20 bytes)
- Type list with entries for each resource type found in the file
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from ..base import IffChunk, register_chunk

try:
    from ...utils.binary import IoBuffer, ByteOrder
except ImportError:
    from utils.binary import IoBuffer, ByteOrder


@dataclass
class RsmpEntry:
    """Single resource entry in rsmp index."""
    file_offset: int  # Byte offset to resource in file
    resource_id: int  # Resource ID
    flags: int  # Resource flags
    name: str = ""  # Optional name (version 0 only)


@dataclass
class RsmpTypeGroup:
    """All resources of a single type."""
    type_code: str  # 4-char type (OBJD, BHAV, etc.)
    entries: List[RsmpEntry] = field(default_factory=list)


@register_chunk('rsmp')
@dataclass
class RSMP(IffChunk):
    """
    Resource Map chunk for fast resource lookup.
    
    Maps to: FSO.Files.Formats.IFF.RSMP (optional chunk)
    
    Note: rsmp is optional - files work fine without it. Primarily used for:
    - Fast random access to resources
    - Building resource indexes
    - Validation of IFF structure
    """
    
    version: int = 0  # 0 = original, 1 = TSO
    type_groups: List[RsmpTypeGroup] = field(default_factory=list)
    
    # Quick lookup maps
    _type_to_entries: Dict[str, Dict[int, RsmpEntry]] = field(default_factory=dict)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Parse rsmp chunk."""
        try:
            # Skip header (IFF chunk header is handled by IffFile)
            # rsmp internal header: 20 bytes
            reserved = stream.read_uint32()  # 0
            self.version = stream.read_uint32()  # 0 or 1
            identifier = stream.read_cstring(4)  # 'rsmp'
            size = stream.read_uint32()  # Total rsmp size (or 0)
            type_count = stream.read_uint32()  # Number of resource types
            
            # Parse each resource type group
            for _ in range(type_count):
                type_code = stream.read_cstring(4)
                num_entries = stream.read_uint32()
                
                type_group = RsmpTypeGroup(type_code=type_code)
                type_dict: Dict[int, RsmpEntry] = {}
                
                # Parse each entry in this type group
                for _ in range(num_entries):
                    offset = stream.read_uint32()
                    res_id = stream.read_uint16()
                    
                    if self.version == 1:
                        # TSO format: extended ID
                        res_id_high = stream.read_uint16()
                        res_id = (res_id_high << 16) | res_id
                    
                    flags = stream.read_uint16()
                    
                    # Read name (version-dependent)
                    name = ""
                    if self.version == 0:
                        # Original: null-terminated string
                        name = stream.read_cstring()
                    elif self.version == 1:
                        # TSO: Pascal string (length-prefixed)
                        name_len = stream.read_uint8()
                        if name_len > 0:
                            name = stream.read_cstring(name_len)
                    
                    entry = RsmpEntry(
                        file_offset=offset,
                        resource_id=res_id,
                        flags=flags,
                        name=name
                    )
                    
                    type_group.entries.append(entry)
                    type_dict[res_id] = entry
                
                self.type_groups.append(type_group)
                self._type_to_entries[type_code] = type_dict
            
            self.chunk_processed = True
            
        except Exception as e:
            # rsmp is optional - don't fail on parse errors
            self.chunk_processed = False
    
    def get_resource(self, type_code: str, resource_id: int) -> Optional[RsmpEntry]:
        """Look up a resource by type and ID."""
        if type_code in self._type_to_entries:
            return self._type_to_entries[type_code].get(resource_id)
        return None
    
    def get_all_by_type(self, type_code: str) -> List[RsmpEntry]:
        """Get all resources of a specific type."""
        if type_code in self._type_to_entries:
            return list(self._type_to_entries[type_code].values())
        return []
    
    def write(self, iff: 'IffFile', stream) -> bool:
        """Write rsmp chunk - not implemented."""
        return False  # rsmp is read-only
    
    def __str__(self) -> str:
        type_summary = ", ".join(
            f"{tg.type_code}({len(tg.entries)})" 
            for tg in self.type_groups
        )
        return f"rsmp (v{self.version}): {type_summary}"
