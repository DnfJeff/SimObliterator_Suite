"""
GLTF Exporter - Export rigged meshes to glTF 2.0 format

Exports BMF meshes with BCF skeleton data to glTF (.gltf + .bin)
for use in Blender, Unity, Unreal, and other 3D tools.

Features:
  - Mesh geometry (vertices, normals, UVs)
  - Skeleton hierarchy with bone transforms
  - Bone skinning weights
  - Material references (texture placeholders)
  - Animation export (from CFP data)
"""

import json
import struct
import base64
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

from .bmf import BMFMesh, Vertex, TextureVertex, BoneBinding
from .bcf import BCF, Skeleton, Bone, Animation, Vector3, Quaternion


@dataclass
class GLTFExporter:
    """
    Export BMF meshes with BCF skeletons to glTF 2.0 format.
    
    Usage:
        exporter = GLTFExporter()
        exporter.export(mesh, skeleton, "character.gltf")
        
    With textures:
        exporter.export(mesh, skeleton, "character.gltf", texture_path="skin.bmp")
    """
    
    def __init__(self):
        self.buffer_data = bytearray()
        self.accessors: List[dict] = []
        self.buffer_views: List[dict] = []
        self.nodes: List[dict] = []
        self.meshes: List[dict] = []
        self.skins: List[dict] = []
        self.materials: List[dict] = []
        self.animations: List[dict] = []
        self.images: List[dict] = []
        self.textures: List[dict] = []
        self.samplers: List[dict] = []
        
        # Bone name to node index mapping
        self.bone_node_map: Dict[str, int] = {}
    
    def export(self, mesh: BMFMesh, skeleton: Optional[Skeleton] = None,
               filepath: str = "mesh.gltf", 
               animations: Optional[List[Animation]] = None,
               embed_buffer: bool = True,
               texture_path: Optional[str] = None):
        """
        Export mesh and optional skeleton to glTF file.
        
        Args:
            mesh: BMFMesh with geometry data
            skeleton: Optional Skeleton from BCF
            filepath: Output .gltf file path
            animations: Optional list of animations to include
            embed_buffer: If True, embed binary data as base64
            texture_path: Optional path to BMP texture file
        """
        self._reset()
        
        # Add texture/material if provided
        if texture_path:
            self._add_texture(texture_path)
        
        # Build skeleton nodes first (if present)
        skin_index = None
        if skeleton:
            skin_index = self._add_skeleton(skeleton)
        
        # Add mesh
        mesh_index = self._add_mesh(mesh, skeleton)
        
        # Create mesh node
        mesh_node = {
            "name": mesh.mesh_name or "Mesh",
            "mesh": mesh_index
        }
        if skin_index is not None:
            mesh_node["skin"] = skin_index
        
        mesh_node_index = len(self.nodes)
        self.nodes.append(mesh_node)
        
        # Add animations
        if animations and skeleton:
            for anim in animations:
                self._add_animation(anim, skeleton)
        
        # Build glTF document
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "SimObliterator Mesh Exporter"
            },
            "scene": 0,
            "scenes": [{"nodes": [mesh_node_index]}]
        }
        
        if self.nodes:
            gltf["nodes"] = self.nodes
        if self.meshes:
            gltf["meshes"] = self.meshes
        if self.accessors:
            gltf["accessors"] = self.accessors
        if self.buffer_views:
            gltf["bufferViews"] = self.buffer_views
        if self.materials:
            gltf["materials"] = self.materials
        if self.skins:
            gltf["skins"] = self.skins
        if self.animations:
            gltf["animations"] = self.animations
        if self.images:
            gltf["images"] = self.images
        if self.textures:
            gltf["textures"] = self.textures
        if self.samplers:
            gltf["samplers"] = self.samplers
        
        # Write buffer
        if embed_buffer:
            # Embed as base64 data URI
            b64_data = base64.b64encode(self.buffer_data).decode('ascii')
            gltf["buffers"] = [{
                "uri": f"data:application/octet-stream;base64,{b64_data}",
                "byteLength": len(self.buffer_data)
            }]
        else:
            # External .bin file
            bin_path = filepath.rsplit('.', 1)[0] + '.bin'
            gltf["buffers"] = [{
                "uri": bin_path.split('/')[-1].split('\\')[-1],
                "byteLength": len(self.buffer_data)
            }]
            with open(bin_path, 'wb') as f:
                f.write(self.buffer_data)
        
        # Write glTF JSON
        with open(filepath, 'w') as f:
            json.dump(gltf, f, indent=2)
    
    def _reset(self):
        """Reset exporter state."""
        self.buffer_data = bytearray()
        self.accessors = []
        self.buffer_views = []
        self.nodes = []
        self.meshes = []
        self.skins = []
        self.materials = []
        self.animations = []
        self.images = []
        self.textures = []
        self.samplers = []
        self.bone_node_map = {}
    
    def _add_texture(self, texture_path: str):
        """Add texture from BMP file.
        
        Embeds the BMP as a base64 data URI in the glTF.
        Note: glTF officially supports PNG/JPEG, but many viewers handle BMP.
        For best compatibility, convert BMP to PNG first.
        """
        import os
        from pathlib import Path
        
        if not os.path.exists(texture_path):
            return
        
        # Read texture data
        with open(texture_path, 'rb') as f:
            texture_data = f.read()
        
        # Embed as base64 data URI
        b64_data = base64.b64encode(texture_data).decode('ascii')
        
        # Determine mime type
        ext = Path(texture_path).suffix.lower()
        mime_types = {
            '.bmp': 'image/bmp',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg'
        }
        mime_type = mime_types.get(ext, 'image/bmp')
        
        # Add image
        image_index = len(self.images)
        self.images.append({
            "uri": f"data:{mime_type};base64,{b64_data}",
            "name": Path(texture_path).stem
        })
        
        # Add sampler (linear filtering)
        sampler_index = len(self.samplers)
        self.samplers.append({
            "magFilter": 9729,  # LINEAR
            "minFilter": 9987,  # LINEAR_MIPMAP_LINEAR
            "wrapS": 10497,     # REPEAT
            "wrapT": 10497      # REPEAT
        })
        
        # Add texture
        texture_index = len(self.textures)
        self.textures.append({
            "source": image_index,
            "sampler": sampler_index
        })
        
        # Add material with texture
        self.materials.append({
            "name": Path(texture_path).stem,
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": texture_index},
                "metallicFactor": 0.0,
                "roughnessFactor": 0.8
            }
        })
    
    def _add_skeleton(self, skeleton: Skeleton) -> int:
        """Add skeleton bones as nodes and create skin."""
        # Build hierarchy
        skeleton.build_hierarchy()
        
        # Create node for each bone
        joint_indices = []
        
        for bone in skeleton.bones:
            node = {
                "name": bone.name,
                "translation": [
                    -bone.translation.x,  # X negated per FreeSO
                    bone.translation.y,
                    bone.translation.z
                ],
                "rotation": [
                    bone.rotation.x,
                    bone.rotation.y, 
                    bone.rotation.z,
                    bone.rotation.w
                ]
            }
            
            node_index = len(self.nodes)
            self.nodes.append(node)
            self.bone_node_map[bone.name] = node_index
            joint_indices.append(node_index)
        
        # Set up parent-child relationships
        for bone in skeleton.bones:
            if bone.parent_name and bone.parent_name in self.bone_node_map:
                parent_idx = self.bone_node_map[bone.parent_name]
                child_idx = self.bone_node_map[bone.name]
                
                if "children" not in self.nodes[parent_idx]:
                    self.nodes[parent_idx]["children"] = []
                self.nodes[parent_idx]["children"].append(child_idx)
        
        # Create inverse bind matrices
        ibm_accessor = self._create_inverse_bind_matrices(skeleton)
        
        # Create skin
        skin = {
            "name": skeleton.name,
            "joints": joint_indices,
            "inverseBindMatrices": ibm_accessor
        }
        
        # Find root bone
        if skeleton.root_bone and skeleton.root_bone.name in self.bone_node_map:
            skin["skeleton"] = self.bone_node_map[skeleton.root_bone.name]
        
        skin_index = len(self.skins)
        self.skins.append(skin)
        
        return skin_index
    
    def _create_inverse_bind_matrices(self, skeleton: Skeleton) -> int:
        """Create inverse bind matrix accessor for skin."""
        matrices = []
        
        for bone in skeleton.bones:
            # Compute world transform
            mat = self._bone_to_matrix(bone)
            
            # Walk up hierarchy
            current = bone
            while current.parent_name:
                parent = skeleton.bone_by_name.get(current.parent_name)
                if parent:
                    parent_mat = self._bone_to_matrix(parent)
                    mat = self._mat4_multiply(parent_mat, mat)
                    current = parent
                else:
                    break
            
            # Invert for bind matrix
            inv_mat = self._mat4_invert(mat)
            matrices.extend(inv_mat)
        
        # Write to buffer
        return self._add_accessor(
            matrices,
            'MAT4',
            5126,  # FLOAT
            len(skeleton.bones)
        )
    
    def _bone_to_matrix(self, bone: Bone) -> List[float]:
        """Convert bone transform to 4x4 matrix (column-major)."""
        # Rotation quaternion to matrix
        q = bone.rotation
        
        xx = q.x * q.x
        yy = q.y * q.y
        zz = q.z * q.z
        xy = q.x * q.y
        xz = q.x * q.z
        yz = q.y * q.z
        wx = q.w * q.x
        wy = q.w * q.y
        wz = q.w * q.z
        
        # Rotation matrix (column-major for glTF)
        rot = [
            1 - 2 * (yy + zz), 2 * (xy + wz), 2 * (xz - wy), 0,
            2 * (xy - wz), 1 - 2 * (xx + zz), 2 * (yz + wx), 0,
            2 * (xz + wy), 2 * (yz - wx), 1 - 2 * (xx + yy), 0,
            -bone.translation.x, bone.translation.y, bone.translation.z, 1
        ]
        
        return rot
    
    def _mat4_multiply(self, a: List[float], b: List[float]) -> List[float]:
        """Multiply two 4x4 matrices (column-major)."""
        result = [0.0] * 16
        for col in range(4):
            for row in range(4):
                for k in range(4):
                    result[col * 4 + row] += a[k * 4 + row] * b[col * 4 + k]
        return result
    
    def _mat4_invert(self, m: List[float]) -> List[float]:
        """Invert a 4x4 matrix."""
        # Simplified - for proper inversion use numpy or full implementation
        # This handles basic transforms
        inv = [
            m[0], m[4], m[8], 0,
            m[1], m[5], m[9], 0,
            m[2], m[6], m[10], 0,
            0, 0, 0, 1
        ]
        
        # Invert translation
        tx = m[12]
        ty = m[13]
        tz = m[14]
        
        inv[12] = -(inv[0] * tx + inv[4] * ty + inv[8] * tz)
        inv[13] = -(inv[1] * tx + inv[5] * ty + inv[9] * tz)
        inv[14] = -(inv[2] * tx + inv[6] * ty + inv[10] * tz)
        
        return inv
    
    def _add_mesh(self, mesh: BMFMesh, skeleton: Optional[Skeleton] = None) -> int:
        """Add mesh geometry and return mesh index."""
        
        # Prepare vertex data
        positions = []
        normals = []
        texcoords = []
        
        pos_min = [float('inf')] * 3
        pos_max = [float('-inf')] * 3
        
        for v in mesh.vertices:
            # Negate X per FreeSO convention
            x, y, z = -v.x, v.y, v.z
            positions.extend([x, y, z])
            
            pos_min[0] = min(pos_min[0], x)
            pos_min[1] = min(pos_min[1], y)
            pos_min[2] = min(pos_min[2], z)
            pos_max[0] = max(pos_max[0], x)
            pos_max[1] = max(pos_max[1], y)
            pos_max[2] = max(pos_max[2], z)
            
            # Use actual normals (negate X for consistency)
            nx, ny, nz = -v.nx, v.ny, v.nz
            normals.extend([nx, ny, nz])
        
        for tc in mesh.texture_coords:
            # Support both tuple (u, v) and object (tc.u, tc.v)
            if isinstance(tc, tuple):
                u, v = tc
            else:
                u, v = tc.u, tc.v
            texcoords.extend([u, 1.0 - v])  # Flip V for glTF
        
        # Create accessors
        pos_accessor = self._add_accessor(
            positions, 'VEC3', 5126, len(mesh.vertices),
            min_val=pos_min, max_val=pos_max
        )
        
        norm_accessor = self._add_accessor(
            normals, 'VEC3', 5126, len(mesh.vertices)
        )
        
        uv_accessor = None
        if texcoords:
            uv_accessor = self._add_accessor(
                texcoords, 'VEC2', 5126, len(mesh.texture_coords)
            )
        
        # Indices
        indices = []
        for face in mesh.faces:
            # Support both tuple (i0, i1, i2) and object (face.a, face.b, face.c)
            if isinstance(face, tuple):
                indices.extend(face)
            else:
                indices.extend([face.a, face.b, face.c])
        
        idx_accessor = self._add_accessor(
            indices, 'SCALAR', 5123, len(indices), is_indices=True
        )
        
        # Build primitive
        primitive = {
            "attributes": {
                "POSITION": pos_accessor,
                "NORMAL": norm_accessor
            },
            "indices": idx_accessor
        }
        
        if uv_accessor is not None:
            primitive["attributes"]["TEXCOORD_0"] = uv_accessor
        
        # Add skinning weights if skeleton present
        if skeleton and mesh.bone_bindings:
            joints, weights = self._create_skin_data(mesh, skeleton)
            if joints:
                joints_accessor = self._add_accessor(
                    joints, 'VEC4', 5121, len(mesh.vertices)
                )
                weights_accessor = self._add_accessor(
                    weights, 'VEC4', 5126, len(mesh.vertices)
                )
                primitive["attributes"]["JOINTS_0"] = joints_accessor
                primitive["attributes"]["WEIGHTS_0"] = weights_accessor
        
        # Add material - use existing texture material if available, else create placeholder
        if self.materials:
            primitive["material"] = 0  # Use first material (from _add_texture)
        elif mesh.texture_name:
            mat_idx = self._add_material(mesh.texture_name)
            primitive["material"] = mat_idx
        
        gltf_mesh = {
            "name": mesh.mesh_name or "Mesh",
            "primitives": [primitive]
        }
        
        mesh_index = len(self.meshes)
        self.meshes.append(gltf_mesh)
        
        return mesh_index
    
    def _create_skin_data(self, mesh: BMFMesh, skeleton: Skeleton) -> Tuple[List, List]:
        """Create joint indices and weights for skinning.
        
        The mesh has:
        - bone_names: List of bone name strings
        - bone_bindings: List of BoneBinding with bone_index (into bone_names)
        - vertices: Real vertices
        - blend_data: Blend weights for multi-bone influence
        
        We need to map mesh bones -> skeleton joint indices.
        """
        # Build mesh bone name -> skeleton joint index map
        skeleton_joint_map = {}
        for skel_idx, bone in enumerate(skeleton.bones):
            skeleton_joint_map[bone.name.upper()] = skel_idx
        
        # Map mesh bone index -> skeleton joint index
        mesh_to_skel = {}
        for mesh_idx, bone_name in enumerate(mesh.bone_names):
            skel_idx = skeleton_joint_map.get(bone_name.upper(), 0)
            mesh_to_skel[mesh_idx] = skel_idx
        
        # Initialize per-vertex joint/weight arrays
        num_verts = len(mesh.vertices)
        joints = [[0, 0, 0, 0] for _ in range(num_verts)]
        weights = [[0.0, 0.0, 0.0, 0.0] for _ in range(num_verts)]
        
        # Assign joints from bone bindings (real vertices)
        for binding in mesh.bone_bindings:
            skel_joint = mesh_to_skel.get(binding.bone_index, 0)
            start = binding.first_real_vertex
            count = binding.real_vertex_count
            
            for i in range(start, min(start + count, num_verts)):
                joints[i][0] = skel_joint
                weights[i][0] = 1.0
        
        # Apply blend data for smooth skinning
        if mesh.blend_data:
            for i, blend in enumerate(mesh.blend_data):
                if i < num_verts:
                    # Weight for primary bone
                    weights[i][0] = blend.weight
                    # Blend with other vertex's bone
                    if blend.other_vertex < num_verts:
                        joints[i][1] = joints[blend.other_vertex][0]
                        weights[i][1] = 1.0 - blend.weight
        
        # Flatten to lists
        flat_joints = []
        flat_weights = []
        for j, w in zip(joints, weights):
            flat_joints.extend(j)
            flat_weights.extend(w)
        
        return flat_joints, flat_weights
    
    def _add_material(self, texture_name: str) -> int:
        """Add a material with texture reference."""
        material = {
            "name": texture_name,
            "pbrMetallicRoughness": {
                "baseColorFactor": [1, 1, 1, 1],
                "metallicFactor": 0,
                "roughnessFactor": 0.5
            }
        }
        
        mat_index = len(self.materials)
        self.materials.append(material)
        return mat_index
    
    def _add_animation(self, anim: Animation, skeleton: Skeleton):
        """Add animation to glTF."""
        if not anim.translations and not anim.rotations:
            return
        
        samplers = []
        channels = []
        
        # Time accessor (shared)
        times = [i / 30.0 for i in range(int(anim.duration * 30))]  # 30 FPS
        if not times:
            return
        
        time_accessor = self._add_accessor(
            times, 'SCALAR', 5126, len(times),
            min_val=[times[0]], max_val=[times[-1]]
        )
        
        # Add samplers for each animated bone
        frame_idx = 0
        for motion in anim.motions:
            bone_name = motion.bone_name if hasattr(motion, 'bone_name') else None
            if not bone_name or bone_name not in self.bone_node_map:
                continue
            
            node_idx = self.bone_node_map[bone_name]
            
            if motion.has_translation and anim.translations:
                # Translation sampler
                trans_data = []
                for i in range(motion.frame_count):
                    if frame_idx + i < len(anim.translations):
                        t = anim.translations[frame_idx + i]
                        trans_data.extend([-t.x, t.y, t.z])
                
                if trans_data:
                    trans_accessor = self._add_accessor(
                        trans_data, 'VEC3', 5126, motion.frame_count
                    )
                    
                    sampler_idx = len(samplers)
                    samplers.append({
                        "input": time_accessor,
                        "output": trans_accessor,
                        "interpolation": "LINEAR"
                    })
                    
                    channels.append({
                        "sampler": sampler_idx,
                        "target": {
                            "node": node_idx,
                            "path": "translation"
                        }
                    })
            
            if motion.has_rotation and anim.rotations:
                # Rotation sampler
                rot_data = []
                for i in range(motion.frame_count):
                    if frame_idx + i < len(anim.rotations):
                        q = anim.rotations[frame_idx + i]
                        rot_data.extend([q.x, q.y, q.z, q.w])
                
                if rot_data:
                    rot_accessor = self._add_accessor(
                        rot_data, 'VEC4', 5126, motion.frame_count
                    )
                    
                    sampler_idx = len(samplers)
                    samplers.append({
                        "input": time_accessor,
                        "output": rot_accessor,
                        "interpolation": "LINEAR"
                    })
                    
                    channels.append({
                        "sampler": sampler_idx,
                        "target": {
                            "node": node_idx,
                            "path": "rotation"
                        }
                    })
            
            frame_idx += motion.frame_count
        
        if samplers and channels:
            self.animations.append({
                "name": anim.name,
                "samplers": samplers,
                "channels": channels
            })
    
    def _add_accessor(self, data: List, accessor_type: str, 
                      component_type: int, count: int,
                      min_val: List = None, max_val: List = None,
                      is_indices: bool = False) -> int:
        """Add data to buffer and create accessor."""
        
        # Align buffer
        alignment = 4
        while len(self.buffer_data) % alignment:
            self.buffer_data.append(0)
        
        byte_offset = len(self.buffer_data)
        
        # Write data based on type
        if component_type == 5126:  # FLOAT
            for val in data:
                self.buffer_data.extend(struct.pack('<f', float(val)))
        elif component_type == 5123:  # UNSIGNED_SHORT
            for val in data:
                self.buffer_data.extend(struct.pack('<H', int(val)))
        elif component_type == 5121:  # UNSIGNED_BYTE
            for val in data:
                self.buffer_data.append(int(val) & 0xFF)
        
        byte_length = len(self.buffer_data) - byte_offset
        
        # Create buffer view
        view = {
            "buffer": 0,
            "byteOffset": byte_offset,
            "byteLength": byte_length
        }
        
        if is_indices:
            view["target"] = 34963  # ELEMENT_ARRAY_BUFFER
        else:
            view["target"] = 34962  # ARRAY_BUFFER
        
        view_index = len(self.buffer_views)
        self.buffer_views.append(view)
        
        # Create accessor
        accessor = {
            "bufferView": view_index,
            "componentType": component_type,
            "count": count,
            "type": accessor_type
        }
        
        if min_val:
            accessor["min"] = min_val
        if max_val:
            accessor["max"] = max_val
        
        accessor_index = len(self.accessors)
        self.accessors.append(accessor)
        
        return accessor_index


