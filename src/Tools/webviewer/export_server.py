"""
Export Server - Flask API for exporting meshes and characters to glTF.

Run with: python export_server.py
Then access the library browser at http://localhost:5000/library_browser.html
"""

import sys
import os
import json
import traceback
import base64
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from formats.mesh.bmf import BMFReader
from formats.mesh.skn import SKNReader
from formats.mesh.bcf import BCFReader
from formats.mesh.cmx import CMXReader, CharacterAssembler
from formats.mesh.gltf_export import GLTFExporter, export_character_gltf
from formats.far.far1 import FAR1Archive

app = Flask(__name__, static_folder='.')
CORS(app)

# Configure paths
GAME_ROOT = Path(r"G:\SteamLibrary\steamapps\common\The Sims Legacy Collection")
EXPORT_DIR = Path(__file__).parent / "exports"
EXPORT_DIR.mkdir(exist_ok=True)


# Default search paths
DEFAULT_MESH_SEARCH_PATHS = [
    GAME_ROOT / "GameData" / "Skins",
    GAME_ROOT / "Deluxe" / "Skins",
    GAME_ROOT / "Downloads",
    GAME_ROOT / "ExpansionPack2" / "Skins",
    GAME_ROOT / "ExpansionShared" / "SkinsBuy",
]
DEFAULT_FAR_ARCHIVE_PATHS = [
    GAME_ROOT / "GameData" / "Skins" / "Skins.far",
    GAME_ROOT / "ExpansionPack" / "ExpansionPack.far",
    GAME_ROOT / "ExpansionPack2" / "ExpansionPack2.far",
    GAME_ROOT / "ExpansionPack3" / "ExpansionPack3.far",
    GAME_ROOT / "ExpansionPack4" / "ExpansionPack4.far",
    GAME_ROOT / "ExpansionPack5" / "ExpansionPack5.far",
    GAME_ROOT / "ExpansionPack6" / "ExpansionPack6.far", 
    GAME_ROOT / "ExpansionPack7" / "ExpansionPack7.far",
    GAME_ROOT / "ExpansionShared" / "ExpansionShared.far",
]

# Mutable search paths (can be set by API)
MESH_SEARCH_PATHS = list(DEFAULT_MESH_SEARCH_PATHS)
FAR_ARCHIVE_PATHS = list(DEFAULT_FAR_ARCHIVE_PATHS)
# API to set search paths
@app.route('/api/config', methods=['POST'])
def set_config():
    """Set search paths for mesh and FAR archive scanning."""
    global MESH_SEARCH_PATHS, FAR_ARCHIVE_PATHS
    data = request.json or {}
    mesh_dirs = data.get('mesh_dirs')
    far_archives = data.get('far_archives')
    # Accept both string and list
    if mesh_dirs:
        if isinstance(mesh_dirs, str):
            mesh_dirs = [mesh_dirs]
        MESH_SEARCH_PATHS = [Path(p) for p in mesh_dirs]
    if far_archives:
        if isinstance(far_archives, str):
            far_archives = [far_archives]
        FAR_ARCHIVE_PATHS = [Path(p) for p in far_archives]
    return jsonify({'success': True, 'mesh_dirs': [str(p) for p in MESH_SEARCH_PATHS], 'far_archives': [str(p) for p in FAR_ARCHIVE_PATHS]})

# Cache loaded FAR archives
_far_cache: dict[str, FAR1Archive] = {}

def get_far_archive(path: Path) -> FAR1Archive | None:
    """Get a cached FAR archive or load it."""
    path_str = str(path)
    if path_str not in _far_cache:
        if path.exists():
            try:
                _far_cache[path_str] = FAR1Archive(path_str)
            except Exception as e:
                print(f"Failed to load FAR archive {path}: {e}")
                return None
        else:
            return None
    return _far_cache.get(path_str)

# Skeleton paths
SKELETON_PATH = GAME_ROOT / "GameData" / "Skins"
ANIMATION_FAR = GAME_ROOT / "GameData" / "Animation" / "Animation.far"


