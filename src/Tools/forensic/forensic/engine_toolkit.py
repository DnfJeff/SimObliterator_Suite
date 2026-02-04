"""
Sims Engine Analysis Toolkit - Unified interface to all ghost globals research tools

This toolkit provides:
1. Semantic Global Resolution - Label calls by meaning, not raw ID
2. Expansion-Aware Diffing - Compare behaviors across expansions
3. Stable Hook Registry - Mod hooks that work on any expansion
4. Save State Analysis - Identify safe vs dangerous modifications
5. FreeSO Parity Gaps - Enumerate missing implementations

Usage:
    from engine_toolkit import EngineToolkit
    
    tk = EngineToolkit()
    
    # Label a global call semantically
    label = tk.label_global(1800)  # "SS::test_user_interrupt"
    
    # Check if save edit is safe
    safe, warnings = tk.is_safe_to_edit([256, 1800, 2585])
    
    # Register mod hook at stable offset
    tk.register_hook(0x19, my_handler)  # Works across all expansions
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass

# Import all our research tools
from .semantic_globals import (
    SemanticGlobalResolver,
    ExpansionBlock,
    EXPANSION_NAMES,
    GlobalInfo,
    ExpansionAwareDiffer,
    StableHookRegistry,
    FreeSoParityChecker
)

from .save_state_analyzer import (
    SaveStateAnalyzer,
    StateCategory,
    TransitionType,
    EngineStateModel,
    ZombieModHookPoints
)

from .graph_labeler import (
    BehaviorGraphLabeler,
    ExpansionBehaviorDiffer,
    GraphNode,
    NodeType
)

try:
    from .freeso_gap_analyzer import (
        FreeSoGapAnalyzer,
        ParityGap,
        ImplementationPriority
    )
except Exception:
    FreeSoGapAnalyzer = None
    ParityGap = None
    ImplementationPriority = None


@dataclass
class ToolkitConfig:
    """Configuration for the toolkit"""
    scan_data_path: Optional[Path] = None
    global_database_path: Optional[Path] = None
    verbose: bool = False


class EngineToolkit:
    """
    Unified interface to all Sims engine analysis tools.
    
    Built on the Ghost Globals research discovery that:
    - Global IDs 512-4095 include engine-internal functions
    - Same function offset appears across all expansion blocks
    - FreeSO needs 200 missing implementations
    """
    
    def __init__(self, config: Optional[ToolkitConfig] = None):
        self.config = config or ToolkitConfig()
        
        # Initialize all subsystems
        self.resolver = SemanticGlobalResolver()
        self.labeler = BehaviorGraphLabeler(self.resolver)
        self.differ = ExpansionBehaviorDiffer(self.labeler)
        self.hooks = StableHookRegistry(self.resolver)
        self.save_analyzer = SaveStateAnalyzer()
        self.state_model = EngineStateModel()
        
        # Load data if available
        if FreeSoGapAnalyzer is not None:
            if self.config.scan_data_path:
                self.gap_analyzer = FreeSoGapAnalyzer(self.config.scan_data_path)
            else:
                self.gap_analyzer = FreeSoGapAnalyzer()
        else:
            self.gap_analyzer = None
    
    # === Semantic Resolution ===
    
    def label_global(self, global_id: int) -> str:
        """Get semantic label for a global ID"""
        return self.resolver.get_semantic_name(global_id)
    
    def resolve_global(self, global_id: int) -> GlobalInfo:
        """Get full resolution info for a global ID"""
        return self.resolver.resolve(global_id)
    
    def get_stable_offset(self, global_id: int) -> int:
        """Get the stable function offset (for cross-expansion compatibility)"""
        return self.resolver.get_stable_offset(global_id)
    
    def find_equivalents(self, global_id: int) -> Dict[ExpansionBlock, int]:
        """Find equivalent function IDs across all expansions"""
        return self.resolver.find_equivalent_across_expansions(global_id)
    
    # === Graph Labeling ===
    
    def create_node(self, opcode: int, call_count: int = 0) -> GraphNode:
        """Create a labeled graph node for an opcode"""
        return self.labeler.create_node(opcode, call_count)
    
    def label_call_graph(self, calls: Dict[int, List[int]]) -> Dict[str, GraphNode]:
        """Label an entire call graph with semantic names"""
        return self.labeler.label_call_graph(calls)
    
    def generate_dot_graph(self, calls: Dict[int, List[int]], title: str = "") -> str:
        """Generate DOT format graph with semantic labels"""
        return self.labeler.generate_dot_graph(calls, title)
    
    # === Behavior Diffing ===
    
    def diff_behaviors(self, 
                       calls_a: List[int], 
                       calls_b: List[int],
                       name_a: str = "A",
                       name_b: str = "B") -> Dict:
        """Diff two behaviors, understanding expansion equivalence"""
        return self.differ.diff_behaviors(calls_a, calls_b, name_a, name_b)
    
    def are_semantically_equivalent(self, 
                                    calls_a: List[int], 
                                    calls_b: List[int]) -> bool:
        """Check if two behaviors are semantically the same"""
        diff = self.diff_behaviors(calls_a, calls_b)
        return diff["equivalent"]
    
    # === Modding Hooks ===
    
    def register_hook(self, offset: int, handler: Callable, name: str = None):
        """Register a mod hook at a stable function offset"""
        self.hooks.register_hook(offset, handler, name)
    
    def should_intercept(self, global_id: int) -> bool:
        """Check if a global call should be intercepted by hooks"""
        return self.hooks.should_intercept(global_id)
    
    def intercept_call(self, global_id: int, *args, **kwargs):
        """Intercept a global call if hooked"""
        return self.hooks.intercept(global_id, *args, **kwargs)
    
    def get_zombie_hooks(self) -> Dict[int, str]:
        """Get recommended hook points for zombie mod"""
        return ZombieModHookPoints.ZOMBIE_HOOKS
    
    def get_hook_globals(self, offset: int) -> List[int]:
        """Get all global IDs that correspond to a hook offset"""
        return ZombieModHookPoints.get_hook_globals(offset)
    
    # === Save Editing ===
    
    def analyze_save_safety(self, global_calls: List[int]) -> Dict:
        """Analyze save file modifications for safety"""
        return self.save_analyzer.analyze_bhav_calls(global_calls)
    
    def is_safe_to_edit(self, global_calls: List[int]) -> Tuple[bool, List[str]]:
        """Quick check if a behavior's state changes are safe to modify"""
        return self.save_analyzer.is_safe_to_modify(global_calls)
    
    def get_safe_state_fields(self) -> Dict[str, List[str]]:
        """Get all safely modifiable state fields"""
        return self.state_model.get_safe_modifications()
    
    def can_modify_state(self, category: str, field: str) -> Tuple[bool, str]:
        """Check if a specific state field can be safely modified"""
        return self.state_model.can_modify(category, field)
    
    # === FreeSO Parity ===
    
    def get_parity_gaps(self) -> List[ParityGap]:
        """Get all FreeSO parity gaps"""
        if self.gap_analyzer is None:
            return []
        return self.gap_analyzer.analyze_all_gaps()
    
    def get_critical_gaps(self) -> List[ParityGap]:
        """Get only critical priority gaps"""
        if ImplementationPriority is None:
            return []
        return [g for g in self.get_parity_gaps() 
                if getattr(g, 'priority', None) == ImplementationPriority.CRITICAL]
    
    def generate_implementation_plan(self) -> str:
        """Generate FreeSO implementation plan"""
        if self.gap_analyzer is None:
            return "No FreeSO gap analyzer available"
        return self.gap_analyzer.generate_implementation_plan()
    
    def generate_csharp_stubs(self) -> str:
        """Generate C# stub code for FreeSO"""
        if self.gap_analyzer is None:
            return ""
        return self.gap_analyzer.generate_csharp_stubs()
    
    # === Utilities ===
    
    def classify_opcode(self, opcode: int) -> str:
        """Classify what type of call an opcode represents"""
        return self.labeler.classify_opcode(opcode).value
    
    def is_engine_internal(self, global_id: int) -> bool:
        """Check if a global ID is engine-internal (ghost global)"""
        if global_id < 256 or global_id >= 4096:
            return False
        return self.resolve_global(global_id).is_engine_internal
    
    def get_expansion(self, global_id: int) -> str:
        """Get expansion name for a global ID"""
        info = self.resolve_global(global_id)
        return EXPANSION_NAMES.get(info.expansion, "Unknown")


