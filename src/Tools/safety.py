"""
Safety API - Cross-Cutting Safety Concern

From Conceptual Directives:
- Safety is a cross-cutting concern
- Any modification path should have access to:
  - is_safe_to_edit()
  - Scope validation
  - Expansion awareness
  - Dependency awareness

This module provides the canonical safety API for ALL edit operations.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple, Any
from enum import Enum
from pathlib import Path


class SafetyLevel(Enum):
    """Safety levels for edit operations."""
    SAFE = "safe"           # Go ahead
    CAUTION = "caution"     # Proceed with awareness
    WARNING = "warning"     # Think twice
    DANGEROUS = "dangerous" # High risk
    BLOCKED = "blocked"     # Cannot edit


class Scope(Enum):
    """Resource scope levels."""
    OBJECT = "object"           # Object-specific
    SEMI_GLOBAL = "semi-global" # Shared within category
    GLOBAL = "global"           # Game-wide
    ENGINE = "engine"           # Core engine (never edit)


class ResourceOwner(Enum):
    """Who owns this resource."""
    EA_BASE = "ea_base"         # Original The Sims
    EA_EXPANSION = "ea_expansion"  # Official expansion
    MAXIS = "maxis"             # Maxis content
    MOD = "mod"                 # User/community mod
    UNKNOWN = "unknown"


@dataclass
class SafetyResult:
    """Result of a safety check."""
    level: SafetyLevel
    reasons: List[str]
    scope: Scope
    owner: ResourceOwner
    affected_count: int = 0
    can_proceed: bool = True
    
    @property
    def is_safe(self) -> bool:
        return self.level in (SafetyLevel.SAFE, SafetyLevel.CAUTION)
    
    def summary(self) -> str:
        """One-line summary for UI."""
        icon = {
            SafetyLevel.SAFE: "✓",
            SafetyLevel.CAUTION: "⚡",
            SafetyLevel.WARNING: "⚠",
            SafetyLevel.DANGEROUS: "⛔",
            SafetyLevel.BLOCKED: "🚫",
        }.get(self.level, "?")
        return f"{icon} {self.level.value.upper()}: {self.reasons[0] if self.reasons else 'Unknown'}"


# ─────────────────────────────────────────────────────────────────────────────
# DANGEROUS PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

# Opcodes that can cause serious game issues
DANGEROUS_OPCODES = {
    0x002E: ("Kill Sim", SafetyLevel.DANGEROUS),
    0x0024: ("Remove Object Instance", SafetyLevel.WARNING),
    0x001E: ("Create Object", SafetyLevel.CAUTION),
    0x0002: ("Expression (motive change)", SafetyLevel.CAUTION),
    0x0027: ("Set Motive Change", SafetyLevel.WARNING),
    0x0012: ("Find Location (routing)", SafetyLevel.CAUTION),
    0x003B: ("Set Balloon/Headline", SafetyLevel.SAFE),
}

# Global BHAV ranges (affects everything)
GLOBAL_BHAV_RANGES = [
    (0x0000, 0x00FF, "Engine primitives"),
    (0x0100, 0x01FF, "Global subroutines"),
    (0x0200, 0x03FF, "Semi-global subroutines"),
]

# Known EA/Maxis paths
EA_PATHS = [
    "expansionpack", "gamedata", "userdata", "downloads",
    "livin' large", "house party", "hot date", "vacation",
    "unleashed", "superstar", "makin' magic"
]


# ─────────────────────────────────────────────────────────────────────────────
# CORE API
# ─────────────────────────────────────────────────────────────────────────────

def is_safe_to_edit(
    chunk: Any,
    file_path: Optional[str] = None,
    check_dependencies: bool = True
) -> SafetyResult:
    """
    THE canonical safety check for any edit operation.
    
    Returns SafetyResult with:
    - level: SafetyLevel enum
    - reasons: List of human-readable explanations
    - scope: Where this resource operates
    - owner: EA vs mod
    - can_proceed: Whether edit should be allowed
    
    Usage:
        result = is_safe_to_edit(chunk, current_file)
        if not result.is_safe:
            show_warning(result.summary())
        if not result.can_proceed:
            block_edit()
    """
    reasons = []
    level = SafetyLevel.SAFE
    scope = Scope.OBJECT
    owner = ResourceOwner.UNKNOWN
    affected_count = 0
    
    # 1. Check file ownership
    if file_path:
        owner = _detect_owner(file_path)
        if owner in (ResourceOwner.EA_BASE, ResourceOwner.EA_EXPANSION, ResourceOwner.MAXIS):
            level = _elevate(level, SafetyLevel.DANGEROUS)
            reasons.append("This is original game content - edits may corrupt game")
    
    # 2. Check chunk scope
    chunk_type = getattr(chunk, 'type_code', None) or getattr(chunk, 'chunk_type', '')
    chunk_id = getattr(chunk, 'chunk_id', 0)
    
    scope, scope_reason = _detect_scope(chunk_type, chunk_id, file_path)
    if scope == Scope.GLOBAL:
        level = _elevate(level, SafetyLevel.WARNING)
        reasons.append(scope_reason)
    elif scope == Scope.SEMI_GLOBAL:
        level = _elevate(level, SafetyLevel.CAUTION)
        reasons.append(scope_reason)
    elif scope == Scope.ENGINE:
        level = SafetyLevel.BLOCKED
        reasons.append("Engine primitives cannot be edited")
    
    # 3. Check for dangerous opcodes (BHAV only)
    if chunk_type == 'BHAV':
        opcode_level, opcode_reasons = _check_bhav_opcodes(chunk)
        level = _elevate(level, opcode_level)
        reasons.extend(opcode_reasons)
    
    # 4. Check dependencies (optional, expensive)
    if check_dependencies and chunk_type == 'BHAV':
        affected_count = _count_dependents(chunk)
        if affected_count > 10:
            level = _elevate(level, SafetyLevel.WARNING)
            reasons.append(f"This BHAV is called by {affected_count} other behaviors")
        elif affected_count > 0:
            level = _elevate(level, SafetyLevel.CAUTION)
            reasons.append(f"This BHAV is called by {affected_count} other behavior(s)")
    
    # 5. Determine if edit should proceed
    can_proceed = level != SafetyLevel.BLOCKED
    
    if not reasons:
        reasons.append("No safety concerns detected")
    
    return SafetyResult(
        level=level,
        reasons=reasons,
        scope=scope,
        owner=owner,
        affected_count=affected_count,
        can_proceed=can_proceed
    )


def check_scope(chunk: Any, file_path: Optional[str] = None) -> Tuple[Scope, str]:
    """Quick scope check without full safety analysis."""
    chunk_type = getattr(chunk, 'type_code', None) or getattr(chunk, 'chunk_type', '')
    chunk_id = getattr(chunk, 'chunk_id', 0)
    return _detect_scope(chunk_type, chunk_id, file_path)


def check_owner(file_path: str) -> ResourceOwner:
    """Check who owns a file."""
    return _detect_owner(file_path)


def get_edit_warning(chunk: Any, file_path: Optional[str] = None) -> Optional[str]:
    """Get a one-liner warning for display, or None if safe."""
    result = is_safe_to_edit(chunk, file_path, check_dependencies=False)
    if result.level in (SafetyLevel.SAFE, SafetyLevel.CAUTION):
        return None
    return result.summary()


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _elevate(current: SafetyLevel, new: SafetyLevel) -> SafetyLevel:
    """Elevate safety level (higher = more dangerous)."""
    order = [SafetyLevel.SAFE, SafetyLevel.CAUTION, SafetyLevel.WARNING, 
             SafetyLevel.DANGEROUS, SafetyLevel.BLOCKED]
    return max(current, new, key=lambda x: order.index(x))


def _detect_owner(file_path: str) -> ResourceOwner:
    """Detect who owns a file based on path."""
    path_lower = file_path.lower() if file_path else ""
    
    for ea_marker in EA_PATHS:
        if ea_marker in path_lower:
            if 'expansion' in ea_marker or ea_marker in ['livin\' large', 'house party', 
                'hot date', 'vacation', 'unleashed', 'superstar', 'makin\' magic']:
                return ResourceOwner.EA_EXPANSION
            return ResourceOwner.EA_BASE
    
    if 'maxis' in path_lower:
        return ResourceOwner.MAXIS
    
    if 'downloads' in path_lower or 'custom' in path_lower or 'mod' in path_lower:
        return ResourceOwner.MOD
    
    return ResourceOwner.UNKNOWN


def _detect_scope(chunk_type: str, chunk_id: int, file_path: Optional[str]) -> Tuple[Scope, str]:
    """Detect the scope of a resource."""
    path_lower = (file_path or "").lower()
    
    # File-based scope detection
    if 'global' in path_lower:
        return Scope.GLOBAL, "Resource is in Global.iff - affects all objects"
    
    if 'semi' in path_lower:
        return Scope.SEMI_GLOBAL, "Resource is semi-global - affects category of objects"
    
    # BHAV ID-based scope detection
    if chunk_type == 'BHAV':
        for start, end, desc in GLOBAL_BHAV_RANGES:
            if start <= chunk_id <= end:
                if chunk_id < 0x0100:
                    return Scope.ENGINE, desc
                elif chunk_id < 0x0200:
                    return Scope.GLOBAL, desc
                else:
                    return Scope.SEMI_GLOBAL, desc
        
        # Private BHAVs (object-specific)
        if chunk_id >= 0x1000:
            return Scope.OBJECT, "Object-private behavior"
    
    return Scope.OBJECT, "Object-specific resource"


def _check_bhav_opcodes(bhav) -> Tuple[SafetyLevel, List[str]]:
    """Check BHAV for dangerous opcodes."""
    level = SafetyLevel.SAFE
    reasons = []
    
    instructions = getattr(bhav, 'instructions', [])
    
    dangerous_found = {}
    for instr in instructions:
        opcode = getattr(instr, 'opcode', 0)
        if opcode in DANGEROUS_OPCODES:
            name, op_level = DANGEROUS_OPCODES[opcode]
            dangerous_found[opcode] = (name, op_level)
            level = _elevate(level, op_level)
    
    for opcode, (name, op_level) in dangerous_found.items():
        reasons.append(f"Contains 0x{opcode:04X} ({name})")
    
    return level, reasons


def _count_dependents(bhav) -> int:
    """Count how many other BHAVs call this one."""
    # This would require EngineToolkit or scanning all BHAVs
    # For now, return 0 (requires integration with semantic DB)
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# EDIT GATE
# ─────────────────────────────────────────────────────────────────────────────

class EditGate:
    """
    Gate keeper for edit operations.
    
    Usage:
        gate = EditGate(chunk, file_path)
        if gate.requires_confirmation:
            if not user_confirmed(gate.warning):
                return
        if gate.is_blocked:
            show_error(gate.block_reason)
            return
        # proceed with edit
    """
    
    def __init__(self, chunk: Any, file_path: Optional[str] = None):
        self.result = is_safe_to_edit(chunk, file_path)
    
    @property
    def is_blocked(self) -> bool:
        return not self.result.can_proceed
    
    @property
    def block_reason(self) -> str:
        return self.result.reasons[0] if self.result.reasons else "Edit blocked"
    
    @property
    def requires_confirmation(self) -> bool:
        return self.result.level in (SafetyLevel.WARNING, SafetyLevel.DANGEROUS)
    
    @property
    def warning(self) -> str:
        return self.result.summary()
    
    @property
    def scope_info(self) -> str:
        return f"Scope: {self.result.scope.value}"
    
    @property
    def owner_info(self) -> str:
        return f"Owner: {self.result.owner.value}"
