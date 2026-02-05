"""
AssetScanner - Configurable multi-path scanner for The Sims 1 assets.

Scans FAR archives, IFF files, and ZIPs recursively to build a complete
asset database for library browsing and character viewer integration.

Extracted data:
- Object GUIDs and names
- Mesh references (body, head, hand)
- Texture references
- Animation references
- Skin codes (age, gender, body type, skin tone)
- Family/character data
"""

import os
import struct
import json
import zipfile
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Iterator, Callable
from datetime import datetime
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from formats.far.far1 import FAR1Archive


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ObjectRecord:
    """An object found in IFF (from OBJD chunk)."""
    guid: int
    name: str
    source_file: str
    source_archive: str = ""
    catalog_id: int = 0
    price: int = 0
    
    @property
    def guid_hex(self) -> str:
        return f"0x{self.guid:08X}"


@dataclass 
class MeshRecord:
    """A mesh reference found in assets."""
    mesh_name: str
    mesh_type: str  # body, head, hand
    source_file: str
    source_archive: str = ""
    texture_name: str = ""
    # Decoded from naming convention
    age: str = ""      # adult, child
    gender: str = ""   # male, female, unknown
    body_type: str = "" # fit, fat, skn
    skin_tone: str = "" # lgt, med, drk


@dataclass
class CharacterRecord:
    """A character/sim from FAM or User IFF."""
    name: str
    source_file: str
    body_mesh: str = ""
    head_mesh: str = ""
    skin_tone: str = ""
    age: str = ""
    gender: str = ""
    body_type: str = ""
    

@dataclass
class AnimationRecord:
    """An animation reference."""
    anim_name: str
    source_file: str
    source_archive: str = ""


@dataclass
class ScanProgress:
    """Progress tracking for scanner."""
    total_files: int = 0
    processed_files: int = 0
    current_file: str = ""
    objects_found: int = 0
    meshes_found: int = 0
    characters_found: int = 0
    animations_found: int = 0
    errors: list = field(default_factory=list)


# ============================================================================
# SCANNER CONFIGURATION
# ============================================================================

@dataclass
class ScanPath:
    """A configured scan path."""
    path: str
    label: str
    enabled: bool = True
    recursive: bool = True
    scan_zips: bool = True
    scan_fars: bool = True


class ScannerConfig:
    """Scanner configuration with up to 5 configurable paths."""
    
    DEFAULT_PATHS = [
        ScanPath(
            path=r"G:\SteamLibrary\steamapps\common\The Sims Legacy Collection",
            label="Steam Legacy Collection",
            enabled=True
        ),
        ScanPath(
            path=str(Path.home() / "Saved Games" / "Electronic Arts"),
            label="Game Saves",
            enabled=True
        ),
        ScanPath(
            path=r"S:\PCGames\SimsStuff\TheSims1_Tools\Archives\Backup Families",
            label="Backup Families",
            enabled=True
        ),
        ScanPath(
            path=r"S:\PCGames\SimsStuff\TheSims1_Tools\Archives\Official Maxis Objects",
            label="Official Maxis Objects",
            enabled=True
        ),
        ScanPath(
            path="",
            label="Custom Path",
            enabled=False
        ),
    ]
    
    def __init__(self, config_file: Optional[str] = None):
        self.paths = list(self.DEFAULT_PATHS)
        self.output_dir = Path(__file__).parent.parent / "data"
        self.database_file = self.output_dir / "asset_database.sqlite"
        
        if config_file and Path(config_file).exists():
            self.load(config_file)
    
    def save(self, config_file: str):
        """Save configuration to JSON."""
        data = {
            "paths": [{"path": p.path, "label": p.label, "enabled": p.enabled, 
                      "recursive": p.recursive, "scan_zips": p.scan_zips, 
                      "scan_fars": p.scan_fars} for p in self.paths],
            "output_dir": str(self.output_dir),
            "database_file": str(self.database_file)
        }
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, config_file: str):
        """Load configuration from JSON."""
        with open(config_file, 'r') as f:
            data = json.load(f)
        self.paths = [ScanPath(**p) for p in data.get("paths", [])]
        if "output_dir" in data:
            self.output_dir = Path(data["output_dir"])
        if "database_file" in data:
            self.database_file = Path(data["database_file"])


# ============================================================================
# IFF PARSING UTILITIES
# ============================================================================

