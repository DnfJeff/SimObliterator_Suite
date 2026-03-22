# VitaMoo Refactor Plan

## Refactor status

| Phase | Status | Notes |
|-------|--------|--------|
| **0** Setup and baseline | Done | mooshow + vitamoospace exist; pnpm filters in use. |
| **1** Extract runtime state | Done | Stage has bodies, selectedActor, setScene, setCharacterSolo, ContentLoader, animation loop. |
| **2** Rendering and hooks | Done | Hooks (onPick, onHover, onSelectionChange, onHighlight, onPlumbBobChange, etc.), picking, SpinController, SoundEngine. |
| **3** VitaMooSpace.svelte | Done | Single full-page component, scene/actor/character/animation controls, loads `/data/content.json`, api/health placeholder. |
| **4** GitHub Pages | Done | `.github/workflows/pages.yml` builds vitamoo → mooshow → vitamoospace and deploys `vitamoospace/build`. Deploy runs only when `VITAMOOSPACE_PAGES_URL` is set (variable or secret) on that repository. |
| **5** Cleanup and parity | Partial | Legacy standalone `demo/` removed from the tree (recoverable from git history). Optional parity write-up and monorepo migration notes still open. |

Definition of Done: items 1–4 are met. Item 5: demo removal done; parity doc and migration notes remain optional.

**Beyond Phase 5:** WebGPU renderer (see DOCUMENTATION.md §6 Plan for mooshow): object-ID rendering, RGB+alpha+z layered sprites from 3D (for object creation), and one reusable pipeline for holodeck runtime (pre-rendered z-buffered background + real-time characters), Sims object creation tools, and save file viewing/editing.

---

## Goal

The former monolithic viewer was split into three clear layers inside `vitamoo/`:

1. `vitamoo/vitamoo` - low-level animation/data core (no UI, no scene editor logic)
2. `vitamoo/mooshow` - graphics/runtime layer (WebGPU renderer via vitamoo `Renderer`, picking via object IDs, hooks, plumb bob, camera, input adapters)
3. `vitamoo/vitamoospace` - SvelteKit app (single full-page UI, menus/scenes from JSON, mouse interactions, demo orchestration)

This is monorepo-ready without doing the full monorepo move yet.

## Current State

- Core library files live in `vitamoo/vitamoo/*.ts`.
- The browser app is **vitamoospace** (SvelteKit + mooshow + vitamoo `Renderer`). Scene data lives under `vitamoospace/static/data/` (including `content.json`).

## Target Layout (inside `vitamoo/`)

