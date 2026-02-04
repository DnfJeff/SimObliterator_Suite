"""
SLOT Parser & Editor — Routing slot resource handling.

SLOT resources define where Sims can stand relative to an object,
routing targets, and placement constraints. This was never finished
in IFF Pencil per community feedback.

Slot types:
- 0x00: Absolute position
- 0x01: Standing (person routing)
- 0x02: Sitting
- 0x03: Ground (for dropped items)
- 0x04: Target object routing
"""

import struct
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import IntEnum

from utils.binary import IoBuffer, ByteOrder


class SlotType(IntEnum):
    """Slot routing types."""
    ABSOLUTE = 0x00
    STANDING = 0x01
    SITTING = 0x02
    GROUND = 0x03
    ROUTING_TARGET = 0x04


class SlotFlags(IntEnum):
    """Slot behavior flags."""
    NONE = 0x00
    SNAP_TO_SLOT = 0x01
    FACE_OBJECT = 0x02
    RANDOM_FACING = 0x04
    SITTING_SLOT = 0x08
    ROUTING_SLOT = 0x10


@dataclass
class SlotPosition:
    """
    3D position with rotation for a slot.
    
    Positions are in game units relative to object origin.
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    facing: float = 0.0  # Radians, 0 = facing positive X
    
    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x, self.y, self.z, self.facing)
    
    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> 'SlotPosition':
        """Read position from binary data."""
        x, y, z, facing = struct.unpack_from('<ffff', data, offset)
        return cls(x=x, y=y, z=z, facing=facing)
    
    def to_bytes(self) -> bytes:
        """Convert to binary format."""
        return struct.pack('<ffff', self.x, self.y, self.z, self.facing)


@dataclass
class SlotEntry:
    """
    A single slot definition.
    
    Attributes:
        index: Slot index (0-based)
        slot_type: Type of slot (standing, sitting, etc.)
        position: 3D position and facing
        flags: Behavior flags
        target_slot: For routing, which slot to route to
        height_offset: Vertical offset for sitting
        name: Optional descriptive name (from editor, not saved)
    """
    index: int
    slot_type: int = SlotType.STANDING
    position: SlotPosition = field(default_factory=SlotPosition)
    flags: int = 0
    target_slot: int = 0
    height_offset: float = 0.0
    standing_eye_offset: float = 0.0
    sitting_eye_offset: float = 0.0
    
    # Editor-only metadata
    name: str = ""
    
    @property
    def type_name(self) -> str:
        try:
            return SlotType(self.slot_type).name.title()
        except ValueError:
            return f"Type_{self.slot_type}"
    
    def get_flag_names(self) -> List[str]:
        """Get list of set flag names."""
        names = []
        for flag in SlotFlags:
            if flag.value and (self.flags & flag.value):
                names.append(flag.name.replace('_', ' ').title())
        return names
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for UI display."""
        return {
            "index": self.index,
            "type": self.type_name,
            "type_code": self.slot_type,
            "position": {
                "x": round(self.position.x, 3),
                "y": round(self.position.y, 3),
                "z": round(self.position.z, 3),
                "facing": round(self.position.facing, 3),
            },
            "flags": self.flags,
            "flag_names": self.get_flag_names(),
            "target_slot": self.target_slot,
            "height_offset": self.height_offset,
            "name": self.name,
        }


@dataclass
class ParsedSLOT:
    """
    Complete parsed SLOT resource.
    """
    chunk_id: int
    version: int = 0
    slots: List[SlotEntry] = field(default_factory=list)
    parse_errors: List[str] = field(default_factory=list)
    
    def get_slot(self, index: int) -> Optional[SlotEntry]:
        """Get slot by index."""
        for slot in self.slots:
            if slot.index == index:
                return slot
        return None
    
    def get_slots_by_type(self, slot_type: int) -> List[SlotEntry]:
        """Get all slots of a specific type."""
        return [s for s in self.slots if s.slot_type == slot_type]
    
    def get_standing_slots(self) -> List[SlotEntry]:
        """Get all standing (routing) slots."""
        return self.get_slots_by_type(SlotType.STANDING)
    
    def get_sitting_slots(self) -> List[SlotEntry]:
        """Get all sitting slots."""
        return self.get_slots_by_type(SlotType.SITTING)
    
    def get_summary(self) -> Dict:
        """Get summary for UI display."""
        return {
            "chunk_id": self.chunk_id,
            "version": self.version,
            "total_slots": len(self.slots),
            "standing_slots": len(self.get_standing_slots()),
            "sitting_slots": len(self.get_sitting_slots()),
            "by_type": {
                SlotType(t).name: count 
                for t, count in self._count_by_type().items()
            },
        }
    
    def _count_by_type(self) -> Dict[int, int]:
        """Count slots by type."""
        counts = {}
        for slot in self.slots:
            counts[slot.slot_type] = counts.get(slot.slot_type, 0) + 1
        return counts


