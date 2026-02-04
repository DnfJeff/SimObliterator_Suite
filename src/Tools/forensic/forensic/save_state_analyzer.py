"""
Save State Engine Analyzer - Reason about engine state transitions safely

When editing save files, understanding which globals are engine-internal
vs IFF-based tells us what state is "safe" to modify.

Key insight: Engine-internal globals represent transient execution state,
while IFF-based globals represent persistent game logic.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum, auto
from pathlib import Path

class StateCategory(Enum):
    """Categories of engine state for save editing safety"""
    SAFE_TO_EDIT = auto()      # Persistent state, well-defined semantics
    CAUTION = auto()           # Transient state, may cause issues
    DANGEROUS = auto()         # Engine-internal, could crash/corrupt
    UNKNOWN = auto()           # Not in our database

class TransitionType(Enum):
    """Types of state transitions"""
    MOTIVE_CHANGE = auto()     # Hunger, Energy, etc.
    RELATIONSHIP = auto()       # Social relationships
    OBJECT_STATE = auto()       # Object attributes
    SIM_STATE = auto()          # Sim properties
    WORLD_STATE = auto()        # Lot/world properties
    ENGINE_SYNC = auto()        # Engine synchronization (DANGEROUS)


@dataclass
class StateTransition:
    """Represents a potential state change"""
    global_id: int
    function_name: str
    transition_type: TransitionType
    safety: StateCategory
    affected_data: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# Map function offsets to state transition types
TRANSITION_MAPPING = {
    0x00: (TransitionType.OBJECT_STATE, "set_graphic", ["sprite_id", "animation_frame"]),
    0x01: (TransitionType.MOTIVE_CHANGE, "inc_comfort", ["comfort_motive"]),
    0x05: (TransitionType.MOTIVE_CHANGE, "set_comfort", ["comfort_motive"]),
    0x0A: (TransitionType.MOTIVE_CHANGE, "set_energy", ["energy_motive"]),
    0x08: (TransitionType.ENGINE_SYNC, "test_user_interrupt", ["ui_state", "input_queue"]),
    0x09: (TransitionType.ENGINE_SYNC, "hide_menu", ["menu_state"]),
    0x19: (TransitionType.ENGINE_SYNC, "wait_for_notify", ["thread_state", "event_queue"]),
    0x12: (TransitionType.SIM_STATE, "move_forward", ["position", "rotation"]),
}

# Known safe globals (from Global.iff, well-documented)
SAFE_GLOBALS = {
    256, 257, 258, 259, 260, 261, 262, 263,  # Base utilities
    266, 267, 268, 269, 270, 271, 272, 273,  # Motive helpers
    274, 275, 276, 277, 278, 279, 280, 281,  # Animation/movement
}

# Known dangerous globals (engine-internal, transient state)
DANGEROUS_OFFSETS = {0x08, 0x09, 0x19}  # UI/threading


class SaveStateAnalyzer:
    """
    Analyze save file modifications for safety.
    
    Uses ghost globals research to identify which state changes
    are safe vs potentially corrupting.
    """
    
    def __init__(self):
        self.safe_globals = SAFE_GLOBALS.copy()
        self.transition_map = TRANSITION_MAPPING.copy()
    
    def _get_offset(self, global_id: int) -> int:
        """Get function offset from global ID"""
        return (global_id - 256) % 256
    
    def _get_expansion(self, global_id: int) -> int:
        """Get expansion block from global ID"""
        return (global_id - 256) // 256
    
    def categorize_global(self, global_id: int) -> StateCategory:
        """Determine safety category for a global ID"""
        if global_id < 256 or global_id >= 4096:
            return StateCategory.UNKNOWN
        
        # Base game globals in known safe set
        if global_id in self.safe_globals:
            return StateCategory.SAFE_TO_EDIT
        
        offset = self._get_offset(global_id)
        expansion = self._get_expansion(global_id)
        
        # Dangerous offsets are dangerous in ANY expansion
        if offset in DANGEROUS_OFFSETS:
            return StateCategory.DANGEROUS
        
        # Non-base expansion globals are engine-internal
        if expansion > 0:
            return StateCategory.CAUTION
        
        return StateCategory.UNKNOWN
    
    def analyze_transition(self, global_id: int) -> StateTransition:
        """Analyze what state a global call affects"""
        offset = self._get_offset(global_id)
        safety = self.categorize_global(global_id)
        
        if offset in self.transition_map:
            trans_type, func_name, affected = self.transition_map[offset]
        else:
            trans_type = TransitionType.OBJECT_STATE
            func_name = f"unknown_0x{offset:02X}"
            affected = ["unknown"]
        
        warnings = []
        if safety == StateCategory.DANGEROUS:
            warnings.append("ENGINE-INTERNAL: Modifying may corrupt save or crash game")
        elif safety == StateCategory.CAUTION:
            warnings.append("Expansion-specific: May behave differently across game versions")
        
        return StateTransition(
            global_id=global_id,
            function_name=func_name,
            transition_type=trans_type,
            safety=safety,
            affected_data=affected,
            warnings=warnings
        )
    
    def analyze_bhav_calls(self, global_calls: List[int]) -> Dict[str, any]:
        """Analyze all global calls in a behavior for save editing safety"""
        results = {
            "safe_calls": [],
            "caution_calls": [],
            "dangerous_calls": [],
            "unknown_calls": [],
            "affected_state": set(),
            "warnings": [],
        }
        
        for gid in global_calls:
            trans = self.analyze_transition(gid)
            
            entry = {
                "id": gid,
                "hex": f"0x{gid:04X}",
                "function": trans.function_name,
                "type": trans.transition_type.name,
            }
            
            if trans.safety == StateCategory.SAFE_TO_EDIT:
                results["safe_calls"].append(entry)
            elif trans.safety == StateCategory.CAUTION:
                results["caution_calls"].append(entry)
            elif trans.safety == StateCategory.DANGEROUS:
                results["dangerous_calls"].append(entry)
            else:
                results["unknown_calls"].append(entry)
            
            results["affected_state"].update(trans.affected_data)
            results["warnings"].extend(trans.warnings)
        
        results["affected_state"] = list(results["affected_state"])
        results["warnings"] = list(set(results["warnings"]))
        
        return results
    
    def is_safe_to_modify(self, global_calls: List[int]) -> Tuple[bool, List[str]]:
        """Quick check if a behavior's state changes are safe to modify"""
        analysis = self.analyze_bhav_calls(global_calls)
        
        if analysis["dangerous_calls"]:
            reasons = [f"Contains dangerous call: {c['function']}" 
                      for c in analysis["dangerous_calls"]]
            return False, reasons
        
        if analysis["caution_calls"]:
            reasons = [f"Contains expansion-specific call: {c['function']}"
                      for c in analysis["caution_calls"]]
            return True, reasons  # Safe but with warnings
        
        return True, []


