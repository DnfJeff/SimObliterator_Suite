"""
Behavior Graph Semantic Labeler - Label call graph nodes meaningfully

Instead of showing "Global 1800" in graphs, show "SS::test_user_interrupt"
This makes call graphs readable and comparable across expansions.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

# Import our semantic resolver
from .semantic_globals import (
    SemanticGlobalResolver, 
    ExpansionBlock, 
    EXPANSION_NAMES,
    GlobalInfo
)


class NodeType(Enum):
    PRIMITIVE = "primitive"      # 0-255
    GLOBAL = "global"            # 256-4095
    LOCAL = "local"              # 4096-8191
    SEMI_GLOBAL = "semi_global"  # 8192+


@dataclass
class GraphNode:
    """A node in the behavior call graph"""
    raw_id: int
    node_type: NodeType
    semantic_label: str
    expansion: Optional[ExpansionBlock]
    is_engine_internal: bool
    call_count: int = 0
    
    def to_dot_label(self, verbose: bool = False) -> str:
        """Generate DOT graph label"""
        if verbose:
            lines = [self.semantic_label]
            lines.append(f"(0x{self.raw_id:04X})")
            if self.is_engine_internal:
                lines.append("[ENGINE]")
            if self.call_count > 0:
                lines.append(f"calls: {self.call_count}")
            return "\\n".join(lines)
        return self.semantic_label
    
    def to_json(self) -> dict:
        return {
            "id": self.raw_id,
            "hex": f"0x{self.raw_id:04X}",
            "type": self.node_type.value,
            "label": self.semantic_label,
            "expansion": EXPANSION_NAMES.get(self.expansion) if self.expansion else None,
            "engine_internal": self.is_engine_internal,
            "calls": self.call_count
        }


class BehaviorGraphLabeler:
    """
    Labels behavior call graph nodes with semantic meanings.
    
    Transforms raw IDs into human-readable labels that:
    - Show function purpose (not just number)
    - Indicate expansion source
    - Flag engine-internal functions
    """
    
    def __init__(self, resolver: Optional[SemanticGlobalResolver] = None):
        self.resolver = resolver or SemanticGlobalResolver()
        self._primitive_names = self._load_primitive_names()
    
    def _load_primitive_names(self) -> Dict[int, str]:
        """Load primitive opcode names"""
        # From FreeSO research
        return {
            0: "sleep",
            1: "generic_call",
            2: "expression",
            4: "grab",
            5: "drop",
            6: "change_suit",
            7: "refresh",
            8: "random",
            9: "burn",
            11: "distance_to",
            12: "direction_to",
            13: "push_interaction",
            14: "find_best_object",
            15: "breakpoint",
            16: "find_location",
            17: "idle_for_input",
            18: "remove_object",
            20: "run_tree",
            21: "show_string",
            22: "look_towards",
            23: "play_sound",
            24: "old_relationship",
            26: "relationship",
            27: "goto_relative",
            28: "run_tree_by_name",
            29: "set_motive_change",
            31: "set_to_next",
            32: "test_object_type",
            35: "special_effect",
            36: "dialog_private",
            37: "test_sim_interacting",
            38: "dialog_global",
            39: "dialog_semiglobal",
            41: "balloon_headline",
            42: "create_object",
            43: "drop_onto",
            44: "animate",
            45: "goto_routing_slot",
            46: "snap",
            47: "reach",
            48: "stop_sounds",
            49: "notify_out_of_idle",
            50: "change_action_string",
        }
    
    def classify_opcode(self, opcode: int) -> NodeType:
        """Determine what type of call this opcode represents"""
        if opcode < 256:
            return NodeType.PRIMITIVE
        elif opcode < 4096:
            return NodeType.GLOBAL
        elif opcode < 8192:
            return NodeType.LOCAL
        else:
            return NodeType.SEMI_GLOBAL
    
    def create_node(self, opcode: int, call_count: int = 0) -> GraphNode:
        """Create a labeled graph node for an opcode"""
        node_type = self.classify_opcode(opcode)
        
        if node_type == NodeType.PRIMITIVE:
            label = self._primitive_names.get(opcode, f"prim_{opcode}")
            return GraphNode(
                raw_id=opcode,
                node_type=node_type,
                semantic_label=f"P::{label}",
                expansion=None,
                is_engine_internal=True,  # All primitives are engine
                call_count=call_count
            )
        
        elif node_type == NodeType.GLOBAL:
            info = self.resolver.resolve(opcode)
            return GraphNode(
                raw_id=opcode,
                node_type=node_type,
                semantic_label=info.semantic_name,
                expansion=info.expansion,
                is_engine_internal=info.is_engine_internal,
                call_count=call_count
            )
        
        elif node_type == NodeType.LOCAL:
            # Local behaviors - just use ID
            local_id = opcode - 4096
            return GraphNode(
                raw_id=opcode,
                node_type=node_type,
                semantic_label=f"L::{local_id}",
                expansion=None,
                is_engine_internal=False,
                call_count=call_count
            )
        
        else:  # SEMI_GLOBAL
            semi_id = opcode - 8192
            return GraphNode(
                raw_id=opcode,
                node_type=node_type,
                semantic_label=f"SG::{semi_id}",
                expansion=None,
                is_engine_internal=False,
                call_count=call_count
            )
    
    def label_call_graph(self, 
                         calls: Dict[int, List[int]], 
                         counts: Optional[Dict[int, int]] = None) -> Dict[str, GraphNode]:
        """
        Label an entire call graph.
        
        calls: mapping of caller_id -> [called_ids]
        counts: optional call count per ID
        """
        counts = counts or {}
        all_ids: Set[int] = set()
        
        # Collect all unique IDs
        for caller, callees in calls.items():
            all_ids.add(caller)
            all_ids.update(callees)
        
        # Create labeled nodes
        nodes = {}
        for opcode in all_ids:
            count = counts.get(opcode, 0)
            node = self.create_node(opcode, count)
            nodes[f"0x{opcode:04X}"] = node
        
        return nodes
    
    def generate_dot_graph(self,
                           calls: Dict[int, List[int]],
                           title: str = "Behavior Call Graph") -> str:
        """Generate DOT format graph with semantic labels"""
        nodes = self.label_call_graph(calls)
        
        lines = [
            f'digraph "{title}" {{',
            '    rankdir=TB;',
            '    node [shape=box, fontname="Consolas"];',
            '',
            '    // Node definitions with semantic labels',
        ]
        
        # Define nodes with styling by type
        for hex_id, node in sorted(nodes.items()):
            style = self._get_node_style(node)
            label = node.to_dot_label(verbose=True)
            lines.append(f'    "{hex_id}" [label="{label}", {style}];')
        
        lines.append('')
        lines.append('    // Edges')
        
        # Add edges
        for caller, callees in calls.items():
            caller_hex = f"0x{caller:04X}"
            for callee in callees:
                callee_hex = f"0x{callee:04X}"
                lines.append(f'    "{caller_hex}" -> "{callee_hex}";')
        
        lines.append('}')
        return '\n'.join(lines)
    
    def _get_node_style(self, node: GraphNode) -> str:
        """Get DOT style attributes for a node"""
        styles = {
            NodeType.PRIMITIVE: 'fillcolor="#FFE4E1", style=filled',  # Light red
            NodeType.GLOBAL: 'fillcolor="#E0FFE0", style=filled' if not node.is_engine_internal 
                            else 'fillcolor="#FFE0E0", style=filled',  # Green/Red
            NodeType.LOCAL: 'fillcolor="#E0E0FF", style=filled',  # Light blue
            NodeType.SEMI_GLOBAL: 'fillcolor="#FFFFE0", style=filled',  # Light yellow
        }
        return styles.get(node.node_type, '')


class ExpansionBehaviorDiffer:
    """
    Diff behaviors across expansions at the semantic level.
    
    Two behaviors calling different raw IDs might be doing the
    exact same thing if those IDs have the same offset.
    """
    
    def __init__(self, labeler: Optional[BehaviorGraphLabeler] = None):
        self.labeler = labeler or BehaviorGraphLabeler()
    
    def normalize_to_offsets(self, calls: List[int]) -> List[Tuple[NodeType, int]]:
        """Convert calls to (type, offset) pairs for comparison"""
        result = []
        for call in calls:
            node_type = self.labeler.classify_opcode(call)
            
            if node_type == NodeType.GLOBAL:
                offset = (call - 256) % 256
                result.append((node_type, offset))
            else:
                result.append((node_type, call))
        
        return result
    
    def diff_behaviors(self, 
                       calls_a: List[int], 
                       calls_b: List[int],
                       name_a: str = "A",
                       name_b: str = "B") -> Dict:
        """
        Diff two behaviors, understanding expansion equivalence.
        
        Returns detailed diff including:
        - Semantic equivalence (same function, different ID)
        - True differences (different function)
        """
        norm_a = self.normalize_to_offsets(calls_a)
        norm_b = self.normalize_to_offsets(calls_b)
        
        result = {
            "equivalent": norm_a == norm_b,
            "length_match": len(calls_a) == len(calls_b),
            "differences": [],
            "semantic_matches": [],  # Same function, different ID
        }
        
        max_len = max(len(calls_a), len(calls_b))
        for i in range(max_len):
            a_call = calls_a[i] if i < len(calls_a) else None
            b_call = calls_b[i] if i < len(calls_b) else None
            
            if a_call == b_call:
                continue  # Exact match
            
            if a_call is None or b_call is None:
                result["differences"].append({
                    "position": i,
                    "type": "missing",
                    name_a: a_call,
                    name_b: b_call,
                })
                continue
            
            # Check for semantic equivalence
            norm_a_i = norm_a[i] if i < len(norm_a) else None
            norm_b_i = norm_b[i] if i < len(norm_b) else None
            
            if norm_a_i == norm_b_i:
                # Same function, different raw ID (expansion difference)
                node_a = self.labeler.create_node(a_call)
                node_b = self.labeler.create_node(b_call)
                result["semantic_matches"].append({
                    "position": i,
                    "function": node_a.semantic_label.split("::")[-1],
                    name_a: {"id": a_call, "label": node_a.semantic_label},
                    name_b: {"id": b_call, "label": node_b.semantic_label},
                })
            else:
                # True difference
                node_a = self.labeler.create_node(a_call)
                node_b = self.labeler.create_node(b_call)
                result["differences"].append({
                    "position": i,
                    "type": "different_function",
                    name_a: {"id": a_call, "label": node_a.semantic_label},
                    name_b: {"id": b_call, "label": node_b.semantic_label},
                })
        
        return result
    
    def format_diff_report(self, diff: Dict, name_a: str = "A", name_b: str = "B") -> str:
        """Format diff result as readable report"""
        lines = [
            "Behavior Diff Report",
            "=" * 50,
            f"Semantically equivalent: {diff['equivalent']}",
            f"Length match: {diff['length_match']}",
            "",
        ]
        
        if diff["semantic_matches"]:
            lines.append("Semantic Matches (same function, different expansion):")
            for m in diff["semantic_matches"]:
                lines.append(f"  [{m['position']}] {m['function']}:")
                lines.append(f"      {name_a}: {m[name_a]['label']}")
                lines.append(f"      {name_b}: {m[name_b]['label']}")
        
        if diff["differences"]:
            lines.append("")
            lines.append("True Differences:")
            for d in diff["differences"]:
                if d["type"] == "missing":
                    lines.append(f"  [{d['position']}] Missing in one behavior")
                else:
                    lines.append(f"  [{d['position']}] Different function:")
                    lines.append(f"      {name_a}: {d[name_a]['label']}")
                    lines.append(f"      {name_b}: {d[name_b]['label']}")
        
        return "\n".join(lines)


# Test
if __name__ == "__main__":
    labeler = BehaviorGraphLabeler()
    
    print("=== Graph Node Labeling ===\n")
    
    test_opcodes = [0, 2, 256, 264, 778, 1800, 2585, 4100, 8200]
    for op in test_opcodes:
        node = labeler.create_node(op)
        print(f"{op:5d} (0x{op:04X}): {node.semantic_label:30s} [{node.node_type.value}]")
    
    print("\n=== Expansion Behavior Diff ===\n")
    
    differ = ExpansionBehaviorDiffer(labeler)
    
    # Same logic, different expansions
    base_calls = [256, 264, 281]  # Base game
    superstar_calls = [256, 1800, 2585]  # Mix of base + Superstar equivalents
    
    diff = differ.diff_behaviors(base_calls, superstar_calls, "Base", "Mixed")
    print(differ.format_diff_report(diff, "Base", "Mixed"))
    
    print("\n=== DOT Graph Sample ===\n")
    
    sample_calls = {
        256: [264, 281],
        264: [0, 2],
        281: [0],
    }
    
    dot = labeler.generate_dot_graph(sample_calls, "Sample Call Graph")
    print(dot[:500] + "...")
