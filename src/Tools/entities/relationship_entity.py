"""
RelationshipEntity - Dependency & Connection Abstraction

A Relationship is the CONNECTION between entities.
It answers the critical question:
  "What depends on this?"
  "If I change X, what breaks?"

This is the GRAPH foundation for:
- Object dependency graphs
- BHAV call chains
- Resource references
- Mod conflict detection
"""

from dataclasses import dataclass, field
from typing import Optional, List, Set, Any, Dict, Tuple
from enum import Enum


class RelationType(Enum):
    """Type of relationship between entities."""
    
    # BHAV relationships
    CALLS = "calls"             # BHAV A calls BHAV B
    CALLED_BY = "called_by"     # BHAV B is called by BHAV A
    
    # Object relationships
    USES = "uses"               # Object uses global BHAV
    OWNS = "owns"               # Object owns private BHAV
    SPAWNS = "spawns"           # Object spawns another object
    DEPENDS_ON = "depends_on"   # General dependency
    
    # Resource relationships
    REFERENCES = "references"   # Chunk references another
    INCLUDES = "includes"       # Container includes resource
    OVERRIDES = "overrides"     # Mod overrides original
    
    # Sim relationships
    KNOWS = "knows"             # Sim knows another Sim
    FAMILY = "family"           # Family relationship
    INTERACTS = "interacts"     # Sim interacts with object


class RiskLevel(Enum):
    """Risk level for modifying this relationship."""
    SAFE = "safe"           # Can modify freely
    CAUTION = "caution"     # Be careful
    WARNING = "warning"     # Likely to break things
    DANGEROUS = "dangerous" # Will break things


@dataclass
class Relationship:
    """
    A single relationship between two entities.
    """
    
    # Source entity
    source_type: str = ""       # 'object', 'bhav', 'sim', 'chunk'
    source_id: Any = None       # ID of source
    source_name: str = ""       # Display name
    source_file: str = ""       # File containing source
    
    # Target entity  
    target_type: str = ""
    target_id: Any = None
    target_name: str = ""
    target_file: str = ""
    
    # Relationship
    relation: RelationType = RelationType.DEPENDS_ON
    strength: int = 1           # How strong (used for sorting)
    
    # Risk
    risk: RiskLevel = RiskLevel.SAFE
    risk_reason: str = ""
    
    def get_display(self) -> str:
        """Human-readable relationship."""
        return f"{self.source_name} {self.relation.value} {self.target_name}"
    
    def invert(self) -> "Relationship":
        """Get the inverse relationship."""
        inverse_map = {
            RelationType.CALLS: RelationType.CALLED_BY,
            RelationType.CALLED_BY: RelationType.CALLS,
            RelationType.USES: RelationType.DEPENDS_ON,
            RelationType.SPAWNS: RelationType.DEPENDS_ON,
        }
        
        return Relationship(
            source_type=self.target_type,
            source_id=self.target_id,
            source_name=self.target_name,
            source_file=self.target_file,
            target_type=self.source_type,
            target_id=self.source_id,
            target_name=self.source_name,
            target_file=self.source_file,
            relation=inverse_map.get(self.relation, RelationType.DEPENDS_ON),
            strength=self.strength,
            risk=self.risk,
        )


