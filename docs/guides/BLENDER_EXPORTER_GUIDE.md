# VitaMoo Blender Exporter Guide

A Rosetta Stone for building Sims 1 character animation tools in Blender,
informed by the original Maxis 3ds Max pipeline that shipped The Sims.

## Historical Context: From maxiscrp.dlx to vitamoo

Twenty-six years ago, Don Hopkins at Maxis built `maxiscrp.dlx` — a C++
plugin for 3ds Max that wrapped the vitaboy character library and exposed
it to MaxScript. Three C++ files (`maxscript.cpp`, `Primitives.cpp`,
`CMXExporter.cpp`) bridged the 3ds Max scene graph to vitaboy's data
structures: `Skeleton`, `Bone`, `Suit`, `Skin`, `Skill`, `Motion`,
`DeformableMesh`. A 2364-line MaxScript UI ("CMX Exporter Turbo-Deluxe")
drove the whole pipeline from a Microsoft Access database through
SourceSafe version control, batch-processing hundreds of animations in
chunks of 50, auto-restarting Max when memory ran out.

The text reports included Walt Whitman poetry from "I Sing the Body Electric."

When Andrew Willmott sat down to build the Sims 2 animation system,
he "spelunked through" the vitaboy code and was "very thankful for
the way the code was written and especially all the comments — they
made it pretty easy to figure out what was going on in what could
have been a pretty hairy bit of code." He later had to jury-rig a
pipeline to export Sims 1 animations from Max, IK them onto the
Sims 2 skeleton in Maya, and re-save them. We have it easier.

We can now do the same thing — and more — directly in Blender, using
VitaMoo's TypeScript library or a Python port of the same binary format
readers and writers. No proprietary DCC tool, no COM/OLE database hacks,
no SourceSafe. Just Blender, Python, and the same binary formats the
game runtime loads.

## Architecture Comparison

### Then: 3ds Max + C++ + MaxScript

```
3ds Max Scene Graph
    ↓ (C++ plugin walks INode tree)
CMXExporter.cpp
    ↓ (creates vitaboy objects)
skeleton.h structs (Skeleton, DeformableMesh, Skill...)
    ↓ (operator<< stream I/O)
.cmx (text) + .skn (text mesh) + .cfp (compressed animation)
```

The C++ plugin registered 28 MaxScript primitives via `def_visible_primitive`.
MaxScript called `exportCmxFile` which triggered the full export pipeline.
Everything flowed through a single global `CMXExporter exporter` instance.

### Now: Blender + Python + VitaMoo

```
Blender Scene Graph
    ↓ (Python addon reads Armature, Mesh, Action)
vitamoo Python module (or TypeScript via wasm/subprocess)
    ↓ (creates VitaMoo data structures)
types.ts structs (SkeletonData, MeshData, SkillData...)
    ↓ (BinaryWriter serialization)
.bcf (binary skeleton/suit/skill) + .bmf (binary mesh) + .cfp (compressed animation)
```

The mapping is cleaner than the original because Blender's data model
is closer to what vitaboy needs:

| Vitaboy Concept | 3ds Max (Old) | Blender (New) |
|---|---|---|
| Skeleton | INode tree + BIPxx naming + Note Track tags | Armature with bone hierarchy |
| Bone rest pose | ObjectTM extraction + parent inverse | `bone.matrix_local` relative to parent |
| Suit / Skin | Note Track `suit=name` tags on timeline | Collection of meshes parented to armature |
| Mesh binding | Physique modifier SDK (max 2 bones, 15-bit weights) | Vertex groups (native weight painting) |
| Skill (animation) | Note Track `beginskill`/`endskill` brackets | Action or NLA strip |
| Motion (per-bone) | Frame-by-frame ObjectTM sampling | F-curve evaluation per bone channel |
| Properties | Note Track key=value pairs | Custom properties on objects/bones |
| Temporal events | Note Track temporal properties in time range | Timeline markers or custom properties on keyframes |

## Coordinate System Conversion

The original Max exporter applied a critical handedness flip at every
transform extraction point. The Sims uses a coordinate system where
Y and Z are swapped relative to 3ds Max:

**3ds Max export (from CMXExporter.cpp `ExtractTransRot`):**
- Translation: `(x, z, y)` — swap Y and Z
- Quaternion: `(x, z, y, -w)` — swap Y/Z, negate W

**Blender export (needed):**
Blender uses right-handed Z-up (like Max) but with different conventions.
The specific transform depends on Blender's bone conventions:

- Blender bones point along local Y by default
- Rest pose matrices are in armature space
- World-space evaluation gives posed transforms

For VitaMoo's WebGL renderer, we already apply coordinate conversion
in `parseCFP`: Z negated on translations, W negated on quaternions
(DirectX left-hand to WebGL right-hand). The Blender exporter would
produce data in the same coordinate space as the original game files.

**Recommended approach:** Match the original game's coordinate convention
in the binary files, let the renderer handle the final conversion.
This means the Blender exporter needs to transform from Blender space
to Sims space:

