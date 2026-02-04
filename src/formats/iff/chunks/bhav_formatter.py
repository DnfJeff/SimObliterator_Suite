"""
BHAV Code Formatter - Convert AST to readable pseudocode

Generates human-readable pseudocode from BHAV AST, with:
- Variable name resolution
- Control flow visualization
- Operand formatting
- Syntax highlighting hints
"""

from typing import List, Dict, Optional, Set
from enum import Enum

from .bhav_ast import (
    BehaviorAST, Instruction, BasicBlock, VariableRef,
    VMVariableScope, VMPrimitiveOperand, PushVariableOperand,
    AnimateSimOperand, GetDistanceToOperand, PlaySoundOperand,
    CompareOperand, ShowStringOperand
)
from .primitive_registry import get_primitive_info, get_primitive_name


class CodeStyle(Enum):
    """Output style options"""
    PSEUDOCODE = 0  # High-level pseudocode
    ASSEMBLY = 1    # Low-level instruction listing
    FLOWCHART = 2   # ASCII flowchart


class BHAVFormatter:
    """Format BHAV AST as readable code"""
    
    def __init__(self, ast: BehaviorAST, style: CodeStyle = CodeStyle.PSEUDOCODE):
        self.ast = ast
        self.style = style
        self.indent_level = 0
        self.variable_names = self._build_variable_names()
        self.formatted_lines = []
    
    def format(self) -> str:
        """Generate formatted output"""
        if self.style == CodeStyle.PSEUDOCODE:
            return self._format_pseudocode()
        elif self.style == CodeStyle.ASSEMBLY:
            return self._format_assembly()
        elif self.style == CodeStyle.FLOWCHART:
            return self._format_flowchart()
        else:
            return ""
    
    def _build_variable_names(self) -> Dict[str, str]:
        """Build friendly variable names"""
        names = {}
        
        # Parameters
        for i in range(self.ast.arg_count):
            names[f"param_{i}"] = f"arg{i}"
        
        # Locals
        for i in range(self.ast.local_count):
            names[f"local_{i}"] = f"local{i}"
        
        return names
    
    def _format_variable_ref(self, var_ref: VariableRef) -> str:
        """Format variable reference"""
        scope_name = var_ref.scope.name.lower()
        
        if var_ref.scope == VMVariableScope.PARAMETERS:
            return f"arg{var_ref.offset}"
        elif var_ref.scope == VMVariableScope.LOCALS:
            return f"local{var_ref.offset}"
        elif var_ref.scope == VMVariableScope.OBJECT_DATA:
            return f"objData[{var_ref.offset}]"
        elif var_ref.scope == VMVariableScope.GLOBAL:
            return f"global[{var_ref.offset}]"
        elif var_ref.scope == VMVariableScope.TEMPS:
            return f"temp{var_ref.offset}"
        else:
            return f"{scope_name}[{var_ref.offset}]"
    
    def _format_operand(self, instr: Instruction) -> str:
        """Format instruction operand"""
        if not instr.operand:
            return ""
        
        op = instr.operand
        
        if isinstance(op, PushVariableOperand):
            return self._format_variable_ref(op.variable)
        
        elif isinstance(op, AnimateSimOperand):
            return f"anim={op.animation_id:04X}, block={op.block_id}, state={op.state_id}"
        
        elif isinstance(op, GetDistanceToOperand):
            target = self._format_variable_ref(
                VariableRef(op.object_scope, op.scope_data)
            )
            return f"target={target}, temp{op.temp_num}"
        
        elif isinstance(op, PlaySoundOperand):
            return f"sound={op.sound_id:04X}, vol={op.volume}, pitch={op.pitch}"
        
        elif isinstance(op, ShowStringOperand):
            return f"str={op.string_table:04X}:{op.string_index:04X}, dur={op.duration}"
        
        elif isinstance(op, CompareOperand):
            return f"{op.value1} vs {op.value2} ({op.comparison})"
        
        else:
            return str(op)
    
    def _format_pseudocode(self) -> str:
        """Format as high-level pseudocode"""
        lines = []
        
        # Header
        lines.append(f"// BHAV Decompilation: {self.ast.source_bhav}")
        lines.append(f"// Arguments: {self.ast.arg_count}, Locals: {self.ast.local_count}")
        lines.append("")
        
        # Function signature
        args = ", ".join([f"arg{i}" for i in range(self.ast.arg_count)])
        lines.append(f"void behavior({args})")
        lines.append("{")
        self.indent_level = 1
        
        # Declare locals
        if self.ast.local_count > 0:
            for i in range(self.ast.local_count):
                lines.append(f"{self._indent()}int local{i};")
            lines.append("")
        
        # Instructions
        for instr in self.ast.instructions:
            line = self._format_instruction_pseudocode(instr)
            if line:
                lines.append(line)
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def _format_instruction_pseudocode(self, instr: Instruction) -> str:
        """Format single instruction as pseudocode"""
        prim_name = instr.primitive_name
        operand_str = self._format_operand(instr)
        
        # Format based on primitive type
        if instr.opcode == 0:  # Push Variable
            return f"{self._indent()}stack.push({operand_str});"
        
        elif instr.opcode == 1:  # Compare
            return f"{self._indent()}result = compare({operand_str});"
        
        elif instr.opcode == 6:  # Animate Sim
            return f"{self._indent()}animate_sim({operand_str});"
        
        elif instr.opcode == 11:  # Get Distance To
            return f"{self._indent()}{operand_str};"
        
        elif instr.opcode == 12:  # Play Sound
            return f"{self._indent()}play_sound({operand_str});"
        
        elif instr.opcode == 18:  # Run Subroutine
            return f"{self._indent()}call_bhav({operand_str});"
        
        elif instr.opcode == 33:  # Show String
            return f"{self._indent()}show_string({operand_str});"
        
        elif instr.opcode == 252:  # Breakpoint
            return f"{self._indent()}__breakpoint__();"
        
        elif instr.opcode == 255:  # Stop
            return f"{self._indent()}return;"
        
        else:
            return f"{self._indent()}// {prim_name}({operand_str}) [opcode {instr.opcode}]"
    
    def _format_assembly(self) -> str:
        """Format as low-level instruction assembly"""
        lines = []
        
        lines.append(f"; BHAV Assembly: {self.ast.source_bhav}")
        lines.append(f"; Args: {self.ast.arg_count}, Locals: {self.ast.local_count}")
        lines.append("")
        
        for instr in self.ast.instructions:
            prim_info = get_primitive_info(instr.opcode)
            prim_name = prim_info.get('name', f'Unknown_{instr.opcode}')
            operand_str = self._format_operand(instr)
            
            line = f"{instr.index:3d}: {prim_name:30s}"
            if operand_str:
                line += f"  {operand_str}"
            
            if instr.is_conditional():
                line += f"  ; T→{instr.true_pointer} F→{instr.false_pointer}"
            elif instr.true_pointer != instr.index + 1:
                line += f"  ; →{instr.true_pointer}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _format_flowchart(self) -> str:
        """Format as ASCII flowchart"""
        lines = []
        
        lines.append(f"BHAV Flowchart: {self.ast.source_bhav}")
        lines.append("")
        
        if not self.ast.cfg:
            return "\n".join(lines) + "(No CFG built)"
        
        # Format each block
        for block in self.ast.cfg.blocks:
            lines.append(f"[Block {block.label}]")
            
            for instr in block.instructions:
                prim_name = get_primitive_name(instr.opcode)
                lines.append(f"  {instr.index:3d}: {prim_name}")
            
            # Show outgoing edges
            edges = [e for e in self.ast.cfg.edges if e[0] in block.instructions]
            for from_instr, to_block in edges:
                lines.append(f"    ↓ (index {from_instr.index} → block {to_block.label})")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _indent(self) -> str:
        """Get current indentation"""
        return "    " * self.indent_level


