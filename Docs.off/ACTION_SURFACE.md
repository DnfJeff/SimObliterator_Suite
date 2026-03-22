# SimObliterator Action Surface

**Complete registry of all 161 canonical actions**  
**Version 1.0.3 | Generated from action_registry.py**

---

## Overview

Every operation in SimObliterator is a registered action. Unregistered operations are rejected at runtime.

**Key Properties:**

- **Mutability**: READ | PREVIEW | WRITE
- **Scope**: FILE | OBJECT | GLOBAL | SAVE | SYSTEM
- **Risk**: LOW | MEDIUM | HIGH
- **Pipeline**: Whether MUTATE mode required
- **Confirmation**: Whether user must confirm

---

## 1. FILE_CONTAINER (16 actions)

Core file loading and container operations.

| Action            | Mutability | Scope  | Risk   | Pipeline | Confirm |
| ----------------- | ---------- | ------ | ------ | -------- | ------- |
| LoadSave          | READ       | save   | LOW    | No       | No      |
| WriteSave         | WRITE      | save   | HIGH   | Yes      | Yes     |
| BackupSave        | WRITE      | system | LOW    | No       | No      |
| RestoreSave       | WRITE      | save   | HIGH   | Yes      | Yes     |
| LoadIFF           | READ       | file   | LOW    | No       | No      |
| LoadFAR           | READ       | file   | LOW    | No       | No      |
| WriteIFF          | WRITE      | file   | HIGH   | Yes      | Yes     |
| WriteFAR          | WRITE      | file   | HIGH   | Yes      | Yes     |
| MergeIFF          | WRITE      | file   | HIGH   | Yes      | Yes     |
| SplitIFF          | WRITE      | file   | MEDIUM | Yes      | Yes     |
| ReplaceChunk      | WRITE      | object | HIGH   | Yes      | Yes     |
| DeleteChunk       | WRITE      | object | HIGH   | Yes      | Yes     |
| AddChunk          | WRITE      | object | MEDIUM | Yes      | Yes     |
| ReindexContainer  | WRITE      | file   | MEDIUM | Yes      | No      |
| NormalizeHeaders  | WRITE      | file   | MEDIUM | Yes      | No      |
| ValidateContainer | READ       | file   | LOW    | No       | No      |

---

## 2. SAVE_STATE (16 actions)

Save file mutation operations.

| Action                  | Mutability | Scope | Risk   | Pipeline | Confirm |
| ----------------------- | ---------- | ----- | ------ | -------- | ------- |
| AddMoney                | WRITE      | save  | MEDIUM | Yes      | Yes     |
| RemoveMoney             | WRITE      | save  | MEDIUM | Yes      | Yes     |
| SetMoney                | WRITE      | save  | MEDIUM | Yes      | Yes     |
| AddSim                  | WRITE      | save  | HIGH   | Yes      | Yes     |
| RemoveSim               | WRITE      | save  | HIGH   | Yes      | Yes     |
| ModifySimAttributes     | WRITE      | save  | HIGH   | Yes      | Yes     |
| ModifyHousehold         | WRITE      | save  | HIGH   | Yes      | Yes     |
| ModifyRelationships     | WRITE      | save  | HIGH   | Yes      | Yes     |
| ModifyInventory         | WRITE      | save  | MEDIUM | Yes      | Yes     |
| ModifyCareer            | WRITE      | save  | MEDIUM | Yes      | Yes     |
| ModifyMotives           | WRITE      | save  | MEDIUM | Yes      | Yes     |
| ModifyAspirations       | WRITE      | save  | MEDIUM | Yes      | Yes     |
| ModifyMemories          | WRITE      | save  | MEDIUM | Yes      | Yes     |
| ModifyTime              | WRITE      | save  | MEDIUM | Yes      | Yes     |
| ModifyLotState          | WRITE      | save  | HIGH   | Yes      | Yes     |
| ModifyNeighborhoodState | WRITE      | save  | HIGH   | Yes      | Yes     |

**Checks Applied:**

- `is_safe_to_edit()`
- BHAV dependencies
- Cross-Sim consistency
- Save version

---

## 3. BHAV (23 actions)

Behavior script operations.

