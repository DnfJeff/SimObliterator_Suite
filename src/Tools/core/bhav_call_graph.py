"""
BHAV Call Graph Builder — Build and analyze BHAV call relationships.

Provides:
- Per-IFF call graph construction
- Entry point identification (called by OBJF/TTAB, not by other BHAVs)
- Utility BHAV detection (called by many)
- Scope classification (local, global, semi-global)
- Cross-reference tracking

Can export graphs in DOT format for visualization.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum

from .chunk_parsers import parse_bhav, parse_ttab, MinimalBHAV, MinimalTTAB


class BHAVScope(Enum):
    """Scope classification for a BHAV."""
    LOCAL = "local"           # 4096+ in object
    GLOBAL = "global"         # 256-4095 in Global.iff
    SEMI_GLOBAL = "semi"      # 8192+ in semi-global IFF
    UNKNOWN = "unknown"
    
    @classmethod
    def from_id(cls, bhav_id: int) -> 'BHAVScope':
        """Determine scope from BHAV ID."""
        if bhav_id < 256:
            return cls.GLOBAL  # Primitives or system
        elif bhav_id < 4096:
            return cls.GLOBAL
        elif bhav_id < 8192:
            return cls.LOCAL
        else:
            return cls.SEMI_GLOBAL


class CallType(Enum):
    """Type of call to a BHAV."""
    GOSUB = "gosub"           # Called via Gosub primitive
    OBJF_HOOK = "objf_hook"   # Entry point from OBJF
    TTAB_ACTION = "ttab_action"  # Action from TTAB
    TTAB_GUARD = "ttab_guard"    # Guard/test from TTAB


@dataclass
class BHAVNode:
    """A node in the call graph representing a BHAV."""
    bhav_id: int
    name: str = ""
    scope: BHAVScope = BHAVScope.UNKNOWN
    instruction_count: int = 0
    source_file: str = ""
    
    # Call relationships
    calls_to: Set[int] = field(default_factory=set)      # BHAVs this calls
    called_by: Set[int] = field(default_factory=set)     # BHAVs that call this
    
    # Entry point info
    objf_hooks: List[str] = field(default_factory=list)   # Which OBJF slots
    ttab_actions: List[int] = field(default_factory=list) # Which TTAB interactions
    ttab_guards: List[int] = field(default_factory=list)
    
    @property
    def id_hex(self) -> str:
        return f"0x{self.bhav_id:04X}"
    
    @property
    def is_entry_point(self) -> bool:
        """True if this BHAV is an entry point (not called by other BHAVs)."""
        return len(self.called_by) == 0 and (self.objf_hooks or self.ttab_actions or self.ttab_guards)
    
    @property
    def is_utility(self) -> bool:
        """True if this BHAV is called by many others (utility function)."""
        return len(self.called_by) >= 3
    
    @property
    def is_orphan(self) -> bool:
        """True if this BHAV has no callers and isn't an entry point."""
        return len(self.called_by) == 0 and not self.objf_hooks and not self.ttab_actions and not self.ttab_guards
    
    @property
    def call_depth(self) -> int:
        """Number of BHAVs this calls (direct only)."""
        return len(self.calls_to)
    
    @property
    def caller_count(self) -> int:
        """Number of BHAVs that call this (direct only)."""
        return len(self.called_by)


@dataclass
class CallEdge:
    """An edge in the call graph."""
    caller_id: int
    callee_id: int
    call_type: CallType
    instruction_index: int = -1  # Which instruction makes the call
    
    def __hash__(self):
        return hash((self.caller_id, self.callee_id, self.call_type))
    
    def __eq__(self, other):
        if not isinstance(other, CallEdge):
            return False
        return (self.caller_id == other.caller_id and 
                self.callee_id == other.callee_id and
                self.call_type == other.call_type)


