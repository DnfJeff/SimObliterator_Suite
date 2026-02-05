# SimObliterator UI Developer Guide

Reference for completing the GUI implementation using Dear PyGui.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            main_app.py                                  │
│         MainApp: viewport, menu bar, docking, panel orchestration       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   AppState      │      │    EventBus     │      │  ActionRegistry │
│   (state.py)    │◄────►│   (events.py)   │◄────►│  (core)         │
│                 │      │                 │      │                 │
│ - current_file  │      │ - subscribe()   │      │ - validate()    │
│ - current_iff   │      │ - publish()     │      │ - audit()       │
│ - current_chunk │      │ - Events.*      │      │ - get_action()  │
└─────────────────┘      └─────────────────┘      └─────────────────┘
         │                          │
         └──────────────────────────┼──────────────────────────┐
                                    ▼                          │
┌─────────────────────────────────────────────────────────────────────────┐
│                            GUI Panels                                   │
│  file_loader │ iff_inspector │ chunk_inspector │ bhav_editor │ ...      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Files

| File                                | Purpose                                |
| ----------------------------------- | -------------------------------------- |
| `src/main_app.py`                   | Entry point, menu bar, panel layout    |
| `src/Tools/gui/state.py`            | Global AppState singleton              |
| `src/Tools/gui/events.py`           | EventBus pub/sub + Events constants    |
| `src/Tools/gui/theme.py`            | Dear PyGui theme (colors, fonts)       |
| `src/Tools/gui/panels/*.py`         | Individual panel implementations       |
| `src/Tools/core/action_registry.py` | 110 canonical actions with safety tags |

---

## Event System

### Publishing Events

```python
from Tools.gui.events import EventBus, Events

# After loading a file
EventBus.publish(Events.FILE_LOADED, file_path)

# After selecting a chunk
EventBus.publish(Events.CHUNK_SELECTED, chunk)

# Status bar update
EventBus.publish(Events.STATUS_UPDATE, "Loaded 42 chunks")
```

### Subscribing to Events

```python
def on_chunk_selected(chunk):
    # Update your panel with the new chunk
    self.display_chunk(chunk)

EventBus.subscribe(Events.CHUNK_SELECTED, on_chunk_selected)
```

### Event Constants

| Event                    | Payload       | When                        |
| ------------------------ | ------------- | --------------------------- |
| `FILE_LOADED`            | Path          | IFF/FAR/DBPF opened         |
| `FILE_CLEARED`           | None          | File closed                 |
| `FAR_LOADED`             | FARArchive    | FAR archive opened          |
| `IFF_LOADED`             | IFFFile       | IFF extracted or loaded     |
| `CHUNK_SELECTED`         | Chunk         | User clicks chunk in tree   |
| `BHAV_SELECTED`          | BHAVChunk     | BHAV selected for editing   |
| `CHARACTER_SELECTED`     | SimEntity     | Sim selected in save editor |
| `GRAPH_NODE_SELECTED`    | (type, id)    | Node clicked in call graph  |
| `SEARCH_RESULT_SELECTED` | (file, chunk) | Search result clicked       |
| `SAVE_MODIFIED`          | SaveFile      | Save file edited            |
| `ANALYSIS_STARTED`       | str           | Long operation begins       |
| `ANALYSIS_COMPLETE`      | result        | Long operation ends         |
| `STATUS_UPDATE`          | str           | Status bar message          |

---

## State Management

### AppState Fields

```python
from Tools.gui.state import AppState

state = AppState()

# Current file context
state.current_file      # Path to loaded file
state.current_file_type # "IFF", "FAR", "SAVE"
state.current_far       # FARArchive object
state.current_iff       # IFFFile object
state.current_chunk     # Selected chunk
state.current_bhav      # Selected BHAV (if any)

# Resource selection (for graph navigation)
state.current_resource_id   # Chunk ID
state.current_resource_type # "BHAV", "OBJD", etc.

# Logging
state.log("Loaded file", "INFO")
state.log("Parse error", "ERROR")
```

### State Update Pattern

```python
# Set file and clear downstream state
state.set_file(path, "IFF")

# Set IFF (clears chunk selection)
state.set_iff(iff_file, "object.iff")

# Set chunk (also sets current_bhav if applicable)
state.set_chunk(chunk)
```

---

## Action Registry Integration

All write operations must go through the action registry for safety.

### Validating Actions

```python
from Tools.core.action_registry import ActionRegistry

registry = ActionRegistry.get()

# Check if action is allowed
valid, reason = registry.validate_and_log("WriteSave", {
    'pipeline_mode': 'MUTATE',
    'user_confirmed': True,
    'safety_checked': True,
})

if not valid:
    show_error(reason)
    return
```

### Action Categories

| Category       | Examples                                    |
| -------------- | ------------------------------------------- |
| FILE_CONTAINER | LoadIFF, WriteIFF, LoadFAR, MergeIFF        |
| SAVE_STATE     | AddMoney, ModifySimAttributes, ModifyCareer |
| BHAV           | DisassembleBHAV, EditBHAV, InjectBHAV       |
| VISUALIZATION  | RenderCallGraph, RenderAnimationFrames      |
| EXPORT         | ExportSprite, ExportMesh, ExportSTR         |
| IMPORT         | ImportSprite, ImportMesh, ImportBHAV        |
| ANALYSIS       | AnalyzeBHAV, DetectPatterns, CompareObjects |
| SLOT           | ParseSLOT, EditSLOT, ExportSLOTXML          |
| TTAB           | ParseTTAB, EditTTAB, AnalyzeAutonomy        |
| LOCALIZATION   | ParseSTR, ScanReferences, AuditLocalization |

