"""
Provenance Model - Confidence & Source Attribution

From Architectural Principles:
  Every fact should be able to say how sure we are.
  SimObliterator never hides uncertainty.

Provenance Model:
- source: Where did this information come from?
- confidence: How sure are we?

This is metadata-only - no UI explosion required.
Attach to any semantic fact for transparency.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Dict
from enum import Enum
from datetime import datetime


class ProvenanceSource(Enum):
    """Where did this information come from?"""
    
    OBSERVED = "observed"       # Direct parse from game files
    INFERRED = "inferred"       # Derived from patterns/heuristics
    DERIVED = "derived"         # Computed from other facts
    EXTERNAL = "external"       # From external documentation (FreeSO, etc.)
    USER = "user"               # User-provided annotation
    UNKNOWN = "unknown"         # Source not tracked


class ConfidenceLevel(Enum):
    """How sure are we about this fact?"""
    
    HIGH = "high"           # Direct observation, verified
    MEDIUM = "medium"       # Strong inference, likely correct
    LOW = "low"             # Heuristic guess, may be wrong
    UNKNOWN = "unknown"     # No confidence data


@dataclass
class Provenance:
    """
    Provenance metadata for any semantic fact.
    
    Attach this to:
    - Semantic BHAV names
    - Opcode descriptions
    - Behavior classifications
    - Safety assessments
    - Cross-pack inferences
    """
    
    source: ProvenanceSource = ProvenanceSource.UNKNOWN
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    
    # Optional details
    source_file: str = ""           # Where was this observed?
    source_reference: str = ""      # Documentation reference
    derivation_method: str = ""     # How was this inferred?
    timestamp: Optional[datetime] = None
    
    # For tracking changes
    previous_value: Optional[Any] = None
    change_reason: str = ""
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    # ─────────────────────────────────────────────────────────────
    # DISPLAY
    # ─────────────────────────────────────────────────────────────
    
    def badge(self) -> str:
        """Get a compact badge for UI display."""
        badges = {
            ConfidenceLevel.HIGH: "✓",
            ConfidenceLevel.MEDIUM: "~",
            ConfidenceLevel.LOW: "?",
            ConfidenceLevel.UNKNOWN: "⚠",
        }
        return badges.get(self.confidence, "⚠")
    
    def color(self) -> tuple:
        """Get color for confidence display (RGBA)."""
        colors = {
            ConfidenceLevel.HIGH: (76, 175, 80, 255),      # Green
            ConfidenceLevel.MEDIUM: (255, 193, 7, 255),    # Yellow
            ConfidenceLevel.LOW: (255, 152, 0, 255),       # Orange
            ConfidenceLevel.UNKNOWN: (158, 158, 158, 255), # Gray
        }
        return colors.get(self.confidence, (158, 158, 158, 255))
    
    def summary(self) -> str:
        """Get human-readable summary."""
        parts = [f"{self.badge()} {self.confidence.value}"]
        
        if self.source != ProvenanceSource.UNKNOWN:
            parts.append(f"({self.source.value})")
        
        if self.derivation_method:
            parts.append(f"- {self.derivation_method}")
        
        return " ".join(parts)
    
    def full_explanation(self) -> str:
        """Get detailed explanation for tooltips."""
        lines = [f"Confidence: {self.confidence.value}"]
        lines.append(f"Source: {self.source.value}")
        
        if self.source_file:
            lines.append(f"File: {self.source_file}")
        if self.source_reference:
            lines.append(f"Reference: {self.source_reference}")
        if self.derivation_method:
            lines.append(f"Method: {self.derivation_method}")
        if self.timestamp:
            lines.append(f"Recorded: {self.timestamp.isoformat()}")
        
        return "\n".join(lines)
    
    # ─────────────────────────────────────────────────────────────
    # FACTORIES
    # ─────────────────────────────────────────────────────────────
    
    @classmethod
    def observed(cls, source_file: str = "") -> "Provenance":
        """Create provenance for directly observed fact."""
        return cls(
            source=ProvenanceSource.OBSERVED,
            confidence=ConfidenceLevel.HIGH,
            source_file=source_file,
        )
    
    @classmethod
    def inferred(cls, method: str = "") -> "Provenance":
        """Create provenance for inferred fact."""
        return cls(
            source=ProvenanceSource.INFERRED,
            confidence=ConfidenceLevel.MEDIUM,
            derivation_method=method,
        )
    
    @classmethod
    def from_freeso(cls, reference: str = "") -> "Provenance":
        """Create provenance for FreeSO-sourced fact."""
        return cls(
            source=ProvenanceSource.EXTERNAL,
            confidence=ConfidenceLevel.HIGH,
            source_reference=f"FreeSO: {reference}" if reference else "FreeSO",
        )
    
    @classmethod
    def guessed(cls, reason: str = "") -> "Provenance":
        """Create provenance for low-confidence guess."""
        return cls(
            source=ProvenanceSource.INFERRED,
            confidence=ConfidenceLevel.LOW,
            derivation_method=f"Heuristic: {reason}" if reason else "Heuristic guess",
        )
    
    @classmethod
    def unknown(cls) -> "Provenance":
        """Create provenance for unknown source."""
        return cls(
            source=ProvenanceSource.UNKNOWN,
            confidence=ConfidenceLevel.UNKNOWN,
        )


@dataclass
class ProvenancedFact:
    """
    A fact with attached provenance.
    
    Use this to wrap any value that needs confidence tracking.
    """
    
    value: Any
    provenance: Provenance = field(default_factory=Provenance.unknown)
    
    def display(self) -> str:
        """Display value with confidence badge."""
        return f"{self.provenance.badge()} {self.value}"
    
    def is_reliable(self) -> bool:
        """Is this fact reliable enough to trust?"""
        return self.provenance.confidence in (
            ConfidenceLevel.HIGH, 
            ConfidenceLevel.MEDIUM
        )
    
    def needs_verification(self) -> bool:
        """Does this fact need human verification?"""
        return self.provenance.confidence in (
            ConfidenceLevel.LOW,
            ConfidenceLevel.UNKNOWN
        )


# ─────────────────────────────────────────────────────────────────
# PROVENANCE REGISTRY
# ─────────────────────────────────────────────────────────────────

class ProvenanceRegistry:
    """
    Global registry for provenance metadata.
    
    Stores provenance for semantic facts by key.
    Keys are typically: "bhav:0x1234" or "opcode:0x42"
    """
    
    _instance = None
    
    def __init__(self):
        self._registry: Dict[str, Provenance] = {}
    
    @classmethod
    def instance(cls) -> "ProvenanceRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set(self, key: str, provenance: Provenance):
        """Set provenance for a key."""
        self._registry[key] = provenance
    
    def get_provenance(self, key: str) -> Provenance:
        """Get provenance for a key, or unknown if not set."""
        return self._registry.get(key, Provenance.unknown())
    
    def has(self, key: str) -> bool:
        """Check if key has provenance."""
        return key in self._registry
    
    def clear(self):
        """Clear all provenance data."""
        self._registry.clear()
    
    # Convenience methods for common key patterns
    
    def set_bhav(self, bhav_id: int, provenance: Provenance):
        """Set provenance for a BHAV semantic name."""
        self.set(f"bhav:0x{bhav_id:04X}", provenance)
    
    def get_bhav(self, bhav_id: int) -> Provenance:
        """Get provenance for a BHAV semantic name."""
        return self.get_provenance(f"bhav:0x{bhav_id:04X}")
    
    def set_opcode(self, opcode: int, provenance: Provenance):
        """Set provenance for an opcode description."""
        self.set(f"opcode:0x{opcode:02X}", provenance)
    
    def get_opcode(self, opcode: int) -> Provenance:
        """Get provenance for an opcode description."""
        return self.get_provenance(f"opcode:0x{opcode:02X}")
    
    # Alias for semantic API compatibility
    def register(self, resource_type: str, resource_id: int, provenance: Provenance):
        """
        Register provenance for a resource.
        
        Alias for set() with type:id key format.
        """
        key = f"{resource_type.lower()}:0x{resource_id:04X}"
        self.set(key, provenance)
    
    def get(self, resource_type: str, resource_id: int) -> Optional[Provenance]:
        """
        Get provenance for a resource.
        
        Returns None if not found.
        """
        key = f"{resource_type.lower()}:0x{resource_id:04X}"
        if self.has(key):
            return self.get_provenance(key)
        return None


# Convenience function
def get_provenance_registry() -> ProvenanceRegistry:
    """Get the global provenance registry."""
    return ProvenanceRegistry.instance()
