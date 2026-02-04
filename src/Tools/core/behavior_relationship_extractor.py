"""
Behavior Relationship Layer (BRL)
Extracts relational signals that define ACTION, GUARD, and UTILITY behaviors.

Three Relationship Types:
1. ACTION_ENTRY: BHAV referenced by TTAB (interaction entry point)
2. BEHAVIOR_CALL: BHAV called via opcode 0x0004 (Push Interaction)
3. TTAB→BEHAVIOR: Direct link to TTAB interaction
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
from enum import Enum


class RelationshipType(Enum):
    """Types of behavior relationships."""
    ACTION_ENTRY = "ACTION_ENTRY"      # TTAB → BHAV
    BEHAVIOR_CALL = "BEHAVIOR_CALL"    # BHAV → BHAV via opcode
    TTAB_ENTRY = "TTAB_ENTRY"          # Metadata: this BHAV is in TTAB


@dataclass
class BehaviorRelationship:
    """Single relationship edge in the behavior network."""
    
    source_bhav_id: Optional[int]       # None if source is TTAB or system
    target_bhav_id: int                 # The BHAV being referenced
    relationship_type: RelationshipType
    source_object: str                  # Owner object name (e.g., "Baby.iff")
    confidence: float = 1.0             # 0.0–1.0
    evidence: List[str] = field(default_factory=list)
    
    def __repr__(self):
        if self.source_bhav_id is None:
            return f"[SYSTEM] →[{self.relationship_type.value}]→ BHAV#{self.target_bhav_id}"
        return f"BHAV#{self.source_bhav_id} →[{self.relationship_type.value}]→ BHAV#{self.target_bhav_id}"


@dataclass
class BehaviorRelationshipGraph:
    """Complete relationship graph for an object's behaviors."""
    
    object_name: str
    relationships: List[BehaviorRelationship] = field(default_factory=list)
    
    # Indexed lookups
    inbound_by_bhav: Dict[int, List[BehaviorRelationship]] = field(default_factory=dict)
    outbound_by_bhav: Dict[int, List[BehaviorRelationship]] = field(default_factory=dict)
    ttab_entries: Dict[int, BehaviorRelationship] = field(default_factory=dict)
    
    def add_relationship(self, rel: BehaviorRelationship):
        """Add relationship and update indices."""
        self.relationships.append(rel)
        
        # Index inbound
        if rel.target_bhav_id not in self.inbound_by_bhav:
            self.inbound_by_bhav[rel.target_bhav_id] = []
        self.inbound_by_bhav[rel.target_bhav_id].append(rel)
        
        # Index outbound
        if rel.source_bhav_id is not None:
            if rel.source_bhav_id not in self.outbound_by_bhav:
                self.outbound_by_bhav[rel.source_bhav_id] = []
            self.outbound_by_bhav[rel.source_bhav_id].append(rel)
        
        # Index TTAB entries
        if rel.relationship_type == RelationshipType.ACTION_ENTRY:
            self.ttab_entries[rel.target_bhav_id] = rel
    
    def get_inbound_count(self, bhav_id: int) -> int:
        """How many times is this BHAV called?"""
        return len(self.inbound_by_bhav.get(bhav_id, []))
    
    def get_outbound_count(self, bhav_id: int) -> int:
        """How many BHAVs does this call?"""
        return len(self.outbound_by_bhav.get(bhav_id, []))
    
    def is_ttab_entry(self, bhav_id: int) -> bool:
        """Is this BHAV directly referenced by TTAB?"""
        return bhav_id in self.ttab_entries
    
    def __repr__(self):
        return f"BRL[{self.object_name}]: {len(self.relationships)} relationships, {len(self.ttab_entries)} TTAB entries"


