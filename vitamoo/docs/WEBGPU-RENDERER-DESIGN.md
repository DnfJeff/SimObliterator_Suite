# WebGPU renderer: upgrade and advanced features

Design for replacing the current WebGL renderer with a WebGPU-only backend and extending it to support Sims-style holodeck rendering: z-buffered sprites, procedural terrain and architecture, and UI feedback (highlighting, selection, pie menu).

---

## 1. WebGL to WebGPU upgrade

### 1.1 Current surface (vitamoo)

All GPU use is in **vitamoo**:

| File | Role |
|------|------|
| `vitamoo/renderer.ts` | Single `Renderer` class, WebGL 1 context, one vertex + one fragment shader (GLSL). Methods: `clear`, `fadeScreen`, `setCamera`, `setCulling`, `drawMesh`, `drawDiamond`, `loadTexture`. Exposes `context` (WebGLRenderingContext) for texture upload. |
| `vitamoo/texture.ts` | `parseBMP` (pure); `loadTexture(url, gl)` creates and uploads a WebGLTexture. |

**mooshow** uses only: `new Renderer(canvas)`, then `clear`, `setCamera`, `context.viewport(…)`, `fadeScreen`, `drawMesh`, `drawDiamond`, and `loader.setGL(renderer.context)` so the content loader can create textures. No other WebGL calls.

### 1.2 Target WebGPU surface

- **Device/queue:** `navigator.gpu.requestAdapter()` → `adapter.requestDevice()`; use one `GPUDevice` and its default `queue` for the lifetime of the renderer.
- **Canvas:** `canvas.getContext('webgpu')`, configure with `device`, `format`, and optional `alphaMode`. Resize and get current texture each frame.
- **Shaders:** WGSL. One or more shader modules; at least:
  - **Mesh pass:** vertex (position, normal, uv, MVP, light direction) → fragment (diffuse + texture, alpha, optional fade color). Matches current GLSL behavior.
  - **Fullscreen quad pass:** for `fadeScreen` (motion blur overlay).
  - **Diamond (plumb bob):** same mesh pipeline with solid color and no texture; or a tiny dedicated pipeline.
- **Pipelines:** `GPURenderPipeline` for mesh, for fullscreen quad, and for diamond if separate. Shared bind group layout for uniforms (projection, modelView, lightDir, alpha, fadeColor, texture).
- **Buffers:** `GPUBuffer` for vertex/index data. Uniforms in a small `GPUBuffer` updated each frame (or per draw). No long-lived vertex buffers for dynamic meshes unless we adopt staging buffers and copy.
- **Textures:** `loadTexture` becomes `loadTexture(device, url)` (or `device` + queue), returns `GPUTexture` (or an opaque handle the renderer accepts in `drawMesh`). Upload via `queue.copyExternalImageToTexture` from `createImageBitmap` or from decoded BMP data.
- **Public API preserved:** `clear`, `setCamera`, `setViewport` (method on renderer, no raw context), `fadeScreen`, `drawMesh(mesh, verts, norms, texture)`, `drawDiamond(…)`. Callers (mooshow stage, content-loader) receive a device or a texture-upload interface instead of `gl`; they never touch WebGPU objects except through the renderer.

### 1.3 Shader migration (GLSL → WGSL)

- **Vertex:** `aPosition`, `aNormal`, `aTexCoord` → `@location(0)` position, `@location(1)` normal, `@location(2)` texCoord. Output position, uv, normal to fragment. Uniforms: `uProjection`, `uModelView` (or single `uModelViewProjection`).
- **Fragment:** `vTexCoord`, `vNormal` from vertex; `uniform sampler2D uTexture`, `uniform bool uHasTexture`, `uLightDir`, `uAlpha`, `uFadeColor`. Same math: if `uFadeColor` is “use fade” sentinel, output fade color; else diffuse + texture or untextured gray. WGSL uses `textureSample`, `textureSampleLevel`, and `@binding`/`@group` for texture and sampler.
- **Fullscreen quad:** vertex outputs NDC position and optional uv; fragment samples nothing (solid color) for fadeScreen. Uniform: clear color + alpha.
- **Entry points:** `@vertex` and `@fragment` per pipeline.

### 1.4 Phases

1. **Parity:** Replace `renderer.ts` and `loadTexture` with WebGPU; keep the same public API and behavior (skinned mesh, motion blur, plumb bob). No new features. mooshow passes device (or renderer’s texture factory) to the loader; viewport set via `renderer.setViewport`.
2. **Object-ID and layered sprites (optional next):** Add a second pass or alternate pipeline that writes object ID (e.g. R32Uint or packed RGB) for picking and for baking RGB+alpha+z layers for object authoring.
3. **Advanced features:** Sims-style pipeline, procedural architecture, and UI shader effects (below).

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

### 2.3 Object-ID and picking

- **ID pass:** Optional render pass that writes a stable object ID per pixel (e.g. integer in R or RGB). Read back on click or sample in a small region to resolve which object was picked. Supports both procedural geometry and sprites if we assign IDs consistently.
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

## 4. Implementation order (suggested)

1. **WebGL → WebGPU parity** (renderer + texture, same API, no new features).
2. **setViewport** and loader texture interface (device or factory) so mooshow and vitamoospace work unchanged.
3. **Object-ID pass** (optional) for picking and future baking.
4. **Background layer:** z-buffered sprites and/or procedural terrain + floor (minimal: grid + height + one tile texture).
5. **Walls and roofs** (procedural or tiled in shaders).
6. **Lighting** (ambient + directional in fragment).
7. **Highlight / selection / feedback** (uniforms + one small overlay pass if needed).
8. **Pie menu** (desaturated bg, feather, shadow) when the app adds a pie UI.

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

This document is the single design reference for the WebGPU upgrade and advanced Sims-style renderer features; implementation can be done incrementally with AI-assisted development and typically shortens the calendar time (e.g. full refactor in a few days with AI assist).
