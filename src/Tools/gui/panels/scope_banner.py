"""
Scope Banner Panel.

Always-visible indicator showing:
- Current edit scope (what will be affected)
- Blast radius warnings
- Breadcrumb navigation
"""

import dearpygui.dearpygui as dpg

from ..events import EventBus, Events
from ..theme import Colors
from ..safety import SCOPE, MODE_MANAGER, EditMode


class ScopeBanner:
    """
    Compact scope indicator for toolbar strip.
    
    Shows:
    - Edit scope (single chunk, object, semi-global, global)
    - Affected object count
    """
    
    TAG = "scope_banner"
    SCOPE_TEXT_TAG = "scope_text"
    AFFECTED_TAG = "affected_text"
    
    def __init__(self, width: int = 350, height: int = 28, pos: tuple = (810, 27)):
        self.width = width
        self.height = height
        self.pos = pos
        self._create_panel()
        self._subscribe_events()
        
        # Register for scope changes
        SCOPE.on_scope_change(self._on_scope_change)
    
    def _create_panel(self):
        """Create the scope banner."""
        with dpg.window(
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            no_close=True,
            no_collapse=True,
            no_resize=True,
            no_move=True,
            no_title_bar=True,
            no_scrollbar=True
        ):
            with dpg.group(horizontal=True):
                dpg.add_text("SCOPE:", color=(120, 120, 130))
                dpg.add_text(
                    "No selection",
                    tag=self.SCOPE_TEXT_TAG,
                    color=(150, 150, 150)
                )
                dpg.add_spacer(width=15)
                dpg.add_text("|", color=(60, 60, 70))
                dpg.add_spacer(width=15)
                dpg.add_text("AFFECTS:", color=(120, 120, 130))
                dpg.add_text(
                    "-",
                    tag=self.AFFECTED_TAG,
                    color=(150, 150, 150)
                )
    
    def _subscribe_events(self):
        """Subscribe to relevant events."""
        EventBus.subscribe(Events.CHUNK_SELECTED, self._on_chunk_selected)
        EventBus.subscribe(Events.IFF_LOADED, self._on_iff_loaded)
    
    def _on_scope_change(self, scope):
        """Handle scope change from tracker."""
        # Update scope display
        text, color = scope.get_scope_display()
        dpg.set_value(self.SCOPE_TEXT_TAG, text)
        dpg.configure_item(self.SCOPE_TEXT_TAG, color=color)
        
        # Update affected display
        if scope.affected_count > 0:
            affected_text = f"{scope.affected_count} objects"
            dpg.set_value(self.AFFECTED_TAG, affected_text)
            
            # Color based on count
            if scope.affected_count > 10:
                dpg.configure_item(self.AFFECTED_TAG, color=(255, 100, 100, 255))
            elif scope.affected_count > 1:
                dpg.configure_item(self.AFFECTED_TAG, color=(255, 180, 100, 255))
            else:
                dpg.configure_item(self.AFFECTED_TAG, color=(100, 220, 150, 255))
        else:
            dpg.set_value(self.AFFECTED_TAG, "This only")
            dpg.configure_item(self.AFFECTED_TAG, color=(100, 220, 150, 255))
    
    def _on_chunk_selected(self, chunk):
        """Handle chunk selection."""
        if chunk is None:
            SCOPE.clear()
            return
        
        SCOPE.set_chunk(
            chunk.chunk_type,
            chunk.chunk_id,
            getattr(chunk, 'chunk_label', None)
        )
    
    def _on_iff_loaded(self, iff):
        """Handle IFF loaded."""
        if iff is None:
            return
        
        SCOPE.set_iff(
            getattr(iff, 'filename', 'unknown'),
            is_global='global' in str(getattr(iff, 'filename', '')).lower()
        )


class BreadcrumbBar:
    """
    Breadcrumb navigation showing current path.
    
    FAR → IFF → Chunk Type → Chunk → Instruction
    """
    
    TAG = "breadcrumb_bar"
    CRUMB_TAG = "breadcrumb_text"
    
    def __init__(self, width: int = 600, height: int = 28, pos: tuple = (10, 27)):
        self.width = width
        self.height = height
        self.pos = pos
        self._create_bar()
        
        # Register for scope changes
        SCOPE.on_scope_change(self._on_scope_change)
    
    def _create_bar(self):
        """Create the breadcrumb bar."""
        with dpg.window(
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            no_title_bar=True,
            no_close=True,
            no_collapse=True,
            no_resize=True,
            no_move=True,
            no_scrollbar=True
        ):
            dpg.add_text(
                "📍 Nothing selected",
                tag=self.CRUMB_TAG,
                color=(150, 150, 150)
            )
    
    def _on_scope_change(self, scope):
        """Update breadcrumb display."""
        crumb = scope.get_breadcrumb()
        dpg.set_value(self.CRUMB_TAG, f"📍 {crumb}")
        
        # Color based on scope level
        if scope.is_global:
            dpg.configure_item(self.CRUMB_TAG, color=(255, 100, 100, 255))
        elif scope.is_semi_global:
            dpg.configure_item(self.CRUMB_TAG, color=(255, 180, 100, 255))
        else:
            dpg.configure_item(self.CRUMB_TAG, color=(200, 200, 200, 255))


