"""
BHAV Authoring — Create BHAV instructions from scratch.

Provides builders for common primitives so users can construct
instructions without hex editing. Inspired by Codex's Expression
primitive builder, but extended to all common primitives.

This addresses the community pain point: "Make lines in functions.
One at a time. I'd love for it to also create the BHAV from scratch,
but that's secondary to creating the individual lines of code."
"""

import struct
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Callable, Any
from enum import IntEnum


class OperandType(IntEnum):
    """Types of operand fields."""
    LITERAL = 0      # Direct value
    VARIABLE = 1     # Variable scope + index
    ENUM = 2         # Choice from list
    FLAGS = 3        # Bitmask
    BHAV_REF = 4     # Reference to BHAV
    STR_REF = 5      # Reference to string
    ANIM_REF = 6     # Reference to animation


@dataclass
class OperandSpec:
    """Specification for a single operand field."""
    name: str
    type: OperandType
    offset: int          # Byte offset in 16-byte operand block
    size: int = 2        # Size in bytes (1, 2, or 4)
    choices: Optional[Dict[int, str]] = None  # For enum types
    default: int = 0
    description: str = ""
    mask: int = 0xFFFF   # For flags or partial reads
    shift: int = 0       # Bit shift for masked values


@dataclass
class InstructionBuilder:
    """
    Builder for a specific primitive type.
    
    Generates valid 16-byte operand blocks from user-friendly parameters.
    """
    opcode: int
    name: str
    operand_specs: List[OperandSpec] = field(default_factory=list)
    description: str = ""
    
    def build_operand(self, **kwargs) -> bytes:
        """
        Build operand bytes from named parameters.
        
        Args:
            **kwargs: Named parameters matching operand specs
            
        Returns:
            16-byte operand block
        """
        data = bytearray(16)
        
        for spec in self.operand_specs:
            value = kwargs.get(spec.name, spec.default)
            
            # Apply mask and shift if needed
            if spec.shift:
                value = (value << spec.shift) & spec.mask
            
            # Pack into data
            if spec.size == 1:
                data[spec.offset] = value & 0xFF
            elif spec.size == 2:
                struct.pack_into('<H', data, spec.offset, value & 0xFFFF)
            elif spec.size == 4:
                struct.pack_into('<I', data, spec.offset, value & 0xFFFFFFFF)
        
        return bytes(data)
    
    def get_defaults(self) -> Dict[str, int]:
        """Get default values for all operands."""
        return {spec.name: spec.default for spec in self.operand_specs}


@dataclass 
class BHAVInstruction:
    """
    A single BHAV instruction ready for insertion.
    """
    opcode: int
    operand: bytes  # 16 bytes
    true_target: int = 254   # Default: true exit
    false_target: int = 255  # Default: false exit
    
    def to_bytes(self) -> bytes:
        """Convert to binary instruction format."""
        # Standard BHAV instruction format
        return struct.pack('<HBB16s', 
                           self.opcode,
                           self.true_target,
                           self.false_target,
                           self.operand)
    
    @property
    def opcode_hex(self) -> str:
        return f"0x{self.opcode:04X}"


# ============================================================================
# PRIMITIVE BUILDERS
# ============================================================================

# Variable scopes for expression/generic use
VARIABLE_SCOPES = {
    0x00: "My",
    0x01: "Stack Object",
    0x02: "Target Object",
    0x03: "My Object's Owner",
    0x04: "Global",
    0x05: "Literal",
    0x06: "Local",
    0x07: "Temps",
    0x08: "Parameters",
    0x09: "BCON",
    0x0A: "Lot",
    0x0B: "Object Definition",
    0x0C: "Neighborhood Data",
    0x0D: "Attribute",
    0x19: "Stack Object ID",
    0x1A: "Tuning",
}

