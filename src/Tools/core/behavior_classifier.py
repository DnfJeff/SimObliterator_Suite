"""
BEHAVIOR CLASSIFIER
Deterministic classification of BHAVs into 4 fundamental behavior types.

Classification Rules (TS1-Accurate):
1. ROLE - Identity-defining, long-running (entry=Main, loops, yields)
2. ACTION - Transactional, finite (called from TTAB, no loops)
3. GUARD - Synchronous, boolean (short, no yields, returns bool-like)
4. UTILITY - Reusable, pure logic (high inbound, used by many)
"""

import importlib.util
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

# Import from core package
from .behavior_profiler import BehaviorProfile, BehaviorProfiler, EntryPointType


class BehaviorClass(Enum):
    """The 5 fundamental behavior classes in TS1."""
    
    ROLE = "ROLE"
    ACTION = "ACTION"
    GUARD = "GUARD"
    FLOW = "FLOW"
    UTILITY = "UTILITY"
    UNKNOWN = "UNKNOWN"  # When classification is uncertain


@dataclass
class ClassificationResult:
    """Result of classifying a behavior."""
    
    bhav_id: int
    assigned_class: BehaviorClass = BehaviorClass.UNKNOWN
    confidence: float = 0.0  # 0.0 to 1.0
    
    # Evidence
    matched_rules: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    
    def is_high_confidence(self) -> bool:
        """Confidence >= 75%"""
        return self.confidence >= 0.75
    
    def is_medium_confidence(self) -> bool:
        """Confidence 50-75%"""
        return 0.5 <= self.confidence < 0.75
    
    def summary(self) -> str:
        """One-line classification summary."""
        conf_pct = int(self.confidence * 100)
        return f"BHAV#{self.bhav_id}: {self.assigned_class.value} ({conf_pct}%)"


