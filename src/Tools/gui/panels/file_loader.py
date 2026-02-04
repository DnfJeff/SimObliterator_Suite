"""
File Loader Panel - Entry Point

Styled after library_browser.html design.
Colors: #00d4ff (cyan), #1a1a2e-#16213e (dark gradient), #e0e0e0 (text)
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE
from ..theme import Colors


class FileLoaderPanel:
    """File loader panel - browse and load IFF/FAR/Save files."""
    
    TAG = "file_loader"
    FILE_LIST_TAG = "file_loader_list"
    SEARCH_INPUT_TAG = "file_loader_search"
    RECENT_TABLE_TAG = "file_loader_recent"
    STATS_TAG = "file_loader_stats"
    
    def __init__(self, width: int = 350, height: int = 550, pos: tuple = (10, 30)):
        self.width = width
        self.height = height
        self.pos = pos
        self.recent_files = []
        self._create_file_dialogs()
        self._create_panel()
        self._subscribe_events()
    
    def _create_file_dialogs(self):
        """Create file dialogs for IFF and FAR files."""
        # IFF file dialog
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_iff_selected,
            tag="file_loader_iff_dialog",
            width=700,
            height=450,
            default_path=str(STATE.game_path) if STATE.game_path else "",
            modal=True
        ):
            dpg.add_file_extension(".iff", color=(0, 212, 255, 255))
            dpg.add_file_extension(".IFF", color=(0, 212, 255, 255))
            dpg.add_file_extension(".*")
        
        # FAR file dialog
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_far_selected,
            tag="file_loader_far_dialog",
            width=700,
            height=450,
            default_path=str(STATE.game_path) if STATE.game_path else "",
            modal=True
        ):
            dpg.add_file_extension(".far", color=(76, 175, 80, 255))
            dpg.add_file_extension(".FAR", color=(76, 175, 80, 255))
            dpg.add_file_extension(".*")
        
        # Save file dialog
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_save_selected,
            tag="file_loader_save_dialog",
            width=700,
            height=450,
            default_path=str(STATE.save_path) if STATE.save_path else "",
            modal=True
        ):
            dpg.add_file_extension(".iff", color=(255, 152, 0, 255))
            dpg.add_file_extension(".IFF", color=(255, 152, 0, 255))
            dpg.add_file_extension(".*")
    
    def _create_panel(self):
        """Create the file loader panel."""
        with dpg.window(
            label="Project / File Loader",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            # Header section
            dpg.add_text("SimObliterator", color=(0, 212, 255, 255), tag=self.STATS_TAG)
            dpg.add_text("v1.0 - File Loader", color=(136, 136, 136, 255))
            
            dpg.add_separator()
            
            # Load buttons - styled like HTML design
            with dpg.group():
                # Row 1: IFF, FAR, Save buttons
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Load IFF",
                        width=98,
                        height=40,
                        callback=lambda: dpg.show_item("file_loader_iff_dialog")
                    )
                    dpg.add_button(
                        label="Load FAR",
                        width=98,
                        height=40,
                        callback=lambda: dpg.show_item("file_loader_far_dialog")
                    )
                    dpg.add_button(
                        label="Load Save",
                        width=98,
                        height=40,
                        callback=lambda: dpg.show_item("file_loader_save_dialog")
                    )
                
                dpg.add_spacer(height=5)
                
                # Directory browser
                dpg.add_button(
                    label="📁 Browse Directory",
                    width=310,
                    height=35,
                    callback=self._on_browse_directory
                )
                
                dpg.add_spacer(height=5)
                
                # Clear/Refresh row
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Clear Project",
                        width=150,
                        height=30,
                        callback=self._on_clear_project
                    )
                    dpg.add_button(
                        label="Refresh",
                        width=150,
                        height=30,
                        callback=self._on_refresh
                    )
            
            dpg.add_separator()
            
            # Session info
            dpg.add_text("Session Context", color=(0, 212, 255, 255))
            with dpg.group():
                dpg.add_text(
                    "Current: [None]",
                    tag="session_current",
                    color=(224, 224, 224, 255)
                )
                dpg.add_text(
                    "Type: -",
                    tag="session_type",
                    color=(136, 136, 136, 255)
                )
                dpg.add_text(
                    "Size: -",
                    tag="session_size",
                    color=(136, 136, 136, 255)
                )
            
            dpg.add_separator()
            
            # Search box
            dpg.add_text("Find Files", color=(0, 212, 255, 255))
            dpg.add_input_text(
                tag=self.SEARCH_INPUT_TAG,
                width=330,
                hint="Search by name or ID...",
                callback=self._on_search
            )
            
            dpg.add_separator()
            
            # Recent files
            dpg.add_text("Recent Files", color=(0, 212, 255, 255))
            dpg.add_listbox(
                items=["(No recent files)"],
                tag=self.RECENT_TABLE_TAG,
                num_items=8,
                width=330,
                callback=self._on_recent_selected
            )
    
    def _subscribe_events(self):
        """Subscribe to app events."""
        EventBus.subscribe(Events.FILE_LOADED, self._on_file_loaded_event)
    
    def _on_iff_selected(self, sender, app_data):
        """Handle IFF file selection."""
        file_path = Path(app_data["file_path"])
        self._load_file(file_path, "IFF")
    
    def _on_far_selected(self, sender, app_data):
        """Handle FAR file selection."""
        file_path = Path(app_data["file_path"])
        self._load_file(file_path, "FAR")
    
    def _on_save_selected(self, sender, app_data):
        """Handle Save file selection."""
        file_path = Path(app_data["file_path"])
        self._load_file(file_path, "SAVE")
    
    def _on_browse_directory(self):
        """Open directory browser."""
        # TODO: Implement directory browser
        print("Browse directory clicked")
    
    def _on_clear_project(self):
        """Clear current project."""
        STATE.current_file = None
        self._update_session_display()
        EventBus.publish(Events.FILE_CLEARED)
        print("Project cleared")
    
    def _on_refresh(self):
        """Refresh current file."""
        if STATE.current_file:
            self._load_file(STATE.current_file, STATE.current_file_type)
    
    def _on_search(self, sender, value):
        """Handle search input."""
        if not value.strip():
            self._update_recent_list()
        else:
            # TODO: Implement search
            print(f"Search for: {value}")
    
    def _on_recent_selected(self, sender, value):
        """Handle recent file selection."""
        if value and value != "(No recent files)":
            # Find and load the file
            matching = [f for f in self.recent_files if str(f) == value]
            if matching:
                file_path = matching[0]
                # Determine type by extension
                ext = file_path.suffix.lower()
                if ext == ".iff":
                    file_type = "IFF"
                elif ext == ".far":
                    file_type = "FAR"
                else:
                    file_type = "SAVE"
                self._load_file(file_path, file_type)
    
    def _load_file(self, file_path, file_type):
        """Load a file and update state."""
        try:
            STATE.current_file = file_path
            STATE.current_file_type = file_type
            
            # Add to recent if not already there
            if file_path not in self.recent_files:
                self.recent_files.insert(0, file_path)
                self.recent_files = self.recent_files[:10]  # Keep 10 most recent
            
            self._update_session_display()
            
            # Publish file loaded event
            EventBus.publish(Events.FILE_LOADED, {
                "file_path": file_path,
                "file_type": file_type
            })
            
            print(f"Loaded {file_type}: {file_path.name}")
        except Exception as e:
            print(f"Error loading file: {e}")
    
    def _update_session_display(self):
        """Update session context display."""
        if STATE.current_file:
            size_mb = STATE.current_file.stat().st_size / (1024 * 1024)
            dpg.set_value("session_current", f"Current: {STATE.current_file.name}")
            dpg.set_value("session_type", f"Type: {STATE.current_file_type}")
            dpg.set_value("session_size", f"Size: {size_mb:.2f} MB")
        else:
            dpg.set_value("session_current", "Current: [None]")
            dpg.set_value("session_type", "Type: -")
            dpg.set_value("session_size", "Size: -")
        
        self._update_recent_list()
    
    def _update_recent_list(self):
        """Update recent files listbox."""
        items = [str(f.name) for f in self.recent_files] if self.recent_files else ["(No recent files)"]
        dpg.configure_item(self.RECENT_TABLE_TAG, items=items)
    
    def _on_file_loaded_event(self, data):
        """Handle file loaded event."""
        self._update_session_display()
    
    def _on_close(self):
        """Handle panel close."""
        EventBus.unsubscribe(Events.FILE_LOADED, self._on_file_loaded_event)
    
    @staticmethod
    def instance():
        """Get singleton instance."""
        return FileLoaderPanel()
