"""
TTAB Parser — Full Tree Table parser with all interaction fields.

Handles TTAB versions 4-10 with complete field extraction:
- Action and Test (guard) BHAV IDs
- Autonomy threshold
- Motive effects (delta, min, personality)
- Attenuation
- Joining index
- Flags

This addresses the community pain point where tools like Menu Editor
don't work correctly with multiple objects in the same IFF, or miss
fields like autonomy level.
"""

import struct
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import IntEnum, IntFlag

from utils.binary import IoBuffer, ByteOrder


class InteractionFlags(IntFlag):
    """TTAB interaction flags."""
    ALLOW_VISITORS = 0x0001
    DEBUG_ONLY = 0x0002
    LEAPFROG_DISABLED = 0x0004
    MUST_RUN = 0x0008
    AUTO_FIRST = 0x0010
    RUN_IMMEDIATELY = 0x0020
    ALLOW_CONSOLE = 0x0040
    CARRY = 0x0080
    REPAIR = 0x0100
    VISIBLE_ON_BREAK = 0x0200
    ALLOW_GHOSTS = 0x0400
    CONSECUTIVE = 0x0800
    # TSO flags (version 10+)
    CHECK_LOT = 0x1000
    TS1_AVAILABLE = 0x2000
    TSO_AVAILABLE = 0x4000
    ALLOW_CAT_DOG = 0x8000


class MotiveIndex(IntEnum):
    """Motive indices for effect arrays."""
    HUNGER = 0
    COMFORT = 1
    HYGIENE = 2
    BLADDER = 3
    ENERGY = 4
    FUN = 5
    SOCIAL = 6
    ROOM = 7


@dataclass
class MotiveEffect:
    """A single motive effect entry."""
    motive_index: int
    effect_delta: int = 0      # Change amount
    effect_min: int = 0        # Minimum for effect (V7+)
    personality_modifier: int = 0  # Personality weighting (V7+)
    
    @property
    def motive_name(self) -> str:
        try:
            return MotiveIndex(self.motive_index).name.title()
        except ValueError:
            return f"Motive_{self.motive_index}"


@dataclass
class TTABInteraction:
    """
    A complete TTAB interaction entry with all fields.
    
    This captures everything needed to fully represent an interaction,
    including autonomy settings that some tools miss.
    """
    index: int                  # Position in TTAB
    
    # BHAV references
    action_function: int = 0    # BHAV ID for action
    test_function: int = 0      # BHAV ID for availability guard
    
    # String reference
    tta_index: int = 0          # Index into TTAs string table
    
    # Autonomy settings (the commonly missed field!)
    autonomy_threshold: int = 0  # 0-100, higher = less likely to pick
    
    # Motive effects for AI decision making
    motive_effects: List[MotiveEffect] = field(default_factory=list)
    
    # Attenuation
    attenuation_code: int = 0   # (V7+) Type of distance falloff
    attenuation_value: float = 0.0  # Distance falloff value
    
    # Multi-sim support
    joining_index: int = -1     # -1 = no joining, else index of interaction to join
    
    # Flags
    flags: int = 0
    flags2: int = 0             # Extended flags (V10+)
    
    def get_flag_names(self) -> List[str]:
        """Get list of set flag names."""
        names = []
        for flag in InteractionFlags:
            if self.flags & flag:
                names.append(flag.name)
        return names
    
    def has_autonomy(self) -> bool:
        """Check if interaction can be chosen autonomously."""
        return self.autonomy_threshold < 100
    
    @property
    def action_bhav_hex(self) -> str:
        return f"0x{self.action_function:04X}"
    
    @property  
    def test_bhav_hex(self) -> str:
        return f"0x{self.test_function:04X}"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "index": self.index,
            "action_function": self.action_function,
            "action_bhav_hex": self.action_bhav_hex,
            "test_function": self.test_function,
            "test_bhav_hex": self.test_bhav_hex,
            "tta_index": self.tta_index,
            "autonomy_threshold": self.autonomy_threshold,
            "attenuation_code": self.attenuation_code,
            "attenuation_value": self.attenuation_value,
            "joining_index": self.joining_index,
            "flags": self.flags,
            "flag_names": self.get_flag_names(),
            "motive_effects": [
                {
                    "motive": eff.motive_name,
                    "delta": eff.effect_delta,
                    "min": eff.effect_min,
                    "personality": eff.personality_modifier,
                }
                for eff in self.motive_effects
            ],
        }


