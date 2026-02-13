"""
DGRP Chunk - Drawing Groups
Port of FreeSO's tso.files/Formats/IFF/Chunks/DGRP.cs

DGRP chunks collect sprites into groups for rendering objects
from all directions and zoom levels. Each object tile has its own DGRP.
"""

from dataclasses import dataclass, field
from enum import IntFlag
from typing import TYPE_CHECKING, Optional

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


class DGRPSpriteFlags(IntFlag):
    """Flags for DGRP sprites."""
    NONE = 0
    FLIP = 0x01         # Horizontally flip the sprite
    UNKNOWN = 0x02      # Set for end table
    LUMINOUS = 0x04     # Sprite is luminous (glows)
    UNKNOWN2 = 0x08
    UNKNOWN3 = 0x10     # Set for end table


# Direction constants
DIR_LEFT_FRONT = 0x10
DIR_LEFT_BACK = 0x40
DIR_RIGHT_FRONT = 0x04
DIR_RIGHT_BACK = 0x01


@dataclass
class DGRPSprite:
    """
    A single sprite reference within a DGRP image.
    Points to a SPR# or SPR2 resource.
    """
    sprite_id: int = 0           # ID of SPR# or SPR2 chunk
    sprite_frame_index: int = 0  # Frame within that sprite
    flags: DGRPSpriteFlags = DGRPSpriteFlags.NONE
    
    # Sprite offset (screen position adjustment)
    sprite_offset_x: float = 0
    sprite_offset_y: float = 0
    
    # Object offset (3D position in tile)
    object_offset_x: float = 0
    object_offset_y: float = 0
    object_offset_z: float = 0
    
    @property
    def flip(self) -> bool:
        return bool(self.flags & DGRPSpriteFlags.FLIP)
    
    @flip.setter
    def flip(self, value: bool):
        if value:
            self.flags |= DGRPSpriteFlags.FLIP
        else:
            self.flags &= ~DGRPSpriteFlags.FLIP
    
    @property
    def luminous(self) -> bool:
        return bool(self.flags & DGRPSpriteFlags.LUMINOUS)
    
    @luminous.setter
    def luminous(self, value: bool):
        if value:
            self.flags |= DGRPSpriteFlags.LUMINOUS
        else:
            self.flags &= ~DGRPSpriteFlags.LUMINOUS


@dataclass
class DGRPImage:
    """
    A DGRP image - one view of an object (specific direction + zoom).
    Contains one or more sprites layered together.
    """
    direction: int = 0   # Which direction (bit flags)
    zoom: int = 0        # Zoom level (1=far, 2=medium, 3=near)
    sprites: list[DGRPSprite] = field(default_factory=list)
    
    def read(self, version: int, io: 'IoBuffer'):
        """Read DGRPImage from stream."""
        if version < 20003:
            sprite_count = io.read_uint16()
            self.direction = io.read_byte()
            self.zoom = io.read_byte()
        else:
            self.direction = io.read_uint32()
            self.zoom = io.read_uint32()
            sprite_count = io.read_uint32()
        
        self.sprites = []
        for _ in range(sprite_count):
            sprite = DGRPSprite()
            self._read_sprite(sprite, version, io)
            self.sprites.append(sprite)
    
    def _read_sprite(self, sprite: DGRPSprite, version: int, io: 'IoBuffer'):
        """Read a single sprite reference."""
        if version < 20003:
            _type = io.read_uint16()  # Ignored
            sprite.sprite_id = io.read_uint16()
            sprite.sprite_frame_index = io.read_uint16()
            sprite.flags = DGRPSpriteFlags(io.read_uint16())
            sprite.sprite_offset_x = io.read_int16()
            sprite.sprite_offset_y = io.read_int16()
            
            if version == 20001:
                sprite.object_offset_z = io.read_float()
        else:
            sprite.sprite_id = io.read_uint32()
            sprite.sprite_frame_index = io.read_uint32()
            sprite.sprite_offset_x = io.read_int32()
            sprite.sprite_offset_y = io.read_int32()
            sprite.object_offset_z = io.read_float()
            sprite.flags = DGRPSpriteFlags(io.read_uint32())
            
            if version == 20004:
                sprite.object_offset_x = io.read_float()
                sprite.object_offset_y = io.read_float()
    
    def write(self, version: int, io: 'IoWriter'):
        """Write DGRPImage to stream."""
        if version < 20003:
            io.write_uint16(len(self.sprites))
            io.write_byte(self.direction)
            io.write_byte(self.zoom)
        else:
            io.write_uint32(self.direction)
            io.write_uint32(self.zoom)
            io.write_uint32(len(self.sprites))
        
        for sprite in self.sprites:
            self._write_sprite(sprite, version, io)
    
    def _write_sprite(self, sprite: DGRPSprite, version: int, io: 'IoWriter'):
        """Write a single sprite reference."""
        if version < 20003:
            io.write_uint16(0)  # Type (ignored on read)
            io.write_uint16(sprite.sprite_id)
            io.write_uint16(sprite.sprite_frame_index)
            io.write_uint16(sprite.flags)
            io.write_int16(int(sprite.sprite_offset_x))
            io.write_int16(int(sprite.sprite_offset_y))
            
            if version == 20001:
                io.write_float(sprite.object_offset_z)
        else:
            io.write_uint32(sprite.sprite_id)
            io.write_uint32(sprite.sprite_frame_index)
            io.write_int32(int(sprite.sprite_offset_x))
            io.write_int32(int(sprite.sprite_offset_y))
            io.write_float(sprite.object_offset_z)
            io.write_uint32(sprite.flags)
            
            if version == 20004:
                io.write_float(sprite.object_offset_x)
                io.write_float(sprite.object_offset_y)


