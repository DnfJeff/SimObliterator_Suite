"""
Save Editor Backend for The Sims 1 Legacy Collection

Self-contained module - no external dependencies beyond standard library.
Provides high-level API for editing:
- Family money (FAMI.budget)
- Sim skills and personality (NBRS/User files)  
- Relationships
- Career/Job data

Based on FreeSO reverse engineering and Niotso wiki documentation.
"""

import struct
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from io import BytesIO

from utils.binary import IoBuffer, ByteOrder


# ============================================================================
# Data Classes for Save Data
# ============================================================================

@dataclass
class FamilyData:
    """Decoded FAMI chunk - family/household data."""
    chunk_id: int = 0
    version: int = 0x9
    house_number: int = 0
    family_number: int = 0  # -1 for townies
    budget: int = 0  # THE MONEY!
    value_in_arch: int = 0
    family_friends: int = 0
    flags: int = 0
    member_guids: List[int] = field(default_factory=list)
    
    # Metadata
    offset_in_file: int = 0
    budget_offset: int = 0  # Offset of budget field for direct editing
    
    @property
    def is_townie(self) -> bool:
        return self.family_number == -1
    
    @property 
    def is_user_created(self) -> bool:
        return bool(self.flags & 0x8)


@dataclass 
class NeighborData:
    """Decoded neighbor/Sim data from NBRS chunk."""
    neighbor_id: int = 0
    guid: int = 0
    name: str = ""
    person_mode: int = 0
    person_data: List[int] = field(default_factory=list)  # 88 shorts
    relationships: Dict[int, List[int]] = field(default_factory=dict)
    
    # Offset tracking for direct edits
    offset_in_file: int = 0
    person_data_offset: int = 0


@dataclass
class PersonData:
    """Sim attributes stored in person_data array (88 shorts)."""
    # Indices based on FreeSO VMPersonDataVariable
    COOKING_SKILL = 0
    MECH_SKILL = 1
    CHARISMA_SKILL = 2
    LOGIC_SKILL = 3
    BODY_SKILL = 4
    CREATIVITY_SKILL = 5
    CLEANING_SKILL = 6  # Yes, there's a cleaning skill internally
    
    NICE_PERSONALITY = 7
    ACTIVE_PERSONALITY = 8
    GENEROUS_PERSONALITY = 9
    PLAYFUL_PERSONALITY = 10
    OUTGOING_PERSONALITY = 11
    NEAT_PERSONALITY = 12
    
    HUNGER_MOTIVE = 13
    COMFORT_MOTIVE = 14
    HYGIENE_MOTIVE = 15
    BLADDER_MOTIVE = 16
    ENERGY_MOTIVE = 17
    FUN_MOTIVE = 18
    SOCIAL_MOTIVE = 19
    ROOM_MOTIVE = 20
    
    PERSON_AGE = 21
    GENDER = 22  # 0=male, 1=female
    
    JOB_TYPE = 23
    JOB_LEVEL = 24
    JOB_EXPERIENCE = 25
    JOB_PERFORMANCE = 26
    
    TS1_FAMILY_NUMBER = 42
    
    @classmethod
    def get_skill_indices(cls) -> List[Tuple[str, int]]:
        """Get all skill name/index pairs."""
        return [
            ("Cooking", cls.COOKING_SKILL),
            ("Mechanical", cls.MECH_SKILL),
            ("Charisma", cls.CHARISMA_SKILL),
            ("Logic", cls.LOGIC_SKILL),
            ("Body", cls.BODY_SKILL),
            ("Creativity", cls.CREATIVITY_SKILL),
        ]
    
    @classmethod
    def get_personality_indices(cls) -> List[Tuple[str, int]]:
        """Get all personality trait name/index pairs."""
        return [
            ("Nice", cls.NICE_PERSONALITY),
            ("Active", cls.ACTIVE_PERSONALITY),
            ("Generous", cls.GENEROUS_PERSONALITY),
            ("Playful", cls.PLAYFUL_PERSONALITY),
            ("Outgoing", cls.OUTGOING_PERSONALITY),
            ("Neat", cls.NEAT_PERSONALITY),
        ]
    
    @classmethod
    def get_motive_indices(cls) -> List[Tuple[str, int]]:
        """Get all motive name/index pairs."""
        return [
            ("Hunger", cls.HUNGER_MOTIVE),
            ("Comfort", cls.COMFORT_MOTIVE),
            ("Hygiene", cls.HYGIENE_MOTIVE),
            ("Bladder", cls.BLADDER_MOTIVE),
            ("Energy", cls.ENERGY_MOTIVE),
            ("Fun", cls.FUN_MOTIVE),
            ("Social", cls.SOCIAL_MOTIVE),
            ("Room", cls.ROOM_MOTIVE),
        ]


