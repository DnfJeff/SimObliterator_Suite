"""
ObjectEntity - System-Level Object Abstraction

An Object is NOT just an OBJD chunk.
An Object is:
- Identity (GUID, name)
- Definition (OBJD properties)
- Behaviors (BHAVs linked via TTAB)
- Visuals (SPR2, DGRP sprites)
- Catalog info (price, room, category)

This entity aggregates all of that into one navigable unit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .behavior_entity import BehaviorEntity


@dataclass
class CatalogInfo:
    """Buy mode catalog information."""
    price: int = 0
    category: str = "Unknown"
    room: str = "Unknown"
    description: str = ""
    expansion: Optional[str] = None


@dataclass
class ObjectEntity:
    """
    System-level Object abstraction.
    
    This is what users think of as "an object" -
    not a chunk, but a complete game entity.
    """
    
    # Identity
    guid: int = 0
    name: str = ""
    
    # Source info
    source_file: str = ""
    source_iff: Optional[Any] = None
    
    # Core chunks (references)
    objd_chunk: Optional[Any] = None
    ttab_chunk: Optional[Any] = None
    sprite_chunks: List[Any] = field(default_factory=list)
    
    # Behaviors (BHAVs this object uses)
    behaviors: List["BehaviorEntity"] = field(default_factory=list)
    behavior_ids: List[int] = field(default_factory=list)
    
    # Catalog
    catalog: CatalogInfo = field(default_factory=CatalogInfo)
    
    # Interactions (from TTAB)
    interactions: List[str] = field(default_factory=list)
    
    # Computed properties
    is_autonomous: bool = False
    is_breakable: bool = False
    is_sellable: bool = True
    
    # Dependencies
    depends_on: List[int] = field(default_factory=list)  # GUIDs of required objects
    global_bhavs: List[int] = field(default_factory=list)  # Global BHAVs used
    semi_global_bhavs: List[int] = field(default_factory=list)
    
    @classmethod
    def from_iff(cls, iff, filename: str = "") -> List["ObjectEntity"]:
        """
        Extract all objects from an IFF file.
        Returns list of ObjectEntity.
        """
        objects = []
        
        chunks = iff.chunks if hasattr(iff, 'chunks') else []
        
        # Index chunks by type
        by_type: Dict[str, List[Any]] = {}
        for chunk in chunks:
            chunk_type = getattr(chunk, 'type_code', '') or getattr(chunk, 'chunk_type', '')
            if chunk_type not in by_type:
                by_type[chunk_type] = []
            by_type[chunk_type].append(chunk)
        
        # Find all OBJDs
        for objd in by_type.get('OBJD', []):
            obj = cls._from_objd(objd, by_type, iff, filename)
            objects.append(obj)
        
        return objects
    
    @classmethod
    def _from_objd(cls, objd, by_type: Dict, iff, filename: str) -> "ObjectEntity":
        """Build ObjectEntity from OBJD chunk."""
        entity = cls(
            guid=getattr(objd, 'guid', 0),
            name=getattr(objd, 'name', f'Object #{objd.chunk_id}'),
            source_file=filename,
            source_iff=iff,
            objd_chunk=objd,
        )
        
        # Extract catalog info
        entity.catalog = CatalogInfo(
            price=getattr(objd, 'price', 0),
            category=getattr(objd, 'catalog_string', 'Unknown'),
            room=getattr(objd, 'room_sort', 'Unknown'),
        )
        
        # Find TTAB (interactions)
        for ttab in by_type.get('TTAB', []):
            entity.ttab_chunk = ttab
            entity.interactions = cls._extract_interactions(ttab)
            entity.behavior_ids = cls._extract_bhav_refs(ttab)
            break
        
        # Find sprites
        entity.sprite_chunks = by_type.get('SPR2', [])[:5]  # First 5
        
        # Compute flags
        flags = getattr(objd, 'flags', 0)
        if flags:
            entity.is_autonomous = bool(flags & 0x0001)
            entity.is_breakable = bool(flags & 0x0008)
        
        # Analyze BHAV dependencies
        entity._analyze_dependencies(by_type.get('BHAV', []))
        
        return entity
    
    @staticmethod
    def _extract_interactions(ttab) -> List[str]:
        """Extract interaction names from TTAB."""
        interactions = []
        entries = getattr(ttab, 'entries', [])
        for entry in entries[:10]:
            name = getattr(entry, 'name', None)
            if name:
                interactions.append(name)
        return interactions
    
    @staticmethod
    def _extract_bhav_refs(ttab) -> List[int]:
        """Extract BHAV references from TTAB."""
        refs = []
        entries = getattr(ttab, 'entries', [])
        for entry in entries:
            bhav_id = getattr(entry, 'action_function', None)
            if bhav_id:
                refs.append(bhav_id)
            check_id = getattr(entry, 'check_function', None)
            if check_id:
                refs.append(check_id)
        return list(set(refs))
    
    def _analyze_dependencies(self, bhavs: List[Any]):
        """Analyze BHAV calls to find dependencies."""
        for bhav in bhavs:
            bhav_id = getattr(bhav, 'chunk_id', 0)
            if bhav_id not in self.behavior_ids:
                continue
            
            instructions = getattr(bhav, 'instructions', [])
            for instr in instructions:
                opcode = getattr(instr, 'opcode', 0)
                
                # Global call
                if 0x0100 <= opcode < 0x0200:
                    if opcode not in self.global_bhavs:
                        self.global_bhavs.append(opcode)
                
                # Semi-global call
                elif 0x0200 <= opcode < 0x1000:
                    if opcode not in self.semi_global_bhavs:
                        self.semi_global_bhavs.append(opcode)
    
    # ─────────────────────────────────────────────────────────────
    # QUERY METHODS
    # ─────────────────────────────────────────────────────────────
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get human-readable summary.
        This is what CC creators want to see!
        """
        return {
            "name": self.name,
            "guid": f"0x{self.guid:08X}",
            "price": f"§{self.catalog.price}",
            "category": self.catalog.category,
            "interactions": self.interactions[:5],
            "autonomous": "Yes" if self.is_autonomous else "No",
            "breakable": "Yes" if self.is_breakable else "No",
            "behaviors": len(self.behavior_ids),
            "uses_globals": len(self.global_bhavs),
        }
    
    def get_behavior_summary(self) -> str:
        """One-liner about behaviors."""
        total = len(self.behavior_ids)
        globals_count = len(self.global_bhavs)
        
        if globals_count > 0:
            return f"{total} behaviors ({globals_count} global calls)"
        return f"{total} behaviors"
    
    def get_complexity(self) -> str:
        """Estimate object complexity."""
        total_bhavs = len(self.behavior_ids)
        total_globals = len(self.global_bhavs)
        
        if total_bhavs == 0:
            return "Simple (no behaviors)"
        elif total_bhavs <= 3 and total_globals == 0:
            return "Basic"
        elif total_bhavs <= 10:
            return "Standard"
        elif total_bhavs <= 25:
            return "Complex"
        else:
            return "Very Complex"
    
    def __repr__(self):
        return f"ObjectEntity(guid=0x{self.guid:08X}, name='{self.name}')"
