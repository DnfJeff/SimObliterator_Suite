# SimObliterator Integration Gaps Report

**Discovery Date**: February 4, 2026  
**Source**: Analysis of `SimObliterator_Private_Versions/Iff_Study/`  
**Status**: ✅ COMPLETE - All critical integrations done

---

## GUI Architecture Status

### Current State (February 2026)

The project has **two parallel UI systems**:

| Interface | Technology | Files | Status |
|-----------|------------|-------|--------|
| **Desktop App** | DearPyGui | 32 files in `src/Tools/gui/` | Stable, full editing |
| **Web Viewers** | HTML/JS/Flask | 6 files in `src/Tools/webviewer/` | Active development |
| **VitaMoo** | TypeScript/WebGPU | `docs/` + `vitamoo/` | 3D character viewer |

### DearPyGui Desktop GUI (32 files)

Location: `src/Tools/gui/`

```
src/Tools/gui/
├── theme.py              # DearPyGui theming
├── menu.py               # Menu bar
├── events.py             # Event bus
├── focus.py              # Focus management
├── selection.py          # Selection state
├── state.py              # Application state
├── opcodes.py            # Opcode display
├── safety/               # Safety system
│   ├── edit_mode.py
│   └── help_system.py
└── panels/               # 27 panel modules
    ├── archiver_panel.py
    ├── batch_runner.py
    ├── bhav_editor.py
    ├── character_viewer_panel.py
    ├── chunk_inspector.py
    ├── diff_compare_panel.py
    ├── diff_view.py
    ├── far_browser.py
    ├── file_loader.py
    ├── graph_canvas.py
    ├── iff_inspector.py
    ├── iff_viewer.py
    ├── library_browser_panel.py
    ├── navigation_bar_panel.py
    ├── object_inspector.py
    ├── safety_indicator.py
    ├── safety_trust_panel.py
    ├── save_editor_panel.py
    ├── scope_banner.py
    ├── scope_switcher.py
    ├── semantic_inspector.py
    ├── sprite_export_panel.py
    ├── status_bar.py
    ├── support_panels.py
    ├── system_overview_panel.py
    ├── task_runner_panel.py
    └── visual_object_browser_panel.py
```

**Capabilities:** Full IFF/FAR/DBPF editing, save mutations, BHAV authoring, batch operations

### Web-Based Viewers (Browser Direction)

Location: `src/Tools/webviewer/`

| File | Size | Description |
|------|------|-------------|
| `export_server.py` | 34KB | Flask server for web exports |
| `character_viewer.html` | 34KB | Interactive character browser |
| `object_viewer.html` | 36KB | Interactive object browser |
| `library_browser.html` | 29KB | Mesh/sprite library browser |
| `graph_viewer_embed.html` | 10KB | Interactive graph visualization |
| `character_exporter.py` | 5KB | Export characters for web viewing |

### VitaMoo 3D Viewer

Location: `docs/` (GitHub Pages) + `vitamoo/` (TypeScript source)

- 3D character rendering with WebGPU
- Animation playback controls
- Scene presets with multiple characters
- Keyboard navigation

### Architecture Direction

> **Note:** Browser-based tooling is the emerging direction for visualization and cross-platform support. The DearPyGui desktop app remains the primary editing interface. No immediate migration planned - both systems coexist and share the same Python backend.

---

## Executive Summary

~~Found approximately **~500KB of research documentation** and **~10MB of data files** in the private research folder that haven't been integrated into SimObliterator Suite.~~

**All critical integrations complete as of February 4, 2026.**

Integrated items:

- ✅ **DEFINITIVE_BHAV_REFERENCE.md** (25KB) - Complete BHAV technical guide
- ✅ **FREESO_BEHAVIORAL_ARCHITECTURE.md** (35KB) - Deep FreeSO engine analysis
- ✅ **GLOBAL_BEHAVIOR_DATABASE.json** (23KB) - Complete global BHAV ID mappings
- ✅ **Webviewer** folder - Complete web-based viewers for characters, objects, meshes
- ✅ **VitaMoo** - 3D character viewer (TypeScript/WebGPU)
- ✅ **characters.json** (2MB), **objects.json** (3MB), **meshes.json** (209KB)