# ============================================================================
# Simple Helper Classes (Self-contained)
# ============================================================================

@dataclass
class IFFChunk:
    """Simple IFF chunk representation."""
    type_code: str = ""
    chunk_id: int = 0
    chunk_size: int = 0
    chunk_label: str = ""
    chunk_data: bytes = b""


class IoBuffer:
    """Simple binary buffer reader for parsing chunk data."""
    
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
    
    @classmethod
    def from_bytes(cls, data: bytes, byte_order=None) -> 'IoBuffer':
        """Create from bytes (byte_order ignored for compatibility)."""
        return cls(data)
    
    @property
    def has_more(self) -> bool:
        return self.pos < len(self.data)
    
    def read_byte(self) -> int:
        if self.pos >= len(self.data):
            return 0
        val = self.data[self.pos]
        self.pos += 1
        return val
    
    def read_bytes(self, count: int) -> bytes:
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result
    
    def read_int16(self) -> int:
        if self.pos + 2 > len(self.data):
            return 0
        val = struct.unpack('<h', self.data[self.pos:self.pos + 2])[0]
        self.pos += 2
        return val
    
    def read_uint16(self) -> int:
        if self.pos + 2 > len(self.data):
            return 0
        val = struct.unpack('<H', self.data[self.pos:self.pos + 2])[0]
        self.pos += 2
        return val
    
    def read_int32(self) -> int:
        if self.pos + 4 > len(self.data):
            return 0
        val = struct.unpack('<i', self.data[self.pos:self.pos + 4])[0]
        self.pos += 4
        return val
    
    def read_uint32(self) -> int:
        if self.pos + 4 > len(self.data):
            return 0
        val = struct.unpack('<I', self.data[self.pos:self.pos + 4])[0]
        self.pos += 4
        return val
    
    def skip(self, count: int):
        self.pos += count


# ============================================================================
# Low-Level IFF Manipulation
# ============================================================================

