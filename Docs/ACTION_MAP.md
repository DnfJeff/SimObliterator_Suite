# SimObliterator Suite - ACTION MAP

## Feature Inventory & Integration Status

This document maps discovered capabilities across tools to inform integration into the Suite.

> 📋 **See Also**: [ACTION_SURFACE.md](ACTION_SURFACE.md) — Canonical action definitions (143 actions, 71 write, 36 high-risk)

---

## 🧠 ARCHITECTURAL PRINCIPLES (MUST READ FIRST)

> **"When integrating features, prioritize shared state, semantic meaning, safety boundaries, and cross-system visibility over adding new panels."**

### 1. Unifying Selection Model

**Concept**: One canonical `SelectionContext` that everything reacts to.

Selection can be: `File | Object | BHAV | Opcode | Sim | GraphNode | Chunk`

**Rule**: Every panel must either:

- SET the selection, OR
- REACT to the selection

No panel operates in isolation.

**Implementation**: `Tools/gui/focus.py` → `FocusCoordinator`

### 2. Time / Lifecycle Awareness

**Concept**: Behaviors classified by WHEN they execute, not just what they do.

| Lifecycle Phase    | Examples                        |
| ------------------ | ------------------------------- |
| Init-time          | Object creation, load from save |
| Runtime            | User interactions, autonomous   |
| Event-driven       | Triggered by state change       |
| Save-load boundary | Persistence hooks               |

**Rule**: Every BHAV should show its execution context.

### 3. Write Barrier Layer

**Concept**: All writes go through a single mutation pipeline.

```
User Intent → Validate → Diff → Risk Check → Commit/Reject
```

| Mode            | Behavior                 |
| --------------- | ------------------------ |
| Inspection-only | Read, no writes possible |
| Preview         | Show diff, no commit     |
| Mutating        | Full write with audit    |

**Rule**: `is_safe_to_edit()` is the gate, but all writes flow through `MutationPipeline`.

### 4. Cross-File / Cross-Pack Reasoning

**Concept**: Expansion comparison is a VIEW, not a feature.

**Questions the UI must answer**:

- "Show me this object across expansions"
- "Compare BHAV 0x#### between packs"
- "What changed from Base → Expansion 1?"

**Rule**: Every entity is expansion-aware. Diff is first-class.

### 5. Simulation Boundary

**Concept**: Clear line between static tracing and live game execution.

| Layer             | What It Does                                     | Status           |
| ----------------- | ------------------------------------------------ | ---------------- |
| Static Analysis   | Parse, decode, relationship mapping              | ✅ Core          |
| Execution Tracing | Follow instruction paths, detect loops/dead code | ✅ Core          |
| Inference         | "This BHAV probably does X"                      | ✅ Core          |
| Live VM Execution | Run primitives with game state                   | ⛔ NOT SUPPORTED |

**Rule**: SimObliterator TRACES and EXPLAINS behavior; it does NOT execute primitives.
Execution tracing is STATIC (no side effects) but COMPLETE (all paths analyzed).

**Core Engine Service**: `Tools/core/bhav_executor.py`

- `BHAVExecutor` - Static execution simulation
- `ExecutionTrace` - Complete path history with loop/dead code detection
- `BHAVExecutionAnalyzer` - Full analysis wrapper

**Depends On**: MutationPipeline, SaveStateAnalyzer, SemanticInspector, GraphCanvas

### 6. Semantic Search

**Concept**: Search operates on MEANING, not filenames or IDs.

**Example queries**:

- "Find BHAVs that modify motive X"
- "Find globals called by objects in scope Y"
- "Find behaviors unsafe in save context"

**Rule**: Search understands semantics, not just text matching.

### 7. Provenance / Confidence Signaling

**Concept**: Every fact says how sure we are.

| Confidence | Source                        |
| ---------- | ----------------------------- |
| ✓ Observed | Direct parse from game files  |
| ~ Inferred | Derived from patterns         |
| ? Guessed  | Heuristic, may be wrong       |
| ⚠ Unknown  | No data, flagged for research |

**Rule**: UI shows confidence badges on inferred data.

### 8. Logging as Forensic Trace

**Concept**: The log explains WHY SimObliterator thinks something is true.

