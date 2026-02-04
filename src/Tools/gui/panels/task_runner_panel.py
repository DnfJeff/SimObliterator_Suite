"""
Task/Batch Runner Panel - Automated Analysis Tasks

From the Flow Map:
- "Analyze all BHAVs"
- "Generate full report"
- "Scan for unsafe patterns"

Bridge between interactive tool and platform automation.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE


class TaskRunnerPanel:
    """
    Batch task runner for automated analysis.
    
    Tasks:
    - Analyze All BHAVs
    - Scan for Unsafe Patterns
    - Generate Report
    - Extract All Sprites
    - Validate Dependencies
    """
    
    TAG = "task_runner"
    LOG_TAG = "task_log"
    
    COLORS = {
        'cyan': (0, 212, 255),
        'green': (76, 175, 80),
        'yellow': (255, 193, 7),
        'red': (244, 67, 54),
        'text': (224, 224, 224),
        'dim': (136, 136, 136),
    }
    
    # Available tasks
    TASKS = {
        'analyze_bhavs': {
            'name': 'Analyze All BHAVs',
            'description': 'Analyze every BHAV in current file',
            'icon': '🔍',
        },
        'scan_unsafe': {
            'name': 'Scan Unsafe Patterns',
            'description': 'Find dangerous opcodes across all BHAVs',
            'icon': '⚠',
        },
        'generate_report': {
            'name': 'Generate Report',
            'description': 'Full analysis report to file',
            'icon': '📄',
        },
        'extract_sprites': {
            'name': 'Extract All Sprites',
            'description': 'Export all SPR2 to PNG',
            'icon': '🖼',
        },
        'validate_deps': {
            'name': 'Validate Dependencies',
            'description': 'Check for missing BHAV calls',
            'icon': '🔗',
        },
        'find_duplicates': {
            'name': 'Find Duplicates',
            'description': 'Find identical or similar BHAVs',
            'icon': '👥',
        },
    }
    
    def __init__(self, width: int = 500, height: int = 450, pos: tuple = (200, 100)):
        self.width = width
        self.height = height
        self.pos = pos
        
        self.running = False
        self.current_task = None
        self.progress = 0
        self.results = []
        
        self._create_panel()
    
    def _create_panel(self):
        """Create the task runner panel."""
        with dpg.window(
            label="⚡ Task Runner",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close,
            show=False
        ):
            # Header
            dpg.add_text("Batch Analysis Tasks", color=self.COLORS['cyan'])
            dpg.add_text("Run automated analysis on loaded files",
                        color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Task buttons
            with dpg.collapsing_header(label="📋 Available Tasks", default_open=True):
                for task_id, task in self.TASKS.items():
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label=f"{task['icon']} {task['name']}",
                            callback=lambda s, a, t=task_id: self._run_task(t),
                            width=200
                        )
                        dpg.add_text(task['description'], color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Progress section
            with dpg.collapsing_header(label="📊 Progress", default_open=True):
                with dpg.group(horizontal=True):
                    dpg.add_text("Status: ", color=self.COLORS['dim'])
                    dpg.add_text("Idle", tag="task_status", color=self.COLORS['text'])
                
                dpg.add_progress_bar(
                    tag="task_progress",
                    default_value=0.0,
                    width=-1
                )
                
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Cancel",
                        tag="task_cancel_btn",
                        callback=self._cancel_task,
                        width=80,
                        enabled=False
                    )
                    dpg.add_text("", tag="task_time", color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Results log
            with dpg.collapsing_header(label="📝 Results", default_open=True):
                with dpg.child_window(tag=self.LOG_TAG, height=150, border=True):
                    dpg.add_text("Task results will appear here...",
                                color=self.COLORS['dim'])
    
    def _run_task(self, task_id: str):
        """Run a task."""
        if self.running:
            self._log("⚠ Task already running", self.COLORS['yellow'])
            return
        
        if not STATE.current_iff:
            self._log("⚠ No IFF file loaded", self.COLORS['yellow'])
            return
        
        task = self.TASKS.get(task_id)
        if not task:
            return
        
        self.running = True
        self.current_task = task_id
        self.progress = 0
        
        dpg.configure_item("task_cancel_btn", enabled=True)
        dpg.set_value("task_status", f"Running: {task['name']}...")
        dpg.configure_item("task_status", color=self.COLORS['cyan'])
        
        self._clear_log()
        self._log(f"Starting: {task['name']}", self.COLORS['cyan'])
        
        # Run in thread
        thread = threading.Thread(target=self._execute_task, args=(task_id,))
        thread.daemon = True
        thread.start()
    
    def _execute_task(self, task_id: str):
        """Execute task in background thread."""
        start_time = time.time()
        
        try:
            if task_id == 'analyze_bhavs':
                self._task_analyze_bhavs()
            elif task_id == 'scan_unsafe':
                self._task_scan_unsafe()
            elif task_id == 'generate_report':
                self._task_generate_report()
            elif task_id == 'extract_sprites':
                self._task_extract_sprites()
            elif task_id == 'validate_deps':
                self._task_validate_deps()
            elif task_id == 'find_duplicates':
                self._task_find_duplicates()
            
            elapsed = time.time() - start_time
            self._finish_task(True, f"Completed in {elapsed:.1f}s")
            
        except Exception as e:
            self._finish_task(False, f"Error: {e}")
    
    def _task_analyze_bhavs(self):
        """Analyze all BHAVs in current IFF."""
        chunks = STATE.current_iff.chunks if STATE.current_iff else []
        bhavs = [c for c in chunks if getattr(c, 'type_code', '') == 'BHAV']
        
        total = len(bhavs)
        self._log(f"Found {total} BHAVs", self.COLORS['text'])
        
        stats = {'total': total, 'with_calls': 0, 'simple': 0, 'complex': 0}
        
        for i, bhav in enumerate(bhavs):
            if not self.running:
                break
            
            instrs = getattr(bhav, 'instructions', [])
            name = getattr(bhav, 'name', f'#{bhav.chunk_id}')
            
            # Analyze
            call_count = sum(1 for ins in instrs if getattr(ins, 'opcode', 0) >= 0x100)
            
            if call_count > 0:
                stats['with_calls'] += 1
            
            if len(instrs) <= 3:
                stats['simple'] += 1
            elif len(instrs) > 20:
                stats['complex'] += 1
            
            # Update progress
            self.progress = (i + 1) / total
            self._update_progress(self.progress, f"{i+1}/{total}")
        
        self._log(f"With calls: {stats['with_calls']}", self.COLORS['text'])
        self._log(f"Simple (≤3 ops): {stats['simple']}", self.COLORS['text'])
        self._log(f"Complex (>20 ops): {stats['complex']}", self.COLORS['text'])
    
    def _task_scan_unsafe(self):
        """Scan for unsafe opcode patterns."""
        chunks = STATE.current_iff.chunks if STATE.current_iff else []
        bhavs = [c for c in chunks if getattr(c, 'type_code', '') == 'BHAV']
        
        dangerous = {
            0x002E: "Kill Sim",
            0x0024: "Remove Object Instance",
            0x001E: "Create Object",
            0x0002: "Expression (motive change)",
        }
        
        found = []
        total = len(bhavs)
        
        for i, bhav in enumerate(bhavs):
            if not self.running:
                break
            
            instrs = getattr(bhav, 'instructions', [])
            name = getattr(bhav, 'name', f'#{bhav.chunk_id}')
            
            for instr in instrs:
                opcode = getattr(instr, 'opcode', 0)
                if opcode in dangerous:
                    found.append((name, opcode, dangerous[opcode]))
            
            self.progress = (i + 1) / total
            self._update_progress(self.progress, f"{i+1}/{total}")
        
        if found:
            self._log(f"⚠ Found {len(found)} unsafe patterns:", self.COLORS['yellow'])
            for name, op, desc in found[:20]:
                self._log(f"  {name}: 0x{op:04X} ({desc})", self.COLORS['red'])
            if len(found) > 20:
                self._log(f"  ... and {len(found) - 20} more", self.COLORS['dim'])
        else:
            self._log("✓ No unsafe patterns found", self.COLORS['green'])
    
    def _task_generate_report(self):
        """Generate a full report."""
        iff = STATE.current_iff
        if not iff:
            return
        
        report_path = Path(STATE.current_file).with_suffix('.report.txt') \
            if STATE.current_file else Path('report.txt')
        
        self._log(f"Generating report: {report_path.name}", self.COLORS['text'])
        
        lines = []
        lines.append("=" * 60)
        lines.append("SIMOBLITERATOR ANALYSIS REPORT")
        lines.append("=" * 60)
        lines.append(f"File: {STATE.current_file}")
        lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Chunk summary
        chunks = iff.chunks if hasattr(iff, 'chunks') else []
        by_type = {}
        for c in chunks:
            t = getattr(c, 'type_code', 'UNK')
            by_type[t] = by_type.get(t, 0) + 1
        
        lines.append("CHUNK SUMMARY")
        lines.append("-" * 40)
        for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"  {t}: {count}")
        lines.append("")
        
        # Write
        report_path.write_text('\n'.join(lines), encoding='utf-8')
        self._log(f"✓ Saved: {report_path}", self.COLORS['green'])
    
    def _task_extract_sprites(self):
        """Extract all sprites."""
        iff = STATE.current_iff
        if not iff:
            return
        
        chunks = iff.chunks if hasattr(iff, 'chunks') else []
        sprites = [c for c in chunks if getattr(c, 'type_code', '') in ['SPR2', 'SPR#']]
        
        self._log(f"Found {len(sprites)} sprite chunks", self.COLORS['text'])
        self._log("(Full extraction requires PIL - showing preview)", self.COLORS['dim'])
        
        for i, spr in enumerate(sprites[:10]):
            name = getattr(spr, 'name', f'sprite_{spr.chunk_id}')
            self._log(f"  Would extract: {name}.png", self.COLORS['text'])
            
            self.progress = (i + 1) / min(len(sprites), 10)
            self._update_progress(self.progress, f"{i+1}/{min(len(sprites), 10)}")
    
    def _task_validate_deps(self):
        """Validate BHAV dependencies."""
        iff = STATE.current_iff
        if not iff:
            return
        
        chunks = iff.chunks if hasattr(iff, 'chunks') else []
        bhavs = {getattr(c, 'chunk_id', 0): c 
                for c in chunks if getattr(c, 'type_code', '') == 'BHAV'}
        
        missing = []
        total = len(bhavs)
        
        for i, (bhav_id, bhav) in enumerate(bhavs.items()):
            if not self.running:
                break
            
            instrs = getattr(bhav, 'instructions', [])
            
            for instr in instrs:
                opcode = getattr(instr, 'opcode', 0)
                # Private BHAV call range
                if 0x1000 <= opcode < 0x2000:
                    target = opcode
                    if target not in bhavs:
                        name = getattr(bhav, 'name', f'#{bhav_id}')
                        missing.append((name, target))
            
            self.progress = (i + 1) / total
            self._update_progress(self.progress, f"{i+1}/{total}")
        
        if missing:
            self._log(f"⚠ {len(missing)} missing dependencies:", self.COLORS['yellow'])
            for src, target in missing[:15]:
                self._log(f"  {src} → 0x{target:04X}", self.COLORS['red'])
        else:
            self._log("✓ All dependencies resolved", self.COLORS['green'])
    
    def _task_find_duplicates(self):
        """Find duplicate BHAVs."""
        iff = STATE.current_iff
        if not iff:
            return
        
        chunks = iff.chunks if hasattr(iff, 'chunks') else []
        bhavs = [c for c in chunks if getattr(c, 'type_code', '') == 'BHAV']
        
        # Hash by opcode sequence
        by_hash = {}
        for bhav in bhavs:
            instrs = getattr(bhav, 'instructions', [])
            ops = tuple(getattr(i, 'opcode', 0) for i in instrs)
            h = hash(ops)
            
            if h not in by_hash:
                by_hash[h] = []
            by_hash[h].append(bhav)
        
        # Find groups
        dupes = [(h, group) for h, group in by_hash.items() if len(group) > 1]
        
        if dupes:
            self._log(f"Found {len(dupes)} duplicate groups:", self.COLORS['yellow'])
            for h, group in dupes[:10]:
                names = [getattr(b, 'name', f'#{b.chunk_id}') for b in group[:3]]
                self._log(f"  {', '.join(names)}", self.COLORS['text'])
        else:
            self._log("✓ No duplicates found", self.COLORS['green'])
    
    def _update_progress(self, value: float, text: str = ""):
        """Update progress bar (thread-safe)."""
        try:
            dpg.set_value("task_progress", value)
            if text:
                dpg.set_value("task_time", text)
        except:
            pass
    
    def _log(self, message: str, color: tuple = None):
        """Add to log (thread-safe)."""
        try:
            dpg.add_text(message, parent=self.LOG_TAG, 
                        color=color or self.COLORS['text'])
        except:
            pass
    
    def _clear_log(self):
        """Clear the log."""
        dpg.delete_item(self.LOG_TAG, children_only=True)
    
    def _finish_task(self, success: bool, message: str):
        """Finish task execution."""
        self.running = False
        self.current_task = None
        
        dpg.configure_item("task_cancel_btn", enabled=False)
        dpg.set_value("task_progress", 1.0 if success else 0.0)
        
        if success:
            dpg.set_value("task_status", "✓ Complete")
            dpg.configure_item("task_status", color=self.COLORS['green'])
            self._log(f"✓ {message}", self.COLORS['green'])
        else:
            dpg.set_value("task_status", "✗ Failed")
            dpg.configure_item("task_status", color=self.COLORS['red'])
            self._log(f"✗ {message}", self.COLORS['red'])
    
    def _cancel_task(self):
        """Cancel running task."""
        self.running = False
        dpg.set_value("task_status", "Cancelled")
        dpg.configure_item("task_status", color=self.COLORS['yellow'])
        self._log("Task cancelled", self.COLORS['yellow'])
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
