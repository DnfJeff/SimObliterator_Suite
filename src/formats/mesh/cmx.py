"""
CMX Parser - Character Manifest for The Sims 1

Parses .cmx text files that define character appearances, skeletons, and animations.
Based on VitaMoo's parser.ts which handles both text CMX and binary BCF formats.

CMX Text Format (one value per line):
  version 300
  skeleton_count
    For each skeleton: name, bone_count, bones...
  suit_count  
    For each suit: name, type, hasProps, [props], skin_count, skins...
  skill_count
    For each skill: name, animation_file, duration, distance, isMoving, motions...

Skeletons are usually defined in separate skeleton files (like adult-skeleton.cmx),
while appearance/suit CMX files typically have skeleton_count=0.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Tuple


# ============================================================
# Data structures matching VitaMoo's types.ts
# ============================================================

@dataclass
class Vec3:
    """3D vector for positions/translations."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Quat:
    """Quaternion for rotations (w, x, y, z)."""
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class BoneData:
    """Bone in a skeleton hierarchy."""
    name: str = ""
    parent_name: str = ""
    position: Vec3 = field(default_factory=Vec3)
    rotation: Quat = field(default_factory=Quat)
    can_translate: bool = False
    can_rotate: bool = False
    can_blend: bool = False
    can_wiggle: bool = False
    wiggle_power: float = 0.0
    props: Dict[str, str] = field(default_factory=dict)


@dataclass
class SkeletonData:
    """Complete skeleton with bone hierarchy."""
    name: str = ""
    bones: List[BoneData] = field(default_factory=list)


@dataclass
class SkinData:
    """Mesh binding within a suit."""
    name: str = ""
    bone_name: str = ""
    flags: int = 0
    mesh_name: str = ""
    props: Dict[str, str] = field(default_factory=dict)


@dataclass
class SuitData:
    """Character appearance/outfit with mesh bindings."""
    name: str = ""
    type: int = 0
    skins: List[SkinData] = field(default_factory=list)
    props: Dict[str, str] = field(default_factory=dict)


@dataclass
class MotionData:
    """Animation data for a single bone."""
    bone_name: str = ""
    frames: int = 0
    duration: float = 0.0
    has_translation: bool = False
    has_rotation: bool = False
    translations_offset: int = 0
    rotations_offset: int = 0
    props: Dict[str, str] = field(default_factory=dict)
    time_props: Dict[int, Dict[str, str]] = field(default_factory=dict)


@dataclass
class SkillData:
    """Animation/skill with motions for each bone."""
    name: str = ""
    animation_file_name: str = ""
    duration: float = 0.0
    distance: float = 0.0
    is_moving: bool = False
    num_translations: int = 0
    num_rotations: int = 0
    motions: List[MotionData] = field(default_factory=list)
    translations: List[Vec3] = field(default_factory=list)
    rotations: List[Quat] = field(default_factory=list)


@dataclass
class CMXFile:
    """Complete CMX file with skeletons, suits, and skills."""
    version: int = 300
    filename: str = ""
    skeletons: List[SkeletonData] = field(default_factory=list)
    suits: List[SuitData] = field(default_factory=list)
    skills: List[SkillData] = field(default_factory=list)
    
    def get_all_meshes(self) -> List[str]:
        """Get list of all referenced mesh names."""
        meshes = []
        for suit in self.suits:
            for skin in suit.skins:
                if skin.mesh_name and skin.mesh_name not in meshes:
                    meshes.append(skin.mesh_name)
        return meshes
    
    def get_skeleton(self, name: str = None) -> Optional[SkeletonData]:
        """Get skeleton by name, or first if no name given."""
        if not self.skeletons:
            return None
        if name:
            for s in self.skeletons:
                if s.name == name:
                    return s
        return self.skeletons[0]


# Legacy aliases for backwards compatibility
CMXBinding = SkinData
CMXAppearance = SuitData


