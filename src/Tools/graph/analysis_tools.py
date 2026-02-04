"""
Analysis Tools (Phase 3.4) - The Payoff Layer

This is where SimObliterator stops being an editor and becomes a forensic tool.

Three powerful analysis tools that cash in on all the Phase 3 infrastructure:
  1. Dead Code Finder → unreachable BHAVs, unused TTAB entries
  2. Blast Radius Calculator → "If I edit this BHAV, what breaks?"
  3. Orphan Explainer → "This chunk is orphaned because..."
"""

from dataclasses import dataclass
from typing import List, Set, Dict, Optional, Tuple
from enum import Enum

from .core import ResourceGraph, ResourceNode, Reference, TGI, ChunkScope
from .cycle_detector import CycleDetector


@dataclass
class DeadCodeItem:
    """Represents a piece of dead (unreachable) code."""
    node: ResourceNode
    reason: str              # Why it's considered dead
    severity: str            # "critical", "warning", "info"
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] Dead code: {self.node.tgi} - {self.reason}"


@dataclass
class BlastRadiusItem:
    """Represents something affected by editing a node."""
    affected_node: TGI
    relationship: str        # "caller", "callee", "cyclic_peer", "visual_dep", etc.
    edge_kind: str          # behavioral, visual, structural, tuning
    distance: int           # Hops from source (1 = direct, 2+ = indirect)
    path: List[TGI]         # Path from source to affected node
    
    def __str__(self) -> str:
        distance_str = "directly" if self.distance == 1 else f"{self.distance} hops away"
        return f"{self.affected_node} ({self.relationship}, {self.edge_kind}, {distance_str})"


@dataclass
class OrphanExplanation:
    """Explains why a chunk is orphaned."""
    node: ResourceNode
    expected_sources: List[str]    # What SHOULD reference it
    similar_nodes: List[TGI]       # Similar non-orphaned nodes
    suggestion: str                # How to fix it
    
    def __str__(self) -> str:
        expected = ", ".join(self.expected_sources) if self.expected_sources else "OBJD/OBJf/TTAB"
        return f"Orphan: {self.node.tgi} - Expected reference from: {expected}\n   {self.suggestion}"


class DeadCodeFinder:
    """
    Finds unreachable code and unused resources.
    
    Dead code includes:
      - BHAVs never called (no inbound behavioral edges)
      - BHAVs in cycles that are never entered
      - TTAB entries never referenced
      - Resources that exist but serve no purpose
    """
    
    def __init__(self, graph: ResourceGraph):
        self.graph = graph
        self.dead_code: List[DeadCodeItem] = []
    
    def find_all(self) -> List[DeadCodeItem]:
        """Find all dead code in the graph."""
        self.dead_code = []
        
        self._find_unreachable_bhavs()
        self._find_orphaned_ttabs()
        self._find_orphaned_graphics()
        self._find_cyclic_dead_code()
        
        return self.dead_code
    
    def _find_unreachable_bhavs(self):
        """Find BHAVs with no inbound behavioral edges."""
        bhav_nodes = [n for n in self.graph.nodes.values() if n.chunk_type == "BHAV"]
        
        for bhav in bhav_nodes:
            inbound = self.graph.who_references(bhav.tgi)
            behavioral_inbound = [ref for ref in inbound if ref.edge_kind == "behavioral"]
            
            if not behavioral_inbound:
                # Check if it has outbound behavioral refs (does something)
                outbound = self.graph.what_references(bhav.tgi)
                behavioral_outbound = [ref for ref in outbound if ref.edge_kind == "behavioral"]
                
                if behavioral_outbound:
                    severity = "critical"
                    reason = "BHAV contains code but is never called (unreachable)"
                else:
                    severity = "warning"
                    reason = "BHAV is empty or stub (never called, no code)"
                
                self.dead_code.append(DeadCodeItem(
                    node=bhav,
                    reason=reason,
                    severity=severity,
                ))
    
    def _find_orphaned_ttabs(self):
        """Find TTAB (interaction tables) with no references."""
        ttab_nodes = [n for n in self.graph.nodes.values() if n.chunk_type == "TTAB"]
        
        for ttab in ttab_nodes:
            inbound = self.graph.who_references(ttab.tgi)
            
            if not inbound:
                self.dead_code.append(DeadCodeItem(
                    node=ttab,
                    reason="TTAB (interaction table) never referenced - dead pie menu entries",
                    severity="warning",
                ))
    
    def _find_orphaned_graphics(self):
        """Find graphics resources with no references."""
        dgrp_nodes = [n for n in self.graph.nodes.values() if n.chunk_type == "DGRP"]
        
        for dgrp in dgrp_nodes:
            inbound = self.graph.who_references(dgrp.tgi)
            
            if not inbound:
                self.dead_code.append(DeadCodeItem(
                    node=dgrp,
                    reason="DGRP (draw group) never referenced - invisible graphics",
                    severity="warning",
                ))
    
    def _find_cyclic_dead_code(self):
        """Find cycles that are themselves unreachable."""
        detector = CycleDetector(self.graph)
        cycles = detector.detect_all_cycles()
        
        for cycle in cycles:
            # Check if ANY node in cycle has inbound refs from outside
            has_entry_point = False
            
            for node_tgi in cycle.nodes:
                inbound = self.graph.who_references(node_tgi)
                
                # Check for inbound refs from outside the cycle
                for ref in inbound:
                    if ref.source.tgi not in cycle.nodes:
                        has_entry_point = True
                        break
                
                if has_entry_point:
                    break
            
            if not has_entry_point and cycle.is_behavioral:
                # Entire cycle is unreachable
                node_str = ", ".join(str(tgi) for tgi in cycle.nodes[:3])
                if len(cycle.nodes) > 3:
                    node_str += ", ..."
                
                for node_tgi in cycle.nodes:
                    node = self.graph.nodes.get(node_tgi)
                    if node and node.chunk_type == "BHAV":
                        self.dead_code.append(DeadCodeItem(
                            node=node,
                            reason=f"Part of unreachable cycle ({node_str})",
                            severity="warning",
                        ))
    
    def get_by_severity(self, severity: str) -> List[DeadCodeItem]:
        """Get dead code items by severity."""
        return [item for item in self.dead_code if item.severity == severity]
    
    def get_by_type(self, chunk_type: str) -> List[DeadCodeItem]:
        """Get dead code items by chunk type."""
        return [item for item in self.dead_code if item.node.chunk_type == chunk_type]


