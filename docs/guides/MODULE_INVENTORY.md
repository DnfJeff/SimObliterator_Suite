# SimObliterator Module Inventory

Complete list of importable modules for UI and tooling integration.

---

## Core Modules (49)

All modules are importable via `from Tools.core.{module} import ...`

| Module                            | Primary Exports                             | Category      |
| --------------------------------- | ------------------------------------------- | ------------- |
| `action_mapper`                   | ActionMapper                                | Mapping       |
| `action_registry`                 | ActionRegistry, validate_action, get_action | Registry      |
| `advanced_import_export`          | AdvancedExporter, bulk_export               | Import/Export |
| `analysis_operations`             | AnalysisEngine, analyze_iff                 | Analysis      |
| `asset_scanner`                   | AssetScanner, scan_assets                   | Scanning      |
| `behavior_classifier`             | BehaviorClassifier                          | Behavior      |
| `behavior_library`                | BehaviorLibrary                             | Behavior      |
| `behavior_library_generator`      | generate_behavior_library                   | Behavior      |
| `behavior_profiler`               | BehaviorProfiler                            | Behavior      |
| `behavior_relationship_extractor` | extract_relationships                       | Behavior      |
| `behavior_trigger_extractor`      | extract_triggers                            | Behavior      |
| `bhav_authoring`                  | BHAVAuthoring, create_bhav                  | BHAV          |
| `bhav_call_graph`                 | BHAVCallGraph, build_call_graph             | BHAV          |
| `bhav_disassembler`               | BHAVDisassembler, disassemble               | BHAV          |
| `bhav_executor`                   | BHAVExecutor, execute_simulation            | BHAV          |
| `bhav_opcodes`                    | get_opcode_info, OPCODES                    | BHAV          |
| `bhav_operations`                 | BHAVOperations                              | BHAV          |
| `bhav_patching`                   | BHAVPatcher, patch_instruction              | BHAV          |
| `bhav_rewiring`                   | BHAVRewirer, rewire_calls                   | BHAV          |
| `chunk_parsers`                   | parse_chunk, ChunkParser                    | Parsing       |
| `chunk_parsers_objf`              | parse_objf, OBJfParser                      | Parsing       |
| `container_operations`            | ContainerOps, list_files                    | Container     |
| `file_operations`                 | FileOps, open_file, save_file               | File I/O      |
| `forensic_module`                 | ForensicAnalyzer                            | Forensics     |
| `id_conflict_scanner`             | scan_id_conflicts                           | Scanning      |
| `iff_reader`                      | IFFReader, read_iff                         | File I/O      |
| `import_operations`               | import_chunk, ImportManager                 | Import/Export |
| `localization_audit`              | audit_localization                          | Analysis      |
| `lot_iff_analyzer`                | analyze_lot                                 | Analysis      |
| `mapping_db`                      | MappingDB, lookup_mapping                   | Database      |
| `mesh_export`                     | MeshExporter, export_mesh                   | Mesh          |
| `mutation_pipeline`               | MutationPipeline, MutationMode              | Mutation      |
| `object_dominance_analyzer`       | analyze_dominance                           | Analysis      |
| `opcode_loader`                   | load_opcodes, OpcodeDB                      | Database      |
| `output_formatters`               | format_json, format_table                   | Output        |
| `primitive_reference`             | PrimitiveReference                          | BHAV          |
| `provenance`                      | ProvenanceTracker, track_origin             | Tracking      |
| `safety`                          | SafetyChecker, validate_safe                | Safety        |
| `save_mutations`                  | SaveMutator, mutate_save                    | Save Editing  |
| `skin_registry`                   | SkinRegistry, list_skins                    | Registry      |
| `slot_editor`                     | SlotEditor, edit_slots                      | Editing       |
| `str_parser`                      | parse_str, STRParser                        | Parsing       |
| `str_reference_scanner`           | scan_str_refs                               | Scanning      |
| `trigger_role_graph`              | TriggerRoleGraph                            | Graph         |
| `ttab_editor`                     | TTABEditor, edit_ttab                       | Editing       |
| `ui_actions`                      | UIActions                                   | UI            |
| `unknowns_db`                     | UnknownsDB, lookup_unknown                  | Database      |
| `variable_analyzer`               | analyze_variables                           | Analysis      |
| `workspace_persistence`           | WorkspacePersistence, save_workspace        | Persistence   |
| `world_mutations`                 | WorldMutator, mutate_world                  | Mutation      |

---

## Entity Modules (4)

High-level abstractions for game data. Import via `from Tools.entities.{module} import ...`

| Module                | Primary Exports    | Description                 |
| --------------------- | ------------------ | --------------------------- |
| `behavior_entity`     | BehaviorEntity     | BHAV behavior wrapper       |
| `object_entity`       | ObjectEntity       | Game object abstraction     |
| `relationship_entity` | RelationshipEntity | Sim relationship data       |
| `sim_entity`          | SimEntity          | Complete Sim representation |

---

## Format Modules

### IFF (`from formats.iff.{module} import ...`)

| Module     | Primary Exports    |
| ---------- | ------------------ |
| `base`     | IFFBase, ChunkBase |
| `iff_file` | IFFFile, load_iff  |

### DBPF (`from formats.dbpf.{module} import ...`)

| Module | Primary Exports                 |
| ------ | ------------------------------- |
| `dbpf` | DBPFFile, read_dbpf, write_dbpf |

### FAR (`from formats.far.{module} import ...`)

| Module | Primary Exports     |
| ------ | ------------------- |
| `far1` | FAR1File, read_far1 |
| `far3` | FAR3File, read_far3 |

### Mesh (`from formats.mesh.{module} import ...`)

| Module        | Primary Exports |
| ------------- | --------------- |
| `bcf`         | BCFFile         |
| `bmf`         | BMFFile         |
| `cfp`         | CFPFile         |
| `cmx`         | CMXFile         |
| `skn`         | SKNFile         |
| `gltf_export` | export_gltf     |

---

## GUI Modules

Import via `from Tools.gui.{module} import ...`

| Module   | Primary Exports      |
| -------- | -------------------- |
| `state`  | AppState (singleton) |
| `events` | EventBus, Events     |
| `theme`  | apply_theme, COLORS  |

---

## Quick Import Reference

```python
# Action System
from Tools.core.action_registry import ActionRegistry, validate_action

# Mutation Pipeline
from Tools.core.mutation_pipeline import MutationPipeline, MutationMode

# BHAV Operations
from Tools.core.bhav_disassembler import BHAVDisassembler
from Tools.core.bhav_opcodes import get_opcode_info
from Tools.core.bhav_patching import BHAVPatcher

# File Operations
from Tools.core.file_operations import FileOps
from Tools.core.container_operations import ContainerOps

# Save Editing
from Tools.core.save_mutations import SaveMutator

# Entities
from Tools.entities.sim_entity import SimEntity
from Tools.entities.object_entity import ObjectEntity

# Formats
from formats.iff.iff_file import IFFFile
from formats.dbpf.dbpf import DBPFFile
```

---

## Related Documentation

- [ACTION_MAP.md](../ACTION_MAP.md) - Action to module mapping
- [ACTION_SURFACE.md](../ACTION_SURFACE.md) - Complete action reference
- [UI_API_REFERENCE.md](UI_API_REFERENCE.md) - Headless API quickstart
- [UI_DEVELOPER_GUIDE.md](UI_DEVELOPER_GUIDE.md) - GUI implementation guide
