"""
BHAV Rewiring Engine — Handle pointer updates during instruction edits.

Provides:
- Pointer remapping for instruction reordering
- Insert/delete pointer adjustments
- Move operation with automatic rewiring
- Validation of pointer integrity

Special pointer values:
- 253 (0xFD): Error exit
- 254 (0xFE): True exit (return true)  
- 255 (0xFF): False exit (return false)

These are preserved during rewiring operations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from copy import deepcopy


# Special pointer values
POINTER_ERROR = 253   # 0xFD - Return error
POINTER_TRUE = 254    # 0xFE - Return true
POINTER_FALSE = 255   # 0xFF - Return false

SPECIAL_POINTERS = {POINTER_ERROR, POINTER_TRUE, POINTER_FALSE}


class RewireOperation(Enum):
    """Types of rewiring operations."""
    INSERT = "insert"
    DELETE = "delete"
    MOVE = "move"
    REORDER = "reorder"  # Full reorder (new ordering)


@dataclass
class Instruction:
    """Minimal instruction for rewiring."""
    index: int
    opcode: int
    true_pointer: int
    false_pointer: int
    operand: bytes = field(default_factory=lambda: bytes(8))
    
    def clone(self) -> 'Instruction':
        return Instruction(
            index=self.index,
            opcode=self.opcode,
            true_pointer=self.true_pointer,
            false_pointer=self.false_pointer,
            operand=bytes(self.operand),
        )


@dataclass
class RewireResult:
    """Result of a rewiring operation."""
    success: bool
    instructions: List[Instruction] = field(default_factory=list)
    pointer_changes: List[str] = field(default_factory=list)  # Human-readable changes
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def is_special_pointer(pointer: int) -> bool:
    """Check if pointer is a special value (exit/error)."""
    return pointer in SPECIAL_POINTERS


def remap_pointer(pointer: int, old_to_new: Dict[int, int]) -> int:
    """
    Remap a single pointer value.
    
    Args:
        pointer: Original pointer value
        old_to_new: Mapping from old indices to new indices
        
    Returns:
        Remapped pointer value
    """
    if is_special_pointer(pointer):
        return pointer
    
    if pointer in old_to_new:
        return old_to_new[pointer]
    
    # Pointer to deleted instruction - return error
    return POINTER_ERROR


def create_insert_mapping(
    instruction_count: int,
    insert_at: int,
    insert_count: int = 1
) -> Dict[int, int]:
    """
    Create pointer mapping for inserting instructions.
    
    Instructions at and after insert_at shift up by insert_count.
    
    Args:
        instruction_count: Current number of instructions
        insert_at: Index where new instructions will be inserted
        insert_count: Number of instructions to insert
        
    Returns:
        Mapping from old indices to new indices
    """
    mapping = {}
    
    for i in range(instruction_count):
        if i < insert_at:
            mapping[i] = i
        else:
            mapping[i] = i + insert_count
    
    return mapping


def create_delete_mapping(
    instruction_count: int,
    delete_indices: List[int]
) -> Dict[int, int]:
    """
    Create pointer mapping for deleting instructions.
    
    Deleted instruction pointers become ERROR.
    Remaining instructions shift down to fill gaps.
    
    Args:
        instruction_count: Current number of instructions
        delete_indices: Indices to delete
        
    Returns:
        Mapping from old indices to new indices (deleted -> None)
    """
    delete_set = set(delete_indices)
    mapping = {}
    
    new_index = 0
    for old_index in range(instruction_count):
        if old_index in delete_set:
            # Deleted - will map to error
            mapping[old_index] = None
        else:
            mapping[old_index] = new_index
            new_index += 1
    
    return mapping


def create_move_mapping(
    instruction_count: int,
    from_index: int,
    to_index: int
) -> Dict[int, int]:
    """
    Create pointer mapping for moving a single instruction.
    
    Args:
        instruction_count: Current number of instructions
        from_index: Original index of instruction to move
        to_index: New index for the instruction
        
    Returns:
        Mapping from old indices to new indices
    """
    if from_index == to_index:
        return {i: i for i in range(instruction_count)}
    
    mapping = {}
    
    if from_index < to_index:
        # Moving down: indices between shift up
        for i in range(instruction_count):
            if i < from_index:
                mapping[i] = i
            elif i == from_index:
                mapping[i] = to_index
            elif i <= to_index:
                mapping[i] = i - 1
            else:
                mapping[i] = i
    else:
        # Moving up: indices between shift down
        for i in range(instruction_count):
            if i < to_index:
                mapping[i] = i
            elif i == from_index:
                mapping[i] = to_index
            elif i < from_index:
                mapping[i] = i + 1
            else:
                mapping[i] = i
    
    return mapping


def create_reorder_mapping(new_order: List[int]) -> Dict[int, int]:
    """
    Create pointer mapping for a complete reordering.
    
    Args:
        new_order: List where new_order[new_idx] = old_idx
        
    Returns:
        Mapping from old indices to new indices
    """
    mapping = {}
    
    for new_idx, old_idx in enumerate(new_order):
        mapping[old_idx] = new_idx
    
    return mapping


class BHAVRewirer:
    """
    Engine for rewiring BHAV instruction pointers.
    
    Handles the complexity of maintaining correct true/false pointers
    when instructions are inserted, deleted, moved, or reordered.
    """
    
    def __init__(self, instructions: List[Instruction]):
        """
        Initialize rewirer with current instructions.
        
        Args:
            instructions: List of Instruction objects
        """
        self._original = [inst.clone() for inst in instructions]
        self._current = [inst.clone() for inst in instructions]
    
    @property
    def instructions(self) -> List[Instruction]:
        """Get current instruction list."""
        return self._current
    
    @property
    def instruction_count(self) -> int:
        return len(self._current)
    
    def insert(
        self,
        at_index: int,
        new_instructions: List[Instruction]
    ) -> RewireResult:
        """
        Insert instructions at a position.
        
        Args:
            at_index: Index to insert at (0 to len)
            new_instructions: Instructions to insert
            
        Returns:
            RewireResult with updated instructions
        """
        result = RewireResult(success=True)
        
        # Validate
        if at_index < 0 or at_index > len(self._current):
            result.success = False
            result.errors.append(f"Invalid insert index: {at_index}")
            return result
        
        # Create mapping
        mapping = create_insert_mapping(
            len(self._current),
            at_index,
            len(new_instructions)
        )
        
        # Remap existing instructions
        new_list = []
        for inst in self._current:
            new_inst = inst.clone()
            old_true = new_inst.true_pointer
            old_false = new_inst.false_pointer
            
            new_inst.true_pointer = remap_pointer(old_true, mapping)
            new_inst.false_pointer = remap_pointer(old_false, mapping)
            new_inst.index = mapping[inst.index]
            
            if old_true != new_inst.true_pointer:
                result.pointer_changes.append(
                    f"Instruction {inst.index} true: {old_true} -> {new_inst.true_pointer}"
                )
            if old_false != new_inst.false_pointer:
                result.pointer_changes.append(
                    f"Instruction {inst.index} false: {old_false} -> {new_inst.false_pointer}"
                )
            
            new_list.append(new_inst)
        
        # Insert new instructions
        for i, new_inst in enumerate(new_instructions):
            insert_inst = new_inst.clone()
            insert_inst.index = at_index + i
            new_list.insert(at_index + i, insert_inst)
        
        # Re-sort by index
        new_list.sort(key=lambda x: x.index)
        
        self._current = new_list
        result.instructions = self._current
        return result
    
    def delete(self, indices: List[int]) -> RewireResult:
        """
        Delete instructions at given indices.
        
        Pointers to deleted instructions become ERROR.
        
        Args:
            indices: Indices to delete
            
        Returns:
            RewireResult with updated instructions
        """
        result = RewireResult(success=True)
        
        # Validate
        for idx in indices:
            if idx < 0 or idx >= len(self._current):
                result.success = False
                result.errors.append(f"Invalid delete index: {idx}")
                return result
        
        # Create mapping
        mapping = create_delete_mapping(len(self._current), indices)
        
        # Remap and filter
        new_list = []
        delete_set = set(indices)
        
        for inst in self._current:
            if inst.index in delete_set:
                continue  # Skip deleted
            
            new_inst = inst.clone()
            old_true = new_inst.true_pointer
            old_false = new_inst.false_pointer
            
            # Remap pointers
            new_true = mapping.get(old_true) if not is_special_pointer(old_true) else old_true
            new_false = mapping.get(old_false) if not is_special_pointer(old_false) else old_false
            
            # None means deleted - use error
            new_inst.true_pointer = new_true if new_true is not None else POINTER_ERROR
            new_inst.false_pointer = new_false if new_false is not None else POINTER_ERROR
            new_inst.index = mapping[inst.index]
            
            if old_true != new_inst.true_pointer:
                if new_true is None:
                    result.warnings.append(
                        f"Instruction {inst.index} true pointer to deleted instruction -> ERROR"
                    )
                result.pointer_changes.append(
                    f"Instruction {inst.index} true: {old_true} -> {new_inst.true_pointer}"
                )
            if old_false != new_inst.false_pointer:
                if new_false is None:
                    result.warnings.append(
                        f"Instruction {inst.index} false pointer to deleted instruction -> ERROR"
                    )
                result.pointer_changes.append(
                    f"Instruction {inst.index} false: {old_false} -> {new_inst.false_pointer}"
                )
            
            new_list.append(new_inst)
        
        # Sort by new index
        new_list.sort(key=lambda x: x.index)
        
        self._current = new_list
        result.instructions = self._current
        return result
    
    def move(self, from_index: int, to_index: int) -> RewireResult:
        """
        Move a single instruction to a new position.
        
        Args:
            from_index: Current index
            to_index: Target index
            
        Returns:
            RewireResult with updated instructions
        """
        result = RewireResult(success=True)
        
        # Validate
        if from_index < 0 or from_index >= len(self._current):
            result.success = False
            result.errors.append(f"Invalid from index: {from_index}")
            return result
        if to_index < 0 or to_index >= len(self._current):
            result.success = False
            result.errors.append(f"Invalid to index: {to_index}")
            return result
        
        if from_index == to_index:
            result.instructions = self._current
            return result
        
        # Create mapping
        mapping = create_move_mapping(len(self._current), from_index, to_index)
        
        # Remap all instructions
        new_list = []
        for inst in self._current:
            new_inst = inst.clone()
            old_true = new_inst.true_pointer
            old_false = new_inst.false_pointer
            
            new_inst.true_pointer = remap_pointer(old_true, mapping)
            new_inst.false_pointer = remap_pointer(old_false, mapping)
            new_inst.index = mapping[inst.index]
            
            if old_true != new_inst.true_pointer:
                result.pointer_changes.append(
                    f"Instruction {inst.index} true: {old_true} -> {new_inst.true_pointer}"
                )
            if old_false != new_inst.false_pointer:
                result.pointer_changes.append(
                    f"Instruction {inst.index} false: {old_false} -> {new_inst.false_pointer}"
                )
            
            new_list.append(new_inst)
        
        # Sort by new index
        new_list.sort(key=lambda x: x.index)
        
        self._current = new_list
        result.instructions = self._current
        return result
    
    def reorder(self, new_order: List[int]) -> RewireResult:
        """
        Apply a complete reordering of instructions.
        
        Args:
            new_order: List where new_order[new_idx] = old_idx
            
        Returns:
            RewireResult with updated instructions
        """
        result = RewireResult(success=True)
        
        # Validate
        if len(new_order) != len(self._current):
            result.success = False
            result.errors.append(
                f"Order length {len(new_order)} doesn't match instruction count {len(self._current)}"
            )
            return result
        
        if set(new_order) != set(range(len(self._current))):
            result.success = False
            result.errors.append("Invalid order: must contain each index exactly once")
            return result
        
        # Create mapping
        mapping = create_reorder_mapping(new_order)
        
        # Remap all instructions
        new_list = []
        for inst in self._current:
            new_inst = inst.clone()
            old_true = new_inst.true_pointer
            old_false = new_inst.false_pointer
            
            new_inst.true_pointer = remap_pointer(old_true, mapping)
            new_inst.false_pointer = remap_pointer(old_false, mapping)
            new_inst.index = mapping[inst.index]
            
            if old_true != new_inst.true_pointer:
                result.pointer_changes.append(
                    f"Instruction {inst.index} true: {old_true} -> {new_inst.true_pointer}"
                )
            if old_false != new_inst.false_pointer:
                result.pointer_changes.append(
                    f"Instruction {inst.index} false: {old_false} -> {new_inst.false_pointer}"
                )
            
            new_list.append(new_inst)
        
        # Sort by new index
        new_list.sort(key=lambda x: x.index)
        
        self._current = new_list
        result.instructions = self._current
        return result
    
    def validate(self) -> List[str]:
        """
        Validate current instruction pointers.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for inst in self._current:
            # Check true pointer
            if not is_special_pointer(inst.true_pointer):
                if inst.true_pointer < 0 or inst.true_pointer >= len(self._current):
                    errors.append(
                        f"Instruction {inst.index}: true pointer {inst.true_pointer} out of range"
                    )
            
            # Check false pointer
            if not is_special_pointer(inst.false_pointer):
                if inst.false_pointer < 0 or inst.false_pointer >= len(self._current):
                    errors.append(
                        f"Instruction {inst.index}: false pointer {inst.false_pointer} out of range"
                    )
        
        return errors
    
    def get_changes_from_original(self) -> List[str]:
        """Get list of changes from original state."""
        changes = []
        
        if len(self._current) != len(self._original):
            changes.append(
                f"Instruction count: {len(self._original)} -> {len(self._current)}"
            )
        
        for new_inst in self._current:
            # Find corresponding original (by original index if available)
            # This is simplified - real implementation would track original indices
            if new_inst.index < len(self._original):
                orig = self._original[new_inst.index]
                if orig.true_pointer != new_inst.true_pointer:
                    changes.append(
                        f"Instruction {new_inst.index} true: {orig.true_pointer} -> {new_inst.true_pointer}"
                    )
                if orig.false_pointer != new_inst.false_pointer:
                    changes.append(
                        f"Instruction {new_inst.index} false: {orig.false_pointer} -> {new_inst.false_pointer}"
                    )
        
        return changes
    
    def reset(self):
        """Reset to original state."""
        self._current = [inst.clone() for inst in self._original]