def find_mesh_file(mesh_name: str) -> tuple[Path | bytes, bool, str] | None:
    """
    Find a mesh file by name. 
    Returns (path_or_data, is_skn, source) or None.
    - path_or_data: Path object for loose files, bytes for FAR-extracted files
    - is_skn: True if SKN format, False if BMF
    - source: Description of where the file was found
    """
    # Remove any file extension from mesh_name
    base_name = Path(mesh_name).stem
    
    # Clean up mesh name - remove common prefixes/suffixes
    clean_name = base_name.replace('xskin-', '').replace('-PELVIS-BODY', '').replace('-HEAD-HEAD', '')
    
    # 1. First search loose files in directories
    for search_path in MESH_SEARCH_PATHS:
        if not search_path.exists():
            continue
        
        # Try exact match first
        for ext in ['.bmf', '.skn']:
            exact_path = search_path / f"{base_name}{ext}"
            if exact_path.exists():
                return (exact_path, ext == '.skn', f"Loose: {search_path.name}")
        
        # Try with xskin- prefix for SKN files (The Sims naming convention)
        skn_path = search_path / f"xskin-{base_name}-PELVIS-BODY.skn"
        if skn_path.exists():
            return (skn_path, True, f"Loose: {search_path.name}")
        
        skn_path = search_path / f"xskin-{clean_name}-PELVIS-BODY.skn"
        if skn_path.exists():
            return (skn_path, True, f"Loose: {search_path.name}")
        
        # Try head mesh pattern
        head_path = search_path / f"xskin-{base_name}-HEAD-HEAD.skn"
        if head_path.exists():
            return (head_path, True, f"Loose: {search_path.name}")
        
        head_path = search_path / f"xskin-{clean_name}-HEAD-HEAD.skn"
        if head_path.exists():
            return (head_path, True, f"Loose: {search_path.name}")
        
        # Case-insensitive pattern search
        search_patterns = [f"*{base_name}*.*", f"*{clean_name}*.*"]
        for pattern in search_patterns:
            for file in search_path.glob(pattern):
                if file.suffix.lower() in ['.bmf', '.skn']:
                    return (file, file.suffix.lower() == '.skn', f"Loose: {search_path.name}")
    
    # 2. Search FAR archives
    search_names = [
        base_name,
        clean_name,
        f"xskin-{base_name}-PELVIS-BODY",
        f"xskin-{clean_name}-PELVIS-BODY",
        f"xskin-{base_name}-HEAD-HEAD",
        f"xskin-{clean_name}-HEAD-HEAD",
    ]
    
    for far_path in FAR_ARCHIVE_PATHS:
        far = get_far_archive(far_path)
        if not far:
            continue
        
        for entry in far.entries:
            entry_name = entry.filename.lower()
            entry_stem = Path(entry.filename).stem.lower()
            
            # Check if this entry matches any of our search names
            for search_name in search_names:
                if search_name.lower() in entry_name or entry_stem == search_name.lower():
                    if entry.filename.lower().endswith('.skn') or entry.filename.lower().endswith('.bmf'):
                        # Extract the file data
                        data = far.get_entry(entry.filename)
                        if data:
                            is_skn = entry.filename.lower().endswith('.skn')
                            return (data, is_skn, f"FAR: {far_path.name}")
    
    return None


def find_skeleton(gender: str = 'adult') -> Path | bytes | None:
    """Find the skeleton BCF file. Returns Path for loose files, bytes for FAR-extracted."""
    skeleton_names = [
        "skeleton.cmx.bcf",
        "adult-skeleton.cmx.bcf", 
        "skeleton.bcf",
        "skeleton-adult.bcf",
    ]
    
    # 1. Search loose files first
    for skel_name in skeleton_names:
        skel_path = SKELETON_PATH / skel_name
        if skel_path.exists():
            return skel_path
    
    # Search more broadly in directories
    for search_path in MESH_SEARCH_PATHS:
        if search_path.exists():
            for bcf in search_path.glob("*skeleton*.bcf"):
                return bcf
    
    # 2. Search Animation.far first (this is where skeletons are)
    if ANIMATION_FAR.exists():
        far = get_far_archive(ANIMATION_FAR)
        if far:
            for entry in far.entries:
                entry_lower = entry.filename.lower()
                if 'skeleton' in entry_lower and entry_lower.endswith('.bcf'):
                    data = far.get_entry(entry.filename)
                    if data:
                        print(f"Found skeleton in Animation.far: {entry.filename}")
                        return data
    
    # 3. Search other FAR archives
    for far_path in FAR_ARCHIVE_PATHS:
        far = get_far_archive(far_path)
        if not far:
            continue
        
        for entry in far.entries:
            entry_lower = entry.filename.lower()
            if 'skeleton' in entry_lower and entry_lower.endswith('.bcf'):
                data = far.get_entry(entry.filename)
                if data:
                    print(f"Found skeleton in FAR: {far_path.name}/{entry.filename}")
                    return data
    
    return None


