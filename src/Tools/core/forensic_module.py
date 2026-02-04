"""
FORENSIC MODULE - Pattern Analysis for Reverse Engineering

Deductive reasoning tool for unknown BHAV opcodes through pattern identification.
Analyzes what objects use which opcodes to infer functionality with forensic rigor.

This is NOT statistical guessing. This is evidence-based analysis:
- What objects use this opcode?
- What do those objects have in common?
- What object types ONLY use this opcode?
- What patterns emerge from cross-object correlation?

Confidence levels:
- HIGH: 100% of objects in a category use this opcode, consistent pattern
- MEDIUM: Strong pattern but with exceptions
- LOW: Isolated usage or insufficient evidence
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter


@dataclass
class OpcodeProfile:
    """Profile of an unknown opcode based on usage patterns."""
    opcode: int
    hex_str: str
    total_occurrences: int  # Total times used across all BHAVs
    objects_using: Set[str] = field(default_factory=set)
    unique_object_count: int = 0
    
    # Evidence tracking
    category_breakdown: Dict[str, int] = field(default_factory=dict)  # Category: count
    object_list: List[str] = field(default_factory=list)  # All objects using this opcode
    
    # Analysis
    confidence_level: str = "UNANALYZED"  # HIGH, MEDIUM, LOW
    primary_category: str = "UNKNOWN"
    inferred_purpose: str = ""
    evidence_summary: List[str] = field(default_factory=list)
    pattern_notes: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)  # Cases that don't fit the pattern


class ForensicAnalyzer:
    """Analyzes unknown opcodes through rigorous pattern matching."""
    
    def __init__(self):
        """Initialize forensic analyzer."""
        # Precise object categorization - not fuzzy keyword matching
        self.object_categories = {
            # COOKING & FOOD preparation
            'Stoves': ['Stoves'],
            'Refrigerators': ['Fridges'],
            'Microwave': ['Microwave'],
            'Counter': ['Counter', 'Counters'],
            'Dishwasher': ['Dishwash'],
            'Food_Service': ['Espresso', 'Coffee', 'Soda', 'BreakfastBar'],
            
            # SLEEPING & HYGIENE
            'Beds': ['Beds', 'BunkBeds'],
            'Toilet': ['Toilets'],
            'Shower': ['ShowerC', 'ShowerStall'],
            'Tub': ['TubC', 'TubM', 'tubx', 'HotTub'],
            'Sink': ['SinkKitchen', 'SinkBath'],
            'Mirror': ['Mirror'],
            
            # ENTERTAINMENT & RELAXATION
            'Stereo': ['Stereo'],
            'TV': ['TVStand'],
            'Piano': ['Piano'],
            'Pool': ['Pool', 'PoolTable'],
            'Game_Machine': ['Arcade', 'Pinball'],
            'Easel': ['Easel'],
            'Bookcase': ['Bookcases'],
            'Chess': ['ChessTable'],
            
            # DINING
            'Dining_Table': ['DiningTables', 'TablesEnd', 'TableDesk'],
            'Seat': ['Chairs', 'chair', 'Couch'],
            
            # WORK & SKILL
            'Computer': ['Computer'],
            'Desk': ['Desks'],
            
            # OUTDOOR
            'Trash': ['Trash', 'trash', 'TrashCompactor', 'TrashOutside'],
            'Door': ['Doors', 'Door'],
            'Mail': ['Mailbox'],
            'Plant': ['Plants'],
            'Sculpture': ['Sculpture'],
            'Fountain': ['Fountain'],
            
            # VEHICLES
            'Car': ['Car'],
            
            # SPECIAL
            'Lighting': ['Lamps'],
            'Decor': ['Paintings'],
            'Phone': ['Phone'],
            'Baby_Care': ['Baby'],
            'Security': ['BurglarAlarm'],
            'Decorative': ['Sculptures', 'aquarium'],
        }
        
        # Build reverse lookup
        self.object_to_category = {}
        for category, objects in self.object_categories.items():
            for obj_pattern in objects:
                self.object_to_category[obj_pattern] = category
    
    def categorize_object(self, object_name: str) -> str:
        """Categorize object by exact/fuzzy matching."""
        # Try exact match first
        if object_name in self.object_to_category:
            return self.object_to_category[object_name]
        
        # Try partial match
        name_lower = object_name.lower()
        for pattern, category in self.object_to_category.items():
            if pattern.lower() in name_lower or name_lower in pattern.lower():
                return category
        
        # Special cases based on naming patterns
        if name_lower.startswith('car'):
            return 'Car'
        elif 'people' in name_lower.lower() or '\\' in object_name:
            return 'NPC'
        
        return 'OTHER'
    
    def analyze_opcode_profiles(self, objects_by_opcode: Dict[int, List[str]]) -> Dict[int, OpcodeProfile]:
        """Analyze opcode usage patterns with forensic rigor.
        
        Args:
            objects_by_opcode: {opcode: [list of object names]}
        
        Returns:
            {opcode: OpcodeProfile with detailed analysis}
        """
        profiles = {}
        
        for opcode, objects in objects_by_opcode.items():
            profile = OpcodeProfile(
                opcode=opcode,
                hex_str=f"0x{opcode:04X}",
                total_occurrences=len(objects),
                objects_using=set(objects),
                unique_object_count=len(set(objects)),
                object_list=sorted(list(set(objects)))
            )
            
            # Categorize all objects using this opcode
            categories = defaultdict(list)  # category -> [objects]
            for obj in set(objects):
                cat = self.categorize_object(obj)
                categories[cat].append(obj)
            
            profile.category_breakdown = {cat: len(objs) for cat, objs in categories.items()}
            
            # Analyze the pattern
            self._analyze_pattern(profile, categories)
            
            profiles[opcode] = profile
        
        return profiles
    
    def _analyze_pattern(self, profile: OpcodeProfile, categories: Dict[str, List[str]]):
        """Perform forensic analysis on opcode usage pattern."""
        total_objects = profile.unique_object_count
        
        if total_objects == 1:
            # Single object - object-specific
            obj = profile.object_list[0]
            cat = self.categorize_object(obj)
            profile.confidence_level = "LOW"
            profile.primary_category = cat
            profile.inferred_purpose = f"Object-specific behavior ({obj})"
            profile.evidence_summary.append(f"Only used by 1 object: {obj}")
            
        elif len(categories) == 1:
            # All objects in single category
            category = list(categories.keys())[0]
            objects = categories[category]
            profile.primary_category = category
            profile.inferred_purpose = f"{category}-specific operation"
            
            # Check how "pure" this category is
            if len(objects) == total_objects:
                profile.confidence_level = "HIGH"
                profile.evidence_summary.append(f"100% of users ({len(objects)}) are {category}")
                profile.pattern_notes.append(f"ALL {category} items: {', '.join(objects[:5])}{'...' if len(objects) > 5 else ''}")
            else:
                profile.confidence_level = "MEDIUM"
                profile.evidence_summary.append(f"{len(objects)} of {total_objects} users are {category}")
                
        elif len(categories) == 2 and 'OTHER' in categories:
            # Mostly one category, some OTHER
            non_other = {k: v for k, v in categories.items() if k != 'OTHER'}
            if non_other:
                category = list(non_other.keys())[0]
                cat_count = len(non_other[category])
                profile.primary_category = category
                
                if cat_count >= total_objects * 0.7:  # 70%+ are in one category
                    profile.confidence_level = "MEDIUM"
                    profile.inferred_purpose = f"Primarily {category}-related"
                    profile.evidence_summary.append(f"{cat_count}/{total_objects} users are {category}")
                    profile.contradictions.append(f"Also used by: {', '.join(categories['OTHER'][:3])}")
                else:
                    profile.confidence_level = "LOW"
                    profile.inferred_purpose = "Mixed usage pattern"
                    profile.evidence_summary.append(f"Used by multiple categories: {', '.join(categories.keys())}")
        
        else:
            # Multiple diverse categories
            profile.confidence_level = "LOW"
            profile.inferred_purpose = "Generic operation (mixed categories)"
            
            # Rank categories by prevalence
            sorted_cats = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
            profile.primary_category = sorted_cats[0][0]
            
            for cat, objs in sorted_cats[:3]:
                profile.evidence_summary.append(f"{cat}: {len(objs)} object(s)")
            
            # But note if there's a strong secondary pattern
            if len(sorted_cats[0][1]) >= total_objects * 0.5:
                profile.pattern_notes.append(f"Primary use in {sorted_cats[0][0]} (50%+)")
    
    def generate_forensic_report(self, profiles: Dict[int, OpcodeProfile]) -> str:
        """Generate detailed forensic analysis report."""
        report = []
        report.append("\n" + "="*120)
        report.append(" FORENSIC ANALYSIS: OPCODE REVERSE ENGINEERING")
        report.append("="*120)
        report.append("\nEvidence-based pattern analysis. Confidence based on usage consistency.\n")
        
        # Group by confidence level
        by_confidence = {"HIGH": [], "MEDIUM": [], "LOW": []}
        for opcode, profile in sorted(profiles.items(), key=lambda x: (x[1].confidence_level, -x[1].unique_object_count)):
            by_confidence[profile.confidence_level].append((opcode, profile))
        
        # HIGH CONFIDENCE - Clear, consistent patterns
        if by_confidence["HIGH"]:
            report.append("\n" + "█"*120)
            report.append("█ HIGH CONFIDENCE: Clear, consistent patterns across all or nearly all users")
            report.append("█"*120)
            for opcode, profile in by_confidence["HIGH"]:
                report.append(f"\n  Opcode {profile.hex_str}:")
                report.append(f"    Purpose: {profile.inferred_purpose}")
                report.append(f"    Evidence: {' | '.join(profile.evidence_summary)}")
                report.append(f"    Objects using: {profile.unique_object_count}")
                
                # Show all objects clearly
                obj_str = ", ".join(profile.object_list)
                if len(obj_str) > 100:
                    report.append(f"    Uses: {obj_str[:100]}...")
                else:
                    report.append(f"    Uses: {obj_str}")
                
                if profile.contradictions:
                    report.append(f"    ⚠ Exceptions: {' | '.join(profile.contradictions)}")
                for note in profile.pattern_notes:
                    report.append(f"    ► {note}")
        
        # MEDIUM CONFIDENCE - Probable patterns with exceptions
        if by_confidence["MEDIUM"]:
            report.append("\n" + "▓"*120)
            report.append("▓ MEDIUM CONFIDENCE: Strong primary pattern with exceptions or secondary usage")
            report.append("▓"*120)
            for opcode, profile in sorted(by_confidence["MEDIUM"], key=lambda x: -x[1].unique_object_count)[:30]:
                report.append(f"\n  Opcode {profile.hex_str}:")
                report.append(f"    Purpose: {profile.inferred_purpose}")
                report.append(f"    Evidence: {' | '.join(profile.evidence_summary)}")
                report.append(f"    Objects using: {profile.unique_object_count}")
                
                # Show objects by category
                for cat in sorted(set(self.categorize_object(obj) for obj in profile.object_list)):
                    objs_in_cat = [obj for obj in profile.object_list if self.categorize_object(obj) == cat]
                    report.append(f"      [{cat}] {', '.join(objs_in_cat[:4])}{'...' if len(objs_in_cat) > 4 else ''}")
                
                if profile.contradictions:
                    report.append(f"    ⚠ Exceptions: {' | '.join(profile.contradictions)}")
                for note in profile.pattern_notes:
                    report.append(f"    ► {note}")
        
        # LOW CONFIDENCE - Insufficient data or too much variability
        if by_confidence["LOW"]:
            report.append("\n" + "░"*120)
            report.append("░ LOW CONFIDENCE: Insufficient data or too much variability - needs more examples")
            report.append("░"*120)
            
            # Organize by object count
            by_count = defaultdict(list)
            for opcode, profile in by_confidence["LOW"]:
                by_count[profile.unique_object_count].append((opcode, profile))
            
            report.append("\n  Isolated usage (single objects):")
            if 1 in by_count:
                for opcode, profile in by_count[1][:20]:
                    report.append(f"    {profile.hex_str}: {profile.object_list[0]}")
                if len(by_count[1]) > 20:
                    report.append(f"    ... and {len(by_count[1]) - 20} more single-object opcodes")
            
            report.append("\n  Mixed category usage (insufficient dominant pattern):")
            mixed = []
            for count in sorted([c for c in by_count if c > 1], reverse=True):
                mixed.extend(by_count[count])
            
            for opcode, profile in mixed[:20]:
                cats = ', '.join(f"{cat}({count})" for cat, count in sorted(profile.category_breakdown.items(), key=lambda x: -x[1]))
                report.append(f"    {profile.hex_str}: {profile.unique_object_count} objects ({cats})")
            
            if len(mixed) > 20:
                report.append(f"    ... and {len(mixed) - 20} more mixed-category opcodes")
        
        # Summary statistics
        report.append("\n" + "="*120)
        report.append(" FORENSIC SUMMARY")
        report.append("="*120)
        report.append(f"Total opcodes analyzed:  {len(profiles)}")
        report.append(f"  HIGH confidence:       {len(by_confidence['HIGH'])} opcodes (clear patterns)")
        report.append(f"  MEDIUM confidence:     {len(by_confidence['MEDIUM'])} opcodes (probable patterns)")
        report.append(f"  LOW confidence:        {len(by_confidence['LOW'])} opcodes (insufficient data)")
        
        return "\n".join(report)
    
    def generate_category_focused_report(self, profiles: Dict[int, OpcodeProfile]) -> str:
        """Generate report organized by object category."""
        report = []
        report.append("\n" + "="*120)
        report.append(" CATEGORY-FOCUSED OPCODE ANALYSIS")
        report.append("="*120 + "\n")
        
        # Map opcodes to categories
        category_opcodes = defaultdict(lambda: defaultdict(int))  # category -> opcode -> count
        category_objects = defaultdict(set)  # category -> set of objects
        
        for opcode, profile in profiles.items():
            for obj in profile.object_list:
                cat = self.categorize_object(obj)
                category_opcodes[cat][opcode] += 1
                category_objects[cat].add(obj)
        
        # Report by category
        for category in sorted(category_opcodes.keys()):
            opcodes = category_opcodes[category]
            objects = category_objects[category]
            
            report.append(f"\n{category}")
            report.append("-" * 120)
            report.append(f"Objects: {len(objects)} ({', '.join(sorted(objects)[:10])}{'...' if len(objects) > 10 else ''})")
            report.append(f"Unique opcodes: {len(opcodes)}")
            
            # Top opcodes used by this category
            report.append("\nMost common opcodes:")
            for opcode, count in sorted(opcodes.items(), key=lambda x: -x[1])[:15]:
                profile = profiles[opcode]
                confidence_icon = "✓" if profile.confidence_level == "HIGH" else "◐" if profile.confidence_level == "MEDIUM" else "✗"
                report.append(f"  {confidence_icon} {profile.hex_str}: {count} objects - {profile.inferred_purpose}")
            
            report.append("")
        
        return "\n".join(report)


def generate_forensic_analysis(objects_by_opcode: Dict[int, List[str]]) -> Tuple[str, str]:
    """Main entry point for forensic analysis.
    
    Args:
        objects_by_opcode: {opcode: [list of object names using it]}
    
    Returns:
        (forensic_report, category_focused_report)
    """
    analyzer = ForensicAnalyzer()
    profiles = analyzer.analyze_opcode_profiles(objects_by_opcode)
    
    forensic_report = analyzer.generate_forensic_report(profiles)
    category_report = analyzer.generate_category_focused_report(profiles)
    
    return forensic_report, category_report
