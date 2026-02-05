"""
FreeSO Parity Gap Analyzer - Enumerate and prioritize missing engine functions

This tool identifies exactly which engine-internal globals FreeSO would need
to implement to achieve full compatibility with The Sims 1 expansion packs.

Key insight: FreeSO returns ERROR on missing globals. We know exactly which
globals are missing (our ghost globals research) and can prioritize by usage.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

# Import our semantic tools
from semantic_globals import (
    SemanticGlobalResolver,
    ExpansionBlock,
    EXPANSION_NAMES,
    CORE_FUNCTION_OFFSETS,
    FreeSoParityChecker
)


class ImplementationPriority(Enum):
    """Priority levels for FreeSO implementation"""
    CRITICAL = 1     # >500 callers, core game functions
    HIGH = 2         # >100 callers, important features
    MEDIUM = 3       # >20 callers, expansion features
    LOW = 4          # <20 callers, rarely used
    UNKNOWN = 5      # No usage data


class ImplementationComplexity(Enum):
    """Estimated complexity for implementing a function"""
    TRIVIAL = 1      # Redirect to base game version
    SIMPLE = 2       # Minor parameter changes
    MODERATE = 3     # Some expansion-specific logic
    COMPLEX = 4      # Significant new code
    UNKNOWN = 5      # Needs research


@dataclass
class ParityGap:
    """A single gap between original game and FreeSO"""
    global_id: int
    function_name: str
    expansion: ExpansionBlock
    offset: int
    caller_count: int
    priority: ImplementationPriority
    complexity: ImplementationComplexity
    base_equivalent: int  # The base game version (if exists)
    suggested_impl: str = ""
    notes: List[str] = field(default_factory=list)


class FreeSoGapAnalyzer:
    """
    Comprehensive analysis of FreeSO compatibility gaps.
    
    Uses ghost globals research + usage data to generate
    actionable implementation priorities.
    """
    
    def __init__(self, scan_data_path: Optional[Path] = None):
        self.resolver = SemanticGlobalResolver()
        self.missing_globals: Dict[int, int] = {}  # id -> caller_count
        self.caller_details: Dict[int, List[str]] = {}  # id -> [caller_names]
        
        if scan_data_path and scan_data_path.exists():
            self._load_scan_data(scan_data_path)
    
    def _load_scan_data(self, path: Path):
        """Load data from ULTIMATE_SCAN.json"""
        with open(path) as f:
            data = json.load(f)
        
        # Load missing globals with counts
        for gid_str, count in data.get('missing_globals', {}).items():
            self.missing_globals[int(gid_str)] = count
        
        # Build caller details from behaviors
        behaviors = data.get('behaviors', {})
        for bhav_id, bhav_data in behaviors.items():
            name = bhav_data.get('name', f'bhav_{bhav_id}')
            for gid in bhav_data.get('calls_globals', []):
                if gid not in self.caller_details:
                    self.caller_details[gid] = []
                self.caller_details[gid].append(name)
    
    def _calculate_priority(self, caller_count: int) -> ImplementationPriority:
        """Determine implementation priority based on usage"""
        if caller_count >= 500:
            return ImplementationPriority.CRITICAL
        elif caller_count >= 100:
            return ImplementationPriority.HIGH
        elif caller_count >= 20:
            return ImplementationPriority.MEDIUM
        elif caller_count > 0:
            return ImplementationPriority.LOW
        return ImplementationPriority.UNKNOWN
    
    def _estimate_complexity(self, offset: int, expansion: ExpansionBlock) -> ImplementationComplexity:
        """Estimate implementation complexity"""
        # Core functions can likely redirect to base
        if offset in CORE_FUNCTION_OFFSETS:
            if expansion.value == 0:
                return ImplementationComplexity.TRIVIAL
            else:
                # Expansion version - may need minor tweaks
                return ImplementationComplexity.SIMPLE
        
        # Unknown functions need more research
        return ImplementationComplexity.UNKNOWN
    
    def _suggest_implementation(self, gap: ParityGap) -> str:
        """Generate implementation suggestion"""
        if gap.complexity == ImplementationComplexity.TRIVIAL:
            return f"// Direct redirect to base implementation"
        
        if gap.complexity == ImplementationComplexity.SIMPLE:
            return f"// Redirect to Global {gap.base_equivalent} ({gap.function_name})"
        
        return f"// TODO: Research {gap.function_name} for {EXPANSION_NAMES[gap.expansion]}"
    
    def analyze_gap(self, global_id: int) -> ParityGap:
        """Analyze a single parity gap"""
        info = self.resolver.resolve(global_id)
        caller_count = self.missing_globals.get(global_id, 0)
        
        base_equiv = 256 + info.offset
        priority = self._calculate_priority(caller_count)
        complexity = self._estimate_complexity(info.offset, info.expansion)
        
        gap = ParityGap(
            global_id=global_id,
            function_name=info.function_name or f"func_0x{info.offset:02X}",
            expansion=info.expansion,
            offset=info.offset,
            caller_count=caller_count,
            priority=priority,
            complexity=complexity,
            base_equivalent=base_equiv,
        )
        
        gap.suggested_impl = self._suggest_implementation(gap)
        
        # Add caller context
        callers = self.caller_details.get(global_id, [])
        if callers:
            unique_callers = list(set(callers))[:5]
            gap.notes.append(f"Called by: {', '.join(unique_callers)}")
        
        return gap
    
    def analyze_all_gaps(self) -> List[ParityGap]:
        """Analyze all parity gaps"""
        gaps = []
        for gid in self.missing_globals.keys():
            gap = self.analyze_gap(gid)
            gaps.append(gap)
        
        # Sort by priority, then caller count
        gaps.sort(key=lambda g: (g.priority.value, -g.caller_count))
        return gaps
    
    def group_by_function(self) -> Dict[str, List[ParityGap]]:
        """Group gaps by function type"""
        gaps = self.analyze_all_gaps()
        groups: Dict[str, List[ParityGap]] = defaultdict(list)
        
        for gap in gaps:
            groups[gap.function_name].append(gap)
        
        return dict(groups)
    
    def generate_implementation_plan(self) -> str:
        """Generate a prioritized implementation plan"""
        gaps = self.analyze_all_gaps()
        groups = self.group_by_function()
        
        lines = [
            "# FreeSO Implementation Plan",
            "",
            "## Summary",
            f"- Total missing globals: {len(gaps)}",
            f"- Unique functions: {len(groups)}",
            f"- Total caller references: {sum(g.caller_count for g in gaps)}",
            "",
            "## Priority Breakdown",
        ]
        
        by_priority = defaultdict(list)
        for gap in gaps:
            by_priority[gap.priority].append(gap)
        
        for priority in ImplementationPriority:
            count = len(by_priority[priority])
            if count > 0:
                total_callers = sum(g.caller_count for g in by_priority[priority])
                lines.append(f"- {priority.name}: {count} globals ({total_callers} callers)")
        
        lines.extend([
            "",
            "## Implementation Phases",
            "",
            "### Phase 1: Critical Functions (500+ callers)",
        ])
        
        for gap in by_priority[ImplementationPriority.CRITICAL]:
            lines.append(f"- [ ] `{gap.function_name}` (0x{gap.global_id:04X}): {gap.caller_count} callers")
            lines.append(f"      {gap.suggested_impl}")
        
        lines.extend([
            "",
            "### Phase 2: High Priority (100+ callers)",
        ])
        
        for gap in by_priority[ImplementationPriority.HIGH][:10]:  # Top 10
            lines.append(f"- [ ] `{gap.function_name}` (0x{gap.global_id:04X}): {gap.caller_count} callers")
        
        if len(by_priority[ImplementationPriority.HIGH]) > 10:
            lines.append(f"  ... and {len(by_priority[ImplementationPriority.HIGH]) - 10} more")
        
        lines.extend([
            "",
            "## Function Groups",
            "",
            "Functions that appear across multiple expansions:",
            "",
        ])
        
        for func_name, func_gaps in sorted(groups.items(), 
                                           key=lambda x: -sum(g.caller_count for g in x[1])):
            total = sum(g.caller_count for g in func_gaps)
            expansions = [EXPANSION_NAMES[g.expansion] for g in func_gaps]
            lines.append(f"### {func_name}")
            lines.append(f"- Expansions: {', '.join(expansions)}")
            lines.append(f"- Total callers: {total}")
            lines.append(f"- Suggested: Implement once, dispatch by expansion")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_csharp_stubs(self) -> str:
        """Generate C# stub code for FreeSO implementation"""
        groups = self.group_by_function()
        
        lines = [
            "// Auto-generated FreeSO parity stubs",
            "// From Ghost Globals Research",
            "",
            "using FSO.SimAntics;",
            "using FSO.SimAntics.Engine;",
            "",
            "namespace FSO.SimAntics.Primitives.TS1",
            "{",
            "    /// <summary>",
            "    /// Handles engine-internal globals that don't exist as BHAV chunks",
            "    /// </summary>",
            "    public static class EngineInternalGlobals",
            "    {",
            "        // Global ID to handler mapping",
            "        private static readonly Dictionary<ushort, Func<VMStackFrame, VMPrimitiveExitCode>> Handlers",
            "            = new Dictionary<ushort, Func<VMStackFrame, VMPrimitiveExitCode>>();",
            "",
            "        static EngineInternalGlobals()",
            "        {",
        ]
        
        # Register handlers
        for func_name, func_gaps in groups.items():
            for gap in func_gaps:
                safe_name = func_name.replace(" ", "_").replace("-", "_")
                lines.append(f"            Handlers[0x{gap.global_id:04X}] = Handle_{safe_name};")
        
        lines.extend([
            "        }",
            "",
            "        /// <summary>",
            "        /// Check if a global ID is engine-internal",
            "        /// </summary>",
            "        public static bool IsEngineInternal(ushort globalId)",
            "        {",
            "            return Handlers.ContainsKey(globalId);",
            "        }",
            "",
            "        /// <summary>",
            "        /// Execute an engine-internal global",
            "        /// </summary>",
            "        public static VMPrimitiveExitCode Execute(VMStackFrame frame, ushort globalId)",
            "        {",
            "            if (Handlers.TryGetValue(globalId, out var handler))",
            "            {",
            "                return handler(frame);",
            "            }",
            "            return VMPrimitiveExitCode.ERROR;",
            "        }",
            "",
        ])
        
        # Generate handler stubs
        seen_funcs = set()
        for func_name, func_gaps in groups.items():
            if func_name in seen_funcs:
                continue
            seen_funcs.add(func_name)
            
            safe_name = func_name.replace(" ", "_").replace("-", "_")
            total_callers = sum(g.caller_count for g in func_gaps)
            
            lines.extend([
                f"        /// <summary>",
                f"        /// {func_name} - {total_callers} callers across expansions",
                f"        /// </summary>",
                f"        private static VMPrimitiveExitCode Handle_{safe_name}(VMStackFrame frame)",
                f"        {{",
                f"            // TODO: Implement {func_name}",
                f"            // Base game equivalent: Global {func_gaps[0].base_equivalent}",
                f"            return VMPrimitiveExitCode.GOTO_TRUE;",
                f"        }}",
                "",
            ])
        
        lines.extend([
            "    }",
            "}",
        ])
        
        return "\n".join(lines)