def export_character_gltf(mesh: BMFMesh, bcf: BCF, 
                          filepath: str,
                          animations: Optional[List[Animation]] = None):
    """
    Convenience function to export a complete character.
    
    Args:
        mesh: BMFMesh with geometry
        bcf: BCF with skeleton and optional animations
        filepath: Output .gltf path
        animations: Optional animations (from BCF or with CFP data)
    """
    skeleton = bcf.skeletons[0] if bcf.skeletons else None
    anims = animations or bcf.animations
    
    exporter = GLTFExporter()
    exporter.export(mesh, skeleton, filepath, anims)


# Test
if __name__ == "__main__":
    from .bmf import Vertex, TextureVertex, BMFMesh
    from .bcf import Bone, Skeleton, Vector3, Quaternion
    
    # Create simple test mesh (triangle)
    mesh = BMFMesh(
        mesh_name="TestTriangle",
        texture_name="test.bmp"
    )
    mesh.vertices = [
        Vertex(0, 0, 0),
        Vertex(1, 0, 0),
        Vertex(0.5, 1, 0)
    ]
    mesh.texture_coords = [
        TextureVertex(0, 0),
        TextureVertex(1, 0),
        TextureVertex(0.5, 1)
    ]
    
    @dataclass
    class Face:
        a: int
        b: int
        c: int
    
    mesh.faces = [Face(0, 1, 2)]
    
    # Export
    exporter = GLTFExporter()
    exporter.export(mesh, None, "test_triangle.gltf")
    print("Exported test_triangle.gltf")
