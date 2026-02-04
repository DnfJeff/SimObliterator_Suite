"""
Navigation Bar - Compact Toolbar with Back/Forward + Scope Switcher

From the Flow Map:
- Back / Forward navigation
- Jump-back from graph → inspector
- Global scope filter (Object-only, Global-only, Semi-Global)

This is a small, persistent toolbar at the top of the workspace.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE
from ..focus import FOCUS, Scope


class NavigationBarPanel:
    """
    Compact navigation toolbar.
    
    Features:
    - Back/Forward buttons
    - Breadcrumb trail
    - Scope filter dropdown
    - Current resource indicator
    """
    
    TAG = "nav_bar"
    
    COLORS = {
        'cyan': (0, 212, 255),
        'red': (233, 69, 96),
        'text': (224, 224, 224),
        'dim': (136, 136, 136),
        'scope_all': (200, 200, 200),
        'scope_object': (76, 175, 80),
        'scope_global': (255, 193, 7),
        'scope_semi': (156, 39, 176),
    }
    
    SCOPE_LABELS = {
        Scope.ALL: "All",
        Scope.OBJECT_ONLY: "Object",
        Scope.GLOBAL_ONLY: "Global",
        Scope.SEMI_GLOBAL: "Semi-Global",
    }
    
    def __init__(self, width: int = 800, height: int = 35, pos: tuple = (10, 0)):
        self.width = width
        self.height = height
        self.pos = pos
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the navigation bar."""
        with dpg.window(
            label="Navigation",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            no_title_bar=True,
            no_resize=True,
            no_move=True,
            no_scrollbar=True,
            no_collapse=True,
        ):
            with dpg.group(horizontal=True):
                # Back/Forward
                dpg.add_button(
                    label="◀",
                    tag="nav_back",
                    callback=self._go_back,
                    width=25,
                    enabled=False
                )
                dpg.add_button(
                    label="▶",
                    tag="nav_forward",
                    callback=self._go_forward,
                    width=25,
                    enabled=False
                )
                
                dpg.add_spacer(width=10)
                
                # Current resource
                dpg.add_text("📍", color=self.COLORS['dim'])
                dpg.add_text("No selection", tag="nav_current", 
                            color=self.COLORS['text'])
                
                dpg.add_spacer(width=20)
                
                # History dropdown
                dpg.add_button(
                    label="📜",
                    tag="nav_history_btn",
                    callback=self._show_history,
                    width=25
                )
                
                dpg.add_spacer(width=30)
                
                # Scope filter
                dpg.add_text("Scope:", color=self.COLORS['dim'])
                dpg.add_combo(
                    items=["All", "Object", "Global", "Semi-Global"],
                    default_value="All",
                    tag="nav_scope",
                    width=100,
                    callback=self._on_scope_change
                )
                
                dpg.add_spacer(width=20)
                
                # Quick jump buttons
                dpg.add_button(
                    label="Last BHAV",
                    callback=self._jump_last_bhav,
                    width=80
                )
                dpg.add_button(
                    label="Last OBJD",
                    callback=self._jump_last_objd,
                    width=80
                )
        
        # History popup (hidden)
        with dpg.window(
            label="Navigation History",
            tag="nav_history_popup",
            width=300,
            height=200,
            show=False,
            popup=True,
            no_title_bar=True
        ):
            dpg.add_text("Recent:", color=self.COLORS['cyan'])
            dpg.add_separator()
            with dpg.child_window(tag="nav_history_list", height=-1, border=False):
                dpg.add_text("No history yet", color=self.COLORS['dim'])
    
    def _subscribe_events(self):
        """Subscribe to focus changes."""
        FOCUS.subscribe(self._on_focus_changed)
    
    def _on_focus_changed(self, entry, scope_changed=False):
        """Handle focus changes."""
        if scope_changed:
            return
        
        # Update current display
        if entry:
            label = f"{entry.resource_type}: {entry.label}"
            dpg.set_value("nav_current", label[:40])
            dpg.configure_item("nav_current", color=self.COLORS['cyan'])
        else:
            dpg.set_value("nav_current", "No selection")
            dpg.configure_item("nav_current", color=self.COLORS['dim'])
        
        # Update button states
        dpg.configure_item("nav_back", enabled=FOCUS.can_go_back())
        dpg.configure_item("nav_forward", enabled=FOCUS.can_go_forward())
    
    def _go_back(self):
        """Navigate back."""
        FOCUS.go_back()
    
    def _go_forward(self):
        """Navigate forward."""
        FOCUS.go_forward()
    
    def _show_history(self):
        """Show history popup."""
        # Update history list
        dpg.delete_item("nav_history_list", children_only=True)
        
        history = FOCUS.get_history(15)
        
        if not history:
            dpg.add_text("No history yet", parent="nav_history_list",
                        color=self.COLORS['dim'])
        else:
            for i, entry in enumerate(reversed(history)):
                idx = len(history) - 1 - i
                label = f"{entry.resource_type}: {entry.label[:25]}"
                
                dpg.add_button(
                    label=label,
                    parent="nav_history_list",
                    callback=lambda s, a, x=idx: self._jump_to_history(x),
                    width=-1
                )
        
        # Show popup
        dpg.configure_item("nav_history_popup", show=True)
    
    def _jump_to_history(self, index: int):
        """Jump to history entry."""
        FOCUS.jump_to_history(index)
        dpg.configure_item("nav_history_popup", show=False)
    
    def _on_scope_change(self, sender, value):
        """Handle scope filter change."""
        scope_map = {
            "All": Scope.ALL,
            "Object": Scope.OBJECT_ONLY,
            "Global": Scope.GLOBAL_ONLY,
            "Semi-Global": Scope.SEMI_GLOBAL,
        }
        
        scope = scope_map.get(value, Scope.ALL)
        FOCUS.scope = scope
        
        # Update scope indicator color
        color = {
            Scope.ALL: self.COLORS['scope_all'],
            Scope.OBJECT_ONLY: self.COLORS['scope_object'],
            Scope.GLOBAL_ONLY: self.COLORS['scope_global'],
            Scope.SEMI_GLOBAL: self.COLORS['scope_semi'],
        }.get(scope, self.COLORS['text'])
        
        # Publish scope change event
        EventBus.publish('scope.changed', scope)
    
    def _jump_last_bhav(self):
        """Jump to last selected BHAV."""
        entry = FOCUS.get_last_of_type('BHAV')
        if entry:
            FOCUS.select(
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                label=entry.label,
                source_panel='nav_bar',
                file_path=entry.file_path
            )
            EventBus.publish(Events.BHAV_SELECTED, entry.extra.get('chunk'))
    
    def _jump_last_objd(self):
        """Jump to last selected OBJD."""
        entry = FOCUS.get_last_of_type('OBJD')
        if entry:
            FOCUS.select(
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                label=entry.label,
                source_panel='nav_bar',
                file_path=entry.file_path
            )
            EventBus.publish(Events.CHUNK_SELECTED, entry.extra.get('chunk'))
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