| Log Type  | Purpose                    |
| --------- | -------------------------- |
| Decision  | "Marked unsafe because..." |
| Discovery | "Found unknown opcode..."  |
| Mutation  | "Changed X from A to B"    |
| Safety    | "Blocked edit due to..."   |

**Rule**: Log is an audit trail, not console spam.

### 9. System Overview Entry Point

**Concept**: "What am I looking at?" panel.

Must show at a glance:

- Loaded packs & files
- Object / BHAV / Chunk counts
- Unknowns encountered
- Safety status
- Current selection context

**Rule**: First thing user sees. Orientation surface.

### 10. Panel Identity (Layered Inspectors)

**Concept**: Inspectors are LAYERED by depth of meaning.

```
File → Structure → Semantics → System Impact
```

| Inspector         | Layer     | Responsibility            |
| ----------------- | --------- | ------------------------- |
| FileLoader        | File      | Which file is loaded      |
| IFFInspector      | Structure | Chunk list, raw data      |
| ChunkInspector    | Semantics | What chunk means          |
| ObjectInspector   | System    | Object in game context    |
| SemanticInspector | System    | Cross-references, globals |

**Rule**: No inspector duplicates another's depth.

---

## 🗄️ EXISTING TOOLS DISCOVERED

### 1. SimObliterator Archiver (`RELEASE/SimObliterator_Archiver/`)

**Status**: ✅ Standalone EXE exists, needs Suite integration

**Capabilities**:
| Feature | File | Description |
|---------|------|-------------|
| Forensics Mode | `archiver_main.py` | Deep pattern analysis, unknown opcode detection |
| Mapping Mode | `archiver_main.py` | Build behavior library, object registry |
| Unknowns Database | `core/unknowns_db.py` | Auto-growing DB of unknown opcodes/chunks |
| Opcode Loader | `core/opcode_loader.py` | Known opcode definitions |
| Behavior Library | `core/behavior_library.py` | BHAV lookup service |

**Data Files** (already populated!):

- `data/unknowns_db.json` - 167+ unknown opcodes discovered (12,407 lines!)
- `data/mappings_db.json` - Behavior mappings
- `data/opcodes_db.json` - Known opcode definitions
- `data/COMPLETE_SCAN.json` - Full game scan results
- `data/GLOBAL_BEHAVIORS.json` - Global BHAV catalog

### 2. Sprite Extractor (`Program/sprite_extractor_main.py`)

**Status**: ⚠️ Exists but needs PIL/SPR2Decoder integration

**Capabilities**:
| Feature | Status | Description |
|---------|--------|-------------|
| Individual Sprite Export | ⚠️ Needs decoder | Extract PNG from SPR2 chunks |
| Sprite Sheet Generation | ⚠️ Needs PIL | Combined sheets with metadata |
| Batch Processing | ✅ Works | Process entire FAR/IFF folders |
| Metadata JSON | ✅ Works | Dimensions, offsets, frame counts |

**Missing for Full Function**:

- `formats/iff/chunks/sprite_export.py` - SPR2Decoder class
- PIL library for image manipulation

### 3. Web-Based Object Viewer (`Program/webviewer/object_viewer.html`)

**Status**: ✅ Full-featured, runs via Flask server

**Capabilities**:
| Feature | Status | Description |
|---------|--------|-------------|
| Sprite Preview | ✅ Works | All directions/zooms |
| Export Single Sprite | ✅ Works | PNG download |
| Export All Sprites (ZIP) | ✅ Works | Batch ZIP export |
| Sprite Sheet Export | 🔴 501 stub | Returns "requires PIL" |
| Analytics/Logging | ✅ Works | Full event tracking |

---

## 📊 RESEARCH DATABASE (Lost Tech Found!)

### Opcode/BHAV Research

