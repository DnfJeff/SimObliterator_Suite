"""
IFF Editor Panel - Context-First Workspace.

Treats an IFF as a living system, not a file — guiding users from 
overview → intent → edit, while constantly signaling blast radius.

Layout:
- Header Zone (top, fixed): filename, scope, danger level, IFF type indicator
- Left Pane: Categorized chunk navigator (50% width)
- Right Pane: Overview dashboard OR chunk detail (50% width)
- Bottom: Cross-IFF awareness + Action buttons
"""

import dearpygui.dearpygui as dpg

from ..events import EventBus, Events
from ..state import STATE
from ..theme import Colors


# OBJf entry point names for lifecycle display
OBJF_ENTRY_NAMES = [
    "Init", "Main", "Load", "Cleanup", "Queue Skipped",
    "Allow Intersection", "Wall Adjacency Changed", "Room Changed",
    "Dynamic Multitile Update", "Placement", "Pick Up", "User Placement",
    "User Pickup", "Level Info Request", "Move In", "Move Out",
    "Cook", "Eat Food", "Dispose", "Fire", "Burn Down",
    "Wash Hands", "Wash Dishes", "Use Toilet", "Use Tub", "Sit",
    "Stand", "Lie In", "Place on Surface", "Pickup from Slot", "Garden"
]


# Chunk classification categories  
CHUNK_CATEGORIES = {
    "Behaviors": {
        "types": ["BHAV"],
        "icon": "🧠",
        "subcategories": {
            "ROLE": lambda c: _classify_bhav_role(c) == "ROLE",
            "ACTION": lambda c: _classify_bhav_role(c) == "ACTION",
            "FLOW": lambda c: _classify_bhav_role(c) == "FLOW",
        }
    },
    "Interactions": {
        "types": ["TTAB", "TTAs"],
        "icon": "📋",
        "subcategories": {}
    },
    "Lifecycle": {
        "types": ["OBJf"],
        "icon": "⚙️",
        "subcategories": {}
    },
    "Resources": {
        "types": ["STR#", "GLOB", "BCON", "TPRP", "TRCN"],
        "icon": "📦",
        "subcategories": {}
    },
    "Definition": {
        "types": ["OBJD", "SLOT"],
        "icon": "📄",
        "subcategories": {}
    },
    "Graphics": {
        "types": ["DGRP", "SPR#", "SPR2", "PALT", "BMP_"],
        "icon": "🎨",
        "subcategories": {}
    },
    "Other": {
        "types": [],  # Catch-all
        "icon": "📁",
        "subcategories": {}
    }
}


def _classify_bhav_role(bhav):
    """
    Classify a BHAV by its role (ROLE/ACTION/FLOW).
    Uses multiple signals: name patterns, instruction count, structure.
    """
    if not hasattr(bhav, 'chunk_label') or not bhav.chunk_label:
        # No label - check instruction count
        if hasattr(bhav, 'instructions'):
            inst_count = len(bhav.instructions)
            if inst_count <= 3:
                return "FLOW"  # Very short = likely helper
            elif inst_count > 50:
                return "ROLE"  # Very long = likely controller
        return "FLOW"
    
    label = bhav.chunk_label.lower()
    
    # ROLE: Main controllers, init, cleanup, load
    role_keywords = ['main', 'init', 'cleanup', 'controller', 'load', 'unload', 
                     'tick', 'update', 'loop', 'process']
    if any(kw in label for kw in role_keywords):
        return "ROLE"
    
    # ACTION: Player-facing interactions
    action_keywords = ['interaction', 'action', 'use', 'get', 'put', 'serve', 
                       'eat', 'sit', 'stand', 'grab', 'drop', 'watch', 'play',
                       'cook', 'wash', 'clean', 'sleep', 'nap', 'talk', 'greet']
    if any(kw in label for kw in action_keywords):
        return "ACTION"
    
    # Everything else is FLOW (helpers, tests, conditions)
    return "FLOW"


def _get_iff_type(iff_name: str, chunks: list) -> str:
    """
    Detect IFF type: OBJECT, CHARACTER, GLOBAL, SEMI-GLOBAL.
    """
    name_lower = iff_name.lower() if iff_name else ""
    
    if 'global' in name_lower and 'semi' not in name_lower:
        return "GLOBAL"
    if 'semi' in name_lower:
        return "SEMI-GLOBAL"
    
    # Check for character indicators
    for chunk in chunks:
        # OBJD type = 2 is person
        if chunk.chunk_type == "OBJD" and hasattr(chunk, 'object_type'):
            if chunk.object_type == 2:  # OBJDType.PERSON
                return "CHARACTER"
        # STR# 200 is body strings (character only)
        if chunk.chunk_type == "STR#" and chunk.chunk_id == 200:
            return "CHARACTER"
    
    return "OBJECT"


