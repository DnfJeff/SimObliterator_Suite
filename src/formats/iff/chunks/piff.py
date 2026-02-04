"""
PIFF Chunk - IFF Patch Format
Port of FreeSO's tso.files/Formats/IFF/Chunks/PIFF.cs

Contains patches to apply to other IFF files - add, remove, or modify chunks.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional
from enum import IntEnum

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


class PIFFEntryType(IntEnum):
    """Type of patch entry."""
    PATCH = 0
    REMOVE = 1
    ADD = 2


class PIFFPatchMode(IntEnum):
    """Mode for individual patches."""
    REMOVE = 0
    ADD = 1


@dataclass
class PIFFPatch:
    """A single patch operation within an entry."""
    offset: int = 0
    size: int = 0
    mode: PIFFPatchMode = PIFFPatchMode.REMOVE
    data: bytes = field(default_factory=bytes)


@dataclass
class PIFFEntry:
    """A single entry in a PIFF file."""
    chunk_type: str = ""
    chunk_id: int = 0
    new_chunk_id: int = 0
    entry_type: PIFFEntryType = PIFFEntryType.PATCH
    comment: str = ""
    
    chunk_label: str = ""
    chunk_flags: int = 0
    new_data_size: int = 0
    
    patches: List[PIFFPatch] = field(default_factory=list)
    
    def apply(self, src: bytes) -> bytes:
        """Apply patches to source data."""
        result = bytearray(self.new_data_size)
        src_ptr = 0
        dest_ptr = 0
        
        for patch in self.patches:
            # Copy unchanged data up to this patch
            copy_count = patch.offset - dest_ptr
            if copy_count > 0:
                result[dest_ptr:dest_ptr + copy_count] = src[src_ptr:src_ptr + copy_count]
                src_ptr += copy_count
                dest_ptr += copy_count
            
            if patch.mode == PIFFPatchMode.ADD:
                # Insert new data
                result[dest_ptr:dest_ptr + patch.size] = patch.data
                dest_ptr += patch.size
            else:
                # Remove - skip in source
                src_ptr += patch.size
        
        # Copy remainder
        remainder = self.new_data_size - dest_ptr
        if remainder > 0 and src_ptr < len(src):
            result[dest_ptr:dest_ptr + remainder] = src[src_ptr:src_ptr + remainder]
        
        return bytes(result)


PIFF_CURRENT_VERSION = 2


@register_chunk('PIFF')
@dataclass
class PIFF(IffChunk):
    """
    IFF patch format chunk.
    Contains instructions to patch other IFF files.
    """
    piff_version: int = PIFF_CURRENT_VERSION
    source_iff: str = ""
    comment: str = ""
    entries: List[PIFFEntry] = field(default_factory=list)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read PIFF chunk."""
        self.piff_version = stream.read_uint16()
        self.source_iff = stream.read_variable_length_pascal_string()
        
        if self.piff_version > 1:
            self.comment = stream.read_variable_length_pascal_string()
        
        entry_count = stream.read_uint16()
        self.entries = []
        
        for _ in range(entry_count):
            entry = PIFFEntry()
            entry.chunk_type = stream.read_cstring(4)
            entry.chunk_id = stream.read_uint16()
            
            if self.piff_version > 1:
                entry.comment = stream.read_variable_length_pascal_string()
            
            entry.entry_type = PIFFEntryType(stream.read_byte())
            
            if entry.entry_type == PIFFEntryType.PATCH:
                entry.chunk_label = stream.read_variable_length_pascal_string()
                entry.chunk_flags = stream.read_uint16()
                
                if self.piff_version > 0:
                    entry.new_chunk_id = stream.read_uint16()
                else:
                    entry.new_chunk_id = entry.chunk_id
                
                entry.new_data_size = stream.read_uint32()
                
                patch_count = stream.read_uint32()
                entry.patches = []
                last_offset = 0
                
                for _ in range(patch_count):
                    patch = PIFFPatch()
                    # Offset is delta from last
                    patch.offset = last_offset + stream.read_varlen()
                    last_offset = patch.offset
                    patch.size = stream.read_varlen()
                    patch.mode = PIFFPatchMode(stream.read_byte())
                    
                    if patch.mode == PIFFPatchMode.ADD:
                        patch.data = stream.read_bytes(patch.size)
                    
                    entry.patches.append(patch)
            
            self.entries.append(entry)
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write PIFF chunk."""
        stream.write_uint16(PIFF_CURRENT_VERSION)
        stream.write_variable_length_pascal_string(self.source_iff)
        stream.write_variable_length_pascal_string(self.comment)
        stream.write_uint16(len(self.entries))
        
        for entry in self.entries:
            stream.write_cstring(entry.chunk_type, 4)
            stream.write_uint16(entry.chunk_id)
            stream.write_variable_length_pascal_string(entry.comment)
            stream.write_byte(entry.entry_type)
            
            if entry.entry_type == PIFFEntryType.PATCH:
                stream.write_variable_length_pascal_string(entry.chunk_label)
                stream.write_uint16(entry.chunk_flags)
                stream.write_uint16(entry.new_chunk_id)
                stream.write_uint32(entry.new_data_size)
                stream.write_uint32(len(entry.patches))
                
                last_offset = 0
                for patch in entry.patches:
                    stream.write_varlen(patch.offset - last_offset)
                    last_offset = patch.offset
                    stream.write_varlen(patch.size)
                    stream.write_byte(patch.mode)
                    if patch.mode == PIFFPatchMode.ADD:
                        stream.write_bytes(patch.data)
        
        return True