class EngineStateModel:
    """
    Model of engine state for reasoning about save modifications.
    
    Tracks which state is mutable vs immutable, transient vs persistent.
    """
    
    def __init__(self):
        self.motive_state = {
            "hunger": {"mutable": True, "safe_range": (-100, 100)},
            "comfort": {"mutable": True, "safe_range": (-100, 100)},
            "hygiene": {"mutable": True, "safe_range": (-100, 100)},
            "bladder": {"mutable": True, "safe_range": (-100, 100)},
            "energy": {"mutable": True, "safe_range": (-100, 100)},
            "fun": {"mutable": True, "safe_range": (-100, 100)},
            "social": {"mutable": True, "safe_range": (-100, 100)},
            "room": {"mutable": True, "safe_range": (-100, 100)},
        }
        
        self.thread_state = {
            "instruction_pointer": {"mutable": False, "reason": "Engine-managed"},
            "stack_depth": {"mutable": False, "reason": "Engine-managed"},
            "wait_state": {"mutable": False, "reason": "Engine synchronization"},
            "event_queue": {"mutable": False, "reason": "Transient"},
        }
        
        self.object_state = {
            "graphic_id": {"mutable": True, "safe_range": (0, 65535)},
            "position": {"mutable": True, "constraints": "Must be valid tile"},
            "rotation": {"mutable": True, "safe_range": (0, 3)},
            "container_id": {"mutable": True, "constraints": "Must exist"},
        }
    
    def can_modify(self, state_category: str, field: str) -> Tuple[bool, str]:
        """Check if a state field can be safely modified"""
        categories = {
            "motive": self.motive_state,
            "thread": self.thread_state,
            "object": self.object_state,
        }
        
        if state_category not in categories:
            return False, f"Unknown category: {state_category}"
        
        cat = categories[state_category]
        if field not in cat:
            return False, f"Unknown field: {field}"
        
        info = cat[field]
        if not info.get("mutable", True):
            return False, info.get("reason", "Not mutable")
        
        return True, ""
    
    def get_safe_modifications(self) -> Dict[str, List[str]]:
        """Get all safely modifiable state fields"""
        safe = {}
        
        for cat_name, cat_data in [
            ("motive", self.motive_state),
            ("thread", self.thread_state),
            ("object", self.object_state),
        ]:
            safe[cat_name] = [
                field for field, info in cat_data.items()
                if info.get("mutable", True)
            ]
        
        return safe


