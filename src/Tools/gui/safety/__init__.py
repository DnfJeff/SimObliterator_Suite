"""
Safety systems for SimObliterator.

This module provides blast-radius control, edit scoping,
snapshot/restore functionality, and user-friendly warnings.

Philosophy: Every powerful action needs:
- Scope visibility
- Reversibility
- Explanation
"""

from .edit_mode import EditMode, EditModeManager, MODE_MANAGER
from .scope_tracker import ScopeTracker, EditScope, SCOPE
from .snapshots import SnapshotManager, ChunkSnapshot, SNAPSHOTS
from .help_system import HelpSystem, HELP

__all__ = [
    'EditMode',
    'EditModeManager',
    'MODE_MANAGER',
    'ScopeTracker',
    'EditScope',
    'SCOPE',
    'SnapshotManager',
    'ChunkSnapshot',
    'SNAPSHOTS',
    'HelpSystem',
    'HELP',
]