class CMXReader:
    """
    Parser for CMX (Character Manifest) text files.
    
    Based on VitaMoo's parseCMX function - reads skeletons, suits, and skills.
    
    Usage:
        reader = CMXReader()
        cmx = reader.read_file("character.cmx")
        
        for skeleton in cmx.skeletons:
            print(f"Skeleton: {skeleton.name} ({len(skeleton.bones)} bones)")
        for suit in cmx.suits:
            print(f"Suit: {suit.name} ({len(suit.skins)} skins)")
        for skill in cmx.skills:
            print(f"Skill: {skill.name} ({len(skill.motions)} motions)")
    """
    
    def __init__(self):
        self.lines: List[str] = []
        self.line_idx: int = 0
    
    def read_file(self, filepath: str) -> Optional[CMXFile]:
        """Read and parse a CMX file."""
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                self.lines = [line.strip() for line in f.readlines()]
            self.line_idx = 0
            cmx = self._parse()
            cmx.filename = filepath
            return cmx
        except Exception as e:
            print(f"Error parsing CMX {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def read_string(self, text: str) -> Optional[CMXFile]:
        """Parse CMX from string content."""
        try:
            self.lines = [line.strip() for line in text.split('\n')]
            self.line_idx = 0
            return self._parse()
        except Exception as e:
            print(f"Error parsing CMX: {e}")
            return None
    
    def _next_line(self) -> str:
        """Get next non-empty, non-comment line."""
        while self.line_idx < len(self.lines):
            line = self.lines[self.line_idx]
            self.line_idx += 1
            # Skip empty lines and comments
            if line and not line.startswith('//'):
                return line
        return ""
    
    def _read_int(self) -> int:
        """Read next line as integer."""
        return int(self._next_line())
    
    def _read_float(self) -> float:
        """Read next line as float."""
        return float(self._next_line())
    
    def _read_bool(self) -> bool:
        """Read next line as boolean (0/1)."""
        return self._read_int() != 0
    
    def _read_string(self) -> str:
        """Read next line as string."""
        return self._next_line()
    
    def _read_vec3(self) -> Vec3:
        """Read three lines as Vec3."""
        return Vec3(
            self._read_float(),
            self._read_float(),
            self._read_float()
        )
    
    def _read_quat(self) -> Quat:
        """Read four lines as Quat (x, y, z, w order in file)."""
        x = self._read_float()
        y = self._read_float()
        z = self._read_float()
        w = self._read_float()
        return Quat(w, x, y, z)
    
    def _read_props(self) -> Dict[str, str]:
        """Read property bag (count, then key-value pairs)."""
        count = self._read_int()
        props = {}
        for _ in range(count):
            key = self._read_string()
            value = self._read_string()
            props[key] = value
        return props
    
    def _read_bone(self) -> BoneData:
        """Read bone data."""
        bone = BoneData()
        bone.name = self._read_string()
        bone.parent_name = self._read_string()
        has_props = self._read_bool()
        if has_props:
            bone.props = self._read_props()
        bone.position = self._read_vec3()
        bone.rotation = self._read_quat()
        bone.can_translate = self._read_bool()
        bone.can_rotate = self._read_bool()
        bone.can_blend = self._read_bool()
        bone.can_wiggle = self._read_bool()
        bone.wiggle_power = self._read_float()
        return bone
    
    def _read_skeleton(self) -> SkeletonData:
        """Read skeleton with bones."""
        skeleton = SkeletonData()
        skeleton.name = self._read_string()
        bone_count = self._read_int()
        for _ in range(bone_count):
            skeleton.bones.append(self._read_bone())
        return skeleton
    
    def _read_skin(self) -> SkinData:
        """Read skin/mesh binding."""
        skin = SkinData()
        skin.name = self._read_string()
        skin.bone_name = self._read_string()
        skin.flags = self._read_int()
        skin.mesh_name = self._read_string()
        has_props = self._read_bool()
        if has_props:
            skin.props = self._read_props()
        return skin
    
    def _read_suit(self) -> SuitData:
        """Read suit/appearance."""
        suit = SuitData()
        suit.name = self._read_string()
        suit.type = self._read_int()
        has_props = self._read_bool()
        if has_props:
            suit.props = self._read_props()
        skin_count = self._read_int()
        for _ in range(skin_count):
            suit.skins.append(self._read_skin())
        return suit
    
    def _read_motion(self) -> MotionData:
        """Read motion/animation track for a bone."""
        motion = MotionData()
        motion.bone_name = self._read_string()
        motion.frames = self._read_int()
        motion.duration = self._read_float()
        motion.has_translation = self._read_bool()
        motion.has_rotation = self._read_bool()
        motion.translations_offset = self._read_int()
        motion.rotations_offset = self._read_int()
        has_props = self._read_bool()
        if has_props:
            motion.props = self._read_props()
        has_time_props = self._read_bool()
        if has_time_props:
            tp_count = self._read_int()
            for _ in range(tp_count):
                time_key = self._read_int()
                tp_props = self._read_props()
                motion.time_props[time_key] = tp_props
        return motion
    
    def _read_skill(self) -> SkillData:
        """Read skill/animation."""
        skill = SkillData()
        skill.name = self._read_string()
        skill.animation_file_name = self._read_string()
        skill.duration = self._read_float()
        skill.distance = self._read_float()
        skill.is_moving = self._read_bool()
        skill.num_translations = self._read_int()
        skill.num_rotations = self._read_int()
        motion_count = self._read_int()
        for _ in range(motion_count):
            skill.motions.append(self._read_motion())
        return skill
    
    def _parse(self) -> CMXFile:
        """Parse CMX content."""
        cmx = CMXFile()
        
        # Version line: "version 300" or just "300"
        version_line = self._next_line()
        if version_line.startswith('version'):
            cmx.version = int(version_line.split()[1])
        else:
            cmx.version = int(version_line)
        
        # Skeletons
        skeleton_count = self._read_int()
        for _ in range(skeleton_count):
            cmx.skeletons.append(self._read_skeleton())
        
        # Suits (appearances)
        suit_count = self._read_int()
        for _ in range(suit_count):
            cmx.suits.append(self._read_suit())
        
        # Skills (animations)
        skill_count = self._read_int()
        for _ in range(skill_count):
            cmx.skills.append(self._read_skill())
        
        return cmx
    
    # Legacy property for backwards compatibility
    @property
    def appearances(self):
        """Legacy accessor - use suits instead."""
        return self.suits


class CharacterAssembler:
    """
    Assembles complete characters from CMX manifests.
    
    Links together:
    - CMX manifest (defines structure)
    - SKN/BMF meshes (geometry)
    - BMP textures
    - BCF skeletons (bone hierarchy)
    """
    
    def __init__(self, search_paths: List[Path] = None):
        """
        Initialize assembler with paths to search for files.
        
        Args:
            search_paths: Directories to search for meshes, textures, etc.
        """
        self.search_paths = search_paths or []
        self._file_cache: Dict[str, Path] = {}
    
    def add_search_path(self, path: Path):
        """Add a directory to search for files."""
        if path not in self.search_paths:
            self.search_paths.append(path)
    
    def find_file(self, name: str, extensions: List[str]) -> Optional[Path]:
        """
        Find a file by name in search paths.
        
        Args:
            name: Base filename (without extension)
            extensions: List of extensions to try (e.g., ['.skn', '.bmf'])
            
        Returns:
            Path to found file, or None
        """
        # Check cache first
        cache_key = f"{name}:{','.join(extensions)}"
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]
        
        # Search in all paths
        for search_path in self.search_paths:
            for ext in extensions:
                # Try exact name
                path = search_path / f"{name}{ext}"
                if path.exists():
                    self._file_cache[cache_key] = path
                    return path
                
                # Try lowercase
                path = search_path / f"{name.lower()}{ext}"
                if path.exists():
                    self._file_cache[cache_key] = path
                    return path
        
        return None
    
    def find_mesh(self, name: str) -> Optional[Path]:
        """Find a mesh file (SKN or BMF)."""
        return self.find_file(name, ['.skn', '.bmf', '.SKN', '.BMF'])
    
    def find_texture(self, name: str) -> Optional[Path]:
        """Find a texture file."""
        return self.find_file(name, ['.bmp', '.tga', '.png', '.BMP', '.TGA', '.PNG'])
    
    def get_character_files(self, cmx: CMXFile) -> Dict[str, Dict]:
        """
        Get all files needed for a character.
        
        Returns:
            Dict with 'meshes' and 'textures' keys, each containing
            {name: path} for found files.
        """
        result = {
            'meshes': {},
            'textures': {},
            'missing_meshes': [],
            'missing_textures': []
        }
        
        for mesh_name in cmx.get_all_meshes():
            path = self.find_mesh(mesh_name)
            if path:
                result['meshes'][mesh_name] = path
            else:
                result['missing_meshes'].append(mesh_name)
        
        return result


# Test
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        reader = CMXReader()
        cmx = reader.read_file(sys.argv[1])
        if cmx:
            print(f"CMX Version: {cmx.version}")
            print(f"Skeletons: {len(cmx.skeletons)}")
            for skel in cmx.skeletons:
                print(f"  {skel.name}: {len(skel.bones)} bones")
                for bone in skel.bones[:3]:  # Show first 3
                    print(f"    {bone.name} (parent: {bone.parent_name})")
                if len(skel.bones) > 3:
                    print(f"    ... and {len(skel.bones) - 3} more")
            
            print(f"\nSuits: {len(cmx.suits)}")
            for suit in cmx.suits:
                print(f"  {suit.name} (type {suit.type}): {len(suit.skins)} skins")
                for skin in suit.skins:
                    print(f"    {skin.bone_name} -> {skin.mesh_name}")
            
            print(f"\nSkills: {len(cmx.skills)}")
            for skill in cmx.skills:
                print(f"  {skill.name}: {skill.duration}ms, {len(skill.motions)} motions")
            
            print(f"\nAll meshes: {cmx.get_all_meshes()}")