@dataclass
class CallGraph:
    """Complete call graph for an IFF file."""
    source_file: str = ""
    nodes: Dict[int, BHAVNode] = field(default_factory=dict)
    edges: List[CallEdge] = field(default_factory=list)
    
    # External references (calls to BHAVs not in this file)
    external_calls: Set[int] = field(default_factory=set)
    
    def get_node(self, bhav_id: int) -> Optional[BHAVNode]:
        return self.nodes.get(bhav_id)
    
    def get_entry_points(self) -> List[BHAVNode]:
        """Get all entry point BHAVs."""
        return [n for n in self.nodes.values() if n.is_entry_point]
    
    def get_utilities(self) -> List[BHAVNode]:
        """Get all utility BHAVs (called by 3+)."""
        return [n for n in self.nodes.values() if n.is_utility]
    
    def get_orphans(self) -> List[BHAVNode]:
        """Get all orphan BHAVs (no callers, not entry points)."""
        return [n for n in self.nodes.values() if n.is_orphan]
    
    def get_by_scope(self, scope: BHAVScope) -> List[BHAVNode]:
        """Get all BHAVs with given scope."""
        return [n for n in self.nodes.values() if n.scope == scope]
    
    def get_callers_of(self, bhav_id: int) -> List[int]:
        """Get all BHAVs that call the given BHAV."""
        node = self.nodes.get(bhav_id)
        if node:
            return list(node.called_by)
        return []
    
    def get_callees_of(self, bhav_id: int) -> List[int]:
        """Get all BHAVs called by the given BHAV."""
        node = self.nodes.get(bhav_id)
        if node:
            return list(node.calls_to)
        return []
    
    def get_call_chain(self, bhav_id: int, max_depth: int = 10) -> List[List[int]]:
        """
        Get all call chains starting from a BHAV.
        
        Returns list of paths, each path is list of BHAV IDs.
        """
        chains = []
        
        def dfs(current_id: int, path: List[int], visited: Set[int]):
            if len(path) > max_depth:
                return
            if current_id in visited:
                return  # Avoid cycles
            
            path = path + [current_id]
            visited = visited | {current_id}
            
            node = self.nodes.get(current_id)
            if not node or not node.calls_to:
                if len(path) > 1:
                    chains.append(path)
                return
            
            for callee_id in node.calls_to:
                dfs(callee_id, path, visited)
        
        dfs(bhav_id, [], set())
        return chains
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        return {
            "source_file": self.source_file,
            "total_bhavs": len(self.nodes),
            "total_edges": len(self.edges),
            "entry_points": len(self.get_entry_points()),
            "utilities": len(self.get_utilities()),
            "orphans": len(self.get_orphans()),
            "external_calls": len(self.external_calls),
            "by_scope": {
                scope.value: len(self.get_by_scope(scope))
                for scope in BHAVScope
            }
        }
    
    def to_dot(self, include_external: bool = False) -> str:
        """
        Export graph to DOT format for Graphviz.
        
        Args:
            include_external: Include external BHAV references
            
        Returns:
            DOT format string
        """
        lines = ["digraph BHAVCallGraph {"]
        lines.append("  rankdir=TB;")
        lines.append("  node [shape=box, fontname=\"Courier\"];")
        lines.append("")
        
        # Color by scope
        scope_colors = {
            BHAVScope.LOCAL: "lightblue",
            BHAVScope.GLOBAL: "lightgreen",
            BHAVScope.SEMI_GLOBAL: "lightyellow",
            BHAVScope.UNKNOWN: "lightgray",
        }
        
        # Nodes
        for bhav_id, node in sorted(self.nodes.items()):
            color = scope_colors.get(node.scope, "white")
            label = f"{node.id_hex}"
            if node.name:
                label += f"\\n{node.name[:20]}"
            
            style = "filled"
            if node.is_entry_point:
                style += ",bold"
            
            lines.append(f'  n{bhav_id} [label="{label}", fillcolor="{color}", style="{style}"];')
        
        # External nodes
        if include_external:
            for ext_id in self.external_calls:
                scope = BHAVScope.from_id(ext_id)
                color = scope_colors.get(scope, "white")
                lines.append(f'  n{ext_id} [label="0x{ext_id:04X}\\n(external)", fillcolor="{color}", style="dashed,filled"];')
        
        lines.append("")
        
        # Edges
        for edge in self.edges:
            style = "solid"
            color = "black"
            
            if edge.call_type == CallType.OBJF_HOOK:
                color = "blue"
                style = "bold"
            elif edge.call_type == CallType.TTAB_ACTION:
                color = "green"
                style = "bold"
            elif edge.call_type == CallType.TTAB_GUARD:
                color = "orange"
                style = "dashed"
            
            if include_external or edge.callee_id in self.nodes:
                lines.append(f'  n{edge.caller_id} -> n{edge.callee_id} [color="{color}", style="{style}"];')
        
        lines.append("}")
        return "\n".join(lines)


