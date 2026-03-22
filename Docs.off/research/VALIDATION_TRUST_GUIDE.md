"""
Scope Validation Visual Guide
Real-world validation examples that build trust
"""

# VALIDATION_GUIDE = r"""

                   SCOPE VALIDATION: BUILDING TRUST

================================================================================

"These are the warnings that make modders say:
'Oh wow, this tool actually understands Sims 1.'"

# VALIDATION 1: BHAV Calls Semi-Global Without GLOB

The Problem:
────────────
chair.iff Functions.iff
┌─────────────┐ ┌─────────────┐
│ BHAV#4096 │───────────────>│ BHAV#8192 │
│ (Init) │ calls semi- │ (Helper) │
└─────────────┘ global! └─────────────┘
│
│
✗ No GLOB chunk!

Detected Issue:
⚠️ [WARNING] BHAV BHAV#4096 calls semi-global BHAV#8192
but object has no GLOB chunk

    Suggestion: Add GLOB chunk to import semi-global library

Why This Matters:
• Object tries to call shared library functions
• No import link established (missing GLOB)
• Game may crash or use wrong function
• Hard to spot without static analysis

Modder Reaction:
"Oh wow, I didn't realize I was calling Functions.iff code
without linking to it. That explains the crashes!"

# VALIDATION 2: Tuning Reference to Non-Existent BCON

The Problem:
────────────
chair.iff
┌─────────────┐ ┌─────────────┐
│ BHAV#4097 │──Expression──>│ BCON#4096 │
│ (Tuned) │ uses BCON │ (MISSING!) │
└─────────────┘ └─────────────┘
👻 Phantom Node

Detected Issue:
❌ [ERROR] BHAV#4097 references non-existent tuning constant BCON#4096

    Suggestion: Add missing BCON table or fix expression operand

Why This Matters:
• BHAV bytecode reads constant from missing table
• **WILL CRASH GAME** when expression evaluates
• Game shows no error message (just crash)
• Hours of debugging without static analysis

Modder Reaction:
"This would have taken hours to debug! The game just crashes
with no error message. Thank you!"

# VALIDATION 3: TTAB Points to Orphaned BHAV

The Problem:
────────────
chair.iff
┌──────────┐ ┌──────────┐
│ TTAB#500 │────────>│ BHAV#4098│
│ (Sit) │ action │ (Handler)│
└──────────┘ └──────────┘
│
✗ No other references!

Detected Issue:
ℹ️ [INFO] TTAB TTAB#500 references orphaned BHAV BHAV#4098

    Suggestion: Verify BHAV is correct interaction handler

Why This Matters:
• Interaction exists but handler has no other callers
• Could be intentional (dedicated handler) - COMMON
• Could be accidental (copied wrong BHAV ID)
• Worth investigating

Modder Reaction:
"Wait, that BHAV isn't used anywhere else? I think I
copied the wrong function ID from another object!"

# VALIDATION 4: Orphaned DGRP (Invisible Graphics)

The Problem:
────────────
chair.iff
┌──────────┐ ┌──────────┐
│ OBJD#100 │ ✗ │ DGRP#200 │
│ (Chair) │ no ref │(Graphics)│
└──────────┘ └──────────┘
│ │
│ │
│ SPR, PALT, etc.
│ (all defined)
│
✗ OBJD.base_graphic_id = 0 or wrong ID

Detected Issue:
⚠️ [WARNING] Orphaned DGRP DGRP#200:
DGRP (draw group) is never referenced - invisible graphics

    Suggestion: Either add reference from OBJD or remove unused resource

Why This Matters:
• Graphics data exists (sprites, palettes, draw groups)
• OBJD doesn't point to it
• **Object is INVISIBLE in-game**
• Wastes file space (dead graphics data)

Modder Reaction:
"Oh! I forgot to update the OBJD.base_graphic_id field.
That's why the chair was invisible! I thought my SPR was broken!"

# VALIDATION 5: Orphaned TTAB (Dead Interactions)

