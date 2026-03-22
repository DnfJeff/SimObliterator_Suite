# UI Integration Checklist

**Step-by-step checklist for UI developers integrating with SimObliterator headless backend.**

---

## Pre-Integration Setup

- [ ] Clone repository
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Verify Python 3.10+ installed
- [ ] Run tests: `python dev/tests/tests.py` (expect 276 passing)
- [ ] Read [UI_API_REFERENCE.md](UI_API_REFERENCE.md)

---

## Phase 1: Basic File Operations

### File Loading

- [ ] Load IFF files with `IffFile(path).parse()`
- [ ] Load FAR archives with `FAR1Archive(path)`
- [ ] Load DBPF packages with `DBPFArchive(path).parse()`
- [ ] Handle `FileNotFoundError`, `PermissionError`
- [ ] Display chunk list in tree view

### File Inspection

- [ ] Iterate `iff.chunks` and display type/id/label
- [ ] Filter chunks by type with `get_chunks_by_type('BHAV')`
- [ ] Display chunk size and offset

**Verification**: Can open any IFF/FAR/DBPF and see chunk list

---

## Phase 2: Action Registry Integration

### Action Validation

- [ ] Import `from Tools.core.action_registry import validate_action`
- [ ] Validate actions before execution
- [ ] Display validation errors to user
- [ ] Check `action.is_write` before enabling save button

### Action Execution

- [ ] Differentiate READ/PREVIEW/WRITE actions
- [ ] Show confirmation dialogs for high-risk actions
- [ ] Disable write actions when pipeline not in MUTATE mode

**Verification**: Invalid actions show clear error messages

---

## Phase 3: Mutation Pipeline

### Mode Management

- [ ] Import `from Tools.core.mutation_pipeline import MutationPipeline, MutationMode`
- [ ] Get singleton: `pipeline = MutationPipeline.get()`
- [ ] Display current mode in status bar
- [ ] Add mode toggle: INSPECT → PREVIEW → MUTATE

### Write Operations

- [ ] Set mode before write: `pipeline.set_mode(MutationMode.MUTATE)`
- [ ] Create MutationRequest for each write
- [ ] Store MutationDiff for undo support

**Verification**: Mode indicator shows correct state, writes fail in INSPECT

---

## Phase 4: Save File Editing

### Save Loading

- [ ] Import `from Tools.save_editor.save_manager import SaveManager`
- [ ] Load saves: `mgr = SaveManager(); mgr.load_save(path)`
- [ ] List families with `mgr.families`
- [ ] List sims with `mgr.get_family_members(family_id)`

### Sim Editing

- [ ] Edit skills: `mgr.set_sim_skill(sim, "Cooking", 850)`
- [ ] Edit motives: `mgr.set_sim_motive(sim, "Hunger", 100)`
- [ ] Max shortcuts: `mgr.max_all_skills(sim)`, `mgr.max_all_motives(sim)`
- [ ] Edit relationships: `mgr.set_relationship(sim, neighbor_id, daily, lifetime)`

### Family Editing

- [ ] Edit money: `mgr.set_family_money(family_id, amount)`
- [ ] Save changes: `mgr.save()`

**Verification**: Can edit sim stats and see changes persist after save/reload

---

## Phase 5: BHAV Operations

### BHAV Viewing

- [ ] Disassemble: `BHAVDisassembler().disassemble(bhav_chunk)`
- [ ] Display instruction list with opcode names
- [ ] Show true/false targets for branching
- [ ] Lookup opcodes: `get_opcode_info(opcode_id)`

### BHAV Editing

- [ ] Edit with undo: `editor.edit(chunk, changes)` returns undo data
- [ ] Implement undo: `editor.undo(chunk, undo_data)`
- [ ] Validate changes: `BHAVValidator().validate(chunk)`

**Verification**: Can view BHAV disassembly, make edit, undo

---

## Phase 6: Entity Abstractions

### Object Entities

- [ ] Import `from Tools.entities.object_entity import ObjectEntity`
- [ ] Wrap chunk: `obj = ObjectEntity(objd_chunk)`
- [ ] Access properties: `obj.name`, `obj.guid`, `obj.price`

### Sim Entities

- [ ] Import `from Tools.entities.sim_entity import SimEntity`
- [ ] Access all sim data through single abstraction
- [ ] Use for display in inspector panels

**Verification**: Entity properties match raw chunk data

---

## Phase 7: Mesh & Export

### Mesh Visualization

- [ ] Load mesh: `from formats.mesh.skn import SKNFile`
- [ ] Parse: `mesh = SKNFile(data); mesh.parse()`
- [ ] Export OBJ: `from Tools.core.mesh_export import MeshVisualizer; MeshVisualizer(mesh).to_obj_string()`

### Data Export

- [ ] Export to JSON: `from Tools.core.output_formatters import format_json`
- [ ] Export to glTF for 3D viewers

**Verification**: Exported OBJ opens in Blender/MeshLab

---

## Phase 8: Event System (Optional)

If using reactive UI:

- [ ] Import `from Tools.gui.events import EventBus, Events`
- [ ] Subscribe: `EventBus.subscribe(Events.FILE_LOADED, handler)`
- [ ] Publish: `EventBus.publish(Events.CHUNK_SELECTED, chunk)`

**Verification**: UI panels react to selection changes

---

## Final Verification

- [ ] All 276 backend tests still pass
- [ ] File operations work (IFF, FAR, DBPF)
- [ ] Save editing persists correctly
- [ ] Action validation catches invalid operations
- [ ] Pipeline modes work correctly
- [ ] Error messages display clearly
- [ ] No console errors in normal operation

---

## Quick Reference Links

| Document                                               | Purpose                          |
| ------------------------------------------------------ | -------------------------------- |
| [UI_API_REFERENCE.md](UI_API_REFERENCE.md)             | Code examples for all operations |
| [MODULE_INVENTORY.md](MODULE_INVENTORY.md)             | All importable modules           |
| [ACTION_MAP.md](../ACTION_MAP.md)                      | Action → module mapping          |
| [ACTION_SURFACE.md](../ACTION_SURFACE.md)              | Complete action reference        |
| [UI_DEVELOPER_GUIDE.md](UI_DEVELOPER_GUIDE.md)         | GUI architecture guide           |
| [headless_examples.py](../../dev/headless_examples.py) | Runnable demonstrations          |

---

_Last updated: v1.0.3 (2026-02-04)_
