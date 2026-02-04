#!/usr/bin/env python3
"""
Merge forensic analyses from all expansion packs into a single comprehensive report.

Extracts HIGH/MEDIUM/LOW confidence opcodes from each pack and shows:
- Which opcodes are consistently HIGH confidence across multiple packs
- Pattern stability metrics
- Opcode frequency across packs
"""

import re
from pathlib import Path
from collections import defaultdict
import json

def parse_forensic_file(filepath):
    """Extract opcode confidences from forensic analysis file."""
    
    opcodes = {
        'HIGH': defaultdict(list),
        'MEDIUM': defaultdict(list),
        'LOW': defaultdict(list),
    }
    
    content = Path(filepath).read_text(errors='ignore')
    
    # Find all opcode sections
    for confidence in ['HIGH', 'MEDIUM', 'LOW']:
        # Match pattern like: "0x1234 - Description (CONFIDENCE: HIGH)"
        pattern = rf'(0x[0-9A-F]{{4}}).*?\(CONFIDENCE:\s*{confidence}\)'
        matches = re.finditer(pattern, content, re.IGNORECASE)
        
        for match in matches:
            opcode = match.group(1).upper()
            # Try to extract the descriptive text
            line_start = max(0, match.start() - 200)
            context = content[line_start:match.end()]
            
            # Extract last sentence that might have description
            desc_match = re.search(r'([\w\s,]+)\s*\(CONFIDENCE', context)
            if desc_match:
                desc = desc_match.group(1).strip()
                opcodes[confidence][opcode].append(desc)
    
    return opcodes

def main():
    forensic_files = sorted(Path('.').glob('expansion_forensic_*.txt'))
    
    print("\n" + "="*140)
    print("CROSS-PACK FORENSIC ANALYSIS MERGER")
    print("="*140 + "\n")
    
    # Parse all files
    pack_data = {}
    pack_order = []
    
    for filepath in forensic_files:
        pack_name = filepath.stem.replace('expansion_forensic_', '').upper()
        pack_order.append(pack_name)
        pack_data[pack_name] = parse_forensic_file(filepath)
        print(f"Parsed: {pack_name}")
    
    # Aggregate HIGH confidence opcodes across packs
    opcode_packs = defaultdict(set)
    opcode_confidence = {}
    
    for pack_name in pack_order:
        for opcode in pack_data[pack_name]['HIGH']:
            opcode_packs[opcode].add(pack_name)
            opcode_confidence[opcode] = (opcode_confidence.get(opcode, 0) + 1, 'HIGH')
    
    for pack_name in pack_order:
        for opcode in pack_data[pack_name]['MEDIUM']:
            if opcode not in opcode_packs:
                opcode_packs[opcode].add(pack_name)
    
    # Generate report
    print(f"\n{'='*140}")
    print("OPCODES WITH HIGHEST VALIDATION (appears as HIGH confidence in multiple packs)")
    print(f"{'='*140}\n")
    
    validated = []
    for opcode in sorted(opcode_packs.keys()):
        packs = opcode_packs[opcode]
        validated.append((opcode, len(packs), packs))
    
    validated.sort(key=lambda x: -x[1])
    
    for opcode, count, packs in validated[:50]:  # Top 50 most validated
        print(f"  {opcode} - Validated in {count} packs: {', '.join(sorted(packs))}")
    
    print(f"\n{'='*140}")
    print(f"Summary: {len([v for v in validated if v[1] >= 2])} opcodes confirmed HIGH confidence in 2+ packs")
    print(f"         {len([v for v in validated if v[1] == 1])} opcodes HIGH confidence in single pack")
    print(f"{'='*140}\n")

if __name__ == '__main__':
    main()
