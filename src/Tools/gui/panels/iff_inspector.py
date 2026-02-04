"""
IFF File Inspector - Chunk list browser

Parses IFF files and displays chunk list.
Clicking a chunk triggers CHUNK_SELECTED event.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from formats.iff import IffFile
from ..events import EventBus, Events
from ..state import STATE
from ..theme import Colors


class IFFInspectorPanel:
    """IFF file inspector - browse chunks."""
    
    TAG = "iff_inspector"
    CHUNK_LIST_TAG = "iff_chunk_list"
    
    def __init__(self, width: int = 280, height: int = 450, pos: tuple = (10, 580)):
        self.width = width
        self.height = height
        self.pos = pos
        self.current_iff = None
        self.chunks = []
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the panel window."""
        with dpg.window(
            label="IFF Inspector",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            dpg.add_text("Chunk List", color=(0, 212, 255, 255))
            dpg.add_separator()
            
            dpg.add_listbox(
                items=[],
                tag=self.CHUNK_LIST_TAG,
                width=-1,
                num_items=20,
                callback=self._on_chunk_selected
            )
    
    def _subscribe_events(self):
        """Subscribe to file loaded events."""
        EventBus.subscribe(Events.FILE_LOADED, self._on_file_loaded)
        EventBus.subscribe(Events.FILE_CLEARED, self._on_file_cleared)
    
    def _on_file_loaded(self, data):
        """Handle file loaded event."""
        file_path = data.get("file_path")
        file_type = data.get("file_type")
        
        if file_type == "IFF":
            self._load_iff(file_path)
        elif file_type == "FAR":
            # TODO: Handle FAR archive loading
            pass
    
    def _on_file_cleared(self):
        """Handle file cleared event."""
        self.current_iff = None
        self.chunks = []
        dpg.configure_item(self.CHUNK_LIST_TAG, items=[])
    
    def _load_iff(self, file_path):
        """Load an IFF file and populate chunk list."""
        try:
            iff = IffFile(file_path)
            self.current_iff = iff
            
            # Extract chunk info
            self.chunks = []
            items = []
            
            for chunk in iff.chunks:
                chunk_type = chunk.chunk_type
                chunk_id = chunk.chunk_id
                chunk_label = getattr(chunk, 'chunk_label', '')
                
                # Format: TYPE #ID (Label)
                if chunk_label:
                    display = f"{chunk_type} #{chunk_id} ({chunk_label})"
                else:
                    display = f"{chunk_type} #{chunk_id}"
                
                items.append(display)
                self.chunks.append(chunk)
            
            # Update listbox
            dpg.configure_item(self.CHUNK_LIST_TAG, items=items)
            print(f"Loaded IFF: {len(self.chunks)} chunks")
            
            STATE.set_iff(iff, str(file_path.name))
            
        except Exception as e:
            print(f"Error loading IFF: {e}")
            dpg.configure_item(self.CHUNK_LIST_TAG, items=[f"Error: {e}"])
    
    def _on_chunk_selected(self, sender, value):
        """Handle chunk selection from listbox."""
        if not value or value >= len(self.chunks):
            return
        
        chunk = self.chunks[int(value)]
        STATE.current_chunk = chunk
        
        # Publish chunk selected event
        EventBus.publish(Events.CHUNK_SELECTED, chunk)
        
        # If it's a BHAV, also publish BHAV selected event
        if chunk.chunk_type == "BHAV":
            EventBus.publish(Events.BHAV_SELECTED, chunk)
        
        print(f"Selected chunk: {chunk.chunk_type} #{chunk.chunk_id}")
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