class SLOTParser:
    """
    Parser for SLOT resources.
    
    SLOT format (The Sims 1):
    - Header with version and count
    - Array of slot entries with position, type, flags
    """
    
    @classmethod
    def parse(cls, data: bytes, chunk_id: int = 0) -> ParsedSLOT:
        """
        Parse SLOT chunk data.
        
        Args:
            data: Raw chunk data
            chunk_id: Chunk ID for context
            
        Returns:
            ParsedSLOT with all slots
        """
        result = ParsedSLOT(chunk_id=chunk_id)
        
        if len(data) < 6:
            result.parse_errors.append("Data too short for SLOT header")
            return result
        
        try:
            buf = IoBuffer.from_bytes(data, ByteOrder.LITTLE_ENDIAN)
            
            # Read header
            # Format: version (2), count (2), unknown (2)
            result.version = buf.read_uint16()
            count = buf.read_uint16()
            _unknown = buf.read_uint16()
            
            # Calculate entry size based on version
            # Older versions have smaller entries
            if result.version >= 4:
                entry_size = 32
            elif result.version >= 2:
                entry_size = 24
            else:
                entry_size = 20
            
            # Parse slots
            for idx in range(count):
                try:
                    slot = cls._parse_slot(buf, idx, result.version)
                    result.slots.append(slot)
                except Exception as e:
                    result.parse_errors.append(f"Error parsing slot {idx}: {e}")
                    break
                    
        except Exception as e:
            result.parse_errors.append(f"Parse exception: {e}")
        
        return result
    
    @classmethod
    def _parse_slot(cls, buf: IoBuffer, index: int, version: int) -> SlotEntry:
        """Parse a single slot entry."""
        slot = SlotEntry(index=index)
        
        # Type
        slot.slot_type = buf.read_uint16()
        
        # Position (X, Y, Z as floats)
        slot.position.x = buf.read_float()
        slot.position.y = buf.read_float()
        slot.position.z = buf.read_float()
        
        # Facing
        slot.position.facing = buf.read_float()
        
        # Flags
        slot.flags = buf.read_uint16()
        
        # Target slot
        slot.target_slot = buf.read_uint16()
        
        # Height offset (version 2+)
        if version >= 2:
            slot.height_offset = buf.read_float()
        
        # Eye offsets (version 4+)
        if version >= 4:
            slot.standing_eye_offset = buf.read_float()
            slot.sitting_eye_offset = buf.read_float()
        
        return slot


class SLOTSerializer:
    """
    Serialize ParsedSLOT back to binary format.
    """
    
    @classmethod
    def serialize(cls, slot_data: ParsedSLOT) -> bytes:
        """
        Serialize SLOT to binary.
        
        Args:
            slot_data: Parsed SLOT to serialize
            
        Returns:
            Binary SLOT chunk data
        """
        parts = []
        
        # Header
        parts.append(struct.pack('<H', slot_data.version))
        parts.append(struct.pack('<H', len(slot_data.slots)))
        parts.append(struct.pack('<H', 0))  # Unknown/padding
        
        # Slots
        for slot in slot_data.slots:
            parts.append(cls._serialize_slot(slot, slot_data.version))
        
        return b''.join(parts)
    
    @classmethod
    def _serialize_slot(cls, slot: SlotEntry, version: int) -> bytes:
        """Serialize a single slot."""
        parts = []
        
        # Type
        parts.append(struct.pack('<H', slot.slot_type))
        
        # Position
        parts.append(struct.pack('<ffff', 
                                 slot.position.x,
                                 slot.position.y,
                                 slot.position.z,
                                 slot.position.facing))
        
        # Flags and target
        parts.append(struct.pack('<H', slot.flags))
        parts.append(struct.pack('<H', slot.target_slot))
        
        # Height offset (version 2+)
        if version >= 2:
            parts.append(struct.pack('<f', slot.height_offset))
        
        # Eye offsets (version 4+)
        if version >= 4:
            parts.append(struct.pack('<f', slot.standing_eye_offset))
            parts.append(struct.pack('<f', slot.sitting_eye_offset))
        
        return b''.join(parts)