| Action               | Mutability | Scope  | Risk | Pipeline | Confirm |
| -------------------- | ---------- | ------ | ---- | -------- | ------- |
| LoadBHAV             | READ       | object | LOW  | No       | No      |
| DisassembleBHAV      | READ       | object | LOW  | No       | No      |
| EditBHAV             | WRITE      | object | HIGH | Yes      | Yes     |
| ReplaceBHAV          | WRITE      | object | HIGH | Yes      | Yes     |
| InjectBHAV           | WRITE      | object | HIGH | Yes      | Yes     |
| RemoveBHAV           | WRITE      | object | HIGH | Yes      | Yes     |
| PatchGlobalBHAV      | WRITE      | global | HIGH | Yes      | Yes     |
| PatchSemiGlobalBHAV  | WRITE      | object | HIGH | Yes      | Yes     |
| PatchObjectBHAV      | WRITE      | object | HIGH | Yes      | Yes     |
| RewireBHAVCalls      | WRITE      | object | HIGH | Yes      | Yes     |
| RemapBHAVIDs         | WRITE      | object | HIGH | Yes      | Yes     |
| ValidateBHAVGraph    | READ       | object | LOW  | No       | No      |
| DetectUnknownOpcodes | READ       | object | LOW  | No       | No      |
| ResolveSemanticNames | READ       | object | LOW  | No       | No      |
| CreateInstruction    | PREVIEW    | object | LOW  | No       | No      |
| BuildOperand         | PREVIEW    | object | LOW  | No       | No      |
| CreateBHAV           | WRITE      | object | HIGH | Yes      | Yes     |
| InsertInstruction    | WRITE      | object | HIGH | Yes      | Yes     |
| DeleteInstruction    | WRITE      | object | HIGH | Yes      | Yes     |
| MoveInstruction      | WRITE      | object | HIGH | Yes      | Yes     |
| CopyInstructions     | READ       | object | LOW  | No       | No      |
| PasteInstructions    | WRITE      | object | HIGH | Yes      | Yes     |
| RewirePointers       | WRITE      | object | HIGH | Yes      | Yes     |

**Checks Applied:**

- Call graph validity
- Opcode legality
- Scope rules
- Cycle detection
- Pointer validity
- BHAV ID range
- Operand validation

---

## 4. VISUALIZATION (9 actions)

All read-only visualization operations.

| Action            | Mutability | Scope  | Risk | Pipeline | Confirm |
| ----------------- | ---------- | ------ | ---- | -------- | ------- |
| LoadAssetTo2D     | READ       | object | LOW  | No       | No      |
| LoadAssetTo3D     | READ       | object | LOW  | No       | No      |
| DecodeSPR2        | READ       | object | LOW  | No       | No      |
| DecodeDrawGroup   | READ       | object | LOW  | No       | No      |
| DecodeMesh        | READ       | object | LOW  | No       | No      |
| DecodeAnimation   | READ       | object | LOW  | No       | No      |
| PreviewRotations  | READ       | object | LOW  | No       | No      |
| PreviewZoomLevels | READ       | object | LOW  | No       | No      |
| PreviewFrames     | READ       | object | LOW  | No       | No      |

---

## 5. EXPORT (9 actions)

Export to external formats.

| Action               | Mutability | Scope  | Risk   | Pipeline | Confirm |
| -------------------- | ---------- | ------ | ------ | -------- | ------- |
| ExportAssetToModern  | READ       | object | LOW    | No       | No      |
| ExportAssetToLegacy  | READ       | object | MEDIUM | No       | Yes     |
| ExportSpritePNGs     | READ       | object | LOW    | No       | No      |
| ExportSpriteSheet    | READ       | object | LOW    | No       | No      |
| ExportMesh           | READ       | object | LOW    | No       | No      |
| ExportBehaviorDocs   | READ       | object | LOW    | No       | No      |
| ExportGraphs         | READ       | system | LOW    | No       | No      |
| ExportSaveSnapshot   | READ       | save   | LOW    | No       | No      |
| ExportUnknownsReport | READ       | system | LOW    | No       | No      |

**Checks Applied:**

- Fidelity loss warnings
- Metadata completeness
- Determinism

---

## 6. IMPORT (9 actions)

Import from external sources.

