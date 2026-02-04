"""
IFF File Parser
Port of FreeSO's tso.files/Formats/IFF/IffFile.cs

IFF (Interchange File Format) is a chunk-based file format for binary 
resource data used by The Sims.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TypeVar, Type, Iterator
from io import BytesIO

try:
    # Try absolute import (preferred)
    from utils.binary import IoBuffer, ByteOrder
except ImportError:
    # Fall back to relative import if in different context
    from ...utils.binary import IoBuffer, ByteOrder

from .base import IffChunk, get_chunk_class, CHUNK_TYPES


T = TypeVar('T', bound=IffChunk)


@dataclass
class IffRuntimeInfo:
    """Runtime information about an IFF file."""
    dirty: bool = False
    use_count: int = 0


@dataclass
class IffFile:
    """
    IFF file container.
    Maps to: FSO.Files.Formats.IFF.IffFile
    """
    filename: str = ""
    retain_chunk_data: bool = False
    runtime_info: IffRuntimeInfo = field(default_factory=IffRuntimeInfo)
    
    # Chunks organized by type and ID
    _chunks_by_id: dict[type, dict[int, IffChunk]] = field(default_factory=dict)
    _chunks_by_type: dict[type, list[IffChunk]] = field(default_factory=list)
    _all_chunks: list[IffChunk] = field(default_factory=list)
    
    # IFF header info
    _is_valid: bool = False
    
    @classmethod
    def read(cls, path: str) -> 'IffFile':
        """Read an IFF file from disk."""
        iff = cls(filename=path)
        iff._chunks_by_id = {}
        iff._chunks_by_type = {}
        iff._all_chunks = []
        
        io = IoBuffer.from_file(path, ByteOrder.BIG_ENDIAN)
        iff._read_from_stream(io)
        
        return iff
    
    @classmethod
    def from_bytes(cls, data: bytes, filename: str = "") -> 'IffFile':
        """Read an IFF from bytes."""
        iff = cls(filename=filename)
        iff._chunks_by_id = {}
        iff._chunks_by_type = {}
        iff._all_chunks = []
        
        io = IoBuffer.from_bytes(data, ByteOrder.BIG_ENDIAN)
        iff._read_from_stream(io)
        
        return iff
    
    def _read_from_stream(self, io: IoBuffer):
        """Parse IFF structure from stream."""
        # Read header: "IFF FILE 2.5:TYPE FOLLOWED BY SIZE\0 JAMIE DOORNBOS & MAXIS 1"
        # Header is exactly 60 bytes
        header = io.read_cstring(60, trim_null=True)
        
        if not header.startswith("IFF FILE"):
            raise ValueError(f"Invalid IFF header: {header[:20]}")
        
        self._is_valid = True
        
        # Read resource map offset (4 bytes, not used but must skip)
        _rsmp_offset = io.read_uint32()
        
        # Now at byte 64, chunks start here
        while io.has_more:
            try:
                chunk = self._read_chunk(io)
                if chunk:
                    self._add_chunk(chunk)
            except Exception as e:
                # Hit end of file or corrupt chunk
                break
    
    def _read_chunk(self, io: IoBuffer) -> Optional[IffChunk]:
        """Read a single chunk from stream."""
        if not io.has_bytes(12):
            return None
        
        start_pos = io.position
        
        # Read chunk header (big endian)
        type_code = io.read_cstring(4, trim_null=False)
        chunk_size = io.read_uint32()
        chunk_id = io.read_uint16()
        chunk_flags = io.read_uint16()
        
        # Read label (64 bytes, null-terminated)
        chunk_label = io.read_cstring(64, trim_null=True)
        
        # Calculate data size (size includes header)
        header_size = 76  # 4 + 4 + 2 + 2 + 64
        data_size = chunk_size - header_size
        
        if data_size < 0:
            return None
        
        # Create appropriate chunk type
        chunk_class = get_chunk_class(type_code)
        chunk = chunk_class()
        chunk.chunk_id = chunk_id
        chunk.chunk_flags = chunk_flags
        chunk.chunk_type = type_code
        chunk.chunk_label = chunk_label
        
        # Read chunk data
        if data_size > 0:
            chunk_data = io.read_bytes(data_size)
            
            if self.retain_chunk_data:
                chunk.original_data = chunk_data
            
            # Parse chunk-specific data
            chunk_io = IoBuffer.from_bytes(chunk_data, ByteOrder.LITTLE_ENDIAN)
            try:
                chunk.read(self, chunk_io)
                chunk.chunk_processed = True
            except Exception as e:
                # Store raw data if parsing fails
                chunk.chunk_data = chunk_data
        
        return chunk
    
    def _add_chunk(self, chunk: IffChunk):
        """Add a chunk to the internal collections."""
        chunk_type = type(chunk)
        
        # Add to type dict
        if chunk_type not in self._chunks_by_type:
            self._chunks_by_type[chunk_type] = []
        self._chunks_by_type[chunk_type].append(chunk)
        
        # Add to ID dict
        if chunk_type not in self._chunks_by_id:
            self._chunks_by_id[chunk_type] = {}
        self._chunks_by_id[chunk_type][chunk.chunk_id] = chunk
        
        # Add to all chunks
        self._all_chunks.append(chunk)
    
    def get(self, chunk_type: Type[T], chunk_id: int) -> Optional[T]:
        """Get a chunk by type and ID."""
        type_dict = self._chunks_by_id.get(chunk_type, {})
        return type_dict.get(chunk_id)
    
    def get_all(self, chunk_type: Type[T]) -> list[T]:
        """Get all chunks of a type."""
        return self._chunks_by_type.get(chunk_type, [])
    
    def get_by_type_code(self, type_code: str) -> list[IffChunk]:
        """Get all chunks matching a 4-char type code."""
        return [c for c in self._all_chunks if c.chunk_type == type_code]
    
    @property
    def chunks(self) -> list[IffChunk]:
        """All chunks in the file."""
        return self._all_chunks
    
    def __iter__(self) -> Iterator[IffChunk]:
        return iter(self._all_chunks)
    
    def __len__(self) -> int:
        return len(self._all_chunks)
    
    def summary(self) -> str:
        """Get a summary of chunks in this file."""
        lines = [f"IFF: {self.filename}", f"Chunks: {len(self._all_chunks)}"]
        
        # Count by type
        type_counts = {}
        for chunk in self._all_chunks:
            code = chunk.chunk_type
            type_counts[code] = type_counts.get(code, 0) + 1
        
        for code, count in sorted(type_counts.items()):
            lines.append(f"  {code}: {count}")
        
        return "\n".join(lines)