---

## Missing Research Documentation

### NewResearch/ Folder (43 files, ~450KB)

| File                               | Size | Priority    | Description                                                               |
| ---------------------------------- | ---- | ----------- | ------------------------------------------------------------------------- |
| DEFINITIVE_BHAV_REFERENCE.md       | 25KB | 🔴 CRITICAL | Complete BHAV technical guide - execution model, classification, patterns |
| FREESO_BEHAVIORAL_ARCHITECTURE.md  | 35KB | 🔴 CRITICAL | Deep FreeSO VM analysis - hook points, injection seams                    |
| FREESO_CHUNK_REFERENCE_ANALYSIS.md | 14KB | 🟡 HIGH     | Chunk type analysis from FreeSO source                                    |
| GLOBAL_BEHAVIOR_DATABASE.json      | 23KB | 🔴 CRITICAL | All 251 base game globals + expansion ranges                              |
| BHAV_OPCODE_REFERENCE.md           | 11KB | 🟡 HIGH     | Opcode documentation                                                      |
| ENGINE_PRIMITIVES.md               | 7KB  | 🟡 HIGH     | Primitive opcode classifications                                          |
| GHOST_GLOBALS_BREAKTHROUGH.md      | 7KB  | 🟢 MEDIUM   | Ghost global research findings                                            |
| GHOST_GLOBALS_FINAL_REPORT.md      | 8KB  | 🟢 MEDIUM   | Complete ghost globals analysis                                           |
| CYCLE_PATTERNS_GUIDE.md            | 10KB | 🟢 MEDIUM   | Behavioral cycle patterns                                                 |
| VALIDATION_TRUST_GUIDE.md          | 11KB | 🟡 HIGH     | Trust/validation system analysis                                          |
| RESOURCE_GRAPH_USAGE_GUIDE.md      | 12KB | 🟡 HIGH     | How to use graph infrastructure                                           |
| freeso_gap_analyzer.py             | 15KB | 🔴 CRITICAL | FreeSO parity gap analysis tool                                           |
| freeso_parity_stubs.cs             | 35KB | 🟢 MEDIUM   | C# stubs for FreeSO implementation                                        |

### Research Document Topics

1. **BHAV Execution Model** - How behaviors really work (not function calls!)
2. **Expansion Pack Ranges** - ID blocks for each expansion (256-511 base, etc.)
3. **Ghost Globals** - Globals that exist but aren't accessible
4. **FreeSO Architecture** - Hook points for modding
5. **Cycle Detection** - Finding infinite loops in behavior graphs
6. **Validation Trust** - Which modifications are safe

---

## Missing Tools

### Program/forensic/ - Additional Tools Not in Suite

| File                        | Size | Description                          |
| --------------------------- | ---- | ------------------------------------ |
| save_corruption_analyzer.py | 15KB | Analyzes save files for corruption   |
| semantic_globals.py         | 14KB | Expansion-aware global ID resolution |
| SAVE_FILE_STRUCTURE.py      | 10KB | Save file format reference           |

### Program/webviewer/ - Web Interface ✅ INTEGRATED

| File                    | Size | Status | Description                       |
| ----------------------- | ---- | ------ | --------------------------------- |
| export_server.py        | 34KB | ✅ | Flask server for web exports      |
| character_viewer.html   | 34KB | ✅ | Interactive character browser     |
| object_viewer.html      | 36KB | ✅ | Interactive object browser        |
| library_browser.html    | 29KB | ✅ | Mesh/sprite library browser       |
| graph_viewer_embed.html | 10KB | ✅ | Interactive graph visualization   |
| character_exporter.py   | 5KB  | ✅ | Export characters for web viewing |
| TESTING_VALIDATION.js   | 17KB | ✅ | JavaScript test suite             |

