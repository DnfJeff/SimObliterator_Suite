"""
Skin Registry - Automatic collection and cataloging of Sim skins.

The Sims 1 stores character appearance information in STR# chunk ID 200 (Body Strings):
  Index 0:  Age type ("adult", "child")
  Index 1:  Body mesh + texture ("b002mafat_01,BODY=B002MAFatlgt_slob")
  Index 2:  Head mesh + texture ("c010ma_baldbeard,HEAD-HEAD=C010MAlgt_baldbeard01")
  Index 12: Gender ("male", "female")
  Index 14: Skin tone ("lgt", "med", "drk")
  Index 15: Nude/underwear outfit
  Index 16: Swimwear outfit
  Indices 17-22: Hand meshes (open/closed, left/right)

Format: mesh_name,BODY=texture_name (body) or mesh_name,HEAD-HEAD=texture_name (head)
"""

import struct
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path


@dataclass
class SkinEntry:
    """Single skin/appearance entry."""
    mesh_name: str
    texture_name: str
    skin_type: str  # "body", "head", "hand", "nude", "swim"
    source_file: str = ""
    
    @classmethod
    def parse(cls, entry_str: str, skin_type: str, source_file: str = "") -> Optional['SkinEntry']:
        """Parse mesh,BODY=texture or mesh,HEAD-HEAD=texture format."""
        if not entry_str or ',' not in entry_str:
            return None
        
        parts = entry_str.split(',', 1)
        mesh_name = parts[0].strip()
        texture_name = ""
        
        if len(parts) > 1:
            # Extract texture after = sign
            eq_idx = parts[1].find('=')
            if eq_idx != -1:
                texture_name = parts[1][eq_idx + 1:].strip()
        
        if not mesh_name:
            return None
            
        return cls(
            mesh_name=mesh_name,
            texture_name=texture_name,
            skin_type=skin_type,
            source_file=source_file
        )


@dataclass
class CharacterAppearance:
    """Complete character appearance profile."""
    age: str = ""           # "adult" or "child"
    gender: str = ""        # "male" or "female"
    skin_tone: str = ""     # "lgt", "med", "drk"
    age_number: int = 0     # 27 for adult, 9 for child
    
    body: Optional[SkinEntry] = None
    head: Optional[SkinEntry] = None
    nude: Optional[SkinEntry] = None
    swim: Optional[SkinEntry] = None
    hands: Dict[str, SkinEntry] = field(default_factory=dict)
    
    source_file: str = ""
    character_name: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "age": self.age,
            "gender": self.gender,
            "skin_tone": self.skin_tone,
            "age_number": self.age_number,
            "character_name": self.character_name,
            "source_file": self.source_file,
        }
        if self.body:
            result["body"] = asdict(self.body)
        if self.head:
            result["head"] = asdict(self.head)
        if self.nude:
            result["nude"] = asdict(self.nude)
        if self.swim:
            result["swim"] = asdict(self.swim)
        if self.hands:
            result["hands"] = {k: asdict(v) for k, v in self.hands.items()}
        return result


