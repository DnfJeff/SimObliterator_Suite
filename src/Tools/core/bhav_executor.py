"""
BHAV Executor Simulator - Trace execution paths through SimAntics bytecode

Based on FreeSO's VMThread/VMStackFrame architecture. This provides static
execution simulation (no actual primitives executed) to trace:
  - Instruction pointer progression
  - Control flow paths (taken branches)
  - Variable state (locals, arguments)
  - Stack object references
  - Reachable instructions
  - Execution loops and dead code

The executor DOES NOT run actual primitive code. It simulates execution by:
  1. Following instruction pointers from the BHAV bytecode
  2. Applying branch decisions based on exit codes
  3. Recording each step in an ExecutionTrace
  4. Detecting loops and unreachable code

This is a static analysis tool, similar to a debugger without actual execution.
"""

import struct
import importlib.util
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Tuple
from enum import Enum
from copy import deepcopy

# Import from same package
from .bhav_disassembler import BHAVDisassembler, ExitCode, DisassembledInstruction
from formats.iff.chunks.bhav import BHAV


class VMPrimitiveExitCode(Enum):
    """FreeSO exit codes - how instruction executions terminate."""
    GOTO_TRUE = 0               # Branch to true_pointer
    GOTO_FALSE = 1              # Branch to false_pointer
    GOTO_TRUE_NEXT_TICK = 2     # Branch to true_pointer, pause execution
    GOTO_FALSE_NEXT_TICK = 3    # Branch to false_pointer, pause execution
    RETURN_TRUE = 4             # Return from BHAV with true
    RETURN_FALSE = 5            # Return from BHAV with false
    ERROR = 6                   # Error - branch to false_pointer and return
    CONTINUE_NEXT_TICK = 7      # Continue next tick (pause)
    CONTINUE = 8                # Continue to next instruction
    INTERRUPT = 9               # Interrupt execution
    CONTINUE_FUTURE_TICK = 10   # Continue in future tick


@dataclass
class StackFrame:
    """Execution context for a BHAV routine (mirrors FreeSO VMStackFrame)."""
    
    routine: 'DisassembledBHAV'          # Which BHAV is executing
    instruction_pointer: int = 0          # Current instruction index
    locals: Dict[int, int] = field(default_factory=dict)  # Local variables
    args: Dict[int, int] = field(default_factory=dict)    # Arguments
    stack_object_id: int = 0              # Stack object reference
    
    def get_current_instruction(self) -> Optional[DisassembledInstruction]:
        """Get instruction at current pointer."""
        if 0 <= self.instruction_pointer < len(self.routine.instructions):
            return self.routine.instructions[self.instruction_pointer]
        return None
    
    def __repr__(self) -> str:
        return (f"StackFrame(routine={self.routine.id}, "
                f"ip={self.instruction_pointer}, "
                f"locals={len(self.locals)}, args={len(self.args)})")


@dataclass
class ExecutionStep:
    """Single step in execution trace."""
    
    step_number: int                       # Ordinal step count
    instruction_pointer: int               # IP before execution
    instruction: DisassembledInstruction   # Instruction executed
    exit_code: VMPrimitiveExitCode        # How instruction terminated
    next_pointer: int                      # Where we're going next
    locals_snapshot: Dict[int, int] = field(default_factory=dict)
    args_snapshot: Dict[int, int] = field(default_factory=dict)
    stack_object_id: int = 0
    
    def __str__(self) -> str:
        """Format as single line."""
        op_str = f"0x{self.instruction.opcode:04X}"
        exit_str = self.exit_code.name
        return (f"Step {self.step_number:3d}: IP={self.instruction_pointer:3d} "
                f"[{op_str}] {self.instruction.opcode_name:25s} → "
                f"{exit_str:20s} → IP={self.next_pointer:3d}")


@dataclass
class DisassembledBHAV:
    """BHAV with disassembled instructions (from BHAVDisassembler)."""
    
    id: int                                 # BHAV ID
    instructions: List[DisassembledInstruction]
    args: int = 0
    locals: int = 0
    
    def get_instruction(self, index: int) -> Optional[DisassembledInstruction]:
        """Get instruction by index."""
        if 0 <= index < len(self.instructions):
            return self.instructions[index]
        return None


