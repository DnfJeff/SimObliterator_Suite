"""
SLOT Chunk - Slot Definitions
Port of FreeSO's tso.files/Formats/IFF/Chunks/SLOT.cs

SLOT defines positions where Sims can interact with objects.
Each slot has position, facing, routing scores, and constraints.
"""

from dataclasses import dataclass, field
from enum import IntFlag, IntEnum
from typing import TYPE_CHECKING, Optional

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer


class SLOTFlags(IntFlag):
    """Routing slot flags."""
    NONE = 0
    NORTH = 1
    NORTH_EAST = 2
    EAST = 4
    SOUTH_EAST = 8
    SOUTH = 16
    SOUTH_WEST = 32
    WEST = 64
    NORTH_WEST = 128
    ALLOW_ANY_ROTATION = 256
    ABSOLUTE = 512              # Do not rotate goal around object
    FACING_AWAY = 1024          # Deprecated
    IGNORE_ROOMS = 2048
    SNAP_TO_DIRECTION = 4096
    RANDOM_SCORING = 8192
    ALLOW_FAILURE_TREES = 16385
    ALLOW_DIFFERENT_ALTS = 32768
    USE_AVERAGE_OBJECT_LOCATION = 65536


class SLOTFacing(IntEnum):
    """Facing direction for slots."""
    FACE_ANYWHERE = -3
    FACE_TOWARDS_OBJECT = -2
    FACE_AWAY_FROM_OBJECT = -1


# Height offsets (1-indexed in original)
HEIGHT_OFFSETS = [
    0,      # Floor
    2.5,    # Low table
    4,      # Table
    4,      # Counter
    0,      # Non-standard (uses offset height)
    0,      # In hand (unused)
    7,      # Sitting (chairs)
    4,      # End table
    0,      # Unknown
]


@dataclass
class SLOTItem:
    """A single slot definition."""
    type: int = 0
    
    # Position offset
    offset_x: float = 0.0
    offset_y: float = 0.0
    offset_z: float = 0.0
    
    # Routing scores (0 = never use)
    standing: int = 1    # Score for standing destinations
    sitting: int = 0     # Score for sitting destinations
    ground: int = 0      # Score for sitting on ground
    
    # Flags and constraints
    rsflags: SLOTFlags = SLOTFlags.NONE
    snap_target_slot: int = -1
    
    # Proximity constraints
    min_proximity: int = 0
    max_proximity: int = 0
    optimal_proximity: int = 0
    max_size: int = 100
    i10: int = 0         # Unknown field
    
    # Additional properties
    gradient: float = 0.0
    height: int = 5      # Height type (index into HEIGHT_OFFSETS)
    facing: SLOTFacing = SLOTFacing.FACE_TOWARDS_OBJECT
    resolution: int = 16


@register_chunk("SLOT")
@dataclass
class SLOT(IffChunk):
    """
    Slot definitions chunk - interaction positions for objects.
    Maps to: FSO.Files.Formats.IFF.Chunks.SLOT
    """
    version: int = 0
    slots: dict[int, list[SLOTItem]] = field(default_factory=dict)
    chronological: list[SLOTItem] = field(default_factory=list)
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read SLOT chunk from stream."""
        _zero = io.read_uint32()
        self.version = io.read_uint32()
        _magic = io.read_bytes(4)  # "TOLS" backwards
        num_slots = io.read_uint32()
        
        self.slots = {}
        self.chronological = []
        
        for _ in range(num_slots):
            item = SLOTItem()
            item.type = io.read_uint16()
            item.offset_x = io.read_float()
            item.offset_y = io.read_float()
            item.offset_z = io.read_float()
            
            item.standing = io.read_int32()
            item.sitting = io.read_int32()
            item.ground = io.read_int32()
            item.rsflags = SLOTFlags(io.read_int32())
            item.snap_target_slot = io.read_int32()
            
            if self.version >= 6:
                item.min_proximity = io.read_int32()
                item.max_proximity = io.read_int32()
                item.optimal_proximity = io.read_int32()
                item.max_size = io.read_int32()
                item.i10 = io.read_int32()
            
            # Scale proximity values for older versions
            if self.version <= 9:
                item.min_proximity *= 16
                item.max_proximity *= 16
                item.optimal_proximity *= 16
            
            if self.version >= 7:
                item.gradient = io.read_float()
            
            if self.version >= 8:
                item.height = io.read_int32()
            
            if item.height == 0:
                item.height = 5  # Non-standard, use offset height
            
            if self.version >= 9:
                item.facing = SLOTFacing(io.read_int32())
            
            if self.version >= 10:
                item.resolution = io.read_int32()
            
            # Add to collections
            if item.type not in self.slots:
                self.slots[item.type] = []
            self.slots[item.type].append(item)
            self.chronological.append(item)
    
    def get_slots_by_type(self, slot_type: int) -> list[SLOTItem]:
        """Get all slots of a specific type."""
        return self.slots.get(slot_type, [])
    
    def __len__(self) -> int:
        return len(self.chronological)
    
    def __iter__(self):
        return iter(self.chronological)
    
    def __str__(self) -> str:
        return f"SLOT #{self.chunk_id}: {self.chunk_label} ({len(self.chronological)} slots)"