def main():
    # Try to load from scan data
    scan_path = Path(r"S:\Repositorys_New\SimObliterator_Private_Versions\Iff_Study\RELEASE\SimObliterator_Archiver\data\ULTIMATE_SCAN.json")
    
    analyzer = FreeSoGapAnalyzer(scan_path if scan_path.exists() else None)
    
    # If no scan data, use our known missing globals
    if not analyzer.missing_globals:
        # Add known high-usage gaps from research
        known_gaps = {
            2585: 583,  # EXT2::wait_for_notify
            1800: 449,  # SS::test_user_interrupt
            778: 440,   # HP::set_energy
            1817: 428,  # SS::wait_for_notify
            1793: 375,  # SS::inc_comfort
            1802: 344,  # SS::set_energy
            793: 334,   # HP::wait_for_notify
            1810: 330,  # SS::move_forward
            1801: 325,  # SS::hide_menu
            1811: 263,  # SS::func_0x13
        }
        analyzer.missing_globals = known_gaps
    
    print("=== FreeSO Parity Gap Analysis ===\n")
    
    # Show top gaps
    gaps = analyzer.analyze_all_gaps()
    
    print("Top 10 Priority Gaps:")
    print("-" * 70)
    for gap in gaps[:10]:
        print(f"  0x{gap.global_id:04X}: {gap.function_name:25s} "
              f"[{gap.priority.name:8s}] {gap.caller_count:4d} callers")
        if gap.notes:
            print(f"         {gap.notes[0]}")
    
    print("\n" + "=" * 70)
    print("\nGenerating implementation plan...")
    
    plan = analyzer.generate_implementation_plan()
    
    # Save plan
    output_path = Path(__file__).parent / "FREESO_IMPLEMENTATION_PLAN.md"
    output_path.write_text(plan)
    print(f"Saved to: {output_path}")
    
    # Generate C# stubs
    print("\nGenerating C# stubs...")
    stubs = analyzer.generate_csharp_stubs()
    
    stubs_path = Path(__file__).parent / "freeso_parity_stubs.cs"
    stubs_path.write_text(stubs)
    print(f"Saved to: {stubs_path}")


if __name__ == "__main__":
    main()