@register_chunk("DGRP")
@dataclass
class DGRP(IffChunk):
    """
    Drawing Group chunk - collects sprites for rendering an object tile.
    Maps to: FSO.Files.Formats.IFF.Chunks.DGRP
    
    A DGRP contains 12 images: 4 directions × 3 zoom levels.
    Multi-tile objects have separate DGRP chunks per tile.
    """
    images: list[DGRPImage] = field(default_factory=list)
    version: int = 0
    
    # Standard zoom levels
    ZOOM_FAR = 1
    ZOOM_MEDIUM = 2
    ZOOM_NEAR = 3
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read DGRP chunk from stream."""
        self.version = io.read_uint16()
        
        if self.version < 20003:
            image_count = io.read_uint16()
        else:
            image_count = io.read_uint32()
        
        self.images = []
        for _ in range(image_count):
            image = DGRPImage()
            image.read(self.version, io)
            self.images.append(image)
    
    def write(self, iff: 'IffFile', io: 'IoWriter') -> bool:
        """Write DGRP chunk to stream."""
        io.write_uint16(self.version)
        
        if self.version < 20003:
            io.write_uint16(len(self.images))
        else:
            io.write_uint32(len(self.images))
        
        for image in self.images:
            image.write(self.version, io)
        
        return True
    
    def get_image(self, direction: int, zoom: int, world_rotation: int = 0) -> Optional[DGRPImage]:
        """
        Get the image for a specific view.
        
        Args:
            direction: Direction flags (0x01, 0x04, 0x10, 0x40)
            zoom: Zoom level (1=far, 2=medium, 3=near)
            world_rotation: World rotation (0-3, rotates direction)
        
        Returns:
            DGRPImage or None if not found
        """
        # Apply world rotation to direction
        rotate_bits = direction << (world_rotation * 2)
        rotated_direction = (rotate_bits & 255) | (rotate_bits >> 8)
        
        for image in self.images:
            if image.direction == rotated_direction and image.zoom == zoom:
                return image
        return None
    
    def get_all_directions(self, zoom: int) -> list[DGRPImage]:
        """Get all images for a zoom level."""
        return [img for img in self.images if img.zoom == zoom]
    
    def __len__(self) -> int:
        return len(self.images)
    
    def __getitem__(self, index: int) -> DGRPImage:
        return self.images[index]
    
    def summary(self) -> str:
        """Get a summary of this DGRP."""
        lines = [f"DGRP #{self.chunk_id}: {self.chunk_label}"]
        lines.append(f"  Version: {self.version}, Images: {len(self.images)}")
        
        for img in self.images:
            dir_name = self._direction_name(img.direction)
            lines.append(f"  Dir:{dir_name} Zoom:{img.zoom} Sprites:{len(img.sprites)}")
        
        return "\n".join(lines)
    
    def _direction_name(self, direction: int) -> str:
        names = {
            0x01: "RB",  # Right-Back
            0x04: "RF",  # Right-Front
            0x10: "LF",  # Left-Front
            0x40: "LB",  # Left-Back
        }
        return names.get(direction, f"0x{direction:02X}")
    
    def __str__(self) -> str:
        return f"DGRP #{self.chunk_id}: {self.chunk_label} ({len(self.images)} images)"