| Document                    | Location                                   | Contents                               |
| --------------------------- | ------------------------------------------ | -------------------------------------- |
| BHAV Opcode Reference       | `NewResearch/BHAV_OPCODE_REFERENCE.md`     | 646 lines, FreeSO-extracted semantics  |
| Definitive BHAV Reference   | `NewResearch/DEFINITIVE_BHAV_REFERENCE.md` | 981 lines, complete architecture model |
| Engine Primitives           | `NewResearch/ENGINE_PRIMITIVES.md`         | All 65 engine opcodes (0-255)          |
| Forensic Opcode Master      | `Testing/FORENSIC_OPCODE_MASTER.md`        | 428 lines, per-expansion analysis      |
| Compressed BHAV Knowledge   | `NewResearch/COMPRESSED_BHAV_KNOWLEDGE.md` | Distilled patterns                     |
| Ghost Globals Investigation | `NewResearch/GHOST_GLOBALS_*.md`           | The 512-2815 mystery resolved          |

### Global BHAV Database (Semantic Names!)

| Document                    | Location                                        | Contents                                |
| --------------------------- | ----------------------------------------------- | --------------------------------------- |
| Global BHAV Reference       | `Testing/GLOBAL_BHAV_REFERENCE.md`              | All global BHAV IDs with names          |
| Global BHAV Categorized     | `Testing/GLOBAL_BHAV_CATEGORIZED.md`            | By function category                    |
| Behavior Library            | `Program/output/BEHAVIOR_LIBRARY.md`            | Classified behaviors (Role/Action/Flow) |
| Behavior Relationship Layer | `Program/output/BEHAVIOR_RELATIONSHIP_LAYER.md` | Call graph analysis                     |

### Technical Documentation

| Document            | Location                                | Contents                         |
| ------------------- | --------------------------------------- | -------------------------------- |
| TheSimsOpenTechDoc  | `TheSimsOpenTechDoc/`                   | 6-part complete format reference |
| FreeSO Architecture | `NewResearch/FREESO_*.md`               | VM analysis, chunk reference     |
| TTAB Research       | `NewResearch/TTAB_RESEARCH_COMPLETE.md` | Interaction table deep dive      |

---

## 🎯 ACTION ITEMS FOR SUITE INTEGRATION

### Priority 1: Sprite Export Panel

**Goal**: Select object in Library → Export sprites to ZIP or Sheet

**Resources Available**:

- `Program/sprite_extractor_main.py` - Core extraction logic
- `Program/webviewer/object_viewer.html` - Export UI patterns
- `formats/iff/chunks/` - Chunk parsers

**Implementation Path**:

1. Add "Export Sprites" button to VisualObjectBrowserPanel
2. Create `SpriteExportDialog` with options:
   - [ ] Individual PNGs (ZIP)
   - [ ] Sprite Sheet (requires PIL)
   - [ ] With metadata JSON
3. Integrate SPR2Decoder from formats/

### Priority 2: Unknowns Database Integration

**Goal**: Auto-grow database as Suite encounters new files

**Resources Available**:

- `RELEASE/SimObliterator_Archiver/core/unknowns_db.py` - Complete implementation
- `RELEASE/SimObliterator_Archiver/data/unknowns_db.json` - 167 entries already!

**Implementation Path**:

1. Copy `unknowns_db.py` to Suite's `Tools/core/`
2. Import in ChunkInspectorPanel (already has stub!)
3. Hook into BHAV analysis to auto-report unknowns
4. Add "Unknowns Report" panel to Suite

### Priority 3: Semantic BHAV Names Database

**Goal**: Every BHAV call shows human-readable name

**Resources Available**:

- `Testing/GLOBAL_BHAV_REFERENCE.md` - ID → Name mappings
- `NewResearch/BHAV_OPCODE_REFERENCE.md` - Opcode semantics
- `forensic/engine_toolkit.py` - Already does this!

**Implementation Path**:

1. Consolidate markdown → JSON database
2. Extend engine_toolkit with all discovered names
3. Add "BHAV Database Viewer" panel

### Priority 4: Archiver Mode in Suite

**Goal**: Batch scan directories from within Suite

**Resources Available**:

- `RELEASE/SimObliterator_Archiver/archiver_main.py` - Full GUI app

**Implementation Path**:

1. Add "Archiver" panel to Suite
2. Port ArchiverApp.extract_file() logic
3. Connect to Suite's existing file browsers

---

## 🔧 MISSING COMPONENTS

### SPR2 Decoder

**Needed For**: Sprite export, sprite sheets, visual browser previews

**Status**: Referenced but may not exist:

```python
from formats.iff.chunks.sprite_export import SPR2Decoder  # Where is this?
```

