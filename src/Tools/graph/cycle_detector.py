"""
Cycle Detection for Resource Graphs (Phase 3.2)

CRITICAL: Cycles are NOT errors in The Sims 1.
This is diagnostic tooling only - cycles are valid patterns.

Why cycles exist:
  - Self-referential BHAVs (helper calling itself)
  - Interaction loops (TTAB → BHAV → TTAB callbacks)
  - Guard/action mutual references
  
What this enables:
  - Infinite-loop detection tooling
  - Safe live-edit features ("will this edit create infinite recursion?")
  - Impact analysis ("why does editing this explode everything?")
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional, Tuple
from enum import Enum

from .core import ResourceGraph, ResourceNode, Reference, TGI


class CycleType(Enum):
    """Classification of cycle patterns in The Sims 1."""
    SELF_REFERENTIAL = "self_referential"      # Node → itself (direct recursion)
    MUTUAL = "mutual"                          # A → B → A (two-node cycle)
    COMPLEX = "complex"                        # A → B → C → A (3+ nodes)


@dataclass
class Cycle:
    """Represents a detected cycle in the resource graph."""
    nodes: List[TGI]                          # Nodes in cycle (in order)
    edges: List[Reference]                    # Edges forming the cycle
    cycle_type: CycleType                     # Classification
    edge_kinds: Set[str]                      # Edge kinds involved (behavioral, structural, etc.)
    description: str = ""                     # Human-readable summary
    
    @property
    def size(self) -> int:
        """Number of nodes in the cycle."""
        return len(self.nodes)
    
    @property
    def is_behavioral(self) -> bool:
        """True if cycle involves behavioral edges (code execution)."""
        return "behavioral" in self.edge_kinds
    
    @property
    def is_pure_behavioral(self) -> bool:
        """True if ALL edges are behavioral."""
        return self.edge_kinds == {"behavioral"}
    
    def __repr__(self) -> str:
        node_str = " → ".join(str(node) for node in self.nodes)
        return f"Cycle({self.cycle_type.value}, {node_str})"


class CycleDetector:
    """
    Detects and classifies cycles in resource graphs.
    
    Uses Tarjan's strongly connected components algorithm for efficiency.
    Cycles are classified by:
      - Size (self-referential, mutual, complex)
      - Edge kinds (behavioral, structural, visual, tuning)
      - Pattern (common vs. unusual)
    
    IMPORTANT: This is diagnostic tooling - cycles are NOT validation errors.
    """
    
    def __init__(self, graph: ResourceGraph):
        self.graph = graph
        self.cycles: List[Cycle] = []
        
        # Tarjan's algorithm state
        self._index = 0
        self._stack: List[TGI] = []
        self._indices: Dict[TGI, int] = {}
        self._lowlinks: Dict[TGI, int] = {}
        self._on_stack: Set[TGI] = set()
    
    def detect_all_cycles(self) -> List[Cycle]:
        """
        Detect all cycles in the graph.
        
        Returns:
            List of Cycle objects (may be empty if no cycles)
        """
        self.cycles = []
        self._index = 0
        self._stack = []
        self._indices = {}
        self._lowlinks = {}
        self._on_stack = set()
        
        # Run Tarjan's algorithm on all nodes
        for tgi in self.graph.nodes:
            if tgi not in self._indices:
                self._strongconnect(tgi)
        
        return self.cycles
    
    def _strongconnect(self, v: TGI):
        """Tarjan's strongly connected components algorithm."""
        # Set the depth index for v
        self._indices[v] = self._index
        self._lowlinks[v] = self._index
        self._index += 1
        self._stack.append(v)
        self._on_stack.add(v)
        
        # Consider successors of v
        if v in self.graph._outbound_refs:
            for ref in self.graph._outbound_refs[v]:
                w = ref.target.tgi
                
                if w not in self._indices:
                    # Successor w has not yet been visited; recurse on it
                    self._strongconnect(w)
                    self._lowlinks[v] = min(self._lowlinks[v], self._lowlinks[w])
                elif w in self._on_stack:
                    # Successor w is in stack and hence in the current SCC
                    self._lowlinks[v] = min(self._lowlinks[v], self._indices[w])
        
        # If v is a root node, pop the stack and process SCC
        if self._lowlinks[v] == self._indices[v]:
            # Pop nodes off stack to form strongly connected component
            component: List[TGI] = []
            while True:
                w = self._stack.pop()
                self._on_stack.remove(w)
                component.append(w)
                if w == v:
                    break
            
            # Only process if it's a real cycle (size > 1 or self-loop)
            if len(component) > 1 or self._has_self_loop(component[0]):
                self._process_cycle(component)
    
    def _has_self_loop(self, tgi: TGI) -> bool:
        """Check if a node has a self-referential edge."""
        if tgi not in self.graph._outbound_refs:
            return False
        
        for ref in self.graph._outbound_refs[tgi]:
            if ref.target.tgi == tgi:
                return True
        return False
    
    def _process_cycle(self, component: List[TGI]):
        """Process a strongly connected component into a Cycle object."""
        # Get all edges within the component
        cycle_edges = []
        edge_kinds = set()
        
        for tgi in component:
            if tgi in self.graph._outbound_refs:
                for ref in self.graph._outbound_refs[tgi]:
                    if ref.target.tgi in component:
                        cycle_edges.append(ref)
                        if ref.edge_kind:
                            edge_kinds.add(ref.edge_kind)
        
        # Classify cycle type
        if len(component) == 1:
            cycle_type = CycleType.SELF_REFERENTIAL
        elif len(component) == 2:
            cycle_type = CycleType.MUTUAL
        else:
            cycle_type = CycleType.COMPLEX
        
        # Generate description
        description = self._generate_description(component, cycle_type, edge_kinds)
        
        # Create cycle object
        cycle = Cycle(
            nodes=component,
            edges=cycle_edges,
            cycle_type=cycle_type,
            edge_kinds=edge_kinds,
            description=description,
        )
        
        self.cycles.append(cycle)
    
    def _generate_description(self, component: List[TGI], cycle_type: CycleType, edge_kinds: Set[str]) -> str:
        """Generate human-readable description of the cycle."""
        # Get node types
        node_types = [tgi.type_code for tgi in component]
        type_summary = "/".join(sorted(set(node_types)))
        
        # Build description
        if cycle_type == CycleType.SELF_REFERENTIAL:
            node = component[0]
            if "behavioral" in edge_kinds:
                return f"Self-referential {node.type_code} (recursive subroutine)"
            else:
                return f"Self-referential {node.type_code}"
        
        elif cycle_type == CycleType.MUTUAL:
            if "behavioral" in edge_kinds and all(t == "BHAV" for t in node_types):
                return f"Mutual BHAV recursion (helper functions)"
            elif "behavioral" in edge_kinds:
                return f"Mutual {type_summary} cycle (interaction loop)"
            else:
                return f"Mutual {type_summary} cycle"
        
        else:  # COMPLEX
            size = len(component)
            if "behavioral" in edge_kinds:
                return f"Complex behavioral cycle ({size} nodes: {type_summary})"
            else:
                return f"Complex {type_summary} cycle ({size} nodes)"
    
    def get_behavioral_cycles(self) -> List[Cycle]:
        """Get cycles involving behavioral edges (code execution)."""
        return [c for c in self.cycles if c.is_behavioral]
    
    def get_pure_behavioral_cycles(self) -> List[Cycle]:
        """Get cycles with ONLY behavioral edges."""
        return [c for c in self.cycles if c.is_pure_behavioral]
    
    def get_self_referential_bhavs(self) -> List[Cycle]:
        """Get self-referential BHAV cycles (common pattern)."""
        return [
            c for c in self.cycles
            if c.cycle_type == CycleType.SELF_REFERENTIAL
            and c.nodes[0].type_code == "BHAV"
        ]
    
    def get_cycles_containing(self, tgi: TGI) -> List[Cycle]:
        """Get all cycles containing a specific node."""
        return [c for c in self.cycles if tgi in c.nodes]
    
    def analyze_cycles(self) -> Dict[str, any]:
        """
        Analyze detected cycles and return statistics.
        
        Returns:
            Dictionary with cycle statistics and classifications
        """
        if not self.cycles:
            self.detect_all_cycles()
        
        total = len(self.cycles)
        
        # Count by type
        self_ref = sum(1 for c in self.cycles if c.cycle_type == CycleType.SELF_REFERENTIAL)
        mutual = sum(1 for c in self.cycles if c.cycle_type == CycleType.MUTUAL)
        complex_cycles = sum(1 for c in self.cycles if c.cycle_type == CycleType.COMPLEX)
        
        # Count by edge kind
        behavioral = sum(1 for c in self.cycles if c.is_behavioral)
        pure_behavioral = sum(1 for c in self.cycles if c.is_pure_behavioral)
        
        # BHAV-specific patterns
        bhav_self_ref = len(self.get_self_referential_bhavs())
        
        return {
            "total_cycles": total,
            "by_type": {
                "self_referential": self_ref,
                "mutual": mutual,
                "complex": complex_cycles,
            },
            "by_edge_kind": {
                "behavioral": behavioral,
                "pure_behavioral": pure_behavioral,
            },
            "common_patterns": {
                "self_referential_bhavs": bhav_self_ref,
            },
            "cycles": self.cycles,
        }
    
    def print_summary(self):
        """Print human-readable summary of detected cycles."""
        stats = self.analyze_cycles()
        
        print("=" * 80)
        print("CYCLE DETECTION SUMMARY (Diagnostic Mode)")
        print("=" * 80)
        print()
        print(f"Total Cycles Detected: {stats['total_cycles']}")
        
        if stats['total_cycles'] == 0:
            print("\n✓ No cycles detected (graph is acyclic)")
            print()
            return
        
        print()
        print("By Type:")
        print(f"  Self-Referential: {stats['by_type']['self_referential']}")
        print(f"  Mutual (2 nodes):  {stats['by_type']['mutual']}")
        print(f"  Complex (3+ nodes): {stats['by_type']['complex']}")
        print()
        print("By Edge Kind:")
        print(f"  Behavioral (code):  {stats['by_edge_kind']['behavioral']}")
        print(f"  Pure Behavioral:    {stats['by_edge_kind']['pure_behavioral']}")
        print()
        print("Common Patterns:")
        print(f"  Self-Ref BHAVs:     {stats['common_patterns']['self_referential_bhavs']}")
        print()
        print("-" * 80)
        print("Sample Cycles:")
        print("-" * 80)
        
        # Show first 10 cycles
        for i, cycle in enumerate(self.cycles[:10], 1):
            node_str = " → ".join(str(node) for node in cycle.nodes[:4])
            if len(cycle.nodes) > 4:
                node_str += " → ..."
            print(f"{i}. {cycle.description}")
            print(f"   {node_str}")
            print(f"   Edge kinds: {', '.join(cycle.edge_kinds)}")
            print()
        
        if len(self.cycles) > 10:
            print(f"... and {len(self.cycles) - 10} more cycles")
            print()
        
        print("=" * 80)
        print("NOTE: Cycles are NOT errors - they are valid TS1 patterns.")
        print("      This is diagnostic information for analysis tools.")
        print("=" * 80)
        print()
