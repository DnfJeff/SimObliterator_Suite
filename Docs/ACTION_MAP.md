# SimObliterator Action Map

**Auto-generated from action_registry.py and test coverage**  
**Version 1.0.3 | 276 Tests | 161 Actions**

This document maps every registered action to its implementing module, tested functionality, and UI integration notes.

---

## Quick Reference

| Category | Actions | Write | High-Risk | Module |
|----------|---------|-------|-----------|--------|
| file_container | 16 | 12 | 6 | `file_operations.py`, `container_operations.py` |
| save_state | 16 | 16 | 4 | `save_mutations.py`, `save_manager.py` |
| bhav | 23 | 11 | 11 | `bhav_operations.py`, `bhav_patching.py` |
| visualization | 9 | 0 | 0 | `mesh_export.py`, chunk parsers |
| export | 9 | 0 | 0 | `mesh_export.py`, `advanced_import_export.py` |
| import | 9 | 9 | 5 | `import_operations.py` |
| analysis | 20 | 0 | 0 | `analysis_operations.py`, graph modules |
| search | 9 | 0 | 0 | `asset_scanner.py` |
| system | 10 | 5 | 1 | `container_operations.py` |
| ui | 8 | 1 | 1 | GUI layer (your responsibility) |
| ttab | 8 | 4 | 2 | `chunk_parsers.py` |
| slot | 8 | 6 | 0 | `chunk_parsers.py` |
| localization | 8 | 3 | 0 | `chunk_parsers.py` |

---

## Test Coverage by Action Category

From `Full_Test_Example.txt` (276 tests passing):

### Core Systems Verified
- Action Registry: 7 tests (loading, validation, rejection, mode gating)
- Mutation Pipeline: 5 tests (singleton, modes, request/diff creation)
- Provenance System: 4 tests
- Safety API: 5 tests

### File Parsing Verified
- IFF Parser: 3 tests
- FAR Parser: 3 tests
- DBPF Parser: 3 tests
- Chunk Parsers: 7 tests (60 parsers available)

### BHAV Operations Verified
- BHAV Executor: 6 tests (VMPrimitiveExitCode, ExecutionTrace)
- BHAV Operations: 5 tests (Serializer, Validator, Editor, Importer)
- BHAV Patching: 13 tests (scope detection, call opcodes, rewiring)

### Save Editing Verified (NEW in v1.0.3)
- Skill modification: tested
- Motive modification: tested
- Personality modification: tested
- Career data: tested
- Relationship editing: tested (in-memory)
- Family budget: tested

---

## 1. FILE/CONTAINER ACTIONS

### LoadIFF
| Property | Value |
|----------|-------|
| **Action** | `LoadIFF` |
| **Module** | `src/formats/iff/iff_file.py` |
| **Class** | `IffFile` |
| **Method** | `IffFile(path).parse()` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_api.py: IFF Parser) |

**Usage:**
```python
from formats.iff.iff_file import IffFile

iff = IffFile(path)
iff.parse()
chunks = iff.get_chunks_by_type('OBJD')
```

### LoadFAR
| Property | Value |
|----------|-------|
| **Action** | `LoadFAR` |
| **Module** | `src/formats/far/far1.py` |
| **Class** | `FAR1Archive` |
| **Method** | `FAR1Archive(path)` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_api.py: FAR Parser) |

**Usage:**
```python
from formats.far.far1 import FAR1Archive

far = FAR1Archive(path)
entries = far.entries
data = far.extract(entry_name)
```

### LoadSave
| Property | Value |
|----------|-------|
| **Action** | `LoadSave` |
| **Module** | `src/Tools/save_editor/save_manager.py` |
| **Class** | `SaveManager` |
| **Method** | `SaveManager.load_save(path)` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_game.py: saves category) |

**Usage:**
```python
from Tools.save_editor.save_manager import SaveManager

mgr = SaveManager()
mgr.load_save(user_data_path)
families = mgr.families
sims = mgr.get_family_members(family_id)
```

### WriteSave
| Property | Value |
|----------|-------|
| **Action** | `WriteSave` |
| **Module** | `src/Tools/save_editor/save_manager.py` |
| **Method** | `SaveManager.write_changes()` |
| **Mutability** | WRITE |
| **Risk** | HIGH |
| **Requires Pipeline** | Yes (MUTATE mode) |
| **Requires Confirmation** | Yes |
| **Tested** | Yes (test_game.py: save_edit category) |

**Usage:**
```python
# Must be in MUTATE mode
from Tools.core.mutation_pipeline import MutationPipeline, PipelineMode

pipeline = MutationPipeline.get()
pipeline.set_mode(PipelineMode.MUTATE)

mgr.save()  # After modifications
```

### ValidateContainer
| Property | Value |
|----------|-------|
| **Action** | `ValidateContainer` |
| **Module** | `src/Tools/core/file_operations.py` |
| **Class** | `ContainerValidator` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_api.py: File Operations) |

---

## 2. SAVE-STATE MUTATIONS

