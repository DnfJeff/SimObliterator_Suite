"""DGRP reference extractor - Drawing groups to sprites."""

from typing import List, Optional

from ..core import Reference, ResourceNode, TGI, ReferenceKind, ChunkScope
from .base import ReferenceExtractor
from .registry import ExtractorRegistry


@ExtractorRegistry.register("DGRP")
class DGRPExtractor(ReferenceExtractor):
    """
    Extract references from DGRP (Drawing Group) chunks.
    
    DGRP chunks contain sprite references:
    - DGRP → SPR2: Each sprite in the drawing group
    
    A DGRP organizes sprites for one object tile across all
    directions and zoom levels.
    """
    
    @property
    def chunk_type(self) -> str:
        return "DGRP"
    
    def extract(self, dgrp: Optional[object], node: ResourceNode) -> List[Reference]:
        """Extract all sprite references from a DGRP chunk."""
        if dgrp is None:
            return []
        
        refs: List[Reference] = []
        
        # Verify this is actually a DGRP object
        if not hasattr(dgrp, 'images'):
            return []
        
        # Track which sprite IDs we've already added (avoid duplicates)
        seen_sprites = set()
        
        # Iterate through all images (direction/zoom combos)
        for img_idx, image in enumerate(dgrp.images):
            if not hasattr(image, 'sprites'):
                continue
            
            # Extract each sprite reference
            for sprite_idx, sprite in enumerate(image.sprites):
                if not hasattr(sprite, 'sprite_id'):
                    continue
                
                sprite_id = sprite.sprite_id
                
                # Skip if we've already added this sprite
                # (same sprite used in multiple directions/zooms)
                if sprite_id in seen_sprites:
                    continue
                seen_sprites.add(sprite_id)
                
                target_tgi = TGI("SPR2", 0x00000001, sprite_id)
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="SPR2",
                    owner_iff=node.owner_iff,
                    scope=ChunkScope.OBJECT,
                    label=f"SPR2 {sprite_id}",
                )
                
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.HARD,
                    source_field=f"image_{img_idx}_sprite_{sprite_idx}",
                    description=f"Drawing group sprite reference (dir={image.direction}, zoom={image.zoom})",
                    edge_kind="visual",
                ))
        
        return refs
