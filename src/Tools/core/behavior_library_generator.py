"""
BEHAVIOR LIBRARY GENERATOR
Produces comprehensive behavior library documentation from classified behaviors.
"""

from typing import Dict, List

# Import from core package
from .behavior_profiler import BehaviorProfiler, BehaviorProfile
from .behavior_classifier import BehaviorClassifier, BehaviorClass, ClassificationResult


class BehaviorLibraryGenerator:
    """Generate behavior library documentation and analysis."""
    
    def __init__(self, profiler: BehaviorProfiler, classifier: BehaviorClassifier):
        self.profiler = profiler
        self.classifier = classifier
    
    def generate_index(self) -> str:
        """Generate an index of all behaviors organized by class."""
        lines = []
        lines.append("# Behavior Library Index\n")
        lines.append("Organized classification of all game behaviors.\n")
        
        index = self.classifier.generate_library_index()
        
        for bclass in [BehaviorClass.ROLE, BehaviorClass.ACTION, BehaviorClass.GUARD, BehaviorClass.FLOW, BehaviorClass.UTILITY]:
            results = index[bclass]
            if not results:
                continue
            
            lines.append(f"\n## {bclass.value} Behaviors ({len(results)})\n")
            lines.append(f"{self._get_class_description(bclass)}\n")
            lines.append("| BHAV ID | Owner | Instructions | Confidence | Summary |\n")
            lines.append("|---------|-------|--------------|------------|----------|\n")
            
            for result in results:
                profile = self.profiler.get_profile(result.bhav_id)
                if not profile:
                    continue
                
                conf_pct = int(result.confidence * 100)
                summary = profile.summary()
                lines.append(f"| {result.bhav_id} | {profile.owner_iff} | {profile.instruction_count} | {conf_pct}% | {summary} |\n")
        
        # Unknown behaviors
        unknown_results = index[BehaviorClass.UNKNOWN]
        if unknown_results:
            lines.append(f"\n## UNKNOWN Behaviors ({len(unknown_results)})\n")
            lines.append("Behaviors that did not match any primary classification.\n")
            lines.append("| BHAV ID | Owner | Instructions | Reasons |\n")
            lines.append("|---------|-------|--------------|----------|\n")
            
            for result in unknown_results:
                profile = self.profiler.get_profile(result.bhav_id)
                if not profile:
                    continue
                
                reasons = "; ".join(result.reasons) if result.reasons else "No match"
                lines.append(f"| {result.bhav_id} | {profile.owner_iff} | {profile.instruction_count} | {reasons} |\n")
        
        return "".join(lines)
    
    def generate_statistics(self) -> Dict:
        """Generate comprehensive statistics on the behavior library."""
        
        profiler_stats = self.profiler.stats()
        classifier_stats = self.classifier.stats()
        
        # Additional analysis
        index = self.classifier.generate_library_index()
        
        high_conf = self.classifier.get_high_confidence_behaviors()
        
        stats = {
            'total_profiles': profiler_stats['total_profiles'],
            'files': profiler_stats['files'],
            'total_classified': classifier_stats['total_classified'],
            'classification_rate': classifier_stats['total_classified'] / max(profiler_stats['total_profiles'], 1) * 100,
            
            'role_count': classifier_stats['role_count'],
            'action_count': classifier_stats['action_count'],
            'guard_count': classifier_stats['guard_count'],
            'utility_count': classifier_stats['utility_count'],
            'unknown_count': classifier_stats['unknown_count'],
            
            'avg_confidence': classifier_stats['avg_confidence'],
            'high_confidence_pct': classifier_stats['high_confidence_pct'],
            'high_confidence_count': len(high_conf),
            
            'avg_inbound_calls': profiler_stats['avg_inbound_calls'],
            'avg_outbound_calls': profiler_stats['avg_outbound_calls'],
            'entry_points': profiler_stats['entry_points'],
            'with_loops': profiler_stats['with_loops'],
            'with_yields': profiler_stats['with_yields'],
            'with_issues': profiler_stats['with_issues'],
        }
        
        return stats
    
    def generate_summary(self) -> str:
        """Generate a text summary of the behavior library."""
        stats = self.generate_statistics()
        
        lines = []
        lines.append("BEHAVIOR LIBRARY SUMMARY\n")
        lines.append("=" * 70 + "\n\n")
        
        lines.append("PROFILING RESULTS:\n")
        lines.append(f"  Total behaviors profiled: {stats['total_profiles']}\n")
        lines.append(f"  Behaviors in {stats['files']} files\n")
        lines.append(f"  Classification rate: {stats['classification_rate']:.1f}%\n\n")
        
        lines.append("CLASSIFICATION BREAKDOWN:\n")
        lines.append(f"  ROLE:    {stats['role_count']:3d} ({stats['role_count']/max(stats['total_classified'], 1)*100:5.1f}%)\n")
        lines.append(f"  ACTION:  {stats['action_count']:3d} ({stats['action_count']/max(stats['total_classified'], 1)*100:5.1f}%)\n")
        lines.append(f"  GUARD:   {stats['guard_count']:3d} ({stats['guard_count']/max(stats['total_classified'], 1)*100:5.1f}%)\n")
        lines.append(f"  UTILITY: {stats['utility_count']:3d} ({stats['utility_count']/max(stats['total_classified'], 1)*100:5.1f}%)\n")
        lines.append(f"  UNKNOWN: {stats['unknown_count']:3d} ({stats['unknown_count']/max(stats['total_classified'], 1)*100:5.1f}%)\n\n")
        
        lines.append("CONFIDENCE METRICS:\n")
        lines.append(f"  Average confidence: {stats['avg_confidence']:.1%}\n")
        lines.append(f"  High confidence (>75%): {stats['high_confidence_pct']:.0f}% ({stats['high_confidence_count']} behaviors)\n\n")
        
        lines.append("BEHAVIOR CHARACTERISTICS:\n")
        lines.append(f"  Entry points: {stats['entry_points']}\n")
        lines.append(f"  With loops: {stats['with_loops']}\n")
        lines.append(f"  With yields: {stats['with_yields']}\n")
        lines.append(f"  With issues: {stats['with_issues']}\n")
        lines.append(f"  Avg inbound calls: {stats['avg_inbound_calls']:.1f}\n")
        lines.append(f"  Avg outbound calls: {stats['avg_outbound_calls']:.1f}\n")
        
        return "".join(lines)
    
    def _get_class_description(self, bclass: BehaviorClass) -> str:
        """Get the description for a behavior class."""
        descriptions = {
            BehaviorClass.ROLE: "**Long-running, identity-defining behaviors.** Start on object/Sim initialization, loop and yield to pause execution. Detect yield via opcode-based primitives. Examples: Idle, Conversation, Work.",
            BehaviorClass.ACTION: "**Transactional, finite behaviors.** Deterministic outcomes, called from TTAB or other behaviors. No loops. Examples: Sit, Pickup, Drop.",
            BehaviorClass.GUARD: "**Synchronous checks.** Short, reusable, return boolean-like results. Called by many other behaviors. Examples: Check idle, Check distance, Check object state.",
            BehaviorClass.FLOW: "**Decision and orchestration logic.** Medium complexity, delegates to other behaviors. Control glue that makes decisions and routes execution. Examples: Pick interaction, Decide next action, Route based on state.",
            BehaviorClass.UTILITY: "**Reusable pure logic.** No entry point, called by many behaviors. Stateless computation. Examples: Math helpers, State getters, Validators.",
        }
        return descriptions.get(bclass, "Unknown class")
    
    def find_similar_behaviors_by_class(self, target_class: BehaviorClass, max_results: int = 10) -> List[ClassificationResult]:
        """Find behaviors of a specific class with similar characteristics."""
        results = self.classifier.find_behaviors_by_class(target_class)
        return results[:max_results]
    
    def get_high_complexity_behaviors(self, min_instructions: int = 20) -> List[BehaviorProfile]:
        """Find complex behaviors (by instruction count)."""
        complex_behaviors = []
        for profile in self.profiler.profiles.values():
            if profile.instruction_count >= min_instructions:
                complex_behaviors.append(profile)
        
        complex_behaviors.sort(key=lambda p: p.instruction_count, reverse=True)
        return complex_behaviors
    
    def get_high_reuse_behaviors(self, min_inbound: int = 5) -> List[BehaviorProfile]:
        """Find highly reused behaviors."""
        reused = []
        for profile in self.profiler.profiles.values():
            if profile.inbound_count >= min_inbound:
                reused.append(profile)
        
        reused.sort(key=lambda p: p.inbound_count, reverse=True)
        return reused
    
    def export_markdown(self, filepath: str):
        """Export full behavior library as markdown."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_summary())
            f.write("\n\n")
            f.write(self.generate_index())