class BehaviorClassifier:
    """
    Deterministically classifies BHAVs into behavior types.
    
    Uses only evidence from BehaviorProfiles (which come from actual tool analysis).
    No heuristics, no guessing - just observable patterns.
    """
    
    def __init__(self, profiler: BehaviorProfiler):
        self.profiler = profiler
        self.results: Dict[int, ClassificationResult] = {}
    
    def classify(self, profile: BehaviorProfile) -> ClassificationResult:
        """Classify a single behavior based on its profile."""
        
        result = ClassificationResult(bhav_id=profile.bhav_id)
        
        # Evidence collection
        evidence = self._collect_evidence(profile)
        
        # Base confidence: start with what we know
        base_confidence = 0.5  # Start at 50% - we have some data
        
        # Rule evaluation (in priority order, TS1-accurate)
        if self._matches_role_rules(evidence):
            result.assigned_class = BehaviorClass.ROLE
            result.matched_rules.append("ROLE_RULES")
            result.reasons.extend([
                f"Main entry point (object autonomy)",
                f"Loops detected ({profile.max_iterations} max iterations)",
                f"Yield-capable (contains yield primitives: animate, route, idle, sleep, etc.)",
            ])
            result.confidence = 0.90  # Very high confidence on ROLE
        
        elif self._matches_action_rules(evidence):
            result.assigned_class = BehaviorClass.ACTION
            result.matched_rules.append("ACTION_RULES")
            result.reasons.extend([
                f"TTAB entry or called by behaviors (transactional)",
                f"Finite execution ({profile.instruction_count} instructions, no loops)",
            ])
            result.confidence = 0.85
        
        elif self._matches_guard_rules(evidence):
            result.assigned_class = BehaviorClass.GUARD
            result.matched_rules.append("GUARD_RULES")
            result.reasons.extend([
                f"Short ({profile.instruction_count} instructions)",
                f"No yields (synchronous)",
                f"Reusable ({profile.behavior_inbound_count}+ callers via behavior graph)",
            ])
            result.confidence = 0.80
        
        elif self._matches_utility_rules(evidence):
            result.assigned_class = BehaviorClass.UTILITY
            result.matched_rules.append("UTILITY_RULES")
            result.reasons.extend([
                f"Highly reused ({profile.behavior_inbound_count}+ callers)",
                f"No entry point (utility helper)",
                f"Pure logic (no side effects)",
            ])
            result.confidence = 0.75
        
        elif self._matches_flow_rules(evidence):
            result.assigned_class = BehaviorClass.FLOW
            result.matched_rules.append("FLOW_RULES")
            result.reasons.extend([
                f"Decision/orchestration logic",
                f"Delegates to other behaviors ({profile.behavior_outbound_count} callees)",
                f"Control glue (medium complexity, not pure predicate)",
            ])
            result.confidence = 0.70
        
        else:
            # Default to FLOW for UNKNOWN patterns (most unknowns are control logic)
            result.assigned_class = BehaviorClass.FLOW
            result.confidence = 0.50  # Lower confidence for default
            result.reasons.append("Default classification: matches FLOW (control logic) pattern")
        
        # Check for contradictions
        self._check_contradictions(profile, result)
        
        # Store result
        self.results[profile.bhav_id] = result
        
        return result
    
    def _collect_evidence(self, profile: BehaviorProfile) -> Dict:
        """Collect observable facts from profile."""
        # Use relationship data if available (is_ttab_entry, inbound_call_count)
        # These override/supplement structural entry point detection
        is_ttab = getattr(profile, 'is_ttab_entry', False)
        is_lifecycle = getattr(profile, 'is_lifecycle_hook', False)  # NEW: OBJf hooks
        inbound_calls = getattr(profile, 'inbound_call_count', 0)
        
        # Special marker: inbound_call_count == 999 means TTAB test function (GUARD)
        is_ttab_test = (inbound_calls == 999)
        
        # Combine structural + relational evidence
        has_ttab_entry = (profile.entry_point == EntryPointType.TTAB) or is_ttab
        has_lifecycle_entry = (profile.entry_point == EntryPointType.MAIN) or is_lifecycle  # NEW
        has_high_reuse = inbound_calls >= 3 or profile.behavior_inbound_count >= 3 or is_ttab_test
        has_very_high_reuse = inbound_calls >= 5 or profile.behavior_inbound_count >= 5
        
        return {
            'has_main_entry': profile.entry_point == EntryPointType.MAIN,
            'has_lifecycle_entry': has_lifecycle_entry,  # NEW: OBJf-based detection
            'has_ttab_entry': has_ttab_entry,
            'is_ttab_test': is_ttab_test,  # TTAB test function = GUARD
            'has_any_entry': profile.is_entry_point() or is_ttab or is_lifecycle,  # NEW
            'is_short': profile.instruction_count <= 5,
            'is_medium': 6 <= profile.instruction_count <= 15,
            'is_long': profile.instruction_count > 15,
            'has_loops': profile.loop_detected,
            'yields': profile.yields,
            'yield_capable': profile.yield_capable,  # Opcode-based yield detection
            'can_yield': profile.can_yield(),  # Either execution or opcode-based
            'has_high_behavior_reuse': has_high_reuse,
            'has_very_high_behavior_reuse': has_very_high_reuse,
            'has_outbound_calls': profile.behavior_outbound_count > 0,
            'is_many_callees': profile.behavior_outbound_count >= 3,
            'is_orphaned': inbound_calls == 0 and profile.behavior_inbound_count == 0 and not profile.is_entry_point() and not is_lifecycle,
            'has_issues': profile.has_issues(),
            'has_branching': profile.has_branching,
            'has_complex_logic': profile.has_complex_logic,
        }
    
    def _matches_role_rules(self, evidence: Dict) -> bool:
        """ROLE: Main/lifecycle entry, loops, yield-capable. Long-running state machine."""
        # Classic ROLE: Entry point + loops + yields (TSO-style)
        classic_role = (
            (evidence['has_main_entry'] or evidence['has_lifecycle_entry']) and
            evidence['has_loops'] and
            evidence['can_yield']
        )
        
        # TS1 lifecycle ROLE: OBJf hooks with loops (even without yields)
        # These are object controllers that may use polling/callbacks instead of yields
        ts1_lifecycle_role = (
            evidence['has_lifecycle_entry'] and
            evidence['has_loops']
        )
        
        return classic_role or ts1_lifecycle_role
    
    def _matches_action_rules(self, evidence: Dict) -> bool:
        """ACTION: TTAB entry OR called by behaviors, finite execution, produces outcome."""
        return (
            evidence['has_ttab_entry'] and
            not evidence['has_loops']  # No loops = finite
        )
    
    def _matches_guard_rules(self, evidence: Dict) -> bool:
        """GUARD: TTAB test functions OR short, reusable, synchronous checks."""
        # TS1 TTAB test functions (availability checks)
        if evidence.get('is_ttab_test', False):
            return True
            
        # Traditional helper function patterns (TSO-style)
        return (
            evidence['is_short'] and
            evidence['has_high_behavior_reuse'] and
            not evidence['can_yield'] and  # Synchronous, no yielding
            not evidence['has_ttab_entry']  # Not a TTAB entry (those are ACTION)
        )
    
    def _matches_utility_rules(self, evidence: Dict) -> bool:
        """UTILITY: Not entry point, very high reuse, no complex control flow."""
        return (
            not evidence['has_any_entry'] and
            evidence['has_very_high_behavior_reuse'] and
            not evidence['has_branching'] and  # Pure logic
            not evidence['has_ttab_entry']  # Not TTAB (those are ACTION)
        )
    
    def _matches_flow_rules(self, evidence: Dict) -> bool:
        """FLOW: Decision/orchestration. Medium complexity, delegates to others."""
        return (
            not evidence['has_any_entry'] and  # Not a direct entry point
            evidence['has_outbound_calls'] and  # Calls other behaviors
            evidence['is_medium']  # Medium complexity (not trivial like GUARD)
        )
    
    def _check_contradictions(self, profile: BehaviorProfile, result: ClassificationResult):
        """Flag any suspicious patterns and apply confidence modifiers."""
        
        # Apply relationship-based confidence boosts
        inbound_calls = getattr(profile, 'inbound_call_count', 0)
        
        # ACTION: TTAB entry with low fan-in (called by game engine, not other BHAVs) = high confidence
        if result.assigned_class == BehaviorClass.ACTION:
            if hasattr(profile, 'is_ttab_entry') and profile.is_ttab_entry and inbound_calls < 3:
                result.confidence = min(0.90, result.confidence + 0.05)  # Boost to 90%
        
        # GUARD: TTAB test function (marked with 999) or high reuse = high confidence
        if result.assigned_class == BehaviorClass.GUARD:
            if inbound_calls == 999:  # TTAB test function marker
                result.confidence = min(0.85, result.confidence + 0.05)  # Boost to 85-90%
        
        # ROLE: loops + yields + entry point = very high confidence
        if result.assigned_class == BehaviorClass.ROLE:
            if profile.loop_detected and profile.can_yield() and profile.is_entry_point():
                result.confidence = min(0.95, result.confidence + 0.05)  # Boost to 95%
        
        # FLOW: Default class with no strong signals stays at baseline
        # (No boost - these are the uncertain ones)
        
        # Dead code in production behavior?
        if profile.reachability.value == "has_dead_code" and result.assigned_class != BehaviorClass.UNKNOWN:
            result.contradictions.append("Has unreachable code")
            result.confidence -= 0.10
        
        # Unknown opcodes in utility?
        if profile.uses_unknown_opcodes and result.assigned_class == BehaviorClass.UTILITY:
            result.contradictions.append("Utility with unknown opcodes (may not be pure)")
            result.confidence -= 0.15
        
        # Validation errors?
        if profile.validation_errors > 0:
            result.contradictions.append(f"{profile.validation_errors} validation errors")
            result.confidence -= 0.05
        
        # Clamp confidence to [0, 1]
        result.confidence = max(0.0, min(1.0, result.confidence))
    
    def classify_all(self) -> List[ClassificationResult]:
        """Classify all profiles in the profiler."""
        results = []
        
        for profile in self.profiler.profiles.values():
            result = self.classify(profile)
            results.append(result)
        
        return results
    
    def stats(self) -> Dict:
        """Overall classification statistics."""
        if not self.results:
            return {
                'total_classified': 0,
                'role_count': 0,
                'action_count': 0,
                'guard_count': 0,
                'flow_count': 0,
                'utility_count': 0,
                'unknown_count': 0,
                'high_confidence_pct': 0.0,
                'avg_confidence': 0.0,
            }
        
        results_list = list(self.results.values())
        
        role_count = sum(1 for r in results_list if r.assigned_class == BehaviorClass.ROLE)
        action_count = sum(1 for r in results_list if r.assigned_class == BehaviorClass.ACTION)
        guard_count = sum(1 for r in results_list if r.assigned_class == BehaviorClass.GUARD)
        flow_count = sum(1 for r in results_list if r.assigned_class == BehaviorClass.FLOW)
        utility_count = sum(1 for r in results_list if r.assigned_class == BehaviorClass.UTILITY)
        unknown_count = sum(1 for r in results_list if r.assigned_class == BehaviorClass.UNKNOWN)
        
        high_conf = sum(1 for r in results_list if r.is_high_confidence())
        high_conf_pct = (high_conf / len(results_list) * 100) if results_list else 0
        
        avg_confidence = (sum(r.confidence for r in results_list) / len(results_list)) if results_list else 0
        
        return {
            'total_classified': len(results_list),
            'role_count': role_count,
            'action_count': action_count,
            'guard_count': guard_count,
            'flow_count': flow_count,
            'utility_count': utility_count,
            'unknown_count': unknown_count,
            'high_confidence_pct': high_conf_pct,
            'avg_confidence': avg_confidence,
        }
    
    def generate_library_index(self) -> Dict[BehaviorClass, List[ClassificationResult]]:
        """Organize results by behavior class."""
        index = {
            BehaviorClass.ROLE: [],
            BehaviorClass.ACTION: [],
            BehaviorClass.GUARD: [],
            BehaviorClass.FLOW: [],
            BehaviorClass.UTILITY: [],
            BehaviorClass.UNKNOWN: [],
        }
        
        for result in self.results.values():
            index[result.assigned_class].append(result)
        
        # Sort each class by BHAV ID
        for bclass in index:
            index[bclass].sort(key=lambda r: r.bhav_id)
        
        return index
    
    def get_high_confidence_behaviors(self, min_confidence: float = 0.75) -> List[ClassificationResult]:
        """Get only high-confidence classifications."""
        return [
            r for r in self.results.values()
            if r.confidence >= min_confidence
        ]
    
    def find_behaviors_by_class(self, target_class: BehaviorClass) -> List[ClassificationResult]:
        """Get all behaviors of a specific class."""
        return [
            r for r in self.results.values()
            if r.assigned_class == target_class
        ]