- **vitamoo/** (workspace root)
  - `package.json` — workspace package root (existing)
  - **vitamoo/** — core module (existing)
    - `vitamoo.ts`, …
  - **mooshow/** — graphics module
    - `package.json`, `tsconfig.json`
    - **src/**
      - `index.ts`
      - **runtime/** — `stage.ts` (WebGPU via vitamoo `Renderer.create`, frame loop, bodies), `content-loader.ts`, `types.ts`
      - **interaction/** — `picking.ts`, `spin-controller.ts`, `top-physics.ts`
      - **audio/** — `sound-engine.ts`, `voice.ts`
      - **hooks/** — `types.ts`, `defaults.ts`
  - **vitamoospace/** — SvelteKit app
    - `package.json`, `svelte.config.js`, `vite.config.ts`, `tsconfig.json`
    - **src/**
      - `app.css`, `app.html`
      - **routes/** — `+layout.svelte`, `+page.svelte`
      - **routes/api/health/** — `+server.ts` (placeholder)
      - **lib/components/** — `VitaMooSpace.svelte`, `SceneMenu.svelte`, `ActorMenu.svelte`
      - **lib/stores/** — `scene-state.svelte.ts`, `app-state.svelte.ts`
      - **lib/config/** — `scenes.schema.ts`
    - **static/data/** — `content.json`, demo assets

## Architectural Boundaries

### `vitamoo` (core)

- Responsibilities:
  - parse/write CMX/SKN/BCF/BMF/CFP
  - skeleton transforms and mesh deformation
  - animation timing primitives
- Must not depend on:
  - DOM APIs
  - canvas rendering
  - app menus/UI state
- Public API stays stable and importable by both `mooshow` and tooling.

### `mooshow` (graphics/runtime)

- Responsibilities:
  - WebGPU draw orchestration on a canvas (vitamoo `Renderer`)
  - character instances and scene graph runtime
  - camera controls and viewport resize handling
  - picking/highlighting/plumb bob extension hooks
  - adapter methods for pointer/drag/spin inputs
- Must not own app menus or route-level state.
- Exposes an API that Svelte components can control.

Suggested API shape:

- `createMooShowStage({ canvas, hooks, assetsBaseUrl })`
- `stage.loadContentIndex(contentJson)`
- `stage.setScene(sceneName)`
- `stage.setActor(actorId)`
- `stage.setAnimation(animationName)`
- `stage.start()` / `stage.stop()` / `stage.destroy()`
- `stage.pick(x, y)`
- `stage.spinSelectedActor(delta)`

### `vitamoospace` (SvelteKit app)

- Responsibilities:
  - app shell and full-page layout
  - menu controls (scene/actor/animation/toggles)
  - JSON config loading and app-level state
  - create/destroy `mooshow` stage
  - connect UI actions to stage methods
- No backend behavior yet beyond a server placeholder endpoint.

## SvelteKit App Requirements

1. SvelteKit latest with Svelte 5 runes mode.
2. Single page that fills viewport with one component:
   - `VitaMooSpace.svelte`
3. Simple CSS:
   - root layout full width/height
   - canvas fills main region
   - menu overlay/panel for scene and actor controls
4. Server placeholder:
   - `src/routes/api/health/+server.ts` returns static JSON
   - no persistence, no game logic on server

## Data and Configuration Strategy

- Treat `vitamoospace/static/data/content.json` as the runtime content index (same schema the old viewer used).
- Runtime-consumed assets stay under:
  - `vitamoospace/static/data/`
- Add optional app-facing scene config:
  - `vitamoospace/src/lib/config/scenes.json` (or TS module after schema validation)
- Rule:
  - graphics/runtime reads normalized data handed by app
  - app owns menu labels, scene presets, and UX defaults

## Migration Plan (Phased)

## Phase 0 - Setup and Baseline

1. Create `mooshow` package skeleton with TypeScript build.
2. Create `vitamoospace` SvelteKit app scaffold.
3. Legacy `demo/` folder removed from the tree (recoverable from git history).
4. Add scripts at `vitamoo/` root:
   - build all local packages/apps
   - run vitamoospace dev server

Acceptance:

- `vitamoo` builds as before.
- `mooshow` compiles with empty runtime stubs.
- `vitamoospace` starts and shows a placeholder full-page shell.

## Phase 1 - Extract Runtime State from `viewer.js`

1. Extract non-UI state engine into `mooshow`:
   - bodies list
   - selected actor
   - scene switching
   - animation clock
2. Extract animation loop and camera state into runtime services.
3. Keep rendering logic functionally identical.

Acceptance:

- Old and new paths produce comparable animation playback for basic scenes.

## Phase 2 - Extract Rendering and Interaction Hooks

1. Move renderer wiring into `mooshow/render`.
2. Implement hook interfaces:
   - `onPick`
   - `onHover`
   - `onSelectionChange`
   - `onHighlight`
   - `onPlumbBobChange`
3. Implement spin/drag controller and picking utilities.

Acceptance:

- `mooshow` can run with default hooks and no Svelte UI.
- Selection and spin behavior works through public stage API.

## Phase 3 - Build `VitaMooSpace.svelte`

1. Build a single full-page component with:
   - canvas region
   - scene selector
   - actor selector
   - animation selector
   - toggles for autoplay/spin/highlight
2. Load JSON content from `/data/content.json`.
3. Instantiate `mooshow` on mount and destroy on unmount.
4. Bind UI controls to stage API.

Acceptance:

- App reproduces core playful demo flow: scene selection, character spin, animation changes, picking and highlighting.

## Phase 4 - GitHub Pages Deployment

Update `.github/workflows/pages.yml` to build and deploy the SvelteKit static site
instead of the legacy `vitamoo/dist` demo.

Historical workflow (pre–vitamoospace):

1. `npm ci` in `vitamoo/`
2. `npm run build` (tsc only today; older commits copied a static demo into `dist/`)
3. Upload `vitamoo/dist` to Pages

New workflow:

1. `pnpm install` at repo root (workspace install).
2. Build vitamoo core: `pnpm --filter vitamoo run build`.
3. Build mooshow: `pnpm --filter mooshow run build`.
4. Build vitamoospace static: `pnpm --filter vitamoospace run build`.
   - SvelteKit with `@sveltejs/adapter-static` outputs to `vitamoo/vitamoospace/build/`.
5. Upload `vitamoo/vitamoospace/build/` to Pages.
6. Deploy.

SvelteKit adapter-static config:

- `fallback: undefined` (no SPA fallback; fully prerendered).
- `prerender: { default: true }` in `svelte.config.js`.
- Base path: set via `paths.base` if deployed under a subpath (e.g. `/SimObliterator_Suite`).

Trigger: `push` to `main`/`master` (paths under `vitamoo/` and workflow) and `workflow_dispatch`. Deploy job is skipped unless `VITAMOOSPACE_PAGES_URL` is configured on the repo.

Acceptance:

- Pages site serves the SvelteKit-built app at the same URL as today.
- Static assets (data files, textures) load correctly from `static/data/`.
- Legacy standalone demo is not deployed.

## Phase 5 - Cleanup and Parity Review

1. Compare former `demo/` features against vitamoospace and document parity status (optional).
2. Legacy `demo/` removed from tree; recover from git if required.
3. Add internal migration notes for future monorepo move:
   - `vitamoo` -> `packages/vitamoo`
   - `mooshow` -> `packages/mooshow`
   - `vitamoospace` -> `apps/vitamoospace`

Acceptance:

- New app is the only supported demo path.
- Legacy standalone viewer is not in the working tree.

## Build and Tooling Notes

- Package manager: pnpm workspace already enabled at repo root.
- Inside `vitamoo/`, prefer package-level scripts:
  - `pnpm --filter ./vitamoo build`
  - `pnpm --filter ./mooshow build`
  - `pnpm --filter ./vitamoospace dev`
- Keep browser assets under SvelteKit `static/` for now.

## Risks and Mitigations

1. Risk: behavior drift while splitting `viewer.js`.
   - Mitigation: move logic in small slices with feature checks per phase.

2. Risk: tight coupling between UI code and runtime internals.
   - Mitigation: enforce a narrow `mooshow` stage API and hooks contract.

3. Risk: asset path breakage during SvelteKit migration.
   - Mitigation: keep original filenames and mirror the `content.json` references in `static/data`.

4. Risk: too much rewrite at once.
   - Mitigation: ship vitamoospace first; remove the old tree only after the new path is stable (done).

## Definition of Done

The refactor is complete when:

1. `vitamoo` is a clean low-level module without demo UI responsibilities.
2. `mooshow` owns graphics/runtime/interactions with explicit hooks.
3. `vitamoospace` is a SvelteKit single-page app that fills the viewport and hosts one `VitaMooSpace` component.
4. `vitamoospace` includes a server-side placeholder route with no active backend behavior.
5. The playful spinning scene demo works from `vitamoospace` using JSON scene/content data.
6. GitHub Pages workflow builds and deploys the SvelteKit static site (replacing the legacy demo deployment).
