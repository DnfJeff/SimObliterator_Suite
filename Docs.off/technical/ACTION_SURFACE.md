# SimObliterator – Action Surface (Canonical)

> **HARD RULE**: If an action is not in this list, it does not exist.  
> New features = new actions = new safety definitions.

---

## ACTION CLASSIFICATION TAGS

Every action MUST declare:

| Tag                            | Values                                               | Description                    |
| ------------------------------ | ---------------------------------------------------- | ------------------------------ |
| **Mutability**                 | `Read` \| `Preview` \| `Write`                       | Does it change state?          |
| **Scope**                      | `File` \| `Object` \| `Global` \| `Save` \| `System` | What does it affect?           |
| **Risk**                       | `Low` \| `Medium` \| `High`                          | Blast radius if wrong          |
| **Requires MutationPipeline**  | `Yes` \| `No`                                        | Must go through write barrier? |
| **Requires User Confirmation** | `Yes` \| `No`                                        | Explicit approval needed?      |
| **Audited**                    | `Yes` \| `No`                                        | Logged to forensic trace?      |

---

## 1. FILE / CONTAINER ACTIONS

> Low-level I/O, high blast radius.

| Action              | Mutability | Scope  | Risk   | Pipeline | Confirm | Audited |
| ------------------- | ---------- | ------ | ------ | -------- | ------- | ------- |
| `LoadSave`          | Read       | Save   | Low    | No       | No      | Yes     |
| `WriteSave`         | Write      | Save   | High   | Yes      | Yes     | Yes     |
| `BackupSave`        | Write      | System | Low    | No       | No      | Yes     |
| `RestoreSave`       | Write      | Save   | High   | Yes      | Yes     | Yes     |
| `LoadIFF`           | Read       | File   | Low    | No       | No      | Yes     |
| `LoadFAR`           | Read       | File   | Low    | No       | No      | Yes     |
| `WriteIFF`          | Write      | File   | High   | Yes      | Yes     | Yes     |
| `WriteFAR`          | Write      | File   | High   | Yes      | Yes     | Yes     |
| `MergeIFF`          | Write      | File   | High   | Yes      | Yes     | Yes     |
| `SplitIFF`          | Write      | File   | Medium | Yes      | Yes     | Yes     |
| `ReplaceChunk`      | Write      | Object | High   | Yes      | Yes     | Yes     |
| `DeleteChunk`       | Write      | Object | High   | Yes      | Yes     | Yes     |
| `AddChunk`          | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `ReindexContainer`  | Write      | File   | Medium | Yes      | No      | Yes     |
| `NormalizeHeaders`  | Write      | File   | Medium | Yes      | No      | Yes     |
| `ValidateContainer` | Read       | File   | Low    | No       | No      | Yes     |

### Checks Required:

- Format version compatibility
- Expansion scope
- Chunk dependency integrity
- Write mode (`INSPECT` / `PREVIEW` / `MUTATE`)

---

## 2. SAVE-STATE MUTATIONS

> Corruption-prone, must ALWAYS go through MutationPipeline.

| Action                    | Mutability | Scope | Risk   | Pipeline | Confirm | Audited |
| ------------------------- | ---------- | ----- | ------ | -------- | ------- | ------- |
| `AddMoney`                | Write      | Save  | Medium | Yes      | Yes     | Yes     |
| `RemoveMoney`             | Write      | Save  | Medium | Yes      | Yes     | Yes     |
| `SetMoney`                | Write      | Save  | Medium | Yes      | Yes     | Yes     |
| `AddSim`                  | Write      | Save  | High   | Yes      | Yes     | Yes     |
| `RemoveSim`               | Write      | Save  | High   | Yes      | Yes     | Yes     |
| `ModifySimAttributes`     | Write      | Save  | High   | Yes      | Yes     | Yes     |
| `ModifyHousehold`         | Write      | Save  | High   | Yes      | Yes     | Yes     |
| `ModifyRelationships`     | Write      | Save  | High   | Yes      | Yes     | Yes     |
| `ModifyInventory`         | Write      | Save  | Medium | Yes      | Yes     | Yes     |
| `ModifyCareer`            | Write      | Save  | Medium | Yes      | Yes     | Yes     |
| `ModifyMotives`           | Write      | Save  | Medium | Yes      | Yes     | Yes     |
| `ModifyAspirations`       | Write      | Save  | Medium | Yes      | Yes     | Yes     |
| `ModifyMemories`          | Write      | Save  | Medium | Yes      | Yes     | Yes     |
| `ModifyTime`              | Write      | Save  | Medium | Yes      | Yes     | Yes     |
| `ModifyLotState`          | Write      | Save  | High   | Yes      | Yes     | Yes     |
| `ModifyNeighborhoodState` | Write      | Save  | High   | Yes      | Yes     | Yes     |

