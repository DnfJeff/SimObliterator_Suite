"""
IFF File Parser and Writer for The Sims 1 Legacy Collection
Based on FreeSO's reverse-engineered formats and Niotso wiki documentation.

IFF Structure:
- 64-byte header (signature + rsmp offset at bytes 60-63 in big-endian)
- Chunks in sequence, each with 76-byte header + data
- rsmp (resource map) chunk at end

Chunk Header (76 bytes):
- Type: 4 bytes ASCII
- Size: 4 bytes big-endian (size of data, NOT including header)
- ChunkID: 2 bytes big-endian  
- Flags: 2 bytes big-endian
- Label: 64 bytes null-padded ASCII
"""

import struct
from pathlib import Path
from typing import Dict, List, Optional, BinaryIO, Union
from dataclasses import dataclass, field


# IFF Header signatures
IFF_HEADER_2_5 = b"IFF FILE 2.5:TYPE FOLLOWED BY SIZE\x00 JAMIE DOORNBOS & MAXIS 1"
IFF_HEADER_2_0 = b"IFF FILE 2.0:TYPE FOLLOWED BY SIZE\x00 JAMIE DOORNBOS & MAXIS 1996\x00"


@dataclass
class IffChunk:
    """Represents a single chunk in an IFF file."""
    chunk_type: str  # 4-char type code
    chunk_id: int    # Chunk ID
    flags: int       # Flags (usually 0x0000 or 0x0010)
    label: str       # 64-byte label (comment)
    data: bytes      # Raw chunk data
    offset: int = 0  # Offset in file (for tracking)
    
    @property
    def size(self) -> int:
        """Size of chunk data (not including 76-byte header)."""
        return len(self.data)
    
    def to_bytes(self) -> bytes:
        """Serialize chunk to bytes (header + data)."""
        # Chunk header is 76 bytes
        header = bytearray(76)
        
        # Type (4 bytes ASCII)
        header[0:4] = self.chunk_type.encode('latin-1')[:4].ljust(4, b'\x00')
        
        # Size (4 bytes big-endian)
        struct.pack_into('>I', header, 4, len(self.data))
        
        # Reserved/padding (4 bytes)
        header[8:12] = b'\x00\x00\x00\x00'
        
        # ChunkID (2 bytes big-endian)
        struct.pack_into('>H', header, 12, self.chunk_id)
        
        # Flags (2 bytes big-endian)
        struct.pack_into('>H', header, 14, self.flags)
        
        # Label (64 bytes, null-padded)
        label_bytes = self.label.encode('latin-1', errors='replace')[:64]
        header[12:76] = label_bytes.ljust(64, b'\x00')
        
        # Wait - re-read the format. Let me fix the header layout:
        # Offset 0-3: Type
        # Offset 4-7: Size (big-endian)
        # Offset 8-9: (Unknown/reserved)
        # Offset 10-11: (Unknown/reserved)  
        # Offset 12-13: ChunkID (big-endian)
        # Offset 14-15: Flags (big-endian)
        # Offset 16-75: Label (actually starts at 12 based on Niotso...)
        
        # Let me check Niotso format again:
        # Type - 4 bytes
        # Size - 4 bytes (big-endian, entire chunk including header)
        # ChunkID - 2 bytes 
        # Flags - 2 bytes
        # Label - 64 bytes
        # = 76 bytes header
        
        # Rebuild correctly:
        header = bytearray(76)
        header[0:4] = self.chunk_type.encode('latin-1')[:4].ljust(4, b'\x00')
        struct.pack_into('>I', header, 4, len(self.data))  # Just data size, not total
        struct.pack_into('>H', header, 12, self.chunk_id)
        struct.pack_into('>H', header, 14, self.flags)
        label_bytes = self.label.encode('latin-1', errors='replace')[:64]
        header[12:76] = b'\x00\x00' + struct.pack('>H', self.chunk_id) + struct.pack('>H', self.flags) + label_bytes.ljust(60, b'\x00')
        
        # Actually simplify - based on observed data:
        header = bytearray(76)
        header[0:4] = self.chunk_type.encode('latin-1')[:4]
        struct.pack_into('>I', header, 4, len(self.data))
        # Bytes 8-11 seem to be zeros
        struct.pack_into('>H', header, 12, self.chunk_id)
        struct.pack_into('>H', header, 14, self.flags)
        label_bytes = self.label.encode('latin-1', errors='replace')[:60]
        header[16:76] = label_bytes.ljust(60, b'\x00')
        
        return bytes(header) + self.data


