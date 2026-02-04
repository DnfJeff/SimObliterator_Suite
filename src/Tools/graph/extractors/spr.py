"""SPR/SPR2 reference extractor - Phase 2."""

from typing import List

from ..core import Reference, ResourceNode, TGI, ReferenceKind, ChunkScope
from .base import ReferenceExtractor
from .registry import ExtractorRegistry


@ExtractorRegistry.register("SPR#")
@ExtractorRegistry.register("SPR2")
class SPRExtractor(ReferenceExtractor):
    """
    Extract references from SPR# and SPR2 (sprite) chunks.
    
    Sprites reference:
    - PALT: color palette (always - except SPR# may use default)
    """
    
    @property
    def chunk_type(self) -> str:
        return "SPR2"
    
    def extract(self, sprite, node: ResourceNode) -> List[Reference]:
        """Extract palette references from a sprite."""
        refs: List[Reference] = []
        
        # SPR2 has palette_id field
        if hasattr(sprite, "palette_id"):
            palt_id = sprite.palette_id
            if palt_id > 0:
                target_tgi = TGI("PALT", 0x00000001, palt_id)
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="PALT",
                    owner_iff=node.owner_iff,
                    scope=ChunkScope.OBJECT,
                    label=f"PALT {palt_id}",
                )
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.HARD,
                    source_field="palette_id",
                    description="Sprite color palette",
                    edge_kind="visual",
                ))
        
        # SPR# may have palette in header too
        elif hasattr(sprite, "frame_palette_id"):
            palt_id = sprite.frame_palette_id
            if palt_id > 0:
                target_tgi = TGI("PALT", 0x00000001, palt_id)
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="PALT",
                    owner_iff=node.owner_iff,
                    scope=ChunkScope.OBJECT,
                    label=f"PALT {palt_id}",
                )
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.HARD,
                    source_field="frame_palette_id",
                    description="Sprite color palette",
                    edge_kind="visual",
                ))
        
        return refs
