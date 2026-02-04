"""
PART Chunk - Particle System Parameters
Port of FreeSO's tso.files/Formats/IFF/Chunks/PART.cs

Contains particle effect parameters for visual effects.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Tuple, List, Optional

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


# Vector3 as tuple (x, y, z)
Vector3 = Tuple[float, float, float]

# Color as RGBA packed uint32 or tuple
Color = int


PART_CURRENT_VERSION = 1


@register_chunk('PART')
@dataclass
class PART(IffChunk):
    """
    Particle system parameters chunk.
    Defines visual particle effects for objects.
    """
    version: int = PART_CURRENT_VERSION
    part_type: int = 0  # 0=default, 1=manual bounds
    
    frequency: float = 0.0
    tex_id: int = 0  # MTEX resource ID
    particles: int = 15
    
    # Optional bounding box (only if type == 1)
    bounds_min: Vector3 = (0.0, 0.0, 0.0)
    bounds_max: Vector3 = (0.0, 0.0, 0.0)
    
    # Particle physics
    velocity: Vector3 = (0.0, 0.0, 0.0)
    gravity: float = -0.8
    random_vel: float = 0.0
    random_rot_vel: float = 0.0
    
    # Particle appearance
    size: float = 1.0
    size_vel: float = 0.0
    duration: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    size_variation: float = 0.0
    
    # Color
    target_color: Color = 0xFFFFFFFF  # Packed RGBA
    target_color_var: float = 0.0
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read PART chunk."""
        self.version = stream.read_int32()
        self.part_type = stream.read_int32()
        
        self.frequency = stream.read_float()
        self.tex_id = stream.read_uint16()
        self.particles = stream.read_int32()
        
        # Bounding box only if type == 1
        if self.part_type == 1:
            self.bounds_min = (
                stream.read_float(),
                stream.read_float(),
                stream.read_float()
            )
            self.bounds_max = (
                stream.read_float(),
                stream.read_float(),
                stream.read_float()
            )
        
        self.velocity = (
            stream.read_float(),
            stream.read_float(),
            stream.read_float()
        )
        self.gravity = stream.read_float()
        self.random_vel = stream.read_float()
        self.random_rot_vel = stream.read_float()
        self.size = stream.read_float()
        self.size_vel = stream.read_float()
        self.duration = stream.read_float()
        self.fade_in = stream.read_float()
        self.fade_out = stream.read_float()
        self.size_variation = stream.read_float()
        self.target_color = stream.read_uint32()
        self.target_color_var = stream.read_float()
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write PART chunk."""
        stream.write_int32(self.version)
        stream.write_int32(self.part_type)
        
        stream.write_float(self.frequency)
        stream.write_uint16(self.tex_id)
        stream.write_int32(self.particles)
        
        if self.part_type == 1:
            stream.write_float(self.bounds_min[0])
            stream.write_float(self.bounds_min[1])
            stream.write_float(self.bounds_min[2])
            stream.write_float(self.bounds_max[0])
            stream.write_float(self.bounds_max[1])
            stream.write_float(self.bounds_max[2])
        
        stream.write_float(self.velocity[0])
        stream.write_float(self.velocity[1])
        stream.write_float(self.velocity[2])
        stream.write_float(self.gravity)
        stream.write_float(self.random_vel)
        stream.write_float(self.random_rot_vel)
        stream.write_float(self.size)
        stream.write_float(self.size_vel)
        stream.write_float(self.duration)
        stream.write_float(self.fade_in)
        stream.write_float(self.fade_out)
        stream.write_float(self.size_variation)
        stream.write_uint32(self.target_color)
        stream.write_float(self.target_color_var)
        
        return True
    
    def get_color_rgba(self) -> Tuple[int, int, int, int]:
        """Unpack target color as (R, G, B, A)."""
        return (
            self.target_color & 0xFF,
            (self.target_color >> 8) & 0xFF,
            (self.target_color >> 16) & 0xFF,
            (self.target_color >> 24) & 0xFF
        )
    
    @staticmethod
    def create_broken_effect() -> 'PART':
        """Create default 'broken' particle effect."""
        part = PART()
        part.gravity = 0.15
        part.random_vel = 0.15
        part.random_rot_vel = 1.0
        part.size = 0.75
        part.size_vel = 2.5
        part.duration = 3.0
        part.fade_in = 0.15
        part.fade_out = 0.6
        part.size_variation = 0.4
        part.target_color = 0xFF808080  # Gray
        part.target_color_var = 0.5
        part.frequency = 6.0
        part.chunk_id = 256
        return part