class SLOTEditor:
    """
    Editor operations for SLOT resources.
    """
    
    @classmethod
    def add_slot(cls, slot_data: ParsedSLOT, 
                 slot_type: int = SlotType.STANDING,
                 position: Optional[SlotPosition] = None) -> SlotEntry:
        """
        Add a new slot.
        
        Args:
            slot_data: SLOT to modify
            slot_type: Type of slot to add
            position: Position (default: origin)
            
        Returns:
            The new slot entry
        """
        new_index = len(slot_data.slots)
        
        slot = SlotEntry(
            index=new_index,
            slot_type=slot_type,
            position=position or SlotPosition(),
        )
        
        slot_data.slots.append(slot)
        return slot
    
    @classmethod
    def remove_slot(cls, slot_data: ParsedSLOT, index: int) -> bool:
        """
        Remove a slot by index.
        
        Args:
            slot_data: SLOT to modify
            index: Index of slot to remove
            
        Returns:
            True if removed, False if not found
        """
        for i, slot in enumerate(slot_data.slots):
            if slot.index == index:
                slot_data.slots.pop(i)
                
                # Renumber remaining slots
                for j, s in enumerate(slot_data.slots):
                    s.index = j
                
                return True
        return False
    
    @classmethod
    def duplicate_slot(cls, slot_data: ParsedSLOT, index: int,
                       offset_x: float = 0.5) -> Optional[SlotEntry]:
        """
        Duplicate a slot with position offset.
        
        Args:
            slot_data: SLOT to modify
            index: Index of slot to duplicate
            offset_x: X offset for new slot
            
        Returns:
            The new slot, or None if source not found
        """
        source = slot_data.get_slot(index)
        if not source:
            return None
        
        new_slot = SlotEntry(
            index=len(slot_data.slots),
            slot_type=source.slot_type,
            position=SlotPosition(
                x=source.position.x + offset_x,
                y=source.position.y,
                z=source.position.z,
                facing=source.position.facing,
            ),
            flags=source.flags,
            target_slot=source.target_slot,
            height_offset=source.height_offset,
        )
        
        slot_data.slots.append(new_slot)
        return new_slot
    
    @classmethod
    def create_basic_chair_slots(cls) -> ParsedSLOT:
        """
        Create basic slot layout for a chair-like object.
        
        Returns:
            ParsedSLOT with sitting and routing slots
        """
        slot_data = ParsedSLOT(chunk_id=0, version=4)
        
        # Sitting slot (on the chair)
        sitting = SlotEntry(
            index=0,
            slot_type=SlotType.SITTING,
            position=SlotPosition(x=0.0, y=0.0, z=0.4, facing=0.0),
            flags=SlotFlags.SITTING_SLOT | SlotFlags.FACE_OBJECT,
            height_offset=0.4,
        )
        slot_data.slots.append(sitting)
        
        # Routing slot (where Sim walks to)
        routing = SlotEntry(
            index=1,
            slot_type=SlotType.STANDING,
            position=SlotPosition(x=0.5, y=0.0, z=0.0, facing=3.14159),
            flags=SlotFlags.ROUTING_SLOT,
            target_slot=0,  # Routes to sitting slot
        )
        slot_data.slots.append(routing)
        
        return slot_data
    
    @classmethod
    def create_basic_counter_slots(cls) -> ParsedSLOT:
        """
        Create basic slot layout for a counter-like object.
        
        Returns:
            ParsedSLOT with front routing slot
        """
        slot_data = ParsedSLOT(chunk_id=0, version=4)
        
        # Front routing slot
        front = SlotEntry(
            index=0,
            slot_type=SlotType.STANDING,
            position=SlotPosition(x=0.5, y=0.0, z=0.0, facing=3.14159),
            flags=SlotFlags.ROUTING_SLOT | SlotFlags.FACE_OBJECT,
        )
        slot_data.slots.append(front)
        
        return slot_data


def parse_slot_chunk(data: bytes, chunk_id: int = 0) -> ParsedSLOT:
    """Convenience function to parse SLOT."""
    return SLOTParser.parse(data, chunk_id)


# ═══════════════════════════════════════════════════════════════════════════════
# XML IMPORT/EXPORT (Transmogrifier compatible)
# ═══════════════════════════════════════════════════════════════════════════════

import xml.etree.ElementTree as ET
from xml.dom import minidom


