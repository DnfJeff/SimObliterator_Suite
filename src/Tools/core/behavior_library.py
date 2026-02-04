"""
Behavior Library Service

Shared service for BHAV lookup, search, and categorization.
Used by IFF Viewer, Graph View, and any other tool needing behavior info.

Features:
- Fast lookup by BHAV ID, name, or pattern
- Role-based filtering (ROLE/ACTION/FLOW)
- Global/Semi-global resolution
- Lazy loading from MappingDatabase

Usage:
    from core.behavior_library import BehaviorLibrary, get_behavior_library
    
    lib = get_behavior_library()
    bhav = lib.lookup("chair.iff", 0x1000)
    main_behaviors = lib.find_by_role("ROLE")
    results = lib.search("cook")
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from .mapping_db import get_mapping_db
from .opcode_loader import get_opcode_info, is_known_opcode


@dataclass
class BehaviorInfo:
    """Information about a behavior."""
    bhav_id: int
    name: str
    owner_file: str
    instruction_count: int = 0
    role: str = "UNKNOWN"
    scope: str = "LOCAL"
    entry_points: List[str] = field(default_factory=list)
    
    @property
    def unique_key(self) -> str:
        return f"{self.owner_file}:{self.bhav_id}"
    
    @property
    def display_name(self) -> str:
        """Human-friendly display name."""
        if self.name and not self.name.startswith("BHAV_"):
            return self.name
        return f"BHAV #{self.bhav_id} ({self.owner_file})"


class BehaviorLibrary:
    """Central service for behavior information."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._cache: Dict[str, BehaviorInfo] = {}
        self._by_name_index: Dict[str, List[str]] = {}  # name_lower -> [unique_keys]
        self._by_role_index: Dict[str, List[str]] = {}  # role -> [unique_keys]
        self._loaded = False
        self._initialized = True
    
    def _ensure_loaded(self):
        """Ensure data is loaded from database."""
        if self._loaded:
            return
        
        db = get_mapping_db()
        behaviors = db.get_all_behaviors()
        
        for key, entry in behaviors.items():
            info = BehaviorInfo(
                bhav_id=entry.get("bhav_id", 0),
                name=entry.get("name", ""),
                owner_file=entry.get("owner_file", ""),
                instruction_count=entry.get("instruction_count", 0),
                role=entry.get("role", "UNKNOWN"),
                scope=entry.get("scope", "LOCAL"),
                entry_points=entry.get("entry_points", [])
            )
            self._cache[key] = info
            
            # Build name index
            name_lower = info.name.lower()
            if name_lower not in self._by_name_index:
                self._by_name_index[name_lower] = []
            self._by_name_index[name_lower].append(key)
            
            # Build role index
            if info.role not in self._by_role_index:
                self._by_role_index[info.role] = []
            self._by_role_index[info.role].append(key)
        
        self._loaded = True
    
    def reload(self):
        """Force reload from database."""
        self._cache.clear()
        self._by_name_index.clear()
        self._by_role_index.clear()
        self._loaded = False
        self._ensure_loaded()
    
    # ═══════════════════════════════════════════════════════════════════
    # LOOKUP METHODS
    # ═══════════════════════════════════════════════════════════════════
    
    def lookup(self, owner_file: str, bhav_id: int) -> Optional[BehaviorInfo]:
        """
        Look up a specific behavior.
        
        Args:
            owner_file: IFF file name
            bhav_id: BHAV chunk ID
        
        Returns:
            BehaviorInfo or None if not found
        """
        self._ensure_loaded()
        key = f"{owner_file}:{bhav_id}"
        return self._cache.get(key)
    
    def lookup_by_key(self, unique_key: str) -> Optional[BehaviorInfo]:
        """Look up by unique key (file:id)."""
        self._ensure_loaded()
        return self._cache.get(unique_key)
    
    def lookup_global(self, bhav_id: int) -> Optional[BehaviorInfo]:
        """Look up a behavior in Global.iff."""
        return self.lookup("Global.iff", bhav_id)
    
    def lookup_semi_global(self, library: str, bhav_id: int) -> Optional[BehaviorInfo]:
        """Look up a behavior in a semi-global library."""
        # Semi-globals may have different naming patterns
        candidates = [
            f"{library}.iff",
            f"semiglobal_{library}.iff",
            library
        ]
        for name in candidates:
            result = self.lookup(name, bhav_id)
            if result:
                return result
        return None
    
    # ═══════════════════════════════════════════════════════════════════
    # SEARCH METHODS
    # ═══════════════════════════════════════════════════════════════════
    
    def search(self, pattern: str, limit: int = 50) -> List[BehaviorInfo]:
        """
        Search behaviors by name pattern.
        
        Args:
            pattern: Search string (case-insensitive)
            limit: Maximum results to return
        
        Returns:
            List of matching BehaviorInfo
        """
        self._ensure_loaded()
        pattern_lower = pattern.lower()
        results = []
        
        for info in self._cache.values():
            if pattern_lower in info.name.lower():
                results.append(info)
                if len(results) >= limit:
                    break
        
        return results
    
    def search_exact_name(self, name: str) -> List[BehaviorInfo]:
        """Search for behaviors with exact name (case-insensitive)."""
        self._ensure_loaded()
        name_lower = name.lower()
        keys = self._by_name_index.get(name_lower, [])
        return [self._cache[k] for k in keys if k in self._cache]
    
    def find_by_role(self, role: str) -> List[BehaviorInfo]:
        """Get all behaviors with a specific role."""
        self._ensure_loaded()
        keys = self._by_role_index.get(role, [])
        return [self._cache[k] for k in keys if k in self._cache]
    
    def find_by_owner(self, owner_file: str) -> List[BehaviorInfo]:
        """Get all behaviors from a specific file."""
        self._ensure_loaded()
        return [info for info in self._cache.values() if info.owner_file == owner_file]
    
    def find_entry_points(self) -> List[BehaviorInfo]:
        """Get behaviors that are entry points (called from OBJf/TTAB)."""
        self._ensure_loaded()
        return [info for info in self._cache.values() if info.entry_points]
    
    # ═══════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get library statistics."""
        self._ensure_loaded()
        
        role_counts = {}
        scope_counts = {}
        
        for info in self._cache.values():
            role_counts[info.role] = role_counts.get(info.role, 0) + 1
            scope_counts[info.scope] = scope_counts.get(info.scope, 0) + 1
        
        return {
            "total_behaviors": len(self._cache),
            "by_role": role_counts,
            "by_scope": scope_counts,
            "unique_names": len(self._by_name_index)
        }
    
    def get_all(self) -> List[BehaviorInfo]:
        """Get all behaviors."""
        self._ensure_loaded()
        return list(self._cache.values())
    
    # ═══════════════════════════════════════════════════════════════════
    # RESOLUTION (for cross-file lookups)
    # ═══════════════════════════════════════════════════════════════════
    
    def resolve_call(
        self, 
        caller_file: str, 
        target_bhav_id: int, 
        call_type: str = "private"
    ) -> Optional[BehaviorInfo]:
        """
        Resolve a BHAV call to its target behavior.
        
        Args:
            caller_file: File making the call
            target_bhav_id: Target BHAV ID
            call_type: "private" (same file), "global", or "semi-global"
        
        Returns:
            Target BehaviorInfo or None
        """
        if call_type == "private":
            return self.lookup(caller_file, target_bhav_id)
        elif call_type == "global":
            return self.lookup_global(target_bhav_id)
        elif call_type == "semi-global":
            # Would need semi-global library info from caller
            # For now, try global first
            return self.lookup_global(target_bhav_id)
        return None


