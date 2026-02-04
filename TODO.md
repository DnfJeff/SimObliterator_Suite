# SimObliterator Suite — Feature Roadmap

> Practical implementation plan for community-requested features.  
> Based on existing tooling from `Iff_Study/Program` and current workspace capabilities.

---

## Quick Status Summary

| Theme                    | Status              | Backend                                                              | GUI        |
| ------------------------ | ------------------- | -------------------------------------------------------------------- | ---------- |
| **Localization/Strings** | ✅ Backend Complete | `str_parser.py`, `str_reference_scanner.py`, `localization_audit.py` | 🔲 Pending |
| **Simantics/Reference**  | ✅ Backend Complete | `primitive_reference.py`, `execution_model.json`                     | 🔲 Pending |
| **BHAV QoL/Authoring**   | ✅ Backend Complete | `bhav_rewiring.py`, `bhav_authoring.py`                              | 🔲 Pending |
| **Variable Visibility**  | ✅ Backend Complete | `variable_analyzer.py`                                               | 🔲 Pending |
| **Cross-BHAV Awareness** | ✅ Backend Complete | `bhav_call_graph.py`                                                 | 🔲 Pending |
| **ID Clash Detection**   | ✅ Backend Complete | `id_conflict_scanner.py`                                             | 🔲 Pending |
| **Safe ID Discovery**    | ✅ Backend Complete | `id_conflict_scanner.py` (IDRangeFinder)                             | 🔲 Pending |
| **TTAB/Autonomy**        | ✅ Backend Complete | `ttab_editor.py`                                                     | 🔲 Pending |
| **SLOT Editor**          | ✅ Backend Complete | `slot_editor.py`                                                     | 🔲 Pending |
| **Multi-Object IFF**     | ✅ Backend Complete | `ttab_editor.py` (MultiObjectContext)                                | 🔲 Pending |
| **CLI/Action Mapper**    | ✅ Complete         | `action_mapper.py`                                                   | N/A        |
| **Lot IFF/Ambience**     | ✅ Backend Complete | `lot_iff_analyzer.py`                                                | 🔲 Pending |

**Backend modules created: 16** | **GUI panels pending: ~10**

---

## Implementation Order

Features grouped by dependency, ordered to avoid spiral development.

---

## Phase 1: Core String Infrastructure (Foundation)

### 1.1 — STR# Language-Aware Parser

**Status:** ✅ COMPLETE  
**Priority:** HIGH (blocks localization features)  
**Files created:**

- `src/Tools/core/str_parser.py` — Full STR# parser with language slot awareness

**Implemented:**

- [x] Port `STRParser` from `skin_registry.py` with full language support
- [x] Handle all STR# formats: `0xFFFF`, `0xFDFF`, `0xFEFF`, Pascal (Format 0)
- [x] Add `LanguageSlot` dataclass with: `language_code`, `value`, `comment`
- [x] Map language codes: `LanguageCode` enum with 20 languages
- [x] Parse both string values AND comments
- [x] `ParsedSTR` with `get_localization_summary()`, `STRSerializer` for writing

---

### 1.2 — STR# Reference Tracker

**Status:** ✅ COMPLETE  
**Priority:** HIGH  
**Files created:**

- `src/Tools/core/str_reference_scanner.py` — Find all STR# usage

**Implemented:**

- [x] Scan OBJD chunks for catalog string references
- [x] Scan TTAB chunks for `tta_index` values
- [x] Scan CTSS chunks for catalog string entries
- [x] `STRUsageSummary` with `is_orphan`, `reference_count`
- [x] `ScanResult.get_orphan_str_chunks()`

---

### 1.3 — Localization Audit Tool

**Status:** ✅ COMPLETE  
**Priority:** HIGH  
**Files created:**

- `src/Tools/core/localization_audit.py`

**Implemented:**

- [x] `LocalizationAuditor` checks language slot population
- [x] `LocalizationIssue` with severity levels
- [x] `LocalizationPreferences` with `AuditLevel` enum
- [x] `check_before_save()` hook for save-time warnings

**Still TODO:**

- [ ] `src/Tools/gui/panels/localization_panel.py` — GUI panel

---

### 1.4 — Language Slot Copy Action

**Status:** ✅ COMPLETE  
**Priority:** MEDIUM  
**Files created:**

