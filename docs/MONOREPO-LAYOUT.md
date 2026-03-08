# SimObliterator monorepo layout and practices

Design for a fresh multi-language monorepo: TypeScript/JavaScript (pnpm), Python, shell scripts, SvelteKit, Blender/Unity, CLI tools, and shared code (e.g. VitaMoo in browser + Node). Informed by central’s best practices without copying its exact structure.

**Repo setup:** Single remote (origin). Push and pull from origin only.

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
├── skills/                 # MOOLLM-compatible skills (CARD, GLANCE, SKILL; sister scripts TS/Python)
│   └── <skill-name>/       # lib/, scripts/, optional package.json or pyproject.toml
├── docs/
├── package.json            # Root: pnpm workspace, only-allow pnpm, root scripts
├── pnpm-workspace.yaml
└── README.md
```

**Alternative (no top-level `python/`):** Keep Python inside `apps/` and `tools/` (e.g. `apps/sister-scripts/` with `pyproject.toml`, `tools/some-cli/` with Python). Then you don’t have a separate `python/` tree; same practices apply.

---

## 3.1 Where to put Python (Option A vs B) and where apps go

**Option A — Top-level `python/` (hybrid layer-first):**

- **`python/libs/`** — Shared installable Python packages (e.g. `simob_common`). Consumed by CLI, web server, Blender, and browser (Pyodide).
- **`python/apps/`** — Python-only runnables: CLIs, sister scripts (LLM-callable), small Python services. Each has its own `pyproject.toml` and depends on `python/libs/` as needed.
- **`apps/`** — Deployable products (layer unchanged): SvelteKit in `apps/web/`, API server in `apps/api/` (Node/TS or Python), Unity in `apps/unity-mygame/`, etc. These can depend on `packages/` (TS) and, if Python, on `python/libs/` (e.g. `apps/api/` as a Python service).
- **`tools/`** — Dev/deploy utilities (TS or Python). Can depend on `packages/` or `python/libs/`.

So with Option A you keep **layers**: `apps/` = products (web, API, Unity), `packages/` = shared TS, `python/libs/` = shared Python, `python/apps/` = Python runnables (CLI/sister scripts), `tools/` = dev tooling. Many app types; one clear home per kind.

**Option B — Colocated Python:** No `python/` at top level. Python lives only inside `apps/<name>/` and `tools/<name>/` (e.g. `apps/api/`, `tools/sister-scripts/`). Shared Python is either a subpackage inside one app (and others depend on it via path) or duplicated. Matches central (e.g. `apps/pyvision`).

**Recommendation:** If you have **shared Python across CLI, web server, and Blender**, use **Option A**. Otherwise start with Option B and add `python/` when you have multiple consumers.

---

## 3.2 Where do Blender plugins go?

Two common choices:

| Place | Example | Advantages | Disadvantages |
|-------|---------|------------|----------------|
| **extensions/blender/** | `extensions/blender/simob-export/` | Clear “this is an add-on, not a standalone app”. One place for all Blender/Unity plugins. Fits “extensions” as things that plug into host apps. | “Apps” (apps/) and “extensions” (extensions/) are different concepts; CI may treat them differently. |
| **apps/** | `apps/blender-addons/simob-export/` or `apps/blender-simob-export/` | Everything deployable lives under apps/. Same CI pattern (build/test per app). Good if you version and ship Blender add-ons like products. | Blender add-ons are not “apps” in the same sense as a web app; mixing can blur the line. |

**Recommendation:** Use **extensions/blender/** (and **extensions/unity/**) so “deployable product” (apps/) stays distinct from “plugin for another app” (extensions/). Use **apps/** for Blender/Unity only if you want a single “all products live here” rule and are fine treating add-ons as apps in CI.

---

## 3.3 Shared Python across CLI, web server, and Blender

When the same Python modules are used in CLI tools, a web server, and Blender add-ons:

- **Put shared packages in `python/libs/`** (e.g. `python/libs/simob_common/`). Each lib has its own `pyproject.toml` and is installable via `uv pip install -e python/libs/simob_common` or equivalent.
- **Consumers:**
  - **CLI / sister scripts:** `tools/<name>/` or `python/apps/sister_scripts/` — add the lib as a dependency (path or editable install).
  - **Web server:** `apps/api/` (or a Python service under `apps/`) — same; install from `python/libs/` or from a built wheel.
  - **Blender:** `extensions/blender/<addon>/` — Blender’s Python can load from a venv or a path that includes `python/libs/`; document the addon’s dependency on the monorepo libs (e.g. “add this repo path to `sys.path`” or install the package into Blender’s Python).
- Keep each lib **pure Python** or use only dependencies that work in all three environments (CLI = system/uv Python; web = same or container; Blender = Blender’s bundled Python). If a lib needs C extensions, ensure they build for Blender’s Python version or provide a pure fallback.

---

## 3.4 Option A vs B vs C — comparison

| Option | Python | Blender/Unity | Pros | Cons |
|--------|--------|----------------|------|------|
| **A** | Top-level `python/` (`python/libs/`, `python/apps/`) | `extensions/blender/`, `extensions/unity/` | One place for shared Python; CLI, web, Blender, browser all consume `python/libs/`. Clear split: TS in `packages/` and `apps/`, Python in `python/`. Single CI story for Python. | Two “runnable” trees: `apps/` (products) and `python/apps/` (Python CLIs/sister scripts). New contributors must learn both. |
| **B** | Colocated in `apps/` and `tools/` only | `extensions/blender/`, `extensions/unity/` | Single `apps/` tree; no top-level `python/`. Simple. Matches repos that keep Python inside app dirs (e.g. central). | Shared Python is awkward: either one app “owns” the lib and others depend by path, or code is duplicated. No single place for “all Python libs”; CI must discover Python per app. |
| **C** | Same as A or B | **In `apps/`** (e.g. `apps/blender-addons/`, `apps/unity/`) | All deployables under one roof. “If we ship it, it’s in apps/.” Same build/deploy pattern for web, Unity, and Blender add-ons. | Blender add-ons are plugins, not standalone apps; putting them in apps/ can blur that. `extensions/` is unused or repurposed. |

**Summary:** Prefer **A** when you have (or will have) shared Python across CLI, web, and Blender. Prefer **B** when Python is per-app and you want minimal structure. Choose **C** only if you want “everything we ship lives in apps/” and are okay treating Blender/Unity add-ons as apps in CI and docs.

---

## 3.5 Python in the browser (WASM)

You can run **the same Python code in the browser** without translating it to TypeScript, using WebAssembly.

- **[Pyodide](https://pyodide.org/)** — CPython compiled to WebAssembly. Runs in the browser (and Node). Use Python as-is; load it from your SvelteKit app (or static HTML). Supports many PyPI packages (pure Python or pre-built wheels); has a JS ↔ Python bridge, async, and access to Web APIs. First load can be large (~several MB); use CDN or self-host.
- **[PyScript](https://pyscript.net/)** — Higher-level platform built on Pyodide (and MicroPython). Simplifies embedding: e.g. `<script type="py">` in HTML, or load from a CDN. Good for quick integration; Pyodide for more control (bundlers, custom loading).

**Implications for the monorepo:**

- Put **browser-runnable Python** in `python/libs/` (or a dedicated `python/libs/simob_browser/`) so the same code can be:
  - Imported by CLI and web server (normal Python).
  - Loaded in the browser via Pyodide (e.g. fetch the .py file or bundle it, then `pyodide.runPython()` or micropip install).
- Prefer **pure Python** for browser use; C extensions must be ported to Pyodide or avoided. See [Pyodide – Loading packages](https://pyodide.org/en/stable/usage/loading-packages.html) and [Building packages for Pyodide](https://pyodide.org/en/stable/development/building-packages.html).
- In `apps/web/` (SvelteKit): load Pyodide from CDN or static assets, then run your lib code (or expose a small Python entry that imports from your shared lib). Optionally use PyScript for simpler `<script type="py">` if you don't need a bundler.

---

## 3.6 MOOLLM compatibility (skills, sister scripts, pnpm, Python venv)

This repo is **MOOLLM-compatible**: it has a **`skills/`** directory. Each skill follows the usual MOOLLM layout (CARD.yml, GLANCE.yml, SKILL.md; entry script and logic in `lib/` or `scripts/`). Skills may ship **sister scripts** in Python and/or TypeScript (CLIs or utilities invoked by the skill or by agents).

### TypeScript sister scripts — pnpm

Use **pnpm** for all TypeScript so building and running TS CLIs is easy and fast.

- **pnpm workspace:** List `skills/<name>` (and/or `tools/<name>`) in `pnpm-workspace.yaml` so each skill or tool that has a TS CLI is its own package with its own `package.json`. pnpm uses a **single content-addressable store** and **symlinks per package**: each package has its own `node_modules`, but dependency files are shared (hard-linked or symlinked from the store). So you get independent `node_modules` per package with no duplication — fast installs and low disk use.
- **Where to put TS sister scripts:** Either (1) **inside the skill** — `skills/<name>/package.json`, `scripts/` or `src/` under the skill, and the skill is a workspace package; or (2) **in `tools/`** — e.g. `tools/<skill-cli>/` with the skill’s CARD/SKILL referencing it (`pnpm --filter <skill-cli> run …`). Prefer (1) when the script is clearly owned by that skill; (2) when the script is shared across skills or is a general dev tool.
- **Recommendation:** Use pnpm; include skill packages in the workspace when a skill ships a TS CLI so `pnpm install` and `pnpm -r run build` stay simple and efficient.

### Python venv — one per skill vs one per repo

| Approach | Pros | Cons |
|----------|------|------|
| **One repo-wide venv** (e.g. `python/.venv` or root `.venv`) | Single place to install deps and run tests; simple CI; easy to use from scripts; `python/libs/` installed editable once. | Two skills needing different versions of the same lib must resolve at repo level (pin one version or use optional deps). |
| **One venv per skill** | Full isolation; no cross-skill dependency conflicts. | Many venvs, more disk and CI work; sharing `python/libs/` requires each skill to install it (path or editable). |

**Recommendation:** Use **one repo-wide Python venv** for the monorepo (and for all skills). Install shared code from `python/libs/` editable; add skill-specific dependencies to a root `pyproject.toml` (optional dependency groups or a single dev dependency list) or to a small number of shared envs (e.g. one for “CLI/skills”, one for “Blender” if needed). If a skill ever needs true isolation (e.g. conflicting dependency versions), document that it may use its own `skills/<name>/.venv` as an escape hatch; do not adopt per-skill venvs by default.

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

- **extensions/** — `extensions/blender/`, `extensions/unity/`. Use when you want “plugins for host apps” separate from “deployable products” (apps/). See §3.2.
- **apps/** — `apps/blender-addons/`, `apps/unity-mygame/`. Use when you want “everything we ship is under apps/” (Option C in §3.4). One home for each; document in README.

---

## 10. Checklist for a fresh start

- [ ] Root `package.json` + `pnpm-workspace.yaml`; `only-allow pnpm`.
- [ ] Create `apps/`, `packages/`, `tools/`, `scripts/`, `docs/`, `.github/workflows/`.
- [ ] Move or create VitaMoo as `packages/vitamoo` with browser + Node reuse.
- [ ] Decide Python placement: colocated in apps/tools vs top-level `python/` (use `python/libs/` when sharing across CLI, web, Blender).
- [ ] Add one SvelteKit app under `apps/web` (or `apps/simob-web`) and wire it to `packages/vitamoo`.
- [ ] Optionally add Pyodide/PyScript in `apps/web` to run shared Python libs in the browser without rewriting to TS.
- [ ] Add at least one workflow: path-based trigger, pnpm install + cache, build (and test if ready).
- [ ] Add a short README and point to this doc for layout and practices.

This keeps SimObliterator consistent with central’s ideas (layer-first, path triggers, cache, security, Python/TS standards) while fitting your mix of TS, Python, SvelteKit, sister scripts, and VitaMoo reuse.