```python
def blender_to_sims_translation(v):
    # Blender Z-up to Sims coordinate system
    return (v.x, v.z, v.y)

def blender_to_sims_quaternion(q):
    # Match the original CMXExporter.cpp ExtractTransRot
    return (q.x, q.z, q.y, -q.w)
```

## Blender Addon Structure

A VitaMoo Blender addon would follow standard Blender addon patterns:

```
vitamoo_blender/
    __init__.py              # Addon registration, menu entries
    operators/
        export_bcf.py        # Export skeleton + suits + skills to BCF
        export_bmf.py        # Export mesh to BMF
        export_cfp.py        # Export animation to CFP
        import_bcf.py        # Import BCF into Blender
        import_bmf.py        # Import BMF mesh
        render_sprites.py    # Sprite sheet renderer
    panels/
        export_panel.py      # UI panel in Properties sidebar
        sprite_panel.py      # Sprite render settings
    core/
        binary_io.py         # BinaryReader/BinaryWriter (port of reader.ts)
        types.py             # Data structures (port of types.ts)
        cfp.py               # Delta compression (port of compress/decompress)
        coordinate.py        # Blender ↔ Sims coordinate transforms
    utils/
        bone_naming.py       # Bone name regression (CALF→LEG1, etc.)
        note_properties.py   # Custom property management
```

### Binary I/O in Python

The TypeScript `BinaryReader`/`BinaryWriter` classes translate directly
to Python using the `struct` module:

```python
import struct

class BinaryReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read_byte(self) -> int:
        v = self.data[self.pos]
        self.pos += 1
        return v

    def read_int32(self) -> int:
        v = struct.unpack_from('<i', self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_float32(self) -> float:
        v = struct.unpack_from('<f', self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_string(self) -> str:
        """CTGFile string: 1-byte length, or 0xFF + 4-byte length."""
        length = self.read_byte()
        if length == 255:
            length = self.read_int32()
        s = self.data[self.pos:self.pos + length].decode('latin-1')
        self.pos += length
        return s

    def read_bool(self) -> bool:
        return self.read_int32() != 0


class BinaryWriter:
    def __init__(self):
        self.parts: list[bytes] = []

    def write_byte(self, v: int):
        self.parts.append(struct.pack('B', v))

    def write_int32(self, v: int):
        self.parts.append(struct.pack('<i', v))

    def write_float32(self, v: float):
        self.parts.append(struct.pack('<f', v))

    def write_string(self, s: str):
        encoded = s.encode('latin-1')
        if len(encoded) < 255:
            self.write_byte(len(encoded))
        else:
            self.write_byte(255)
            self.write_int32(len(encoded))
        self.parts.append(encoded)

    def write_bool(self, v: bool):
        self.write_int32(1 if v else 0)

    def to_bytes(self) -> bytes:
        return b''.join(self.parts)
```

### CFP Delta Compression in Python

The key insight that makes this "stupid ad hoc compression algorithm"
work so well: **compress columns, not rows.** Instead of delta-encoding
`(x,y,z)` tuples where all three components jump around, we process all
the X values first, then all the Y values, then all the Z values. Within
a single dimension, consecutive keyframe values change very little — a
bone's X position barely moves between frames. The deltas are tiny, and
the quartic distribution table concentrates 253 code points right near
zero where they're needed most.

This is a well-known technique (column-major / structure-of-arrays
compression) but applying it here with a hand-tuned quartic curve and
a repeat-run encoder was enough to ship the game without anything
fancier. Several iterations of parameter tuning found the right
trade-off between table spread, epsilon thresholds, and the quartic
exponent. Sometimes "good enough" ships, and sometimes it ships for
26 years.

The quartic delta table and dimension-based compression translate
directly from the TypeScript implementation:

```python
import math

DELTA_TABLE_SIZE = 253
SPREAD = 0.1

def build_delta_table() -> list[float]:
    table = []
    for i in range(DELTA_TABLE_SIZE):
        unit_range = i / (DELTA_TABLE_SIZE - 1)
        val = 2.0 * unit_range - 1.0
        sgn = -1.0 if val < 0 else 1.0
        table.append(sgn * val * val * val * val * SPREAD)
    return table

def decompress_floats(reader, count, dims):
    """Decompress CFP stream. Dimension-first order, interleaved output."""
    delta_table = build_delta_table()
    buf = [0.0] * (count * dims)
    val = 0.0
    repeat = 0
    for dim in range(dims):
        for i in range(count):
            if repeat > 0:
                repeat -= 1
            else:
                code = reader.read_byte()
                if code == 255:
                    val = reader.read_float32()
                elif code == 254:
                    repeat = struct.unpack_from('<H',
                        reader.data, reader.pos)[0]
                    reader.pos += 2
                else:
                    val += delta_table[code]
            buf[dim + i * dims] = val
    return buf
```

### Skeleton Export

The core of skeleton export maps Blender's Armature to VitaMoo's
`SkeletonData`. The original Max exporter walked `INode` children
and computed relative transforms via `ExtractTransRot`. In Blender:

