"""
Primitive Reference — Enhanced SimAntics opcode documentation.

Provides:
- Opcode name and category
- Operand field definitions (bit positions, meanings)
- Yield/return behavior
- Stack requirements
- Common usage patterns

This extends opcode_loader with structured operand field information.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class OperandFieldType(Enum):
    """Types of operand fields."""
    UINT8 = "uint8"
    UINT16 = "uint16"
    INT8 = "int8"
    INT16 = "int16"
    ENUM = "enum"
    FLAGS = "flags"
    VARIABLE_SOURCE = "variable_source"
    VARIABLE_DATA = "variable_data"
    BHAV_ID = "bhav_id"


class YieldBehavior(Enum):
    """How a primitive returns/yields."""
    CONTINUES = "continues"       # Always continues (true pointer)
    RETURNS_BOOL = "returns_bool" # Returns true or false
    RETURNS_TRUE = "returns_true" # Always returns true
    RETURNS_FALSE = "returns_false" # Always returns false
    BLOCKING = "blocking"         # Blocks (yields to sim queue)
    ERROR = "error"               # Returns error (253)
    TREE_BREAK = "tree_break"     # Breaks out of tree


@dataclass
class OperandField:
    """Definition of a single operand field."""
    name: str
    field_type: OperandFieldType
    byte_offset: int          # Offset in operand (0-7)
    bit_offset: int = 0       # Bit offset within byte(s)
    bit_width: int = 8        # Width in bits
    description: str = ""
    enum_values: Dict[int, str] = field(default_factory=dict)
    
    def extract_value(self, operand: bytes) -> int:
        """Extract this field's value from operand bytes."""
        if len(operand) <= self.byte_offset:
            return 0
        
        if self.bit_width <= 8:
            value = operand[self.byte_offset]
            if self.bit_offset > 0:
                value = (value >> self.bit_offset) & ((1 << self.bit_width) - 1)
            return value
        elif self.bit_width <= 16:
            if len(operand) <= self.byte_offset + 1:
                return operand[self.byte_offset]
            low = operand[self.byte_offset]
            high = operand[self.byte_offset + 1]
            return low | (high << 8)
        return 0
    
    def format_value(self, value: int) -> str:
        """Format value for display."""
        if self.field_type == OperandFieldType.ENUM:
            return self.enum_values.get(value, f"Unknown({value})")
        elif self.field_type == OperandFieldType.FLAGS:
            parts = []
            for bit_val, name in self.enum_values.items():
                if value & bit_val:
                    parts.append(name)
            return " | ".join(parts) if parts else "None"
        elif self.field_type == OperandFieldType.BHAV_ID:
            return f"BHAV 0x{value:04X}"
        else:
            return str(value)


@dataclass
class PrimitiveDefinition:
    """Complete definition of a SimAntics primitive."""
    opcode: int
    name: str
    category: str
    description: str
    yield_behavior: YieldBehavior = YieldBehavior.RETURNS_BOOL
    operand_fields: List[OperandField] = field(default_factory=list)
    stack_requirements: str = ""
    common_patterns: List[str] = field(default_factory=list)
    notes: str = ""
    
    def decode_operand(self, operand: bytes) -> Dict[str, Tuple[int, str]]:
        """
        Decode operand bytes into named field values.
        
        Returns:
            Dict mapping field name to (raw_value, formatted_string)
        """
        result = {}
        for field_def in self.operand_fields:
            value = field_def.extract_value(operand)
            formatted = field_def.format_value(value)
            result[field_def.name] = (value, formatted)
        return result
    
    def get_operand_summary(self, operand: bytes) -> str:
        """Get human-readable summary of operand."""
        decoded = self.decode_operand(operand)
        parts = [f"{name}={formatted}" for name, (_, formatted) in decoded.items()]
        return ", ".join(parts)


# Variable source scope values (used by Expression and many other primitives)
VARIABLE_SCOPES = {
    0: "My",                    # Object's own attributes
    1: "Stack Object's",        # Stack object's attributes
    2: "My (Person)",           # Sim's person data
    3: "Stack Object's (Person)",
    4: "Global",
    5: "Literal (Value)",
    6: "Local",                 # Local variable
    7: "Temp",                  # Temporary variable
    8: "Parameter",             # Function parameter
    9: "BCON",                  # Constant from BCON
    10: "Attribute (Array)",
    11: "Temps (Array)",
    12: "Check Tree Ad (Motive)",
    13: "Check Tree Person Motive",
    14: "My Stack Object's Attribute",
    15: "Stack Object's Stack Object's",
    16: "Stack Object Comparison",
    17: "Neighbor's in Stack Object",
    18: "Object ID from param[0]",
    19: "Object ID from local[0]",
    20: "Neighbor's/Inventory",
    21: "My Motives",
    22: "Stack Object's Motives",
    23: "Me Check Tree",
    24: "Stack Object Check Tree",
    25: "Temperature",
    26: "Tuning",               # Tuning table (BCON)
}

