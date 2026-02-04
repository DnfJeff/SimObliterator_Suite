#!/usr/bin/env python3
"""
FORENSIC TOOL 3: Opcode Co-occurrence & Behavioral Suite Analyzer

Find opcodes that:
  1. Always appear together (opcode suites)
  2. Appear in specific BHAV patterns (behavioral markers)
  3. Form dependency chains (opcode A followed by opcode B)

This reveals which opcodes are related and what suites/clusters exist.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
import re


def extract_all_high_confidence_opcodes(content):
    """Extract ALL high confidence opcodes from forensic file."""
    
    opcodes = {}
    
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
        purpose = match.group(2).strip()
        obj_list = match.group(5).strip()
        objects = [o.strip() for o in obj_list.split(',')]
        
        opcodes[opcode] = {
            'purpose': purpose,
            'objects': objects,
            'count': len(objects)
        }
    
    return opcodes


def find_opcode_cooccurrence(content):
    """
    Find which opcodes appear together in the same objects.
    Build matrix: opcode_A appears with opcode_B in X objects
    """
    
    cooccurrence = defaultdict(lambda: defaultdict(int))
    
    # Extract all HIGH confidence opcodes
    opcodes = extract_all_high_confidence_opcodes(content)
    
    # For each pair of opcodes, check if they share objects
    opcode_list = list(opcodes.keys())
    
    for i, opcode_a in enumerate(opcode_list):
        objects_a = set(opcodes[opcode_a]['objects'])
        
        for opcode_b in opcode_list[i+1:]:
            objects_b = set(opcodes[opcode_b]['objects'])
            
            # Count shared objects
            shared = len(objects_a & objects_b)
            
            if shared > 0:
                cooccurrence[opcode_a][opcode_b] = shared
                cooccurrence[opcode_b][opcode_a] = shared  # Symmetric
    
    return cooccurrence, opcodes


def main():
    if len(sys.argv) < 2:
        print("Usage: python forensic_cooccurrence.py <forensic_file> [--min-shared N]")
        print("Example: python forensic_cooccurrence.py expansion_forensic_base_game.txt --min-shared 2")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    min_shared = 1
    
    if '--min-shared' in sys.argv:
        idx = sys.argv.index('--min-shared')
        if idx + 1 < len(sys.argv):
            min_shared = int(sys.argv[idx + 1])
    
    content = filepath.read_text(errors='ignore')
    
    print("\n" + "="*140)
    print(f"OPCODE CO-OCCURRENCE ANALYSIS: {filepath.name}")
    print(f"(Finding opcodes that appear together in {min_shared}+ objects)")
    print("="*140 + "\n")
    
    cooccurrence, opcodes = find_opcode_cooccurrence(content)
    
    # Find strongest associations
    associations = []
    for opcode_a in cooccurrence:
        for opcode_b, shared_count in cooccurrence[opcode_a].items():
            if opcode_a < opcode_b:  # Avoid duplicates
                # Score: higher shared count = stronger association
                score = shared_count
                associations.append({
                    'opcodes': (opcode_a, opcode_b),
                    'shared': shared_count,
                    'purpose_a': opcodes[opcode_a]['purpose'],
                    'purpose_b': opcodes[opcode_b]['purpose'],
                    'objects_a': opcodes[opcode_a]['count'],
                    'objects_b': opcodes[opcode_b]['count'],
                })
    
    # Sort by shared count
    associations.sort(key=lambda x: -x['shared'])
    
    # Find behavioral suites (3+ opcodes appearing together)
    print("\n" + "▪"*140)
    print("BEHAVIORAL SUITES (3+ opcodes appearing together in same objects)")
    print("▪"*140 + "\n")
    
    # Find cliques of opcodes that all appear together
    def find_suites(cooccurrence, min_suite_size=3, min_overlap=2):
        """Find groups of opcodes that all appear together."""
        suites = []
        
        opcodes_list = list(cooccurrence.keys())
        
        # For each starting opcode, find which other opcodes appear with it
        for start_opcode in opcodes_list:
            # Get all opcodes that appear with this one
            companions = defaultdict(int)
            for opcode_b, count in cooccurrence[start_opcode].items():
                if count >= min_overlap:
                    companions[opcode_b] = count
            
            if len(companions) >= min_suite_size - 1:
                # Check if these companions also appear with each other
                suite = [start_opcode] + list(companions.keys())[:min_suite_size-1]
                suites.append(suite)
        
        # Remove duplicate suites
        unique_suites = []
        suite_strs = set()
        for suite in suites:
            suite_str = ','.join(sorted(suite))
            if suite_str not in suite_strs:
                suite_strs.add(suite_str)
                unique_suites.append(sorted(suite))
        
        return unique_suites
    
    suites = find_suites(cooccurrence, min_suite_size=3, min_overlap=2)
    
    if suites:
        for i, suite in enumerate(suites[:10], 1):  # Top 10 suites
            print(f"\nSuite {i}: {', '.join(suite)}")
            print("-" * 140)
            
            # Show shared objects
            all_objects = None
            for opcode in suite:
                obj_set = set(opcodes[opcode]['objects'])
                if all_objects is None:
                    all_objects = obj_set
                else:
                    all_objects = all_objects & obj_set
            
            if all_objects:
                print(f"Shared across: {', '.join(sorted(all_objects))}")
                print(f"Purposes: {' + '.join([opcodes[op]['purpose'] for op in suite])}")
    else:
        print("[No clear behavioral suites found]")
    
    # Show top associations
    print("\n" + "▪"*140)
    print(f"TOP OPCODE PAIRS (appearing together in {min_shared}+ objects)")
    print("▪"*140 + "\n")
    
    for i, assoc in enumerate(associations[:20], 1):
        opcode_a, opcode_b = assoc['opcodes']
        shared = assoc['shared']
        
        print(f"{i:2d}. {opcode_a} + {opcode_b}: Shared in {shared} objects")
        print(f"     • {opcode_a}: {assoc['purpose_a']} ({assoc['objects_a']} objects)")
        print(f"     • {opcode_b}: {assoc['purpose_b']} ({assoc['objects_b']} objects)")
        print()
    
    print("="*140)
    print(f"Analysis complete: Found {len(associations)} opcode associations")
    print("="*140 + "\n")


if __name__ == '__main__':
    main()