| Action                | Mutability | Scope  | Risk   | Pipeline | Confirm |
| --------------------- | ---------- | ------ | ------ | -------- | ------- |
| ImportAssetFromModern | WRITE      | object | HIGH   | Yes      | Yes     |
| ImportAssetFromLegacy | WRITE      | object | HIGH   | Yes      | Yes     |
| ImportSpritePNG       | WRITE      | object | MEDIUM | Yes      | Yes     |
| ImportSpriteSheet     | WRITE      | object | MEDIUM | Yes      | Yes     |
| ImportMesh            | WRITE      | object | MEDIUM | Yes      | Yes     |
| ImportBehavior        | WRITE      | system | HIGH   | Yes      | Yes     |
| ImportOpcodeDefs      | WRITE      | system | MEDIUM | Yes      | Yes     |
| ImportUnknownsDB      | WRITE      | system | LOW    | Yes      | No      |
| ImportSavePatch       | WRITE      | system | HIGH   | Yes      | Yes     |

**Checks Applied:**

- Schema validation
- ID collision
- Expansion compatibility
- Dry-run diff

---

## 7. ANALYSIS (20 actions)

Read-only analysis operations.

| Action               | Mutability | Scope  | Risk | Pipeline | Confirm |
| -------------------- | ---------- | ------ | ---- | -------- | ------- |
| BuildCallGraph       | READ       | object | LOW  | No       | No      |
| BuildResourceGraph   | READ       | file   | LOW  | No       | No      |
| BuildDependencyGraph | READ       | file   | LOW  | No       | No      |
| DetectCycles         | READ       | object | LOW  | No       | No      |
| DetectDeadCode       | READ       | object | LOW  | No       | No      |
| DetectUnusedAssets   | READ       | file   | LOW  | No       | No      |
| CompareExpansions    | READ       | system | LOW  | No       | No      |
| DiffObjects          | READ       | object | LOW  | No       | No      |
| DiffBHAVs            | READ       | object | LOW  | No       | No      |
| DiffGlobals          | READ       | global | LOW  | No       | No      |
| AnalyzeLot           | READ       | object | LOW  | No       | No      |
| GetTerrainType       | READ       | object | LOW  | No       | No      |
| ListAmbienceObjects  | READ       | object | LOW  | No       | No      |
| ScanLotFolder        | READ       | file   | LOW  | No       | No      |
| FindAmbienceByGUID   | READ       | object | LOW  | No       | No      |
| ParseSIMI            | READ       | object | LOW  | No       | No      |
| ParseHOUS            | READ       | object | LOW  | No       | No      |
| ListLotARRYChunks    | READ       | object | LOW  | No       | No      |
| ExtractLotObjects    | READ       | object | LOW  | No       | No      |
| CompareLots          | READ       | file   | LOW  | No       | No      |

---

## 8. SEARCH (9 actions)

Search and cross-reference operations.

| Action                  | Mutability | Scope  | Risk | Pipeline | Confirm |
| ----------------------- | ---------- | ------ | ---- | -------- | ------- |
| SearchByName            | READ       | system | LOW  | No       | No      |
| SearchByID              | READ       | system | LOW  | No       | No      |
| SearchByOpcode          | READ       | system | LOW  | No       | No      |
| SearchByBehaviorPurpose | READ       | system | LOW  | No       | No      |
| SearchByLifecyclePhase  | READ       | system | LOW  | No       | No      |
| SearchBySafetyRisk      | READ       | system | LOW  | No       | No      |
| SearchByExpansion       | READ       | system | LOW  | No       | No      |
| SearchByUnknownUsage    | READ       | system | LOW  | No       | No      |
| CrossReferenceSearch    | READ       | system | LOW  | No       | No      |

---

## 9. SYSTEM (10 actions)

System-level operations.

| Action              | Mutability | Scope  | Risk   | Pipeline | Confirm |
| ------------------- | ---------- | ------ | ------ | -------- | ------- |
| ScanDirectory       | READ       | system | LOW    | No       | No      |
| FullForensicScan    | READ       | system | LOW    | No       | No      |
| UpdateUnknownsDB    | WRITE      | system | LOW    | Yes      | No      |
| RebuildIndexes      | WRITE      | system | LOW    | No       | No      |
| ClearCaches         | WRITE      | system | LOW    | No       | No      |
| ValidateEnvironment | READ       | system | LOW    | No       | No      |
| CheckDependencies   | READ       | system | LOW    | No       | No      |
| MigrateData         | WRITE      | system | MEDIUM | Yes      | Yes     |
| LoadWorkspace       | READ       | system | LOW    | No       | No      |
| SaveWorkspace       | WRITE      | system | LOW    | No       | No      |

---

## 10. UI (8 actions)

User interface operations (your responsibility).