class BlastRadiusCalculator:
    """
    Calculates the blast radius of editing a node.
    
    "If I edit this BHAV, what breaks?"
    
    Shows:
      - Direct callers (will definitely be affected)
      - Indirect callers (may be affected)
      - Callees (functions this BHAV uses)
      - Cyclic peers (mutual dependencies)
      - Different impact by edge kind (behavioral vs. visual vs. tuning)
    """
    
    def __init__(self, graph: ResourceGraph):
        self.graph = graph
    
    def calculate(self, target_tgi: TGI, max_depth: int = 3) -> Dict[str, List[BlastRadiusItem]]:
        """
        Calculate blast radius for editing a node.
        
        Args:
            target_tgi: The node being edited
            max_depth: Maximum hops to traverse (default 3)
        
        Returns:
            Dictionary with categories:
              - direct_callers: Nodes that directly call this
              - indirect_callers: Nodes that indirectly call this
              - callees: Nodes this calls
              - cyclic_peers: Nodes in cycles with this
              - visual_deps: Visual pipeline dependencies
              - tuning_deps: Tuning constant dependencies
        """
        results = {
            "direct_callers": [],
            "indirect_callers": [],
            "callees": [],
            "cyclic_peers": [],
            "visual_deps": [],
            "tuning_deps": [],
        }
        
        # Direct callers (inbound)
        inbound = self.graph.who_references(target_tgi)
        for ref in inbound:
            item = BlastRadiusItem(
                affected_node=ref.source.tgi,
                relationship="caller",
                edge_kind=ref.edge_kind or "unknown",
                distance=1,
                path=[ref.source.tgi, target_tgi],
            )
            
            if ref.edge_kind == "behavioral":
                results["direct_callers"].append(item)
            elif ref.edge_kind == "visual":
                results["visual_deps"].append(item)
            elif ref.edge_kind == "tuning":
                results["tuning_deps"].append(item)
        
        # Callees (outbound)
        outbound = self.graph.what_references(target_tgi)
        for ref in outbound:
            item = BlastRadiusItem(
                affected_node=ref.target.tgi,
                relationship="callee",
                edge_kind=ref.edge_kind or "unknown",
                distance=1,
                path=[target_tgi, ref.target.tgi],
            )
            results["callees"].append(item)
        
        # Indirect callers (BFS traversal of inbound refs)
        visited = {target_tgi}
        queue = [(ref.source.tgi, 2, [ref.source.tgi, target_tgi]) for ref in inbound]
        
        while queue:
            node_tgi, distance, path = queue.pop(0)
            
            if distance > max_depth:
                continue
            
            if node_tgi in visited:
                continue
            visited.add(node_tgi)
            
            # Add to indirect callers
            results["indirect_callers"].append(BlastRadiusItem(
                affected_node=node_tgi,
                relationship="indirect_caller",
                edge_kind="behavioral",
                distance=distance,
                path=path,
            ))
            
            # Continue traversal
            for ref in self.graph.who_references(node_tgi):
                if ref.edge_kind == "behavioral" and ref.source.tgi not in visited:
                    queue.append((ref.source.tgi, distance + 1, [ref.source.tgi] + path))
        
        # Cyclic peers
        detector = CycleDetector(self.graph)
        cycles = detector.detect_all_cycles()
        
        for cycle in cycles:
            if target_tgi in cycle.nodes:
                for node_tgi in cycle.nodes:
                    if node_tgi != target_tgi:
                        results["cyclic_peers"].append(BlastRadiusItem(
                            affected_node=node_tgi,
                            relationship="cyclic_peer",
                            edge_kind="behavioral",
                            distance=1,
                            path=[target_tgi, node_tgi],  # Simplified path
                        ))
        
        return results
    
    def print_blast_radius(self, target_tgi: TGI, max_depth: int = 3):
        """Print human-readable blast radius report."""
        results = self.calculate(target_tgi, max_depth)
        
        print("=" * 80)
        print(f"BLAST RADIUS: {target_tgi}")
        print("=" * 80)
        print()
        
        total = sum(len(items) for items in results.values())
        print(f"Total Affected Nodes: {total}")
        print()
        
        # Direct callers
        if results["direct_callers"]:
            print(f"Direct Callers ({len(results['direct_callers'])}):")
            print("  These nodes call this directly - will definitely be affected")
            for item in results["direct_callers"][:10]:
                print(f"  • {item}")
            if len(results["direct_callers"]) > 10:
                print(f"  ... and {len(results['direct_callers']) - 10} more")
            print()
        
        # Indirect callers
        if results["indirect_callers"]:
            print(f"Indirect Callers ({len(results['indirect_callers'])}):")
            print("  These nodes call this indirectly - may be affected")
            for item in results["indirect_callers"][:10]:
                print(f"  • {item}")
            if len(results["indirect_callers"]) > 10:
                print(f"  ... and {len(results['indirect_callers']) - 10} more")
            print()
        
        # Callees
        if results["callees"]:
            print(f"Callees ({len(results['callees'])}):")
            print("  This node calls these - changing logic may affect calls")
            for item in results["callees"][:10]:
                print(f"  • {item}")
            if len(results["callees"]) > 10:
                print(f"  ... and {len(results['callees']) - 10} more")
            print()
        
        # Cyclic peers
        if results["cyclic_peers"]:
            print(f"Cyclic Peers ({len(results['cyclic_peers'])}):")
            print("  These nodes are in cycles with this - mutual dependencies")
            for item in results["cyclic_peers"][:10]:
                print(f"  • {item}")
            print()
        
        # Visual deps
        if results["visual_deps"]:
            print(f"Visual Dependencies ({len(results['visual_deps'])}):")
            for item in results["visual_deps"]:
                print(f"  • {item}")
            print()
        
        # Tuning deps
        if results["tuning_deps"]:
            print(f"Tuning Dependencies ({len(results['tuning_deps'])}):")
            for item in results["tuning_deps"]:
                print(f"  • {item}")
            print()
        
        print("=" * 80)


