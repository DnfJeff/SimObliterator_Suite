"""
SKN Parser - Text-based Skin/Mesh Format for The Sims 1

Parses .skn files containing mesh data in text format.
This is the source format before compilation to .bmf (binary).

SKN Text Format:
  Line 1: Mesh name
  Line 2: Texture name
  Line 3: Bone count
  Lines 4-N: Bone names (one per line)
  Line N+1: Face count
  Faces: "v0 v1 v2" (one per line)
  Bone binding count
  Bindings: "bone_idx first_real real_count first_blend blend_count"
  UV count
  UVs: "u v" (one per line)
  Blend data count
  Blends: "weight other_vertex" (one per line)
  Vertex count
  Vertices: "x y z nx ny nz" (one per line)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional


@dataclass
class SKNBoneBinding:
    """Maps vertices to a bone."""
    bone_index: int = 0
    first_real_vertex: int = 0
    real_vertex_count: int = 0
    first_blend_vertex: int = 0
    blend_vertex_count: int = 0


@dataclass
class SKNBlendData:
    """Blend weight for vertex skinning."""
    weight: float = 0.0
    other_vertex: int = 0


@dataclass
class SKNVertex:
    """3D vertex with position and normal."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    nx: float = 0.0
    ny: float = 0.0
    nz: float = 0.0
    
    @property
    def position(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
    @property
    def normal(self) -> Tuple[float, float, float]:
        return (self.nx, self.ny, self.nz)


@dataclass
class SKNMesh:
    """Complete SKN mesh data."""
    mesh_name: str = ""
    texture_name: str = ""
    bone_names: List[str] = field(default_factory=list)
    faces: List[Tuple[int, int, int]] = field(default_factory=list)
    bone_bindings: List[SKNBoneBinding] = field(default_factory=list)
    texture_coords: List[Tuple[float, float]] = field(default_factory=list)
    blend_data: List[SKNBlendData] = field(default_factory=list)
    vertices: List[SKNVertex] = field(default_factory=list)
    
    @property
    def vertex_count(self) -> int:
        return len(self.vertices)
    
    @property
    def face_count(self) -> int:
        return len(self.faces)


class SKNReader:
    """
    Parser for SKN (text-based skin) mesh files.
    
    Usage:
        reader = SKNReader()
        mesh = reader.read_file("skin.skn")
    """
    
    def __init__(self):
        self.lines: List[str] = []
        self.line_idx: int = 0
    
    def read_file(self, filepath: str) -> Optional[SKNMesh]:
        """Read and parse an SKN file."""
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                self.lines = [line.strip() for line in f.readlines()]
            self.line_idx = 0
            return self._parse()
        except Exception as e:
            print(f"Error parsing SKN {filepath}: {e}")
            return None
    
    def read_string(self, text: str) -> Optional[SKNMesh]:
        """Parse SKN from string content."""
        try:
            self.lines = [line.strip() for line in text.split('\n')]
            self.line_idx = 0
            return self._parse()
        except Exception as e:
            print(f"Error parsing SKN: {e}")
            return None
    
    def _next_line(self) -> str:
        """Get next non-empty line."""
        while self.line_idx < len(self.lines):
            line = self.lines[self.line_idx]
            self.line_idx += 1
            if line and not line.startswith('//'):
                return line
        return ""
    
    def _parse(self) -> SKNMesh:
        """Parse SKN content."""
        mesh = SKNMesh()
        
        # Line 1: Mesh name
        mesh.mesh_name = self._next_line()
        
        # Line 2: Texture name
        mesh.texture_name = self._next_line()
        
        # Line 3: Bone count
        bone_count = int(self._next_line())
        
        # Bone names
        for _ in range(bone_count):
            mesh.bone_names.append(self._next_line())
        
        # Face count
        face_count = int(self._next_line())
        
        # Faces (v0 v1 v2)
        for _ in range(face_count):
            parts = self._next_line().split()
            if len(parts) >= 3:
                mesh.faces.append((int(parts[0]), int(parts[1]), int(parts[2])))
        
        # Bone binding count
        binding_count = int(self._next_line())
        
        # Bone bindings
        for _ in range(binding_count):
            parts = self._next_line().split()
            if len(parts) >= 5:
                binding = SKNBoneBinding(
                    bone_index=int(parts[0]),
                    first_real_vertex=int(parts[1]),
                    real_vertex_count=int(parts[2]),
                    first_blend_vertex=int(parts[3]),
                    blend_vertex_count=int(parts[4])
                )
                mesh.bone_bindings.append(binding)
        
        # UV count
        uv_count = int(self._next_line())
        
        # UVs
        for _ in range(uv_count):
            parts = self._next_line().split()
            if len(parts) >= 2:
                mesh.texture_coords.append((float(parts[0]), float(parts[1])))
        
        # Blend data count
        blend_count = int(self._next_line())
        
        # Blend data
        for _ in range(blend_count):
            parts = self._next_line().split()
            if len(parts) >= 2:
                blend = SKNBlendData(
                    weight=float(parts[0]),
                    other_vertex=int(parts[1])
                )
                mesh.blend_data.append(blend)
        
        # Vertex count
        vertex_count = int(self._next_line())
        
        # Vertices (x y z nx ny nz)
        for _ in range(vertex_count):
            parts = self._next_line().split()
            if len(parts) >= 6:
                vertex = SKNVertex(
                    x=float(parts[0]),
                    y=float(parts[1]),
                    z=float(parts[2]),
                    nx=float(parts[3]),
                    ny=float(parts[4]),
                    nz=float(parts[5])
                )
                mesh.vertices.append(vertex)
        
        return mesh


def export_skn_to_obj(mesh: SKNMesh, output_path: str, include_normals: bool = True):
    """
    Export SKN mesh to Wavefront OBJ format.
    
    Args:
        mesh: Parsed SKN mesh
        output_path: Path for .obj file
        include_normals: Include vertex normals
    """
    from pathlib import Path
    
    lines = []
    lines.append(f"# Exported from The Sims 1 SKN")
    lines.append(f"# Mesh: {mesh.mesh_name}")
    lines.append(f"# Texture: {mesh.texture_name}")
    lines.append(f"# Bones: {len(mesh.bone_names)}")
    lines.append("")
    
    # Material reference
    mtl_name = Path(output_path).stem
    lines.append(f"mtllib {mtl_name}.mtl")
    lines.append(f"usemtl {mtl_name}")
    lines.append("")
    
    # Vertices (negate X for coordinate system conversion)
    for v in mesh.vertices:
        lines.append(f"v {-v.x:.6f} {v.y:.6f} {v.z:.6f}")
    lines.append("")
    
    # Texture coordinates (flip V)
    for u, v in mesh.texture_coords:
        lines.append(f"vt {u:.6f} {1.0 - v:.6f}")
    lines.append("")
    
    # Normals
    if include_normals:
        for v in mesh.vertices:
            lines.append(f"vn {-v.nx:.6f} {v.ny:.6f} {v.nz:.6f}")
        lines.append("")
    
    # Faces (OBJ is 1-indexed)
    for i0, i1, i2 in mesh.faces:
        if include_normals:
            lines.append(f"f {i0+1}/{i0+1}/{i0+1} {i1+1}/{i1+1}/{i1+1} {i2+1}/{i2+1}/{i2+1}")
        else:
            lines.append(f"f {i0+1}/{i0+1} {i1+1}/{i1+1} {i2+1}/{i2+1}")
    
    # Write OBJ
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    
    # Write MTL
    mtl_path = Path(output_path).with_suffix('.mtl')
    mtl_lines = [
        f"# Material for {mesh.mesh_name}",
        f"newmtl {mtl_name}",
        "Ka 1.0 1.0 1.0",
        "Kd 1.0 1.0 1.0",
        "Ks 0.0 0.0 0.0",
        "d 1.0",
        f"map_Kd {mesh.texture_name}.bmp",
    ]
    with open(mtl_path, 'w') as f:
        f.write('\n'.join(mtl_lines))


# Test
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        reader = SKNReader()
        mesh = reader.read_file(sys.argv[1])
        if mesh:
            print(f"Mesh: {mesh.mesh_name}")
            print(f"Texture: {mesh.texture_name}")
            print(f"Bones: {len(mesh.bone_names)}")
            for i, bone in enumerate(mesh.bone_names):
                print(f"  {i}: {bone}")
            print(f"Faces: {mesh.face_count}")
            print(f"Vertices: {mesh.vertex_count}")
            print(f"UVs: {len(mesh.texture_coords)}")
            print(f"Bone bindings: {len(mesh.bone_bindings)}")
            print(f"Blend data: {len(mesh.blend_data)}")
            
            if len(sys.argv) > 2:
                export_skn_to_obj(mesh, sys.argv[2])
                print(f"Exported to {sys.argv[2]}")