# Expression operators
EXPRESSION_OPERATORS = {
    0x00: "Set (=)",
    0x01: "Add (+=)",
    0x02: "Subtract (-=)",
    0x03: "Multiply (*=)",
    0x04: "Divide (/=)",
    0x05: "Increment (++)",
    0x06: "Decrement (--)",
    0x07: "Greater Than (>)",
    0x08: "Less Than (<)",
    0x09: "Equal To (==)",
    0x0A: "Add Abs",
    0x0B: "Sub Abs",
    0x0C: "Not Equal (!=)",
    0x0D: "Greater/Equal (>=)",
    0x0E: "Less/Equal (<=)",
    0x0F: "Modulo (%)",
    0x10: "Bitwise AND (&)",
    0x11: "Bitwise OR (|)",
    0x12: "Bitwise NOT (~)",
    0x13: "Set Sign",
    0x14: "Abs",
}


def build_expression_primitive() -> InstructionBuilder:
    """
    Expression primitive builder (opcode 0x02).
    
    The Expression primitive is one of the most commonly used.
    Performs arithmetic and comparison operations on variables.
    """
    return InstructionBuilder(
        opcode=0x02,
        name="Expression",
        description="Perform arithmetic or comparison on variables",
        operand_specs=[
            OperandSpec(
                name="dest_scope",
                type=OperandType.ENUM,
                offset=0,
                size=1,
                choices=VARIABLE_SCOPES,
                default=0x06,  # Local
                description="Destination variable scope"
            ),
            OperandSpec(
                name="dest_index",
                type=OperandType.LITERAL,
                offset=2,
                size=2,
                default=0,
                description="Destination variable index"
            ),
            OperandSpec(
                name="src_scope",
                type=OperandType.ENUM,
                offset=4,
                size=1,
                choices=VARIABLE_SCOPES,
                default=0x05,  # Literal
                description="Source variable scope"
            ),
            OperandSpec(
                name="src_index",
                type=OperandType.LITERAL,
                offset=6,
                size=2,
                default=0,
                description="Source value or variable index"
            ),
            OperandSpec(
                name="operator",
                type=OperandType.ENUM,
                offset=8,
                size=1,
                choices=EXPRESSION_OPERATORS,
                default=0x00,  # Set
                description="Operation to perform"
            ),
        ]
    )


def build_sleep_primitive() -> InstructionBuilder:
    """Sleep primitive builder (opcode 0x00)."""
    return InstructionBuilder(
        opcode=0x00,
        name="Sleep",
        description="Pause execution for specified ticks",
        operand_specs=[
            OperandSpec(
                name="scope",
                type=OperandType.ENUM,
                offset=0,
                size=1,
                choices=VARIABLE_SCOPES,
                default=0x05,  # Literal
                description="Sleep duration source"
            ),
            OperandSpec(
                name="ticks",
                type=OperandType.LITERAL,
                offset=2,
                size=2,
                default=10,
                description="Number of ticks to sleep"
            ),
        ]
    )


def build_gosub_primitive() -> InstructionBuilder:
    """Gosub primitive builder (opcode 0x04)."""
    return InstructionBuilder(
        opcode=0x04,
        name="Gosub",
        description="Call another BHAV and return",
        operand_specs=[
            OperandSpec(
                name="bhav_id",
                type=OperandType.BHAV_REF,
                offset=0,
                size=2,
                default=0x1000,
                description="BHAV ID to call (4096+ for local)"
            ),
            OperandSpec(
                name="param_0",
                type=OperandType.LITERAL,
                offset=2,
                size=2,
                default=0,
                description="Parameter 0 to pass"
            ),
            OperandSpec(
                name="param_1",
                type=OperandType.LITERAL,
                offset=4,
                size=2,
                default=0,
                description="Parameter 1 to pass"
            ),
            OperandSpec(
                name="param_2",
                type=OperandType.LITERAL,
                offset=6,
                size=2,
                default=0,
                description="Parameter 2 to pass"
            ),
            OperandSpec(
                name="param_3",
                type=OperandType.LITERAL,
                offset=8,
                size=2,
                default=0,
                description="Parameter 3 to pass"
            ),
        ]
    )