def _get_danger_level(iff_name: str, chunk_count: int, iff_type: str) -> tuple:
    """Determine danger level for an IFF file."""
    if iff_type == "GLOBAL":
        return ("🔴 HIGH", (255, 80, 80), "Global file - affects ALL objects!")
    elif iff_type == "SEMI-GLOBAL":
        return ("🟠 MEDIUM", (255, 180, 80), "Semi-global - affects objects using this library")
    elif chunk_count > 100:
        return ("🟡 CAUTION", (255, 220, 80), "Large file - verify changes carefully")
    else:
        return ("🟢 LOW", (80, 255, 120), "Local object - safe to edit")


def _get_chunk_smart_name(chunk, iff) -> str:
    """
    Get a smart human-readable name for a chunk.
    Uses TPRP labels, TTAs strings, known patterns, etc.
    """
    # Start with label if present and meaningful
    if chunk.chunk_label and chunk.chunk_label.strip():
        return chunk.chunk_label
    
    # BHAV: Show instruction count as hint
    if chunk.chunk_type == "BHAV":
        if hasattr(chunk, 'instructions'):
            count = len(chunk.instructions)
            return f"(unnamed, {count} instr)"
        return "(unnamed)"
    
    # TTAB: Show interaction count
    if chunk.chunk_type == "TTAB":
        if hasattr(chunk, 'interactions') and chunk.interactions:
            return f"Interactions ({len(chunk.interactions)})"
        return "(empty)"
    
    # OBJf: Show as lifecycle table
    if chunk.chunk_type == "OBJf":
        if hasattr(chunk, 'functions'):
            active = sum(1 for f in chunk.functions if f.action_function or f.condition_function)
            return f"Lifecycle ({active} active)"
        return "Lifecycle"
    
    # OBJD: Show type info
    if chunk.chunk_type == "OBJD":
        if hasattr(chunk, 'object_type'):
            type_names = {0: "Unknown", 2: "Person", 4: "Object", 7: "System", 8: "Portal", 34: "Food"}
            type_val = int(chunk.object_type) if hasattr(chunk.object_type, '__int__') else chunk.object_type
            type_name = type_names.get(type_val, f"Type {type_val}")
            return f"Definition ({type_name})"
        return "Definition"
    
    # STR#: Show string count
    if chunk.chunk_type == "STR#":
        # Well-known IDs
        known_strs = {200: "Body Strings", 256: "Person Attributes"}
        if chunk.chunk_id in known_strs:
            return known_strs[chunk.chunk_id]
        if hasattr(chunk, 'length'):
            return f"Strings ({chunk.length})"
        return "Strings"
    
    # BCON: Show constant count
    if chunk.chunk_type == "BCON":
        return "Constants"
    
    # TPRP: Labels for BHAV
    if chunk.chunk_type == "TPRP":
        if hasattr(chunk, 'param_names'):
            return f"Labels (BHAV #{chunk.chunk_id})"
        return "Labels"
    
    # SLOT: Routing slots
    if chunk.chunk_type == "SLOT":
        return "Routing Slots"
    
    # GLOB: Semi-global reference
    if chunk.chunk_type == "GLOB":
        return "Semi-Global Ref"
    
    # Default
    return "(unnamed)"


# ═══════════════════════════════════════════════════════════════════════════
# CROSS-REFERENCE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def _build_xref_map(iff) -> dict:
    """
    Build a cross-reference map for an IFF file.
    Returns: {
        bhav_id: {
            "called_by_bhav": [list of BHAV IDs],
            "used_by_ttab": [list of (ttab_id, interaction_index, "test"|"action")],
            "used_by_objf": [list of (entry_index, "guard"|"action")],
        }
    }
    """
    if not iff or not hasattr(iff, 'chunks'):
        return {}
    
    xref = {}
    
    # Initialize empty entry for each BHAV
    for chunk in iff.chunks:
        if chunk.chunk_type == "BHAV":
            xref[chunk.chunk_id] = {
                "called_by_bhav": [],
                "used_by_ttab": [],
                "used_by_objf": [],
            }
    
    # Scan BHAV instructions for calls to other BHAVs
    for chunk in iff.chunks:
        if chunk.chunk_type == "BHAV" and hasattr(chunk, 'instructions'):
            for inst in chunk.instructions:
                # Opcode 0x0002 = Call private/local BHAV
                # Opcode 0x000D = Call semi-global
                # Check operands for target BHAV
                if hasattr(inst, 'opcode') and hasattr(inst, 'operands'):
                    # Operand format varies but often operand[0] or operand[0-1] is target
                    target_bhav = None
                    if inst.opcode == 0x0002:  # Private call
                        if len(inst.operands) >= 1:
                            target_bhav = inst.operands[0]
                    elif inst.opcode == 0x000D:  # Semi-global call
                        if len(inst.operands) >= 2:
                            target_bhav = (inst.operands[0] << 8) | inst.operands[1]
                    
                    if target_bhav and target_bhav in xref:
                        if chunk.chunk_id not in xref[target_bhav]["called_by_bhav"]:
                            xref[target_bhav]["called_by_bhav"].append(chunk.chunk_id)
    
    # Scan TTAB interactions for BHAV references
    for chunk in iff.chunks:
        if chunk.chunk_type == "TTAB" and hasattr(chunk, 'interactions'):
            for i, inter in enumerate(chunk.interactions):
                if hasattr(inter, 'test_function') and inter.test_function:
                    if inter.test_function in xref:
                        xref[inter.test_function]["used_by_ttab"].append((chunk.chunk_id, i, "test"))
                if hasattr(inter, 'action_function') and inter.action_function:
                    if inter.action_function in xref:
                        xref[inter.action_function]["used_by_ttab"].append((chunk.chunk_id, i, "action"))
    
    # Scan OBJf entries for BHAV references
    for chunk in iff.chunks:
        if chunk.chunk_type == "OBJf" and hasattr(chunk, 'functions'):
            for i, entry in enumerate(chunk.functions):
                if hasattr(entry, 'condition_function') and entry.condition_function:
                    if entry.condition_function in xref:
                        xref[entry.condition_function]["used_by_objf"].append((i, "guard"))
                if hasattr(entry, 'action_function') and entry.action_function:
                    if entry.action_function in xref:
                        xref[entry.action_function]["used_by_objf"].append((i, "action"))
    
    return xref