# Comparison operators for Expression primitive
COMPARISON_OPERATORS = {
    0: "<",
    1: "<=",
    2: "==",
    3: ">=",
    4: ">",
    5: "!=",
}

# Math operators for Expression primitive
MATH_OPERATORS = {
    0: ":=",    # Assignment
    1: "+=",
    2: "-=",
    3: "*=",
    4: "/=",
    5: "%=",    # Modulo
    6: "&=",    # Bitwise AND
    7: "|=",    # Bitwise OR
    8: "^=",    # Bitwise XOR
    9: ">>=",   # Shift right
    10: "<<=",  # Shift left
}


# Built-in primitive definitions
# These are the most commonly used primitives with full field definitions

PRIMITIVE_DEFINITIONS: Dict[int, PrimitiveDefinition] = {}


def _build_expression_primitive() -> PrimitiveDefinition:
    """Build definition for Expression (opcode 0x02)."""
    return PrimitiveDefinition(
        opcode=0x02,
        name="Expression",
        category="Math/Control",
        description="Evaluate mathematical or comparison expression",
        yield_behavior=YieldBehavior.RETURNS_BOOL,
        operand_fields=[
            OperandField(
                name="lhs_data",
                field_type=OperandFieldType.UINT16,
                byte_offset=0,
                bit_width=16,
                description="Left-hand side data (meaning depends on scope)"
            ),
            OperandField(
                name="rhs_data",
                field_type=OperandFieldType.UINT16,
                byte_offset=2,
                bit_width=16,
                description="Right-hand side data (meaning depends on scope)"
            ),
            OperandField(
                name="is_comparison",
                field_type=OperandFieldType.FLAGS,
                byte_offset=4,
                bit_offset=0,
                bit_width=1,
                description="0=assignment, 1=comparison",
                enum_values={0: "Assignment", 1: "Comparison"}
            ),
            OperandField(
                name="operator",
                field_type=OperandFieldType.ENUM,
                byte_offset=5,
                bit_width=8,
                description="Operator (assignment or comparison)",
            ),
            OperandField(
                name="lhs_scope",
                field_type=OperandFieldType.ENUM,
                byte_offset=6,
                bit_width=8,
                description="Left-hand side variable scope",
                enum_values=VARIABLE_SCOPES
            ),
            OperandField(
                name="rhs_scope",
                field_type=OperandFieldType.ENUM,
                byte_offset=7,
                bit_width=8,
                description="Right-hand side variable scope",
                enum_values=VARIABLE_SCOPES
            ),
        ],
        stack_requirements="Stack Object used for scope 1, 3",
        common_patterns=[
            "temp:0 = stack_obj:attr[5] — copy attribute to temp",
            "local:0 == literal:5 — compare local to constant",
        ],
        notes="Most flexible primitive. Is_comparison flag determines operator set."
    )


def _build_gosub_primitive() -> PrimitiveDefinition:
    """Build definition for Gosub (opcode 0x04)."""
    return PrimitiveDefinition(
        opcode=0x04,
        name="Gosub",
        category="Control",
        description="Call another BHAV and return",
        yield_behavior=YieldBehavior.RETURNS_BOOL,
        operand_fields=[
            OperandField(
                name="bhav_id",
                field_type=OperandFieldType.BHAV_ID,
                byte_offset=0,
                bit_width=16,
                description="BHAV ID to call (local: 4096+, global: 0-4095)"
            ),
            OperandField(
                name="param0",
                field_type=OperandFieldType.UINT8,
                byte_offset=2,
                description="Parameter 0 to pass"
            ),
            OperandField(
                name="param1",
                field_type=OperandFieldType.UINT8,
                byte_offset=3,
                description="Parameter 1 to pass"
            ),
            OperandField(
                name="param2",
                field_type=OperandFieldType.UINT8,
                byte_offset=4,
                description="Parameter 2 to pass"
            ),
            OperandField(
                name="param3",
                field_type=OperandFieldType.UINT8,
                byte_offset=5,
                description="Parameter 3 to pass"
            ),
        ],
        stack_requirements="None",
        common_patterns=[
            "Call utility BHAV with constants",
            "Delegate to specialized handler",
        ],
        notes="BHAV IDs 256-4095 are global, 4096+ are local to object"
    )


def _build_sleep_primitive() -> PrimitiveDefinition:
    """Build definition for Sleep (opcode 0x00)."""
    return PrimitiveDefinition(
        opcode=0x00,
        name="Sleep",
        category="Control",
        description="Pause execution for specified ticks",
        yield_behavior=YieldBehavior.BLOCKING,
        operand_fields=[
            OperandField(
                name="ticks",
                field_type=OperandFieldType.UINT16,
                byte_offset=0,
                bit_width=16,
                description="Number of ticks to sleep"
            ),
        ],
        stack_requirements="None",
        common_patterns=[
            "Sleep 30 — wait ~1 second",
        ],
        notes="Yields control to sim engine. Blocking primitive."
    )


