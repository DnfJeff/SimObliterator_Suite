#!/usr/bin/env python3
"""
FORENSIC REPORT GENERATOR: Comprehensive BHAV Deduction Analysis

Combines:
1. Category clustering (signature opcodes)
2. BHAV structure analysis (where opcodes appear)
3. Co-occurrence analysis (opcode suites)

Output: Comprehensive hypothesis about what each HIGH confidence opcode does
"""

import sys
from pathlib import Path
from collections import defaultdict
import re


def extract_all_opcodes(content):
    """Extract all HIGH confidence opcodes with full context."""
    
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
        opcodes[opcode] = {
            'purpose': match.group(2).strip(),
            'evidence': match.group(3).strip(),
            'objects': [o.strip() for o in match.group(5).split(',')],
            'count': int(match.group(4))
        }
    
    return opcodes


def analyze_opcode_pattern(opcode, opcode_data, all_opcodes):
    """Generate hypothesis about what an opcode does."""
    
    data = opcode_data[opcode]
    
    # Analyze object types
    objects = data['objects']
    categories = categorize_objects(objects)
    
    # Build pattern description
    patterns = []
    
    # Pattern 1: Category exclusive?
    unique_categories = len(categories)
    dominant_category = max(categories.items(), key=lambda x: x[1])[0] if categories else 'Unknown'
    
    if unique_categories == 1:
        patterns.append(f"🎯 CATEGORY-EXCLUSIVE: Only in {dominant_category} objects ({len(objects)}/100%)")
    else:
        main_pct = (categories[dominant_category] / len(objects)) * 100
        patterns.append(f"🔹 DOMINANT PATTERN: {dominant_category} ({categories[dominant_category]}/{len(objects)} = {main_pct:.0f}%)")
    
    # Pattern 2: Functional role (inferred from object types)
    if dominant_category == 'Trash':
        patterns.append("💼 INFERRED ROLE: Deletion/disposal operation (trash-exclusive suggests cleanup/discard)")
    elif dominant_category == 'NPC':
        patterns.append("👥 INFERRED ROLE: NPC initialization or behavioral control")
    elif dominant_category == 'Seating':
        patterns.append("🪑 INFERRED ROLE: Seating interaction handler")
    elif dominant_category == 'Eating':
        patterns.append("🍽️  INFERRED ROLE: Food consumption or serving logic")
    elif dominant_category == 'Tub':
        patterns.append("🛁 INFERRED ROLE: Water/bathing interaction handler")
    elif dominant_category == 'Multi-use':
        # Check if it's in interaction-heavy objects
        if any(obj in ['Food', 'SocialInteractions'] for obj in objects):
            patterns.append("🤝 INFERRED ROLE: Social/interaction suite component")
    
    # Pattern 3: Dependency pattern
    suite_opcodes = find_related_opcodes(opcode, all_opcodes, max_related=3)
    if suite_opcodes:
        patterns.append(f"🔗 PART OF SUITE: Often paired with {', '.join(suite_opcodes)}")
    
    return patterns


def categorize_objects(objects):
    """Categorize objects by type."""
    
    categories = defaultdict(int)
    
    keywords = {
        'Trash': ['trash', 'trash', 'Trash', 'Compactor'],
        'NPC': ['People', 'NPC', 'Maid', 'Gardener', 'Repairman', 'Officer', 'Firefighter', 'PizzaDude', 'RepoMan'],
        'Seating': ['Chair', 'Sofa', 'Bench', 'Toilet', 'Couch'],
        'Eating': ['Food', 'Fridge', 'Stove', 'Counter', 'Diner', 'Watermelon', 'Candy'],
        'Tub': ['Tub', 'Hot'],
        'Bed': ['Bed', 'Crib'],
        'Entertainment': ['TV', 'Stereo', 'Game', 'Phone'],
        'Work': ['Desk', 'Computer', 'Easel'],
    }
    
    for obj in objects:
        categorized = False
        for category, keywords_list in keywords.items():
            if any(kw.lower() in obj.lower() for kw in keywords_list):
                categories[category] += 1
                categorized = True
                break
        
        if not categorized:
            categories['Other'] += 1
    
    if len(categories) > 1:
        categories['Multi-use'] = len(objects)
    
    return dict(categories)


def find_related_opcodes(opcode, all_opcodes, max_related=3):
    """Find opcodes that appear in same objects."""
    
    target_objects = set(all_opcodes[opcode]['objects'])
    related = []
    
    for other_opcode in all_opcodes:
        if other_opcode == opcode:
            continue
        
        other_objects = set(all_opcodes[other_opcode]['objects'])
        shared = len(target_objects & other_objects)
        
        if shared >= 2:
            related.append((other_opcode, shared))
    
    # Return top N
    related.sort(key=lambda x: -x[1])
    return [op for op, _ in related[:max_related]]


def main():
    if len(sys.argv) < 2:
        print("Usage: python forensic_comprehensive_report.py <forensic_file> [--count N]")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    count = 15
    
    if '--count' in sys.argv:
        idx = sys.argv.index('--count')
        if idx + 1 < len(sys.argv):
            count = int(sys.argv[idx + 1])
    
    content = filepath.read_text(errors='ignore')
    opcodes = extract_all_opcodes(content)
    
    print("\n" + "="*140)
    print(f"COMPREHENSIVE FORENSIC ANALYSIS REPORT: {filepath.name}")
    print("="*140 + "\n")
    
    # Sort by object count (most common first = most evidence)
    sorted_opcodes = sorted(opcodes.items(), key=lambda x: -x[1]['count'])
    
    print(f"Found {len(opcodes)} HIGH confidence opcodes\n")
    print("LEGEND:")
    print("  🎯 = Category-exclusive (appears ONLY in one object type)")
    print("  🔹 = Dominant pattern (appears mostly in one type, with minor exceptions)")
    print("  🔗 = Part of a functional suite (works with other opcodes)")
    print("  💼/👥/🪑/🍽️/🛁/🤝 = Inferred behavioral role\n")
    print("-"*140)
    
    for i, (opcode, data) in enumerate(sorted_opcodes[:count], 1):
        print(f"\n[{i:2d}] {opcode}: {data['purpose']}")
        print(f"     Evidence: {data['evidence']}")
        print(f"     Objects: {len(data['objects'])} - {', '.join(data['objects'][:5])}", end='')
        if len(data['objects']) > 5:
            print(f" + {len(data['objects'])-5} more")
        else:
            print()
        
        # Generate patterns
        patterns = analyze_opcode_pattern(opcode, opcodes, opcodes)
        for pattern in patterns:
            print(f"     {pattern}")
    
    print("\n" + "="*140)
    print(f"Report complete - analyzed top {min(count, len(opcodes))} opcodes")
    print("="*140 + "\n")


if __name__ == '__main__':
    main()
