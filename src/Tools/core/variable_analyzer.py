"""
Variable Analyzer — Track variable usage within BHAVs.

Provides:
- Per-BHAV variable usage (locals, temps, params, attributes, globals)
- First-write detection
- Read-before-write detection (uninitialized variables)
- Written-but-never-read detection (dead variables)
- Cross-instruction variable flow

Works with the bhav_disassembler for instruction analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum

from .chunk_parsers import MinimalBHAV, parse_bhav
from .primitive_reference import VARIABLE_SCOPES


class VariableScope(Enum):
    """Variable scope types."""
    MY_ATTRIBUTE = 0
    STACK_OBJECT_ATTRIBUTE = 1
    MY_PERSON = 2
    STACK_OBJECT_PERSON = 3
    GLOBAL = 4
    LITERAL = 5
    LOCAL = 6
    TEMP = 7
    PARAMETER = 8
    BCON = 9
    
    @classmethod
    def from_code(cls, code: int) -> Optional['VariableScope']:
        """Convert scope code to enum."""
        try:
            return cls(code)
        except ValueError:
            return None
    
    @classmethod
    def get_name(cls, code: int) -> str:
        """Get human-readable name for scope code."""
        return VARIABLE_SCOPES.get(code, f"Unknown({code})")
    
    def is_writable(self) -> bool:
        """Check if this scope can be written to."""
        return self not in [VariableScope.LITERAL, VariableScope.BCON]
    
    def is_local_to_bhav(self) -> bool:
        """Check if this scope is local to the BHAV."""
        return self in [VariableScope.LOCAL, VariableScope.TEMP]


class AccessType(Enum):
    """Type of variable access."""
    READ = "read"
    WRITE = "write"


@dataclass
class VariableAccess:
    """A single access to a variable."""
    scope: int              # Scope code (0-26+)
    data: int               # Data value (variable index or literal)
    access_type: AccessType
    instruction_index: int  # Which instruction
    operand_position: str   # "lhs" or "rhs"
    
    @property
    def scope_name(self) -> str:
        return VariableScope.get_name(self.scope)
    
    @property
    def display_name(self) -> str:
        """Get display name like 'temp:3' or 'local:0'."""
        scope_short = {
            6: "local",
            7: "temp",
            8: "param",
            4: "global",
            0: "attr",
            1: "stack_attr",
            5: "literal",
            9: "bcon",
        }
        prefix = scope_short.get(self.scope, f"scope{self.scope}")
        return f"{prefix}:{self.data}"


@dataclass
class VariableInfo:
    """Aggregated info about a single variable."""
    scope: int
    data: int               # Index/ID within scope
    accesses: List[VariableAccess] = field(default_factory=list)
    
    @property
    def display_name(self) -> str:
        if self.accesses:
            return self.accesses[0].display_name
        return f"scope{self.scope}:{self.data}"
    
    @property
    def read_count(self) -> int:
        return sum(1 for a in self.accesses if a.access_type == AccessType.READ)
    
    @property
    def write_count(self) -> int:
        return sum(1 for a in self.accesses if a.access_type == AccessType.WRITE)
    
    @property
    def first_access_index(self) -> int:
        """Get instruction index of first access."""
        if not self.accesses:
            return -1
        return min(a.instruction_index for a in self.accesses)
    
    @property
    def first_write_index(self) -> int:
        """Get instruction index of first write."""
        writes = [a for a in self.accesses if a.access_type == AccessType.WRITE]
        if not writes:
            return -1
        return min(a.instruction_index for a in writes)
    
    @property
    def first_read_index(self) -> int:
        """Get instruction index of first read."""
        reads = [a for a in self.accesses if a.access_type == AccessType.READ]
        if not reads:
            return -1
        return min(a.instruction_index for a in reads)
    
    @property
    def is_read_before_written(self) -> bool:
        """Check if variable is read before it's written."""
        first_read = self.first_read_index
        first_write = self.first_write_index
        if first_read == -1:
            return False
        if first_write == -1:
            return True  # Read but never written
        return first_read < first_write
    
    @property
    def is_written_never_read(self) -> bool:
        """Check if variable is written but never read (dead variable)."""
        return self.write_count > 0 and self.read_count == 0
    
    @property
    def is_read_only(self) -> bool:
        """Check if variable is only read, never written."""
        return self.read_count > 0 and self.write_count == 0
    
    def get_accessing_instructions(self) -> List[int]:
        """Get all instruction indices that access this variable."""
        return sorted(set(a.instruction_index for a in self.accesses))