def extract_objd_from_iff(data: bytes, source_file: str, source_archive: str = "") -> list[ObjectRecord]:
    """Extract OBJD chunks from IFF data."""
    objects = []
    if len(data) < 64:
        return objects
    
    pos = 64  # Skip IFF header
    while pos < len(data) - 76:
        try:
            type_code = data[pos:pos+4].decode('ascii', errors='ignore')
            chunk_size = struct.unpack('>I', data[pos+4:pos+8])[0]
            
            if chunk_size < 76 or chunk_size > len(data) - pos:
                break
                
            if type_code == 'OBJD' and chunk_size > 100:
                chunk_data = data[pos+76:pos+chunk_size]
                if len(chunk_data) >= 30:
                    # GUID at offset 26-30
                    guid = struct.unpack('<I', chunk_data[26:30])[0]
                    # Try to get name from chunk header
                    name = ""
                    try:
                        # Chunk label is at pos+12 (64 bytes max)
                        raw_name = data[pos+12:pos+76]
                        name = raw_name.split(b'\x00')[0].decode('ascii', errors='ignore')
                    except:
                        pass
                    
                    if guid != 0:
                        objects.append(ObjectRecord(
                            guid=guid,
                            name=name or f"Object_{guid:08X}",
                            source_file=source_file,
                            source_archive=source_archive
                        ))
            
            pos += chunk_size
        except:
            break
    
    return objects


def extract_str_chunk(data: bytes, str_id: int) -> list[str]:
    """Extract a specific STR# chunk by ID. 
    
    Note: User IFF files use STR# 51200 (0xC800) for body strings,
    while documentation refers to STR# 200. Both are checked.
    """
    strings = []
    if len(data) < 64:
        return strings
    
    # Also check alternative IDs used in User IFFs
    ids_to_check = [str_id]
    if str_id == 200:
        ids_to_check.append(51200)  # 0xC800 - User IFF format
    
    pos = 64
    while pos < len(data) - 76:
        try:
            type_code = data[pos:pos+4].decode('ascii', errors='ignore')
            chunk_size = struct.unpack('>I', data[pos+4:pos+8])[0]
            
            if chunk_size < 76 or chunk_size > len(data) - pos:
                break
            
            if type_code == 'STR#':
                # Check chunk ID at offset 8
                chunk_id = struct.unpack('<H', data[pos+8:pos+10])[0]
                if chunk_id in ids_to_check:
                    chunk_data = data[pos+76:pos+chunk_size]
                    # Parse STR# format
                    if len(chunk_data) >= 2:
                        format_code = struct.unpack('<H', chunk_data[0:2])[0]
                        if format_code == 0xFFFD and len(chunk_data) >= 4:
                            num_strings = struct.unpack('<H', chunk_data[2:4])[0]
                            str_pos = 4
                            for _ in range(num_strings):
                                if str_pos >= len(chunk_data):
                                    break
                                try:
                                    # Language code + 2 pascal strings
                                    str_pos += 1  # lang code
                                    if str_pos < len(chunk_data):
                                        str_len = chunk_data[str_pos]
                                        str_pos += 1
                                        s = chunk_data[str_pos:str_pos+str_len].decode('latin-1', errors='ignore')
                                        strings.append(s)
                                        str_pos += str_len
                                        # Skip description
                                        if str_pos < len(chunk_data):
                                            desc_len = chunk_data[str_pos]
                                            str_pos += 1 + desc_len
                                except:
                                    break
                    break
            
            pos += chunk_size
        except:
            break
    
    return strings


