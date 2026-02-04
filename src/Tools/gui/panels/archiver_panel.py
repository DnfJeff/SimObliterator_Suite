"""
ARCHIVER PANEL

Minimal widget for batch game analysis and database building.

Modes:
- FORENSICS: Deep analysis, collect unknowns, pattern detection
- MAPPING: Build comprehensive game maps (behaviors, objects, relationships)  
- PIPELINE: test_pipeline's QUICK/STANDARD/DEEP analysis levels

Features:
- Directory input (game path or specific folder)
- Output directory (for reports/copies)
- Progress tracking with real-time updates
- Automatic unknowns collection (always runs alongside any mode)
- Results summary view
"""

import dearpygui.dearpygui as dpg
import threading
import time
from pathlib import Path
from typing import Optional, Callable
from enum import Enum

from ..events import EventBus, Events
from ..state import STATE
from ..theme import Colors

# Import core modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.unknowns_db import get_unknowns_db
from core.mapping_db import get_mapping_db


class ArchiverMode(Enum):
    """Analysis modes for Archiver."""
    FORENSICS = "forensics"
    MAPPING = "mapping"
    PIPELINE_QUICK = "pipeline_quick"
    PIPELINE_STANDARD = "pipeline_standard"
    PIPELINE_DEEP = "pipeline_deep"


