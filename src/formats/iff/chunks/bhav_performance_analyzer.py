"""BHAV Performance Analyzer - Identifies performance bottlenecks.

Detects dead code, inefficient patterns, and generates performance metrics
including cyclomatic complexity, nesting depth, and hot spots.

Author: SimObliterator
License: MIT
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum
import logging

from simobliterator.formats.iff.chunks.bhav_ast import BehaviorAST, Instruction
from simobliterator.formats.iff.chunks.primitive_registry import PRIMITIVE_REGISTRY

logger = logging.getLogger(__name__)


class PerformanceIssueType(Enum):
    """Types of performance issues detected."""
    DEAD_CODE = "dead_code"
    INFINITE_LOOP = "infinite_loop"
    DEEP_NESTING = "deep_nesting"
    HOT_SPOT = "hot_spot"
    UNREACHABLE = "unreachable"
    COMPLEX_LOGIC = "complex_logic"


@dataclass
class PerformanceIssue:
    """A detected performance issue."""
    issue_type: PerformanceIssueType
    instruction_index: int
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    suggestion: str


@dataclass
class LoopInfo:
    """Information about a detected loop."""
    loop_id: int
    start_index: int
    end_index: int
    estimated_iterations: Optional[int] = None
    is_infinite: bool = False
    contains_subroutine_calls: bool = False
    nesting_depth: int = 0


@dataclass
class PerformanceReport:
    """Comprehensive performance analysis report."""
    total_instructions: int
    dead_code_blocks: List[int] = field(default_factory=list)
    loops: List[LoopInfo] = field(default_factory=list)
    infinite_loops: List[LoopInfo] = field(default_factory=list)
    hot_spots: List[Tuple[int, int, str]] = field(default_factory=list)  # (index, primitive, reason)
    issues: List[PerformanceIssue] = field(default_factory=list)
    
    # Metrics
    cyclomatic_complexity: int = 0
    max_nesting_depth: int = 0
    avg_nesting_depth: float = 0.0
    code_coverage: float = 1.0  # Percentage of instructions reachable
    
    def issue_count(self) -> int:
        """Get total number of issues found."""
        return len(self.issues)
    
    def error_count(self) -> int:
        """Get number of error-level issues."""
        return sum(1 for i in self.issues if i.severity == "ERROR")
    
    def warning_count(self) -> int:
        """Get number of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == "WARNING")