```python
import bpy
from mathutils import Quaternion, Vector

def export_skeleton(armature_obj) -> dict:
    """Export Blender Armature to VitaMoo SkeletonData."""
    armature = armature_obj.data
    bones = []

    for bone in armature.bones:
        # Compute position and rotation relative to parent
        if bone.parent:
            parent_mat = bone.parent.matrix_local
            local_mat = parent_mat.inverted() @ bone.matrix_local
        else:
            local_mat = bone.matrix_local

        pos = local_mat.to_translation()
        rot = local_mat.to_quaternion()

        # Transform to Sims coordinate system
        sims_pos = (pos.x, pos.z, pos.y)
        sims_rot = (rot.x, rot.z, rot.y, -rot.w)

        # Read custom properties for bone flags
        props = bone.get('vitamoo_props', {})

        bones.append({
            'name': bone.name,
            'parent_name': bone.parent.name if bone.parent else '',
            'position': sims_pos,
            'rotation': sims_rot,
            'can_translate': props.get('can_translate', bone.parent is None),
            'can_rotate': props.get('can_rotate', True),
            'can_blend': props.get('can_blend', True),
            'can_wiggle': props.get('can_wiggle', False),
            'wiggle_power': props.get('wiggle_power', 0.0),
            'props': {},
        })

    return {
        'name': armature_obj.name,
        'bones': bones,
    }
```

### Mesh Export (BMF)

The original Max exporter used the Physique SDK to extract per-vertex
bone weights — a complex API requiring COM interfaces and careful
deallocation. In Blender, vertex groups provide the same data natively:

```python
def export_mesh(mesh_obj, armature_obj) -> dict:
    """Export Blender Mesh to VitaMoo MeshData (BMF format)."""
    mesh = mesh_obj.data
    mesh.calc_normals_split()

    # Map vertex group names to bone indices
    bone_names = [b.name for b in armature_obj.data.bones]
    vg_to_bone = {}
    for vg in mesh_obj.vertex_groups:
        if vg.name in bone_names:
            vg_to_bone[vg.index] = bone_names.index(vg.name)

    # Collect per-vertex bone weights (max 2 per vertex, like original)
    vertices = []
    normals = []
    bone_bindings = {}  # bone_index -> list of vertex indices

    for vert in mesh.vertices:
        # Get bone weights, sorted by weight descending
        weights = []
        for g in vert.groups:
            if g.group in vg_to_bone:
                weights.append((vg_to_bone[g.group], g.weight))
        weights.sort(key=lambda w: -w[1])
        weights = weights[:2]  # Max 2 bones, same as original

        # Normalize
        total = sum(w for _, w in weights)
        if total > 0:
            weights = [(bi, w / total) for bi, w in weights]

        # Store vertex position and normal in Sims coords
        v = vert.co
        n = vert.normal
        vertices.append((v.x, v.z, v.y))
        normals.append((n.x, n.z, n.y))

        # Track bone assignments for binding construction
        if weights:
            primary_bone = weights[0][0]
            if primary_bone not in bone_bindings:
                bone_bindings[primary_bone] = []
            bone_bindings[primary_bone].append(vert.index)

    # Build faces, UVs from mesh loops
    uv_layer = mesh.uv_layers.active
    faces = []
    uvs = [None] * len(vertices)
    for poly in mesh.polygons:
        if len(poly.loop_indices) == 3:
            li = poly.loop_indices
            a, b, c = [mesh.loops[i].vertex_index for i in li]
            # Reverse winding (same as original CMXExporter)
            faces.append((c, b, a))
            # UV coordinates (Y flipped, same as original)
            for loop_idx in li:
                vi = mesh.loops[loop_idx].vertex_index
                if uv_layer and uvs[vi] is None:
                    uv = uv_layer.data[loop_idx].uv
                    uvs[vi] = (uv.x, 1.0 - uv.y)

    # Fill missing UVs
    for i in range(len(uvs)):
        if uvs[i] is None:
            uvs[i] = (0.0, 0.0)

    return {
        'name': mesh_obj.name,
        'texture_name': get_texture_name(mesh_obj),
        'bone_names': bone_names,
        'faces': faces,
        'bone_bindings': build_bone_bindings(bone_bindings, vertices),
        'uvs': uvs,
        'blend_bindings': [],  # populated from 2-bone weights
        'vertices': vertices,
        'normals': normals,
    }
```

### Animation Export (Skill + CFP)

The original exporter sampled every frame between `beginskill`/`endskill`
Note Track brackets. In Blender, Actions or NLA strips define the range:

