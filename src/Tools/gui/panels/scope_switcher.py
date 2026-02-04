"""
Scope / Context Switcher — Global Scope Filter

Persistent toolbar widget that lets users control scope globally:
- Object-only
- Global-only
- Semi-Global
- All

Applied consistently to Search, Graph, Inspectors.
Prevents "why did this show up?" confusion.
"""

import dearpygui.dearpygui as dpg
from typing import Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..selection import SELECTION, Scope


class ScopeSwitcher:
    """
    Global scope filter widget.
    
    Small, persistent widget that controls analysis scope.
    All panels that display filtered data should respect this.
    """
    
    TAG = "scope_switcher"
    
    COLORS = {
        'cyan': (0, 212, 255, 255),
        'green': (76, 175, 80, 255),
        'yellow': (255, 193, 7, 255),
        'purple': (156, 39, 176, 255),
        'text': (224, 224, 224, 255),
        'dim': (136, 136, 136, 255),
        'active': (0, 212, 255, 255),
        'inactive': (80, 80, 80, 255),
    }
    
    SCOPE_INFO = {
        Scope.ALL: {
            'label': 'All',
            'icon': '🌐',
            'description': 'Show all resources',
            'color': 'cyan',
        },
        Scope.OBJECT_ONLY: {
            'label': 'Object',
            'icon': '📦',
            'description': 'Object-specific resources only',
            'color': 'green',
        },
        Scope.GLOBAL_ONLY: {
            'label': 'Global',
            'icon': '🌍',
            'description': 'Global.iff resources only',
            'color': 'yellow',
        },
        Scope.SEMI_GLOBAL: {
            'label': 'Semi',
            'icon': '📂',
            'description': 'Semi-global resources only',
            'color': 'purple',
        },
    }
    
    def __init__(self, pos: tuple = (140, 10)):
        self.pos = pos
        self.current_scope = Scope.ALL
        self._create_widget()
        self._subscribe_selection()
    
    def _create_widget(self):
        """Create the scope switcher widget."""
        with dpg.window(
            label="Scope",
            tag=self.TAG,
            width=220,
            height=40,
            pos=self.pos,
            no_title_bar=True,
            no_resize=True,
            no_move=False,
            no_scrollbar=True,
            no_collapse=True,
        ):
            with dpg.group(horizontal=True):
                dpg.add_text("Scope:", color=self.COLORS['dim'])
                
                # Scope buttons
                for scope in [Scope.ALL, Scope.OBJECT_ONLY, Scope.GLOBAL_ONLY, Scope.SEMI_GLOBAL]:
                    info = self.SCOPE_INFO[scope]
                    is_active = scope == self.current_scope
                    
                    dpg.add_button(
                        label=info['icon'],
                        tag=f"scope_btn_{scope.value}",
                        callback=lambda s, a, u=scope: self._set_scope(u),
                        width=28,
                        height=24,
                    )
                    
                    # Tooltip
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text(f"{info['label']}: {info['description']}")
    
    def _subscribe_selection(self):
        """Subscribe to selection changes."""
        SELECTION.subscribe(self._on_selection_changed)
    
    def _on_selection_changed(self, state):
        """Handle selection state change - update UI if scope changed."""
        if state.scope != self.current_scope:
            self.current_scope = state.scope
            self._update_buttons()
    
    def _set_scope(self, scope: Scope):
        """Set the global scope filter."""
        self.current_scope = scope
        SELECTION.set_scope(scope, locked=True)
        self._update_buttons()
        
        # Publish scope change event for panels to react
        EventBus.publish("scope.changed", scope)
    
    def _update_buttons(self):
        """Update button visual state."""
        for scope in [Scope.ALL, Scope.OBJECT_ONLY, Scope.GLOBAL_ONLY, Scope.SEMI_GLOBAL]:
            btn_tag = f"scope_btn_{scope.value}"
            if not dpg.does_item_exist(btn_tag):
                continue
            
            is_active = scope == self.current_scope
            info = self.SCOPE_INFO[scope]
            
            # Visual feedback - we'd use themes for proper styling
            # For now, the active state is indicated by selection coordinator
    
    def get_scope(self) -> Scope:
        """Get current scope."""
        return self.current_scope
    
    @classmethod
    def show(cls):
        """Show the widget."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
    
    @classmethod  
    def hide(cls):
        """Hide the widget."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=False)