The Problem:
────────────
chair.iff
┌──────────┐ ┌──────────┐
│ OBJD#100 │ ✗ │ TTAB#501 │
│ (Chair) │ no ref │(Stand Up)│
└──────────┘ └──────────┘
│ │
│ ├─> BHAV (action)
OBJD.tree_table_id ├─> BHAV (guard)
points to TTAB#500 └─> TTAs (text)
(not TTAB#501!)

Detected Issue:
⚠️ [WARNING] Orphaned TTAB TTAB#501:
TTAB (interaction table) is never referenced - dead interactions

    Suggestion: Either add reference from OBJD or remove unused resource

Why This Matters:
• Pie menu interactions fully defined
• Never accessible (OBJD points to different TTAB)
• Modder wasted time creating unused content
• Confusing for players ("where's the Stand Up option?")

Modder Reaction:
"I spent an hour setting up those interactions and they're
not even hooked up?! No wonder I couldn't see them in-game!"

# VALIDATION 6: Missing BHAV Reference (Broken Call)

The Problem:
────────────
chair.iff
┌──────────┐ ┌──────────┐
│ BHAV#4099│──Subroutine──>│ BHAV#4100│
│ (Caller) │ call! │ (MISSING)│
└──────────┘ └──────────┘
👻 Phantom Node

Detected Issue:
❌ [ERROR] BHAV#4099 references missing BHAV BHAV#4100

    Suggestion: Add missing BHAV chunk or fix reference to point
                to existing resource

Why This Matters:
• BHAV tries to call subroutine that doesn't exist
• **WILL CRASH GAME** when instruction executes
• Opcode 256+ with non-existent BHAV ID
• Common when copying code between objects

Modder Reaction:
"I copied this BHAV from another object and forgot to copy
the helper function it calls. That's why it crashed!"

================================================================================
VALIDATION WORKFLOW
================================================================================

Step 1: Load Object
───────────────────
graph = load_iff_to_graph("Chair.iff")

Step 2: Run Validation
───────────────────────
validator = graph.validate_scope()
validator.print_summary()

Output:
================================================================================
SCOPE VALIDATION REPORT
================================================================================

    Total Issues: 5
      Errors:      2 (will crash)
      Warnings:    3 (likely bugs)

    ❌ 2 critical error(s) - will likely cause crashes
    ⚠️  3 warning(s) - likely bugs or dead code

Step 3: Fix Critical Errors First
──────────────────────────────────
errors = validator.get_issues_by_severity(ValidationSeverity.ERROR)

    for issue in errors:
        print(f"❌ {issue.message}")
        print(f"   Fix: {issue.suggestion}")
        print()

Output:
❌ BHAV#4097 references non-existent tuning constant BCON#4096
Fix: Add missing BCON table or fix expression operand

    ❌ BHAV#4099 references missing BHAV BHAV#4100
       Fix: Add missing BHAV chunk or fix reference

Step 4: Address Warnings
─────────────────────────
warnings = validator.get_issues_by_severity(ValidationSeverity.WARNING)

    for issue in warnings:
        print(f"⚠️  {issue.message}")
        print(f"   Fix: {issue.suggestion}")
        print()

Step 5: Review Info/Suggestions
────────────────────────────────
(Best practices, suspicious patterns)

================================================================================
TRUST INDICATORS (What Modders See)
================================================================================

✓ No Critical Errors:
"✓ No critical errors - file is structurally sound"
→ Modder trusts file will load in-game

❌ Critical Errors Found:
"❌ 2 critical error(s) - will likely cause crashes"
→ Modder knows EXACTLY what will crash and why

✓ No Warnings:
"✓ No warnings - scope rules followed correctly"
→ Modder trusts object follows best practices

⚠️ Warnings Found:
"⚠️ 3 warning(s) - likely bugs or dead code"
→ Modder knows what to investigate

The Difference:
WITHOUT validation: "Why does my object crash/disappear/break?"
WITH validation: "Oh, that's why! Let me fix that."

================================================================================
BEFORE vs. AFTER
================================================================================

BEFORE Scope Validation:
────────────────────────
Modder: _Spends 3 hours debugging invisible chair_

Forum Post:
"Help! My chair is invisible in-game. I have the SPR2 files,
the DGRP is set up, the palettes are correct. What am I doing wrong?"

Community Response:
"Did you check the OBJD.base_graphic_id field?"

Modder:
"Oh... no. Let me try that. (30 minutes later) IT WORKS!
Thanks! I wasted 3 hours on that."

AFTER Scope Validation:
───────────────────────
Modder: _Runs scope validation before testing_

Tool Output:
⚠️ [WARNING] Orphaned DGRP DGRP#200:
DGRP (draw group) is never referenced - invisible graphics

    Suggestion: Either add reference from OBJD or remove unused resource

Modder:
"Oh! I forgot to set base_graphic_id. Let me fix that."

    (Fixes it, re-validates)

    ✓ No validation issues found

Modder:
"Perfect! Now I can test it."

Time Saved: 2 hours 50 minutes
Trust Built: "This tool actually understands Sims 1!"

================================================================================
THE TRUST-BUILDING MOMENT
================================================================================

When a modder runs scope validation for the first time and sees:

    ❌ [ERROR] BHAV#4097 references non-existent tuning constant BCON#4096
       Suggestion: Add missing BCON table or fix expression operand

    ⚠️  [WARNING] BHAV BHAV#4096 calls semi-global BHAV#8192
        but object has no GLOB chunk
       Suggestion: Add GLOB chunk to import semi-global library

    ⚠️  [WARNING] Orphaned DGRP DGRP#200: invisible graphics
       Suggestion: Add reference from OBJD.base_graphic_id

They think:

    "Wait... this tool just found THREE issues I didn't know about.

     The first one would have crashed the game.
     The second one explains why Functions weren't working.
     The third one is why my object was invisible.

     And it told me EXACTLY how to fix each one.

     This tool actually understands Sims 1.

     I'm using this for every object I make from now on."

That's the moment. That's when trust is built.

================================================================================
"""

if **name** == "**main**":
print(VALIDATION_GUIDE)
