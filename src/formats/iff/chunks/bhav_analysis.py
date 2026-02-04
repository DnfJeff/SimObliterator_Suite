"""
BHAV Code Analysis - Semantic analysis and quality metrics

Identifies code patterns, potential issues, and optimization opportunities.
Provides metrics on code complexity, stack usage, variable scope, etc.
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .bhav_ast import BehaviorAST, Instruction, VMVariableScope, VariableRef
from .primitive_registry import get_primitive_info, PRIMITIVE_REGISTRY


class IssueSeverity(Enum):
    """Issue severity levels"""
    INFO = 0
    WARNING = 1
    ERROR = 2


@dataclass
class CodeIssue:
    """Identified code issue"""
    instruction_index: int
    severity: IssueSeverity
    category: str
    message: str
    suggestion: Optional[str] = None


class VariableUsageAnalyzer:
    """Analyze variable usage patterns"""
    
    def __init__(self, ast: BehaviorAST):
        self.ast = ast
        self.reads = {}
        self.writes = {}
        self.unused = []
    
    def analyze(self) -> Dict[str, any]:
        """Analyze variable usage"""
        self._scan_instructions()
        
        return {
            'total_reads': sum(len(v) for v in self.reads.values()),
            'total_writes': sum(len(v) for v in self.writes.values()),
            'unused_variables': self.unused,
            'read_before_write': self._find_read_before_write(),
            'scope_usage': self._analyze_scope_usage()
        }
    
    def _scan_instructions(self):
        """Scan all instructions for variable usage"""
        for instr in self.ast.instructions:
            # Detect reads and writes based on primitive type
            if instr.opcode == 0:  # Push Variable (read)
                self._record_read(instr)
            # TODO: Add more patterns
    
    def _record_read(self, instr: Instruction):
        """Record variable read"""
        # Extract variable reference from operand
        # TODO: Implement
        pass
    
    def _record_write(self, instr: Instruction):
        """Record variable write"""
        # Extract variable reference from operand
        # TODO: Implement
        pass
    
    def _find_read_before_write(self) -> List[Tuple[str, int]]:
        """Find variables read before being written"""
        issues = []
        
        for var_key, reads in self.reads.items():
            writes = self.writes.get(var_key, [])
            
            if not writes:  # Never written
                if reads:  # But is read
                    issues.append((var_key, reads[0]))
            else:
                first_read_idx = min(reads)
                first_write_idx = min(writes)
                
                if first_read_idx < first_write_idx:
                    issues.append((var_key, first_read_idx))
        
        return issues
    
    def _analyze_scope_usage(self) -> Dict[str, int]:
        """Count usage by scope"""
        usage = {
            'PARAMETERS': 0,
            'LOCALS': 0,
            'OBJECT_DATA': 0,
            'GLOBAL': 0,
            'TEMPS': 0
        }
        
        for scope, count in usage.items():
            # Count uses
            pass
        
        return usage


class StackAnalyzer:
    """Analyze stack usage and depth"""
    
    def __init__(self, ast: BehaviorAST):
        self.ast = ast
        self.max_depth = 0
        self.current_depth = 0
        self.depth_at_instruction = {}
    
    def analyze(self) -> Dict[str, any]:
        """Analyze stack usage"""
        self._trace_stack_depth()
        
        return {
            'max_depth': self.max_depth,
            'operations': self._count_operations(),
            'imbalanced_instructions': self._find_imbalanced_stacks(),
            'potential_overflows': self._check_for_overflow()
        }
    
    def _trace_stack_depth(self):
        """Trace stack depth through all instructions"""
        self.current_depth = 0
        
        for instr in self.ast.instructions:
            prim_info = get_primitive_info(instr.opcode)
            
            # Estimate stack impact (simplified)
            if instr.opcode == 0:  # Push Variable
                self.current_depth += 1
            
            # TODO: Add more patterns from PRIMITIVE_REGISTRY
            
            self.depth_at_instruction[instr.index] = self.current_depth
            self.max_depth = max(self.max_depth, self.current_depth)
    
    def _count_operations(self) -> Dict[str, int]:
        """Count operation types"""
        counts = {
            'pushes': 0,
            'pops': 0,
            'comparisons': 0,
            'calls': 0,
            'branches': 0
        }
        
        for instr in self.ast.instructions:
            if instr.opcode == 0:
                counts['pushes'] += 1
            elif instr.opcode == 1:
                counts['comparisons'] += 1
            elif instr.opcode == 18:
                counts['calls'] += 1
            elif instr.is_conditional():
                counts['branches'] += 1
        
        return counts
    
    def _find_imbalanced_stacks(self) -> List[int]:
        """Find instructions with suspicious stack depth"""
        issues = []
        
        for idx, depth in self.depth_at_instruction.items():
            if depth < 0:
                issues.append(idx)
            elif depth > 256:  # Unreasonably deep
                issues.append(idx)
        
        return issues
    
    def _check_for_overflow(self) -> List[int]:
        """Check for potential stack overflow"""
        max_safe_depth = 1024  # Arbitrary limit
        issues = []
        
        for idx, depth in self.depth_at_instruction.items():
            if depth > max_safe_depth:
                issues.append(idx)
        
        return issues


class ComplexityAnalyzer:
    """Measure code complexity"""
    
    def __init__(self, ast: BehaviorAST):
        self.ast = ast
    
    def analyze(self) -> Dict[str, any]:
        """Analyze complexity metrics"""
        return {
            'cyclomatic_complexity': self._cyclomatic_complexity(),
            'instruction_count': len(self.ast.instructions),
            'nesting_depth': self._max_nesting_depth(),
            'function_calls': self._count_calls(),
            'variables_used': self._count_variables()
        }
    
    def _cyclomatic_complexity(self) -> int:
        """Calculate cyclomatic complexity"""
        branches = sum(1 for instr in self.ast.instructions if instr.is_conditional())
        return max(1, branches + 1)
    
    def _max_nesting_depth(self) -> int:
        """Calculate maximum nesting depth (loops/branches)"""
        if not self.ast.cfg:
            return 1
        
        # Simple approximation: count nested control structures
        depth = 0
        max_depth = 0
        
        # TODO: Implement proper nesting analysis
        
        return max_depth
    
    def _count_calls(self) -> int:
        """Count function calls"""
        return sum(1 for instr in self.ast.instructions if instr.opcode == 18)
    
    def _count_variables(self) -> int:
        """Count unique variables used"""
        variables = set()
        
        # TODO: Scan operands for variable references
        
        return len(variables)


class BHAVLinter:
    """Lint BHAV code for issues"""
    
    def __init__(self, ast: BehaviorAST):
        self.ast = ast
        self.issues: List[CodeIssue] = []
    
    def lint(self) -> List[CodeIssue]:
        """Run all lint checks"""
        self._check_unreachable_code()
        self._check_stack_issues()
        self._check_variable_issues()
        self._check_performance()
        self._check_logic_errors()
        
        return sorted(self.issues, key=lambda x: x.instruction_index)
    
    def _check_unreachable_code(self):
        """Find unreachable code using control flow graph"""
        if not self.ast.cfg or not self.ast.instructions:
            return
        
        # Mark first instruction as always reachable
        reachable = set([0])
        
        # Build reachability set from control flow
        for i, instr in enumerate(self.ast.instructions):
            if i in reachable:
                # Mark branch targets as reachable
                if hasattr(instr, 'true_pointer'):
                    reachable.add(instr.true_pointer)
                if hasattr(instr, 'false_pointer'):
                    reachable.add(instr.false_pointer)
                # Fall-through to next instruction
                if not hasattr(instr, 'is_terminal') or not instr.is_terminal():
                    reachable.add(i + 1)
        
        # Report unreachable instructions
        for i, instr in enumerate(self.ast.instructions):
            if i not in reachable and i > 0:
                self.issues.append(CodeIssue(
                    instruction_index=i,
                    severity=IssueSeverity.WARNING,
                    category="Dead Code",
                    message="Instruction is unreachable in all execution paths",
                    suggestion="Remove dead code or adjust control flow"
                ))
    
    def _check_stack_issues(self):
        """Check for stack depth problems"""
        # Track stack depth through execution
        depth = 0
        
        for i, instr in enumerate(self.ast.instructions):
            # Estimate stack effect based on opcode
            if instr.opcode == 0:  # Push Variable
                depth += 1
            elif instr.opcode == 1:  # Compare
                depth = max(0, depth - 2)  # Consumes 2
            elif instr.opcode == 11:  # Get Distance To
                depth = max(0, depth - 1) + 1  # Consumes 1, produces 1
            
            # Check for negative stack (popping from empty)
            if depth < 0:
                self.issues.append(CodeIssue(
                    instruction_index=i,
                    severity=IssueSeverity.ERROR,
                    category="Stack Imbalance",
                    message="Stack underflow: attempting to pop from empty stack",
                    suggestion="Check instruction sequence and operand dependencies"
                ))
                depth = 0  # Reset to continue analysis
            
            # Check for excessive depth
            if depth > 256:
                self.issues.append(CodeIssue(
                    instruction_index=i,
                    severity=IssueSeverity.WARNING,
                    category="Stack Imbalance",
                    message=f"Excessive stack depth ({depth}): possible logic error",
                    suggestion="Review stack operations and control flow"
                ))
    
    def _check_variable_issues(self):
        """Check variable usage issues"""
        # Track variable scope access
        written_vars = set()
        
        for i, instr in enumerate(self.ast.instructions):
            operand = getattr(instr, 'operand', None)
            
            # Check parameter usage bounds
            if i == 0 and self.ast.arg_count == 0:
                if hasattr(operand, 'Variable') and operand.Variable.scope == VMVariableScope.PARAMETERS:
                    self.issues.append(CodeIssue(
                        instruction_index=i,
                        severity=IssueSeverity.WARNING,
                        category="Variable Scope Issue",
                        message="Using parameter but arg_count is 0",
                        suggestion="Set correct arg_count or remove parameter access"
                    ))
            
            # Check local variable bounds
            if hasattr(operand, 'Variable') and operand.Variable.scope == VMVariableScope.LOCALS:
                local_idx = operand.Variable.offset
                if local_idx >= self.ast.local_count:
                    self.issues.append(CodeIssue(
                        instruction_index=i,
                        severity=IssueSeverity.ERROR,
                        category="Variable Scope Issue",
                        message=f"Accessing local variable at offset {local_idx} but local_count is {self.ast.local_count}",
                        suggestion="Increase local_count or fix variable offset"
                    ))
            
            # Check read before write for temps
            if hasattr(operand, 'Variable') and operand.Variable.scope == VMVariableScope.TEMPS:
                var_key = f"temp_{operand.Variable.offset}"
                if instr.opcode == 0 and var_key not in written_vars:  # Push Variable (read)
                    self.issues.append(CodeIssue(
                        instruction_index=i,
                        severity=IssueSeverity.WARNING,
                        category="Uninitialized Variable",
                        message=f"Temporary variable temp_{operand.Variable.offset} read before being written",
                        suggestion="Initialize temporary variable before use"
                    ))
                elif instr.opcode in [18, 19]:  # Store operations (write)
                    written_vars.add(var_key)
    
    def _check_performance(self):
        """Check for performance issues"""
        call_count = sum(1 for instr in self.ast.instructions if instr.opcode == 18)
        push_count = sum(1 for instr in self.ast.instructions if instr.opcode == 0)
        
        # High function call count
        if call_count > 50:
            self.issues.append(CodeIssue(
                instruction_index=0,
                severity=IssueSeverity.INFO,
                category="Performance",
                message=f"High number of function calls ({call_count}): may impact performance",
                suggestion="Consider inlining or refactoring into smaller behaviors"
            ))
        
        # Excessive variable pushes (redundant loads)
        if len(self.ast.instructions) > 0 and push_count > len(self.ast.instructions) * 0.7:
            self.issues.append(CodeIssue(
                instruction_index=0,
                severity=IssueSeverity.INFO,
                category="Performance",
                message=f"High ratio of variable loads ({push_count}/{len(self.ast.instructions)}): possible redundant operations",
                suggestion="Look for repeated variable reads that could be cached"
            ))
        
        # Very long behavior (>200 instructions)
        if len(self.ast.instructions) > 200:
            self.issues.append(CodeIssue(
                instruction_index=0,
                severity=IssueSeverity.INFO,
                category="Performance",
                message=f"Large behavior ({len(self.ast.instructions)} instructions): may be slow",
                suggestion="Consider splitting into multiple smaller behaviors"
            ))
    
    def _check_logic_errors(self):
        """Check for common logic errors"""
        # Detect infinite loops and suspicious control flow
        for i, instr in enumerate(self.ast.instructions):
            # Self-branching (infinite loop)
            if hasattr(instr, 'true_pointer') and hasattr(instr, 'false_pointer'):
                if instr.true_pointer == i:
                    self.issues.append(CodeIssue(
                        instruction_index=i,
                        severity=IssueSeverity.ERROR,
                        category="Infinite Loop",
                        message="True branch loops back to same instruction (infinite loop)",
                        suggestion="Review branch target logic"
                    ))
                if instr.false_pointer == i:
                    self.issues.append(CodeIssue(
                        instruction_index=i,
                        severity=IssueSeverity.ERROR,
                        category="Infinite Loop",
                        message="False branch loops back to same instruction (infinite loop)",
                        suggestion="Review branch target logic"
                    ))
            
            # Both branches point to same location (pointless conditional)
            if hasattr(instr, 'true_pointer') and hasattr(instr, 'false_pointer'):
                if instr.true_pointer == instr.false_pointer and instr.true_pointer != i:
                    self.issues.append(CodeIssue(
                        instruction_index=i,
                        severity=IssueSeverity.WARNING,
                        category="Logic Error",
                        message="Both branches point to same location: pointless conditional",
                        suggestion="Remove unnecessary branch or fix target pointers"
                    ))
            
            # Branch to end of behavior
            if hasattr(instr, 'true_pointer') and hasattr(instr, 'false_pointer'):
                max_instr = len(self.ast.instructions) - 1
                if ((instr.true_pointer is not None and instr.true_pointer > max_instr) or 
                    (instr.false_pointer is not None and instr.false_pointer > max_instr)):
                    self.issues.append(CodeIssue(
                        instruction_index=i,
                        severity=IssueSeverity.ERROR,
                        category="Logic Error",
                        message="Branch target points past end of behavior",
                        suggestion="Verify branch target indices"
                    ))
            
            # Backwards branch creating potential loop
            if hasattr(instr, 'true_pointer') and hasattr(instr, 'false_pointer'):
                if instr.true_pointer is not None and instr.true_pointer < i and instr.true_pointer > 0:
                    self.issues.append(CodeIssue(
                        instruction_index=i,
                        severity=IssueSeverity.INFO,
                        category="Potential Loop",
                        message="True branch goes backwards (loop detected)",
                        suggestion="Verify loop termination condition"
                    ))
                if instr.false_pointer is not None and instr.false_pointer < i and instr.false_pointer > 0:
                    self.issues.append(CodeIssue(
                        instruction_index=i,
                        severity=IssueSeverity.INFO,
                        category="Potential Loop",
                        message="False branch goes backwards (loop detected)",
                        suggestion="Verify loop termination condition"
                    ))


class CodeMetrics:
    """Collect overall code metrics"""
    
    def __init__(self, ast: BehaviorAST):
        self.ast = ast
    
    def get_metrics(self) -> Dict[str, any]:
        """Get comprehensive metrics"""
        var_analyzer = VariableUsageAnalyzer(self.ast)
        stack_analyzer = StackAnalyzer(self.ast)
        complexity_analyzer = ComplexityAnalyzer(self.ast)
        
        return {
            'variables': var_analyzer.analyze(),
            'stack': stack_analyzer.analyze(),
            'complexity': complexity_analyzer.analyze(),
            'estimated_lines': len(self.ast.instructions) // 2,  # Rough estimate
            'argument_count': self.ast.arg_count,
            'local_count': self.ast.local_count
        }


def lint_bhav(ast: BehaviorAST) -> List[CodeIssue]:
    """Quick lint function"""
    linter = BHAVLinter(ast)
    return linter.lint()


def analyze_bhav(ast: BehaviorAST) -> Dict[str, any]:
    """Quick analysis function"""
    metrics = CodeMetrics(ast)
    return metrics.get_metrics()
