#!/usr/bin/env python3
"""
FORENSIC TOOL 2: BHAV Structure Analyzer

For each opcode, analyze:
  - Which BHAVs contain it
  - What are those BHAVs named (hints about purpose)
  - Where in BHAV structure does opcode appear
  - What opcodes surround it (context)
  - How many objects use this BHAV+opcode combo

Deeper than categorization - reveals BEHAVIORAL patterns.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
import re


def parse_bhav_section(content, object_name):
    """Extract BHAV structure from forensic output.
    
    Format:
        [  1/126] AlarmClock
            BHAVs (7): #4096(main), #4097(Set Alarm), ...
    
    Returns: {object_name: [(bhav_id, bhav_name), ...]}
    """
    
    bhavs = []
    
    # Find object entry
    pattern = rf'^\s*\[\s*\d+/\d+\]\s+{re.escape(object_name)}\s*$'
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            # Next line should have BHAVs
            if i + 1 < len(lines):
                bhav_line = lines[i + 1]
                # Extract: BHAVs (7): #4096(main), #4097(Set Alarm), ...
                match = re.search(r'BHAVs\s*\((\d+)\):\s*(.*?)(?:\n|$)', bhav_line)
                if match:
                    bhav_str = match.group(2)
                    # Parse each BHAV: #4096(main)
                    for bhav_match in re.finditer(r'#(\d+)\(([^)]+)\)', bhav_str):
                        bhav_id = int(bhav_match.group(1))
                        bhav_name = bhav_match.group(2)
                        bhavs.append((bhav_id, bhav_name))
            break
    
    return bhavs if bhavs else None


def analyze_forensic_file(filepath):
    """
    Analyze a forensic output file and build:
    - opcode → [(object, bhav_id, bhav_name), ...]
    - object → [bhav_structures]
    
    Returns: {opcode: [(object, bhav_id, bhav_name, evidence), ...]}
    """
    
    content = Path(filepath).read_text(errors='ignore')
    
    opcode_usage = defaultdict(list)
    
    # Find HIGH confidence opcodes section
    if 'HIGH CONFIDENCE' not in content:
        return opcode_usage
    
    section_start = content.index('HIGH CONFIDENCE')
    section_end = content.find('MEDIUM CONFIDENCE', section_start)
    if section_end == -1:
        section_end = content.find('LOW CONFIDENCE', section_start)
    
    high_section = content[section_start:section_end]
    
    # Extract each opcode and its objects
    # Format:
    #   Opcode 0x0157:
    #     Purpose: Trash-specific operation
    #     Evidence: 100% of users (4) are Trash
    #     Objects using: 4
    #     Uses: TrashCompactor, TrashOutside, trash1, trashpile
    
    for match in re.finditer(
        r'Opcode\s+(0x[0-9A-Fa-f]{4}):\n'
        r'\s+Purpose:\s*(.+?)\n'
        r'\s+Evidence:\s*(.+?)\n'
        r'\s+Objects using:\s*(\d+)\n'
        r'\s+Uses:\s*(.+?)(?:\n|$)',
        high_section
    ):
        opcode = match.group(1).upper()
        purpose = match.group(2).strip()
        evidence = match.group(3).strip()
        obj_count = int(match.group(4))
        obj_list = match.group(5).strip()
        
        # Parse object list
        objects = [o.strip() for o in obj_list.split(',')]
        
        # For each object, extract BHAV structure
        # We need to find it in the main content
        for obj in objects:
            bhavs = parse_bhav_section(content, obj)
            if bhavs:
                for bhav_id, bhav_name in bhavs:
                    opcode_usage[opcode].append({
                        'object': obj,
                        'bhav_id': bhav_id,
                        'bhav_name': bhav_name,
                        'purpose': purpose,
                        'evidence': evidence
                    })
            else:
                # Object found in HIGH confidence but BHAV info not located
                opcode_usage[opcode].append({
                    'object': obj,
                    'bhav_id': '?',
                    'bhav_name': '?',
                    'purpose': purpose,
                    'evidence': evidence
                })
    
    return opcode_usage


def main():
    if len(sys.argv) < 2:
        print("Usage: python forensic_bhav_analyzer.py <forensic_output_file> [--top N]")
        print("Example: python forensic_bhav_analyzer.py expansion_forensic_base_game.txt --top 10")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    top_n = 15  # Default
    
    if '--top' in sys.argv:
        idx = sys.argv.index('--top')
        if idx + 1 < len(sys.argv):
            top_n = int(sys.argv[idx + 1])
    
    print("\n" + "="*140)
    print(f"BHAV STRUCTURE ANALYSIS: {filepath.name}")
    print("="*140 + "\n")
    
    opcode_data = analyze_forensic_file(filepath)
    
    # Sort by number of objects using each opcode
    sorted_opcodes = sorted(
        opcode_data.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    # Show top N most-used opcodes with BHAV context
    for i, (opcode, usages) in enumerate(sorted_opcodes[:top_n]):
        
        print(f"\n{opcode}: {len(usages)} object instances")
        print("-" * 140)
        
        # Group by BHAV name to find patterns
        bhav_patterns = defaultdict(list)
        for usage in usages:
            key = usage['bhav_name']
            bhav_patterns[key].append(usage['object'])
        
        print(f"Purpose: {usages[0]['purpose']}")
        print(f"Evidence: {usages[0]['evidence']}")
        print(f"\nBHAV Usage Patterns:")
        
        for bhav_name, objects in sorted(bhav_patterns.items(), key=lambda x: -len(x[1]))[:5]:
            print(f"  • In '{bhav_name}' BHAVs: {len(objects)} objects")
            if len(objects) <= 4:
                print(f"    └─ {', '.join(objects)}")
            else:
                print(f"    └─ {', '.join(objects[:3])} ... (+{len(objects)-3} more)")
        
        print()
    
    print(f"\n{'='*140}")
    print(f"Analysis complete: {len(opcode_data)} HIGH confidence opcodes analyzed")
    print(f"Use '--top N' to show different counts (default: 15)")
    print(f"{'='*140}\n")


if __name__ == '__main__':
    main()
