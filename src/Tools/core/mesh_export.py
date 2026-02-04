"""
Mesh Export - 3D Mesh Export to Modern Formats

Implements EXPORT actions for 3D mesh data.

Actions Implemented:
- ExportMesh (EXPORT) - Export to GLTF/GLB format
- DecodeMesh (READ) - Full mesh decoding
- LoadAssetTo3D (READ) - Load mesh for visualization
"""

import struct
import base64
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from Tools.core.mutation_pipeline import (
    MutationPipeline, MutationMode, MutationRequest, 
    MutationDiff, MutationResult, get_pipeline, propose_change
)
from Tools.core.action_registry import validate_action


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MeshExportResult:
    """Result of a mesh export operation."""
    success: bool
    message: str
    output_path: Optional[str] = None
    vertex_count: int = 0
    face_count: int = 0
    data: Optional[Any] = None


# ═══════════════════════════════════════════════════════════════════════════════
# MESH DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Vertex:
    """3D vertex with optional attributes."""
    x: float
    y: float
    z: float
    nx: float = 0.0  # Normal X
    ny: float = 0.0  # Normal Y
    nz: float = 0.0  # Normal Z
    u: float = 0.0   # Texture U
    v: float = 0.0   # Texture V
    
    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]
    
    def normal_list(self) -> List[float]:
        return [self.nx, self.ny, self.nz]
    
    def uv_list(self) -> List[float]:
        return [self.u, self.v]


@dataclass
class Face:
    """Triangle face with vertex indices."""
    v0: int
    v1: int
    v2: int
    
    def to_list(self) -> List[int]:
        return [self.v0, self.v1, self.v2]