def decode_mesh_name(mesh_name: str) -> dict:
    """Decode mesh naming convention to extract metadata."""
    result = {
        "age": "",
        "gender": "",
        "body_type": "",
        "skin_tone": "",
        "mesh_type": ""
    }
    
    name = mesh_name.lower()
    
    # Body mesh: b###[m/f][a/c][fat/fit/skn]_##
    if name.startswith('b') and len(name) >= 7:
        result["mesh_type"] = "body"
        # Gender at position 4
        if len(name) > 4:
            if name[4] == 'm':
                result["gender"] = "male"
            elif name[4] == 'f':
                result["gender"] = "female"
            elif name[4] == 'u':
                result["gender"] = "unknown"
        # Age at position 5
        if len(name) > 5:
            if name[5] == 'a':
                result["age"] = "adult"
            elif name[5] == 'c':
                result["age"] = "child"
        # Body type
        if 'fat' in name:
            result["body_type"] = "fat"
        elif 'fit' in name:
            result["body_type"] = "fit"
        elif 'skn' in name:
            result["body_type"] = "skinny"
        elif 'chd' in name:
            result["body_type"] = "child"
    
    # Head mesh: c###[m/f][a/c]_name
    elif name.startswith('c') and len(name) >= 6:
        result["mesh_type"] = "head"
        if len(name) > 4:
            if name[4] == 'm':
                result["gender"] = "male"
            elif name[4] == 'f':
                result["gender"] = "female"
        if len(name) > 5:
            if name[5] == 'a':
                result["age"] = "adult"
            elif name[5] == 'c':
                result["age"] = "child"
    
    # Hand mesh: H[m/f/u][L/R][O/P/C]
    elif name.startswith('h') and len(name) >= 4:
        result["mesh_type"] = "hand"
    
    # Skin tone from texture
    if 'lgt' in name:
        result["skin_tone"] = "light"
    elif 'med' in name:
        result["skin_tone"] = "medium"
    elif 'drk' in name:
        result["skin_tone"] = "dark"
    
    return result


def extract_uchr_skins(data: bytes) -> list[str]:
    """Extract skin strings from uChr chunks (embedded in FAM files)."""
    skins = []
    # Search for skin-related patterns
    patterns = [b',BODY=', b',HEAD-HEAD=', b'fit_', b'fat_', b'skn_']
    
    for pattern in patterns:
        idx = 0
        while True:
            idx = data.find(pattern, idx)
            if idx == -1:
                break
            # Extract surrounding context
            start = max(0, idx - 50)
            end = min(len(data), idx + 100)
            chunk = data[start:end]
            # Find the mesh name
            try:
                text = chunk.decode('latin-1', errors='ignore')
                # Look for mesh names
                import re
                matches = re.findall(r'[bc]\d{3}[mfu][ac][a-z_]+', text, re.IGNORECASE)
                skins.extend(matches)
            except:
                pass
            idx += 1
    
    return list(set(skins))


# ============================================================================
# MAIN SCANNER CLASS
# ============================================================================

