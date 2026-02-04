"""
Edit Scope Tracker.

Tracks what's being edited and calculates blast radius.
Provides always-visible scope indicators.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Any
from pathlib import Path


class ScopeLevel(Enum):
    """Edit scope levels, from safest to most dangerous."""
    NONE = auto()           # Nothing selected
    SINGLE_CHUNK = auto()   # Single chunk in single object
    SINGLE_OBJECT = auto()  # Single object's BHAVs
    SEMI_GLOBAL = auto()    # Semi-global (affects multiple objects)
    GLOBAL = auto()         # Global.iff (affects everything)


@dataclass
class EditScope:
    """Represents the current editing scope and its blast radius."""
    
    level: ScopeLevel = ScopeLevel.NONE
    
    # Current selection path (breadcrumb)
    far_file: Optional[str] = None
    iff_file: Optional[str] = None
    chunk_type: Optional[str] = None
    chunk_id: Optional[int] = None
    chunk_label: Optional[str] = None
    instruction_index: Optional[int] = None
    
    # Blast radius info
    affected_objects: list[str] = field(default_factory=list)
    affected_count: int = 0
    is_semi_global: bool = False
    is_global: bool = False
    
    # Confidence info for BHAV classification
    classification: Optional[str] = None  # ROLE, FLOW, ACTION, GUARD, etc.
    confidence: float = 0.0
    confidence_reason: str = ""
    
    def get_breadcrumb(self) -> str:
        """Get breadcrumb navigation string."""
        parts = []
        
        if self.far_file:
            parts.append(Path(self.far_file).name)
        
        if self.iff_file:
            parts.append(self.iff_file)
        
        if self.chunk_type and self.chunk_id is not None:
            label = self.chunk_label or "(unnamed)"
            parts.append(f"{self.chunk_type} #{self.chunk_id}: {label}")
        
        if self.instruction_index is not None:
            parts.append(f"Instruction {self.instruction_index}")
        
        return " → ".join(parts) if parts else "Nothing selected"
    
    def get_scope_display(self) -> tuple[str, tuple]:
        """
        Get the scope banner text and color.
        
        Returns:
            Tuple of (display_text, rgba_color)
        """
        if self.level == ScopeLevel.NONE:
            return ("No selection", (150, 150, 150, 255))
        
        if self.is_global:
            return (
                "⚠️ GLOBAL - Affects entire game",
                (255, 100, 100, 255)
            )
        
        if self.is_semi_global:
            count = self.affected_count or len(self.affected_objects)
            return (
                f"⚠️ SEMI-GLOBAL - Affects {count} objects",
                (255, 180, 100, 255)
            )
        
        if self.level == ScopeLevel.SINGLE_OBJECT:
            return (
                f"📦 This object only",
                (100, 180, 255, 255)
            )
        
        if self.level == ScopeLevel.SINGLE_CHUNK:
            return (
                f"📄 Single chunk",
                (100, 220, 150, 255)
            )
        
        return ("Unknown scope", (150, 150, 150, 255))
    
    def get_confidence_display(self) -> tuple[str, tuple]:
        """Get confidence display text and color."""
        if not self.classification:
            return ("", (150, 150, 150, 255))
        
        if self.confidence >= 0.8:
            color = (100, 220, 100, 255)  # Green - high confidence
            level = "High"
        elif self.confidence >= 0.5:
            color = (220, 200, 100, 255)  # Yellow - medium
            level = "Medium"
        else:
            color = (220, 150, 100, 255)  # Orange - low
            level = "Low"
        
        return (
            f"{level} confidence: {self.classification}",
            color
        )


class ScopeTracker:
    """
    Tracks and calculates edit scope and blast radius.
    
    This is the source of truth for what the user is looking at
    and what would be affected by edits.
    """
    
    def __init__(self):
        self._scope = EditScope()
        self._scope_callbacks: list = []
        
        # Known semi-global patterns (from FreeSO research)
        self._semi_global_patterns = {
            "Social",
            "Relationship",
            "Autonomy",
            "Routing",
            "Posture",
            "Cooking",
            "Repair",
        }
    
    @property
    def scope(self) -> EditScope:
        """Get current scope."""
        return self._scope
    
    def on_scope_change(self, callback):
        """Register callback for scope changes."""
        self._scope_callbacks.append(callback)
    
    def _notify_scope_change(self):
        """Notify all callbacks of scope change."""
        for cb in self._scope_callbacks:
            try:
                cb(self._scope)
            except Exception as e:
                print(f"Scope callback error: {e}")
    
    def set_far(self, far_path: str):
        """Set FAR file context."""
        self._scope = EditScope(
            level=ScopeLevel.NONE,
            far_file=far_path
        )
        self._notify_scope_change()
    
    def set_iff(self, iff_name: str, is_global: bool = False):
        """Set IFF file context."""
        self._scope.iff_file = iff_name
        self._scope.is_global = is_global or iff_name.lower() in ("global.iff", "global")
        
        if self._scope.is_global:
            self._scope.level = ScopeLevel.GLOBAL
        else:
            self._scope.level = ScopeLevel.SINGLE_OBJECT
        
        # Clear deeper selections
        self._scope.chunk_type = None
        self._scope.chunk_id = None
        self._scope.chunk_label = None
        self._scope.instruction_index = None
        
        self._notify_scope_change()
    
    def set_chunk(self, chunk_type: str, chunk_id: int, chunk_label: str = None):
        """Set chunk context."""
        self._scope.chunk_type = chunk_type
        self._scope.chunk_id = chunk_id
        self._scope.chunk_label = chunk_label
        self._scope.instruction_index = None
        
        # Check for semi-global indicators
        self._check_semi_global(chunk_label)
        
        if self._scope.is_global:
            self._scope.level = ScopeLevel.GLOBAL
        elif self._scope.is_semi_global:
            self._scope.level = ScopeLevel.SEMI_GLOBAL
        else:
            self._scope.level = ScopeLevel.SINGLE_CHUNK
        
        self._notify_scope_change()
    
    def set_instruction(self, index: int):
        """Set instruction context within current BHAV."""
        self._scope.instruction_index = index
        self._notify_scope_change()
    
    def set_classification(self, classification: str, confidence: float, reason: str = ""):
        """Set BHAV classification info."""
        self._scope.classification = classification
        self._scope.confidence = confidence
        self._scope.confidence_reason = reason
        self._notify_scope_change()
    
    def set_affected_objects(self, objects: list[str]):
        """Set list of objects affected by current selection."""
        self._scope.affected_objects = objects
        self._scope.affected_count = len(objects)
        self._notify_scope_change()
    
    def _check_semi_global(self, label: str):
        """Check if current selection appears to be a semi-global."""
        if not label:
            return
        
        label_lower = label.lower()
        
        # Check known semi-global patterns
        for pattern in self._semi_global_patterns:
            if pattern.lower() in label_lower:
                self._scope.is_semi_global = True
                return
        
        # Check for semi-global GUID ranges (if we have that info)
        # TODO: Integrate with GUID database
        
        self._scope.is_semi_global = False
    
    def clear(self):
        """Clear all scope info."""
        self._scope = EditScope()
        self._notify_scope_change()
    
    def get_scope_type_for_edit(self) -> str:
        """Get scope type string for edit mode warnings."""
        if self._scope.is_global:
            return "global"
        if self._scope.is_semi_global:
            return "semi_global"
        return "normal"


# Singleton instance
SCOPE = ScopeTracker()
