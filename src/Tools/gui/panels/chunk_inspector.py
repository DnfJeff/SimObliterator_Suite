"""
Chunk Inspector Panel.
Displays detailed information about selected chunks.
Auto-reports unknown opcodes and chunks to the unknowns database.
Integrates semantic global labeling for BHAV calls.

PROGRESSIVE DEPTH (from Conceptual Directives):
- Mode 1: SUMMARY  - Quick overview, what is this?
- Mode 2: EXPLAIN  - Detailed view, what does it do?
- Mode 3: EDIT     - Full access, let me change it
"""

import dearpygui.dearpygui as dpg
from enum import Enum

from ..events import EventBus, Events
from ..state import STATE
from ..theme import Colors
from ..opcodes import OPCODE_NAMES, format_pointer

# Import comprehensive opcodes from core
try:
    from core.opcode_loader import get_opcode_info, is_known_opcode, PRIMITIVE_INSTRUCTIONS
    from core.unknowns_db import get_unknowns_db
except ImportError:
    # Fallback
    PRIMITIVE_INSTRUCTIONS = {}
    def get_opcode_info(op): return {"name": f"Op_{op}"}
    def is_known_opcode(op): return op in PRIMITIVE_INSTRUCTIONS
    def get_unknowns_db(): return None

# Import engine toolkit for semantic global labeling
try:
    from forensic.engine_toolkit import EngineToolkit
    _toolkit = EngineToolkit()
    _toolkit_available = True
except ImportError:
    _toolkit = None
    _toolkit_available = False

# Import safety API
try:
    from Tools.core.safety import is_safe_to_edit
    _safety_available = True
except ImportError:
    def is_safe_to_edit(chunk, path): return None
    _safety_available = False


class DepthMode(Enum):
    """Progressive depth modes."""
    SUMMARY = "summary"   # Quick overview
    EXPLAIN = "explain"   # Detailed view  
    EDIT = "edit"         # Full editing access


