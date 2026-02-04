"""
Entity Abstractions - System-Level Thinking

From Conceptual Directives:
- Users are working with game systems, not files
- Files are containers, chunks are representations
- Meaning lives at the system level

Core Entities:
- ObjectEntity: Aggregates OBJD + BHAVs + Sprites
- BehaviorEntity: BHAV with semantic context  
- SimEntity: Sim data from saves
- RelationshipEntity: Dependencies between entities
- RelationshipGraph: The "What depends on this?" engine

Supporting Types:
- BehaviorScope, BehaviorPurpose: BHAV classification
- SimType, Motive, Skill: Sim data structures
- RelationType, RiskLevel, Relationship: Graph edges
"""

# Core Entities
from .object_entity import ObjectEntity, CatalogInfo
from .behavior_entity import BehaviorEntity, BehaviorScope, BehaviorPurpose
from .sim_entity import (
    SimEntity, SimType, Motive, MotiveLevel, 
    Skill, SimRelationship
)
from .relationship_entity import (
    RelationshipGraph, Relationship,
    RelationType, RiskLevel
)

__all__ = [
    # Core Entities
    "ObjectEntity",
    "BehaviorEntity", 
    "SimEntity",
    "RelationshipGraph",
    
    # Object types
    "CatalogInfo",
    
    # Behavior types
    "BehaviorScope",
    "BehaviorPurpose",
    
    # Sim types
    "SimType",
    "Motive",
    "MotiveLevel", 
    "Skill",
    "SimRelationship",
    
    # Relationship types
    "Relationship",
    "RelationType",
    "RiskLevel",
]
