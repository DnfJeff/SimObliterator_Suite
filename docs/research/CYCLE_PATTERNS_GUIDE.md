"""
Cycle Detection Visual Guide
Shows real-world cycle patterns in The Sims 1
"""

# CYCLE_PATTERNS = r"""

                    THE SIMS 1: CYCLE PATTERNS GUIDE

================================================================================

⚠️ CRITICAL: Cycles are NOT bugs - they are valid SimAntics patterns.
This tooling detects and classifies cycles for analysis, not validation.

# PATTERN 1: Self-Referential BHAV (Recursive Subroutine)

    ┌─────────────┐
    │  BHAV#1234  │───┐
    │   (Helper)  │   │
    └─────────────┘   │
          ↑           │
          └───────────┘

    • Most common cycle pattern
    • Used for loops, iterations, recursive helpers
    • Edge kind: behavioral
    • Example: "Process Each Sim in Room" (recursive iteration)

    Detection:
      CycleType.SELF_REFERENTIAL
      Size: 1 node

    Action: None required (normal pattern)

# PATTERN 2: Mutual BHAV Recursion (State Machine)

    ┌─────────────┐          ┌─────────────┐
    │  BHAV#4000  │──────────>│  BHAV#4001  │
    │   (StateA)  │          │   (StateB)  │
    └─────────────┘          └─────────────┘
          ↑                        │
          └────────────────────────┘

    • Common in state machines, alternating logic
    • Edge kind: behavioral
    • Example: "Toggle State" → "Check Condition" → "Toggle State"

    Detection:
      CycleType.MUTUAL
      Size: 2 nodes

    Action: None required (normal pattern)

# PATTERN 3: Interaction Loop (TTAB ↔ BHAV Callback)

    ┌──────────┐         ┌──────────┐         ┌──────────┐
    │ TTAB#500 │─────────>│ BHAV#1500│─────────>│ TTAB#501 │
    │  (Main)  │         │ (Handler)│         │(Callback)│
    └──────────┘         └──────────┘         └──────────┘
         ↑                                          │
         └──────────────────────────────────────────┘

    • Interaction callbacks and event loops
    • Edge kind: behavioral
    • Example: "Sit" → "Wait for Stand" → "Trigger Stand" → "Sit"

    Detection:
      CycleType.COMPLEX
      Size: 3 nodes
      Types: TTAB/BHAV/TTAB

    Action: None required (normal pattern)

# PATTERN 4: Complex Behavioral Cycle (Call Chain)

    ┌──────────┐     ┌──────────┐
    │ BHAV#2000│────>│ BHAV#2001│
    │  (Init)  │     │ (Helper) │
    └──────────┘     └──────────┘
         ↑                │
         │                ↓
    ┌──────────┐     ┌──────────┐
    │ BHAV#2003│<────│ BHAV#2002│
    │ (Update) │     │(Process) │
    └──────────┘     └──────────┘

    • Update loops, event processing
    • Edge kind: behavioral
    • Example: Init → Helper → Process → Update → Init

    Detection:
      CycleType.COMPLEX
      Size: 4+ nodes
      Types: BHAV/BHAV/BHAV/BHAV

    Action: Normal pattern, but verify intentional

# PATTERN 5: Visual Cycle (UNUSUAL - Investigate)

    ┌──────────┐          ┌──────────┐
    │ DGRP#100 │─────────>│ SPR2#200 │
    │ (DrawGrp)│          │ (Sprite) │
    └──────────┘          └──────────┘
         ↑                     │
         └─────────────────────┘

    • Visual pipeline should be acyclic (tree structure)
    • Edge kind: visual
    • Example: Draw Group → Sprite → Draw Group (circular ref)

    Detection:
      CycleType.MUTUAL
      Size: 2 nodes
      Types: DGRP/SPR2

    Action: ⚠️  INVESTIGATE - likely data corruption or error

# PATTERN 6: Structural Cycle (VERY RARE)

    ┌──────────┐          ┌──────────┐
    │ OBJD#123 │─────────>│ SLOT#456 │
    │ (Object) │          │(Routing) │
    └──────────┘          └──────────┘
         ↑                     │
         └─────────────────────┘

    • Structural references should be acyclic (placement data)
    • Edge kind: structural
    • Example: Object → SLOT → Object (impossible in real data)

    Detection:
      CycleType.MUTUAL
      Size: 2 nodes
      Types: OBJD/SLOT

    Action: ⚠️  CRITICAL - definitely an error, investigate immediately