def build_animate_primitive() -> InstructionBuilder:
    """Animate primitive builder (opcode 0x01)."""
    return InstructionBuilder(
        opcode=0x01,
        name="Animate",
        description="Play an animation on the object",
        operand_specs=[
            OperandSpec(
                name="anim_index",
                type=OperandType.LITERAL,
                offset=0,
                size=2,
                default=0,
                description="Animation index"
            ),
            OperandSpec(
                name="object_type",
                type=OperandType.ENUM,
                offset=2,
                size=1,
                choices={0: "Me", 1: "Stack Object"},
                default=0,
                description="Which object to animate"
            ),
            OperandSpec(
                name="anim_source",
                type=OperandType.ENUM,
                offset=3,
                size=1,
                choices={0: "Object Anims", 1: "Person Anims"},
                default=0,
                description="Animation table source"
            ),
            OperandSpec(
                name="expected_events",
                type=OperandType.LITERAL,
                offset=4,
                size=1,
                default=0,
                description="Expected sound/effect events"
            ),
        ]
    )


def build_random_number_primitive() -> InstructionBuilder:
    """Random Number primitive builder (opcode 0x08)."""
    return InstructionBuilder(
        opcode=0x08,
        name="Random Number",
        description="Generate random number in range",
        operand_specs=[
            OperandSpec(
                name="dest_scope",
                type=OperandType.ENUM,
                offset=0,
                size=1,
                choices=VARIABLE_SCOPES,
                default=0x07,  # Temps
                description="Destination scope"
            ),
            OperandSpec(
                name="dest_index",
                type=OperandType.LITERAL,
                offset=2,
                size=2,
                default=0,
                description="Destination variable index"
            ),
            OperandSpec(
                name="range_scope",
                type=OperandType.ENUM,
                offset=4,
                size=1,
                choices=VARIABLE_SCOPES,
                default=0x05,  # Literal
                description="Range source scope"
            ),
            OperandSpec(
                name="range_value",
                type=OperandType.LITERAL,
                offset=6,
                size=2,
                default=100,
                description="Max value (result is 0 to value-1)"
            ),
        ]
    )


def build_set_motive_primitive() -> InstructionBuilder:
    """Set Motive primitive builder (opcode 0x5F)."""
    return InstructionBuilder(
        opcode=0x5F,
        name="Set Motive",
        description="Set or adjust a Sim's motive level",
        operand_specs=[
            OperandSpec(
                name="motive",
                type=OperandType.ENUM,
                offset=0,
                size=1,
                choices={
                    0: "Hunger", 1: "Comfort", 2: "Hygiene",
                    3: "Bladder", 4: "Energy", 5: "Fun",
                    6: "Social", 7: "Room"
                },
                default=0,
                description="Which motive to modify"
            ),
            OperandSpec(
                name="value_scope",
                type=OperandType.ENUM,
                offset=2,
                size=1,
                choices=VARIABLE_SCOPES,
                default=0x05,  # Literal
                description="Value source scope"
            ),
            OperandSpec(
                name="value",
                type=OperandType.LITERAL,
                offset=4,
                size=2,
                default=100,
                description="Value to set or add"
            ),
            OperandSpec(
                name="mode",
                type=OperandType.ENUM,
                offset=6,
                size=1,
                choices={0: "Set", 1: "Add", 2: "Subtract"},
                default=0,
                description="How to apply value"
            ),
        ]
    )


# Registry of all available builders
PRIMITIVE_BUILDERS: Dict[int, Callable[[], InstructionBuilder]] = {
    0x00: build_sleep_primitive,
    0x01: build_animate_primitive,
    0x02: build_expression_primitive,
    0x04: build_gosub_primitive,
    0x08: build_random_number_primitive,
    0x5F: build_set_motive_primitive,
}


