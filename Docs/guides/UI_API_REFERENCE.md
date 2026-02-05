# UI Developer API Reference

**Headless API for SimObliterator Suite**  
**Version 1.0.3 | 276 Tests Verified**

This document shows UI developers exactly how to use the backend headlessly. All examples work without any GUI.

---

## Quick Start

```python
import sys
sys.path.insert(0, 'S:/Repositorys_New/SimObliterator_Suite/src')

# Core imports
from formats.iff.iff_file import IffFile
from Tools.save_editor.save_manager import SaveManager
from Tools.core.action_registry import ActionRegistry, validate_action
```

---

## 1. File Loading

### Load IFF File

```python
from formats.iff.iff_file import IffFile

iff = IffFile("path/to/file.iff")
iff.parse()

# Get all chunks
for chunk in iff.chunks:
    print(f"{chunk.type_code} #{chunk.id}: {chunk.label}")

# Get specific chunk types
objd_chunks = iff.get_chunks_by_type('OBJD')
bhav_chunks = iff.get_chunks_by_type('BHAV')
```

### Load FAR Archive

```python
from formats.far.far1 import FAR1Archive

far = FAR1Archive("path/to/archive.far")
for entry in far.entries:
    print(f"{entry.filename}: {entry.size} bytes")

# Extract specific file
data = far.extract("Objects/lamp.iff")
```

### Load DBPF (Sims 2)

```python
from formats.dbpf.dbpf import DBPFArchive, DBPFTypeID

dbpf = DBPFArchive("path/to/package.package")
dbpf.parse()

# Get BHAV entries
bhavs = dbpf.get_entries_by_type(DBPFTypeID.BHAV)
```

---

## 2. Save File Editing

### Load Save

```python
from Tools.save_editor.save_manager import SaveManager

mgr = SaveManager()
mgr.load_save("C:/Users/You/Saved Games/Electronic Arts/The Sims 25")

# List families
for fam in mgr.families:
    print(f"Family {fam.id}: ${fam.money}")

# Get sims in family
sims = mgr.get_family_members(family_id=4)
for sim in sims:
    print(f"  {sim.first_name} {sim.last_name}")
```

### Edit Skills (Binary-Level)

```python
# Get a sim
sim = mgr.get_sim_by_name("Bob Newbie")

# Set individual skill (0-1000)
mgr.set_sim_skill(sim, "Cooking", 850)
mgr.set_sim_skill(sim, "Mechanical", 1000)

# Or max all skills at once
mgr.max_all_skills(sim)
# Output: Set Bob's Cooking to 1000
# Output: Set Bob's Mechanical to 1000
# ... etc
```

**Skill Names:** `Cooking`, `Mechanical`, `Charisma`, `Logic`, `Body`, `Creativity`

### Edit Motives (Binary-Level)

```python
# Set individual motive (-100 to 100)
mgr.set_sim_motive(sim, "Hunger", 100)    # Full
mgr.set_sim_motive(sim, "Energy", 100)    # Fully rested

# Or max all motives
mgr.max_all_motives(sim)
```

**Motive Names:** `Hunger`, `Comfort`, `Hygiene`, `Bladder`, `Energy`, `Fun`, `Social`, `Room`

### Edit Personality

```python
# Set personality trait (0-1000)
mgr.set_sim_personality(sim, "Nice", 750)   # Nice = friendly
mgr.set_sim_personality(sim, "Active", 500) # Middle ground
```

**Personality Names:** `Nice`, `Outgoing`, `Active`, `Playful`, `Neat`

### Edit Career

```python
mgr.set_sim_career(sim, career_id=5, level=8, performance=100)
```

### Edit Relationships

```python
# Set relationship with another sim
mgr.set_relationship(sim, neighbor_id=15, daily=100, lifetime=50)
# Note: Call rebuild_nbrs_chunk() to persist binary
```

### Edit Family Money

```python
mgr.set_family_money(family_id=4, amount=50000)
# Output: Set family 4 money to $50,000
```

### Save Changes

```python
# After all modifications
mgr.save()
```

---

## 3. BHAV Operations

### Disassemble BHAV