```python
def export_skill(armature_obj, action, start_frame, end_frame) -> dict:
    """Export Blender Action to VitaMoo SkillData + CFP data."""
    scene = bpy.context.scene
    armature = armature_obj.data
    frame_count = end_frame - start_frame + 1

    translations = []
    rotations = []
    motions = []
    trans_offset = 0
    rot_offset = 0

    for bone in armature.bones:
        has_translation = bone.parent is None  # only root translates
        has_rotation = True

        bone_translations = []
        bone_rotations = []

        for frame in range(start_frame, end_frame + 1):
            scene.frame_set(frame)
            pose_bone = armature_obj.pose.bones[bone.name]

            # Get pose-space transform relative to rest
            if bone.parent:
                parent_pose = armature_obj.pose.bones[bone.parent.name]
                local_mat = (parent_pose.matrix.inverted()
                             @ pose_bone.matrix)
            else:
                local_mat = pose_bone.matrix

            pos = local_mat.to_translation()
            rot = local_mat.to_quaternion()

            # Quaternion continuity (same as MakeClosest in original)
            if bone_rotations:
                prev = bone_rotations[-1]
                if rot.dot(prev) < 0:
                    rot.negate()

            if has_translation:
                bone_translations.append(
                    (pos.x, pos.z, pos.y))
            bone_rotations.append(
                (rot.x, rot.z, rot.y, -rot.w))

        motions.append({
            'bone_name': bone.name,
            'frames': frame_count,
            'duration': frame_count * (1000.0 / scene.render.fps),
            'has_translation': has_translation,
            'has_rotation': has_rotation,
            'translations_offset': trans_offset,
            'rotations_offset': rot_offset,
            'props': {},
            'time_props': {},
        })

        translations.extend(bone_translations)
        rotations.extend(bone_rotations)
        if has_translation:
            trans_offset += frame_count
        rot_offset += frame_count

    return {
        'name': action.name,
        'animation_file_name': action.name,
        'duration': frame_count * (1000.0 / scene.render.fps),
        'distance': compute_root_distance(translations, frame_count),
        'is_moving': len(translations) > 0,
        'num_translations': len(translations),
        'num_rotations': len(rotations),
        'motions': motions,
        'translations': translations,
        'rotations': rotations,
    }
```

## Sprite Rendering Pipeline

The Sims renders characters as pre-rendered isometric sprites. The
original `SimsSpriteExporter` is a standalone C++ application that loads
vitaboy data, renders each animation frame from multiple angles and zoom
levels, and outputs sprite sheets with color + depth (Z-buffer in alpha).

### Isometric Camera Setup

The view is technically **dimetric**, not true isometric. It creates the
characteristic "looking down into a dollhouse" feel:

| Parameter | Value | Notes |
|---|---|---|
| Elevation | 60 degrees from horizontal | `PI / 3.0f` — steeper than true isometric (35.26 deg) |
| Projection | Orthographic | No perspective foreshortening |
| Target distance | 5.5 feet | `mDefaultTDist = 5.5f` |
| Cage width | 3.0 feet | One floor tile |
| Cage height | 12.0 feet | Floor to ceiling |
| Camera Z offset | 6.0 feet | Half cage height, centers the view |

### Rotation Angles

4 rotations at 90-degree intervals, offset by 45 degrees from axis-aligned:

| Rotation | Azimuth (Z rotation) | Formula |
|---|---|---|
| 0 | 225 degrees | `PI/2 * 2.5` |
| 1 | 315 degrees | `PI/2 * 3.5` |
| 2 | 45 degrees | `PI/2 * 4.5` |
| 3 | 135 degrees | `PI/2 * 5.5` |

### Zoom Levels

3 zoom levels, each half the resolution of the previous:

| Zoom | Width (px) | Height (px) | Scale |
|---|---|---|---|
| 0 (large) | 136 | 384 | 1x |
| 1 (medium) | 68 | 192 | 0.5x |
| 2 (small) | 34 | 96 | 0.25x |

Width includes a 4-pixel border on each side: `(128 + 2*4) >> zoom`.

### Z-Buffer Encoding

The depth buffer is encoded in the alpha channel for sprite compositing:

```
span = 2 * w / sqrt(3) + 0.5 * (h - w / sqrt(3))
    where w = 3.0 * sqrt(2) ≈ 4.243 feet (diagonal tile width)
          h = 12.0 feet (cage height)
          span ≈ 9.9 feet

z_alpha = (-254.0 / span) * z + 127.0
```

Valid Z maps to alpha values 0-253; infinite Z (background) maps to 0xFFFF.

### Sprite Sheet Layout

Output organized as a grid:

- **Columns**: 12 total (4 rotations x 3 zooms)
  - Columns 0-3: zoom 0, rotations 0-3
  - Columns 4-7: zoom 1, rotations 0-3
  - Columns 8-11: zoom 2, rotations 0-3
- **Rows**: `frames_per_animation * tiles_per_frame`
  - For multi-tile characters, each frame produces multiple rows

### Blender Sprite Renderer

The same pipeline can run in Blender using its rendering engine:

