"""BHAV Package Decompiler - Decompiles entire object packages with cross-BHAV tracking.

This module provides functionality to decompile all BHAVs in an object file and track
their relationships (subroutine calls, state interactions, etc.).

Author: SimObliterator
License: MIT
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum
import logging

from simobliterator.formats.iff.chunks.bhav_decompiler import BHAVDecompiler
from simobliterator.formats.iff.chunks.bhav_ast import BehaviorAST, Instruction
from simobliterator.formats.iff.iff_file import IffFile
from simobliterator.formats.iff.chunks.bhav import BHAV

logger = logging.getLogger(__name__)


class CallType(Enum):
    """Type of BHAV-to-BHAV relationship."""
    SUBROUTINE = "subroutine"  # Direct BHAV call
    CALLBACK = "callback"  # Set as callback for future execution
    INTERACTION = "interaction"  # Part of interaction chain
    AUTONOMOUS = "autonomous"  # Autonomous decision behavior


@dataclass
class BHAVCall:
    """Represents a call from one BHAV to another."""
    caller_id: int
    callee_id: int
    call_type: CallType
    instruction_indices: List[int] = field(default_factory=list)
    operand_data: Dict = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash((self.caller_id, self.callee_id, self.call_type))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BHAVCall):
            return NotImplemented
        return (self.caller_id == other.caller_id and 
                self.callee_id == other.callee_id and
                self.call_type == other.call_type)


@dataclass
class BHAVMetadata:
    """Metadata about a single BHAV in a package."""
    bhav_id: int
    bhav_name: Optional[str]
    ast: BehaviorAST
    instruction_count: int
    local_var_count: int
    argument_count: int
    callers: List[BHAVCall] = field(default_factory=list)
    callees: List[BHAVCall] = field(default_factory=list)
    is_entry_point: bool = False
    is_used: bool = True


@dataclass
class PackageAST:
    """AST for entire object package - collection of BHAVs."""
    package_id: Optional[int]
    bhav_map: Dict[int, BHAVMetadata] = field(default_factory=dict)
    call_graph: Dict[int, List[BHAVCall]] = field(default_factory=dict)
    cycles: List[List[int]] = field(default_factory=list)
    
    def add_behavior(self, bhav_id: int, ast: BehaviorAST, name: Optional[str] = None):
        """Add a decompiled BHAV to package."""
        metadata = BHAVMetadata(
            bhav_id=bhav_id,
            bhav_name=name,
            ast=ast,
            instruction_count=len(ast.instructions),
            local_var_count=len(ast.local_variables),
            argument_count=len(ast.arguments)
        )
        self.bhav_map[bhav_id] = metadata
    
    def add_call(self, bhav_call: BHAVCall):
        """Add a call relationship between BHAVs."""
        if bhav_call.caller_id not in self.call_graph:
            self.call_graph[bhav_call.caller_id] = []
        self.call_graph[bhav_call.caller_id].append(bhav_call)
        
        # Update metadata
        if bhav_call.caller_id in self.bhav_map:
            self.bhav_map[bhav_call.caller_id].callees.append(bhav_call)
        if bhav_call.callee_id in self.bhav_map:
            self.bhav_map[bhav_call.callee_id].callers.append(bhav_call)
    
    def get_callers_of(self, bhav_id: int) -> List[BHAVCall]:
        """Get all BHAVs that call the given BHAV."""
        return self.bhav_map.get(bhav_id, BHAVMetadata(bhav_id, None, BehaviorAST(), 0, 0, 0)).callers
    
    def get_callees_of(self, bhav_id: int) -> List[BHAVCall]:
        """Get all BHAVs called by the given BHAV."""
        return self.bhav_map.get(bhav_id, BHAVMetadata(bhav_id, None, BehaviorAST(), 0, 0, 0)).callees
    
    def get_unused_bhavs(self) -> List[int]:
        """Return list of BHAV IDs that are never called."""
        unused = []
        for bhav_id, metadata in self.bhav_map.items():
            if not metadata.callers and not metadata.is_entry_point:
                unused.append(bhav_id)
        return unused


class BHAVPackageDecompiler:
    """Decompiles entire BHAV packages with cross-reference tracking."""
    
    def __init__(self):
        """Initialize package decompiler."""
        self.bhav_decompiler = BHAVDecompiler()
        self.logger = logging.getLogger(__name__)
    
    def decompile_package(self, iff: IffFile, package_id: Optional[int] = None) -> PackageAST:
        """
        Decompile all BHAVs in an IFF object file.
        
        Args:
            iff: IFF file containing BHAV chunks
            package_id: Optional identifier for this package
        
        Returns:
            PackageAST containing all decompiled BHAVs and relationships
        """
        package_ast = PackageAST(package_id=package_id)
        
        # Step 1: Decompile all BHAV chunks
        bhav_chunks = iff.get_by_type_code('BHAV')
        self.logger.info(f"Found {len(bhav_chunks)} BHAV chunks in package")
        
        for bhav_chunk in bhav_chunks:
            try:
                ast = self.bhav_decompiler.decompile(bhav_chunk)
                package_ast.add_behavior(bhav_chunk.chunk_id, ast)
                self.logger.debug(f"Decompiled BHAV {bhav_chunk.chunk_id}")
            except Exception as e:
                self.logger.error(f"Failed to decompile BHAV {bhav_chunk.chunk_id}: {e}")
        
        # Step 2: Analyze BHAV-to-BHAV calls
        self._analyze_subroutine_calls(package_ast, iff)
        
        # Step 3: Detect cycles in call graph
        package_ast.cycles = self._detect_cycles(package_ast)
        
        # Step 4: Mark entry points and unused BHAVs
        self._identify_entry_points(package_ast, iff)
        
        self.logger.info(f"Package decompilation complete: {len(package_ast.bhav_map)} BHAVs, "
                        f"{len(package_ast.call_graph)} call sites")
        
        return package_ast
    
    def _analyze_subroutine_calls(self, package_ast: PackageAST, iff: IffFile) -> None:
        """
        Analyze BHAV-to-BHAV subroutine calls and relationships.
        
        Detects:
        - Direct subroutine calls (CallBHAV, CallSubroutine)
        - Callback registration (SetCallback, OnInteraction)
        - Object/Avatar creation with initial BHAVs
        """
        for bhav_id, metadata in package_ast.bhav_map.items():
            for instr in metadata.ast.instructions:
                # Check for subroutine call primitives
                if instr.opcode in (0x0008, 0x0009):  # CallBHAV, CallSubroutine
                    callee_id = self._extract_bhav_id_from_operand(instr)
                    if callee_id is not None:
                        call = BHAVCall(
                            caller_id=bhav_id,
                            callee_id=callee_id,
                            call_type=CallType.SUBROUTINE,
                            instruction_indices=[instr.index]
                        )
                        package_ast.add_call(call)
                        self.logger.debug(f"Found call: BHAV {bhav_id} → BHAV {callee_id} "
                                        f"at instruction {instr.index}")
                
                # Check for callback registration
                elif instr.opcode in (0x002C, 0x002D):  # SetCallback, OnInteraction
                    callee_id = self._extract_bhav_id_from_operand(instr)
                    if callee_id is not None:
                        call = BHAVCall(
                            caller_id=bhav_id,
                            callee_id=callee_id,
                            call_type=CallType.CALLBACK,
                            instruction_indices=[instr.index]
                        )
                        package_ast.add_call(call)
    
    def _extract_bhav_id_from_operand(self, instr: Instruction) -> Optional[int]:
        """Extract BHAV ID from instruction operand."""
        try:
            if hasattr(instr.operand, 'bhav_id'):
                return instr.operand.bhav_id
            elif isinstance(instr.operand, dict) and 'BhavID' in instr.operand:
                return instr.operand['BhavID']
        except (AttributeError, KeyError, TypeError):
            pass
        return None
    
    def _detect_cycles(self, package_ast: PackageAST) -> List[List[int]]:
        """
        Detect cycles in the BHAV call graph using DFS.
        
        Returns:
            List of cycles, where each cycle is a list of BHAV IDs
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(bhav_id: int) -> None:
            visited.add(bhav_id)
            rec_stack.add(bhav_id)
            path.append(bhav_id)
            
            for call in package_ast.call_graph.get(bhav_id, []):
                if call.callee_id not in visited:
                    dfs(call.callee_id)
                elif call.callee_id in rec_stack:
                    # Found cycle
                    cycle_start = path.index(call.callee_id)
                    cycle = path[cycle_start:] + [call.callee_id]
                    cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(bhav_id)
        
        for bhav_id in package_ast.bhav_map:
            if bhav_id not in visited:
                dfs(bhav_id)
        
        if cycles:
            self.logger.warning(f"Found {len(cycles)} cycles in BHAV call graph")
            for cycle in cycles:
                self.logger.warning(f"  Cycle: {' → '.join(map(str, cycle))}")
        
        return cycles
    
    def _identify_entry_points(self, package_ast: PackageAST, iff: IffFile) -> None:
        """
        Identify entry point BHAVs.
        
        Entry points are typically:
        - Garden/lot main BHAV (0)
        - Sim object main BHAV (if exists)
        - Interaction starter BHAVs
        """
        # BHAV 0 is typically the main/entry point for objects
        if 0 in package_ast.bhav_map:
            package_ast.bhav_map[0].is_entry_point = True
        
        # Mark all called BHAVs as used
        called_ids = set()
        for calls in package_ast.call_graph.values():
            called_ids.update(call.callee_id for call in calls)
        
        for bhav_id in package_ast.bhav_map:
            if bhav_id not in called_ids and bhav_id != 0:
                package_ast.bhav_map[bhav_id].is_used = False
    
    def get_call_chain(self, package_ast: PackageAST, start_id: int, 
                       max_depth: int = 10) -> Dict[int, int]:
        """
        Get call chain from a starting BHAV showing call depths.
        
        Args:
            package_ast: Package AST
            start_id: Starting BHAV ID
            max_depth: Maximum recursion depth
        
        Returns:
            Dict mapping BHAV ID → depth in call chain
        """
        depths = {start_id: 0}
        queue = [(start_id, 0)]
        
        while queue:
            bhav_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            
            for call in package_ast.get_callees_of(bhav_id):
                if call.callee_id not in depths:
                    depths[call.callee_id] = depth + 1
                    queue.append((call.callee_id, depth + 1))
        
        return depths
    
    def get_statistics(self, package_ast: PackageAST) -> Dict:
        """Get package-level statistics."""
        total_instructions = sum(m.instruction_count for m in package_ast.bhav_map.values())
        total_calls = len([c for calls in package_ast.call_graph.values() for c in calls])
        unused_bhavs = package_ast.get_unused_bhavs()
        
        return {
            'total_bhavs': len(package_ast.bhav_map),
            'total_instructions': total_instructions,
            'total_call_sites': total_calls,
            'unused_bhavs': len(unused_bhavs),
            'has_cycles': len(package_ast.cycles) > 0,
            'cycle_count': len(package_ast.cycles),
            'avg_instructions_per_bhav': total_instructions / max(1, len(package_ast.bhav_map)),
        }


def decompile_iff_package(iff_path: str) -> PackageAST:
    """
    Convenience function to decompile an IFF file.
    
    Args:
        iff_path: Path to IFF file
    
    Returns:
        PackageAST with decompiled BHAVs
    """
    iff = IffFile.load(iff_path)
    decompiler = BHAVPackageDecompiler()
    return decompiler.decompile_package(iff)