class IFFEditor:
    """
    Low-level IFF file editor with direct byte manipulation.
    This preserves file structure while allowing targeted edits.
    """
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.data: bytearray = bytearray()
        self.chunks: List[IFFChunk] = []
        self.rsmp_offset: int = 0
        self._dirty = False
        
    def load(self) -> bool:
        """Load IFF file into memory."""
        try:
            with open(self.filepath, 'rb') as f:
                self.data = bytearray(f.read())
            
            # Parse header
            if len(self.data) < 64:
                return False
            
            # rsmp offset at bytes 60-63 (big-endian)
            self.rsmp_offset = struct.unpack('>I', self.data[60:64])[0]
            
            # Parse chunks
            # NOTE: In IFF files, the size field INCLUDES the 76-byte header!
            self.chunks = []
            offset = 64
            while offset < self.rsmp_offset:
                chunk = self._parse_chunk_header(offset)
                if chunk is None:
                    break
                self.chunks.append(chunk)
                # Move by total size (which includes the 76-byte header)
                offset += chunk.chunk_size
            
            return True
        except Exception as e:
            print(f"Error loading IFF: {e}")
            return False
    
    def _parse_chunk_header(self, offset: int) -> Optional[IFFChunk]:
        """Parse chunk header at offset."""
        if offset + 76 > len(self.data):
            return None
        
        chunk = IFFChunk()
        chunk.type_code = self.data[offset:offset+4].decode('latin-1', errors='replace')
        # Size INCLUDES the 76-byte header
        chunk.chunk_size = struct.unpack('>I', self.data[offset+4:offset+8])[0]
        chunk.chunk_id = struct.unpack('>H', self.data[offset+8:offset+10])[0]
        # chunk_flags at offset+10:offset+12
        chunk.chunk_label = self.data[offset+12:offset+76].rstrip(b'\x00').decode('latin-1', errors='replace')
        # Data size is total size minus header
        data_size = chunk.chunk_size - 76
        if data_size > 0:
            chunk.chunk_data = bytes(self.data[offset+76:offset+76+data_size])
        else:
            chunk.chunk_data = b""
        
        return chunk
    
    def get_chunk(self, type_code: str, chunk_id: int = None) -> Optional[IFFChunk]:
        """Find a chunk by type (and optionally ID)."""
        for chunk in self.chunks:
            if chunk.type_code == type_code:
                if chunk_id is None or chunk.chunk_id == chunk_id:
                    return chunk
        return None
    
    def get_chunks_by_type(self, type_code: str) -> List[IFFChunk]:
        """Get all chunks of a specific type."""
        return [c for c in self.chunks if c.type_code == type_code]
    
    def write_bytes_at(self, offset: int, data: bytes):
        """Write bytes at a specific offset."""
        for i, b in enumerate(data):
            if offset + i < len(self.data):
                self.data[offset + i] = b
        self._dirty = True
    
    def read_int32_le(self, offset: int) -> int:
        """Read little-endian int32 at offset."""
        return struct.unpack('<i', self.data[offset:offset+4])[0]
    
    def write_int32_le(self, offset: int, value: int):
        """Write little-endian int32 at offset."""
        self.write_bytes_at(offset, struct.pack('<i', value))
    
    def read_int16_le(self, offset: int) -> int:
        """Read little-endian int16 at offset."""
        return struct.unpack('<h', self.data[offset:offset+2])[0]
    
    def write_int16_le(self, offset: int, value: int):
        """Write little-endian int16 at offset."""
        self.write_bytes_at(offset, struct.pack('<h', value))
    
    def save(self, filepath: str = None):
        """Save IFF file."""
        if filepath is None:
            filepath = self.filepath
        
        with open(filepath, 'wb') as f:
            f.write(self.data)
        
        self._dirty = False
    
    @property
    def is_dirty(self) -> bool:
        return self._dirty


# ============================================================================
# High-Level Save Manager
# ============================================================================