```python
import bpy
import math

# Isometric camera constants (from SimsSpriteExporter)
ELEVATION_ANGLE = math.pi / 3.0     # 60 degrees
CAGE_HEIGHT = 12.0
CAMERA_Z_OFFSET = CAGE_HEIGHT / 2.0
TARGET_DISTANCE = 5.5

ROTATIONS = [
    math.pi / 2.0 * 2.5,  # 225 deg
    math.pi / 2.0 * 3.5,  # 315 deg
    math.pi / 2.0 * 4.5,  # 45 deg
    math.pi / 2.0 * 5.5,  # 135 deg
]

ZOOM_LEVELS = [
    (136, 384),   # large
    (68, 192),    # medium
    (34, 96),     # small
]


def setup_sims_camera(rotation_index, zoom_index):
    """Configure Blender camera to match Sims isometric view."""
    cam_data = bpy.data.cameras.new('SimsCamera')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = TARGET_DISTANCE

    cam_obj = bpy.data.objects.new('SimsCamera', cam_data)
    bpy.context.collection.objects.link(cam_obj)

    # Position: rotate around Z, then tilt 60 degrees
    azimuth = ROTATIONS[rotation_index]
    dist = TARGET_DISTANCE

    # Camera location in world space
    x = dist * math.cos(azimuth) * math.cos(ELEVATION_ANGLE)
    y = dist * math.sin(azimuth) * math.cos(ELEVATION_ANGLE)
    z = CAMERA_Z_OFFSET + dist * math.sin(ELEVATION_ANGLE)

    cam_obj.location = (x, y, z)

    # Point at cage center
    direction = Vector((0, 0, CAMERA_Z_OFFSET)) - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

    # Set render resolution
    w, h = ZOOM_LEVELS[zoom_index]
    bpy.context.scene.render.resolution_x = w
    bpy.context.scene.render.resolution_y = h

    return cam_obj


def render_sprite_sheet(armature_obj, action,
                        start_frame, end_frame, output_dir):
    """Render a complete sprite sheet for an animation."""
    scene = bpy.context.scene
    armature_obj.animation_data.action = action

    for frame in range(start_frame, end_frame + 1):
        scene.frame_set(frame)
        for rot in range(4):
            for zoom in range(3):
                cam = setup_sims_camera(rot, zoom)
                scene.camera = cam

                # Render color pass
                scene.render.filepath = (
                    f'{output_dir}/{action.name}'
                    f'_f{frame:04d}_r{rot}_z{zoom}.png')
                bpy.ops.render.render(write_still=True)

                # Clean up camera
                bpy.data.objects.remove(cam)
```

## Multi-Tile Object Sprites

Objects in The Sims can span multiple floor tiles — a sofa occupies 2x1,
a dining table 1x2, a bed 3x2. The sprite exporter handles this by
rendering the entire multi-tile object as one oversized image, then
splitting it into individual tile-sized sprites using z-buffer unprojection.

### How Multi-Tile Rendering Works

**Step 1: Enlarged render.** The camera zooms out to encompass all tiles.
`ComputeImageDims` iterates every tile position (x,y) in the extent,
applies the isometric offset formula to each, and unions all tile
rectangles to get the total bounding rect. The camera's orthographic
scale is adjusted proportionally:

```
Isometric tile offset (per tile):
  dx = -(rot.x + rot.y) * tileWidth / 2
  dy = -(rot.x - rot.y) * tileWidth / 4
```

This is the standard 2:1 isometric projection ratio. The camera is
centered on the object's centroid (average of all tile centers).

**Step 2: Cage clipping.** Z-caging planes expand to cover the full
multi-tile footprint. For a 2x2 object at origin (0,0), the cage spans
\[-1.5, +4.5\] feet in both X and Y (where each tile is 3.0 feet wide).
Poke-through elimination handles geometry that sticks past tile
boundaries, using pinch thresholds of 6 inches and delta margins
of 1.5 inches to handle the tricky edge-of-tile seams.

**Step 3: Per-pixel tile assignment.** `ProcessSubObjectBitmaps` iterates
every pixel of the master render and determines which tile it belongs
to. For each pixel with geometry (z > -infinity):

1. **Unproject** the pixel to world space using the z-buffer ray
2. Shift by half a cage width to center on the tile grid
3. Divide by `kCageWidth` (3.0 feet) to get tile-space coordinates
4. Subtract virtual origin to get local tile index
5. Clamp to extent bounds
6. Compute flat subtile index: `index = subY * extentX + subX`
7. Remap pixel coordinates to sub-tile local space
8. Copy color, alpha, and **z-adjusted** depth to the target sub-tile

The z-adjustment accounts for the camera position difference between
the master (multi-tile centered) camera and the individual sub-tile
camera. This ensures each tile's z-buffer is correct for compositing
when the game draws the tiles independently.

### Multi-Tile Parameters

| Parameter | Range | Default | Purpose |
|---|---|---|---|
| extentX | 1-12 | 1 | Tiles wide (X axis) |
| extentY | 1-12 | 1 | Tiles deep (Y axis) |
| virtualOriginX | 0-3 | 0 | Anchor tile X offset |
| virtualOriginY | 0-3 | 0 | Anchor tile Y offset |

### Sprite Sheet Layout with Multi-Tile