================================================================================
ANALYSIS QUERIES
================================================================================

Query 1: Show All Behavioral Cycles (Code Flow)
───────────────────────────────────────────────
detector = graph.detect_cycles()
behavioral = detector.get_behavioral_cycles()

    for cycle in behavioral:
        print(f"  {cycle.description}")
        print(f"  Size: {cycle.size} nodes")

Query 2: Find Self-Referential BHAVs (Common Pattern)
──────────────────────────────────────────────────────
self_ref = detector.get_self_referential_bhavs()

    print(f"Found {len(self_ref)} recursive BHAVs:")
    for cycle in self_ref:
        bhav = cycle.nodes[0]
        print(f"  • {bhav}")

Query 3: Flag Unusual Cycles (Investigate)
───────────────────────────────────────────
all_cycles = detector.cycles

    unusual = [c for c in all_cycles
               if c.edge_kinds - {"behavioral"}]  # Non-behavioral

    if unusual:
        print("⚠️  Unusual cycles detected:")
        for cycle in unusual:
            print(f"  {cycle}")
            print(f"    Edge kinds: {cycle.edge_kinds}")

Query 4: Cycles Containing Specific Node
─────────────────────────────────────────
bhav_tgi = TGI("BHAV", 0x00000001, 1234)
cycles = detector.get_cycles_containing(bhav_tgi)

    if cycles:
        print(f"BHAV#1234 is in {len(cycles)} cycle(s):")
        for cycle in cycles:
            print(f"  • {cycle.description}")

================================================================================
SAFE EDITING WITH CYCLE AWARENESS
================================================================================

Before Editing a Node:
──────────────────────

1. Check if node is in any cycles
2. Show cycle context to user
3. Warn about potential impact

   node_tgi = TGI("BHAV", 0x00000001, target_id)
   cycles = detector.get_cycles_containing(node_tgi)

   if cycles:
   print("⚠️ This BHAV is in recursive code:")
   for cycle in cycles:
   print(f" • {cycle.description}")
   print("\nEditing may affect recursive behavior.")
   if confirm("Continue anyway?"): # proceed with edit
   else: # safe to edit (no cycles)

Infinite Loop Detection:
─────────────────────────
Potential infinite loop = cycle with no exit condition

Check for cycles that:
• Are pure behavioral (code execution)
• Have no conditional branches out
• Involve only HARD references (no SOFT fallbacks)

    risky_cycles = [
        c for c in detector.get_pure_behavioral_cycles()
        if all(ref.kind == ReferenceKind.HARD
               for ref in c.edges)
    ]

    if risky_cycles:
        print("⚠️  Potential infinite loops detected:")
        for cycle in risky_cycles:
            print(f"  {cycle}")

================================================================================
REAL-WORLD STATISTICS
================================================================================

Expected Cycle Distribution (typical TS1 object):
──────────────────────────────────────────────────
Self-Referential BHAVs: 5-15 (common, normal)
Mutual BHAV Recursion: 2-8 (common, normal)
Complex BHAV Cycles: 1-3 (uncommon, normal)
Interaction Loops: 0-2 (rare, normal)
Visual Cycles: 0 (should not occur)
Structural Cycles: 0 (should not occur)

If you see:
• 20+ self-ref BHAVs: Normal for complex objects
• Visual cycles: Investigate (likely corruption)
• Structural cycles: Critical error (impossible pattern)

================================================================================
KEY TAKEAWAYS
================================================================================

✓ Cycles are VALID patterns in The Sims 1 SimAntics
✓ Most common: Self-referential BHAVs (recursive helpers)
✓ Also common: Mutual recursion, interaction loops
✓ Unusual: Visual/structural cycles (investigate)

✓ Cycle detection enables:
• Infinite loop detection
• Safe live-edit warnings
• Impact analysis ("why does this explode?")
• Pattern understanding (common vs. unusual)

✓ Philosophy: Detect and classify, never block
✓ Integration: One-line usage via graph.detect_cycles()
✓ Performance: O(V+E) using Tarjan's algorithm

================================================================================
"""

if **name** == "**main**":
print(CYCLE_PATTERNS)