@dataclass
class RelationshipGraph:
    """
    Complete relationship graph for dependency analysis.
    
    This is the "What depends on this?" engine.
    """
    
    # All relationships
    relationships: List[Relationship] = field(default_factory=list)
    
    # Indexes for fast lookup
    _by_source: Dict[Tuple[str, Any], List[Relationship]] = field(
        default_factory=dict, repr=False
    )
    _by_target: Dict[Tuple[str, Any], List[Relationship]] = field(
        default_factory=dict, repr=False
    )
    
    def add(self, rel: Relationship):
        """Add a relationship."""
        self.relationships.append(rel)
        
        # Index by source
        key = (rel.source_type, rel.source_id)
        if key not in self._by_source:
            self._by_source[key] = []
        self._by_source[key].append(rel)
        
        # Index by target
        key = (rel.target_type, rel.target_id)
        if key not in self._by_target:
            self._by_target[key] = []
        self._by_target[key].append(rel)
    
    # ─────────────────────────────────────────────────────────────
    # THE CRITICAL QUESTION: "What depends on this?"
    # ─────────────────────────────────────────────────────────────
    
    def what_depends_on(self, entity_type: str, entity_id: Any) -> List[Relationship]:
        """
        Get everything that depends on this entity.
        
        This is the ANSWER to "If I change this, what breaks?"
        """
        key = (entity_type, entity_id)
        return self._by_target.get(key, [])
    
    def what_does_this_depend_on(self, entity_type: str, entity_id: Any) -> List[Relationship]:
        """
        Get everything this entity depends on.
        
        Answers: "What does this need to work?"
        """
        key = (entity_type, entity_id)
        return self._by_source.get(key, [])
    
    # ─────────────────────────────────────────────────────────────
    # TRANSITIVE ANALYSIS
    # ─────────────────────────────────────────────────────────────
    
    def get_dependency_chain(self, entity_type: str, entity_id: Any,
                             depth: int = 10) -> List[Relationship]:
        """
        Get full dependency chain (transitive closure).
        
        Follows: A → B → C → ...
        """
        seen: Set[Tuple[str, Any]] = set()
        result: List[Relationship] = []
        
        def visit(etype: str, eid: Any, current_depth: int):
            if current_depth <= 0:
                return
            key = (etype, eid)
            if key in seen:
                return
            seen.add(key)
            
            for rel in self._by_source.get(key, []):
                result.append(rel)
                visit(rel.target_type, rel.target_id, current_depth - 1)
        
        visit(entity_type, entity_id, depth)
        return result
    
    def get_dependents_chain(self, entity_type: str, entity_id: Any,
                             depth: int = 10) -> List[Relationship]:
        """
        Get everything that depends on this, transitively.
        
        Answers: "What ALL breaks if I change this?"
        """
        seen: Set[Tuple[str, Any]] = set()
        result: List[Relationship] = []
        
        def visit(etype: str, eid: Any, current_depth: int):
            if current_depth <= 0:
                return
            key = (etype, eid)
            if key in seen:
                return
            seen.add(key)
            
            for rel in self._by_target.get(key, []):
                result.append(rel)
                visit(rel.source_type, rel.source_id, current_depth - 1)
        
        visit(entity_type, entity_id, depth)
        return result
    
    # ─────────────────────────────────────────────────────────────
    # RISK ANALYSIS
    # ─────────────────────────────────────────────────────────────
    
    def assess_change_risk(self, entity_type: str, entity_id: Any) -> Dict[str, Any]:
        """
        Assess risk of modifying an entity.
        
        Returns:
        - risk_level: Overall risk
        - dependent_count: How many things depend on this
        - affected_files: Which files would be affected
        - summary: Human-readable summary
        """
        dependents = self.get_dependents_chain(entity_type, entity_id)
        
        if not dependents:
            return {
                'risk_level': RiskLevel.SAFE,
                'dependent_count': 0,
                'affected_files': [],
                'summary': "✓ Nothing depends on this, safe to modify"
            }
        
        # Collect affected files
        affected_files = set()
        for rel in dependents:
            if rel.source_file:
                affected_files.add(rel.source_file)
        
        # Determine risk level
        count = len(dependents)
        if count > 20:
            risk = RiskLevel.DANGEROUS
        elif count > 10:
            risk = RiskLevel.WARNING
        elif count > 3:
            risk = RiskLevel.CAUTION
        else:
            risk = RiskLevel.SAFE
        
        return {
            'risk_level': risk,
            'dependent_count': count,
            'affected_files': list(affected_files),
            'summary': f"⚠ {count} entities depend on this across {len(affected_files)} files"
        }
    
    # ─────────────────────────────────────────────────────────────
    # BUILDERS
    # ─────────────────────────────────────────────────────────────
    
    @classmethod
    def from_bhav_analysis(cls, object_entity: Any) -> "RelationshipGraph":
        """
        Build relationship graph from an ObjectEntity's behaviors.
        """
        graph = cls()
        
        behaviors = getattr(object_entity, 'behaviors', [])
        
        for bhav in behaviors:
            bhav_id = getattr(bhav, 'bhav_id', 0)
            name = getattr(bhav, 'name', f'BHAV #{bhav_id}')
            calls = getattr(bhav, 'calls', [])
            
            for target_id in calls:
                graph.add(Relationship(
                    source_type='bhav',
                    source_id=bhav_id,
                    source_name=name,
                    target_type='bhav',
                    target_id=target_id,
                    target_name=f'BHAV 0x{target_id:04X}',
                    relation=RelationType.CALLS,
                ))
        
        return graph
    
    # ─────────────────────────────────────────────────────────────
    # DISPLAY
    # ─────────────────────────────────────────────────────────────
    
    def get_summary(self) -> str:
        """Summary of the graph."""
        return f"RelationshipGraph: {len(self.relationships)} relationships"
    
    def get_stats(self) -> Dict[str, int]:
        """Statistics about the graph."""
        by_type: Dict[RelationType, int] = {}
        for rel in self.relationships:
            by_type[rel.relation] = by_type.get(rel.relation, 0) + 1
        
        return {
            'total': len(self.relationships),
            'by_type': {k.value: v for k, v in by_type.items()},
        }