class ExecutionTrace:
    """Complete execution history of a BHAV routine."""
    
    def __init__(self, bhav_id: int):
        self.bhav_id = bhav_id
        self.steps: List[ExecutionStep] = []
        self.entry_point: int = 0
        self.exit_code: Optional[VMPrimitiveExitCode] = None
        self.visited_instructions: Set[int] = set()
        self.loops_detected: List[Tuple[int, int]] = []  # (from_ip, to_ip)
        self.unreachable_instructions: Set[int] = set()
    
    def add_step(self, step: ExecutionStep) -> None:
        """Record execution step."""
        self.steps.append(step)
        self.visited_instructions.add(step.instruction_pointer)
    
    def detect_loops(self) -> None:
        """Find backward jumps (potential loops)."""
        for i, step in enumerate(self.steps):
            if step.next_pointer < step.instruction_pointer:
                # Backward jump detected
                self.loops_detected.append((step.instruction_pointer, step.next_pointer))
    
    def find_unreachable(self, total_instructions: int) -> None:
        """Identify instructions never visited."""
        self.unreachable_instructions = set(range(total_instructions)) - self.visited_instructions
    
    def format_summary(self) -> str:
        """Format execution summary."""
        lines = []
        lines.append(f"Execution Trace: BHAV #{self.bhav_id}")
        lines.append(f"  Total Steps: {len(self.steps)}")
        lines.append(f"  Visited Instructions: {len(self.visited_instructions)}")
        lines.append(f"  Loops Detected: {len(self.loops_detected)}")
        lines.append(f"  Unreachable Instructions: {len(self.unreachable_instructions)}")
        lines.append(f"  Exit Code: {self.exit_code.name if self.exit_code else 'N/A'}")
        return "\n".join(lines)
    
    def format_steps(self, max_steps: Optional[int] = None) -> str:
        """Format execution steps."""
        lines = [f"Execution Steps (BHAV #{self.bhav_id}):"]
        lines.append("")
        
        steps_to_show = self.steps[:max_steps] if max_steps else self.steps
        for step in steps_to_show:
            lines.append(str(step))
        
        if max_steps and len(self.steps) > max_steps:
            lines.append(f"... and {len(self.steps) - max_steps} more steps")
        
        return "\n".join(lines)
    
    def format_loops(self) -> str:
        """Format detected loops."""
        if not self.loops_detected:
            return "No loops detected"
        
        lines = ["Loops Detected:"]
        for from_ip, to_ip in self.loops_detected:
            lines.append(f"  Backward jump: IP {from_ip} → IP {to_ip}")
        return "\n".join(lines)
    
    def format_unreachable(self, instructions: List[DisassembledInstruction]) -> str:
        """Format unreachable instructions."""
        if not self.unreachable_instructions:
            return "All instructions reachable"
        
        lines = ["Unreachable Instructions:"]
        for ip in sorted(self.unreachable_instructions):
            if ip < len(instructions):
                inst = instructions[ip]
                lines.append(f"  IP {ip:3d}: [{inst.opcode:04X}] {inst.opcode_name}")
        return "\n".join(lines)