### Checks Required:

- `is_safe_to_edit()` (mandatory)
- Active BHAV dependencies
- Cross-Sim consistency
- Save version constraints

---

## 3. BEHAVIOR / BHAV ACTIONS

> High semantic impact.

| Action                 | Mutability | Scope  | Risk | Pipeline | Confirm | Audited |
| ---------------------- | ---------- | ------ | ---- | -------- | ------- | ------- |
| `LoadBHAV`             | Read       | Object | Low  | No       | No      | Yes     |
| `DisassembleBHAV`      | Read       | Object | Low  | No       | No      | No      |
| `EditBHAV`             | Write      | Object | High | Yes      | Yes     | Yes     |
| `ReplaceBHAV`          | Write      | Object | High | Yes      | Yes     | Yes     |
| `InjectBHAV`           | Write      | Object | High | Yes      | Yes     | Yes     |
| `RemoveBHAV`           | Write      | Object | High | Yes      | Yes     | Yes     |
| `PatchGlobalBHAV`      | Write      | Global | High | Yes      | Yes     | Yes     |
| `PatchSemiGlobalBHAV`  | Write      | Global | High | Yes      | Yes     | Yes     |
| `PatchObjectBHAV`      | Write      | Object | High | Yes      | Yes     | Yes     |
| `RewireBHAVCalls`      | Write      | Object | High | Yes      | Yes     | Yes     |
| `RemapBHAVIDs`         | Write      | File   | High | Yes      | Yes     | Yes     |
| `ValidateBHAVGraph`    | Read       | Object | Low  | No       | No      | Yes     |
| `DetectUnknownOpcodes` | Read       | Object | Low  | No       | No      | Yes     |
| `ResolveSemanticNames` | Read       | Global | Low  | No       | No      | No      |

### Checks Required:

- Call graph validity
- Opcode legality per expansion
- Global/Semi/Object scope rules
- Cycle detection
- Unknown opcode logging

---

## 4. ASSET → VISUALIZATION ACTIONS

> Read-only unless explicitly exporting.

| Action              | Mutability | Scope  | Risk | Pipeline | Confirm | Audited |
| ------------------- | ---------- | ------ | ---- | -------- | ------- | ------- |
| `LoadAssetTo2D`     | Read       | Object | Low  | No       | No      | No      |
| `LoadAssetTo3D`     | Read       | Object | Low  | No       | No      | No      |
| `DecodeSPR2`        | Read       | Object | Low  | No       | No      | No      |
| `DecodeDrawGroup`   | Read       | Object | Low  | No       | No      | No      |
| `DecodeMesh`        | Read       | Object | Low  | No       | No      | No      |
| `DecodeAnimation`   | Read       | Object | Low  | No       | No      | No      |
| `PreviewRotations`  | Read       | Object | Low  | No       | No      | No      |
| `PreviewZoomLevels` | Read       | Object | Low  | No       | No      | No      |
| `PreviewFrames`     | Read       | Object | Low  | No       | No      | No      |

### Checks Required:

- Decoder availability
- Fallback rendering path
- Read-only enforcement

---

## 5. EXPORT ACTIONS

> Cross-ecosystem boundary.

| Action                 | Mutability | Scope  | Risk   | Pipeline | Confirm | Audited |
| ---------------------- | ---------- | ------ | ------ | -------- | ------- | ------- |
| `ExportAssetToModern`  | Read       | Object | Low    | No       | No      | Yes     |
| `ExportAssetToLegacy`  | Read       | Object | Medium | No       | Yes     | Yes     |
| `ExportSpritePNGs`     | Read       | Object | Low    | No       | No      | Yes     |
| `ExportSpriteSheet`    | Read       | Object | Low    | No       | No      | Yes     |
| `ExportMesh`           | Read       | Object | Low    | No       | No      | Yes     |
| `ExportBehaviorDocs`   | Read       | Object | Low    | No       | No      | Yes     |
| `ExportGraphs`         | Read       | System | Low    | No       | No      | Yes     |
| `ExportSaveSnapshot`   | Read       | Save   | Low    | No       | No      | Yes     |
| `ExportUnknownsReport` | Read       | System | Low    | No       | No      | Yes     |

