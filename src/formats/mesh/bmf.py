"""
BMF Mesh Parser - Binary Mesh Format for The Sims 1

Parses .bmf files (compiled SKN meshes) for character/object rendering.
Based on FreeSO's SKNCodec.cs and TheSimsOpenTechDoc Part IV.

BMF Structure:
  1. FILENAMES - mesh name, texture name
  2. BONES - bone name list  
  3. FACES - triangle indices
  4. BONEBINDINGS - vertex-to-bone assignments
  5. TEXTUREVERTICES - UV coordinates
  6. BLENDDATA - vertex blend weights
  7. VERTICES - positions and normals
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional, BinaryIO
from io import BytesIO


@dataclass
class BoneBinding:
    """Maps vertices to a bone for skeletal animation."""
    bone_index: int = 0
    first_real_vertex: int = 0
    real_vertex_count: int = 0
    first_blend_vertex: int = 0
    blend_vertex_count: int = 0


@dataclass
class BlendData:
    """Blend weight for smooth bone transitions."""
    weight: float = 0.0
    other_vertex: int = 0  # Index of vertex to blend with


@dataclass
class Vertex:
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
class TextureVertex:
    """UV texture coordinate."""
    u: float = 0.0
    v: float = 0.0


@dataclass
class BMFMesh:
    """
    Complete BMF mesh data structure.
    
    Ready for export to OBJ, GLTF, or rendering.
    """
    # Metadata
    mesh_name: str = ""
    texture_name: str = ""
    
    # Skeleton reference
    bone_names: List[str] = field(default_factory=list)
    
    # Geometry
    faces: List[Tuple[int, int, int]] = field(default_factory=list)  # Triangle indices
    vertices: List[Vertex] = field(default_factory=list)  # Real vertices
    blend_vertices: List[Vertex] = field(default_factory=list)  # Blended vertices
    texture_coords: List[TextureVertex] = field(default_factory=list)  # UVs
    
    # Rigging
    bone_bindings: List[BoneBinding] = field(default_factory=list)
    blend_data: List[BlendData] = field(default_factory=list)
    
    @property
    def vertex_count(self) -> int:
        return len(self.vertices) + len(self.blend_vertices)
    
    @property
    def face_count(self) -> int:
        return len(self.faces)
    
    def get_all_vertices(self) -> List[Vertex]:
        """Get combined real + blend vertices."""
        return self.vertices + self.blend_vertices


class BMFReader:
    """
    Parser for BMF (Binary Mesh Format) files.
    
    Usage:
        reader = BMFReader()
        mesh = reader.read_file("body.bmf")
        # or
        mesh = reader.read_bytes(data)
    """
    
    def __init__(self):
        self.pos = 0
        self.data = b""
    
    def read_file(self, filepath: str) -> Optional[BMFMesh]:
        """Read BMF from file."""
        with open(filepath, 'rb') as f:
            return self.read_bytes(f.read())
    
    def read_bytes(self, data: bytes) -> Optional[BMFMesh]:
        """Read BMF from byte buffer."""
        self.data = data
        self.pos = 0
        
        try:
            return self._parse()
        except Exception as e:
            print(f"Error parsing BMF: {e}")
            return None
    
    def _parse(self) -> BMFMesh:
        """Parse complete BMF structure."""
        mesh = BMFMesh()
        
        # 1. FILENAMES
        mesh.mesh_name = self._read_pascal_string()
        mesh.texture_name = self._read_pascal_string()
        
        # 2. BONES
        bone_count = self._read_int32()
        mesh.bone_names = [self._read_pascal_string() for _ in range(bone_count)]
        
        # 3. FACES
        face_count = self._read_int32()
        mesh.faces = []
        for _ in range(face_count):
            # Counter-clockwise winding
            i0 = self._read_int32()
            i1 = self._read_int32()
            i2 = self._read_int32()
            mesh.faces.append((i0, i1, i2))
        
        # 4. BONE BINDINGS
        binding_count = self._read_int32()
        mesh.bone_bindings = []
        for _ in range(binding_count):
            bb = BoneBinding()
            bb.bone_index = self._read_int32()
            bb.first_real_vertex = self._read_int32()
            bb.real_vertex_count = self._read_int32()
            bb.first_blend_vertex = self._read_int32()
            bb.blend_vertex_count = self._read_int32()
            mesh.bone_bindings.append(bb)
        
        # 5. TEXTURE VERTICES (UVs)
        uv_count = self._read_int32()
        mesh.texture_coords = []
        for _ in range(uv_count):
            tv = TextureVertex()
            tv.u = self._read_float()
            tv.v = self._read_float()
            mesh.texture_coords.append(tv)
        
        # 6. BLEND DATA
        blend_count = self._read_int32()
        mesh.blend_data = []
        for _ in range(blend_count):
            bd = BlendData()
            # Weight is fixed-point int32: 0x8000 = 1.0 (per VitaMoo)
            bd.weight = self._read_int32() / 0x8000
            bd.other_vertex = self._read_int32()
            mesh.blend_data.append(bd)
        
        # 7. VERTICES (real)
        real_count = self._read_int32()
        mesh.vertices = []
        for _ in range(real_count):
            v = self._read_vertex()
            mesh.vertices.append(v)
        
        # 8. VERTICES (blend)
        # Blend vertex count may not be explicitly stored
        # Read remaining as blend vertices
        blend_vert_count = blend_count  # Same as blend data count
        mesh.blend_vertices = []
        for _ in range(blend_vert_count):
            if self.pos + 24 > len(self.data):
                break
            v = self._read_vertex()
            mesh.blend_vertices.append(v)
        
        return mesh
    
    def _read_vertex(self) -> Vertex:
        """Read a vertex (position + normal).
        
        Per VitaMoo: read raw values, no coordinate transforms in BMF.
        """
        v = Vertex()
        v.x = self._read_float()
        v.y = self._read_float()
        v.z = self._read_float()
        v.nx = self._read_float()
        v.ny = self._read_float()
        v.nz = self._read_float()
        return v
    
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
    
    def _reinterpret_as_float(self, val: int) -> float:
        """Reinterpret int bits as float."""
        return struct.unpack('<f', struct.pack('<i', val))[0]


def export_obj(mesh: BMFMesh, output_path: str, include_normals: bool = True):
    """
    Export BMF mesh to Wavefront OBJ format.
    
    Args:
        mesh: Parsed BMF mesh
        output_path: Path for .obj file
        include_normals: Include vertex normals
    """
    lines = []
    lines.append(f"# Exported from The Sims 1 BMF")
    lines.append(f"# Mesh: {mesh.mesh_name}")
    lines.append(f"# Texture: {mesh.texture_name}")
    lines.append("")
    
    # Material reference
    mtl_name = Path(output_path).stem
    lines.append(f"mtllib {mtl_name}.mtl")
    lines.append(f"usemtl {mtl_name}")
    lines.append("")
    
    # Vertices
    all_verts = mesh.get_all_vertices()
    for v in all_verts:
        lines.append(f"v {v.x:.6f} {v.y:.6f} {v.z:.6f}")
    lines.append("")
    
    # Texture coordinates
    for uv in mesh.texture_coords:
        # Flip V for OBJ convention
        lines.append(f"vt {uv.u:.6f} {1.0 - uv.v:.6f}")
    lines.append("")
    
    # Normals
    if include_normals:
        for v in all_verts:
            lines.append(f"vn {v.nx:.6f} {v.ny:.6f} {v.nz:.6f}")
        lines.append("")
    
    # Faces (OBJ is 1-indexed)
    for i0, i1, i2 in mesh.faces:
        if include_normals:
            # f v/vt/vn v/vt/vn v/vt/vn
            lines.append(f"f {i0+1}/{i0+1}/{i0+1} {i1+1}/{i1+1}/{i1+1} {i2+1}/{i2+1}/{i2+1}")
        else:
            # f v/vt v/vt v/vt
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
        f"map_Kd {mesh.texture_name}",
    ]
    with open(mtl_path, 'w') as f:
        f.write('\n'.join(mtl_lines))


# Test
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        reader = BMFReader()
        mesh = reader.read_file(sys.argv[1])
        if mesh:
            print(f"Mesh: {mesh.mesh_name}")
            print(f"Texture: {mesh.texture_name}")
            print(f"Bones: {len(mesh.bone_names)}")
            print(f"Faces: {mesh.face_count}")
            print(f"Vertices: {mesh.vertex_count}")
            print(f"UVs: {len(mesh.texture_coords)}")
            
            if len(sys.argv) > 2:
                export_obj(mesh, sys.argv[2])
                print(f"Exported to {sys.argv[2]}")