@dataclass
class BHAVVariableAnalysis:
    """Complete variable analysis for a BHAV."""
    bhav_id: int
    instruction_count: int
    declared_locals: int     # From BHAV header
    declared_params: int     # From BHAV header
    
    # Variables by scope, then by data index
    variables: Dict[int, Dict[int, VariableInfo]] = field(default_factory=dict)
    
    # Analysis results
    errors: List[str] = field(default_factory=list)
    
    def get_variable(self, scope: int, data: int) -> Optional[VariableInfo]:
        """Get info for a specific variable."""
        if scope not in self.variables:
            return None
        return self.variables[scope].get(data)
    
    def get_all_by_scope(self, scope: int) -> List[VariableInfo]:
        """Get all variables in a scope."""
        if scope not in self.variables:
            return []
        return list(self.variables[scope].values())
    
    def get_locals(self) -> List[VariableInfo]:
        """Get all local variables."""
        return self.get_all_by_scope(6)  # LOCAL = 6
    
    def get_temps(self) -> List[VariableInfo]:
        """Get all temp variables."""
        return self.get_all_by_scope(7)  # TEMP = 7
    
    def get_params(self) -> List[VariableInfo]:
        """Get all parameter accesses."""
        return self.get_all_by_scope(8)  # PARAMETER = 8
    
    def get_globals(self) -> List[VariableInfo]:
        """Get all global variable accesses."""
        return self.get_all_by_scope(4)  # GLOBAL = 4
    
    def get_attributes(self) -> List[VariableInfo]:
        """Get all object attribute accesses."""
        return self.get_all_by_scope(0) + self.get_all_by_scope(1)
    
    def get_uninitialized_reads(self) -> List[VariableInfo]:
        """Get variables that are read before written (potential bugs)."""
        result = []
        for scope_vars in self.variables.values():
            for var_info in scope_vars.values():
                if var_info.is_read_before_written:
                    result.append(var_info)
        return result
    
    def get_dead_variables(self) -> List[VariableInfo]:
        """Get variables that are written but never read."""
        result = []
        for scope_vars in self.variables.values():
            for var_info in scope_vars.values():
                if var_info.is_written_never_read:
                    result.append(var_info)
        return result
    
    def get_variables_for_instruction(self, instruction_index: int) -> List[VariableInfo]:
        """Get all variables accessed by a specific instruction."""
        result = []
        for scope_vars in self.variables.values():
            for var_info in scope_vars.values():
                if instruction_index in var_info.get_accessing_instructions():
                    result.append(var_info)
        return result
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        total_vars = sum(len(vars) for vars in self.variables.values())
        
        return {
            "bhav_id": f"0x{self.bhav_id:04X}",
            "instruction_count": self.instruction_count,
            "declared_locals": self.declared_locals,
            "declared_params": self.declared_params,
            "total_unique_variables": total_vars,
            "locals_used": len(self.get_locals()),
            "temps_used": len(self.get_temps()),
            "params_accessed": len(self.get_params()),
            "globals_accessed": len(self.get_globals()),
            "potential_issues": {
                "uninitialized_reads": len(self.get_uninitialized_reads()),
                "dead_variables": len(self.get_dead_variables()),
            }
        }