class SaveManager:
    """
    High-level save file manager for The Sims 1 Legacy Collection.
    
    Handles:
    - Neighborhood.iff: Contains FAMI (families), NBRS (neighbors), NGBH (neighborhood data)
    - User#####.iff: Individual Sim data
    - House##.iff: House/lot data
    """
    
    def __init__(self, userdata_path: str):
        self.userdata_path = Path(userdata_path)
        self.neighborhood_path: Optional[Path] = None
        self.neighborhood: Optional[IFFEditor] = None
        self.families: Dict[int, FamilyData] = {}
        self.neighbors: Dict[int, NeighborData] = {}
        
    def find_neighborhood(self, neighborhood_id: int = 1) -> Optional[Path]:
        """Find the Neighborhood.iff file for a given neighborhood ID."""
        # Standard path: UserData/Neighborhoods/N001/Neighborhood.iff
        # Or for Legacy Collection: UserData7/Neighborhood.iff
        
        # Try various paths
        possible_paths = [
            self.userdata_path / "Neighborhood.iff",
            self.userdata_path / f"N00{neighborhood_id}" / "Neighborhood.iff",
            self.userdata_path / "Neighborhoods" / f"N00{neighborhood_id}" / "Neighborhood.iff",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def load_neighborhood(self, neighborhood_id: int = 1) -> bool:
        """Load a neighborhood's data."""
        path = self.find_neighborhood(neighborhood_id)
        if path is None:
            # Try to find any Neighborhood.iff
            for p in self.userdata_path.rglob("Neighborhood.iff"):
                path = p
                break
        
        if path is None or not path.exists():
            print(f"Could not find Neighborhood.iff in {self.userdata_path}")
            return False
        
        self.neighborhood_path = path
        self.neighborhood = IFFEditor(str(path))
        
        if not self.neighborhood.load():
            return False
        
        # Parse families and neighbors
        self._parse_families()
        self._parse_neighbors()
        
        return True
    
    def _parse_families(self):
        """Parse all FAMI chunks from neighborhood."""
        self.families = {}
        
        for chunk in self.neighborhood.get_chunks_by_type('FAMI'):
            fami = self._decode_fami(chunk)
            if fami:
                self.families[fami.chunk_id] = fami
    
    def _decode_fami(self, chunk: IFFChunk) -> Optional[FamilyData]:
        """Decode a FAMI chunk."""
        data = chunk.chunk_data
        if len(data) < 40:
            return None
        
        try:
            fami = FamilyData(chunk_id=chunk.chunk_id)
            
            # Find chunk offset in file
            # Note: chunk.chunk_size INCLUDES the 76-byte header
            for i, c in enumerate(self.neighborhood.chunks):
                if c is chunk:
                    offset = 64  # After file header
                    for j in range(i):
                        # Size includes header, so just add it directly
                        offset += self.neighborhood.chunks[j].chunk_size
                    fami.offset_in_file = offset + 76  # Data starts after chunk header
                    break
            
            # FAMI format (little-endian):
            # 0-3: padding (0)
            # 4-7: version (0x9)
            # 8-11: magic "IMAF"
            # 12-15: house_number
            # 16-19: family_number
            # 20-23: budget (MONEY!)
            # 24-27: value_in_arch
            # 28-31: family_friends
            # 32-35: flags/unknown
            # 36-39: member_count
            # 40+: member GUIDs (4 bytes each)
            
            fami.version = struct.unpack('<I', data[4:8])[0]
            # magic = data[8:12]  # "IMAF"
            fami.house_number = struct.unpack('<i', data[12:16])[0]
            fami.family_number = struct.unpack('<i', data[16:20])[0]
            fami.budget = struct.unpack('<i', data[20:24])[0]
            fami.budget_offset = fami.offset_in_file + 20  # Offset of budget in file
            fami.value_in_arch = struct.unpack('<i', data[24:28])[0]
            fami.family_friends = struct.unpack('<i', data[28:32])[0]
            fami.flags = struct.unpack('<i', data[32:36])[0]
            
            member_count = struct.unpack('<i', data[36:40])[0]
            fami.member_guids = []
            for i in range(member_count):
                offset = 40 + i * 4
                if offset + 4 <= len(data):
                    guid = struct.unpack('<I', data[offset:offset+4])[0]
                    fami.member_guids.append(guid)
            
            return fami
        except Exception as e:
            print(f"Error decoding FAMI: {e}")
            return None
    
    def _parse_neighbors(self):
        """Parse NBRS chunk from neighborhood."""
        self.neighbors = {}
        
        chunk = self.neighborhood.get_chunk('NBRS')
        if chunk is None:
            return
        
        data = chunk.chunk_data
        if len(data) < 16:
            return
        
        # Find chunk data offset in file
        nbrs_offset = 64  # File header
        for c in self.neighborhood.chunks:
            if c is chunk:
                break
            nbrs_offset += c.chunk_size
        nbrs_data_offset = nbrs_offset + 76  # After chunk header
        
        try:
            buf = IoBuffer.from_bytes(data, ByteOrder.LITTLE_ENDIAN)
            
            _pad = buf.read_uint32()
            _version = buf.read_uint32()  # 0x49
            _magic = buf.read_bytes(4)    # "SRBN"
            count = buf.read_uint32()
            
            for _ in range(count):
                if not buf.has_more:
                    break
                
                neigh = self._read_neighbor(buf, nbrs_data_offset)
                if neigh and neigh.neighbor_id > 0:
                    self.neighbors[neigh.neighbor_id] = neigh
                    
        except Exception as e:
            print(f"Error parsing NBRS: {e}")
    
    def _read_neighbor(self, buf: IoBuffer, base_offset: int = 0) -> Optional[NeighborData]:
        """Read a single neighbor entry.
        
        Args:
            buf: Buffer positioned at start of neighbor entry
            base_offset: File offset where NBRS chunk data begins (for offset tracking)
        """
        try:
            neigh = NeighborData()
            entry_start = buf.pos
            neigh.offset_in_file = base_offset + entry_start
            
            unknown1 = buf.read_int32()
            if unknown1 != 1:
                return None
            
            version = buf.read_int32()
            
            if version == 0xA:
                _unknown3 = buf.read_int32()
            
            # Read null-terminated name
            name_bytes = bytearray()
            while buf.has_more:
                b = buf.read_byte()
                if b == 0:
                    break
                name_bytes.append(b)
            neigh.name = name_bytes.decode('latin-1', errors='replace')
            
            # Padding
            if len(neigh.name) % 2 == 0:
                buf.read_byte()
            
            _mystery_zero = buf.read_int32()
            neigh.person_mode = buf.read_int32()
            
            # Person data - track offset before reading
            if neigh.person_mode > 0:
                neigh.person_data_offset = base_offset + buf.pos  # Track file offset!
                size = 0xA0 if version == 0x4 else 0x200
                neigh.person_data = []
                bytes_read = 0
                while bytes_read < size and len(neigh.person_data) < 88:
                    neigh.person_data.append(buf.read_int16())
                    bytes_read += 2
                # Skip remaining
                if bytes_read < size:
                    buf.skip(size - bytes_read)
            
            neigh.neighbor_id = buf.read_int16()
            neigh.guid = buf.read_uint32()
            _unknown_neg_one = buf.read_int32()
            
            # Relationships
            num_rels = buf.read_int32()
            for _ in range(num_rels):
                _key_count = buf.read_int32()
                key = buf.read_int32()
                value_count = buf.read_int32()
                values = [buf.read_int32() for _ in range(value_count)]
                neigh.relationships[key] = values
            
            return neigh
        except Exception as e:
            return None
    
    # ========================================================================
    # Edit Operations
    # ========================================================================
    
    def set_family_money(self, family_id: int, amount: int) -> bool:
        """Set a family's budget/money."""
        if family_id not in self.families:
            print(f"Family {family_id} not found")
            return False
        
        fami = self.families[family_id]
        
        # Update in memory
        fami.budget = amount
        
        # Update in file data
        self.neighborhood.write_int32_le(fami.budget_offset, amount)
        
        print(f"Set family {family_id} money to ${amount:,}")
        return True
    
    def get_family_money(self, family_id: int) -> Optional[int]:
        """Get a family's current budget."""
        if family_id not in self.families:
            return None
        return self.families[family_id].budget
    
    # ========================================================================
    # Sim Attribute Edit Operations (Skills, Motives, Personality, Career)
    # ========================================================================
    
    def _get_person_data_offset(self, neighbor_id: int, index: int) -> Optional[int]:
        """Get the file offset for a specific person_data index (each is 2 bytes)."""
        if neighbor_id not in self.neighbors:
            return None
        neigh = self.neighbors[neighbor_id]
        if neigh.person_data_offset == 0:
            return None
        if index < 0 or index >= 88:
            return None
        return neigh.person_data_offset + (index * 2)
    
    def set_sim_skill(self, neighbor_id: int, skill: str, level: int) -> bool:
        """
        Set a Sim's skill level.
        
        Args:
            neighbor_id: The Sim's neighbor ID
            skill: Skill name (cooking, mechanical, charisma, logic, body, creativity)
            level: Skill level (0-1000, where 1000 = max)
        """
        skill_map = {
            'cooking': PersonData.COOKING_SKILL,
            'mechanical': PersonData.MECH_SKILL,
            'charisma': PersonData.CHARISMA_SKILL,
            'logic': PersonData.LOGIC_SKILL,
            'body': PersonData.BODY_SKILL,
            'creativity': PersonData.CREATIVITY_SKILL,
        }
        
        skill_lower = skill.lower()
        if skill_lower not in skill_map:
            print(f"Unknown skill: {skill}")
            return False
        
        index = skill_map[skill_lower]
        offset = self._get_person_data_offset(neighbor_id, index)
        if offset is None:
            print(f"Neighbor {neighbor_id} not found or has no person_data")
            return False
        
        # Clamp value
        level = max(0, min(level, 1000))
        
        # Update in memory
        neigh = self.neighbors[neighbor_id]
        if len(neigh.person_data) > index:
            neigh.person_data[index] = level
        
        # Update in file
        self.neighborhood.write_int16_le(offset, level)
        print(f"Set {neigh.name}'s {skill} to {level}")
        return True
    
    def set_sim_motive(self, neighbor_id: int, motive: str, value: int) -> bool:
        """
        Set a Sim's motive value.
        
        Args:
            neighbor_id: The Sim's neighbor ID
            motive: Motive name (hunger, comfort, hygiene, bladder, energy, fun, social, room)
            value: Motive value (-100 to 100, where 100 = full)
        """
        motive_map = {
            'hunger': PersonData.HUNGER_MOTIVE,
            'comfort': PersonData.COMFORT_MOTIVE,
            'hygiene': PersonData.HYGIENE_MOTIVE,
            'bladder': PersonData.BLADDER_MOTIVE,
            'energy': PersonData.ENERGY_MOTIVE,
            'fun': PersonData.FUN_MOTIVE,
            'social': PersonData.SOCIAL_MOTIVE,
            'room': PersonData.ROOM_MOTIVE,
        }
        
        motive_lower = motive.lower()
        if motive_lower not in motive_map:
            print(f"Unknown motive: {motive}")
            return False
        
        index = motive_map[motive_lower]
        offset = self._get_person_data_offset(neighbor_id, index)
        if offset is None:
            print(f"Neighbor {neighbor_id} not found or has no person_data")
            return False
        
        # Clamp value (motives are typically -100 to 100 scaled)
        value = max(-100, min(value, 100))
        
        # Update in memory
        neigh = self.neighbors[neighbor_id]
        if len(neigh.person_data) > index:
            neigh.person_data[index] = value
        
        # Update in file
        self.neighborhood.write_int16_le(offset, value)
        print(f"Set {neigh.name}'s {motive} to {value}")
        return True
    
    def set_sim_personality(self, neighbor_id: int, trait: str, value: int) -> bool:
        """
        Set a Sim's personality trait.
        
        Args:
            neighbor_id: The Sim's neighbor ID
            trait: Trait name (nice, active, generous, playful, outgoing, neat)
            value: Trait value (0-1000)
        """
        trait_map = {
            'nice': PersonData.NICE_PERSONALITY,
            'active': PersonData.ACTIVE_PERSONALITY,
            'generous': PersonData.GENEROUS_PERSONALITY,
            'playful': PersonData.PLAYFUL_PERSONALITY,
            'outgoing': PersonData.OUTGOING_PERSONALITY,
            'neat': PersonData.NEAT_PERSONALITY,
        }
        
        trait_lower = trait.lower()
        if trait_lower not in trait_map:
            print(f"Unknown personality trait: {trait}")
            return False
        
        index = trait_map[trait_lower]
        offset = self._get_person_data_offset(neighbor_id, index)
        if offset is None:
            print(f"Neighbor {neighbor_id} not found or has no person_data")
            return False
        
        # Clamp value
        value = max(0, min(value, 1000))
        
        # Update in memory
        neigh = self.neighbors[neighbor_id]
        if len(neigh.person_data) > index:
            neigh.person_data[index] = value
        
        # Update in file
        self.neighborhood.write_int16_le(offset, value)
        print(f"Set {neigh.name}'s {trait} to {value}")
        return True
    
    def set_sim_career(self, neighbor_id: int, job_type: int = None, 
                       job_level: int = None, job_exp: int = None,
                       job_performance: int = None) -> bool:
        """
        Set a Sim's career/job data.
        
        Args:
            neighbor_id: The Sim's neighbor ID
            job_type: Job type ID (None to keep current)
            job_level: Job level 1-10 (None to keep current)
            job_exp: Job experience points (None to keep current)
            job_performance: Job performance (None to keep current)
        """
        if neighbor_id not in self.neighbors:
            print(f"Neighbor {neighbor_id} not found")
            return False
        
        neigh = self.neighbors[neighbor_id]
        
        if job_type is not None:
            offset = self._get_person_data_offset(neighbor_id, PersonData.JOB_TYPE)
            if offset:
                neigh.person_data[PersonData.JOB_TYPE] = job_type
                self.neighborhood.write_int16_le(offset, job_type)
        
        if job_level is not None:
            offset = self._get_person_data_offset(neighbor_id, PersonData.JOB_LEVEL)
            if offset:
                level = max(1, min(job_level, 10))
                neigh.person_data[PersonData.JOB_LEVEL] = level
                self.neighborhood.write_int16_le(offset, level)
        
        if job_exp is not None:
            offset = self._get_person_data_offset(neighbor_id, PersonData.JOB_EXPERIENCE)
            if offset:
                neigh.person_data[PersonData.JOB_EXPERIENCE] = job_exp
                self.neighborhood.write_int16_le(offset, job_exp)
        
        if job_performance is not None:
            offset = self._get_person_data_offset(neighbor_id, PersonData.JOB_PERFORMANCE)
            if offset:
                neigh.person_data[PersonData.JOB_PERFORMANCE] = job_performance
                self.neighborhood.write_int16_le(offset, job_performance)
        
        print(f"Updated {neigh.name}'s career data")
        return True
    
    def max_all_skills(self, neighbor_id: int) -> bool:
        """Set all of a Sim's skills to maximum (1000)."""
        success = True
        for skill_name, _ in PersonData.get_skill_indices():
            if not self.set_sim_skill(neighbor_id, skill_name, 1000):
                success = False
        return success
    
    def max_all_motives(self, neighbor_id: int) -> bool:
        """Set all of a Sim's motives to maximum (100)."""
        success = True
        for motive_name, _ in PersonData.get_motive_indices():
            if not self.set_sim_motive(neighbor_id, motive_name, 100):
                success = False
        return success
    
    # ========================================================================
    # Relationship Operations
    # Note: Relationships are variable-length in NBRS, so modifications here
    # are in-memory only. Call rebuild_nbrs_chunk() to persist changes.
    # ========================================================================
    
    def get_relationship(self, neighbor_id: int, target_id: int) -> Optional[List[int]]:
        """Get relationship values between two sims.
        
        Returns list of [daily, lifetime] or None if no relationship.
        """
        if neighbor_id not in self.neighbors:
            return None
        neigh = self.neighbors[neighbor_id]
        return neigh.relationships.get(target_id)
    
    def set_relationship(self, neighbor_id: int, target_id: int, 
                         daily: int = None, lifetime: int = None) -> bool:
        """Set relationship values between two sims.
        
        Note: Changes are in-memory. Call rebuild_nbrs_chunk() to persist.
        
        Args:
            neighbor_id: Source sim
            target_id: Target sim
            daily: Daily relationship value (-100 to 100)
            lifetime: Lifetime relationship value (-100 to 100)
        """
        if neighbor_id not in self.neighbors:
            print(f"Neighbor {neighbor_id} not found")
            return False
        
        neigh = self.neighbors[neighbor_id]
        
        # Get or create relationship entry
        if target_id not in neigh.relationships:
            neigh.relationships[target_id] = [0, 0]  # [daily, lifetime]
        
        rel = neigh.relationships[target_id]
        
        if daily is not None:
            rel[0] = max(-100, min(daily, 100))
        if lifetime is not None:
            if len(rel) > 1:
                rel[1] = max(-100, min(lifetime, 100))
            else:
                rel.append(max(-100, min(lifetime, 100)))
        
        print(f"Set {neigh.name}'s relationship with neighbor {target_id}: daily={rel[0]}, lifetime={rel[1] if len(rel) > 1 else 'N/A'}")
        print("  (Note: Call rebuild_nbrs_chunk() to persist)")
        return True
    
    def make_friends(self, neighbor_id: int, target_id: int) -> bool:
        """Set a relationship to best friends (100/100)."""
        return self.set_relationship(neighbor_id, target_id, 100, 100)
    
    def make_enemies(self, neighbor_id: int, target_id: int) -> bool:
        """Set a relationship to enemies (-100/-100)."""
        return self.set_relationship(neighbor_id, target_id, -100, -100)
    
    def list_families(self) -> List[FamilyData]:
        """Get all families in the neighborhood."""
        return list(self.families.values())
    
    def get_family_by_house(self, house_number: int) -> Optional[FamilyData]:
        """Find the family living in a specific house."""
        for fami in self.families.values():
            if fami.house_number == house_number:
                return fami
        return None
    
    def list_neighbors(self) -> List[NeighborData]:
        """Get all neighbors in the neighborhood."""
        return list(self.neighbors.values())
    
    def get_neighbor(self, neighbor_id: int) -> Optional[NeighborData]:
        """Get a specific neighbor by ID."""
        return self.neighbors.get(neighbor_id)
    
    def get_neighbor_by_guid(self, guid: int) -> Optional[NeighborData]:
        """Get a neighbor by their GUID."""
        for neigh in self.neighbors.values():
            if neigh.guid == guid:
                return neigh
        return None
    
    def save_neighborhood(self, backup: bool = True) -> bool:
        """Save changes to the neighborhood file."""
        if self.neighborhood is None:
            return False
        
        # Create backup
        if backup and self.neighborhood_path:
            backup_path = self.neighborhood_path.with_suffix('.iff.bak')
            import shutil
            shutil.copy2(self.neighborhood_path, backup_path)
            print(f"Backup saved to {backup_path}")
        
        # Save
        self.neighborhood.save()
        print(f"Saved {self.neighborhood_path}")
        return True
    
    # ========================================================================
    # User File Operations (Individual Sim data)
    # ========================================================================
    
    def find_user_files(self) -> List[Path]:
        """Find all User#####.iff files in the userdata folder."""
        user_files = []
        for path in self.userdata_path.rglob("User*.iff"):
            if path.name.startswith("User") and path.name.endswith(".iff"):
                user_files.append(path)
        return sorted(user_files)
    
    def load_user_file(self, filepath: str) -> Optional[IFFEditor]:
        """Load a User#####.iff file for editing."""
        editor = IFFEditor(filepath)
        if editor.load():
            return editor
        return None
    
    # ========================================================================
    # Reporting
    # ========================================================================
    
    def print_summary(self):
        """Print a summary of the loaded neighborhood."""
        print(f"\n{'='*60}")
        print(f"Neighborhood: {self.neighborhood_path}")
        print(f"{'='*60}")
        
        print(f"\nFamilies ({len(self.families)}):")
        print("-" * 40)
        for fami in sorted(self.families.values(), key=lambda f: f.chunk_id):
            house = f"House {fami.house_number}" if fami.house_number > 0 else "No house"
            townie = " [Townie]" if fami.is_townie else ""
            print(f"  ID {fami.chunk_id}: ${fami.budget:,} | {len(fami.member_guids)} members | {house}{townie}")
        
        print(f"\nNeighbors ({len(self.neighbors)}):")
        print("-" * 40)
        for neigh in sorted(self.neighbors.values(), key=lambda n: n.neighbor_id)[:20]:
            skills = ""
            if neigh.person_data and len(neigh.person_data) > 6:
                skill_sum = sum(neigh.person_data[:6])
                skills = f" | Skills: {skill_sum}"
            print(f"  [{neigh.neighbor_id:3}] {neigh.name[:20]:<20} GUID: 0x{neigh.guid:08X}{skills}")
        
        if len(self.neighbors) > 20:
            print(f"  ... and {len(self.neighbors) - 20} more neighbors")


# ============================================================================
# Quick Test
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Default test path - adjust for your system
    test_path = r"C:\Program Files (x86)\Steam\steamapps\common\The Sims Legacy Collection\UserData7"
    
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    
    print(f"Testing SaveManager with: {test_path}")
    
    mgr = SaveManager(test_path)
    if mgr.load_neighborhood():
        mgr.print_summary()
        
        # Test money edit
        if mgr.families:
            first_family = next(iter(mgr.families.values()))
            print(f"\nFirst family budget: ${first_family.budget:,}")
            # mgr.set_family_money(first_family.chunk_id, 999999)
            # mgr.save_neighborhood()
    else:
        print("Failed to load neighborhood")
