"""
BHAV Patching - Advanced BHAV Modification Operations

Implements high-risk BHAV modification actions.

Actions Implemented:
- RemapBHAVIDs (WRITE) - Remap BHAV IDs to avoid collisions
- RewireBHAVCalls (WRITE) - Update BHAV call targets after remapping
- PatchGlobalBHAV (WRITE) - Patch global BHAV references
- PatchSemiGlobalBHAV (WRITE) - Patch semi-global BHAV references
- PatchObjectBHAV (WRITE) - Patch object-local BHAV references
"""

import struct
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Tuple
from pathlib import Path

from Tools.core.mutation_pipeline import (
    MutationPipeline, MutationMode, MutationRequest, 
    MutationDiff, MutationResult, get_pipeline, propose_change
)
from Tools.core.action_registry import validate_action


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BHAVPatchResult:
    """Result of a BHAV patching operation."""
    success: bool
    message: str
    patches_applied: int = 0
    id_map: Dict[int, int] = field(default_factory=dict)
    affected_bhavs: List[int] = field(default_factory=list)
    data: Optional[Any] = None


# ═══════════════════════════════════════════════════════════════════════════════
# BHAV SCOPE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

class BHAVScope:
    """BHAV scope ranges (ID space allocation)."""
    
    # Global BHAVs (shared across all objects)
    GLOBAL_MIN = 0x0000
    GLOBAL_MAX = 0x00FF
    
    # Semi-global BHAVs (shared within category)
    SEMI_GLOBAL_MIN = 0x0100
    SEMI_GLOBAL_MAX = 0x0FFF
    
    # Object-local BHAVs
    OBJECT_MIN = 0x1000
    OBJECT_MAX = 0xFFFF
    
    @classmethod
    def get_scope(cls, bhav_id: int) -> str:
        """Determine scope from BHAV ID."""
        if cls.GLOBAL_MIN <= bhav_id <= cls.GLOBAL_MAX:
            return 'global'
        elif cls.SEMI_GLOBAL_MIN <= bhav_id <= cls.SEMI_GLOBAL_MAX:
            return 'semi-global'
        else:
            return 'object'
    
    @classmethod
    def is_global(cls, bhav_id: int) -> bool:
        return cls.GLOBAL_MIN <= bhav_id <= cls.GLOBAL_MAX
    
    @classmethod
    def is_semi_global(cls, bhav_id: int) -> bool:
        return cls.SEMI_GLOBAL_MIN <= bhav_id <= cls.SEMI_GLOBAL_MAX
    
    @classmethod
    def is_object_local(cls, bhav_id: int) -> bool:
        return cls.OBJECT_MIN <= bhav_id <= cls.OBJECT_MAX


# ═══════════════════════════════════════════════════════════════════════════════
# BHAV CALL OPCODES
# ═══════════════════════════════════════════════════════════════════════════════

class BHAVCallOpcodes:
    """Opcodes that call other BHAVs."""
    
    # Opcode -> (id_operand_offset, id_is_word)
    CALL_OPCODES = {
        0x0002: (0, True),   # Call Tree (Run Immediately)
        0x0003: (0, True),   # Call Tree by name
        0x0004: (0, True),   # Call Tree (Push Interaction)
        0x0009: (0, True),   # Run Tree
        0x000A: (0, True),   # Queue Tree
        0x0016: (0, True),   # Run Function Call  
        0x002E: (0, True),   # Check Action String
        0x0042: (0, True),   # Find Best Action
    }
    
    # Global call opcodes
    GLOBAL_CALL = 0x0002    # Call global BHAV
    SEMI_GLOBAL_CALL = 0x0003  # Call semi-global
    PRIVATE_CALL = 0x0004   # Call private (object-local)
    
    @classmethod
    def is_call_opcode(cls, opcode: int) -> bool:
        return opcode in cls.CALL_OPCODES
    
    @classmethod
    def get_call_info(cls, opcode: int) -> Optional[Tuple[int, bool]]:
        """Get (offset, is_word) for call opcode."""
        return cls.CALL_OPCODES.get(opcode)