class CallGraphBuilder:
    """
    Builder for BHAV call graphs.
    
    Usage:
        builder = CallGraphBuilder()
        graph = builder.build(iff_reader, "myobject.iff")
        print(graph.get_summary())
    """
    
    # Opcodes that call other BHAVs
    GOSUB_OPCODE = 0x04
    
    def __init__(self):
        self._graph: Optional[CallGraph] = None
        self._chunks_by_type: Dict[str, List[Tuple[int, bytes]]] = {}
    
    def build(self, iff_reader, filename: str = "") -> CallGraph:
        """
        Build call graph from an IFF file.
        
        Args:
            iff_reader: An IFFReader instance with chunks loaded
            filename: Filename for context
            
        Returns:
            CallGraph with all relationships
        """
        self._graph = CallGraph(source_file=filename)
        self._chunks_by_type = {}
        
        # Index chunks
        self._index_chunks(iff_reader)
        
        # Build nodes from BHAV chunks
        self._build_nodes()
        
        # Extract calls from BHAV instructions
        self._extract_calls()
        
        # Extract entry points from OBJF
        self._extract_objf_hooks()
        
        # Extract entry points from TTAB
        self._extract_ttab_hooks()
        
        return self._graph
    
    def _index_chunks(self, iff_reader):
        """Index all chunks by type."""
        for chunk in iff_reader.chunks:
            type_code = chunk.type_code
            if type_code not in self._chunks_by_type:
                self._chunks_by_type[type_code] = []
            self._chunks_by_type[type_code].append((chunk.chunk_id, chunk.chunk_data))
    
    def _build_nodes(self):
        """Create nodes for all BHAV chunks."""
        bhav_chunks = self._chunks_by_type.get('BHAV', [])
        
        for chunk_id, chunk_data in bhav_chunks:
            bhav = parse_bhav(chunk_data, chunk_id)
            if bhav is None:
                continue
            
            node = BHAVNode(
                bhav_id=chunk_id,
                scope=BHAVScope.from_id(chunk_id),
                instruction_count=len(bhav.instructions),
                source_file=self._graph.source_file,
            )
            
            self._graph.nodes[chunk_id] = node
    
    def _extract_calls(self):
        """Extract call relationships from BHAV instructions."""
        bhav_chunks = self._chunks_by_type.get('BHAV', [])
        
        for chunk_id, chunk_data in bhav_chunks:
            bhav = parse_bhav(chunk_data, chunk_id)
            if bhav is None:
                continue
            
            caller_node = self._graph.nodes.get(chunk_id)
            if caller_node is None:
                continue
            
            for idx, inst in enumerate(bhav.instructions):
                if inst.opcode == self.GOSUB_OPCODE:
                    # Gosub: target BHAV ID is in operand[0:2]
                    operand = inst.operand or bytes(8)
                    target_id = operand[0] | (operand[1] << 8)
                    
                    if target_id == 0:
                        continue
                    
                    # Record the call
                    caller_node.calls_to.add(target_id)
                    
                    # Record edge
                    edge = CallEdge(
                        caller_id=chunk_id,
                        callee_id=target_id,
                        call_type=CallType.GOSUB,
                        instruction_index=idx,
                    )
                    self._graph.edges.append(edge)
                    
                    # Update callee's called_by
                    if target_id in self._graph.nodes:
                        self._graph.nodes[target_id].called_by.add(chunk_id)
                    else:
                        # External call
                        self._graph.external_calls.add(target_id)
    
    def _extract_objf_hooks(self):
        """Extract OBJF entry point hooks."""
        objf_chunks = self._chunks_by_type.get('OBJF', [])
        
        # OBJF slot names
        objf_slots = [
            "Init", "Main", "Cleanup", "Sleep", "Wake",
            "Activate", "Deactivate", "Run", "Terminate",
            # Add more as needed
        ]
        
        for chunk_id, chunk_data in objf_chunks:
            # OBJF is array of uint16 BHAV IDs
            if len(chunk_data) < 4:
                continue
            
            idx = 0
            slot_idx = 0
            while idx + 2 <= len(chunk_data) and slot_idx < len(objf_slots):
                bhav_id = chunk_data[idx] | (chunk_data[idx + 1] << 8)
                
                if bhav_id != 0 and bhav_id in self._graph.nodes:
                    node = self._graph.nodes[bhav_id]
                    slot_name = objf_slots[slot_idx] if slot_idx < len(objf_slots) else f"Slot{slot_idx}"
                    node.objf_hooks.append(slot_name)
                
                idx += 2
                slot_idx += 1
    
    def _extract_ttab_hooks(self):
        """Extract TTAB interaction entry points."""
        ttab_chunks = self._chunks_by_type.get('TTAB', [])
        
        for chunk_id, chunk_data in ttab_chunks:
            ttab = parse_ttab(chunk_data, chunk_id)
            if ttab is None:
                continue
            
            for inter_idx, interaction in enumerate(ttab.interactions):
                # Action BHAV
                if interaction.action_function != 0:
                    if interaction.action_function in self._graph.nodes:
                        node = self._graph.nodes[interaction.action_function]
                        node.ttab_actions.append(inter_idx)
                
                # Guard/test BHAV
                if interaction.test_function != 0:
                    if interaction.test_function in self._graph.nodes:
                        node = self._graph.nodes[interaction.test_function]
                        node.ttab_guards.append(inter_idx)


def build_call_graph(iff_reader, filename: str = "") -> CallGraph:
    """
    Convenience function to build a call graph.
    
    Args:
        iff_reader: An IFFReader instance
        filename: Filename for context
        
    Returns:
        CallGraph with all relationships
    """
    builder = CallGraphBuilder()
    return builder.build(iff_reader, filename)


def find_shared_globals(graph: CallGraph) -> Dict[int, List[int]]:
    """
    Find global BHAVs that are called by multiple local BHAVs.
    
    Args:
        graph: A call graph
        
    Returns:
        Dict mapping global BHAV ID to list of local callers
    """
    shared = {}
    
    for bhav_id in graph.external_calls:
        if BHAVScope.from_id(bhav_id) == BHAVScope.GLOBAL:
            # Find all local BHAVs that call this global
            callers = []
            for node in graph.nodes.values():
                if node.scope == BHAVScope.LOCAL and bhav_id in node.calls_to:
                    callers.append(node.bhav_id)
            
            if len(callers) >= 2:
                shared[bhav_id] = callers
    
    return shared