def slot_to_xml(slot_data: ParsedSLOT, pretty: bool = True) -> str:
    """
    Export SLOT data to XML format (Transmogrifier-style).
    
    This format is human-editable and compatible with modding workflows.
    
    Args:
        slot_data: ParsedSLOT object to export
        pretty: If True, format with indentation
        
    Returns:
        XML string
    """
    root = ET.Element('SLOT')
    root.set('version', str(slot_data.version))
    root.set('chunk_id', f"0x{slot_data.chunk_id:04X}")
    
    for slot in slot_data.slots:
        slot_elem = ET.SubElement(root, 'Slot')
        slot_elem.set('index', str(slot.index))
        slot_elem.set('type', slot.type_name)
        slot_elem.set('type_id', str(slot.slot_type))
        
        if slot.name:
            slot_elem.set('name', slot.name)
        
        # Position
        pos_elem = ET.SubElement(slot_elem, 'Position')
        pos_elem.set('x', f"{slot.position.x:.4f}")
        pos_elem.set('y', f"{slot.position.y:.4f}")
        pos_elem.set('z', f"{slot.position.z:.4f}")
        pos_elem.set('facing', f"{slot.position.facing:.4f}")
        
        # Flags
        flags_elem = ET.SubElement(slot_elem, 'Flags')
        flags_elem.set('value', f"0x{slot.flags:02X}")
        # Decode flags for readability
        flag_names = []
        for flag in SlotFlags:
            if slot.flags & flag:
                flag_names.append(flag.name)
        if flag_names:
            flags_elem.set('decoded', ','.join(flag_names))
        
        # Optional fields
        if slot.target_slot != 0:
            target_elem = ET.SubElement(slot_elem, 'TargetSlot')
            target_elem.text = str(slot.target_slot)
        
        if slot.height_offset != 0.0:
            height_elem = ET.SubElement(slot_elem, 'HeightOffset')
            height_elem.text = f"{slot.height_offset:.4f}"
        
        if slot.standing_eye_offset != 0.0:
            eye_elem = ET.SubElement(slot_elem, 'StandingEyeOffset')
            eye_elem.text = f"{slot.standing_eye_offset:.4f}"
        
        if slot.sitting_eye_offset != 0.0:
            eye_elem = ET.SubElement(slot_elem, 'SittingEyeOffset')
            eye_elem.text = f"{slot.sitting_eye_offset:.4f}"
    
    if pretty:
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')
    else:
        return ET.tostring(root, encoding='unicode')


def xml_to_slot(xml_content: str) -> ParsedSLOT:
    """
    Import SLOT data from XML format.
    
    Args:
        xml_content: XML string
        
    Returns:
        ParsedSLOT object
    """
    root = ET.fromstring(xml_content)
    
    version = int(root.get('version', '4'))
    chunk_id_str = root.get('chunk_id', '0x0000')
    if chunk_id_str.startswith('0x'):
        chunk_id = int(chunk_id_str, 16)
    else:
        chunk_id = int(chunk_id_str)
    
    slot_data = ParsedSLOT(chunk_id=chunk_id, version=version)
    
    for slot_elem in root.findall('Slot'):
        index = int(slot_elem.get('index', '0'))
        type_id = int(slot_elem.get('type_id', '1'))
        name = slot_elem.get('name', '')
        
        # Parse position
        pos_elem = slot_elem.find('Position')
        if pos_elem is not None:
            position = SlotPosition(
                x=float(pos_elem.get('x', '0')),
                y=float(pos_elem.get('y', '0')),
                z=float(pos_elem.get('z', '0')),
                facing=float(pos_elem.get('facing', '0'))
            )
        else:
            position = SlotPosition()
        
        # Parse flags
        flags_elem = slot_elem.find('Flags')
        if flags_elem is not None:
            flags_str = flags_elem.get('value', '0')
            if flags_str.startswith('0x'):
                flags = int(flags_str, 16)
            else:
                flags = int(flags_str)
        else:
            flags = 0
        
        # Optional fields
        target_elem = slot_elem.find('TargetSlot')
        target_slot = int(target_elem.text) if target_elem is not None else 0
        
        height_elem = slot_elem.find('HeightOffset')
        height_offset = float(height_elem.text) if height_elem is not None else 0.0
        
        standing_eye_elem = slot_elem.find('StandingEyeOffset')
        standing_eye = float(standing_eye_elem.text) if standing_eye_elem is not None else 0.0
        
        sitting_eye_elem = slot_elem.find('SittingEyeOffset')
        sitting_eye = float(sitting_eye_elem.text) if sitting_eye_elem is not None else 0.0
        
        slot = SlotEntry(
            index=index,
            slot_type=type_id,
            position=position,
            flags=flags,
            target_slot=target_slot,
            height_offset=height_offset,
            standing_eye_offset=standing_eye,
            sitting_eye_offset=sitting_eye,
            name=name
        )
        slot_data.slots.append(slot)
    
    return slot_data


def export_slot_to_file(slot_data: ParsedSLOT, filepath: str) -> None:
    """Export SLOT to XML file."""
    xml_content = slot_to_xml(slot_data)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(xml_content)


def import_slot_from_file(filepath: str) -> ParsedSLOT:
    """Import SLOT from XML file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return xml_to_slot(f.read())
