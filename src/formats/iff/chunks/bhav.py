"""
BHAV Chunk - Behavior Scripts (SimAntics)
Port of FreeSO's tso.files/Formats/IFF/Chunks/BHAV.cs

BHAV chunks contain SimAntics bytecode - the scripting language for object behaviors.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer


@dataclass
class BHAVInstruction:
    """
    A single SimAntics instruction.
    
    Attributes:
        opcode: The operation code (primitive ID or sub-call)
        true_pointer: Next instruction if condition true (or always for non-conditional)
        false_pointer: Next instruction if condition false
        operand: 8 bytes of operand data (meaning depends on opcode)
    """
    opcode: int = 0
    true_pointer: int = 0      # 0xFD = error, 0xFE = false, 0xFF = true
    false_pointer: int = 0
    operand: bytes = field(default_factory=lambda: bytes(8))
    breakpoint: bool = False   # Runtime only
    
    # Special pointer values
    RETURN_TRUE = 0xFF
    RETURN_FALSE = 0xFE
    RETURN_ERROR = 0xFD
    
    def is_primitive(self) -> bool:
        """Is this a primitive call (vs subroutine)?"""
        return self.opcode < 256
    
    def __str__(self) -> str:
        op_hex = f"0x{self.opcode:04X}"
        return f"[{op_hex}] T:{self.true_pointer} F:{self.false_pointer}"


@register_chunk("BHAV")
@dataclass
class BHAV(IffChunk):
    """
    Behavior chunk - contains SimAntics bytecode.
    Maps to: FSO.Files.Formats.IFF.Chunks.BHAV
    
    SimAntics is a stack-based VM where each instruction can branch
    to a true or false target, or return from the routine.
    """
    instructions: list[BHAVInstruction] = field(default_factory=list)
    type: int = 0          # Function type
    args: int = 0          # Number of arguments
    locals: int = 0        # Number of local variables
    version: int = 0       # Script version
    file_version: int = 0  # File format version
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read BHAV chunk from stream."""
        self.file_version = io.read_uint16()
        count = 0
        
        if self.file_version == 0x8000:
            count = io.read_uint16()
            io.skip(8)
            
        elif self.file_version == 0x8001:
            count = io.read_uint16()
            io.skip(8)  # Unknown bytes
            
        elif self.file_version == 0x8002:
            count = io.read_uint16()
            self.type = io.read_byte()
            self.args = io.read_byte()
            self.locals = io.read_uint16()
            self.version = io.read_uint16()
            io.skip(2)
            
        elif self.file_version == 0x8003:
            self.type = io.read_byte()
            self.args = io.read_byte()
            self.locals = io.read_byte()
            io.skip(2)
            self.version = io.read_uint16()
            count = io.read_uint32()
        
        # Read instructions
        self.instructions = []
        for _ in range(count):
            inst = BHAVInstruction()
            inst.opcode = io.read_uint16()
            inst.true_pointer = io.read_byte()
            inst.false_pointer = io.read_byte()
            inst.operand = io.read_bytes(8)
            self.instructions.append(inst)
    
    def get_instruction(self, index: int) -> Optional[BHAVInstruction]:
        """Get instruction by index."""
        if 0 <= index < len(self.instructions):
            return self.instructions[index]
        return None
    
    def __len__(self) -> int:
        return len(self.instructions)
    
    def __getitem__(self, index: int) -> BHAVInstruction:
        return self.instructions[index]
    
    def __iter__(self):
        return iter(self.instructions)
    
    def disassemble(self) -> str:
        """Get a simple disassembly of the behavior."""
        lines = [
            f"BHAV #{self.chunk_id}: {self.chunk_label}",
            f"  Args: {self.args}, Locals: {self.locals}, Type: {self.type}",
            f"  Instructions: {len(self.instructions)}",
            ""
        ]
        
        for i, inst in enumerate(self.instructions):
            true_str = self._pointer_str(inst.true_pointer)
            false_str = self._pointer_str(inst.false_pointer)
            op_str = f"0x{inst.opcode:04X}"
            operand_hex = inst.operand.hex()
            lines.append(f"  {i:3d}: [{op_str}] T→{true_str} F→{false_str}  ({operand_hex})")
        
        return "\n".join(lines)
    
    def _pointer_str(self, ptr: int) -> str:
        if ptr == 0xFF:
            return "TRUE"
        elif ptr == 0xFE:
            return "FALSE"
        elif ptr == 0xFD:
            return "ERROR"
        else:
            return f"{ptr:3d}"
    
    def __str__(self) -> str:
        return f"BHAV #{self.chunk_id}: {self.chunk_label} ({len(self.instructions)} instructions)"
