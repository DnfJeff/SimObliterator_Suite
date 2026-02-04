"""
CHAR Chunk - Character/Sim Personality Traits Data

What: Binary format for Sim personality traits, aspirations, motives, and skills.
Contains complete personality definition for a character in The Sims 1.

Reference: FreeSO tso.files/Formats/IFF/Chunks/CHAR.cs

Structure:
- Header: version
- Personality traits (5 main traits: neat, outgoing, active, playful, nice)
- Aspirations/goals
- Skills (cooking, mechanical, logic, body, charisma, cleaning)
- Motives/needs (hunger, energy, etc.)
- Zodiac/birth date
- Life span data

Used by: Character customization, Casual Cheater personality editor, NPC personality browsing.

Integration: Works with SIMI (appearance), NBRS (NPC data), and personality UI widgets.
"""

from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
import struct
import logging
from enum import IntEnum

from ..base import IffChunk, register_chunk

logger = logging.getLogger(__name__)


class Personality(IntEnum):
    """Personality trait indices (The Sims 1 standard 5 traits)."""
    NEAT = 0           # Neat/Sloppy
    OUTGOING = 1       # Outgoing/Shy
    ACTIVE = 2         # Active/Lazy
    PLAYFUL = 3        # Playful/Serious
    NICE = 4           # Nice/Mean
    
    @staticmethod
    def names() -> List[str]:
        return ["Neat", "Outgoing", "Active", "Playful", "Nice"]
    
    @staticmethod
    def descriptions() -> Dict[int, str]:
        return {
            Personality.NEAT: "Neat (clean) vs Sloppy (dirty)",
            Personality.OUTGOING: "Outgoing (social) vs Shy (withdrawn)",
            Personality.ACTIVE: "Active (energetic) vs Lazy (relaxed)",
            Personality.PLAYFUL: "Playful (fun) vs Serious (earnest)",
            Personality.NICE: "Nice (kind) vs Mean (cruel)",
        }


class Skill(IntEnum):
    """Skill indices (The Sims 1 skills)."""
    COOKING = 0        # Cooking skill
    MECHANICAL = 1     # Mechanical/Repair skill
    LOGIC = 2          # Logic skill
    BODY = 3           # Body/Fitness skill
    CHARISMA = 4       # Charisma skill
    CLEANING = 5       # Cleaning skill
    
    @staticmethod
    def names() -> List[str]:
        return ["Cooking", "Mechanical", "Logic", "Body", "Charisma", "Cleaning"]
    
    @staticmethod
    def max_level() -> int:
        return 10  # Skills go from 0-10


class Aspiration(IntEnum):
    """Life aspirations/goals."""
    FAMILY = 0          # Family-focused
    POPULARITY = 1      # Popularity-focused
    ROMANCE = 2         # Romance-focused
    FORTUNE = 3         # Fortune/Money-focused
    
    @staticmethod
    def names() -> List[str]:
        return ["Family", "Popularity", "Romance", "Fortune"]


@dataclass
class PersonalityTraits:
    """Complete personality definition for a Sim."""
    neat: int = 50              # Range: 0-100 (50 = neutral)
    outgoing: int = 50
    active: int = 50
    playful: int = 50
    nice: int = 50
    
    def get_trait(self, trait_id: int) -> int:
        """Get trait value by ID."""
        traits = [self.neat, self.outgoing, self.active, self.playful, self.nice]
        if 0 <= trait_id < len(traits):
            return traits[trait_id]
        return 50
    
    def set_trait(self, trait_id: int, value: int):
        """Set trait value (0-100)."""
        value = max(0, min(100, value))  # Clamp to 0-100
        if trait_id == Personality.NEAT:
            self.neat = value
        elif trait_id == Personality.OUTGOING:
            self.outgoing = value
        elif trait_id == Personality.ACTIVE:
            self.active = value
        elif trait_id == Personality.PLAYFUL:
            self.playful = value
        elif trait_id == Personality.NICE:
            self.nice = value
    
    def to_array(self) -> List[int]:
        """Convert to array format for binary storage."""
        return [self.neat, self.outgoing, self.active, self.playful, self.nice]
    
    @classmethod
    def from_array(cls, values: List[int]) -> 'PersonalityTraits':
        """Create from array (expects 5 values)."""
        if len(values) < 5:
            values = values + [50] * (5 - len(values))
        return cls(
            neat=values[0],
            outgoing=values[1],
            active=values[2],
            playful=values[3],
            nice=values[4]
        )
    
    def summary(self) -> str:
        """Get human-readable personality summary."""
        traits_str = []
        # Map trait indices to descriptions
        descriptions = {
            Personality.NEAT: ("Sloppy", "Neat"),
            Personality.OUTGOING: ("Shy", "Outgoing"),
            Personality.ACTIVE: ("Lazy", "Active"),
            Personality.PLAYFUL: ("Serious", "Playful"),
            Personality.NICE: ("Mean", "Nice"),
        }
        
        for i, name in enumerate(Personality.names()):
            value = self.get_trait(i)
            # Determine if leaning one way or other
            low_desc, high_desc = descriptions.get(i, (name, name))
            if value < 40:
                traits_str.append(f"{low_desc} ({value})")
            elif value > 60:
                traits_str.append(f"{high_desc} ({value})")
            else:
                traits_str.append(f"Balanced {name}")
        return ", ".join(traits_str)