class BHAVFactory:
    """
    Factory for creating BHAVs and instructions from scratch.
    """
    
    BHAV_HEADER_SIZE = 76  # Standard BHAV header size
    
    @classmethod
    def get_builder(cls, opcode: int) -> Optional[InstructionBuilder]:
        """Get builder for a specific opcode."""
        if opcode in PRIMITIVE_BUILDERS:
            return PRIMITIVE_BUILDERS[opcode]()
        return None
    
    @classmethod
    def list_available_primitives(cls) -> List[Dict[str, Any]]:
        """List all primitives with builders available."""
        result = []
        for opcode, builder_fn in PRIMITIVE_BUILDERS.items():
            builder = builder_fn()
            result.append({
                "opcode": opcode,
                "opcode_hex": f"0x{opcode:02X}",
                "name": builder.name,
                "description": builder.description,
                "operands": [spec.name for spec in builder.operand_specs],
            })
        return result
    
    @classmethod
    def create_instruction(cls, opcode: int, 
                          true_target: int = 254, 
                          false_target: int = 255,
                          **operands) -> BHAVInstruction:
        """
        Create a new instruction using a builder.
        
        Args:
            opcode: Primitive opcode
            true_target: True branch target (254 = exit true)
            false_target: False branch target (255 = exit false)
            **operands: Operand values keyed by spec name
            
        Returns:
            BHAVInstruction ready for insertion
        """
        builder = cls.get_builder(opcode)
        
        if builder:
            operand_bytes = builder.build_operand(**operands)
        else:
            # Generic: just use zeros
            operand_bytes = bytes(16)
        
        return BHAVInstruction(
            opcode=opcode,
            operand=operand_bytes,
            true_target=true_target,
            false_target=false_target,
        )
    
    @classmethod
    def create_bhav(cls, bhav_id: int, 
                   instructions: List[BHAVInstruction],
                   flags: int = 0,
                   tree_type: int = 0,
                   num_params: int = 0,
                   num_locals: int = 0) -> bytes:
        """
        Create a complete BHAV chunk from scratch.
        
        Args:
            bhav_id: BHAV chunk ID
            instructions: List of instructions
            flags: BHAV flags
            tree_type: Tree type indicator
            num_params: Number of parameters
            num_locals: Number of local variables
            
        Returns:
            Complete BHAV chunk data
        """
        parts = []
        
        # Header (simplified - real format may vary)
        header = bytearray(16)
        header[0:2] = struct.pack('<H', len(instructions))  # Instruction count
        header[2] = tree_type
        header[3] = num_params
        header[4] = num_locals
        header[5] = flags & 0xFF
        parts.append(bytes(header))
        
        # Instructions
        for instr in instructions:
            parts.append(instr.to_bytes())
        
        return b''.join(parts)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_expression(dest_scope: int, dest_index: int,
                     operator: int, 
                     src_scope: int = 0x05, src_index: int = 0) -> BHAVInstruction:
    """
    Create an Expression instruction with simplified parameters.
    
    Common operators:
        0x00 = Set (=)
        0x01 = Add (+=)
        0x02 = Subtract (-=)
        0x07 = Greater Than
        0x09 = Equal
    """
    return BHAVFactory.create_instruction(
        0x02,
        dest_scope=dest_scope,
        dest_index=dest_index,
        src_scope=src_scope,
        src_index=src_index,
        operator=operator,
    )


def create_sleep(ticks: int) -> BHAVInstruction:
    """Create a Sleep instruction with literal tick count."""
    return BHAVFactory.create_instruction(0x00, scope=0x05, ticks=ticks)


def create_gosub(bhav_id: int, *params) -> BHAVInstruction:
    """Create a Gosub instruction to call another BHAV."""
    kwargs = {"bhav_id": bhav_id}
    for i, p in enumerate(params[:4]):
        kwargs[f"param_{i}"] = p
    return BHAVFactory.create_instruction(0x04, **kwargs)


def create_random(dest_scope: int, dest_index: int, 
                  max_value: int) -> BHAVInstruction:
    """Create a Random Number instruction."""
    return BHAVFactory.create_instruction(
        0x08,
        dest_scope=dest_scope,
        dest_index=dest_index,
        range_scope=0x05,  # Literal
        range_value=max_value,
    )
