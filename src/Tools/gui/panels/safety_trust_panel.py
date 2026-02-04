"""
Safety Trust Surface - Persistent Safety Indicator

From the Flow Map:
- Small, persistent indicator: Safe / Warning / Unsafe
- Click → explanation (from SaveStateAnalyzer)
- Builds confidence and teaches users SimAntics constraints

This is a floating toolbar/badge that shows current safety status.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE
from ..focus import FOCUS


class SafetyTrustPanel:
    """
    Persistent safety indicator.
    
    Shows:
    - Current resource safety status (Safe/Warning/Unsafe)
    - Click to expand detailed explanation
    - Real-time updates as selections change
    """
    
    TAG = "safety_trust"
    DETAIL_TAG = "safety_detail"
    
    # Safety levels with colors
    SAFETY_LEVELS = {
        'safe': {
            'color': (76, 175, 80),      # Green
            'icon': '✓',
            'label': 'SAFE',
        },
        'warning': {
            'color': (255, 193, 7),      # Yellow
            'icon': '⚠',
            'label': 'CAUTION',
        },
        'unsafe': {
            'color': (244, 67, 54),      # Red
            'icon': '✗',
            'label': 'UNSAFE',
        },
        'unknown': {
            'color': (158, 158, 158),    # Gray
            'icon': '?',
            'label': 'UNKNOWN',
        },
    }
    
    # Known dangerous opcodes
    DANGEROUS_OPCODES = {
        0x0002: "Expression - can modify motives",
        0x0012: "Find Location - can break routing",
        0x001E: "Create Object - resource allocation",
        0x0024: "Remove Object Instance - deletion",
        0x0027: "Set Motive Change - direct motive edit",
        0x002E: "Kill Sim - instant death",
        0x003B: "Set Balloon/Headline - UI manipulation",
    }
    
    # Safe read-only opcodes
    SAFE_OPCODES = {
        0x0001: "Sleep - wait cycles",
        0x0003: "Animation - visual only",
        0x0005: "Relationship - read check",
        0x0006: "Goto - flow control",
        0x0007: "Return - exit",
    }
    
    def __init__(self, width: int = 280, height: int = 40, pos: tuple = (10, 10)):
        self.width = width
        self.height = height
        self.pos = pos
        self.current_level = 'unknown'
        self.current_reasons = []
        self.expanded = False
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the safety indicator panel."""
        with dpg.window(
            label="Safety",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            no_title_bar=True,
            no_resize=True,
            no_move=False,
            no_scrollbar=True,
            no_collapse=True,
        ):
            # Compact indicator bar
            with dpg.group(horizontal=True):
                # Status badge
                dpg.add_text("?", tag="safety_icon", color=(158, 158, 158))
                dpg.add_text("UNKNOWN", tag="safety_label", color=(158, 158, 158))
                dpg.add_spacer(width=10)
                
                # Expand button
                dpg.add_button(
                    label="▼",
                    tag="safety_expand_btn",
                    callback=self._toggle_expand,
                    width=20,
                    height=20
                )
            
            # Detail panel (hidden by default)
            with dpg.child_window(
                tag=self.DETAIL_TAG,
                height=150,
                border=True,
                show=False
            ):
                dpg.add_text("Safety Analysis", color=(0, 212, 255))
                dpg.add_separator()
                dpg.add_text("", tag="safety_resource", color=(224, 224, 224))
                dpg.add_spacer(height=5)
                dpg.add_text("Reasons:", color=(136, 136, 136))
                
                with dpg.child_window(tag="safety_reasons", height=80, border=False):
                    dpg.add_text("No analysis yet", color=(136, 136, 136))
    
    def _subscribe_events(self):
        """Subscribe to selection events."""
        EventBus.subscribe(Events.CHUNK_SELECTED, self._on_chunk_selected)
        EventBus.subscribe(Events.BHAV_SELECTED, self._on_bhav_selected)
        FOCUS.subscribe(self._on_focus_changed)
    
    def _toggle_expand(self):
        """Toggle detail panel visibility."""
        self.expanded = not self.expanded
        dpg.configure_item(self.DETAIL_TAG, show=self.expanded)
        
        # Resize window
        new_height = 200 if self.expanded else 40
        dpg.configure_item(self.TAG, height=new_height)
        
        # Update button
        dpg.set_value("safety_expand_btn", "▲" if self.expanded else "▼")
        dpg.configure_item("safety_expand_btn", label="▲" if self.expanded else "▼")
    
    def _on_focus_changed(self, entry, scope_changed=False):
        """Handle focus changes from FocusCoordinator."""
        if entry is None or scope_changed:
            return
        
        # Analyze based on resource type
        if entry.resource_type == 'BHAV':
            self._analyze_bhav_by_id(entry.resource_id)
        elif entry.resource_type == 'OBJD':
            self._set_status('safe', [
                "OBJD chunks are metadata only",
                "No executable code"
            ], f"OBJD #{entry.resource_id}")
        else:
            self._set_status('unknown', [
                f"No safety analysis for {entry.resource_type}"
            ], f"{entry.resource_type} #{entry.resource_id}")
    
    def _on_chunk_selected(self, chunk):
        """Handle chunk selection."""
        if chunk is None:
            self._set_status('unknown', ["No chunk selected"])
            return
        
        chunk_type = getattr(chunk, 'type_code', None) or getattr(chunk, 'chunk_type', 'UNK')
        chunk_id = getattr(chunk, 'chunk_id', 0)
        
        if chunk_type == 'BHAV':
            self._analyze_bhav(chunk)
        elif chunk_type == 'OBJD':
            self._set_status('safe', [
                "OBJD is object definition metadata",
                "Contains GUIDs, catalog info, tuning",
                "No executable code"
            ], f"OBJD #{chunk_id}")
        elif chunk_type in ['SPR2', 'SPR#']:
            self._set_status('safe', [
                "Sprite data is visual only",
                "No game logic"
            ], f"{chunk_type} #{chunk_id}")
        else:
            self._set_status('unknown', [
                f"No specific analysis for {chunk_type}"
            ], f"{chunk_type} #{chunk_id}")
    
    def _on_bhav_selected(self, bhav):
        """Handle BHAV selection."""
        if bhav:
            self._analyze_bhav(bhav)
    
    def _analyze_bhav(self, bhav):
        """Analyze a BHAV chunk for safety."""
        reasons = []
        level = 'safe'
        
        bhav_id = getattr(bhav, 'chunk_id', 0)
        name = getattr(bhav, 'name', f'BHAV #{bhav_id}')
        
        instructions = getattr(bhav, 'instructions', [])
        
        for instr in instructions:
            opcode = getattr(instr, 'opcode', 0)
            
            if opcode in self.DANGEROUS_OPCODES:
                level = 'unsafe' if level != 'unsafe' else level
                reasons.append(f"⚠ Opcode 0x{opcode:04X}: {self.DANGEROUS_OPCODES[opcode]}")
            elif opcode >= 0x1000:
                # Private BHAV call
                if level == 'safe':
                    level = 'warning'
                reasons.append(f"→ Calls private BHAV 0x{opcode:04X}")
            elif opcode >= 0x0100:
                # Semi-global call
                if level == 'safe':
                    level = 'warning'
                reasons.append(f"→ Calls semi-global 0x{opcode:04X}")
        
        if not reasons:
            reasons = ["No dangerous patterns detected", "Read-only or simple logic"]
        
        self._set_status(level, reasons, name)
    
    def _analyze_bhav_by_id(self, bhav_id: int):
        """Analyze BHAV by ID when we don't have the chunk."""
        # Try to get from current IFF
        if STATE.current_iff and hasattr(STATE.current_iff, 'chunks'):
            for chunk in STATE.current_iff.chunks:
                if getattr(chunk, 'chunk_id', None) == bhav_id:
                    chunk_type = getattr(chunk, 'type_code', None)
                    if chunk_type == 'BHAV':
                        self._analyze_bhav(chunk)
                        return
        
        # Fallback
        self._set_status('unknown', [
            f"BHAV #{bhav_id} not loaded",
            "Load the file to analyze"
        ], f"BHAV #{bhav_id}")
    
    def _set_status(self, level: str, reasons: list, resource: str = ""):
        """Set the safety status."""
        self.current_level = level
        self.current_reasons = reasons
        
        config = self.SAFETY_LEVELS.get(level, self.SAFETY_LEVELS['unknown'])
        
        # Update badge
        dpg.set_value("safety_icon", config['icon'])
        dpg.configure_item("safety_icon", color=config['color'])
        
        dpg.set_value("safety_label", config['label'])
        dpg.configure_item("safety_label", color=config['color'])
        
        # Update detail panel
        dpg.set_value("safety_resource", resource or "No selection")
        
        # Clear and rebuild reasons
        dpg.delete_item("safety_reasons", children_only=True)
        for reason in reasons[:5]:  # Max 5 reasons
            dpg.add_text(reason, parent="safety_reasons", 
                        color=config['color'], wrap=250)
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
