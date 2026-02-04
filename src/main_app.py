"""
SimObliterator Main Application Frame

DearPyGUI window setup, docking, menu bar, and panel initialization.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "Tools"))
sys.path.insert(0, str(Path(__file__).parent / "formats"))

from Tools.gui.panels.file_loader import FileLoaderPanel
from Tools.gui.panels.iff_inspector import IFFInspectorPanel
from Tools.gui.panels.chunk_inspector import ChunkInspectorPanel
from Tools.gui.panels.bhav_editor import BHAVEditorPanel
from Tools.gui.panels.far_browser import FARBrowserPanel
from Tools.gui.panels.semantic_inspector import SemanticInspectorPanel
from Tools.gui.panels.support_panels import GlobalSearchPanel, PreferencesPanel, LogPanel
from Tools.gui.panels.object_inspector import ObjectInspectorPanel
from Tools.gui.panels.graph_canvas import GraphCanvasPanel
from Tools.gui.panels.save_editor_panel import SaveEditorPanel
from Tools.gui.panels.library_browser_panel import LibraryBrowserPanel
from Tools.gui.panels.character_viewer_panel import CharacterViewerPanel
# Platform-level panels (critical pieces from flow map)
from Tools.gui.panels.safety_trust_panel import SafetyTrustPanel
from Tools.gui.panels.diff_compare_panel import DiffComparePanel
from Tools.gui.panels.task_runner_panel import TaskRunnerPanel
from Tools.gui.panels.visual_object_browser_panel import VisualObjectBrowserPanel
from Tools.gui.panels.navigation_bar_panel import NavigationBarPanel
# Orientation & Export panels (UI/IO completeness)
from Tools.gui.panels.system_overview_panel import SystemOverviewPanel
from Tools.gui.panels.sprite_export_panel import SpriteExportPanel
from Tools.gui.panels.archiver_panel import ArchiverPanel
from Tools.gui.panels.status_bar import StatusBar
from Tools.gui.theme import setup_theme
from Tools.gui.events import EventBus

# Import MutationPipeline for mode switching
try:
    from Tools.core.mutation_pipeline import MutationPipeline, MutationMode
    PIPELINE_AVAILABLE = True
except ImportError:
    MutationPipeline = None
    MutationMode = None
    PIPELINE_AVAILABLE = False


class MainApp:
    """Main application frame and window manager."""
    
    def __init__(self, width: int = 1400, height: int = 900):
        self.width = width
        self.height = height
        self.panels = {}
        self.root_dir = Path(__file__).parent.parent  # Go up from src/ to root
        
        # Setup DearPyGUI
        dpg.create_context()
        setup_theme()
        
        # Create main viewport with icon
        dpg.create_viewport(
            title="SimObliterator Suite - IFF Editor & Analyzer",
            width=width,
            height=height,
            small_icon=str(self.root_dir / "assets" / "icon.ico"),
            large_icon=str(self.root_dir / "assets" / "icon.ico")
        )
        
        # Setup menu bar
        self._create_menu_bar()
        
        # Initialize panels
        self._init_panels()
        
        # Setup initial layout
        self._setup_layout()
    
    def _create_menu_bar(self):
        """Create the application menu bar."""
        with dpg.viewport_menu_bar():
            # File Menu
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Load IFF...", callback=lambda: EventBus.publish('file.browse_iff'))
                dpg.add_menu_item(label="Load FAR...", callback=lambda: EventBus.publish('far.browse_requested'))
                dpg.add_menu_item(label="Load Save...", callback=lambda: EventBus.publish('save.browse_requested'))
                dpg.add_separator()
                dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())
            
            # View Menu
            with dpg.menu(label="View"):
                dpg.add_menu_item(label="System Overview", callback=lambda: self._show_panel("system_overview"))
                dpg.add_menu_item(label="Visual Browser", callback=lambda: self._show_panel("visual_browser"))
                dpg.add_menu_item(label="Library Browser", callback=lambda: self._show_panel("library_browser"))
                dpg.add_separator()
                dpg.add_menu_item(label="BHAV Editor", callback=lambda: self._show_panel("bhav_editor"))
                dpg.add_menu_item(label="Graph Canvas", callback=lambda: self._show_panel("graph_canvas"))
                dpg.add_menu_item(label="Save Editor", callback=lambda: self._show_panel("save_editor"))
                dpg.add_separator()
                dpg.add_menu_item(label="Diff Compare", callback=lambda: self._show_panel("diff_compare"))
                dpg.add_menu_item(label="Search", callback=lambda: self._show_panel("search"))
                dpg.add_menu_item(label="Log", callback=lambda: self._show_panel("log"))
            
            # Tools Menu
            with dpg.menu(label="Tools"):
                dpg.add_menu_item(label="Archiver", callback=lambda: self._show_panel("archiver"))
                dpg.add_menu_item(label="Task Runner", callback=lambda: self._show_panel("task_runner"))
                dpg.add_menu_item(label="Sprite Export", callback=lambda: self._show_panel("sprite_export"))
                dpg.add_separator()
                dpg.add_menu_item(label="Preferences", callback=lambda: self._show_panel("preferences"))
            
            # Mode Menu (MutationPipeline)
            with dpg.menu(label="Mode"):
                dpg.add_menu_item(
                    label="🔒 INSPECT (Read-Only)", 
                    callback=lambda: self._set_mode('INSPECT'),
                    check=True,
                    default_value=True,
                    tag="mode_inspect"
                )
                dpg.add_menu_item(
                    label="👁 PREVIEW (Show Changes)", 
                    callback=lambda: self._set_mode('PREVIEW'),
                    check=True,
                    tag="mode_preview"
                )
                dpg.add_menu_item(
                    label="✏️ MUTATE (Full Edit)", 
                    callback=lambda: self._set_mode('MUTATE'),
                    check=True,
                    tag="mode_mutate"
                )
            
            # Help Menu
            with dpg.menu(label="Help"):
                dpg.add_menu_item(label="About", callback=self._show_about)
    
    def _show_panel(self, panel_name: str):
        """Show a panel by name."""
        panel = self.panels.get(panel_name)
        if panel and hasattr(panel, 'TAG'):
            if dpg.does_item_exist(panel.TAG):
                dpg.configure_item(panel.TAG, show=True)
                dpg.focus_item(panel.TAG)
    
    def _set_mode(self, mode_name: str):
        """Set mutation pipeline mode."""
        # Update checkmarks
        dpg.set_value("mode_inspect", mode_name == 'INSPECT')
        dpg.set_value("mode_preview", mode_name == 'PREVIEW')
        dpg.set_value("mode_mutate", mode_name == 'MUTATE')
        
        # Set pipeline mode if available
        if PIPELINE_AVAILABLE and MutationPipeline:
            pipeline = MutationPipeline.get()
            if mode_name == 'INSPECT':
                pipeline.set_mode(MutationMode.INSPECT)
            elif mode_name == 'PREVIEW':
                pipeline.set_mode(MutationMode.PREVIEW)
            elif mode_name == 'MUTATE':
                pipeline.set_mode(MutationMode.MUTATE)
        
        # Update status
        EventBus.publish('status.update', f"Mode: {mode_name}")
    
    def _show_about(self):
        """Show about dialog."""
        with dpg.window(label="About SimObliterator", modal=True, width=350, height=200):
            dpg.add_text("SimObliterator Suite", color=(0, 212, 255))
            dpg.add_text("System-Aware Sims 1 IFF Editor & Analyzer")
            dpg.add_separator()
            dpg.add_text("Version 1.0.0")
            dpg.add_text("© 2025-2026")
            dpg.add_spacer(height=10)
            dpg.add_button(label="Close", callback=lambda: dpg.delete_item(dpg.last_item()))
    
    def _init_panels(self):
        """Initialize all UI panels."""
        # File Loader - entry point
        self.panels["file_loader"] = FileLoaderPanel(
            width=350,
            height=150,
            pos=(10, 30)
        )
        
        # IFF Inspector - chunk list
        self.panels["iff_inspector"] = IFFInspectorPanel(
            width=280,
            height=300,
            pos=(10, 190)
        )
        
        # Chunk Inspector - details
        self.panels["chunk_inspector"] = ChunkInspectorPanel(
            width=350,
            height=500,
            pos=(1030, 30)
        )
        
        # BHAV Editor - node graph
        self.panels["bhav_editor"] = BHAVEditorPanel(
            width=1000,
            height=450,
            pos=(300, 430)
        )
        
        # FAR Browser - archive browser
        self.panels["far_browser"] = FARBrowserPanel(
            width=280,
            height=300,
            pos=(10, 500)
        )
        
        # Semantic Inspector - EngineToolkit analysis
        self.panels["semantic_inspector"] = SemanticInspectorPanel(
            width=350,
            height=350,
            pos=(1030, 540)
        )
        
        # Support panels (hidden by default)
        self.panels["search"] = GlobalSearchPanel(
            width=400,
            height=300,
            pos=(500, 100)
        )
        
        self.panels["preferences"] = PreferencesPanel(
            width=400,
            height=350,
            pos=(500, 200)
        )
        
        self.panels["log"] = LogPanel(
            width=600,
            height=200,
            pos=(400, 680)
        )
        
        # Object Inspector - 3D preview
        self.panels["object_inspector"] = ObjectInspectorPanel(
            width=500,
            height=400,
            pos=(400, 30)
        )
        
        # Graph Canvas - dependency viewer
        self.panels["graph_canvas"] = GraphCanvasPanel(
            width=700,
            height=500,
            pos=(300, 100)
        )
        
        # Save Editor - family money, sim skills (for casual users)
        self.panels["save_editor"] = SaveEditorPanel(
            width=450,
            height=700,
            pos=(950, 30)
        )
        
        # Library Browser - asset library with card grid
        self.panels["library_browser"] = LibraryBrowserPanel(
            width=800,
            height=600,
            pos=(50, 50)
        )
        
        # Character Viewer - Sim details and 3D preview
        self.panels["character_viewer"] = CharacterViewerPanel(
            width=700,
            height=550,
            pos=(200, 100)
        )
        
        # === PLATFORM-LEVEL PANELS (Critical Missing Pieces) ===
        
        # Navigation Bar - Back/Forward + Scope switcher (top bar)
        self.panels["nav_bar"] = NavigationBarPanel(
            width=900,
            height=35,
            pos=(10, 0)
        )
        
        # Safety Trust Panel - persistent Safe/Warning/Unsafe indicator
        self.panels["safety_trust"] = SafetyTrustPanel(
            width=280,
            height=40,
            pos=(920, 0)
        )
        
        # Diff Compare - side-by-side BHAV comparison (hidden by default)
        self.panels["diff_compare"] = DiffComparePanel(
            width=900,
            height=600,
            pos=(100, 100)
        )
        
        # Task Runner - automated analysis tasks (hidden by default)
        self.panels["task_runner"] = TaskRunnerPanel(
            width=500,
            height=450,
            pos=(150, 100)
        )
        
        # Visual Object Browser - CC creator entry point (hidden by default)
        self.panels["visual_browser"] = VisualObjectBrowserPanel(
            width=850,
            height=600,
            pos=(50, 50)
        )
        
        # === ORIENTATION & EXPORT PANELS (UI/IO Completeness) ===
        
        # System Overview - "What am I looking at?" orientation surface
        self.panels["system_overview"] = SystemOverviewPanel(
            width=300,
            height=400,
            pos=(10, 45)
        )
        
        # Sprite Export - Export sprites to PNG/ZIP/Sheet
        self.panels["sprite_export"] = SpriteExportPanel(
            width=400,
            height=350,
            pos=(500, 200)
        )
        
        # Archiver - Batch game analysis and database building
        self.panels["archiver"] = ArchiverPanel(
            width=450,
            height=500,
            pos=(200, 100)
        )
        
        # Status Bar - Bottom application status
        self.panels["status_bar"] = StatusBar(
            width=self.width,
            height=30,
            y_pos=self.height - 35
        )
    
    def _setup_layout(self):
        """Setup initial panel positions and layout."""
        pass
    
    def show(self):
        """Show the main window."""
        dpg.setup_dearpygui()
        dpg.show_viewport()
    
    def run(self):
        """Run the main event loop."""
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
    
    def shutdown(self):
        """Shutdown the application."""
        dpg.destroy_context()


def main():
    """Entry point."""
    try:
        app = MainApp(width=1400, height=900)
        app.show()
        app.run()
        app.shutdown()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