def _get_bhav_references(bhav_id: int, xref: dict) -> dict:
    """Get all references to a specific BHAV."""
    if bhav_id not in xref:
        return {"called_by_bhav": [], "used_by_ttab": [], "used_by_objf": []}
    return xref[bhav_id]


def _format_xref_summary(refs: dict) -> str:
    """Format a human-readable summary of cross-references."""
    parts = []
    if refs["called_by_bhav"]:
        parts.append(f"{len(refs['called_by_bhav'])} BHAV")
    if refs["used_by_ttab"]:
        parts.append(f"{len(refs['used_by_ttab'])} TTAB")
    if refs["used_by_objf"]:
        parts.append(f"{len(refs['used_by_objf'])} OBJf")
    
    if not parts:
        return "No references (orphan?)"
    return f"Used by: {', '.join(parts)}"


class IFFViewerPanel:
    """IFF Editor Panel - context-first workspace."""
    
    TAG = "iff_panel"
    HEADER_TAG = "iff_header"
    NAV_TAG = "iff_navigator"
    DETAIL_TAG = "iff_detail"
    FOOTER_TAG = "iff_footer"
    
    _instance = None
    
    def __init__(self, width: int = 500, height: int = 600, pos: tuple = (300, 30)):
        self.width = width
        self.height = height
        self.pos = pos
        self.current_iff = None
        self.current_iff_type = "OBJECT"
        self.selected_chunk = None
        self.modified_chunks = set()  # Track modified chunk IDs
        self.xref_map = {}  # Cross-reference map for current IFF
        
        IFFViewerPanel._instance = self
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the panel window with header/nav/detail/footer layout."""
        with dpg.window(
            label="IFF Editor",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            # ═══════════════════════════════════════════════════════════
            # HEADER ZONE - Orientation First (Always Visible)
            # ═══════════════════════════════════════════════════════════
            with dpg.child_window(tag=self.HEADER_TAG, height=90, border=True):
                self._create_header_content()
            
            dpg.add_spacer(height=5)
            
            # ═══════════════════════════════════════════════════════════
            # MAIN CONTENT - Split Nav (left 50%) | Detail (right 50%)
            # Using -1 width on detail pane to fill remaining space
            # ═══════════════════════════════════════════════════════════
            with dpg.group(horizontal=True):
                # LEFT: Chunk Navigator (approximately half width)
                # Use percentage-based width calculation
                nav_width = int((self.width - 30) * 0.45)  # 45% for nav
                with dpg.child_window(tag=self.NAV_TAG, width=nav_width, border=True):
                    self._create_nav_placeholder()
                
                dpg.add_spacer(width=5)
                
                # RIGHT: Detail/Overview Pane (fills remaining space)
                with dpg.child_window(tag=self.DETAIL_TAG, border=True):
                    self._create_overview_placeholder()
            
            # ═══════════════════════════════════════════════════════════
            # FOOTER - Actions + Cross-IFF Awareness
            # ═══════════════════════════════════════════════════════════
            dpg.add_spacer(height=5)
            with dpg.child_window(tag=self.FOOTER_TAG, height=60, border=True):
                self._create_footer_content()
    
    def _create_header_content(self):
        """Create header zone content."""
        dpg.add_text("📦 No IFF loaded", tag="iff_header_title", color=Colors.TEXT_DIM)
        with dpg.group(horizontal=True):
            dpg.add_text("Type:", color=Colors.TEXT_DIM)
            dpg.add_text("—", tag="iff_header_type")
            dpg.add_spacer(width=20)
            dpg.add_text("Chunks:", color=Colors.TEXT_DIM)
            dpg.add_text("—", tag="iff_header_chunks")
        with dpg.group(horizontal=True):
            dpg.add_text("Danger:", color=Colors.TEXT_DIM)
            dpg.add_text("—", tag="iff_header_danger")
            dpg.add_spacer(width=10)
            dpg.add_text("", tag="iff_header_danger_tip", color=Colors.TEXT_DIM)
    
    def _create_nav_placeholder(self):
        """Create navigator placeholder."""
        dpg.add_text("Load an IFF file", color=Colors.TEXT_DIM)
        dpg.add_text("to browse chunks", color=Colors.TEXT_DIM)
    
    def _create_overview_placeholder(self):
        """Create overview/detail placeholder."""
        dpg.add_text("IFF Overview", color=Colors.ACCENT_BLUE)
        dpg.add_separator()
        dpg.add_text("Open an IFF file to see", color=Colors.TEXT_DIM)
        dpg.add_text("its structure and contents.", color=Colors.TEXT_DIM)
    
    def _create_footer_content(self):
        """Create footer with action buttons and references."""
        with dpg.group(horizontal=True):
            dpg.add_button(label="📤 Export Chunk", callback=self._on_export_chunk, enabled=False, tag="btn_export_chunk")
            dpg.add_button(label="🔍 Opcodes", callback=self._show_opcode_reference)
            dpg.add_button(label="📚 Behavior Dict", callback=self._show_behavior_dict)
        dpg.add_text("", tag="iff_footer_refs", color=Colors.TEXT_DIM)
    
    def _subscribe_events(self):
        """Subscribe to relevant events."""
        EventBus.subscribe(Events.IFF_LOADED, self._on_iff_loaded)
        EventBus.subscribe(Events.CHUNK_SELECTED, self._on_chunk_selected)
    
    def _on_iff_loaded(self, iff):
        """Handle IFF loaded event - refresh entire panel."""
        self.current_iff = iff
        self.selected_chunk = None
        
        # Detect IFF type
        name = STATE.current_iff_name or ""
        self.current_iff_type = _get_iff_type(name, iff.chunks if iff else [])
        
        self._refresh_header()
        self._refresh_navigator()
        self._show_overview()
        self._refresh_footer()
    
    def _on_chunk_selected(self, chunk):
        """Handle chunk selection from this or other panels."""
        self.selected_chunk = chunk
        self._show_chunk_detail(chunk)
        # Enable export button
        if dpg.does_item_exist("btn_export_chunk"):
            dpg.configure_item("btn_export_chunk", enabled=(chunk is not None))
    
    # ═══════════════════════════════════════════════════════════════════
    # HEADER REFRESH
    # ═══════════════════════════════════════════════════════════════════
    
    def _refresh_header(self):
        """Refresh the header zone with current IFF info."""
        if self.current_iff is None:
            dpg.set_value("iff_header_title", "📦 No IFF loaded")
            dpg.set_value("iff_header_type", "—")
            dpg.set_value("iff_header_chunks", "—")
            dpg.set_value("iff_header_danger", "—")
            dpg.set_value("iff_header_danger_tip", "")
            return
        
        name = STATE.current_iff_name or "unknown.iff"
        chunk_count = len(self.current_iff.chunks)
        danger_text, danger_color, danger_tip = _get_danger_level(name, chunk_count, self.current_iff_type)
        
        # Type-specific icon
        type_icons = {
            "OBJECT": "📦", "CHARACTER": "👤", "GLOBAL": "🌐", "SEMI-GLOBAL": "📚"
        }
        icon = type_icons.get(self.current_iff_type, "📄")
        
        dpg.set_value("iff_header_title", f"{icon} {name}")
        dpg.set_value("iff_header_type", self.current_iff_type)
        dpg.set_value("iff_header_chunks", str(chunk_count))
        dpg.set_value("iff_header_danger", danger_text)
        dpg.set_value("iff_header_danger_tip", danger_tip)
        
        # Update danger color
        dpg.configure_item("iff_header_danger", color=danger_color)
    
    # ═══════════════════════════════════════════════════════════════════
    # NAVIGATOR REFRESH - Categorized Chunk Tree
    # ═══════════════════════════════════════════════════════════════════
    
    def _refresh_navigator(self):
        """Refresh the chunk navigator with categorized tree."""
        dpg.delete_item(self.NAV_TAG, children_only=True)
        
        if self.current_iff is None:
            dpg.add_text("Load an IFF file", parent=self.NAV_TAG, color=Colors.TEXT_DIM)
            return
        
        # Categorize all chunks
        categorized = self._categorize_chunks()
        
        # Create tree for each category
        for category_name, category_data in categorized.items():
            if not category_data["chunks"]:
                continue
            
            total_count = len(category_data["chunks"])
            icon = CHUNK_CATEGORIES.get(category_name, {}).get("icon", "📁")
            
            # Behaviors default open, others closed
            default_open = category_name in ["Behaviors", "Lifecycle"]
            
            with dpg.tree_node(
                label=f"{icon} {category_name} ({total_count})",
                parent=self.NAV_TAG,
                default_open=default_open
            ):
                # If subcategories exist (BHAVs), group by role
                if category_data["subcategories"]:
                    for sub_name, sub_chunks in category_data["subcategories"].items():
                        if not sub_chunks:
                            continue
                        sub_icon = {"ROLE": "🎯", "ACTION": "▶️", "FLOW": "🔀"}.get(sub_name, "•")
                        with dpg.tree_node(label=f"{sub_icon} {sub_name} ({len(sub_chunks)})", default_open=(sub_name == "ROLE")):
                            for chunk in sorted(sub_chunks, key=lambda c: c.chunk_id):
                                self._add_chunk_item(chunk)
                else:
                    # Flat list by chunk type
                    by_type = {}
                    for chunk in category_data["chunks"]:
                        ctype = chunk.chunk_type
                        if ctype not in by_type:
                            by_type[ctype] = []
                        by_type[ctype].append(chunk)
                    
                    for ctype, chunks in sorted(by_type.items()):
                        if len(by_type) > 1:
                            with dpg.tree_node(label=f"{ctype} ({len(chunks)})"):
                                for chunk in sorted(chunks, key=lambda c: c.chunk_id):
                                    self._add_chunk_item(chunk)
                        else:
                            for chunk in sorted(chunks, key=lambda c: c.chunk_id):
                                self._add_chunk_item(chunk)
    
    def _categorize_chunks(self) -> dict:
        """Categorize chunks into the defined categories."""
        result = {}
        assigned_chunks = set()
        
        for cat_name, cat_def in CHUNK_CATEGORIES.items():
            result[cat_name] = {"chunks": [], "subcategories": {}}
            
            for chunk in self.current_iff.chunks:
                if id(chunk) in assigned_chunks:
                    continue
                
                # Check if chunk type matches this category
                if cat_def["types"] and chunk.chunk_type not in cat_def["types"]:
                    continue
                
                # Special case: "Other" catches unassigned
                if cat_name == "Other" and cat_def["types"] == []:
                    result[cat_name]["chunks"].append(chunk)
                    assigned_chunks.add(id(chunk))
                    continue
                
                result[cat_name]["chunks"].append(chunk)
                assigned_chunks.add(id(chunk))
                
                # Apply subcategory filters
                for sub_name, sub_filter in cat_def.get("subcategories", {}).items():
                    if sub_name not in result[cat_name]["subcategories"]:
                        result[cat_name]["subcategories"][sub_name] = []
                    
                    if sub_filter(chunk):
                        result[cat_name]["subcategories"][sub_name].append(chunk)
        
        # Assign remaining to "Other"
        for chunk in self.current_iff.chunks:
            if id(chunk) not in assigned_chunks:
                result["Other"]["chunks"].append(chunk)
        
        return result
    
    def _add_chunk_item(self, chunk):
        """Add a single chunk item to the navigator with smart naming."""
        # Get smart human-readable name
        smart_name = _get_chunk_smart_name(chunk, self.current_iff)
        
        # Add modified indicator
        modified = "● " if chunk.chunk_id in self.modified_chunks else ""
        
        # Format: "#ID: SmartName"
        display = f"{modified}#{chunk.chunk_id}: {smart_name}"
        
        # Use buttons for clickable items (all chunks are clickable now)
        dpg.add_button(
            label=display,
            width=-1,
            callback=lambda s, a, c=chunk: self._on_nav_chunk_clicked(c)
        )
    
    def _on_nav_chunk_clicked(self, chunk):
        """Handle chunk click from navigator."""
        self.selected_chunk = chunk
        STATE.set_chunk(chunk)
        
        # Enable export button
        if dpg.does_item_exist("btn_export_chunk"):
            dpg.configure_item("btn_export_chunk", enabled=True)
        
        # Publish events
        EventBus.publish(Events.CHUNK_SELECTED, chunk)
        
        smart_name = _get_chunk_smart_name(chunk, self.current_iff)
        
        if chunk.chunk_type == "BHAV":
            inst_count = len(chunk.instructions) if hasattr(chunk, 'instructions') else 0
            EventBus.publish(Events.STATUS_UPDATE, 
                f"BHAV #{chunk.chunk_id}: {smart_name} ({inst_count} instructions)")
            EventBus.publish(Events.BHAV_SELECTED, chunk)
        else:
            EventBus.publish(Events.STATUS_UPDATE, 
                f"{chunk.chunk_type} #{chunk.chunk_id}: {smart_name}")
        
        # Show detail pane
        self._show_chunk_detail(chunk)
    
    # ═══════════════════════════════════════════════════════════════════
    # OVERVIEW PANE - Dashboard when nothing selected
    # ═══════════════════════════════════════════════════════════════════
    
    def _show_overview(self):
        """Show the overview dashboard in detail pane."""
        dpg.delete_item(self.DETAIL_TAG, children_only=True)
        
        if self.current_iff is None:
            dpg.add_text("Open an IFF file", parent=self.DETAIL_TAG, color=Colors.TEXT_DIM)
            return
        
        # Count chunks by category
        bhav_count = sum(1 for c in self.current_iff.chunks if c.chunk_type == "BHAV")
        ttab_count = sum(1 for c in self.current_iff.chunks if c.chunk_type == "TTAB")
        str_count = sum(1 for c in self.current_iff.chunks if c.chunk_type == "STR#")
        objd_count = sum(1 for c in self.current_iff.chunks if c.chunk_type == "OBJD")
        objf_count = sum(1 for c in self.current_iff.chunks if c.chunk_type == "OBJf")
        other_count = len(self.current_iff.chunks) - bhav_count - ttab_count - str_count - objd_count - objf_count
        
        # Classify BHAVs
        role_count = 0
        action_count = 0
        flow_count = 0
        for chunk in self.current_iff.chunks:
            if chunk.chunk_type == "BHAV":
                role = _classify_bhav_role(chunk)
                if role == "ROLE":
                    role_count += 1
                elif role == "ACTION":
                    action_count += 1
                else:
                    flow_count += 1
        
        dpg.add_text("📋 IFF Overview", parent=self.DETAIL_TAG, color=Colors.ACCENT_BLUE)
        dpg.add_separator(parent=self.DETAIL_TAG)
        dpg.add_spacer(height=10, parent=self.DETAIL_TAG)
        
        dpg.add_text("This object defines:", parent=self.DETAIL_TAG, color=Colors.TEXT_DIM)
        dpg.add_spacer(height=5, parent=self.DETAIL_TAG)
        
        if role_count:
            dpg.add_text(f"  • {role_count} Controller(s) (ROLE)", parent=self.DETAIL_TAG)
        if action_count:
            dpg.add_text(f"  • {action_count} Player Interaction(s)", parent=self.DETAIL_TAG)
        if flow_count:
            dpg.add_text(f"  • {flow_count} Flow Behavior(s)", parent=self.DETAIL_TAG)
        if ttab_count:
            dpg.add_text(f"  • {ttab_count} Interaction Table(s)", parent=self.DETAIL_TAG)
        if str_count:
            dpg.add_text(f"  • {str_count} String Resource(s)", parent=self.DETAIL_TAG)
        if objf_count:
            dpg.add_text(f"  • {objf_count} Object Function(s)", parent=self.DETAIL_TAG)
        if objd_count:
            dpg.add_text(f"  • {objd_count} Object Definition(s)", parent=self.DETAIL_TAG)
        if other_count:
            dpg.add_text(f"  • {other_count} Other Resource(s)", parent=self.DETAIL_TAG, color=Colors.TEXT_DIM)
        
        dpg.add_spacer(height=20, parent=self.DETAIL_TAG)
        dpg.add_separator(parent=self.DETAIL_TAG)
        dpg.add_spacer(height=10, parent=self.DETAIL_TAG)
        
        dpg.add_text("👉 Select a behavior to inspect or edit.", parent=self.DETAIL_TAG, color=Colors.ACCENT_GREEN)
    
    # ═══════════════════════════════════════════════════════════════════
    # CHUNK DETAIL PANE - Context-sensitive
    # ═══════════════════════════════════════════════════════════════════
    
    def _show_chunk_detail(self, chunk):
        """Show detail view for selected chunk."""
        dpg.delete_item(self.DETAIL_TAG, children_only=True)
        
        if chunk is None:
            self._show_overview()
            return
        
        if chunk.chunk_type == "BHAV":
            self._show_bhav_detail(chunk)
        elif chunk.chunk_type == "TTAB":
            self._show_ttab_detail(chunk)
        elif chunk.chunk_type == "OBJf":
            self._show_objf_detail(chunk)
        else:
            self._show_generic_detail(chunk)
    
    def _show_bhav_detail(self, bhav):
        """Show BHAV-specific detail view."""
        label = bhav.chunk_label or "(unnamed)"
        role = _classify_bhav_role(bhav)
        inst_count = len(bhav.instructions) if hasattr(bhav, 'instructions') else 0
        
        dpg.add_text(f"🧠 {label}", parent=self.DETAIL_TAG, color=Colors.ACCENT_BLUE)
        dpg.add_separator(parent=self.DETAIL_TAG)
        
        with dpg.group(parent=self.DETAIL_TAG):
            dpg.add_text(f"Type: BHAV (Behavior)", color=Colors.TEXT_DIM)
            dpg.add_text(f"ID: #{bhav.chunk_id}")
            dpg.add_text(f"Role: {role}")
            dpg.add_text(f"Instructions: {inst_count}")
        
        dpg.add_spacer(height=10, parent=self.DETAIL_TAG)
        dpg.add_separator(parent=self.DETAIL_TAG)
        dpg.add_spacer(height=10, parent=self.DETAIL_TAG)
        
        # Edit mode selector
        dpg.add_text("Edit Mode:", parent=self.DETAIL_TAG, color=Colors.TEXT_DIM)
        with dpg.group(parent=self.DETAIL_TAG):
            dpg.add_radio_button(
                items=["Safe (local copy)", "Override (advanced)", "Global (⚠️ dangerous)"],
                default_value="Safe (local copy)",
                tag=f"edit_mode_{bhav.chunk_id}"
            )
        
        dpg.add_spacer(height=10, parent=self.DETAIL_TAG)
        dpg.add_separator(parent=self.DETAIL_TAG)
        dpg.add_spacer(height=10, parent=self.DETAIL_TAG)
        
        # Action buttons
        dpg.add_text("Actions:", parent=self.DETAIL_TAG, color=Colors.TEXT_DIM)
        with dpg.group(horizontal=True, parent=self.DETAIL_TAG):
            dpg.add_button(label="🔍 Inspect", callback=lambda: self._inspect_chunk(bhav))
            dpg.add_button(label="🧠 View Graph", callback=lambda: self._view_graph(bhav))
        with dpg.group(horizontal=True, parent=self.DETAIL_TAG):
            dpg.add_button(label="✏️ Edit", callback=lambda: self._edit_chunk(bhav))
            dpg.add_button(label="🌱 Fork", callback=lambda: self._fork_chunk(bhav))
    
    def _show_ttab_detail(self, ttab):
        """Show TTAB-specific detail view."""
        label = ttab.chunk_label or "(unnamed)"
        
        dpg.add_text(f"📋 {label}", parent=self.DETAIL_TAG, color=Colors.ACCENT_BLUE)
        dpg.add_separator(parent=self.DETAIL_TAG)
        
        with dpg.group(parent=self.DETAIL_TAG):
            dpg.add_text(f"Type: TTAB (Tree Table)", color=Colors.TEXT_DIM)
            dpg.add_text(f"ID: #{ttab.chunk_id}")
            
            if hasattr(ttab, 'interactions') and ttab.interactions:
                dpg.add_text(f"Interactions: {len(ttab.interactions)}")
                dpg.add_spacer(height=5)
                dpg.add_text("Pie Menu Entries:", color=Colors.ACCENT_GREEN)
                
                # Show first few interactions
                for i, inter in enumerate(ttab.interactions[:8]):
                    test_str = f"T:0x{inter.test_function:04X}" if inter.test_function else "T:—"
                    act_str = f"A:0x{inter.action_function:04X}" if inter.action_function else "A:—"
                    dpg.add_text(f"  [{i}] {test_str} {act_str}", color=Colors.TEXT_DIM)
                
                if len(ttab.interactions) > 8:
                    dpg.add_text(f"  ... ({len(ttab.interactions) - 8} more)", color=Colors.TEXT_DIM)
        
        dpg.add_spacer(height=10, parent=self.DETAIL_TAG)
        dpg.add_button(label="🔍 Inspect", parent=self.DETAIL_TAG, callback=lambda: self._inspect_chunk(ttab))
    
    def _show_objf_detail(self, objf):
        """Show OBJf-specific detail view with lifecycle entries."""
        label = objf.chunk_label or "Object Functions"
        
        dpg.add_text(f"⚙️ {label}", parent=self.DETAIL_TAG, color=Colors.ACCENT_BLUE)
        dpg.add_separator(parent=self.DETAIL_TAG)
        
        with dpg.group(parent=self.DETAIL_TAG):
            dpg.add_text(f"Type: OBJf (Object Functions)", color=Colors.TEXT_DIM)
            dpg.add_text(f"ID: #{objf.chunk_id}")
            
            if hasattr(objf, 'functions') and objf.functions:
                active = sum(1 for f in objf.functions if f.action_function or f.condition_function)
                dpg.add_text(f"Entries: {len(objf.functions)} ({active} active)")
                dpg.add_spacer(height=5)
                dpg.add_text("Lifecycle Hooks:", color=Colors.ACCENT_GREEN)
                
                # Show active entries
                for i, entry in enumerate(objf.functions):
                    if not entry.action_function and not entry.condition_function:
                        continue
                    
                    name = OBJF_ENTRY_NAMES[i] if i < len(OBJF_ENTRY_NAMES) else f"Entry_{i}"
                    guard_str = f"G:0x{entry.condition_function:04X}" if entry.condition_function else "G:—"
                    act_str = f"A:0x{entry.action_function:04X}" if entry.action_function else "A:—"
                    
                    # Make clickable buttons for BHAVs
                    with dpg.group(horizontal=True, parent=self.DETAIL_TAG):
                        dpg.add_text(f"  {name}:", color=Colors.TEXT_DIM)
                        if entry.action_function:
                            dpg.add_button(
                                label=act_str, 
                                callback=lambda s, a, bhav_id=entry.action_function: self._goto_bhav(bhav_id),
                                small=True
                            )
        
        dpg.add_spacer(height=10, parent=self.DETAIL_TAG)
        dpg.add_button(label="🔍 Inspect", parent=self.DETAIL_TAG, callback=lambda: self._inspect_chunk(objf))
    
    def _show_generic_detail(self, chunk):
        """Show generic chunk detail view."""
        smart_name = _get_chunk_smart_name(chunk, self.current_iff)
        
        dpg.add_text(f"📄 {smart_name}", parent=self.DETAIL_TAG, color=Colors.TEXT_DIM)
        dpg.add_separator(parent=self.DETAIL_TAG)
        
        with dpg.group(parent=self.DETAIL_TAG):
            dpg.add_text(f"Type: {chunk.chunk_type}", color=Colors.TEXT_DIM)
            dpg.add_text(f"ID: #{chunk.chunk_id}")
            if chunk.chunk_label:
                dpg.add_text(f"Label: {chunk.chunk_label}")
            if hasattr(chunk, 'original_data') and chunk.original_data:
                dpg.add_text(f"Size: {len(chunk.original_data)} bytes")
            elif hasattr(chunk, 'chunk_data') and chunk.chunk_data:
                dpg.add_text(f"Size: {len(chunk.chunk_data)} bytes")
        
        dpg.add_spacer(height=10, parent=self.DETAIL_TAG)
        dpg.add_button(label="🔍 Inspect", parent=self.DETAIL_TAG, callback=lambda: self._inspect_chunk(chunk))
    
    # ═══════════════════════════════════════════════════════════════════
    # FOOTER REFRESH
    # ═══════════════════════════════════════════════════════════════════
    
    def _refresh_footer(self):
        """Refresh footer status text."""
        if self.current_iff is None:
            dpg.set_value("iff_footer_refs", "Load an IFF to begin")
            return
        
        # Show type-specific info
        type_msgs = {
            "GLOBAL": "⚠️ GLOBAL - changes affect ALL objects",
            "SEMI-GLOBAL": "📚 Semi-Global library file",
            "CHARACTER": "👤 Character/NPC definition",
            "OBJECT": "📦 Object definition"
        }
        dpg.set_value("iff_footer_refs", type_msgs.get(self.current_iff_type, ""))
    
    # ═══════════════════════════════════════════════════════════════════
    # ACTION HANDLERS
    # ═══════════════════════════════════════════════════════════════════
    
    def _goto_bhav(self, bhav_id: int):
        """Navigate to a BHAV by ID."""
        if not self.current_iff:
            return
        
        for chunk in self.current_iff.chunks:
            if chunk.chunk_type == "BHAV" and chunk.chunk_id == bhav_id:
                self._on_nav_chunk_clicked(chunk)
                return
        
        EventBus.publish(Events.STATUS_UPDATE, f"BHAV 0x{bhav_id:04X} not found in this IFF")
    
    def _inspect_chunk(self, chunk):
        """Open chunk inspector for the chunk."""
        STATE.set_chunk(chunk)
        EventBus.publish(Events.CHUNK_SELECTED, chunk)
        EventBus.publish(Events.STATUS_UPDATE, f"Inspecting: {chunk.chunk_type} #{chunk.chunk_id}")
    
    def _view_graph(self, bhav):
        """Open BHAV graph editor."""
        STATE.current_bhav = bhav
        EventBus.publish(Events.BHAV_SELECTED, bhav)
        EventBus.publish(Events.STATUS_UPDATE, f"Opening graph: {bhav.chunk_label or 'BHAV'}")
    
    def _edit_chunk(self, chunk):
        """Enter edit mode for chunk."""
        # Mark as modified
        self.modified_chunks.add(chunk.chunk_id)
        self._refresh_navigator()  # Update display to show modified indicator
        EventBus.publish(Events.STATUS_UPDATE, f"Editing: {chunk.chunk_type} #{chunk.chunk_id}")
    
    def _fork_chunk(self, chunk):
        """Create a local copy/fork of chunk."""
        EventBus.publish(Events.STATUS_UPDATE, f"Forking: {chunk.chunk_type} #{chunk.chunk_id} (not implemented)")
    
    def _on_export_chunk(self):
        """Export selected chunk."""
        if not self.selected_chunk:
            EventBus.publish(Events.STATUS_UPDATE, "No chunk selected to export")
            return
        EventBus.publish(Events.STATUS_UPDATE, f"Export: {self.selected_chunk.chunk_type} #{self.selected_chunk.chunk_id} (not implemented)")
    
    def _show_opcode_reference(self):
        """Show opcode reference panel/popup."""
        EventBus.publish(Events.STATUS_UPDATE, "Opcode reference (TODO: implement popup)")
    
    def _show_behavior_dict(self):
        """Show behavior dictionary panel/popup."""
        EventBus.publish(Events.STATUS_UPDATE, "Behavior dictionary (TODO: implement popup)")
    
    # ═══════════════════════════════════════════════════════════════════
    # PANEL MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════
    
    def _on_close(self):
        """Handle panel close - hide instead of destroy."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel (used by View menu)."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