@dataclass
class SkillSet:
    """Complete skill set for a Sim."""
    cooking: int = 0
    mechanical: int = 0
    logic: int = 0
    body: int = 0
    charisma: int = 0
    cleaning: int = 0
    
    def get_skill(self, skill_id: int) -> int:
        """Get skill level by ID (0-10)."""
        skills = [self.cooking, self.mechanical, self.logic, self.body, self.charisma, self.cleaning]
        if 0 <= skill_id < len(skills):
            return skills[skill_id]
        return 0
    
    def set_skill(self, skill_id: int, value: int):
        """Set skill level (0-10)."""
        value = max(0, min(Skill.max_level(), value))
        if skill_id == Skill.COOKING:
            self.cooking = value
        elif skill_id == Skill.MECHANICAL:
            self.mechanical = value
        elif skill_id == Skill.LOGIC:
            self.logic = value
        elif skill_id == Skill.BODY:
            self.body = value
        elif skill_id == Skill.CHARISMA:
            self.charisma = value
        elif skill_id == Skill.CLEANING:
            self.cleaning = value
    
    def to_array(self) -> List[int]:
        """Convert to array format."""
        return [self.cooking, self.mechanical, self.logic, self.body, self.charisma, self.cleaning]
    
    @classmethod
    def from_array(cls, values: List[int]) -> 'SkillSet':
        """Create from array."""
        if len(values) < 6:
            values = values + [0] * (6 - len(values))
        return cls(
            cooking=values[0],
            mechanical=values[1],
            logic=values[2],
            body=values[3],
            charisma=values[4],
            cleaning=values[5]
        )
    
    def total_points(self) -> int:
        """Calculate total skill points."""
        return sum(self.to_array())
    
    def summary(self) -> str:
        """Get human-readable skill summary."""
        skills_str = []
        for i, name in enumerate(Skill.names()):
            level = self.get_skill(i)
            if level > 0:
                skills_str.append(f"{name} {level}")
        return ", ".join(skills_str) if skills_str else "No skills"


@dataclass
class CharacterTraits:
    """Complete character personality and skill data."""
    personality: PersonalityTraits = field(default_factory=PersonalityTraits)
    skills: SkillSet = field(default_factory=SkillSet)
    aspiration: int = 0  # Aspiration type (Family/Popularity/Romance/Fortune)
    birthday_month: int = 1  # 1-12
    birthday_day: int = 1    # 1-31
    zodiac_sign: int = 0     # Computed from birthday
    life_span: int = 0       # Lifespan length (0=normal, 1=short, 2=long)
    
    def get_aspiration_name(self) -> str:
        """Get aspiration name."""
        aspiration_names = Aspiration.names()
        if 0 <= self.aspiration < len(aspiration_names):
            return aspiration_names[self.aspiration]
        return "Unknown"


