"""
Opcode Database Loader

Loads opcode definitions from external JSON (data/opcodes_db.json).
Falls back to embedded minimal set if JSON unavailable.

Usage:
    from core.opcode_loader import get_opcode_info, get_all_opcodes, PRIMITIVE_INSTRUCTIONS
"""

import json
from pathlib import Path
from typing import Dict, Optional

# Path to JSON database
_DATA_DIR = Path(__file__).parent.parent / "data"
_OPCODES_JSON = _DATA_DIR / "opcodes_db.json"

# Cache loaded data
_opcodes_cache: Optional[Dict] = None
_categories_cache: Optional[Dict] = None


def _load_opcodes_db() -> Dict:
    """Load opcodes from JSON file, with caching."""
    global _opcodes_cache, _categories_cache
    
    if _opcodes_cache is not None:
        return _opcodes_cache
    
    try:
        if _OPCODES_JSON.exists():
            with open(_OPCODES_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert string keys back to integers for primitives
            primitives = {}
            for key, value in data.get("primitives", {}).items():
                primitives[int(key)] = value
            
            _opcodes_cache = primitives
            _categories_cache = data.get("categories", {})
            
            return _opcodes_cache
    except Exception as e:
        print(f"Warning: Could not load opcodes_db.json: {e}")
    
    # Fallback to minimal embedded set
    _opcodes_cache = _FALLBACK_OPCODES
    _categories_cache = {}
    return _opcodes_cache


# Minimal fallback if JSON fails to load
_FALLBACK_OPCODES = {
    0: {"name": "Sleep", "category": "Control", "description": "Pause execution"},
    1: {"name": "GenericTSOCall", "category": "Control", "description": "Call primitive"},
    2: {"name": "Expression", "category": "Math/Control", "description": "Evaluate expression"},
}


def get_opcode_info(opcode: int) -> Dict:
    """
    Get semantics for an opcode.
    
    Args:
        opcode: Instruction opcode (0-255 for primitives)
    
    Returns:
        Dictionary with name, category, description, etc.
    """
    opcodes = _load_opcodes_db()
    
    if opcode in opcodes:
        return opcodes[opcode]
    
    # Return unknown info with hex value
    return {
        "name": f"Unknown_0x{opcode:02X}",
        "category": "Unknown",
        "description": f"Undocumented opcode 0x{opcode:02X}",
        "stack_effect": "",
        "operand": "",
        "exit_code": "",
        "is_unknown": True
    }


def get_all_opcodes() -> Dict[int, Dict]:
    """Get all loaded opcodes."""
    return _load_opcodes_db().copy()


def get_category_opcodes(category: str) -> list:
    """Get all opcodes in a category."""
    global _categories_cache
    _load_opcodes_db()  # Ensure loaded
    return _categories_cache.get(category, [])


def get_all_categories() -> Dict[str, list]:
    """Get all opcode categories."""
    global _categories_cache
    _load_opcodes_db()  # Ensure loaded
    return _categories_cache.copy() if _categories_cache else {}


def is_known_opcode(opcode: int) -> bool:
    """Check if opcode is in our database."""
    opcodes = _load_opcodes_db()
    return opcode in opcodes


def reload_database():
    """Force reload from JSON (after external updates)."""
    global _opcodes_cache, _categories_cache
    _opcodes_cache = None
    _categories_cache = None
    _load_opcodes_db()


# Compatibility: Expose as PRIMITIVE_INSTRUCTIONS for existing code
def _get_primitive_instructions():
    """Lazy load for backwards compatibility."""
    return _load_opcodes_db()

# This creates a dict-like object that loads on first access
class _LazyDict(dict):
    def __init__(self, loader):
        self._loader = loader
        self._loaded = False
    
    def _ensure_loaded(self):
        if not self._loaded:
            super().update(self._loader())
            self._loaded = True
    
    def __getitem__(self, key):
        self._ensure_loaded()
        return super().__getitem__(key)
    
    def __contains__(self, key):
        self._ensure_loaded()
        return super().__contains__(key)
    
    def get(self, key, default=None):
        self._ensure_loaded()
        return super().get(key, default)
    
    def keys(self):
        self._ensure_loaded()
        return super().keys()
    
    def values(self):
        self._ensure_loaded()
        return super().values()
    
    def items(self):
        self._ensure_loaded()
        return super().items()


PRIMITIVE_INSTRUCTIONS = _LazyDict(_get_primitive_instructions)