# Convenience function for quick access
def create_toolkit(scan_data_path: str = None) -> EngineToolkit:
    """Create a toolkit instance with optional scan data"""
    config = ToolkitConfig()
    if scan_data_path:
        config.scan_data_path = Path(scan_data_path)
    return EngineToolkit(config)


# Demo
if __name__ == "__main__":
    print("=== Sims Engine Analysis Toolkit ===\n")
    
    # Create toolkit
    tk = create_toolkit(
        r"S:\Repositorys_New\SimObliterator_Private_Versions\Iff_Study\RELEASE\SimObliterator_Archiver\data\ULTIMATE_SCAN.json"
    )
    
    print("1. Semantic Resolution")
    print("-" * 40)
    test_ids = [264, 778, 1800, 2585]
    for gid in test_ids:
        label = tk.label_global(gid)
        offset = tk.get_stable_offset(gid)
        exp = tk.get_expansion(gid)
        internal = "ENGINE" if tk.is_engine_internal(gid) else "IFF"
        print(f"   {gid:5d}: {label:30s} offset=0x{offset:02X} [{internal}]")
    
    print("\n2. Expansion Equivalents")
    print("-" * 40)
    equiv = tk.find_equivalents(264)
    print(f"   Equivalents of 264 (test_user_interrupt):")
    for exp, gid in list(equiv.items())[:5]:
        print(f"      {EXPANSION_NAMES[exp]}: {gid}")
    
    print("\n3. Behavior Diff")
    print("-" * 40)
    base_calls = [256, 264, 281]
    mixed_calls = [256, 1800, 2585]
    diff = tk.diff_behaviors(base_calls, mixed_calls, "Base", "Mixed")
    print(f"   Semantically equivalent: {diff['equivalent']}")
    print(f"   Semantic matches: {len(diff['semantic_matches'])}")
    
    print("\n4. Save Edit Safety")
    print("-" * 40)
    safe, warnings = tk.is_safe_to_edit([256, 257, 1800, 2585])
    print(f"   Safe to edit: {safe}")
    if warnings:
        print(f"   Warnings: {warnings[0]}")
    
    print("\n5. FreeSO Gaps")
    print("-" * 40)
    gaps = tk.get_parity_gaps()
    critical = tk.get_critical_gaps()
    print(f"   Total gaps: {len(gaps)}")
    print(f"   Critical: {len(critical)}")
    if critical:
        print(f"   Top critical: {critical[0].function_name} ({critical[0].caller_count} callers)")
    
    print("\n6. Zombie Mod Hooks")
    print("-" * 40)
    hooks = tk.get_zombie_hooks()
    for offset, desc in list(hooks.items())[:3]:
        globals_list = tk.get_hook_globals(offset)
        print(f"   0x{offset:02X}: {desc[:40]}...")
        print(f"         Covers {len(globals_list)} global IDs across expansions")
    
    print("\n=== Toolkit Ready ===")