All save mutations require MUTATE mode and user confirmation.

### SetMoney / AddMoney / RemoveMoney
| Property | Value |
|----------|-------|
| **Action** | `SetMoney`, `AddMoney`, `RemoveMoney` |
| **Module** | `src/Tools/save_editor/save_manager.py` |
| **Method** | `SaveManager.set_family_money(family_id, amount)` |
| **Mutability** | WRITE |
| **Risk** | MEDIUM |
| **Tested** | Yes (test_game.py: family budget tests) |

**Usage:**
```python
mgr.set_family_money(family_id=4, amount=50000)
# Prints: "Set family 4 money to $50,000"
```

### ModifySimAttributes (Skills)
| Property | Value |
|----------|-------|
| **Action** | `ModifySimAttributes` |
| **Module** | `src/Tools/save_editor/save_manager.py` |
| **Method** | `SaveManager.set_sim_skill(sim, skill_name, value)` |
| **Mutability** | WRITE |
| **Risk** | HIGH |
| **Tested** | Yes (test_game.py: skill modification) |

**Skill Indices:**
```python
COOKING_SKILL = 0
MECHANICAL_SKILL = 1
CHARISMA_SKILL = 2
LOGIC_SKILL = 3
BODY_SKILL = 4
CREATIVITY_SKILL = 5
```

**Usage:**
```python
sim = mgr.get_sim_by_name("Bob")
mgr.set_sim_skill(sim, "Cooking", 1000)  # Max skill
mgr.max_all_skills(sim)  # Set all skills to 1000
```

### ModifyMotives
| Property | Value |
|----------|-------|
| **Action** | `ModifyMotives` |
| **Module** | `src/Tools/save_editor/save_manager.py` |
| **Method** | `SaveManager.set_sim_motive(sim, motive_name, value)` |
| **Mutability** | WRITE |
| **Risk** | MEDIUM |
| **Tested** | Yes (test_game.py: motive modification) |

**Motive Indices:**
```python
HUNGER_MOTIVE = 13
COMFORT_MOTIVE = 14
HYGIENE_MOTIVE = 15
BLADDER_MOTIVE = 16
ENERGY_MOTIVE = 17
FUN_MOTIVE = 18
SOCIAL_MOTIVE = 19
ROOM_MOTIVE = 20
```

**Usage:**
```python
mgr.set_sim_motive(sim, "Hunger", 100)  # 100 = full
mgr.max_all_motives(sim)  # All motives to 100
```

### ModifyRelationships
| Property | Value |
|----------|-------|
| **Action** | `ModifyRelationships` |
| **Module** | `src/Tools/save_editor/save_manager.py` |
| **Method** | `SaveManager.set_relationship(sim, neighbor_id, daily, lifetime)` |
| **Mutability** | WRITE |
| **Risk** | HIGH |
| **Tested** | Yes (test_game.py: relationship modification) |

**Usage:**
```python
mgr.set_relationship(sim, neighbor_id=15, daily=100, lifetime=50)
# Note: Call rebuild_nbrs_chunk() to persist to binary
```

### ModifyCareer
| Property | Value |
|----------|-------|
| **Action** | `ModifyCareer` |
| **Module** | `src/Tools/save_editor/save_manager.py` |
| **Method** | `SaveManager.set_sim_career(sim, career_id, level, performance)` |
| **Mutability** | WRITE |
| **Risk** | MEDIUM |
| **Tested** | Yes (test_game.py: career modification) |

**Career Indices:**
```python
CAREER_TYPE = 23
CAREER_LEVEL = 24
CAREER_TRACK = 25
JOB_PERFORMANCE = 26
```

---

## 3. BHAV ACTIONS

### DisassembleBHAV
| Property | Value |
|----------|-------|
| **Action** | `DisassembleBHAV` |
| **Module** | `src/Tools/core/bhav_disassembler.py` |
| **Class** | `BHAVDisassembler` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_game.py: bhav_mut category) |

**Usage:**
```python
from Tools.core.bhav_disassembler import BHAVDisassembler

dis = BHAVDisassembler()
result = dis.disassemble(bhav_chunk)
for instr in result.instructions:
    print(f"0x{instr.index:02X}: {instr.opcode_name} {instr.operands}")
```

### EditBHAV
| Property | Value |
|----------|-------|
| **Action** | `EditBHAV` |
| **Module** | `src/Tools/core/bhav_operations.py` |
| **Class** | `BHAVEditor` |
| **Method** | `edit(chunk, modifications)` |
| **Mutability** | WRITE |
| **Risk** | HIGH |
| **Requires Pipeline** | Yes |
| **Tested** | Yes (test_game.py: BHAV edit/undo cycle) |

**Usage:**
```python
from Tools.core.bhav_operations import BHAVEditor

editor = BHAVEditor()
# Edit returns undo data for rollback
undo_data = editor.edit(chunk, {"operand_0": 0x42})
# Undo if needed
editor.undo(chunk, undo_data)
```

