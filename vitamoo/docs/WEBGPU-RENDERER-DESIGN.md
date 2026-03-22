# WebGPU renderer: current state and advanced features

The vitamoo **WebGPU `Renderer`** is a **rendering framework**, not a single-purpose character toy. It is meant to grow into the common GPU layer for **the rest of Sims-era and adjacent content** (lots, objects, architecture, UI chrome, tooling views) and for **plug-ins** such as custom user interface, data visualization, editors, and holodeck-style composition. **Skinned character animation** (CMX/SKN/CFP, `deformMesh`, `drawMesh`) is the **first shipped slice**; the same pipeline (depth, object IDs, display-list shapes, WGSL passes) extends to terrain, sprites, overlays, and third-party draws.

This document covers the **current** WebGPU surface and the **roadmap** for Sims-style holodeck rendering: z-buffered sprites, procedural terrain and architecture, and UI feedback (highlighting, selection, pie menu).

---

## 1. Current WebGPU surface

### 1.1 Implemented (vitamoo)

All GPU drawing lives in **vitamoo** (`Renderer`); **mooshow** orchestrates it for the character viewer (and **vitamoospace** hosts the demo app).

| File | Role |
|------|------|
| `vitamoo/vitamoo/renderer.ts` | Single `Renderer` class. WebGPU only. `Renderer.create(canvas)` → `Promise<Renderer>`. Methods: `clear`, `fadeScreen`, `setCamera`, `setCulling`, `drawMesh(mesh, verts, norms, texture?, objectId?)`, `drawDiamond(…, objectId?)`, `setViewport`, `endFrame`, `getTextureFactory`, `readObjectIdAt`, `setDebugSlice`, `setPlumbBobMeshes`, `setPlumbBobScale`. **Dual attachments:** color target + `rgba32uint` object-ID texture (same pass, shared depth). WGSL mesh + fullscreen fade + diamond. One encoder/pass per frame; depth from `setViewport`. |
| `vitamoo/vitamoo/texture.ts` | `parseBMP(buffer)` (pure). `loadTexture(device, queue, url)` → `Promise<TextureHandle>` (GPUTexture). BMP → parseBMP → ImageData → createImageBitmap → copyExternalImageToTexture; other formats → fetch → createImageBitmap → same. |

**mooshow:** `Renderer.create(canvas)`; `setTextureFactory`, `setViewport`. Per frame: `clear` or `fadeScreen` → `setCamera` → CPU `deformMesh` then `drawMesh` / `drawDiamond` with pick ids → `endFrame`. Picking and hover use `readObjectIdAt`. `setDebugSlice` is wired for debug display modes. No raw WebGPU in the loader.

**Procedural meshes and display list:** The plumb-bob diamond is implemented as a procedural mesh plug-in: `createDiamondMesh(size?, segments?)` in `vitamoo/procedural/diamond.ts` returns a `MeshData` in model space. The renderer caches one diamond mesh and uses `transformMesh(mesh, x, y, z, rotY, scale)` from `display-list.ts` each frame to get world-space vertices/normals, then draws via `drawMesh` (with optional objectId). So geometry is generated once and reused; only the transform is applied per draw. A **display list** is represented by `DisplayListEntry[]`: each entry has a `kind` (`'static'` | `'skinned'` | `'ui'`) and the right data (mesh + transform for static/UI; mesh + skeleton + boneMap for skinned). See §7 for the full generalized format covering characters, terrain, walls, roofs, UI, and optional UV/texture-ID for paint-on-skin.

### 1.2 Shaders (WGSL, as implemented)

- **Mesh:** Vertex: position, normal, texCoord. Uniforms: projection, modelView, lightDir, alpha, fadeColor (fade when .r ≥ 0), hasTexture, ambient, diffuseFactor, highlight (vec4), idType/objectId/subObjectId, debugMode. Fragment: dual output — object id (`vec4u`) and color (`vec4f`); diffuse + texture or untextured gray; optional highlight mix.
- **Fullscreen quad:** NDC positions; fade color; writes zero object id when the ID attachment is bound.
- **Diamond:** Same mesh pipeline family, solid color, optional object id.

### 1.3 Next phases (implementation order in §4)

1. ~~WebGPU parity + setViewport + loader texture factory~~ — **done**.
2. ~~Object-ID in the main pass + `readObjectIdAt` + mooshow picking~~ — **done** (single pass, not a separate object-ID pass).
3. **Holodeck / advanced:** Background layer, terrain, walls, UI (§4 steps 4–8).
4. **GPU deformation / animation (§5):** Parallel track; not started.