def find_texture(mesh, search_paths: list[Path]) -> Path | bytes | None:
    """Find texture file for a mesh. Returns Path for loose files, bytes for FAR-extracted."""
    if not hasattr(mesh, 'texture_name') or not mesh.texture_name:
        return None
    
    tex_name = mesh.texture_name
    extensions = ['.bmp', '.tga', '.png', '.BMP', '.TGA', '.PNG']
    
    # 1. Search loose files first
    for search_dir in search_paths:
        if not search_dir.exists():
            continue
        for ext in extensions:
            for name in [tex_name, tex_name.lower(), tex_name.upper()]:
                tex_path = search_dir / f"{name}{ext}"
                if tex_path.exists():
                    return tex_path
    
    # 2. Search FAR archives
    tex_name_lower = tex_name.lower()
    for far_path in FAR_ARCHIVE_PATHS:
        far = get_far_archive(far_path)
        if not far:
            continue
        
        for entry in far.entries:
            entry_lower = entry.filename.lower()
            entry_stem = Path(entry.filename).stem.lower()
            
            # Check if this is a texture file with matching name
            if entry_stem == tex_name_lower:
                if any(entry_lower.endswith(ext.lower()) for ext in extensions):
                    data = far.get_entry(entry.filename)
                    if data:
                        print(f"Found texture in FAR: {far_path.name}/{entry.filename}")
                        return data
    
    return None


# === API Endpoints ===

