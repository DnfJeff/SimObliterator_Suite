"""OBJD reference extractor - Phase 1."""

import sys
from pathlib import Path
from typing import List, Optional

# Ensure formats package is importable
workspace_root = Path(__file__).parent.parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

# Lazy import OBJD - try to import but don't fail if unavailable
OBJD = None
try:
    from formats.iff import OBJD
except ImportError:
    pass

from ..core import Reference, ResourceNode, TGI, ReferenceKind, ChunkScope
from .base import ReferenceExtractor
from .registry import ExtractorRegistry


@ExtractorRegistry.register("OBJD")
class OBJDExtractor(ReferenceExtractor):
    """
    Extract references from OBJD (Object Definition) chunks.
    
    OBJD is the master resource for objects. It references:
    - BHAV: init, main, cleanup, and ~30 other behavior entry points
    - STR#: catalog/body strings
    - SPR/DGRP: graphics
    - SLOT: routing/positioning
    - GLOB: semi-global reference (implicit)
    """
    
    @property
    def chunk_type(self) -> str:
        return "OBJD"
    
    def extract(self, objd: Optional[object], node: ResourceNode) -> List[Reference]:
        """Extract all references from an OBJD chunk."""
        if OBJD is None or objd is None:
            return []
        
        refs: List[Reference] = []
        
        # Graphics references (DGRP - draw group)
        if hasattr(objd, "base_graphic_id") and objd.base_graphic_id > 0:
            dgrp_id = objd.base_graphic_id
            target_tgi = TGI("DGRP", 0x00000001, dgrp_id)
            target_node = ResourceNode(
                tgi=target_tgi,
                chunk_type="DGRP",
                owner_iff=node.owner_iff,
                scope=ChunkScope.OBJECT,
                label=f"DGRP {dgrp_id}",
            )
            refs.append(Reference(
                source=node,
                target=target_node,
                kind=ReferenceKind.HARD,
                source_field="base_graphic_id",
                description="Base graphics draw group",
                edge_kind="visual",
            ))
        
        # Interaction table (TTAB - tree table)
        if hasattr(objd, "tree_table_id") and objd.tree_table_id > 0:
            ttab_id = objd.tree_table_id
            target_tgi = TGI("TTAB", 0x00000001, ttab_id)
            target_node = ResourceNode(
                tgi=target_tgi,
                chunk_type="TTAB",
                owner_iff=node.owner_iff,
                scope=ChunkScope.OBJECT,
                label=f"TTAB {ttab_id}",
            )
            refs.append(Reference(
                source=node,
                target=target_node,
                kind=ReferenceKind.HARD,
                source_field="tree_table_id",
                description="Interaction tree table",
                edge_kind="behavioral",
            ))
        
        # Routing (SLOT - approach/footprint)
        if hasattr(objd, "slot_id") and objd.slot_id > 0:
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
                description="Object routing and footprint",
                edge_kind="structural",
            ))
        
        # String references
        if hasattr(objd, "catalog_strings_id") and objd.catalog_strings_id > 0:
            str_id = objd.catalog_strings_id
            target_tgi = TGI("STR#", 0x00000001, str_id)
            target_node = ResourceNode(
                tgi=target_tgi,
                chunk_type="STR#",
                owner_iff=node.owner_iff,
                scope=ChunkScope.OBJECT,
                label=f"STR# catalog",
            )
            refs.append(Reference(
                source=node,
                target=target_node,
                kind=ReferenceKind.HARD,
                source_field="catalog_strings_id",
                description="Catalog text strings",
                edge_kind="tuning",
            ))
        
        if hasattr(objd, "body_string_id") and objd.body_string_id > 0:
            str_id = objd.body_string_id
            target_tgi = TGI("STR#", 0x00000001, str_id)
            target_node = ResourceNode(
                tgi=target_tgi,
                chunk_type="STR#",
                owner_iff=node.owner_iff,
                scope=ChunkScope.OBJECT,
                label=f"STR# body",
            )
            refs.append(Reference(
                source=node,
                target=target_node,
                kind=ReferenceKind.HARD,
                source_field="body_string_id",
                description="Object description/body text",
                edge_kind="tuning",
            ))
        
        # Legacy BHAV entry points (usually 0 in modern TS1, but handle them if present)
        bhav_fields = [
            ("bhav_init", "init"),
            ("bhav_main_id", "main"),
            ("bhav_cleanup", "cleanup"),
        ]
        
        for field_name, description in bhav_fields:
            if hasattr(objd, field_name):
                bhav_id = getattr(objd, field_name, 0)
                if bhav_id > 0:
                    target_tgi = TGI("BHAV", 0x00000001, bhav_id)
                    target_node = ResourceNode(
                        tgi=target_tgi,
                        chunk_type="BHAV",
                        owner_iff=node.owner_iff,
                        scope=ChunkScope.OBJECT,
                        label=f"BHAV {description}",
                    )
                    refs.append(Reference(
                        source=node,
                        target=target_node,
                        kind=ReferenceKind.HARD,
                        source_field=field_name,
                        description=f"Legacy entry point: {description}",
                        edge_kind="behavioral",
                    ))
        
        return refs
