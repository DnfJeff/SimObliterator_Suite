"""
Selection / Focus Coordinator — Single Source of Truth

CRITICAL PLATFORM PIECE:
All panels read from this. Only specific panels mutate it.
Prevents desync between GraphCanvas, Inspectors, Search results.
Makes "jump to" and "highlight everywhere" trivial.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Callable
from enum import Enum


class ResourceType(Enum):
    """Types of resources that can be selected."""
    NONE = "none"
    BHAV = "bhav"
    OBJD = "objd"
    CHUNK = "chunk"
    FILE = "file"
    FAMILY = "family"
    SIM = "sim"
    GRAPH_NODE = "graph_node"


class Scope(Enum):
    """Scope filters for analysis context."""
    ALL = "all"
    OBJECT_ONLY = "object_only"      # Object-specific resources
    GLOBAL_ONLY = "global_only"      # Global.iff resources
    SEMI_GLOBAL = "semi_global"      # Semi-global resources
    NEIGHBORHOOD = "neighborhood"    # Neighborhood/save data


class Context(Enum):
    """Current working context."""
    NONE = "none"
    FILE = "file"          # Working with a single file
    ARCHIVE = "archive"    # Working with FAR archive
    SAVE = "save"          # Working with save data
    GRAPH = "graph"        # Graph exploration mode


@dataclass
class SelectionState:
    """Current selection state."""
    resource_type: ResourceType = ResourceType.NONE
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    resource_data: Optional[Any] = None
    
    # Context
    scope: Scope = Scope.ALL
    context: Context = Context.NONE
    source_panel: Optional[str] = None
    
    # File context
    file_path: Optional[str] = None
    file_type: Optional[str] = None  # IFF, FAR, SAVE


@dataclass  
class HistoryEntry:
    """Navigation history entry."""
    resource_type: ResourceType
    resource_id: Optional[int]
    resource_name: Optional[str]
    source_panel: str
    context: Context


class SelectionCoordinator:
    """
    Central selection/focus coordinator.
    
    All panels subscribe to selection changes.
    Only specific panels (IFFInspector, ChunkInspector, GraphCanvas, Search)
    are allowed to mutate selection.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """Initialize the coordinator."""
        self.current = SelectionState()
        self._subscribers: list[Callable[[SelectionState], None]] = []
        
        # Navigation history
        self._history: list[HistoryEntry] = []
        self._history_index: int = -1
        self._max_history: int = 100
        
        # Scope lock (when user explicitly sets scope)
        self._scope_locked: bool = False
    
    # ─────────────────────────────────────────────────────────────
    # SELECTION API
    # ─────────────────────────────────────────────────────────────
    
    def select(
        self,
        resource_type: ResourceType,
        resource_id: Optional[int] = None,
        resource_name: Optional[str] = None,
        resource_data: Any = None,
        source_panel: str = "unknown",
        add_to_history: bool = True
    ):
        """
        Select a resource. This is the ONLY way to change selection.
        
        Args:
            resource_type: Type of resource being selected
            resource_id: Numeric ID (chunk_id, GUID, etc.)
            resource_name: Human-readable name
            resource_data: The actual resource object
            source_panel: Which panel initiated the selection
            add_to_history: Whether to add to navigation history
        """
        # Update current selection
        self.current.resource_type = resource_type
        self.current.resource_id = resource_id
        self.current.resource_name = resource_name
        self.current.resource_data = resource_data
        self.current.source_panel = source_panel
        
        # Add to history
        if add_to_history and resource_type != ResourceType.NONE:
            self._push_history(HistoryEntry(
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                source_panel=source_panel,
                context=self.current.context
            ))
        
        # Notify all subscribers
        self._notify()
    
    def clear(self):
        """Clear selection."""
        self.select(ResourceType.NONE, source_panel="system", add_to_history=False)
    
    def set_context(self, context: Context, file_path: str = None, file_type: str = None):
        """Set the working context."""
        self.current.context = context
        self.current.file_path = file_path
        self.current.file_type = file_type
        self._notify()
    
    def set_scope(self, scope: Scope, locked: bool = True):
        """
        Set the scope filter.
        
        Args:
            scope: The scope to apply
            locked: If True, scope won't auto-change based on file
        """
        self.current.scope = scope
        self._scope_locked = locked
        self._notify()
    
    def auto_scope(self, filename: str):
        """
        Auto-detect scope from filename (if not locked).
        
        Called by FileLoader/IFFInspector when loading files.
        """
        if self._scope_locked:
            return
        
        lower = filename.lower()
        if 'global' in lower:
            self.current.scope = Scope.GLOBAL_ONLY
        elif 'semi' in lower:
            self.current.scope = Scope.SEMI_GLOBAL
        elif 'neighborhood' in lower or 'userdata' in lower:
            self.current.scope = Scope.NEIGHBORHOOD
        else:
            self.current.scope = Scope.OBJECT_ONLY
    
    # ─────────────────────────────────────────────────────────────
    # SUBSCRIPTION API
    # ─────────────────────────────────────────────────────────────
    
    def subscribe(self, callback: Callable[[SelectionState], None]):
        """Subscribe to selection changes."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[SelectionState], None]):
        """Unsubscribe from selection changes."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def _notify(self):
        """Notify all subscribers of selection change."""
        for cb in self._subscribers:
            try:
                cb(self.current)
            except Exception as e:
                print(f"SelectionCoordinator notify error: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # NAVIGATION HISTORY
    # ─────────────────────────────────────────────────────────────
    
    def _push_history(self, entry: HistoryEntry):
        """Push entry to history, truncating forward history."""
        # Truncate forward history
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]
        
        # Avoid duplicates
        if self._history and self._history[-1].resource_id == entry.resource_id:
            return
        
        self._history.append(entry)
        
        # Limit size
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        self._history_index = len(self._history) - 1
    
    def can_go_back(self) -> bool:
        """Check if back navigation is possible."""
        return self._history_index > 0
    
    def can_go_forward(self) -> bool:
        """Check if forward navigation is possible."""
        return self._history_index < len(self._history) - 1
    
    def go_back(self) -> Optional[HistoryEntry]:
        """Navigate back in history."""
        if not self.can_go_back():
            return None
        
        self._history_index -= 1
        entry = self._history[self._history_index]
        
        # Update selection without adding to history
        self.select(
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            resource_name=entry.resource_name,
            source_panel="history",
            add_to_history=False
        )
        
        return entry
    
    def go_forward(self) -> Optional[HistoryEntry]:
        """Navigate forward in history."""
        if not self.can_go_forward():
            return None
        
        self._history_index += 1
        entry = self._history[self._history_index]
        
        # Update selection without adding to history
        self.select(
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            resource_name=entry.resource_name,
            source_panel="history",
            add_to_history=False
        )
        
        return entry
    
    def get_history(self, limit: int = 20) -> list[HistoryEntry]:
        """Get recent history entries."""
        start = max(0, len(self._history) - limit)
        return self._history[start:]
    
    def get_last_of_type(self, resource_type: ResourceType) -> Optional[HistoryEntry]:
        """Get the last selected resource of a specific type."""
        for entry in reversed(self._history):
            if entry.resource_type == resource_type:
                return entry
        return None
    
    # ─────────────────────────────────────────────────────────────
    # QUERY API
    # ─────────────────────────────────────────────────────────────
    
    def is_selected(self, resource_type: ResourceType, resource_id: int) -> bool:
        """Check if a specific resource is currently selected."""
        return (
            self.current.resource_type == resource_type and
            self.current.resource_id == resource_id
        )
    
    def matches_scope(self, filename: str) -> bool:
        """Check if a filename matches the current scope filter."""
        if self.current.scope == Scope.ALL:
            return True
        
        lower = filename.lower()
        
        if self.current.scope == Scope.GLOBAL_ONLY:
            return 'global' in lower
        elif self.current.scope == Scope.SEMI_GLOBAL:
            return 'semi' in lower
        elif self.current.scope == Scope.OBJECT_ONLY:
            return 'global' not in lower and 'semi' not in lower
        elif self.current.scope == Scope.NEIGHBORHOOD:
            return 'neighborhood' in lower or 'userdata' in lower
        
        return True


# Singleton instance
SELECTION = SelectionCoordinator()