@app.route('/')
def index():
    return send_from_directory('.', 'library_browser.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)


@app.route('/exports/<path:filename>')
def serve_export(filename):
    return send_from_directory(str(EXPORT_DIR), filename)


@app.route('/api/export/mesh', methods=['POST'])
def export_mesh():
    """Export a mesh to glTF format."""
    try:
        data = request.json
        mesh_name = data.get('mesh_name')
        include_skeleton = data.get('include_skeleton', True)
        
        if not mesh_name:
            return jsonify({'error': 'mesh_name required'}), 400
        
        # Find the mesh file
        result = find_mesh_file(mesh_name)
        if not result:
            return jsonify({
                'error': f'Mesh file not found: {mesh_name}',
                'searched': [str(p) for p in MESH_SEARCH_PATHS if p.exists()],
                'far_archives': [str(p) for p in FAR_ARCHIVE_PATHS if p.exists()]
            }), 404
        
        path_or_data, is_skn, source = result
        
        # Read mesh - handle both Path objects and bytes data
        mesh = None
        if is_skn:
            reader = SKNReader()
            if isinstance(path_or_data, bytes):
                # From FAR archive - decode bytes to string for SKN (text format)
                mesh = reader.read_string(path_or_data.decode('latin-1'))
            else:
                mesh = reader.read_file(str(path_or_data))
            if not mesh:
                return jsonify({'error': f'Failed to read SKN from {source}'}), 500
        else:
            reader = BMFReader()
            if isinstance(path_or_data, bytes):
                # From FAR archive - BMF is binary
                mesh = reader.read_bytes(path_or_data)
            else:
                mesh = reader.read_file(str(path_or_data))
            if not mesh:
                return jsonify({'error': f'Failed to read BMF from {source}'}), 500
        
        # Find and load skeleton
        skeleton = None
        if include_skeleton:
            skel_result = find_skeleton()
            if skel_result:
                try:
                    bcf_reader = BCFReader()
                    if isinstance(skel_result, bytes):
                        bcf = bcf_reader.read_bytes(skel_result)
                    else:
                        bcf = bcf_reader.read_file(str(skel_result))
                    if bcf and bcf.skeletons:
                        skeleton = bcf.skeletons[0]
                except Exception as e:
                    print(f"Warning: Could not load skeleton: {e}")
        
        # Find texture
        texture_path = find_texture(mesh, MESH_SEARCH_PATHS)
        
        # Export to glTF
        output_name = f"{mesh_name}.gltf"
        output_path = EXPORT_DIR / output_name
        
        exporter = GLTFExporter()
        exporter.export(
            mesh=mesh,
            skeleton=skeleton,
            filepath=str(output_path),
            texture_path=str(texture_path) if texture_path else None
        )
        
        return jsonify({
            'success': True,
            'mesh_name': mesh_name,
            'output_file': output_name,
            'output_url': f'/exports/{output_name}',
            'source': source,
            'has_skeleton': skeleton is not None,
            'has_texture': texture_path is not None,
            'format': 'skn' if is_skn else 'bmf',
            'vertices': mesh.vertex_count if hasattr(mesh, 'vertex_count') else 0,
            'faces': mesh.face_count if hasattr(mesh, 'face_count') else 0
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/export/character', methods=['POST'])
def export_character():
    """Export a character (body + head) to glTF format."""
    try:
        data = request.json
        char_name = data.get('name')
        body_mesh = data.get('body_mesh')
        head_mesh = data.get('head_mesh')
        
        if not char_name:
            return jsonify({'error': 'name required'}), 400
        
        exported_parts = []
        
        # Helper function to read mesh from result
        def read_mesh_from_result(result):
            path_or_data, is_skn, source = result
            if is_skn:
                reader = SKNReader()
                if isinstance(path_or_data, bytes):
                    return reader.read_string(path_or_data.decode('latin-1')), source
                else:
                    return reader.read_file(str(path_or_data)), source
            else:
                reader = BMFReader()
                if isinstance(path_or_data, bytes):
                    return reader.read_bytes(path_or_data), source
                else:
                    return reader.read_file(str(path_or_data)), source
        
        # Export body mesh
        if body_mesh:
            result = find_mesh_file(body_mesh)
            if result:
                mesh, source = read_mesh_from_result(result)
                
                if mesh:
                    output_name = f"{char_name}_body.gltf"
                    output_path = EXPORT_DIR / output_name
                    
                    # Load skeleton for body
                    skeleton = None
                    skel_result = find_skeleton()
                    if skel_result:
                        try:
                            bcf_reader = BCFReader()
                            if isinstance(skel_result, bytes):
                                bcf = bcf_reader.read_bytes(skel_result)
                            else:
                                bcf = bcf_reader.read_file(str(skel_result))
                            if bcf and bcf.skeletons:
                                skeleton = bcf.skeletons[0]
                        except:
                            pass
                    
                    texture_path = find_texture(mesh, MESH_SEARCH_PATHS)
                    
                    exporter = GLTFExporter()
                    exporter.export(
                        mesh=mesh,
                        skeleton=skeleton,
                        filepath=str(output_path),
                        texture_path=str(texture_path) if texture_path else None
                    )
                    exported_parts.append({
                        'type': 'body',
                        'file': output_name,
                        'url': f'/exports/{output_name}',
                        'source': source
                    })
        
        # Export head mesh  
        if head_mesh:
            result = find_mesh_file(head_mesh)
            if result:
                mesh, source = read_mesh_from_result(result)
                
                if mesh:
                    output_name = f"{char_name}_head.gltf"
                    output_path = EXPORT_DIR / output_name
                    
                    texture_path = find_texture(mesh, MESH_SEARCH_PATHS)
                    
                    exporter = GLTFExporter()
                    exporter.export(
                        mesh=mesh,
                        skeleton=None,  # Heads typically don't have full skeletons
                        filepath=str(output_path),
                        texture_path=str(texture_path) if texture_path else None
                    )
                    exported_parts.append({
                        'type': 'head',
                        'file': output_name,
                        'url': f'/exports/{output_name}',
                        'source': source
                    })
        
        if not exported_parts:
            return jsonify({
                'error': 'No meshes could be exported',
                'body_mesh': body_mesh,
                'head_mesh': head_mesh
            }), 404
        
        return jsonify({
            'success': True,
            'character': char_name,
            'exports': exported_parts
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/list/exports')
def list_exports():
    """List all exported glTF files."""
    exports = []
    for f in EXPORT_DIR.glob("*.gltf"):
        exports.append({
            'name': f.stem,
            'file': f.name,
            'url': f'/exports/{f.name}',
            'size': f.stat().st_size
        })
    return jsonify(exports)


@app.route('/api/status')
def status():
    """Health check and configuration info."""
    # Get FAR archive info
    far_info = []
    for far_path in FAR_ARCHIVE_PATHS:
        far = get_far_archive(far_path)
        if far:
            far_info.append({
                'name': far_path.name,
                'path': str(far_path),
                'files': len(far.entries),
                'loaded': True
            })
        else:
            far_info.append({
                'name': far_path.name,
                'path': str(far_path),
                'files': 0,
                'loaded': False,
                'exists': far_path.exists()
            })
    
    return jsonify({
        'status': 'ok',
        'game_root': str(GAME_ROOT),
        'game_exists': GAME_ROOT.exists(),
        'export_dir': str(EXPORT_DIR),
        'search_paths': [{'path': str(p), 'exists': p.exists()} for p in MESH_SEARCH_PATHS],
        'far_archives': far_info,
        'cached_archives': len(_far_cache)
    })


# ============================================================
# Object/Sprite API Endpoints
# ============================================================

def load_iff_file(source_file: str, source_archive: str) -> 'IffFile':
    """Load an IFF file from disk or FAR archive."""
    from formats.iff.iff_file import IffFile
    
    if source_archive:
        # Load from FAR archive
        far_path = Path(source_archive)
        far = get_far_archive(far_path)
        if far:
            data = far.get_entry(source_file)
            if data:
                return IffFile.from_bytes(data, source_file)
    else:
        # Load from disk
        iff_path = GAME_ROOT / source_file
        if iff_path.exists():
            return IffFile(str(iff_path))
    
    return None


def extract_object_sprites(iff_file, guid: int) -> dict:
    """Extract all sprites for an object from an IFF file."""
    from formats.iff.chunks.sprite_export import SPR2Decoder, export_sprite_png
    from formats.iff.chunks.spr import SPR2
    from formats.iff.chunks.palt import PALT
    from formats.iff.chunks.dgrp import DGRP
    from formats.iff.chunks.objd import OBJD
    import io
    import base64
    
    sprites = {}
    
    # Find the OBJD for this GUID
    objd = None
    for chunk in iff_file.chunks:
        if getattr(chunk, 'chunk_type', '') == 'OBJD':
            if hasattr(chunk, 'guid') and chunk.guid == guid:
                objd = chunk
                break
    
    if not objd:
        return sprites
    
    # Get the DGRP for this object (base_graphic_id)
    dgrp = None
    for chunk in iff_file.chunks:
        if getattr(chunk, 'chunk_type', '') == 'DGRP' and chunk.chunk_id == objd.base_graphic_id:
            dgrp = chunk
            break
    
    if not dgrp:
        return sprites
    
    # Find palette
    palt = None
    for chunk in iff_file.chunks:
        if getattr(chunk, 'chunk_type', '') == 'PALT':
            palt = chunk
            break
    
    # Find SPR2 chunks
    spr2_map = {}
    for chunk in iff_file.chunks:
        if getattr(chunk, 'chunk_type', '') == 'SPR2':
            spr2_map[chunk.chunk_id] = chunk
    
    # Decode each DGRP image
    # Direction flags to names: 0x01=RightBack(SW), 0x04=RightFront(SE), 0x10=LeftFront(NE), 0x40=LeftBack(NW)
    decoder = SPR2Decoder(palt)
    direction_map = {0x10: 'ne', 0x04: 'se', 0x01: 'sw', 0x40: 'nw'}
    zoom_map = {1: 'far', 2: 'med', 3: 'near'}
    
    for img in dgrp.images:
        dir_name = direction_map.get(img.direction)
        zoom_name = zoom_map.get(img.zoom)
        
        if not dir_name or not zoom_name:
            continue
            
        key = f"{dir_name}_{zoom_name}"
        
        # Get sprite from DGRP image
        if img.sprites:
            sprite_ref = img.sprites[0]  # Primary sprite
            spr2 = spr2_map.get(sprite_ref.sprite_id)
            if spr2 and sprite_ref.sprite_frame_index < len(spr2.frames):
                frame = spr2.frames[sprite_ref.sprite_frame_index]
                decoded = decoder.decode_frame(frame, palt)
                if decoded:
                    # Convert to base64 PNG
                    png_data = sprite_to_png_bytes(decoded)
                    sprites[key] = f"data:image/png;base64,{base64.b64encode(png_data).decode('ascii')}"
    
    return sprites


def sprite_to_png_bytes(sprite) -> bytes:
    """Convert a DecodedSprite to PNG bytes."""
    import struct
    import zlib
    
    width = sprite.width
    height = sprite.height
    rgba = sprite.rgba_data
    
    # Build PNG manually (similar to export_sprite_png)
    def png_chunk(chunk_type, data):
        length = struct.pack('>I', len(data))
        crc_data = chunk_type + data
        crc = zlib.crc32(crc_data) & 0xffffffff
        return length + crc_data + struct.pack('>I', crc)
    
    # PNG signature
    png = b'\x89PNG\r\n\x1a\n'
    
    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    png += png_chunk(b'IHDR', ihdr_data)
    
    # IDAT - raw image data with filter bytes
    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)  # Filter: None
        row_start = y * width * 4
        row_end = row_start + width * 4
        raw_data.extend(rgba[row_start:row_end])
    
    compressed = zlib.compress(bytes(raw_data), 9)
    png += png_chunk(b'IDAT', compressed)
    
    # IEND
    png += png_chunk(b'IEND', b'')
    
    return png


@app.route('/api/object/sprites', methods=['POST'])
def get_object_sprites():
    """Get all sprite views for an object."""
    try:
        data = request.get_json()
        guid_raw = data.get('guid')
        source_file = data.get('source_file', '')
        source_archive = data.get('source_archive', '')
        debug_log = []
        
        if not guid_raw:
            return jsonify({'success': False, 'error': 'No GUID provided', 'debug': ['No GUID provided']}), 400
        
        # Accept GUID as int, hex string, or decimal string
        guid = None
        if isinstance(guid_raw, int):
            guid = guid_raw
            debug_log.append(f"GUID provided as int: {guid}")
        elif isinstance(guid_raw, str):
            try:
                if guid_raw.lower().startswith('0x'):
                    guid = int(guid_raw, 16)
                    debug_log.append(f"GUID parsed from hex string: {guid_raw} -> {guid}")
                else:
                    guid = int(guid_raw)
                    debug_log.append(f"GUID parsed from decimal string: {guid_raw} -> {guid}")
            except Exception as e:
                debug_log.append(f"Failed to parse GUID string: {guid_raw} ({e})")
        else:
            debug_log.append(f"Unknown GUID type: {type(guid_raw)}")
        
        if guid is None:
            return jsonify({'success': False, 'error': 'Invalid GUID format', 'debug': debug_log}), 400
        
        # Load IFF file
        iff_file = load_iff_file(source_file, source_archive)
        if not iff_file:
            debug_log.append(f"Could not load IFF: {source_file}")
            return jsonify({'success': False, 'error': f'Could not load IFF: {source_file}', 'debug': debug_log}), 404
        
        # Extract sprites (primary lookup)
        sprites = extract_object_sprites(iff_file, guid)
        debug_log.append(f"Tried extract_object_sprites with GUID {guid}: {len(sprites)} sprites found")
        
        if sprites:
            return jsonify({
                'success': True,
                'guid': guid,
                'source_file': source_file,
                'sprites': sprites,
                'count': len(sprites),
                'debug': debug_log
            })
        
        # Fallback: try to find object by name or partial match
        # Load objects.json for suggestions
        suggestions = []
        try:
            objects_file = Path(__file__).parent.parent / 'data' / 'objects.json'
            if not objects_file.exists():
                objects_file = Path(__file__).parent / 'objects.json'
            if objects_file.exists():
                with open(objects_file, 'r') as f:
                    objects = json.load(f)
                # Try to find by name or partial match
                for obj in objects:
                    if str(obj.get('guid', '')).lower() == str(guid_raw).lower() or str(obj.get('guid_hex', '')).lower() == str(guid_raw).lower():
                        suggestions.append(obj)
                    elif source_file and obj.get('source_file', '') == source_file:
                        suggestions.append(obj)
                    elif guid_raw.lower() in (obj.get('name', '') or '').lower():
                        suggestions.append(obj)
                debug_log.append(f"Suggestions found: {len(suggestions)}")
        except Exception as e:
            debug_log.append(f"Failed to load objects.json for suggestions: {e}")
        
        return jsonify({
            'success': False,
            'error': f'No sprites found for GUID {guid}',
            'debug': debug_log,
            'suggestions': suggestions[:5]  # Limit to 5 suggestions
        }), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e), 'debug': debug_log if 'debug_log' in locals() else []}), 500


@app.route('/api/export/sprites/zip', methods=['POST'])
def export_sprites_zip():
    """Export all object sprites as a ZIP file."""
    try:
        import zipfile
        import io
        
        data = request.get_json()
        guid = data.get('guid')
        source_file = data.get('source_file', '')
        source_archive = data.get('source_archive', '')
        
        if not guid:
            return jsonify({'success': False, 'error': 'No GUID provided'}), 400
        
        # Load and extract sprites
        iff_file = load_iff_file(source_file, source_archive)
        if not iff_file:
            return jsonify({'success': False, 'error': f'Could not load IFF'}), 404
        
        sprites = extract_object_sprites(iff_file, guid)
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for key, data_url in sprites.items():
                # Decode base64
                png_data = base64.b64decode(data_url.split(',')[1])
                zf.writestr(f'{key}.png', png_data)
        
        # Save to exports
        name = Path(source_file).stem
        zip_name = f'{name}_{guid:08X}_sprites.zip'
        zip_path = EXPORT_DIR / zip_name
        with open(zip_path, 'wb') as f:
            f.write(zip_buffer.getvalue())
        
        return jsonify({
            'success': True,
            'filename': zip_name,
            'download_url': f'/exports/{zip_name}'
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/sprites/sheet', methods=['POST'])
def export_sprite_sheet():
    """Export object sprites as a sprite sheet."""
    try:
        data = request.get_json()
        guid = data.get('guid')
        source_file = data.get('source_file', '')
        source_archive = data.get('source_archive', '')
        
        if not guid:
            return jsonify({'success': False, 'error': 'No GUID provided'}), 400
        
        # Load and extract sprites
        iff_file = load_iff_file(source_file, source_archive)
        if not iff_file:
            return jsonify({'success': False, 'error': f'Could not load IFF'}), 404
        
        sprites = extract_object_sprites(iff_file, guid)
        
        if not sprites:
            return jsonify({'success': False, 'error': 'No sprites found'}), 404
        
        # For now, just return the ZIP (sprite sheet requires PIL)
        # TODO: Implement proper sprite sheet with PIL
        return jsonify({
            'success': False, 
            'error': 'Sprite sheet export requires PIL. Use ZIP export instead.'
        }), 501
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/list/objects', methods=['GET'])
def list_objects():
    """List all scanned objects from objects.json."""
    try:
        objects_file = Path(__file__).parent.parent / 'data' / 'objects.json'
        if not objects_file.exists():
            # Try webviewer directory
            objects_file = Path(__file__).parent / 'objects.json'
        
        if objects_file.exists():
            with open(objects_file, 'r') as f:
                objects = json.load(f)
            return jsonify({
                'success': True,
                'objects': objects,
                'count': len(objects)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'objects.json not found',
                'searched': [str(objects_file)]
            }), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("SimObliterator Export Server")
    print("=" * 60)
    print(f"Export directory: {EXPORT_DIR}")
    print(f"Game root: {GAME_ROOT}")
    print(f"\nLoose file search paths:")
    for p in MESH_SEARCH_PATHS:
        exists = "✓" if p.exists() else "✗"
        print(f"  [{exists}] {p}")
    print(f"\nFAR archives:")
    for p in FAR_ARCHIVE_PATHS:
        exists = "✓" if p.exists() else "✗"
        print(f"  [{exists}] {p}")
    print()
    print("Server starting at http://localhost:5000")
    print("Open http://localhost:5000/library_browser.html")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