class BHAVPerformanceAnalyzer:
    """Analyzes BHAV for performance issues."""
    
    def __init__(self):
        """Initialize performance analyzer."""
        self.logger = logging.getLogger(__name__)
    
    def analyze(self, ast: BehaviorAST) -> PerformanceReport:
        """
        Perform comprehensive performance analysis on BHAV.
        
        Args:
            ast: BehaviorAST to analyze
        
        Returns:
            PerformanceReport with findings
        """
        report = PerformanceReport(total_instructions=len(ast.instructions))
        
        # Analysis passes
        report.dead_code_blocks = self._find_dead_code(ast)
        report.loops = self._analyze_loops(ast)
        report.infinite_loops = self._detect_infinite_loops(ast)
        report.hot_spots = self._find_hot_spots(ast)
        report.cyclomatic_complexity = self._calculate_cyclomatic_complexity(ast)
        report.max_nesting_depth = self._calculate_max_nesting_depth(ast)
        report.avg_nesting_depth = self._calculate_avg_nesting_depth(ast)
        report.code_coverage = self._calculate_code_coverage(ast)
        
        # Generate issues
        report.issues = self._generate_issues(ast, report)
        
        return report
    
    def _find_dead_code(self, ast: BehaviorAST) -> List[int]:
        """
        Identify unreachable code blocks using BFS reachability analysis.
        
        Returns:
            List of instruction indices that are unreachable
        """
        if not ast.instructions:
            return []
        
        reachable = set()
        queue = [0]
        reachable.add(0)
        
        while queue:
            idx = queue.pop(0)
            if idx >= len(ast.instructions):
                continue
            
            instr = ast.instructions[idx]
            
            # Add unconditional next instruction
            if instr.opcode not in (0xFFFF,):  # Not a terminator
                next_idx = idx + 1
                if next_idx < len(ast.instructions) and next_idx not in reachable:
                    reachable.add(next_idx)
                    queue.append(next_idx)
            
            # Add branch targets
            if instr.true_pointer is not None and instr.true_pointer not in reachable:
                reachable.add(instr.true_pointer)
                queue.append(instr.true_pointer)
            
            if instr.false_pointer is not None and instr.false_pointer not in reachable:
                reachable.add(instr.false_pointer)
                queue.append(instr.false_pointer)
        
        # Dead code = not reachable
        dead_code = [i for i in range(len(ast.instructions)) if i not in reachable]
        
        if dead_code:
            self.logger.warning(f"Found {len(dead_code)} unreachable instructions")
        
        return dead_code
    
    def _analyze_loops(self, ast: BehaviorAST) -> List[LoopInfo]:
        """
        Detect loops by finding backward branches.
        
        Returns:
            List of detected loops
        """
        loops = []
        loop_id = 0
        visited_backward = set()
        
        for i, instr in enumerate(ast.instructions):
            # Check for backward branches
            backward_targets = []
            
            if instr.true_pointer is not None and instr.true_pointer < i:
                backward_targets.append(instr.true_pointer)
            
            if instr.false_pointer is not None and instr.false_pointer < i:
                backward_targets.append(instr.false_pointer)
            
            for target in backward_targets:
                if target not in visited_backward:
                    visited_backward.add(target)
                    
                    loop = LoopInfo(
                        loop_id=loop_id,
                        start_index=target,
                        end_index=i,
                        nesting_depth=self._calculate_nesting_depth_at(ast, target)
                    )
                    
                    # Check for subroutine calls in loop
                    loop.contains_subroutine_calls = any(
                        ast.instructions[j].opcode in (0x0008, 0x0009)
                        for j in range(target, i + 1)
                    )
                    
                    loops.append(loop)
                    loop_id += 1
        
        self.logger.info(f"Found {len(loops)} loops")
        return loops
    
    def _detect_infinite_loops(self, ast: BehaviorAST) -> List[LoopInfo]:
        """
        Detect potential infinite loops (self-branching, circular references).
        
        Returns:
            List of detected infinite loops
        """
        infinite = []
        
        for loop in self._analyze_loops(ast):
            # Check for self-branching (instruction branches to itself)
            instr = ast.instructions[loop.end_index]
            if instr.true_pointer == loop.end_index or instr.false_pointer == loop.end_index:
                loop.is_infinite = True
                infinite.append(loop)
                self.logger.warning(
                    f"Found infinite loop: {loop.start_index}-{loop.end_index}"
                )
            
            # Check for loops with no exit condition
            # (This would require more sophisticated analysis)
        
        return infinite
    
    def _find_hot_spots(self, ast: BehaviorAST) -> List[Tuple[int, int, str]]:
        """
        Identify hot spots: expensive operations in loops or frequently called.
        
        Returns:
            List of (instruction_index, opcode, reason) tuples
        """
        hot_spots = []
        loops = self._analyze_loops(ast)
        
        # Expensive opcodes
        expensive_ops = {
            0x0014: "Create Object Instance",  # Object creation
            0x0015: "Create Sim Description",
            0x000A: "Change Suit",
            0x000B: "Drop",
            0x001C: "Transfer Funds",  # Financial operations
        }
        
        for i, instr in enumerate(ast.instructions):
            if instr.opcode in expensive_ops:
                # Check if in loop
                in_loop = any(loop.start_index <= i <= loop.end_index for loop in loops)
                
                if in_loop:
                    hot_spots.append((
                        i,
                        instr.opcode,
                        f"Expensive operation in loop: {expensive_ops[instr.opcode]}"
                    ))
                    self.logger.warning(
                        f"Found hot spot at instruction {i}: {expensive_ops[instr.opcode]} in loop"
                    )
        
        return hot_spots
    
    def _calculate_cyclomatic_complexity(self, ast: BehaviorAST) -> int:
        """
        Calculate cyclomatic complexity (number of independent paths through code).
        
        Formula: CC = E - N + 2P
        where E = edges, N = nodes, P = connected components
        
        Simplified: CC = number of branches + 1
        """
        branch_count = sum(
            1 for instr in ast.instructions
            if instr.true_pointer is not None or instr.false_pointer is not None
        )
        return branch_count + 1
    
    def _calculate_max_nesting_depth(self, ast: BehaviorAST) -> int:
        """Calculate maximum nesting depth in instruction sequence."""
        max_depth = 0
        for i in range(len(ast.instructions)):
            depth = self._calculate_nesting_depth_at(ast, i)
            max_depth = max(max_depth, depth)
        return max_depth
    
    def _calculate_avg_nesting_depth(self, ast: BehaviorAST) -> float:
        """Calculate average nesting depth."""
        if not ast.instructions:
            return 0.0
        
        total_depth = sum(
            self._calculate_nesting_depth_at(ast, i)
            for i in range(len(ast.instructions))
        )
        return total_depth / len(ast.instructions)
    
    def _calculate_nesting_depth_at(self, ast: BehaviorAST, instr_index: int) -> int:
        """Calculate nesting depth at specific instruction."""
        depth = 0
        
        for i in range(instr_index):
            instr = ast.instructions[i]
            
            # If this instruction branches, check if we're in one of its branches
            if instr.true_pointer is not None and instr.true_pointer > instr_index:
                depth += 1
            
            if instr.false_pointer is not None and instr.false_pointer > instr_index:
                depth += 1
        
        return depth
    
    def _calculate_code_coverage(self, ast: BehaviorAST) -> float:
        """Calculate percentage of reachable code."""
        if not ast.instructions:
            return 1.0
        
        dead_code = self._find_dead_code(ast)
        reachable = len(ast.instructions) - len(dead_code)
        return reachable / len(ast.instructions)
    
    def _generate_issues(self, ast: BehaviorAST, report: PerformanceReport) -> List[PerformanceIssue]:
        """Generate performance issues from analysis."""
        issues = []
        
        # Issue: Dead code
        for idx in report.dead_code_blocks:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.DEAD_CODE,
                instruction_index=idx,
                severity="WARNING",
                message=f"Instruction {idx} is unreachable",
                suggestion="Remove or fix branch logic to reach this instruction"
            ))
        
        # Issue: Infinite loops
        for loop in report.infinite_loops:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.INFINITE_LOOP,
                instruction_index=loop.end_index,
                severity="ERROR",
                message=f"Potential infinite loop: {loop.start_index}-{loop.end_index}",
                suggestion="Add exit condition or break statement"
            ))
        
        # Issue: Hot spots
        for idx, opcode, reason in report.hot_spots:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.HOT_SPOT,
                instruction_index=idx,
                severity="WARNING",
                message=f"Performance hot spot: {reason}",
                suggestion="Consider optimizing or moving outside of loop"
            ))
        
        # Issue: Deep nesting
        if report.max_nesting_depth > 5:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.DEEP_NESTING,
                instruction_index=-1,
                severity="INFO",
                message=f"Complex nesting depth: {report.max_nesting_depth}",
                suggestion="Consider refactoring to reduce nesting"
            ))
        
        # Issue: High cyclomatic complexity
        if report.cyclomatic_complexity > 10:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.COMPLEX_LOGIC,
                instruction_index=-1,
                severity="INFO",
                message=f"High cyclomatic complexity: {report.cyclomatic_complexity}",
                suggestion="Consider breaking into multiple smaller behaviors"
            ))
        
        return issues
    
    def generate_performance_summary(self, report: PerformanceReport) -> str:
        """Generate human-readable performance summary."""
        lines = [
            "=== BHAV PERFORMANCE ANALYSIS ===",
            f"Total Instructions: {report.total_instructions}",
            f"Code Coverage: {report.code_coverage:.1%}",
            f"",
            "Complexity Metrics:",
            f"  Cyclomatic Complexity: {report.cyclomatic_complexity}",
            f"  Max Nesting Depth: {report.max_nesting_depth}",
            f"  Avg Nesting Depth: {report.avg_nesting_depth:.1f}",
            f"",
            "Issues Found:",
            f"  Errors: {report.error_count()}",
            f"  Warnings: {report.warning_count()}",
            f"",
        ]
        
        if report.dead_code_blocks:
            lines.append(f"Dead Code: {len(report.dead_code_blocks)} blocks")
        
        if report.loops:
            lines.append(f"Loops: {len(report.loops)}")
        
        if report.infinite_loops:
            lines.append(f"Infinite Loops: {len(report.infinite_loops)} ⚠️")
        
        if report.hot_spots:
            lines.append(f"Hot Spots: {len(report.hot_spots)} performance concerns")
        
        return "\n".join(lines)
