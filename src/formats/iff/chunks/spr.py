"""
SPR/SPR2 Chunks - Sprite Graphics
Port of FreeSO's tso.files/Formats/IFF/Chunks/SPR.cs and SPR2.cs

SPR = Original paletted sprites (no z-buffer)
SPR2 = Enhanced sprites with z-buffer and alpha support
"""

from dataclasses import dataclass, field
from enum import IntFlag
from typing import TYPE_CHECKING, Optional, Tuple

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer


@dataclass
class SPRFrame:
    """
    A single sprite frame from SPR chunk.
    Contains paletted pixel data.
    """
    width: int = 0
    height: int = 0
    flags: int = 0
    palette_id: int = 0
    transparent_index: int = 0
    position_x: int = 0
    position_y: int = 0
    
    # Raw data (RLE encoded)
    raw_data: bytes = field(default_factory=bytes)
    # Decoded palette indices
    pixel_indices: Optional[bytes] = None
    
    def decode(self, palette: Optional[list] = None) -> Optional[bytes]:
        """
        Decode RLE sprite data to palette indices.
        Returns bytes where each byte is a palette index.
        """
        if not self.raw_data or self.width == 0 or self.height == 0:
            return None
        
        # SPR uses simple RLE encoding
        # This is a simplified decoder - full impl would handle all edge cases
        result = bytearray(self.width * self.height)
        # TODO: Full RLE decode implementation
        self.pixel_indices = bytes(result)
        return self.pixel_indices


@dataclass
class SPR2Frame:
    """
    A single sprite frame from SPR2 chunk.
    Enhanced format with z-buffer and alpha channel support.
    """
    width: int = 0
    height: int = 0
    flags: int = 0
    palette_id: int = 0
    transparent_index: int = 0
    position_x: int = 0
    position_y: int = 0
    
    # Raw encoded data
    raw_data: bytes = field(default_factory=bytes)
    
    # Decoded data
    pixel_data: Optional[bytes] = None    # RGBA pixels
    zbuffer_data: Optional[bytes] = None  # Z-buffer values
    pal_data: Optional[bytes] = None      # Palette indices
    
    # Flags
    HAS_ALPHA = 0x01
    HAS_ZBUFFER = 0x02
    
    @property
    def has_alpha(self) -> bool:
        return bool(self.flags & self.HAS_ALPHA)
    
    @property
    def has_zbuffer(self) -> bool:
        return bool(self.flags & self.HAS_ZBUFFER)


@register_chunk("SPR#")
@dataclass
class SPR(IffChunk):
    """
    Sprite chunk - paletted sprites without z-buffer.
    Maps to: FSO.Files.Formats.IFF.Chunks.SPR
    
    Used for simpler graphics, UI elements, etc.
    """
    frames: list[SPRFrame] = field(default_factory=list)
    palette_id: int = 0
    version: int = 0
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read SPR chunk from stream."""
        # Check endianness from version
        version1 = io.read_uint16()
        version2 = io.read_uint16()
        
        if version1 == 0:
            # Big endian
            self.version = ((version2 | 0xFF00) >> 8) | ((version2 & 0xFF) << 8)
            # Note: Would need to switch IoBuffer to big endian here
        else:
            self.version = version1
        
        sprite_count = io.read_uint32()
        self.palette_id = io.read_uint32()
        
        self.frames = []
        
        if self.version != 1001:
            # Version with offset table
            offsets = [io.read_uint32() for _ in range(sprite_count)]
            
            for i, offset in enumerate(offsets):
                frame = SPRFrame()
                # Calculate size from next offset or end
                if i + 1 < len(offsets):
                    size = offsets[i + 1] - offset
                else:
                    size = 0  # Read to end
                
                # Store raw data for later decoding
                io.seek(offset)
                frame.raw_data = io.read_bytes(size) if size > 0 else b''
                self.frames.append(frame)
        else:
            # Streaming version
            while io.has_more:
                frame = SPRFrame()
                # Read frame header and data
                self.frames.append(frame)
    
    def get_frame(self, index: int) -> Optional[SPRFrame]:
        """Get a frame by index."""
        if 0 <= index < len(self.frames):
            return self.frames[index]
        return None
    
    def __len__(self) -> int:
        return len(self.frames)
    
    def __getitem__(self, index: int) -> SPRFrame:
        return self.frames[index]


@register_chunk("SPR2")
@dataclass
class SPR2(IffChunk):
    """
    Enhanced sprite chunk with z-buffer and alpha support.
    Maps to: FSO.Files.Formats.IFF.Chunks.SPR2
    
    Used for object and character sprites that need depth sorting.
    """
    frames: list[SPR2Frame] = field(default_factory=list)
    default_palette_id: int = 0
    version: int = 0
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read SPR2 chunk from stream."""
        self.version = io.read_uint32()
        
        if self.version == 1000:
            # Version with offset table
            sprite_count = io.read_uint32()
            self.default_palette_id = io.read_uint32()
            
            offsets = [io.read_uint32() for _ in range(sprite_count)]
            
            self.frames = []
            for i, offset in enumerate(offsets):
                frame = SPR2Frame()
                io.seek(offset)
                
                # Calculate guessed size
                if i + 1 < len(offsets):
                    size = offsets[i + 1] - offset
                else:
                    size = 0
                
                self._read_frame(frame, io, size)
                self.frames.append(frame)
                
        elif self.version == 1001:
            # Streaming version
            self.default_palette_id = io.read_uint32()
            sprite_count = io.read_uint32()
            
            self.frames = []
            for _ in range(sprite_count):
                frame = SPR2Frame()
                sprite_version = io.read_uint32()
                sprite_size = io.read_uint32()
                
                # Read frame data
                start_pos = io.position
                self._read_frame_header(frame, io)
                
                # Store remaining as raw data
                remaining = sprite_size - (io.position - start_pos)
                if remaining > 0:
                    frame.raw_data = io.read_bytes(remaining)
                
                self.frames.append(frame)
    
    def _read_frame(self, frame: SPR2Frame, io: 'IoBuffer', size: int):
        """Read a frame with guessed size (v1000)."""
        self._read_frame_header(frame, io)
        # Remaining data is RLE encoded pixels
        if size > 0:
            header_size = 10  # Approximate header size
            remaining = size - header_size
            if remaining > 0:
                frame.raw_data = io.read_bytes(remaining)
    
    def _read_frame_header(self, frame: SPR2Frame, io: 'IoBuffer'):
        """Read common frame header."""
        frame.width = io.read_uint16()
        frame.height = io.read_uint16()
        frame.flags = io.read_uint32()
        frame.palette_id = io.read_uint16()
        
        # Transparent color handling
        if frame.palette_id == 0 or frame.palette_id == 0xA3A3:
            frame.palette_id = self.default_palette_id
        
        frame.transparent_index = io.read_uint16()
        frame.position_y = io.read_int16()
        frame.position_x = io.read_int16()
    
    def get_frame(self, index: int) -> Optional[SPR2Frame]:
        """Get a frame by index."""
        if 0 <= index < len(self.frames):
            return self.frames[index]
        return None
    
    def __len__(self) -> int:
        return len(self.frames)
    
    def __getitem__(self, index: int) -> SPR2Frame:
        return self.frames[index]
    
    def __str__(self) -> str:
        return f"SPR2 #{self.chunk_id}: {self.chunk_label} ({len(self.frames)} frames)"