### Checks Required:

- Format fidelity loss warnings
- Metadata completeness
- Licensing / attribution notes
- Determinism (repeatable output)

---

## 6. IMPORT ACTIONS

> **Highest risk surface.**

| Action                  | Mutability | Scope  | Risk   | Pipeline | Confirm | Audited |
| ----------------------- | ---------- | ------ | ------ | -------- | ------- | ------- |
| `ImportAssetFromModern` | Write      | Object | High   | Yes      | Yes     | Yes     |
| `ImportAssetFromLegacy` | Write      | Object | High   | Yes      | Yes     | Yes     |
| `ImportSpritePNG`       | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `ImportSpriteSheet`     | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `ImportMesh`            | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `ImportBehavior`        | Write      | Object | High   | Yes      | Yes     | Yes     |
| `ImportOpcodeDefs`      | Write      | System | Medium | Yes      | Yes     | Yes     |
| `ImportUnknownsDB`      | Write      | System | Low    | Yes      | No      | Yes     |
| `ImportSavePatch`       | Write      | Save   | High   | Yes      | Yes     | Yes     |

### Checks Required:

- Schema validation
- ID collision detection
- Expansion compatibility
- **Dry-run diff required**
- **Explicit user confirmation**

---

## 7. GRAPH / ANALYSIS ACTIONS

> Pure analysis, but can drive decisions.

| Action                 | Mutability | Scope  | Risk | Pipeline | Confirm | Audited |
| ---------------------- | ---------- | ------ | ---- | -------- | ------- | ------- |
| `BuildCallGraph`       | Read       | Object | Low  | No       | No      | No      |
| `BuildResourceGraph`   | Read       | File   | Low  | No       | No      | No      |
| `BuildDependencyGraph` | Read       | File   | Low  | No       | No      | No      |
| `DetectCycles`         | Read       | Object | Low  | No       | No      | Yes     |
| `DetectDeadCode`       | Read       | Object | Low  | No       | No      | Yes     |
| `DetectUnusedAssets`   | Read       | File   | Low  | No       | No      | Yes     |
| `CompareExpansions`    | Read       | System | Low  | No       | No      | No      |
| `DiffObjects`          | Read       | Object | Low  | No       | No      | No      |
| `DiffBHAVs`            | Read       | Object | Low  | No       | No      | No      |
| `DiffGlobals`          | Read       | Global | Low  | No       | No      | No      |

### Checks Required:

- Analysis scope correctness
- Caching validity
- Deterministic graph generation

---

## 8. SEARCH / QUERY ACTIONS

> Semantic surface.

| Action                    | Mutability | Scope  | Risk | Pipeline | Confirm | Audited |
| ------------------------- | ---------- | ------ | ---- | -------- | ------- | ------- |
| `SearchByName`            | Read       | System | Low  | No       | No      | No      |
| `SearchByID`              | Read       | System | Low  | No       | No      | No      |
| `SearchByOpcode`          | Read       | System | Low  | No       | No      | No      |
| `SearchByBehaviorPurpose` | Read       | System | Low  | No       | No      | No      |
| `SearchByLifecyclePhase`  | Read       | System | Low  | No       | No      | No      |
| `SearchBySafetyRisk`      | Read       | System | Low  | No       | No      | No      |
| `SearchByExpansion`       | Read       | System | Low  | No       | No      | No      |
| `SearchByUnknownUsage`    | Read       | System | Low  | No       | No      | No      |
| `CrossReferenceSearch`    | Read       | System | Low  | No       | No      | No      |

### Checks Required:

- Semantic index availability
- Confidence weighting
- Provenance tags

---

## 9. SYSTEM / META ACTIONS

> Suite integrity.

