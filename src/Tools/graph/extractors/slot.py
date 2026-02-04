"""SLOT reference extractor - Structural routing references."""

import sys
from pathlib import Path
from typing import List, Optional

# Ensure formats package is importable
workspace_root = Path(__file__).parent.parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

# Lazy import OBJD
OBJD = None
try:
    from formats.iff.chunks.objd import OBJD
except ImportError:
    pass

from ..core import Reference, ResourceNode, TGI, ReferenceKind, ChunkScope
from .base import ReferenceExtractor
from .registry import ExtractorRegistry


@ExtractorRegistry.register("OBJD_SLOT")  # Sub-extractor for OBJD
class SLOTExtractor(ReferenceExtractor):
    """
    Extract OBJD → SLOT references (routing/placement).
    
    SLOT defines routing positions for objects - where Sims stand, sit, or
    navigate when using an object. Every interactive object has SLOT data.
    
    Reference Pattern:
        OBJD.slot_id (2-byte ID at offset 18) → SLOT resource
    
    Edge Classification: STRUCTURAL
        - Not behavioral code execution
        - Placement and routing infrastructure
        - Critical for in-world positioning
        - Low ambiguity (single field reference)
    
    Strategic Value (Phase 3):
        - Structural edges collapse orphans into meaningful subgraphs
        - Extremely common in real objects
        - Simple, deterministic extraction (baseline for validation)
    """
    
    @property
    def chunk_type(self) -> str:
        return "OBJD"  # We extract from OBJD chunks
    
    def extract(self, objd: Optional[object], node: ResourceNode) -> List[Reference]:
        """Extract SLOT reference from OBJD."""
        if OBJD is None or objd is None:
            return []
        
        refs: List[Reference] = []
        
        # OBJD.slot_id → SLOT (structural routing reference)
        if hasattr(objd, 'slot_id') and objd.slot_id > 0:
            slot_id = objd.slot_id
            target_tgi = TGI("SLOT", 0x00000001, slot_id)
            target_node = ResourceNode(
                tgi=target_tgi,
                chunk_type="SLOT",
                owner_iff=node.owner_iff,
                scope=ChunkScope.OBJECT,
                label=f"SLOT {slot_id}",
            )
            refs.append(Reference(
                source=node,
                target=target_node,
                kind=ReferenceKind.HARD,
                source_field="slot_id",
                description="Routing positions for Sim interactions",
                edge_kind="structural",  # NEW: Phase 3 edge metadata
            ))
            
        return refs
    
    def validate(self, objd: Optional[object], node: ResourceNode) -> List[str]:
        """
        Validate SLOT references.
        
        Validation rules:
        - Interactive objects (type 4 = NORMAL) should have SLOT
        - SLOT ID should be non-zero if present
        - SLOT resource should exist in same IFF file (checked by graph builder)
        """
        if OBJD is None or objd is None:
            return []
        
        warnings = []
        
        # Check if interactive object lacks SLOT
        if hasattr(objd, 'object_type'):
            # NORMAL objects (type 4) typically have slots
            if objd.object_type == 4:  # NORMAL interactive object
                if not hasattr(objd, 'slot_id') or objd.slot_id == 0:
                    warnings.append(
                        f"OBJD {node.tgi.instance_id}: Interactive object lacks SLOT reference"
                    )
        
        return warnings
