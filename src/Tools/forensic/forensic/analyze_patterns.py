#!/usr/bin/env python3
"""Analyze patterns in missing global IDs"""

import json
from pathlib import Path
from engine_toolkit import create_toolkit

# Load scan data
scan_path = Path(r"S:\Repositorys_New\SimObliterator_Private_Versions\Iff_Study\RELEASE\SimObliterator_Archiver\data\ULTIMATE_SCAN.json")
with open(scan_path, 'r') as f:
    data = json.load(f)

missing = data.get('missing_globals', {})

print("=" * 70)
print("LOW BYTE PATTERN ANALYSIS")
print("Looking for common function offsets within each expansion block...")
print("=" * 70)
print()

# Analyze low byte patterns
low_byte_counts = {}
for id_str, callers in missing.items():
    gid = int(id_str)
    low_byte = gid & 0xFF
    if low_byte not in low_byte_counts:
        low_byte_counts[low_byte] = {'count': 0, 'callers': 0, 'ids': []}
    low_byte_counts[low_byte]['count'] += 1
    low_byte_counts[low_byte]['callers'] += callers
    low_byte_counts[low_byte]['ids'].append(gid)

# Sort by most callers
sorted_patterns = sorted(low_byte_counts.items(), key=lambda x: -x[1]['callers'])

print("Top 15 Function Offsets by Usage:")
print("-" * 70)
print(f"{'Offset':<8} {'Count':<8} {'Callers':<10} Expansions")
print("-" * 70)

block_map = {
    2: 'LL', 3: 'HP', 4: 'HD', 5: 'DT', 6: 'VAC', 
    7: 'UNL', 8: 'SS', 9: 'MM', 10: '?10', 11: '?11',
    12: '?12', 13: '?13', 14: '?14', 15: '?15'
}

for offset, info in sorted_patterns[:15]:
    blocks = set((gid >> 8) for gid in info['ids'])
    bnames = [block_map.get(b, f'?{b}') for b in sorted(blocks)]
    print(f"0x{offset:02X}     {info['count']:<8} {info['callers']:<10} {bnames}")

print()
print("=" * 70)
print("PATTERN DISCOVERY: 0x19 OFFSET")
print("=" * 70)
print()

# 0x19 appears in almost every expansion - likely the same function type
ids_0x19 = low_byte_counts.get(0x19, {}).get('ids', [])
print(f"IDs ending in 0x19: {sorted(ids_0x19)}")
print()

# What might 0x19 be? Let's check if there's a base game global at 256+0x19 = 281
print("Base game equivalent (256 + 0x19 = 281):")
found = data.get('found_behaviors', {})
for bhav_id, info in found.items():
    if info.get('id') == 281:
        print(f"  ID 281 = {info.get('name', 'unknown')}")
        break

print()
print("=" * 70)
print("HYPOTHESIS: Each expansion block (256 IDs) mirrors base game structure")
print("=" * 70)
print()

# Test: Do missing IDs follow the base game pattern?
# Let's see if base game has behaviors at offsets 0x08, 0x0A, 0x01, 0x12, etc.
test_offsets = [0x00, 0x01, 0x08, 0x09, 0x0A, 0x12, 0x13, 0x19]
print("Base game globals at key offsets:")
for off in test_offsets:
    base_id = 256 + off
    for bhav_id, info in found.items():
        if info.get('id') == base_id:
            print(f"  256 + 0x{off:02X} = {base_id} = {info.get('name', 'unknown')}")
            break

print()
print("=" * 70)
print("CROSS-EXPANSION FUNCTION TABLE")
print("=" * 70)
print()

# Build a table showing each expansion's equivalent function
key_offsets = [0x00, 0x01, 0x08, 0x09, 0x0A, 0x19]
exp_names = ['Base', 'LL', 'HP', 'HD', 'DT', 'VAC', 'UNL', 'SS', 'MM']
exp_bases = [256, 512, 768, 1024, 1280, 1536, 1792, 2048, 2304]

print(f"{'Offset':<8}", end='')
for name in exp_names:
    print(f"{name:<8}", end='')
print()
print("-" * 80)

for off in key_offsets:
    print(f"0x{off:02X}     ", end='')
    for base in exp_bases:
        gid = base + off
        # Check if found or missing
        found_here = False
        for bhav_id, info in found.items():
            if info.get('id') == gid:
                found_here = True
                break
        if found_here:
            print(f"FOUND   ", end='')
        elif str(gid) in missing:
            callers = missing[str(gid)]
            print(f"M({callers:3})  ", end='')
        else:
            print(f"-       ", end='')
    print()

from engine_toolkit import create_toolkit

tk = create_toolkit()

# Semantic labeling: "1800" → "SS::test_user_interrupt"
tk.label_global(1800)

# Expansion diffing: Same logic? Different backend!
tk.are_semantically_equivalent([264], [1800])  # True!

# Zombie hooks at stable offsets
tk.register_hook(0x19, my_handler)  # Works on ALL expansions

# Save edit safety check
safe, warnings = tk.is_safe_to_edit([256, 1800])

# FreeSO gaps enumeration
gaps = tk.get_parity_gaps()  # 200 actionable items