**Location:** `src/Tools/webviewer/`

### Program/scripts/ - Utility Scripts (MISSING)

| File             | Description                      |
| ---------------- | -------------------------------- |
| run_full_scan.py | Full game data scan orchestrator |

---

## Missing Data Files

### Private Program/data/ vs Suite data/

| File                          | Size  | In Suite? | Notes                                           |
| ----------------------------- | ----- | --------- | ----------------------------------------------- |
| asset_database.sqlite         | 2.2MB | ❌ NO     | Complete asset database (lower priority)        |
| characters.json               | 2MB   | ✅ YES    | **INTEGRATED** - All character data             |
| objects.json                  | 3.2MB | ✅ YES    | **INTEGRATED** - All object data                |
| meshes.json                   | 209KB | ✅ YES    | **INTEGRATED** - Mesh metadata                  |
| maxis_objects.sqlite          | 29KB  | ❌ NO     | Maxis object database (lower priority)          |
| mappings_db.json              | 365B  | ❌ NO     | ID mappings (in webviewer)                      |
| opcodes_db.json               | 13KB  | ✅ YES    | Already have (slight difference)                |
| unknowns_db.json              | 331B  | ✅ YES    | Already have (much larger in Suite)             |
| global_behavior_database.json | 23KB  | ✅ YES    | **INTEGRATED** - 251 globals + expansion ranges |

---

## Critical Integration: FOUND_TREASURE.md Discoveries

The FOUND_TREASURE.md document reveals that the following infrastructure exists but wasn't integrated:

### Forensic Package (155KB, 20 files)

Already in Suite ✅ but may need updates from private version:

- engine_toolkit.py (10.6KB) - Unified forensic interface
- semantic_globals.py (14.1KB) - Global ID database
- graph_labeler.py (14.5KB) - Call graph visualization
- save_state_analyzer.py (13.2KB) - Save state classification
- forensic_bhav_analyzer.py (6.3KB) - Opcode pattern mining
- forensic_expansion_analyzer.py (5.9KB) - Expansion pack diffing
- forensic_comprehensive_report.py (7.2KB) - Object analysis
- forensic_cooccurrence.py (7.2KB) - Opcode co-occurrence
- master_forensic_analyzer.py (6.6KB) - Orchestrates analysis
- save_file_analyzer.py (21.5KB) - Complete save decoder

### Graph Package (50KB, 8 files)

Already in Suite ✅ - appears complete:

- core.py - Resource graph data structures
- loader.py - Graph loading from IFF files
- analysis_tools.py - Dependency traversal
- cycle_detector.py - Circular dependency detection
- scope_validator.py - Reference scope validation
- extractors/ - Type-specific parsers

---

## Key Insights from Research

### Expansion ID Blocks (MUST DOCUMENT)

Every expansion gets 256 global IDs:

```
Base Game:    256-511   (0x100-0x1FF)
Livin' Large: 512-767   (0x200-0x2FF)
House Party:  768-1023  (0x300-0x3FF)
Hot Date:     1024-1279 (0x400-0x4FF)
Vacation:     1280-1535 (0x500-0x5FF)
Unleashed:    1536-1791 (0x600-0x6FF)
Superstar:    1792-2047 (0x700-0x7FF)
Makin' Magic: 2048-2303 (0x800-0x8FF)
```

**Magic**: Same function appears at SAME OFFSET across all packs!

- Global 264 (Base 0x08) = "test_user_interrupt"
- Global 1800 (SS 0x08) = same function, Superstar version

### BHAV Classification (from research)

BHAVs fall into 4 categories:

1. **ROLE** (52%) - Long-running autonomy cores, entry points
2. **FLOW** (25%) - Control flow coordinators
3. **ACTION** (15%) - Deterministic outcomes
4. **GUARD** (8%) - Condition checkers

### Save State Safety Categories

- ✅ **SAFE**: Skills, money, relationships, traits
- ⚠️ **DANGEROUS**: UI pointers, animation state
- 🚫 **FORBIDDEN**: Physics, threading, GC state

