"""
Semantic Inspector Panel

Displays semantic context for selected BHAV/chunks using EngineToolkit:
- Expansion ownership
- Equivalent BHAVs across packs
- Known patterns / classifications  
- Warnings (unsafe / unknown)
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE

# Try to import EngineToolkit
try:
    from forensic.engine_toolkit import EngineToolkit
    _toolkit = EngineToolkit()
    TOOLKIT_AVAILABLE = True
except ImportError:
    _toolkit = None
    TOOLKIT_AVAILABLE = False


class SemanticInspectorPanel:
    """Semantic context inspector - powered by EngineToolkit."""
    
    TAG = "semantic_inspector"
    CONTENT_TAG = "semantic_content"
    
    def __init__(self, width: int = 350, height: int = 400, pos: tuple = (1030, 540)):
        self.width = width
        self.height = height
        self.pos = pos
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the panel window."""
        with dpg.window(
            label="Semantic Inspector",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            # Header
            dpg.add_text("Semantic Context", color=(0, 212, 255, 255))
            
            if not TOOLKIT_AVAILABLE:
                dpg.add_text("⚠️ EngineToolkit not available", color=(255, 180, 80, 255))
                dpg.add_text("(Some features disabled)", color=(136, 136, 136, 255))
            
            dpg.add_separator()
            
            with dpg.child_window(tag=self.CONTENT_TAG, border=False):
                dpg.add_text("Select a BHAV to analyze", color=(136, 136, 136, 255))
    
    def _subscribe_events(self):
        """Subscribe to BHAV selection events."""
        EventBus.subscribe(Events.BHAV_SELECTED, self._on_bhav_selected)
        EventBus.subscribe(Events.CHUNK_SELECTED, self._on_chunk_selected)
    
    def _on_bhav_selected(self, bhav):
        """Handle BHAV selection - show semantic analysis."""
        self._analyze_bhav(bhav)
    
    def _on_chunk_selected(self, chunk):
        """Handle chunk selection - show if BHAV."""
        if chunk and chunk.chunk_type == "BHAV":
            self._analyze_bhav(chunk)
    
    def _analyze_bhav(self, bhav):
        """Analyze a BHAV and display semantic info."""
        dpg.delete_item(self.CONTENT_TAG, children_only=True)
        
        if bhav is None:
            return
        
        with dpg.group(parent=self.CONTENT_TAG):
            # BHAV identity
            dpg.add_text(f"BHAV #{bhav.chunk_id}", color=(0, 212, 255, 255))
            if hasattr(bhav, 'chunk_label') and bhav.chunk_label:
                dpg.add_text(f"Label: {bhav.chunk_label}", color=(224, 224, 224, 255))
            
            dpg.add_separator()
            
            # Semantic name (from EngineToolkit)
            dpg.add_text("🏷️ Semantic Name", color=(233, 69, 96, 255))
            if TOOLKIT_AVAILABLE and _toolkit:
                try:
                    semantic_name = _toolkit.label_global(bhav.chunk_id)
                    dpg.add_text(f"  {semantic_name}", color=(76, 175, 80, 255))
                except Exception:
                    dpg.add_text("  (Unknown)", color=(136, 136, 136, 255))
            else:
                dpg.add_text("  (Toolkit unavailable)", color=(136, 136, 136, 255))
            
            dpg.add_separator()
            
            # Expansion ownership
            dpg.add_text("📦 Expansion Pack", color=(233, 69, 96, 255))
            if TOOLKIT_AVAILABLE and _toolkit:
                try:
                    expansion = _toolkit.get_expansion(bhav.chunk_id)
                    dpg.add_text(f"  {expansion}", color=(224, 224, 224, 255))
                except Exception:
                    dpg.add_text("  Base Game", color=(224, 224, 224, 255))
            else:
                dpg.add_text("  (Unknown)", color=(136, 136, 136, 255))
            
            dpg.add_separator()
            
            # Equivalents across packs
            dpg.add_text("🔗 Equivalents", color=(233, 69, 96, 255))
            if TOOLKIT_AVAILABLE and _toolkit:
                try:
                    equivalents = _toolkit.find_equivalents(bhav.chunk_id)
                    if equivalents:
                        for eq in equivalents[:5]:
                            dpg.add_text(f"  → {eq}", color=(150, 200, 255, 255))
                    else:
                        dpg.add_text("  (No equivalents found)", color=(136, 136, 136, 255))
                except Exception:
                    dpg.add_text("  (Lookup failed)", color=(136, 136, 136, 255))
            else:
                dpg.add_text("  (Toolkit unavailable)", color=(136, 136, 136, 255))
            
            dpg.add_separator()
            
            # Safety warnings
            dpg.add_text("⚠️ Safety Analysis", color=(233, 69, 96, 255))
            if TOOLKIT_AVAILABLE and _toolkit:
                try:
                    safety = _toolkit.check_safety(bhav.chunk_id)
                    if safety.get('safe', True):
                        dpg.add_text("  ✓ Safe to edit", color=(76, 175, 80, 255))
                    else:
                        dpg.add_text("  ✗ UNSAFE", color=(255, 100, 100, 255))
                        reason = safety.get('reason', 'Unknown reason')
                        dpg.add_text(f"    {reason}", color=(255, 180, 80, 255))
                except Exception:
                    dpg.add_text("  (Check unavailable)", color=(136, 136, 136, 255))
            else:
                dpg.add_text("  (Toolkit unavailable)", color=(136, 136, 136, 255))
            
            dpg.add_separator()
            
            # BHAV details
            dpg.add_text("📊 Statistics", color=(233, 69, 96, 255))
            if hasattr(bhav, 'instructions'):
                dpg.add_text(f"  Instructions: {len(bhav.instructions)}", color=(224, 224, 224, 255))
            if hasattr(bhav, 'args'):
                dpg.add_text(f"  Arguments: {bhav.args}", color=(224, 224, 224, 255))
            if hasattr(bhav, 'locals'):
                dpg.add_text(f"  Locals: {bhav.locals}", color=(224, 224, 224, 255))
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