**Action**: Check if exists, if not create from FreeSO C# reference

### PIL Integration

**Needed For**: Sprite sheet generation, image manipulation

**Status**: Optional dependency, gracefully degraded

**Action**: Add to requirements.txt, enable sprite sheet features

---

## 📁 DATA FILES TO MIGRATE

### From Archiver → Suite

| Source                                               | Destination                  | Purpose                  |
| ---------------------------------------------------- | ---------------------------- | ------------------------ |
| `SimObliterator_Archiver/data/unknowns_db.json`      | `SimObliterator_Suite/data/` | Unknown opcode database  |
| `SimObliterator_Archiver/data/opcodes_db.json`       | `SimObliterator_Suite/data/` | Known opcode definitions |
| `SimObliterator_Archiver/data/GLOBAL_BEHAVIORS.json` | `SimObliterator_Suite/data/` | Global BHAV catalog      |

### From Research → Suite

| Source                                 | Destination   | Purpose              |
| -------------------------------------- | ------------- | -------------------- |
| `Testing/GLOBAL_BHAV_REFERENCE.md`     | Parse to JSON | Semantic names       |
| `NewResearch/BHAV_OPCODE_REFERENCE.md` | Parse to JSON | Opcode documentation |

---

## 🎮 USER STORIES ENABLED

### CC Creator Flow

1. Open Suite
2. Browse Library → Find "Chair"
3. Select chair object
4. Click "Export Sprites" → Choose ZIP
5. Download chair_sprites.zip with all rotations

### Researcher Flow

1. Open Suite
2. Load unknown mod IFF
3. See "⚠️ 3 unknown opcodes found"
4. Click "Report Unknowns" → Added to database
5. Later: View unknowns_db.json to research

### Modder Flow

1. Open Suite
2. Search "Init" → Find all initialization BHAVs
3. See semantic names for all global calls
4. Edit behavior with full context

---

## 📈 INTEGRATION PRIORITY MATRIX

| Feature                 | Effort | Value  | Priority | Status     |
| ----------------------- | ------ | ------ | -------- | ---------- |
| Unknowns DB Integration | Low    | High   | 🔴 P1    | ✅ Done    |
| Semantic BHAV Names     | Low    | High   | 🔴 P1    | ✅ Done    |
| Sprite Export (ZIP)     | Medium | High   | 🟡 P2    | ✅ Done    |
| Sprite Sheet Export     | Medium | Medium | 🟡 P2    | ✅ Done    |
| System Overview Panel   | Low    | High   | 🔴 P1    | ✅ Done    |
| Mutation Pipeline       | Medium | High   | 🔴 P1    | ✅ Done    |
| BHAV Execution Tracing  | High   | High   | 🔴 P1    | ✅ Done    |
| Archiver Panel          | High   | Medium | 🟢 P3    | ⚠️ Partial |

---

## ✅ IMPLEMENTATION STATUS

> **🔒 ARCHITECTURE LOCKED**: New features MUST integrate via FocusCoordinator, MutationPipeline, EngineToolkit.  
> No direct writes. No orphan panels. No silent assumptions.

### Architectural Principles Implemented

| Principle               | Implementation                     | File(s)                                     | Status |
| ----------------------- | ---------------------------------- | ------------------------------------------- | ------ |
| 1. Selection Model      | FocusCoordinator singleton         | `Tools/gui/focus.py`                        | ✅     |
| 2. Lifecycle Awareness  | BehaviorPurpose enum               | `Tools/entities/behavior_entity.py`         | ✅     |
| 3. Write Barrier        | MutationPipeline                   | `Tools/core/mutation_pipeline.py`           | ✅     |
| 4. Cross-Pack Reasoning | DiffComparePanel + CrossPack scope | `Tools/gui/panels/diff_compare_panel.py`    | ✅     |
| 5. Simulation Boundary  | Static tracing ✅, Live exec ⛔    | `Tools/core/bhav_executor.py`               | ✅     |
| 6. Semantic Search      | GlobalSearchPanel (enhanced)       | `Tools/gui/panels/support_panels.py`        | ✅     |
| 7. Confidence Signaling | ProvenanceRegistry                 | `Tools/core/provenance.py`                  | ✅     |
| 8. Forensic Logging     | LogPanel                           | `Tools/gui/panels/support_panels.py`        | ✅     |
| 9. System Overview      | SystemOverviewPanel                | `Tools/gui/panels/system_overview_panel.py` | ✅     |
| 10. Panel Layering      | Depth modes                        | ChunkInspector, ObjectInspector             | ✅     |