- `src/Tools/core/localization_audit.py` (includes `LocalizationFixer`)

**Implemented:**

- [x] `copy_language_to_missing()` function
- [x] `LocalizationFixer.preview_copy()` — preview mode
- [x] `LocalizationFixer.apply_copy()` — apply with serialization\*\*

- `src/Tools/core/str_mutations.py` — STR# editing operations
- `src/Tools/core/action_registry.py` — Register the action

**Work items:**

- [ ] One-click action: "Copy US English to all missing slots"
- [ ] Configurable source language (default: US English, code 0)
- [ ] Preview mode: show what will change before applying
- [ ] Preserve comments when copying values
- [ ] STR# serialization back to binary format (all 4 formats)

---

## Phase 2: Simantics / Primitive Reference System

### 2.1 — Primitive Reference Database

**Status:** ✅ COMPLETE  
**Priority:** HIGH  
**Files created:**

- `src/Tools/core/primitive_reference.py` — Query interface with operand definitions

**Implemented:**

- [x] `PrimitiveDefinition` with operand field definitions
- [x] `OperandField` with bit positions, types, enum values
- [x] `YieldBehavior` enum for return semantics
- [x] `VARIABLE_SCOPES` lookup (all 26+ scopes)
- [x] `decode_operand_for_opcode()` and `get_operand_display()`
- [x] `PRIMITIVE_CATEGORIES` for grouping
- [x] Definitions for Expression, Gosub, Sleep, Animate, Change Suit

**Still TODO:**

- [ ] Add more primitive definitions (currently 5 of ~100)

---

### 2.2 — Execution Model Documentation

**Status:** ✅ COMPLETE  
**Priority:** MEDIUM  
**Files created:**

- `data/execution_model.json` — Full execution model reference

**Implemented:**

- [x] Document entry point types: OBJF hooks, TTAB action/guard, globals
- [x] Document guard tree semantics
- [x] Document tree types: Main, Check, Private
- [x] Document instruction flow: pointer semantics, special returns
- [x] Variable scope documentation
- [x] Common patterns (guard, action loop, interrupt check)
- [x] BHAV ID range documentation

---

### 2.3 — In-Tool Cheat Sheet Panel

**Status:** 🔲 Not Started  
**Priority:** MEDIUM  
**Files to create:**

- `src/Tools/gui/panels/primitive_reference_panel.py`

**Work items:**

- [ ] Searchable primitive browser
- [ ] Show: opcode, name, category, operand fields, return behavior
- [ ] Context-aware: clicking instruction in BHAV editor → shows that primitive
- [ ] Filterable by category (Math, Animation, Routing, etc.)
- [ ] Collapsible detail sections

---

## Phase 3: BHAV Editor QoL / Authoring

### 3.1 — Instruction Selection & Multi-Select

**Status:** 🔲 Not Started  
**Priority:** HIGH  
**Files to modify:**

- `src/Tools/gui/panels/bhav_editor.py`

**Work items:**

- [ ] Single-click to select instruction
- [ ] Shift+click for range select
- [ ] Ctrl+click for toggle select
- [ ] Visual highlight for selected instructions
- [ ] Selection state preserved during scrolling

---

### 3.2 — Copy/Paste Instructions

**Status:** � Backend Ready  
**Priority:** HIGH  
**Files created:**

- `src/Tools/core/bhav_rewiring.py` — Pointer rewiring engine (see 3.4)

**Work items:**

- [ ] GUI: Copy selected instructions to internal clipboard
- [ ] GUI: Paste at cursor position
- [x] Backend: `rewire_for_copy_paste()` function implemented
- [ ] Handle cross-BHAV paste (warn about scope)
- [x] Backend: Preserve operand data

---

### 3.3 — Drag-and-Drop Reordering

**Status:** 🟡 Backend Ready  
**Priority:** MEDIUM  
**Files to modify:**

- `src/Tools/gui/panels/bhav_editor.py`

**Work items:**

- [ ] GUI: Drag instruction node to new position
- [x] Backend: `BHAVRewirer.move()` auto-rewires pointers
- [ ] Visual feedback during drag
- [ ] Undo support for reorder operations
- [x] Backend: Pointer integrity maintained

---

### 3.4 — Instruction Pointer Rewiring Engine

**Status:** ✅ COMPLETE  
**Priority:** HIGH (dependency for 3.2, 3.3)  
**Files created:**