| Action          | Mutability | Scope  | Risk | Pipeline | Confirm |
| --------------- | ---------- | ------ | ---- | -------- | ------- |
| SelectEntity    | READ       | system | LOW  | No       | No      |
| ChangeScope     | READ       | system | LOW  | No       | No      |
| ToggleViewMode  | READ       | system | LOW  | No       | No      |
| OpenInspector   | READ       | system | LOW  | No       | No      |
| ApplyFilter     | READ       | system | LOW  | No       | No      |
| TriggerPreview  | PREVIEW    | system | LOW  | No       | No      |
| ConfirmMutation | WRITE      | system | HIGH | Yes      | Yes     |
| CancelMutation  | READ       | system | LOW  | No       | No      |

---

## 11. TTAB (8 actions)

Interaction table operations.

| Action                  | Mutability | Scope  | Risk   | Pipeline | Confirm |
| ----------------------- | ---------- | ------ | ------ | -------- | ------- |
| LoadTTAB                | READ       | object | LOW    | No       | No      |
| ParseTTABFull           | READ       | object | LOW    | No       | No      |
| EditTTABAutonomy        | WRITE      | object | MEDIUM | Yes      | Yes     |
| EditTTABMotiveEffect    | WRITE      | object | MEDIUM | Yes      | Yes     |
| AddTTABInteraction      | WRITE      | object | HIGH   | Yes      | Yes     |
| RemoveTTABInteraction   | WRITE      | object | HIGH   | Yes      | Yes     |
| BuildMultiObjectContext | READ       | file   | LOW    | No       | No      |
| SwitchObjectContext     | READ       | file   | LOW    | No       | No      |

---

## 12. SLOT (8 actions)

Routing slot operations.

| Action             | Mutability | Scope  | Risk   | Pipeline | Confirm |
| ------------------ | ---------- | ------ | ------ | -------- | ------- |
| LoadSLOT           | READ       | object | LOW    | No       | No      |
| ParseSLOT          | READ       | object | LOW    | No       | No      |
| AddSLOT            | WRITE      | object | MEDIUM | Yes      | Yes     |
| EditSLOT           | WRITE      | object | MEDIUM | Yes      | Yes     |
| RemoveSLOT         | WRITE      | object | MEDIUM | Yes      | Yes     |
| DuplicateSLOT      | WRITE      | object | LOW    | Yes      | No      |
| CreateChairSlots   | WRITE      | object | LOW    | Yes      | No      |
| CreateCounterSlots | WRITE      | object | LOW    | Yes      | No      |

---

## 13. LOCALIZATION (8 actions)

String and localization operations.

| Action            | Mutability | Scope  | Risk   | Pipeline | Confirm |
| ----------------- | ---------- | ------ | ------ | -------- | ------- |
| ParseSTR          | READ       | object | LOW    | No       | No      |
| ListLanguageSlots | READ       | object | LOW    | No       | No      |
| AuditLocalization | READ       | file   | LOW    | No       | No      |
| CopyLanguageSlot  | WRITE      | object | MEDIUM | Yes      | Yes     |
| FillMissingSlots  | WRITE      | object | MEDIUM | Yes      | Yes     |
| FindSTRReferences | READ       | file   | LOW    | No       | No      |
| FindOrphanSTR     | READ       | file   | LOW    | No       | No      |
| EditSTREntry      | WRITE      | object | MEDIUM | Yes      | Yes     |

---

## Statistics Summary

| Metric                   | Count |
| ------------------------ | ----- |
| **Total Actions**        | 161   |
| **Read Actions**         | 82    |
| **Write Actions**        | 79    |
| **High Risk**            | 37    |
| **Require Pipeline**     | 55    |
| **Require Confirmation** | 51    |

---

## Adding New Actions

**HARD RULE**: New features = new actions registered here.

To add a new action:

1. Define in `action_registry.py` `_register_canonical_actions()`
2. Add to appropriate category
3. Set correct mutability, scope, risk
4. Add checks list
5. Update this document
6. Add test coverage

---

## Related Documentation

- [ACTION_MAP.md](ACTION_MAP.md) - Maps actions to modules with test coverage
- [UI_API_REFERENCE.md](guides/UI_API_REFERENCE.md) - Headless API quickstart
- [MODULE_INVENTORY.md](guides/MODULE_INVENTORY.md) - All importable modules

---

_Last updated: v1.0.3 (2026-02-04)_