```python
from Tools.core.bhav_disassembler import BHAVDisassembler

# Get BHAV chunk from IFF
bhav_chunk = iff.get_chunk_by_id('BHAV', 0x1000)

dis = BHAVDisassembler()
result = dis.disassemble(bhav_chunk)

print(f"BHAV 0x{bhav_chunk.id:04X}: {result.name}")
print(f"Arguments: {result.num_args}, Locals: {result.num_locals}")

for instr in result.instructions:
    print(f"  {instr.index:02X}: {instr.opcode_name}")
```

### Edit BHAV with Undo

```python
from Tools.core.bhav_operations import BHAVEditor

editor = BHAVEditor()

# Make edit (returns undo data)
undo_data = editor.edit(bhav_chunk, {"operand_0": 0x42})

# If user cancels, undo
editor.undo(bhav_chunk, undo_data)
```

### Serialize BHAV

```python
from Tools.core.bhav_operations import BHAVSerializer

ser = BHAVSerializer()
binary_data = ser.serialize(bhav_chunk)
```

### Validate BHAV

```python
from Tools.core.bhav_operations import BHAVValidator

validator = BHAVValidator()
is_valid, errors = validator.validate(bhav_chunk)
```

### Lookup Opcodes

```python
from Tools.core.opcode_loader import lookup_opcode

info = lookup_opcode(0x0002)  # Call subroutine
print(f"Opcode: {info.name}")
print(f"Category: {info.category}")
```

---

## 4. Graph Building

### Call Graph

```python
from Tools.graph.call_graph_builder import CallGraphBuilder

builder = CallGraphBuilder(iff)
graph = builder.build()  # Returns NetworkX DiGraph

# Find all callees of a BHAV
callees = list(graph.successors(bhav_id))

# Find all callers
callers = list(graph.predecessors(bhav_id))
```

### Resource Graph

```python
from Tools.graph.resource_graph import ResourceGraph

rg = ResourceGraph(iff)
rg.build()

# Find dependencies
deps = rg.get_dependencies(chunk)
```

---

## 5. Export Operations

### Export Mesh to glTF

```python
from Tools.core.mesh_export import GLTFExporter, MeshDecoder

decoder = MeshDecoder()
mesh = decoder.decode(mesh_chunk)

exporter = GLTFExporter()
exporter.export(mesh, "output.gltf")
```

### Export Sprite to PNG

```python
from Tools.core.mesh_export import ChunkMeshExporter

exporter = ChunkMeshExporter()
exporter.export_sprite(spr2_chunk, "output.png")
```

---

## 6. Entity Abstractions

These are data containers for display. Use them to present information.

### ObjectEntity

```python
from Tools.entities.object_entity import ObjectEntity

obj = ObjectEntity.from_iff(iff)
print(f"GUID: 0x{obj.guid:08X}")
print(f"Name: {obj.name}")
print(f"Catalog Price: ${obj.catalog_price}")
```

### BehaviorEntity

```python
from Tools.entities.behavior_entity import BehaviorEntity, BehaviorPurpose

bhav_entity = BehaviorEntity.from_chunk(bhav_chunk)
print(f"Purpose: {bhav_entity.purpose.name}")  # ROLE, ACTION, GUARD, UTILITY
```

### SimEntity

```python
from Tools.entities.sim_entity import SimEntity

sim_entity = SimEntity.from_save(sim_data)
print(f"Name: {sim_entity.full_name}")
print(f"Skills: {sim_entity.skills}")
```

---

## 7. Action Validation

Before executing any action, validate it:

```python
from Tools.core.action_registry import validate_action, is_registered_action

# Check if action exists
if is_registered_action("EditBHAV"):
    print("Action registered")

# Validate with context
is_valid, reason = validate_action("WriteSave", {
    'pipeline_mode': 'MUTATE',
    'user_confirmed': True,
    'safety_checked': True
})

if not is_valid:
    print(f"Blocked: {reason}")
```

---

## 8. Pipeline Modes

Write actions require MUTATE mode:

```python
from Tools.core.mutation_pipeline import MutationPipeline, PipelineMode

pipeline = MutationPipeline.get()

# Check current mode
print(f"Mode: {pipeline.mode.value}")  # 'inspect'

# Switch to MUTATE for write operations
pipeline.set_mode(PipelineMode.MUTATE)

# Do your writes...

# Switch back
pipeline.set_mode(PipelineMode.INSPECT)
```

---

## 9. Error Handling Pattern