### ValidateBHAVGraph
| Property | Value |
|----------|-------|
| **Action** | `ValidateBHAVGraph` |
| **Module** | `src/Tools/core/bhav_operations.py` |
| **Class** | `BHAVValidator` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_api.py: BHAV Operations) |

### DetectUnknownOpcodes
| Property | Value |
|----------|-------|
| **Action** | `DetectUnknownOpcodes` |
| **Module** | `src/Tools/core/opcode_loader.py` |
| **Function** | `lookup_opcode(id)` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_game.py: opcode lookup) |

---

## 4. ANALYSIS ACTIONS

### BuildCallGraph
| Property | Value |
|----------|-------|
| **Action** | `BuildCallGraph` |
| **Module** | `src/Tools/graph/call_graph_builder.py` |
| **Class** | `CallGraphBuilder` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_game.py: graph category) |

**Usage:**
```python
from Tools.graph.call_graph_builder import CallGraphBuilder

builder = CallGraphBuilder(iff)
graph = builder.build()
# Returns NetworkX DiGraph
```

### BuildResourceGraph
| Property | Value |
|----------|-------|
| **Action** | `BuildResourceGraph` |
| **Module** | `src/Tools/graph/resource_graph.py` |
| **Class** | `ResourceGraph` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_game.py: graph category) |

---

## 5. ENTITY ABSTRACTIONS

These are data containers UI developers use for display:

### ObjectEntity
| Property | Value |
|----------|-------|
| **Module** | `src/Tools/entities/object_entity.py` |
| **Class** | `ObjectEntity` |
| **Tested** | Yes (test_api.py: Entity Abstractions) |

### BehaviorEntity
| Property | Value |
|----------|-------|
| **Module** | `src/Tools/entities/behavior_entity.py` |
| **Class** | `BehaviorEntity` |
| **Tested** | Yes (test_api.py: Entity Abstractions) |

### SimEntity
| Property | Value |
|----------|-------|
| **Module** | `src/Tools/entities/sim_entity.py` |
| **Class** | `SimEntity` |
| **Tested** | Yes (test_api.py: Entity Abstractions) |

---

## 6. EXPORT ACTIONS

### ExportSpritePNGs
| Property | Value |
|----------|-------|
| **Action** | `ExportSpritePNGs` |
| **Module** | `src/Tools/core/mesh_export.py` |
| **Class** | `ChunkMeshExporter` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_game.py: export category) |

### ExportMesh
| Property | Value |
|----------|-------|
| **Action** | `ExportMesh` |
| **Module** | `src/Tools/core/mesh_export.py` |
| **Class** | `GLTFExporter` |
| **Mutability** | READ |
| **Risk** | LOW |
| **Tested** | Yes (test_api.py: Mesh Export) |

---

## UI Integration Checklist

For each action your UI exposes:

- [ ] Check `is_registered_action(name)` exists
- [ ] Use `validate_action(name, context)` before execution
- [ ] Set pipeline mode if action `requires_pipeline`
- [ ] Show confirmation dialog if action `requires_confirmation`
- [ ] Handle write actions in MUTATE mode only
- [ ] Display safety badges for HIGH risk actions
- [ ] Log audit trail via `ActionRegistry.get().get_audit_log()`

---

## Module Import Paths

```python
# Core
from Tools.core.action_registry import ActionRegistry, validate_action
from Tools.core.mutation_pipeline import MutationPipeline, PipelineMode
from Tools.core.bhav_operations import BHAVEditor, BHAVSerializer, BHAVValidator
from Tools.core.bhav_disassembler import BHAVDisassembler
from Tools.core.file_operations import BackupManager, IFFWriter, ChunkOperations
from Tools.core.container_operations import CacheManager, IFFMerger, IFFSplitter
from Tools.core.import_operations import ChunkImporter, SpriteImporter
from Tools.core.mesh_export import GLTFExporter, ChunkMeshExporter
from Tools.core.analysis_operations import ForensicAnalyzer
from Tools.core.opcode_loader import lookup_opcode

# Formats
from formats.iff.iff_file import IffFile
from formats.far.far1 import FAR1Archive
from formats.far.far3 import FAR3Archive
from formats.dbpf.dbpf import DBPFArchive

# Save Editing
from Tools.save_editor.save_manager import SaveManager

# Entities (for display)
from Tools.entities.object_entity import ObjectEntity
from Tools.entities.behavior_entity import BehaviorEntity
from Tools.entities.sim_entity import SimEntity

# Graph
from Tools.graph.call_graph_builder import CallGraphBuilder
from Tools.graph.resource_graph import ResourceGraph
```

---

## Related Documentation

- [ACTION_SURFACE.md](ACTION_SURFACE.md) - Complete action reference with properties
- [UI_API_REFERENCE.md](guides/UI_API_REFERENCE.md) - Headless API quickstart
- [MODULE_INVENTORY.md](guides/MODULE_INVENTORY.md) - All importable modules
- [headless_examples.py](../dev/headless_examples.py) - Runnable API demonstrations

---

*Last updated: v1.0.3 (2026-02-04)*