class BHAVVariableAnalyzer:
    """
    Analyzer for variable usage in BHAV code.
    
    Extracts variable accesses from instruction operands and tracks
    read/write patterns.
    """
    
    # Opcodes that we know how to extract variable references from
    EXPRESSION_OPCODE = 0x02
    
    def __init__(self):
        self._analysis: Optional[BHAVVariableAnalysis] = None
    
    def analyze(self, bhav: MinimalBHAV) -> BHAVVariableAnalysis:
        """
        Analyze a BHAV for variable usage.
        
        Args:
            bhav: Parsed BHAV chunk
            
        Returns:
            BHAVVariableAnalysis with all variable access info
        """
        self._analysis = BHAVVariableAnalysis(
            bhav_id=bhav.chunk_id,
            instruction_count=len(bhav.instructions),
            declared_locals=bhav.locals,
            declared_params=bhav.args,
        )
        
        for idx, inst in enumerate(bhav.instructions):
            self._analyze_instruction(idx, inst)
        
        return self._analysis
    
    def _analyze_instruction(self, idx: int, inst):
        """Analyze a single instruction for variable accesses."""
        opcode = inst.opcode
        operand = inst.operand or bytes(8)
        
        # Handle Expression primitive (most common variable access)
        if opcode == self.EXPRESSION_OPCODE:
            self._analyze_expression(idx, operand)
        
        # Handle Gosub (parameters become writes in callee)
        elif opcode == 0x04:
            self._analyze_gosub(idx, operand)
        
        # Other primitives may also access variables
        # Add more handlers as needed
    
    def _analyze_expression(self, idx: int, operand: bytes):
        """
        Analyze Expression primitive for variable accesses.
        
        Operand layout:
        [0-1]: lhs_data (uint16)
        [2-3]: rhs_data (uint16)
        [4]: flags (bit 0 = is_comparison)
        [5]: operator
        [6]: lhs_scope
        [7]: rhs_scope
        """
        if len(operand) < 8:
            return
        
        lhs_data = operand[0] | (operand[1] << 8)
        rhs_data = operand[2] | (operand[3] << 8)
        is_comparison = (operand[4] & 0x01) != 0
        lhs_scope = operand[6]
        rhs_scope = operand[7]
        
        # LHS is written for assignments, read for comparisons
        if is_comparison:
            self._record_access(lhs_scope, lhs_data, AccessType.READ, idx, "lhs")
        else:
            # Assignment: LHS is written
            if self._is_writable_scope(lhs_scope):
                self._record_access(lhs_scope, lhs_data, AccessType.WRITE, idx, "lhs")
        
        # RHS is always read (unless it's a literal, we still record for tracking)
        self._record_access(rhs_scope, rhs_data, AccessType.READ, idx, "rhs")
    
    def _analyze_gosub(self, idx: int, operand: bytes):
        """
        Analyze Gosub primitive.
        
        Parameters passed to subroutine are reads of current scope.
        """
        # For gosub, we'd need to know what the callee does with params
        # For now, just note that params 0-3 are being passed
        pass
    
    def _is_writable_scope(self, scope: int) -> bool:
        """Check if scope can be written to."""
        # Literals (5) and BCON (9) cannot be written
        return scope not in [5, 9]
    
    def _record_access(
        self,
        scope: int,
        data: int,
        access_type: AccessType,
        instruction_index: int,
        position: str
    ):
        """Record a variable access."""
        # Skip literals for variable tracking (they're constants)
        if scope == 5:  # LITERAL
            return
        
        # Ensure scope dict exists
        if scope not in self._analysis.variables:
            self._analysis.variables[scope] = {}
        
        # Ensure variable info exists
        if data not in self._analysis.variables[scope]:
            self._analysis.variables[scope][data] = VariableInfo(
                scope=scope,
                data=data
            )
        
        # Record access
        access = VariableAccess(
            scope=scope,
            data=data,
            access_type=access_type,
            instruction_index=instruction_index,
            operand_position=position
        )
        self._analysis.variables[scope][data].accesses.append(access)


def analyze_bhav_variables(bhav_data: bytes, chunk_id: int) -> Optional[BHAVVariableAnalysis]:
    """
    Convenience function to analyze BHAV variable usage.
    
    Args:
        bhav_data: Raw BHAV chunk data
        chunk_id: BHAV chunk ID
        
    Returns:
        BHAVVariableAnalysis or None if parsing fails
    """
    bhav = parse_bhav(bhav_data, chunk_id)
    if bhav is None:
        return None
    
    analyzer = BHAVVariableAnalyzer()
    return analyzer.analyze(bhav)


def get_variable_display_for_instruction(
    analysis: BHAVVariableAnalysis,
    instruction_index: int
) -> List[Dict]:
    """
    Get display info for variables used by an instruction.
    
    Returns list of dicts with:
        - name: display name (e.g., "temp:3")
        - access: "read" or "write"
        - scope_name: full scope name
    """
    result = []
    
    for var_info in analysis.get_variables_for_instruction(instruction_index):
        for access in var_info.accesses:
            if access.instruction_index == instruction_index:
                result.append({
                    "name": access.display_name,
                    "access": access.access_type.value,
                    "scope_name": access.scope_name,
                    "data": access.data,
                })
    
    return result