class ArchiverPanel:
    """Archiver - batch analysis and database building tool."""
    
    TAG = "archiver_panel"
    
    _instance = None
    
    def __init__(self, width: int = 450, height: int = 500, pos: tuple = (100, 100)):
        self.width = width
        self.height = height
        self.pos = pos
        
        self.input_dir: Optional[str] = None
        self.output_dir: Optional[str] = None
        self.current_mode: ArchiverMode = ArchiverMode.MAPPING
        
        self._running = False
        self._cancel_requested = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # Progress tracking
        self._total_files = 0
        self._processed_files = 0
        self._current_file = ""
        self._results_text = ""
        
        ArchiverPanel._instance = self
        self._create_panel()
    
    def _create_panel(self):
        """Create the Archiver panel."""
        with dpg.window(
            label="🗄️ Archiver",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            # ═══════════════════════════════════════════════════════════
            # INPUT SECTION
            # ═══════════════════════════════════════════════════════════
            dpg.add_text("📂 Input Directory", color=Colors.ACCENT_BLUE)
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    tag="archiver_input_dir",
                    hint="Game directory or specific folder...",
                    width=-80
                )
                dpg.add_button(
                    label="Browse",
                    callback=self._browse_input
                )
            
            dpg.add_text(
                "Tip: Point to GameData folder for full game scan",
                color=Colors.TEXT_DIM
            )
            
            dpg.add_spacer(height=10)
            
            # ═══════════════════════════════════════════════════════════
            # OUTPUT SECTION (optional)
            # ═══════════════════════════════════════════════════════════
            dpg.add_text("📁 Output Directory (optional)", color=Colors.TEXT_DIM)
            
            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    tag="archiver_output_dir",
                    hint="Leave empty for no file output",
                    width=-80
                )
                dpg.add_button(
                    label="Browse",
                    callback=self._browse_output
                )
            
            dpg.add_spacer(height=15)
            
            # ═══════════════════════════════════════════════════════════
            # MODE SELECTION
            # ═══════════════════════════════════════════════════════════
            dpg.add_text("⚙️ Analysis Mode", color=Colors.ACCENT_BLUE)
            dpg.add_separator()
            
            dpg.add_radio_button(
                tag="archiver_mode",
                items=[
                    "🔍 Forensics (deep unknowns detection)",
                    "🗺️ Mapping (build game structure maps)",
                    "⚡ Pipeline QUICK (fast scan)",
                    "📊 Pipeline STANDARD (balanced)",
                    "🔬 Pipeline DEEP (full analysis)"
                ],
                default_value="🗺️ Mapping (build game structure maps)",
                callback=self._on_mode_changed
            )
            
            dpg.add_spacer(height=5)
            
            # Mode description
            dpg.add_text(
                "Builds behavior library, object registry, chunk maps",
                tag="archiver_mode_desc",
                color=Colors.TEXT_DIM,
                wrap=self.width - 30
            )
            
            dpg.add_spacer(height=5)
            
            # Always-on feature note
            dpg.add_text(
                "✓ Unknowns detection runs on ALL modes",
                color=Colors.ACCENT_GREEN
            )
            
            dpg.add_spacer(height=15)
            
            # ═══════════════════════════════════════════════════════════
            # CONTROL BUTTONS
            # ═══════════════════════════════════════════════════════════
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="▶️ Start Scan",
                    tag="archiver_start_btn",
                    callback=self._start_scan,
                    width=150
                )
                dpg.add_button(
                    label="⏹️ Cancel",
                    tag="archiver_cancel_btn",
                    callback=self._cancel_scan,
                    width=100,
                    enabled=False
                )
                dpg.add_button(
                    label="📋 View DB",
                    callback=self._view_database,
                    width=100
                )
            
            dpg.add_spacer(height=10)
            
            # ═══════════════════════════════════════════════════════════
            # PROGRESS SECTION
            # ═══════════════════════════════════════════════════════════
            dpg.add_text("Progress", color=Colors.ACCENT_BLUE)
            dpg.add_separator()
            
            dpg.add_progress_bar(
                tag="archiver_progress",
                default_value=0.0,
                width=-1
            )
            
            dpg.add_text(
                "Ready",
                tag="archiver_status",
                color=Colors.TEXT_DIM
            )
            
            dpg.add_text(
                "",
                tag="archiver_current_file",
                color=Colors.TEXT_DIM,
                wrap=self.width - 30
            )
            
            dpg.add_spacer(height=10)
            
            # ═══════════════════════════════════════════════════════════
            # RESULTS SECTION
            # ═══════════════════════════════════════════════════════════
            dpg.add_text("📊 Results", color=Colors.ACCENT_BLUE)
            dpg.add_separator()
            
            dpg.add_input_text(
                tag="archiver_results",
                multiline=True,
                readonly=True,
                width=-1,
                height=120,
                default_value="Results will appear here..."
            )
            
            # ═══════════════════════════════════════════════════════════
            # DATABASE STATS
            # ═══════════════════════════════════════════════════════════
            dpg.add_spacer(height=5)
            
            with dpg.group(horizontal=True):
                dpg.add_text("DB Stats:", color=Colors.TEXT_DIM)
                dpg.add_text(
                    "Loading...",
                    tag="archiver_db_stats",
                    color=Colors.TEXT_BRIGHT
                )
            
            # Initial stats refresh
            self._refresh_db_stats()
    
    def _on_mode_changed(self, sender, app_data):
        """Update mode description when mode changes."""
        mode_descriptions = {
            "🔍 Forensics (deep unknowns detection)": 
                "Deep pattern analysis, unknown opcode forensics, behavioral correlation",
            "🗺️ Mapping (build game structure maps)": 
                "Builds behavior library, object registry, chunk maps",
            "⚡ Pipeline QUICK (fast scan)": 
                "Fast enumeration, basic chunk parsing, minimal analysis",
            "📊 Pipeline STANDARD (balanced)": 
                "Full parsing, behavior profiling, trigger extraction",
            "🔬 Pipeline DEEP (full analysis)": 
                "Everything + execution simulation, graph building, cycle detection"
        }
        desc = mode_descriptions.get(app_data, "")
        dpg.set_value("archiver_mode_desc", desc)
        
        # Map to enum
        mode_map = {
            "🔍 Forensics (deep unknowns detection)": ArchiverMode.FORENSICS,
            "🗺️ Mapping (build game structure maps)": ArchiverMode.MAPPING,
            "⚡ Pipeline QUICK (fast scan)": ArchiverMode.PIPELINE_QUICK,
            "📊 Pipeline STANDARD (balanced)": ArchiverMode.PIPELINE_STANDARD,
            "🔬 Pipeline DEEP (full analysis)": ArchiverMode.PIPELINE_DEEP,
        }
        self.current_mode = mode_map.get(app_data, ArchiverMode.MAPPING)
    
    def _browse_input(self):
        """Open directory browser for input."""
        # DearPyGui file dialog
        def callback(sender, app_data):
            if app_data and 'file_path_name' in app_data:
                # For directory, use the containing folder
                path = app_data.get('file_path_name', '')
                if path:
                    dpg.set_value("archiver_input_dir", str(Path(path).parent))
            elif app_data and 'current_path' in app_data:
                dpg.set_value("archiver_input_dir", app_data['current_path'])
        
        with dpg.file_dialog(
            directory_selector=True,
            show=True,
            callback=callback,
            width=500,
            height=400
        ):
            pass
    
    def _browse_output(self):
        """Open directory browser for output."""
        def callback(sender, app_data):
            if app_data and 'current_path' in app_data:
                dpg.set_value("archiver_output_dir", app_data['current_path'])
        
        with dpg.file_dialog(
            directory_selector=True,
            show=True,
            callback=callback,
            width=500,
            height=400
        ):
            pass
    
    def _start_scan(self):
        """Start the scanning process."""
        self.input_dir = dpg.get_value("archiver_input_dir")
        self.output_dir = dpg.get_value("archiver_output_dir") or None
        
        if not self.input_dir or not Path(self.input_dir).exists():
            dpg.set_value("archiver_status", "❌ Invalid input directory!")
            return
        
        self._running = True
        self._cancel_requested = False
        
        # Update UI
        dpg.configure_item("archiver_start_btn", enabled=False)
        dpg.configure_item("archiver_cancel_btn", enabled=True)
        dpg.set_value("archiver_progress", 0.0)
        dpg.set_value("archiver_status", "Starting scan...")
        dpg.set_value("archiver_results", "")
        
        # Start worker thread
        self._worker_thread = threading.Thread(target=self._run_scan, daemon=True)
        self._worker_thread.start()
    
    def _cancel_scan(self):
        """Request scan cancellation."""
        self._cancel_requested = True
        dpg.set_value("archiver_status", "Cancelling...")
    
    def _run_scan(self):
        """Run the scan in background thread."""
        try:
            input_path = Path(self.input_dir)
            
            # Find all FAR/IFF files
            far_files = list(input_path.rglob("*.far"))
            iff_files = list(input_path.rglob("*.iff"))
            
            self._total_files = len(far_files) + len(iff_files)
            self._processed_files = 0
            
            if self._total_files == 0:
                self._update_ui("status", "No FAR or IFF files found!")
                self._scan_complete({"error": "No files found"})
                return
            
            self._update_ui("status", f"Found {len(far_files)} FAR, {len(iff_files)} IFF files")
            
            # Route to appropriate handler
            if self.current_mode == ArchiverMode.FORENSICS:
                results = self._run_forensics(far_files, iff_files)
            elif self.current_mode == ArchiverMode.MAPPING:
                results = self._run_mapping(far_files, iff_files)
            else:
                results = self._run_pipeline(far_files, iff_files)
            
            self._scan_complete(results)
            
        except Exception as e:
            self._update_ui("status", f"❌ Error: {str(e)}")
            self._scan_complete({"error": str(e)})
    
    def _run_forensics(self, far_files, iff_files) -> dict:
        """Run forensics mode."""
        from core.forensic_module import ForensicAnalyzer
        from formats.far.far1 import FAR1Archive
        from formats.iff.iff_file import IffFile
        
        unknowns_db = get_unknowns_db()
        analyzer = ForensicAnalyzer()
        
        results = {
            "mode": "FORENSICS",
            "files_scanned": 0,
            "new_unknown_opcodes": 0,
            "new_unknown_chunks": 0,
            "objects_analyzed": 0
        }
        
        # Process FAR archives
        for far_path in far_files:
            if self._cancel_requested:
                break
            
            self._update_progress(far_path.name)
            
            try:
                archive = FAR1Archive(str(far_path))
                entries = archive.list_entries()
                
                for entry_name in entries:
                    if self._cancel_requested:
                        break
                    
                    if not entry_name.endswith('.iff'):
                        continue
                    
                    try:
                        iff_data = archive.get_entry(entry_name)
                        if iff_data:
                            iff = IffFile.from_bytes(iff_data)
                            self._analyze_iff_for_unknowns(iff, entry_name, unknowns_db, results)
                            results["objects_analyzed"] += 1
                    except Exception:
                        pass
                
                results["files_scanned"] += 1
            except Exception:
                pass
        
        # Process loose IFF files
        for iff_path in iff_files:
            if self._cancel_requested:
                break
            
            self._update_progress(iff_path.name)
            
            try:
                iff = IffFile.from_file(str(iff_path))
                self._analyze_iff_for_unknowns(iff, iff_path.name, unknowns_db, results)
                results["files_scanned"] += 1
                results["objects_analyzed"] += 1
            except Exception:
                pass
        
        # Save database
        unknowns_db.save()
        
        return results
    
    def _run_mapping(self, far_files, iff_files) -> dict:
        """Run mapping mode - build game structure maps."""
        from formats.far.far1 import FAR1Archive
        from formats.iff.iff_file import IffFile
        
        unknowns_db = get_unknowns_db()
        mapping_db = get_mapping_db()
        
        results = {
            "mode": "MAPPING",
            "files_scanned": 0,
            "behaviors_mapped": 0,
            "objects_mapped": 0,
            "new_unknown_opcodes": 0
        }
        
        # Process FAR archives
        for far_path in far_files:
            if self._cancel_requested:
                break
            
            self._update_progress(far_path.name)
            
            try:
                archive = FAR1Archive(str(far_path))
                entries = archive.list_entries()
                
                for entry_name in entries:
                    if self._cancel_requested:
                        break
                    
                    if not entry_name.endswith('.iff'):
                        continue
                    
                    try:
                        iff_data = archive.get_entry(entry_name)
                        if iff_data:
                            iff = IffFile.from_bytes(iff_data)
                            self._map_iff(iff, entry_name, mapping_db, unknowns_db, results)
                    except Exception:
                        pass
                
                results["files_scanned"] += 1
            except Exception:
                pass
        
        # Process loose IFF files
        for iff_path in iff_files:
            if self._cancel_requested:
                break
            
            self._update_progress(iff_path.name)
            
            try:
                iff = IffFile.from_file(str(iff_path))
                self._map_iff(iff, iff_path.name, mapping_db, unknowns_db, results)
                results["files_scanned"] += 1
            except Exception:
                pass
        
        # Save databases
        mapping_db.record_full_scan()
        mapping_db.set_game_path(self.input_dir)
        mapping_db.save()
        unknowns_db.save()
        
        return results
    
    def _run_pipeline(self, far_files, iff_files) -> dict:
        """Run pipeline mode using test_pipeline infrastructure."""
        # Import test_pipeline
        try:
            from test_pipeline import ComprehensiveTestPipeline, AnalysisLevel
        except ImportError:
            return {"error": "Could not import test_pipeline"}
        
        # Map mode to analysis level
        level_map = {
            ArchiverMode.PIPELINE_QUICK: AnalysisLevel.QUICK,
            ArchiverMode.PIPELINE_STANDARD: AnalysisLevel.STANDARD,
            ArchiverMode.PIPELINE_DEEP: AnalysisLevel.DEEP,
        }
        level = level_map.get(self.current_mode, AnalysisLevel.STANDARD)
        
        results = {
            "mode": f"PIPELINE_{level.name}",
            "files_scanned": 0,
            "objects_processed": 0,
            "bhavs_analyzed": 0,
            "errors": []
        }
        
        unknowns_db = get_unknowns_db()
        
        for far_path in far_files:
            if self._cancel_requested:
                break
            
            self._update_progress(far_path.name)
            
            try:
                pipeline = ComprehensiveTestPipeline(level=level)
                pipeline.load_archive(far_path)
                
                if pipeline.archive:
                    entries = pipeline.archive.list_entries()
                    for entry in entries:
                        if self._cancel_requested:
                            break
                        if entry.endswith('.iff'):
                            obj_name = entry.replace('.iff', '')
                            if pipeline.process_object(obj_name):
                                results["objects_processed"] += 1
                                results["bhavs_analyzed"] += pipeline.metrics.total_bhavs
                    
                    # Collect unknowns from pipeline metrics
                    for opcode in pipeline.metrics.unique_unknown_opcodes:
                        if unknowns_db.add_unknown_opcode(opcode, far_path.name):
                            results.setdefault("new_unknown_opcodes", 0)
                            results["new_unknown_opcodes"] += 1
                
                results["files_scanned"] += 1
            except Exception as e:
                results["errors"].append(f"{far_path.name}: {str(e)}")
        
        unknowns_db.save()
        return results
    
    def _analyze_iff_for_unknowns(self, iff, source_name, unknowns_db, results):
        """Analyze IFF for unknown opcodes and chunks."""
        from core.opcode_loader import is_known_opcode
        
        known_chunks = {
            'BHAV', 'TTAB', 'OBJf', 'OBJD', 'TPRP', 'TRCN', 'TTAs',
            'BCON', 'STR#', 'GLOB', 'SLOT', 'DGRP', 'SPR#', 'SPR2',
            'PALT', 'BMP_', 'CTSS', 'rsmp', 'POSI', 'OBJM', 'FAMI'
        }
        
        for chunk in iff.chunks:
            # Check for unknown chunk types
            if chunk.chunk_type not in known_chunks:
                if unknowns_db.add_unknown_chunk(chunk.chunk_type, source_name):
                    results["new_unknown_chunks"] += 1
            
            # Check BHAV instructions for unknown opcodes
            if chunk.chunk_type == 'BHAV' and hasattr(chunk, 'instructions'):
                for inst in chunk.instructions:
                    if hasattr(inst, 'opcode'):
                        if not is_known_opcode(inst.opcode):
                            if unknowns_db.add_unknown_opcode(
                                inst.opcode, 
                                source_name,
                                context={"bhav_id": chunk.chunk_id}
                            ):
                                results["new_unknown_opcodes"] += 1
    
    def _map_iff(self, iff, source_name, mapping_db, unknowns_db, results):
        """Map an IFF file's structure to the database."""
        from core.opcode_loader import is_known_opcode
        
        # Count chunks by type
        chunk_dist = {}
        bhav_count = 0
        ttab_count = 0
        object_type = "OBJECT"
        guid = None
        semi_global = None
        
        for chunk in iff.chunks:
            chunk_dist[chunk.chunk_type] = chunk_dist.get(chunk.chunk_type, 0) + 1
            
            if chunk.chunk_type == 'BHAV':
                bhav_count += 1
                
                # Add to behavior registry
                name = chunk.chunk_label or f"BHAV_{chunk.chunk_id}"
                inst_count = len(chunk.instructions) if hasattr(chunk, 'instructions') else 0
                
                mapping_db.add_behavior(
                    bhav_id=chunk.chunk_id,
                    name=name,
                    owner_file=source_name,
                    instruction_count=inst_count,
                    role=self._classify_bhav_role(chunk),
                    scope="LOCAL"
                )
                results["behaviors_mapped"] += 1
                
                # Check for unknowns
                if hasattr(chunk, 'instructions'):
                    for inst in chunk.instructions:
                        if hasattr(inst, 'opcode') and not is_known_opcode(inst.opcode):
                            unknowns_db.add_unknown_opcode(
                                inst.opcode, source_name, 
                                {"bhav_id": chunk.chunk_id}
                            )
                            results["new_unknown_opcodes"] += 1
            
            elif chunk.chunk_type == 'TTAB':
                ttab_count += len(chunk.interactions) if hasattr(chunk, 'interactions') else 0
            
            elif chunk.chunk_type == 'OBJD':
                if hasattr(chunk, 'object_type'):
                    type_val = int(chunk.object_type) if hasattr(chunk.object_type, '__int__') else chunk.object_type
                    if type_val == 2:
                        object_type = "CHARACTER"
                if hasattr(chunk, 'guid'):
                    guid = chunk.guid
            
            elif chunk.chunk_type == 'GLOB':
                if hasattr(chunk, 'semi_global_name'):
                    semi_global = chunk.semi_global_name
        
        # Detect Global.iff
        if 'global' in source_name.lower() and 'semi' not in source_name.lower():
            object_type = "GLOBAL"
        elif 'semi' in source_name.lower():
            object_type = "SEMI-GLOBAL"
        
        # Add object to registry
        obj_name = source_name.replace('.iff', '')
        mapping_db.add_object(
            object_name=obj_name,
            source_file=source_name,
            object_type=object_type,
            guid=guid,
            bhav_count=bhav_count,
            chunk_types=chunk_dist,
            ttab_count=ttab_count,
            semi_global=semi_global
        )
        mapping_db.add_chunk_distribution(source_name, chunk_dist)
        results["objects_mapped"] += 1
    
    def _classify_bhav_role(self, bhav) -> str:
        """Quick BHAV role classification."""
        if not hasattr(bhav, 'chunk_label') or not bhav.chunk_label:
            return "FLOW"
        
        label = bhav.chunk_label.lower()
        
        role_keywords = ['main', 'init', 'cleanup', 'controller', 'load']
        if any(kw in label for kw in role_keywords):
            return "ROLE"
        
        action_keywords = ['interaction', 'action', 'use', 'get', 'put', 'eat', 'sit']
        if any(kw in label for kw in action_keywords):
            return "ACTION"
        
        return "FLOW"
    
    def _update_progress(self, current_file: str):
        """Update progress UI (thread-safe)."""
        self._processed_files += 1
        self._current_file = current_file
        progress = self._processed_files / max(self._total_files, 1)
        
        # Schedule UI update on main thread
        dpg.set_value("archiver_progress", progress)
        dpg.set_value("archiver_current_file", f"📄 {current_file}")
        dpg.set_value("archiver_status", f"Processing {self._processed_files}/{self._total_files}...")
    
    def _update_ui(self, element: str, value: str):
        """Update UI element (thread-safe)."""
        tag_map = {
            "status": "archiver_status",
            "results": "archiver_results",
            "current_file": "archiver_current_file"
        }
        if element in tag_map:
            dpg.set_value(tag_map[element], value)
    
    def _scan_complete(self, results: dict):
        """Handle scan completion."""
        self._running = False
        
        # Update UI
        dpg.configure_item("archiver_start_btn", enabled=True)
        dpg.configure_item("archiver_cancel_btn", enabled=False)
        dpg.set_value("archiver_progress", 1.0 if not self._cancel_requested else 0.5)
        
        if self._cancel_requested:
            dpg.set_value("archiver_status", "⏹️ Cancelled")
        elif "error" in results:
            dpg.set_value("archiver_status", f"❌ Error: {results['error']}")
        else:
            dpg.set_value("archiver_status", "✅ Complete!")
        
        # Format results
        lines = [f"Mode: {results.get('mode', 'UNKNOWN')}"]
        for key, value in results.items():
            if key != 'mode' and key != 'errors':
                lines.append(f"  {key}: {value}")
        
        if results.get('errors'):
            lines.append(f"\nErrors ({len(results['errors'])}):")
            for err in results['errors'][:5]:
                lines.append(f"  - {err}")
        
        dpg.set_value("archiver_results", "\n".join(lines))
        
        # Refresh stats
        self._refresh_db_stats()
    
    def _refresh_db_stats(self):
        """Refresh database statistics display."""
        try:
            unknowns = get_unknowns_db().get_statistics()
            mappings = get_mapping_db().get_statistics()
            
            stats = (
                f"Unknowns: {unknowns['unknown_opcodes_count']} opcodes, "
                f"{unknowns['unknown_chunks_count']} chunks | "
                f"Mapped: {mappings['total_behaviors']} BHAVs, "
                f"{mappings['total_objects']} objects"
            )
            dpg.set_value("archiver_db_stats", stats)
        except Exception as e:
            dpg.set_value("archiver_db_stats", f"Error: {e}")
    
    def _view_database(self):
        """Show database contents in a popup."""
        unknowns = get_unknowns_db()
        mappings = get_mapping_db()
        
        report = unknowns.export_report()
        report += "\n\n" + mappings.export_behavior_library()
        
        # Show in results area for now
        dpg.set_value("archiver_results", report[:2000] + "..." if len(report) > 2000 else report)
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