| Action                | Mutability | Scope  | Risk   | Pipeline | Confirm | Audited |
| --------------------- | ---------- | ------ | ------ | -------- | ------- | ------- |
| `ScanDirectory`       | Read       | System | Low    | No       | No      | Yes     |
| `FullForensicScan`    | Read       | System | Low    | No       | No      | Yes     |
| `UpdateUnknownsDB`    | Write      | System | Low    | Yes      | No      | Yes     |
| `RebuildIndexes`      | Write      | System | Low    | No       | No      | Yes     |
| `ClearCaches`         | Write      | System | Low    | No       | No      | Yes     |
| `ValidateEnvironment` | Read       | System | Low    | No       | No      | No      |
| `CheckDependencies`   | Read       | System | Low    | No       | No      | No      |
| `MigrateData`         | Write      | System | Medium | Yes      | Yes     | Yes     |
| `LoadWorkspace`       | Read       | System | Low    | No       | No      | Yes     |
| `SaveWorkspace`       | Write      | System | Low    | No       | No      | Yes     |

### Checks Required:

- Version compatibility
- Backward migration safety
- Partial failure recovery

---

## 10. UI-LEVEL ACTIONS

> Must NOT bypass system rules.

| Action            | Mutability | Scope  | Risk   | Pipeline | Confirm | Audited |
| ----------------- | ---------- | ------ | ------ | -------- | ------- | ------- |
| `SelectEntity`    | Read       | System | Low    | No       | No      | No      |
| `ChangeScope`     | Read       | System | Low    | No       | No      | No      |
| `ToggleViewMode`  | Read       | System | Low    | No       | No      | No      |
| `OpenInspector`   | Read       | System | Low    | No       | No      | No      |
| `ApplyFilter`     | Read       | System | Low    | No       | No      | No      |
| `TriggerPreview`  | Preview    | Object | Low    | No       | No      | No      |
| `ConfirmMutation` | Write      | varies | varies | Yes      | Yes     | Yes     |
| `CancelMutation`  | Read       | System | Low    | No       | No      | Yes     |

### Checks Required:

- Selection validity
- Mode gating (`INSPECT` vs `MUTATE`)
- Undo/rollback availability

---

## 11. TTAB / INTERACTION ACTIONS

> Interaction tables — autonomy, motive effects, multi-object context.

| Action                    | Mutability | Scope  | Risk   | Pipeline | Confirm | Audited |
| ------------------------- | ---------- | ------ | ------ | -------- | ------- | ------- |
| `LoadTTAB`                | Read       | Object | Low    | No       | No      | Yes     |
| `ParseTTABFull`           | Read       | Object | Low    | No       | No      | No      |
| `EditTTABAutonomy`        | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `EditTTABMotiveEffect`    | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `AddTTABInteraction`      | Write      | Object | High   | Yes      | Yes     | Yes     |
| `RemoveTTABInteraction`   | Write      | Object | High   | Yes      | Yes     | Yes     |
| `BuildMultiObjectContext` | Read       | File   | Low    | No       | No      | Yes     |
| `SwitchObjectContext`     | Read       | File   | Low    | No       | No      | No      |

### Checks Required:

- Multi-OBJD awareness (which TTAB belongs to which OBJD)
- Autonomy value range (0-100)
- Motive effect bounds
- TTAB version compatibility (V4-V10)

---

## 12. SLOT / ROUTING ACTIONS

> Routing slots — where Sims stand, sit, interact.

| Action               | Mutability | Scope  | Risk   | Pipeline | Confirm | Audited |
| -------------------- | ---------- | ------ | ------ | -------- | ------- | ------- |
| `LoadSLOT`           | Read       | Object | Low    | No       | No      | Yes     |
| `ParseSLOT`          | Read       | Object | Low    | No       | No      | No      |
| `AddSLOT`            | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `EditSLOT`           | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `RemoveSLOT`         | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `DuplicateSLOT`      | Write      | Object | Low    | Yes      | No      | Yes     |
| `CreateChairSlots`   | Write      | Object | Low    | Yes      | No      | Yes     |
| `CreateCounterSlots` | Write      | Object | Low    | Yes      | No      | Yes     |

### Checks Required:

- Slot position bounds
- Slot type validity
- Facing direction normalization
- Target slot references

---

## 13. BHAV AUTHORING ACTIONS

> Create instructions and BHAVs from scratch.

