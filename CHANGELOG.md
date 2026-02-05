# Changelog

All notable changes to SimObliterator Suite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.2] - 2026-02-04

### Test System Overhaul

Unified and modularized the test infrastructure for better maintainability.

#### Changed

- Consolidated `test_suite.py` and `real_game_tests.py` into modular architecture:
  - `tests.py` - Main runner with CLI options (`--api`, `--game`, `--quick`, `--verbose`)
  - `test_api.py` - 174 API/module tests (no game files required)
  - `test_game.py` - 73 real game file tests (uses `test_paths.txt` configuration)
- All modules can run standalone or via unified runner
- Total: 247 tests passing

#### Removed

- `test_suite.py` - Merged into `test_api.py`
- `real_game_tests.py` - Renamed to `test_game.py`

---

## [1.0.1] - 2026-02-04

### Research Integration

Integrated extensive research and tooling from private development repository.

#### Added Documentation

- **DEFINITIVE_BHAV_REFERENCE.md** (25KB) - Complete BHAV technical guide with execution model
- **FREESO_BEHAVIORAL_ARCHITECTURE.md** (35KB) - Deep FreeSO VM analysis with hook points
- **BHAV_OPCODE_REFERENCE.md** - Comprehensive opcode documentation
- **ENGINE_PRIMITIVES.md** - Primitive opcode classifications
- **RESOURCE_GRAPH_USAGE_GUIDE.md** - Graph infrastructure usage guide
- **VALIDATION_TRUST_GUIDE.md** - Trust and validation system analysis
- **CYCLE_PATTERNS_GUIDE.md** - Behavioral cycle pattern documentation
- **INTEGRATION_GAPS.md** - Tracks remaining integration work

#### Added Tools

- **freeso_gap_analyzer.py** - FreeSO parity gap analysis with implementation priorities
- **webviewer/** - Complete web-based viewer suite:
  - `character_viewer.html` - Interactive character browser
  - `object_viewer.html` - Interactive object browser
  - `library_browser.html` - Mesh/sprite library browser
  - `graph_viewer_embed.html` - Interactive graph visualization
  - `export_server.py` (34KB) - Flask server for web exports

#### Added Data Files

- **global_behavior_database.json** (23KB) - 251 base game globals with expansion block ranges
- **characters.json** (2MB) - Extracted character data for all game sims
- **objects.json** (3MB) - Extracted object data for all game objects
- **meshes.json** (209KB) - Mesh metadata

#### Fixed

- `test_suite.py` path setup for dev/tests/ location (now 135/135 tests pass)
- `test_paths.txt` updated with new data file documentation

---

## [1.0.0] - 2026-02-04

### Initial Release

First public release of the SimObliterator Suite - a comprehensive toolkit for analyzing, editing, and extracting data from The Sims 1 game files.

### Core Systems

- **IFF File Parser** - Complete support for IFF container format with chunk-level access
- **FAR Archive Support** - FAR1 and FAR3 archive reading/writing with recursive discovery
- **DBPF Support** - Package file format support for expansion content
- **38 Chunk Types** - Full parser implementations for all known IFF chunk types

### Behavior Analysis

- **BHAV Disassembler** - Full SimAntics bytecode decoding with semantic primitives
- **Primitive Reference** - Operand field definitions for all common primitives
- **Variable Analyzer** - Track locals, temps, params, attributes with data flow analysis
- **Call Graph Builder** - Visualize behavior relationships and dependencies
- **Execution Tracer** - Path analysis, dead code detection, loop identification
- **Behavior Classifier** - Categorize BHAVs as ROLE/ACTION/GUARD/FLOW/UTILITY
- **Behavior Profiler** - Analyze entry points, yields, complexity metrics
- **BHAV Authoring** - Create new instructions from scratch with operand builders

### String Table Support

- **STR# Parser** - Full format support (0xFFFF, 0xFDFF, 0xFEFF, Pascal)
- **Language Awareness** - 20 language codes with proper slot handling
- **Reference Scanner** - Find all STR# usage from OBJD, TTAB, CTSS
- **Localization Audit** - Detect missing translations with auto-fix

### SLOT Resource Support

- **SLOT Parser** - Complete routing slot parsing (versions 2-4)
- **SLOT Editor** - Add, remove, duplicate slots programmatically
- **SLOT Templates** - Pre-built templates for chairs, counters
- **XML Export/Import** - Transmogrifier-compatible XML workflow

### TTAB Interaction Support

- **Full Field Parsing** - All versions 4-10 with autonomy and motive effects
- **Multi-Object Context** - Map resources to objects in multi-OBJD files
- **Motive Effects** - Full motive delta/min/personality parsing
- **TTAB Editor** - Modify autonomy, flags, action/test BHAVs

### Lot Analysis

- **Terrain Detection** - House number to terrain type mapping (from FreeSO)
- **Ambience System** - 35 ambient sound definitions with GUIDs
- **ARRY Chunk Analysis** - Floor, wall, object placement arrays
- **Object Placement** - Parse placed object positions and rotations

### Save File Editing

- **Save Manager** - Load and modify save game files safely
- **Family Money** - Edit household funds (simoleons)
- **Sim Skills** - All 7 skills (Cooking, Mechanical, Charisma, Logic, Body, Creativity, Cleaning)
- **Sim Motives** - All 8 motives (Hunger, Comfort, Hygiene, Bladder, Energy, Fun, Social, Room)
- **Sim Personality** - 5 traits (Neat, Outgoing, Active, Playful, Nice)
- **Career Manager** - 24 career tracks with promotions
- **Relationship Editor** - Daily and lifetime relationship values
- **Aspiration Manager** - Modify aspiration points (save_mutations.py)
- **Memory Manager** - Edit sim memories (save_mutations.py)

### Export/Import

- **Sprite Export** - SPR2 to PNG with palette handling
- **Sprite Sheets** - Combine frames into single image
- **Mesh Export** - 3D models to glTF/GLB format
- **Chunk Export** - Export raw chunk bytes

### ID Conflict Detection

- **GUID Scanner** - Detect duplicate GUIDs across files
- **BHAV ID Overlap** - Warn on local BHAV ID conflicts
- **Semi-Global Conflicts** - Detect group ID issues
- **Range Finder** - Find unused ID ranges for safe assignment

### Safety System

- **Mutation Pipeline** - All writes validated through single barrier
- **Transaction Model** - Preview changes before commit
- **Snapshot Manager** - Chunk-level snapshots for restoration
- **Backup Manager** - Automatic backups before modifications
- **Audit Trail** - Full logging of all write operations
- **Rollback Support** - Undo pending changes

### Content Validation

- **Scope Validator** - Validate resource scope boundaries
- **BHAV Validator** - Check instruction pointers and references
- **ID Conflict Scanner** - Pre-flight check for conflicts

### Research & Data Gathering

- **Unknowns Database** - Persistent storage for discovered unknowns
- **Opcode Database** - 143 opcode definitions from game analysis
- **Global Behaviors DB** - Mapping of global behavior IDs
- **Execution Model** - Documented engine semantics

### Test Coverage

- 73 tests across 17 categories
- Real game file validation
- Round-trip encoding verification

---

## [Unreleased]

### Planned

- MacOS support
- Linux support
- Plugin system for custom analyzers
- Batch processing improvements
