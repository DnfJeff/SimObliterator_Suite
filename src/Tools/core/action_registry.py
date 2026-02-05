"""
SimObliterator Action Registry
==============================

Canonical action surface enforcement.

HARD RULE: If an action is not registered here, it does not exist.
New features = new actions = new safety definitions.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Dict, Set
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION CLASSIFICATION ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class Mutability(Enum):
    """Does the action change state?"""
    READ = "read"
    PREVIEW = "preview"
    WRITE = "write"


class ActionScope(Enum):
    """What does the action affect?"""
    FILE = "file"
    OBJECT = "object"
    GLOBAL = "global"
    SAVE = "save"
    SYSTEM = "system"


class RiskLevel(Enum):
    """Blast radius if wrong."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionCategory(Enum):
    """Category for grouping actions."""
    FILE_CONTAINER = "file_container"
    SAVE_STATE = "save_state"
    BHAV = "bhav"
    VISUALIZATION = "visualization"
    EXPORT = "export"
    IMPORT = "import"
    ANALYSIS = "analysis"
    SEARCH = "search"
    SYSTEM = "system"
    UI = "ui"
    TTAB = "ttab"
    SLOT = "slot"
    LOCALIZATION = "localization"


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ActionDefinition:
    """
    Complete definition of a canonical action.
    
    Every action in the system MUST have one of these.
    """
    name: str
    category: ActionCategory
    mutability: Mutability
    scope: ActionScope
    risk: RiskLevel
    requires_pipeline: bool = False
    requires_confirmation: bool = False
    audited: bool = True
    description: str = ""
    checks: list = field(default_factory=list)
    
    def validate_execution(self, context: dict = None) -> tuple[bool, str]:
        """
        Validate if this action can execute in the given context.
        
        Returns (is_valid, reason).
        """
        context = context or {}
        
        # Check mutation pipeline requirement
        if self.requires_pipeline:
            pipeline_mode = context.get('pipeline_mode', 'INSPECT')
            if self.mutability == Mutability.WRITE and pipeline_mode == 'INSPECT':
                return False, f"Action '{self.name}' requires MUTATE mode, currently in INSPECT"
        
        # Check user confirmation requirement
        if self.requires_confirmation and not context.get('user_confirmed', False):
            return False, f"Action '{self.name}' requires user confirmation"
        
        # Check safety for write actions
        if self.mutability == Mutability.WRITE:
            if not context.get('safety_checked', False) and self.risk == RiskLevel.HIGH:
                return False, f"Action '{self.name}' is HIGH risk and requires safety check"
        
        return True, "OK"
    
    def tags(self) -> dict:
        """Return classification tags as dictionary."""
        return {
            'Mutability': self.mutability.value,
            'Scope': self.scope.value,
            'Risk': self.risk.value,
            'Requires MutationPipeline': 'Yes' if self.requires_pipeline else 'No',
            'Requires User Confirmation': 'Yes' if self.requires_confirmation else 'No',
            'Audited': 'Yes' if self.audited else 'No',
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION REGISTRY (SINGLETON)
# ═══════════════════════════════════════════════════════════════════════════════

class ActionRegistry:
    """
    Canonical registry of all valid actions.
    
    HARD RULE: Unregistered actions are rejected at runtime.
    """
    
    _instance = None
    
    def __init__(self):
        self._actions: Dict[str, ActionDefinition] = {}
        self._audit_log: list = []
        self._register_canonical_actions()
    
    @classmethod
    def get(cls) -> "ActionRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(self, action: ActionDefinition):
        """Register an action definition."""
        self._actions[action.name] = action
    
    def get_action(self, name: str) -> Optional[ActionDefinition]:
        """Get action definition by name."""
        return self._actions.get(name)
    
    def is_valid_action(self, name: str) -> bool:
        """Check if action name is registered."""
        return name in self._actions
    
    def validate_and_log(self, action_name: str, context: dict = None) -> tuple[bool, str]:
        """
        Validate action execution and log if audited.
        
        This is the ONLY way to execute actions.
        """
        action = self.get_action(action_name)
        
        # HARD RULE: Unregistered actions are rejected
        if action is None:
            self._audit_log.append({
                'timestamp': datetime.now().isoformat(),
                'action': action_name,
                'result': 'REJECTED',
                'reason': 'Unregistered action',
            })
            return False, f"REJECTED: '{action_name}' is not a registered action"
        
        # Validate execution context
        is_valid, reason = action.validate_execution(context)
        
        # Log if audited
        if action.audited:
            self._audit_log.append({
                'timestamp': datetime.now().isoformat(),
                'action': action_name,
                'category': action.category.value,
                'mutability': action.mutability.value,
                'result': 'ALLOWED' if is_valid else 'BLOCKED',
                'reason': reason,
                'context': context,
            })
        
        return is_valid, reason
    
    def get_audit_log(self) -> list:
        """Get action audit log."""
        return self._audit_log.copy()
    
    def get_actions_by_category(self, category: ActionCategory) -> list[ActionDefinition]:
        """Get all actions in a category."""
        return [a for a in self._actions.values() if a.category == category]
    
    def get_write_actions(self) -> list[ActionDefinition]:
        """Get all write actions."""
        return [a for a in self._actions.values() if a.mutability == Mutability.WRITE]
    
    def get_high_risk_actions(self) -> list[ActionDefinition]:
        """Get all high-risk actions."""
        return [a for a in self._actions.values() if a.risk == RiskLevel.HIGH]
    
    def summary(self) -> dict:
        """Get registry summary statistics."""
        actions = list(self._actions.values())
        return {
            'total': len(actions),
            'by_category': {
                cat.value: len([a for a in actions if a.category == cat])
                for cat in ActionCategory
            },
            'write_actions': len([a for a in actions if a.mutability == Mutability.WRITE]),
            'high_risk': len([a for a in actions if a.risk == RiskLevel.HIGH]),
            'require_pipeline': len([a for a in actions if a.requires_pipeline]),
            'require_confirmation': len([a for a in actions if a.requires_confirmation]),
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # CANONICAL ACTION REGISTRATION
    # ─────────────────────────────────────────────────────────────────────────
    
    def _register_canonical_actions(self):
        """Register all canonical actions from ACTION_SURFACE.md."""
        
        # ═══════════════════════════════════════════════════════════════════
        # 1. FILE / CONTAINER ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        file_actions = [
            ("LoadSave", Mutability.READ, ActionScope.SAVE, RiskLevel.LOW, False, False),
            ("WriteSave", Mutability.WRITE, ActionScope.SAVE, RiskLevel.HIGH, True, True),
            ("BackupSave", Mutability.WRITE, ActionScope.SYSTEM, RiskLevel.LOW, False, False),
            ("RestoreSave", Mutability.WRITE, ActionScope.SAVE, RiskLevel.HIGH, True, True),
            ("LoadIFF", Mutability.READ, ActionScope.FILE, RiskLevel.LOW, False, False),
            ("LoadFAR", Mutability.READ, ActionScope.FILE, RiskLevel.LOW, False, False),
            ("WriteIFF", Mutability.WRITE, ActionScope.FILE, RiskLevel.HIGH, True, True),
            ("WriteFAR", Mutability.WRITE, ActionScope.FILE, RiskLevel.HIGH, True, True),
            ("MergeIFF", Mutability.WRITE, ActionScope.FILE, RiskLevel.HIGH, True, True),
            ("SplitIFF", Mutability.WRITE, ActionScope.FILE, RiskLevel.MEDIUM, True, True),
            ("ReplaceChunk", Mutability.WRITE, ActionScope.OBJECT, RiskLevel.HIGH, True, True),
            ("DeleteChunk", Mutability.WRITE, ActionScope.OBJECT, RiskLevel.HIGH, True, True),
            ("AddChunk", Mutability.WRITE, ActionScope.OBJECT, RiskLevel.MEDIUM, True, True),
            ("ReindexContainer", Mutability.WRITE, ActionScope.FILE, RiskLevel.MEDIUM, True, False),
            ("NormalizeHeaders", Mutability.WRITE, ActionScope.FILE, RiskLevel.MEDIUM, True, False),
            ("ValidateContainer", Mutability.READ, ActionScope.FILE, RiskLevel.LOW, False, False),
        ]
        
        for name, mut, scope, risk, pipeline, confirm in file_actions:
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.FILE_CONTAINER,
                mutability=mut,
                scope=scope,
                risk=risk,
                requires_pipeline=pipeline,
                requires_confirmation=confirm,
                checks=["Format version", "Expansion scope", "Chunk dependency", "Write mode"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 2. SAVE-STATE MUTATIONS
        # ═══════════════════════════════════════════════════════════════════
        
        save_actions = [
            ("AddMoney", RiskLevel.MEDIUM),
            ("RemoveMoney", RiskLevel.MEDIUM),
            ("SetMoney", RiskLevel.MEDIUM),
            ("AddSim", RiskLevel.HIGH),
            ("RemoveSim", RiskLevel.HIGH),
            ("ModifySimAttributes", RiskLevel.HIGH),
            ("ModifyHousehold", RiskLevel.HIGH),
            ("ModifyRelationships", RiskLevel.HIGH),
            ("ModifyInventory", RiskLevel.MEDIUM),
            ("ModifyCareer", RiskLevel.MEDIUM),
            ("ModifyMotives", RiskLevel.MEDIUM),
            ("ModifyAspirations", RiskLevel.MEDIUM),
            ("ModifyMemories", RiskLevel.MEDIUM),
            ("ModifyTime", RiskLevel.MEDIUM),
            ("ModifyLotState", RiskLevel.HIGH),
            ("ModifyNeighborhoodState", RiskLevel.HIGH),
            # Granular binary-level actions (v1.0.3)
            ("SetSimSkill", RiskLevel.MEDIUM),
            ("SetSimMotive", RiskLevel.MEDIUM),
            ("SetSimPersonality", RiskLevel.MEDIUM),
            ("SetSimCareer", RiskLevel.MEDIUM),
            ("MaxAllSkills", RiskLevel.MEDIUM),
            ("MaxAllMotives", RiskLevel.MEDIUM),
            ("SetRelationship", RiskLevel.HIGH),
            ("SetFamilyMoney", RiskLevel.MEDIUM),
        ]
        
        for name, risk in save_actions:
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.SAVE_STATE,
                mutability=Mutability.WRITE,
                scope=ActionScope.SAVE,
                risk=risk,
                requires_pipeline=True,
                requires_confirmation=True,
                checks=["is_safe_to_edit()", "BHAV dependencies", "Cross-Sim consistency", "Save version"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 3. BHAV ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        bhav_actions = [
            ("LoadBHAV", Mutability.READ, RiskLevel.LOW, False, False),
            ("DisassembleBHAV", Mutability.READ, RiskLevel.LOW, False, False),
            ("EditBHAV", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("ReplaceBHAV", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("InjectBHAV", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("RemoveBHAV", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("PatchGlobalBHAV", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("PatchSemiGlobalBHAV", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("PatchObjectBHAV", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("RewireBHAVCalls", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("RemapBHAVIDs", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("ValidateBHAVGraph", Mutability.READ, RiskLevel.LOW, False, False),
            ("DetectUnknownOpcodes", Mutability.READ, RiskLevel.LOW, False, False),
            ("ResolveSemanticNames", Mutability.READ, RiskLevel.LOW, False, False),
        ]
        
        for name, mut, risk, pipeline, confirm in bhav_actions:
            scope = ActionScope.GLOBAL if "Global" in name else ActionScope.OBJECT
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.BHAV,
                mutability=mut,
                scope=scope,
                risk=risk,
                requires_pipeline=pipeline,
                requires_confirmation=confirm,
                audited=mut != Mutability.READ or "Detect" in name or "Validate" in name,
                checks=["Call graph validity", "Opcode legality", "Scope rules", "Cycle detection"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 4. VISUALIZATION ACTIONS (all read-only)
        # ═══════════════════════════════════════════════════════════════════
        
        viz_actions = [
            "LoadAssetTo2D", "LoadAssetTo3D", "DecodeSPR2", "DecodeDrawGroup",
            "DecodeMesh", "DecodeAnimation", "PreviewRotations", "PreviewZoomLevels",
            "PreviewFrames"
        ]
        
        for name in viz_actions:
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.VISUALIZATION,
                mutability=Mutability.READ,
                scope=ActionScope.OBJECT,
                risk=RiskLevel.LOW,
                requires_pipeline=False,
                requires_confirmation=False,
                audited=False,
                checks=["Decoder availability", "Fallback path", "Read-only enforcement"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 5. EXPORT ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        export_actions = [
            ("ExportAssetToModern", ActionScope.OBJECT, False),
            ("ExportAssetToLegacy", ActionScope.OBJECT, True),
            ("ExportSpritePNGs", ActionScope.OBJECT, False),
            ("ExportSpriteSheet", ActionScope.OBJECT, False),
            ("ExportMesh", ActionScope.OBJECT, False),
            ("ExportBehaviorDocs", ActionScope.OBJECT, False),
            ("ExportGraphs", ActionScope.SYSTEM, False),
            ("ExportSaveSnapshot", ActionScope.SAVE, False),
            ("ExportUnknownsReport", ActionScope.SYSTEM, False),
        ]
        
        for name, scope, confirm in export_actions:
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.EXPORT,
                mutability=Mutability.READ,
                scope=scope,
                risk=RiskLevel.LOW if not confirm else RiskLevel.MEDIUM,
                requires_pipeline=False,
                requires_confirmation=confirm,
                checks=["Fidelity loss warnings", "Metadata completeness", "Determinism"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 6. IMPORT ACTIONS (highest risk)
        # ═══════════════════════════════════════════════════════════════════
        
        import_actions = [
            ("ImportAssetFromModern", RiskLevel.HIGH),
            ("ImportAssetFromLegacy", RiskLevel.HIGH),
            ("ImportSpritePNG", RiskLevel.MEDIUM),
            ("ImportSpriteSheet", RiskLevel.MEDIUM),
            ("ImportMesh", RiskLevel.MEDIUM),
            ("ImportBehavior", RiskLevel.HIGH),
            ("ImportOpcodeDefs", RiskLevel.MEDIUM),
            ("ImportUnknownsDB", RiskLevel.LOW),
            ("ImportSavePatch", RiskLevel.HIGH),
        ]
        
        for name, risk in import_actions:
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.IMPORT,
                mutability=Mutability.WRITE,
                scope=ActionScope.OBJECT if "Asset" in name or "Sprite" in name or "Mesh" in name else ActionScope.SYSTEM,
                risk=risk,
                requires_pipeline=True,
                requires_confirmation=risk != RiskLevel.LOW,
                checks=["Schema validation", "ID collision", "Expansion compatibility", "Dry-run diff"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 7. ANALYSIS ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        analysis_actions = [
            ("BuildCallGraph", False),
            ("BuildResourceGraph", False),
            ("BuildDependencyGraph", False),
            ("DetectCycles", True),
            ("DetectDeadCode", True),
            ("DetectUnusedAssets", True),
            ("CompareExpansions", False),
            ("DiffObjects", False),
            ("DiffBHAVs", False),
            ("DiffGlobals", False),
        ]
        
        for name, audited in analysis_actions:
            scope = ActionScope.GLOBAL if "Global" in name else (
                ActionScope.FILE if "Resource" in name or "Dependency" in name or "Unused" in name 
                else ActionScope.OBJECT
            )
            if "Expansion" in name:
                scope = ActionScope.SYSTEM
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.ANALYSIS,
                mutability=Mutability.READ,
                scope=scope,
                risk=RiskLevel.LOW,
                requires_pipeline=False,
                requires_confirmation=False,
                audited=audited,
                checks=["Analysis scope", "Caching validity", "Deterministic generation"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 8. SEARCH ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        search_actions = [
            "SearchByName", "SearchByID", "SearchByOpcode", "SearchByBehaviorPurpose",
            "SearchByLifecyclePhase", "SearchBySafetyRisk", "SearchByExpansion",
            "SearchByUnknownUsage", "CrossReferenceSearch"
        ]
        
        for name in search_actions:
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.SEARCH,
                mutability=Mutability.READ,
                scope=ActionScope.SYSTEM,
                risk=RiskLevel.LOW,
                requires_pipeline=False,
                requires_confirmation=False,
                audited=False,
                checks=["Semantic index availability", "Confidence weighting", "Provenance tags"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 9. SYSTEM ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        system_actions = [
            ("ScanDirectory", Mutability.READ, RiskLevel.LOW, False, False),
            ("FullForensicScan", Mutability.READ, RiskLevel.LOW, False, False),
            ("UpdateUnknownsDB", Mutability.WRITE, RiskLevel.LOW, True, False),
            ("RebuildIndexes", Mutability.WRITE, RiskLevel.LOW, False, False),
            ("ClearCaches", Mutability.WRITE, RiskLevel.LOW, False, False),
            ("ValidateEnvironment", Mutability.READ, RiskLevel.LOW, False, False),
            ("CheckDependencies", Mutability.READ, RiskLevel.LOW, False, False),
            ("MigrateData", Mutability.WRITE, RiskLevel.MEDIUM, True, True),
            ("LoadWorkspace", Mutability.READ, RiskLevel.LOW, False, False),
            ("SaveWorkspace", Mutability.WRITE, RiskLevel.LOW, False, False),
        ]
        
        for name, mut, risk, pipeline, confirm in system_actions:
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.SYSTEM,
                mutability=mut,
                scope=ActionScope.SYSTEM,
                risk=risk,
                requires_pipeline=pipeline,
                requires_confirmation=confirm,
                audited=mut == Mutability.WRITE or "Scan" in name,
                checks=["Version compatibility", "Migration safety", "Partial failure recovery"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 10. UI ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        ui_actions = [
            ("SelectEntity", Mutability.READ, False, False),
            ("ChangeScope", Mutability.READ, False, False),
            ("ToggleViewMode", Mutability.READ, False, False),
            ("OpenInspector", Mutability.READ, False, False),
            ("ApplyFilter", Mutability.READ, False, False),
            ("TriggerPreview", Mutability.PREVIEW, False, False),
            ("ConfirmMutation", Mutability.WRITE, True, True),
            ("CancelMutation", Mutability.READ, False, False),
        ]
        
        for name, mut, pipeline, confirm in ui_actions:
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.UI,
                mutability=mut,
                scope=ActionScope.SYSTEM,
                risk=RiskLevel.LOW if mut != Mutability.WRITE else RiskLevel.HIGH,
                requires_pipeline=pipeline,
                requires_confirmation=confirm,
                audited=mut == Mutability.WRITE or name == "CancelMutation",
                checks=["Selection validity", "Mode gating", "Undo availability"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 11. TTAB / INTERACTION ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        ttab_actions = [
            ("LoadTTAB", Mutability.READ, RiskLevel.LOW, False, False),
            ("ParseTTABFull", Mutability.READ, RiskLevel.LOW, False, False),
            ("EditTTABAutonomy", Mutability.WRITE, RiskLevel.MEDIUM, True, True),
            ("EditTTABMotiveEffect", Mutability.WRITE, RiskLevel.MEDIUM, True, True),
            ("AddTTABInteraction", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("RemoveTTABInteraction", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("BuildMultiObjectContext", Mutability.READ, RiskLevel.LOW, False, False),
            ("SwitchObjectContext", Mutability.READ, RiskLevel.LOW, False, False),
        ]
        
        for name, mut, risk, pipeline, confirm in ttab_actions:
            scope = ActionScope.FILE if "Context" in name else ActionScope.OBJECT
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.TTAB,
                mutability=mut,
                scope=scope,
                risk=risk,
                requires_pipeline=pipeline,
                requires_confirmation=confirm,
                audited=mut == Mutability.WRITE or "Load" in name or "Build" in name,
                checks=["Multi-OBJD awareness", "Autonomy range", "TTAB version"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 12. SLOT / ROUTING ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        slot_actions = [
            ("LoadSLOT", Mutability.READ, RiskLevel.LOW, False, False),
            ("ParseSLOT", Mutability.READ, RiskLevel.LOW, False, False),
            ("AddSLOT", Mutability.WRITE, RiskLevel.MEDIUM, True, True),
            ("EditSLOT", Mutability.WRITE, RiskLevel.MEDIUM, True, True),
            ("RemoveSLOT", Mutability.WRITE, RiskLevel.MEDIUM, True, True),
            ("DuplicateSLOT", Mutability.WRITE, RiskLevel.LOW, True, False),
            ("CreateChairSlots", Mutability.WRITE, RiskLevel.LOW, True, False),
            ("CreateCounterSlots", Mutability.WRITE, RiskLevel.LOW, True, False),
        ]
        
        for name, mut, risk, pipeline, confirm in slot_actions:
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.SLOT,
                mutability=mut,
                scope=ActionScope.OBJECT,
                risk=risk,
                requires_pipeline=pipeline,
                requires_confirmation=confirm,
                audited=mut == Mutability.WRITE or "Load" in name,
                checks=["Slot position bounds", "Slot type", "Facing normalization"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 13. BHAV AUTHORING ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        authoring_actions = [
            ("CreateInstruction", Mutability.PREVIEW, RiskLevel.LOW, False, False),
            ("BuildOperand", Mutability.PREVIEW, RiskLevel.LOW, False, False),
            ("CreateBHAV", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("InsertInstruction", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("DeleteInstruction", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("MoveInstruction", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("CopyInstructions", Mutability.READ, RiskLevel.LOW, False, False),
            ("PasteInstructions", Mutability.WRITE, RiskLevel.HIGH, True, True),
            ("RewirePointers", Mutability.WRITE, RiskLevel.HIGH, True, True),
        ]
        
        for name, mut, risk, pipeline, confirm in authoring_actions:
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.BHAV,
                mutability=mut,
                scope=ActionScope.OBJECT,
                risk=risk,
                requires_pipeline=pipeline,
                requires_confirmation=confirm,
                audited=mut == Mutability.WRITE,
                checks=["Pointer validity", "BHAV ID range", "Operand validation", "Auto-rewire"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 14. LOCALIZATION / STRING ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        localization_actions = [
            ("ParseSTR", Mutability.READ, RiskLevel.LOW, False, False),
            ("ListLanguageSlots", Mutability.READ, RiskLevel.LOW, False, False),
            ("AuditLocalization", Mutability.READ, RiskLevel.LOW, False, False),
            ("CopyLanguageSlot", Mutability.WRITE, RiskLevel.MEDIUM, True, True),
            ("FillMissingSlots", Mutability.WRITE, RiskLevel.MEDIUM, True, True),
            ("FindSTRReferences", Mutability.READ, RiskLevel.LOW, False, False),
            ("FindOrphanSTR", Mutability.READ, RiskLevel.LOW, False, False),
            ("EditSTREntry", Mutability.WRITE, RiskLevel.MEDIUM, True, True),
        ]
        
        for name, mut, risk, pipeline, confirm in localization_actions:
            scope = ActionScope.FILE if "Orphan" in name or "Audit" in name or "References" in name else ActionScope.OBJECT
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.LOCALIZATION,
                mutability=mut,
                scope=scope,
                risk=risk,
                requires_pipeline=pipeline,
                requires_confirmation=confirm,
                audited=mut == Mutability.WRITE or "Audit" in name or "Orphan" in name,
                checks=["STR# format detection", "Language code validation", "Catalog references"]
            ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 15. LOT / AMBIENCE ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        
        lot_actions = [
            ("AnalyzeLot", Mutability.READ, RiskLevel.LOW, False, False),
            ("GetTerrainType", Mutability.READ, RiskLevel.LOW, False, False),
            ("ListAmbienceObjects", Mutability.READ, RiskLevel.LOW, False, False),
            ("ScanLotFolder", Mutability.READ, RiskLevel.LOW, False, False),
            ("FindAmbienceByGUID", Mutability.READ, RiskLevel.LOW, False, False),
            ("ParseSIMI", Mutability.READ, RiskLevel.LOW, False, False),
            ("ParseHOUS", Mutability.READ, RiskLevel.LOW, False, False),
            ("ListLotARRYChunks", Mutability.READ, RiskLevel.LOW, False, False),
            ("ExtractLotObjects", Mutability.READ, RiskLevel.LOW, False, False),
            ("CompareLots", Mutability.READ, RiskLevel.LOW, False, False),
        ]
        
        for name, mut, risk, pipeline, confirm in lot_actions:
            scope = ActionScope.FILE if "Folder" in name or "Compare" in name else ActionScope.OBJECT
            self.register(ActionDefinition(
                name=name,
                category=ActionCategory.ANALYSIS,
                mutability=mut,
                scope=scope,
                risk=risk,
                requires_pipeline=pipeline,
                requires_confirmation=confirm,
                audited="Analyze" in name or "Scan" in name or "Compare" in name,
                checks=["House number extraction", "Terrain type lookup", "ARRY chunk validation"]
            ))


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_action(action_name: str, context: dict = None) -> tuple[bool, str]:
    """
    Validate an action before execution.
    
    This is the primary entry point for action validation.
    """
    return ActionRegistry.get().validate_and_log(action_name, context)


def is_registered_action(action_name: str) -> bool:
    """Check if an action is registered."""
    return ActionRegistry.get().is_valid_action(action_name)


def get_action_info(action_name: str) -> Optional[dict]:
    """Get full info about an action."""
    action = ActionRegistry.get().get_action(action_name)
    if action is None:
        return None
    return {
        'name': action.name,
        'category': action.category.value,
        **action.tags(),
        'checks': action.checks,
    }
