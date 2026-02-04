"""
Status Bar Component.
Displays application status and messages.
"""

import dearpygui.dearpygui as dpg

from ..events import EventBus, Events
from ..theme import Colors


class StatusBar:
    """Application status bar."""
    
    TAG = "status_bar"
    TEXT_TAG = "status_text"
    
    def __init__(self, width: int = 1600, height: int = 30, y_pos: int = 970):
        self.width = width
        self.height = height
        self.y_pos = y_pos
        self._create_bar()
        self._subscribe_events()
    
    def _create_bar(self):
        """Create the status bar."""
        with dpg.window(
            tag=self.TAG,
            no_title_bar=True,
            no_resize=True,
            no_move=True,
            no_close=True,
            no_collapse=True,
            no_scrollbar=True,
            pos=(0, self.y_pos),
            width=self.width,
            height=self.height
        ):
            with dpg.group(horizontal=True):
                dpg.add_text("SimObliterator", color=Colors.ACCENT_GREEN)
                dpg.add_text(" | ", color=Colors.SEPARATOR)
                dpg.add_text("Ready", tag=self.TEXT_TAG, color=Colors.TEXT_DIM)
    
    def _subscribe_events(self):
        """Subscribe to status events."""
        EventBus.subscribe(Events.STATUS_UPDATE, self._on_status_update)
    
    def _on_status_update(self, message: str):
        """Handle status update event."""
        dpg.set_value(self.TEXT_TAG, message)
    
    @classmethod
    def update(cls, message: str):
        """Directly update the status bar text."""
        if dpg.does_item_exist(cls.TEXT_TAG):
            dpg.set_value(cls.TEXT_TAG, message)