class STRParser:
    """Parser for STR# string table chunks."""
    
    @staticmethod
    def parse(data: bytes) -> List[str]:
        """Parse STR# chunk data, returns list of strings."""
        if len(data) < 4:
            return []
        
        fmt = struct.unpack('>H', data[0:2])[0]
        strings = []
        
        if fmt == 0xFFFF:
            # Null-terminated format
            count = struct.unpack('<H', data[2:4])[0]
            offset = 4
            for _ in range(count):
                end = data.find(b'\x00', offset)
                if end == -1:
                    break
                strings.append(data[offset:end].decode('latin-1', errors='replace'))
                offset = end + 1
                
        elif fmt == 0xFDFF:
            # Language-coded pairs format
            count = struct.unpack('<H', data[2:4])[0]
            offset = 4
            for _ in range(count):
                if offset >= len(data) - 1:
                    break
                # Skip language byte
                offset += 1
                # String value
                end = data.find(b'\x00', offset)
                if end == -1:
                    break
                strings.append(data[offset:end].decode('latin-1', errors='replace'))
                # Comment string
                end2 = data.find(b'\x00', end + 1)
                offset = end2 + 1 if end2 != -1 else len(data)
                
        elif fmt == 0xFEFF:
            # Paired null-terminated format
            count = struct.unpack('<H', data[2:4])[0]
            offset = 4
            for _ in range(count):
                end = data.find(b'\x00', offset)
                if end == -1:
                    break
                strings.append(data[offset:end].decode('latin-1', errors='replace'))
                # Skip comment
                end2 = data.find(b'\x00', end + 1)
                offset = end2 + 1 if end2 != -1 else len(data)
                
        elif fmt < 256:
            # Format 0 - Pascal strings
            count = fmt
            offset = 2
            for _ in range(count):
                if offset >= len(data):
                    break
                slen = data[offset]
                offset += 1
                strings.append(data[offset:offset + slen].decode('latin-1', errors='replace'))
                offset += slen
        else:
            # Unknown format - try null-terminated from start
            offset = 0
            while offset < len(data):
                end = data.find(b'\x00', offset)
                if end == -1 or end == offset:
                    break
                strings.append(data[offset:end].decode('latin-1', errors='replace'))
                offset = end + 1
                
        return strings


