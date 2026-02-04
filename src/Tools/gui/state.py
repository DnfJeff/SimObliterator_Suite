"""
Global application state.
Single source of truth for the UI.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from pathlib import Path


@dataclass
class AppState:
    """Global application state container."""
    
    # Loaded data
    current_file: Optional[Path] = None
    current_file_type: Optional[str] = None  # "IFF", "FAR", "SAVE"
    current_far: Optional[Any] = None
    current_iff: Optional[Any] = None
    current_bhav: Optional[Any] = None
    current_chunk: Optional[Any] = None
    
    # Engine & Semantic (from flow map)
    engine_toolkit: Optional[Any] = None
    semantic_db: Optional[Any] = None
    graph_model: Optional[Any] = None
    
    # Current selection (resource ID + type)
    current_resource_id: Optional[int] = None
    current_resource_type: Optional[str] = None  # "BHAV", "OBJD", "SPR2", etc.
    
    # Logs (append-only)
    logs: list = field(default_factory=list)
    
    # Paths
    game_path: str = r"G:\SteamLibrary\steamapps\common\The Sims Legacy Collection"
    save_path: str = r"C:\Users\jeffe\Saved Games\Electronic Arts\The Sims 25"
    current_far_path: Optional[str] = None
    current_iff_name: Optional[str] = None
    
    # UI state
    handler_counter: int = 0
    
    def get_unique_tag(self, prefix: str = "item") -> str:
        """Generate a unique tag for DPG items."""
        self.handler_counter += 1
        return f"{prefix}_{self.handler_counter}"
    
    def set_file(self, file_path: Path, file_type: str):
        """Set current file (IFF/FAR/SAVE)."""
        self.current_file = file_path
        self.current_file_type = file_type
        # Clear downstream state
        self.current_iff = None
        self.current_iff_name = None
        self.current_bhav = None
        self.current_chunk = None
    
    def set_far(self, far_archive: Any, path: str):
        """Set current FAR archive."""
        self.current_far = far_archive
        self.current_far_path = path
        # Clear downstream state
        self.current_iff = None
        self.current_iff_name = None
        self.current_bhav = None
        self.current_chunk = None
    
    def set_iff(self, iff_file: Any, name: str):
        """Set current IFF file."""
        self.current_iff = iff_file
        self.current_iff_name = name
        # Clear downstream state
        self.current_bhav = None
        self.current_chunk = None
    def set_chunk(self, chunk: Any):
        """Set current chunk."""
        self.current_chunk = chunk
        # If it's a BHAV, also set current_bhav
        if hasattr(chunk, 'instructions'):
            self.current_bhav = chunk
    
    def set_resource(self, resource_id: int, resource_type: str):
        """Set current resource selection (for graph/search navigation)."""
        self.current_resource_id = resource_id
        self.current_resource_type = resource_type
    
    def log(self, message: str, level: str = "INFO"):
        """Add log entry (from flow map: Log panel reads this)."""
        import time
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message
        }
        self.logs.append(entry)
        # Keep last 1000 entries
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]
    
    def clear(self):
        """Clear all state."""
        self.current_far = None
        self.current_far_path = None
        self.current_iff = None
        self.current_iff_name = None
        self.current_bhav = None
        self.current_chunk = None
        self.current_resource_id = None
        self.current_resource_type = None


# Singleton instance
STATE = AppState()
