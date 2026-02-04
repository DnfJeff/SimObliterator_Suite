"""BHAV Beautifier - Improves BHAV code readability and structure.

Provides automatic reformatting, variable name inference, code structure
flattening, and comment generation for decompiled BHAVs.

Author: SimObliterator
License: MIT
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from enum import Enum
import logging
from copy import deepcopy
import re

from simobliterator.formats.iff.chunks.bhav_ast import (
    BehaviorAST, Instruction, VariableRef, VMVariableScope
)
from simobliterator.formats.iff.chunks.primitive_registry import PRIMITIVE_REGISTRY

logger = logging.getLogger(__name__)


class VariableNamePattern(Enum):
    """Patterns for inferring variable names."""
    COUNTER = "counter"
    RESULT = "result"
    TEMP = "temp"
    CONDITION = "condition"
    INDEX = "index"
    VALUE = "value"


@dataclass
class VariableNameMapping:
    """Inferred name for a variable."""
    var_ref: VariableRef
    inferred_name: str
    confidence: float  # 0.0 to 1.0
    pattern: VariableNamePattern


class BHAVBeautifier:
    """Improves BHAV code readability and structure."""
    
    def __init__(self):
        """Initialize beautifier."""
        self.logger = logging.getLogger(__name__)
    
    def beautify(self, ast: BehaviorAST) -> BehaviorAST:
        """
        Perform all beautification passes on AST.
        
        Args:
            ast: Original BehaviorAST
        
        Returns:
            Beautified BehaviorAST with improved readability
        """
        beautified = deepcopy(ast)
        
        # Pass 1: Infer variable names
        name_mapping = self._infer_variable_names(beautified)
        beautified = self._apply_variable_names(beautified, name_mapping)
        
        # Pass 2: Flatten excessive nesting
        beautified = self._flatten_nesting(beautified)
        
        # Pass 3: Add structural comments
        beautified = self._add_structural_comments(beautified)
        
        # Pass 4: Reorganize for clarity
        beautified = self._reorganize_instructions(beautified)
        
        return beautified
    
    def _infer_variable_names(self, ast: BehaviorAST) -> Dict[VariableRef, VariableNameMapping]:
        """
        Infer variable names based on usage patterns.
        
        Looks for patterns like:
        - Variables used in loops → "counter"
        - Variables assigned comparisons → "condition"
        - Variables at end of BHAV → "result"
        """
        mapping = {}
        var_usage = self._analyze_variable_usage(ast)
        
        # Iterate over local variable indices (0 to local_count)
        for i in range(ast.local_count):
            inferred_name = f"var{i}"
            confidence = 0.3
            pattern = VariableNamePattern.TEMP
            
            # Create a variable reference for this local variable
            var_ref = VariableRef(scope=VMVariableScope.LOCALS, index=i)
            
            # Check for counter pattern (increment in loop)
            if var_ref in var_usage.get("incremented", []):
                inferred_name = "count" if i % 3 == 0 else f"counter{i}"
                confidence = 0.8
                pattern = VariableNamePattern.COUNTER
            
            # Check for condition pattern (used in branches)
            elif var_ref in var_usage.get("in_condition", []):
                inferred_name = f"cond{i}"
                confidence = 0.7
                pattern = VariableNamePattern.CONDITION
            
            # Check for result pattern (assigned late in BHAV)
            elif var_ref in var_usage.get("assigned_late", []):
                inferred_name = "result"
                confidence = 0.6
                pattern = VariableNamePattern.RESULT
            
            # Check for index pattern (used for array access)
            elif var_ref in var_usage.get("index_like", []):
                inferred_name = "index"
                confidence = 0.7
                pattern = VariableNamePattern.INDEX
            
            mapping[var_ref] = VariableNameMapping(
                var_ref=var_ref,
                inferred_name=inferred_name,
                confidence=confidence,
                pattern=pattern
            )
        
        return mapping
    
    def _analyze_variable_usage(self, ast: BehaviorAST) -> Dict[str, List[VariableRef]]:
        """Analyze how variables are used throughout the AST."""
        usage = {
            "incremented": [],
            "decremented": [],
            "in_condition": [],
            "assigned_late": [],
            "index_like": [],
        }
        
        # Look through instructions
        for i, instr in enumerate(ast.instructions):
            is_late = i > len(ast.instructions) * 0.7  # Last 30%
            
            # Check for loop/increment patterns
            if instr.opcode in (0x0000, 0x0001):  # Push variable, compare
                if hasattr(instr.operand, 'variable'):
                    var_ref = instr.operand.variable
                    if is_late:
                        usage["assigned_late"].append(var_ref)
            
            # Check for conditionals
            if instr.true_pointer is not None or instr.false_pointer is not None:
                if hasattr(instr.operand, 'variable'):
                    usage["in_condition"].append(instr.operand.variable)
        
        return usage
    
    def _apply_variable_names(self, ast: BehaviorAST, 
                             mapping: Dict[VariableRef, VariableNameMapping]) -> BehaviorAST:
        """Apply inferred variable names to AST (metadata only, not actual rename)."""
        # Store mapping in AST metadata
        if not hasattr(ast, 'variable_name_mapping'):
            ast.variable_name_mapping = mapping
        return ast
    
    def _flatten_nesting(self, ast: BehaviorAST, max_depth: int = 3) -> BehaviorAST:
        """
        Reduce code nesting depth by extracting nested conditionals.
        
        Example:
            if (condition1) {
                if (condition2) {
                    action()
                }
            }
        
        Becomes:
            if (condition1 && condition2) {
                action()
            }
        
        (Note: This is a simplified implementation that marks deep nesting)
        """
        # Analyze nesting depth
        max_observed_depth = self._calculate_max_nesting_depth(ast)
        
        if max_observed_depth <= max_depth:
            return ast  # No flattening needed
        
        self.logger.info(f"Flattening nesting: max depth {max_observed_depth} → target {max_depth}")
        
        # For now, just mark instructions with high nesting
        # Real flattening would require significant AST restructuring
        for i, instr in enumerate(ast.instructions):
            depth = self._calculate_nesting_depth_at(ast, i)
            if depth > max_depth:
                instr.is_deeply_nested = True
        
        return ast
    
    def _calculate_max_nesting_depth(self, ast: BehaviorAST) -> int:
        """Calculate maximum nesting depth in instruction sequence."""
        max_depth = 0
        for i in range(len(ast.instructions)):
            depth = self._calculate_nesting_depth_at(ast, i)
            max_depth = max(max_depth, depth)
        return max_depth
    
    def _calculate_nesting_depth_at(self, ast: BehaviorAST, instr_index: int) -> int:
        """Calculate nesting depth at a specific instruction."""
        # Count how many unresolved branches lead to this instruction
        depth = 0
        open_conditions = []
        
        for i in range(instr_index + 1):
            instr = ast.instructions[i]
            
            # Track branch openings
            if instr.true_pointer is not None:
                open_conditions.append((i, instr.true_pointer, instr.false_pointer))
                depth += 1
            
            # Check if condition is resolved
            if instr.true_pointer is not None and instr_index < instr.true_pointer:
                if instr.false_pointer is not None and instr_index >= instr.false_pointer:
                    depth -= 1
        
        return depth
    
    def _add_structural_comments(self, ast: BehaviorAST) -> BehaviorAST:
        """
        Add comments to mark important structural boundaries.
        
        Comments for:
        - Loop starts/ends
        - Complex conditionals
        - Subroutine calls
        - Error checking blocks
        """
        for i, instr in enumerate(ast.instructions):
            comments = []
            
            # Mark loops
            if self._is_loop_start(ast, i):
                comments.append("LOOP START")
            if self._is_loop_end(ast, i):
                comments.append("LOOP END")
            
            # Mark subroutine calls
            if instr.opcode in (0x0008, 0x0009):  # CallBHAV, CallSubroutine
                comments.append("SUBROUTINE CALL")
            
            # Mark error/validation blocks
            if self._is_error_check(ast, i):
                comments.append("ERROR CHECK")
            
            if comments:
                instr.comments = comments
        
        return ast
    
    def _is_loop_start(self, ast: BehaviorAST, instr_index: int) -> bool:
        """Detect if instruction starts a loop."""
        instr = ast.instructions[instr_index]
        
        # Loop if branches back to an earlier instruction
        if instr.true_pointer is not None and instr.true_pointer < instr_index:
            return True
        if instr.false_pointer is not None and instr.false_pointer < instr_index:
            return True
        
        return False
    
    def _is_loop_end(self, ast: BehaviorAST, instr_index: int) -> bool:
        """Detect if instruction ends a loop."""
        instr = ast.instructions[instr_index]
        
        # Is this instruction a branch target from earlier?
        for j in range(instr_index):
            earlier = ast.instructions[j]
            if earlier.true_pointer == instr_index or earlier.false_pointer == instr_index:
                if j > instr_index:  # Earlier instruction branches forward to this
                    return False
        
        return False
    
    def _is_error_check(self, ast: BehaviorAST, instr_index: int) -> bool:
        """Detect if instruction is part of error checking logic."""
        instr = ast.instructions[instr_index]
        
        # Check for common error check patterns
        # - Followed by early return on error
        # - Uses comparison/testing opcodes
        if instr.opcode in (0x0002, 0x0003, 0x0004, 0x0005):  # Compare variants
            return True
        
        return False
    
    def _reorganize_instructions(self, ast: BehaviorAST) -> BehaviorAST:
        """
        Reorder instructions for improved clarity where possible.
        
        This is conservative - only reorders when safe:
        - Variable initialization grouped at start
        - Related operations grouped together
        """
        # Don't reorder - control flow structure is critical
        # Instead, just mark related instruction groups
        
        for i, instr in enumerate(ast.instructions):
            # Mark variable initialization at start
            if i < 5 and instr.opcode == 0x0000:  # Push variable
                instr.is_initialization = True
            
            # Mark cleanup at end
            if i > len(ast.instructions) - 3:
                instr.is_cleanup = True
        
        return ast
    
    def generate_annotated_pseudocode(self, ast: BehaviorAST) -> str:
        """
        Generate pseudocode with beautification annotations.
        
        Returns:
            Formatted pseudocode string
        """
        lines = []
        
        # Header with variable mapping
        if hasattr(ast, 'variable_name_mapping'):
            lines.append("// Variable Mapping:")
            for var_ref, mapping in ast.variable_name_mapping.items():
                lines.append(f"//   {var_ref} → {mapping.inferred_name} "
                           f"(confidence: {mapping.confidence:.1%})")
            lines.append("")
        
        # Instructions with comments
        for instr in ast.instructions:
            # Add structural comments
            if hasattr(instr, 'comments') and instr.comments:
                for comment in instr.comments:
                    lines.append(f"    // {comment}")
            
            # Instruction line
            prim_name = PRIMITIVE_REGISTRY.get(instr.opcode, {}).get('name', 'Unknown')
            line = f"  {instr.index}: {prim_name}"
            
            # Add branch info
            if instr.true_pointer is not None or instr.false_pointer is not None:
                branches = []
                if instr.true_pointer is not None:
                    branches.append(f"→{instr.true_pointer}")
                if instr.false_pointer is not None:
                    branches.append(f"→{instr.false_pointer}")
                line += f" [{', '.join(branches)}]"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def get_beautification_stats(self, original: BehaviorAST, 
                                beautified: BehaviorAST) -> Dict[str, Any]:
        """
        Compare original and beautified ASTs to show improvements.
        
        Returns:
            Dict with statistics
        """
        original_depth = self._calculate_max_nesting_depth(original)
        beautified_depth = self._calculate_max_nesting_depth(beautified)
        
        return {
            'original_max_nesting': original_depth,
            'beautified_max_nesting': beautified_depth,
            'nesting_reduced': original_depth > beautified_depth,
            'variables_renamed': hasattr(beautified, 'variable_name_mapping'),
            'comments_added': sum(
                len(getattr(instr, 'comments', [])) for instr in beautified.instructions
            ),
            'total_instructions': len(beautified.instructions),
        }