Each animation frame produces `extentX * extentY` rows in the sprite
sheet instead of one. The subtile index determines row order within
each frame group:

```
For a 2x3 object (6 tiles), frame 0:
  Row 0: subtile (0,0) = index 0
  Row 1: subtile (1,0) = index 1
  Row 2: subtile (0,1) = index 2
  Row 3: subtile (1,1) = index 3
  Row 4: subtile (0,2) = index 4
  Row 5: subtile (1,2) = index 5
  --- frame 1 ---
  Row 6: subtile (0,0) = index 0
  ...
```

Total sprite sheet height: `384 * numFrames * extentX * extentY` pixels
(at zoom 0). Width stays constant at 952 pixels (12 columns).

### Rotation of Tile Coordinates

The `Rotate` function applies 90-degree CCW rotations per step:
`(x,y) → (y,-x)`. So a 2x3 object viewed from rotation 1 appears
as a 3x2 object. The isometric offsets adjust accordingly, which is
why `ComputeImageDims` recomputes the bounding rectangle per rotation.

### Blender Multi-Tile Implementation

In Blender, multi-tile rendering can use the same approach:

```python
import bpy
from mathutils import Vector

CAGE_WIDTH = 3.0  # feet per tile

def render_multi_tile_sprites(obj, extent_x, extent_y,
                              rotation, zoom, frame, output_dir):
    """Render a multi-tile object and split into per-tile sprites."""
    # Step 1: Render the full object with enlarged viewport
    cam = setup_multi_tile_camera(extent_x, extent_y, rotation, zoom)
    bpy.context.scene.camera = cam
    bpy.context.scene.frame_set(frame)

    # Render with depth pass enabled
    master_path = f'{output_dir}/master_r{rotation}_z{zoom}_f{frame}.exr'
    bpy.context.scene.render.filepath = master_path
    bpy.ops.render.render(write_still=True)

    # Step 2: Split into per-tile sprites using compositor
    for sub_y in range(extent_y):
        for sub_x in range(extent_x):
            subtile_idx = sub_y * extent_x + sub_x
            crop_tile_from_master(
                master_path, sub_x, sub_y,
                extent_x, extent_y,
                rotation, zoom, subtile_idx,
                output_dir, frame)

    # Clean up
    bpy.data.objects.remove(cam)


def setup_multi_tile_camera(extent_x, extent_y, rotation, zoom):
    """Camera centered on multi-tile object centroid."""
    import math

    # Compute centroid of all tiles
    center = Vector((0, 0, 0))
    for x in range(extent_x):
        for y in range(extent_y):
            center += Vector((CAGE_WIDTH * x, CAGE_WIDTH * y, 0))
    center /= (extent_x * extent_y)

    cam_data = bpy.data.cameras.new('MultiTileCamera')
    cam_data.type = 'ORTHO'

    # Scale orthographic size to encompass all tiles
    # Base scale for 1 tile = 5.5, grow proportionally
    max_extent = max(extent_x, extent_y)
    cam_data.ortho_scale = 5.5 * max_extent

    cam_obj = bpy.data.objects.new('MultiTileCamera', cam_data)
    bpy.context.collection.objects.link(cam_obj)

    # Position at isometric angle, offset by centroid
    azimuth = ROTATIONS[rotation]
    elevation = math.pi / 3.0
    dist = 20.0  # far enough for ortho

    cam_obj.location = (
        center.x + dist * math.cos(azimuth) * math.cos(elevation),
        center.y + dist * math.sin(azimuth) * math.cos(elevation),
        center.z + 6.0 + dist * math.sin(elevation),
    )

    # Point at centroid + half cage height
    target = center + Vector((0, 0, 6.0))
    direction = target - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    return cam_obj
```

For a simpler approach in Blender, render each tile individually by
moving the camera to each tile position rather than rendering one
master image and splitting — Blender's render overhead is low enough
that multiple renders may be faster than post-processing pixel splits.

## Extended Render Passes for Content Generators

The original SimsSpriteExporter produced only color + Z-buffer.
For modern content generation tools (Picture-o-Matic and similar),
additional render passes unlock powerful workflows:

### UV + Object ID Maps for Multi-Parameter Templates

The real power comes from combining UV coordinates with object IDs in
a single render pass. Each pixel carries three channels of information:
U, V, and which body part it belongs to. This creates a **multi-parameter
template** — a single image that tells a content generator exactly where
every pixel maps to on every mesh.

Render the UV coordinates as pixel colors (R=U, G=V) and the object ID
in the blue channel. Each pixel now encodes:
- **WHERE** on the texture this pixel comes from (U, V)
- **WHICH** mesh part this pixel belongs to (object ID)

This enables:
- **Texture projection**: Paint directly on the sprite view, project back
  to UV space per body part — head paint stays on the head texture, body
  paint stays on the body texture
- **Multi-mesh texture transfer**: Different body parts have different UV
  layouts and different textures. The object ID channel tells the generator
  which UV space to use for each pixel