def rewire_for_copy_paste(
    source_instructions: List[Instruction],
    paste_at: int,
    target_instruction_count: int
) -> List[Instruction]:
    """
    Prepare instructions for pasting into another location.
    
    Adjusts internal pointers to be relative to paste position.
    Pointers that go outside the pasted range become exits.
    
    Args:
        source_instructions: Instructions being pasted (with original indices)
        paste_at: Index where they will be pasted
        target_instruction_count: Size of target BHAV (before paste)
        
    Returns:
        Adjusted instructions ready for pasting
    """
    result = []
    source_count = len(source_instructions)
    
    # Build mapping: old source index -> new target index
    source_indices = [inst.index for inst in source_instructions]
    source_to_target = {
        old_idx: paste_at + i 
        for i, old_idx in enumerate(source_indices)
    }
    
    for i, inst in enumerate(source_instructions):
        new_inst = inst.clone()
        new_inst.index = paste_at + i
        
        # Remap pointers within the pasted block
        if is_special_pointer(inst.true_pointer):
            pass  # Keep special
        elif inst.true_pointer in source_to_target:
            new_inst.true_pointer = source_to_target[inst.true_pointer]
        else:
            # Pointer goes outside pasted block - need to decide behavior
            # For now, keep it (may become invalid)
            pass
        
        if is_special_pointer(inst.false_pointer):
            pass
        elif inst.false_pointer in source_to_target:
            new_inst.false_pointer = source_to_target[inst.false_pointer]
        else:
            pass
        
        result.append(new_inst)
    
    return result
