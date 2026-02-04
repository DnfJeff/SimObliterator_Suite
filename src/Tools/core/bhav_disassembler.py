"""
BHAV Disassembler - Decode SimAntics bytecode with semantic annotations

This tool takes BHAV bytecode (instructions) and produces human-readable
disassembly with full semantic annotations from the opcode reference.

Note: This disassembler is based on FreeSO (The Sims Online) opcode reference.
FreeSO and The Sims 1 were created around the same time and share similar
architecture, but may have differences. Unknown opcodes indicate:
  1. Possible Sims 1-specific primitives not in FreeSO
  2. Subroutine calls or special encoding
  3. Gaps in our current knowledge

These gaps are intentionally exposed to enable collaborative reverse engineering.

It handles:
- Instruction decoding (opcode, operands, pointers)
- Stack state tracking
- Exit code implications
- Semantic annotations (what each instruction does)
- Control flow visualization
- Variable references
- Cross-references to other BHAVs/primitives
- Unknown opcode identification and research hints
"""

import struct
import importlib.util
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from enum import Enum

# Import from same package
from .bhav_opcodes import get_opcode_info, get_category_opcodes, PRIMITIVE_INSTRUCTIONS


class ExitCode(Enum):
    """BHAV instruction exit codes."""
    CONTINUE = "CONTINUE"           # Execute next instruction
    GOTO_TRUE = "GOTO_TRUE"         # Branch to true_pointer
    GOTO_FALSE = "GOTO_FALSE"       # Branch to false_pointer
    ERROR = "ERROR"                 # Return error, execute false_pointer
    RETURN = "RETURN"               # Return from BHAV
    RETURN_TRUE = "RETURN_TRUE"     # Return true
    RETURN_FALSE = "RETURN_FALSE"   # Return false


@dataclass
class DisassembledInstruction:
    """Single disassembled instruction with all metadata."""
    
    index: int                          # Instruction index
    opcode: int                         # Raw opcode (0x0000-0xFFFF)
    opcode_name: str                    # Symbolic name (from reference)
    category: str                       # Semantic category (Control, Math, etc.)
    description: str                    # What it does
    true_pointer: int                   # Branch target (true/success)
    false_pointer: int                  # Branch target (false/error)
    operand_bytes: bytes                # Raw 8-byte operand
    operand_hex: str                    # Hex representation
    stack_effect: str                   # Stack input/output
    exit_code: str                      # Exit type
    operand_format: str                 # What operand means
    is_primitive: bool                  # Primitive (opcode<256) vs subroutine
    is_conditional: bool                # Branches on condition
    is_terminal: bool                   # Returns/errors
    is_special: bool                    # Special control opcode (0xFF**)
    
    # Optional/defaulted fields
    is_unknown: bool = False            # True if opcode not in reference
    call_target: Optional[int] = None   # If calling BHAV/primitive
    
    def format_operand(self) -> str:
        """Format operand in a readable way."""
        # Interpret operand based on opcode
        if self.opcode == 0:  # Sleep
            duration_ticks = struct.unpack('<I', self.operand_bytes[:4])[0]
            return f"Duration: {duration_ticks} ticks ({duration_ticks/30:.2f}s)"
        elif self.opcode == 1:  # GenericTSOCall
            target = struct.unpack('<H', self.operand_bytes[:2])[0]
            return f"Target: 0x{target:04X}"
        elif self.opcode == 2:  # Expression
            operator = self.operand_bytes[0]
            return f"Operator: 0x{operator:02X}"
        elif self.opcode in [4, 5]:  # Grab, Drop
            obj_id = struct.unpack('<H', self.operand_bytes[:2])[0]
            return f"Object: {obj_id}"
        elif self.opcode in [11, 12]:  # GetDistanceTo, GetDirectionTo
            target = struct.unpack('<H', self.operand_bytes[:2])[0]
            return f"Target: {target}"
        else:
            # Generic operand display
            return f"Raw: {self.operand_hex}"
    
    def __str__(self) -> str:
        """Simple string representation."""
        op_str = f"0x{self.opcode:04X}"
        t_str = self._pointer_str(self.true_pointer)
        f_str = self._pointer_str(self.false_pointer)
        return f"{self.index:3d}: [{op_str}] {self.opcode_name:25s} T→{t_str} F→{f_str}"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    @staticmethod
    def _pointer_str(ptr: int) -> str:
        """Format pointer target."""
        if ptr == 0xFF:
            return "RET"
        elif ptr == 0xFE:
            return "ERR"
        elif ptr == 0xFD:
            return "ERR"
        else:
            return f"{ptr:3d}"