- **AI texture generation**: Provide UV+ID maps as conditioning for
  image-to-image models. The model can generate a coherent outfit across
  head, body, and hand textures simultaneously because it knows which
  texture each pixel maps to
- **Picture-o-Matic templates**: User content generators can offer a sprite
  view where users paint or select patterns, and the tool automatically
  projects the result back to the correct texture atlas for each body part
- **Palette-driven recoloring**: Object IDs let you recolor specific parts
  independently (shirt vs pants vs skin vs hair) while the UV coordinates
  ensure the recoloring follows the mesh topology correctly

In Blender, this is a material override that outputs UV as color:

```python
# Shader node setup for UV pass
def create_uv_material():
    mat = bpy.data.materials.new('UV_Pass')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()
    tex_coord = nodes.new('ShaderNodeTexCoord')
    emission = nodes.new('ShaderNodeEmission')
    output = nodes.new('ShaderNodeOutputMaterial')

    # UV.x -> R, UV.y -> G, 0 -> B
    links.new(tex_coord.outputs['UV'], emission.inputs['Color'])
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    return mat
```

### Anisometric Texture Coverage Maps

When projecting between screen pixels and texture texels, the mapping
is almost never uniform. A pixel on the top of the head covers a
different amount of texture area than a pixel on the side of the torso.
The isometric camera makes this worse — surfaces nearly parallel to the
view direction get extreme foreshortening. Content generators need to
know this to produce textures at the right detail level everywhere.

The mathematical model is the **Jacobian** of the screen-to-UV mapping:
the 2x2 matrix of partial derivatives that describes how texture
coordinates change as you move across the screen:

```
J = | dU/dx  dU/dy |
    | dV/dx  dV/dy |
```

From this matrix you get everything:
- **Texel density** = `|det(J)|` — area ratio between one screen pixel
  and the texture area it covers. High values mean the texture is
  compressed (many texels per pixel); low values mean it's stretched
- **Anisotropy ratio** = `σ_max / σ_min` (ratio of singular values of J)
  — how elongated the texture footprint is. 1.0 = isotropic (square
  pixel maps to square texel area). 8.0 = highly stretched in one direction
- **Anisotropy direction** = angle of the major singular vector — which
  screen direction maps to the most texture stretching

This is exactly what GPUs compute with `dFdx`/`dFdy` for mip-mapping
and anisotropic filtering (EWA filtering). There's no single standard
image format, but the natural representation is a **4-channel float
image** per pixel: `(dU/dx, dU/dy, dV/dx, dV/dy)`. From those four
values, any downstream tool can reconstruct the full Jacobian.

In Blender, render this as a shader that computes UV derivatives:

```python
def create_texture_coverage_material():
    """Shader that outputs the UV Jacobian as pixel colors.

    R = dU/dx (horizontal UV gradient, U component)
    G = dU/dy (vertical UV gradient, U component)
    B = dV/dx (horizontal UV gradient, V component)
    A = dV/dy (vertical UV gradient, V component)

    The determinant |R*A - G*B| gives texel density per pixel.
    Singular value decomposition gives anisotropy ratio and direction.
    """
    mat = bpy.data.materials.new('TexCoverage_Pass')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()
    tex_coord = nodes.new('ShaderNodeTexCoord')
    # Use a script node or bake pass to capture dFdx/dFdy
    # In practice, Blender's OSL shading supports Dx()/Dy() functions
    # for exactly this purpose
    emission = nodes.new('ShaderNodeEmission')
    output = nodes.new('ShaderNodeOutputMaterial')

    links.new(tex_coord.outputs['UV'], emission.inputs['Color'])
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    return mat
```

For AI content generators, the texel density map tells the model where
it needs to generate fine detail (high density = many texels per screen
pixel, so the texture needs to be sharp there) versus where it can be
coarse (low density = stretched texture, fine detail would be wasted).
Combined with the UV+Object ID template, this gives a complete
specification: where, which part, and how much detail.

### Object ID Maps

Render each mesh part (body, head, hands) with a unique flat color.
This enables:
- **Segmentation**: Know which body part occupies each pixel
- **Selective editing**: Recolor or modify specific parts
- **Compositing**: Layer different body parts independently
- **AI training data**: Ground-truth segmentation masks

```python
# Assign unique colors per body part
BODY_PART_COLORS = {
    'HEAD':  (1.0, 0.0, 0.0, 1.0),  # Red
    'BODY':  (0.0, 1.0, 0.0, 1.0),  # Green
    'LHAND': (0.0, 0.0, 1.0, 1.0),  # Blue
    'RHAND': (1.0, 1.0, 0.0, 1.0),  # Yellow
}

def create_object_id_material(part_name):
    mat = bpy.data.materials.new(f'ObjID_{part_name}')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()
    emission = nodes.new('ShaderNodeEmission')
    output = nodes.new('ShaderNodeOutputMaterial')

    color = BODY_PART_COLORS.get(part_name, (0.5, 0.5, 0.5, 1.0))
    emission.inputs['Color'].default_value = color
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    return mat
```

### Depth Pass (Z-Buffer)

