#!/usr/bin/env python3
"""
Extract and merge HIGH confidence opcodes from all 8 expansion pack forensic analyses.
"""

import re
from pathlib import Path
from collections import defaultdict

def extract_high_confidence_opcodes(filepath):
    """Extract HIGH confidence opcodes from a forensic file."""
    
    content = Path(filepath).read_text(errors='ignore')
    opcodes = {}
    
    # Find HIGH confidence section (avoid unicode issues)
    if 'HIGH CONFIDENCE' not in content:
        return opcodes
    
    # Extract section from HIGH CONFIDENCE to MEDIUM/LOW
    section_start = content.index('HIGH CONFIDENCE')
    section_end = content.find('MEDIUM CONFIDENCE', section_start)
    if section_end == -1:
        section_end = content.find('LOW CONFIDENCE', section_start)
    
    section = content[section_start:section_end]
    
    # Find all "Opcode 0x" patterns with their purpose
    # Format: "  Opcode 0x0157:\n    Purpose: Trash-specific operation"
    for match in re.finditer(r'Opcode\s+(0x[0-9A-Fa-f]{4}):\n\s+Purpose:\s*(.+?)(?:\n|$)', section):
        opcode = match.group(1).upper()
        purpose = match.group(2).strip()
        opcodes[opcode] = {'description': purpose}
    
    return opcodes

def main():
    forensic_files = sorted(Path('.').glob('expansion_forensic_*.txt'))
    
    print("\n" + "="*140)
    print("HIGH CONFIDENCE OPCODE CROSS-PACK VALIDATION")
    print("="*140 + "\n")
    
    # Extract from all files
    pack_opcodes = {}
    pack_order = []
    
    for filepath in forensic_files:
        pack_name = filepath.stem.replace('expansion_forensic_', '').upper()
        pack_order.append(pack_name)
        pack_opcodes[pack_name] = extract_high_confidence_opcodes(filepath)
        
        high_count = len(pack_opcodes[pack_name])
        print(f"  {pack_name:20s}: {high_count:3d} HIGH confidence opcodes")
    
    # Find opcodes that appear across multiple packs
    opcode_appearances = defaultdict(list)
    opcode_descriptions = {}
    
    for pack_name in pack_order:
        for opcode, data in pack_opcodes[pack_name].items():
            opcode_appearances[opcode].append(pack_name)
            opcode_descriptions[opcode] = data['description']
    
    # Filter for multi-pack appearances
    validated = {}
    for opcode in sorted(opcode_appearances.keys()):
        if len(opcode_appearances[opcode]) >= 2:
            validated[opcode] = opcode_appearances[opcode]
    
    print(f"\n{'='*140}")
    print(f"OPCODES VALIDATED ACROSS 2+ PACKS (VERY HIGH CONFIDENCE)")
    print(f"{'='*140}\n")
    
    if validated:
        for opcode in sorted(validated.keys()):
            packs = validated[opcode]
            desc = opcode_descriptions.get(opcode, 'Unknown')
            print(f"  {opcode}: {desc}")
            print(f"    ├─ Appears in: {', '.join(packs)}")
            print(f"    └─ Validation strength: {len(packs)}/{len(pack_order)} packs\n")
    else:
        print("  [No opcodes yet validated across 2+ packs]")
        print("  Note: HIGH confidence patterns are still emerging with multi-pack analysis\n")
    
    # Show per-pack summary
    print(f"{'='*140}")
    print(f"HIGH CONFIDENCE OPCODE SUMMARY")
    print(f"{'='*140}\n")
    
    for pack_name in pack_order:
        opcodes = pack_opcodes[pack_name]
        if opcodes:
            print(f"{pack_name}:")
            for opcode in sorted(opcodes.keys())[:10]:  # Top 10
                desc = opcodes[opcode]['description']
                print(f"  ✓ {opcode}: {desc}")
            if len(opcodes) > 10:
                print(f"  ... and {len(opcodes) - 10} more")
        else:
            print(f"{pack_name}: (no HIGH confidence opcodes)")
        print()

if __name__ == '__main__':
    main()
