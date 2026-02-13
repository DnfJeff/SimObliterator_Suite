"""
BCF Parser - Binary Character Format for The Sims 1

Parses .cmx.bcf files containing skeletons, suits, and animations.
Based on FreeSO's BCFCodec.cs and TheSimsOpenTechDoc Part IV.

BCF Structure:
  - Skeleton count + Skeletons[]
  - Suit/Appearance count + Appearances[]  
  - Animation/Skill count + Animations[]

Each BCF typically contains ONE non-zero section.
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import math


@dataclass
class Quaternion:
    """Rotation quaternion (W, X, Y, Z)."""
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def normalize(self) -> 'Quaternion':
        """Return normalized quaternion."""
        mag = math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        if mag < 0.0001:
            return Quaternion(1, 0, 0, 0)
        return Quaternion(self.w/mag, self.x/mag, self.y/mag, self.z/mag)
    
    def to_euler(self) -> Tuple[float, float, float]:
        """Convert to Euler angles (radians): pitch, yaw, roll."""
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (self.w * self.x + self.y * self.z)
        cosr_cosp = 1 - 2 * (self.x * self.x + self.y * self.y)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2 * (self.w * self.y - self.z * self.x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)
        else:
            pitch = math.asin(sinp)
        
        # Yaw (z-axis rotation)
        siny_cosp = 2 * (self.w * self.z + self.x * self.y)
        cosy_cosp = 1 - 2 * (self.y * self.y + self.z * self.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        
        return (pitch, yaw, roll)


@dataclass
class Vector3:
    """3D vector/position."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)


@dataclass
class Bone:
    """Skeleton bone with transform."""
    name: str = ""
    parent_name: str = ""
    translation: Vector3 = field(default_factory=Vector3)
    rotation: Quaternion = field(default_factory=Quaternion)
    can_translate: bool = False
    can_rotate: bool = False
    can_blend: bool = False
    wiggle_value: float = 0.0
    wiggle_power: float = 0.0
    properties: Dict[str, str] = field(default_factory=dict)
    
    # Computed at runtime
    parent: Optional['Bone'] = None
    children: List['Bone'] = field(default_factory=list)


@dataclass
class Skeleton:
    """Complete bone hierarchy."""
    name: str = ""
    bones: List[Bone] = field(default_factory=list)
    bone_by_name: Dict[str, Bone] = field(default_factory=dict)
    root_bone: Optional[Bone] = None
    
    def build_hierarchy(self):
        """Link parent/child relationships."""
        self.bone_by_name = {b.name: b for b in self.bones}
        
        for bone in self.bones:
            if bone.parent_name and bone.parent_name in self.bone_by_name:
                bone.parent = self.bone_by_name[bone.parent_name]
                bone.parent.children.append(bone)
            else:
                self.root_bone = bone


@dataclass
class Binding:
    """Maps a mesh to a bone (skin in VitaMoo terminology)."""
    name: str = ""  # Skin name
    bone_name: str = ""
    flags: int = 0  # Censor flags etc
    mesh_name: str = ""
    texture_name: str = ""
    props: Dict[str, str] = field(default_factory=dict)


@dataclass
class Appearance:
    """Character appearance (suit) with mesh bindings."""
    name: str = ""
    appearance_type: int = 0  # 0=light, 1=medium, 2=dark
    bindings: List[Binding] = field(default_factory=list)


@dataclass
class AnimationMotion:
    """Per-bone animation channel."""
    bone_name: str = ""
    frame_count: int = 0
    duration: float = 0.0
    has_translation: bool = False
    has_rotation: bool = False
    first_translation_index: int = 0
    first_rotation_index: int = 0
    properties: Dict[str, str] = field(default_factory=dict)
    time_properties: List[Tuple[float, str, str]] = field(default_factory=list)


@dataclass
class Animation:
    """Complete animation with all bone motions."""
    name: str = ""
    duration: float = 0.0  # milliseconds
    distance: float = 0.0
    is_moving: bool = False
    
    # Frame data (populated from CFP)
    translations: List[Vector3] = field(default_factory=list)
    rotations: List[Quaternion] = field(default_factory=list)
    
    motions: List[AnimationMotion] = field(default_factory=list)


@dataclass
class BCF:
    """Complete BCF file contents."""
    skeletons: List[Skeleton] = field(default_factory=list)
    appearances: List[Appearance] = field(default_factory=list)
    animations: List[Animation] = field(default_factory=list)
    
    def get_skeleton(self, name: str = None) -> Optional[Skeleton]:
        """Get skeleton by name, or first if no name given."""
        if not self.skeletons:
            return None
        if name:
            for s in self.skeletons:
                if s.name == name:
                    return s
        return self.skeletons[0]


