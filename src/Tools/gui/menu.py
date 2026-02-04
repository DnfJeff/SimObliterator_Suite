"""
Application Menu Bar.
Main menu for the application with safety-aware options.
"""

import sys
from pathlib import Path

import dearpygui.dearpygui as dpg

try:
    from .theme import Colors
except ImportError:  # Allow running as a script
    program_root = Path(__file__).resolve().parents[1]
    if str(program_root) not in sys.path:
        sys.path.insert(0, str(program_root))
    globals()["__package__"] = "gui"
    from gui.theme import Colors


# Default panel layout (must match gui_main.py)
PANEL_DEFAULTS = {
    "far_browser": {"pos": (20, 50), "size": (300, 420)},
    "iff_panel": {"pos": (330, 50), "size": (340, 420)},
    "chunk_inspector": {"pos": (680, 50), "size": (420, 420)},
    "bhav_editor": {"pos": (20, 480), "size": (1080, 480)},
}


def create_menu_bar():
    """Create the viewport menu bar."""
    
    with dpg.viewport_menu_bar():
        # File menu
        with dpg.menu(label="File"):
            dpg.add_menu_item(
                label="Open FAR Archive...",
                callback=lambda: dpg.show_item("far_file_dialog")
            )
            dpg.add_menu_item(
                label="Open IFF File...",
                callback=lambda: dpg.show_item("iff_file_dialog")
            )
            dpg.add_separator()
            dpg.add_menu_item(
                label="View Snapshots...",
                callback=_show_snapshots
            )
            dpg.add_menu_item(
                label="Restore to Vanilla...",
                callback=_show_restore_vanilla
            )
            dpg.add_separator()
            dpg.add_menu_item(
                label="Exit",
                callback=lambda: dpg.stop_dearpygui()
            )
        
        # Edit menu (safety-aware)
        with dpg.menu(label="Edit"):
            dpg.add_menu_item(
                label="Switch to View Mode",
                callback=_switch_to_view,
                shortcut="Ctrl+Shift+V"
            )
            dpg.add_menu_item(
                label="Switch to Edit Mode",
                callback=_switch_to_edit,
                shortcut="Ctrl+Shift+E"
            )
            dpg.add_menu_item(
                label="Enter Sandbox Mode",
                callback=_enter_sandbox,
                shortcut="Ctrl+Shift+S"
            )
            dpg.add_separator()
            dpg.add_menu_item(
                label="Create Snapshot",
                callback=_create_snapshot
            )
        
        # View menu
        with dpg.menu(label="View"):
            # Panel visibility toggles
            with dpg.menu(label="Panels"):
                dpg.add_menu_item(
                    label="FAR Browser",
                    callback=_show_far_browser
                )
                dpg.add_menu_item(
                    label="IFF Structure",
                    callback=_show_iff_viewer
                )
                dpg.add_menu_item(
                    label="Chunk Inspector",
                    callback=_show_chunk_inspector
                )
                dpg.add_menu_item(
                    label="BHAV Node Editor",
                    callback=_show_bhav_editor
                )
                dpg.add_separator()
                dpg.add_menu_item(
                    label="🗄️ Archiver",
                    callback=_show_archiver
                )
            dpg.add_separator()
            dpg.add_menu_item(
                label="Reset Layout",
                callback=_reset_layout
            )
            dpg.add_separator()
            dpg.add_menu_item(
                label="Show Affected Objects",
                callback=_show_affected_objects
            )
            dpg.add_separator()
            dpg.add_menu_item(
                label="Show Metrics",
                callback=lambda: dpg.show_tool(dpg.mvTool_Metrics)
            )
            dpg.add_menu_item(
                label="Show Style Editor",
                callback=lambda: dpg.show_tool(dpg.mvTool_Style)
            )
        
        # Help menu
        with dpg.menu(label="Help"):
            dpg.add_menu_item(
                label="I'm Lost - Help!",
                callback=_show_help,
                shortcut="F1"
            )
            dpg.add_separator()
            dpg.add_menu_item(
                label="What is a BHAV?",
                callback=lambda: _show_topic("bhav")
            )
            dpg.add_menu_item(
                label="What are Semi-Globals?",
                callback=lambda: _show_topic("semiglobal")
            )
            dpg.add_menu_item(
                label="Understanding Scope",
                callback=lambda: _show_topic("scope")
            )
            dpg.add_separator()
            dpg.add_menu_item(
                label="About",
                callback=_show_about
            )


def _reset_layout():
    """Reset panel positions to default arrangement."""
    for panel_tag, defaults in PANEL_DEFAULTS.items():
        if dpg.does_item_exist(panel_tag):
            dpg.configure_item(
                panel_tag,
                pos=defaults["pos"],
                width=defaults["size"][0],
                height=defaults["size"][1],
                show=True
            )


def _show_far_browser():
    """Show the FAR Browser panel."""
    from .panels import FARBrowserPanel
    FARBrowserPanel.show()


def _show_iff_viewer():
    """Show the IFF Structure panel."""
    from .panels import IFFViewerPanel
    IFFViewerPanel.show()


def _show_chunk_inspector():
    """Show the Chunk Inspector panel."""
    from .panels import ChunkInspectorPanel
    ChunkInspectorPanel.show()


def _show_bhav_editor():
    """Show the BHAV Node Editor panel."""
    from .panels import BHAVEditorPanel
    BHAVEditorPanel.show()


