"""
CMX Parser - Character Manifest for The Sims 1

Parses .cmx files that define character appearances by linking
skeleton bones to meshes (SKN/BMF) and textures.

CMX Text Format:
  // Comment
  version 300
  skeleton_count (usually 0)
  appearance_count
  For each appearance:
    appearance_name
    unknown1 (handgroup?)
    body_type (0-2: light/medium/dark)
    binding_count
    For each binding:
      bone_name
      mesh_filename
      texture_name (can be 0 for none)
      unknown2
      unknown3
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict


@dataclass
class CMXBinding:
    """Links a bone to a mesh and texture."""
    bone_name: str = ""
    mesh_name: str = ""  # SKN/BMF filename (without extension)
    texture_name: str = ""  # BMP filename (without extension), empty if '0'


@dataclass 
class CMXAppearance:
    """A character appearance/outfit."""
    name: str = ""
    hand_group: int = 0
    body_type: int = 0  # 0=light, 1=medium, 2=dark
    bindings: List[CMXBinding] = field(default_factory=list)
    
    @property
    def skin_tone(self) -> str:
        """Human-readable skin tone."""
        tones = {0: "Light", 1: "Medium", 2: "Dark"}
        return tones.get(self.body_type, "Unknown")


@dataclass
class CMXFile:
    """Complete CMX character manifest."""
    version: int = 300
    filename: str = ""
    appearances: List[CMXAppearance] = field(default_factory=list)
    
    def get_all_meshes(self) -> List[str]:
        """Get list of all referenced mesh names."""
        meshes = []
        for app in self.appearances:
            for binding in app.bindings:
                if binding.mesh_name and binding.mesh_name not in meshes:
                    meshes.append(binding.mesh_name)
        return meshes
    
    def get_all_textures(self) -> List[str]:
        """Get list of all referenced texture names."""
        textures = []
        for app in self.appearances:
            for binding in app.bindings:
                if binding.texture_name and binding.texture_name not in textures:
                    textures.append(binding.texture_name)
        return textures


class CMXReader:
    """
    Parser for CMX (Character Manifest) files.
    
    Usage:
        reader = CMXReader()
        cmx = reader.read_file("character.cmx")
        
        for app in cmx.appearances:
            print(f"Appearance: {app.name}")
            for binding in app.bindings:
                print(f"  {binding.bone_name} -> {binding.mesh_name}")
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
    
    def _parse(self) -> CMXFile:
        """Parse CMX content."""
        cmx = CMXFile()
        
        # Version line: "version 300"
        version_line = self._next_line()
        if version_line.startswith('version'):
            cmx.version = int(version_line.split()[1])
        
        # Skeleton count (usually 0, skeletons are in BCF files)
        skeleton_count = int(self._next_line())
        # Skip skeleton data if any
        for _ in range(skeleton_count):
            # Each skeleton would have bone data, but usually 0
            pass
        
        # Appearance count
        appearance_count = int(self._next_line())
        
        # Parse appearances
        for _ in range(appearance_count):
            app = CMXAppearance()
            
            # Appearance name
            app.name = self._next_line()
            
            # Hand group (unknown purpose)
            app.hand_group = int(self._next_line())
            
            # Body type / skin tone
            app.body_type = int(self._next_line())
            
            # Binding count
            binding_count = int(self._next_line())
            
            # Parse bindings
            for _ in range(binding_count):
                binding = CMXBinding()
                
                # Bone name
                binding.bone_name = self._next_line()
                
                # Mesh filename
                binding.mesh_name = self._next_line()
                
                # Texture name (can be '0' for none)
                tex = self._next_line()
                binding.texture_name = "" if tex == "0" else tex
                
                # Two unknown values
                self._next_line()  # unknown1
                self._next_line()  # unknown2
                
                app.bindings.append(binding)
            
            cmx.appearances.append(app)
        
        return cmx


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
        
        for tex_name in cmx.get_all_textures():
            path = self.find_texture(tex_name)
            if path:
                result['textures'][tex_name] = path
            else:
                result['missing_textures'].append(tex_name)
        
        return result


# Test
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        reader = CMXReader()
        cmx = reader.read_file(sys.argv[1])
        if cmx:
            print(f"CMX Version: {cmx.version}")
            print(f"Appearances: {len(cmx.appearances)}")
            
            for app in cmx.appearances:
                print(f"\n  Appearance: {app.name}")
                print(f"    Skin tone: {app.skin_tone}")
                print(f"    Bindings: {len(app.bindings)}")
                
                for binding in app.bindings:
                    print(f"      {binding.bone_name}:")
                    print(f"        Mesh: {binding.mesh_name}")
                    print(f"        Texture: {binding.texture_name or '(none)'}")
            
            print(f"\nAll meshes: {cmx.get_all_meshes()}")
            print(f"All textures: {cmx.get_all_textures()}")
