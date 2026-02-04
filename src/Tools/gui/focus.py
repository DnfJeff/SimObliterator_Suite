"""
Focus Coordinator - Single Source of Truth for Selection & Navigation

From the Flow Map:
- Current resource (ID + type)
- Current scope (object, global, semi-global)
- Current context (file, graph, save)
- Navigation history with back/forward

All panels read from here. Only selection actions mutate.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, List
from enum import Enum


class Scope(Enum):
    """Scope filter for global consistency."""
    ALL = "all"
    OBJECT_ONLY = "object"
    GLOBAL_ONLY = "global"
    SEMI_GLOBAL = "semi-global"


class Context(Enum):
    """Current working context."""
    FILE = "file"           # Viewing/editing a file
    GRAPH = "graph"         # Exploring relationships
    SAVE = "save"           # Editing save data
    SEARCH = "search"       # Search results
    COMPARE = "compare"     # Diff view


@dataclass
class SelectionEntry:
    """A single selection in the navigation history."""
    resource_type: str      # BHAV, OBJD, SPR2, etc.
    resource_id: int        # Chunk ID or GUID
    label: str              # Human-readable name
    source_panel: str       # Where the selection came from
    file_path: Optional[str] = None
    extra: dict = field(default_factory=dict)


class FocusCoordinator:
    """
    Central selection and navigation manager.
    
    Solves:
    - Desync between GraphCanvas, Inspectors, Search
    - "Jump to" and "highlight everywhere"
    - Back/Forward navigation
    - Scope filtering
    """
    
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        
        # Current selection
        self._current: Optional[SelectionEntry] = None
        
        # Navigation history
        self._history: List[SelectionEntry] = []
        self._history_index: int = -1
        
        # Scope & Context
        self._scope: Scope = Scope.ALL
        self._context: Context = Context.FILE
        
        # Subscribers for selection changes
        self._subscribers: list = []
    
    # ─────────────────────────────────────────────────────────────
    # SELECTION
    # ─────────────────────────────────────────────────────────────
    
    @property
    def current(self) -> Optional[SelectionEntry]:
        """Get current selection."""
        return self._current
    
    def select(self, resource_type: str, resource_id: int, label: str, 
               source_panel: str, file_path: str = None, **extra):
        """
        Select a resource. This is THE way to change focus.
        
        - Adds to history
        - Notifies all subscribers
        - Updates scope context if needed
        """
        entry = SelectionEntry(
            resource_type=resource_type,
            resource_id=resource_id,
            label=label,
            source_panel=source_panel,
            file_path=file_path,
            extra=extra
        )
        
        # Don't add duplicate consecutive entries
        if self._current and self._same_selection(self._current, entry):
            return
        
        # Truncate forward history if we're not at the end
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]
        
        # Add to history
        self._history.append(entry)
        if len(self._history) > self.max_history:
            self._history.pop(0)
        
        self._history_index = len(self._history) - 1
        self._current = entry
        
        # Auto-detect scope from resource type
        self._infer_scope(entry)
        
        # Notify subscribers
        self._notify(entry)
    
    def _same_selection(self, a: SelectionEntry, b: SelectionEntry) -> bool:
        """Check if two selections are the same."""
        return (a.resource_type == b.resource_type and 
                a.resource_id == b.resource_id and
                a.file_path == b.file_path)
    
    def _infer_scope(self, entry: SelectionEntry):
        """Infer scope from resource context."""
        if entry.file_path:
            path_lower = entry.file_path.lower()
            if 'global' in path_lower:
                self._scope = Scope.GLOBAL_ONLY
            elif 'semi' in path_lower:
                self._scope = Scope.SEMI_GLOBAL
            else:
                self._scope = Scope.OBJECT_ONLY
    
    # ─────────────────────────────────────────────────────────────
    # NAVIGATION HISTORY
    # ─────────────────────────────────────────────────────────────
    
    def can_go_back(self) -> bool:
        """Check if back navigation is possible."""
        return self._history_index > 0
    
    def can_go_forward(self) -> bool:
        """Check if forward navigation is possible."""
        return self._history_index < len(self._history) - 1
    
    def go_back(self) -> Optional[SelectionEntry]:
        """Navigate back in history."""
        if not self.can_go_back():
            return None
        
        self._history_index -= 1
        self._current = self._history[self._history_index]
        self._notify(self._current)
        return self._current
    
    def go_forward(self) -> Optional[SelectionEntry]:
        """Navigate forward in history."""
        if not self.can_go_forward():
            return None
        
        self._history_index += 1
        self._current = self._history[self._history_index]
        self._notify(self._current)
        return self._current
    
    def get_history(self, limit: int = 10) -> List[SelectionEntry]:
        """Get recent history entries."""
        start = max(0, len(self._history) - limit)
        return self._history[start:]
    
    def jump_to_history(self, index: int) -> Optional[SelectionEntry]:
        """Jump to a specific history entry."""
        if 0 <= index < len(self._history):
            self._history_index = index
            self._current = self._history[index]
            self._notify(self._current)
            return self._current
        return None
    
    # ─────────────────────────────────────────────────────────────
    # SCOPE & CONTEXT
    # ─────────────────────────────────────────────────────────────
    
    @property
    def scope(self) -> Scope:
        """Get current scope filter."""
        return self._scope
    
    @scope.setter
    def scope(self, value: Scope):
        """Set scope filter."""
        self._scope = value
        # Notify scope change (use None to indicate scope-only change)
        for cb in self._subscribers:
            try:
                cb(None, scope_changed=True)
            except TypeError:
                pass  # Callback doesn't accept scope_changed
    
    @property
    def context(self) -> Context:
        """Get current context."""
        return self._context
    
    @context.setter
    def context(self, value: Context):
        """Set context."""
        self._context = value
    
    def matches_scope(self, resource_path: str) -> bool:
        """Check if a resource matches the current scope filter."""
        if self._scope == Scope.ALL:
            return True
        
        path_lower = resource_path.lower() if resource_path else ""
        
        if self._scope == Scope.GLOBAL_ONLY:
            return 'global' in path_lower
        elif self._scope == Scope.SEMI_GLOBAL:
            return 'semi' in path_lower
        elif self._scope == Scope.OBJECT_ONLY:
            return 'global' not in path_lower and 'semi' not in path_lower
        
        return True
    
    # ─────────────────────────────────────────────────────────────
    # SUBSCRIPTIONS
    # ─────────────────────────────────────────────────────────────
    
    def subscribe(self, callback):
        """Subscribe to selection changes."""
        self._subscribers.append(callback)
    
    def unsubscribe(self, callback):
        """Unsubscribe from selection changes."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def _notify(self, entry: SelectionEntry):
        """Notify all subscribers of selection change."""
        for cb in self._subscribers:
            try:
                cb(entry)
            except Exception as e:
                print(f"FocusCoordinator notify error: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────────────────────
    
    def clear(self):
        """Clear all history and selection."""
        self._current = None
        self._history.clear()
        self._history_index = -1
    
    def get_last_of_type(self, resource_type: str) -> Optional[SelectionEntry]:
        """Get the last selected resource of a specific type."""
        for entry in reversed(self._history):
            if entry.resource_type == resource_type:
                return entry
        return None


# Singleton instance
FOCUS = FocusCoordinator()