class OrphanExplainer:
    """
    Explains why chunks are orphaned with context.
    
    Instead of just "this is orphaned", provide:
      - What SHOULD reference it (expected sources)
      - Similar non-orphaned nodes (examples)
      - Specific suggestions for fixing
    """
    
    def __init__(self, graph: ResourceGraph):
        self.graph = graph
    
    def explain(self, orphan_tgi: TGI) -> Optional[OrphanExplanation]:
        """Generate detailed explanation for an orphaned node."""
        node = self.graph.nodes.get(orphan_tgi)
        if not node:
            return None
        
        # Check if actually orphaned
        inbound = self.graph.who_references(orphan_tgi)
        if inbound:
            return None  # Not orphaned
        
        # Generate explanation based on chunk type
        if node.chunk_type == "BHAV":
            return self._explain_bhav_orphan(node)
        elif node.chunk_type == "TTAB":
            return self._explain_ttab_orphan(node)
        elif node.chunk_type == "DGRP":
            return self._explain_dgrp_orphan(node)
        elif node.chunk_type == "BCON":
            return self._explain_bcon_orphan(node)
        elif node.chunk_type == "STR#":
            return self._explain_str_orphan(node)
        else:
            return OrphanExplanation(
                node=node,
                expected_sources=[],
                similar_nodes=[],
                suggestion=f"Orphaned {node.chunk_type} - add reference or remove if unused",
            )
    
    def _explain_bhav_orphan(self, node: ResourceNode) -> OrphanExplanation:
        """Explain orphaned BHAV."""
        # Check if BHAV has code (outbound refs)
        outbound = self.graph.what_references(node.tgi)
        has_code = any(ref.edge_kind == "behavioral" for ref in outbound)
        
        # Find similar referenced BHAVs
        similar = self._find_similar_bhavs(node)
        
        if has_code:
            return OrphanExplanation(
                node=node,
                expected_sources=["OBJD", "OBJf", "TTAB", "other BHAVs"],
                similar_nodes=similar,
                suggestion="BHAV contains code but is never called. Add to OBJD/OBJf entry points or call from another BHAV.",
            )
        else:
            return OrphanExplanation(
                node=node,
                expected_sources=["OBJD", "OBJf", "TTAB", "other BHAVs"],
                similar_nodes=similar,
                suggestion="BHAV is empty or stub. Either implement it and hook it up, or remove if unused.",
            )
    
    def _explain_ttab_orphan(self, node: ResourceNode) -> OrphanExplanation:
        """Explain orphaned TTAB."""
        # Find referenced TTABs as examples
        ttab_nodes = [n for n in self.graph.nodes.values() if n.chunk_type == "TTAB"]
        referenced_ttabs = [n.tgi for n in ttab_nodes if self.graph.who_references(n.tgi)]
        
        return OrphanExplanation(
            node=node,
            expected_sources=["OBJD.tree_table_id"],
            similar_nodes=referenced_ttabs[:3],
            suggestion="TTAB defines interactions but OBJD doesn't reference it. Set OBJD.tree_table_id to this TTAB's ID.",
        )
    
    def _explain_dgrp_orphan(self, node: ResourceNode) -> OrphanExplanation:
        """Explain orphaned DGRP."""
        # Find referenced DGRPs as examples
        dgrp_nodes = [n for n in self.graph.nodes.values() if n.chunk_type == "DGRP"]
        referenced_dgrps = [n.tgi for n in dgrp_nodes if self.graph.who_references(n.tgi)]
        
        return OrphanExplanation(
            node=node,
            expected_sources=["OBJD.base_graphic_id"],
            similar_nodes=referenced_dgrps[:3],
            suggestion="DGRP defines graphics but OBJD doesn't reference it. Set OBJD.base_graphic_id to this DGRP's ID. Object will be invisible without this!",
        )
    
    def _explain_bcon_orphan(self, node: ResourceNode) -> OrphanExplanation:
        """Explain orphaned BCON."""
        return OrphanExplanation(
            node=node,
            expected_sources=["BHAV expressions (opcode 2, scope 26)"],
            similar_nodes=[],
            suggestion="BCON defines tuning constants but no BHAV uses them. Either reference from BHAV expressions or remove if unused.",
        )
    
    def _explain_str_orphan(self, node: ResourceNode) -> OrphanExplanation:
        """Explain orphaned STR#."""
        return OrphanExplanation(
            node=node,
            expected_sources=["OBJD.catalog_strings_id", "OBJD.body_string_id", "TTAB"],
            similar_nodes=[],
            suggestion="STR# defines text but nothing references it. Add reference from OBJD or remove if unused.",
        )
    
    def _find_similar_bhavs(self, node: ResourceNode) -> List[TGI]:
        """Find similar BHAVs that ARE referenced (as examples)."""
        bhav_nodes = [n for n in self.graph.nodes.values() 
                     if n.chunk_type == "BHAV" and n.owner_iff == node.owner_iff]
        
        referenced = [n.tgi for n in bhav_nodes if self.graph.who_references(n.tgi)]
        return referenced[:3]
    
    def explain_all_orphans(self) -> List[OrphanExplanation]:
        """Explain all orphans in the graph."""
        orphans = self.graph.find_orphans()
        explanations = []
        
        for orphan in orphans:
            explanation = self.explain(orphan.tgi)
            if explanation:
                explanations.append(explanation)
        
        return explanations
    
    def print_explanations(self):
        """Print all orphan explanations."""
        explanations = self.explain_all_orphans()
        
        print("=" * 80)
        print(f"ORPHAN EXPLANATIONS ({len(explanations)} orphans)")
        print("=" * 80)
        print()
        
        if not explanations:
            print("✓ No orphans found - all resources are referenced")
            print()
            return
        
        # Group by type
        by_type: Dict[str, List[OrphanExplanation]] = {}
        for exp in explanations:
            chunk_type = exp.node.chunk_type
            if chunk_type not in by_type:
                by_type[chunk_type] = []
            by_type[chunk_type].append(exp)
        
        for chunk_type, exps in sorted(by_type.items()):
            print(f"{chunk_type} Orphans ({len(exps)}):")
            print("-" * 80)
            for exp in exps[:5]:
                print(f"  {exp}")
                if exp.similar_nodes:
                    similar_str = ", ".join(str(tgi) for tgi in exp.similar_nodes)
                    print(f"   Examples of referenced {chunk_type}s: {similar_str}")
                print()
            
            if len(exps) > 5:
                print(f"  ... and {len(exps) - 5} more {chunk_type} orphans")
                print()
        
        print("=" * 80)