@dataclass
class ParsedTTAB:
    """
    Complete parsed TTAB chunk.
    
    Contains all interactions with full field data.
    """
    chunk_id: int
    version: int
    compression_code: int = 0  # V9-10 only
    interactions: List[TTABInteraction] = field(default_factory=list)
    parse_errors: List[str] = field(default_factory=list)
    
    def get_interaction(self, index: int) -> Optional[TTABInteraction]:
        """Get interaction by index."""
        for inter in self.interactions:
            if inter.index == index:
                return inter
        return None
    
    def get_by_tta_index(self, tta_index: int) -> Optional[TTABInteraction]:
        """Get interaction by string table index."""
        for inter in self.interactions:
            if inter.tta_index == tta_index:
                return inter
        return None
    
    def get_autonomous_interactions(self) -> List[TTABInteraction]:
        """Get all interactions that can be chosen autonomously."""
        return [i for i in self.interactions if i.has_autonomy()]
    
    def get_summary(self) -> Dict:
        """Get summary of TTAB contents."""
        return {
            "chunk_id": self.chunk_id,
            "version": self.version,
            "interaction_count": len(self.interactions),
            "autonomous_count": len(self.get_autonomous_interactions()),
            "with_motive_effects": sum(1 for i in self.interactions if i.motive_effects),
            "with_joining": sum(1 for i in self.interactions if i.joining_index >= 0),
        }


class TTABParser:
    """
    Full TTAB parser supporting versions 4-10.
    
    This parser captures ALL fields, unlike some existing tools that
    miss autonomy or motive effect details.
    """
    
    @classmethod
    def parse(cls, data: bytes, chunk_id: int = 0) -> ParsedTTAB:
        """
        Parse TTAB chunk data.
        
        Args:
            data: Raw chunk data
            chunk_id: Chunk ID for context
            
        Returns:
            ParsedTTAB with all interactions
        """
        result = ParsedTTAB(chunk_id=chunk_id, version=0)
        
        if len(data) < 4:
            result.parse_errors.append("Data too short for TTAB header")
            return result
        
        try:
            buf = IoBuffer.from_bytes(data, ByteOrder.LITTLE_ENDIAN)
            
            # Read header
            count = buf.read_uint16()
            if count == 0:
                return result
            
            result.version = buf.read_uint16()
            
            # Version 3 and below not fully supported
            if result.version <= 3:
                result.parse_errors.append(f"TTAB version {result.version} not fully supported")
                return result
            
            # Compression code for V9+
            if result.version >= 9:
                result.compression_code = buf.read_byte()
                if result.compression_code == 1:
                    result.parse_errors.append("Compressed TTAB (field encoding) not yet supported")
                    # Would need special field decoder here
            
            # Parse interactions
            for idx in range(count):
                try:
                    inter = cls._parse_interaction(buf, idx, result.version)
                    result.interactions.append(inter)
                except Exception as e:
                    result.parse_errors.append(f"Error parsing interaction {idx}: {e}")
                    break
                    
        except Exception as e:
            result.parse_errors.append(f"Parse exception: {e}")
        
        return result
    
    @classmethod
    def _parse_interaction(cls, buf: IoBuffer, index: int, version: int) -> TTABInteraction:
        """Parse a single interaction entry."""
        inter = TTABInteraction(index=index)
        
        # Core fields (all versions 4+)
        inter.action_function = buf.read_uint16()
        inter.test_function = buf.read_uint16()
        
        num_motives = buf.read_uint32()
        inter.flags = buf.read_uint32()
        inter.tta_index = buf.read_uint32()
        
        # Attenuation code (V7+)
        if version >= 7:
            inter.attenuation_code = buf.read_uint32()
        
        # Attenuation value and autonomy
        inter.attenuation_value = buf.read_float()
        inter.autonomy_threshold = buf.read_uint32()
        inter.joining_index = buf.read_int32()
        
        # Parse motive effects
        for m_idx in range(num_motives):
            motive = MotiveEffect(motive_index=m_idx)
            
            if version >= 7:
                motive.effect_min = buf.read_int16()
            
            motive.effect_delta = buf.read_int16()
            
            if version >= 7:
                motive.personality_modifier = buf.read_uint16()
            
            inter.motive_effects.append(motive)
        
        # Extended flags (V10+)
        if version >= 10:
            inter.flags2 = buf.read_uint32()
        
        return inter