def _show_archiver():
    """Show the Archiver panel."""
    from .panels import ArchiverPanel
    ArchiverPanel.show()


def _switch_to_view():
    """Switch to view mode."""
    from .safety import MODE_MANAGER
    MODE_MANAGER.exit_to_view()


def _switch_to_edit():
    """Switch to edit mode (with safety checks)."""
    from .safety import MODE_MANAGER, SCOPE
    scope_type = SCOPE.get_scope_type_for_edit()
    MODE_MANAGER.request_edit_mode(scope_type)


def _enter_sandbox():
    """Enter sandbox/playground mode."""
    from .safety import MODE_MANAGER
    MODE_MANAGER.enter_sandbox()


def _create_snapshot():
    """Create a snapshot of current selection."""
    from .safety import SNAPSHOTS
    from .state import STATE
    
    if STATE.current_chunk is None:
        _show_message("No Selection", "Select a chunk first to create a snapshot.")
        return
    
    # Create snapshot
    source = STATE.current_far.path if STATE.current_far else "unknown"
    SNAPSHOTS.create_snapshot(
        STATE.current_chunk,
        str(source),
        description="Manual snapshot"
    )
    
    _show_message("Snapshot Created", f"Snapshot saved for {STATE.current_chunk.chunk_type} #{STATE.current_chunk.chunk_id}")


def _show_snapshots():
    """Show snapshot browser."""
    _show_message("Snapshots", "Snapshot browser coming soon.\nSnapshots are saved automatically before edits.")


def _show_restore_vanilla():
    """Show restore to vanilla dialog."""
    _show_message("Restore to Vanilla", "Vanilla restore coming soon.\nKeep your original game files backed up!")


def _show_affected_objects():
    """Show panel of affected objects for current selection."""
    from .safety import SCOPE
    
    scope = SCOPE.scope
    
    if dpg.does_item_exist("affected_objects_window"):
        dpg.delete_item("affected_objects_window")
    
    with dpg.window(
        label="Affected Objects",
        tag="affected_objects_window",
        width=350,
        height=300,
        pos=(1050, 200)
    ):
        if not scope.affected_objects and scope.affected_count == 0:
            dpg.add_text("This edit affects only the current item.", color=(100, 220, 150))
        elif scope.is_global:
            dpg.add_text("⚠️ GLOBAL EDIT", color=(255, 100, 100))
            dpg.add_text("This affects EVERYTHING in the game.")
            dpg.add_separator()
            dpg.add_text("All Sims, all objects, all interactions.")
        elif scope.is_semi_global:
            dpg.add_text(f"⚠️ Affects {scope.affected_count or 'multiple'} objects", color=(255, 180, 100))
            dpg.add_separator()
            
            if scope.affected_objects:
                for obj in scope.affected_objects[:20]:
                    dpg.add_text(f"  • {obj}")
                if len(scope.affected_objects) > 20:
                    dpg.add_text(f"  ... and {len(scope.affected_objects) - 20} more")
            else:
                dpg.add_text("  (List loading...)", color=(150, 150, 150))
        
        dpg.add_separator()
        dpg.add_button(
            label="Close",
            width=-1,
            callback=lambda: dpg.delete_item("affected_objects_window")
        )


def _show_help():
    """Show help window."""
    from .safety import HELP
    HELP.show_help_window()


def _show_topic(topic_key: str):
    """Show a specific help topic."""
    from .safety import HELP
    HELP.show_help_window(topic_key)


def _show_message(title: str, message: str):
    """Show a simple message dialog."""
    tag = f"message_{title.lower().replace(' ', '_')}"
    
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    
    with dpg.window(
        label=title,
        tag=tag,
        modal=True,
        width=350,
        height=150,
        pos=(625, 425)
    ):
        dpg.add_text(message, wrap=320)
        dpg.add_spacer(height=10)
        dpg.add_button(
            label="OK",
            width=-1,
            callback=lambda: dpg.delete_item(tag)
        )


def _show_about():
    """Show about dialog."""
    if dpg.does_item_exist("about_window"):
        dpg.show_item("about_window")
        return
    
    with dpg.window(
        label="About SimObliterator",
        tag="about_window",
        modal=True,
        width=450,
        height=280,
        pos=(575, 360)
    ):
        dpg.add_text("SimObliterator", color=Colors.ACCENT_GREEN)
        dpg.add_text("The Perfect Sims 1 Mod Tool Suite")
        dpg.add_separator()
        dpg.add_text("A playground for messing with a living world.", color=Colors.TEXT_DIM)
        dpg.add_spacer(height=10)
        
        dpg.add_text("Safety Philosophy:", color=Colors.ACCENT_BLUE)
        dpg.add_text("• Every action shows its scope", bullet=True)
        dpg.add_text("• Snapshots before every edit", bullet=True)
        dpg.add_text("• Warnings, not blocks", bullet=True)
        dpg.add_text("• Always reversible", bullet=True)
        
        dpg.add_spacer(height=10)
        dpg.add_text("Built with Dear PyGui", color=Colors.TEXT_DIM)
        dpg.add_button(
            label="Close",
            width=-1,
            callback=lambda: dpg.hide_item("about_window")
        )


def _launch_from_script():
    """Launch the full GUI when running this file directly."""
    from gui_main import main
    main()


if __name__ == "__main__":
    _launch_from_script()
