# WebGPU renderer — context and next pass

**Purpose:** Handoff doc for the WebGPU renderer. The stack is **WebGPU-only**; WebGL has been removed. Use this file to iterate on the next pass.

---

## Canonical design

**Single source of truth:** `vitamoo/docs/WEBGPU-RENDERER-DESIGN.md`

- §1: Current WebGPU surface (what’s implemented).
- §2–3: Advanced features (Sims-style pipeline, terrain/walls/roofs, highlighting, pie menu) — future.
- §4: Implementation order — steps 1 and 2 done; next is step 3 (object-ID) or later steps.
- §5: GPU-side skeletal deformation — later.

---

## Repo and stack

- **Repo:** `SimObliterator_Suite`, subpath `vitamoo/`.
- **Layers:**
  - **vitamoo** (core): `vitamoo/vitamoo/` — parsers, skeleton, `deformMesh`, **Renderer** (WebGPU), **loadTexture**.
  - **mooshow** (runtime): `vitamoo/mooshow/src/` — `MooShowStage`, `ContentLoader`, animation loop; owns canvas and calls renderer.
  - **vitamoospace** (app): SvelteKit app that uses mooshow; no direct renderer use.

---

## Current WebGPU surface (as implemented)

| File | Role |
|------|------|
| `vitamoo/vitamoo/renderer.ts` | Single `Renderer` class. WebGPU only. **Creation:** `Renderer.create(canvas)` returns `Promise<Renderer \| null>`. Methods: `clear`, `fadeScreen`, `setCamera`, `setCulling`, `drawMesh`, `drawDiamond`, `setViewport(x,y,w,h)`, `endFrame()`, `getTextureFactory()`. No `context`; loader uses texture factory. |
| `vitamoo/vitamoo/texture.ts` | `parseBMP(buffer)` (pure). `loadTexture(device, queue, url)` returns `Promise<TextureHandle>` (GPUTexture). BMP → parseBMP → ImageData → createImageBitmap → copyExternalImageToTexture; other formats → fetch → createImageBitmap → same. |

**mooshow usage:**

- `Renderer.create(canvas)` (async); then `renderer.setViewport(0, 0, w, h)`, `loader.setTextureFactory(renderer.getTextureFactory())`.
- Per frame: `clear` or `fadeScreen` → `setCamera` → for each body `drawMesh(mesh, verts, norms, texture)` → `drawDiamond(...)` → `renderer.endFrame()`.
- Texture type: `TextureHandle` (GPUTexture). `BodyMeshEntry.texture` is `TextureHandle | null`.

**Stage render flow:** `_getRenderer()` (resolves renderer promise once) → `fadeScreen` or `clear` → `setCamera` → deform + `drawMesh` → `drawDiamond` → `endFrame`. Depth test and backface culling on.

**Pipelines:** WGSL mesh pass (vertex: position/normal/uv, MVP, lightDir → fragment: diffuse + texture, alpha, fade sentinel). Fullscreen quad for `fadeScreen`. Diamond uses mesh pipeline with solid color (no texture). Depth buffer created in `setViewport`; one encoder/pass per frame, submitted in `endFrame`.

---

## Object-ID buffer (type + 24-bit id per pixel)

Shared ID texture: **1 byte type** (0=none, 1=character, 2=object, 3=wall, 4=floor, …) and **24-bit object id**. Stored as `R32Uint`: `(type << 24) | (objectId & 0x00FFFFFF)`. Any pass (characters, objects, walls, floor tiles) can run an object-ID pass after drawing color; it uses the same depth buffer so only visible pixels get a type/id. See WEBGPU-RENDERER-DESIGN §2.3.

---

## Next pass (choose one and iterate)

- **Step 3 — Object-ID:** Implement/wire `beginObjectIdPass`, `drawMeshObjectId`/`drawDiamondObjectId(type, objectId)`, `readObjectIdAt(x,y)`; then walls/floor/objects when added.
- **Step 4 — Background layer:** z-buffered sprites and/or procedural terrain + floor. See §2.1, §2.2, §4 step 4.
- **Steps 5–8:** Walls/roofs, lighting, highlight/selection/feedback, pie menu. See §3, §4.

No backwards compat or WebGL preservation; move forward only.

---

## Shader reference (current WGSL)

- **Mesh:** `@location(0)` position, `@location(1)` normal, `@location(2)` texCoord. Uniforms: projection, modelView, lightDir, alpha, fadeColor (fade when .r ≥ 0), hasTexture. Fragment: diffuse + texture or untextured gray.
- **Fullscreen quad:** NDC positions; fragment solid color (fade). No texture.
- **Diamond:** Same mesh pipeline, solid color, no texture.

---

## What is out of scope (until we choose that step)

- Object-ID pass, picking buffer, layered sprites (step 3).
- Terrain, floors, walls, roofs, display-list pipeline (steps 4–5; see obliterator-designs).
- GPU-side skeletal deformation (§5).
- Highlight/selection/feedback uniforms, pie menu (steps 7–8).
- Animation/deformation still CPU: `deformMesh` → upload deformed verts each frame.

---

## Related design docs (for later)

- **obliterator-designs/designs/04-DISPLAY-LISTS-AND-GPU-RESOURCES.md** — Display lists + resource pools (terrain, tiles, walls, roofs, sprites).
- **obliterator-designs/designs/05-SIMS1-WORLD-RENDER-LAYERS.md** — Sims draw order (static → dynamic → 3D people).
- **vitamoo/REFACTOR-PLAN.md** — Refactor status.
