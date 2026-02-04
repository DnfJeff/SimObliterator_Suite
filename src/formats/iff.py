"""
IFF File Format - Re-export from formats.iff for backward compatibility.

This module re-exports the actual implementations from simobliterator.formats.iff
to maintain backward compatibility with code that imports from simobliterator.iff.

The actual implementations are in:
- formats/iff/base.py: Chunk base classes and registry
- formats/iff/iff_file.py: IFF file parser
- formats/iff/chunks/*.py: All 38 chunk types
- formats/far/far1.py: FAR1 archive support

Reference: FreeSO tso.files/Formats/IFF/ and tso.files/FAR1/

This module eliminates circular import risks by centralizing all IFF-related
exports in the formats subpackage and re-exporting them here.
"""

# Re-export from formats.iff to avoid duplication
from simobliterator.formats.iff import (
    IffChunk, 
    IffFile, 
    IffRuntimeInfo,
    ChunkRuntimeState,
    register_chunk, 
    get_chunk_class, 
    CHUNK_TYPES,
)
from simobliterator.formats.far.far1 import FAR1Archive, FarEntry

# Re-export all chunk types for convenient access
from simobliterator.formats.iff.chunks import (  # noqa: F401
    STR, CTSS, OBJD, OBJDType,
    BHAV, BHAVInstruction,
    SPR, SPR2, SPRFrame, SPR2Frame,
    DGRP, DGRPImage, DGRPSprite, DGRPSpriteFlags,
)

__all__ = [
    # Core classes
    'IffChunk',
    'IffFile',
    'IffRuntimeInfo',
    'ChunkRuntimeState',
    # Registry functions
    'register_chunk',
    'get_chunk_class',
    'CHUNK_TYPES',
    # Archive
    'FAR1Archive',
    'FarEntry',
    # Chunk types
    'STR', 'CTSS', 'OBJD', 'OBJDType',
    'BHAV', 'BHAVInstruction',
    'SPR', 'SPR2', 'SPRFrame', 'SPR2Frame',
    'DGRP', 'DGRPImage', 'DGRPSprite', 'DGRPSpriteFlags',
]