| Action              | Mutability | Scope  | Risk | Pipeline | Confirm | Audited |
| ------------------- | ---------- | ------ | ---- | -------- | ------- | ------- |
| `CreateInstruction` | Preview    | Object | Low  | No       | No      | No      |
| `BuildOperand`      | Preview    | Object | Low  | No       | No      | No      |
| `CreateBHAV`        | Write      | Object | High | Yes      | Yes     | Yes     |
| `InsertInstruction` | Write      | Object | High | Yes      | Yes     | Yes     |
| `DeleteInstruction` | Write      | Object | High | Yes      | Yes     | Yes     |
| `MoveInstruction`   | Write      | Object | High | Yes      | Yes     | Yes     |
| `CopyInstructions`  | Read       | Object | Low  | No       | No      | No      |
| `PasteInstructions` | Write      | Object | High | Yes      | Yes     | Yes     |
| `RewirePointers`    | Write      | Object | High | Yes      | Yes     | Yes     |

### Checks Required:

- Instruction pointer validity (253=error, 254=true, 255=false)
- BHAV ID range (4096-8191 local, 8192+ semi-global)
- Operand spec validation per opcode
- Auto-rewiring on insert/delete

---

## 14. LOCALIZATION / STRING ACTIONS

> STR# parsing, language slots, localization auditing.

| Action              | Mutability | Scope  | Risk   | Pipeline | Confirm | Audited |
| ------------------- | ---------- | ------ | ------ | -------- | ------- | ------- |
| `ParseSTR`          | Read       | Object | Low    | No       | No      | No      |
| `ListLanguageSlots` | Read       | Object | Low    | No       | No      | No      |
| `AuditLocalization` | Read       | File   | Low    | No       | No      | Yes     |
| `CopyLanguageSlot`  | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `FillMissingSlots`  | Write      | Object | Medium | Yes      | Yes     | Yes     |
| `FindSTRReferences` | Read       | File   | Low    | No       | No      | No      |
| `FindOrphanSTR`     | Read       | File   | Low    | No       | No      | Yes     |
| `EditSTREntry`      | Write      | Object | Medium | Yes      | Yes     | Yes     |

### Checks Required:

- STR# format detection (0xFFFF, 0xFDFF, 0xFEFF, Pascal)
- Language code validation (20 languages)
- Catalog string references
- Orphan chunk detection

---

## ACTION COUNTS BY CATEGORY

| Category         | Total Actions | Write Actions | High Risk |
| ---------------- | ------------- | ------------- | --------- |
| File/Container   | 16            | 12            | 8         |
| Save-State       | 16            | 16            | 6         |
| BHAV             | 14            | 9             | 9         |
| Visualization    | 9             | 0             | 0         |
| Export           | 9             | 0             | 0         |
| Import           | 9             | 9             | 5         |
| Analysis         | 10            | 0             | 0         |
| Search           | 9             | 0             | 0         |
| System           | 10            | 5             | 0         |
| UI               | 8             | 1             | 0         |
| **TTAB**         | **8**         | **4**         | **2**     |
| **SLOT**         | **8**         | **6**         | **0**     |
| **BHAV Auth**    | **9**         | **6**         | **6**     |
| **Localization** | **8**         | **3**         | **0**     |
| **TOTAL**        | **143**       | **71**        | **36**    |

---

## ENFORCEMENT

All code paths MUST:

1. **Declare their action** from this list
2. **Pass classification checks** before execution
3. **Route through MutationPipeline** if `Requires MutationPipeline = Yes`
4. **Log to forensic trace** if `Audited = Yes`
5. **Prompt user** if `Requires User Confirmation = Yes`

**Unregistered actions are rejected at runtime.**

---

---

## CLI / ACTION MAPPER

> Programmatic access — "Fuck the UI" interface

All canonical actions are accessible via `action_mapper.py`:

```python
from src.Tools.core.action_mapper import ActionMapper
mapper = ActionMapper()
result = mapper.execute("parse-ttab", file="object.iff")
```

CLI:

```bash
python -m src.Tools.core.action_mapper list-actions
python -m src.Tools.core.action_mapper get-autonomy object.iff
```

---

_Canonical Document — Do Not Modify Without Architecture Review_
_Last Updated: February 4, 2026_
