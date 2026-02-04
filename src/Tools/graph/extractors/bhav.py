"""BHAV reference extractor - Phase 1."""

import sys
from pathlib import Path
from typing import List, Optional

# Ensure formats package is importable
workspace_root = Path(__file__).parent.parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

# Lazy import BHAV - try to import but don't fail if unavailable
BHAV = None
try:
    from formats.iff.chunks import BHAV
except ImportError:
    pass

from ..core import Reference, ResourceNode, TGI, ReferenceKind, ChunkScope
from .base import ReferenceExtractor
from .registry import ExtractorRegistry


@ExtractorRegistry.register("BHAV")
class BHAVExtractor(ReferenceExtractor):
    """
    Extract references from BHAV (Behavior) chunks.
    
    BHAV chunks contain SimAntics bytecode that can:
    - Call other BHAV subroutines (opcode 256+)
    - Reference BCON constants (opcode 2 - expressions)
    - Reference other resources indirectly
    
    Phase 1: Extract subroutine calls (BHAV → BHAV)
    Future: Extract BCON references, validate instruction graph
    """
    
    @property
    def chunk_type(self) -> str:
        return "BHAV"
    
    def extract(self, bhav: Optional[object], node: ResourceNode) -> List[Reference]:
        """Extract all references from a BHAV chunk."""
        if bhav is None:
            return []
        
        refs: List[Reference] = []
        
        # Verify this is actually a BHAV object
        if not hasattr(bhav, 'instructions'):
            return []
        
        # Iterate through all instructions
        for inst_idx, inst in enumerate(bhav.instructions):
            if not hasattr(inst, 'opcode'):
                continue
            
            opcode = inst.opcode
            
            # Subroutine calls: opcodes 256+ indicate a call to another BHAV
            if opcode >= 256:
                # The opcode itself is the BHAV ID (for most cases)
                # For more complex operand structures, we'd parse operands here
                bhav_id = opcode
                
                # Determine scope based on ID range
                # 256-4095 (0x0100-0FFF): Global subroutines
                # 4096-8191 (0x1000-1FFF): Local subroutines
                # 8192+ (0x2000+): Semi-global subroutines
                
                if 256 <= bhav_id <= 4095:
                    scope = ChunkScope.GLOBAL
                    scope_name = "global"
                    # Global BHAVs are from Global.iff, not the current file
                    owner_iff = None
                elif 4096 <= bhav_id <= 8191:
                    scope = ChunkScope.OBJECT
                    scope_name = "local"
                    # Local BHAVs are in the same file
                    owner_iff = node.owner_iff
                else:
                    scope = ChunkScope.SEMI_GLOBAL
                    scope_name = "semi-global"
                    # Semi-global BHAVs are from GLOB file
                    owner_iff = None
                
                target_tgi = TGI("BHAV", 0x00000001, bhav_id)
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="BHAV",
                    owner_iff=owner_iff,
                    scope=scope,
                    label=f"BHAV {scope_name}",
                )
                
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.HARD,
                    source_field=f"instruction_{inst_idx}",
                    description=f"Subroutine call at instruction {inst_idx} (opcode 0x{opcode:04X})",
                    edge_kind="behavioral",
                ))
            
            # Expression evaluation: opcode 2
            # Extracts potential BCON constant references
            elif opcode == 2:
                bcon_refs = self._extract_expression_bcon_refs(inst, inst_idx, node)
                refs.extend(bcon_refs)
        
        return refs
    
    def _extract_expression_bcon_refs(self, inst: object, inst_idx: int, node: ResourceNode) -> List[Reference]:
        """
        Extract BCON/Tuning references from opcode 2 (Expression) instructions.
        
        Expression operand structure (8 bytes):
        - [0-1]: lhs_data (int16)
        - [2-3]: rhs_data (int16)
        - [4]: is_signed (bool)
        - [5]: operator (VMExpressionOperator)
        - [6]: lhs_scope (VMVariableScope)
        - [7]: rhs_scope (VMVariableScope)
        
        BCON references: When scope is 26 (Tuning), the data value encodes:
        - High 9 bits: tableID (0-191, maps to 256-8255 actual range)
        - Low 7 bits: keyID (constant index within table)
        
        From FreeSO: Scope 26 (Tuning) lookups map to BCON (local 4096+) or
        OTF tables (global 256+, semi-global 8192+).
        """
        refs: List[Reference] = []
        
        if not hasattr(inst, 'operand') or inst.operand is None:
            return refs
        
        operand = inst.operand
        if len(operand) < 8:
            return refs
        
        try:
            # Parse operand bytes
            import struct
            lhs_data = struct.unpack('<h', operand[0:2])[0]  # signed int16
            rhs_data = struct.unpack('<h', operand[2:4])[0]
            is_signed = operand[4] != 0
            operator = operand[5]
            lhs_scope = operand[6]
            rhs_scope = operand[7]
            
            # Extract BCON references (Scope 26 = Tuning/BCON)
            # From FreeSO VMTuning: tableID is high 9 bits, keyID is low 7 bits
            # But we need to look at signed 16-bit values
            
            # Check LHS for BCON reference (Scope 26 = Tuning/BCON)
            if lhs_scope == 26:  # Scope 26 = Tuning (BCON/OTF)
                # Extract table ID and key ID
                # Data format: high 9 bits = tableID, low 7 bits = keyID
                # But values are 16-bit signed, so we work with them as-is
                table_id = (lhs_data >> 7) & 0x1FF  # High 9 bits
                key_id = lhs_data & 0x7F             # Low 7 bits
                
                # Map table_id to actual BCON chunk ID based on mode
                # Mode 0 (local): offset 4096
                # Mode 1 (semi-global): offset 8192
                # Mode 2 (global): offset 256
                if table_id < 64:
                    bcon_id = 4096 + table_id
                    scope = ChunkScope.OBJECT
                elif table_id < 128:
                    bcon_id = 8192 + (table_id - 64)
                    scope = ChunkScope.SEMI_GLOBAL
                else:
                    bcon_id = 256 + (table_id - 128)
                    scope = ChunkScope.GLOBAL
                
                owner_iff = node.owner_iff if scope == ChunkScope.OBJECT else None
                
                target_tgi = TGI("BCON", 0x00000001, bcon_id)
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="BCON",
                    owner_iff=owner_iff,
                    scope=scope,
                    label=f"BCON constant",
                )
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.INDEXED,
                    source_field=f"instruction_{inst_idx}_lhs",
                    description=f"Expression LHS tuning constant (table {bcon_id}, key {key_id}) at instruction {inst_idx}",
                    edge_kind="tuning",
                ))
            
            # Check RHS for BCON reference (Scope 26 = Tuning/BCON)
            if rhs_scope == 26:  # Scope 26 = Tuning (BCON/OTF)
                # Extract table ID and key ID
                table_id = (rhs_data >> 7) & 0x1FF  # High 9 bits
                key_id = rhs_data & 0x7F             # Low 7 bits
                
                # Map table_id to actual BCON chunk ID based on mode
                if table_id < 64:
                    bcon_id = 4096 + table_id
                    scope = ChunkScope.OBJECT
                elif table_id < 128:
                    bcon_id = 8192 + (table_id - 64)
                    scope = ChunkScope.SEMI_GLOBAL
                else:
                    bcon_id = 256 + (table_id - 128)
                    scope = ChunkScope.GLOBAL
                
                owner_iff = node.owner_iff if scope == ChunkScope.OBJECT else None
                
                target_tgi = TGI("BCON", 0x00000001, bcon_id)
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="BCON",
                    owner_iff=owner_iff,
                    scope=scope,
                    label=f"BCON constant",
                )
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.INDEXED,
                    source_field=f"instruction_{inst_idx}_rhs",
                    description=f"Expression RHS tuning constant (table {bcon_id}, key {key_id}) at instruction {inst_idx}",
                    edge_kind="tuning",
                ))
        
        except Exception as e:
            # Silently skip if we can't parse - malformed operand
            pass
        
        return refs