---

## 2. Advanced WebGPU renderer — Sims-style pipeline

### 2.1 Holodeck composition

- **Background:** Pre-rendered or procedurally generated: terrain, floors, walls, roofs, and static props. Rendered first into the same depth buffer (or a separate depth that we merge). Can be:
  - Pre-rendered RGB+alpha+z sprites (layered images with depth), or
  - Procedural geometry drawn in the same pass (terrain, tiles, walls, roofs from shaders).
- **Characters:** Real-time vitamoo skinned meshes (current `drawMesh` path). Drawn after the background with depth test on, so they correctly occlude and are occluded.
- **Order:** (1) Clear. (2) Draw background (sprites and/or procedural) with depth write. (3) Draw 3D characters with depth test and write. (4) Optional: UI overlay (pie menu, feedback).

One camera, one depth buffer, one render pass (or a small number of passes) so composition stays simple and correct.

### 2.2 Z-buffered sprites

- **Input:** Per-object or per-layer RGBA + depth (e.g. from object-ID / bake pass, or from pre-rendered assets). Sprites are screen-aligned or billboarded quads with texture (RGB+A) and depth.
- **Composition:** Draw sprites in back-to-front or use depth buffer: draw each sprite with its depth so characters and other geometry correctly interleave. Same pipeline as “background” above when background is image-based.
- **Object creation:** 3D model (OBJ, glTF, or Sims assets) → render to RGB + alpha + z → export as layered sprite for use in holodeck or in object tools.

### 2.3 Object-ID buffer (type + object id + sub-object id per pixel)

Every pixel has **type** (8 bits), **object id** (32 bits), and **sub-object id** (8 bits). The buffer is shared: characters, objects, walls, floor tiles, and future passes all write into the same ID texture using the same depth buffer so the visible pixel wins. Picking maps back to the original content (catalog, character, or part).

- **Format:** One `rgba32uint` pixel: R = type, G = objectId, B = subObjectId, A = 0. So 8-bit type (0–255), 32-bit object id (0–~4B), 8-bit sub-object id (0–255). No 64k limit: 32-bit objectId supports very large scenes (e.g. huge crowds).
- **Reserved types:** `0` = none/background, `1` = character, `2` = object (prop), `3` = wall, `4` = floor, `5` = terrain, `6` = plumb-bob (diamond or custom mesh). Plumb-bob uses the same objectId as the character it hovers over. The plumb-bob shape can be the built-in procedural diamond or a user-supplied mesh (see §6). Extend as we add passes.
- **Sub-object id semantics:** Keep a **single low-level granular ID** in the buffer: e.g. the mesh index (or draw index) within the object. So for characters, subObjectId is the index of the mesh in the body’s mesh list (0 = first skin, 1 = second, …). For props, it’s the draw group or sprite index. The renderer does not encode dressing, suite, or character in the ID; it only writes (type, objectId, subObjectId). The **application maintains maps** from (type, objectId, subObjectId) up to higher-level identities: e.g. (CHARACTER, bodyIndex, meshIndex) → dressing → suite → character. One granular sub-object id at the GPU, then derive dressing ⇒ suite ⇒ character (and any other hierarchy) via app-side lookups. That keeps the buffer format simple and stable while allowing flexible resolution for UI, paint tools, and selection.
- **TODO (future):** Character renderer could render which (main) bone each triangle was skinned to into the ID buffer (e.g. via vertex attribute or per-draw bone id), so you get bone-based selection: click on an arm and resolve to the upper-arm bone. Not yet implemented.
- **Flow:** One pass with **two color attachments** and one depth buffer. **Attachment 0** is `rgba32uint` (object ID). **Attachment 1** is the surface/swapchain color. The mesh fragment shader outputs `@location(0) objectId: vec4u` and `@location(1) color: vec4f` (type / objectId / subObjectId in the uint target). Same depth test and write for both; no second geometry pass for IDs. Fullscreen fade writes color to attachment 1 and `(0,0,0,0)` to attachment 0 when dual-targeting is active.
- **API:** `drawMesh(mesh, verts, norms, texture?, objectId?)` and `drawDiamond(..., objectId?)`. When `objectId` is provided, the mesh uniform includes type/objectId/subObjectId and the fragment writes them to the second attachment. When omitted, (0,0,0,0) is written. `readObjectIdAt(x, y)` returns `Promise<{ type, objectId, subObjectId }>`. No separate `beginObjectIdPass()` or `drawMeshObjectId`; one pass, one draw per object.
- **Layered sprite authoring:** Same ID or a separate “bake” pass used to generate the RGB+alpha+z layers for new objects.