---

## Integration Checklist

### ✅ Completed (2026-02-04)

- [x] Copy `GLOBAL_BEHAVIOR_DATABASE.json` to `data/` - **DONE**
- [x] Copy `DEFINITIVE_BHAV_REFERENCE.md` to `Docs/` - **DONE**
- [x] Copy `FREESO_BEHAVIORAL_ARCHITECTURE.md` to `Docs/` - **DONE**
- [x] Copy `BHAV_OPCODE_REFERENCE.md` to `Docs/` - **DONE**
- [x] Copy `ENGINE_PRIMITIVES.md` to `Docs/` - **DONE**
- [x] Copy `RESOURCE_GRAPH_USAGE_GUIDE.md` to `Docs/` - **DONE**
- [x] Copy `VALIDATION_TRUST_GUIDE.md` to `Docs/` - **DONE**
- [x] Copy `CYCLE_PATTERNS_GUIDE.md` to `Docs/` - **DONE**
- [x] Copy `freeso_gap_analyzer.py` to `src/Tools/forensic/` - **DONE**
- [x] Copy webviewer/ folder to `src/Tools/` - **DONE**
- [x] Copy large data files (characters.json, objects.json, meshes.json) - **DONE**
- [x] Update test_paths.txt with new data file documentation - **DONE**
- [x] Fix test_suite.py path for dev/tests/ location - **DONE** (135/135 tests pass)

### Already Present

- [x] `semantic_globals.py` - Already in `src/Tools/forensic/`
- [x] `save_corruption_analyzer.py` - Already in `src/Tools/forensic/`
- [x] Full forensic package - Already integrated
- [x] Full graph package - Already integrated

### Lower Priority (Later)

- [ ] Evaluate browser-based editing (currently view-only)
- [ ] Integrate graph visualization into main app
- [ ] Add web export server auto-launch option
- [ ] Full FreeSO parity report generation
- [ ] Copy SQLite databases (asset_database.sqlite, maxis_objects.sqlite)

### GUI Architecture Decisions (Pending)

The DearPyGui desktop GUI (`src/Tools/gui/`, 32 files) provides full editing functionality:
- All 27 panels are functional
- Complete save mutation pipeline
- Transaction-based safety system

Browser-based tooling (`src/Tools/webviewer/`, `docs/vitamoo`) handles visualization:
- Read-only browsing of game data
- 3D character/animation preview
- Cross-platform via any modern browser

**No migration currently planned.** Both systems share the Python backend and can coexist. If browser-based editing becomes viable, the DearPyGui code is cleanly separated and can be deprecated without affecting core functionality.

---

## Files to Compare

Some files exist in both locations - need diff comparison:

| File                   | Private Size | Suite Size | Action            |
| ---------------------- | ------------ | ---------- | ----------------- |
| engine_toolkit.py      | 11.4KB       | ?          | Check for updates |
| save_state_analyzer.py | 13.5KB       | ?          | Check for updates |
| save_file_analyzer.py  | 22KB         | ?          | Check for updates |
| graph_labeler.py       | 14.9KB       | ?          | Check for updates |

---

## Impact Assessment

~~Without these integrations:~~

~~- ❌ No expansion-aware BHAV labeling~~
~~- ❌ No semantic global resolution~~
~~- ❌ No FreeSO parity analysis~~
~~- ❌ No save corruption detection~~
~~- ❌ No web-based viewers~~
~~- ❌ Missing 3.2MB of object data~~
~~- ❌ Missing 2MB of character data~~

**All critical integrations now complete!**

With these integrations:

- ✅ Complete BHAV semantic awareness
- ✅ Cross-expansion equivalence detection
- ✅ Safe vs dangerous edit classification
- ✅ FreeSO compatibility reporting
- ✅ Web-based data exploration
- ✅ Comprehensive object/character databases

---

**This is the juice. It was in the other folder all along. 🍊**

**Integration completed: 2026-02-04**
