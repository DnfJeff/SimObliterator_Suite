# SimObliterator monorepo layout and practices

Design for a fresh multi-language monorepo: TypeScript/JavaScript (pnpm), Python, shell scripts, SvelteKit, Blender/Unity, CLI tools, and shared code (e.g. VitaMoo in browser + Node). Informed by central’s best practices without copying its exact structure.

---

## 1. Approaches to multi-language monorepos

### By organization axis

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **Layer-first** | Top-level by role: `apps/`, `packages/`, `tools/` (central-style). Each layer can mix languages inside. | Clear “where do I add X?”. CI can target layers. | Python and TS live in different trees; shared logic is per-app or in a single lib. |
| **Language-first** | Top-level by language: `python/`, `typescript/` (or `js/`), then apps/packages under each. | Each ecosystem has its own tooling and conventions. | Cross-language reuse is explicit “contracts” (e.g. OpenAPI, shared schemas); two build graphs. |
| **Hybrid** | Shared packages in one place (`packages/`), apps grouped by delivery (e.g. `apps/web/`, `apps/cli/`) with each app choosing language(s). | Balances discoverability and reuse. | Need clear rules for “shared TS” vs “shared Python” and where they live. |

**Recommendation for SimObliterator:** Hybrid, with a **layer-first top level** (like central) and **explicit places for Python** so both ecosystems stay consistent.

### By build/task runner

- **pnpm workspaces only** — Root `pnpm-workspace.yaml`; `pnpm -r run build` / `filter` for TS. Python per-app (e.g. `uv`/`pip`/`poetry` in `apps/foo` or `python/`). No shared task DAG.
- **Turborepo** — Task pipeline and caching on top of pnpm; good when many apps share packages and you want `build`/`test` dependency order and cache.
- **Nx** — More structure (project graph, affected, plugins for Python/TS); heavier.

**Recommendation:** Start with **pnpm workspaces + root scripts** (build/test per layer). Add Turborepo later if cache and task ordering become important.

---

## 2. Central practices to reuse (conceptually)

- **apps/** — Deployable applications (SvelteKit, Next, servers, workers). Subdirs can have their own `package.json` and/or `pyproject.toml`/`requirements.txt`.
- **packages/** — Shared libraries consumed by apps/tools. TS packages; no Python “packages” in central’s sense (Python lives inside apps, e.g. `apps/pyvision`).
- **tools/** — Dev/deploy tooling (CLI, generators, one-off scripts with `package.json`).
- **scripts/** — Runnable scripts (some with their own `package.json` for TS, or shell/Python at repo root).
- **.github/workflows** — Path-based triggers (`paths: apps/foo/**`), separate build vs deploy, pnpm cache (`pnpm store path` + `hashFiles('**/pnpm-lock.yaml')`), composite actions where useful.
- **Python** — PEP 8, type hints, Black; per-app deps (requirements.txt or pyproject.toml/poetry); avoid committing credentials; use env/secrets.
- **TypeScript** — Strict typing, ESLint, async/await; pnpm, `preinstall: only-allow pnpm`.
- **Security** — No credentials in repo; secrets in env or secret manager; least privilege.

---

## 3. Recommended top-level layout for SimObliterator

```
SimObliterator_Suite/
├── .github/
│   ├── workflows/          # Path-based triggers, pnpm cache, build/deploy split
│   └── actions/            # Composite actions if needed
├── apps/                   # Deployable applications
│   ├── web/                # SvelteKit (or main web app)
│   ├── api/                # Optional API server (Node/TS or Python)
│   └── ...                 # Other runnable apps (Unity/Blender are “apps” by product)
├── packages/               # Shared TS/JS libraries (pnpm workspace)
│   ├── vitamoo/            # Character animation: browser + Node (shared core)
│   ├── shared-types/       # Shared types/schemas
│   └── ...
├── python/                 # Python as first-class (optional; see 3.1)
│   ├── libs/               # Shared Python packages (installable, e.g. uv/pip -e)
│   │   └── simob_common/
│   └── apps/               # Or: Python “apps” (CLI, services, sister scripts)
│       └── sister_scripts/
├── tools/                  # Dev/deploy CLIs and utilities (TS or Python)
│   └── ...
├── scripts/                # Shell + thin wrappers; can call into apps/tools
│   └── *.sh
├── extensions/             # Blender add-ons, Unity plugins (if you want one place)
│   ├── blender/
│   └── unity/
├── docs/
├── package.json            # Root: pnpm workspace, only-allow pnpm, root scripts
├── pnpm-workspace.yaml
└── README.md
```

**Alternative (no top-level `python/`):** Keep Python inside `apps/` and `tools/` (e.g. `apps/sister-scripts/` with `pyproject.toml`, `tools/some-cli/` with Python). Then you don’t have a separate `python/` tree; same practices apply.

---

## 3.1 Where to put Python

- **Option A — Top-level `python/`:** Use `python/libs/` for shared installable packages and `python/apps/` (or `python/scripts/`) for CLIs and “sister scripts” LLMs call. Single place for `uv`/`poetry` and CI. Good if you have several Python consumers and want one lockfile per app/lib.
- **Option B — Colocated:** Python only under `apps/` and `tools/` (e.g. `apps/sister-scripts/`, `tools/blender-export/`). Matches central (e.g. `apps/pyvision`, `apps/hub/scripts/*.py`). No `python/` at top level.