class BHAVAnnotator:
    """Add semantic annotations to code"""
    
    @staticmethod
    def annotate_variables(ast: BehaviorAST) -> Dict[str, str]:
        """Infer variable purposes"""
        annotations = {}
        
        # Scan for patterns
        for instr in ast.instructions:
            if instr.operand and isinstance(instr.operand, PushVariableOperand):
                var_key = str(instr.operand.variable)
                
                # Look for usage patterns
                # TODO: Implement heuristics
        
        return annotations
    
    @staticmethod
    def find_dead_code(ast: BehaviorAST) -> Set[int]:
        """Identify unreachable instructions"""
        if not ast.cfg:
            return set()
        
        reachable = set()
        stack = [ast.cfg.entry]
        
        while stack:
            block = stack.pop()
            for instr in block.instructions:
                reachable.add(instr.index)
            
            # Follow edges
            for edge in ast.cfg.edges:
                if any(instr in block.instructions for instr in [edge[0]]):
                    if edge[1] not in reachable:
                        stack.append(edge[1])
        
        dead = set()
        for i in range(len(ast.instructions)):
            if i not in reachable:
                dead.add(i)
        
        return dead


def format_bhav(ast: BehaviorAST, style: CodeStyle = CodeStyle.PSEUDOCODE) -> str:
    """Quick format function"""
    formatter = BHAVFormatter(ast, style)
    return formatter.format()