Use Blender's compositor to extract the Z-buffer with the same encoding
as the original SimsSpriteExporter:

```python
def setup_depth_compositor():
    """Configure compositor to output Z-buffer in alpha channel."""
    scene = bpy.context.scene
    scene.use_nodes = True
    tree = scene.node_tree
    nodes = tree.nodes
    links = tree.links

    nodes.clear()
    render_layers = nodes.new('CompositorNodeRLayers')
    normalize = nodes.new('CompositorNodeNormalize')
    combine = nodes.new('CompositorNodeCombRGBA')
    composite = nodes.new('CompositorNodeComposite')

    # Color RGB from render
    links.new(render_layers.outputs['Image'],
              combine.inputs['R'])
    # Depth into alpha (normalized)
    links.new(render_layers.outputs['Depth'],
              normalize.inputs['Value'])
    links.new(normalize.outputs['Value'],
              combine.inputs['A'])
    links.new(combine.outputs['Image'],
              composite.inputs['Image'])
```

### Normal Maps

Render world-space normals as colors for relighting:

```python
def create_normal_material():
    mat = bpy.data.materials.new('Normal_Pass')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()
    geometry = nodes.new('ShaderNodeNewGeometry')
    mapping = nodes.new('ShaderNodeVectorMath')
    mapping.operation = 'SCALE'
    mapping.inputs[1].default_value = (0.5, 0.5, 0.5)

    add = nodes.new('ShaderNodeVectorMath')
    add.operation = 'ADD'
    add.inputs[1].default_value = (0.5, 0.5, 0.5)

    emission = nodes.new('ShaderNodeEmission')
    output = nodes.new('ShaderNodeOutputMaterial')

    links.new(geometry.outputs['Normal'], mapping.inputs[0])
    links.new(mapping.outputs['Vector'], add.inputs[0])
    links.new(add.outputs['Vector'], emission.inputs['Color'])
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    return mat
```

## Bone Name Regression

The original exporter regressed modern Biped bone names to the Sims
conventions. This mapping is still needed for compatibility:

| 3ds Max / Biped | Sims Bone Name |
|---|---|
| CALF | LEG1 |
| THIGH | LEG |
| UPPERARM | ARM1 |
| FOREARM | ARM2 |
| CLAVICLE | ARM |
| PELVIS | ROOT |
| SPINE | SPINE |
| HEAD | HEAD |
| NECK | NECK |
| HAND | (varies by L/R) |
| FINGER | (varies by digit) |
| TOE | TOE |
| FOOT | FOOT |

The BIP prefix (e.g., "BIP01 L CALF") is stripped and L/R markers are
moved to the end: "L_LEG1" or "R_LEG1".

## File Format Summary

All formats VitaMoo reads and writes, for reference:

| Format | Type | Content | Reader | Writer |
|---|---|---|---|---|
| BCF | Binary | Skeletons, suits, skills (compiled CMX) | `parseBCF()` | `writeBCF()` |
| BMF | Binary | Mesh geometry (compiled SKN) | `parseBMF()` | `writeBMF()` |
| CFP | Binary | Delta-compressed animation keyframes | `parseCFP()` | `writeCFP()` |
| BMP | Binary | 8-bit indexed skin textures | `parseBMP()` | — |
| CMX | Text | Skeletons, suits, skills (development) | `parseCMX()` | — |
| SKN | Text | Mesh geometry (development) | `parseSKN()` | — |

The binary formats (BCF, BMF, CFP) are what the game loads at runtime.
The text formats (CMX, SKN) were Maxis development tools. VitaMoo
supports reading both but writes only binary — the runtime formats.

## Future Work

Tracked in the VitaMoo project TODO:

- **Blender addon**: Import/export BCF+BMF+CFP, drive animation, sprite rendering
- **Sprite renderer**: Reproduce the SimsSpriteExporter pipeline in Blender
  with extended passes (UV maps, object ID, depth, normals)
- **Content generator integration**: UV and object ID maps for Picture-o-Matic
  and AI-driven texture generation pipelines
- **Browser sprite exporter**: WebGL-based sprite rendering (TypeScript port
  of the Blender pipeline for browser-based content tools)
- **FAR archive support**: Read/write game archive files directly
- **SPR/SPR2 sprite format**: Read/write the game's sprite sheet format
- **Batch pipeline**: Database-driven batch export (the modern equivalent
  of "CMX Exporter Turbo-Deluxe" and its "Blowing Chunks" batch processor)

## References

- `SimsKit/maxscript/` — Original 3ds Max plugin (C++ + MaxScript)
- `SimsKit/vitaboy/` — Core C++ character library
- `SimsKit/SimsSpriteExporter/` — Sprite rendering pipeline
- `SimsKit/SprMaker/` — Sprite sheet assembly tool
- `SimsKit/animcomp/` — Animation compiler (CMX text → BCF+CFP binary)
- `SimsKit/farcomp/` — FAR archive compiler
- `vitamoo/src/` — TypeScript implementation (this project)