class BHAVDisassembler:
    """Disassemble BHAV bytecode with semantic annotations."""
    
    def __init__(self):
        """Initialize disassembler."""
        self.instructions: List[DisassembledInstruction] = []
    
    def disassemble(self, bhav_obj) -> List[DisassembledInstruction]:
        """
        Disassemble a BHAV chunk object.
        
        Args:
            bhav_obj: BHAV chunk from formats.iff.chunks
        
        Returns:
            List of DisassembledInstruction objects
        """
        self.instructions = []
        
        for i, bhav_inst in enumerate(bhav_obj.instructions):
            disasm = self._disassemble_instruction(
                bhav_inst.opcode,
                bhav_inst.true_pointer,
                bhav_inst.false_pointer,
                bhav_inst.operand,
                i
            )
            self.instructions.append(disasm)
        
        return self.instructions
    
    def _disassemble_instruction(
        self,
        opcode: int,
        true_ptr: int,
        false_ptr: int,
        operand: bytes,
        index: int = 0
    ) -> DisassembledInstruction:
        """Disassemble single instruction with metadata."""
        
        # Get opcode info from reference
        opcode_info = get_opcode_info(opcode)
        
        # Determine instruction type
        is_primitive = opcode < 256
        is_special = (opcode & 0xFF00) == 0xFF00
        
        # Check if this is an unknown opcode
        is_unknown = opcode_info.get("name") == "Unknown"
        
        # Determine semantics
        opcode_name = opcode_info.get("name", f"Unknown_0x{opcode:04X}")
        category = opcode_info.get("category", "Unknown")
        description = opcode_info.get("description", "Unknown instruction")
        stack_effect = opcode_info.get("stack_effect", "Unknown")
        exit_code = opcode_info.get("exit_code", "UNKNOWN")
        operand_format = opcode_info.get("operand", "")
        
        # Determine control flow
        is_conditional = (
            opcode in [1, 2, 13, 14, 17, 20, 28, 49, 50] and  # Conditional opcodes
            (true_ptr != false_ptr or exit_code in ["GOTO_TRUE", "GOTO_FALSE"])
        )
        is_terminal = exit_code in ["RETURN", "RETURN_TRUE", "RETURN_FALSE"] or true_ptr in [0xFD, 0xFE, 0xFF]
        
        # Determine call target if this is a call
        call_target = None
        if opcode == 1:  # GenericTSOCall
            try:
                call_target = struct.unpack('<H', operand[:2])[0]
            except:
                pass
        
        return DisassembledInstruction(
            index=index,
            opcode=opcode,
            opcode_name=opcode_name,
            category=category,
            description=description,
            true_pointer=true_ptr,
            false_pointer=false_ptr,
            operand_bytes=operand,
            operand_hex=operand.hex().upper(),
            stack_effect=stack_effect,
            exit_code=exit_code,
            operand_format=operand_format,
            is_primitive=is_primitive,
            is_conditional=is_conditional,
            is_terminal=is_terminal,
            is_special=is_special,
            is_unknown=is_unknown,
            call_target=call_target,
        )
    
    def format_disassembly(
        self,
        title: str = "BHAV Disassembly",
        show_operands: bool = True,
        show_stack: bool = True,
        show_description: bool = True,
        max_width: int = 200,
    ) -> str:
        """
        Format disassembled instructions for display.
        
        Args:
            title: Title for output
            show_operands: Include formatted operands
            show_stack: Include stack effects
            show_description: Include instruction descriptions
            max_width: Maximum line width
        
        Returns:
            Formatted string
        """
        lines = [
            "=" * max_width,
            f" {title}",
            "=" * max_width,
            "",
        ]
        
        for inst in self.instructions:
            # Basic instruction line
            t_str = inst._pointer_str(inst.true_pointer)
            f_str = inst._pointer_str(inst.false_pointer)
            
            line = f"{inst.index:3d}: {inst.opcode_name:30s} [0x{inst.opcode:04X}]"
            if inst.is_conditional:
                line += f" T→{t_str} F→{f_str}"
            elif inst.is_terminal:
                line += f" {t_str}"
            else:
                line += f" →{t_str}"
            
            lines.append(line)
            
            # Category and exit code
            lines.append(f"     Category: {inst.category:20s} Exit: {inst.exit_code}")
            
            # Stack effect
            if show_stack:
                lines.append(f"     Stack: {inst.stack_effect}")
            
            # Description
            if show_description:
                # Word wrap description to max_width - 5
                desc = inst.description
                if len(desc) > max_width - 15:
                    words = desc.split()
                    desc_lines = []
                    current = ""
                    for word in words:
                        if len(current) + len(word) + 1 <= max_width - 15:
                            current += word + " "
                        else:
                            if current:
                                desc_lines.append(current.rstrip())
                            current = word + " "
                    if current:
                        desc_lines.append(current.rstrip())
                    for desc_line in desc_lines:
                        lines.append(f"     {desc_line}")
                else:
                    lines.append(f"     {desc}")
            
            # Operand
            if show_operands and inst.operand_format:
                formatted = inst.format_operand()
                lines.append(f"     Operand: {formatted}")
            
            # Blank line between instructions
            lines.append("")
        
        return "\n".join(lines)
    
    def format_concise(self) -> str:
        """Format as compact single-line per instruction."""
        lines = [
            "=" * 120,
            " BHAV Disassembly (Concise)",
            "=" * 120,
            "",
            f"{'#':>3} {'Instruction':30} {'0xOPCODE':10} {'Targets':15} {'Category':15} {'Exit':12}",
            "-" * 120,
        ]
        
        for inst in self.instructions:
            t_str = inst._pointer_str(inst.true_pointer)
            f_str = inst._pointer_str(inst.false_pointer)
            
            if inst.is_conditional:
                targets = f"T:{t_str} F:{f_str}"
            else:
                targets = f"→{t_str}"
            
            line = (
                f"{inst.index:3d} "
                f"{inst.opcode_name:30s} "
                f"[0x{inst.opcode:04X}]  "
                f"{targets:15s} "
                f"{inst.category:15s} "
                f"{inst.exit_code:12s}"
            )
            lines.append(line)
        
        lines.append("-" * 120)
        lines.append("")
        return "\n".join(lines)
    
    def build_control_flow_graph(self) -> Dict[int, List[int]]:
        """
        Build control flow graph from disassembled instructions.
        
        Returns:
            Dict mapping instruction index → list of next instruction indices
        """
        graph = {}
        
        for inst in self.instructions:
            targets = set()
            
            # Determine next instructions based on control flow
            if inst.true_pointer in [0xFF, 0xFE, 0xFD]:
                # Returns/errors
                if inst.is_conditional:
                    # Also follow false path
                    if inst.false_pointer not in [0xFF, 0xFE, 0xFD]:
                        targets.add(inst.false_pointer)
            else:
                # Normal branch
                targets.add(inst.true_pointer)
                
                if inst.is_conditional and inst.false_pointer not in [0xFF, 0xFE, 0xFD]:
                    # Conditional with false path
                    targets.add(inst.false_pointer)
                elif not inst.is_conditional and inst.exit_code != "CONTINUE":
                    # Non-conditional but may not fall through
                    pass
            
            # Add fall-through for CONTINUE instructions
            if inst.exit_code == "CONTINUE" and inst.index + 1 < len(self.instructions):
                targets.add(inst.index + 1)
            
            graph[inst.index] = sorted(list(targets))
        
        return graph
    
    def find_unreachable_instructions(self) -> List[int]:
        """
        Find instruction indices that are unreachable from instruction 0.
        
        Returns:
            List of unreachable instruction indices
        """
        if not self.instructions:
            return []
        
        # BFS from instruction 0
        visited = set()
        queue = [0]
        
        cfg = self.build_control_flow_graph()
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            if current in cfg:
                for next_inst in cfg[current]:
                    if next_inst not in visited:
                        queue.append(next_inst)
        
        # All indices not visited are unreachable
        unreachable = [
            i for i in range(len(self.instructions))
            if i not in visited
        ]
        
        return unreachable
    
    def find_call_targets(self) -> List[Tuple[int, int]]:
        """
        Find all BHAV/primitive calls.
        
        Returns:
            List of (instruction_index, call_target)
        """
        targets = []
        
        for inst in self.instructions:
            if inst.opcode == 1 and inst.call_target is not None:
                targets.append((inst.index, inst.call_target))
        
        return targets
    
    def find_unknown_opcodes(self) -> List[Tuple[int, int]]:
        """
        Find all unknown opcodes in the BHAV.
        
        Returns:
            List of (instruction_index, opcode) for unknown instructions
        """
        unknowns = []
        
        for inst in self.instructions:
            if inst.is_unknown:
                unknowns.append((inst.index, inst.opcode))
        
        return unknowns
    
    def get_unknown_opcode_summary(self) -> Dict[int, int]:
        """
        Get frequency count of unknown opcodes.
        
        Returns:
            Dict mapping opcode -> count
        """
        unknown_counts = {}
        
        for inst in self.instructions:
            if inst.is_unknown:
                if inst.opcode not in unknown_counts:
                    unknown_counts[inst.opcode] = 0
                unknown_counts[inst.opcode] += 1
        
        return unknown_counts


