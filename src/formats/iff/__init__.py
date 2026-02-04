"""IFF format package - Interchange File Format for The Sims."""
from .iff_file import IffFile, IffRuntimeInfo
from .base import IffChunk, register_chunk, get_chunk_class, CHUNK_TYPES, ChunkRuntimeState
from .chunks import (
    STR, CTSS, OBJD, OBJDType,
    BHAV, BHAVInstruction,
    SPR, SPR2, SPRFrame, SPR2Frame,
    DGRP, DGRPImage, DGRPSprite, DGRPSpriteFlags,
)

__all__ = [
    'IffFile', 'IffRuntimeInfo',
    'IffChunk', 'register_chunk', 'get_chunk_class', 'CHUNK_TYPES', 'ChunkRuntimeState',
    'STR', 'CTSS', 'OBJD', 'OBJDType',
    'BHAV', 'BHAVInstruction',
    'SPR', 'SPR2', 'SPRFrame', 'SPR2Frame',
    'DGRP', 'DGRPImage', 'DGRPSprite', 'DGRPSpriteFlags',
]
