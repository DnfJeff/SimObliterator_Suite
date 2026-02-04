"""Analyze primitive opcode usage from scan data"""
import json

with open(r'S:\Repositorys_New\SimObliterator_Private_Versions\Iff_Study\RELEASE\SimObliterator_Archiver\data\ULTIMATE_SCAN.json', 'r') as f:
    data = json.load(f)

ops = data.get('opcode_usage', {})

print('PRIMITIVE OPCODES (0-255) USAGE')
print('='*60)

# Parse keys - might be hex strings
primitives = {}
for k, v in ops.items():
    try:
        if k.startswith('0x'):
            opcode = int(k, 16)
        else:
            opcode = int(k)
        
        if opcode < 256:
            primitives[opcode] = v
    except ValueError:
        pass

# Sort by usage
sorted_prims = sorted(primitives.items(), key=lambda x: -x[1])[:30]

for opcode, count in sorted_prims:
    print(f'  Opcode {opcode:3d} (0x{opcode:02X}): {count:,} uses')

print()
print(f'Total unique primitives used: {len(primitives)}')
print(f'Total primitive instructions: {sum(primitives.values()):,}')