class BHAVAnalyzer:
    """Analyze disassembled BHAV bytecode."""
    
    def __init__(self, disassembler: BHAVDisassembler):
        """Initialize analyzer."""
        self.disassembler = disassembler
    
    def get_stack_depth_range(self) -> Tuple[int, int]:
        """
        Estimate stack depth before/after BHAV execution.
        
        Returns:
            (min_depth, max_depth) - conservative estimates
        """
        min_depth = 0
        max_depth = 0
        current = 0
        
        for inst in self.disassembler.instructions:
            # Simple stack tracking - needs operand-specific logic for full accuracy
            if "Pops" in inst.stack_effect:
                current -= 1
            if "Pushes" in inst.stack_effect:
                current += 1
            if "Push" in inst.stack_effect and "Pops" not in inst.stack_effect:
                current += 1
            
            min_depth = min(min_depth, current)
            max_depth = max(max_depth, current)
        
        return (min_depth, max_depth)
    
    def get_instruction_summary(self) -> Dict:
        """Get summary statistics about the BHAV."""
        if not self.disassembler.instructions:
            return {}
        
        categories = {}
        for inst in self.disassembler.instructions:
            cat = inst.category
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        unreachable = len(self.disassembler.find_unreachable_instructions())
        call_targets = len(self.disassembler.find_call_targets())
        unknown_opcodes = len(self.disassembler.find_unknown_opcodes())
        
        return {
            "total_instructions": len(self.disassembler.instructions),
            "unreachable_instructions": unreachable,
            "call_targets": call_targets,
            "unknown_opcodes": unknown_opcodes,
            "categories": categories,
        }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    """
    Example: Disassemble a BHAV from game data
    
    Usage:
        python bhav_disassembler.py
    """
    
    print("BHAV Disassembler Example")
    print("=" * 80)
    print()
    print("To use this disassembler:")
    print()
    print("  from bhav_disassembler import BHAVDisassembler, BHAVAnalyzer")
    print("  from formats.iff.iff_file import IffFile")
    print()
    print("  # Load BHAV from IFF file")
    print("  iff = IffFile.read('Objects.far/AlarmClock.iff')")
    print("  bhav = iff.get_chunk('BHAV', 0)")
    print()
    print("  # Disassemble")
    print("  disasm = BHAVDisassembler()")
    print("  instructions = disasm.disassemble(bhav)")
    print()
    print("  # Display")
    print("  print(disasm.format_disassembly(title='AlarmClock BHAV #0'))")
    print("  print(disasm.format_concise())")
    print()
    print("  # Analyze")
    print("  analyzer = BHAVAnalyzer(disasm)")
    print("  summary = analyzer.get_instruction_summary()")
    print("  print(f'Total instructions: {summary[\"total_instructions\"]}')")
    print("  print(f'Unreachable: {summary[\"unreachable_instructions\"]}')")
    print("  print(f'Calls: {summary[\"call_targets\"]}')")
    print()
    print("=" * 80)