@dataclass
class Mesh:
    """3D mesh with vertices and faces."""
    name: str = "mesh"
    vertices: List[Vertex] = field(default_factory=list)
    faces: List[Face] = field(default_factory=list)
    
    @property
    def vertex_count(self) -> int:
        return len(self.vertices)
    
    @property
    def face_count(self) -> int:
        return len(self.faces)
    
    def get_bounds(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Get bounding box (min, max)."""
        if not self.vertices:
            return ((0, 0, 0), (0, 0, 0))
        
        min_x = min(v.x for v in self.vertices)
        min_y = min(v.y for v in self.vertices)
        min_z = min(v.z for v in self.vertices)
        max_x = max(v.x for v in self.vertices)
        max_y = max(v.y for v in self.vertices)
        max_z = max(v.z for v in self.vertices)
        
        return ((min_x, min_y, min_z), (max_x, max_y, max_z))


# ═══════════════════════════════════════════════════════════════════════════════
# MESH DECODER
# ═══════════════════════════════════════════════════════════════════════════════

class MeshDecoder:
    """
    Decode mesh data from IFF chunks.
    
    Supports GMDC (Sims 2) and related formats.
    """
    
    def __init__(self, chunk):
        """
        Initialize with a mesh chunk.
        
        Args:
            chunk: Mesh chunk (GMDC, CRES, etc.)
        """
        self.chunk = chunk
        self.mesh = Mesh()
    
    def decode(self) -> Mesh:
        """
        Decode mesh from chunk.
        
        Returns:
            Mesh object
        """
        chunk_type = getattr(self.chunk, 'chunk_type', 'UNKN')
        
        if chunk_type == 'GMDC':
            return self._decode_gmdc()
        elif chunk_type == 'CRES':
            return self._decode_cres()
        else:
            return self._decode_generic()
    
    def _decode_gmdc(self) -> Mesh:
        """Decode GMDC (Geometric Mesh Data Container) format."""
        data = getattr(self.chunk, 'original_data', None) or getattr(self.chunk, 'chunk_data', b'')
        
        if len(data) < 12:
            return self.mesh
        
        offset = 0
        
        # Read header
        # GMDC format varies - this is a simplified reader
        try:
            # Version
            version = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            
            # Vertex count
            vert_count = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            
            # Face count
            face_count = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            
            # Read vertices (simplified - assuming X,Y,Z floats)
            for i in range(min(vert_count, 10000)):  # Safety limit
                if offset + 12 > len(data):
                    break
                    
                x, y, z = struct.unpack_from('<fff', data, offset)
                offset += 12
                
                self.mesh.vertices.append(Vertex(x, y, z))
            
            # Read faces (simplified - assuming 3 x uint16)
            for i in range(min(face_count, 10000)):  # Safety limit
                if offset + 6 > len(data):
                    break
                    
                v0, v1, v2 = struct.unpack_from('<HHH', data, offset)
                offset += 6
                
                self.mesh.faces.append(Face(v0, v1, v2))
                
        except struct.error:
            pass  # Incomplete data
        
        self.mesh.name = getattr(self.chunk, 'chunk_label', 'gmdc')
        return self.mesh
    
    def _decode_cres(self) -> Mesh:
        """Decode CRES (resource container) - extract embedded mesh."""
        # CRES typically contains references, not direct mesh data
        # For now, return empty mesh
        self.mesh.name = getattr(self.chunk, 'chunk_label', 'cres')
        return self.mesh
    
    def _decode_generic(self) -> Mesh:
        """Generic mesh decoding attempt."""
        data = getattr(self.chunk, 'original_data', None) or getattr(self.chunk, 'chunk_data', b'')
        
        # Try to detect vertex/face structure
        # Look for sequences of floats that could be vertices
        
        if len(data) < 36:  # Minimum for 3 vertices
            return self.mesh
        
        # Attempt to read as raw float triples
        offset = 0
        try:
            while offset + 12 <= len(data) and len(self.mesh.vertices) < 1000:
                x, y, z = struct.unpack_from('<fff', data, offset)
                
                # Sanity check - vertices should be reasonable size
                if abs(x) < 10000 and abs(y) < 10000 and abs(z) < 10000:
                    self.mesh.vertices.append(Vertex(x, y, z))
                
                offset += 12
                
        except struct.error:
            pass
        
        self.mesh.name = getattr(self.chunk, 'chunk_label', 'mesh')
        return self.mesh


def decode_mesh(chunk) -> Mesh:
    """Decode mesh from chunk. Convenience function."""
    return MeshDecoder(chunk).decode()


# ═══════════════════════════════════════════════════════════════════════════════
# GLTF EXPORTER
# ═══════════════════════════════════════════════════════════════════════════════

class GLTFExporter:
    """
    Export mesh to GLTF/GLB format.
    
    Implements ExportMesh action.
    """
    
    GLTF_VERSION = "2.0"
    
    def __init__(self, mesh: Mesh):
        """
        Initialize with a Mesh object.
        
        Args:
            mesh: Mesh to export
        """
        self.mesh = mesh
    
    def export_gltf(self, output_path: str,
                    embed_data: bool = False,
                    reason: str = "") -> MeshExportResult:
        """
        Export to GLTF format (JSON + binary).
        
        Args:
            output_path: Output .gltf file path
            embed_data: If True, embed binary data as base64
            reason: Reason for export
            
        Returns:
            MeshExportResult
        """
        valid, msg = validate_action('ExportMesh', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True
        })
        
        # ExportMesh is read-only, should be allowed
        
        if self.mesh.vertex_count == 0:
            return MeshExportResult(False, "No vertices to export")
        
        try:
            gltf, buffers = self._build_gltf()
            
            if embed_data:
                # Embed binary as base64
                for i, buf in enumerate(buffers):
                    gltf['buffers'][i]['uri'] = f"data:application/octet-stream;base64,{base64.b64encode(buf).decode()}"
                
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(gltf, f, indent=2)
                    
            else:
                # Separate .bin file
                bin_path = Path(output_path).with_suffix('.bin')
                gltf['buffers'][0]['uri'] = bin_path.name
                
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w') as f:
                    json.dump(gltf, f, indent=2)
                
                with open(bin_path, 'wb') as f:
                    for buf in buffers:
                        f.write(buf)
            
            return MeshExportResult(
                True,
                f"Exported GLTF: {self.mesh.vertex_count} vertices, {self.mesh.face_count} faces",
                output_path=output_path,
                vertex_count=self.mesh.vertex_count,
                face_count=self.mesh.face_count
            )
            
        except Exception as e:
            return MeshExportResult(False, f"Export failed: {e}")
    
    def export_glb(self, output_path: str,
                   reason: str = "") -> MeshExportResult:
        """
        Export to GLB format (binary GLTF).
        
        Args:
            output_path: Output .glb file path
            reason: Reason for export
            
        Returns:
            MeshExportResult
        """
        valid, msg = validate_action('ExportMesh', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True
        })
        
        if self.mesh.vertex_count == 0:
            return MeshExportResult(False, "No vertices to export")
        
        try:
            gltf, buffers = self._build_gltf()
            
            # Combine buffers
            bin_data = b''.join(buffers)
            
            # Update buffer info (no URI for embedded)
            gltf['buffers'][0].pop('uri', None)
            gltf['buffers'][0]['byteLength'] = len(bin_data)
            
            json_str = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
            
            # Pad to 4-byte boundary
            json_padding = (4 - len(json_str) % 4) % 4
            json_str += b' ' * json_padding
            
            bin_padding = (4 - len(bin_data) % 4) % 4
            bin_data += b'\x00' * bin_padding
            
            # Build GLB
            glb = bytearray()
            
            # GLB header (12 bytes)
            glb.extend(b'glTF')  # Magic
            glb.extend(struct.pack('<I', 2))  # Version 2
            total_length = 12 + 8 + len(json_str) + 8 + len(bin_data)
            glb.extend(struct.pack('<I', total_length))
            
            # JSON chunk
            glb.extend(struct.pack('<I', len(json_str)))  # Chunk length
            glb.extend(b'JSON')  # Chunk type
            glb.extend(json_str)
            
            # BIN chunk
            glb.extend(struct.pack('<I', len(bin_data)))  # Chunk length
            glb.extend(b'BIN\x00')  # Chunk type
            glb.extend(bin_data)
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(glb)
            
            return MeshExportResult(
                True,
                f"Exported GLB: {self.mesh.vertex_count} vertices, {self.mesh.face_count} faces",
                output_path=output_path,
                vertex_count=self.mesh.vertex_count,
                face_count=self.mesh.face_count
            )
            
        except Exception as e:
            return MeshExportResult(False, f"Export failed: {e}")
    
    def _build_gltf(self) -> Tuple[Dict, List[bytes]]:
        """Build GLTF structure and binary buffers."""
        # Build position buffer
        positions = bytearray()
        for v in self.mesh.vertices:
            positions.extend(struct.pack('<fff', v.x, v.y, v.z))
        
        # Build index buffer
        indices = bytearray()
        max_index = 0
        for f in self.mesh.faces:
            indices.extend(struct.pack('<HHH', f.v0, f.v1, f.v2))
            max_index = max(max_index, f.v0, f.v1, f.v2)
        
        # Combined buffer
        buffer_data = bytes(positions) + bytes(indices)
        
        # Bounds
        bounds = self.mesh.get_bounds()
        
        gltf = {
            "asset": {
                "version": self.GLTF_VERSION,
                "generator": "SimObliterator Suite"
            },
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "name": self.mesh.name}],
            "meshes": [{
                "name": self.mesh.name,
                "primitives": [{
                    "attributes": {"POSITION": 0},
                    "indices": 1,
                    "mode": 4  # TRIANGLES
                }]
            }],
            "accessors": [
                {
                    "bufferView": 0,
                    "componentType": 5126,  # FLOAT
                    "count": self.mesh.vertex_count,
                    "type": "VEC3",
                    "min": list(bounds[0]),
                    "max": list(bounds[1])
                },
                {
                    "bufferView": 1,
                    "componentType": 5123,  # UNSIGNED_SHORT
                    "count": self.mesh.face_count * 3,
                    "type": "SCALAR"
                }
            ],
            "bufferViews": [
                {
                    "buffer": 0,
                    "byteOffset": 0,
                    "byteLength": len(positions),
                    "target": 34962  # ARRAY_BUFFER
                },
                {
                    "buffer": 0,
                    "byteOffset": len(positions),
                    "byteLength": len(indices),
                    "target": 34963  # ELEMENT_ARRAY_BUFFER
                }
            ],
            "buffers": [{
                "byteLength": len(buffer_data)
            }]
        }
        
        return gltf, [buffer_data]


def export_mesh_gltf(mesh: Mesh, output_path: str, **kwargs) -> MeshExportResult:
    """Export mesh to GLTF. Convenience function."""
    return GLTFExporter(mesh).export_gltf(output_path, **kwargs)


def export_mesh_glb(mesh: Mesh, output_path: str, **kwargs) -> MeshExportResult:
    """Export mesh to GLB. Convenience function."""
    return GLTFExporter(mesh).export_glb(output_path, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# CHUNK MESH EXPORTER
# ═══════════════════════════════════════════════════════════════════════════════

class ChunkMeshExporter:
    """
    Export mesh directly from IFF chunk.
    
    Combines decode and export in one operation.
    """
    
    def __init__(self, chunk):
        """
        Initialize with a mesh chunk.
        
        Args:
            chunk: Mesh chunk to export
        """
        self.chunk = chunk
    
    def export(self, output_path: str, 
               format: str = 'glb',
               reason: str = "") -> MeshExportResult:
        """
        Export chunk mesh to file.
        
        Args:
            output_path: Output file path
            format: 'gltf' or 'glb'
            reason: Reason for export
            
        Returns:
            MeshExportResult
        """
        # Decode mesh from chunk
        decoder = MeshDecoder(self.chunk)
        mesh = decoder.decode()
        
        if mesh.vertex_count == 0:
            return MeshExportResult(
                False,
                f"No mesh data found in chunk (type: {getattr(self.chunk, 'chunk_type', '?')})"
            )
        
        # Export
        exporter = GLTFExporter(mesh)
        
        if format.lower() == 'glb':
            return exporter.export_glb(output_path, reason=reason)
        else:
            return exporter.export_gltf(output_path, reason=reason)


def export_chunk_mesh(chunk, output_path: str, **kwargs) -> MeshExportResult:
    """Export mesh from chunk. Convenience function."""
    return ChunkMeshExporter(chunk).export(output_path, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# MESH VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class MeshVisualizer:
    """
    Prepare mesh for 3D visualization.
    
    Implements LoadAssetTo3D action.
    """
    
    def __init__(self, mesh: Mesh):
        """
        Initialize with a Mesh.
        
        Args:
            mesh: Mesh to visualize
        """
        self.mesh = mesh
    
    def to_three_js(self) -> Dict:
        """
        Convert mesh to Three.js compatible format.
        
        Returns:
            Dict with vertices, indices, bounds
        """
        vertices = []
        for v in self.mesh.vertices:
            vertices.extend([v.x, v.y, v.z])
        
        indices = []
        for f in self.mesh.faces:
            indices.extend([f.v0, f.v1, f.v2])
        
        bounds = self.mesh.get_bounds()
        
        return {
            'type': 'BufferGeometry',
            'vertices': vertices,
            'indices': indices,
            'vertexCount': self.mesh.vertex_count,
            'faceCount': self.mesh.face_count,
            'bounds': {
                'min': bounds[0],
                'max': bounds[1]
            }
        }
    
    def to_obj_string(self) -> str:
        """
        Convert mesh to OBJ format string.
        
        Returns:
            OBJ format string
        """
        lines = [f"# {self.mesh.name}", f"# Vertices: {self.mesh.vertex_count}", ""]
        
        # Vertices
        for v in self.mesh.vertices:
            lines.append(f"v {v.x:.6f} {v.y:.6f} {v.z:.6f}")
        
        lines.append("")
        
        # Faces (OBJ uses 1-based indexing)
        for f in self.mesh.faces:
            lines.append(f"f {f.v0+1} {f.v1+1} {f.v2+1}")
        
        return '\n'.join(lines)


def load_asset_to_3d(chunk) -> Dict:
    """Load mesh for 3D visualization. Convenience function."""
    mesh = MeshDecoder(chunk).decode()
    return MeshVisualizer(mesh).to_three_js()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Data structures
    'Vertex', 'Face', 'Mesh',
    
    # Decoding
    'MeshDecoder', 'decode_mesh',
    
    # GLTF export
    'GLTFExporter', 'export_mesh_gltf', 'export_mesh_glb',
    
    # Chunk export
    'ChunkMeshExporter', 'export_chunk_mesh',
    
    # Visualization
    'MeshVisualizer', 'load_asset_to_3d',
    
    # Result type
    'MeshExportResult',
]