def _build_animation_primitive() -> PrimitiveDefinition:
    """Build definition for Animate (opcode 0x01)."""
    return PrimitiveDefinition(
        opcode=0x01,
        name="Animate",
        category="Animation",
        description="Play animation on sim or object",
        yield_behavior=YieldBehavior.BLOCKING,
        operand_fields=[
            OperandField(
                name="animation_id",
                field_type=OperandFieldType.UINT16,
                byte_offset=0,
                bit_width=16,
                description="Animation ID to play"
            ),
            OperandField(
                name="flags",
                field_type=OperandFieldType.FLAGS,
                byte_offset=2,
                bit_width=8,
                description="Animation flags",
                enum_values={
                    0x01: "Loop",
                    0x02: "Reverse",
                    0x04: "Reset",
                }
            ),
        ],
        stack_requirements="Stack Object is target of animation",
        notes="Blocking primitive. Returns when animation completes."
    )


def _build_change_suit_primitive() -> PrimitiveDefinition:
    """Build definition for Change Suit (opcode 0x22)."""
    return PrimitiveDefinition(
        opcode=0x22,
        name="Change Suit/Access",
        category="Sim Control",
        description="Change sim's outfit or accessory",
        yield_behavior=YieldBehavior.CONTINUES,
        operand_fields=[
            OperandField(
                name="suit_source",
                field_type=OperandFieldType.ENUM,
                byte_offset=0,
                bit_width=8,
                description="Source of suit definition",
                enum_values={
                    0: "Body Strings",
                    1: "Literal",
                    2: "Temp Variable",
                }
            ),
            OperandField(
                name="suit_index",
                field_type=OperandFieldType.UINT16,
                byte_offset=1,
                bit_width=16,
                description="Suit index or variable"
            ),
        ],
        stack_requirements="Stack Object is sim to change",
        notes="Used for outfit changes, accessories"
    )


def _init_definitions():
    """Initialize the built-in primitive definitions."""
    global PRIMITIVE_DEFINITIONS
    
    PRIMITIVE_DEFINITIONS = {
        0x00: _build_sleep_primitive(),
        0x01: _build_animation_primitive(),
        0x02: _build_expression_primitive(),
        0x04: _build_gosub_primitive(),
        0x22: _build_change_suit_primitive(),
    }


# Initialize on module load
_init_definitions()


def get_primitive_definition(opcode: int) -> Optional[PrimitiveDefinition]:
    """
    Get full primitive definition for an opcode.
    
    Args:
        opcode: The primitive opcode
        
    Returns:
        PrimitiveDefinition if we have detailed info, else None
    """
    return PRIMITIVE_DEFINITIONS.get(opcode)


def has_detailed_definition(opcode: int) -> bool:
    """Check if we have detailed operand field definitions for this opcode."""
    return opcode in PRIMITIVE_DEFINITIONS


def decode_operand_for_opcode(opcode: int, operand: bytes) -> Dict:
    """
    Decode operand bytes for a primitive.
    
    Args:
        opcode: The primitive opcode
        operand: 8-byte operand data
        
    Returns:
        Dict with decoded field values, or raw bytes if unknown
    """
    defn = get_primitive_definition(opcode)
    if defn:
        return defn.decode_operand(operand)
    
    # Fallback: return raw byte view
    return {
        f"byte[{i}]": (operand[i], f"0x{operand[i]:02X}") 
        for i in range(min(8, len(operand)))
    }


def get_operand_display(opcode: int, operand: bytes) -> str:
    """
    Get human-readable operand display string.
    
    Args:
        opcode: The primitive opcode
        operand: 8-byte operand data
        
    Returns:
        Formatted string describing the operand
    """
    defn = get_primitive_definition(opcode)
    if defn:
        return defn.get_operand_summary(operand)
    
    # Fallback: hex display
    return " ".join(f"{b:02X}" for b in operand[:8])


# Categories for grouping primitives in UI
PRIMITIVE_CATEGORIES = {
    "Control": [0x00, 0x04, 0x05, 0x09],  # Sleep, Gosub, etc.
    "Math/Control": [0x02],                # Expression
    "Animation": [0x01, 0x0A, 0x0B],       # Animate, etc.
    "Sim Control": [0x22, 0x23, 0x24],     # Change Suit, etc.
    "Object": [0x0C, 0x0D, 0x0E],          # Create/Destroy Object
    "Routing": [0x14, 0x15, 0x16],         # Walk, etc.
    "Social": [0x20, 0x21],                # Relationship primitives
    "Motive": [0x30, 0x31, 0x32],          # Motive adjustments
}


def get_primitives_by_category(category: str) -> List[int]:
    """Get list of opcodes in a category."""
    return PRIMITIVE_CATEGORIES.get(category, [])


def get_all_documented_categories() -> List[str]:
    """Get list of all documented categories."""
    return list(PRIMITIVE_CATEGORIES.keys())