class EditModeToolbar:
    """
    Compact edit mode toggle for toolbar strip.
    
    Shows current mode with quick switch buttons.
    """
    
    TAG = "edit_mode_toolbar"
    MODE_TAG = "mode_display"
    
    def __init__(self, width: int = 180, height: int = 28, pos: tuple = (620, 27)):
        self.width = width
        self.height = height
        self.pos = pos
        self._create_toolbar()
        
        # Register for mode changes
        MODE_MANAGER.on_mode_change(self._on_mode_change)
    
    def _create_toolbar(self):
        """Create the edit mode toolbar."""
        with dpg.window(
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            no_close=True,
            no_collapse=True,
            no_resize=True,
            no_move=True,
            no_title_bar=True,
            no_scrollbar=True
        ):
            with dpg.group(horizontal=True):
                # Current mode display
                mode_text, mode_color = MODE_MANAGER.get_mode_display()
                dpg.add_text(
                    mode_text,
                    tag=self.MODE_TAG,
                    color=mode_color
                )
                dpg.add_spacer(width=10)
                # Quick switch buttons
                dpg.add_button(
                    label="👁",
                    width=24,
                    callback=self._switch_to_view
                )
                dpg.add_button(
                    label="✏",
                    width=24,
                    callback=self._switch_to_edit
                )
                dpg.add_button(
                    label="🎮",
                    width=24,
                    callback=self._switch_to_sandbox
                )
    
    def _on_mode_change(self, old_mode, new_mode):
        """Handle mode change."""
        mode_text, mode_color = MODE_MANAGER.get_mode_display()
        dpg.set_value(self.MODE_TAG, mode_text)
        dpg.configure_item(self.MODE_TAG, color=mode_color)
    
    def _switch_to_view(self):
        """Switch to view mode."""
        MODE_MANAGER.exit_to_view()
    
    def _switch_to_edit(self):
        """Request edit mode (may show warning)."""
        scope_type = SCOPE.get_scope_type_for_edit()
        MODE_MANAGER.request_edit_mode(scope_type)
    
    def _switch_to_sandbox(self):
        """Enter sandbox/playground mode."""
        MODE_MANAGER.enter_sandbox()


class ConfidenceOverlay:
    """
    Compact classification confidence display for toolbar.
    """
    
    TAG = "confidence_overlay"
    CLASS_TAG = "classification_text"
    
    def __init__(self, width: int = 160, height: int = 28, pos: tuple = (1170, 27)):
        self.width = width
        self.height = height
        self.pos = pos
        self._create_panel()
        
        # Register for scope changes
        SCOPE.on_scope_change(self._on_scope_change)
    
    def _create_panel(self):
        """Create the confidence overlay."""
        with dpg.window(
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            no_close=True,
            no_collapse=True,
            no_resize=True,
            no_move=True,
            no_title_bar=True,
            no_scrollbar=True
        ):
            with dpg.group(horizontal=True):
                dpg.add_text("CLASS:", color=(120, 120, 130))
                dpg.add_text(
                    "-",
                    tag=self.CLASS_TAG,
                    color=(150, 150, 150)
                )
    
    def _on_scope_change(self, scope):
        """Update classification display."""
        if scope.classification:
            # Classification display with color
            class_colors = {
                "ROLE": (100, 220, 100, 255),     # Green
                "FLOW": (220, 200, 100, 255),     # Yellow  
                "ACTION": (100, 180, 255, 255),   # Blue
                "GUARD": (220, 150, 255, 255),    # Purple
            }
            
            color = class_colors.get(scope.classification, (150, 150, 150, 255))
            
            # Show classification with confidence indicator
            conf_icon = "●" if scope.confidence >= 0.8 else "◐" if scope.confidence >= 0.5 else "○"
            dpg.set_value(self.CLASS_TAG, f"{conf_icon} {scope.classification}")
            dpg.configure_item(self.CLASS_TAG, color=color)
        else:
            dpg.set_value(self.CLASS_TAG, "-")
            dpg.configure_item(self.CLASS_TAG, color=(150, 150, 150, 255))


class HelpButton:
    """
    The "I'm Lost" escape hatch button.
    
    Always visible in toolbar, opens contextual help.
    """
    
    TAG = "help_button_window"
    
    def __init__(self, pos: tuple = (1480, 27)):
        self.pos = pos
        self._create_button()
    
    def _create_button(self):
        """Create the help button."""
        from ..safety import HELP
        
        with dpg.window(
            tag=self.TAG,
            width=110,
            height=28,
            pos=self.pos,
            no_title_bar=True,
            no_close=True,
            no_collapse=True,
            no_resize=True,
            no_move=True,
            no_scrollbar=True
        ):
            dpg.add_button(
                label="😬 I'm Lost",
                width=-1,
                height=-1,
                callback=lambda: HELP.show_help_window()
            )
