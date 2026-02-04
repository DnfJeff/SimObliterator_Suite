"""OBJf reference extractor."""

from typing import List, Optional

from ..core import Reference, ResourceNode, TGI, ReferenceKind, ChunkScope
from .base import ReferenceExtractor
from .registry import ExtractorRegistry


@ExtractorRegistry.register("OBJf")
class OBJfExtractor(ReferenceExtractor):
    """
    Extract references from OBJf (Object Functions) chunks.
    
    OBJf is the modern entry point table, replacing old OBJD tree ID fields.
    It contains up to 31 (guard, action) BHAV pairs for:
    - init, main, load, cleanup, etc.
    - Interactions (eat, sit, stand, cook, etc.)
    """
    
    @property
    def chunk_type(self) -> str:
        return "OBJf"
    
    def extract(self, objf: Optional[object], node: ResourceNode) -> List[Reference]:
        """Extract BHAV references from OBJf."""
        if objf is None:
            return []
        
        refs: List[Reference] = []
        
        if not hasattr(objf, "entries"):
            return []
        
        # Entry point names from tech docs
        entry_names = [
            "init",
            "main",
            "load",
            "cleanup",
            "queue_skipped",
            "allow_intersection",
            "wall_adjacency_changed",
            "room_changed",
            "dynamic_multitile_update",
            "placement",
            "pick_up",
            "cook",
            "eat_food",
            "dispose",
            "fire",
            "burn_down",
            "wash_hands",
            "wash_dishes",
            "use_toilet",
            "use_tub",
            "sit",
            "stand",
            "gardening",
            "repair",
            "eat_surface",
            "serve_surface",
            "clean",
            "portal",
            "tree_initialization",
            "tree_end",
            "reserved",
        ]
        
        entries = objf.entries
        for i, entry in enumerate(entries):
            if i >= len(entry_names):
                break
            
            entry_name = entry_names[i]
            
            # Guard BHAV
            if hasattr(entry, "guard_bhav_id") and entry.guard_bhav_id > 0:
                target_tgi = TGI("BHAV", 0x00000001, entry.guard_bhav_id)
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="BHAV",
                    owner_iff=node.owner_iff,
                    scope=ChunkScope.OBJECT,
                    label=f"BHAV guard {entry_name}",
                )
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.HARD,
                    source_field=f"entry[{i}].guard",
                    description=f"Guard for {entry_name} interaction",
                    edge_kind="behavioral",
                ))
            
            # Action BHAV
            if hasattr(entry, "action_bhav_id") and entry.action_bhav_id > 0:
                target_tgi = TGI("BHAV", 0x00000001, entry.action_bhav_id)
                target_node = ResourceNode(
                    tgi=target_tgi,
                    chunk_type="BHAV",
                    owner_iff=node.owner_iff,
                    scope=ChunkScope.OBJECT,
                    label=f"BHAV action {entry_name}",
                )
                refs.append(Reference(
                    source=node,
                    target=target_node,
                    kind=ReferenceKind.HARD,
                    source_field=f"entry[{i}].action",
                    description=f"Action for {entry_name} entry point",
                    edge_kind="behavioral",
                ))
        
        return refs