class CHAR:
    """
    CHAR Chunk - Character Personality Traits
    
    Stores all personality-related data for a Sim.
    """
    
    chunk_type = b'CHAR'
    label = 'CHAR'
    
    def __init__(self):
        self.version: int = 0
        self.traits: CharacterTraits = CharacterTraits()
    
    def read(self, data: bytes):
        """Parse CHAR chunk from binary data.
        
        Format (based on FreeSO CHAR.cs):
        - Version (4 bytes, uint32)
        - Personality (5 bytes): neat, outgoing, active, playful, nice
        - Skills (6 bytes): cooking, mechanical, logic, body, charisma, cleaning
        - Aspiration (1 byte): family/popularity/romance/fortune
        - Birthday (2 bytes): month (0-11), day (0-30)
        """
        if len(data) < 4:
            logger.warning("CHAR chunk too small, need at least 4 bytes")
            return self
        
        offset = 0
        
        # Version
        self.version = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        
        logger.debug(f"CHAR: version={self.version:#x}, data_len={len(data)}")
        
        # Read personality traits (5 bytes, 0-100 scale)
        # Range: 0=very sloppy/shy/lazy/serious/mean, 50=balanced, 100=very neat/outgoing/active/playful/nice
        traits_data = []
        if offset + 5 <= len(data):
            for i, trait_name in enumerate(Personality.names()):
                trait_val = data[offset + i]
                traits_data.append(trait_val)
                logger.debug(f"  {trait_name}: {trait_val}")
            self.traits.personality = PersonalityTraits.from_array(traits_data)
            offset += 5
        else:
            logger.warning(f"CHAR: Insufficient data for traits (have {len(data)-offset}, need 5)")
        
        # Read skills (6 bytes, 0-10 scale)
        skills_data = []
        if offset + 6 <= len(data):
            for i, skill_name in enumerate(Skill.names()):
                skill_val = data[offset + i]
                skills_data.append(skill_val)
                logger.debug(f"  {skill_name}: {skill_val}")
            self.traits.skills = SkillSet.from_array(skills_data)
            offset += 6
        else:
            logger.warning(f"CHAR: Insufficient data for skills (have {len(data)-offset}, need 6)")
        
        # Read aspiration (1 byte)
        if offset + 1 <= len(data):
            self.traits.aspiration = min(data[offset], 3)  # Clamp to 0-3
            logger.debug(f"  Aspiration: {self.traits.get_aspiration_name()}")
            offset += 1
        
        # Read birthday (2 bytes: month, day)
        if offset + 2 <= len(data):
            month_byte = data[offset]
            day_byte = data[offset + 1]
            # Convert from 0-based to 1-based
            self.traits.birthday_month = month_byte + 1 if month_byte < 12 else 1
            self.traits.birthday_day = day_byte + 1 if day_byte < 31 else 1
            logger.debug(f"  Birthday: {self.traits.birthday_month}/{self.traits.birthday_day}")
            offset += 2
        
        logger.debug(f"CHAR: Parsed {offset} bytes total")
        
        return self
    
    def write(self) -> bytes:
        """Write CHAR chunk to binary data."""
        data = bytearray()
        
        # Version
        data.extend(struct.pack('<I', self.version))
        
        # Personality traits
        for trait in self.traits.personality.to_array():
            data.append(max(0, min(100, trait)))
        
        # Skills
        for skill in self.traits.skills.to_array():
            data.append(max(0, min(10, skill)))
        
        # Aspiration
        data.append(max(0, min(3, self.traits.aspiration)))
        
        # Birthday
        data.append(max(0, min(11, self.traits.birthday_month - 1)))
        data.append(max(0, min(30, self.traits.birthday_day - 1)))
        
        return bytes(data)
    
    def summary(self) -> str:
        """Get summary of character traits."""
        lines = [
            f"CHAR Chunk: {self.traits.get_aspiration_name()} aspiration",
            f"Personality: {self.traits.personality.summary()}",
            f"Skills: {self.traits.skills.summary()}",
            f"Birthday: {self.traits.birthday_month}/{self.traits.birthday_day}",
        ]
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return f"<CHAR {self.traits.get_aspiration_name()} {self.traits.personality.nice}>Nice"


# Register chunk
@register_chunk('CHAR')
class CHARChunk(CHAR):
    """CHAR chunk registered with IFF parser."""
    pass


__all__ = [
    'CHAR', 'CHARChunk',
    'PersonalityTraits', 'SkillSet', 'CharacterTraits',
    'Personality', 'Skill', 'Aspiration',
]
