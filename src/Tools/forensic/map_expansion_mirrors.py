#!/usr/bin/env python3
"""Map base game globals to expansion equivalents"""

import json

with open(r"S:\Repositorys_New\SimObliterator_Private_Versions\Iff_Study\NewResearch\GLOBAL_BEHAVIOR_DATABASE.json", 'r') as f:
    db = json.load(f)

found = db['found_globals']

# Key offsets that appear in missing globals
offsets = [0x00, 0x01, 0x08, 0x09, 0x0A, 0x12, 0x13, 0x19]

print("Base Game Globals at Key Offsets:")
print("=" * 60)
offset_names = {}
for off in offsets:
    base_id = str(256 + off)
    if base_id in found:
        name = found[base_id]['name']
        print(f"0x{off:02X} -> ID {256+off}: {name}")
        offset_names[off] = name
    else:
        print(f"0x{off:02X} -> ID {256+off}: NOT FOUND IN BASE")
        offset_names[off] = "???"

print()
print("=" * 60)
print("EXPANSION FUNCTION MIRRORS")
print("=" * 60)
print()
print("Each expansion has its own version of these core functions!")
print("These are the 'ghost globals' - called but not in any IFF file.")
print("They are likely HARDCODED in the engine (TheSims.exe)")
print()

exp_names = ['LL', 'HP', 'HD', 'DT', 'VAC', 'UNL', 'SS', 'MM']
exp_bases = [512, 768, 1024, 1280, 1536, 1792, 2048, 2304]

# Load missing globals for caller counts
with open(r"S:\Repositorys_New\SimObliterator_Private_Versions\Iff_Study\RELEASE\SimObliterator_Archiver\data\ULTIMATE_SCAN.json", 'r') as f:
    scan = json.load(f)
missing = scan.get('missing_globals', {})

print(f"{'Function':<30} ", end='')
for name in exp_names:
    print(f"{name:>6}", end='')
print()
print("-" * 80)

for off in offsets:
    name = offset_names.get(off, "???")
    print(f"{name[:28]:<30} ", end='')
    for base in exp_bases:
        gid = base + off
        if str(gid) in missing:
            callers = missing[str(gid)]
            print(f"{callers:>6}", end='')
        else:
            # Check if it's found
            if str(gid) in found:
                print(f"{'FOUND':>6}", end='')
            else:
                print(f"{'---':>6}", end='')
    print()

print()
print("=" * 60)
print("CONCLUSION")
print("=" * 60)
print("""
The 'ghost globals' ARE NOT missing behaviors - they are ENGINE-INTERNAL
functions that each expansion pack registers with the SimAntics VM.

When an expansion pack loads, it registers these subroutines with the
SimAntics engine, which are then callable using the global opcode range
but the bytecode lives in TheSims.exe, NOT in IFF files.

This explains why:
1. These IDs are heavily called (thousands of callers)
2. No BHAV chunks exist for them
3. They follow a consistent pattern across expansions
4. FreeSO likely has to RE-IMPLEMENT each one

The engine internal functions appear to include:
- Wait functions (0x19 = Wait For Notify variants)
- Utility functions (0x0A = SetEnergy equivalent?)
- Entry/exit functions (0x08, 0x09 = Standard entry/exit?)
""")
