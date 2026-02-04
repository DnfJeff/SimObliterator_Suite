"""
Lot IFF / Ambience Investigation Module

Provides comprehensive analysis of lot IFF files including:
- Terrain type detection by house number (as discovered in FreeSO)
- Ambience sound resource identification
- Lot structure analysis (ARRY chunks for floors, walls, objects)
- SIMI (Simulation Info) parsing for lot metadata
- HOUS chunk parsing for camera/roof settings
- Object placement maps (OBJM/OBJT)

Based on research from:
- FreeSO/tso.simantics/Utils/VMTS1Activator.cs
- FreeSO/tso.simantics/Engine/VMAmbientSound.cs
- riperiperi's Legacy Collection technical overview
- TheSimsOpenTechDoc

Author: SimObliterator Suite
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple, Any, Set
from pathlib import Path
import struct


# ═══════════════════════════════════════════════════════════════════════════════
# TERRAIN TYPES (from FreeSO VMTS1Activator)
# ═══════════════════════════════════════════════════════════════════════════════

class TerrainType(Enum):
    """Terrain/grass types for lots.
    
    Terrain is NOT stored in the lot IFF - it's determined by house number.
    This was confirmed by FreeSO and riperiperi's Legacy Collection analysis.
    """
    GRASS = "grass"            # Default for most lots
    SAND = "sand"              # Beach lots (Downtown, Vacation island)
    SNOW = "snow"              # Vacation winter lots
    TS1_DARK_GRASS = "dark"    # Studio Town lots
    TS1_AUTUMN_GRASS = "autumn"  # Magic Town autumn
    TS1_CLOUD = "cloud"        # Magic cloud realm


# House number to terrain type mapping (from FreeSO)
HOUSE_NUMBER_TO_TERRAIN: Dict[int, TerrainType] = {
    # Downtown beach lots
    28: TerrainType.SAND,
    29: TerrainType.SAND,
    
    # Vacation winter lots
    40: TerrainType.SNOW,
    41: TerrainType.SNOW,
    42: TerrainType.SNOW,
    
    # Vacation beach lots
    46: TerrainType.SAND,
    47: TerrainType.SAND,
    48: TerrainType.SAND,
    
    # Studio Town lots (dark grass)
    90: TerrainType.TS1_DARK_GRASS,
    91: TerrainType.TS1_DARK_GRASS,
    92: TerrainType.TS1_DARK_GRASS,
    93: TerrainType.TS1_DARK_GRASS,
    94: TerrainType.TS1_DARK_GRASS,
    
    # Magic Town autumn
    95: TerrainType.TS1_AUTUMN_GRASS,
    96: TerrainType.TS1_AUTUMN_GRASS,
    
    # Magic cloud realm
    99: TerrainType.TS1_CLOUD,
}


def get_terrain_type(house_number: int) -> TerrainType:
    """Get terrain type for a lot by house number.
    
    Args:
        house_number: The house number (from filename or Global[10])
        
    Returns:
        TerrainType for the lot (defaults to GRASS)
    """
    return HOUSE_NUMBER_TO_TERRAIN.get(house_number, TerrainType.GRASS)


def extract_house_number(filename: str) -> Optional[int]:
    """Extract house number from a lot IFF filename.
    
    Args:
        filename: Like "House00.iff" or "User00088.iff"
        
    Returns:
        House number or None if parsing fails
    """
    import re
    match = re.search(r'(\d+)', Path(filename).stem)
    if match:
        return int(match.group(1))
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# AMBIENCE SYSTEM (from FreeSO VMAmbientSound)
# ═══════════════════════════════════════════════════════════════════════════════

class AmbienceCategory(Enum):
    """Categories for ambient sounds."""
    ANIMALS = 0       # Birds, dogs, farm animals, wolves
    MECHANICAL = 1    # Construction, sirens, industrial, gunshots
    WEATHER = 2       # Wind, rain, thunder
    PEOPLE = 3        # Office, restaurant, screams, magic
    LOOPS = 4         # Background loops (brook, crowd, indoor, outdoor)


@dataclass
class AmbienceDefinition:
    """Definition of an ambient sound."""
    guid: int                 # Object GUID that triggers this
    category: AmbienceCategory
    name: str                 # Human-readable name
    sound_path: str           # Path to sound file
    is_loop: bool = False     # True for continuous loops


# Ambient sound definitions (from FreeSO VMAmbientSound.cs)
AMBIENCE_DEFINITIONS: List[AmbienceDefinition] = [
    # Animals
    AmbienceDefinition(0x3dd887a6, AmbienceCategory.ANIMALS, "DayBirds", 
                       "sounddata/ambience/daybirds/daybirds.fsc"),
    AmbienceDefinition(0x7dd887ad, AmbienceCategory.ANIMALS, "FarmAnimals",
                       "sounddata/ambience/farmanimals/farmanimals.fsc"),
    AmbienceDefinition(0x5e12818c, AmbienceCategory.ANIMALS, "Dog",
                       "sounddata/ambience/dog/dog.fsc"),
    AmbienceDefinition(0xbe128196, AmbienceCategory.ANIMALS, "Jungle",
                       "sounddata/ambience/jungle/jungle.fsc"),
    AmbienceDefinition(0x1e1281ad, AmbienceCategory.ANIMALS, "Wolf",
                       "sounddata/ambience/wolf/wolf.fsc"),
    AmbienceDefinition(0xbe19bb2d, AmbienceCategory.ANIMALS, "SeaBirds",
                       "sounddata/ambience/seabirds/seabirds.fsc"),
    AmbienceDefinition(0x3e128192, AmbienceCategory.ANIMALS, "Insects",
                       "sounddata/ambience/insect/insect.fsc"),
    AmbienceDefinition(0xa9b96539, AmbienceCategory.ANIMALS, "NightBirds",
                       "sounddata/ambience/nightbirds/nightbirds.fsc"),
    
    # Mechanical
    AmbienceDefinition(0x3dd887aa, AmbienceCategory.MECHANICAL, "Explosions",
                       "sounddata/ambience/explosions/explosions.fsc"),
    AmbienceDefinition(0x9dd887af, AmbienceCategory.MECHANICAL, "Gunshots",
                       "sounddata/ambience/gunshots/gunshots.fsc"),
    AmbienceDefinition(0xddd887b3, AmbienceCategory.MECHANICAL, "Planes",
                       "sounddata/ambience/planes/planes.fsc"),
    AmbienceDefinition(0xfe128189, AmbienceCategory.MECHANICAL, "Construction",
                       "sounddata/ambience/construction/construction.fsc"),
    AmbienceDefinition(0xbe12818d, AmbienceCategory.MECHANICAL, "DriveBy",
                       "sounddata/ambience/driveby/driveby.fsc"),
    AmbienceDefinition(0x1e128190, AmbienceCategory.MECHANICAL, "Industrial",
                       "sounddata/ambience/indust/indust.fsc"),
    AmbienceDefinition(0xbe12819c, AmbienceCategory.MECHANICAL, "SciBleeps",
                       "sounddata/ambience/scibleeps/scibleeps.fsc"),
    AmbienceDefinition(0x1e1281ac, AmbienceCategory.MECHANICAL, "Sirens",
                       "sounddata/ambience/siren/siren.fsc"),
    AmbienceDefinition(0xa9b9652a, AmbienceCategory.MECHANICAL, "SmallMachines",
                       "sounddata/ambience/smallmachines/smallmachines.fsc"),
    
    # Weather
    AmbienceDefinition(0xfdd887b5, AmbienceCategory.WEATHER, "Thunder",
                       "sounddata/ambience/thunder/thunder.fsc"),
    AmbienceDefinition(0x1e128187, AmbienceCategory.WEATHER, "Breeze",
                       "sounddata/ambience/breeze/breeze.fsc"),
    AmbienceDefinition(0xde12818f, AmbienceCategory.WEATHER, "HowlingWind",
                       "sounddata/ambience/howlingwind/howlingwind.fsc"),
    AmbienceDefinition(0xde19bb31, AmbienceCategory.WEATHER, "RainDrops",
                       "sounddata/ambience/raindrops/raindrops.fsc"),
    
    # People
    AmbienceDefinition(0xde128198, AmbienceCategory.PEOPLE, "Office",
                       "sounddata/ambience/office/office.fsc"),
    AmbienceDefinition(0x3e12819a, AmbienceCategory.PEOPLE, "Restaurant",
                       "sounddata/ambience/restaurant/restaurant.fsc"),
    AmbienceDefinition(0xbe1a033e, AmbienceCategory.PEOPLE, "Magic",
                       "sounddata/ambience/magic/magic.fsc"),
    AmbienceDefinition(0xa9b96536, AmbienceCategory.PEOPLE, "Screams",
                       "sounddata/ambience/screams/screams.fsc"),
    AmbienceDefinition(0xa9b9653c, AmbienceCategory.PEOPLE, "Gym",
                       "sounddata/ambience/gym/gym.fsc"),
    AmbienceDefinition(0xa9b9653e, AmbienceCategory.PEOPLE, "Ghost",
                       "sounddata/ambience/ghost/ghost.fsc"),
    
    # Loops
    AmbienceDefinition(0x9e0bc19a, AmbienceCategory.LOOPS, "BrookLoop",
                       "sounddata/ambience/loops/brook_lp.xa", is_loop=True),
    AmbienceDefinition(0xfe0bc1a1, AmbienceCategory.LOOPS, "CrowdLoop",
                       "sounddata/ambience/loops/crowd_lp.xa", is_loop=True),
    AmbienceDefinition(0x1e0bc1a3, AmbienceCategory.LOOPS, "HeartbeatLoop",
                       "sounddata/ambience/loops/heartbeat_lp.xa", is_loop=True),
    AmbienceDefinition(0x5e0bc1a4, AmbienceCategory.LOOPS, "IndoorLoop",
                       "sounddata/ambience/loops/indoor_lp.xa", is_loop=True),
    AmbienceDefinition(0x5e0bc1a6, AmbienceCategory.LOOPS, "InsectLoop",
                       "sounddata/ambience/loops/insect_lp.xa", is_loop=True),
    AmbienceDefinition(0xbe0bc1a9, AmbienceCategory.LOOPS, "OceanLoop",
                       "sounddata/ambience/loops/ocean_lp.xa", is_loop=True),
    AmbienceDefinition(0x1e0bc1ab, AmbienceCategory.LOOPS, "OutdoorLoop",
                       "sounddata/ambience/loops/outdoor_lp.xa", is_loop=True),
    AmbienceDefinition(0xde0bc1ad, AmbienceCategory.LOOPS, "RainLoop",
                       "sounddata/ambience/loops/rain_lp.xa", is_loop=True),
    AmbienceDefinition(0x3e0bc2af, AmbienceCategory.LOOPS, "ScifiLoop",
                       "sounddata/ambience/loops/scifi_lp.xa", is_loop=True),
    AmbienceDefinition(0x1e0bc2b2, AmbienceCategory.LOOPS, "StormLoop",
                       "sounddata/ambience/loops/storm_lp.xa", is_loop=True),
    AmbienceDefinition(0x3e0bc2b4, AmbienceCategory.LOOPS, "TrafficLoop",
                       "sounddata/ambience/loops/traffic_lp.xa", is_loop=True),
    AmbienceDefinition(0x1e0bc2b5, AmbienceCategory.LOOPS, "WindLoop",
                       "sounddata/ambience/loops/wind_lp.xa", is_loop=True),
]

# Build lookup by GUID
AMBIENCE_BY_GUID: Dict[int, AmbienceDefinition] = {
    amb.guid: amb for amb in AMBIENCE_DEFINITIONS
}


def get_ambience_by_guid(guid: int) -> Optional[AmbienceDefinition]:
    """Look up ambient sound by object GUID."""
    return AMBIENCE_BY_GUID.get(guid)


def list_ambiences_by_category(category: AmbienceCategory) -> List[AmbienceDefinition]:
    """Get all ambient sounds in a category."""
    return [amb for amb in AMBIENCE_DEFINITIONS if amb.category == category]


# ═══════════════════════════════════════════════════════════════════════════════
# LOT IFF STRUCTURE (from FreeSO VMTS1Activator and docs)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LotDimensions:
    """Lot size information."""
    width: int = 64    # Default TS1 lot size
    height: int = 64   # Default TS1 lot size
    
    @property
    def tile_count(self) -> int:
        return self.width * self.height


@dataclass
class SimulationInfo:
    """SIMI chunk data - lot metadata and global state.
    
    The SIMI chunk contains:
    - GlobalData[23]: Lot size
    - GlobalData[35]: Lot type
    - GlobalData[0]: Current hour
    - GlobalData[1]: Day of month
    - GlobalData[5]: Minutes
    - GlobalData[7]: Month
    - GlobalData[8]: Year
    - Architecture value, objects value, version
    """
    lot_size: int = 64
    lot_type: int = 0
    hour: int = 8
    day: int = 1
    minutes: int = 0
    month: int = 1
    year: int = 1997
    architecture_value: int = 0
    objects_value: int = 0
    version: int = 0x3E
    global_data: List[int] = field(default_factory=list)


@dataclass 
class HouseInfo:
    """HOUS chunk data - house settings."""
    camera_direction: int = 0  # 0-3, affects road flip
    roof_name: str = ""        # Roof texture name
    
    @property
    def flip_road(self) -> bool:
        """Whether the road should be flipped based on camera direction."""
        return (self.camera_direction & 1) > 0


@dataclass
class ObjectPlacement:
    """An object placed on the lot."""
    object_id: int           # Instance ID
    objt_index: int          # Index into OBJT
    guid: int = 0            # Object GUID (resolved from OBJT)
    name: str = ""           # Object name (resolved from OBJT)
    x: int = 0               # X tile position
    y: int = 0               # Y tile position
    floor: int = 0           # Floor level (0 or 1)
    direction: int = 0       # Rotation


@dataclass
class LotAnalysis:
    """Complete analysis of a lot IFF file."""
    filename: str
    house_number: Optional[int] = None
    terrain_type: TerrainType = TerrainType.GRASS
    dimensions: LotDimensions = field(default_factory=LotDimensions)
    simi: Optional[SimulationInfo] = None
    hous: Optional[HouseInfo] = None
    objects: List[ObjectPlacement] = field(default_factory=list)
    ambience_objects: List[Tuple[ObjectPlacement, AmbienceDefinition]] = field(default_factory=list)
    chunk_types_found: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def object_count(self) -> int:
        return len(self.objects)
    
    @property
    def ambience_count(self) -> int:
        return len(self.ambience_objects)
    
    def format_summary(self) -> str:
        """Format a human-readable summary."""
        lines = [
            f"╔══════════════════════════════════════════════════════════════╗",
            f"║ LOT ANALYSIS: {Path(self.filename).name:^47} ║",
            f"╠══════════════════════════════════════════════════════════════╣",
            f"║ House Number: {self.house_number or 'Unknown':>47} ║",
            f"║ Terrain Type: {self.terrain_type.value:>47} ║",
            f"║ Dimensions:   {self.dimensions.width}x{self.dimensions.height} ({self.dimensions.tile_count} tiles){' ' * (47 - len(f'{self.dimensions.width}x{self.dimensions.height} ({self.dimensions.tile_count} tiles)'))}║",
            f"║ Objects:      {self.object_count:>47} ║",
            f"║ Ambience:     {self.ambience_count:>47} ║",
        ]
        
        if self.simi:
            time_str = f"{self.simi.hour:02d}:{self.simi.minutes:02d}"
            date_str = f"{self.simi.month}/{self.simi.day}/{self.simi.year}"
            lines.append(f"║ Game Time:    {time_str} on {date_str}{' ' * (47 - len(f'{time_str} on {date_str}'))}║")
            lines.append(f"║ Value:        §{self.simi.architecture_value + self.simi.objects_value:,}{' ' * (47 - len(f'§{self.simi.architecture_value + self.simi.objects_value:,}'))}║")
        
        if self.chunk_types_found:
            chunks = ", ".join(sorted(self.chunk_types_found)[:10])
            lines.append(f"╟──────────────────────────────────────────────────────────────╢")
            lines.append(f"║ Chunks: {chunks[:53]:53} ║")
        
        if self.ambience_objects:
            lines.append(f"╟──────────────────────────────────────────────────────────────╢")
            lines.append(f"║ AMBIENCE SOURCES:                                            ║")
            for obj, amb in self.ambience_objects[:5]:
                lines.append(f"║   • {amb.name} ({amb.category.name}){' ' * (56 - len(f'• {amb.name} ({amb.category.name})'))}║")
            if len(self.ambience_objects) > 5:
                lines.append(f"║   ... and {len(self.ambience_objects) - 5} more{' ' * (51 - len(f'... and {len(self.ambience_objects) - 5} more'))}║")
        
        if self.warnings:
            lines.append(f"╟──────────────────────────────────────────────────────────────╢")
            lines.append(f"║ WARNINGS:                                                    ║")
            for warn in self.warnings[:3]:
                lines.append(f"║   ⚠ {warn[:55]:55} ║")
        
        lines.append(f"╚══════════════════════════════════════════════════════════════╝")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# LOT ARRY CHUNKS (Array data for floors, walls, objects, etc.)
# ═══════════════════════════════════════════════════════════════════════════════

class LotARRYType(Enum):
    """Known ARRY chunk IDs in lot IFFs (from FreeSO)."""
    HEIGHTS = 0         # Terrain heights
    FLOORS_L0 = 1       # Ground floor tiles (8-bit)
    WALLS_L0 = 2        # Ground floor walls (8-bit)
    OBJECTS_L0 = 3      # Ground floor object IDs
    GRASS_STATE = 6     # Grass liveness per tile
    TARGET_GRASS = 7    # Target grass state
    FLAGS = 8           # Tile flags
    POOLS = 9           # Pool tiles
    WATER = 10          # Water tiles
    ADV_FLOORS_L0 = 11  # Ground floor tiles (16-bit, modern TS1)
    ADV_WALLS_L0 = 12   # Ground floor walls (16-bit, modern TS1)
    
    FLOORS_L1 = 101     # Second floor tiles
    WALLS_L1 = 102      # Second floor walls
    OBJECTS_L1 = 103    # Second floor object IDs
    FLAGS_L1 = 108      # Second floor flags
    ADV_FLOORS_L1 = 111 # Second floor tiles (16-bit)
    ADV_WALLS_L1 = 112  # Second floor walls (16-bit)


@dataclass
class ARRYChunkInfo:
    """Information about an ARRY chunk."""
    chunk_id: int
    arry_type: Optional[LotARRYType]
    data_size: int
    description: str


def describe_arry_chunk(chunk_id: int, data_size: int) -> ARRYChunkInfo:
    """Describe what an ARRY chunk contains."""
    try:
        arry_type = LotARRYType(chunk_id)
        descriptions = {
            LotARRYType.HEIGHTS: "Terrain height map",
            LotARRYType.FLOORS_L0: "Ground floor tiles (8-bit format)",
            LotARRYType.WALLS_L0: "Ground floor walls (8-bit format)",
            LotARRYType.OBJECTS_L0: "Ground floor object placement IDs",
            LotARRYType.GRASS_STATE: "Grass liveness values (0-127)",
            LotARRYType.TARGET_GRASS: "Target grass state for growth",
            LotARRYType.FLAGS: "Tile flags (buildable area, etc.)",
            LotARRYType.POOLS: "Pool placement (0xFF = none)",
            LotARRYType.WATER: "Water/pond placement",
            LotARRYType.ADV_FLOORS_L0: "Ground floor tiles (16-bit advanced)",
            LotARRYType.ADV_WALLS_L0: "Ground floor walls (16-bit advanced)",
            LotARRYType.FLOORS_L1: "Second floor tiles",
            LotARRYType.WALLS_L1: "Second floor walls",
            LotARRYType.OBJECTS_L1: "Second floor object placement IDs",
            LotARRYType.FLAGS_L1: "Second floor tile flags",
            LotARRYType.ADV_FLOORS_L1: "Second floor tiles (16-bit advanced)",
            LotARRYType.ADV_WALLS_L1: "Second floor walls (16-bit advanced)",
        }
        return ARRYChunkInfo(
            chunk_id=chunk_id,
            arry_type=arry_type,
            data_size=data_size,
            description=descriptions.get(arry_type, "Unknown ARRY type")
        )
    except ValueError:
        return ARRYChunkInfo(
            chunk_id=chunk_id,
            arry_type=None,
            data_size=data_size,
            description=f"Unknown ARRY ID {chunk_id}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LOT ANALYZER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class LotIFFAnalyzer:
    """Analyzes lot IFF files for terrain, ambience, and structure."""
    
    def __init__(self):
        self.iff_file = None
        self._objt_entries: List[Dict[str, Any]] = []
        
    def analyze(self, iff_file) -> LotAnalysis:
        """Analyze a loaded IFF file as a lot.
        
        Args:
            iff_file: An IffFile instance with loaded chunks
            
        Returns:
            LotAnalysis with complete lot information
        """
        self.iff_file = iff_file
        
        analysis = LotAnalysis(filename=iff_file.filename)
        
        # Extract house number from filename
        analysis.house_number = extract_house_number(iff_file.filename)
        if analysis.house_number is not None:
            analysis.terrain_type = get_terrain_type(analysis.house_number)
        
        # Collect chunk types
        for chunk in iff_file.chunks:
            analysis.chunk_types_found.add(chunk.type_id)
        
        # Parse SIMI
        simi = iff_file.get_chunk('SIMI', 1)
        if simi:
            analysis.simi = self._parse_simi(simi)
            analysis.dimensions.width = analysis.simi.lot_size
            analysis.dimensions.height = analysis.simi.lot_size
        
        # Parse HOUS
        hous = iff_file.get_chunk('HOUS', 0)
        if hous:
            analysis.hous = self._parse_hous(hous)
        
        # Parse OBJT (object types)
        objt = iff_file.get_chunk('OBJT', 0)
        if objt:
            self._objt_entries = self._parse_objt(objt)
        
        # Parse OBJM (object map)
        objm = iff_file.get_chunk('OBJM', 1)
        if objm and self._objt_entries:
            analysis.objects = self._parse_objm(objm)
            
            # Identify ambience objects
            for obj in analysis.objects:
                amb = get_ambience_by_guid(obj.guid)
                if amb:
                    analysis.ambience_objects.append((obj, amb))
        
        # Check for expected lot chunks
        expected_chunks = {'SIMI', 'HOUS', 'OBJT', 'OBJM', 'ARRY'}
        missing = expected_chunks - analysis.chunk_types_found
        if missing:
            analysis.warnings.append(f"Missing expected lot chunks: {missing}")
        
        return analysis
    
    def _parse_simi(self, chunk) -> SimulationInfo:
        """Parse SIMI chunk into SimulationInfo."""
        simi = SimulationInfo()
        
        try:
            data = chunk.get_data()
            if hasattr(chunk, 'global_data'):
                simi.global_data = list(chunk.global_data)
                if len(simi.global_data) > 23:
                    simi.lot_size = simi.global_data[23]
                if len(simi.global_data) > 35:
                    simi.lot_type = simi.global_data[35]
                if len(simi.global_data) > 0:
                    simi.hour = simi.global_data[0]
                if len(simi.global_data) > 1:
                    simi.day = simi.global_data[1]
                if len(simi.global_data) > 5:
                    simi.minutes = simi.global_data[5]
                if len(simi.global_data) > 7:
                    simi.month = simi.global_data[7]
                if len(simi.global_data) > 8:
                    simi.year = simi.global_data[8]
            
            if hasattr(chunk, 'architecture_value'):
                simi.architecture_value = chunk.architecture_value
            if hasattr(chunk, 'objects_value'):
                simi.objects_value = chunk.objects_value
            if hasattr(chunk, 'version'):
                simi.version = chunk.version
        except Exception:
            pass
            
        return simi
    
    def _parse_hous(self, chunk) -> HouseInfo:
        """Parse HOUS chunk into HouseInfo."""
        hous = HouseInfo()
        
        try:
            if hasattr(chunk, 'camera_dir'):
                hous.camera_direction = chunk.camera_dir
            if hasattr(chunk, 'roof_name'):
                hous.roof_name = chunk.roof_name
        except Exception:
            pass
            
        return hous
    
    def _parse_objt(self, chunk) -> List[Dict[str, Any]]:
        """Parse OBJT chunk into list of object type entries."""
        entries = []
        
        try:
            if hasattr(chunk, 'entries'):
                for entry in chunk.entries:
                    entries.append({
                        'guid': entry.guid if hasattr(entry, 'guid') else 0,
                        'name': entry.name if hasattr(entry, 'name') else "",
                    })
        except Exception:
            pass
            
        return entries
    
    def _parse_objm(self, chunk) -> List[ObjectPlacement]:
        """Parse OBJM chunk into list of placed objects."""
        objects = []
        
        try:
            if hasattr(chunk, 'object_data'):
                for obj_id, obj_data in chunk.object_data.items():
                    obj = ObjectPlacement(
                        object_id=obj_id,
                        objt_index=obj_data.get('type_id', 0) if isinstance(obj_data, dict) else 0
                    )
                    
                    # Resolve GUID and name from OBJT
                    if obj.objt_index > 0 and obj.objt_index <= len(self._objt_entries):
                        entry = self._objt_entries[obj.objt_index - 1]
                        obj.guid = entry['guid']
                        obj.name = entry['name']
                    
                    if isinstance(obj_data, dict):
                        obj.x = obj_data.get('x', 0)
                        obj.y = obj_data.get('y', 0)
                        obj.floor = obj_data.get('floor', 0)
                        obj.direction = obj_data.get('direction', 0)
                    
                    objects.append(obj)
        except Exception:
            pass
            
        return objects


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_lot_file(filepath: str) -> LotAnalysis:
    """Quick analysis of a lot IFF file.
    
    Args:
        filepath: Path to the lot IFF file
        
    Returns:
        LotAnalysis with lot information
        
    Note: Requires formats.iff.iff_file to be available
    """
    from formats.iff.iff_file import IffFile
    
    iff = IffFile.load(filepath)
    analyzer = LotIFFAnalyzer()
    return analyzer.analyze(iff)


def scan_lot_folder(folder_path: str) -> List[LotAnalysis]:
    """Scan a folder of lot IFF files.
    
    Args:
        folder_path: Path to folder containing House*.iff or User*.iff files
        
    Returns:
        List of LotAnalysis for each lot found
    """
    from formats.iff.iff_file import IffFile
    
    folder = Path(folder_path)
    results = []
    
    for pattern in ['House*.iff', 'User*.iff']:
        for lot_file in folder.glob(pattern):
            try:
                analysis = analyze_lot_file(str(lot_file))
                results.append(analysis)
            except Exception as e:
                results.append(LotAnalysis(
                    filename=str(lot_file),
                    warnings=[f"Failed to analyze: {e}"]
                ))
    
    return sorted(results, key=lambda a: a.house_number or 9999)


def find_ambience_in_game(game_install: str) -> Dict[str, List[str]]:
    """Scan game installation for ambience sound files.
    
    Args:
        game_install: Path to game installation root
        
    Returns:
        Dict mapping category to list of found sound files
    """
    game_path = Path(game_install)
    found = {}
    
    for amb in AMBIENCE_DEFINITIONS:
        category = amb.category.name
        if category not in found:
            found[category] = []
        
        # Try multiple possible locations
        possible_paths = [
            game_path / amb.sound_path,
            game_path / "GameData" / amb.sound_path,
            game_path / "ExpansionShared" / amb.sound_path,
        ]
        
        for path in possible_paths:
            if path.exists():
                found[category].append(str(path))
                break
    
    return found


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Terrain
    'TerrainType',
    'HOUSE_NUMBER_TO_TERRAIN',
    'get_terrain_type',
    'extract_house_number',
    
    # Ambience
    'AmbienceCategory',
    'AmbienceDefinition',
    'AMBIENCE_DEFINITIONS',
    'AMBIENCE_BY_GUID',
    'get_ambience_by_guid',
    'list_ambiences_by_category',
    
    # Lot structure
    'LotDimensions',
    'SimulationInfo',
    'HouseInfo',
    'ObjectPlacement',
    'LotAnalysis',
    'LotARRYType',
    'ARRYChunkInfo',
    'describe_arry_chunk',
    
    # Analyzer
    'LotIFFAnalyzer',
    'analyze_lot_file',
    'scan_lot_folder',
    'find_ambience_in_game',
]
