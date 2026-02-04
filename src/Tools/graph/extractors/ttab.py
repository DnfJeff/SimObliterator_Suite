"""
TTAB Reference Extractor

Extracts references from TTAB (interaction table) chunks:
  - TTAB → BHAV (action function)
  - TTAB → BHAV (test/guard function)
  - TTAB → TTAs (string table)
"""

from typing import List, Optional

from ..core import Reference, ResourceNode, TGI, ReferenceKind, ChunkScope
from .base import ReferenceExtractor
from .registry import ExtractorRegistry


@ExtractorRegistry.register("TTAB")
class TTABExtractor(ReferenceExtractor):
    """
    Extract references from TTAB (interaction table) chunks.
    
    TTAB defines object interactions (pie menu items).
    Each interaction has:
      - Action BHAV: the behavior to execute
      - Guard BHAV: the condition to check
      - TTAs index: the string table with menu text
    
    All references are OBJECT scope (interactions are per-object).
    """
    
    @property
    def chunk_type(self) -> str:
        return "TTAB"
    
    def extract(self, ttab: Optional[object], node: ResourceNode) -> List[Reference]:
        """Extract references from TTAB chunk."""
        if ttab is None:
            return []
        
        # Verify this is a MinimalTTAB object
        if not hasattr(ttab, 'interactions'):
            return []
        
        refs: List[Reference] = []
        
        # Extract references from each interaction
        for interaction_idx, interaction in enumerate(ttab.interactions):
            # Action BHAV reference
            if interaction.action_function > 0:
                target_tgi = TGI(
                    type_code="BHAV",
                    group_id=0x00000001,
                    instance_id=interaction.action_function
                )
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="BHAV",
                    owner_iff=node.owner_iff,
                    scope=ChunkScope.OBJECT,
                    label=f"BHAV action",
                )
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.HARD,
                    source_field=f"interaction_{interaction_idx}",
                    description=f"Interaction {interaction_idx}: Action BHAV",
                    edge_kind="behavioral",
                ))
            
            # Guard (test) BHAV reference
            if interaction.test_function > 0:
                target_tgi = TGI(
                    type_code="BHAV",
                    group_id=0x00000001,
                    instance_id=interaction.test_function
                )
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="BHAV",
                    owner_iff=node.owner_iff,
                    scope=ChunkScope.OBJECT,
                    label=f"BHAV guard",
                )
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.HARD,
                    source_field=f"interaction_{interaction_idx}",
                    description=f"Interaction {interaction_idx}: Guard BHAV",
                    edge_kind="behavioral",
                ))
            
            # TTAs (string table) reference
            if interaction.tta_index > 0:
                target_tgi = TGI(
                    type_code="TTAs",
                    group_id=0x00000001,
                    instance_id=interaction.tta_index
                )
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="TTAs",
                    owner_iff=node.owner_iff,
                    scope=ChunkScope.OBJECT,
                    label=f"TTAs string",
                )
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.INDEXED,
                    source_field=f"interaction_{interaction_idx}",
                    description=f"Interaction {interaction_idx}: Menu text",
                    edge_kind="tuning",
                ))
        
        return refs
