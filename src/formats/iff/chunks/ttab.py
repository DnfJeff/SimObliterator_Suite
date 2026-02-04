"""
TTAB Chunk - Tree Tables (Interactions)
Port of FreeSO's tso.files/Formats/IFF/Chunks/TTAB.cs

TTAB defines the list of interactions (pie menu options) for an object.
Each interaction links to BHAV subroutines for action and test functions.
Labels are stored in TTAs chunks with matching IDs.
"""

from dataclasses import dataclass, field
from enum import IntFlag
from typing import TYPE_CHECKING, Optional

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer


class TTABFlags(IntFlag):
    """Interaction flags."""
    NONE = 0
    ALLOW_VISITORS = 1
    JOINABLE = 1 << 1
    RUN_IMMEDIATELY = 1 << 2
    ALLOW_CONSECUTIVE = 1 << 3
    
    # TS1 specific
    TS1_NO_CHILD = 1 << 4
    TS1_NO_DEMO_CHILD = 1 << 5
    TS1_NO_ADULT = 1 << 6
    
    DEBUG = 1 << 7
    AUTO_FIRST_SELECT = 1 << 8
    
    # Pet flags (overlap with TS1 flags)
    TS1_ALLOW_CATS = 1 << 9
    TS1_ALLOW_DOGS = 1 << 10
    LEAPFROG = 1 << 9
    MUST_RUN = 1 << 10
    ALLOW_DOGS = 1 << 11
    ALLOW_CATS = 1 << 12
    
    # Mask flags (bits 16-19)
    TSO_AVAILABLE_CARRYING = 1 << 16
    TSO_IS_REPAIR = 1 << 17
    TSO_RUN_CHECK_ALWAYS = 1 << 18
    TSO_AVAILABLE_WHEN_DEAD = 1 << 19


class TSOFlags(IntFlag):
    """TSO-specific interaction flags."""
    NONE = 0
    NON_EMPTY = 1
    ALLOW_OBJECT_OWNER = 1 << 1
    ALLOW_ROOMMATES = 1 << 2
    ALLOW_FRIENDS = 1 << 3
    ALLOW_VISITORS = 1 << 4
    ALLOW_GHOST = 1 << 5
    UNDER_PARENTAL_CONTROL = 1 << 6
    ALLOW_CSRS = 1 << 7


# Attenuation presets
ATTENUATION_VALUES = [0, 0, 0.1, 0.3, 0.6]  # custom, none, low, medium, high


@dataclass
class TTABMotiveEntry:
    """Motive effect for an interaction."""
    motive_index: int = 0
    effect_range_minimum: int = 0
    effect_range_delta: int = 0
    personality_modifier: int = 0


@dataclass
class TTABInteraction:
    """A single interaction definition."""
    action_function: int = 0       # BHAV ID for action
    test_function: int = 0         # BHAV ID for availability test
    motive_entries: list[TTABMotiveEntry] = field(default_factory=list)
    flags: TTABFlags = TTABFlags.NONE
    tta_index: int = 0             # Index into TTAs string list
    attenuation_code: int = 0      # Autonomy attenuation preset
    attenuation_value: float = 0.0 # Custom attenuation value
    autonomy_threshold: int = 0
    joining_index: int = -1
    flags2: TSOFlags = TSOFlags.NONE
    
    # Properties for common flags
    @property
    def allow_visitors(self) -> bool:
        return bool(self.flags & TTABFlags.ALLOW_VISITORS) or bool(self.flags2 & TSOFlags.ALLOW_VISITORS)
    
    @property
    def debug(self) -> bool:
        return bool(self.flags & TTABFlags.DEBUG)
    
    @property
    def run_immediately(self) -> bool:
        return bool(self.flags & TTABFlags.RUN_IMMEDIATELY)
    
    @property
    def auto_first(self) -> bool:
        return bool(self.flags & TTABFlags.AUTO_FIRST_SELECT)
    
    @property
    def must_run(self) -> bool:
        return bool(self.flags & TTABFlags.MUST_RUN)
    
    @property
    def joinable(self) -> bool:
        return bool(self.flags & TTABFlags.JOINABLE)