**Recommendation:** Start with **Option B** (colocated). Add `python/libs/` or top-level `python/` only when you have multiple apps needing the same Python library.

---

## 4. Shared TypeScript: VitaMoo in browser and Node

- Put the **core logic** (animation, data structures, pure logic) in a **package** under `packages/vitamoo/` (or `packages/character-animation/`).
- Build outputs:
  - **Browser:** ESM bundle (e.g. Vite/rollup) used by SvelteKit or a static `apps/web/` (or `apps/viewer/`). No Node-only APIs in this entry.
  - **Node:** Same package, different entry (e.g. `src/node.ts` or `exports` in package.json) or the same ESM with conditional requires so it runs in Node for server-side or scripts.
- Structure example:

```
packages/vitamoo/
├── src/
│   ├── core/           # Shared: types, animation logic, data loading
│   ├── browser.ts      # Browser entry (canvas/DOM, etc.)
│   └── node.ts         # Node entry (optional; file I/O, etc.)
├── package.json        # "exports": { ".": {...}, "./browser": "...", "./node": "..." }
├── tsconfig.json
└── vite.config.ts     # or rollup for browser bundle
```

- Apps:
  - **Browser:** `apps/web` (SvelteKit) or `apps/viewer` depends on `workspace:packages/vitamoo`, imports `vitamoo/browser` or the main export.
  - **Node:** A small `tools/vitamoo-cli` or server in `apps/api` depends on `packages/vitamoo` and uses the node entry or main.

---

## 5. Top-level directories (summary)

| Directory | Purpose |
|-----------|--------|
| `apps/` | Deployable apps: SvelteKit, API server, future Unity/Blender “products” (or links to their projects). |
| `packages/` | Shared TS/JS (pnpm workspace). VitaMoo and other shared libs. |
| `python/` (optional) | Shared Python libs + Python apps; else Python lives in `apps/` and `tools/`. |
| `tools/` | Dev/deploy CLIs and utilities (TS or Python), each with own deps. |
| `scripts/` | Shell scripts and thin wrappers; invoke tools/apps. |
| `extensions/` | Blender add-ons, Unity plugins (optional single place). |
| `.github/` | Workflows (path-based, pnpm cache), composite actions. |
| `docs/` | Design and runbooks (e.g. this file). |

---

## 6. Package manager and root scripts

- **JS/TS:** pnpm only. Root `package.json`: `"preinstall": "npx only-allow pnpm"`, `pnpm-workspace.yaml` listing `packages/*`, `apps/*`, `tools/*`, etc. (exclude non-pnpm trees).
- **Python:** Per-app or per-lib: `pyproject.toml` (with uv or poetry) or `requirements.txt`; virtualenv in `.venv` (gitignored). Prefer one lockfile per app/lib.
- **Root scripts (examples):**
  - `pnpm build` → `pnpm -r --filter './packages/**' run build` then `--filter './apps/**' run build`.
  - `pnpm test` → same with `test`. Optional: add Python `pytest` for `apps/*` or `python/` that have tests.
  - `pnpm build:packages`, `pnpm build:apps`, `pnpm test:packages`, `pnpm test:apps` for granular runs.

---

## 7. GitHub Actions (high level)

- **Path-based triggers:** e.g. `paths: ['apps/web/**', 'packages/vitamoo/**']` for web build; `paths: ['python/**', 'apps/sister-scripts/**']` for Python.
- **Caching:** pnpm store (`pnpm store path`, key from `pnpm-lock.yaml`); optionally Python `pip`/`uv` cache.
- **Build vs deploy:** Separate workflows or jobs; build produces artifacts, deploy consumes them (and secrets).
- **Matrix:** Node version for TS; Python version for Python jobs if needed.

---

## 8. Shell scripts

- **scripts/** at repo root for host-oriented automation (run this app, run tests, one-off migrations). Prefer small, idempotent scripts that call into `apps/` or `tools/`.
- Keep scripts in `apps/<app>/scripts/` when they are owned by that app (e.g. `apps/web/scripts/build.sh`). Same idea as central’s `apps/hub/scripts/`.

---

## 9. Blender / Unity

- **Option A:** Under `extensions/blender/` and `extensions/unity/` so all add-ons/plugins live in one place.
- **Option B:** Under `apps/blender-tools/` and `apps/unity-app/` if you treat them as “apps” with their own build/deploy. Use the same rule everywhere: one home for each, document in README.

---

## 10. Checklist for a fresh start

- [ ] Root `package.json` + `pnpm-workspace.yaml`; `only-allow pnpm`.
- [ ] Create `apps/`, `packages/`, `tools/`, `scripts/`, `docs/`, `.github/workflows/`.
- [ ] Move or create VitaMoo as `packages/vitamoo` with browser + Node reuse.
- [ ] Decide Python placement: colocated in apps/tools vs top-level `python/`.
- [ ] Add one SvelteKit app under `apps/web` (or `apps/simob-web`) and wire it to `packages/vitamoo`.
- [ ] Add at least one workflow: path-based trigger, pnpm install + cache, build (and test if ready).
- [ ] Add a short README and point to this doc for layout and practices.

This keeps SimObliterator consistent with central’s ideas (layer-first, path triggers, cache, security, Python/TS standards) while fitting your mix of TS, Python, SvelteKit, sister scripts, and VitaMoo reuse.
