"""
BEHAVIOR PROFILER
Generates BehaviorProfiles for all BHAVs using existing tools.

A BehaviorProfile is a complete behavioral signature containing:
- Identity (BHAV ID, owner, scope)
- Structure (entry point, instruction count, reachability)
- Dynamics (yields, loops, max iterations)
- Relationships (callers, callees)
- Quality (unknown opcodes, validation errors)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from pathlib import Path


class BehaviorScope(Enum):
    """Scope of a BHAV (derived from owner)."""
    OBJECT = "OBJECT"
    SEMI_GLOBAL = "SEMI_GLOBAL"
    GLOBAL = "GLOBAL"


class EntryPointType(Enum):
    """How a BHAV can be called."""
    MAIN = "Main"
    TTAB = "TTAB"
    OTHER = "Other"
    NONE = "None"


class Reachability(Enum):
    """Code reachability status."""
    FULLY_REACHABLE = "fully_reachable"
    HAS_DEAD_CODE = "has_dead_code"
    UNREACHABLE = "unreachable"


# TS1 Yield-Capable Opcodes (primitives that pause execution)
# These are opcode ranges that indicate the BHAV can yield control back to scheduler
YIELD_CAPABLE_OPCODES = {
    # Animation primitives (0x0030-0x003F range estimated)
    0x0030, 0x0032, 0x003C,  # Animation/pose related
    
    # Routing primitives (0x0040-0x004F range)
    0x004D,  # Likely routing
    
    # Idle/Wait primitives (0x0050-0x005F range)
    0x005D,  # Wait/idle
    
    # Sleep primitives
    0x006E,  # Sleep
    
    # Interaction queue primitives (0x0100-0x01FF)
    0x0118,  # Push interaction (yields while executing)
    0x0119,  # Similar interaction operations
    
    # Audio/speech primitives that yield
    0x0154, 0x0156,  # Speech/animation
}

# Commonly found in complex behaviors
FLOW_CHARACTERISTIC_OPCODES = {
    # Decision-making, branching
    0x0004,  # Test condition
    0x0006,  # If/else
    0x001D,  # Switch/case
}


@dataclass
class BehaviorProfile:
    """Complete behavioral signature for one BHAV."""
    
    # Identity
    bhav_id: int
    owner_iff: str  # "AlarmClock.iff"
    owner_object_id: Optional[int] = None  # OBJD ID if OBJECT scope
    
    # Scope
    scope: BehaviorScope = BehaviorScope.OBJECT
    entry_point: EntryPointType = EntryPointType.NONE
    
    # Structure (from disassembler)
    instruction_count: int = 0
    uses_unknown_opcodes: bool = False
    unknown_opcode_list: List[str] = field(default_factory=list)
    stack_push: int = 0  # Max stack depth needed
    stack_pop: int = 0   # Items produced
    
    # Dynamics (from executor)
    yields: bool = False  # Has pause points (execution-based)
    yield_capable: bool = False  # Contains yield-capable primitives (opcode-based)
    loop_detected: bool = False
    max_iterations: int = 0  # For looping behaviors
    
    # Relationships (from graph)
    inbound_callers: List[str] = field(default_factory=list)  # [BHAV#ID, OBJD#ID, etc]
    inbound_count: int = 0
    outbound_calls: List[str] = field(default_factory=list)  # [BHAV#ID, ...]
    outbound_count: int = 0
    
    # Behavior call graph (more accurate than resource graph)
    behavior_inbound_callers: List[str] = field(default_factory=list)  # Via TTAB, Main, Push
    behavior_inbound_count: int = 0
    behavior_outbound_calls: List[str] = field(default_factory=list)
    behavior_outbound_count: int = 0
    
    # Reachability (from dead code finder)
    reachability: Reachability = Reachability.FULLY_REACHABLE
    
    # Quality (from validator)
    validation_errors: int = 0
    validation_warnings: int = 0
    scope_violations: int = 0
    
    # Characteristics for FLOW detection
    has_branching: bool = False
    has_complex_logic: bool = False
    
    # Relationship signals (for ACTION/GUARD/UTILITY splitting)
    is_ttab_entry: bool = False  # Referenced by TTAB interaction entry
    inbound_call_count: int = 0  # Count of 0x0004 (Push Interaction) calls to this BHAV
    
    def __post_init__(self):
        """Validate profile integrity."""
        self.inbound_count = len(self.inbound_callers)
        self.outbound_count = len(self.outbound_calls)
        self.behavior_inbound_count = len(self.behavior_inbound_callers)
        self.behavior_outbound_count = len(self.behavior_outbound_calls)
    
    def complexity_score(self) -> int:
        """Simple complexity metric: instruction count."""
        return self.instruction_count
    
    def reuse_score(self) -> int:
        """How many behaviors call this one (via behavior call graph)."""
        return self.behavior_inbound_count
    
    def is_entry_point(self) -> bool:
        """Is this a main entry (not called by other BHAVs)."""
        return self.entry_point in (EntryPointType.MAIN, EntryPointType.TTAB)
    
    def can_yield(self) -> bool:
        """Can this behavior yield (either detected or capable)."""
        return self.yields or self.yield_capable
    
    def has_issues(self) -> bool:
        """Any validation problems."""
        return (self.validation_errors > 0 or 
                self.scope_violations > 0 or
                self.uses_unknown_opcodes or
                self.reachability == Reachability.HAS_DEAD_CODE)
    
    def summary(self) -> str:
        """One-line summary of the behavior."""
        parts = []
        
        if self.entry_point != EntryPointType.NONE:
            parts.append(f"Entry:{self.entry_point.value}")
        
        if self.loop_detected:
            parts.append(f"Loop(max={self.max_iterations})")
        
        if self.can_yield():
            parts.append("Yields")
        
        if self.behavior_inbound_count > 0 or self.behavior_outbound_count > 0:
            parts.append(f"{self.behavior_inbound_count}→{self.behavior_outbound_count}")
        
        return f"[BHAV#{self.bhav_id}] {' '.join(parts)}"


class BehaviorProfiler:
    """
    Generates BehaviorProfiles for all BHAVs.
    
    Consumes data from:
    - BHAVDisassembler (instruction data)
    - BHAVExecutor (loop/yield data)
    - ResourceGraph (caller/callee relationships)
    - ScopeValidator (validation errors)
    - DeadCodeFinder (reachability)
    """
    
    def __init__(self):
        self.profiles: Dict[int, BehaviorProfile] = {}
        self.profiles_by_owner: Dict[str, List[int]] = {}
    
    def create_profile(
        self,
        bhav_id: int,
        owner_iff: str,
        owner_object_id: Optional[int] = None,
        scope: BehaviorScope = BehaviorScope.OBJECT,
        entry_point: EntryPointType = EntryPointType.NONE,
        instruction_count: int = 0,
        yields: bool = False,
        yield_capable: bool = False,
        loop_detected: bool = False,
        max_iterations: int = 0,
        inbound_callers: Optional[List[str]] = None,
        outbound_calls: Optional[List[str]] = None,
        behavior_inbound_callers: Optional[List[str]] = None,
        behavior_outbound_calls: Optional[List[str]] = None,
        uses_unknown_opcodes: bool = False,
        unknown_opcode_list: Optional[List[str]] = None,
        reachability: Reachability = Reachability.FULLY_REACHABLE,
        validation_errors: int = 0,
        validation_warnings: int = 0,
        scope_violations: int = 0,
        stack_push: int = 0,
        stack_pop: int = 0,
        has_branching: bool = False,
        has_complex_logic: bool = False,
    ) -> BehaviorProfile:
        """Create a behavior profile with all required data."""
        
        profile = BehaviorProfile(
            bhav_id=bhav_id,
            owner_iff=owner_iff,
            owner_object_id=owner_object_id,
            scope=scope,
            entry_point=entry_point,
            instruction_count=instruction_count,
            yields=yields,
            yield_capable=yield_capable,
            loop_detected=loop_detected,
            max_iterations=max_iterations,
            inbound_callers=inbound_callers or [],
            outbound_calls=outbound_calls or [],
            behavior_inbound_callers=behavior_inbound_callers or [],
            behavior_outbound_calls=behavior_outbound_calls or [],
            uses_unknown_opcodes=uses_unknown_opcodes,
            unknown_opcode_list=unknown_opcode_list or [],
            reachability=reachability,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            scope_violations=scope_violations,
            stack_push=stack_push,
            stack_pop=stack_pop,
            has_branching=has_branching,
            has_complex_logic=has_complex_logic,
        )
        
        self.profiles[bhav_id] = profile
        
        # Index by owner
        if owner_iff not in self.profiles_by_owner:
            self.profiles_by_owner[owner_iff] = []
        self.profiles_by_owner[owner_iff].append(bhav_id)
        
        return profile
    
    def get_profile(self, bhav_id: int) -> Optional[BehaviorProfile]:
        """Retrieve a profile by BHAV ID."""
        return self.profiles.get(bhav_id)
    
    def get_profiles_by_owner(self, owner_iff: str) -> List[BehaviorProfile]:
        """Get all profiles for a specific IFF file."""
        ids = self.profiles_by_owner.get(owner_iff, [])
        return [self.profiles[bid] for bid in ids]
    
    def stats(self) -> Dict:
        """Overall statistics on all profiles."""
        if not self.profiles:
            return {
                'total_profiles': 0,
                'files': 0,
            }
        
        profiles_list = list(self.profiles.values())
        
        entry_points = sum(1 for p in profiles_list if p.is_entry_point())
        with_loops = sum(1 for p in profiles_list if p.loop_detected)
        with_yields = sum(1 for p in profiles_list if p.can_yield())  # Use can_yield() for both execution and opcode-based
        with_yield_capable = sum(1 for p in profiles_list if p.yield_capable)
        with_issues = sum(1 for p in profiles_list if p.has_issues())
        highly_reused = sum(1 for p in profiles_list if p.behavior_inbound_count > 2)
        
        # Calculate average calls, filtering out GUARD markers (inbound_call_count=999)
        real_inbound = [p.inbound_call_count for p in profiles_list if p.inbound_call_count < 999]
        avg_inbound = sum(real_inbound) / len(real_inbound) if real_inbound else 0.0
        
        return {
            'total_profiles': len(self.profiles),
            'files': len(self.profiles_by_owner),
            'entry_points': entry_points,
            'with_loops': with_loops,
            'with_yields': with_yields,
            'with_yield_capable': with_yield_capable,
            'with_issues': with_issues,
            'highly_reused': highly_reused,
            'avg_inbound_calls': avg_inbound,
            'avg_outbound_calls': sum(p.behavior_outbound_count for p in profiles_list) / len(profiles_list),
        }
    
    def find_similar_behaviors(self, bhav_id: int, max_results: int = 5) -> List[Tuple[int, float]]:
        """Find behaviors with similar profiles (simple: same instruction count range)."""
        profile = self.profiles.get(bhav_id)
        if not profile:
            return []
        
        target_count = profile.instruction_count
        similar = []
        
        for bid, p in self.profiles.items():
            if bid == bhav_id:
                continue
            
            # Simple similarity: instruction count within 30%
            if abs(p.instruction_count - target_count) <= max(target_count * 0.3, 2):
                similarity = 1.0 - (abs(p.instruction_count - target_count) / max(target_count, 1))
                similar.append((bid, similarity))
        
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar[:max_results]