---

## 3. Shader scope — how much in shaders

Goal: push as much Sims-style look and feel into shaders as we can (performance, consistency, single pipeline). Below is a concrete list; implementation order can follow parity first, then background/terrain, then UI.

### 3.1 Terrain

- **Options:** (a) Heightfield from texture or vertex grid, (b) tiled terrain with repeating or blended tiles, (c) fully procedural (noise-based height + optional texture). Shaders: vertex displacing by height, fragment for color (texture sample or procedural). We can start with a simple grid + height texture and add procedural variation later.

### 3.2 Floor tiles

- **Grid:** Vertex buffer or instancing for a grid of quads. UVs for tile index or atlas. Shader: sample floor tile atlas; optional edge lines or pattern (e.g. checker) in fragment. Tiling and repetition fully in shader.

### 3.3 Walls

- **Quads or boxes:** Planar geometry with normals. Shader: diffuse (and optional simple procedural pattern or texture). Wall edges or trim can be a separate pass or same pass with different UVs. Lighting from shared directional/ambient.

### 3.4 Roofs

- **Pitched planes:** Triangles or quads for roof faces. Shader: tiling texture or procedural (e.g. shingle pattern). Same lighting model as walls. Can be instanced for repeated roof segments.

### 3.5 Lighting

- **Current (keep):** Directional light from camera direction + bias; diffuse in fragment.
- **Extend in shaders:** Ambient term (constant or from uniform). Optional: second light (fill). No need for full PBR initially; keep “Sims-style” simple diffuse + ambient.
- **Shadows (optional):** Simple shadow map or fake “blob” under characters; can be a later pass. Not required for first advanced pass.

### 3.6 Highlighting (hover)

- **Options:** (a) Outline pass (render object again with scaled geometry and solid color), (b) tint overlay (multiply or add a color in fragment when “highlight” uniform is set), (c) second pass that adds a highlight color where object-ID matches hovered ID. Prefer (b) or (c) to avoid double geometry; can be a uniform on the existing mesh pipeline: `uHighlight (vec3 or vec4)` and blend in fragment.

### 3.7 Selection

- **Object-ID:** Already covered; click resolves ID. Visual: same as highlighting (tint or outline) keyed by “selected” ID. Optional: thicker outline or different color for selection vs hover.

### 3.8 Feedback (click / state)

- **In shader:** Brief flash or pulse: e.g. `uFeedback` (float 0..1) that lerps or multiplies with base color. Driven by JS timer. No new geometry; just a uniform on mesh or fullscreen overlay.

### 3.9 Pie menu

