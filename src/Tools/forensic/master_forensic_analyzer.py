#!/usr/bin/env python3
"""
MASTER FORENSIC ANALYZER - Orchestrates deep analysis across all FAR files

Workflow:
1. Run comprehensive report on each file (category clustering + inferred roles)
2. Find opcodes that appear in SAME functional role across multiple packs
3. Build confidence matrix: How many packs confirm same role = confidence level
4. Generate OPCODE REFERENCE GUIDE with HIGH/MEDIUM/LOW confidence functional deductions

This is where we unlock the serious discoveries.
"""

import sys
from pathlib import Path
from collections import defaultdict
import re


def extract_opcodes_from_forensic(filepath):
    """Extract HIGH confidence opcodes from forensic file."""
    
    opcodes = {}
    content = filepath.read_text(errors='ignore')
    
    if 'HIGH CONFIDENCE' not in content:
        return opcodes
    
    section_start = content.index('HIGH CONFIDENCE')
    section_end = content.find('MEDIUM CONFIDENCE', section_start)
    if section_end == -1:
        section_end = content.find('LOW CONFIDENCE', section_start)
    
    high_section = content[section_start:section_end]
    
    for match in re.finditer(
        r'Opcode\s+(0x[0-9A-Fa-f]{4}):\n'
        r'\s+Purpose:\s*(.+?)\n'
        r'\s+Evidence:\s*(.+?)\n'
        r'\s+Objects using:\s*(\d+)\n'
        r'\s+Uses:\s*(.+?)(?:\n|$)',
        high_section
    ):
        opcode = match.group(1).upper()
        opcodes[opcode] = {
            'purpose': match.group(2).strip(),
            'evidence': match.group(3).strip(),
            'objects': [o.strip() for o in match.group(5).split(',')],
        }
    
    return opcodes


def infer_functional_category(opcode_data):
    """Infer what the opcode likely does based on objects using it."""
    
    objects = opcode_data['objects']
    evidence = opcode_data['evidence']
    
    # Simple keyword-based inference
    if 'Trash' in evidence or 'trash' in str(objects).lower():
        return 'TRASH_DISPOSAL'
    elif 'NPC' in evidence or 'People' in str(objects):
        return 'NPC_BEHAVIOR'
    elif 'Tub' in evidence or 'tub' in str(objects).lower():
        return 'WATER_BATHING'
    elif 'Food' in str(objects) or 'eat' in evidence.lower():
        return 'FOOD_INTERACTION'
    elif 'Bed' in str(objects):
        return 'SLEEP_REST'
    elif 'Toilet' in str(objects):
        return 'SANITATION'
    else:
        return 'GENERIC'


def main():
    forensic_files = sorted(Path('.').glob('expansion_forensic_*.txt'))
    
    if not forensic_files:
        print("No forensic files found. Run 'python run_expansion_analysis.py' first.")
        sys.exit(1)
    
    print("\n" + "="*140)
    print("MASTER FORENSIC ANALYZER - Cross-Pack Opcode Discovery")
    print("="*140 + "\n")
    
    # Extract opcodes from all files
    all_pack_opcodes = {}
    opcode_func_categories = defaultdict(list)  # opcode -> [(pack, category), ...]
    opcode_evidence = {}  # opcode -> (most common evidence description)
    
    for filepath in forensic_files:
        pack_name = filepath.stem.replace('expansion_forensic_', '').upper()
        opcodes = extract_opcodes_from_forensic(filepath)
        all_pack_opcodes[pack_name] = opcodes
        
        print(f"  {pack_name:20s}: {len(opcodes):3d} HIGH confidence opcodes")
        
        for opcode, data in opcodes.items():
            func_cat = infer_functional_category(data)
            opcode_func_categories[opcode].append((pack_name, func_cat))
            
            # Store evidence for later
            if opcode not in opcode_evidence:
                opcode_evidence[opcode] = data['evidence']
    
    print(f"\n{'='*140}")
    print("DISCOVERY PHASE: Opcodes with CONSISTENT functional roles across packs")
    print(f"{'='*140}\n")
    
    # Find opcodes that have same functional category across multiple packs
    consistent_opcodes = []
    
    for opcode, pack_categories in opcode_func_categories.items():
        if len(pack_categories) >= 2:
            categories = [cat for _, cat in pack_categories]
            # Check if all categories are the same
            if len(set(categories)) == 1:
                confidence_level = min(3, len(pack_categories))  # 1-3 stars
                consistent_opcodes.append({
                    'opcode': opcode,
                    'category': categories[0],
                    'packs': len(pack_categories),
                    'evidence': opcode_evidence[opcode],
                })
    
    # Sort by pack count (most validated = most confident)
    consistent_opcodes.sort(key=lambda x: -x['packs'])
    
    print(f"Found {len(consistent_opcodes)} opcodes with CONSISTENT roles across 2+ packs\n")
    
    # Group by functional category
    by_category = defaultdict(list)
    for item in consistent_opcodes:
        by_category[item['category']].append(item)
    
    for category in sorted(by_category.keys()):
        opcodes_in_category = by_category[category]
        confidence_star = '⭐' * min(3, max(item['packs'] for item in opcodes_in_category))
        
        print(f"\n{category} {confidence_star}")
        print("-" * 140)
        
        for item in sorted(opcodes_in_category, key=lambda x: -x['packs'])[:10]:
            packs_str = f"({item['packs']} packs)"
            print(f"  {item['opcode']:8s} {packs_str:12s} | {item['evidence']}")
    
    # Summary statistics
    print(f"\n{'='*140}")
    print("CONFIDENCE BREAKDOWN")
    print(f"{'='*140}\n")
    
    three_star = len([x for x in consistent_opcodes if x['packs'] >= 3])
    two_star = len([x for x in consistent_opcodes if x['packs'] == 2])
    
    print(f"  ⭐⭐⭐ (3+ packs):      {three_star:3d} opcodes - VERY HIGH confidence deductions")
    print(f"  ⭐⭐  (2 packs):       {two_star:3d} opcodes - HIGH confidence deductions")
    print(f"  ⭐   (single pack):   Remaining opcodes - MEDIUM confidence (needs expansion data)\n")
    
    print(f"  Total HIGH confidence opcodes across all packs: {len(opcodes)}")
    print(f"  Validated across multiple packs: {len(consistent_opcodes)} ({(len(consistent_opcodes)*100//len(opcodes)):.0f}%)")
    
    print(f"\n{'='*140}")
    print("NEXT STEPS")
    print(f"{'='*140}\n")
    print("1. Use forensic_bhav_analyzer.py to detail WHERE in BHAVs opcodes appear")
    print("2. Use forensic_cooccurrence.py to understand OPCODE SUITES")
    print("3. Manually verify high-confidence deductions against FSO source code")
    print("4. Build OPCODE REFERENCE GUIDE with discovered patterns\n")


if __name__ == '__main__':
    main()