class ZombieModHookPoints:
    """
    Identify stable hook points for the Zombie mod.
    
    Instead of hardcoding expansion-specific global IDs,
    hook at stable offsets that work across all expansions.
    """
    
    # Recommended hook offsets for zombie behavior modification
    ZOMBIE_HOOKS = {
        0x01: "inc_comfort - modify to decay instead of increase",
        0x05: "set_comfort - clamp to zombie range",
        0x0A: "set_energy - drain faster for undead",
        0x19: "wait_for_notify - add shambling delay",
    }
    
    @staticmethod
    def get_hook_globals(offset: int) -> List[int]:
        """Get all global IDs that correspond to a hook offset"""
        globals_list = []
        for expansion in range(10):  # All expansions
            gid = 256 + (expansion * 256) + offset
            if gid < 4096:
                globals_list.append(gid)
        return globals_list
    
    @staticmethod
    def generate_hook_table() -> str:
        """Generate C-style hook table for mod"""
        lines = [
            "// Zombie Mod Hook Table",
            "// Hook by offset, not raw ID - works across all expansions",
            "",
            "typedef struct {",
            "    uint8_t offset;",
            "    const char* description;",
            "    void (*handler)(SimState* state);",
            "} ZombieHook;",
            "",
            "ZombieHook zombie_hooks[] = {",
        ]
        
        for offset, desc in ZombieModHookPoints.ZOMBIE_HOOKS.items():
            lines.append(f'    {{0x{offset:02X}, "{desc}", NULL}},')
        
        lines.append("};")
        lines.append("")
        lines.append("// Check if global ID should be intercepted")
        lines.append("bool should_intercept(uint16_t global_id) {")
        lines.append("    if (global_id < 256 || global_id >= 4096) return false;")
        lines.append("    uint8_t offset = (global_id - 256) % 256;")
        lines.append("    for (int i = 0; i < sizeof(zombie_hooks)/sizeof(ZombieHook); i++) {")
        lines.append("        if (zombie_hooks[i].offset == offset) return true;")
        lines.append("    }")
        lines.append("    return false;")
        lines.append("}")
        
        return "\n".join(lines)


# Test
if __name__ == "__main__":
    analyzer = SaveStateAnalyzer()
    
    print("=== Save State Safety Analysis ===\n")
    
    # Test behavior with mixed calls
    test_calls = [256, 257, 266, 778, 1800, 2585]
    
    print(f"Analyzing calls: {test_calls}\n")
    
    analysis = analyzer.analyze_bhav_calls(test_calls)
    
    print("Safe calls:")
    for c in analysis["safe_calls"]:
        print(f"  {c['hex']}: {c['function']}")
    
    print("\nCaution calls:")
    for c in analysis["caution_calls"]:
        print(f"  {c['hex']}: {c['function']}")
    
    print("\nDangerous calls:")
    for c in analysis["dangerous_calls"]:
        print(f"  {c['hex']}: {c['function']}")
    
    print(f"\nAffected state: {analysis['affected_state']}")
    print(f"Warnings: {analysis['warnings']}")
    
    print("\n=== Zombie Mod Hook Table ===\n")
    print(ZombieModHookPoints.generate_hook_table())