@register_chunk("TTAB")
@dataclass
class TTAB(IffChunk):
    """
    Tree table chunk - interaction definitions.
    Maps to: FSO.Files.Formats.IFF.Chunks.TTAB
    """
    interactions: list[TTABInteraction] = field(default_factory=list)
    version: int = 0
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read TTAB chunk from stream."""
        num_interactions = io.read_uint16()
        if num_interactions == 0:
            self.interactions = []
            return
        
        self.version = io.read_uint16()
        
        # Version 3 or below not supported
        if self.version <= 3:
            self.interactions = []
            return
        
        # Check for field encoding (versions 9-10)
        use_field_encoding = False
        if 9 <= self.version <= 10:
            compression_code = io.read_byte()
            use_field_encoding = (compression_code == 1)
        
        # Note: Field encoding is complex, we read normally for now
        # Full implementation would need IffFieldEncode decoder
        
        self.interactions = []
        for _ in range(num_interactions):
            interaction = TTABInteraction()
            interaction.action_function = io.read_uint16()
            interaction.test_function = io.read_uint16()
            
            num_motives = io.read_uint32()
            interaction.flags = TTABFlags(io.read_uint32())
            interaction.tta_index = io.read_uint32()
            
            if self.version > 6:
                interaction.attenuation_code = io.read_uint32()
            
            interaction.attenuation_value = io.read_float()
            interaction.autonomy_threshold = io.read_uint32()
            interaction.joining_index = io.read_int32()
            
            # Read motive entries
            interaction.motive_entries = []
            for j in range(num_motives):
                motive = TTABMotiveEntry()
                motive.motive_index = j
                
                if self.version > 6:
                    motive.effect_range_minimum = io.read_int16()
                
                motive.effect_range_delta = io.read_int16()
                
                if self.version > 6:
                    motive.personality_modifier = io.read_uint16()
                
                interaction.motive_entries.append(motive)
            
            # TSO flags for version > 9
            if self.version > 9:
                interaction.flags2 = TSOFlags(io.read_uint32())
            
            self.interactions.append(interaction)
    
    def get_interaction(self, index: int) -> Optional[TTABInteraction]:
        """Get interaction by index."""
        if 0 <= index < len(self.interactions):
            return self.interactions[index]
        return None
    
    def get_by_tta_index(self, tta_index: int) -> Optional[TTABInteraction]:
        """Get interaction by its TTAs string index."""
        for interaction in self.interactions:
            if interaction.tta_index == tta_index:
                return interaction
        return None
    
    def get_auto_interactions(self) -> list[TTABInteraction]:
        """Get interactions that can be triggered autonomously."""
        return [
            i for i in self.interactions 
            if any(m.effect_range_delta != 0 for m in i.motive_entries)
        ]
    
    def __len__(self) -> int:
        return len(self.interactions)
    
    def __getitem__(self, index: int) -> TTABInteraction:
        return self.interactions[index]
    
    def __iter__(self):
        return iter(self.interactions)
    
    def summary(self) -> str:
        """Get a summary of interactions."""
        lines = [f"TTAB #{self.chunk_id}: {self.chunk_label}"]
        lines.append(f"  Version: {self.version}, Interactions: {len(self.interactions)}")
        
        for i, inter in enumerate(self.interactions):
            flags_str = []
            if inter.debug:
                flags_str.append("DEBUG")
            if inter.auto_first:
                flags_str.append("AUTO")
            if inter.run_immediately:
                flags_str.append("IMMEDIATE")
            
            flag_part = f" [{','.join(flags_str)}]" if flags_str else ""
            lines.append(f"  {i}: Action=0x{inter.action_function:04X} Test=0x{inter.test_function:04X}{flag_part}")
        
        return "\n".join(lines)
    
    def __str__(self) -> str:
        return f"TTAB #{self.chunk_id}: {self.chunk_label} ({len(self.interactions)} interactions)"
