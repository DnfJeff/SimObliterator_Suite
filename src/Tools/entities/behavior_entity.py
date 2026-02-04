"""
BehaviorEntity - System-Level BHAV Abstraction

A Behavior is NOT just a BHAV chunk.
A Behavior is:
- Identity (ID, semantic name)
- Code (instructions)
- Context (what calls it, what it calls)
- Scope (global, semi-global, object-private)
- Safety profile (dangerous opcodes, side effects)

This entity provides meaning beyond raw bytes.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any, Set
from enum import Enum


class BehaviorScope(Enum):
    """Where this behavior operates."""
    ENGINE = "engine"           # Primitive opcode
    GLOBAL = "global"           # Global.iff
    SEMI_GLOBAL = "semi-global" # Shared category
    PRIVATE = "private"         # Object-specific


class BehaviorPurpose(Enum):
    """What kind of behavior this is."""
    INIT = "init"               # Initialization
    MAIN = "main"               # Main action loop
    CHECK = "check"             # Test/check function
    HELPER = "helper"           # Utility subroutine
    AUTONOMOUS = "autonomous"   # Autonomous action
    UNKNOWN = "unknown"


@dataclass
class BehaviorEntity:
    """
    System-level Behavior abstraction.
    
    This provides semantic meaning and relationship
    context for BHAV chunks.
    """
    
    # Identity
    bhav_id: int = 0
    name: str = ""
    semantic_name: str = ""  # From EngineToolkit
    
    # Source
    source_file: str = ""
    source_iff: Optional[Any] = None
    chunk: Optional[Any] = None
    
    # Scope & Purpose
    scope: BehaviorScope = BehaviorScope.PRIVATE
    purpose: BehaviorPurpose = BehaviorPurpose.UNKNOWN
    
    # Code metrics
    instruction_count: int = 0
    has_loops: bool = False
    is_recursive: bool = False
    
    # Relationships
    calls: List[int] = field(default_factory=list)      # BHAVs this calls
    called_by: List[int] = field(default_factory=list)  # BHAVs that call this
    uses_primitives: List[int] = field(default_factory=list)  # Engine opcodes
    
    # Safety
    dangerous_opcodes: List[int] = field(default_factory=list)
    modifies_motives: bool = False
    modifies_objects: bool = False
    can_kill_sim: bool = False
    
    @classmethod
    def from_chunk(cls, chunk: Any, file_path: str = "", 
                   toolkit: Any = None) -> "BehaviorEntity":
        """Build BehaviorEntity from BHAV chunk."""
        bhav_id = getattr(chunk, 'chunk_id', 0)
        name = getattr(chunk, 'name', f'BHAV #{bhav_id}')
        
        entity = cls(
            bhav_id=bhav_id,
            name=name,
            source_file=file_path,
            chunk=chunk,
        )
        
        # Get semantic name if toolkit available
        if toolkit:
            try:
                semantic = toolkit.label_global(bhav_id)
                if semantic:
                    entity.semantic_name = semantic
            except:
                pass
        
        # Detect scope
        entity.scope = cls._detect_scope(bhav_id, file_path)
        
        # Analyze instructions
        entity._analyze_instructions(chunk)
        
        # Infer purpose from name
        entity.purpose = cls._infer_purpose(name, bhav_id)
        
        return entity
    
    @staticmethod
    def _detect_scope(bhav_id: int, file_path: str) -> BehaviorScope:
        """Detect scope from ID and path."""
        path_lower = file_path.lower()
        
        if 'global' in path_lower:
            return BehaviorScope.GLOBAL
        
        if bhav_id < 0x0100:
            return BehaviorScope.ENGINE
        elif bhav_id < 0x0200:
            return BehaviorScope.GLOBAL
        elif bhav_id < 0x1000:
            return BehaviorScope.SEMI_GLOBAL
        else:
            return BehaviorScope.PRIVATE
    
    @staticmethod
    def _infer_purpose(name: str, bhav_id: int) -> BehaviorPurpose:
        """Infer purpose from naming conventions."""
        name_lower = name.lower()
        
        if 'init' in name_lower or 'create' in name_lower:
            return BehaviorPurpose.INIT
        if 'main' in name_lower or 'action' in name_lower:
            return BehaviorPurpose.MAIN
        if 'test' in name_lower or 'check' in name_lower or 'can' in name_lower:
            return BehaviorPurpose.CHECK
        if 'util' in name_lower or 'helper' in name_lower or 'sub' in name_lower:
            return BehaviorPurpose.HELPER
        if 'autonomous' in name_lower or 'auto' in name_lower:
            return BehaviorPurpose.AUTONOMOUS
        
        return BehaviorPurpose.UNKNOWN
    
    def _analyze_instructions(self, chunk: Any):
        """Analyze instructions for metrics and safety."""
        instructions = getattr(chunk, 'instructions', [])
        self.instruction_count = len(instructions)
        
        # Dangerous opcodes
        DANGEROUS = {
            0x002E: "kill_sim",
            0x0024: "remove_object",
            0x001E: "create_object",
            0x0002: "expression",
            0x0027: "set_motive_change",
        }
        
        seen_targets: Set[int] = set()
        
        for instr in instructions:
            opcode = getattr(instr, 'opcode', 0)
            
            # Track dangerous opcodes
            if opcode in DANGEROUS:
                self.dangerous_opcodes.append(opcode)
                if opcode == 0x002E:
                    self.can_kill_sim = True
                elif opcode in (0x0002, 0x0027):
                    self.modifies_motives = True
                elif opcode in (0x001E, 0x0024):
                    self.modifies_objects = True
            
            # Track calls
            if opcode >= 0x0100:
                self.calls.append(opcode)
            elif opcode < 0x0100:
                self.uses_primitives.append(opcode)
            
            # Check for loops (simplified)
            true_target = getattr(instr, 'true_target', None)
            false_target = getattr(instr, 'false_target', None)
            
            idx = instructions.index(instr)
            if true_target is not None and true_target < idx:
                self.has_loops = True
            if false_target is not None and false_target < idx:
                self.has_loops = True
        
        # Check for recursion
        if self.bhav_id in self.calls:
            self.is_recursive = True
    
    # ─────────────────────────────────────────────────────────────
    # QUERY METHODS
    # ─────────────────────────────────────────────────────────────
    
    def get_display_name(self) -> str:
        """Get best display name."""
        if self.semantic_name:
            return self.semantic_name
        return self.name
    
    def get_summary(self) -> str:
        """One-liner summary."""
        parts = [f"{self.scope.value}"]
        
        if self.instruction_count:
            parts.append(f"{self.instruction_count} ops")
        
        if self.calls:
            parts.append(f"calls {len(self.calls)}")
        
        if self.dangerous_opcodes:
            parts.append("⚠ dangerous")
        
        return " | ".join(parts)
    
    def get_safety_summary(self) -> str:
        """Safety information."""
        if self.can_kill_sim:
            return "⛔ Can kill Sim"
        if self.modifies_objects:
            return "⚠ Modifies objects"
        if self.modifies_motives:
            return "⚡ Modifies motives"
        if self.dangerous_opcodes:
            return "⚡ Contains risky opcodes"
        return "✓ Safe"
    
    def get_relationship_summary(self) -> str:
        """Relationship information."""
        parts = []
        
        global_calls = [c for c in self.calls if 0x0100 <= c < 0x0200]
        semi_calls = [c for c in self.calls if 0x0200 <= c < 0x1000]
        private_calls = [c for c in self.calls if c >= 0x1000]
        
        if global_calls:
            parts.append(f"{len(global_calls)} global calls")
        if semi_calls:
            parts.append(f"{len(semi_calls)} semi-global calls")
        if private_calls:
            parts.append(f"{len(private_calls)} private calls")
        
        if not parts:
            return "No outgoing calls"
        
        return ", ".join(parts)
    
    def __repr__(self):
        return f"BehaviorEntity(id=0x{self.bhav_id:04X}, name='{self.name}')"
