"""
Mesh formats package for The Sims 1

Modules:
  - bmf: BMF mesh parser (vertices, faces, UVs, bone bindings)
  - bcf: BCF skeleton/animation parser (bones, appearances, anim headers)
  - cfp: CFP animation frame decompressor (delta-encoded floats)
  - gltf_export: Export rigged meshes to glTF 2.0 format

Usage:
    from formats.mesh import BMFReader, BCFReader, CFPReader, GLTFExporter
    
    # Load a mesh
    mesh_reader = BMFReader()
    mesh = mesh_reader.read_file("bodies/adult_female.bmf")
    mesh_reader.export_obj(mesh, "exported/female.obj")
    
    # Load a skeleton
    bcf_reader = BCFReader()
    bcf = bcf_reader.read_file("skeletons/adult.bcf")
    print(f"Skeleton: {bcf.skeletons[0].name}")
    print(f"Bones: {[b.name for b in bcf.skeletons[0].bones]}")
    
    # Decompress animation data
    cfp_reader = CFPReader()
    cfp_data = cfp_reader.read_file("animations.cfp")
    translations = cfp_reader.decompress_vectors(cfp_data, frame_count, offset)
    
    # Export rigged mesh to glTF
    from formats.mesh import export_character_gltf
    export_character_gltf(mesh, bcf, "character.gltf")
"""

from .bmf import BMFMesh, BMFReader, BoneBinding, BlendData, Vertex, TextureVertex
from .bcf import BCF, BCFReader, Skeleton, Bone, Animation, Binding, Appearance
from .bcf import Vector3, Quaternion
from .cfp import CFPReader, CFPData, compress_floats
from .gltf_export import GLTFExporter, export_character_gltf

__all__ = [
    # BMF
    'BMFMesh', 'BMFReader', 'BoneBinding', 'BlendData', 'Vertex', 'TextureVertex',
    # BCF
    'BCF', 'BCFReader', 'Skeleton', 'Bone', 'Animation', 'Binding', 'Appearance',
    # CFP
    'CFPReader', 'CFPData', 'compress_floats',
    # GLTF Export
    'GLTFExporter', 'export_character_gltf',
    # Shared
    'Vector3', 'Quaternion',
]