- `src/Tools/core/bhav_rewiring.py`

**Implemented:**

- [x] `BHAVRewirer` class with insert, delete, move, reorder
- [x] `create_insert_mapping()`, `create_delete_mapping()`, `create_move_mapping()`
- [x] Handle special values: 253 (error), 254 (true), 255 (false)
- [x] `RewireResult` with pointer_changes and warnings
- [x] `validate()` for broken reference detection
- [x] `rewire_for_copy_paste()` helper

---

## Phase 4: Operand Authoring Abstractions

### 4.1 — Operand Field Editor

**Status:** 🟡 Backend Ready  
**Priority:** MEDIUM  
**Files created:**

- `src/Tools/core/primitive_reference.py` — Field definitions

**Backend ready:**

- [x] `OperandField.extract_value()` and `format_value()`
- [x] Enum values for dropdowns
- [x] Variable scope enums

**Still TODO:**

- [ ] `src/Tools/gui/widgets/operand_editor.py` — GUI widget
- [ ] Named flag toggles instead of raw bit manipulation
- [ ] Preview of raw binary (for verification)

---

### 4.2 — Expression-Style Input (Optional)

**Status:** 🔲 Not Started  
**Priority:** LOW  
**Files to create:**

- `src/Tools/core/expression_parser.py`

**Work items:**

- [ ] Parse: `my_local:0 = stack_obj:1 + temp:3`
- [ ] Convert to operand bytes
- [ ] Only for common primitives (expression, conditional)
- [ ] Optional — traditional input always available

---

## Phase 5: Variable Visibility & Tracing

### 5.1 — Variable Usage Analyzer

**Status:** ✅ COMPLETE  
**Priority:** HIGH  
**Files created:**

- `src/Tools/core/variable_analyzer.py`

**Implemented:**

- [x] Per-BHAV: list all locals, temps, params, attributes used
- [x] Track first-write vs reads (data flow) — `first_write_index`, `first_read_index`
- [x] Flag: written but never read — `is_written_never_read`
- [x] Flag: read before written (uninitialized) — `is_read_before_written`
- [x] `VariableScope`, `AccessType`, `VariableAccess`, `VariableInfo` dataclasses
- [x] `BHAVVariableAnalysis` with per-scope variable tracking
- [x] `BHAVVariableAnalyzer.analyze()` method

**Still TODO:**

- [ ] Detect variables inherited from caller (params) — cross-BHAV analysis

---

### 5.2 — Variable Sidebar Panel

**Status:** 🔲 Not Started  
**Priority:** MEDIUM  
**Files to create:**

- `src/Tools/gui/panels/variable_panel.py`

**Work items:**

- [ ] List all variables for current BHAV
- [ ] Group by scope: Locals, Temps, Params, Attributes, Globals
- [ ] Click variable → highlight all instructions that use it
- [ ] Tied to instruction selection (selected instruction shows which vars)
- [ ] Show TPRP labels if available

---

### 5.3 — TPRP/TRCN Integration

**Status:** 🔲 Not Started  
**Priority:** MEDIUM  
**Files to create:**

- `src/Tools/core/chunk_parsers_tprp.py`

**Work items:**

- [ ] Parse TPRP chunks (parameter name labels)
- [ ] Parse TRCN chunks (constant name labels)
- [ ] Map: `{(bhav_id, param_idx): "label"}` and `{(bcon_id, idx): "label"}`
- [ ] Integrate with variable panel and operand display

---

## Phase 6: Cross-BHAV Awareness

### 6.1 — BHAV Call Graph Builder

**Status:** ✅ COMPLETE  
**Priority:** HIGH  
**Files created:**

- `src/Tools/core/bhav_call_graph.py`

**Implemented:**

- [x] Build call graph per IFF file — `CallGraphBuilder.build_from_iff()`
- [x] Handle scope: `BHAVScope` enum (LOCAL, GLOBAL, SEMI_GLOBAL)
- [x] Track: caller → callee relationships — `BHAVNode.calls_to`, `called_by`
- [x] Identify: entry points — `BHAVNode.is_entry_point`, `objf_hooks`, `ttab_actions`
- [x] Identify: utility BHAVs (called by many) — `BHAVNode.is_utility`
- [x] Identify: orphan BHAVs — `BHAVNode.is_orphan`
- [x] Exportable as DOT graph — `CallGraph.to_dot()`

