"""
Global Search / Finder Panel

Search by ID or semantic name across loaded files.
Jump to inspector / graph from results.

BHAV AWARENESS (from Conceptual Directives):
Every opcode, every BHAV call should be labeled with semantic names.
Search must work with semantic names, not just raw IDs.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE

# Import engine toolkit for semantic BHAV labeling
try:
    from forensic.engine_toolkit import EngineToolkit
    _toolkit = EngineToolkit()
    _toolkit_available = True
except ImportError:
    _toolkit = None
    _toolkit_available = False


class GlobalSearchPanel:
    """Global search / finder panel with semantic BHAV awareness."""
    
    TAG = "global_search"
    RESULTS_TAG = "search_results"
    SEARCH_INPUT_TAG = "search_input"
    
    def __init__(self, width: int = 400, height: int = 300, pos: tuple = (500, 100)):
        self.width = width
        self.height = height
        self.pos = pos
        self.results = []
        self._semantic_cache = {}  # Cache semantic names for quick search
        self._opcode_effects = {}  # Cache opcode -> effect category
        self._lifecycle_cache = {}  # Cache BHAV -> lifecycle phase
        self._create_panel()
        self._build_effect_caches()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SEMANTIC FILTER CONSTANTS (Principle #6: If a query can't express meaning, it's incomplete)
    # ═══════════════════════════════════════════════════════════════════════════
    
    EFFECT_FILTERS = [
        "Any Effect",
        "Motive Change",      # Sleep, Hunger, Fun, etc.
        "Relationship",       # REL primitives
        "Object Interaction", # Object manipulation
        "Animation/Sound",    # Animate, Sound primitives
        "Memory/Data",        # Data read/write
        "Control Flow",       # Branching, calls
        "Error/Idle",         # Error handling, idle
    ]
    
    LIFECYCLE_FILTERS = [
        "Any Phase",
        "Init",          # Initialization behaviors
        "Main",          # Main interaction loops
        "Cleanup",       # Termination, cleanup
        "Timer/Periodic",# Timed callbacks
        "UI/Menu",       # Pie menu, UI-related
    ]
    
    SAFETY_FILTERS = [
        "Any Safety",
        "🟢 Safe",       # Read-only, no side effects
        "🟡 Caution",    # Has side effects but reversible
        "🔴 Dangerous",  # Irreversible, save-affecting
    ]
    
    def _create_panel(self):
        """Create the search panel with semantic filters."""
        with dpg.window(
            label="Global Search",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            show=False,  # Hidden by default
            on_close=self._on_close
        ):
            dpg.add_text("Semantic Search", color=(0, 212, 255, 255))
            dpg.add_text("Find BHAVs by meaning, not just text", color=(136, 136, 136, 255))
            
            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    tag=self.SEARCH_INPUT_TAG,
                    width=280,
                    hint="ID, label, or semantic (e.g. 'motive', 'init')",
                    on_enter=True,
                    callback=self._on_search
                )
                dpg.add_button(
                    label="🔍",
                    width=40,
                    callback=self._on_search
                )
            
            dpg.add_separator()
            
            # ═══════════════════════════════════════════════════════════════════
            # SEMANTIC FILTERS - First-class citizens, not afterthoughts
            # ═══════════════════════════════════════════════════════════════════
            
            dpg.add_text("⚙️ Semantic Filters", color=(233, 69, 96, 255))
            
            with dpg.group(horizontal=True):
                dpg.add_text("Effect:", color=(136, 136, 136, 255))
                dpg.add_combo(
                    items=self.EFFECT_FILTERS,
                    default_value="Any Effect",
                    width=140,
                    tag="filter_effect"
                )
                dpg.add_text("Lifecycle:", color=(136, 136, 136, 255))
                dpg.add_combo(
                    items=self.LIFECYCLE_FILTERS,
                    default_value="Any Phase",
                    width=120,
                    tag="filter_lifecycle"
                )
            
            with dpg.group(horizontal=True):
                dpg.add_text("Safety:", color=(136, 136, 136, 255))
                dpg.add_combo(
                    items=self.SAFETY_FILTERS,
                    default_value="Any Safety",
                    width=120,
                    tag="filter_safety"
                )
            
            dpg.add_separator()
            
            # Search scope (expanded for cross-pack)
            with dpg.group(horizontal=True):
                dpg.add_text("Scope:", color=(136, 136, 136, 255))
                dpg.add_radio_button(
                    items=["Current File", "All Global", "Primitives", "Cross-Pack"],
                    default_value="Current File",
                    horizontal=True,
                    tag="search_scope"
                )
            
            dpg.add_separator()
            
            dpg.add_text("Results:", color=(136, 136, 136, 255))
            dpg.add_listbox(
                items=[],
                tag=self.RESULTS_TAG,
                width=-1,
                num_items=10,
                callback=self._on_result_selected
            )
            
            # Provenance indicator for selected result
            dpg.add_text("", tag="result_provenance", color=(136, 136, 136, 255))
    
    def _build_effect_caches(self):
        """Build caches for semantic effect categorization."""
        # Map opcode ranges to effect categories
        self._opcode_effects = {
            # Motive primitives (0x01-0x0F in some contexts)
            'motive': {0x01, 0x02, 0x03, 0x04, 0x05},
            # Relationship primitives
            'relationship': {0x1D, 0x1E, 0x1F, 0x27},  # REL primitives
            # Object interaction
            'object': {0x0D, 0x0E, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15},
            # Animation/Sound
            'animate': {0x00, 0x07, 0x33, 0x35, 0x36},  # Animate, Sounds
            # Memory/Data
            'data': {0x06, 0x09, 0x0A, 0x0B, 0x0C, 0x16, 0x17},
            # Control flow
            'control': {0x02, 0x08, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45},
            # Error/Idle
            'error': {0x18, 0x19, 0x1A, 0x1B, 0x1C},
        }
        
        # Build lifecycle hints from semantic names
        self._lifecycle_keywords = {
            'init': ['init', 'setup', 'create', 'spawn', 'load'],
            'main': ['main', 'loop', 'run', 'execute', 'do'],
            'cleanup': ['cleanup', 'destroy', 'delete', 'remove', 'end'],
            'timer': ['timer', 'tick', 'periodic', 'repeat', 'interval'],
            'ui': ['menu', 'pie', 'ui', 'dialog', 'click', 'button'],
        }
    
    def _get_effect_category(self, bhav_chunk) -> str:
        """Determine effect category for a BHAV based on its opcodes."""
        if not hasattr(bhav_chunk, 'instructions'):
            return "unknown"
        
        # Count opcode categories
        category_counts = {cat: 0 for cat in self._opcode_effects.keys()}
        
        for instr in getattr(bhav_chunk, 'instructions', []):
            opcode = getattr(instr, 'opcode', 0) & 0xFF
            for cat, opcodes in self._opcode_effects.items():
                if opcode in opcodes:
                    category_counts[cat] += 1
        
        # Return dominant category
        if sum(category_counts.values()) == 0:
            return "unknown"
        return max(category_counts, key=category_counts.get)
    
    def _get_lifecycle_phase(self, name: str) -> str:
        """Determine lifecycle phase from semantic name."""
        name_lower = name.lower()
        for phase, keywords in self._lifecycle_keywords.items():
            if any(kw in name_lower for kw in keywords):
                return phase
        return "unknown"
    
    def _get_safety_level(self, bhav_chunk) -> str:
        """Determine safety level for a BHAV."""
        try:
            from safety import SafetyLevel, is_safe_to_edit
            level = is_safe_to_edit(bhav_chunk)
            if level == SafetyLevel.SAFE:
                return "safe"
            elif level == SafetyLevel.WARN:
                return "caution"
            else:
                return "dangerous"
        except:
            return "unknown"
    
    def _matches_filters(self, chunk, semantic_name: str = "") -> bool:
        """Check if chunk matches current semantic filters."""
        effect_filter = dpg.get_value("filter_effect")
        lifecycle_filter = dpg.get_value("filter_lifecycle")
        safety_filter = dpg.get_value("filter_safety")
        
        # Effect filter
        if effect_filter != "Any Effect":
            effect_map = {
                "Motive Change": "motive",
                "Relationship": "relationship",
                "Object Interaction": "object",
                "Animation/Sound": "animate",
                "Memory/Data": "data",
                "Control Flow": "control",
                "Error/Idle": "error",
            }
            required = effect_map.get(effect_filter, "")
            if required and self._get_effect_category(chunk) != required:
                return False
        
        # Lifecycle filter
        if lifecycle_filter != "Any Phase":
            phase_map = {
                "Init": "init",
                "Main": "main",
                "Cleanup": "cleanup",
                "Timer/Periodic": "timer",
                "UI/Menu": "ui",
            }
            required = phase_map.get(lifecycle_filter, "")
            if required and self._get_lifecycle_phase(semantic_name) != required:
                return False
        
        # Safety filter
        if safety_filter != "Any Safety":
            safety_map = {
                "🟢 Safe": "safe",
                "🟡 Caution": "caution",
                "🔴 Dangerous": "dangerous",
            }
            required = safety_map.get(safety_filter, "")
            if required and self._get_safety_level(chunk) != required:
                return False
        
        return True
    
    def _build_semantic_cache(self):
        """Build cache of semantic names for fast search."""
        if not _toolkit_available or not _toolkit:
            return
        
        self._semantic_cache.clear()
        
        # Cache global BHAV names (0x100 - 0x0FFF)
        for bhav_id in range(0x100, 0x1000):
            try:
                name = _toolkit.label_global(bhav_id)
                if name and not name.startswith("Global_"):
                    self._semantic_cache[bhav_id] = name.lower()
            except:
                pass
    
    def _on_search(self, sender=None, value=None):
        """Handle search with semantic BHAV awareness and filters."""
        query = dpg.get_value(self.SEARCH_INPUT_TAG).strip().lower()
        
        self.results = []
        items = []
        scope = dpg.get_value("search_scope")
        
        # Build semantic cache if needed
        if not self._semantic_cache:
            self._build_semantic_cache()
        
        # ═══════════════════════════════════════════════════════════════════
        # FILTER-ONLY MODE: If no query but filters set, find by filters alone
        # ═══════════════════════════════════════════════════════════════════
        filters_active = (
            dpg.get_value("filter_effect") != "Any Effect" or
            dpg.get_value("filter_lifecycle") != "Any Phase" or
            dpg.get_value("filter_safety") != "Any Safety"
        )
        
        # Search in current IFF
        if STATE.current_iff and scope == "Current File":
            for chunk in STATE.current_iff.chunks:
                match = False
                display = ""
                semantic_name = ""
                
                # Get semantic name for BHAV
                if chunk.chunk_type == "BHAV" and chunk.chunk_id in self._semantic_cache:
                    semantic_name = _toolkit.label_global(chunk.chunk_id) if _toolkit else ""
                
                # If no query but filters active, match all chunks
                if not query and filters_active:
                    if chunk.chunk_type == "BHAV":  # Only BHAVs for filter-only mode
                        match = True
                        display = f"BHAV #{chunk.chunk_id} ⟨{semantic_name or 'unnamed'}⟩"
                
                # Match by ID (decimal)
                elif query and query.isdigit() and chunk.chunk_id == int(query):
                    match = True
                    display = f"{chunk.chunk_type} #{chunk.chunk_id}"
                
                # Match by hex ID
                elif query and query.startswith("0x"):
                    try:
                        if chunk.chunk_id == int(query, 16):
                            match = True
                            display = f"{chunk.chunk_type} #{chunk.chunk_id}"
                    except:
                        pass
                
                # Match by label
                elif query and hasattr(chunk, 'chunk_label') and query in (chunk.chunk_label or "").lower():
                    match = True
                    label = chunk.chunk_label or "(no label)"
                    display = f"{chunk.chunk_type} #{chunk.chunk_id} ({label})"
                
                # Match by semantic name (BHAV only)
                elif query and chunk.chunk_type == "BHAV" and chunk.chunk_id in self._semantic_cache:
                    if query in self._semantic_cache[chunk.chunk_id]:
                        match = True
                        display = f"BHAV #{chunk.chunk_id} ⟨{semantic_name}⟩"
                
                # Apply semantic filters
                if match and not self._matches_filters(chunk, semantic_name):
                    match = False
                
                if match:
                    # Add safety badge to display
                    safety = self._get_safety_level(chunk)
                    safety_badge = {"safe": "🟢", "caution": "🟡", "dangerous": "🔴"}.get(safety, "⚪")
                    items.append(f"{safety_badge} {display}")
                    self.results.append(chunk)
        
        # Search in global BHAVs (semantic names from engine toolkit)
        if scope == "All Global" and _toolkit_available:
            for bhav_id, semantic_lower in self._semantic_cache.items():
                match = False
                if not query and filters_active:
                    match = True  # Filter-only mode
                elif query and query in semantic_lower:
                    match = True
                
                if match:
                    semantic = _toolkit.label_global(bhav_id)
                    # Check lifecycle filter for globals
                    if dpg.get_value("filter_lifecycle") != "Any Phase":
                        phase = self._get_lifecycle_phase(semantic)
                        phase_map = {"Init": "init", "Main": "main", "Cleanup": "cleanup",
                                     "Timer/Periodic": "timer", "UI/Menu": "ui"}
                        required = phase_map.get(dpg.get_value("filter_lifecycle"), "")
                        if required and phase != required:
                            continue
                    
                    items.append(f"🔵 Global BHAV 0x{bhav_id:04X} ⟨{semantic}⟩")
                    self.results.append(('global_bhav', bhav_id, semantic))
        
        # Search in primitives
        if scope == "Primitives":
            try:
                from core.opcode_loader import get_opcode_info
                for op in range(256):
                    info = get_opcode_info(op)
                    name = info.get('name', '').lower()
                    match = False
                    if not query and filters_active:
                        match = True  # Filter-only
                    elif query and query in name:
                        match = True
                    
                    if match:
                        # Check effect filter for primitives
                        if dpg.get_value("filter_effect") != "Any Effect":
                            effect_map = {
                                "Motive Change": "motive", "Relationship": "relationship",
                                "Object Interaction": "object", "Animation/Sound": "animate",
                                "Memory/Data": "data", "Control Flow": "control", "Error/Idle": "error",
                            }
                            required_effect = effect_map.get(dpg.get_value("filter_effect"), "")
                            # Check if opcode is in the effect category
                            if required_effect and op not in self._opcode_effects.get(required_effect, set()):
                                continue
                        
                        items.append(f"⚙️ Primitive 0x{op:02X}: {info.get('name', 'Unknown')}")
                        self.results.append(('primitive', op, info.get('name', '')))
            except ImportError:
                pass
        
        # Cross-Pack search: Find same BHAV ID across multiple loaded IFFs
        if scope == "Cross-Pack" and hasattr(STATE, 'loaded_iffs'):
            target_id = None
            if query.isdigit():
                target_id = int(query)
            elif query.startswith("0x"):
                try:
                    target_id = int(query, 16)
                except:
                    pass
            
            if target_id is not None:
                for pack_name, iff in getattr(STATE, 'loaded_iffs', {}).items():
                    for chunk in iff.chunks:
                        if chunk.chunk_type == "BHAV" and chunk.chunk_id == target_id:
                            semantic_name = ""
                            if chunk.chunk_id in self._semantic_cache:
                                semantic_name = _toolkit.label_global(chunk.chunk_id) if _toolkit else ""
                            
                            if self._matches_filters(chunk, semantic_name):
                                safety = self._get_safety_level(chunk)
                                safety_badge = {"safe": "🟢", "caution": "🟡", "dangerous": "🔴"}.get(safety, "⚪")
                                items.append(f"{safety_badge} [{pack_name}] BHAV #{target_id} ⟨{semantic_name or 'unnamed'}⟩")
                                self.results.append(('cross_pack', pack_name, chunk))
        
        # Update results
        if not items and not query and not filters_active:
            dpg.configure_item(self.RESULTS_TAG, items=["Enter query or set filters"])
        else:
            dpg.configure_item(self.RESULTS_TAG, items=items if items else ["No results match filters"])
    
    def _on_result_selected(self, sender, value):
        """Handle result selection - jump to chunk with provenance display."""
        if value is None or value >= len(self.results):
            return
        
        result = self.results[value]
        
        # Handle tuple results (global_bhav, primitive, cross_pack)
        if isinstance(result, tuple):
            result_type = result[0]
            if result_type == 'global_bhav':
                # Publish search result event for global BHAV
                EventBus.publish(Events.SEARCH_RESULT_SELECTED, {
                    'type': 'global_bhav',
                    'id': result[1],
                    'name': result[2],
                })
                # Update provenance display
                dpg.set_value("result_provenance", 
                    f"📚 Source: FreeSO Engine Toolkit | Confidence: HIGH")
            elif result_type == 'primitive':
                EventBus.publish(Events.SEARCH_RESULT_SELECTED, {
                    'type': 'primitive',
                    'opcode': result[1],
                    'name': result[2],
                })
                dpg.set_value("result_provenance",
                    f"📚 Source: Opcode Database | Confidence: HIGH")
            elif result_type == 'cross_pack':
                pack_name = result[1]
                chunk = result[2]
                EventBus.publish(Events.SEARCH_RESULT_SELECTED, {
                    'type': 'cross_pack',
                    'pack': pack_name,
                    'chunk': chunk,
                })
                dpg.set_value("result_provenance",
                    f"📦 Pack: {pack_name} | Cross-pack equivalence match")
            return
        
        # Handle chunk results
        chunk = result
        STATE.current_chunk = chunk
        EventBus.publish(Events.CHUNK_SELECTED, chunk)
        
        if chunk.chunk_type == "BHAV":
            EventBus.publish(Events.BHAV_SELECTED, chunk)
            # Show provenance for BHAV
            semantic = ""
            if chunk.chunk_id in self._semantic_cache and _toolkit:
                semantic = _toolkit.label_global(chunk.chunk_id)
                dpg.set_value("result_provenance",
                    f"📚 Semantic: {semantic} | Source: FreeSO | Confidence: HIGH")
            else:
                dpg.set_value("result_provenance",
                    f"📚 Source: Local IFF | Confidence: OBSERVED")
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)


class PreferencesPanel:
    """Application preferences panel."""
    
    TAG = "preferences"
    
    def __init__(self, width: int = 400, height: int = 350, pos: tuple = (500, 200)):
        self.width = width
        self.height = height
        self.pos = pos
        self._create_panel()
    
    def _create_panel(self):
        """Create the preferences panel."""
        with dpg.window(
            label="Preferences",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            show=False,  # Hidden by default
            on_close=self._on_close
        ):
            dpg.add_text("Settings", color=(0, 212, 255, 255))
            dpg.add_separator()
            
            # Theme
            dpg.add_text("🎨 Theme", color=(233, 69, 96, 255))
            dpg.add_combo(
                items=["Dark (Default)", "Light", "High Contrast"],
                default_value="Dark (Default)",
                width=200,
                callback=self._on_theme_changed
            )
            
            dpg.add_separator()
            
            # Paths
            dpg.add_text("📁 Paths", color=(233, 69, 96, 255))
            dpg.add_text("Game Directory:", color=(136, 136, 136, 255))
            dpg.add_input_text(
                default_value=STATE.game_path,
                width=-1,
                tag="pref_game_path"
            )
            dpg.add_text("Save Directory:", color=(136, 136, 136, 255))
            dpg.add_input_text(
                default_value=STATE.save_path,
                width=-1,
                tag="pref_save_path"
            )
            
            dpg.add_separator()
            
            # Safety
            dpg.add_text("⚠️ Safety", color=(233, 69, 96, 255))
            dpg.add_checkbox(
                label="Enable strict safety checks",
                default_value=True,
                tag="pref_strict_safety"
            )
            dpg.add_checkbox(
                label="Auto-backup before edits",
                default_value=True,
                tag="pref_auto_backup"
            )
            
            dpg.add_separator()
            
            # Debug
            dpg.add_text("🔧 Debug", color=(233, 69, 96, 255))
            dpg.add_checkbox(
                label="Show debug logging",
                default_value=False,
                tag="pref_debug"
            )
            
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Save",
                    width=100,
                    callback=self._on_save
                )
                dpg.add_button(
                    label="Cancel",
                    width=100,
                    callback=self._on_close
                )
    
    def _on_theme_changed(self, sender, value):
        """Handle theme change."""
        print(f"Theme changed to: {value}")
    
    def _on_save(self):
        """Save preferences."""
        STATE.game_path = dpg.get_value("pref_game_path")
        STATE.save_path = dpg.get_value("pref_save_path")
        print("Preferences saved")
        self._on_close()
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)


class LogPanel:
    """Log / diagnostics panel."""
    
    TAG = "log_panel"
    LOG_OUTPUT_TAG = "log_output"
    
    _messages = []
    
    def __init__(self, width: int = 600, height: int = 200, pos: tuple = (400, 650)):
        self.width = width
        self.height = height
        self.pos = pos
        self._create_panel()
    
    def _create_panel(self):
        """Create the log panel."""
        with dpg.window(
            label="Log / Diagnostics",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            show=False,  # Hidden by default
            on_close=self._on_close
        ):
            with dpg.group(horizontal=True):
                dpg.add_text("📋 Log Output", color=(0, 212, 255, 255))
                dpg.add_button(
                    label="Clear",
                    width=60,
                    callback=self._on_clear
                )
                dpg.add_button(
                    label="Export",
                    width=60,
                    callback=self._on_export
                )
            
            dpg.add_separator()
            
            dpg.add_input_text(
                tag=self.LOG_OUTPUT_TAG,
                multiline=True,
                readonly=True,
                width=-1,
                height=-1,
                default_value=""
            )
    
    @classmethod
    def log(cls, message: str, level: str = "INFO"):
        """Add a log message."""
        formatted = f"[{level}] {message}"
        cls._messages.append(formatted)
        
        # Keep last 500 messages
        if len(cls._messages) > 500:
            cls._messages = cls._messages[-500:]
        
        # Update display if exists
        if dpg.does_item_exist(cls.LOG_OUTPUT_TAG):
            dpg.set_value(cls.LOG_OUTPUT_TAG, "\n".join(cls._messages))
    
    def _on_clear(self):
        """Clear log."""
        LogPanel._messages = []
        dpg.set_value(self.LOG_OUTPUT_TAG, "")
    
    def _on_export(self):
        """Export log to file."""
        log_file = Path("simobliterator_log.txt")
        with open(log_file, 'w') as f:
            f.write("\n".join(LogPanel._messages))
        print(f"Log exported to {log_file}")
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
