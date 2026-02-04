"""
Task / Batch Runner — Automated Analysis Tasks

Bridge between interactive tool and platform:
- Analyze all BHAVs in file
- Generate full report
- Scan for unsafe patterns
- Batch compare across expansions

Runs in background, shows progress, outputs reports.
"""

import dearpygui.dearpygui as dpg
from typing import Optional, Callable, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_name: str
    status: TaskStatus
    items_processed: int
    items_total: int
    findings: list
    errors: list
    duration_ms: int


class BatchRunnerPanel:
    """
    Batch task runner panel.
    
    Features:
    - Pre-defined analysis tasks
    - Progress tracking
    - Background execution
    - Report generation
    """
    
    TAG = "batch_runner"
    PROGRESS_TAG = "batch_progress"
    OUTPUT_TAG = "batch_output"
    
    COLORS = {
        'cyan': (0, 212, 255, 255),
        'green': (76, 175, 80, 255),
        'yellow': (255, 193, 7, 255),
        'red': (244, 67, 54, 255),
        'text': (224, 224, 224, 255),
        'dim': (136, 136, 136, 255),
    }
    
    # Pre-defined tasks
    TASKS = {
        'analyze_all_bhavs': {
            'name': '🔍 Analyze All BHAVs',
            'description': 'Analyze every BHAV in current file for patterns and safety',
        },
        'find_unsafe': {
            'name': '⚠️ Find Unsafe Patterns',
            'description': 'Scan all BHAVs for potentially dangerous opcodes',
        },
        'generate_report': {
            'name': '📄 Generate Full Report',
            'description': 'Create comprehensive analysis report of current file',
        },
        'count_opcodes': {
            'name': '📊 Opcode Distribution',
            'description': 'Count and analyze opcode usage across all BHAVs',
        },
        'find_dead_code': {
            'name': '💀 Find Dead Code',
            'description': 'Identify unreachable instructions in BHAVs',
        },
        'cross_reference': {
            'name': '🔗 Cross Reference',
            'description': 'Build call graph of all BHAV references',
        },
    }
    
    def __init__(self, width: int = 600, height: int = 500, pos: tuple = (100, 100)):
        self.width = width
        self.height = height
        self.pos = pos
        self.current_task = None
        self.is_running = False
        self.should_cancel = False
        self.results: list[TaskResult] = []
        self._create_panel()
    
    def _create_panel(self):
        """Create the batch runner panel."""
        with dpg.window(
            label="🚀 Batch Runner",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            show=False,
            on_close=self._on_close
        ):
            # Header
            dpg.add_text("Batch Analysis Tasks", color=self.COLORS['cyan'])
            dpg.add_text("Run automated analysis on current file", color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Task buttons
            dpg.add_text("Available Tasks:", color=self.COLORS['dim'])
            
            for task_id, task_info in self.TASKS.items():
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label=task_info['name'],
                        callback=lambda s, a, u=task_id: self._run_task(u),
                        width=200,
                        tag=f"task_btn_{task_id}"
                    )
                    dpg.add_text(task_info['description'], color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Progress section
            dpg.add_text("Progress:", color=self.COLORS['dim'])
            
            with dpg.group(horizontal=True):
                dpg.add_text("Idle", tag="batch_status", color=self.COLORS['text'])
                dpg.add_spacer(width=20)
                dpg.add_button(
                    label="Cancel",
                    callback=self._cancel,
                    width=80,
                    tag="batch_cancel_btn",
                    enabled=False
                )
            
            dpg.add_progress_bar(
                tag=self.PROGRESS_TAG,
                default_value=0.0,
                width=-1
            )
            
            dpg.add_text("0 / 0", tag="batch_progress_text", color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Output section
            dpg.add_text("Output:", color=self.COLORS['dim'])
            
            with dpg.child_window(tag=self.OUTPUT_TAG, height=-40, border=True):
                dpg.add_text("Run a task to see output...", color=self.COLORS['dim'])
            
            # Footer buttons
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Clear Output",
                    callback=self._clear_output,
                    width=100
                )
                dpg.add_button(
                    label="Export Report",
                    callback=self._export_report,
                    width=100
                )
    
    def _run_task(self, task_id: str):
        """Run a specific task."""
        if self.is_running:
            self._log("Another task is already running", "warning")
            return
        
        if not STATE.current_iff:
            self._log("No IFF file loaded", "error")
            return
        
        self.current_task = task_id
        self.is_running = True
        self.should_cancel = False
        
        # Update UI
        dpg.set_value("batch_status", f"Running: {self.TASKS[task_id]['name']}")
        dpg.configure_item("batch_cancel_btn", enabled=True)
        
        # Disable task buttons
        for tid in self.TASKS:
            if dpg.does_item_exist(f"task_btn_{tid}"):
                dpg.configure_item(f"task_btn_{tid}", enabled=False)
        
        # Run task based on type
        if task_id == 'analyze_all_bhavs':
            self._task_analyze_all_bhavs()
        elif task_id == 'find_unsafe':
            self._task_find_unsafe()
        elif task_id == 'generate_report':
            self._task_generate_report()
        elif task_id == 'count_opcodes':
            self._task_count_opcodes()
        elif task_id == 'find_dead_code':
            self._task_find_dead_code()
        elif task_id == 'cross_reference':
            self._task_cross_reference()
        
        self._finish_task()
    
    def _finish_task(self):
        """Clean up after task completion."""
        self.is_running = False
        self.current_task = None
        
        status = "Completed" if not self.should_cancel else "Cancelled"
        dpg.set_value("batch_status", status)
        dpg.configure_item("batch_cancel_btn", enabled=False)
        
        # Re-enable task buttons
        for tid in self.TASKS:
            if dpg.does_item_exist(f"task_btn_{tid}"):
                dpg.configure_item(f"task_btn_{tid}", enabled=True)
    
    def _cancel(self):
        """Cancel current task."""
        self.should_cancel = True
        self._log("Cancelling...", "warning")
    
    def _update_progress(self, current: int, total: int):
        """Update progress bar."""
        progress = current / total if total > 0 else 0
        if dpg.does_item_exist(self.PROGRESS_TAG):
            dpg.set_value(self.PROGRESS_TAG, progress)
        if dpg.does_item_exist("batch_progress_text"):
            dpg.set_value("batch_progress_text", f"{current} / {total}")
    
    def _log(self, message: str, level: str = "info"):
        """Log to output panel."""
        if not dpg.does_item_exist(self.OUTPUT_TAG):
            return
        
        color = self.COLORS['text']
        if level == "warning":
            color = self.COLORS['yellow']
        elif level == "error":
            color = self.COLORS['red']
        elif level == "success":
            color = self.COLORS['green']
        
        dpg.add_text(message, parent=self.OUTPUT_TAG, color=color)
    
    def _clear_output(self):
        """Clear output panel."""
        if dpg.does_item_exist(self.OUTPUT_TAG):
            for child in dpg.get_item_children(self.OUTPUT_TAG, 1) or []:
                dpg.delete_item(child)
    
    # ─────────────────────────────────────────────────────────────
    # TASK IMPLEMENTATIONS
    # ─────────────────────────────────────────────────────────────
    
    def _task_analyze_all_bhavs(self):
        """Analyze all BHAVs in current file."""
        self._clear_output()
        self._log("=== Analyzing All BHAVs ===", "info")
        
        iff = STATE.current_iff
        bhavs = [c for c in iff.chunks if getattr(c, 'type_code', '') == 'BHAV']
        
        total = len(bhavs)
        self._log(f"Found {total} BHAVs to analyze", "info")
        
        stats = {'total': 0, 'with_instructions': 0, 'formats': {}}
        
        for idx, bhav in enumerate(bhavs):
            if self.should_cancel:
                break
            
            self._update_progress(idx + 1, total)
            
            stats['total'] += 1
            
            if hasattr(bhav, 'instructions') and bhav.instructions:
                stats['with_instructions'] += 1
                instr_count = len(bhav.instructions)
            else:
                instr_count = 0
            
            # Track format versions
            fmt = getattr(bhav, 'format_', 0)
            stats['formats'][fmt] = stats['formats'].get(fmt, 0) + 1
            
            name = getattr(bhav, 'name', f"#{bhav.chunk_id}")
            self._log(f"  BHAV {bhav.chunk_id}: {name} ({instr_count} instr)")
        
        self._log("", "info")
        self._log("=== Summary ===", "success")
        self._log(f"Total BHAVs: {stats['total']}", "info")
        self._log(f"With instructions: {stats['with_instructions']}", "info")
        self._log(f"Format distribution: {stats['formats']}", "info")
    
    def _task_find_unsafe(self):
        """Find unsafe opcode patterns."""
        self._clear_output()
        self._log("=== Scanning for Unsafe Patterns ===", "warning")
        
        dangerous_opcodes = {
            0x002C: "Kill Object",
            0x0021: "Global Event",
            0x0031: "Set Object",
            0x001C: "Push Interaction",
        }
        
        iff = STATE.current_iff
        bhavs = [c for c in iff.chunks if getattr(c, 'type_code', '') == 'BHAV']
        
        total = len(bhavs)
        findings = []
        
        for idx, bhav in enumerate(bhavs):
            if self.should_cancel:
                break
            
            self._update_progress(idx + 1, total)
            
            if not hasattr(bhav, 'instructions'):
                continue
            
            for i, instr in enumerate(bhav.instructions):
                opcode = getattr(instr, 'opcode', 0)
                if opcode in dangerous_opcodes:
                    name = getattr(bhav, 'name', f"#{bhav.chunk_id}")
                    findings.append({
                        'bhav': name,
                        'bhav_id': bhav.chunk_id,
                        'instr': i,
                        'opcode': opcode,
                        'desc': dangerous_opcodes[opcode]
                    })
        
        self._log("", "info")
        if findings:
            self._log(f"⚠ Found {len(findings)} potentially unsafe operations:", "warning")
            for f in findings[:50]:  # Limit output
                self._log(f"  {f['bhav']} @ {f['instr']}: {f['desc']} (0x{f['opcode']:04X})", "warning")
            if len(findings) > 50:
                self._log(f"  ... and {len(findings) - 50} more", "dim")
        else:
            self._log("✓ No unsafe patterns found!", "success")
    
    def _task_generate_report(self):
        """Generate comprehensive report."""
        self._clear_output()
        self._log("=== Generating Full Report ===", "info")
        
        iff = STATE.current_iff
        
        # Chunk type distribution
        type_counts = {}
        for chunk in iff.chunks:
            t = getattr(chunk, 'type_code', 'UNK')
            type_counts[t] = type_counts.get(t, 0) + 1
        
        self._log("", "info")
        self._log("Chunk Type Distribution:", "info")
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
            self._log(f"  {t}: {c}", "info")
        
        # BHAV analysis
        bhavs = [c for c in iff.chunks if getattr(c, 'type_code', '') == 'BHAV']
        total_instructions = 0
        for bhav in bhavs:
            if hasattr(bhav, 'instructions'):
                total_instructions += len(bhav.instructions)
        
        self._log("", "info")
        self._log("BHAV Statistics:", "info")
        self._log(f"  Total BHAVs: {len(bhavs)}", "info")
        self._log(f"  Total Instructions: {total_instructions}", "info")
        self._log(f"  Avg per BHAV: {total_instructions / len(bhavs) if bhavs else 0:.1f}", "info")
        
        self._log("", "success")
        self._log("Report generation complete!", "success")
        
        self._update_progress(1, 1)
    
    def _task_count_opcodes(self):
        """Count opcode usage distribution."""
        self._clear_output()
        self._log("=== Opcode Distribution ===", "info")
        
        iff = STATE.current_iff
        bhavs = [c for c in iff.chunks if getattr(c, 'type_code', '') == 'BHAV']
        
        opcode_counts = {}
        total = len(bhavs)
        
        for idx, bhav in enumerate(bhavs):
            if self.should_cancel:
                break
            
            self._update_progress(idx + 1, total)
            
            if not hasattr(bhav, 'instructions'):
                continue
            
            for instr in bhav.instructions:
                opcode = getattr(instr, 'opcode', 0)
                opcode_counts[opcode] = opcode_counts.get(opcode, 0) + 1
        
        self._log("", "info")
        self._log("Top 20 Most Used Opcodes:", "info")
        
        sorted_opcodes = sorted(opcode_counts.items(), key=lambda x: -x[1])
        for opcode, count in sorted_opcodes[:20]:
            self._log(f"  0x{opcode:04X}: {count}", "info")
        
        self._log("", "info")
        self._log(f"Total unique opcodes: {len(opcode_counts)}", "success")
    
    def _task_find_dead_code(self):
        """Find unreachable instructions."""
        self._clear_output()
        self._log("=== Finding Dead Code ===", "info")
        
        iff = STATE.current_iff
        bhavs = [c for c in iff.chunks if getattr(c, 'type_code', '') == 'BHAV']
        
        total = len(bhavs)
        dead_code_bhavs = []
        
        for idx, bhav in enumerate(bhavs):
            if self.should_cancel:
                break
            
            self._update_progress(idx + 1, total)
            
            if not hasattr(bhav, 'instructions') or len(bhav.instructions) < 2:
                continue
            
            # Simple reachability: start from 0, follow targets
            reachable = set()
            to_visit = [0]
            
            while to_visit:
                i = to_visit.pop()
                if i in reachable or i >= len(bhav.instructions):
                    continue
                reachable.add(i)
                
                instr = bhav.instructions[i]
                true_t = getattr(instr, 'true_target', 0)
                false_t = getattr(instr, 'false_target', 0)
                
                # Special targets
                if true_t < 0xFD:
                    to_visit.append(true_t)
                if false_t < 0xFD:
                    to_visit.append(false_t)
            
            unreachable = len(bhav.instructions) - len(reachable)
            if unreachable > 0:
                name = getattr(bhav, 'name', f"#{bhav.chunk_id}")
                dead_code_bhavs.append((name, bhav.chunk_id, unreachable))
        
        self._log("", "info")
        if dead_code_bhavs:
            self._log(f"Found {len(dead_code_bhavs)} BHAVs with potentially dead code:", "warning")
            for name, bid, count in dead_code_bhavs[:30]:
                self._log(f"  {name} (#{bid}): {count} unreachable instructions", "warning")
        else:
            self._log("✓ No dead code found!", "success")
    
    def _task_cross_reference(self):
        """Build BHAV call graph."""
        self._clear_output()
        self._log("=== Building Cross Reference Graph ===", "info")
        
        iff = STATE.current_iff
        bhavs = [c for c in iff.chunks if getattr(c, 'type_code', '') == 'BHAV']
        
        # Build ID to name map
        id_to_name = {}
        for bhav in bhavs:
            name = getattr(bhav, 'name', f"#{bhav.chunk_id}")
            id_to_name[bhav.chunk_id] = name
        
        # Find call references (opcode 0x0002 with certain operands, or 0x0042 GoSub)
        call_graph = {}
        total = len(bhavs)
        
        for idx, bhav in enumerate(bhavs):
            if self.should_cancel:
                break
            
            self._update_progress(idx + 1, total)
            
            if not hasattr(bhav, 'instructions'):
                continue
            
            calls = set()
            for instr in bhav.instructions:
                opcode = getattr(instr, 'opcode', 0)
                # Common call opcodes
                if opcode in [0x0042, 0x0043]:  # GoSub Local/Global
                    # Target BHAV ID is typically in operands
                    ops = getattr(instr, 'operands', b'')
                    if len(ops) >= 2:
                        target_id = ops[0] | (ops[1] << 8)
                        if target_id in id_to_name:
                            calls.add(target_id)
            
            if calls:
                call_graph[bhav.chunk_id] = calls
        
        self._log("", "info")
        self._log("BHAVs with outgoing calls:", "info")
        
        for caller_id, callees in sorted(call_graph.items(), key=lambda x: -len(x[1])):
            caller_name = id_to_name.get(caller_id, f"#{caller_id}")
            self._log(f"  {caller_name} calls:", "info")
            for callee_id in callees:
                callee_name = id_to_name.get(callee_id, f"#{callee_id}")
                self._log(f"    → {callee_name}", "dim")
        
        self._log("", "success")
        self._log(f"Total callers: {len(call_graph)}", "success")
    
    def _export_report(self):
        """Export current output to file."""
        # Would save to file - for now just log
        self._log("", "info")
        self._log("Export functionality: would save to report.txt", "info")
    
    def _on_close(self):
        """Handle panel close."""
        if self.is_running:
            self._cancel()
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