# Convenience function
def get_behavior_library() -> BehaviorLibrary:
    """Get the singleton BehaviorLibrary instance."""
    return BehaviorLibrary()


# ═══════════════════════════════════════════════════════════════════════════
# OPCODE HELPERS (for behavior analysis)
# ═══════════════════════════════════════════════════════════════════════════

def get_opcode_display_name(opcode: int) -> str:
    """Get display name for an opcode."""
    info = get_opcode_info(opcode)
    return info.get("name", f"Unknown_0x{opcode:02X}")


def get_opcode_category(opcode: int) -> str:
    """Get category for an opcode."""
    info = get_opcode_info(opcode)
    return info.get("category", "Unknown")


def analyze_bhav_opcodes(instructions: list) -> Dict[str, Any]:
    """
    Analyze opcode usage in a BHAV's instructions.
    
    Returns:
        {
            "total_instructions": int,
            "opcode_distribution": {opcode: count},
            "categories_used": {category: count},
            "unknown_opcodes": [opcodes],
            "has_calls": bool,
            "has_loops": bool (detected by backwards jumps)
        }
    """
    result = {
        "total_instructions": len(instructions),
        "opcode_distribution": {},
        "categories_used": {},
        "unknown_opcodes": [],
        "has_calls": False,
        "has_loops": False
    }
    
    for i, inst in enumerate(instructions):
        if not hasattr(inst, 'opcode'):
            continue
        
        opcode = inst.opcode
        result["opcode_distribution"][opcode] = result["opcode_distribution"].get(opcode, 0) + 1
        
        if not is_known_opcode(opcode):
            if opcode not in result["unknown_opcodes"]:
                result["unknown_opcodes"].append(opcode)
        else:
            category = get_opcode_category(opcode)
            result["categories_used"][category] = result["categories_used"].get(category, 0) + 1
        
        # Detect calls (opcode 2 with certain operands, or 0x0100+ ranges)
        if opcode == 2 or opcode >= 0x0100:
            result["has_calls"] = True
        
        # Detect potential loops (backwards jumps)
        if hasattr(inst, 'true_target') and inst.true_target < i:
            result["has_loops"] = True
        if hasattr(inst, 'false_target') and inst.false_target < i:
            result["has_loops"] = True
    
    return result