- **Background:** Desaturated version of the scene behind the menu. Options: (a) Copy current framebuffer to a texture, then draw a fullscreen quad that samples it and desaturates (e.g. dot with gray weights) and optionally darkens; (b) Re-render scene with a desaturate-only fragment shader to an offscreen texture, then draw that as background. (a) is simpler if we have a resolve/copy path.
- **Feather / vignette:** Fullscreen quad with radial gradient (soft falloff) so the center is clear and the edges fade to a shadow color. Drawn after the desaturated background. Alpha blend.
- **Shadows:** “Drop shadow” behind the pie: draw the pie shape (or a rounded rect) slightly offset and blurred (or with a soft edge) in a dark color, then draw the pie on top. Can be a simple soft quad or a small blur in a shader (e.g. 4-tap or 9-tap blur on a small texture). All of this can live in one “UI overlay” pass with 2–3 draws: desaturated bg, feather, shadow, then menu content.
- **Head in pie menu:** The character animation system already supports rendering only the head (e.g. head mesh/suit in local or bone-local coordinates, as in the original vitaboy “drawing the people's heads in the center of the pie menu”). The WebGPU renderer reuses the same mesh pipeline: draw the head mesh with the appropriate camera and transform so the Sim’s head appears in the center of the pie. No new shader; just a dedicated draw call with head-only geometry and optional scale/position for the menu.

### 3.10 Summary table

| Feature | Where it lives | Notes |
|--------|-----------------|-------|
| Terrain | Vertex + fragment | Height, tile or procedural color |
| Floor tiles | Fragment (atlas/UV) | Grid geometry, shader does tiling |
| Walls | Vertex + fragment | Quads, diffuse + optional texture |
| Roofs | Vertex + fragment | Pitched planes, tiling or texture |
| Lighting | Fragment | Directional + ambient; extend current |
| Highlighting | Fragment (uniform) | Tint or blend when hover |
| Selection | Fragment (uniform) or ID | Same as highlight, different color/state |
| Feedback | Fragment (uniform) | Flash/pulse driven by JS |
| Pie menu bg | Fullscreen quad | Desaturate current frame or re-render |
| Pie menu feather | Fullscreen quad | Radial alpha / vignette |
| Pie menu shadow | Fullscreen / quad | Soft drop shadow behind menu |
| Pie menu head | Mesh (existing) | Head-only render in center; animation system already supports it |

---

## 4. Implementation order

**Holodeck / presentation track** (serial steps; 1–3 complete)

1. ~~WebGPU parity (renderer + texture)~~ — **done**.
2. ~~setViewport + loader texture factory~~ — **done**.
3. ~~Object-ID in main pass + `readObjectIdAt` + app picking~~ — **done** (mooshow uses ids for pick/hover; supports layered-sprite authoring later).
4. **Background layer:** z-buffered sprites and/or procedural terrain + floor (minimal: grid + height + one tile texture).
5. **Walls and roofs** (procedural or tiled in shaders).
6. **Lighting** — directional + ambient already in WGSL; expose and tune from mooshow (public setters if missing).
7. **Highlight / selection / feedback** — highlight uniform exists in shader; wire hover/selected ids from stage and add API on `Renderer` if needed; optional small overlay pass.
8. **Pie menu** (desaturated bg, feather, shadow) when the app adds a pie UI.

**Parallel track — performance (§5)**  
Not scheduled inside steps 4–8: **GPU-side deformation** (then optional full GPU animation). Reduces per-frame vertex upload; large win for crowds. Starts only when someone takes §5 as the active task.

---

## 5. Advanced goal: GPU-side skeletal deformation

**Idea:** Upload all undeformed character meshes and skeletons to the GPU once; run skeletal mesh deformation (and ideally animation) on the GPU; render from the resulting mesh state without streaming deformed vertices back from the CPU each frame. We can put the animations on the GPU too — keyframes or motion curves resident in buffers/textures, so the GPU evaluates pose from a time uniform and then deforms. No per-frame animation or skeleton data from the CPU.

### 5.1 Current divide

Today the CPU owns the pipeline: `updateTransforms(bones)` and `deformMesh(mesh, bones, boneMap)` produce deformed vertices and normals in JS; the renderer uploads those to the GPU every frame and draws. Mesh and skeleton data live in CPU memory; only the final deformed buffers are sent to the GPU each frame.

### 5.2 Target: data on GPU, animate on GPU

- **Upload once (or at load):** For each character, upload to GPU and keep there:
  - **Undeformed mesh:** positions, normals, UVs, indices; plus **bone bindings** (per-bone: firstVertex, vertexCount, firstBlendedVertex, blendedVertexCount) and **blend bindings** (otherVertexIndex, weight). These are static per mesh.
  - **Skeleton:** hierarchy (parent indices or structure), rest pose (local position, rotation per bone). Static per character.
  - **Animation data (optional):** Keyframes or motion curves per bone (translation, rotation over time) so the GPU can derive current pose from a time uniform.
- **Animate on GPU:** Two possible levels:
  - **Option A — Deformation only on GPU:** CPU still runs `Practice.tick` and computes bone world poses each frame; upload only the current bone matrices (or position+rotation) to a uniform/storage buffer. A **compute shader** (or vertex shader, if we restructure — see below) performs the same Phase 0 / Phase 1 / Blend logic as `deformMesh`, writing deformed positions and normals to a GPU buffer. The render pass then draws from that buffer. No deformed data leaves the GPU; only a small bone-matrix upload per frame.
  - **Option B — Full GPU animation:** Time (and maybe skill/sequence ID) is uploaded each frame. A **compute shader** evaluates animation (keyframe interpolation, or sample from textures) to produce bone world matrices, then runs the same deformation logic and writes deformed mesh buffer. No per-frame skeleton or mesh data from CPU; only time (and optionally a few parameters).
- **Render from GPU output:** The mesh draw uses the buffer filled by the deformation pass (positions, normals; UVs and indices are unchanged). One compute pass per character (or batched), then one draw per character from the deformed buffer. No readback of deformed vertices to CPU.

So yes: we can download (upload) all undeformed meshes and skeletons to the GPU and leave them there; then animate and deform on the GPU and render from that state.

### 5.3 Implementing the current deformation model on GPU

The vitamoo deformation model (see `skeleton.ts`) is:

- **Phase 0:** Each bone transforms its “bound” vertices (position and normal) by its world position and rotation.
- **Phase 1:** Each bone transforms its “blended” vertices (stored at offset `boundCount` in the vertex array).
- **Blend:** Each blend binding lerps a blended vertex into a bound vertex: `destVert = lerp(destByBoneA, blendByBoneB, weight)` (and same for normals, normalized).

This is not the usual per-vertex “bone indices + weights” skinning; it’s bone-ranged and then a blend pass. It maps cleanly to a **compute shader**:

- **Input buffers (read-only, resident on GPU):** undeformed vertices/normals, bone bindings (bone index, firstVertex, vertexCount, firstBlendedVertex, blendedVertexCount), blend bindings (otherVertexIndex, weight), and per-frame bone world matrices (position.xyz + rotation quat or 3×3).
- **Output buffer (write):** deformed positions and normals (same layout as current `drawMesh` input).
- **Dispatch:** One thread per vertex (or per binding range); implement Phase 0 and Phase 1 by having each thread know which bone(s) affect it, then a second pass or same pass with careful ordering for the blend step. (Blend reads from and writes to the same buffer, so either two buffers ping-pong or structure the blend so writes don’t conflict — e.g. blend bindings write into bound vertex indices, which are not written in the blend phase.)

Alternatively, we could **pre-convert** the mesh to a conventional format (e.g. per-vertex up to N bone indices and weights) and use **vertex-shader skinning**; that would require a one-time conversion and might approximate the current blend behavior rather than match it exactly.

### 5.4 What stays on CPU vs GPU

| Data | Today | Advanced (GPU deformation) |
|------|--------|-----------------------------|
| Undeformed mesh (verts, norms, UVs, indices, bone/blend bindings) | CPU | GPU (upload once) |
| Skeleton (rest pose, hierarchy) | CPU | GPU (upload once) |
| Animation (motions, keyframes) | CPU | Optional: GPU (for Option B) |
| Current bone poses (world position, rotation) | CPU every frame | Option A: CPU computes, upload matrices. Option B: GPU computes from time. |
| Deformed vertices/normals | CPU every frame → upload | GPU only (compute output → render input) |

### 5.5 Benefits

- **No per-frame vertex upload:** Deformed mesh stays on GPU; only small uniform/buffer updates (bone matrices or time).
- **Scalability:** Many characters mean many small compute dispatches and draws, not huge CPU→GPU vertex streams.
- **Pipeline clarity:** Load → upload assets once; each frame: update pose (or time), run deformation, draw. Same mental model as “holodeck”: static and skinned data on GPU, animate on that side of the divide.

### 5.6 How many characters could animate at once?

With the **current CPU pipeline** (deform in JS, upload deformed verts every frame), the limit is CPU cost per character (deformMesh + building buffers) and the bus (upload size × character count). For Sims-style meshes (hundreds to a few thousand verts each), **tens to low hundreds** of characters is typical before frame time or upload becomes the bottleneck.

With **full GPU** (Option B: animations + deformation on GPU, only time or a tiny uniform set per character per frame):

- **CPU** does almost nothing per character: no `Practice.tick`, no `deformMesh`, no vertex upload — just submit compute + draw and maybe update a time or sequence ID.
- **GPU** does: one (or batched) compute pass to evaluate animation → bone matrices, then deformation → deformed buffer, then draw. Compute and draw scale with GPU parallelism; vertex and bone counts per character are small by modern standards.
- **Practical limits** then shift to: **draw calls** (hundreds to a few thousand is fine with batching or multi-draw), **fill rate** (how many pixels of characters on screen), **GPU memory** (all undeformed meshes, skeletons, and animation data resident). Sims-style characters are light: a few KB of mesh + a few dozen bones + keyframes per skill. So **hundreds to thousands** of characters animating at once is in reach on typical hardware — the kind of crowd or busy neighbourhood that would bring a CPU-bound pipeline to its knees. The exact number depends on mesh complexity, resolution, and batching strategy, but the order of magnitude jumps from "tens–hundreds" to "hundreds–thousands" once animation and deformation live on the GPU.

---

## 6. Plumb-bob and static meshes: glTF and plug-in shapes

The plumb-bob is currently a **procedural diamond** (see §1.1). To allow custom plumb-bobs (and other static props) without code changes, support loading from a standard 3D format.

### 6.1 Display list (no per-frame geometry regeneration)

- **Mesh identity:** Procedural meshes (e.g. `createDiamondMesh()`) or loaded meshes (e.g. from glTF) are created or loaded once and stored as `MeshData`.
- **Per frame:** Only the **transform** (position, rotation, scale) is applied each frame via `transformMesh(mesh, x, y, z, rotY, scale)`; the result is passed to `drawMesh(..., objectId?)`. No regeneration of triangles or topology.

### 6.2 Standard format: glTF 2.0

- **Recommendation:** Use **glTF 2.0** (JSON `.gltf` or binary `.glb`) as the standard format for static meshes such as plumb-bobs. It is widely supported, toolable (Blender, glTF viewers), and has a well-defined schema.
- **Loader:** Use a small, engine-agnostic glTF loader that outputs positions, normals, UVs, and indices (e.g. **minimal-gltf-loader** or similar) and convert the result into `MeshData` (vertices, normals, uvs, faces). No need for a full scene graph or PBR; only mesh geometry is required for the plumb-bob use case.
- **Placement:** Add a loader under e.g. `vitamoo/loaders/` that: given a URL or parsed glTF JSON, extracts the first mesh (or a named mesh), and returns `MeshData` compatible with `drawMesh` and `transformMesh`. The default plumb-bob can remain the procedural diamond; an optional config or URL can point to a `.gltf`/`.glb` file to use as the plumb-bob shape instead.

### 6.3 Plug-in plumb-bobs

- **User flow:** Provide a way (config, UI, or asset path) to specify a glTF file for the plumb-bob. At load time, fetch and parse the glTF, convert to `MeshData`, and store it. Each frame, use that mesh with the same display-list path: `transformMesh(plumbBobMesh, x, y, z, rotY, scale)` then `drawMesh(..., objectId?)`. No code change required for new shapes; users can author plumb-bobs in Blender (or any glTF exporter) and drop the file in.

### 6.4 Summary

| Item | Approach |
|------|----------|
| Procedural plumb-bob | `createDiamondMesh()` → cached; draw via transform + `drawMesh`. |
| Display list | `DisplayListEntry`: mesh + transform + color/objectId; run = transform + draw per entry. |
| Custom plumb-bob | Load glTF → `MeshData` once; same transform + draw path. |
| Library | Use a minimal glTF 2.0 JSON (and optionally binary) parser that outputs positions, normals, indices; map to `MeshData`. |

---

## 7. Generalized display list — one format for all drawing

The display list is designed to be **general and powerful enough** to represent every kind of draw: character bodies and accessories, user interface, terrain, floor tiles, walls, wall gap covers, roofs, props, and plumb-bobs. One executor runs the list each frame; each entry type is handled appropriately.

### 7.1 Entry kinds

| Kind | Use case | Per-frame work |
|------|----------|----------------|
| **static** | Plumb-bobs, props, terrain tiles, floor, walls, wall gap covers, roofs | `transformMesh(mesh, transform)` → `drawMesh`. Mesh and topology are fixed; only position/rotation/scale applied. |
| **skinned** | Character bodies, accessories | `deformMesh(mesh, skeleton, boneMap)` then optional world transform → `drawMesh`. Skeleton poses updated by animation; deformation runs each frame. |
| **ui** | Pie menu, HUD, buttons, fullscreen fade | Draw with orthographic/screen-space camera (or NDC). Optional depth; often `layer: 'overlay'` and drawn last. |

- **Transform:** Static and UI entries use `Transform3D` (position + optional rotY + scale) or `Transform3DFull` (position + quaternion rotation + scale) for walls, rotated props, etc. Skinned entries can add an optional world `transform` applied after deformation (e.g. body position and direction).
- **Layer:** `'world'` (default) = depth-tested 3D; `'overlay'` = typically no depth write, drawn after world; or a numeric sort key so the executor can order passes (e.g. terrain → floor → walls → gap covers → roofs → characters → UI).
- **Picking:** Every entry can carry optional `picking` (type, objectId, subObjectId) so the same pass writes object ID for click resolution. For paint-on-skin, see §7.3.

### 7.2 What goes in the list

- **Character bodies and accessories:** Skinned entries (mesh + skeleton + boneMap). One entry per mesh; accessories are just more skinned meshes with the same skeleton. Executor runs `updateTransforms` on the skeleton, then for each skinned entry runs `deformMesh` and `drawMesh` with picking if needed.
- **User interface:** UI entries (quads or meshes) with `layer: 'overlay'`. Ortho camera or NDC; optional texture (icons, menu art). Picking for buttons/menu items.
- **Terrain, floor tiles, walls, wall gap covers, roofs:** Static entries. Mesh is procedural or loaded (e.g. glTF); transform places and orients. Full 3D rotation for walls at any angle. Instancing (same mesh, many transforms) can be a later optimization; initially one entry per instance.
- **Props and plumb-bobs:** Static entries; mesh from procedural or glTF, transform per frame.

The executor’s job: sort by layer, then for each entry dispatch to the right path (static → transformMesh + draw; skinned → deformMesh + draw; UI → ortho/NDC + draw). Same `drawMesh` and color/objectId pipeline for all; only the source of vertices (transformed static, deformed skinned, or UI geometry) and camera (perspective vs ortho) vary.

### 7.3 UV map and texture-ID map for painting on skins

To support **painting on character skins** (and other textured surfaces), the renderer can expose an **optional, enable/disable** pair of buffers:

- **UV map (enable/disable):** When enabled, a third color attachment (e.g. `rg32float`) stores the **interpolated UV** at each pixel. On click, the app reads not only `readObjectIdAt(x, y)` but also `readUVAt(x, y)` → `{ u, v }` in texture space. The paint tool can then draw at `(u, v)` on the correct texture (identified by objectId/subObjectId). When disabled, no UV buffer is allocated and the mesh pass does not write UV; zero cost when not painting.
- **Texture ID map (optional):** Object ID already identifies *which* mesh/part (objectId + subObjectId). To know *which texture* to paint on, the app can map (objectId, subObjectId) to a texture handle or atlas region. If needed, a separate “texture ID” channel could encode atlas tile or texture index in the same pass (e.g. pack in unused bits or a fourth attachment). For most paint tools, objectId + subObjectId + UV are enough: the app maintains the mapping from (objectId, subObjectId) to the skin texture and uses (u, v) for the brush. So “texture ID map” can mean: (1) same as objectId/subObjectId (app resolves to texture), or (2) optional fourth output for atlas/texture index when using atlases. Design choice: start with UV only; add explicit texture/atlas ID in the buffer only if needed.

**Implementation sketch:**

- **Renderer:** `setUVBufferEnabled(true | false)`. When true, `setViewport` creates a third texture (e.g. `r32float` or `rg32float` for u,v); the mesh pass has a third fragment target and writes `vec2f(texCoord)` (and optionally 0 for “no UV”). `readUVAt(screenX, screenY)` returns `Promise<{ u, v } | null>` (null if disabled or out of bounds).
- **Mesh WGSL:** When the pipeline has three targets, fragment output is `struct { color, objectId, uv }`; `uv = vec2f(input.texCoord)` (or 0 if no texture). No change to object ID or color path.
- **Display list:** Entries with `picking.writeUV: true` (or a global “UV capture” mode when painting is active) ensure the pass is run with the UV buffer enabled. So: one format, one list; UV is a render-time option and a readback API, not a new entry type.

This keeps the display list format general: same entries for characters, terrain, UI, etc.; UV and texture-ID are **output options** of the same pass for paint tools, not a separate kind of drawing.

---

## 8. Importing standard JSON 3D formats (skeletons, meshes, animations)

To support external assets and eventually skeletons, deformable meshes, and animations from standard tools (Blender, etc.), we need a well-supported interchange format. Recommendation: **prioritize one format** that can cover static meshes, skinned meshes, and animation, then add loaders that map into vitamoo’s types.

### 8.1 Which format to support

- **glTF 2.0** (`.gltf` JSON or `.glb` binary) is the best choice:
  - **Industry standard:** Khronos, used everywhere (Blender, Unity, Unreal, web).
  - **Single format** for meshes, materials, **skeletons (nodes)**, **skins** (joints + inverse-bind + per-vertex joint indices and weights), and **animations** (channels + samplers over time).
  - **JSON option:** `.gltf` is JSON; `.glb` is binary with an optional JSON chunk. Start with `.gltf` for simplicity; add `.glb` when needed.
  - **Tooling:** Export from Blender/Maya/etc.; validate with glTF viewers and validators.
- **Alternatives (not recommended as primary):**
  - **COLLADA (.dae):** XML, not JSON; heavier; glTF supersedes it for runtime.
  - **FBX:** Binary (or ASCII FBX, not JSON); SDK-heavy; use only if you need direct FBX in the pipeline; otherwise export FBX → glTF from the DCC.
  - **Three.js JSON / legacy formats:** Not a standard; glTF is the replacement.

So: **support glTF 2.0 first** (JSON `.gltf`, then binary `.glb` if desired). It is the standard that contains meshes, skeletons, skins, and animations in one place.

### 8.2 What glTF provides vs what vitamoo uses

| glTF 2.0 | Vitamoo | Notes |
|----------|---------|--------|
| **Mesh** (attributes: POSITION, NORMAL, TEXCOORD_0; indices) | **MeshData** (vertices, normals, uvs, faces) | Direct for static; for skinned, see below. |
| **Node** (tree; translation, rotation, scale; optional mesh, skin) | **SkeletonData** / **BoneData** (name, parentName, position, rotation) | Nodes that are joints → bones; build hierarchy. |
| **Skin** (inverseBindMatrices, joints = node indices) + mesh **JOINTS_0**, **WEIGHTS_0** | **MeshData** (boneNames, boneBindings, blendBindings) + **SkinData** (mesh → bone) | glTF uses **per-vertex** joint indices (e.g. 4) + weights. Vitamoo uses **bone-ranged** bindings + blend bindings. Conversion required (see §8.4). |
| **Animation** (channels: node + path translation/rotation/scale; samplers: input time, output values) | **SkillData** / **MotionData** (boneName, translations[], rotations[], duration) | Map each channel to a Motion; fill shared translation/rotation arrays from samplers. |

### 8.3 Phased support (eventually: static → skinned → animated)

1. **Static meshes (now / first):** Load glTF → extract first (or named) mesh → **MeshData** (vertices, normals, uvs, faces; no bone bindings). Use for plumb-bobs, props, terrain tiles, etc. No skeleton or animation. Easiest; already scoped in §6.
2. **Skeletons and deformable meshes (next):** Load glTF → build **SkeletonData** from nodes that participate in a **Skin** (joints array). For each skinned mesh, convert glTF’s per-vertex JOINTS_0/WEIGHTS_0 into Vitamoo’s **boneBindings** and **blendBindings**, or introduce a “glTF-style” skinning path (vertex shader with joint matrices) and keep two mesh types. Prefer conversion to Vitaboy format so one deformation pipeline stays in place.
3. **Animations (later):** Load glTF **animations** → for each channel (node + path), create **MotionData** (boneName from node name, frames/duration from sampler input, translation/rotation from sampler output); aggregate into **SkillData** with shared translation/rotation arrays. Drive existing **Practice** so glTF-authored clips play on the same skeleton.

### 8.4 Skinning model: glTF vs Vitamoo

- **glTF:** Each vertex has up to 4 joint indices and 4 weights. Deform: `pos = sum(weight[i] * jointMatrix[i] * bindPos)`. Standard and well documented.
- **Vitamoo (Vitaboy):** Bone-ranged: each bone owns a contiguous block of vertices (boneBindings); plus blend bindings that lerp from one bone’s “blended” vertex into another’s. Different layout, same idea (multi-bone influence).

**Conversion (glTF → Vitamoo):** For each bone (joint), find vertices that have that joint in their top-4; assign them to that bone’s binding range. Vertices influenced by multiple joints become blend bindings (dominant bone = bound, others = blended with weight). This approximates glTF skinning with Vitaboy’s model; some quality loss at 4+ influences is acceptable for many assets. Alternative: add a second deformation path that takes glTF-style (joint indices + weights) and joint matrices and runs the usual 4-weight vertex skinning in JS (or later GPU), then feed the same `drawMesh`; then no conversion of mesh layout, only skeleton and animation mapping.

### 8.5 Summary

| Goal | Format | Output types | Phase |
|------|--------|---------------|--------|
| Static meshes (plumb-bobs, props, terrain) | glTF 2.0 (.gltf) | MeshData | First |
| Skeletons + skinned meshes | glTF 2.0 | SkeletonData, MeshData (with bone/blend bindings or glTF-style path) | Next |
| Animations | glTF 2.0 | SkillData, MotionData | Later |

Use **one standard JSON 3D format (glTF 2.0)** and map it into existing vitamoo structures so we can eventually support skeletons, deformable meshes, and animations from Blender and other tools without maintaining multiple interchange formats.

---

This document is the single design reference for the WebGPU renderer and advanced Sims-style features; implementation can be done incrementally.