**Still TODO:**

- [ ] GUI panel for call graph visualization

---

### 6.2 — Shared State Detector

**Status:** 🔲 Not Started  
**Priority:** MEDIUM  
**Files to create:**

- `src/Tools/core/shared_state_analyzer.py`

**Work items:**

- [ ] Identify which BHAVs touch globals (scope 0-3)
- [ ] Identify which BHAVs touch object data (attributes)
- [ ] Map: `{global_id: [list of BHAVs that access it]}`
- [ ] Identify potential concurrency/conflict points

---

### 6.3 — Unused Variable Lint

**Status:** 🔲 Not Started  
**Priority:** LOW  
**Files to modify:**

- `src/Tools/core/variable_analyzer.py`

**Work items:**

- [ ] Cross-BHAV analysis for shared temps
- [ ] Flag: local written but never read (whole-file analysis)
- [ ] Optional lint — not enforced

---

## Phase 7: ID Clash Detection & Safe ID Discovery

### 7.1 — ID Conflict Scanner

**Status:** ✅ COMPLETE  
**Priority:** HIGH  
**Files created:**

- `src/Tools/core/id_conflict_scanner.py`

**Implemented:**

- [x] Scan loaded objects for overlapping:
  - Object GUIDs — `ConflictType.GUID_DUPLICATE`
  - OBJD chunk IDs — `ConflictType.OBJD_ID_OVERLAP`
  - Semi-global group IDs — `ConflictType.SEMIGLOBAL_CONFLICT`
  - BHAV IDs — `ConflictType.BHAV_ID_OVERLAP`
- [x] Report: which objects conflict, which IDs, why it's unsafe — `IDConflict` dataclass
- [x] Distinguish: same-file clash vs cross-file clash
- [x] Exportable text report — `ScanResult`, `to_report()`
- [x] `ConflictSeverity` enum (ERROR, WARNING, INFO)
- [x] `IDConflictScanner.scan_file()`, `scan_directory()`

---

### 7.2 — Safe ID Discovery

**Status:** ✅ COMPLETE  
**Priority:** MEDIUM  
**Files created:**

- `src/Tools/core/id_conflict_scanner.py` (includes `IDRangeFinder`)

**Implemented:**

- [x] Enumerate all IDs used in current scan — `IDRangeFinder`
- [x] Find unused ID ranges in local scope — `find_unused_guid_range()`, `find_unused_bhav_range()`
- [x] Clearly labeled: "LOCALLY unused, not globally reserved" — see docstrings
- [x] `get_usage_summary()` for statistics

**Still TODO:**

- [ ] Stub for future magic-cookie list integration (not required now)

---

### 7.3 — ID Report Panel

**Status:** 🔲 Not Started  
**Priority:** MEDIUM  
**Files to create:**

- `src/Tools/gui/panels/id_report_panel.py`

**Work items:**

- [ ] Display ID scan results
- [ ] Filter by conflict type
- [ ] Export button (text/CSV)

---

## Phase 8: Lot IFF / Ambience Investigation

### 8.1 — Lot IFF Analyzer

**Status:** ✅ COMPLETE  
**Priority:** MEDIUM  
**Files created:**

- `src/Tools/core/lot_iff_analyzer.py`

**Implemented:**

