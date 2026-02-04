"""Parse and extract OBJf (Object Functions) chunks."""

from dataclasses import dataclass
from typing import List, Optional
from utils.binary import IoBuffer, ByteOrder


@dataclass
class OBJfEntry:
    """Single OBJf entry (guard + action BHAV pair)."""
    guard_bhav_id: int
    action_bhav_id: int


@dataclass
class MinimalOBJf:
    """Minimal OBJf chunk - entry point table."""
    chunk_id: int
    entries: List[OBJfEntry]
    
    def get_all_bhav_ids(self) -> List[int]:
        """Get all non-zero BHAV IDs referenced by this OBJf."""
        bhav_ids = []
        for entry in self.entries:
            if entry.guard_bhav_id > 0:
                bhav_ids.append(entry.guard_bhav_id)
            if entry.action_bhav_id > 0:
                bhav_ids.append(entry.action_bhav_id)
        return bhav_ids


def parse_objf(chunk_data: bytes, chunk_id: int) -> Optional[MinimalOBJf]:
    """
    Parse OBJf chunk into entry list.
    
    OBJf structure:
    - Header (16 bytes): reserved (4), version (4), identifier (4), entry_count (4)
    - Entries: 4 bytes each (guard_id, action_id as uint16)
    """
    if len(chunk_data) < 16:
        return None
    
    try:
        buf = IoBuffer.from_bytes(chunk_data, ByteOrder.LITTLE_ENDIAN)
        
        # Read header
        reserved = buf.read_uint32()
        version = buf.read_uint32()
        identifier = buf.read_bytes(4)
        entry_count = buf.read_uint32()
        
        # Verify identifier
        if identifier != b'fJBO':
            return None
        
        objf = MinimalOBJf(chunk_id=chunk_id, entries=[])
        
        # Read entries
        for i in range(entry_count):
            guard_id = buf.read_uint16()
            action_id = buf.read_uint16()
            entry = OBJfEntry(guard_bhav_id=guard_id, action_bhav_id=action_id)
            objf.entries.append(entry)
        
        return objf
    except Exception as e:
        print(f"Error parsing OBJf: {e}")
        return None
