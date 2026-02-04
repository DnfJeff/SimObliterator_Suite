"""
Edit Mode Manager.

Controls read-only vs edit mode with deliberate switching.
Implements soft locks with warnings rather than hard blocks.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable, Any
import dearpygui.dearpygui as dpg


class EditMode(Enum):
    """Application edit modes."""
    VIEW = auto()      # Read-only, safe browsing
    EDIT = auto()      # Active editing mode
    SANDBOX = auto()   # Playground mode - changes don't persist


@dataclass
class EditModeManager:
    """
    Manages the application's edit state.
    
    Key principle: Read-only by default.
    Editing is a deliberate mode switch.
    """
    
    current_mode: EditMode = EditMode.VIEW
    _mode_callbacks: list[Callable] = field(default_factory=list)
    _warning_acknowledged: dict[str, bool] = field(default_factory=dict)
    
    # Warning categories that require acknowledgment
    WARNING_GLOBAL = "global_edit"
    WARNING_SEMI_GLOBAL = "semi_global_edit"
    WARNING_SHARED_BHAV = "shared_bhav_edit"
    
    def get_mode(self) -> EditMode:
        """Get current edit mode."""
        return self.current_mode
    
    def is_editable(self) -> bool:
        """Check if editing is currently allowed."""
        return self.current_mode in (EditMode.EDIT, EditMode.SANDBOX)
    
    def is_sandbox(self) -> bool:
        """Check if in sandbox/playground mode."""
        return self.current_mode == EditMode.SANDBOX
    
    def set_mode(self, mode: EditMode, callback: Optional[Callable] = None):
        """
        Set the edit mode.
        
        Args:
            mode: The new edit mode
            callback: Optional callback when mode changes
        """
        old_mode = self.current_mode
        self.current_mode = mode
        
        # Notify all registered callbacks
        for cb in self._mode_callbacks:
            try:
                cb(old_mode, mode)
            except Exception as e:
                print(f"EditMode callback error: {e}")
        
        if callback:
            callback(old_mode, mode)
    
    def on_mode_change(self, callback: Callable):
        """Register a callback for mode changes."""
        self._mode_callbacks.append(callback)
    
    def request_edit_mode(self, scope_type: str = "normal") -> bool:
        """
        Request to enter edit mode with appropriate warnings.
        
        Returns True if edit mode was granted.
        Shows warning dialogs for dangerous scopes.
        """
        if scope_type == "global" and not self._warning_acknowledged.get(self.WARNING_GLOBAL):
            self._show_global_warning()
            return False
        
        if scope_type == "semi_global" and not self._warning_acknowledged.get(self.WARNING_SEMI_GLOBAL):
            self._show_semi_global_warning()
            return False
        
        self.set_mode(EditMode.EDIT)
        return True
    
    def enter_sandbox(self):
        """Enter sandbox/playground mode."""
        self.set_mode(EditMode.SANDBOX)
    
    def exit_to_view(self):
        """Return to safe view mode."""
        self.set_mode(EditMode.VIEW)
        # Clear acknowledgments when leaving edit mode
        self._warning_acknowledged.clear()
    
    def acknowledge_warning(self, warning_type: str):
        """Acknowledge a warning to allow editing."""
        self._warning_acknowledged[warning_type] = True
    
    def _show_global_warning(self):
        """Show warning for global edits."""
        if dpg.does_item_exist("global_warning_modal"):
            dpg.show_item("global_warning_modal")
            return
        
        with dpg.window(
            label="⚠️ Global Edit Warning",
            tag="global_warning_modal",
            modal=True,
            width=500,
            height=250,
            pos=(550, 350),
            no_resize=True
        ):
            dpg.add_text("You are about to edit a GLOBAL file.", color=(255, 200, 100))
            dpg.add_spacer(height=10)
            dpg.add_text(
                "This affects the ENTIRE GAME.\n"
                "Every Sim, every object, every interaction.",
                color=(200, 200, 200)
            )
            dpg.add_spacer(height=10)
            dpg.add_text(
                "Changes here can break your game in unexpected ways.\n"
                "A snapshot will be created automatically.",
                color=(150, 150, 150)
            )
            dpg.add_spacer(height=20)
            
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Continue Editing",
                    width=150,
                    callback=lambda: self._confirm_dangerous_edit(self.WARNING_GLOBAL)
                )
                dpg.add_button(
                    label="Duplicate First",
                    width=150,
                    callback=lambda: self._duplicate_before_edit()
                )
                dpg.add_button(
                    label="Cancel",
                    width=100,
                    callback=lambda: dpg.hide_item("global_warning_modal")
                )
    
    def _show_semi_global_warning(self):
        """Show warning for semi-global edits."""
        if dpg.does_item_exist("semiglobal_warning_modal"):
            dpg.show_item("semiglobal_warning_modal")
            return
        
        with dpg.window(
            label="⚠️ Semi-Global Edit Warning",
            tag="semiglobal_warning_modal",
            modal=True,
            width=500,
            height=280,
            pos=(550, 350),
            no_resize=True
        ):
            dpg.add_text("You are editing a SEMI-GLOBAL behavior.", color=(255, 200, 100))
            dpg.add_spacer(height=10)
            dpg.add_text(
                "Semi-globals are shared across multiple objects.\n"
                "Your change will affect ALL objects using this behavior.",
                color=(200, 200, 200)
            )
            dpg.add_spacer(height=10)
            dpg.add_text(
                "This is the #1 cause of unexpected mod behavior.\n"
                "Consider forking this semi-global for your specific object.",
                color=(150, 150, 150)
            )
            dpg.add_spacer(height=15)
            dpg.add_text("Affected objects will be shown in the scope panel.", color=(100, 180, 255))
            dpg.add_spacer(height=15)
            
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="I Understand",
                    width=120,
                    callback=lambda: self._confirm_dangerous_edit(self.WARNING_SEMI_GLOBAL)
                )
                dpg.add_button(
                    label="Fork Semi-Global",
                    width=140,
                    callback=lambda: self._fork_semi_global()
                )
                dpg.add_button(
                    label="Cancel",
                    width=100,
                    callback=lambda: dpg.hide_item("semiglobal_warning_modal")
                )
    
    def _confirm_dangerous_edit(self, warning_type: str):
        """Confirm a dangerous edit after warning."""
        self.acknowledge_warning(warning_type)
        
        # Hide the appropriate modal
        modal_map = {
            self.WARNING_GLOBAL: "global_warning_modal",
            self.WARNING_SEMI_GLOBAL: "semiglobal_warning_modal",
        }
        modal = modal_map.get(warning_type)
        if modal and dpg.does_item_exist(modal):
            dpg.hide_item(modal)
        
        # Now enter edit mode
        self.set_mode(EditMode.EDIT)
    
    def _duplicate_before_edit(self):
        """Placeholder: Duplicate resource before editing."""
        # This will trigger snapshot creation and then allow editing
        dpg.hide_item("global_warning_modal")
        # TODO: Trigger actual duplication via EventBus
        print("TODO: Duplicate resource before editing")
    
    def _fork_semi_global(self):
        """Placeholder: Fork semi-global to object-specific."""
        dpg.hide_item("semiglobal_warning_modal")
        # TODO: Create object-specific copy of semi-global
        print("TODO: Fork semi-global to object-specific")
    
    def get_mode_display(self) -> tuple[str, tuple]:
        """Get display text and color for current mode."""
        if self.current_mode == EditMode.VIEW:
            return ("👁 VIEW", (150, 200, 255, 255))
        elif self.current_mode == EditMode.EDIT:
            return ("✏ EDIT", (255, 180, 100, 255))
        else:  # SANDBOX
            return ("🎮 SANDBOX", (100, 255, 150, 255))


# Singleton instance
MODE_MANAGER = EditModeManager()
