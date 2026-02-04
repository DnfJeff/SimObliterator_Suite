"""Analyze who calls the missing globals and map function offsets"""
import json

with open(r'S:\Repositorys_New\SimObliterator_Private_Versions\Iff_Study\RELEASE\SimObliterator_Archiver\data\ULTIMATE_SCAN.json', 'r') as f:
    data = json.load(f)

behaviors = data.get('behaviors', {})

# Find known globals in base range (256-511) to map names to offsets
base_globals = {int(k): v for k, v in behaviors.items() if 256 <= int(k) < 512}

# Build offset->name map
offset_to_name = {}
for gid, bdata in base_globals.items():
    offset = gid - 256
    offset_to_name[offset] = bdata.get('name', 'unknown')

# Show the function offset -> name mapping  
print('FUNCTION OFFSET TO NAME MAPPING (from Base Game globals)')
print('='*70)
print('These offsets appear in EVERY expansion range (256, 512, 768, etc.)')
print()

# Focus on the heavy-use offsets we found
key_offsets = [0x00, 0x01, 0x03, 0x04, 0x05, 0x08, 0x09, 0x0A, 0x12, 0x19]

for offset in key_offsets:
    name = offset_to_name.get(offset, '<<MISSING IN BASE>>')
    base_gid = 256 + offset
    print(f'Offset +0x{offset:02X} ({offset:3d}): Global {base_gid} = "{name}"')

# Show the complete theory
print()
print('COMPLETE ENGINE INTERNAL FUNCTION THEORY')
print('='*70)
print('The Sims engine maintains a function jump table where:')
print('  Global 256 + offset = Base game function')
print('  Global 512 + offset = Livin Large version of same function')
print('  Global 768 + offset = House Party version')
print('  ... and so on for each expansion')
print()
print('This explains why callers reference globals that dont exist as BHAV chunks!')
print('The ENGINE provides these functions internally, not IFF files.')

# Calculate total coverage
missing = data.get('missing_globals', {})
print(f'\nTotal missing globals: {len(missing)}')
print(f'Total caller references to missing: {sum(missing.values())}')
