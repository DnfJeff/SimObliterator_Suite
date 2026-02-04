"""
Semantic Global Resolver - Label global calls by function meaning, not raw ID

The key insight: Global IDs are (expansion_block * 256) + function_offset
This means global 1800 = Superstar block + offset 0x08 = "test for user interrupt"

Usage:
    resolver = SemanticGlobalResolver()
    name = resolver.get_semantic_name(1800)  # "Superstar::test_for_user_interrupt"
    offset = resolver.get_stable_offset(1800)  # 0x08
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import IntEnum

class ExpansionBlock(IntEnum):
    """Expansion pack ID blocks - each gets 256 global IDs"""
    BASE_GAME = 0       # 256-511
    LIVIN_LARGE = 1     # 512-767
    HOUSE_PARTY = 2     # 768-1023
    HOT_DATE = 3        # 1024-1279
    VACATION = 4        # 1280-1535
    UNLEASHED = 5       # 1536-1791
    SUPERSTAR = 6       # 1792-2047
    MAKIN_MAGIC = 7     # 2048-2303
    EXTENDED_1 = 8      # 2304-2559
    EXTENDED_2 = 9      # 2560-2815

EXPANSION_NAMES = {
    ExpansionBlock.BASE_GAME: "Base",
    ExpansionBlock.LIVIN_LARGE: "LL",
    ExpansionBlock.HOUSE_PARTY: "HP",
    ExpansionBlock.HOT_DATE: "HD",
    ExpansionBlock.VACATION: "VAC",
    ExpansionBlock.UNLEASHED: "UNL",
    ExpansionBlock.SUPERSTAR: "SS",
    ExpansionBlock.MAKIN_MAGIC: "MM",
    ExpansionBlock.EXTENDED_1: "EXT1",
    ExpansionBlock.EXTENDED_2: "EXT2",
}

# Core function offsets discovered in our research
# These appear at the SAME offset in every expansion block
CORE_FUNCTION_OFFSETS = {
    0x00: "set_graphic",
    0x01: "inc_comfort",
    0x03: "old_idle",
    0x04: "set_object_graphic",
    0x05: "set_comfort",
    0x08: "test_user_interrupt",
    0x09: "hide_menu",
    0x0A: "set_energy",
    0x12: "move_forward_n_tiles",
    0x19: "wait_for_notify",
}

@dataclass
class GlobalInfo:
    """Semantic information about a global ID"""
    raw_id: int
    expansion: ExpansionBlock
    offset: int
    function_name: Optional[str]
    is_engine_internal: bool
    
    @property
    def semantic_name(self) -> str:
        """Get human-readable name like 'Superstar::wait_for_notify'"""
        exp_name = EXPANSION_NAMES.get(self.expansion, f"EXP{self.expansion}")
        func_name = self.function_name or f"func_0x{self.offset:02X}"
        return f"{exp_name}::{func_name}"
    
    @property
    def stable_hook_id(self) -> str:
        """Get stable ID for modding: 'offset_0x19' instead of raw ID"""
        return f"offset_0x{self.offset:02X}"


class SemanticGlobalResolver:
    """
    Resolves raw global IDs to semantic meanings.
    
    Key insight from ghost globals research:
    - Each expansion gets a 256-ID block
    - Same function offsets repeat across blocks
    - Engine implements these internally, not in IFF files
    """
    
    def __init__(self, database_path: Optional[Path] = None):
        self.known_globals: Dict[int, str] = {}
        self.engine_internal: set = set()
        
        if database_path and database_path.exists():
            self._load_database(database_path)
        else:
            self._build_default_database()
    
    def _load_database(self, path: Path):
        """Load from GLOBAL_BEHAVIOR_DATABASE.json"""
        with open(path) as f:
            data = json.load(f)
        
        for gid_str, info in data.get('known_globals', {}).items():
            gid = int(gid_str)
            self.known_globals[gid] = info.get('name', f'global_{gid}')
        
        for gid_str in data.get('missing_globals', {}).keys():
            self.engine_internal.add(int(gid_str))
    
    def _build_default_database(self):
        """Build from core function offsets"""
        # Base game globals (256-511) - these exist in IFF
        for offset, name in CORE_FUNCTION_OFFSETS.items():
            self.known_globals[256 + offset] = name
        
        # Mark expansion-range functions as engine internal
        for exp in range(1, 10):  # Expansions 1-9
            for offset in CORE_FUNCTION_OFFSETS.keys():
                gid = 256 + (exp * 256) + offset
                self.engine_internal.add(gid)
    
    def resolve(self, global_id: int) -> GlobalInfo:
        """Resolve a raw global ID to semantic information"""
        if global_id < 256 or global_id >= 4096:
            raise ValueError(f"Not a global ID: {global_id} (must be 256-4095)")
        
        # Calculate expansion block and offset
        block = (global_id - 256) // 256
        offset = (global_id - 256) % 256
        
        try:
            expansion = ExpansionBlock(block)
        except ValueError:
            expansion = ExpansionBlock.BASE_GAME  # Fallback
        
        # Get function name - check base game first, then offset table
        func_name = None
        base_id = 256 + offset
        
        if global_id in self.known_globals:
            func_name = self.known_globals[global_id]
        elif base_id in self.known_globals:
            func_name = self.known_globals[base_id]
        elif offset in CORE_FUNCTION_OFFSETS:
            func_name = CORE_FUNCTION_OFFSETS[offset]
        
        is_internal = global_id in self.engine_internal or block > 0
        
        return GlobalInfo(
            raw_id=global_id,
            expansion=expansion,
            offset=offset,
            function_name=func_name,
            is_engine_internal=is_internal
        )
    
    def get_semantic_name(self, global_id: int) -> str:
        """Quick lookup for semantic name"""
        return self.resolve(global_id).semantic_name
    
    def get_stable_offset(self, global_id: int) -> int:
        """Get the stable function offset (for cross-expansion compatibility)"""
        return self.resolve(global_id).offset
    
    def find_equivalent_across_expansions(self, global_id: int) -> Dict[ExpansionBlock, int]:
        """Find equivalent function IDs across all expansions"""
        offset = self.get_stable_offset(global_id)
        
        equivalents = {}
        for exp in ExpansionBlock:
            equiv_id = 256 + (exp.value * 256) + offset
            if equiv_id < 4096:  # Stay in global range
                equivalents[exp] = equiv_id
        
        return equivalents
    
    def label_call_graph_node(self, global_id: int, verbose: bool = False) -> str:
        """Generate a label for graph visualization"""
        info = self.resolve(global_id)
        
        if verbose:
            internal = " [ENGINE]" if info.is_engine_internal else ""
            return f"{info.semantic_name} (0x{global_id:04X}){internal}"
        else:
            return info.semantic_name


class ExpansionAwareDiffer:
    """
    Compare behaviors across expansions, normalizing for engine backend differences.
    
    Key insight: Same logic may call different global IDs depending on expansion,
    but if the OFFSET is the same, it's semantically equivalent.
    """
    
    def __init__(self, resolver: Optional[SemanticGlobalResolver] = None):
        self.resolver = resolver or SemanticGlobalResolver()
    
    def normalize_global_calls(self, global_ids: List[int]) -> List[int]:
        """Convert expansion-specific IDs to base game equivalents"""
        normalized = []
        for gid in global_ids:
            if 256 <= gid < 4096:
                offset = self.resolver.get_stable_offset(gid)
                base_equiv = 256 + offset  # Base game version
                normalized.append(base_equiv)
            else:
                normalized.append(gid)  # Keep non-globals as-is
        return normalized
    
    def behaviors_equivalent(self, 
                            calls_a: List[int], 
                            calls_b: List[int]) -> Tuple[bool, List[str]]:
        """
        Check if two behaviors are semantically equivalent despite
        different raw global IDs.
        
        Returns (is_equivalent, list of differences)
        """
        norm_a = self.normalize_global_calls(calls_a)
        norm_b = self.normalize_global_calls(calls_b)
        
        differences = []
        
        if len(norm_a) != len(norm_b):
            differences.append(f"Different call counts: {len(calls_a)} vs {len(calls_b)}")
            return False, differences
        
        for i, (a, b) in enumerate(zip(norm_a, norm_b)):
            if a != b:
                name_a = self.resolver.get_semantic_name(calls_a[i]) if 256 <= calls_a[i] < 4096 else str(calls_a[i])
                name_b = self.resolver.get_semantic_name(calls_b[i]) if 256 <= calls_b[i] < 4096 else str(calls_b[i])
                differences.append(f"Call {i}: {name_a} vs {name_b}")
        
        return len(differences) == 0, differences


class StableHookRegistry:
    """
    Registry for mod hooks that work across expansions.
    
    Instead of hooking global ID 1800 (Superstar-specific),
    hook offset 0x08 (test_user_interrupt) which works everywhere.
    """
    
    def __init__(self, resolver: Optional[SemanticGlobalResolver] = None):
        self.resolver = resolver or SemanticGlobalResolver()
        self.hooks: Dict[int, callable] = {}  # offset -> handler
    
    def register_hook(self, offset: int, handler: callable, name: str = None):
        """Register a hook at a stable offset"""
        self.hooks[offset] = handler
        print(f"Registered hook at offset 0x{offset:02X}" + 
              (f" ({name})" if name else ""))
    
    def should_intercept(self, global_id: int) -> bool:
        """Check if this global call should be intercepted"""
        if not (256 <= global_id < 4096):
            return False
        offset = self.resolver.get_stable_offset(global_id)
        return offset in self.hooks
    
    def get_handler(self, global_id: int) -> Optional[callable]:
        """Get the handler for this global call"""
        if not self.should_intercept(global_id):
            return None
        offset = self.resolver.get_stable_offset(global_id)
        return self.hooks.get(offset)
    
    def intercept(self, global_id: int, *args, **kwargs):
        """Intercept a global call if hooked"""
        handler = self.get_handler(global_id)
        if handler:
            info = self.resolver.resolve(global_id)
            return handler(info, *args, **kwargs)
        return None


class FreeSoParityChecker:
    """
    Identify gaps between original game and FreeSO implementation.
    
    FreeSO returns ERROR on missing globals - we can enumerate exactly
    which engine-internal functions would need reimplementation.
    """
    
    def __init__(self, resolver: Optional[SemanticGlobalResolver] = None):
        self.resolver = resolver or SemanticGlobalResolver()
    
    def get_missing_implementations(self) -> List[GlobalInfo]:
        """Get all engine-internal globals that FreeSO would need to implement"""
        missing = []
        for gid in sorted(self.resolver.engine_internal):
            info = self.resolver.resolve(gid)
            missing.append(info)
        return missing
    
    def group_by_function(self) -> Dict[str, List[GlobalInfo]]:
        """Group missing implementations by function type"""
        groups: Dict[str, List[GlobalInfo]] = {}
        
        for info in self.get_missing_implementations():
            func = info.function_name or f"unknown_0x{info.offset:02X}"
            if func not in groups:
                groups[func] = []
            groups[func].append(info)
        
        return groups
    
    def generate_stub_code(self, language: str = "csharp") -> str:
        """Generate stub implementations for FreeSO"""
        groups = self.group_by_function()
        
        if language == "csharp":
            lines = ["// Auto-generated stubs for engine-internal globals", ""]
            
            for func_name, infos in sorted(groups.items()):
                ids = [f"0x{i.raw_id:04X}" for i in infos]
                lines.append(f"// {func_name}: {', '.join(ids)}")
                lines.append(f"private VMPrimitiveExitCode Handle_{func_name}(VMStackFrame frame)")
                lines.append("{")
                lines.append("    // TODO: Implement engine-internal function")
                lines.append("    return VMPrimitiveExitCode.GOTO_TRUE;")
                lines.append("}")
                lines.append("")
            
            return "\n".join(lines)
        
        return f"// Language '{language}' not supported"
    
    def report(self) -> str:
        """Generate a parity gap report"""
        groups = self.group_by_function()
        
        lines = [
            "FreeSO Parity Gap Report",
            "=" * 60,
            "",
            f"Total engine-internal globals: {len(self.resolver.engine_internal)}",
            f"Unique functions needing implementation: {len(groups)}",
            "",
            "Functions by expansion coverage:",
            "-" * 40,
        ]
        
        for func_name, infos in sorted(groups.items(), key=lambda x: -len(x[1])):
            expansions = [EXPANSION_NAMES[i.expansion] for i in infos]
            lines.append(f"  {func_name}: {', '.join(expansions)}")
        
        return "\n".join(lines)


# Quick test
if __name__ == "__main__":
    resolver = SemanticGlobalResolver()
    
    print("=== Semantic Global Resolution ===\n")
    
    test_ids = [256, 264, 281, 778, 1800, 1817, 2585]
    for gid in test_ids:
        info = resolver.resolve(gid)
        print(f"Global {gid} (0x{gid:04X}):")
        print(f"  Semantic: {info.semantic_name}")
        print(f"  Offset:   0x{info.offset:02X}")
        print(f"  Engine:   {info.is_engine_internal}")
        print()
    
    print("=== Cross-Expansion Equivalents ===\n")
    equivalents = resolver.find_equivalent_across_expansions(264)
    print(f"Equivalents of 264 (test_user_interrupt):")
    for exp, gid in equivalents.items():
        print(f"  {EXPANSION_NAMES[exp]}: {gid} (0x{gid:04X})")
    
    print("\n=== FreeSO Parity Check ===\n")
    checker = FreeSoParityChecker(resolver)
    print(checker.report())