### GlobalSearchPanel Semantic Filters (Principle #6)

> "If a query can't express meaning, it's incomplete."

| Filter    | Options                                                     | Purpose                |
| --------- | ----------------------------------------------------------- | ---------------------- |
| Effect    | Motive, Relationship, Object, Animate, Data, Control, Error | Find by what BHAV DOES |
| Lifecycle | Init, Main, Cleanup, Timer, UI                              | Find by WHEN BHAV runs |
| Safety    | 🟢 Safe, 🟡 Caution, 🔴 Dangerous                           | Find by risk level     |
| Scope     | Current File, All Global, Primitives, **Cross-Pack**        | Where to search        |

**Features**:

- Filter-only mode (no query required)
- Safety badges on results
- Provenance display for selected result
- Cross-pack equivalence search

### Panels Implemented (24 total)

| Category   | Panels                                                 |
| ---------- | ------------------------------------------------------ |
| Core       | FileLoader, IFFInspector, FARBrowser, IFFViewer        |
| Inspection | ChunkInspector, ObjectInspector, SemanticInspector     |
| Editing    | BHAVEditor, SaveEditor, **TTABEditor**, **SLOTEditor** |
| Navigation | LibraryBrowser, VisualObjectBrowser, NavigationBar     |
| Analysis   | GraphCanvas, DiffCompare, TaskRunner                   |
| Safety     | SafetyTrust                                            |
| Support    | GlobalSearch, Preferences, Log, StatusBar              |
| Overview   | **SystemOverview** (NEW)                               |
| Export     | **SpriteExport** (NEW)                                 |
| Authoring  | **InstructionBuilder** (NEW)                           |

### Entity Abstractions

| Entity            | Purpose                     | File                                    |
| ----------------- | --------------------------- | --------------------------------------- |
| ObjectEntity      | Aggregate OBJD+BHAV+Sprites | `Tools/entities/object_entity.py`       |
| BehaviorEntity    | BHAV with semantic context  | `Tools/entities/behavior_entity.py`     |
| SimEntity         | Sim data from saves         | `Tools/entities/sim_entity.py`          |
| RelationshipGraph | Dependency analysis         | `Tools/entities/relationship_entity.py` |

### Core Modules (NEW - February 2026)

| Module              | Purpose                              | File                                  |
| ------------------- | ------------------------------------ | ------------------------------------- |
| TTABEditor          | Full TTAB parsing w/ autonomy        | `Tools/core/ttab_editor.py`           |
| SLOTEditor          | Routing slot editor (IFF Pencil gap) | `Tools/core/slot_editor.py`           |
| BHAVAuthoring       | Create instructions from scratch     | `Tools/core/bhav_authoring.py`        |
| ActionMapper        | CLI/Script "Fuck the UI" interface   | `Tools/core/action_mapper.py`         |
| STRParser           | Language-aware STR# parser           | `Tools/core/str_parser.py`            |
| STRReferenceScanner | Find all STR# usages                 | `Tools/core/str_reference_scanner.py` |
| LocalizationAuditor | Check missing language slots         | `Tools/core/localization_audit.py`    |
| BHAVCallGraph       | Cross-BHAV call relationships        | `Tools/core/bhav_call_graph.py`       |
| BHAVRewirer         | Pointer updates on instruction edit  | `Tools/core/bhav_rewiring.py`         |
| IDConflictScanner   | Detect overlapping IDs across files  | `Tools/core/id_conflict_scanner.py`   |
| VariableAnalyzer    | Track variable usage in BHAVs        | `Tools/core/variable_analyzer.py`     |
| PrimitiveReference  | Enhanced opcode documentation        | `Tools/core/primitive_reference.py`   |
| MultiObjectContext  | Track OBJDs in multi-object IFFs     | `Tools/core/ttab_editor.py`           |

### Safety & Mutation

