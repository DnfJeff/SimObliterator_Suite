"""
BHAV Decompiler - Convert BHAV chunks to AST representation

This module orchestrates the decompilation process:
1. Load BHAV chunk data
2. Parse instruction stream
3. Decode operands for each instruction
4. Build control flow graph
5. Return structured AST

The decompiler handles:
- BHAV instruction format (16 bytes per instruction)
- Operand decoding for all primitive types
- Branch pointer resolution
- CFG construction for analysis
"""

from typing import Dict, List, Optional, Tuple
import struct
from io import BytesIO

from .bhav_ast import (
    BehaviorAST, Instruction, VMVariableScope, VMPrimitiveOperand,
    VariableRef, BasicBlock, ControlFlowGraph
)
from .bhav_operands import decode_operand
from .primitive_registry import (
    PRIMITIVE_REGISTRY, get_primitive_info, is_routine_call
)


class BHAVDecompiler:
    """Main BHAV decompilation engine"""
    
    def __init__(self):
        self.instructions: List[Instruction] = []
        self.arg_count = 0
        self.local_count = 0
        self.source_bhav = None
        
    def decompile(self, bhav_data: bytes, group_id: int = 0, 
                  bhav_id: int = 0) -> Optional[BehaviorAST]:
        """
        Decompile BHAV chunk data
        
        Args:
            bhav_data: Raw BHAV chunk bytes
            group_id: Resource group ID (for reference)
            bhav_id: Resource ID (for reference)
            
        Returns:
            BehaviorAST if successful, None on error
        """
        try:
            # Parse BHAV header
            if not self._parse_header(bhav_data):
                return None
            
            # Parse instruction stream
            if not self._parse_instructions(bhav_data):
                return None
            
            # Build AST
            ast = BehaviorAST(
                args=self.arg_count,
                locals=self.local_count,
                behavior_type=0,
                instructions=self.instructions,
                source_bhav=f"{group_id:04X}:{bhav_id:04X}"
            )
            
            # Build control flow graph
            ast.build_cfg()
            
            return ast
            
        except Exception as e:
            print(f"BHAV decompilation error: {e}")
            return None
    
    def _parse_header(self, data: bytes) -> bool:
        """Parse BHAV header (first 12 bytes)"""
        if len(data) < 12:
            return False
        
        try:
            # Header format:
            # 0-3: version (uint32)
            # 4-7: arg_count (uint32)
            # 8-11: local_count (uint32)
            version = struct.unpack('<I', data[0:4])[0]
            self.arg_count = struct.unpack('<I', data[4:8])[0]
            self.local_count = struct.unpack('<I', data[8:12])[0]
            
            return True
        except:
            return False
    
    def _parse_instructions(self, data: bytes) -> bool:
        """Parse instruction stream"""
        if len(data) < 12:
            return False
        
        try:
            # Skip header (12 bytes)
            offset = 12
            instruction_index = 0
            
            # Read instructions until we reach the end
            while offset + 16 <= len(data):
                instr = self._parse_instruction(
                    data[offset:offset+16],
                    instruction_index
                )
                
                if instr:
                    self.instructions.append(instr)
                
                offset += 16
                instruction_index += 1
            
            return True
            
        except Exception as e:
            print(f"Instruction parsing error: {e}")
            return False
    
    def _parse_instruction(self, data: bytes, index: int) -> Optional[Instruction]:
        """
        Parse single 16-byte instruction
        
        Instruction format:
        0-1:   opcode (uint16)
        2-9:   operand data (8 bytes)
        10-11: true_ptr / return value (uint16)
        12-13: false_ptr (uint16)
        14-15: args_return (uint16)
        """
        if len(data) < 16:
            return None
        
        try:
            # Parse instruction structure
            opcode = struct.unpack('<H', data[0:2])[0]
            operand_data = data[2:10]
            true_ptr = struct.unpack('<H', data[10:12])[0]
            false_ptr = struct.unpack('<H', data[12:14])[0]
            args_return = struct.unpack('<H', data[14:16])[0]
            
            # Decode operand based on primitive type
            operand = decode_operand(opcode, operand_data)
            
            # Get primitive info
            prim_info = get_primitive_info(opcode)
            prim_name = prim_info.get('name', f'Unknown_{opcode}')
            
            # Create instruction
            instr = Instruction(
                index=index,
                opcode=opcode,
                operand=operand,
                true_pointer=true_ptr,
                false_pointer=false_ptr,
                primitive_name=prim_name
            )
            
            return instr
            
        except Exception as e:
            print(f"Instruction parse error at {index}: {e}")
            return None
    
    def decompile_multiple(self, bhavs: Dict[Tuple[int, int], bytes]) -> Dict[Tuple[int, int], BehaviorAST]:
        """
        Decompile multiple BHAV chunks
        
        Args:
            bhavs: Dict of (group_id, bhav_id) -> bhav_data
            
        Returns:
            Dict of (group_id, bhav_id) -> BehaviorAST
        """
        results = {}
        
        for (group_id, bhav_id), data in bhavs.items():
            ast = self.decompile(data, group_id, bhav_id)
            if ast:
                results[(group_id, bhav_id)] = ast
        
        return results


