"""
Workspace Persistence - Workspace State Save/Load Operations

Implements ACTION_SURFACE actions for workspace persistence.

Actions Implemented:
- LoadWorkspace (READ) - Load workspace state from JSON
- SaveWorkspace (WRITE) - Save workspace state to JSON
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from Tools.core.mutation_pipeline import (
    MutationPipeline, MutationMode, MutationDiff, 
    MutationResult, get_pipeline, propose_change
)
from Tools.core.action_registry import validate_action


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WorkspaceResult:
    """Result of a workspace operation."""
    success: bool
    message: str
    workspace_path: Optional[str] = None
    data: Optional[Dict] = None


# ═══════════════════════════════════════════════════════════════════════════════
# WORKSPACE STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RecentFile:
    """Recent file entry."""
    path: str
    last_opened: str
    file_type: str = "iff"
    pinned: bool = False


@dataclass
class SelectionState:
    """Selection state."""
    file_path: Optional[str] = None
    chunk_type: Optional[str] = None
    chunk_id: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None


@dataclass
class PanelLayout:
    """Panel layout state."""
    panel_id: str
    visible: bool = True
    position: str = "left"  # left, right, center, bottom
    width: int = 300
    height: int = 400
    collapsed: bool = False


@dataclass
class WorkspaceState:
    """Complete workspace state for persistence."""
    # Metadata
    version: str = "1.0"
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    last_saved: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Recent files
    recent_files: List[Dict] = field(default_factory=list)
    max_recent: int = 20
    
    # Current selection
    selection: Dict = field(default_factory=dict)
    
    # Panel layouts
    panel_layouts: List[Dict] = field(default_factory=list)
    
    # Preferences
    preferences: Dict = field(default_factory=lambda: {
        'theme': 'dark',
        'font_size': 12,
        'auto_save': True,
        'auto_backup': True,
        'confirm_writes': True,
        'show_hex': True,
        'show_semantic_names': True,
        'pipeline_mode': 'INSPECT',
    })
    
    # Opened files (paths)
    open_files: List[str] = field(default_factory=list)
    
    # Bookmarks
    bookmarks: List[Dict] = field(default_factory=list)
    
    # Search history
    search_history: List[str] = field(default_factory=list)
    max_search_history: int = 50
    
    # Custom data (for extensions)
    custom_data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "WorkspaceState":
        """Create from dictionary."""
        # Handle defaults for missing fields
        state = cls()
        for key, value in data.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state


# ═══════════════════════════════════════════════════════════════════════════════
# WORKSPACE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class WorkspaceManager:
    """
    Manage workspace state persistence.
    
    Implements LoadWorkspace, SaveWorkspace actions.
    """
    
    DEFAULT_FILENAME = ".simobliterator_workspace.json"
    
    _instance = None
    
    def __init__(self, workspace_dir: str = None):
        """
        Initialize workspace manager.
        
        Args:
            workspace_dir: Directory for workspace file
        """
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path.cwd()
        self._state = WorkspaceState()
        self._dirty = False
        self._loaded_from = None
    
    @classmethod
    def get(cls, workspace_dir: str = None) -> "WorkspaceManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(workspace_dir)
        return cls._instance
    
    @property
    def state(self) -> WorkspaceState:
        """Get current workspace state."""
        return self._state
    
    @property
    def is_dirty(self) -> bool:
        """Check if state has unsaved changes."""
        return self._dirty
    
    # ─── Load Operations ──────────────────────────────────────────────────────
    
    def load_workspace(self, file_path: str = None) -> WorkspaceResult:
        """
        Load workspace state from JSON file.
        
        Args:
            file_path: Path to workspace file (default: .simobliterator_workspace.json)
            
        Returns:
            WorkspaceResult
        """
        valid, msg = validate_action('LoadWorkspace', {
            'pipeline_mode': get_pipeline().mode.value
        })
        
        if not valid:
            return WorkspaceResult(False, f"Action blocked: {msg}")
        
        if file_path is None:
            file_path = self.workspace_dir / self.DEFAULT_FILENAME
        else:
            file_path = Path(file_path)
        
        if not file_path.exists():
            # Create default state
            self._state = WorkspaceState()
            self._loaded_from = str(file_path)
            return WorkspaceResult(
                True,
                "No workspace file found, using defaults",
                workspace_path=str(file_path),
                data=self._state.to_dict()
            )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._state = WorkspaceState.from_dict(data)
            self._loaded_from = str(file_path)
            self._dirty = False
            
            return WorkspaceResult(
                True,
                f"Loaded workspace from {file_path.name}",
                workspace_path=str(file_path),
                data=self._state.to_dict()
            )
            
        except json.JSONDecodeError as e:
            return WorkspaceResult(False, f"Invalid JSON: {e}")
        except Exception as e:
            return WorkspaceResult(False, f"Load failed: {e}")
    
    # ─── Save Operations ──────────────────────────────────────────────────────
    
    def save_workspace(self, file_path: str = None,
                       reason: str = "") -> WorkspaceResult:
        """
        Save workspace state to JSON file.
        
        Args:
            file_path: Path to save to (default: .simobliterator_workspace.json)
            reason: Reason for save
            
        Returns:
            WorkspaceResult
        """
        valid, msg = validate_action('SaveWorkspace', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True
        })
        
        if not valid:
            return WorkspaceResult(False, f"Action blocked: {msg}")
        
        if file_path is None:
            if self._loaded_from:
                file_path = Path(self._loaded_from)
            else:
                file_path = self.workspace_dir / self.DEFAULT_FILENAME
        else:
            file_path = Path(file_path)
        
        # Update last saved time
        self._state.last_saved = datetime.now().isoformat()
        
        diffs = [MutationDiff(
            field_path='workspace',
            old_value=self._loaded_from or '(none)',
            new_value=str(file_path),
            display_old='Previous state',
            display_new=f"Save to {file_path.name}"
        )]
        
        audit = propose_change(
            target_type='workspace',
            target_id='workspace_state',
            diffs=diffs,
            file_path=str(file_path),
            reason=reason or "Save workspace state"
        )
        
        if audit.result == MutationResult.SUCCESS:
            try:
                # Ensure directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self._state.to_dict(), f, indent=2)
                
                self._dirty = False
                self._loaded_from = str(file_path)
                
                return WorkspaceResult(
                    True,
                    f"Saved workspace to {file_path.name}",
                    workspace_path=str(file_path),
                    data=self._state.to_dict()
                )
                
            except Exception as e:
                return WorkspaceResult(False, f"Save failed: {e}")
                
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return WorkspaceResult(
                True,
                f"Preview: would save to {file_path.name}",
                workspace_path=str(file_path)
            )
        else:
            return WorkspaceResult(False, f"SaveWorkspace rejected: {audit.result.value}")
    
    # ─── Recent Files ─────────────────────────────────────────────────────────
    
    def add_recent_file(self, file_path: str, file_type: str = "iff"):
        """Add a file to recent files list."""
        # Remove if already exists
        self._state.recent_files = [
            rf for rf in self._state.recent_files 
            if rf.get('path') != file_path
        ]
        
        # Add to front
        self._state.recent_files.insert(0, {
            'path': file_path,
            'last_opened': datetime.now().isoformat(),
            'file_type': file_type,
            'pinned': False
        })
        
        # Trim to max (keeping pinned)
        pinned = [rf for rf in self._state.recent_files if rf.get('pinned')]
        unpinned = [rf for rf in self._state.recent_files if not rf.get('pinned')]
        max_unpinned = self._state.max_recent - len(pinned)
        self._state.recent_files = pinned + unpinned[:max_unpinned]
        
        self._dirty = True
    
    def get_recent_files(self) -> List[Dict]:
        """Get recent files list."""
        return self._state.recent_files.copy()
    
    def pin_recent_file(self, file_path: str, pinned: bool = True):
        """Pin/unpin a recent file."""
        for rf in self._state.recent_files:
            if rf.get('path') == file_path:
                rf['pinned'] = pinned
                self._dirty = True
                break
    
    def clear_recent_files(self, keep_pinned: bool = True):
        """Clear recent files."""
        if keep_pinned:
            self._state.recent_files = [
                rf for rf in self._state.recent_files if rf.get('pinned')
            ]
        else:
            self._state.recent_files = []
        self._dirty = True
    
    # ─── Selection State ──────────────────────────────────────────────────────
    
    def set_selection(self, **kwargs):
        """Set current selection state."""
        self._state.selection = {
            'file_path': kwargs.get('file_path'),
            'chunk_type': kwargs.get('chunk_type'),
            'chunk_id': kwargs.get('chunk_id'),
            'entity_type': kwargs.get('entity_type'),
            'entity_id': kwargs.get('entity_id'),
        }
        self._dirty = True
    
    def get_selection(self) -> Dict:
        """Get current selection state."""
        return self._state.selection.copy()
    
    # ─── Panel Layouts ────────────────────────────────────────────────────────
    
    def set_panel_layout(self, panel_id: str, **kwargs):
        """Set a panel's layout."""
        # Find existing or create
        layout = None
        for pl in self._state.panel_layouts:
            if pl.get('panel_id') == panel_id:
                layout = pl
                break
        
        if layout is None:
            layout = {'panel_id': panel_id}
            self._state.panel_layouts.append(layout)
        
        # Update fields
        for key, value in kwargs.items():
            if key in ('visible', 'position', 'width', 'height', 'collapsed'):
                layout[key] = value
        
        self._dirty = True
    
    def get_panel_layout(self, panel_id: str) -> Optional[Dict]:
        """Get a panel's layout."""
        for pl in self._state.panel_layouts:
            if pl.get('panel_id') == panel_id:
                return pl.copy()
        return None
    
    # ─── Preferences ──────────────────────────────────────────────────────────
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        return self._state.preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any):
        """Set a preference value."""
        self._state.preferences[key] = value
        self._dirty = True
    
    # ─── Bookmarks ────────────────────────────────────────────────────────────
    
    def add_bookmark(self, name: str, file_path: str, 
                     chunk_type: str = None, chunk_id: int = None):
        """Add a bookmark."""
        self._state.bookmarks.append({
            'name': name,
            'file_path': file_path,
            'chunk_type': chunk_type,
            'chunk_id': chunk_id,
            'created': datetime.now().isoformat()
        })
        self._dirty = True
    
    def remove_bookmark(self, name: str):
        """Remove a bookmark by name."""
        self._state.bookmarks = [
            b for b in self._state.bookmarks if b.get('name') != name
        ]
        self._dirty = True
    
    def get_bookmarks(self) -> List[Dict]:
        """Get all bookmarks."""
        return self._state.bookmarks.copy()
    
    # ─── Search History ───────────────────────────────────────────────────────
    
    def add_search(self, query: str):
        """Add a search to history."""
        # Remove if exists
        if query in self._state.search_history:
            self._state.search_history.remove(query)
        
        # Add to front
        self._state.search_history.insert(0, query)
        
        # Trim
        self._state.search_history = self._state.search_history[:self._state.max_search_history]
        self._dirty = True
    
    def get_search_history(self) -> List[str]:
        """Get search history."""
        return self._state.search_history.copy()
    
    def clear_search_history(self):
        """Clear search history."""
        self._state.search_history = []
        self._dirty = True
    
    # ─── Custom Data ──────────────────────────────────────────────────────────
    
    def set_custom_data(self, namespace: str, key: str, value: Any):
        """Set custom data (for extensions)."""
        if namespace not in self._state.custom_data:
            self._state.custom_data[namespace] = {}
        self._state.custom_data[namespace][key] = value
        self._dirty = True
    
    def get_custom_data(self, namespace: str, key: str, default: Any = None) -> Any:
        """Get custom data."""
        return self._state.custom_data.get(namespace, {}).get(key, default)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_workspace(file_path: str = None) -> WorkspaceResult:
    """Load workspace state. Convenience function."""
    return WorkspaceManager.get().load_workspace(file_path)


def save_workspace(file_path: str = None, reason: str = "") -> WorkspaceResult:
    """Save workspace state. Convenience function."""
    return WorkspaceManager.get().save_workspace(file_path, reason)


def get_workspace_manager() -> WorkspaceManager:
    """Get the workspace manager singleton."""
    return WorkspaceManager.get()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # State classes
    'WorkspaceState', 'RecentFile', 'SelectionState', 'PanelLayout',
    
    # Manager
    'WorkspaceManager', 'get_workspace_manager',
    
    # Convenience functions
    'load_workspace', 'save_workspace',
    
    # Result type
    'WorkspaceResult',
]