class IffFile:
    """
    Parser and writer for IFF (Interchange File Format) files.
    Used by The Sims 1 for save files, objects, and game data.
    """
    
    def __init__(self, filepath: Optional[Union[str, Path]] = None):
        self.filepath: Optional[Path] = Path(filepath) if filepath else None
        self.header: bytes = b''
        self.chunks: List[IffChunk] = []
        self.rsmp_offset: int = 0
        self._chunks_by_type: Dict[str, List[IffChunk]] = {}
        self._chunks_by_id: Dict[int, IffChunk] = {}
        
        if filepath:
            self.load(filepath)
    
    def load(self, filepath: Union[str, Path]) -> None:
        """Load and parse an IFF file."""
        self.filepath = Path(filepath)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        self._parse(data)
    
    def _parse(self, data: bytes) -> None:
        """Parse IFF file from bytes."""
        if len(data) < 64:
            raise ValueError("File too small to be valid IFF")
        
        # Parse header (64 bytes)
        self.header = data[:64]
        
        # Get rsmp offset from last 4 bytes of header (big-endian)
        self.rsmp_offset = struct.unpack('>I', data[60:64])[0]
        
        # Parse chunks
        self.chunks = []
        self._chunks_by_type = {}
        self._chunks_by_id = {}
        
        offset = 64
        while offset < len(data) - 8:  # Need at least 8 bytes for type+size
            # Check if we're at or past rsmp
            if offset >= self.rsmp_offset:
                # Parse rsmp specially
                chunk = self._parse_chunk(data, offset)
                if chunk:
                    self.chunks.append(chunk)
                break
            
            chunk = self._parse_chunk(data, offset)
            if chunk is None:
                break
            
            self.chunks.append(chunk)
            
            # Index by type
            if chunk.chunk_type not in self._chunks_by_type:
                self._chunks_by_type[chunk.chunk_type] = []
            self._chunks_by_type[chunk.chunk_type].append(chunk)
            
            # Index by ID (may have collisions across types)
            self._chunks_by_id[chunk.chunk_id] = chunk
            
            # Move to next chunk
            offset += 76 + chunk.size
    
    def _parse_chunk(self, data: bytes, offset: int) -> Optional[IffChunk]:
        """Parse a single chunk at the given offset."""
        if offset + 76 > len(data):
            return None
        
        # Read header
        chunk_type = data[offset:offset+4].decode('latin-1', errors='replace')
        chunk_size = struct.unpack('>I', data[offset+4:offset+8])[0]
        chunk_id = struct.unpack('>H', data[offset+12:offset+14])[0]
        flags = struct.unpack('>H', data[offset+14:offset+16])[0]
        label = data[offset+16:offset+76].rstrip(b'\x00').decode('latin-1', errors='replace')
        
        # Sanity check
        if offset + 76 + chunk_size > len(data):
            # Truncated chunk - read what we can
            chunk_size = len(data) - offset - 76
            if chunk_size < 0:
                return None
        
        # Read data
        chunk_data = data[offset+76:offset+76+chunk_size]
        
        return IffChunk(
            chunk_type=chunk_type,
            chunk_id=chunk_id,
            flags=flags,
            label=label,
            data=chunk_data,
            offset=offset
        )
    
    def get_chunks_by_type(self, chunk_type: str) -> List[IffChunk]:
        """Get all chunks of a specific type."""
        return self._chunks_by_type.get(chunk_type, [])
    
    def get_chunk(self, chunk_type: str, chunk_id: int) -> Optional[IffChunk]:
        """Get a specific chunk by type and ID."""
        for chunk in self.get_chunks_by_type(chunk_type):
            if chunk.chunk_id == chunk_id:
                return chunk
        return None
    
    def add_chunk(self, chunk: IffChunk) -> None:
        """Add a new chunk to the file."""
        self.chunks.append(chunk)
        
        if chunk.chunk_type not in self._chunks_by_type:
            self._chunks_by_type[chunk.chunk_type] = []
        self._chunks_by_type[chunk.chunk_type].append(chunk)
        self._chunks_by_id[chunk.chunk_id] = chunk
    
    def remove_chunk(self, chunk: IffChunk) -> None:
        """Remove a chunk from the file."""
        if chunk in self.chunks:
            self.chunks.remove(chunk)
        if chunk.chunk_type in self._chunks_by_type:
            if chunk in self._chunks_by_type[chunk.chunk_type]:
                self._chunks_by_type[chunk.chunk_type].remove(chunk)
        if self._chunks_by_id.get(chunk.chunk_id) == chunk:
            del self._chunks_by_id[chunk.chunk_id]
    
    def _build_rsmp(self) -> bytes:
        """Build resource map (rsmp) chunk data."""
        # rsmp format (little-endian data):
        # 4 bytes: Reserved (0)
        # 4 bytes: Version (0 for TS1, 1 for TSO)
        # 4 bytes: Magic "pmsr" (rsmp reversed) or 0
        # 4 bytes: Size (can be 0)
        # 4 bytes: Number of unique chunk types
        # For each type:
        #   4 bytes: Type (byte-swapped)
        #   4 bytes: Count of chunks of this type
        #   For each chunk:
        #     4 bytes: Offset from file start
        #     2 bytes: ChunkID (byte-swapped for v0, 4 bytes for v1)
        #     2 bytes: Flags (byte-swapped)
        #     Variable: Label (null-terminated, padded to even length for v0)
        
        # Group chunks by type (excluding rsmp itself)
        chunks_by_type: Dict[str, List[tuple]] = {}  # type -> [(offset, id, flags, label), ...]
        
        current_offset = 64  # Start after header
        for chunk in self.chunks:
            if chunk.chunk_type == 'rsmp':
                continue
            
            ctype = chunk.chunk_type
            if ctype not in chunks_by_type:
                chunks_by_type[ctype] = []
            
            chunks_by_type[ctype].append((
                current_offset,
                chunk.chunk_id,
                chunk.flags,
                chunk.label
            ))
            
            current_offset += 76 + len(chunk.data)
        
        # Build rsmp data
        rsmp_data = bytearray()
        
        # Header
        rsmp_data.extend(struct.pack('<I', 0))  # Reserved
        rsmp_data.extend(struct.pack('<I', 0))  # Version 0 for TS1
        rsmp_data.extend(b'pmsr')  # Magic
        rsmp_data.extend(struct.pack('<I', 0))  # Size placeholder
        rsmp_data.extend(struct.pack('<I', len(chunks_by_type)))  # Type count
        
        # For each chunk type
        for ctype, chunk_list in chunks_by_type.items():
            # Type (byte-swapped)
            rsmp_data.extend(ctype[::-1].encode('latin-1'))
            rsmp_data.extend(struct.pack('<I', len(chunk_list)))  # Count
            
            for offset, chunk_id, flags, label in chunk_list:
                rsmp_data.extend(struct.pack('<I', offset))  # Offset
                rsmp_data.extend(struct.pack('<H', chunk_id))  # ID (swapped)
                rsmp_data.extend(struct.pack('<H', flags))  # Flags
                
                # Label: null-terminated, padded to even length
                label_bytes = label.encode('latin-1', errors='replace')
                rsmp_data.extend(label_bytes)
                rsmp_data.append(0)  # Null terminator
                if len(label_bytes) % 2 == 0:
                    rsmp_data.append(0)  # Pad to even
        
        return bytes(rsmp_data)
    
    def save(self, filepath: Optional[Union[str, Path]] = None) -> None:
        """Save the IFF file."""
        if filepath is None:
            filepath = self.filepath
        if filepath is None:
            raise ValueError("No filepath specified")
        
        filepath = Path(filepath)
        
        # Build output
        output = bytearray()
        
        # Placeholder header (we'll update rsmp offset later)
        output.extend(self.header[:60])
        output.extend(b'\x00\x00\x00\x00')  # rsmp offset placeholder
        
        # Write chunks (excluding rsmp)
        for chunk in self.chunks:
            if chunk.chunk_type == 'rsmp':
                continue
            output.extend(chunk.to_bytes())
        
        # Build and write rsmp
        rsmp_offset = len(output)
        rsmp_data = self._build_rsmp()
        rsmp_chunk = IffChunk(
            chunk_type='rsmp',
            chunk_id=0,
            flags=0,
            label='',
            data=rsmp_data
        )
        output.extend(rsmp_chunk.to_bytes())
        
        # Update rsmp offset in header (big-endian)
        struct.pack_into('>I', output, 60, rsmp_offset)
        
        # Write to file
        with open(filepath, 'wb') as f:
            f.write(output)
    
    def __repr__(self) -> str:
        return f"IffFile({self.filepath}, {len(self.chunks)} chunks)"