- [x] Load UserData lot IFFs (House##.iff, User#####.iff)
- [x] Parse lot-specific chunks (ARRY, SIMI, HOUS, OBJT, OBJM)
- [x] `TerrainType` enum with 6 terrain types (GRASS, SAND, SNOW, TS1_DARK_GRASS, TS1_AUTUMN_GRASS, TS1_CLOUD)
- [x] `HOUSE_NUMBER_TO_TERRAIN` dict with 12 mappings from FreeSO research
- [x] Identify object placements with GUID, position, rotation
- [x] `LotARRYType` enum for terrain heights, floors, walls, grass, pools, etc.

**Key Discovery:** Terrain type is NOT stored in lot IFF files. It's determined by house number via lookup table (source: FreeSO `VMTS1Activator.cs`).

---

### 8.2 — Ambience Resource Scanner

**Status:** ✅ COMPLETE  
**Priority:** MEDIUM  
**Files created:**

- `src/Tools/core/lot_iff_analyzer.py` (includes ambience definitions)

**Implemented:**

- [x] `AmbienceCategory` enum (ANIMALS, MECHANICAL, WEATHER, PEOPLE, LOOPS, UNKNOWN)
- [x] `AmbienceDefinition` dataclass with GUID, name, sound_path, category
- [x] 40+ ambience definitions from FreeSO `VMAmbientSound.cs`
- [x] `get_ambience_by_guid()` for lookup
- [x] `find_ambience_in_game()` to locate ambience resources in game files

**Key Finding:** Ambience is handled by objects with specific GUIDs. Sound resources stored in game's FAR archives, mapped by GUID→sound path.

---

### 8.3 — Ambience Investigation Report

**Status:** ✅ COMPLETE  
**Priority:** LOW

**Findings Documented:**

- [x] Ambience stored via object GUIDs, not lot-specific chunks
- [x] Sound files in `SoundData` folder's FAR archives
- [x] Hot Date beach lots use house numbers 28-29 → SAND terrain
- [x] Vacation island: 46-48 → SAND, Vacation snow: 40-42 → SNOW
- [x] Studio Town: 90-94 → TS1_DARK_GRASS
- [x] Magic Town: 95-96 → TS1_AUTUMN_GRASS, House 99 → TS1_CLOUD

---

### 8.4 — Test Suite for Real Game Files

**Status:** ✅ COMPLETE  
**Priority:** HIGH  
**Files created:**

- `dev/real_game_tests.py` — Comprehensive test suite
- `dev/test_paths.txt` — Configurable path configuration

**Implemented:**

- [x] `TestPaths` dataclass with auto-discovery of derived paths
- [x] `load_test_paths()` parses user-configurable test_paths.txt
- [x] 11 test categories: paths, formats, core, strings, bhav, objects, lots, saves, export, far_deep, cc_folder
- [x] CLI with --verbose, --category, --quick options
- [x] Tests FAR1/FAR3 parsing, IFF loading, DBPF parsing, BHAV analysis, lot analysis, STR# parsing
- [x] Tests against real Legacy Collection and UserData files

---

## Cross-Cutting: Guardrails & UX

### GR.1 — Explicit Edit Mode

**Status:** 🟡 Partial (safety.py exists)  
**Priority:** ONGOING

**Principles:**

- [ ] All mutations require explicit user action
- [ ] No silent rewrites
- [ ] Preview before commit

---

### GR.2 — Warnings Over Hard Blocks

**Status:** 🔲 Not Started  
**Priority:** ONGOING

**Principles:**

- [ ] Prefer warnings and visibility over hard enforcement
- [ ] User can override warnings with confirmation
- [ ] Log all override decisions

---

### GR.3 — Undocumented Behavior Labels

**Status:** 🔲 Not Started  
**Priority:** ONGOING

**Principles:**

- [ ] Mark behavior as "observed" vs "documented"
- [ ] Never claim certainty about undocumented behavior
- [ ] Link to source of knowledge (OpenTechDoc, FreeSO, testing)

---

## Dependency Graph

```
Phase 1 (STR#) ──┐
                 ├──> Phase 4 (Operand Authoring)
Phase 2 (Prims) ─┘

Phase 3 (BHAV QoL) ──> Phase 4 (Operand Authoring)

Phase 5 (Variables) ──> Phase 6 (Cross-BHAV)

Phase 7 (ID Clash) ── standalone

Phase 8 (Lot/Ambience) ── standalone
```

---

## Files to Port from Iff_Study/Program

| Source File                         | Target Location                | Status |
| ----------------------------------- | ------------------------------ | ------ |
| `core/skin_registry.py` (STRParser) | `src/Tools/core/str_parser.py` | ✅     |
| `core/mapping_db.py`                | Already in workspace           | ✅     |
| `core/opcode_loader.py`             | Already in workspace           | ✅     |
| `forensic/engine_toolkit.py`        | Already in workspace           | ✅     |
| `gui/panels/bhav_editor.py`         | Already in workspace           | ✅     |
| `gui/safety/*`                      | Already in workspace           | ✅     |
| `graph/extractors/bhav.py`          | Review for variable scope      | 🔲     |

---

## Phase 9: Community Pain Points (Multi-Object IFF, BHAV Authoring, SLOT)

> These address specific issues reported by the community with existing tools
> (IFF Pencil, Menu Editor, Codex)

### 9.1 — Multi-Object TTAB/Autonomy Editing

**Status:** ✅ COMPLETE (Backend)  
**Priority:** HIGH  
**Problem:** Menu Editor doesn't work with multiple objects in same IFF. IFF Pencil misses autonomy. Codex has save issues.

**Files created:**

- `src/Tools/core/ttab_editor.py` — Full TTAB parser + serializer + multi-object context

**Implemented:**

- [x] Parse ALL TTAB fields including autonomy level, motive effects
- [x] Handle multiple OBJDs in same IFF correctly (`MultiObjectContext`)
- [x] Link TTAB to correct OBJD by tree_table_id reference
- [x] Edit autonomy threshold per-interaction
- [x] Serialize TTAB back to binary with all fields preserved
- [x] Support TTAB versions 4-10 (V9+ compression code noted)
- [x] `InteractionFlags`, `MotiveEffect`, `TTABInteraction` dataclasses
- [x] `TTABParser`, `TTABSerializer` classes

**Still TODO:**

- [ ] `src/Tools/gui/panels/ttab_editor_panel.py` — GUI panel

---

### 9.2 — BHAV Instruction Authoring (From Scratch)

**Status:** ✅ COMPLETE (Backend)  
**Priority:** HIGH  
**Problem:** Users need to create new BHAV lines from scratch, not just edit existing.

**Files created:**

- `src/Tools/core/bhav_authoring.py` — Instruction builders + factory

**Implemented:**

- [x] `InstructionBuilder` with `OperandSpec` for each primitive
- [x] Expression primitive: full operand builder
- [x] Sleep primitive: operand builder
- [x] Animate primitive: operand builder
- [x] Gosub primitive: BHAV ID + parameters builder
- [x] Random Number primitive: operand builder
- [x] Set Motive primitive: operand builder
- [x] `BHAVFactory.create_instruction()` — create from operand values
- [x] `BHAVFactory.create_bhav()` — create complete BHAV from instructions
- [x] Convenience functions: `create_expression()`, `create_sleep()`, etc.

**Still TODO:**

- [ ] `src/Tools/gui/panels/instruction_builder.py` — GUI for building instructions
- [ ] More primitives: Find Best Object, Relationship, etc.
- [ ] Template library for common instruction patterns

---

### 9.3 — SLOT Resource Editor

**Status:** ✅ COMPLETE (Backend)  
**Priority:** MEDIUM  
**Problem:** IFF Pencil's SLOT editor was never finished. Needed for object routing.

**Files created:**

- `src/Tools/core/slot_editor.py` — Full SLOT parser + editor + serializer

**Implemented:**

- [x] Parse SLOT chunk format (all versions)
- [x] `SlotEntry` with type, position, flags, target, height
- [x] `SlotType` enum: Absolute, Standing, Sitting, Ground, Routing Target
- [x] `SlotFlags` enum: Snap, Face Object, Random Facing, etc.
- [x] `SLOTParser`, `SLOTSerializer` classes
- [x] `SLOTEditor.add_slot()`, `remove_slot()`, `duplicate_slot()`
- [x] Template generators: `create_basic_chair_slots()`, `create_basic_counter_slots()`

**Still TODO:**

- [ ] `src/Tools/gui/panels/slot_editor_panel.py` — Visual slot editor
- [ ] Visual grid showing slot positions on object footprint

---

### 9.4 — OBJD Multi-Object Awareness

**Status:** ✅ COMPLETE (Backend)  
**Priority:** HIGH  
**Problem:** Tools confuse OBJDs when multiple objects in same file.

**Files created:**

- `src/Tools/core/ttab_editor.py` (includes `MultiObjectContext`)

**Implemented:**

- [x] `MultiObjectContext` dataclass tracking all OBJDs per IFF
- [x] `ObjectEntry` with OBJD ID, name, GUID, TTAB ID, catalog STR ID
- [x] `get_object_for_ttab()` — find owner of a TTAB
- [x] `build_multi_object_context()` — scan IFF for all objects
- [x] Pull object names from catalog strings

**Still TODO:**

- [ ] Object switcher UI for multi-object IFFs
- [ ] Clear indication of "current object context" in all panels

---

## Notes

- This document is a work list, not a promise
- Order may shift based on what unblocks other work
- Each phase should be testable independently
- Community feedback may reprioritize items
