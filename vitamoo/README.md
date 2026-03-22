# VitaMoo

**VitaMoo** is a **Sims 1**-style animation and asset stack: parse CMX/SKN/CFP, drive skeletons, deform meshes. The **WebGPU `Renderer`** (WGSL) is a **framework** aimed at rendering **more than characters** over time—other Sims content types, tooling, and **plug-ins** such as custom UI and data visualization—with **skinned character animation** as the **first** integrated slice. No game engine: TypeScript and a small layered stack you can reuse or replace.

## What’s in this directory

| Layer | Role |
|-------|------|
| **vitamoo/** | Core: parsers, skeleton math, mesh deformation, animation ticks. No DOM, no canvas. |
| **mooshow/** | Graphics/runtime: WebGPU stage (`Renderer.create`), camera, object-ID picking, spin input, hooks for UI (selection, plumb bob, keys). Depends on `vitamoo`. |
| **vitamoospace/** | SvelteKit app: full-page demo, scene/character/animation menus, one `VitaMooSpace` component that uses `vitamoo` + `mooshow`. |

Scenes and characters come from a **content index** (e.g. `content.json`) plus CMX/SKN/BMP/CFP assets. Bodies are an array of characters; the loader fills it from a scene or from one character by index. The app can use a current character index (e.g. -1 for “all” in the UI).

## Quick start

From the repo root (pnpm workspace):

```bash
pnpm install
pnpm --filter vitamoo run build
pnpm --filter mooshow run build
pnpm --filter vitamoospace run build
pnpm --filter vitamoospace run preview
```

Open the preview URL (e.g. `http://localhost:4173/`) for the Spin the Sims demo.

## Use only what you need

- **Data/tooling only:** depend on `vitamoo` for parsing and skeleton/mesh/animation logic; bring your own renderer.
- **Browser viewer with your UI:** depend on `mooshow`; create a stage, load a content index, wire hooks to your components.
- **Full demo:** use or fork `vitamoospace`; swap assets and content index to rebrand.

See **DOCUMENTATION.md** in this directory for full API and layer boundaries, data formats, and how to extend or build on top.