class RelationshipExtractor:
    """Extract relationship signals from IFF object data."""
    
    def extract_from_object(self, object_profile) -> BehaviorRelationshipGraph:
        """
        Extract all relationships for an object.
        
        Assumes object_profile has:
        - .name: object name (e.g., "Baby.iff")
        - .chunks: dict of chunk type → list of chunks
        - .bhav_profiles: list of BehaviorProfile objects
        """
        graph = BehaviorRelationshipGraph(object_name=object_profile.name)
        
        # Phase 1: Extract TTAB → BHAV relationships
        self._extract_ttab_entries(object_profile, graph)
        
        # Phase 2: Extract BHAV → BHAV relationships
        self._extract_behavior_calls(object_profile, graph)
        
        return graph
    
    def _extract_ttab_entries(self, object_profile, graph: BehaviorRelationshipGraph):
        """
        Extract ACTION_ENTRY relationships from TTAB chunks.
        
        TTAB structure (simplified):
        - TTAB contains interaction definitions
        - Each interaction has a behavior ID pointing to a BHAV
        - This makes that BHAV an ACTION candidate
        """
        ttab_chunks = object_profile.chunks.get('TTAB', [])
        
        for ttab_chunk in ttab_chunks:
            # TTAB internal structure varies, but typically:
            # - Has entries/interactions
            # - Each entry references a BHAV ID
            
            if not hasattr(ttab_chunk, 'interactions') and \
               not hasattr(ttab_chunk, 'entries'):
                continue
            
            entries = getattr(ttab_chunk, 'interactions', None) or \
                      getattr(ttab_chunk, 'entries', None) or []
            
            for entry in entries:
                # Extract BHAV ID from entry
                bhav_id = self._get_bhav_id_from_ttab_entry(entry)
                
                if bhav_id is not None:
                    rel = BehaviorRelationship(
                        source_bhav_id=None,
                        target_bhav_id=bhav_id,
                        relationship_type=RelationshipType.ACTION_ENTRY,
                        source_object=object_profile.name,
                        confidence=0.25,  # Base confidence from TTAB link
                        evidence=["via_ttab_entry"]
                    )
                    graph.add_relationship(rel)
    
    def _extract_behavior_calls(self, object_profile, graph: BehaviorRelationshipGraph):
        """
        Extract BEHAVIOR_CALL relationships from BHAV → BHAV opcode calls.
        
        Opcode 0x0004 = Push Interaction / Call BHAV
        This directly calls another BHAV.
        """
        bhav_profiles = getattr(object_profile, 'bhav_profiles', [])
        
        for source_bhav in bhav_profiles:
            instructions = getattr(source_bhav, 'instructions', [])
            
            for inst in instructions:
                # 0x0004 = Push Interaction (calls another BHAV)
                if inst.opcode == 0x0004:
                    target_bhav_id = self._get_bhav_id_from_opcode(inst)
                    
                    if target_bhav_id is not None:
                        rel = BehaviorRelationship(
                            source_bhav_id=source_bhav.bhav_id,
                            target_bhav_id=target_bhav_id,
                            relationship_type=RelationshipType.BEHAVIOR_CALL,
                            source_object=object_profile.name,
                            confidence=1.0,  # Direct opcode call
                            evidence=["opcode_0x0004_push_interaction"]
                        )
                        graph.add_relationship(rel)
    
    @staticmethod
    def _get_bhav_id_from_ttab_entry(entry) -> Optional[int]:
        """
        Extract BHAV ID from a TTAB entry.
        Handles various field name possibilities.
        """
        # Try common field names
        candidates = ['bhav_id', 'behavior_id', 'behavior', 'action_id', 'id']
        
        for field_name in candidates:
            if hasattr(entry, field_name):
                value = getattr(entry, field_name)
                if isinstance(value, int):
                    return value
        
        return None
    
    @staticmethod
    def _get_bhav_id_from_opcode(inst) -> Optional[int]:
        """
        Extract BHAV ID from an opcode instruction.
        Handles various operand field names.
        """
        # Try operands dict
        if hasattr(inst, 'operands') and isinstance(inst.operands, dict):
            candidates = ['behavior_id', 'bhav_id', 'id', 'target']
            for field_name in candidates:
                if field_name in inst.operands:
                    value = inst.operands[field_name]
                    if isinstance(value, int):
                        return value
        
        # Try direct attributes
        candidates = ['behavior_id', 'bhav_id', 'target_id', 'arg1', 'arg2']
        for field_name in candidates:
            if hasattr(inst, field_name):
                value = getattr(inst, field_name)
                if isinstance(value, int):
                    return value
        
        return None


def build_relationship_metrics(graph: BehaviorRelationshipGraph,
                               bhav_profiles: Dict[int, 'BehaviorProfile']) -> Dict[int, Dict]:
    """
    Build derived metrics for each BHAV from relationship graph.
    
    Returns dict: bhav_id → {
        'inbound_call_count': int,
        'outbound_call_count': int,
        'is_ttab_entry': bool,
        'inbound_from_main': bool,
        'can_be_action_conf': float,
        'can_be_guard_conf': float,
        'can_be_utility_conf': float,
    }
    """
    metrics = {}
    
    for bhav_id, profile in bhav_profiles.items():
        inbound_count = graph.get_inbound_count(bhav_id)
        outbound_count = graph.get_outbound_count(bhav_id)
        is_ttab = graph.is_ttab_entry(bhav_id)
        
        # Confidence calculations (heuristic-based)
        
        # ACTION: TTAB entry + finite
        action_conf = 0.0
        if is_ttab:
            action_conf = 0.25
            if not getattr(profile, 'has_infinite_loop', False):
                action_conf += 0.15
            if getattr(profile, 'yield_capable', False):
                action_conf += 0.10
            action_conf = min(action_conf, 1.0)
        
        # GUARD: called from multiple places, short, no yield
        guard_conf = 0.0
        if inbound_count > 0 and not is_ttab:
            guard_conf = 0.15
            inst_count = getattr(profile, 'instruction_count', 0)
            if inst_count <= 10:
                guard_conf += 0.20
            if getattr(profile, 'has_loops', False):
                guard_conf = 0.0
            if getattr(profile, 'yield_capable', False):
                guard_conf = 0.0
            if inbound_count >= 3:
                guard_conf += 0.15
            guard_conf = min(guard_conf, 1.0)
        
        # UTILITY: high fan-in, not entry, reusable
        utility_conf = 0.0
        if inbound_count > 0 and not is_ttab:
            utility_conf = 0.15
            if inbound_count >= 3:
                utility_conf += 0.20
            inst_count = getattr(profile, 'instruction_count', 0)
            if inst_count <= 20:
                utility_conf += 0.10
            if getattr(profile, 'has_loops', False):
                utility_conf -= 0.10
            utility_conf = max(min(utility_conf, 1.0), 0.0)
        
        metrics[bhav_id] = {
            'inbound_call_count': inbound_count,
            'outbound_call_count': outbound_count,
            'is_ttab_entry': is_ttab,
            'inbound_from_main': getattr(profile, 'is_entry_point', False),
            'can_be_action_conf': action_conf,
            'can_be_guard_conf': guard_conf,
            'can_be_utility_conf': utility_conf,
        }
    
    return metrics