class ChunkInspectorPanel:
    """Chunk details inspector panel with Progressive Depth."""
    
    TAG = "chunk_inspector"
    DETAILS_TAG = "chunk_details"
    MODE_TAG = "depth_mode_group"
    
    _instance = None
    
    def __init__(self, width: int = 400, height: int = 450, pos: tuple = (630, 30)):
        self.width = width
        self.height = height
        self.pos = pos
        self.current_chunk = None
        self.depth_mode = DepthMode.SUMMARY  # Start shallow
        ChunkInspectorPanel._instance = self
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the panel window."""
        with dpg.window(
            label="Chunk Inspector",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            # Progressive Depth mode selector
            with dpg.group(horizontal=True, tag=self.MODE_TAG):
                dpg.add_text("Depth:", color=(136, 136, 136, 255))
                dpg.add_button(
                    label="Summary", 
                    tag="depth_btn_summary",
                    callback=lambda: self._set_depth(DepthMode.SUMMARY),
                    small=True
                )
                dpg.add_button(
                    label="Explain", 
                    tag="depth_btn_explain",
                    callback=lambda: self._set_depth(DepthMode.EXPLAIN),
                    small=True
                )
                dpg.add_button(
                    label="Edit", 
                    tag="depth_btn_edit",
                    callback=lambda: self._set_depth(DepthMode.EDIT),
                    small=True
                )
            
            dpg.add_separator()
            dpg.add_text("Select a chunk to inspect", color=(136, 136, 136, 255))
            
            with dpg.child_window(tag=self.DETAILS_TAG, border=False):
                pass
        
        # Initialize button highlighting
        self._update_depth_buttons()
    
    def _set_depth(self, mode: DepthMode):
        """Change the inspection depth mode."""
        self.depth_mode = mode
        self._update_depth_buttons()
        
        # Re-render current chunk at new depth
        if self.current_chunk:
            self._on_chunk_selected(self.current_chunk)
    
    def _update_depth_buttons(self):
        """Update button visual state for current depth."""
        modes = [
            ("depth_btn_summary", DepthMode.SUMMARY),
            ("depth_btn_explain", DepthMode.EXPLAIN),
            ("depth_btn_edit", DepthMode.EDIT),
        ]
        
        for tag, mode in modes:
            if dpg.does_item_exist(tag):
                if mode == self.depth_mode:
                    # Active mode - highlight
                    dpg.bind_item_theme(tag, None)  # Reset first
                else:
                    # Inactive mode - dim
                    pass
    
    def _subscribe_events(self):
        """Subscribe to relevant events."""
        EventBus.subscribe(Events.CHUNK_SELECTED, self._on_chunk_selected)
    
    def _on_chunk_selected(self, chunk):
        """Handle chunk selection event."""
        self.current_chunk = chunk
        dpg.delete_item(self.DETAILS_TAG, children_only=True)
        
        if chunk is None:
            return
        
        with dpg.group(parent=self.DETAILS_TAG):
            # Safety indicator (always shown)
            if _safety_available:
                safety = is_safe_to_edit(chunk, STATE.current_file_path or "")
                if safety:
                    if safety.level.value == "safe":
                        dpg.add_text("✓ Safe to edit", color=(76, 175, 80, 255))
                    elif safety.level.value in ("caution", "warning"):
                        dpg.add_text(f"⚠ {safety.summary()}", color=(255, 193, 7, 255))
                    else:
                        dpg.add_text(f"⛔ {safety.summary()}", color=(255, 87, 34, 255))
                    dpg.add_separator()
            
            # Render based on depth mode
            if self.depth_mode == DepthMode.SUMMARY:
                self._render_summary(chunk)
            elif self.depth_mode == DepthMode.EXPLAIN:
                self._render_explain(chunk)
            else:  # EDIT
                self._render_edit(chunk)
    
    # ─────────────────────────────────────────────────────────────
    # PROGRESSIVE DEPTH: SUMMARY MODE
    # Quick one-liner answers: What is this?
    # ─────────────────────────────────────────────────────────────
    
    def _render_summary(self, chunk):
        """Quick summary - answers 'What is this?'"""
        dpg.add_text(f"📦 {chunk.chunk_type}", color=(0, 212, 255, 255))
        dpg.add_text(f"   ID #{chunk.chunk_id}", color=(160, 160, 160, 255))
        
        if chunk.chunk_label:
            dpg.add_text(f"   \"{chunk.chunk_label}\"", color=(224, 224, 224, 255))
        
        # Type-specific one-liner
        if chunk.chunk_type == "BHAV":
            count = len(getattr(chunk, 'instructions', []))
            dpg.add_text(f"   Behavior script with {count} instructions", 
                         color=(160, 160, 160, 255))
        elif chunk.chunk_type == "TTAB":
            count = len(getattr(chunk, 'interactions', []))
            dpg.add_text(f"   Pie menu with {count} interactions",
                         color=(160, 160, 160, 255))
        elif chunk.chunk_type == "OBJD":
            if hasattr(chunk, 'guid'):
                dpg.add_text(f"   Object definition (GUID: 0x{chunk.guid:08X})",
                             color=(160, 160, 160, 255))
        elif chunk.chunk_type == "STR#":
            count = len(getattr(chunk, 'strings', []))
            dpg.add_text(f"   String table with {count} entries",
                         color=(160, 160, 160, 255))
        elif chunk.chunk_type == "OBJf":
            dpg.add_text(f"   Object lifecycle functions",
                         color=(160, 160, 160, 255))
        else:
            size = len(getattr(chunk, 'chunk_data', b'') or b'')
            dpg.add_text(f"   {size} bytes of data",
                         color=(160, 160, 160, 255))
        
        dpg.add_separator()
        dpg.add_text("💡 Switch to 'Explain' for details", 
                     color=(136, 136, 136, 255))
    
    # ─────────────────────────────────────────────────────────────
    # PROGRESSIVE DEPTH: EXPLAIN MODE  
    # Detailed breakdown: What does it do?
    # ─────────────────────────────────────────────────────────────
    
    def _render_explain(self, chunk):
        """Detailed explanation - answers 'What does it do?'"""
        # Basic info - styled like HTML
        dpg.add_text(f"Type: {chunk.chunk_type}", color=(0, 212, 255, 255))
        dpg.add_text(f"ID: #{chunk.chunk_id}", color=(224, 224, 224, 255))
        dpg.add_text(f"Label: {chunk.chunk_label or '(none)'}", color=(224, 224, 224, 255))
        dpg.add_separator()
        
        # Type-specific rendering
        if chunk.chunk_type == "BHAV" and hasattr(chunk, 'instructions'):
            self._render_bhav_details(chunk)
        elif chunk.chunk_type == "TTAB" and hasattr(chunk, 'interactions'):
            self._render_ttab_details(chunk)
        elif chunk.chunk_type == "OBJf" and hasattr(chunk, 'functions'):
            self._render_objf_details(chunk)
        elif chunk.chunk_type == "OBJD":
            self._render_objd_details(chunk)
        elif chunk.chunk_type == "STR#" and hasattr(chunk, 'strings'):
            self._render_str_details(chunk)
        else:
            # Generic chunk info
            data_size = len(getattr(chunk, 'chunk_data', b'') or b'')
            dpg.add_text(f"Data size: {data_size} bytes")
        
        dpg.add_separator()
        dpg.add_text("💡 Switch to 'Edit' for modifications", 
                     color=(136, 136, 136, 255))
    
    # ─────────────────────────────────────────────────────────────
    # PROGRESSIVE DEPTH: EDIT MODE
    # Full editing access with safety gates
    # ─────────────────────────────────────────────────────────────
    
    def _render_edit(self, chunk):
        """Full edit mode - with safety gates."""
        dpg.add_text("✏️ EDIT MODE", color=(255, 193, 7, 255))
        dpg.add_separator()
        
        # First show explain content
        self._render_explain_content_only(chunk)
        
        dpg.add_separator()
        dpg.add_text("Edit Actions:", color=(255, 193, 7, 255))
        
        # Type-specific edit buttons
        if chunk.chunk_type == "BHAV":
            dpg.add_button(
                label="Open in BHAV Editor →",
                callback=lambda: EventBus.publish(Events.BHAV_SELECTED, chunk)
            )
        elif chunk.chunk_type == "STR#":
            dpg.add_button(
                label="Edit Strings...",
                callback=lambda: self._open_string_editor(chunk)
            )
        elif chunk.chunk_type == "OBJD":
            dpg.add_button(
                label="Edit Object Properties...",
                callback=lambda: self._open_objd_editor(chunk)
            )
        else:
            dpg.add_text("(No specialized editor for this type)", 
                         color=(136, 136, 136, 255))
        
        dpg.add_separator()
        dpg.add_button(
            label="Export Raw Bytes...",
            callback=lambda: self._export_raw(chunk)
        )
    
    def _render_explain_content_only(self, chunk):
        """Render explain content without navigation hints."""
        dpg.add_text(f"Type: {chunk.chunk_type}", color=(0, 212, 255, 255))
        dpg.add_text(f"ID: #{chunk.chunk_id}", color=(224, 224, 224, 255))
        dpg.add_text(f"Label: {chunk.chunk_label or '(none)'}", color=(224, 224, 224, 255))
        dpg.add_separator()
        
        if chunk.chunk_type == "BHAV" and hasattr(chunk, 'instructions'):
            self._render_bhav_details(chunk)
        elif chunk.chunk_type == "TTAB" and hasattr(chunk, 'interactions'):
            self._render_ttab_details(chunk)
        elif chunk.chunk_type == "OBJf" and hasattr(chunk, 'functions'):
            self._render_objf_details(chunk)
        elif chunk.chunk_type == "OBJD":
            self._render_objd_details(chunk)
        elif chunk.chunk_type == "STR#" and hasattr(chunk, 'strings'):
            self._render_str_details(chunk)
        else:
            data_size = len(getattr(chunk, 'chunk_data', b'') or b'')
            dpg.add_text(f"Data size: {data_size} bytes")
    
    def _open_string_editor(self, chunk):
        """Placeholder for string editor."""
        print(f"TODO: Open string editor for STR# #{chunk.chunk_id}")
    
    def _open_objd_editor(self, chunk):
        """Placeholder for OBJD editor."""
        print(f"TODO: Open OBJD editor for #{chunk.chunk_id}")
    
    def _export_raw(self, chunk):
        """Placeholder for raw export."""
        print(f"TODO: Export raw bytes for {chunk.chunk_type} #{chunk.chunk_id}")
    
    def _render_bhav_details(self, bhav):
        """Render BHAV-specific details and report unknown opcodes."""
        dpg.add_text("🧠 BHAV Properties", color=(233, 69, 96, 255))
        dpg.add_text(f"  Instructions: {len(bhav.instructions)}", color=(224, 224, 224, 255))
        
        if hasattr(bhav, 'args'):
            dpg.add_text(f"  Arguments: {bhav.args}", color=(224, 224, 224, 255))
        if hasattr(bhav, 'locals'):
            dpg.add_text(f"  Locals: {bhav.locals}", color=(224, 224, 224, 255))
        if hasattr(bhav, 'type'):
            dpg.add_text(f"  Type: {bhav.type}", color=(224, 224, 224, 255))
        if hasattr(bhav, 'file_version'):
            dpg.add_text(f"  Format: 0x{bhav.file_version:04X}", color=(224, 224, 224, 255))
        
        dpg.add_separator()
        dpg.add_text("Disassembly:", color=(255, 213, 79, 255))
        
        # Track unknowns for auto-reporting
        unknown_opcodes = []
        
        # Show up to 15 instructions with better formatting
        for i, inst in enumerate(bhav.instructions[:15]):
            opname = self._get_opcode_name(inst.opcode)
            
            t_str = format_pointer(inst.true_pointer)
            f_str = format_pointer(inst.false_pointer)
            
            # Color-code by opcode type and track unknowns
            if not is_known_opcode(inst.opcode) and inst.opcode < 256:
                color = (255, 100, 100)  # Unknown primitive - red
                if inst.opcode not in unknown_opcodes:
                    unknown_opcodes.append(inst.opcode)
            elif inst.opcode < 256:
                color = (224, 224, 224, 255)  # Known primitive - white
            elif inst.opcode < 0x1000:
                color = (150, 200, 255)  # Global call - blue
            elif inst.opcode < 0x2000:
                color = (150, 255, 150)  # Local call - green
            else:
                color = (255, 200, 150)  # Semi-global - orange
            
            dpg.add_text(f"[{i:3d}] {opname}", color=color)
            dpg.add_text(f"      → T:{t_str}  F:{f_str}", color=(136, 136, 136, 255))
        
        if len(bhav.instructions) > 15:
            dpg.add_text(f"  ... ({len(bhav.instructions) - 15} more)", color=(136, 136, 136, 255))
        
        # Auto-report unknown opcodes to database
        if unknown_opcodes:
            dpg.add_separator()
            dpg.add_text(f"⚠️ {len(unknown_opcodes)} unknown opcode(s)", color=(255, 180, 80))
            self._report_unknown_opcodes(bhav, unknown_opcodes)
    
    def _report_unknown_opcodes(self, bhav, opcodes: list):
        """Report unknown opcodes to the database."""
        try:
            db = get_unknowns_db()
            if db is None:
                return
            
            source_file = STATE.current_iff_name or "unknown.iff"
            for opcode in opcodes:
                db.add_unknown_opcode(
                    opcode=opcode,
                    source_file=source_file,
                    context={"bhav_id": bhav.chunk_id, "bhav_name": bhav.chunk_label or ""}
                )
            db.save()
        except Exception:
            pass  # Silent fail - don't break UI
    
    def _render_ttab_details(self, ttab):
        """Render TTAB-specific details with semantic function names."""
        dpg.add_text("📋 TTAB (Interactions)", color=(76, 175, 80, 255))
        dpg.add_text(f"  Count: {len(ttab.interactions)}", color=(224, 224, 224, 255))
        dpg.add_text(f"  Version: {ttab.version}", color=(224, 224, 224, 255))
        dpg.add_separator()
        
        for i, inter in enumerate(ttab.interactions[:10]):
            # Display test function with semantic name if available
            if inter.test_function:
                if _toolkit_available and _toolkit and 256 <= inter.test_function < 4096:
                    try:
                        test_semantic = _toolkit.label_global(inter.test_function)
                        test_str = f"T:{test_semantic} (#{inter.test_function:04X})"
                    except Exception:
                        test_str = f"T:0x{inter.test_function:04X}"
                else:
                    test_str = f"T:0x{inter.test_function:04X}"
            else:
                test_str = "T:—"
            
            # Display action function with semantic name if available
            if inter.action_function:
                if _toolkit_available and _toolkit and 256 <= inter.action_function < 4096:
                    try:
                        act_semantic = _toolkit.label_global(inter.action_function)
                        act_str = f"A:{act_semantic} (#{inter.action_function:04X})"
                    except Exception:
                        act_str = f"A:0x{inter.action_function:04X}"
                else:
                    act_str = f"A:0x{inter.action_function:04X}"
            else:
                act_str = "A:—"
            
            dpg.add_text(f"  [{i}] {test_str} {act_str}")
        
        if len(ttab.interactions) > 10:
            dpg.add_text(f"  ... ({len(ttab.interactions) - 10} more)", color=Colors.TEXT_DIM)
    
    def _render_objf_details(self, objf):
        """Render OBJf-specific details."""
        dpg.add_text("⚙️ OBJf (Lifecycle)", color=(76, 175, 80, 255))
        dpg.add_text(f"  Entries: {len(objf.functions)}", color=(224, 224, 224, 255))
        dpg.add_separator()
        
        NAMES = ["Init", "Main", "Load", "Cleanup", "QueueSkipped", "AllowIntersect",
                 "WallAdj", "RoomChg", "DynMulti", "Place", "PickUp", "UserPlace"]
        
        for i, entry in enumerate(objf.functions[:12]):
            if not entry.action_function and not entry.condition_function:
                continue
            name = NAMES[i] if i < len(NAMES) else f"Entry_{i}"
            act = f"0x{entry.action_function:04X}" if entry.action_function else "—"
            dpg.add_text(f"  {name}: {act}")
    
    def _render_objd_details(self, objd):
        """Render OBJD-specific details."""
        dpg.add_text("📄 OBJD (Definition)", color=(76, 175, 80, 255))
        
        if hasattr(objd, 'object_type'):
            type_names = {0: "Unknown", 2: "Person", 4: "Object", 7: "System", 8: "Portal", 34: "Food"}
            type_val = int(objd.object_type) if hasattr(objd.object_type, '__int__') else objd.object_type
            dpg.add_text(f"  Type: {type_names.get(type_val, type_val)}", color=(224, 224, 224, 255))
        if hasattr(objd, 'guid'):
            dpg.add_text(f"  GUID: 0x{objd.guid:08X}", color=(224, 224, 224, 255))
        if hasattr(objd, 'price'):
            dpg.add_text(f"  Price: §{objd.price}", color=(224, 224, 224, 255))
        if hasattr(objd, 'tree_table_id') and objd.tree_table_id:
            dpg.add_text(f"  TTAB: #{objd.tree_table_id}", color=(224, 224, 224, 255))
    
    def _render_str_details(self, str_chunk):
        """Render STR#-specific details."""
        dpg.add_text("📝 STR# (Strings)", color=(76, 175, 80, 255))
        dpg.add_text(f"  Count: {len(str_chunk.strings)}", color=(224, 224, 224, 255))
        dpg.add_separator()
        
        for i, s in enumerate(str_chunk.strings[:10]):
            # Truncate long strings
            display = s[:40] + "..." if len(s) > 40 else s
            dpg.add_text(f"  [{i}] {display}", color=(224, 224, 224, 255))
        
        if len(str_chunk.strings) > 10:
            dpg.add_text(f"  ... ({len(str_chunk.strings) - 10} more)", color=(136, 136, 136, 255))
    
    def _get_opcode_name(self, opcode: int) -> str:
        """Get human-readable opcode name using opcode_loader and semantic globals."""
        if opcode < 256:
            # Primitive - use opcode_loader (reads from JSON)
            info = get_opcode_info(opcode)
            name = info.get('name', f'Prim_{opcode}')
            if info.get('is_unknown'):
                return f"❓{name}"  # Mark unknown
            return name
        elif opcode < 0x1000:
            # Global call - use semantic labeling if toolkit available
            if _toolkit_available and _toolkit:
                try:
                    semantic = _toolkit.label_global(opcode)
                    return f"{semantic} (#{opcode:04X})"
                except Exception:
                    # Fallback if lookup fails
                    pass
            return f"Global_0x{opcode:04X}"
        elif opcode < 0x2000:
            return f"Local_0x{opcode:04X}"
        else:
            return f"SemiGlob_0x{opcode:04X}"
    
    def _on_close(self):
        """Handle panel close - hide instead of destroy."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel (used by View menu)."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
