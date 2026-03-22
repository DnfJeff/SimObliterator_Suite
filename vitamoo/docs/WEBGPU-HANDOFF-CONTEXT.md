# WebGPU renderer — context and next pass

**Purpose:** Handoff doc for the vitamoo WebGPU **`Renderer`**: a framework meant to support broader Sims content and plug-ins (UI, visualization, editors); character animation is the first integrated slice. Use this file to iterate on the next pass.

---

## Canonical design

**Single source of truth:** `vitamoo/docs/WEBGPU-RENDERER-DESIGN.md`

- §1: Current WebGPU surface (what is implemented).
- §2–3: Advanced features (Sims-style pipeline, terrain/walls/roofs, highlighting, pie menu) — mostly future.
- §4: Holodeck implementation order (steps 1–3 done; next is step 4 onward).
- §5: GPU-side skeletal deformation — not started; parallel track to §4.

---

## Status snapshot (matches tree)

| Area | State |
|------|--------|
| WebGPU draw path (WGSL mesh, depth, fade, plumb-bob) | Done |
| Textures (`loadTexture`, `getTextureFactory`, mooshow loader) | Done |
| Object-ID buffer + `readObjectIdAt`; mooshow picking | Done |
| CPU animation | `Practice.tick`, `updateTransforms`, `deformMesh` in JS; deformed verts uploaded every frame |
| GPU skeletal deformation / compute | Not started (see §5) |
| Holodeck background (terrain, sprites, walls) | Not started (§4 steps 4–5) |
| Highlight / selection tint in app | WGSL has `highlight` + `ambient` uniforms; mooshow does not expose setters yet (defaults only) |

---

## Repo and stack

- **Repo:** `SimObliterator_Suite`, subpath `vitamoo/`.
- **Layers:**
  - **vitamoo** (core): `vitamoo/vitamoo/` — parsers, skeleton, `deformMesh`, **Renderer** (WebGPU), **loadTexture**, `display-list.ts`, `procedural/diamond.ts`, `loaders/gltf.ts`.
  - **mooshow** (runtime): `vitamoo/mooshow/src/runtime/stage.ts` — stage loop, `Renderer.create`, `readObjectIdAt` for pick/hover, `setDebugSlice` for debug views.
  - **vitamoospace** (app): SvelteKit demo; no direct renderer use.

---

## Current WebGPU surface (as implemented)

| File | Role |
|------|------|
| `vitamoo/vitamoo/renderer.ts` | `Renderer.create(canvas)` → `Promise<Renderer \| null>`. `clear`, `fadeScreen`, `setCamera`, `setCulling`, `drawMesh(…, objectId?)`, `drawDiamond(…, objectId?)`, `setViewport`, `endFrame`, `getTextureFactory`, `readObjectIdAt`, `setDebugSlice`, `setPlumbBobMeshes`, `setPlumbBobScale`. Dual color attachments: **attachment 0** `rgba32uint` (object id), **attachment 1** surface color. |
| `vitamoo/vitamoo/texture.ts` | `parseBMP`; `loadTexture(device, queue, url)` → `TextureHandle` (`GPUTexture`). |

**mooshow:** `Renderer.create` → `setViewport`, `setTextureFactory`. Each frame: clear/fade → `setCamera` → per body `deformMesh` then `drawMesh` with `ObjectIdType` / body index / mesh index → plumb-bob draws → `endFrame`. Picking: `readObjectIdAt` (character and plumb-bob types). `setDebugSlice` wired from stage config / URL.

**Object-ID layout:** Matches §2.3 of the design doc: `vec4u(type, objectId, subObjectId, 0)` in the uint attachment (see `ObjectIdType` in vitamoo exports).

---

## Recommended next steps

Pick one track and ship a vertical slice.

**Holodeck track (§4 step 4+)**  
1. **Background layer:** First procedural or z-buffered background draw before characters (same depth buffer): minimal grid/quad + one texture, or one sprite path.  
2. **Walls/roofs** when the background path is stable.  
3. **§4 steps 6–8:** Expose lighting/highlight APIs on `Renderer` and drive hover/selection from mooshow; pie menu when the app needs it.

**Performance track (§5)**  
1. **GPU deformation (Option A):** Keep `Practice` on CPU; upload bone matrices each frame; compute shader (or staged compute) implements vitamoo’s Phase 0 / Phase 1 / blend model; draw from GPU-resident deformed buffer instead of streaming full vertex arrays from JS.  
2. **Option B** (later): move animation evaluation to GPU.

**Small polish**  
- Remove or gate verbose `readObjectIdAt` logging in `renderer.ts` if it is still noisy in production.  
- Optional: bone-level id in the object-ID buffer (§2.3 TODO) for mesh-part picking.

---

## Shader reference (current WGSL)

- **Mesh:** Positions/normals/UVs; uniforms include projection, modelView, lightDir, alpha, fadeColor, hasTexture, ambient, diffuseFactor, highlight (vec4), idType/objectId/subObjectId, debugMode. Fragment writes object-id output and color output; diffuse + texture; highlight mix when `highlight.a > 0`.
- **Fullscreen quad:** Fade only; writes zero object id where dual-target is active.
- **Diamond:** Mesh pipeline branch, solid color, optional object id.

---

## What is still out of scope until built

- Holodeck terrain, floors, walls, roofs, layered sprite authoring pipeline.
- GPU-side skeletal deformation and GPU-resident animation (§5).
- Pie menu passes (desaturate, vignette) and head-in-pie wiring in the app.
- Display-list **executor** that consumes `DisplayListEntry[]` for the whole scene (types exist; stage still loops bodies explicitly).

---

## Related design docs

- **obliterator-designs/designs/04-DISPLAY-LISTS-AND-GPU-RESOURCES.md** — Display lists + resource pools.
- **obliterator-designs/designs/05-SIMS1-WORLD-RENDER-LAYERS.md** — Sims draw order.
- **vitamoo/REFACTOR-PLAN.md** — Broader refactor status.