| Component         | Purpose             | File                              |
| ----------------- | ------------------- | --------------------------------- |
| is_safe_to_edit() | Safety gate API     | `Tools/safety.py`                 |
| MutationPipeline  | Write barrier       | `Tools/core/mutation_pipeline.py` |
| SafetyLevel enum  | Risk classification | `Tools/safety.py`                 |

### BHAV Execution Engine (Core Service)

| Component             | Purpose                         | File                          |
| --------------------- | ------------------------------- | ----------------------------- |
| BHAVExecutor          | Static execution simulation     | `Tools/core/bhav_executor.py` |
| ExecutionTrace        | Path history, loop detection    | `Tools/core/bhav_executor.py` |
| BHAVExecutionAnalyzer | Full analysis wrapper           | `Tools/core/bhav_executor.py` |
| VMPrimitiveExitCode   | Exit code enum (mirrors FreeSO) | `Tools/core/bhav_executor.py` |

**Capabilities**:

- Trace all instruction paths through BHAV bytecode
- Detect infinite loops (backward jumps)
- Find unreachable/dead code
- Build complete execution history
- Support MutationPipeline validation

**Game Coverage**: 2,287 BHAVs across 24 global IFF files traced

### Data Files Migrated

| File                  | Purpose              | Location                     |
| --------------------- | -------------------- | ---------------------------- |
| unknowns_db.json      | 167+ unknown opcodes | `data/unknowns_db.json`      |
| opcodes_db.json       | Known opcode defs    | `data/opcodes_db.json`       |
| global_behaviors.json | Global BHAV catalog  | `data/global_behaviors.json` |
| execution_model.json  | SimAntics VM model   | `data/execution_model.json`  |

---

## 🔧 CLI / ACTION MAPPER ("Fuck the UI")

> All functionality available without GUI via `action_mapper.py`

### Python API

```python
from src.Tools.core.action_mapper import ActionMapper

mapper = ActionMapper()

# List all available actions
mapper.list_actions()

# Parse TTAB with autonomy (the field Menu Editor misses!)
result = mapper.execute("get-autonomy", file="multitile.iff")

# List objects in multi-OBJD file
result = mapper.execute("list-objects", file="multitile.iff")

# Create BHAV instruction from scratch
result = mapper.execute("create-instruction", opcode=0x02,
                        operands={"dest_scope": 6, "dest_index": 0, "operator": 0})

# Batch processing
results = mapper.run_batch([
    {"action": "list-chunks", "args": {"file": "obj1.iff"}},
    {"action": "parse-ttab", "args": {"file": "obj2.iff"}},
])
```

### CLI Usage

```bash
# List all actions
python -m src.Tools.core.action_mapper list-actions

# Parse file
python -m src.Tools.core.action_mapper list-chunks object.iff

# BHAV operations
python -m src.Tools.core.action_mapper parse-bhav object.iff --bhav-id 0x1000
python -m src.Tools.core.action_mapper bhav-call-graph object.iff --format dot

# TTAB/Autonomy (community pain point!)
python -m src.Tools.core.action_mapper get-autonomy multitile.iff
python -m src.Tools.core.action_mapper list-interactions object.iff

# Export
python -m src.Tools.core.action_mapper export-report object.iff -o report.json -f json
```

### Action Categories

| Category | Actions                                                                                     | Description       |
| -------- | ------------------------------------------------------------------------------------------- | ----------------- |
| `file`   | load-iff, list-chunks, extract-chunk, validate-iff                                          | File I/O          |
| `object` | list-objects, get-object-info, scan-id-conflicts                                            | OBJD operations   |
| `bhav`   | parse-bhav, list-bhavs, bhav-call-graph, analyze-variables, create-bhav, create-instruction | BHAV operations   |
| `ttab`   | parse-ttab, list-interactions, get-autonomy, set-autonomy                                   | TTAB/Interactions |
| `string` | parse-str, list-strings, localization-audit, find-str-references                            | STR#/Localization |
| `slot`   | parse-slot, list-slots, add-slot                                                            | Routing slots     |
| `export` | export-report, export-bhav-dot, export-opcodes                                              | Export operations |
| `meta`   | list-actions, help, version                                                                 | Meta operations   |

---

_Last Updated: February 4, 2026_
_Architectural principles integrated - platform coherence maintained_