class SkinRegistry:
    """
    Registry for collecting and cataloging Sim skins.
    
    Automatically discovers skin information from:
    - Character IFF files (User####.iff)
    - Family files (*.FAM)
    - Object files with character data
    """
    
    # Body string indices (per TheSimsOpenTechDoc)
    IDX_AGE = 0         # "adult" or "child"
    IDX_BODY = 1        # Body mesh + texture
    IDX_HEAD = 2        # Head mesh + texture
    IDX_GENDER = 12     # "male" or "female"
    IDX_AGE_NUM = 13    # Age number (27 for adult)
    IDX_SKIN = 14       # Skin tone (lgt/med/drk)
    IDX_NUDE = 15       # Nude/underwear outfit
    IDX_SWIM = 16       # Swimwear outfit
    IDX_LHO = 17        # Left hand open
    IDX_RHO = 18        # Right hand open
    IDX_LHP = 19        # Left hand pointing
    IDX_RHP = 20        # Right hand pointing
    IDX_LHC = 21        # Left hand closed
    IDX_RHC = 22        # Right hand closed
    
    def __init__(self):
        self.characters: Dict[str, CharacterAppearance] = {}
        self.unique_bodies: Dict[str, SkinEntry] = {}
        self.unique_heads: Dict[str, SkinEntry] = {}
        self.unique_hands: Dict[str, SkinEntry] = {}
        self.scan_count = 0
        
    def extract_from_iff(self, iff_reader, source_file: str = "") -> Optional[CharacterAppearance]:
        """Extract character appearance from an IFF reader."""
        # Find STR# chunk with ID 200
        str_chunk = None
        for chunk in iff_reader.chunks:
            if chunk.type_code == 'STR#' and chunk.chunk_id == 200:
                str_chunk = chunk
                break
        
        if not str_chunk:
            return None
            
        strings = STRParser.parse(str_chunk.chunk_data)
        if len(strings) < 15:  # Need at least up to skin tone
            return None
            
        return self._parse_body_strings(strings, source_file)
    
    def _parse_body_strings(self, strings: List[str], source_file: str) -> CharacterAppearance:
        """Parse body strings into CharacterAppearance."""
        def safe_get(idx: int) -> str:
            return strings[idx] if idx < len(strings) else ""
        
        appearance = CharacterAppearance(
            age=safe_get(self.IDX_AGE),
            gender=safe_get(self.IDX_GENDER),
            skin_tone=safe_get(self.IDX_SKIN),
            source_file=source_file
        )
        
        # Age number
        try:
            appearance.age_number = int(safe_get(self.IDX_AGE_NUM))
        except ValueError:
            appearance.age_number = 27 if appearance.age == "adult" else 9
        
        # Body
        body_str = safe_get(self.IDX_BODY)
        if body_str:
            appearance.body = SkinEntry.parse(body_str, "body", source_file)
            if appearance.body:
                self.unique_bodies[appearance.body.mesh_name] = appearance.body
        
        # Head
        head_str = safe_get(self.IDX_HEAD)
        if head_str:
            appearance.head = SkinEntry.parse(head_str, "head", source_file)
            if appearance.head:
                self.unique_heads[appearance.head.mesh_name] = appearance.head
        
        # Nude
        nude_str = safe_get(self.IDX_NUDE)
        if nude_str:
            appearance.nude = SkinEntry.parse(nude_str, "nude", source_file)
        
        # Swim
        swim_str = safe_get(self.IDX_SWIM)
        if swim_str:
            appearance.swim = SkinEntry.parse(swim_str, "swim", source_file)
        
        # Hands
        hand_indices = [
            (self.IDX_LHO, "left_open"),
            (self.IDX_RHO, "right_open"),
            (self.IDX_LHP, "left_point"),
            (self.IDX_RHP, "right_point"),
            (self.IDX_LHC, "left_closed"),
            (self.IDX_RHC, "right_closed"),
        ]
        for idx, name in hand_indices:
            hand_str = safe_get(idx)
            if hand_str:
                hand_entry = SkinEntry.parse(hand_str, "hand", source_file)
                if hand_entry:
                    appearance.hands[name] = hand_entry
                    self.unique_hands[hand_entry.mesh_name] = hand_entry
        
        # Track character
        char_key = f"{source_file}_{self.scan_count}"
        self.characters[char_key] = appearance
        self.scan_count += 1
        
        return appearance
    
    def scan_directory(self, directory: str, recursive: bool = True) -> int:
        """Scan directory for character IFF files."""
        from .iff_reader import IFFReader
        
        count = 0
        path = Path(directory)
        
        pattern = "**/*.iff" if recursive else "*.iff"
        for iff_path in path.glob(pattern):
            if iff_path.name.startswith('User') or iff_path.suffix.upper() == '.FAM':
                reader = IFFReader(str(iff_path))
                if reader.read():
                    appearance = self.extract_from_iff(reader, str(iff_path))
                    if appearance:
                        count += 1
        
        return count
    
    def get_summary(self) -> dict:
        """Get summary of registered skins."""
        return {
            "characters_scanned": len(self.characters),
            "unique_bodies": len(self.unique_bodies),
            "unique_heads": len(self.unique_heads),
            "unique_hands": len(self.unique_hands),
            "body_meshes": list(self.unique_bodies.keys()),
            "head_meshes": list(self.unique_heads.keys()),
        }
    
    def export_to_json(self, filepath: str):
        """Export registry to JSON file."""
        data = {
            "summary": self.get_summary(),
            "characters": {k: v.to_dict() for k, v in self.characters.items()},
            "unique_bodies": {k: asdict(v) for k, v in self.unique_bodies.items()},
            "unique_heads": {k: asdict(v) for k, v in self.unique_heads.items()},
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load_from_json(cls, filepath: str) -> 'SkinRegistry':
        """Load registry from JSON file."""
        registry = cls()
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct entries
        for mesh_name, entry_dict in data.get("unique_bodies", {}).items():
            registry.unique_bodies[mesh_name] = SkinEntry(**entry_dict)
        for mesh_name, entry_dict in data.get("unique_heads", {}).items():
            registry.unique_heads[mesh_name] = SkinEntry(**entry_dict)
            
        return registry


def extract_mesh_texture_pair(entry_str: str) -> Tuple[str, str]:
    """
    Extract mesh and texture names from body string format.
    
    Examples:
        "b002mafat_01,BODY=B002MAFatlgt_slob" -> ("b002mafat_01", "B002MAFatlgt_slob")
        "c010ma_baldbeard,HEAD-HEAD=C010MAlgt_baldbeard01" -> ("c010ma_baldbeard", "C010MAlgt_baldbeard01")
    """
    if not entry_str or ',' not in entry_str:
        return (entry_str, "")
    
    parts = entry_str.split(',', 1)
    mesh_name = parts[0].strip()
    texture_name = ""
    
    if len(parts) > 1:
        eq_idx = parts[1].find('=')
        if eq_idx != -1:
            texture_name = parts[1][eq_idx + 1:].strip()
    
    return (mesh_name, texture_name)


def decode_mesh_naming(mesh_name: str) -> dict:
    """
    Decode mesh naming convention.
    
    Body format: b###[m/f][a/c][fat/fit/skn]_##
    Head format: c###[m/f][a/c]_name
    Hand format: H[m/f/u][L/R][O/P/C]
    
    Examples:
        "b002mafat_01" -> {type: "body", gender: "male", age: "adult", build: "fat"}
        "c010ma_baldbeard" -> {type: "head", gender: "male", age: "adult", name: "baldbeard"}
        "HmLO" -> {type: "hand", gender: "male", side: "left", pose: "open"}
    """
    result = {"original": mesh_name}
    
    if not mesh_name:
        return result
    
    name_lower = mesh_name.lower()
    
    # Hand mesh
    if name_lower.startswith('h') and len(mesh_name) >= 4:
        if mesh_name[1] in 'mfuMFU' and mesh_name[2] in 'lrLR':
            result["type"] = "hand"
            result["gender"] = {"m": "male", "f": "female", "u": "child"}.get(mesh_name[1].lower(), "unknown")
            result["side"] = {"l": "left", "r": "right"}.get(mesh_name[2].lower(), "unknown")
            if len(mesh_name) > 3:
                result["pose"] = {"o": "open", "p": "pointing", "c": "closed"}.get(mesh_name[3].lower(), "unknown")
            return result
    
    # Body mesh (starts with 'b')
    if name_lower.startswith('b') and len(mesh_name) >= 8:
        result["type"] = "body"
        # Try to extract parts
        if len(mesh_name) > 4:
            gender_char = mesh_name[4:5].lower()
            result["gender"] = "male" if gender_char == 'm' else "female" if gender_char == 'f' else "unknown"
        if len(mesh_name) > 5:
            age_char = mesh_name[5:6].lower()
            result["age"] = "adult" if age_char == 'a' else "child" if age_char == 'c' else "unknown"
        # Build type
        if "fat" in name_lower:
            result["build"] = "fat"
        elif "fit" in name_lower:
            result["build"] = "fit"
        elif "skn" in name_lower:
            result["build"] = "skinny"
        return result
    
    # Head mesh (starts with 'c')
    if name_lower.startswith('c') and len(mesh_name) >= 6:
        result["type"] = "head"
        if len(mesh_name) > 4:
            gender_char = mesh_name[4:5].lower()
            result["gender"] = "male" if gender_char == 'm' else "female" if gender_char == 'f' else "unknown"
        if len(mesh_name) > 5:
            age_char = mesh_name[5:6].lower()
            result["age"] = "adult" if age_char == 'a' else "child" if age_char == 'c' else "unknown"
        # Extract name part after underscore
        if '_' in mesh_name:
            result["name"] = mesh_name.split('_', 1)[1]
        return result
    
    # Nude mesh (starts with 'n')
    if name_lower.startswith('n') and len(mesh_name) >= 5:
        result["type"] = "nude"
        if mesh_name[1:2].lower() in 'mf':
            result["gender"] = "male" if mesh_name[1].lower() == 'm' else "female"
        return result
    
    # Swim mesh (starts with 's' or 'u')
    if name_lower.startswith(('s', 'u')) and ('fit' in name_lower or 'fat' in name_lower or 'skn' in name_lower):
        result["type"] = "swimwear" if name_lower.startswith('s') else "underwear"
        return result
    
    return result