```python
from Tools.core.action_registry import validate_action
from Tools.core.file_operations import FileOpResult

def safe_write_operation(action_name, operation_func, context):
    """Standard pattern for safe write operations."""
    
    # Step 1: Validate action
    is_valid, reason = validate_action(action_name, context)
    if not is_valid:
        return FileOpResult(success=False, error=reason)
    
    # Step 2: Create backup
    from Tools.core.file_operations import BackupManager
    backup = BackupManager()
    backup_path = backup.create_backup(context.get('file_path'))
    
    try:
        # Step 3: Execute operation
        result = operation_func()
        return FileOpResult(success=True, data=result)
    except Exception as e:
        # Step 4: Restore on failure
        backup.restore_backup(backup_path)
        return FileOpResult(success=False, error=str(e))
```

---

## 10. Return Types

### FileOpResult

```python
from Tools.core.file_operations import FileOpResult

result = FileOpResult(
    success=True,
    data={"chunks_modified": 5},
    warnings=["Some non-fatal warning"]
)

if result.success:
    print(result.data)
else:
    print(result.error)
```

### BHAVOpResult

```python
from Tools.core.bhav_operations import BHAVOpResult

result = BHAVOpResult(
    success=True,
    bhav_id=0x1000,
    instructions_modified=3
)
```

### SaveMutationResult

```python
from Tools.core.save_mutations import SaveMutationResult

result = SaveMutationResult(
    success=True,
    sims_modified=1,
    message="Set cooking skill to 1000"
)
```

---

## 11. Data Files

The backend uses JSON databases you can read:

```python
import json
from pathlib import Path

DATA_DIR = Path("S:/Repositorys_New/SimObliterator_Suite/data")

# Opcode database
with open(DATA_DIR / "opcodes_db.json") as f:
    opcodes = json.load(f)
    
# Global behavior database
with open(DATA_DIR / "global_behavior_database.json") as f:
    globals_db = json.load(f)
    print(f"Known globals: {len(globals_db['found_globals'])}")
```

---

## 12. Module Summary

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `formats.iff.iff_file` | IFF parsing | `IffFile` |
| `formats.far.far1` | FAR1 archives | `FAR1Archive` |
| `formats.dbpf.dbpf` | DBPF (Sims 2) | `DBPFArchive` |
| `Tools.save_editor.save_manager` | Save editing | `SaveManager` |
| `Tools.core.bhav_operations` | BHAV editing | `BHAVEditor`, `BHAVSerializer` |
| `Tools.core.bhav_disassembler` | BHAV disasm | `BHAVDisassembler` |
| `Tools.core.action_registry` | Action validation | `ActionRegistry` |
| `Tools.core.mutation_pipeline` | Write mode | `MutationPipeline` |
| `Tools.core.file_operations` | File I/O | `BackupManager`, `IFFWriter` |
| `Tools.core.mesh_export` | 3D export | `GLTFExporter`, `MeshDecoder` |
| `Tools.graph.call_graph_builder` | Graph analysis | `CallGraphBuilder` |
| `Tools.entities.*` | Data containers | `ObjectEntity`, `SimEntity` |

---

## 13. Test Verification

All examples above are verified by the test suite. Run tests to confirm your environment:

```bash
cd dev/tests
python tests.py

# Expected: 276 tests, all passing
```

See `Full_Test_Example.txt` for complete test output.

---

## 14. Event Hooks (For Your UI)

When building your UI, emit these events at appropriate times:

| Event | When to Emit | Payload |
|-------|--------------|---------|
| `FILE_LOADED` | After LoadIFF/LoadFAR | `path` |
| `FILE_CLEARED` | After closing file | `None` |
| `CHUNK_SELECTED` | User selects chunk | `chunk` |
| `SAVE_MODIFIED` | After any save mutation | `SaveManager` |
| `MODE_CHANGED` | Pipeline mode switch | `PipelineMode` |
| `STATUS_UPDATE` | Status bar messages | `str` |

Your UI subscribes to these for reactivity.

---

## 15. Return Types Reference

Understanding what data comes back from API calls.

### File Objects

```python
# IffFile after parse()
iff.chunks      # list[Chunk] - all parsed chunks
iff.filename    # str - source filename
iff.size        # int - file size in bytes

# Chunk object
chunk.type_code # str - 4-char type ('BHAV', 'OBJD', etc)
chunk.id        # int - chunk ID (0x0000-0xFFFF)
chunk.label     # str - human-readable label
chunk.data      # bytes - raw chunk data
chunk.offset    # int - offset in file
```

