"""
Safety Trust Surface — Persistent Safety Indicator

Shows current safety status: Safe / Warning / Unsafe
Click for detailed explanation from SaveStateAnalyzer.
Builds user confidence and teaches SimAntics constraints.
"""

import dearpygui.dearpygui as dpg
from typing import Optional, Any
from enum import Enum
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE


class SafetyLevel(Enum):
    """Safety classification levels."""
    SAFE = "safe"
    WARNING = "warning"
    UNSAFE = "unsafe"
    UNKNOWN = "unknown"


class SafetyTrustSurface:
    """
    Persistent safety indicator panel.
    
    Small, always-visible indicator showing:
    - Current resource safety status
    - Click to expand for details
    - Color-coded: Green/Yellow/Red
    """
    
    TAG = "safety_indicator"
    DETAILS_TAG = "safety_details"
    
    # Safety colors
    COLORS = {
        SafetyLevel.SAFE: (76, 175, 80, 255),      # Green
        SafetyLevel.WARNING: (255, 193, 7, 255),   # Yellow/Amber
        SafetyLevel.UNSAFE: (244, 67, 54, 255),   # Red
        SafetyLevel.UNKNOWN: (158, 158, 158, 255), # Grey
    }
    
    ICONS = {
        SafetyLevel.SAFE: "✓",
        SafetyLevel.WARNING: "⚠",
        SafetyLevel.UNSAFE: "✗",
        SafetyLevel.UNKNOWN: "?",
    }
    
    LABELS = {
        SafetyLevel.SAFE: "Safe",
        SafetyLevel.WARNING: "Warning",
        SafetyLevel.UNSAFE: "Unsafe",
        SafetyLevel.UNKNOWN: "Unknown",
    }
    
    def __init__(self, pos: tuple = (10, 10)):
        self.pos = pos
        self.current_level = SafetyLevel.UNKNOWN
        self.current_reasons: list[str] = []
        self.current_resource: str = "No resource selected"
        self.details_expanded = False
        self._analyzer = None
        self._try_load_analyzer()
        self._create_indicator()
        self._subscribe_events()
    
    def _try_load_analyzer(self):
        """Try to load SaveStateAnalyzer for safety analysis."""
        try:
            from forensic.engine_toolkit import EngineToolkit
            self._analyzer = EngineToolkit()
        except ImportError:
            pass
    
    def _create_indicator(self):
        """Create the persistent safety indicator."""
        with dpg.window(
            label="Safety",
            tag=self.TAG,
            width=120,
            height=40,
            pos=self.pos,
            no_title_bar=True,
            no_resize=True,
            no_move=False,
            no_scrollbar=True,
            no_collapse=True,
        ):
            with dpg.group(horizontal=True):
                # Icon
                dpg.add_text(
                    "?",
                    tag="safety_icon",
                    color=self.COLORS[SafetyLevel.UNKNOWN]
                )
                # Label
                dpg.add_text(
                    "Unknown",
                    tag="safety_label",
                    color=self.COLORS[SafetyLevel.UNKNOWN]
                )
                # Expand button
                dpg.add_button(
                    label="▼",
                    tag="safety_expand_btn",
                    callback=self._toggle_details,
                    width=20,
                    height=20
                )
        
        # Details popup (hidden by default)
        with dpg.window(
            label="Safety Details",
            tag=self.DETAILS_TAG,
            width=350,
            height=250,
            pos=(self.pos[0], self.pos[1] + 45),
            show=False,
            no_resize=True,
            on_close=self._close_details
        ):
            dpg.add_text("Resource:", color=(136, 136, 136))
            dpg.add_text("-", tag="safety_resource_name", color=(224, 224, 224))
            
            dpg.add_separator()
            
            dpg.add_text("Analysis:", color=(136, 136, 136))
            
            with dpg.child_window(height=150, border=True, tag="safety_reasons_list"):
                dpg.add_text("No analysis available", tag="safety_reasons_text", 
                           color=(136, 136, 136), wrap=320)
            
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Learn More",
                    callback=self._show_help,
                    width=100
                )
                dpg.add_button(
                    label="Close",
                    callback=self._close_details,
                    width=80
                )
    
    def _subscribe_events(self):
        """Subscribe to selection events."""
        EventBus.subscribe(Events.CHUNK_SELECTED, self._on_chunk_selected)
        EventBus.subscribe(Events.BHAV_SELECTED, self._on_bhav_selected)
        EventBus.subscribe(Events.FILE_LOADED, self._on_file_loaded)
    
    def _on_chunk_selected(self, chunk):
        """Analyze selected chunk for safety."""
        if chunk is None:
            self._set_unknown()
            return
        
        self.current_resource = getattr(chunk, 'type_code', 'Chunk')
        if hasattr(chunk, 'chunk_id'):
            self.current_resource += f" #{chunk.chunk_id}"
        
        # Analyze chunk
        self._analyze_chunk(chunk)
    
    def _on_bhav_selected(self, bhav):
        """Analyze selected BHAV for safety."""
        if bhav is None:
            self._set_unknown()
            return
        
        self.current_resource = f"BHAV #{bhav.chunk_id}"
        if hasattr(bhav, 'name'):
            self.current_resource = f"{bhav.name} (BHAV)"
        
        # Analyze BHAV
        self._analyze_bhav(bhav)
    
    def _on_file_loaded(self, filepath):
        """Reset safety when new file loaded."""
        self._set_unknown()
    
    def _analyze_chunk(self, chunk):
        """Analyze a chunk for safety issues."""
        reasons = []
        level = SafetyLevel.SAFE
        
        chunk_type = getattr(chunk, 'type_code', '')
        
        # Basic safety rules
        if chunk_type == 'BHAV':
            level, reasons = self._analyze_bhav(chunk)
        elif chunk_type == 'GLOB':
            reasons.append("GLOB chunks define global tuning")
            reasons.append("Editing may affect game balance")
            level = SafetyLevel.WARNING
        elif chunk_type == 'OBJD':
            reasons.append("Object definition - generally safe to inspect")
            level = SafetyLevel.SAFE
        elif chunk_type in ['SPR2', 'SPR#']:
            reasons.append("Sprite data - visual only, safe")
            level = SafetyLevel.SAFE
        else:
            reasons.append(f"Unknown chunk type: {chunk_type}")
            level = SafetyLevel.UNKNOWN
        
        self._update_display(level, reasons)
    
    def _analyze_bhav(self, bhav) -> tuple[SafetyLevel, list[str]]:
        """Analyze a BHAV for safety issues."""
        reasons = []
        level = SafetyLevel.SAFE
        
        if not hasattr(bhav, 'instructions'):
            reasons.append("No instructions found")
            self._update_display(SafetyLevel.UNKNOWN, reasons)
            return SafetyLevel.UNKNOWN, reasons
        
        # Check for dangerous opcodes
        dangerous_opcodes = {
            0x0002: "Expression (can modify any variable)",
            0x001A: "Set to Next (loop control)",
            0x001C: "Push Interaction (can trigger behaviors)",
            0x0021: "Global Event (affects other objects)",
            0x002C: "Kill Object (destroys objects)",
            0x0031: "Set Object (modifies objects)",
        }
        
        warning_opcodes = {
            0x0001: "Primitive Call (external call)",
            0x000B: "Dialog (UI interaction)",
            0x0013: "Relationship (modifies relationships)",
            0x0016: "Notify Stack Object Out of Idle",
        }
        
        found_dangerous = []
        found_warning = []
        
        for instr in bhav.instructions:
            opcode = getattr(instr, 'opcode', 0)
            
            if opcode in dangerous_opcodes:
                found_dangerous.append(dangerous_opcodes[opcode])
            elif opcode in warning_opcodes:
                found_warning.append(warning_opcodes[opcode])
        
        # Determine level
        if found_dangerous:
            level = SafetyLevel.UNSAFE
            reasons.append("⚠ DANGEROUS OPCODES DETECTED:")
            reasons.extend([f"  • {d}" for d in set(found_dangerous)])
        elif found_warning:
            level = SafetyLevel.WARNING
            reasons.append("⚡ Notable opcodes:")
            reasons.extend([f"  • {w}" for w in set(found_warning)])
        else:
            level = SafetyLevel.SAFE
            reasons.append("✓ No dangerous opcodes found")
            reasons.append(f"  {len(bhav.instructions)} instructions analyzed")
        
        # Check for common patterns
        if hasattr(bhav, 'format_') and bhav.format_ > 0x8003:
            reasons.append(f"⚡ Uses format 0x{bhav.format_:04X} (newer)")
        
        self._update_display(level, reasons)
        return level, reasons
    
    def _update_display(self, level: SafetyLevel, reasons: list[str]):
        """Update the indicator display."""
        self.current_level = level
        self.current_reasons = reasons
        
        color = self.COLORS[level]
        icon = self.ICONS[level]
        label = self.LABELS[level]
        
        if dpg.does_item_exist("safety_icon"):
            dpg.set_value("safety_icon", icon)
            dpg.configure_item("safety_icon", color=color)
        
        if dpg.does_item_exist("safety_label"):
            dpg.set_value("safety_label", label)
            dpg.configure_item("safety_label", color=color)
        
        # Update details if visible
        if self.details_expanded:
            self._update_details()
    
    def _update_details(self):
        """Update the details panel."""
        if dpg.does_item_exist("safety_resource_name"):
            dpg.set_value("safety_resource_name", self.current_resource)
        
        if dpg.does_item_exist("safety_reasons_text"):
            reasons_text = "\n".join(self.current_reasons) if self.current_reasons else "No analysis available"
            dpg.set_value("safety_reasons_text", reasons_text)
            dpg.configure_item("safety_reasons_text", color=self.COLORS[self.current_level])
    
    def _set_unknown(self):
        """Reset to unknown state."""
        self.current_resource = "No resource selected"
        self._update_display(SafetyLevel.UNKNOWN, ["Select a resource to analyze"])
    
    def _toggle_details(self):
        """Toggle the details panel."""
        self.details_expanded = not self.details_expanded
        
        if dpg.does_item_exist(self.DETAILS_TAG):
            dpg.configure_item(self.DETAILS_TAG, show=self.details_expanded)
        
        if dpg.does_item_exist("safety_expand_btn"):
            dpg.set_item_label("safety_expand_btn", "▲" if self.details_expanded else "▼")
        
        if self.details_expanded:
            self._update_details()
    
    def _close_details(self):
        """Close the details panel."""
        self.details_expanded = False
        if dpg.does_item_exist(self.DETAILS_TAG):
            dpg.configure_item(self.DETAILS_TAG, show=False)
        if dpg.does_item_exist("safety_expand_btn"):
            dpg.set_item_label("safety_expand_btn", "▼")
    
    def _show_help(self):
        """Show help about safety analysis."""
        # Could open a help window or documentation
        STATE.log("Safety Analysis uses opcode inspection to detect potentially dangerous BHAV operations", "INFO")
    
    @classmethod
    def show(cls):
        """Show the indicator."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
    
    @classmethod
    def hide(cls):
        """Hide the indicator."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=False)
