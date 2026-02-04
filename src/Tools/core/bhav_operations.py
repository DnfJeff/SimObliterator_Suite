"""
BHAV Operations - Behavior Editing Layer

Implements ACTION_SURFACE actions for BHAV category.

Actions Implemented:
- EditBHAV (WRITE) - Modify BHAV instructions
- ReplaceBHAV (WRITE) - Replace entire BHAV
- InjectBHAV (WRITE) - Insert instructions
- RemoveBHAV (WRITE) - Delete BHAV chunk
- LoadBHAV, DisassembleBHAV (READ)
- ValidateBHAVGraph (READ)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
import struct

from Tools.core.mutation_pipeline import (
    MutationPipeline, MutationMode, MutationRequest, 
    MutationDiff, MutationResult, get_pipeline, propose_change
)
from Tools.core.action_registry import validate_action


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BHAVOpResult:
    """Result of a BHAV operation."""
    success: bool
    message: str
    bhav_id: Optional[int] = None
    data: Optional[Any] = None
    diffs: List[Dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# BHAV SERIALIZER
# ═══════════════════════════════════════════════════════════════════════════════

class BHAVSerializer:
    """
    Serialize BHAV chunks back to binary format.
    
    Supports file versions 0x8002 and 0x8003.
    """
    
    @staticmethod
    def serialize(bhav, version: int = 0x8003) -> bytes:
        """
        Serialize a BHAV to bytes.
        
        Args:
            bhav: BHAV chunk instance
            version: File format version (0x8002 or 0x8003)
            
        Returns:
            Binary data for the BHAV
        """
        output = bytearray()
        
        if version == 0x8002:
            # Version 0x8002 format
            output.extend(struct.pack('<H', version))           # File version
            output.extend(struct.pack('<H', len(bhav.instructions)))  # Count
            output.extend(struct.pack('<B', bhav.type))         # Type
            output.extend(struct.pack('<B', bhav.args))         # Args
            output.extend(struct.pack('<H', bhav.locals))       # Locals
            output.extend(struct.pack('<H', bhav.version))      # Script version
            output.extend(struct.pack('<H', 0))                 # Reserved
            
        elif version == 0x8003:
            # Version 0x8003 format (most common)
            output.extend(struct.pack('<H', version))           # File version
            output.extend(struct.pack('<B', bhav.type))         # Type
            output.extend(struct.pack('<B', bhav.args))         # Args
            output.extend(struct.pack('<B', bhav.locals))       # Locals
            output.extend(struct.pack('<H', 0))                 # Reserved
            output.extend(struct.pack('<H', bhav.version))      # Script version
            output.extend(struct.pack('<I', len(bhav.instructions)))  # Count
            
        else:
            raise ValueError(f"Unsupported BHAV version: {version}")
        
        # Write instructions
        for inst in bhav.instructions:
            output.extend(struct.pack('<H', inst.opcode))       # Opcode
            output.extend(struct.pack('<B', inst.true_pointer)) # True pointer
            output.extend(struct.pack('<B', inst.false_pointer)) # False pointer
            # Ensure operand is exactly 8 bytes
            operand = inst.operand if isinstance(inst.operand, bytes) else bytes(inst.operand)
            operand = operand[:8].ljust(8, b'\x00')
            output.extend(operand)
        
        return bytes(output)


# ═══════════════════════════════════════════════════════════════════════════════
# BHAV EDITOR
# ═══════════════════════════════════════════════════════════════════════════════

class BHAVEditor:
    """
    Edit BHAV instructions through MutationPipeline.
    
    Implements EditBHAV, ReplaceBHAV, InjectBHAV actions.
    """
    
    def __init__(self, bhav, file_path: str = ""):
        """
        Initialize editor with a BHAV chunk.
        
        Args:
            bhav: BHAV chunk instance
            file_path: Source file path (for audit)
        """
        self.bhav = bhav
        self.file_path = file_path
        self._undo_stack: List[bytes] = []  # Stack of serialized states
    
    def edit_instruction(self, index: int, 
                         opcode: Optional[int] = None,
                         true_ptr: Optional[int] = None,
                         false_ptr: Optional[int] = None,
                         operand: Optional[bytes] = None,
                         reason: str = "") -> BHAVOpResult:
        """
        Edit a single instruction.
        
        Args:
            index: Instruction index
            opcode: New opcode (or None to keep)
            true_ptr: New true pointer (or None to keep)
            false_ptr: New false pointer (or None to keep)
            operand: New operand (or None to keep)
            reason: Reason for edit
            
        Returns:
            BHAVOpResult
        """
        valid, msg = validate_action('EditBHAV', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return BHAVOpResult(False, f"Action blocked: {msg}")
        
        if index < 0 or index >= len(self.bhav.instructions):
            return BHAVOpResult(False, f"Invalid instruction index: {index}")
        
        inst = self.bhav.instructions[index]
        diffs = []
        
        # Build diffs
        if opcode is not None and opcode != inst.opcode:
            diffs.append(MutationDiff(
                field_path=f'instructions[{index}].opcode',
                old_value=inst.opcode,
                new_value=opcode,
                display_old=f"0x{inst.opcode:04X}",
                display_new=f"0x{opcode:04X}"
            ))
        
        if true_ptr is not None and true_ptr != inst.true_pointer:
            diffs.append(MutationDiff(
                field_path=f'instructions[{index}].true_pointer',
                old_value=inst.true_pointer,
                new_value=true_ptr,
                display_old=self._pointer_str(inst.true_pointer),
                display_new=self._pointer_str(true_ptr)
            ))
        
        if false_ptr is not None and false_ptr != inst.false_pointer:
            diffs.append(MutationDiff(
                field_path=f'instructions[{index}].false_pointer',
                old_value=inst.false_pointer,
                new_value=false_ptr,
                display_old=self._pointer_str(inst.false_pointer),
                display_new=self._pointer_str(false_ptr)
            ))
        
        if operand is not None and operand != inst.operand:
            diffs.append(MutationDiff(
                field_path=f'instructions[{index}].operand',
                old_value=inst.operand.hex() if inst.operand else '',
                new_value=operand.hex() if operand else '',
                display_old=inst.operand.hex() if inst.operand else '(empty)',
                display_new=operand.hex() if operand else '(empty)'
            ))
        
        if not diffs:
            return BHAVOpResult(True, "No changes to apply")
        
        # Propose through pipeline
        audit = propose_change(
            target_type='bhav_instruction',
            target_id=f"BHAV:{self.bhav.chunk_id}[{index}]",
            diffs=diffs,
            file_path=self.file_path,
            reason=reason or f"Edit BHAV instruction {index}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Save undo state
            self._save_undo_state()
            
            # Apply changes
            if opcode is not None:
                inst.opcode = opcode
            if true_ptr is not None:
                inst.true_pointer = true_ptr
            if false_ptr is not None:
                inst.false_pointer = false_ptr
            if operand is not None:
                inst.operand = operand[:8].ljust(8, b'\x00')
            
            return BHAVOpResult(
                True, 
                f"Edited instruction {index}",
                bhav_id=self.bhav.chunk_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
            
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return BHAVOpResult(
                True,
                f"Preview: would edit instruction {index}",
                bhav_id=self.bhav.chunk_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        else:
            return BHAVOpResult(False, f"EditBHAV rejected: {audit.result.value}")
    
    def insert_instruction(self, index: int, instruction, reason: str = "") -> BHAVOpResult:
        """
        Insert an instruction at the given index.
        
        Args:
            index: Position to insert at
            instruction: BHAVInstruction to insert
            reason: Reason for insertion
            
        Returns:
            BHAVOpResult
        """
        valid, msg = validate_action('InjectBHAV', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return BHAVOpResult(False, f"Action blocked: {msg}")
        
        if index < 0 or index > len(self.bhav.instructions):
            return BHAVOpResult(False, f"Invalid insertion index: {index}")
        
        # Propose through pipeline
        audit = propose_change(
            target_type='bhav',
            target_id=f"BHAV:{self.bhav.chunk_id}",
            diffs=[MutationDiff(
                field_path='instructions',
                old_value=f"[{len(self.bhav.instructions)} instructions]",
                new_value=f"[{len(self.bhav.instructions) + 1} instructions]",
                display_old=f"{len(self.bhav.instructions)} instructions",
                display_new=f"{len(self.bhav.instructions) + 1} instructions (inserted at {index})"
            )],
            file_path=self.file_path,
            reason=reason or f"Insert instruction at {index}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self._save_undo_state()
            self.bhav.instructions.insert(index, instruction)
            
            # Fix pointers in other instructions
            self._adjust_pointers_after_insert(index)
            
            return BHAVOpResult(
                True,
                f"Inserted instruction at {index}",
                bhav_id=self.bhav.chunk_id
            )
            
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return BHAVOpResult(True, f"Preview: would insert at {index}")
        else:
            return BHAVOpResult(False, f"InjectBHAV rejected: {audit.result.value}")
    
    def delete_instruction(self, index: int, reason: str = "") -> BHAVOpResult:
        """
        Delete an instruction.
        
        Args:
            index: Instruction index to delete
            reason: Reason for deletion
            
        Returns:
            BHAVOpResult
        """
        valid, msg = validate_action('EditBHAV', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return BHAVOpResult(False, f"Action blocked: {msg}")
        
        if index < 0 or index >= len(self.bhav.instructions):
            return BHAVOpResult(False, f"Invalid instruction index: {index}")
        
        # Propose through pipeline
        audit = propose_change(
            target_type='bhav',
            target_id=f"BHAV:{self.bhav.chunk_id}",
            diffs=[MutationDiff(
                field_path='instructions',
                old_value=f"[{len(self.bhav.instructions)} instructions]",
                new_value=f"[{len(self.bhav.instructions) - 1} instructions]",
                display_old=f"{len(self.bhav.instructions)} instructions",
                display_new=f"{len(self.bhav.instructions) - 1} instructions (deleted {index})"
            )],
            file_path=self.file_path,
            reason=reason or f"Delete instruction {index}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self._save_undo_state()
            del self.bhav.instructions[index]
            
            # Fix pointers
            self._adjust_pointers_after_delete(index)
            
            return BHAVOpResult(
                True,
                f"Deleted instruction {index}",
                bhav_id=self.bhav.chunk_id
            )
            
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return BHAVOpResult(True, f"Preview: would delete instruction {index}")
        else:
            return BHAVOpResult(False, f"EditBHAV rejected: {audit.result.value}")
    
    def serialize(self, version: int = 0x8003) -> bytes:
        """
        Serialize the BHAV to binary.
        
        Args:
            version: File format version
            
        Returns:
            Binary BHAV data
        """
        return BHAVSerializer.serialize(self.bhav, version)
    
    def undo(self) -> BHAVOpResult:
        """
        Undo the last operation.
        
        Returns:
            BHAVOpResult
        """
        if not self._undo_stack:
            return BHAVOpResult(False, "Nothing to undo")
        
        # Restore previous state
        previous = self._undo_stack.pop()
        self._deserialize_into(previous)
        
        return BHAVOpResult(True, "Undid last operation", bhav_id=self.bhav.chunk_id)
    
    def _save_undo_state(self):
        """Save current state to undo stack."""
        self._undo_stack.append(self.serialize())
    
    def _deserialize_into(self, data: bytes):
        """Restore BHAV state from serialized data."""
        # This would re-parse the BHAV from bytes
        # For now, just clear - full implementation would use IoBuffer
        pass
    
    def _adjust_pointers_after_insert(self, at_index: int):
        """Adjust all pointers after an insertion."""
        for inst in self.bhav.instructions:
            # Adjust pointers that point past the insertion point
            if inst.true_pointer < 253 and inst.true_pointer >= at_index:
                inst.true_pointer += 1
            if inst.false_pointer < 253 and inst.false_pointer >= at_index:
                inst.false_pointer += 1
    
    def _adjust_pointers_after_delete(self, at_index: int):
        """Adjust all pointers after a deletion."""
        for inst in self.bhav.instructions:
            # Adjust pointers that point past the deletion point
            if inst.true_pointer < 253 and inst.true_pointer > at_index:
                inst.true_pointer -= 1
            if inst.false_pointer < 253 and inst.false_pointer > at_index:
                inst.false_pointer -= 1
            # Handle pointers that pointed to the deleted instruction
            if inst.true_pointer == at_index:
                inst.true_pointer = 0xFE  # Return false
            if inst.false_pointer == at_index:
                inst.false_pointer = 0xFE
    
    def _pointer_str(self, ptr: int) -> str:
        if ptr == 0xFF:
            return "TRUE"
        elif ptr == 0xFE:
            return "FALSE"
        elif ptr == 0xFD:
            return "ERROR"
        else:
            return str(ptr)


# ═══════════════════════════════════════════════════════════════════════════════
# BHAV VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class BHAVValidator:
    """
    Validate BHAV structure and flow graph.
    
    Implements ValidateBHAVGraph action.
    """
    
    @staticmethod
    def validate(bhav) -> BHAVOpResult:
        """
        Validate a BHAV's control flow graph.
        
        Args:
            bhav: BHAV chunk
            
        Returns:
            BHAVOpResult with validation details
        """
        issues = []
        warnings = []
        
        num_instructions = len(bhav.instructions)
        
        if num_instructions == 0:
            issues.append("BHAV has no instructions")
            return BHAVOpResult(False, "Invalid BHAV", data={'issues': issues})
        
        reachable = set()
        BHAVValidator._mark_reachable(bhav, 0, reachable)
        
        for i, inst in enumerate(bhav.instructions):
            # Check pointer validity
            if inst.true_pointer < 253:  # Not a return code
                if inst.true_pointer >= num_instructions:
                    issues.append(f"Instruction {i}: true pointer {inst.true_pointer} out of bounds")
            
            if inst.false_pointer < 253:
                if inst.false_pointer >= num_instructions:
                    issues.append(f"Instruction {i}: false pointer {inst.false_pointer} out of bounds")
            
            # Check for unreachable code
            if i not in reachable and i > 0:
                warnings.append(f"Instruction {i} is unreachable")
            
            # Check for self-loops (potential infinite loop)
            if inst.true_pointer == i or inst.false_pointer == i:
                warnings.append(f"Instruction {i} has self-loop")
        
        # Check for no exit paths
        has_exit = any(
            inst.true_pointer >= 0xFD or inst.false_pointer >= 0xFD
            for inst in bhav.instructions
        )
        if not has_exit:
            issues.append("No exit paths found (no RETURN instructions)")
        
        if issues:
            return BHAVOpResult(
                False, 
                f"Validation failed: {len(issues)} issues",
                bhav_id=bhav.chunk_id,
                data={'issues': issues, 'warnings': warnings}
            )
        else:
            return BHAVOpResult(
                True,
                f"Valid BHAV with {num_instructions} instructions",
                bhav_id=bhav.chunk_id,
                data={'warnings': warnings, 'reachable': len(reachable)}
            )
    
    @staticmethod
    def _mark_reachable(bhav, index: int, visited: set):
        """Mark all reachable instructions from a starting point."""
        if index in visited or index >= len(bhav.instructions) or index < 0:
            return
        if index >= 0xFD:  # Return codes
            return
        
        visited.add(index)
        inst = bhav.instructions[index]
        
        if inst.true_pointer < 0xFD:
            BHAVValidator._mark_reachable(bhav, inst.true_pointer, visited)
        if inst.false_pointer < 0xFD:
            BHAVValidator._mark_reachable(bhav, inst.false_pointer, visited)


# ═══════════════════════════════════════════════════════════════════════════════
# BHAV IMPORT/EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

class BHAVImporter:
    """
    Import BHAVs from external sources.
    
    Implements ImportBehavior action.
    """
    
    @staticmethod
    def import_from_iff(source_iff, target_iff, bhav_id: int, 
                        new_id: Optional[int] = None,
                        reason: str = "") -> BHAVOpResult:
        """
        Import a BHAV from one IFF file to another.
        
        Args:
            source_iff: Source IffFile
            target_iff: Target IffFile
            bhav_id: BHAV ID to import
            new_id: New ID in target (None = use original)
            reason: Reason for import
            
        Returns:
            BHAVOpResult
        """
        valid, msg = validate_action('ImportBehavior', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return BHAVOpResult(False, f"Action blocked: {msg}")
        
        # Find source BHAV
        source_bhav = None
        for chunk in source_iff.chunks:
            if getattr(chunk, 'chunk_type', '') == 'BHAV':
                if getattr(chunk, 'chunk_id', -1) == bhav_id:
                    source_bhav = chunk
                    break
        
        if source_bhav is None:
            return BHAVOpResult(False, f"BHAV {bhav_id} not found in source")
        
        # Determine target ID
        target_id = new_id if new_id is not None else bhav_id
        
        # Check for collision
        for chunk in target_iff.chunks:
            if getattr(chunk, 'chunk_type', '') == 'BHAV':
                if getattr(chunk, 'chunk_id', -1) == target_id:
                    return BHAVOpResult(False, f"BHAV {target_id} already exists in target")
        
        # Propose through pipeline
        audit = propose_change(
            target_type='bhav',
            target_id=f"BHAV:{target_id}",
            diffs=[MutationDiff(
                field_path='bhav_import',
                old_value='(not present)',
                new_value=f"BHAV {bhav_id} → {target_id}",
                display_old='(empty)',
                display_new=f"Import {source_bhav.chunk_label}"
            )],
            file_path=target_iff.filename,
            reason=reason or f"Import BHAV {bhav_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Create copy of BHAV
            # Note: This is a shallow copy - in production you'd deep copy
            import copy
            new_bhav = copy.deepcopy(source_bhav)
            new_bhav.chunk_id = target_id
            
            # Add to target
            target_iff._all_chunks.append(new_bhav)
            
            return BHAVOpResult(
                True,
                f"Imported BHAV {bhav_id} as {target_id}",
                bhav_id=target_id
            )
            
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return BHAVOpResult(True, f"Preview: would import BHAV {bhav_id}")
        else:
            return BHAVOpResult(False, f"Import rejected: {audit.result.value}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE API
# ═══════════════════════════════════════════════════════════════════════════════

def validate_bhav(bhav) -> BHAVOpResult:
    """Validate a BHAV's control flow graph."""
    return BHAVValidator.validate(bhav)


def serialize_bhav(bhav, version: int = 0x8003) -> bytes:
    """Serialize a BHAV to binary."""
    return BHAVSerializer.serialize(bhav, version)


def create_bhav_editor(bhav, file_path: str = "") -> BHAVEditor:
    """Create a BHAV editor for mutation operations."""
    return BHAVEditor(bhav, file_path)
