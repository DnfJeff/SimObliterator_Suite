"""
Mapping Database

Persistent storage for game structure maps built during analysis.
Stores behavior library, object registry, chunk distributions, cross-references.

Features:
- Comprehensive game mapping storage
- Incremental updates (add to existing maps)
- Fast lookup by various keys (BHAV ID, object name, GUID, etc.)
- Cross-reference tracking

Usage:
    from core.mapping_db import MappingDatabase, get_mapping_db
    
    db = get_mapping_db()
    db.add_behavior(bhav_id=0x1000, name="main", owner="chair.iff", ...)
    db.save()
"""

import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

# Path to JSON database
_DATA_DIR = Path(__file__).parent.parent / "data"
_MAPPINGS_JSON = _DATA_DIR / "mappings_db.json"


class MappingDatabase:
    """Manages persistent storage of game structure maps."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._data = None
        self._dirty = False
        self._load()
        self._initialized = True
    
    def _load(self):
        """Load database from JSON file."""
        try:
            if _MAPPINGS_JSON.exists():
                with open(_MAPPINGS_JSON, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            else:
                self._data = self._create_empty_db()
        except Exception as e:
            print(f"Warning: Could not load mappings_db.json: {e}")
            self._data = self._create_empty_db()
    
    def _create_empty_db(self) -> Dict:
        """Create empty database structure."""
        return {
            "_meta": {
                "version": "1.0.0",
                "description": "Game structure maps - behaviors, objects, relationships",
                "created": datetime.now().isoformat(),
                "last_full_scan": None,
                "game_path": None,
                "total_behaviors": 0,
                "total_objects": 0
            },
            "behaviors": {},          # BHAV registry: {unique_key: BehaviorEntry}
            "objects": {},            # Object registry: {object_name: ObjectEntry}
            "chunk_distributions": {},# Per-file chunk stats
            "cross_references": {},   # BHAV call graph, etc.
            "global_behaviors": {},   # From Global.iff
            "semi_global_libraries": {}# Semi-global files
        }
    
    def save(self):
        """Save database to JSON file."""
        if not self._dirty:
            return
        
        with self._lock:
            try:
                # Update meta counts
                self._data["_meta"]["total_behaviors"] = len(self._data["behaviors"])
                self._data["_meta"]["total_objects"] = len(self._data["objects"])
                
                _DATA_DIR.mkdir(parents=True, exist_ok=True)
                
                with open(_MAPPINGS_JSON, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False)
                
                self._dirty = False
            except Exception as e:
                print(f"Error saving mappings database: {e}")
    
    # ═══════════════════════════════════════════════════════════════════
    # BEHAVIOR REGISTRY
    # ═══════════════════════════════════════════════════════════════════
    
    def add_behavior(
        self,
        bhav_id: int,
        name: str,
        owner_file: str,
        instruction_count: int = 0,
        role: str = "UNKNOWN",
        scope: str = "LOCAL",
        entry_points: Optional[List[str]] = None,
        calls: Optional[List[int]] = None,
        called_by: Optional[List[str]] = None
    ) -> str:
        """
        Add a behavior to the registry.
        
        Args:
            bhav_id: BHAV chunk ID
            name: BHAV label/name
            owner_file: IFF file containing this BHAV
            instruction_count: Number of instructions
            role: ROLE/ACTION/FLOW classification
            scope: LOCAL/GLOBAL/SEMI-GLOBAL
            entry_points: How this BHAV is entered (OBJf, TTAB, etc.)
            calls: List of BHAV IDs this behavior calls
            called_by: List of owner_file:bhav_id that call this
        
        Returns:
            Unique key for this behavior entry
        """
        # Create unique key: owner_file:bhav_id
        unique_key = f"{owner_file}:{bhav_id}"
        
        with self._lock:
            self._data["behaviors"][unique_key] = {
                "bhav_id": bhav_id,
                "name": name,
                "owner_file": owner_file,
                "instruction_count": instruction_count,
                "role": role,
                "scope": scope,
                "entry_points": entry_points or [],
                "calls": calls or [],
                "called_by": called_by or [],
                "first_seen": datetime.now().isoformat()
            }
            self._dirty = True
        
        return unique_key
    
    def get_behavior(self, owner_file: str, bhav_id: int) -> Optional[Dict]:
        """Get a specific behavior entry."""
        unique_key = f"{owner_file}:{bhav_id}"
        return self._data["behaviors"].get(unique_key)
    
    def find_behaviors_by_name(self, name_pattern: str) -> List[Dict]:
        """Find behaviors matching name pattern (case-insensitive)."""
        pattern_lower = name_pattern.lower()
        results = []
        for entry in self._data["behaviors"].values():
            if pattern_lower in entry["name"].lower():
                results.append(entry)
        return results
    
    def find_behaviors_by_role(self, role: str) -> List[Dict]:
        """Get all behaviors with a specific role."""
        return [e for e in self._data["behaviors"].values() if e["role"] == role]
    
    def get_all_behaviors(self) -> Dict:
        """Get all behaviors."""
        return self._data["behaviors"].copy()
    
    # ═══════════════════════════════════════════════════════════════════
    # OBJECT REGISTRY
    # ═══════════════════════════════════════════════════════════════════
    
    def add_object(
        self,
        object_name: str,
        source_file: str,
        object_type: str = "UNKNOWN",
        guid: Optional[int] = None,
        bhav_count: int = 0,
        chunk_types: Optional[Dict[str, int]] = None,
        ttab_count: int = 0,
        semi_global: Optional[str] = None
    ) -> str:
        """
        Add an object to the registry.
        
        Args:
            object_name: Object identifier (usually filename without extension)
            source_file: Full path or archive entry name
            object_type: OBJECT/CHARACTER/GLOBAL/SEMI-GLOBAL
            guid: Object GUID from OBJD
            bhav_count: Number of BHAVs in this object
            chunk_types: Distribution of chunk types {type: count}
            ttab_count: Number of TTAB interactions
            semi_global: Semi-global library used (GLOB chunk reference)
        
        Returns:
            Object name key
        """
        with self._lock:
            self._data["objects"][object_name] = {
                "object_name": object_name,
                "source_file": source_file,
                "object_type": object_type,
                "guid": guid,
                "bhav_count": bhav_count,
                "chunk_types": chunk_types or {},
                "ttab_count": ttab_count,
                "semi_global": semi_global,
                "first_seen": datetime.now().isoformat()
            }
            self._dirty = True
        
        return object_name
    
    def get_object(self, object_name: str) -> Optional[Dict]:
        """Get a specific object entry."""
        return self._data["objects"].get(object_name)
    
    def find_objects_by_type(self, object_type: str) -> List[Dict]:
        """Get all objects of a specific type."""
        return [e for e in self._data["objects"].values() if e["object_type"] == object_type]
    
    def find_objects_using_semi_global(self, semi_global: str) -> List[Dict]:
        """Find all objects using a specific semi-global library."""
        return [e for e in self._data["objects"].values() if e.get("semi_global") == semi_global]
    
    def get_all_objects(self) -> Dict:
        """Get all objects."""
        return self._data["objects"].copy()
    
    # ═══════════════════════════════════════════════════════════════════
    # CHUNK DISTRIBUTIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def add_chunk_distribution(self, source_file: str, distribution: Dict[str, int]):
        """Record chunk type distribution for a file."""
        with self._lock:
            self._data["chunk_distributions"][source_file] = {
                "distribution": distribution,
                "total_chunks": sum(distribution.values()),
                "timestamp": datetime.now().isoformat()
            }
            self._dirty = True
    
    def get_global_chunk_distribution(self) -> Dict[str, int]:
        """Get aggregated chunk distribution across all files."""
        totals = {}
        for entry in self._data["chunk_distributions"].values():
            for chunk_type, count in entry.get("distribution", {}).items():
                totals[chunk_type] = totals.get(chunk_type, 0) + count
        return totals
    
    # ═══════════════════════════════════════════════════════════════════
    # CROSS-REFERENCES
    # ═══════════════════════════════════════════════════════════════════
    
    def add_cross_reference(
        self,
        ref_type: str,
        source: str,
        target: str,
        context: Optional[Dict] = None
    ):
        """
        Add a cross-reference.
        
        Args:
            ref_type: Type of reference (BHAV_CALL, TTAB_ACTION, OBJF_HOOK, etc.)
            source: Source identifier (file:id)
            target: Target identifier (file:id)
            context: Additional context
        """
        with self._lock:
            if ref_type not in self._data["cross_references"]:
                self._data["cross_references"][ref_type] = []
            
            ref = {
                "source": source,
                "target": target,
                "context": context or {}
            }
            
            # Avoid duplicates
            if ref not in self._data["cross_references"][ref_type]:
                self._data["cross_references"][ref_type].append(ref)
                self._dirty = True
    
    def get_references_to(self, target: str) -> List[Dict]:
        """Get all references pointing to a target."""
        results = []
        for ref_type, refs in self._data["cross_references"].items():
            for ref in refs:
                if ref["target"] == target:
                    results.append({"type": ref_type, **ref})
        return results
    
    def get_references_from(self, source: str) -> List[Dict]:
        """Get all references from a source."""
        results = []
        for ref_type, refs in self._data["cross_references"].items():
            for ref in refs:
                if ref["source"] == source:
                    results.append({"type": ref_type, **ref})
        return results
    
    # ═══════════════════════════════════════════════════════════════════
    # GLOBAL & SEMI-GLOBAL
    # ═══════════════════════════════════════════════════════════════════
    
    def set_global_behaviors(self, behaviors: Dict):
        """Set the Global.iff behavior map."""
        with self._lock:
            self._data["global_behaviors"] = behaviors
            self._dirty = True
    
    def add_semi_global_library(self, library_name: str, behaviors: Dict):
        """Add a semi-global library's behaviors."""
        with self._lock:
            self._data["semi_global_libraries"][library_name] = {
                "behaviors": behaviors,
                "timestamp": datetime.now().isoformat()
            }
            self._dirty = True
    
    def get_global_behavior(self, bhav_id: int) -> Optional[Dict]:
        """Look up a behavior in Global.iff."""
        return self._data["global_behaviors"].get(str(bhav_id))
    
    def get_semi_global_behavior(self, library: str, bhav_id: int) -> Optional[Dict]:
        """Look up a behavior in a semi-global library."""
        lib = self._data["semi_global_libraries"].get(library)
        if lib:
            return lib.get("behaviors", {}).get(str(bhav_id))
        return None
    
    # ═══════════════════════════════════════════════════════════════════
    # META & UTILITIES
    # ═══════════════════════════════════════════════════════════════════
    
    def set_game_path(self, path: str):
        """Set the game installation path."""
        with self._lock:
            self._data["_meta"]["game_path"] = path
            self._dirty = True
    
    def record_full_scan(self):
        """Record that a full game scan was completed."""
        with self._lock:
            self._data["_meta"]["last_full_scan"] = datetime.now().isoformat()
            self._dirty = True
    
    def get_statistics(self) -> Dict:
        """Get database statistics."""
        return {
            "total_behaviors": len(self._data["behaviors"]),
            "total_objects": len(self._data["objects"]),
            "chunk_distributions_recorded": len(self._data["chunk_distributions"]),
            "cross_reference_types": len(self._data["cross_references"]),
            "global_behaviors": len(self._data["global_behaviors"]),
            "semi_global_libraries": len(self._data["semi_global_libraries"]),
            "game_path": self._data["_meta"].get("game_path"),
            "last_full_scan": self._data["_meta"].get("last_full_scan")
        }
    
    def clear_all(self):
        """Clear all data (for fresh start)."""
        with self._lock:
            self._data = self._create_empty_db()
            self._dirty = True
    
    def export_behavior_library(self) -> str:
        """Export behavior library as readable text."""
        lines = []
        lines.append("=" * 80)
        lines.append("BEHAVIOR LIBRARY EXPORT")
        lines.append("=" * 80)
        
        stats = self.get_statistics()
        lines.append(f"\nTotal Behaviors: {stats['total_behaviors']}")
        lines.append(f"Total Objects: {stats['total_objects']}")
        lines.append(f"Game Path: {stats['game_path'] or 'Not set'}")
        
        # Group by role
        by_role = {"ROLE": [], "ACTION": [], "FLOW": [], "UNKNOWN": []}
        for entry in self._data["behaviors"].values():
            role = entry.get("role", "UNKNOWN")
            if role not in by_role:
                by_role[role] = []
            by_role[role].append(entry)
        
        for role, behaviors in by_role.items():
            if behaviors:
                lines.append(f"\n{'=' * 40}")
                lines.append(f"{role} BEHAVIORS ({len(behaviors)})")
                lines.append("=" * 40)
                for b in sorted(behaviors, key=lambda x: x["name"]):
                    lines.append(f"  {b['name']:<30} [{b['owner_file']}] {b['instruction_count']} instr")
        
        return "\n".join(lines)


# Convenience function
def get_mapping_db() -> MappingDatabase:
    """Get the singleton MappingDatabase instance."""
    return MappingDatabase()
