"""
SimEntity - System-Level Sim Abstraction

A Sim is NOT just bytes in a save file.
A Sim is:
- Identity (name, aspiration)
- Stats (motives, skills, interests)
- Relationships (with other Sims, to objects)
- Location (lot, room, current object)
- History (interactions, memories if applicable)

This entity provides meaning beyond raw save data.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class SimType(Enum):
    """Type of Sim."""
    PLAYABLE = "playable"
    NPC = "npc"
    VISITOR = "visitor"
    UNKNOWN = "unknown"


class MotiveLevel(Enum):
    """Motive status categories."""
    CRITICAL = "critical"   # Dangerously low
    LOW = "low"             # Needs attention
    NEUTRAL = "neutral"     # Acceptable
    GOOD = "good"           # Above average
    FULL = "full"           # Maximum


@dataclass
class Motive:
    """Individual motive state."""
    name: str
    value: int          # Current value
    max_value: int = 100
    decay_rate: float = 1.0
    
    @property
    def level(self) -> MotiveLevel:
        ratio = self.value / self.max_value if self.max_value else 0
        if ratio < 0.15:
            return MotiveLevel.CRITICAL
        elif ratio < 0.35:
            return MotiveLevel.LOW
        elif ratio < 0.55:
            return MotiveLevel.NEUTRAL
        elif ratio < 0.85:
            return MotiveLevel.GOOD
        else:
            return MotiveLevel.FULL


@dataclass
class Skill:
    """Skill level."""
    name: str
    level: int      # 0-10 typically
    max_level: int = 10


@dataclass
class SimRelationship:
    """Relationship to another Sim."""
    other_sim_id: int
    other_sim_name: str = ""
    daily: int = 0
    lifetime: int = 0
    relationship_type: str = "acquaintance"


@dataclass
class SimEntity:
    """
    System-level Sim abstraction.
    
    This provides semantic meaning and relationship
    context for Sim data from saves.
    """
    
    # Identity
    sim_id: int = 0
    first_name: str = ""
    last_name: str = ""
    age: str = "adult"
    
    # Type
    sim_type: SimType = SimType.PLAYABLE
    
    # Location
    lot_id: int = 0
    lot_name: str = ""
    current_room: str = ""
    current_action: str = ""
    
    # Stats
    motives: List[Motive] = field(default_factory=list)
    skills: List[Skill] = field(default_factory=list)
    interests: Dict[str, int] = field(default_factory=dict)
    
    # Relationships
    relationships: List[SimRelationship] = field(default_factory=list)
    household_members: List[int] = field(default_factory=list)
    
    # Misc
    aspiration_points: int = 0
    money: int = 0
    job: str = ""
    job_level: int = 0
    
    # Source tracking
    source_file: str = ""
    
    @classmethod
    def from_save_data(cls, data: Dict[str, Any], 
                       file_path: str = "") -> "SimEntity":
        """
        Build SimEntity from parsed save data.
        
        The exact format depends on save parser implementation.
        This is a template for integration.
        """
        entity = cls(
            sim_id=data.get('id', 0),
            first_name=data.get('first_name', 'Unknown'),
            last_name=data.get('last_name', ''),
            source_file=file_path,
        )
        
        # Parse motives
        motive_data = data.get('motives', {})
        for name, value in motive_data.items():
            entity.motives.append(Motive(name=name, value=value))
        
        # Parse skills
        skill_data = data.get('skills', {})
        for name, level in skill_data.items():
            entity.skills.append(Skill(name=name, level=level))
        
        # Parse relationships
        rel_data = data.get('relationships', [])
        for rel in rel_data:
            entity.relationships.append(SimRelationship(
                other_sim_id=rel.get('sim_id', 0),
                other_sim_name=rel.get('name', ''),
                daily=rel.get('daily', 0),
                lifetime=rel.get('lifetime', 0),
            ))
        
        return entity
    
    # ─────────────────────────────────────────────────────────────
    # QUERY METHODS
    # ─────────────────────────────────────────────────────────────
    
    @property
    def full_name(self) -> str:
        """Full display name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    def get_critical_motives(self) -> List[Motive]:
        """Get motives that need urgent attention."""
        return [m for m in self.motives if m.level == MotiveLevel.CRITICAL]
    
    def get_low_motives(self) -> List[Motive]:
        """Get motives that are low but not critical."""
        return [m for m in self.motives if m.level == MotiveLevel.LOW]
    
    def get_motive_summary(self) -> str:
        """Summary of motive status."""
        critical = self.get_critical_motives()
        low = self.get_low_motives()
        
        if critical:
            names = [m.name for m in critical]
            return f"⛔ CRITICAL: {', '.join(names)}"
        elif low:
            names = [m.name for m in low]
            return f"⚠ Low: {', '.join(names)}"
        else:
            return "✓ All motives stable"
    
    def get_top_skills(self, n: int = 3) -> List[Skill]:
        """Get top N skills."""
        sorted_skills = sorted(self.skills, key=lambda s: s.level, reverse=True)
        return sorted_skills[:n]
    
    def get_skill_summary(self) -> str:
        """Summary of skill levels."""
        if not self.skills:
            return "No skills"
        
        top = self.get_top_skills(3)
        parts = [f"{s.name}:{s.level}" for s in top]
        return ", ".join(parts)
    
    def get_relationship_summary(self) -> str:
        """Summary of relationships."""
        if not self.relationships:
            return "No relationships"
        
        friends = [r for r in self.relationships if r.daily >= 50]
        enemies = [r for r in self.relationships if r.daily <= -50]
        
        parts = []
        if friends:
            parts.append(f"{len(friends)} friends")
        if enemies:
            parts.append(f"{len(enemies)} enemies")
        
        total = len(self.relationships)
        parts.append(f"{total} total")
        
        return ", ".join(parts)
    
    def get_friends(self) -> List[SimRelationship]:
        """Get positive relationships."""
        return [r for r in self.relationships if r.daily >= 50]
    
    def get_enemies(self) -> List[SimRelationship]:
        """Get negative relationships."""
        return [r for r in self.relationships if r.daily <= -50]
    
    def get_summary(self) -> str:
        """
        Complete human-readable summary.
        
        PERFECT for CC creators and modders!
        """
        lines = []
        
        # Header
        lines.append(f"╔═══ {self.full_name} ═══")
        
        # Type & Location
        lines.append(f"║ Type: {self.sim_type.value}")
        if self.lot_name:
            lines.append(f"║ Location: {self.lot_name}")
        if self.current_action:
            lines.append(f"║ Action: {self.current_action}")
        
        # Stats summary
        lines.append(f"║ Motives: {self.get_motive_summary()}")
        lines.append(f"║ Skills: {self.get_skill_summary()}")
        lines.append(f"║ Relationships: {self.get_relationship_summary()}")
        
        # Career
        if self.job:
            lines.append(f"║ Career: {self.job} (Level {self.job_level})")
        
        lines.append(f"╚{'═' * 30}")
        
        return "\n".join(lines)
    
    def __repr__(self):
        return f"SimEntity(id={self.sim_id}, name='{self.full_name}')"