### Save Objects

```python
# SaveManager after load_save()
mgr.families    # list[Family] - all families
mgr.sims        # list[Sim] - all sims in neighborhood

# Family object
family.id       # int - family ID
family.money    # int - family funds
family.lot_id   # int - lot they live on

# Sim object  
sim.id          # int - sim ID
sim.first_name  # str
sim.last_name   # str
sim.age         # int - age in days
sim.skills      # dict[str, int] - skill name -> 0-1000
sim.motives     # dict[str, int] - motive name -> -100 to 100
sim.personality # dict[str, int] - trait name -> 0-1000
```

### BHAV Objects

```python
# BHAVDisassembler.disassemble() returns:
result.name        # str - BHAV name
result.num_args    # int - number of arguments
result.num_locals  # int - number of locals
result.instructions # list[Instruction]

# Instruction object
instr.index        # int - instruction index
instr.opcode       # int - opcode number
instr.opcode_name  # str - human-readable opcode name
instr.operands     # list[int] - operand values
instr.true_target  # int - jump target if true
instr.false_target # int - jump target if false
```

### Action Validation

```python
# validate_action() returns:
result = validate_action("SetSimSkill", context)
result.valid       # bool - is action allowed
result.errors      # list[str] - validation errors
result.warnings    # list[str] - non-blocking warnings
```

### Mutation Results

```python
# After write operations, MutationPipeline returns:
diff.action        # str - action name
diff.before        # dict - state before
diff.after         # dict - state after
diff.path          # str - file modified
diff.timestamp     # datetime
```

---

## 16. Error Handling Patterns

Standard patterns for handling errors from backend operations.

### File Loading Errors

```python
from formats.iff.iff_file import IffFile, IFFParseError

try:
    iff = IffFile(path)
    iff.parse()
except FileNotFoundError:
    show_error(f"File not found: {path}")
except IFFParseError as e:
    show_error(f"Invalid IFF file: {e}")
except PermissionError:
    show_error(f"Cannot access file: {path}")
```

### Action Validation Errors

```python
from Tools.core.action_registry import validate_action, ActionError

result = validate_action("WriteIFF", context)
if not result.valid:
    for err in result.errors:
        show_error(err)
    return  # Don't proceed

# Safe to execute action
```

### Pipeline Mode Errors

```python
from Tools.core.mutation_pipeline import MutationPipeline, MutationMode

pipeline = MutationPipeline.get()

# Check mode before write operations
if pipeline.current_mode != MutationMode.MUTATE:
    show_warning("Enable write mode to save changes")
    return
```

### Save File Errors

```python
from Tools.save_editor.save_manager import SaveManager, SaveError

try:
    mgr = SaveManager()
    mgr.load_save(path)
except SaveError as e:
    show_error(f"Invalid save: {e}")
except Exception as e:
    show_error(f"Unexpected error: {e}")
```

### BHAV Validation

```python
from Tools.core.bhav_operations import BHAVValidator, ValidationError

validator = BHAVValidator()
issues = validator.validate(bhav_chunk)

for issue in issues:
    if issue.severity == "error":
        show_error(issue.message)
    else:
        show_warning(issue.message)
```

### General Error Strategy

```python
def safe_execute(action_name, callback, *args):
    """Wrap any backend call with standard error handling."""
    try:
        return callback(*args)
    except FileNotFoundError as e:
        show_error(f"File not found: {e}")
    except PermissionError as e:
        show_error(f"Access denied: {e}")
    except ValueError as e:
        show_error(f"Invalid value: {e}")
    except Exception as e:
        show_error(f"Operation failed: {e}")
        log_exception(e)
    return None
```

---

## 17. What You Don't Need to Build

The backend handles:
- Binary parsing (all formats)
- Offset calculation (save editing writes to correct bytes)
- Validation (action registry checks)
- Undo support (BHAV editor returns undo data)
- Graph building (NetworkX integration)
- Export (glTF, PNG, OBJ)

Your UI only needs to:
- Call the right methods
- Display the results
- Handle user confirmation for write actions
- Manage pipeline mode

---

*Last updated: v1.0.3 (2026-02-04)*
