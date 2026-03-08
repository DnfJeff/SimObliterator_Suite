# SimObliterator monorepo layout and practices

Design for a fresh multi-language monorepo: TypeScript/JavaScript (pnpm), Python, shell scripts, SvelteKit, Blender/Unity, CLI tools, and shared code (e.g. VitaMoo in browser + Node). Informed by central’s best practices without copying its exact structure.

**Repo setup:** Single remote (origin). Push and pull from origin only.

### Decisions made (summary)

| Area | Decision |
|------|----------|
| **Layout** | Hybrid layer-first: `apps/`, `packages/`, `tools/`, `scripts/`, `skills/`, optional `python/` with `python/libs/`, `python/apps/`. Blender/Unity in `extensions/`. |
| **JS/TS** | pnpm at repo root; workspace includes `packages/*`, `apps/*`, `tools/*`, `skills/*`. Start with pnpm only; add Turborepo later if needed. |
| **Python venv** | One repo-wide venv at **root** (`.venv`), same level as `package.json`. Used by `scripts/`, `apps/`, `tools/`, **skills/** (MOOLLM skill CLIs). |
| **Scripts** | All Python CLIs (arg parsers, imports, thunks into modules) in top-level `scripts/` only; modules in `python/` have no CLI—pure library code. Self-documenting, sniffable sister scripts in one place. Root `.venv`. |
| **Skills** | MOOLLM-compatible `skills/` with CARD, GLANCE, SKILL; entry in `scripts/<cli>.py` or `<name>.py`, logic in `lib/`. Share root venv. |
| **Shared Python** | `python/libs/` = modules; `python/apps/` = runnables; optional `python/blender/`. Scripts import via editable install (e.g. `pip install -e python/libs/foo`). |
| **Python WASM (browser)** | Pyodide in SvelteKit client; layer libs into browser-safe **core** (runs in Pyodide + normal Python) and optional **server/node** (I/O, native deps—not loaded in browser). Pluggable backends; `sys.platform == 'emscripten'` to guard. |

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
- **scripts/** — Monorepo-wide runnables (Python preferred, or shell); use root `.venv` for Python.
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
├── python/                 # Python libs and apps (optional; see 3.1); scripts/ import from here
│   ├── libs/               # Shared modules (pip install -e python/libs/foo); scripts use these
│   │   └── simob_common/
│   ├── apps/               # Python runnables (sister scripts, services); not top-level CLIs
│   │   └── ...
│   └── blender/            # Optional: Blender-specific modules (python/blender/bar)
├── tools/                  # Dev/deploy CLIs and utilities (TS or Python)
│   └── ...
├── scripts/                # Monorepo-wide runnables (Python preferred, or shell); use root .venv
│   └── *.py, *.sh
├── extensions/             # Blender add-ons, Unity plugins (if you want one place)
│   ├── blender/
│   └── unity/
├── skills/                 # MOOLLM-compatible skills (CARD, GLANCE, SKILL; sister scripts TS/Python)
│   └── <skill-name>/       # lib/, scripts/, optional package.json or pyproject.toml
├── docs/
├── .venv/                  # Repo-wide Python venv (same level as pnpm); scripts/, apps, tools, skills/ all use it
├── package.json            # Root: pnpm workspace, only-allow pnpm, root scripts
├── pnpm-workspace.yaml
└── README.md
```

**Alternative (no top-level `python/`):** Keep Python inside `apps/` and `tools/` (e.g. `apps/sister-scripts/` with `pyproject.toml`, `tools/some-cli/` with Python). Then you don’t have a separate `python/` tree; same practices apply.

---

## 3.1 Where to put Python (Option A vs B) and where apps go

**Option A — Top-level `python/` (hybrid layer-first):**

- **`python/libs/`** — Shared installable Python packages (e.g. `simob_common`, `foo`). Reusable modules consumed by scripts, web server, Blender, and browser (Pyodide). Install into root venv: `pip install -e python/libs/foo`.
- **`python/apps/`** — Python-only runnables that are not top-level CLIs: sister scripts (LLM-callable), small services. Each has its own `pyproject.toml` and depends on `python/libs/` as needed. Optional: **`python/blender/`** for Blender-specific modules (e.g. `python/blender/bar`) if you want them separate from libs.
- **Top-level `scripts/`** — All monorepo-wide **Python CLI tools** (management, CI/CD, build helpers) live here. They import from `python/libs/` (and, if needed, from `python/apps/` or `python/blender/`). Run with root `.venv`; after `pip install -e python/libs/foo`, a script does `from foo import ...` or `import foo.bar`. So: CLIs = `scripts/*.py`; reusable code = `python/libs/`, `python/apps/`, optionally `python/blender/`.
- **`apps/`** — Deployable products (layer unchanged): SvelteKit in `apps/web/`, API server in `apps/api/` (Node/TS or Python), Unity in `apps/unity-mygame/`, etc. These can depend on `packages/` (TS) and, if Python, on `python/libs/` (e.g. `apps/api/` as a Python service).
- **`tools/`** — Dev/deploy utilities (TS or Python). Can depend on `packages/` or `python/libs/`.

So with Option A you keep **layers**: **CLI entry points** in top-level `scripts/`; **reusable Python** in `python/libs/`, `python/apps/`, and optionally `python/blender/`; deployable products in `apps/`; shared TS in `packages/`; dev tooling in `tools/`. Scripts import from `python/libs/foo`, `python/apps/bar`, or `python/blender/bar` via the venv (editable install) or PYTHONPATH.

**CLI in one place; modules stay CLI-free.** The whole CLI layer—argument parsers, imports, and thunks into the real logic—lives in **`scripts/`** only. Modules in `python/libs/`, `python/apps/`, and `python/blender/` do **not** define their own CLI (no `if __name__ == "__main__"` with argparse there); they are pure library code. Each script in `scripts/` is the single entry point: it parses args, imports from the modules, and calls into them. That keeps all invocable, self-documenting, **sniffable** Python sister scripts (MOOLLM/sniffable-python style) in one place; the modules stay importable and testable without any CLI surface.

**Option B — Colocated Python:** No `python/` at top level. Python lives only inside `apps/<name>/` and `tools/<name>/` (e.g. `apps/api/`, `tools/sister-scripts/`). Shared Python is either a subpackage inside one app (and others depend on it via path) or duplicated. Matches central (e.g. `apps/pyvision`).

**Recommendation:** If you have **shared Python across CLI, web server, and Blender**, use **Option A**. Otherwise start with Option B and add `python/` when you have multiple consumers.

### 3.1.1 Why `packages/` for TS but a top-level `python/` (no `ts/`)? Sharing level and ecosystem differences

**Why the asymmetry?**

- **TypeScript/JS** is organized by **layer** at the top level: shared code lives in `packages/`, runnables in `apps/` and `tools/`. There is no top-level `ts/` or `typescript/` because the JS/TS ecosystem standard is a **single workspace root** (one `package.json`, one `pnpm-workspace.yaml`) with many packages under `packages/` and apps under `apps/`. The “shared modules” dir for TS *is* `packages/`; it’s layer-named, not language-named.
- **Python** gets an optional top-level **language-named** dir `python/` (with `python/libs/` and `python/apps/`) when it’s first-class. That gives one place for all shared Python and Python runnables, and one natural home for the **repo-wide venv** (e.g. `python/.venv`). So: shared Python = `python/libs/` (analogous to `packages/` for TS), but under a language umbrella so one venv and one tooling story apply.

**Right level to share package manager and env per language**

| Language | Share at | Mechanism |
|----------|----------|-----------|
| **JS/TS** | **Repo root** | Single pnpm workspace: root `package.json` + `pnpm-workspace.yaml`; list `packages/*`, `apps/*`, `tools/*`, `skills/*` as workspace members. One lockfile, one store; each package has its own `package.json` and optional `node_modules` (pnpm symlinks). Node version: `.nvmrc` or `engines` at root. |
| **Python** | **Repo root or `python/`** | One venv (e.g. `.venv` or `python/.venv`). Shared libs: `pip install -e python/libs/simob_common` (or uv equivalent). One or a few `pyproject.toml` (root and/or under `python/`). No standard “workspace” list like pnpm; sharing = editable installs from a single tree. |

**Different constraints and approaches**

- **JS/TS:** Workspaces are the norm; many packages, one lockfile, dependency hoisting/store. Build outputs are per-package (`dist/`). Adding a new shared lib = add a dir under `packages/` and add it to the workspace. No “interpreter per repo” in the same way—Node version is process-level.
- **Python:** No universal workspace protocol. Sharing = one (or few) venvs + path/editable installs. One venv = one Python version; add a new shared lib = add under `python/libs/` and `pip install -e`. Multiple venvs only when you need different Python versions or conflicting deps. So: **one workspace root for TS, one venv root for Python** is the right level for each.

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

**WASM Python implementations (researched):**

- **[Pyodide](https://pyodide.org/)** — CPython compiled to WebAssembly. Runs in the browser and Node.js. Same codebase runs in both; JS ↔ Python bridge, async, Web APIs (DOM, Fetch). Many PyPI packages work (pure Python or pre-built wheels); use **micropip** in-browser for deps. First load is large (~several MB); use CDN (e.g. JsDelivr) or self-host; consider **pyodide-core** for minimal builds. Detect at runtime: `sys.platform == 'emscripten'` or `"pyodide" in sys.modules`. See [Pyodide usage](https://pyodide.org/en/stable/usage/quickstart.html), [loading packages](https://pyodide.org/en/stable/usage/loading-packages.html).
- **[PyScript](https://pyscript.net/)** — Higher-level on Pyodide (and MicroPython). `<script type="py">`, CDN; good for quick embed; use Pyodide when you need bundler/worker control.

**SvelteKit app: server + client running Python WASM**

- **Server:** SvelteKit (or `apps/api/`) handles HTTP, auth, DB, and can serve Python WASM assets and API endpoints that delegate to your Python backend if needed.
- **Client:** In `apps/web/` (SvelteKit client), load Pyodide (e.g. from CDN or static assets), then load and run a **subset** of your `python/libs/` modules that are safe for the browser. The same Python modules run in normal Python (CLI, server) and in the browser via Pyodide.
- **Flow:** User opens the web app → SvelteKit serves the page → client loads Pyodide → fetches or bundles your browser-safe Python → `pyodide.runPython()` or import your package via micropip. Optionally run heavy work in a **Web Worker** so the main thread stays responsive.

**Making the org friendly: layered, factored, pluggable modules**

- **Factor and layer** `python/libs/` so that:
  - **Browser-safe core** — Pure Python (or Pyodide-compatible deps only), no file I/O, no native C extensions, no Node/server-only APIs. This subset runs in **both** normal Python and Pyodide. Put it in e.g. `python/libs/<pkg>/core/` or the top-level public API that only imports browser-safe code.
  - **Optional, non-browser layers** — Code that uses `open()`, sockets, DB drivers, Blender APIs, or C extensions lives in **optional subpackages or modules** that are **not** imported when running in Pyodide. Examples: `python/libs/<pkg>/server/`, `python/libs/<pkg>/node/`, or `python/libs/<pkg>/io.py` guarded by runtime checks.
- **Detection:** In shared code, use `sys.platform == 'emscripten'` or `"pyodide" in sys.modules` to branch or to **skip optional imports**. Use try/except around `import something_server_only` and provide a stub or lazy placeholder in the browser.
- **Optional imports / dependency markers:** In `pyproject.toml` you can mark deps as not needed in Pyodide: `dependency; sys_platform != 'emscripten'` (see [Pyodide platform](https://pyodide.org/en/stable/development/abi.html)). That keeps browser installs from pulling server-only deps.
- **Pluggable backends:** For I/O or services, define a small interface in the core; in normal Python inject the real implementation (file system, DB); in the browser inject a stub or a JS-backed implementation via the Pyodide JS bridge. So the **core logic** is shared and environment-agnostic; the **pluggable** parts are swapped per environment.

**Concrete layout example**

```
python/libs/simob_common/
├── __init__.py          # Exposes only core or checks sys.platform before importing server/
├── core/                 # Browser-safe: pure logic, types, algorithms (runs in Pyodide + normal Python)
│   ├── __init__.py
│   └── models.py
├── server/               # Optional: file I/O, DB, HTTP server (only in normal Python; do not import in Pyodide)
│   ├── __init__.py
│   └── storage.py
└── py.typed
```

- **SvelteKit + Pyodide:** In `apps/web/`, load Pyodide (CDN or vendored), then load `simob_common.core` (e.g. via micropip install from a wheel you build, or fetch and run a bundle of the core package). Never load `server/` in the browser.
- **CLI / server:** Normal Python imports full `simob_common`; `simob_common/__init__.py` can import both `core` and `server` when `sys.platform != 'emscripten'`.

**Summary:** Use **Pyodide** as the WASM Python runtime. Structure libs so a **browser-safe core** runs everywhere and **server/node/IO** code is in optional, pluggable modules that are skipped or stubbed in the browser. SvelteKit serves the app and the client runs Python WASM; keep the core generic and the rest modular so the org stays WASM-friendly.

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

**Where to put the venv:** Prefer **root `.venv`** (same level as `package.json` and `pnpm-workspace.yaml`). Then **`scripts/`**, **`apps/`**, **`tools/`**, and **`skills/`** all share that venv: monorepo scripts, MOOLLM skill CLIs (e.g. `skills/cursor-mirror/scripts/cursor_mirror.py`), and any Python app or tool run with one interpreter and one set of deps. Run from repo root with `./.venv/bin/python scripts/foo.py` or `./.venv/bin/python skills/cursor-mirror/scripts/cursor_mirror.py` (or after `source .venv/bin/activate`). Symmetric with pnpm at root. If you prefer all Python under one tree, you can use `python/.venv` and `python/scripts/`; this doc assumes **root `.venv`** so that top-level `scripts/` and the top-level **skills/** dir both use it.

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
| `python/` (optional) | Shared Python libs (`python/libs/`) + Python apps (`python/apps/`); else Python in `apps/` and `tools/`. |
| `tools/` | Dev/deploy CLIs and utilities (TS or Python), each with own deps. |
| `scripts/` | Monorepo-wide runnables (Python preferred, or shell); use root `.venv`. |
| `skills/` | MOOLLM skills (CARD, GLANCE, SKILL; `lib/`, `scripts/`); share root `.venv`. |
| `extensions/` | Blender add-ons, Unity plugins (optional single place). |
| `.venv/` | Repo-wide Python venv (gitignored); scripts, apps, tools, skills use it. |
| `.github/` | Workflows (path-based, pnpm cache), composite actions. |
| `docs/` | Design and runbooks (e.g. this file). |

---

## 6. Package manager and root scripts

- **JS/TS:** pnpm only. Root `package.json`: `"preinstall": "npx only-allow pnpm"`, `pnpm-workspace.yaml` listing `packages/*`, `apps/*`, `tools/*`, etc. (exclude non-pnpm trees).
- **Python:** Root `.venv` (gitignored). Root or per-layer `pyproject.toml` (uv or pip); `pip install -e python/libs/<pkg>` into the root venv. Optional dependency groups for skills/apps in root pyproject.
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

## 8. Monorepo scripts (Python preferred)

- **scripts/** at repo root = the **only** CLI layer: arg parsers, imports from `python/libs/` (and `python/apps/`, `python/blender/`), and thunks into module code. Modules in `python/` do not define their own CLI; they stay pure and importable. Scripts are self-documenting, sniffable Python sister scripts (MOOLLM style). Run with root `.venv` (e.g. `./.venv/bin/python scripts/ci.py`). Keep scripts small and idempotent; call into modules or `apps/`/`tools/` as needed.
- App-owned scripts live in `apps/<app>/scripts/` when owned by that app (e.g. `apps/web/scripts/build.sh`). Same idea as central’s `apps/hub/scripts/`.

---

## 9. Blender / Unity

- **extensions/** — `extensions/blender/`, `extensions/unity/`. Use when you want “plugins for host apps” separate from “deployable products” (apps/). See §3.2.
- **apps/** — `apps/blender-addons/`, `apps/unity-mygame/`. Use when you want “everything we ship is under apps/” (Option C in §3.4). One home for each; document in README.

---

## 10. Decisions still to make

Before or as you implement, decide:

| Topic | Options | Notes |
|-------|---------|-------|
| **Option A vs B (Python)** | Top-level `python/` with `python/libs/`, `python/apps/` vs Python only in `apps/` and `tools/` | Use A when sharing Python across CLI, web, Blender; B for minimal structure. |
| **First app** | SvelteKit in `apps/web`, name (simob-web vs web), and whether to add an API app (Node/TS or Python) | Affects workspace and CI paths. |
| **VitaMoo** | Create as `packages/vitamoo` from scratch vs migrate from existing repo; browser + Node entry points | Shared animation/types for web and tooling. |
| **Python in browser** | Whether to use Pyodide/PyScript in `apps/web` for shared Python libs | Pure Python libs in `python/libs/` can run in browser without rewriting to TS. |
| **Blender/Unity** | When to add `extensions/blender/` or `extensions/unity/`; one add-on vs multiple | Doc recommends extensions/ when you have plugins. |
| **Root pyproject.toml** | Single root `pyproject.toml` with optional deps (e.g. dependency groups) vs per-layer only | Simplifies one-venv story; list shared deps and optional skill/app groups. |
| **CI workflows** | Exact path triggers, Python version matrix, whether to cache uv/pip, separate build vs deploy jobs | Start with one workflow; add path triggers and cache as in central. |
| **Skill imports** | How apps/tools import from `skills/<name>/lib/`: PYTHONPATH at runtime vs editable install of skill packages vs thin loader in `python/libs/` | Affects how you run apps that depend on cursor-mirror or moo lib. |
| **Node / Python versions** | `.nvmrc` or `engines` (e.g. Node 20); Python 3.11 vs 3.12 in root venv | Pin in CI and README. |

---

## 11. Checklist for a fresh start

- [ ] Root `package.json` + `pnpm-workspace.yaml`; `only-allow pnpm`.
- [ ] Root `.venv` (e.g. `uv venv` or `python -m venv .venv`); add to `.gitignore`. Optional root `pyproject.toml`.
- [ ] Create `apps/`, `packages/`, `tools/`, `scripts/`, `skills/`, `docs/`, `.github/workflows/`. Optionally `python/libs/`, `python/apps/`, `extensions/blender/`, `extensions/unity/`.
- [ ] Move or create VitaMoo as `packages/vitamoo` with browser + Node reuse.
- [ ] Decide Python placement: Option A (top-level `python/`) vs Option B (colocated in apps/tools). If A: `pip install -e python/libs/simob_common` into root venv.
- [ ] Add one SvelteKit app under `apps/web` (or `apps/simob-web`) and wire it to `packages/vitamoo`.
- [ ] Optionally add Pyodide/PyScript in `apps/web` for shared Python in browser.
- [ ] Add at least one workflow: path-based trigger, pnpm install + cache, build (and test if ready). Optionally Python test job using root `.venv`.
- [ ] Add a short README and point to this doc for layout and practices.

This keeps SimObliterator consistent with central’s ideas (layer-first, path triggers, cache, security, Python/TS standards) while fitting your mix of TS, Python, SvelteKit, sister scripts, MOOLLM skills, and VitaMoo reuse.
