"""
DBPF Format - Database Packed File (Sims 2+ format)

Reference: FreeSO's tso.files/Formats/DBPF/DBPFFile.cs

The DBPF format is used by The Sims Online, SimCity 4, The Sims 2, Spore,
The Sims 3, and SimCity 2013. It's a more advanced archive format than FAR
with support for metadata and resource indexing.

Structure:
  Header:
    - Magic: "DBPF" (4 bytes)
    - Major Version (4 bytes)
    - Minor Version (4 bytes)
    - Unknown (12 bytes)
    - [Version-specific fields...]
  
  Index:
    - Multiple entries with TypeID, GroupID, InstanceID
    - File offset and size for each entry
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from enum import IntEnum
from io import BytesIO, IOBase

try:
    from utils.binary import IoBuffer, ByteOrder
except ImportError:
    # Fallback for relative imports
    from utils.binary import IoBuffer, ByteOrder


class DBPFTypeID(IntEnum):
    """DBPF Resource Type IDs (common ones from The Sims series)"""
    
    # Object/IFF related
    OBJD = 0xC0C0C001  # Object definition
    BHAV = 0xC0C0C002  # Behavior
    TRCN = 0xC0C0C003  # Constant labels
    TTAB = 0xC0C0C004  # Tree table
    TPRP = 0xC0C0C005  # Tree properties
    DGRP = 0xC0C0C006  # Draw group
    
    # Strings and UI
    STR = 0xC0C0C008   # String table
    CTSS = 0xC0C0C009  # Catalog strings
    TTAS = 0xC0C0C00A  # Tree table strings
    
    # Graphics
    SPR2 = 0xC0C0C00D  # Sprite (type B)
    SPR = 0xC0C0C00E   # Sprite (type A)
    PALT = 0xC0C0C00F  # Palette
    
    # Data
    BCON = 0xC0C0C010  # Behavioral constants
    SLOT = 0xC0C0C011  # Slot definitions
    FCNS = 0xC0C0C015  # Function constants
    
    # Career/Job
    CARR = 0xC0C0C018  # Career definition
    
    # Audio
    FWAV = 0xC0C0C01F  # File WAV reference
    HIT = 0xC0C0C020   # Sound events
    HSM = 0xC0C0C021   # Audio state machine
    
    # Other
    GLOB = 0xC0C0C028  # Global reference
    TREE = 0xC0C0C029  # Tree structure


class DBPFGroupID(IntEnum):
    """DBPF Resource Group IDs"""
    
    GLOBAL = 0x00000000
    NEIGHBORS = 0xFFFFFFFF


@dataclass
class DBPFEntry:
    """A single resource entry in a DBPF archive"""
    
    type_id: int = 0          # Resource type (DBPFTypeID)
    group_id: int = 0         # Resource group
    instance_id: int = 0      # Resource instance/GUID
    file_offset: int = 0      # Offset to data in archive
    file_size: int = 0        # Size of data


class DBPFFile:
    """
    DBPF (Database Packed File) reader
    
    Reference: FreeSO's tso.files/Formats/DBPF/DBPFFile.cs
    
    Features:
    - Supports DBPF v1.0 through v2.0
    - Efficient indexing by TypeID, GroupID, InstanceID
    - Compatible with The Sims 2, SimCity 4, and later
    """
    
    MAGIC = "DBPF"
    
    def __init__(self, path: Optional[str] = None):
        """
        Create a DBPF instance
        
        Args:
            path: Path to a DBPF file to read (optional)
        """
        self.date_created: int = 0
        self.date_modified: int = 0
        
        self._index_major_version: int = 0
        self._num_entries: int = 0
        self._entries_list: List[DBPFEntry] = []
        self._entries_by_id: Dict[int, DBPFEntry] = {}
        self._entries_by_type: Dict[int, List[DBPFEntry]] = {}
        self._io_buffer: Optional[IoBuffer] = None
        
        if path:
            with open(path, 'rb') as f:
                self.read(f)
    
    def read(self, stream: IOBase) -> None:
        """
        Read a DBPF archive from a stream
        
        Args:
            stream: File stream to read from
        """
        # Reset state
        self._entries_by_id = {}
        self._entries_list = []
        self._entries_by_type = {}
        
        # Create IO buffer
        io = IoBuffer.from_stream(stream, ByteOrder.LITTLE_ENDIAN)
        self._io_buffer = io
        
        # Read magic
        magic = io.read_cstring(4)
        if magic != self.MAGIC:
            raise ValueError(f"Not a DBPF file: {magic}")
        
        # Read version
        major_version = io.read_uint32()
        minor_version = io.read_uint32()
        version = major_version + (minor_version / 10.0)
        
        # Skip unknown (12 bytes)
        io.skip(12)
        
        # Version-specific fields
        if version == 1.0:
            self.date_created = io.read_int32()
            self.date_modified = io.read_int32()
        
        if version < 2.0:
            self._index_major_version = io.read_uint32()
        
        # Read index information
        self._num_entries = io.read_uint32()
        
        index_offset = 0
        if version < 2.0:
            index_offset = io.read_uint32()
        
        index_size = io.read_uint32()
        
        # Read trash entries (v1 only)
        if version < 2.0:
            trash_entry_count = io.read_uint32()
            trash_index_offset = io.read_uint32()
            trash_index_size = io.read_uint32()
            index_minor = io.read_uint32()
        
        # Version 2.0 specific
        elif version == 2.0:
            index_minor = io.read_uint32()
            index_offset = io.read_uint32()
            io.skip(4)
        
        # Skip padding (32 bytes)
        io.skip(32)
        
        # Seek to index and read entries
        io.seek(index_offset)
        
        for _ in range(self._num_entries):
            entry = DBPFEntry()
            entry.type_id = io.read_uint32()
            entry.group_id = io.read_uint32()
            entry.instance_id = io.read_uint32()
            entry.file_offset = io.read_uint32()
            entry.file_size = io.read_uint32()
            
            self._entries_list.append(entry)
            
            # Build lookup tables
            entry_id = (entry.instance_id << 32) + entry.type_id
            if entry_id not in self._entries_by_id:
                self._entries_by_id[entry_id] = entry
            
            if entry.type_id not in self._entries_by_type:
                self._entries_by_type[entry.type_id] = []
            
            self._entries_by_type[entry.type_id].append(entry)
    
    def get_entry(self, entry: DBPFEntry) -> bytes:
        """
        Get data for a DBPF entry
        
        Args:
            entry: DBPFEntry to retrieve
            
        Returns:
            Raw data bytes
        """
        if not self._io_buffer:
            raise RuntimeError("No file loaded")
        
        self._io_buffer.seek(entry.file_offset)
        return self._io_buffer.read_bytes(entry.file_size)
    
    def get_entry_by_id(self, entry_id: int) -> bytes:
        """
        Get entry data by combined ID (InstanceID + TypeID)
        
        Args:
            entry_id: Combined entry ID
            
        Returns:
            Raw data bytes
        """
        if entry_id not in self._entries_by_id:
            raise KeyError(f"Entry not found: {entry_id:08X}")
        
        return self.get_entry(self._entries_by_id[entry_id])
    
    def get_entries_by_type(self, type_id: int) -> List[bytes]:
        """
        Get all entries of a specific type
        
        Args:
            type_id: Resource type ID
            
        Returns:
            List of data for all entries of that type
        """
        if type_id not in self._entries_by_type:
            return []
        
        result = []
        for entry in self._entries_by_type[type_id]:
            result.append(self.get_entry(entry))
        
        return result
    
    @property
    def entries(self) -> List[DBPFEntry]:
        """Get all entries"""
        return self._entries_list.copy()
    
    @property
    def num_entries(self) -> int:
        """Get number of entries"""
        return len(self._entries_list)
    
    def close(self) -> None:
        """Close the DBPF file"""
        if self._io_buffer:
            self._io_buffer = None


__all__ = [
    'DBPFTypeID',
    'DBPFGroupID',
    'DBPFEntry',
    'DBPFFile',
]
