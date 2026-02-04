"""
Diff / Compare View — Side-by-Side BHAV Comparison

Compare:
- BHAV A vs BHAV B
- Same BHAV across expansions
- Side-by-side or inline diff

Critical for forensic analysis across game versions.
"""

import dearpygui.dearpygui as dpg
from typing import Optional, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE


class DiffViewPanel:
    """
    Side-by-side BHAV comparison panel.
    
    Features:
    - Load two BHAVs for comparison
    - Opcode-level diff highlighting
    - Cross-expansion comparison
    - Instruction-by-instruction analysis
    """
    
    TAG = "diff_view"
    LEFT_TAG = "diff_left"
    RIGHT_TAG = "diff_right"
    
    # Colors
    COLORS = {
        'added': (76, 175, 80, 255),      # Green - new instruction
        'removed': (244, 67, 54, 255),    # Red - removed instruction
        'changed': (255, 193, 7, 255),    # Yellow - modified
        'same': (136, 136, 136, 255),     # Grey - unchanged
        'header': (0, 212, 255, 255),     # Cyan - headers
        'text': (224, 224, 224, 255),
        'dim': (102, 102, 102, 255),
    }
    
    def __init__(self, width: int = 900, height: int = 600, pos: tuple = (50, 50)):
        self.width = width
        self.height = height
        self.pos = pos
        self.left_bhav = None
        self.right_bhav = None
        self.diff_results = []
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the diff view panel."""
        with dpg.window(
            label="🔍 Diff / Compare",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            show=False,
            on_close=self._on_close
        ):
            # Toolbar
            with dpg.group(horizontal=True):
                dpg.add_text("Compare:", color=self.COLORS['dim'])
                dpg.add_button(
                    label="Load Left",
                    callback=self._load_left,
                    width=80
                )
                dpg.add_button(
                    label="Load Right",
                    callback=self._load_right,
                    width=80
                )
                dpg.add_separator()
                dpg.add_button(
                    label="Compare",
                    callback=self._run_diff,
                    width=80
                )
                dpg.add_button(
                    label="Clear",
                    callback=self._clear,
                    width=60
                )
                dpg.add_spacer(width=20)
                dpg.add_text("Changes: ", color=self.COLORS['dim'])
                dpg.add_text("0", tag="diff_change_count", color=self.COLORS['text'])
            
            dpg.add_separator()
            
            # Source labels
            with dpg.group(horizontal=True):
                with dpg.group(width=self.width // 2 - 20):
                    dpg.add_text("← Left (Base)", color=self.COLORS['header'])
                    dpg.add_text("No BHAV loaded", tag="diff_left_name", 
                               color=self.COLORS['dim'])
                with dpg.group(width=self.width // 2 - 20):
                    dpg.add_text("→ Right (Compare)", color=self.COLORS['header'])
                    dpg.add_text("No BHAV loaded", tag="diff_right_name", 
                               color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Side-by-side view
            with dpg.group(horizontal=True):
                # Left pane
                with dpg.child_window(
                    tag=self.LEFT_TAG,
                    width=self.width // 2 - 15,
                    height=-50,
                    border=True
                ):
                    dpg.add_text("Load a BHAV to compare", color=self.COLORS['dim'])
                
                # Right pane
                with dpg.child_window(
                    tag=self.RIGHT_TAG,
                    width=self.width // 2 - 15,
                    height=-50,
                    border=True
                ):
                    dpg.add_text("Load a BHAV to compare", color=self.COLORS['dim'])
            
            # Legend
            with dpg.group(horizontal=True):
                dpg.add_text("Legend:", color=self.COLORS['dim'])
                dpg.add_text("● Added", color=self.COLORS['added'])
                dpg.add_text("● Removed", color=self.COLORS['removed'])
                dpg.add_text("● Changed", color=self.COLORS['changed'])
                dpg.add_text("● Same", color=self.COLORS['same'])
    
    def _subscribe_events(self):
        """Subscribe to events."""
        EventBus.subscribe(Events.BHAV_SELECTED, self._on_bhav_for_compare)
    
    def _on_bhav_for_compare(self, bhav):
        """Handle BHAV selection - offer to load for comparison."""
        # Don't auto-load, user must explicitly choose left/right
        pass
    
    def _load_left(self):
        """Load current BHAV as left side."""
        if STATE.current_bhav:
            self.left_bhav = STATE.current_bhav
            name = getattr(self.left_bhav, 'name', f"BHAV #{self.left_bhav.chunk_id}")
            if dpg.does_item_exist("diff_left_name"):
                dpg.set_value("diff_left_name", name)
            self._render_left()
    
    def _load_right(self):
        """Load current BHAV as right side."""
        if STATE.current_bhav:
            self.right_bhav = STATE.current_bhav
            name = getattr(self.right_bhav, 'name', f"BHAV #{self.right_bhav.chunk_id}")
            if dpg.does_item_exist("diff_right_name"):
                dpg.set_value("diff_right_name", name)
            self._render_right()
    
    def _render_left(self):
        """Render left BHAV instructions."""
        if not dpg.does_item_exist(self.LEFT_TAG):
            return
        
        # Clear existing
        for child in dpg.get_item_children(self.LEFT_TAG, 1) or []:
            dpg.delete_item(child)
        
        if not self.left_bhav or not hasattr(self.left_bhav, 'instructions'):
            dpg.add_text("No instructions", parent=self.LEFT_TAG, color=self.COLORS['dim'])
            return
        
        for idx, instr in enumerate(self.left_bhav.instructions):
            self._render_instruction(self.LEFT_TAG, idx, instr, 'same')
    
    def _render_right(self):
        """Render right BHAV instructions."""
        if not dpg.does_item_exist(self.RIGHT_TAG):
            return
        
        # Clear existing
        for child in dpg.get_item_children(self.RIGHT_TAG, 1) or []:
            dpg.delete_item(child)
        
        if not self.right_bhav or not hasattr(self.right_bhav, 'instructions'):
            dpg.add_text("No instructions", parent=self.RIGHT_TAG, color=self.COLORS['dim'])
            return
        
        for idx, instr in enumerate(self.right_bhav.instructions):
            self._render_instruction(self.RIGHT_TAG, idx, instr, 'same')
    
    def _render_instruction(self, parent: str, idx: int, instr, status: str):
        """Render a single instruction line."""
        opcode = getattr(instr, 'opcode', 0)
        true_target = getattr(instr, 'true_target', 0)
        false_target = getattr(instr, 'false_target', 0)
        operands = getattr(instr, 'operands', b'')
        
        color = self.COLORS.get(status, self.COLORS['same'])
        
        with dpg.group(horizontal=True, parent=parent):
            # Line number
            dpg.add_text(f"{idx:03d}", color=self.COLORS['dim'])
            # Opcode
            dpg.add_text(f"0x{opcode:04X}", color=color)
            # Targets
            dpg.add_text(f"T:{true_target:02X} F:{false_target:02X}", color=self.COLORS['dim'])
            # Status indicator
            if status == 'added':
                dpg.add_text("+", color=color)
            elif status == 'removed':
                dpg.add_text("-", color=color)
            elif status == 'changed':
                dpg.add_text("~", color=color)
    
    def _run_diff(self):
        """Run diff comparison between left and right."""
        if not self.left_bhav or not self.right_bhav:
            return
        
        if not hasattr(self.left_bhav, 'instructions') or not hasattr(self.right_bhav, 'instructions'):
            return
        
        left_instrs = self.left_bhav.instructions
        right_instrs = self.right_bhav.instructions
        
        # Compute diff using LCS-style algorithm
        self.diff_results = self._compute_diff(left_instrs, right_instrs)
        
        # Render with diff highlighting
        self._render_diff()
        
        # Update stats
        changes = sum(1 for d in self.diff_results if d['status'] != 'same')
        if dpg.does_item_exist("diff_change_count"):
            dpg.set_value("diff_change_count", str(changes))
    
    def _compute_diff(self, left: list, right: list) -> list:
        """Compute instruction-level diff."""
        results = []
        
        # Simple comparison by index
        max_len = max(len(left), len(right))
        
        for i in range(max_len):
            left_instr = left[i] if i < len(left) else None
            right_instr = right[i] if i < len(right) else None
            
            if left_instr is None:
                results.append({
                    'idx': i,
                    'left': None,
                    'right': right_instr,
                    'status': 'added'
                })
            elif right_instr is None:
                results.append({
                    'idx': i,
                    'left': left_instr,
                    'right': None,
                    'status': 'removed'
                })
            elif self._instructions_equal(left_instr, right_instr):
                results.append({
                    'idx': i,
                    'left': left_instr,
                    'right': right_instr,
                    'status': 'same'
                })
            else:
                results.append({
                    'idx': i,
                    'left': left_instr,
                    'right': right_instr,
                    'status': 'changed'
                })
        
        return results
    
    def _instructions_equal(self, a, b) -> bool:
        """Check if two instructions are equal."""
        if a is None or b is None:
            return False
        
        # Compare key fields
        if getattr(a, 'opcode', 0) != getattr(b, 'opcode', 0):
            return False
        if getattr(a, 'true_target', 0) != getattr(b, 'true_target', 0):
            return False
        if getattr(a, 'false_target', 0) != getattr(b, 'false_target', 0):
            return False
        
        # Compare operands
        a_ops = getattr(a, 'operands', b'')
        b_ops = getattr(b, 'operands', b'')
        if a_ops != b_ops:
            return False
        
        return True
    
    def _render_diff(self):
        """Render both panes with diff highlighting."""
        # Clear both panes
        for tag in [self.LEFT_TAG, self.RIGHT_TAG]:
            if dpg.does_item_exist(tag):
                for child in dpg.get_item_children(tag, 1) or []:
                    dpg.delete_item(child)
        
        # Render diff results
        for result in self.diff_results:
            idx = result['idx']
            status = result['status']
            
            # Left pane
            if result['left']:
                self._render_instruction(self.LEFT_TAG, idx, result['left'], 
                    'removed' if status == 'removed' else ('changed' if status == 'changed' else 'same'))
            elif status == 'added':
                dpg.add_text(f"{idx:03d} ---", parent=self.LEFT_TAG, color=self.COLORS['dim'])
            
            # Right pane
            if result['right']:
                self._render_instruction(self.RIGHT_TAG, idx, result['right'],
                    'added' if status == 'added' else ('changed' if status == 'changed' else 'same'))
            elif status == 'removed':
                dpg.add_text(f"{idx:03d} ---", parent=self.RIGHT_TAG, color=self.COLORS['dim'])
    
    def _clear(self):
        """Clear both sides."""
        self.left_bhav = None
        self.right_bhav = None
        self.diff_results = []
        
        if dpg.does_item_exist("diff_left_name"):
            dpg.set_value("diff_left_name", "No BHAV loaded")
        if dpg.does_item_exist("diff_right_name"):
            dpg.set_value("diff_right_name", "No BHAV loaded")
        if dpg.does_item_exist("diff_change_count"):
            dpg.set_value("diff_change_count", "0")
        
        for tag in [self.LEFT_TAG, self.RIGHT_TAG]:
            if dpg.does_item_exist(tag):
                for child in dpg.get_item_children(tag, 1) or []:
                    dpg.delete_item(child)
                dpg.add_text("Load a BHAV to compare", parent=tag, color=self.COLORS['dim'])
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