class TTABSerializer:
    """
    Serialize ParsedTTAB back to binary format.
    
    Preserves all fields including autonomy and motive effects.
    """
    
    @classmethod
    def serialize(cls, ttab: ParsedTTAB) -> bytes:
        """
        Serialize TTAB to binary.
        
        Args:
            ttab: Parsed TTAB to serialize
            
        Returns:
            Binary TTAB chunk data
        """
        parts = []
        
        # Header
        parts.append(struct.pack('<H', len(ttab.interactions)))  # Count
        parts.append(struct.pack('<H', ttab.version))  # Version
        
        # Compression code for V9+
        if ttab.version >= 9:
            parts.append(bytes([ttab.compression_code]))
        
        # Interactions
        for inter in ttab.interactions:
            parts.append(cls._serialize_interaction(inter, ttab.version))
        
        return b''.join(parts)
    
    @classmethod
    def _serialize_interaction(cls, inter: TTABInteraction, version: int) -> bytes:
        """Serialize a single interaction."""
        parts = []
        
        # Core fields
        parts.append(struct.pack('<H', inter.action_function))
        parts.append(struct.pack('<H', inter.test_function))
        parts.append(struct.pack('<I', len(inter.motive_effects)))
        parts.append(struct.pack('<I', inter.flags))
        parts.append(struct.pack('<I', inter.tta_index))
        
        # Attenuation code (V7+)
        if version >= 7:
            parts.append(struct.pack('<I', inter.attenuation_code))
        
        # Attenuation value and autonomy
        parts.append(struct.pack('<f', inter.attenuation_value))
        parts.append(struct.pack('<I', inter.autonomy_threshold))
        parts.append(struct.pack('<i', inter.joining_index))
        
        # Motive effects
        for motive in inter.motive_effects:
            if version >= 7:
                parts.append(struct.pack('<h', motive.effect_min))
            parts.append(struct.pack('<h', motive.effect_delta))
            if version >= 7:
                parts.append(struct.pack('<H', motive.personality_modifier))
        
        # Extended flags (V10+)
        if version >= 10:
            parts.append(struct.pack('<I', inter.flags2))
        
        return b''.join(parts)


@dataclass
class MultiObjectContext:
    """
    Context for working with IFFs containing multiple objects.
    
    Maps which resources (TTAB, BHAV, STR#) belong to which OBJD.
    """
    
    @dataclass
    class ObjectEntry:
        """A single object in the IFF."""
        objd_id: int
        name: str = ""
        guid: int = 0
        ttab_id: int = 0
        catalog_str_id: int = 0
        bhav_ids: List[int] = field(default_factory=list)
    
    objects: List['MultiObjectContext.ObjectEntry'] = field(default_factory=list)
    source_file: str = ""
    
    def get_object_by_objd(self, objd_id: int) -> Optional['MultiObjectContext.ObjectEntry']:
        for obj in self.objects:
            if obj.objd_id == objd_id:
                return obj
        return None
    
    def get_object_for_ttab(self, ttab_id: int) -> Optional['MultiObjectContext.ObjectEntry']:
        """Find which object owns a TTAB."""
        for obj in self.objects:
            if obj.ttab_id == ttab_id:
                return obj
        return None


def build_multi_object_context(iff_reader, filename: str = "") -> MultiObjectContext:
    """
    Build context mapping resources to objects in a multi-object IFF.
    
    Args:
        iff_reader: IFF reader with chunks loaded
        filename: Source filename
        
    Returns:
        MultiObjectContext with all objects mapped
    """
    from .chunk_parsers import parse_objd
    
    ctx = MultiObjectContext(source_file=filename)
    
    # Find all OBJDs
    for chunk in iff_reader.chunks:
        if chunk.type_code == 'OBJD':
            objd = parse_objd(chunk.chunk_data, chunk.chunk_id)
            if objd:
                entry = MultiObjectContext.ObjectEntry(
                    objd_id=chunk.chunk_id,
                    ttab_id=objd.tree_table_id,
                    catalog_str_id=objd.catalog_strings_id,
                )
                
                # Extract GUID
                data = chunk.chunk_data
                if len(data) >= 32:
                    entry.guid = data[28] | (data[29] << 8) | (data[30] << 16) | (data[31] << 24)
                
                ctx.objects.append(entry)
    
    # Try to get names from catalog strings
    str_chunks = {c.chunk_id: c.chunk_data for c in iff_reader.chunks if c.type_code == 'STR#'}
    
    from .str_parser import STRParser
    
    for obj in ctx.objects:
        if obj.catalog_str_id in str_chunks:
            parsed = STRParser.parse(str_chunks[obj.catalog_str_id])
            if parsed.entries:
                obj.name = parsed.entries[0].get_value(0)  # First string is usually name
    
    return ctx


def parse_ttab_full(data: bytes, chunk_id: int = 0) -> ParsedTTAB:
    """Convenience function to parse TTAB."""
    return TTABParser.parse(data, chunk_id)
