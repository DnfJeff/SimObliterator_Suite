"""
FAR Archive Browser Panel.
Browse and load .far archives from The Sims.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from formats.far.far1 import FAR1Archive
from ..events import EventBus, Events
from ..state import STATE
from ..theme import Colors


class FARBrowserPanel:
    """FAR archive browser panel."""
    
    TAG = "far_browser"
    FILE_DIALOG_TAG = "far_file_dialog"
    FILE_LIST_TAG = "far_file_list"
    
    def __init__(self, width: int = 280, height: int = 450, pos: tuple = (10, 30)):
        self.width = width
        self.height = height
        self.pos = pos
        self._create_file_dialog()
        self._create_panel()
        self._subscribe_events()
    
    def _subscribe_events(self):
        """Subscribe to file load events (from flow map)."""
        EventBus.subscribe(Events.FILE_LOADED, self._on_file_loaded)
    
    def _on_file_loaded(self, data):
        """Handle file loaded - switch to FAR browser if FAR file loaded."""
        if STATE.current_file_type == "FAR" and STATE.current_far:
            self._populate_far_entries()
    
    def _create_file_dialog(self):
        """Create the file dialog for opening FAR archives."""
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_file_selected,
            tag=self.FILE_DIALOG_TAG,
            width=700,
            height=450,
            default_path=STATE.game_path,
            modal=True
        ):
            dpg.add_file_extension(".far", color=(100, 255, 100, 255))
            dpg.add_file_extension(".FAR", color=(100, 255, 100, 255))
            dpg.add_file_extension(".*")        
        # Create IFF file dialog (separate)
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_iff_file_selected,
            tag="iff_file_dialog",
            width=700,
            height=450,
            default_path=STATE.game_path,
            modal=True
        ):
            dpg.add_file_extension(".iff", color=(150, 200, 255, 255))
            dpg.add_file_extension(".IFF", color=(150, 200, 255, 255))
            dpg.add_file_extension(".*")    
    def _create_panel(self):
        """Create the panel window."""
        with dpg.window(
            label="FAR Browser",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            dpg.add_button(
                label="Open FAR Archive...",
                callback=self._browse_clicked,
                width=-1
            )
            dpg.add_separator()
            
            with dpg.child_window(tag=self.FILE_LIST_TAG, border=False):
                dpg.add_text("No archive loaded", color=(136, 136, 136, 255))
    
    def _on_close(self):
        """Handle panel close - just hide, don't delete."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel (called from View menu)."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
    
    def _browse_clicked(self):
        """Handle browse button click."""
        dpg.show_item(self.FILE_DIALOG_TAG)
    
    def _on_file_selected(self, sender, app_data):
        """Handle file selection from dialog."""
        filepath = app_data.get('file_path_name', '')
        if not filepath:
            return
        
        try:
            far_archive = FAR1Archive(filepath)
            STATE.set_far(far_archive, filepath)
            
            # Update scope tracker
            try:
                from ..safety import SCOPE
                SCOPE.set_far(filepath)
            except ImportError:
                pass
            
            EventBus.publish(Events.STATUS_UPDATE, 
                f"Loaded: {Path(filepath).name} ({STATE.current_far.num_files} files)")
            EventBus.publish(Events.FAR_LOADED, STATE.current_far)
            self._refresh_file_list()
        except Exception as e:
            EventBus.publish(Events.STATUS_UPDATE, f"Error: {e}")
    
    def _refresh_file_list(self):
        """Refresh the file list display."""
        dpg.delete_item(self.FILE_LIST_TAG, children_only=True)
        
        if STATE.current_far is None:
            dpg.add_text("No archive loaded", parent=self.FILE_LIST_TAG, color=Colors.TEXT_DIM)
            return
        
        # Separate IFF files from others
        iff_files = []
        other_files = []
        
        for entry in STATE.current_far.entries:
            if entry.filename.lower().endswith('.iff'):
                iff_files.append(entry)
            else:
                other_files.append(entry)
        
        # IFF files section
        if iff_files:
            with dpg.tree_node(
                label=f"IFF Files ({len(iff_files)})",
                parent=self.FILE_LIST_TAG,
                default_open=True
            ):
                for entry in iff_files:
                    dpg.add_button(
                        label=f"  {entry.filename}",
                        width=-1,
                        callback=lambda s, a, e=entry: self._on_iff_clicked(e)
                    )
        
        # Other files section
        if other_files:
            with dpg.tree_node(
                label=f"Other Files ({len(other_files)})",
                parent=self.FILE_LIST_TAG
            ):
                for entry in other_files:
                    dpg.add_text(f"  {entry.filename}", color=Colors.TEXT_DIM)
    
    def _on_iff_file_selected(self, sender, app_data):
        """Handle IFF file selection from dialog (direct load)."""
        filepath = app_data.get('file_path_name', '')
        if not filepath:
            return
        
        try:
            from formats.iff.iff_file import IffFile
            
            with open(filepath, 'rb') as f:
                data = f.read()
            
            filename = Path(filepath).name
            iff_file = IffFile.from_bytes(data, filename)
            STATE.set_iff(iff_file, filename)
            
            # Update scope tracker
            try:
                from ..safety import SCOPE
                is_global = 'global' in filename.lower()
                SCOPE.set_iff(filename, is_global=is_global)
            except ImportError:
                pass
            
            EventBus.publish(Events.STATUS_UPDATE, 
                f"Loaded IFF: {filename} ({len(STATE.current_iff.chunks)} chunks)")
            EventBus.publish(Events.IFF_LOADED, STATE.current_iff)
        except Exception as e:
            EventBus.publish(Events.STATUS_UPDATE, f"Error loading IFF: {e}")
    
    def _on_iff_clicked(self, entry):
        """Handle IFF file click."""
        try:
            from formats.iff.iff_file import IffFile
            
            data = STATE.current_far.get_entry(entry.filename)
            if data:
                iff_file = IffFile.from_bytes(data, entry.filename)
                STATE.set_iff(iff_file, entry.filename)
                
                # Update scope tracker
                try:
                    from ..safety import SCOPE
                    is_global = 'global' in entry.filename.lower()
                    SCOPE.set_iff(entry.filename, is_global=is_global)
                except ImportError:
                    pass
                
                EventBus.publish(Events.STATUS_UPDATE, 
                    f"IFF: {entry.filename} ({len(STATE.current_iff.chunks)} chunks)")
                EventBus.publish(Events.IFF_LOADED, STATE.current_iff)
        except Exception as e:
            EventBus.publish(Events.STATUS_UPDATE, f"Error loading IFF: {e}")
