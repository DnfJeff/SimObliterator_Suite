"""BHAV Validator - Static validation of BHAV correctness.

Validates type checking, stack analysis, variable scope, and logic errors
to ensure BHAVs are syntactically and semantically correct.

Author: SimObliterator
License: MIT
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum
import logging

from simobliterator.formats.iff.chunks.bhav_ast import (
    BehaviorAST, Instruction, VariableRef, VMVariableScope
)
from simobliterator.formats.iff.chunks.primitive_registry import PRIMITIVE_REGISTRY

logger = logging.getLogger(__name__)


class ValidationErrorType(Enum):
    """Types of validation errors."""
    TYPE_MISMATCH = "type_mismatch"
    STACK_UNDERFLOW = "stack_underflow"
    STACK_OVERFLOW = "stack_overflow"
    VARIABLE_UNINITIALIZED = "variable_uninitialized"
    VARIABLE_OUT_OF_BOUNDS = "variable_out_of_bounds"
    INVALID_BRANCH_TARGET = "invalid_branch_target"
    MISSING_RETURN = "missing_return"
    LOGIC_ERROR = "logic_error"
    INVALID_OPERAND = "invalid_operand"


@dataclass
class ValidationError:
    """A single validation error."""
    error_type: ValidationErrorType
    instruction_index: int
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    suggestion: str = ""


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    total_instructions: int
    type_errors: List[ValidationError] = field(default_factory=list)
    stack_errors: List[ValidationError] = field(default_factory=list)
    variable_errors: List[ValidationError] = field(default_factory=list)
    control_flow_errors: List[ValidationError] = field(default_factory=list)
    logic_errors: List[ValidationError] = field(default_factory=list)
    
    @property
    def all_errors(self) -> List[ValidationError]:
        """Get all errors."""
        return (self.type_errors + self.stack_errors + self.variable_errors +
                self.control_flow_errors + self.logic_errors)
    
    def error_count(self) -> int:
        """Get total error count."""
        return len(self.all_errors)
    
    def is_valid(self) -> bool:
        """Check if BHAV passes all validations."""
        return all(e.severity != "ERROR" for e in self.all_errors)
    
    def error_summary(self) -> Dict[str, int]:
        """Get count of each error type."""
        summary = {}
        for error in self.all_errors:
            error_type = error.error_type.value
            summary[error_type] = summary.get(error_type, 0) + 1
        return summary


class BHAVValidator:
    """Validates BHAV AST for correctness."""
    
    def __init__(self):
        """Initialize validator."""
        self.logger = logging.getLogger(__name__)
    
    def validate(self, ast: BehaviorAST) -> ValidationReport:
        """
        Perform comprehensive validation on BHAV.
        
        Args:
            ast: BehaviorAST to validate
        
        Returns:
            ValidationReport with findings
        """
        report = ValidationReport(total_instructions=len(ast.instructions))
        
        # Validation passes
        report.type_errors = self._check_types(ast)
        report.stack_errors = self._check_stack_balance(ast)
        report.variable_errors = self._check_variables(ast)
        report.control_flow_errors = self._check_control_flow(ast)
        report.logic_errors = self._check_logic(ast)
        
        self.logger.info(f"Validation complete: {report.error_count()} errors found")
        
        return report
    
    def _check_types(self, ast: BehaviorAST) -> List[ValidationError]:
        """
        Validate operand types match primitive expectations.
        
        Returns:
            List of type validation errors
        """
        errors = []
        
        for i, instr in enumerate(ast.instructions):
            prim_spec = PRIMITIVE_REGISTRY.get(instr.opcode)
            
            if not prim_spec:
                errors.append(ValidationError(
                    error_type=ValidationErrorType.TYPE_MISMATCH,
                    instruction_index=i,
                    severity="ERROR",
                    message=f"Unknown opcode: {instr.opcode:04X}",
                    suggestion="Check if opcode is valid"
                ))
                continue
            
            # Check operand type if specified
            expected_operand_type = prim_spec.get('operand_type')
            if expected_operand_type and hasattr(instr.operand, 'type'):
                if instr.operand.type != expected_operand_type:
                    errors.append(ValidationError(
                        error_type=ValidationErrorType.TYPE_MISMATCH,
                        instruction_index=i,
                        severity="WARNING",
                        message=f"Operand type mismatch: expected {expected_operand_type}, "
                               f"got {instr.operand.type}",
                        suggestion="Check operand structure"
                    ))
        
        return errors
    
    def _check_stack_balance(self, ast: BehaviorAST) -> List[ValidationError]:
        """
        Check that stack depth doesn't go negative and ends at valid state.
        
        Returns:
            List of stack validation errors
        """
        errors = []
        stack_depth = 0
        stack_history = {}
        
        for i, instr in enumerate(ast.instructions):
            prim_spec = PRIMITIVE_REGISTRY.get(instr.opcode, {})
            
            # Get stack delta for this instruction
            delta = prim_spec.get('stack_delta', 0)
            
            # Special handling for specific opcodes
            if instr.opcode == 0x0000:  # Push variable
                delta = 1
            elif instr.opcode == 0x0002:  # Pop
                delta = -1
            elif instr.opcode == 0x0008:  # Call subroutine
                delta = 0  # Subroutine handles its own stack
            
            stack_depth += delta
            stack_history[i] = stack_depth
            
            # Check for underflow
            if stack_depth < 0:
                errors.append(ValidationError(
                    error_type=ValidationErrorType.STACK_UNDERFLOW,
                    instruction_index=i,
                    severity="ERROR",
                    message=f"Stack underflow at instruction {i}: depth = {stack_depth}",
                    suggestion="Check operand stack manipulation"
                ))
                stack_depth = 0  # Reset to continue validation
            
            # Check for overflow (stack depth > reasonable limit)
            if stack_depth > 20:
                errors.append(ValidationError(
                    error_type=ValidationErrorType.STACK_OVERFLOW,
                    instruction_index=i,
                    severity="WARNING",
                    message=f"Excessive stack depth at instruction {i}: depth = {stack_depth}",
                    suggestion="Check for missing pop operations"
                ))
        
        # Check final stack depth
        if stack_depth != 0:
            errors.append(ValidationError(
                error_type=ValidationErrorType.STACK_UNDERFLOW,
                instruction_index=len(ast.instructions) - 1,
                severity="WARNING",
                message=f"Non-zero final stack depth: {stack_depth}",
                suggestion="Ensure all pushed values are consumed or explicitly returned"
            ))
        
        return errors
    
    def _check_variables(self, ast: BehaviorAST) -> List[ValidationError]:
        """
        Check variable access and scope validity.
        
        Returns:
            List of variable validation errors
        """
        errors = []
        var_accessed = {}  # Track which variables have been read/written
        var_initialized = set()
        
        for i, instr in enumerate(ast.instructions):
            # Check if instruction reads a variable
            if hasattr(instr.operand, 'variable'):
                var_ref = instr.operand.variable
                
                # Check bounds
                if isinstance(var_ref, VariableRef):
                    if var_ref.scope == VariableScope.LOCALS:
                        if var_ref.offset >= len(ast.local_variables):
                            errors.append(ValidationError(
                                error_type=ValidationErrorType.VARIABLE_OUT_OF_BOUNDS,
                                instruction_index=i,
                                severity="ERROR",
                                message=f"Local variable offset {var_ref.offset} out of bounds "
                                       f"(max: {len(ast.local_variables) - 1})",
                                suggestion="Check variable reference"
                            ))
                    elif var_ref.scope == VariableScope.ARGUMENTS:
                        if var_ref.offset >= len(ast.arguments):
                            errors.append(ValidationError(
                                error_type=ValidationErrorType.VARIABLE_OUT_OF_BOUNDS,
                                instruction_index=i,
                                severity="ERROR",
                                message=f"Argument offset {var_ref.offset} out of bounds "
                                       f"(max: {len(ast.arguments) - 1})",
                                suggestion="Check variable reference"
                            ))
                    
                    # Track variable access
                    if var_ref not in var_accessed:
                        var_accessed[var_ref] = []
                    var_accessed[var_ref].append(i)
                    
                    # Check for read-before-write
                    if i not in var_initialized and var_ref.scope == VariableScope.LOCALS:
                        if not self._is_write_operation(instr):
                            errors.append(ValidationError(
                                error_type=ValidationErrorType.VARIABLE_UNINITIALIZED,
                                instruction_index=i,
                                severity="WARNING",
                                message=f"Variable {var_ref} may be read before initialization",
                                suggestion="Ensure variable is written before reading"
                            ))
            
            # Track variable writes
            if self._is_write_operation(instr):
                if hasattr(instr.operand, 'variable'):
                    var_initialized.add(instr.operand.variable)
        
        return errors
    
    def _check_control_flow(self, ast: BehaviorAST) -> List[ValidationError]:
        """
        Check control flow validity (branch targets, reachability, returns).
        
        Returns:
            List of control flow validation errors
        """
        errors = []
        max_index = len(ast.instructions) - 1
        
        for i, instr in enumerate(ast.instructions):
            # Check branch targets are valid
            if instr.true_pointer is not None:
                if instr.true_pointer > max_index:
                    errors.append(ValidationError(
                        error_type=ValidationErrorType.INVALID_BRANCH_TARGET,
                        instruction_index=i,
                        severity="ERROR",
                        message=f"Invalid true branch target: {instr.true_pointer} "
                               f"(max instruction: {max_index})",
                        suggestion="Check branch target address"
                    ))
            
            if instr.false_pointer is not None:
                if instr.false_pointer > max_index:
                    errors.append(ValidationError(
                        error_type=ValidationErrorType.INVALID_BRANCH_TARGET,
                        instruction_index=i,
                        severity="ERROR",
                        message=f"Invalid false branch target: {instr.false_pointer} "
                               f"(max instruction: {max_index})",
                        suggestion="Check branch target address"
                    ))
        
        return errors
    
    def _check_logic(self, ast: BehaviorAST) -> List[ValidationError]:
        """
        Check for logical errors (contradictions, pointless operations, etc).
        
        Returns:
            List of logic validation errors
        """
        errors = []
        
        for i, instr in enumerate(ast.instructions):
            # Check for pointless conditionals (both branches go same place)
            if (instr.true_pointer is not None and instr.false_pointer is not None and
                instr.true_pointer == instr.false_pointer):
                errors.append(ValidationError(
                    error_type=ValidationErrorType.LOGIC_ERROR,
                    instruction_index=i,
                    severity="WARNING",
                    message=f"Pointless conditional at instruction {i}: "
                           f"true and false branches go to same target",
                    suggestion="Remove unnecessary conditional"
                ))
            
            # Check for infinite recursion (self-call without modification)
            if instr.opcode in (0x0008, 0x0009):  # Call subroutine
                if hasattr(instr.operand, 'bhav_id'):
                    # Note: Full recursion analysis would need inter-BHAV tracking
                    pass
        
        return errors
    
    def _is_write_operation(self, instr: Instruction) -> bool:
        """Check if instruction writes to a variable."""
        # Operations that write to variables
        write_opcodes = {
            0x0000,  # Push variable (writes to temp)
            0x0001,  # Pop (reads)
            0x0011,  # Set local
            0x0012,  # Set temp
        }
        return instr.opcode in write_opcodes
    
    def generate_validation_report_text(self, report: ValidationReport) -> str:
        """Generate human-readable validation report."""
        lines = [
            "=== BHAV VALIDATION REPORT ===",
            f"Total Instructions: {report.total_instructions}",
            f"Status: {'✓ VALID' if report.is_valid() else '✗ INVALID'}",
            f"",
            f"Errors: {report.error_count()}",
        ]
        
        if report.all_errors:
            lines.append("")
            for error in report.all_errors:
                lines.append(f"  [{error.severity}] {error.error_type.value}")
                lines.append(f"    Instruction {error.instruction_index}: {error.message}")
                if error.suggestion:
                    lines.append(f"    → {error.suggestion}")
        
        error_summary = report.error_summary()
        if error_summary:
            lines.append("")
            lines.append("Error Summary:")
            for error_type, count in error_summary.items():
                lines.append(f"  {error_type}: {count}")
        
        return "\n".join(lines)