class BHAVValidator:
    """Validate BHAV data integrity"""
    
    @staticmethod
    def validate(data: bytes) -> Tuple[bool, str]:
        """
        Validate BHAV chunk structure
        
        Returns:
            (is_valid, error_message)
        """
        if len(data) < 12:
            return False, "BHAV too short (< 12 bytes)"
        
        try:
            # Check header is reasonable
            version = struct.unpack('<I', data[0:4])[0]
            arg_count = struct.unpack('<I', data[4:8])[0]
            local_count = struct.unpack('<I', data[8:12])[0]
            
            if version != 0:
                return False, f"Unsupported BHAV version: {version}"
            
            if arg_count > 256:
                return False, f"Invalid arg count: {arg_count}"
            
            if local_count > 256:
                return False, f"Invalid local count: {local_count}"
            
            # Check instruction count
            instr_count = (len(data) - 12) // 16
            if (len(data) - 12) % 16 != 0:
                return False, "Invalid BHAV size (not aligned to 16-byte instructions)"
            
            if instr_count > 4096:
                return False, f"Too many instructions: {instr_count}"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)


class BHAVAnalyzer:
    """Analyze BHAV for code quality"""
    
    @staticmethod
    def find_unreachable_code(ast: BehaviorAST) -> List[int]:
        """Find unreachable instruction indices"""
        if not ast.cfg:
            return []
        
        reachable = set()
        stack = [ast.cfg.entry]
        
        while stack:
            block = stack.pop()
            if block in reachable:
                continue
            
            reachable.add(block)
            
            for instr in block.instructions:
                for edge in ast.cfg.edges.get(instr, []):
                    if edge[1] not in reachable:
                        stack.append(edge[1])
        
        # Find instructions not in any reachable block
        unreachable = []
        for i, instr in enumerate(ast.instructions):
            if not any(instr in block.instructions for block in reachable):
                unreachable.append(i)
        
        return unreachable
    
    @staticmethod
    def analyze_stack_usage(ast: BehaviorAST) -> Dict[str, any]:
        """Analyze stack operations"""
        stats = {
            'pushes': 0,
            'pops': 0,
            'calls': 0,
            'max_depth': 0,
            'current_depth': 0
        }
        
        for instr in ast.instructions:
            if instr.opcode == 0:  # Push Variable
                stats['pushes'] += 1
                stats['current_depth'] += 1
                stats['max_depth'] = max(stats['max_depth'], stats['current_depth'])
            
            elif instr.opcode >= 256:  # Routine call
                stats['calls'] += 1
        
        return stats


def decompile_bhav(data: bytes) -> Optional[BehaviorAST]:
    """Quick decompile function"""
    decompiler = BHAVDecompiler()
    return decompiler.decompile(data)