class AssetScanner:
    """
    Main scanner class for building asset database.
    
    Usage:
        scanner = AssetScanner()
        scanner.scan_all(progress_callback=my_callback)
        scanner.save_database()
    """
    
    def __init__(self, config: Optional[ScannerConfig] = None):
        self.config = config or ScannerConfig()
        self.objects: list[ObjectRecord] = []
        self.meshes: list[MeshRecord] = []
        self.characters: list[CharacterRecord] = []
        self.animations: list[AnimationRecord] = []
        self.progress = ScanProgress()
        self._progress_callback: Optional[Callable[[ScanProgress], None]] = None
    
    def scan_all(self, progress_callback: Optional[Callable[[ScanProgress], None]] = None):
        """Scan all configured paths."""
        self._progress_callback = progress_callback
        self.progress = ScanProgress()
        
        # Count total files first
        for scan_path in self.config.paths:
            if scan_path.enabled and scan_path.path and Path(scan_path.path).exists():
                self._count_files(Path(scan_path.path), scan_path)
        
        self._update_progress()
        
        # Scan each path
        for scan_path in self.config.paths:
            if scan_path.enabled and scan_path.path and Path(scan_path.path).exists():
                print(f"\n{'='*60}")
                print(f"Scanning: {scan_path.label}")
                print(f"Path: {scan_path.path}")
                print(f"{'='*60}")
                self._scan_path(Path(scan_path.path), scan_path)
        
        self._update_progress()
        print(f"\n{'='*60}")
        print("SCAN COMPLETE")
        print(f"Objects: {len(self.objects)}")
        print(f"Meshes: {len(self.meshes)}")
        print(f"Characters: {len(self.characters)}")
        print(f"Errors: {len(self.progress.errors)}")
        print(f"{'='*60}")
    
    def _count_files(self, path: Path, scan_path: ScanPath):
        """Count files to process."""
        try:
            for item in path.iterdir():
                if item.is_file():
                    ext = item.suffix.lower()
                    if ext in ['.iff', '.far']:
                        self.progress.total_files += 1
                    elif ext == '.zip' and scan_path.scan_zips:
                        self.progress.total_files += 1
                elif item.is_dir() and scan_path.recursive:
                    self._count_files(item, scan_path)
        except PermissionError:
            pass
    
    def _scan_path(self, path: Path, scan_path: ScanPath):
        """Recursively scan a path."""
        try:
            for item in path.iterdir():
                if item.is_file():
                    self._scan_file(item, scan_path)
                elif item.is_dir() and scan_path.recursive:
                    self._scan_path(item, scan_path)
        except PermissionError as e:
            self.progress.errors.append(f"Permission denied: {path}")
    
    def _scan_file(self, file_path: Path, scan_path: ScanPath):
        """Scan a single file."""
        ext = file_path.suffix.lower()
        self.progress.current_file = str(file_path)
        
        try:
            if ext == '.far' and scan_path.scan_fars:
                self._scan_far(file_path)
            elif ext == '.iff':
                # Check if it's a User IFF (character file)
                is_user_iff = file_path.name.upper().startswith('USER')
                self._scan_iff(file_path, is_user_iff=is_user_iff)
            elif ext == '.zip' and scan_path.scan_zips:
                self._scan_zip(file_path)
            elif ext == '.fam':
                # FAM files are IFF format
                self._scan_iff(file_path, is_fam=True)
        except Exception as e:
            self.progress.errors.append(f"{file_path}: {e}")
        
        self.progress.processed_files += 1
        
        # Step output every 10 files
        if self.progress.processed_files % 10 == 0:
            self._update_progress()
    
    def _scan_far(self, far_path: Path):
        """Scan a FAR archive."""
        try:
            far = FAR1Archive(str(far_path))
            print(f"  FAR: {far_path.name} ({len(far.entries)} entries)")
            
            for entry in far.entries:
                if entry.filename.upper().endswith('.IFF'):
                    data = far.get_entry(entry.filename)
                    if data:
                        self._process_iff_data(data, entry.filename, str(far_path))
        except Exception as e:
            self.progress.errors.append(f"FAR error {far_path}: {e}")
    
    def _scan_iff(self, iff_path: Path, is_fam: bool = False, is_user_iff: bool = False):
        """Scan an IFF file."""
        try:
            with open(iff_path, 'rb') as f:
                data = f.read()
            
            self._process_iff_data(data, iff_path.name, "", is_fam=is_fam, is_user_iff=is_user_iff)
            
        except Exception as e:
            self.progress.errors.append(f"IFF error {iff_path}: {e}")
    
    def _scan_zip(self, zip_path: Path):
        """Scan a ZIP archive."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    if name.upper().endswith('.IFF') or name.upper().endswith('.FAM'):
                        try:
                            data = zf.read(name)
                            basename = Path(name).name.upper()
                            is_user_iff = basename.startswith('USER')
                            self._process_iff_data(data, name, str(zip_path), 
                                                   is_fam=name.upper().endswith('.FAM'),
                                                   is_user_iff=is_user_iff)
                        except:
                            pass
        except Exception as e:
            self.progress.errors.append(f"ZIP error {zip_path}: {e}")
    
    def _process_iff_data(self, data: bytes, source_file: str, source_archive: str, 
                          is_fam: bool = False, is_user_iff: bool = False):
        """Process IFF data and extract all asset information."""
        # Extract objects
        objects = extract_objd_from_iff(data, source_file, source_archive)
        for obj in objects:
            self.objects.append(obj)
            self.progress.objects_found += 1
        
        # Extract STR# 200 (Body Strings) for skin info
        # User IFFs use STR# 51200 instead - extract_str_chunk handles both
        body_strings = extract_str_chunk(data, 200)
        
        # For User IFFs, we need to parse the format differently
        # The first string often contains combined data
        if is_user_iff and body_strings:
            # User IFF format: strings contain embedded mesh refs
            char = CharacterRecord(
                name=source_file.replace('.iff', '').replace('.IFF', ''),
                source_file=source_file
            )
            
            # Parse each string for mesh references
            import re
            for s in body_strings:
                # Look for body mesh patterns
                body_match = re.search(r'([bc]\d{3}[mfu][ac][a-z_0-9]+),BODY=', s, re.IGNORECASE)
                if body_match and not char.body_mesh:
                    mesh_name = body_match.group(1)
                    char.body_mesh = mesh_name
                    meta = decode_mesh_name(mesh_name)
                    self.meshes.append(MeshRecord(
                        mesh_name=mesh_name,
                        mesh_type="body",
                        source_file=source_file,
                        source_archive=source_archive,
                        **{k: v for k, v in meta.items() if k != "mesh_type"}
                    ))
                    self.progress.meshes_found += 1
                
                # Look for head mesh patterns
                head_match = re.search(r'([c]\d{3}[mfu][ac][a-z_0-9]+),HEAD-HEAD=', s, re.IGNORECASE)
                if head_match and not char.head_mesh:
                    mesh_name = head_match.group(1)
                    char.head_mesh = mesh_name
                    meta = decode_mesh_name(mesh_name)
                    self.meshes.append(MeshRecord(
                        mesh_name=mesh_name,
                        mesh_type="head",
                        source_file=source_file,
                        source_archive=source_archive,
                        **{k: v for k, v in meta.items() if k != "mesh_type"}
                    ))
                    self.progress.meshes_found += 1
            
            if char.body_mesh or char.head_mesh:
                self.characters.append(char)
                self.progress.characters_found += 1
                
        elif body_strings:
            char = CharacterRecord(
                name=source_file.replace('.iff', '').replace('.IFF', ''),
                source_file=source_file
            )
            
            # Parse body strings
            for i, s in enumerate(body_strings):
                if i == 0:  # Age
                    char.age = s.lower() if s else ""
                elif i == 1 and ',' in s:  # Body mesh
                    mesh_name = s.split(',')[0]
                    char.body_mesh = mesh_name
                    meta = decode_mesh_name(mesh_name)
                    self.meshes.append(MeshRecord(
                        mesh_name=mesh_name,
                        mesh_type="body",
                        source_file=source_file,
                        source_archive=source_archive,
                        **{k: v for k, v in meta.items() if k != "mesh_type"}
                    ))
                    self.progress.meshes_found += 1
                elif i == 2 and ',' in s:  # Head mesh
                    mesh_name = s.split(',')[0]
                    char.head_mesh = mesh_name
                    meta = decode_mesh_name(mesh_name)
                    self.meshes.append(MeshRecord(
                        mesh_name=mesh_name,
                        mesh_type="head",
                        source_file=source_file,
                        source_archive=source_archive,
                        **{k: v for k, v in meta.items() if k != "mesh_type"}
                    ))
                    self.progress.meshes_found += 1
                elif i == 12:  # Gender
                    char.gender = s.lower() if s else ""
                elif i == 14:  # Skin tone
                    char.skin_tone = s.lower() if s else ""
            
            if char.body_mesh or char.head_mesh:
                self.characters.append(char)
                self.progress.characters_found += 1
        
        # For FAM files, also check uChr chunks
        if is_fam:
            skins = extract_uchr_skins(data)
            for skin in skins:
                meta = decode_mesh_name(skin)
                if meta["mesh_type"]:
                    self.meshes.append(MeshRecord(
                        mesh_name=skin,
                        mesh_type=meta["mesh_type"],
                        source_file=source_file,
                        source_archive=source_archive,
                        **{k: v for k, v in meta.items() if k != "mesh_type"}
                    ))
                    self.progress.meshes_found += 1
    
    def _update_progress(self):
        """Update progress callback."""
        if self._progress_callback:
            self._progress_callback(self.progress)
        else:
            pct = (self.progress.processed_files / max(1, self.progress.total_files)) * 100
            print(f"  [{pct:5.1f}%] {self.progress.processed_files}/{self.progress.total_files} files | "
                  f"Obj:{self.progress.objects_found} Mesh:{self.progress.meshes_found} "
                  f"Char:{self.progress.characters_found}")
    
    def save_database(self, db_path: Optional[Path] = None):
        """Save to SQLite database."""
        db_path = db_path or self.config.database_file
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        
        # Create tables
        cur.execute('''CREATE TABLE IF NOT EXISTS objects (
            id INTEGER PRIMARY KEY,
            guid INTEGER,
            guid_hex TEXT,
            name TEXT,
            source_file TEXT,
            source_archive TEXT,
            catalog_id INTEGER,
            price INTEGER
        )''')
        
        cur.execute('''CREATE TABLE IF NOT EXISTS meshes (
            id INTEGER PRIMARY KEY,
            mesh_name TEXT,
            mesh_type TEXT,
            source_file TEXT,
            source_archive TEXT,
            texture_name TEXT,
            age TEXT,
            gender TEXT,
            body_type TEXT,
            skin_tone TEXT
        )''')
        
        cur.execute('''CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY,
            name TEXT,
            source_file TEXT,
            body_mesh TEXT,
            head_mesh TEXT,
            skin_tone TEXT,
            age TEXT,
            gender TEXT,
            body_type TEXT
        )''')
        
        cur.execute('''CREATE TABLE IF NOT EXISTS scan_info (
            id INTEGER PRIMARY KEY,
            scan_date TEXT,
            total_files INTEGER,
            objects_found INTEGER,
            meshes_found INTEGER,
            characters_found INTEGER,
            errors INTEGER
        )''')
        
        # Clear existing data
        cur.execute('DELETE FROM objects')
        cur.execute('DELETE FROM meshes')
        cur.execute('DELETE FROM characters')
        
        # Insert objects
        for obj in self.objects:
            cur.execute('INSERT INTO objects (guid, guid_hex, name, source_file, source_archive) VALUES (?, ?, ?, ?, ?)',
                       (obj.guid, obj.guid_hex, obj.name, obj.source_file, obj.source_archive))
        
        # Insert meshes (deduplicated)
        seen_meshes = set()
        for mesh in self.meshes:
            key = (mesh.mesh_name, mesh.mesh_type)
            if key not in seen_meshes:
                seen_meshes.add(key)
                cur.execute('INSERT INTO meshes (mesh_name, mesh_type, source_file, source_archive, texture_name, age, gender, body_type, skin_tone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                           (mesh.mesh_name, mesh.mesh_type, mesh.source_file, mesh.source_archive, 
                            mesh.texture_name, mesh.age, mesh.gender, mesh.body_type, mesh.skin_tone))
        
        # Insert characters
        for char in self.characters:
            cur.execute('INSERT INTO characters (name, source_file, body_mesh, head_mesh, skin_tone, age, gender, body_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (char.name, char.source_file, char.body_mesh, char.head_mesh, 
                        char.skin_tone, char.age, char.gender, char.body_type))
        
        # Insert scan info
        cur.execute('INSERT INTO scan_info (scan_date, total_files, objects_found, meshes_found, characters_found, errors) VALUES (?, ?, ?, ?, ?, ?)',
                   (datetime.now().isoformat(), self.progress.total_files, 
                    len(self.objects), len(seen_meshes), len(self.characters), len(self.progress.errors)))
        
        conn.commit()
        conn.close()
        
        print(f"\nDatabase saved: {db_path}")
        print(f"  Objects: {len(self.objects)}")
        print(f"  Meshes: {len(seen_meshes)}")
        print(f"  Characters: {len(self.characters)}")
    
    def export_json(self, output_dir: Optional[Path] = None):
        """Export to JSON files for web viewer."""
        output_dir = output_dir or self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Objects catalog
        with open(output_dir / "objects.json", 'w') as f:
            json.dump([asdict(o) for o in self.objects], f, indent=2)
        
        # Meshes catalog (deduplicated)
        seen = set()
        unique_meshes = []
        for m in self.meshes:
            if m.mesh_name not in seen:
                seen.add(m.mesh_name)
                unique_meshes.append(asdict(m))
        with open(output_dir / "meshes.json", 'w') as f:
            json.dump(unique_meshes, f, indent=2)
        
        # Characters
        with open(output_dir / "characters.json", 'w') as f:
            json.dump([asdict(c) for c in self.characters], f, indent=2)
        
        print(f"JSON exported to: {output_dir}")


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    """Run scanner from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scan Sims 1 assets")
    parser.add_argument('--config', help='Config file path')
    parser.add_argument('--output', help='Output directory')
    parser.add_argument('--json', action='store_true', help='Also export JSON')
    args = parser.parse_args()
    
    config = ScannerConfig(args.config)
    if args.output:
        config.output_dir = Path(args.output)
        config.database_file = config.output_dir / "asset_database.sqlite"
    
    scanner = AssetScanner(config)
    scanner.scan_all()
    scanner.save_database()
    
    if args.json:
        scanner.export_json()


if __name__ == "__main__":
    main()