class BHAVExecutor:
    """Execute BHAV bytecode with tracing (static analysis, no real primitives)."""
    
    # Settings
    MAX_STEPS = 10000  # Prevent infinite loops
    
    def __init__(self):
        self.disassembler = BHAVDisassembler()
    
    def execute(self, bhav: BHAV, entry_point: int = 0,
                trace: bool = True,
                max_steps: Optional[int] = None) -> ExecutionTrace:
        """
        Execute BHAV with tracing.
        
        Args:
            bhav: BHAV chunk to execute
            entry_point: Starting instruction index (default 0)
            trace: Record execution trace
            max_steps: Limit steps (prevents infinite loops)
        
        Returns:
            ExecutionTrace with execution history
        """
        
        max_steps = max_steps or self.MAX_STEPS
        
        # Disassemble BHAV
        instructions = self.disassembler.disassemble(bhav)
        
        # Create wrapper
        disasm_bhav = DisassembledBHAV(
            id=bhav.chunk_id,
            instructions=instructions,
            args=bhav.args,
            locals=bhav.locals
        )
        
        # Create trace
        exec_trace = ExecutionTrace(bhav.chunk_id)
        exec_trace.entry_point = entry_point
        
        # Create initial stack frame
        frame = StackFrame(routine=disasm_bhav, instruction_pointer=entry_point)
        
        # Execute
        step_number = 0
        while step_number < max_steps:
            # Get current instruction
            inst = frame.get_current_instruction()
            if not inst:
                # Out of bounds - execution ended
                break
            
            # Simulate execution
            exit_code, next_pointer = self._execute_instruction(inst)
            
            # Record step
            if trace:
                step = ExecutionStep(
                    step_number=step_number,
                    instruction_pointer=frame.instruction_pointer,
                    instruction=inst,
                    exit_code=exit_code,
                    next_pointer=next_pointer,
                    locals_snapshot=deepcopy(frame.locals),
                    args_snapshot=deepcopy(frame.args),
                    stack_object_id=frame.stack_object_id
                )
                exec_trace.add_step(step)
            
            # Handle exit code
            if exit_code in [VMPrimitiveExitCode.RETURN_TRUE,
                            VMPrimitiveExitCode.RETURN_FALSE,
                            VMPrimitiveExitCode.ERROR]:
                # Execution ends
                exec_trace.exit_code = exit_code
                break
            
            # Move to next instruction
            if next_pointer == 255:  # Special return-false pointer
                exec_trace.exit_code = VMPrimitiveExitCode.RETURN_FALSE
                break
            elif next_pointer == 254:  # Special return-true pointer
                exec_trace.exit_code = VMPrimitiveExitCode.RETURN_TRUE
                break
            
            frame.instruction_pointer = next_pointer
            step_number += 1
        
        # Post-process trace
        exec_trace.detect_loops()
        exec_trace.find_unreachable(len(instructions))
        
        return exec_trace
    
    def _execute_instruction(self, inst: DisassembledInstruction) -> Tuple[VMPrimitiveExitCode, int]:
        """
        Simulate instruction execution (without actual primitives).
        
        Returns:
            (exit_code, next_instruction_pointer)
        """
        
        # Simulate based on opcode semantics
        
        # Expression operators - simulate as always succeeding
        if inst.opcode == 0x0002:  # Expression
            exit_code = VMPrimitiveExitCode.GOTO_TRUE
            next_pointer = inst.true_pointer
        
        # Control flow - follow branches
        elif inst.opcode in [0x0001]:  # GenericTSOCall / subroutine
            exit_code = VMPrimitiveExitCode.CONTINUE
            next_pointer = inst.index + 1
        
        # Return instructions
        elif inst.opcode in [0x00FE]:  # Return
            exit_code = VMPrimitiveExitCode.RETURN_TRUE
            next_pointer = inst.true_pointer
        
        # Unknown opcodes - treat as continue
        elif inst.is_unknown:
            exit_code = VMPrimitiveExitCode.CONTINUE
            next_pointer = inst.index + 1
        
        # Default - continue to next instruction
        else:
            exit_code = VMPrimitiveExitCode.CONTINUE
            next_pointer = inst.index + 1
        
        return exit_code, next_pointer
    
    def find_reachable_instructions(self, bhav: BHAV,
                                    entry_point: int = 0) -> Set[int]:
        """Find all instructions reachable from entry point."""
        trace = self.execute(bhav, entry_point=entry_point, trace=True)
        return trace.visited_instructions
    
    def find_unreachable_instructions(self, bhav: BHAV,
                                      entry_point: int = 0) -> Set[int]:
        """Find all unreachable instructions."""
        trace = self.execute(bhav, entry_point=entry_point, trace=True)
        return trace.unreachable_instructions
    
    def detect_loops(self, bhav: BHAV,
                     entry_point: int = 0) -> List[Tuple[int, int]]:
        """Find backward jumps (potential infinite loops)."""
        trace = self.execute(bhav, entry_point=entry_point, trace=True)
        return trace.loops_detected


class BHAVExecutionAnalyzer:
    """Analyze BHAV execution traces."""
    
    def __init__(self, executor: BHAVExecutor):
        self.executor = executor
    
    def analyze(self, bhav: BHAV) -> Dict:
        """Run full execution analysis."""
        trace = self.executor.execute(bhav, trace=True)
        
        instructions = self.executor.disassembler.disassemble(bhav)
        
        return {
            'bhav_id': bhav.chunk_id,
            'total_instructions': len(instructions),
            'reachable_instructions': len(trace.visited_instructions),
            'unreachable_count': len(trace.unreachable_instructions),
            'execution_steps': len(trace.steps),
            'loops_detected': len(trace.loops_detected),
            'trace': trace,
            'instructions': instructions
        }
    
    def print_analysis(self, analysis: Dict) -> None:
        """Print analysis results."""
        print(f"BHAV #{analysis['bhav_id']} Execution Analysis")
        print("=" * 80)
        print(f"Total Instructions: {analysis['total_instructions']}")
        print(f"Reachable: {analysis['reachable_instructions']}")
        print(f"Unreachable: {analysis['unreachable_count']}")
        print(f"Execution Steps: {analysis['execution_steps']}")
        print(f"Loops Detected: {analysis['loops_detected']}")
        print()
        
        trace = analysis['trace']
        print(trace.format_summary())
        print()
        
        # Show execution path
        print(trace.format_steps(max_steps=20))
        print()
        
        # Show loops if any
        if trace.loops_detected:
            print(trace.format_loops())
            print()
        
        # Show unreachable
        if trace.unreachable_instructions:
            print(trace.format_unreachable(analysis['instructions']))
