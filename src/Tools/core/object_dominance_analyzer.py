"""
Object Dominance Analyzer - Phase 7
====================================

Per-object lifecycle analysis for mod development intelligence:
- Hook inventory (which lifecycle events are bound)
- Loop ownership (which ROLE controls execution)
- FLOW→ROLE coordination patterns
- Safe insertion points for mod code
- Conflict detection and compatibility analysis
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum

# Import from core package
from .behavior_profiler import BehaviorProfile
from .behavior_classifier import BehaviorClassifier, BehaviorClass, ClassificationResult
from .behavior_trigger_extractor import TriggerType, TriggerMap


class LifecycleEvent(Enum):
    """OBJf lifecycle event types."""
    INIT = 0      # Object creation/placement
    MAIN = 1      # Primary controller loop
    CLEANUP = 2   # Object deletion/removal
    LOAD = 3      # Restore from save file
    RESET = 4     # State reset


@dataclass
class LifecycleHook:
    """A single lifecycle hook binding."""
    event: LifecycleEvent
    bhav_id: int
    profile: BehaviorProfile
    classification: ClassificationResult
    has_loop: bool
    instruction_count: int
    yields: bool


@dataclass
class ObjectDominanceMap:
    """Complete dominance analysis for a single object."""
    object_name: str
    
    # Lifecycle hooks
    hooks: Dict[LifecycleEvent, LifecycleHook] = field(default_factory=dict)
    
    # ROLE behaviors (controllers)
    role_behaviors: List[Tuple[int, BehaviorProfile, ClassificationResult]] = field(default_factory=list)
    
    # FLOW behaviors (coordinators)
    flow_behaviors: List[Tuple[int, BehaviorProfile, ClassificationResult]] = field(default_factory=list)
    
    # ACTION behaviors (interactions)
    action_behaviors: List[Tuple[int, BehaviorProfile, ClassificationResult]] = field(default_factory=list)
    
    # GUARD behaviors (checks)
    guard_behaviors: List[Tuple[int, BehaviorProfile, ClassificationResult]] = field(default_factory=list)
    
    # Dominance analysis
    primary_controller: Optional[int] = None  # BHAV ID of loop owner
    loop_owners: List[int] = field(default_factory=list)  # All BHAVs with loops
    
    # TTAB interactions
    ttab_action_count: int = 0
    ttab_test_count: int = 0
    
    def get_safe_insertion_points(self) -> List[Tuple[int, str]]:
        """Identify safe points to inject mod code."""
        points = []
        
        # Primary controller (Main hook with loop) is safest
        if self.primary_controller:
            points.append((self.primary_controller, "Primary controller (Main loop) - SAFEST"))
        
        # Init hooks are safe for setup code
        if LifecycleEvent.INIT in self.hooks:
            hook = self.hooks[LifecycleEvent.INIT]
            points.append((hook.bhav_id, "Init hook - safe for setup/state initialization"))
        
        # Cleanup hooks for teardown
        if LifecycleEvent.CLEANUP in self.hooks:
            hook = self.hooks[LifecycleEvent.CLEANUP]
            points.append((hook.bhav_id, "Cleanup hook - safe for teardown/state cleanup"))
        
        return points
    
    def get_conflict_risks(self) -> List[str]:
        """Identify potential mod conflicts."""
        risks = []
        
        # Multiple loop owners = potential timing conflicts
        if len(self.loop_owners) > 1:
            risks.append(f"Multiple loop owners ({len(self.loop_owners)}) - timing conflicts possible")
        
        # FLOW coordinators = shared state dependencies
        if len(self.flow_behaviors) > 0:
            risks.append(f"{len(self.flow_behaviors)} FLOW coordinators - check state dependencies")
        
        # No Main hook = unusual architecture
        if LifecycleEvent.MAIN not in self.hooks:
            risks.append("No Main lifecycle hook - non-standard object architecture")
        
        return risks
    
    def calculate_dominance_score(self) -> float:
        """
        Calculate how "dominated" this object is by its primary controller.
        High score = single strong controller (easy to mod)
        Low score = distributed control (complex, risky to mod)
        """
        if not self.primary_controller:
            return 0.0
        
        score = 0.0
        
        # Main hook with loop = strong dominance
        if LifecycleEvent.MAIN in self.hooks and self.hooks[LifecycleEvent.MAIN].bhav_id == self.primary_controller:
            score += 50.0
        
        # Single loop owner = clear dominance
        if len(self.loop_owners) == 1:
            score += 30.0
        elif len(self.loop_owners) > 1:
            score += 10.0  # Distributed control
        
        # Few FLOW coordinators = simpler architecture
        if len(self.flow_behaviors) <= 2:
            score += 20.0
        elif len(self.flow_behaviors) <= 5:
            score += 10.0
        
        return min(score, 100.0)


class ObjectDominanceAnalyzer:
    """Analyzes per-object execution dominance for modding intelligence."""
    
    def __init__(self):
        self.dominance_maps: Dict[str, ObjectDominanceMap] = {}
    
    def analyze_object(
        self,
        object_name: str,
        profiles: Dict[int, BehaviorProfile],
        classifications: Dict[int, ClassificationResult],
        trigger_map: TriggerMap
    ) -> ObjectDominanceMap:
        """
        Build complete dominance map for an object.
        
        Args:
            object_name: Object filename
            profiles: All BHAV profiles for this object
            classifications: Classification results for each BHAV
            trigger_map: Trigger extraction results (TTAB/OBJf bindings)
        
        Returns:
            Complete dominance analysis
        """
        dom_map = ObjectDominanceMap(object_name=object_name)
        
        # Phase 1: Extract lifecycle hooks from trigger map
        # TriggerMap has explicit fields for lifecycle functions
        lifecycle_bindings = {
            LifecycleEvent.INIT: trigger_map.init_function,
            LifecycleEvent.MAIN: trigger_map.main_function,
            LifecycleEvent.CLEANUP: trigger_map.cleanup_function,
            LifecycleEvent.LOAD: trigger_map.load_function,
            LifecycleEvent.RESET: trigger_map.reset_function,
        }
        
        for event, bhav_id in lifecycle_bindings.items():
            if bhav_id and bhav_id > 0 and bhav_id in profiles:
                profile = profiles[bhav_id]
                # Try to get classification, default to None
                classification = classifications.get(bhav_id)
                if not classification:
                    # Create dummy classification if not available
                    classification = ClassificationResult(bhav_id=bhav_id)
                    classification.assigned_class = BehaviorClass.UNKNOWN
                
                hook = LifecycleHook(
                    event=event,
                    bhav_id=bhav_id,
                    profile=profile,
                    classification=classification,
                    has_loop=profile.loop_detected,
                    instruction_count=profile.instruction_count,
                    yields=profile.yields
                )
                dom_map.hooks[event] = hook
        
        # Phase 2: Categorize all behaviors by class
        for bhav_id, classification in classifications.items():
            if bhav_id not in profiles:
                continue
            
            profile = profiles[bhav_id]
            
            if classification.assigned_class == BehaviorClass.ROLE:
                dom_map.role_behaviors.append((bhav_id, profile, classification))
                if profile.loop_detected:
                    dom_map.loop_owners.append(bhav_id)
            elif classification.assigned_class == BehaviorClass.FLOW:
                dom_map.flow_behaviors.append((bhav_id, profile, classification))
            elif classification.assigned_class == BehaviorClass.ACTION:
                dom_map.action_behaviors.append((bhav_id, profile, classification))
            elif classification.assigned_class == BehaviorClass.GUARD:
                dom_map.guard_behaviors.append((bhav_id, profile, classification))
        
        # Phase 3: Identify primary controller
        dom_map.primary_controller = self._identify_primary_controller(dom_map)
        
        # Phase 4: Store TTAB statistics
        dom_map.ttab_action_count = trigger_map.ttab_action_count
        dom_map.ttab_test_count = trigger_map.ttab_test_count
        
        # Cache the map
        self.dominance_maps[object_name] = dom_map
        
        return dom_map
    
    def _trigger_to_event(self, trigger: TriggerType) -> LifecycleEvent:
        """Convert trigger type to lifecycle event."""
        mapping = {
            TriggerType.LIFECYCLE_INIT: LifecycleEvent.INIT,
            TriggerType.LIFECYCLE_MAIN: LifecycleEvent.MAIN,
            TriggerType.LIFECYCLE_CLEANUP: LifecycleEvent.CLEANUP,
            TriggerType.LIFECYCLE_LOAD: LifecycleEvent.LOAD,
            TriggerType.LIFECYCLE_RESET: LifecycleEvent.RESET,
        }
        return mapping.get(trigger, LifecycleEvent.MAIN)
    
    def _identify_primary_controller(self, dom_map: ObjectDominanceMap) -> Optional[int]:
        """
        Identify the primary controller BHAV.
        
        Priority:
        1. Main lifecycle hook with loop (THE primary controller)
        2. Any lifecycle hook with loop
        3. Any ROLE with loop
        4. Main lifecycle hook (even without loop)
        """
        # Priority 1: Main hook with loop
        if LifecycleEvent.MAIN in dom_map.hooks:
            main_hook = dom_map.hooks[LifecycleEvent.MAIN]
            if main_hook.has_loop:
                return main_hook.bhav_id
        
        # Priority 2: Any lifecycle hook with loop
        for hook in dom_map.hooks.values():
            if hook.has_loop:
                return hook.bhav_id
        
        # Priority 3: Any ROLE with loop
        for bhav_id, profile, _ in dom_map.role_behaviors:
            if profile.loop_detected:
                return bhav_id
        
        # Priority 4: Main hook without loop
        if LifecycleEvent.MAIN in dom_map.hooks:
            return dom_map.hooks[LifecycleEvent.MAIN].bhav_id
        
        return None
    
    def generate_object_report(self, object_name: str) -> str:
        """Generate human-readable report for a single object."""
        if object_name not in self.dominance_maps:
            return f"No dominance map found for {object_name}"
        
        dom_map = self.dominance_maps[object_name]
        lines = []
        
        # Header
        lines.append(f"\n{'='*80}")
        lines.append(f"OBJECT: {object_name}")
        lines.append(f"{'='*80}\n")
        
        # Lifecycle hooks
        lines.append("LIFECYCLE HOOKS:")
        if dom_map.hooks:
            for event in [LifecycleEvent.INIT, LifecycleEvent.MAIN, LifecycleEvent.CLEANUP, 
                         LifecycleEvent.LOAD, LifecycleEvent.RESET]:
                if event in dom_map.hooks:
                    hook = dom_map.hooks[event]
                    controller_marker = " <- PRIMARY CONTROLLER" if hook.bhav_id == dom_map.primary_controller else ""
                    loop_marker = " [LOOP]" if hook.has_loop else ""
                    yield_marker = " [YIELDS]" if hook.yields else ""
                    lines.append(f"  {event.name:8} : BHAV#{hook.bhav_id} ({hook.instruction_count} insts{loop_marker}{yield_marker}){controller_marker}")
        else:
            lines.append("  (none)")
        
        # Dominance score
        score = dom_map.calculate_dominance_score()
        lines.append(f"\nDOMINANCE SCORE: {score:.0f}/100")
        if score >= 80:
            lines.append("  [+] Strong single controller - EASY TO MOD")
        elif score >= 50:
            lines.append("  [!] Moderate control - MOD WITH CARE")
        else:
            lines.append("  [-] Distributed control - COMPLEX MOD TARGET")
        
        # ROLE behaviors
        lines.append(f"\nROLE BEHAVIORS ({len(dom_map.role_behaviors)}):")
        if dom_map.role_behaviors:
            for bhav_id, profile, classification in dom_map.role_behaviors[:5]:  # Top 5
                loop_marker = " [LOOP]" if profile.loop_detected else ""
                confidence = f"{classification.confidence:.0%}"
                lines.append(f"  BHAV#{bhav_id}: {profile.instruction_count} insts{loop_marker} (conf: {confidence})")
        
        # FLOW coordinators
        lines.append(f"\nFLOW COORDINATORS ({len(dom_map.flow_behaviors)}):")
        if dom_map.flow_behaviors:
            for bhav_id, profile, _ in dom_map.flow_behaviors[:5]:  # Top 5
                lines.append(f"  BHAV#{bhav_id}: {profile.instruction_count} insts - routes state/events")
        
        # TTAB interactions
        if dom_map.ttab_action_count > 0 or dom_map.ttab_test_count > 0:
            lines.append(f"\nTTAB INTERACTIONS:")
            lines.append(f"  Actions: {dom_map.ttab_action_count}")
            lines.append(f"  Tests: {dom_map.ttab_test_count}")
        
        # Safe insertion points
        insertion_points = dom_map.get_safe_insertion_points()
        if insertion_points:
            lines.append(f"\nSAFE INSERTION POINTS:")
            for bhav_id, reason in insertion_points:
                lines.append(f"  [OK] BHAV#{bhav_id}: {reason}")
        
        # Conflict risks
        risks = dom_map.get_conflict_risks()
        if risks:
            lines.append(f"\nCONFLICT RISKS:")
            for risk in risks:
                lines.append(f"  [!] {risk}")
        
        lines.append("")
        return "\n".join(lines)
    
    def generate_role_trigger_matrix(self) -> str:
        """Generate a ROLE -> Trigger Matrix showing which OBJf events bind ROLEs."""
        lines = []
        lines.append("\n" + "="*120)
        lines.append("ROLE -> TRIGGER MATRIX: Which OBJf Events Bind ROLE Controllers")
        lines.append("="*120)
        
        # Header row
        lines.append(f"\n{'OBJECT':<25} {'ROLE BHAV':<12} {'INIT':<10} {'MAIN':<10} {'CLEANUP':<10} {'LOAD':<10} {'RESET':<10} {'EXEC MODEL':<15} {'TTAB EXP?':<10} {'PATTERN':<15}")
        lines.append("-" * 120)
        
        pure_dominance_count = 0
        
        for object_name in sorted(self.dominance_maps.keys()):
            dom_map = self.dominance_maps[object_name]
            
            if not dom_map.primary_controller:
                continue  # Skip objects with no primary controller
            
            role_bhav = dom_map.primary_controller
            
            # Check which lifecycle events bind this ROLE
            init_bound = "[X] INIT" if LifecycleEvent.INIT in dom_map.hooks and dom_map.hooks[LifecycleEvent.INIT].bhav_id == role_bhav else ""
            main_bound = "[X] MAIN" if LifecycleEvent.MAIN in dom_map.hooks and dom_map.hooks[LifecycleEvent.MAIN].bhav_id == role_bhav else ""
            cleanup_bound = "[X] CLNP" if LifecycleEvent.CLEANUP in dom_map.hooks and dom_map.hooks[LifecycleEvent.CLEANUP].bhav_id == role_bhav else ""
            load_bound = "[X] LOAD" if LifecycleEvent.LOAD in dom_map.hooks and dom_map.hooks[LifecycleEvent.LOAD].bhav_id == role_bhav else ""
            reset_bound = "[X] RSET" if LifecycleEvent.RESET in dom_map.hooks and dom_map.hooks[LifecycleEvent.RESET].bhav_id == role_bhav else ""
            
            # Check if ROLE yields
            main_hook = dom_map.hooks.get(LifecycleEvent.MAIN)
            exec_model = "COOPERATIVE" if main_hook and main_hook.yields else "POLLING"
            
            # Check if ROLE exposes TTAB actions indirectly
            ttab_exposed = "YES" if dom_map.ttab_action_count > 0 else "NO"
            
            # Determine pattern complexity
            hook_count = len(dom_map.hooks)
            loop_owner_count = len(dom_map.loop_owners)
            has_delegation = any(hook.bhav_id != role_bhav for hook in dom_map.hooks.values())
            
            if hook_count == 1 and loop_owner_count == 1 and not has_delegation and dom_map.ttab_action_count == 0:
                pattern = "PURE"
                pure_dominance_count += 1
            elif has_delegation:
                pattern = "DELEGATED"
            elif loop_owner_count > 1:
                pattern = "SHARED"
            elif dom_map.ttab_action_count > 0:
                pattern = "UI-EXPOSED"
            else:
                pattern = "COMPLEX"
            
            lines.append(f"{object_name:<25} BHAV#{role_bhav:<8} {init_bound:<10} {main_bound:<10} {cleanup_bound:<10} {load_bound:<10} {reset_bound:<10} {exec_model:<15} {ttab_exposed:<10} {pattern:<15}")
        
        lines.append("-" * 120)
        lines.append(f"\nPURE DOMINANCE CASES: {pure_dominance_count}/{len(self.dominance_maps)}")
        lines.append("  These are the cleanest implementations with single ROLE exclusive control.")
        lines.append("  Perfect candidates for safe ROLE injection and mod hooks.")
        
        lines.append("\nLegend:")
        lines.append("  [X] INIT   = ROLE also handles object initialization")
        lines.append("  [X] MAIN   = ROLE is primary controller (main loop)")
        lines.append("  [X] CLNP   = ROLE also handles cleanup on deletion")
        lines.append("  [X] LOAD   = ROLE handles save/load restoration")
        lines.append("  [X] RSET   = ROLE handles state reset")
        lines.append("")
        lines.append("  EXECUTION MODEL:")
        lines.append("    - POLLING       = Non-yielding loop (continuous execution)")
        lines.append("    - COOPERATIVE   = Yields during execution (engine-managed scheduling)")
        lines.append("")
        lines.append("  PATTERN:")
        lines.append("    - PURE       = Single ROLE, single MAIN, no delegation, no TTAB exposure (safest for mods)")
        lines.append("    - DELEGATED  = ROLE delegates to other BHAVs in lifecycle")
        lines.append("    - SHARED     = Multiple ROLE candidates compete for control")
        lines.append("    - UI-EXPOSED = ROLE indirectly exposes TTAB actions (can be interacted with)")
        lines.append("    - COMPLEX    = Other patterns (requires detailed analysis)")
        
        return "\n".join(lines)
    
    def generate_summary_report(self) -> str:
        """Generate game-wide summary of dominance patterns."""
        lines = []
        
        lines.append(f"\n{'='*80}")
        lines.append("GAME-WIDE DOMINANCE ANALYSIS")
        lines.append(f"{'='*80}\n")
        
        # Statistics
        total_objects = len(self.dominance_maps)
        objects_with_main = sum(1 for dm in self.dominance_maps.values() if LifecycleEvent.MAIN in dm.hooks)
        objects_with_controller = sum(1 for dm in self.dominance_maps.values() if dm.primary_controller)
        
        avg_dominance = sum(dm.calculate_dominance_score() for dm in self.dominance_maps.values()) / total_objects if total_objects > 0 else 0
        
        lines.append(f"Total objects analyzed: {total_objects}")
        lines.append(f"Objects with Main hook: {objects_with_main} ({objects_with_main/total_objects*100:.1f}%)")
        lines.append(f"Objects with primary controller: {objects_with_controller} ({objects_with_controller/total_objects*100:.1f}%)")
        lines.append(f"Average dominance score: {avg_dominance:.1f}/100")
        
        # Categorize by moddability
        easy_mod = sum(1 for dm in self.dominance_maps.values() if dm.calculate_dominance_score() >= 80)
        moderate_mod = sum(1 for dm in self.dominance_maps.values() if 50 <= dm.calculate_dominance_score() < 80)
        complex_mod = sum(1 for dm in self.dominance_maps.values() if dm.calculate_dominance_score() < 50)
        
        lines.append(f"\nMODDABILITY CLASSIFICATION:")
        lines.append(f"  [+] Easy to mod: {easy_mod} ({easy_mod/total_objects*100:.1f}%)")
        lines.append(f"  [!] Moderate complexity: {moderate_mod} ({moderate_mod/total_objects*100:.1f}%)")
        lines.append(f"  [-] Complex/risky: {complex_mod} ({complex_mod/total_objects*100:.1f}%)")
        
        # Architecture patterns
        lines.append(f"\nARCHITECTURE PATTERNS:")
        single_loop = sum(1 for dm in self.dominance_maps.values() if len(dm.loop_owners) == 1)
        multi_loop = sum(1 for dm in self.dominance_maps.values() if len(dm.loop_owners) > 1)
        no_loop = sum(1 for dm in self.dominance_maps.values() if len(dm.loop_owners) == 0)
        
        lines.append(f"  Single loop owner: {single_loop} ({single_loop/total_objects*100:.1f}%)")
        lines.append(f"  Multiple loop owners: {multi_loop} ({multi_loop/total_objects*100:.1f}%)")
        lines.append(f"  No loops: {no_loop} ({no_loop/total_objects*100:.1f}%)")
        
        lines.append("")
        return "\n".join(lines)
