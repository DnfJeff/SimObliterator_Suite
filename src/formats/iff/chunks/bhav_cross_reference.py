"""BHAV Cross-Reference Tool - Analyzes which BHAVs call which.

Provides functionality to query and analyze BHAV calling relationships,
detect unused BHAVs, and generate cross-reference reports.

Author: SimObliterator
License: MIT
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum
import logging
from collections import defaultdict

from simobliterator.formats.iff.chunks.bhav_package_decompiler import PackageAST, BHAVCall, CallType

logger = logging.getLogger(__name__)


@dataclass
class CallSite:
    """Information about a specific call site."""
    instruction_index: int
    operand_data: Dict = field(default_factory=dict)
    call_type: CallType = CallType.SUBROUTINE


@dataclass
class CrossRefEntry:
    """Cross-reference entry for a BHAV."""
    bhav_id: int
    callers: Dict[int, List[CallSite]] = field(default_factory=dict)
    callees: Dict[int, List[CallSite]] = field(default_factory=dict)
    
    def caller_count(self) -> int:
        """Get number of unique callers."""
        return len(self.callers)
    
    def callee_count(self) -> int:
        """Get number of unique callees."""
        return len(self.callees)
    
    def total_calls(self) -> int:
        """Get total number of call sites."""
        return sum(len(sites) for sites in self.callers.values()) + \
               sum(len(sites) for sites in self.callees.values())


class BHAVCrossReference:
    """Query and analyze BHAV calling relationships."""
    
    def __init__(self, package_ast: PackageAST):
        """
        Initialize cross-reference analyzer.
        
        Args:
            package_ast: PackageAST from BHAVPackageDecompiler
        """
        self.package = package_ast
        self.xref: Dict[int, CrossRefEntry] = {}
        self.call_matrix: Dict[Tuple[int, int], List[CallSite]] = {}
        self._build_cross_ref_index()
    
    def _build_cross_ref_index(self) -> None:
        """Build comprehensive cross-reference index."""
        # Initialize entries for all BHAVs
        for bhav_id in self.package.bhav_map:
            self.xref[bhav_id] = CrossRefEntry(bhav_id)
        
        # Populate caller/callee relationships
        for caller_id, calls in self.package.call_graph.items():
            for call in calls:
                callee_id = call.callee_id
                
                # Add to cross-ref index
                if caller_id in self.xref:
                    if callee_id not in self.xref[caller_id].callees:
                        self.xref[caller_id].callees[callee_id] = []
                    
                    site = CallSite(
                        instruction_index=call.instruction_indices[0] if call.instruction_indices else -1,
                        operand_data=call.operand_data,
                        call_type=call.call_type
                    )
                    self.xref[caller_id].callees[callee_id].append(site)
                
                if callee_id in self.xref:
                    if caller_id not in self.xref[callee_id].callers:
                        self.xref[callee_id].callers[caller_id] = []
                    
                    site = CallSite(
                        instruction_index=call.instruction_indices[0] if call.instruction_indices else -1,
                        operand_data=call.operand_data,
                        call_type=call.call_type
                    )
                    self.xref[callee_id].callers[caller_id].append(site)
                
                # Add to call matrix
                self.call_matrix[(caller_id, callee_id)] = [site]
    
    # Query Methods
    
    def callers_of(self, bhav_id: int) -> Dict[int, List[CallSite]]:
        """
        Get all BHAVs that call the given BHAV.
        
        Args:
            bhav_id: Target BHAV ID
        
        Returns:
            Dict mapping caller BHAV ID → list of call sites
        """
        if bhav_id not in self.xref:
            return {}
        return self.xref[bhav_id].callers
    
    def callees_of(self, bhav_id: int) -> Dict[int, List[CallSite]]:
        """
        Get all BHAVs called by the given BHAV.
        
        Args:
            bhav_id: Source BHAV ID
        
        Returns:
            Dict mapping callee BHAV ID → list of call sites
        """
        if bhav_id not in self.xref:
            return {}
        return self.xref[bhav_id].callees
    
    def direct_callers_of(self, bhav_id: int) -> List[int]:
        """Get list of BHAV IDs that directly call the given BHAV."""
        return list(self.callers_of(bhav_id).keys())
    
    def direct_callees_of(self, bhav_id: int) -> List[int]:
        """Get list of BHAV IDs directly called by the given BHAV."""
        return list(self.callees_of(bhav_id).keys())
    
    def call_depth(self, caller_id: int, callee_id: int) -> Optional[int]:
        """
        Get the minimum call depth from caller to callee.
        
        Args:
            caller_id: Source BHAV
            callee_id: Target BHAV
        
        Returns:
            Minimum call depth, or None if no path exists
        """
        if caller_id == callee_id:
            return 0
        
        visited = {caller_id}
        queue = [(caller_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            
            for next_id in self.direct_callees_of(current_id):
                if next_id == callee_id:
                    return depth + 1
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, depth + 1))
        
        return None
    
    def has_path(self, caller_id: int, callee_id: int) -> bool:
        """Check if there is a call path from caller to callee."""
        return self.call_depth(caller_id, callee_id) is not None
    
    def is_recursive(self, bhav_id: int) -> bool:
        """Check if BHAV can eventually call itself."""
        return self.has_path(bhav_id, bhav_id)
    
    def get_all_descendants(self, bhav_id: int) -> Set[int]:
        """
        Get all BHAVs reachable from the given BHAV.
        
        Args:
            bhav_id: Root BHAV ID
        
        Returns:
            Set of all reachable BHAV IDs
        """
        descendants = set()
        visited = {bhav_id}
        queue = [bhav_id]
        
        while queue:
            current_id = queue.pop(0)
            
            for callee_id in self.direct_callees_of(current_id):
                if callee_id not in visited:
                    descendants.add(callee_id)
                    visited.add(callee_id)
                    queue.append(callee_id)
        
        return descendants
    
    def get_all_ancestors(self, bhav_id: int) -> Set[int]:
        """
        Get all BHAVs that can eventually reach the given BHAV.
        
        Args:
            bhav_id: Target BHAV ID
        
        Returns:
            Set of all reaching BHAV IDs
        """
        ancestors = set()
        visited = {bhav_id}
        queue = [bhav_id]
        
        while queue:
            current_id = queue.pop(0)
            
            for caller_id in self.direct_callers_of(current_id):
                if caller_id not in visited:
                    ancestors.add(caller_id)
                    visited.add(caller_id)
                    queue.append(caller_id)
        
        return ancestors
    
    # Analysis Methods
    
    def get_unused_bhavs(self) -> List[int]:
        """Get list of BHAVs that are never called."""
        return self.package.get_unused_bhavs()
    
    def get_leaf_bhavs(self) -> List[int]:
        """Get list of BHAVs that don't call any other BHAVs."""
        leaves = []
        for bhav_id, xref_entry in self.xref.items():
            if xref_entry.callee_count() == 0:
                leaves.append(bhav_id)
        return leaves
    
    def get_root_bhavs(self) -> List[int]:
        """Get list of BHAVs that are never called (entry points)."""
        roots = []
        for bhav_id, xref_entry in self.xref.items():
            if xref_entry.caller_count() == 0:
                roots.append(bhav_id)
        return roots
    
    def get_most_called(self, limit: int = 10) -> List[Tuple[int, int]]:
        """
        Get BHAVs with the most callers.
        
        Args:
            limit: Maximum number of results
        
        Returns:
            List of (BHAV ID, caller count) tuples, sorted by caller count
        """
        sorted_bhavs = sorted(
            self.xref.items(),
            key=lambda x: x[1].caller_count(),
            reverse=True
        )
        return [(bhav_id, xref.caller_count()) for bhav_id, xref in sorted_bhavs[:limit]]
    
    def get_most_calling(self, limit: int = 10) -> List[Tuple[int, int]]:
        """
        Get BHAVs that call the most other BHAVs.
        
        Args:
            limit: Maximum number of results
        
        Returns:
            List of (BHAV ID, callee count) tuples, sorted by callee count
        """
        sorted_bhavs = sorted(
            self.xref.items(),
            key=lambda x: x[1].callee_count(),
            reverse=True
        )
        return [(bhav_id, xref.callee_count()) for bhav_id, xref in sorted_bhavs[:limit]]
    
    def get_call_complexity(self) -> Dict[str, float]:
        """
        Calculate call graph complexity metrics.
        
        Returns:
            Dict with metrics: avg_calls, max_calls, branching_factor, etc.
        """
        call_counts = [len(calls) for calls in self.package.call_graph.values()]
        callee_counts = [xref.callee_count() for xref in self.xref.values()]
        
        return {
            'total_bhavs': len(self.xref),
            'total_call_sites': sum(call_counts) if call_counts else 0,
            'avg_calls_per_bhav': sum(call_counts) / max(1, len(call_counts)),
            'max_calls_per_bhav': max(call_counts) if call_counts else 0,
            'avg_callees': sum(callee_counts) / max(1, len(callee_counts)),
            'max_callees': max(callee_counts) if callee_counts else 0,
            'leaf_bhavs': len(self.get_leaf_bhavs()),
            'root_bhavs': len(self.get_root_bhavs()),
            'unused_bhavs': len(self.get_unused_bhavs()),
            'has_cycles': len(self.package.cycles) > 0,
        }
    
    # Report Generation Methods
    
    def generate_call_matrix(self) -> Dict[Tuple[int, int], int]:
        """
        Generate a caller × callee matrix showing call counts.
        
        Returns:
            Dict mapping (caller_id, callee_id) → call_count
        """
        matrix = {}
        for (caller_id, callee_id), sites in self.call_matrix.items():
            matrix[(caller_id, callee_id)] = len(sites)
        return matrix
    
    def generate_csv_report(self) -> str:
        """
        Generate CSV report of all BHAV relationships.
        
        Returns:
            CSV string with columns: caller_id,callee_id,call_sites,type
        """
        lines = ["caller_id,callee_id,call_sites,call_type"]
        
        for caller_id, calls in self.package.call_graph.items():
            for call in calls:
                lines.append(
                    f"{caller_id},{call.callee_id},{len(call.instruction_indices)},{call.call_type.value}"
                )
        
        return "\n".join(lines)
    
    def generate_graph_report(self) -> Dict:
        """
        Generate graph format report compatible with GraphML/DOT.
        
        Returns:
            Dict with nodes and edges for graph visualization
        """
        nodes = []
        edges = []
        
        # Create nodes
        for bhav_id, xref in self.xref.items():
            node_type = "entry" if self.package.bhav_map[bhav_id].is_entry_point else "normal"
            nodes.append({
                "id": bhav_id,
                "label": f"BHAV {bhav_id}",
                "type": node_type,
                "callers": xref.caller_count(),
                "callees": xref.callee_count(),
            })
        
        # Create edges
        for (caller_id, callee_id), sites in self.call_matrix.items():
            edges.append({
                "source": caller_id,
                "target": callee_id,
                "weight": len(sites),
                "label": f"{len(sites)} calls",
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": self.get_call_complexity()
        }
    
    def find_circular_dependencies(self) -> List[List[int]]:
        """Get all circular dependencies (cycles) in call graph."""
        return self.package.cycles
    
    def analyze_bhav(self, bhav_id: int) -> Dict:
        """
        Generate comprehensive analysis of a single BHAV.
        
        Args:
            bhav_id: BHAV to analyze
        
        Returns:
            Dict with detailed information about the BHAV
        """
        if bhav_id not in self.xref:
            return {}
        
        xref = self.xref[bhav_id]
        metadata = self.package.bhav_map.get(bhav_id)
        
        # Check if part of any cycle
        in_cycle = False
        cycles_involved = []
        for cycle in self.package.cycles:
            if bhav_id in cycle:
                in_cycle = True
                cycles_involved.append(cycle)
        
        return {
            "bhav_id": bhav_id,
            "instructions": metadata.instruction_count if metadata else 0,
            "local_vars": metadata.local_var_count if metadata else 0,
            "arguments": metadata.argument_count if metadata else 0,
            "direct_callers": self.direct_callers_of(bhav_id),
            "direct_callees": self.direct_callees_of(bhav_id),
            "all_ancestors": list(self.get_all_ancestors(bhav_id)),
            "all_descendants": list(self.get_all_descendants(bhav_id)),
            "is_entry_point": metadata.is_entry_point if metadata else False,
            "is_leaf": xref.callee_count() == 0,
            "is_unused": xref.caller_count() == 0,
            "is_recursive": self.is_recursive(bhav_id),
            "in_cycle": in_cycle,
            "cycles_involved": cycles_involved,
        }