---

## Panel Development

### Panel Template

```python
import dearpygui.dearpygui as dpg
from Tools.gui.events import EventBus, Events

class MyPanel:
    def __init__(self, tag: str = "my_panel"):
        self.tag = tag
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        EventBus.subscribe(Events.CHUNK_SELECTED, self._on_chunk_selected)

    def _on_chunk_selected(self, chunk):
        # React to selection
        self.refresh(chunk)

    def create(self):
        with dpg.window(label="My Panel", tag=self.tag):
            dpg.add_text("Content here")
            dpg.add_button(label="Action", callback=self._on_action)

    def _on_action(self, sender, app_data):
        # Do something
        EventBus.publish(Events.STATUS_UPDATE, "Action completed")

    def refresh(self, data):
        # Update panel contents
        pass
```

### Panel Checklist

- [ ] Subscribe to relevant events in `__init__`
- [ ] Unsubscribe in destructor if panel can be closed
- [ ] Use `AppState` for reading current context
- [ ] Publish events when user makes selections
- [ ] Validate write actions through `ActionRegistry`
- [ ] Update status bar via `Events.STATUS_UPDATE`

---

## Incomplete Features (TODOs)

These are stub implementations waiting for GUI wiring:

### File Operations

| Location                   | TODO                                      |
| -------------------------- | ----------------------------------------- |
| `file_loader.py:215`       | Implement directory browser               |
| `file_loader.py:235`       | Implement search                          |
| `iff_inspector.py:69`      | Handle FAR archive loading                |
| `save_editor_panel.py:264` | Use file dialog instead of hardcoded path |

### Object Editing

| Location                  | TODO                            |
| ------------------------- | ------------------------------- |
| `object_inspector.py:458` | Edit price for OBJD             |
| `object_inspector.py:461` | Edit name for OBJD              |
| `object_inspector.py:472` | Clone object (OBJD duplication) |
| `chunk_inspector.py:316`  | Open string editor for STR#     |
| `chunk_inspector.py:320`  | Open OBJD editor                |
| `chunk_inspector.py:324`  | Export raw bytes                |

### Safety System

| Location               | TODO                         |
| ---------------------- | ---------------------------- |
| `scope_tracker.py:242` | Integrate with GUID database |
| `edit_mode.py:224-231` | Trigger resource duplication |

### Export Features

| Location                        | TODO                            |
| ------------------------------- | ------------------------------- |
| `character_viewer_panel.py:365` | GLTF export for characters      |
| `character_viewer_panel.py:372` | PNG export for character render |

### Reference Panels

| Location            | TODO                      |
| ------------------- | ------------------------- |
| `iff_viewer.py:898` | Opcode reference popup    |
| `iff_viewer.py:902` | Behavior dictionary popup |

---

## Core Parsers Available

All parsing is done - just needs UI wiring.

| Resource | Parser                        | Editor                  |
| -------- | ----------------------------- | ----------------------- |
| IFF      | `formats/iff/iff_file.py`     | -                       |
| FAR1/3   | `formats/far/far1.py`         | -                       |
| DBPF     | `formats/dbpf/dbpf.py`        | -                       |
| BHAV     | `core/bhav_disassembler.py`   | `core/bhav_patching.py` |
| OBJD     | `core/chunk_parsers.py`       | -                       |
| TTAB     | `core/chunk_parsers.py`       | `core/ttab_editor.py`   |
| SLOT     | `core/slot_editor.py`         | `core/slot_editor.py`   |
| STR#     | `core/str_parser.py`          | -                       |
| SPR2     | `core/chunk_parsers.py`       | `core/sprite_export.py` |
| Saves    | `save_editor/save_manager.py` | `save_editor/*.py`      |

---

## Testing Your Changes

```bash
cd dev

# Run all tests to verify nothing broke
python real_game_tests.py

# Run quick subset during development
python real_game_tests.py --quick

# Test specific category
python real_game_tests.py --category formats
```

---

## Style Guidelines

1. **Panel names**: Use `_panel` suffix for window tags
2. **Callbacks**: Use `_on_` prefix for event handlers
3. **State**: Never store state in panels - use `AppState`
4. **Events**: Always publish when user makes a selection
5. **Errors**: Show user-friendly messages, log technical details
6. **Undo**: All write operations should support undo via `MutationPipeline`

---

## Quick Reference

### Dear PyGui Patterns

```python
# Get value from input
value = dpg.get_value("input_tag")

# Set value
dpg.set_value("input_tag", new_value)

# Show/hide
dpg.show_item("panel_tag")
dpg.hide_item("panel_tag")

# Delete all children (refresh list)
dpg.delete_item("container_tag", children_only=True)

# File dialog
with dpg.file_dialog(callback=self._on_file_selected):
    dpg.add_file_extension(".iff", color=(0, 255, 0))
    dpg.add_file_extension(".far", color=(0, 200, 255))
```

### Common Imports

```python
import dearpygui.dearpygui as dpg
from pathlib import Path

from Tools.gui.events import EventBus, Events
from Tools.gui.state import AppState
from Tools.core.action_registry import ActionRegistry
from Tools.core.mutation_pipeline import MutationPipeline, MutationMode
```
