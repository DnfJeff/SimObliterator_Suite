"""
IFF Chunk Base Class
Port of FreeSO's tso.files/Formats/IFF/AbstractIffChunk.cs
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .iff_file import IffFile
    from ..utils.binary import IoBuffer


class ChunkRuntimeState(Enum):
    NORMAL = 0
    MODIFIED = 1
    DELETE = 2
    PATCHED = 3


@dataclass
class IffChunk(ABC):
    """
    Base class for all IFF chunks.
    Maps to: FSO.Files.Formats.IFF.IffChunk
    """
    chunk_id: int = 0
    chunk_flags: int = 0
    chunk_type: str = ""
    chunk_label: str = ""
    chunk_processed: bool = False
    original_data: Optional[bytes] = None
    original_id: int = 0
    added_by_patch: bool = False
    original_label: str = ""
    chunk_data: Optional[bytes] = None
    runtime_info: ChunkRuntimeState = ChunkRuntimeState.NORMAL
    
    @abstractmethod
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read chunk data from stream."""
        pass
    
    def write(self, iff: 'IffFile', stream) -> bool:
        """
        Write chunk data to stream. Returns True if written.
        
        ⚠️ IMPORTANT: Write operations are implemented in many chunks but have NOT
        been tested end-to-end for Phase 4-5 (save file editing). Use with caution.
        See WRITE_OPERATIONS_STATUS.md for testing status and known limitations.
        
        Default implementation returns False (read-only chunk).
        """
        return False
    
    def __str__(self) -> str:
        return f"#{self.chunk_id} {self.chunk_label}"


# Chunk type registry - maps 4-char codes to chunk classes
CHUNK_TYPES: dict[str, type] = {}


def register_chunk(type_code: str):
    """Decorator to register a chunk type."""
    def decorator(cls):
        CHUNK_TYPES[type_code] = cls
        return cls
    return decorator


def get_chunk_class(type_code: str) -> type:
    """Get chunk class for a type code, or UnknownChunk if not found."""
    return CHUNK_TYPES.get(type_code, UnknownChunk)


@dataclass
class UnknownChunk(IffChunk):
    """Fallback for unrecognized chunk types."""
    raw_data: bytes = field(default_factory=bytes)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        # Just store raw data
        self.raw_data = stream.read_bytes(stream.stream.read())
    
    def write(self, iff: 'IffFile', stream) -> bool:
        stream.write_bytes(self.raw_data)
        return True
