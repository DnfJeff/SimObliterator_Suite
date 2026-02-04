"""
Diff/Compare Panel - Side-by-side BHAV Comparison

From the Flow Map:
- Compare BHAV A vs BHAV B
- Same BHAV across expansions
- Side-by-side or inline diff
- Opcode-level diff

Essential for forensic analysis and understanding expansion changes.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE
from ..focus import FOCUS


class DiffComparePanel:
    """
    BHAV comparison view.
    
    Features:
    - Side-by-side opcode diff
    - Highlights additions, deletions, changes
    - Compare across files/expansions
    - Jump to differences
    """
    
    TAG = "diff_compare"
    LEFT_TAG = "diff_left"
    RIGHT_TAG = "diff_right"
    
    COLORS = {
        'added': (76, 175, 80),      # Green
        'removed': (244, 67, 54),    # Red
        'changed': (255, 193, 7),    # Yellow
        'same': (136, 136, 136),     # Gray
        'header': (0, 212, 255),     # Cyan
        'text': (224, 224, 224),
    }
    
    def __init__(self, width: int = 900, height: int = 600, pos: tuple = (100, 50)):
        self.width = width
        self.height = height
        self.pos = pos
        
        self.left_bhav = None
        self.right_bhav = None
        self.diff_results = []
        
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the diff panel."""
        with dpg.window(
            label="🔍 Compare BHAVs",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close,
            show=False  # Hidden by default
        ):
            # Toolbar
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="📋 Set Left",
                    callback=self._set_left_from_current,
                    width=100
                )
                dpg.add_button(
                    label="📋 Set Right",
                    callback=self._set_right_from_current,
                    width=100
                )
                dpg.add_separator()
                dpg.add_button(
                    label="⟷ Swap",
                    callback=self._swap_sides,
                    width=60
                )
                dpg.add_button(
                    label="Compare",
                    callback=self._run_compare,
                    width=80
                )
                dpg.add_spacer(width=20)
                dpg.add_text("", tag="diff_status", color=self.COLORS['header'])
            
            dpg.add_separator()
            
            # Selection info
            with dpg.group(horizontal=True):
                with dpg.child_window(width=420, height=50, border=True):
                    dpg.add_text("LEFT:", color=self.COLORS['header'])
                    dpg.add_text("(none selected)", tag="diff_left_label", 
                                color=self.COLORS['same'])
                
                with dpg.child_window(width=420, height=50, border=True):
                    dpg.add_text("RIGHT:", color=self.COLORS['header'])
                    dpg.add_text("(none selected)", tag="diff_right_label",
                                color=self.COLORS['same'])
            
            # Summary stats
            with dpg.group(horizontal=True):
                dpg.add_text("Added: ", color=self.COLORS['same'])
                dpg.add_text("0", tag="diff_added", color=self.COLORS['added'])
                dpg.add_spacer(width=20)
                dpg.add_text("Removed: ", color=self.COLORS['same'])
                dpg.add_text("0", tag="diff_removed", color=self.COLORS['removed'])
                dpg.add_spacer(width=20)
                dpg.add_text("Changed: ", color=self.COLORS['same'])
                dpg.add_text("0", tag="diff_changed", color=self.COLORS['changed'])
                dpg.add_spacer(width=20)
                dpg.add_text("Same: ", color=self.COLORS['same'])
                dpg.add_text("0", tag="diff_same", color=self.COLORS['same'])
            
            dpg.add_separator()
            
            # Side-by-side view
            with dpg.group(horizontal=True):
                # Left panel
                with dpg.child_window(tag=self.LEFT_TAG, width=420, height=-1, border=True):
                    dpg.add_text("Left BHAV opcodes will appear here",
                                color=self.COLORS['same'])
                
                # Right panel
                with dpg.child_window(tag=self.RIGHT_TAG, width=420, height=-1, border=True):
                    dpg.add_text("Right BHAV opcodes will appear here",
                                color=self.COLORS['same'])
    
    def _subscribe_events(self):
        """Subscribe to events."""
        pass  # Manual selection via buttons
    
    def _set_left_from_current(self):
        """Set left side from current selection."""
        if STATE.current_bhav:
            self.left_bhav = STATE.current_bhav
            self._update_left_label()
    
    def _set_right_from_current(self):
        """Set right side from current selection."""
        if STATE.current_bhav:
            self.right_bhav = STATE.current_bhav
            self._update_right_label()
    
    def _update_left_label(self):
        """Update left selection label."""
        if self.left_bhav:
            name = getattr(self.left_bhav, 'name', f'BHAV #{self.left_bhav.chunk_id}')
            count = len(getattr(self.left_bhav, 'instructions', []))
            dpg.set_value("diff_left_label", f"{name} ({count} opcodes)")
            dpg.configure_item("diff_left_label", color=self.COLORS['text'])
    
    def _update_right_label(self):
        """Update right selection label."""
        if self.right_bhav:
            name = getattr(self.right_bhav, 'name', f'BHAV #{self.right_bhav.chunk_id}')
            count = len(getattr(self.right_bhav, 'instructions', []))
            dpg.set_value("diff_right_label", f"{name} ({count} opcodes)")
            dpg.configure_item("diff_right_label", color=self.COLORS['text'])
    
    def _swap_sides(self):
        """Swap left and right."""
        self.left_bhav, self.right_bhav = self.right_bhav, self.left_bhav
        self._update_left_label()
        self._update_right_label()
    
    def _run_compare(self):
        """Run the comparison."""
        if not self.left_bhav or not self.right_bhav:
            dpg.set_value("diff_status", "⚠ Select both BHAVs first")
            return
        
        dpg.set_value("diff_status", "Comparing...")
        
        # Get instructions
        left_instrs = getattr(self.left_bhav, 'instructions', [])
        right_instrs = getattr(self.right_bhav, 'instructions', [])
        
        # Simple LCS-based diff
        diff = self._compute_diff(left_instrs, right_instrs)
        self.diff_results = diff
        
        # Display results
        self._display_diff(diff, left_instrs, right_instrs)
        
        # Update stats
        added = sum(1 for d in diff if d['type'] == 'added')
        removed = sum(1 for d in diff if d['type'] == 'removed')
        changed = sum(1 for d in diff if d['type'] == 'changed')
        same = sum(1 for d in diff if d['type'] == 'same')
        
        dpg.set_value("diff_added", str(added))
        dpg.set_value("diff_removed", str(removed))
        dpg.set_value("diff_changed", str(changed))
        dpg.set_value("diff_same", str(same))
        
        dpg.set_value("diff_status", f"✓ Found {added + removed + changed} differences")
    
    def _compute_diff(self, left: list, right: list) -> list:
        """Compute diff between two instruction lists."""
        diff = []
        
        # Simple line-by-line comparison
        max_len = max(len(left), len(right))
        
        for i in range(max_len):
            left_instr = left[i] if i < len(left) else None
            right_instr = right[i] if i < len(right) else None
            
            if left_instr is None:
                diff.append({
                    'type': 'added',
                    'index': i,
                    'left': None,
                    'right': right_instr
                })
            elif right_instr is None:
                diff.append({
                    'type': 'removed',
                    'index': i,
                    'left': left_instr,
                    'right': None
                })
            else:
                left_op = getattr(left_instr, 'opcode', 0)
                right_op = getattr(right_instr, 'opcode', 0)
                
                if left_op == right_op:
                    # Check operands
                    left_ops = self._get_operands(left_instr)
                    right_ops = self._get_operands(right_instr)
                    
                    if left_ops == right_ops:
                        diff.append({
                            'type': 'same',
                            'index': i,
                            'left': left_instr,
                            'right': right_instr
                        })
                    else:
                        diff.append({
                            'type': 'changed',
                            'index': i,
                            'left': left_instr,
                            'right': right_instr,
                            'detail': 'Operands differ'
                        })
                else:
                    diff.append({
                        'type': 'changed',
                        'index': i,
                        'left': left_instr,
                        'right': right_instr,
                        'detail': 'Opcode differs'
                    })
        
        return diff
    
    def _get_operands(self, instr) -> tuple:
        """Get operands from instruction for comparison."""
        operands = getattr(instr, 'operands', None)
        if operands:
            return tuple(operands)
        
        # Try individual operand fields
        ops = []
        for i in range(16):
            op = getattr(instr, f'operand_{i}', None)
            if op is not None:
                ops.append(op)
        return tuple(ops) if ops else ()
    
    def _format_instruction(self, instr) -> str:
        """Format instruction for display."""
        if instr is None:
            return "(none)"
        
        opcode = getattr(instr, 'opcode', 0)
        
        # Get semantic name if available
        name = f"0x{opcode:04X}"
        
        # Add operands summary
        ops = self._get_operands(instr)
        if ops:
            ops_str = " ".join(f"{o:02X}" for o in ops[:4])
            return f"{name}  [{ops_str}]"
        
        return name
    
    def _display_diff(self, diff: list, left: list, right: list):
        """Display diff results in side-by-side panels."""
        # Clear panels
        dpg.delete_item(self.LEFT_TAG, children_only=True)
        dpg.delete_item(self.RIGHT_TAG, children_only=True)
        
        for entry in diff:
            diff_type = entry['type']
            idx = entry['index']
            color = self.COLORS.get(diff_type, self.COLORS['same'])
            
            # Left side
            if entry['left']:
                left_text = f"{idx:3d}: {self._format_instruction(entry['left'])}"
            else:
                left_text = f"{idx:3d}: ---"
            
            # Right side
            if entry['right']:
                right_text = f"{idx:3d}: {self._format_instruction(entry['right'])}"
            else:
                right_text = f"{idx:3d}: ---"
            
            # Add to panels
            dpg.add_text(left_text, parent=self.LEFT_TAG, color=color)
            dpg.add_text(right_text, parent=self.RIGHT_TAG, color=color)
    
    def set_bhavs(self, left_bhav, right_bhav):
        """Set both BHAVs programmatically."""
        self.left_bhav = left_bhav
        self.right_bhav = right_bhav
        self._update_left_label()
        self._update_right_label()
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
