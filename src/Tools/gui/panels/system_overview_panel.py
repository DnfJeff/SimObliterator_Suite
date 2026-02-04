"""
System Overview Panel - "What Am I Looking At?"

From Architectural Principles:
  There must be a "what am I looking at?" panel.
  
This is the FIRST thing users see. Orientation surface.
Shows at a glance:
- Loaded packs & files
- Object / BHAV / Chunk counts  
- Unknowns encountered
- Safety status
- Current selection context
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE
from ..focus import FocusCoordinator


class SystemOverviewPanel:
    """
    System Overview - The orientation surface.
    
    Users see this first to understand:
    - What's loaded
    - What's selected
    - What's the safety status
    - What needs attention
    """
    
    TAG = "system_overview"
    STATS_TAG = "overview_stats"
    SELECTION_TAG = "overview_selection"
    ALERTS_TAG = "overview_alerts"
    
    def __init__(self, width: int = 300, height: int = 400, pos: tuple = (10, 10)):
        self.width = width
        self.height = height
        self.pos = pos
        self.stats = {
            'files_loaded': 0,
            'objects': 0,
            'behaviors': 0,
            'chunks': 0,
            'unknowns': 0,
        }
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the overview panel."""
        with dpg.window(
            label="📊 System Overview",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            no_close=True,  # Always visible
        ):
            # Header
            dpg.add_text("SimObliterator Suite", color=(0, 212, 255, 255))
            dpg.add_text("System-Aware Sims 1 Explorer", color=(136, 136, 136, 255))
            dpg.add_separator()
            
            # Stats section
            with dpg.collapsing_header(label="📈 Statistics", default_open=True):
                with dpg.group(tag=self.STATS_TAG):
                    self._render_stats()
            
            # Current Selection section
            with dpg.collapsing_header(label="🎯 Current Selection", default_open=True):
                with dpg.group(tag=self.SELECTION_TAG):
                    dpg.add_text("Nothing selected", color=(136, 136, 136, 255))
            
            # Alerts section
            with dpg.collapsing_header(label="⚠️ Alerts", default_open=True):
                with dpg.group(tag=self.ALERTS_TAG):
                    dpg.add_text("No alerts", color=(76, 175, 80, 255))
            
            # Quick Actions
            with dpg.collapsing_header(label="⚡ Quick Actions", default_open=False):
                dpg.add_button(
                    label="Open File...",
                    width=-1,
                    callback=lambda: EventBus.publish("command.open_file", None)
                )
                dpg.add_button(
                    label="Browse Library",
                    width=-1,
                    callback=lambda: EventBus.publish("command.show_library", None)
                )
                dpg.add_button(
                    label="Global Search",
                    width=-1,
                    callback=lambda: EventBus.publish("command.show_search", None)
                )
                dpg.add_button(
                    label="View Unknowns",
                    width=-1,
                    callback=lambda: EventBus.publish("command.show_unknowns", None)
                )
    
    def _subscribe_events(self):
        """Subscribe to state changes."""
        EventBus.subscribe(Events.FILE_LOADED, self._on_file_loaded)
        EventBus.subscribe(Events.CHUNK_SELECTED, self._on_selection_changed)
        EventBus.subscribe(Events.BHAV_SELECTED, self._on_selection_changed)
    
    def _render_stats(self):
        """Render statistics display."""
        dpg.delete_item(self.STATS_TAG, children_only=True)
        
        with dpg.group(parent=self.STATS_TAG):
            # File stats
            dpg.add_text("Loaded Files:", color=(200, 200, 200, 255))
            
            if STATE.current_iff_name:
                dpg.add_text(f"  📁 {STATE.current_iff_name}", color=(0, 212, 255, 255))
            else:
                dpg.add_text("  (none)", color=(136, 136, 136, 255))
            
            dpg.add_spacer(height=5)
            
            # Chunk counts
            if STATE.current_iff and hasattr(STATE.current_iff, 'chunks'):
                chunks = STATE.current_iff.chunks
                
                # Count by type
                by_type = {}
                for chunk in chunks:
                    t = chunk.chunk_type
                    by_type[t] = by_type.get(t, 0) + 1
                
                dpg.add_text(f"Chunks: {len(chunks)}", color=(200, 200, 200, 255))
                
                # Key types
                for chunk_type in ['OBJD', 'BHAV', 'TTAB', 'STR#', 'SPR2']:
                    count = by_type.get(chunk_type, 0)
                    if count:
                        color = self._get_type_color(chunk_type)
                        dpg.add_text(f"  {chunk_type}: {count}", color=color)
                
                # Others
                other_count = sum(v for k, v in by_type.items() 
                                  if k not in ['OBJD', 'BHAV', 'TTAB', 'STR#', 'SPR2'])
                if other_count:
                    dpg.add_text(f"  Other: {other_count}", color=(136, 136, 136, 255))
                
                self.stats['chunks'] = len(chunks)
                self.stats['objects'] = by_type.get('OBJD', 0)
                self.stats['behaviors'] = by_type.get('BHAV', 0)
            else:
                dpg.add_text("Chunks: 0", color=(136, 136, 136, 255))
            
            dpg.add_spacer(height=5)
            
            # Unknowns count
            unknowns = self._get_unknowns_count()
            if unknowns > 0:
                dpg.add_text(f"⚠️ Unknowns: {unknowns}", color=(255, 193, 7, 255))
            else:
                dpg.add_text("✓ No unknowns", color=(76, 175, 80, 255))
    
    def _get_type_color(self, chunk_type: str) -> tuple:
        """Get color for chunk type."""
        colors = {
            'OBJD': (76, 175, 80, 255),     # Green
            'BHAV': (233, 69, 96, 255),     # Red
            'TTAB': (255, 193, 7, 255),     # Yellow
            'STR#': (156, 39, 176, 255),    # Purple
            'SPR2': (0, 188, 212, 255),     # Cyan
        }
        return colors.get(chunk_type, (200, 200, 200, 255))
    
    def _get_unknowns_count(self) -> int:
        """Get count of unknown opcodes/chunks encountered."""
        try:
            from core.unknowns_db import get_unknowns_db
            db = get_unknowns_db()
            if db:
                return len(db.get_all_unknowns())
        except:
            pass
        return 0
    
    def _on_file_loaded(self, filepath):
        """Handle file loaded event."""
        self._render_stats()
        self._update_alerts()
    
    def _on_selection_changed(self, data):
        """Handle selection change."""
        dpg.delete_item(self.SELECTION_TAG, children_only=True)
        
        with dpg.group(parent=self.SELECTION_TAG):
            focus = FocusCoordinator.get()
            current = focus.current
            
            if current:
                dpg.add_text(f"Type: {current.resource_type}", color=(0, 212, 255, 255))
                dpg.add_text(f"ID: {current.resource_id}", color=(200, 200, 200, 255))
                if current.label:
                    dpg.add_text(f"Label: {current.label}", color=(200, 200, 200, 255))
                dpg.add_text(f"Source: {current.source_panel}", color=(136, 136, 136, 255))
                
                # Show scope
                dpg.add_text(f"Scope: {focus.scope.value}", color=(136, 136, 136, 255))
                dpg.add_text(f"Context: {focus.context.value}", color=(136, 136, 136, 255))
            else:
                dpg.add_text("Nothing selected", color=(136, 136, 136, 255))
            
            # History
            history = focus.get_history()
            if len(history) > 1:
                dpg.add_separator()
                dpg.add_text(f"History: {len(history)} items", color=(136, 136, 136, 255))
    
    def _update_alerts(self):
        """Update alerts section."""
        dpg.delete_item(self.ALERTS_TAG, children_only=True)
        
        alerts = []
        
        # Check for unknowns
        unknowns = self._get_unknowns_count()
        if unknowns > 0:
            alerts.append(("⚠️", f"{unknowns} unknown opcodes", (255, 193, 7, 255)))
        
        # Check mutation mode
        try:
            from Tools.core.mutation_pipeline import get_pipeline, MutationMode
            pipeline = get_pipeline()
            if pipeline.mode == MutationMode.MUTATE:
                alerts.append(("✏️", "Write mode ENABLED", (255, 152, 0, 255)))
            elif pipeline.mode == MutationMode.PREVIEW:
                alerts.append(("👁", "Preview mode", (0, 188, 212, 255)))
        except:
            pass
        
        # Check for modified files
        if hasattr(STATE, 'modified_files') and STATE.modified_files:
            count = len(STATE.modified_files)
            alerts.append(("💾", f"{count} unsaved changes", (255, 87, 34, 255)))
        
        with dpg.group(parent=self.ALERTS_TAG):
            if alerts:
                for icon, text, color in alerts:
                    dpg.add_text(f"{icon} {text}", color=color)
            else:
                dpg.add_text("✓ All clear", color=(76, 175, 80, 255))
    
    def refresh(self):
        """Force refresh of all sections."""
        self._render_stats()
        self._on_selection_changed(None)
        self._update_alerts()
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