class BCFReader:
    """
    Parser for BCF (Binary Character Format) files.
    
    Usage:
        reader = BCFReader()
        bcf = reader.read_file("skeleton.cmx.bcf")
        skeleton = bcf.get_skeleton()
    """
    
    def __init__(self):
        self.pos = 0
        self.data = b""
    
    def read_file(self, filepath: str) -> Optional[BCF]:
        """Read BCF from file."""
        with open(filepath, 'rb') as f:
            return self.read_bytes(f.read())
    
    def read_bytes(self, data: bytes) -> Optional[BCF]:
        """Read BCF from byte buffer."""
        self.data = data
        self.pos = 0
        
        try:
            return self._parse()
        except Exception as e:
            print(f"Error parsing BCF: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse(self) -> BCF:
        """Parse complete BCF structure."""
        bcf = BCF()
        
        # Skeletons
        skeleton_count = self._read_int32()
        for _ in range(skeleton_count):
            skel = self._read_skeleton()
            skel.build_hierarchy()
            bcf.skeletons.append(skel)
        
        # Appearances
        appearance_count = self._read_int32()
        for _ in range(appearance_count):
            app = self._read_appearance()
            bcf.appearances.append(app)
        
        # Animations
        animation_count = self._read_int32()
        for _ in range(animation_count):
            anim = self._read_animation_bcf()
            bcf.animations.append(anim)
        
        return bcf
    
    def _read_skeleton(self) -> Skeleton:
        """Read skeleton structure.
        
        Per TheSimsOpenTechDoc Part IV:
        - Name: pascal string
        - Bone count: 4 bytes (Int32)
        - Bones: repeated bone data
        """
        skel = Skeleton()
        skel.name = self._read_pascal_string()
        
        # TS1 uses Int32 for bone count (not Int16 like TSO/FreeSO)
        bone_count = self._read_int32()
        for _ in range(bone_count):
            bone = self._read_bone()
            if bone is not None:  # Skip empty bones (BCF markers)
                skel.bones.append(bone)
        
        return skel
    
    def _read_bone(self) -> Bone:
        """Read bone data in BCF binary format.
        
        BCF format per VitaMoo (matching text CMX but binary primitives):
        - name: string
        - parent_name: string
        - hasProps: bool (int32, 0 or 1)
        - if hasProps: property count, then key-value pairs
        - position: vec3 (3 floats)
        - rotation: quat (4 floats, x,y,z,w order in file)
        - canTranslate, canRotate, canBlend, canWiggle: bool (int32 each)
        - wigglePower: float
        
        Note: Coordinates are stored RAW - transforms applied in CFP, not here!
        """
        bone = Bone()
        bone.name = self._read_pascal_string()
        bone.parent_name = self._read_pascal_string()
        
        # Skip empty bones (BCF marker) - but parent was already read
        if bone.name == "":
            return None
        
        # hasProps boolean MUST be read (VitaMoo matches this)
        has_props = self._read_int32() != 0
        if has_props:
            # Properties: count, then key-value pairs
            prop_count = self._read_int32()
            for _ in range(prop_count):
                key = self._read_pascal_string()
                val = self._read_pascal_string()
                bone.properties[key] = val
        
        # Transform - read RAW values (transforms happen in CFP, not here)
        bone.translation = Vector3(
            self._read_float(),
            self._read_float(),
            self._read_float()
        )
        
        # Quaternion (stored as x, y, z, w in file, we store as w, x, y, z)
        qx = self._read_float()
        qy = self._read_float()
        qz = self._read_float()
        qw = self._read_float()
        bone.rotation = Quaternion(qw, qx, qy, qz)
        
        bone.can_translate = bool(self._read_int32())
        bone.can_rotate = bool(self._read_int32())
        bone.can_blend = bool(self._read_int32())
        bone.wiggle_value = self._read_float()
        bone.wiggle_power = self._read_float()
        
        return bone
    
    def _read_appearance(self) -> Appearance:
        """Read appearance/suit data (matches VitaMoo's readSuit).
        
        Structure per VitaMoo:
        - name: string
        - type: int32
        - hasProps: bool (int32)
        - if hasProps: properties
        - skinCount: int32
        - skins[]: each with name, boneName, flags, meshName, hasProps, [props]
        """
        app = Appearance()
        app.name = self._read_pascal_string()
        app.appearance_type = self._read_int32()
        
        # hasProps boolean
        has_props = self._read_int32() != 0
        if has_props:
            prop_count = self._read_int32()
            for _ in range(prop_count):
                key = self._read_pascal_string()
                val = self._read_pascal_string()
                # Store props if needed
        
        # Skins (bindings)
        skin_count = self._read_int32()
        for _ in range(skin_count):
            binding = Binding()
            binding.name = self._read_pascal_string()  # Skin name
            binding.bone_name = self._read_pascal_string()
            binding.flags = self._read_int32()
            binding.mesh_name = self._read_pascal_string()
            
            # Skin hasProps
            skin_has_props = self._read_int32() != 0
            if skin_has_props:
                prop_count = self._read_int32()
                for _ in range(prop_count):
                    key = self._read_pascal_string()
                    val = self._read_pascal_string()
            
            app.bindings.append(binding)
        
        return app
    
    def _read_animation_bcf(self) -> Animation:
        """Read animation from BCF (header only, data in CFP)."""
        anim = Animation()
        anim.name = self._read_pascal_string()
        _xskill = self._read_pascal_string()  # X-skill reference
        
        anim.duration = self._read_float()
        anim.distance = self._read_float()
        anim.is_moving = bool(self._read_int32())
        
        _translation_count = self._read_uint32()
        # Translations stored in CFP
        
        _rotation_count = self._read_uint32()
        # Rotations stored in CFP
        
        motion_count = self._read_uint32()
        for _ in range(motion_count):
            motion = self._read_motion_bcf()
            anim.motions.append(motion)
        
        return anim
    
    def _read_motion_bcf(self) -> AnimationMotion:
        """Read animation motion from BCF (matches VitaMoo's readMotion)."""
        motion = AnimationMotion()
        motion.bone_name = self._read_pascal_string()
        motion.frame_count = self._read_int32()
        motion.duration = self._read_float()
        motion.has_translation = bool(self._read_int32())
        motion.has_rotation = bool(self._read_int32())
        motion.first_translation_index = self._read_int32()
        motion.first_rotation_index = self._read_int32()
        
        # Properties with hasProps check
        has_props = self._read_int32() != 0
        if has_props:
            prop_count = self._read_int32()
            for _ in range(prop_count):
                key = self._read_pascal_string()
                val = self._read_pascal_string()
                motion.properties[key] = val
        
        # Time properties with hasTimeProps check
        has_time_props = self._read_int32() != 0
        if has_time_props:
            tp_count = self._read_int32()
            for _ in range(tp_count):
                time_key = self._read_int32()
                # Read props for this time key
                prop_count = self._read_int32()
                for _ in range(prop_count):
                    key = self._read_pascal_string()
                    val = self._read_pascal_string()
                    motion.time_properties.append((float(time_key), key, val))
        
        return motion
    
    # Binary helpers
    def _read_pascal_string(self) -> str:
        """Read length-prefixed string."""
        length = self._read_byte()
        if length == 0:
            return ""
        s = self.data[self.pos:self.pos + length].decode('latin-1', errors='replace')
        self.pos += length
        return s
    
    def _read_byte(self) -> int:
        val = self.data[self.pos]
        self.pos += 1
        return val
    
    def _read_int16(self) -> int:
        val = struct.unpack('<h', self.data[self.pos:self.pos + 2])[0]
        self.pos += 2
        return val
    
    def _read_uint16(self) -> int:
        val = struct.unpack('<H', self.data[self.pos:self.pos + 2])[0]
        self.pos += 2
        return val
    
    def _read_int32(self) -> int:
        val = struct.unpack('<i', self.data[self.pos:self.pos + 4])[0]
        self.pos += 4
        return val
    
    def _read_uint32(self) -> int:
        val = struct.unpack('<I', self.data[self.pos:self.pos + 4])[0]
        self.pos += 4
        return val
    
    def _read_float(self) -> float:
        val = struct.unpack('<f', self.data[self.pos:self.pos + 4])[0]
        self.pos += 4
        return val


# Test
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        reader = BCFReader()
        bcf = reader.read_file(sys.argv[1])
        if bcf:
            print(f"Skeletons: {len(bcf.skeletons)}")
            for skel in bcf.skeletons:
                print(f"  {skel.name}: {len(skel.bones)} bones")
                if skel.root_bone:
                    print(f"    Root: {skel.root_bone.name}")
            
            print(f"Appearances: {len(bcf.appearances)}")
            for app in bcf.appearances:
                print(f"  {app.name}: {len(app.bindings)} bindings")
            
            print(f"Animations: {len(bcf.animations)}")
            for anim in bcf.animations:
                print(f"  {anim.name}: {anim.duration}ms, {len(anim.motions)} motions")