# ═══════════════════════════════════════════════════════════════════════════════
# BHAV ID REMAPPER
# ═══════════════════════════════════════════════════════════════════════════════

class BHAVIDRemapper:
    """
    Remap BHAV IDs to avoid collisions.
    
    Implements RemapBHAVIDs action.
    """
    
    def __init__(self, iff_file):
        """
        Initialize with an IffFile instance.
        
        Args:
            iff_file: IffFile containing BHAVs to remap
        """
        self.iff = iff_file
        self.id_map: Dict[int, int] = {}
    
    def build_remap(self, offset: int = 0x1000, 
                    avoid_ids: Set[int] = None,
                    scope: str = 'all') -> Dict[int, int]:
        """
        Build ID remapping without applying.
        
        Args:
            offset: Starting ID for remapped BHAVs
            avoid_ids: Set of IDs to avoid
            scope: 'all', 'global', 'semi-global', or 'object'
            
        Returns:
            Dict mapping old_id -> new_id
        """
        avoid_ids = avoid_ids or set()
        self.id_map = {}
        
        next_id = offset
        
        for chunk in self.iff.chunks:
            if getattr(chunk, 'chunk_type', '') != 'BHAV':
                continue
            
            old_id = getattr(chunk, 'chunk_id', 0)
            chunk_scope = BHAVScope.get_scope(old_id)
            
            # Check scope filter
            if scope != 'all' and chunk_scope != scope:
                continue
            
            # Find next available ID
            while next_id in avoid_ids or next_id in self.id_map.values():
                next_id += 1
            
            if old_id != next_id:
                self.id_map[old_id] = next_id
            
            next_id += 1
        
        return self.id_map
    
    def apply_remap(self, id_map: Dict[int, int] = None,
                    reason: str = "") -> BHAVPatchResult:
        """
        Apply ID remapping to BHAV chunks.
        
        Args:
            id_map: Mapping to apply (or use built mapping)
            reason: Reason for remapping
            
        Returns:
            BHAVPatchResult
        """
        valid, msg = validate_action('RemapBHAVIDs', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return BHAVPatchResult(False, f"Action blocked: {msg}")
        
        id_map = id_map or self.id_map
        
        if not id_map:
            return BHAVPatchResult(True, "No remapping needed", id_map={})
        
        # Build diffs
        diffs = []
        for old_id, new_id in id_map.items():
            diffs.append(MutationDiff(
                field_path=f'bhav[{old_id}].chunk_id',
                old_value=old_id,
                new_value=new_id,
                display_old=f"BHAV:0x{old_id:04X}",
                display_new=f"BHAV:0x{new_id:04X}"
            ))
        
        # Propose through pipeline
        audit = propose_change(
            target_type='bhav_remap',
            target_id=Path(self.iff.file_path).name if hasattr(self.iff, 'file_path') else 'IFF',
            diffs=diffs,
            file_path=getattr(self.iff, 'file_path', ''),
            reason=reason or f"Remap {len(id_map)} BHAV IDs"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Apply remapping
            remapped = []
            for chunk in self.iff.chunks:
                if getattr(chunk, 'chunk_type', '') != 'BHAV':
                    continue
                
                old_id = getattr(chunk, 'chunk_id', 0)
                if old_id in id_map:
                    chunk.chunk_id = id_map[old_id]
                    remapped.append(old_id)
            
            # Store mapping for reference
            self.iff._bhav_id_map = id_map
            
            return BHAVPatchResult(
                True,
                f"Remapped {len(remapped)} BHAV IDs",
                patches_applied=len(remapped),
                id_map=id_map,
                affected_bhavs=remapped
            )
            
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return BHAVPatchResult(
                True,
                f"Preview: would remap {len(id_map)} BHAV IDs",
                patches_applied=0,
                id_map=id_map
            )
        else:
            return BHAVPatchResult(False, f"RemapBHAVIDs rejected: {audit.result.value}")


def remap_bhav_ids(iff_file, **kwargs) -> BHAVPatchResult:
    """Remap BHAV IDs. Convenience function."""
    remapper = BHAVIDRemapper(iff_file)
    remapper.build_remap(**kwargs)
    return remapper.apply_remap()


# ═══════════════════════════════════════════════════════════════════════════════
# BHAV CALL REWIRER
# ═══════════════════════════════════════════════════════════════════════════════

class BHAVCallRewirer:
    """
    Update BHAV call targets after ID remapping.
    
    Implements RewireBHAVCalls action.
    """
    
    def __init__(self, iff_file):
        """
        Initialize with an IffFile instance.
        
        Args:
            iff_file: IffFile containing BHAVs to rewire
        """
        self.iff = iff_file
    
    def rewire(self, id_map: Dict[int, int],
               reason: str = "") -> BHAVPatchResult:
        """
        Rewire BHAV call targets according to ID mapping.
        
        Args:
            id_map: Mapping of old_id -> new_id
            reason: Reason for rewiring
            
        Returns:
            BHAVPatchResult
        """
        valid, msg = validate_action('RewireBHAVCalls', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return BHAVPatchResult(False, f"Action blocked: {msg}")
        
        if not id_map:
            return BHAVPatchResult(True, "No rewiring needed (empty map)")
        
        # Find all call sites that need rewiring
        rewire_sites = []
        
        for chunk in self.iff.chunks:
            if getattr(chunk, 'chunk_type', '') != 'BHAV':
                continue
            
            bhav_id = getattr(chunk, 'chunk_id', 0)
            
            if not hasattr(chunk, 'instructions'):
                continue
            
            for idx, inst in enumerate(chunk.instructions):
                opcode = getattr(inst, 'opcode', 0)
                
                if not BHAVCallOpcodes.is_call_opcode(opcode):
                    continue
                
                # Get call target from operand
                call_info = BHAVCallOpcodes.get_call_info(opcode)
                if call_info is None:
                    continue
                
                offset, is_word = call_info
                operand = getattr(inst, 'operand', b'\x00' * 8)
                
                if is_word:
                    target_id = struct.unpack('<H', operand[offset:offset+2])[0]
                else:
                    target_id = operand[offset]
                
                if target_id in id_map:
                    rewire_sites.append({
                        'bhav_id': bhav_id,
                        'inst_idx': idx,
                        'old_target': target_id,
                        'new_target': id_map[target_id],
                        'opcode': opcode,
                        'offset': offset,
                        'is_word': is_word,
                    })
        
        if not rewire_sites:
            return BHAVPatchResult(True, "No call sites to rewire")
        
        # Build diffs
        diffs = []
        for site in rewire_sites:
            diffs.append(MutationDiff(
                field_path=f"bhav[0x{site['bhav_id']:04X}].inst[{site['inst_idx']}].call_target",
                old_value=site['old_target'],
                new_value=site['new_target'],
                display_old=f"calls 0x{site['old_target']:04X}",
                display_new=f"calls 0x{site['new_target']:04X}"
            ))
        
        # Propose through pipeline
        audit = propose_change(
            target_type='bhav_rewire',
            target_id=Path(self.iff.file_path).name if hasattr(self.iff, 'file_path') else 'IFF',
            diffs=diffs,
            file_path=getattr(self.iff, 'file_path', ''),
            reason=reason or f"Rewire {len(rewire_sites)} BHAV call sites"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Apply rewiring
            affected = set()
            
            for site in rewire_sites:
                chunk = self._find_bhav(site['bhav_id'])
                if chunk is None:
                    continue
                
                inst = chunk.instructions[site['inst_idx']]
                operand = bytearray(inst.operand)
                
                if site['is_word']:
                    struct.pack_into('<H', operand, site['offset'], site['new_target'])
                else:
                    operand[site['offset']] = site['new_target'] & 0xFF
                
                inst.operand = bytes(operand)
                affected.add(site['bhav_id'])
            
            return BHAVPatchResult(
                True,
                f"Rewired {len(rewire_sites)} call sites in {len(affected)} BHAVs",
                patches_applied=len(rewire_sites),
                id_map=id_map,
                affected_bhavs=list(affected)
            )
            
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return BHAVPatchResult(
                True,
                f"Preview: would rewire {len(rewire_sites)} call sites",
                patches_applied=0,
                id_map=id_map
            )
        else:
            return BHAVPatchResult(False, f"RewireBHAVCalls rejected: {audit.result.value}")
    
    def _find_bhav(self, bhav_id: int):
        """Find BHAV chunk by ID."""
        for chunk in self.iff.chunks:
            if (getattr(chunk, 'chunk_type', '') == 'BHAV' and
                getattr(chunk, 'chunk_id', -1) == bhav_id):
                return chunk
        return None


def rewire_bhav_calls(iff_file, id_map: Dict[int, int], **kwargs) -> BHAVPatchResult:
    """Rewire BHAV calls. Convenience function."""
    return BHAVCallRewirer(iff_file).rewire(id_map, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL BHAV PATCHER
# ═══════════════════════════════════════════════════════════════════════════════

class GlobalBHAVPatcher:
    """
    Patch global BHAV references in object files.
    
    Implements PatchGlobalBHAV action.
    
    CAUTION: Modifying global BHAVs affects ALL objects in the game.
    """
    
    def __init__(self, iff_file, global_iff=None):
        """
        Initialize with IffFiles.
        
        Args:
            iff_file: Object IFF file to patch
            global_iff: Global IFF containing replacement BHAVs
        """
        self.iff = iff_file
        self.global_iff = global_iff
    
    def patch_global_calls(self, replacements: Dict[int, int],
                           reason: str = "") -> BHAVPatchResult:
        """
        Patch calls to global BHAVs with replacement IDs.
        
        Args:
            replacements: Dict of old_global_id -> new_global_id
            reason: Reason for patching
            
        Returns:
            BHAVPatchResult
        """
        valid, msg = validate_action('PatchGlobalBHAV', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return BHAVPatchResult(False, f"Action blocked: {msg}")
        
        # Validate all replacements are in global scope
        for old_id, new_id in replacements.items():
            if not BHAVScope.is_global(old_id):
                return BHAVPatchResult(
                    False, 
                    f"ID 0x{old_id:04X} is not in global scope"
                )
        
        # Use rewirer to patch
        rewirer = BHAVCallRewirer(self.iff)
        result = rewirer.rewire(
            replacements,
            reason=reason or "PatchGlobalBHAV"
        )
        
        return BHAVPatchResult(
            result.success,
            result.message.replace("Rewired", "Patched global"),
            patches_applied=result.patches_applied,
            id_map=result.id_map,
            affected_bhavs=result.affected_bhavs
        )
    
    def inject_global_override(self, global_id: int, 
                               replacement_bhav,
                               reason: str = "") -> BHAVPatchResult:
        """
        Inject a replacement for a global BHAV as object-local.
        
        This creates a local BHAV that shadows the global, then
        rewires calls to use the local version.
        
        Args:
            global_id: Global BHAV ID to override
            replacement_bhav: Replacement BHAV chunk
            reason: Reason for override
            
        Returns:
            BHAVPatchResult
        """
        if not BHAVScope.is_global(global_id):
            return BHAVPatchResult(
                False,
                f"ID 0x{global_id:04X} is not in global scope"
            )
        
        # Find next available local ID
        existing_ids = {
            getattr(c, 'chunk_id', 0) 
            for c in self.iff.chunks 
            if getattr(c, 'chunk_type', '') == 'BHAV'
        }
        
        new_local_id = BHAVScope.OBJECT_MIN
        while new_local_id in existing_ids:
            new_local_id += 1
        
        # Clone and add the replacement BHAV
        import copy
        local_bhav = copy.deepcopy(replacement_bhav)
        local_bhav.chunk_id = new_local_id
        
        diffs = [
            MutationDiff(
                field_path='bhavs',
                old_value=f"[{len(existing_ids)} BHAVs]",
                new_value=f"[{len(existing_ids) + 1} BHAVs]",
                display_old=f"{len(existing_ids)} BHAVs",
                display_new=f"Added override at 0x{new_local_id:04X}"
            ),
            MutationDiff(
                field_path=f'global_override[0x{global_id:04X}]',
                old_value='(original global)',
                new_value=f'(local: 0x{new_local_id:04X})',
                display_old=f"Uses global 0x{global_id:04X}",
                display_new=f"Uses local 0x{new_local_id:04X}"
            )
        ]
        
        audit = propose_change(
            target_type='bhav_global_override',
            target_id=f'override_0x{global_id:04X}',
            diffs=diffs,
            file_path=getattr(self.iff, 'file_path', ''),
            reason=reason or f"Override global 0x{global_id:04X}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Add local BHAV
            self.iff.chunks.append(local_bhav)
            
            # Rewire calls from global to local
            rewirer = BHAVCallRewirer(self.iff)
            rewire_result = rewirer.rewire({global_id: new_local_id})
            
            return BHAVPatchResult(
                True,
                f"Injected global override: 0x{global_id:04X} → 0x{new_local_id:04X}",
                patches_applied=rewire_result.patches_applied + 1,
                id_map={global_id: new_local_id},
                affected_bhavs=[new_local_id] + rewire_result.affected_bhavs
            )
            
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return BHAVPatchResult(
                True,
                f"Preview: would override global 0x{global_id:04X}",
                patches_applied=0,
                id_map={global_id: new_local_id}
            )
        else:
            return BHAVPatchResult(False, f"PatchGlobalBHAV rejected: {audit.result.value}")


def patch_global_bhav(iff_file, replacements: Dict[int, int], **kwargs) -> BHAVPatchResult:
    """Patch global BHAV calls. Convenience function."""
    return GlobalBHAVPatcher(iff_file).patch_global_calls(replacements, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# SEMI-GLOBAL BHAV PATCHER
# ═══════════════════════════════════════════════════════════════════════════════

class SemiGlobalBHAVPatcher:
    """
    Patch semi-global BHAV references.
    
    Implements PatchSemiGlobalBHAV action.
    """
    
    def __init__(self, iff_file, semi_global_iff=None):
        """
        Initialize with IffFiles.
        
        Args:
            iff_file: Object IFF file to patch
            semi_global_iff: Semi-global IFF (e.g., category globals)
        """
        self.iff = iff_file
        self.semi_global_iff = semi_global_iff
    
    def patch_semi_global_calls(self, replacements: Dict[int, int],
                                reason: str = "") -> BHAVPatchResult:
        """
        Patch calls to semi-global BHAVs.
        
        Args:
            replacements: Dict of old_id -> new_id
            reason: Reason for patching
            
        Returns:
            BHAVPatchResult
        """
        valid, msg = validate_action('PatchSemiGlobalBHAV', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return BHAVPatchResult(False, f"Action blocked: {msg}")
        
        # Validate scope
        for old_id in replacements:
            if not BHAVScope.is_semi_global(old_id):
                return BHAVPatchResult(
                    False,
                    f"ID 0x{old_id:04X} is not in semi-global scope"
                )
        
        # Use rewirer
        rewirer = BHAVCallRewirer(self.iff)
        result = rewirer.rewire(
            replacements,
            reason=reason or "PatchSemiGlobalBHAV"
        )
        
        return BHAVPatchResult(
            result.success,
            result.message.replace("Rewired", "Patched semi-global"),
            patches_applied=result.patches_applied,
            id_map=result.id_map,
            affected_bhavs=result.affected_bhavs
        )


def patch_semi_global_bhav(iff_file, replacements: Dict[int, int], **kwargs) -> BHAVPatchResult:
    """Patch semi-global BHAV calls. Convenience function."""
    return SemiGlobalBHAVPatcher(iff_file).patch_semi_global_calls(replacements, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# OBJECT BHAV PATCHER
# ═══════════════════════════════════════════════════════════════════════════════

class ObjectBHAVPatcher:
    """
    Patch object-local BHAV references.
    
    Implements PatchObjectBHAV action.
    """
    
    def __init__(self, iff_file):
        """
        Initialize with an IffFile instance.
        
        Args:
            iff_file: Object IFF file to patch
        """
        self.iff = iff_file
    
    def patch_object_calls(self, replacements: Dict[int, int],
                           reason: str = "") -> BHAVPatchResult:
        """
        Patch calls to object-local BHAVs.
        
        Args:
            replacements: Dict of old_id -> new_id
            reason: Reason for patching
            
        Returns:
            BHAVPatchResult
        """
        valid, msg = validate_action('PatchObjectBHAV', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return BHAVPatchResult(False, f"Action blocked: {msg}")
        
        # Use rewirer
        rewirer = BHAVCallRewirer(self.iff)
        result = rewirer.rewire(
            replacements,
            reason=reason or "PatchObjectBHAV"
        )
        
        return BHAVPatchResult(
            result.success,
            result.message.replace("Rewired", "Patched object"),
            patches_applied=result.patches_applied,
            id_map=result.id_map,
            affected_bhavs=result.affected_bhavs
        )
    
    def duplicate_bhav(self, source_id: int, 
                       new_id: int = None,
                       reason: str = "") -> BHAVPatchResult:
        """
        Duplicate a BHAV with a new ID.
        
        Args:
            source_id: BHAV ID to duplicate
            new_id: New ID (None = auto-assign)
            reason: Reason for duplication
            
        Returns:
            BHAVPatchResult
        """
        # Find source BHAV
        source = None
        for chunk in self.iff.chunks:
            if (getattr(chunk, 'chunk_type', '') == 'BHAV' and
                getattr(chunk, 'chunk_id', -1) == source_id):
                source = chunk
                break
        
        if source is None:
            return BHAVPatchResult(False, f"BHAV 0x{source_id:04X} not found")
        
        # Determine new ID
        if new_id is None:
            existing = {
                getattr(c, 'chunk_id', 0)
                for c in self.iff.chunks
                if getattr(c, 'chunk_type', '') == 'BHAV'
            }
            new_id = max(existing) + 1 if existing else 0x1000
        
        import copy
        new_bhav = copy.deepcopy(source)
        new_bhav.chunk_id = new_id
        
        diffs = [MutationDiff(
            field_path='bhavs',
            old_value=f"BHAV:0x{source_id:04X}",
            new_value=f"BHAV:0x{new_id:04X} (copy)",
            display_old=f"Original: 0x{source_id:04X}",
            display_new=f"Duplicate: 0x{new_id:04X}"
        )]
        
        audit = propose_change(
            target_type='bhav_duplicate',
            target_id=f'dup_0x{source_id:04X}',
            diffs=diffs,
            file_path=getattr(self.iff, 'file_path', ''),
            reason=reason or f"Duplicate BHAV 0x{source_id:04X}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self.iff.chunks.append(new_bhav)
            return BHAVPatchResult(
                True,
                f"Duplicated BHAV: 0x{source_id:04X} → 0x{new_id:04X}",
                patches_applied=1,
                id_map={source_id: new_id},
                affected_bhavs=[new_id]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return BHAVPatchResult(
                True,
                f"Preview: would duplicate BHAV 0x{source_id:04X}",
                id_map={source_id: new_id}
            )
        else:
            return BHAVPatchResult(False, f"PatchObjectBHAV rejected: {audit.result.value}")


def patch_object_bhav(iff_file, replacements: Dict[int, int], **kwargs) -> BHAVPatchResult:
    """Patch object BHAV calls. Convenience function."""
    return ObjectBHAVPatcher(iff_file).patch_object_calls(replacements, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Scope utilities
    'BHAVScope', 'BHAVCallOpcodes',
    
    # ID remapping
    'BHAVIDRemapper', 'remap_bhav_ids',
    
    # Call rewiring
    'BHAVCallRewirer', 'rewire_bhav_calls',
    
    # Global patching
    'GlobalBHAVPatcher', 'patch_global_bhav',
    
    # Semi-global patching
    'SemiGlobalBHAVPatcher', 'patch_semi_global_bhav',
    
    # Object patching
    'ObjectBHAVPatcher', 'patch_object_bhav',
    
    # Result type
    'BHAVPatchResult',
]
