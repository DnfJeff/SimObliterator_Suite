"""
Graph Canvas Panel - Native Node Graph Viewer

Replaces web-based THREE.js graph with DearPyGUI node_editor.
Displays BHAV relationships, function dependencies, and flow analysis.

CRITICAL DIRECTIVE: Graphs are EXPLANATORY
The graph must answer: "What depends on this?"
Not just pretty visualization - actual dependency analysis.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys
import math

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE

# Import relationship graph for dependency analysis
try:
    from Tools.entities import RelationshipGraph, RelationType
    _graph_entities_available = True
except ImportError:
    RelationshipGraph = None
    _graph_entities_available = False

# Import engine toolkit for semantic labeling
try:
    from forensic.engine_toolkit import EngineToolkit
    _toolkit = EngineToolkit()
    _toolkit_available = True
except ImportError:
    _toolkit = None
    _toolkit_available = False


class GraphCanvasPanel:
    """Native graph canvas with dependency analysis ('What depends on this?')."""
    
    TAG = "graph_canvas"
    EDITOR_TAG = "graph_node_editor"
    DEPS_TAG = "deps_panel"  # Dependency analysis panel
    
    # Color palette
    COLORS = {
        'cyan': (0, 212, 255),
        'red': (233, 69, 96),
        'green': (76, 175, 80),
        'yellow': (255, 235, 59),
        'purple': (156, 39, 176),
        'orange': (255, 152, 0),
        'text': (224, 224, 224),
        'dim': (136, 136, 136),
        'bg': (26, 26, 46),
    }
    
    # Node type colors
    NODE_COLORS = {
        'BHAV': 'cyan',
        'OBJD': 'green',
        'TTAB': 'yellow',
        'GLOB': 'purple',
        'BCON': 'orange',
        'default': 'dim',
    }
    
    def __init__(self, width: int = 700, height: int = 500, pos: tuple = (100, 100)):
        self.width = width
        self.height = height
        self.pos = pos
        self.nodes = {}
        self.links = []
        self.node_counter = 0
        self.link_counter = 0
        self.selected_node = None
        self.dependency_graph = None  # RelationshipGraph for dependency analysis
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the graph canvas panel."""
        with dpg.window(
            label="Graph Viewer",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            # Toolbar
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Clear",
                    callback=self.clear_graph,
                    width=60
                )
                dpg.add_button(
                    label="Auto Layout",
                    callback=self._auto_layout,
                    width=80
                )
                dpg.add_button(
                    label="Zoom Fit",
                    callback=self._zoom_fit,
                    width=70
                )
                dpg.add_separator()
                # CRITICAL: The dependency question
                dpg.add_button(
                    label="What depends on this?",
                    callback=self._show_dependents,
                    width=140
                )
                dpg.add_button(
                    label="What does this use?",
                    callback=self._show_dependencies,
                    width=130
                )
            
            with dpg.group(horizontal=True):
                dpg.add_text("Graph Viewer", color=self.COLORS['cyan'])
                dpg.add_spacer(width=50)
                dpg.add_text("Nodes: ", color=self.COLORS['dim'])
                dpg.add_text("0", tag="graph_node_count", color=self.COLORS['text'])
                dpg.add_text("  Links: ", color=self.COLORS['dim'])
                dpg.add_text("0", tag="graph_link_count", color=self.COLORS['text'])
            
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                # Left: Node editor (70% width)
                with dpg.child_window(width=int(self.width * 0.65), height=-1, border=True):
                    with dpg.node_editor(
                        tag=self.EDITOR_TAG,
                        callback=self._on_link_created,
                        delink_callback=self._on_link_deleted,
                        minimap=True,
                        minimap_location=dpg.mvNodeMiniMap_Location_BottomRight
                    ):
                        pass  # Nodes added dynamically
                
                # Right: Dependency analysis panel (30% width)
                with dpg.child_window(width=-1, height=-1, border=True, tag=self.DEPS_TAG):
                    dpg.add_text("📊 Dependency Analysis", color=self.COLORS['cyan'])
                    dpg.add_separator()
                    dpg.add_text("Select a node, then click", color=self.COLORS['dim'])
                    dpg.add_text("'What depends on this?'", color=self.COLORS['dim'])
        
        # Register handler for node selection (poll-based)
        with dpg.handler_registry():
            dpg.add_mouse_click_handler(callback=self._check_node_selection)
    
    def _subscribe_events(self):
        """Subscribe to relevant events."""
        EventBus.subscribe(Events.FILE_LOADED, self._on_file_loaded)
        EventBus.subscribe(Events.BHAV_SELECTED, self._on_bhav_selected)
        EventBus.subscribe(Events.GRAPH_NODE_SELECTED, self._on_external_node_selected)
    
    def _check_node_selection(self, sender, app_data):
        """Check if a node was selected and publish event (from flow map)."""
        if not dpg.does_item_exist(self.EDITOR_TAG):
            return
        
        selected = dpg.get_selected_nodes(self.EDITOR_TAG)
        if selected and selected[0] != self.selected_node:
            self.selected_node = selected[0]
            node_tag = selected[0]
            
            if node_tag in self.nodes:
                node_data = self.nodes[node_tag]
                # Publish graph node selection event
                EventBus.publish(Events.GRAPH_NODE_SELECTED, {
                    'node_tag': node_tag,
                    'node_type': node_data['type'],
                    'node_id': node_data['id'],
                    'label': node_data['label']
                })
                # Update state
                STATE.set_resource(node_data['id'], node_data['type'])
    
    def _on_external_node_selected(self, data):
        """Handle external node selection (from other panels)."""
        if data and 'node_tag' in data:
            node_tag = data['node_tag']
            if node_tag in self.nodes and dpg.does_item_exist(node_tag):
                dpg.clear_selected_nodes(self.EDITOR_TAG)
                dpg.set_selected_node(self.EDITOR_TAG, node_tag)
    
    def _on_file_loaded(self, filepath):
        """Handle file loaded - build initial graph."""
        self.clear_graph()
        self.dependency_graph = None  # Reset for new file
        
        if STATE.current_iff:
            self._build_iff_graph(STATE.current_iff)
            self._build_dependency_graph()  # Build dependency graph
    
    def _on_bhav_selected(self, bhav_chunk):
        """Handle BHAV selection - highlight node and show dependencies."""
        if bhav_chunk:
            node_id = f"bhav_{bhav_chunk.chunk_id}"
            self._highlight_node(node_id)
    
    def _build_iff_graph(self, iff):
        """Build graph from IFF file structure."""
        if not hasattr(iff, 'chunks'):
            return
        
        # Group chunks by type
        chunks_by_type = {}
        for chunk in iff.chunks:
            ctype = chunk.chunk_type
            if ctype not in chunks_by_type:
                chunks_by_type[ctype] = []
            chunks_by_type[ctype].append(chunk)
        
        # Position nodes in concentric rings by type
        type_order = ['OBJD', 'BHAV', 'TTAB', 'GLOB', 'BCON']
        ring_radius = 150
        center_x, center_y = 300, 200
        
        for ring_idx, chunk_type in enumerate(type_order):
            if chunk_type not in chunks_by_type:
                continue
            
            chunks = chunks_by_type[chunk_type][:20]  # Limit per type
            angle_step = 2 * math.pi / max(len(chunks), 1)
            
            for idx, chunk in enumerate(chunks):
                angle = idx * angle_step
                x = center_x + (ring_radius * (ring_idx + 1) / 2) * math.cos(angle)
                y = center_y + (ring_radius * (ring_idx + 1) / 2) * math.sin(angle)
                
                node_id = self.add_node(
                    chunk_type,
                    chunk.chunk_id,
                    getattr(chunk, 'chunk_label', '') or f"{chunk_type}#{chunk.chunk_id}",
                    int(x), int(y)
                )
                
                # Store chunk reference
                self.nodes[node_id]['chunk'] = chunk
        
        # Add links based on OBJD -> BHAV references
        for chunk_type, chunks in chunks_by_type.items():
            if chunk_type == 'OBJD':
                for objd in chunks:
                    objd_node = f"objd_{objd.chunk_id}"
                    
                    # Link to tree table
                    if hasattr(objd, 'tree_table_id') and objd.tree_table_id:
                        ttab_node = f"ttab_{objd.tree_table_id}"
                        if ttab_node in self.nodes:
                            self.add_link(objd_node, ttab_node)
        
        self._update_counts()
    
    def add_node(self, node_type: str, node_id: int, label: str, x: int = 100, y: int = 100):
        """Add a node to the graph."""
        color_key = self.NODE_COLORS.get(node_type, 'default')
        color = self.COLORS[color_key]
        
        tag = f"{node_type.lower()}_{node_id}"
        
        if tag in self.nodes:
            return tag
        
        with dpg.node(
            tag=tag,
            label=label[:25],
            pos=[x, y],
            parent=self.EDITOR_TAG
        ):
            # Input attribute
            with dpg.node_attribute(
                tag=f"{tag}_in",
                attribute_type=dpg.mvNode_Attr_Input
            ):
                dpg.add_text(f"{node_type}", color=color)
            
            # Static content
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text(f"ID: {node_id}", color=self.COLORS['dim'])
            
            # Output attribute
            with dpg.node_attribute(
                tag=f"{tag}_out",
                attribute_type=dpg.mvNode_Attr_Output
            ):
                dpg.add_text("→", color=self.COLORS['dim'])
        
        self.nodes[tag] = {
            'type': node_type,
            'id': node_id,
            'label': label,
            'x': x,
            'y': y,
        }
        
        self.node_counter += 1
        return tag
    
    def add_link(self, from_node: str, to_node: str):
        """Add a link between two nodes."""
        from_attr = f"{from_node}_out"
        to_attr = f"{to_node}_in"
        
        if not dpg.does_item_exist(from_attr) or not dpg.does_item_exist(to_attr):
            return None
        
        link_tag = f"link_{self.link_counter}"
        
        dpg.add_node_link(
            from_attr, to_attr,
            tag=link_tag,
            parent=self.EDITOR_TAG
        )
        
        self.links.append({
            'tag': link_tag,
            'from': from_node,
            'to': to_node,
        })
        
        self.link_counter += 1
        return link_tag
    
    def clear_graph(self):
        """Clear all nodes and links."""
        for link in self.links:
            if dpg.does_item_exist(link['tag']):
                dpg.delete_item(link['tag'])
        
        for node_tag in list(self.nodes.keys()):
            if dpg.does_item_exist(node_tag):
                dpg.delete_item(node_tag)
        
        self.nodes.clear()
        self.links.clear()
        self.node_counter = 0
        self.link_counter = 0
        self._update_counts()
    
    def _highlight_node(self, node_tag: str):
        """Highlight a specific node."""
        # In DearPyGUI, we can use themes to highlight
        # For now, we'll just select it
        if dpg.does_item_exist(node_tag):
            dpg.set_primary_window(self.TAG, True)
            # Node selection would require custom theming
    
    def _auto_layout(self):
        """Auto-layout nodes in a grid pattern."""
        if not self.nodes:
            return
        
        # Group by type
        by_type = {}
        for tag, data in self.nodes.items():
            t = data['type']
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(tag)
        
        # Layout each group
        y_offset = 50
        x_spacing = 150
        y_spacing = 120
        
        for node_type, tags in by_type.items():
            for idx, tag in enumerate(tags):
                x = 50 + (idx % 4) * x_spacing
                y = y_offset + (idx // 4) * y_spacing
                
                if dpg.does_item_exist(tag):
                    dpg.set_item_pos(tag, [x, y])
            
            y_offset += (len(tags) // 4 + 1) * y_spacing + 30
    
    def _zoom_fit(self):
        """Zoom to fit all nodes."""
        # DearPyGUI node editor doesn't have direct zoom control
        # Auto-layout is a reasonable substitute
        self._auto_layout()
    
    def _update_counts(self):
        """Update node and link count displays."""
        if dpg.does_item_exist("graph_node_count"):
            dpg.set_value("graph_node_count", str(len(self.nodes)))
        if dpg.does_item_exist("graph_link_count"):
            dpg.set_value("graph_link_count", str(len(self.links)))
    
    def _on_link_created(self, sender, app_data):
        """Handle user-created link."""
        self.link_counter += 1
        self._update_counts()
    
    def _on_link_deleted(self, sender, app_data):
        """Handle link deletion."""
        # Remove from our tracking
        link_tag = app_data
        self.links = [l for l in self.links if l['tag'] != link_tag]
        self._update_counts()
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
    
    # Public API matching original web viewer
    def render_graph(self, data: dict):
        """Render graph from structured data (API compatible with web viewer)."""
        self.clear_graph()
        
        nodes = data.get('nodes', [])
        edges = data.get('edges', [])
        
        for node in nodes:
            self.add_node(
                node.get('type', 'default'),
                node.get('id', self.node_counter),
                node.get('label', 'Node'),
                node.get('x', 100),
                node.get('y', 100)
            )
        
        for edge in edges:
            self.add_link(edge.get('from', ''), edge.get('to', ''))
        
        self._update_counts()
    
    def highlight_node_by_id(self, node_id: int, node_type: str = 'bhav'):
        """Highlight node by ID (API compatible with web viewer)."""
        tag = f"{node_type}_{node_id}"
        self._highlight_node(tag)
    
    # ─────────────────────────────────────────────────────────────
    # DEPENDENCY ANALYSIS - "What depends on this?"
    # This is the CRITICAL feature from Conceptual Directives
    # ─────────────────────────────────────────────────────────────
    
    def _build_dependency_graph(self):
        """Build the RelationshipGraph from current IFF."""
        if not _graph_entities_available or not RelationshipGraph:
            return
        
        self.dependency_graph = RelationshipGraph()
        
        if not STATE.current_iff or not hasattr(STATE.current_iff, 'chunks'):
            return
        
        # Scan all BHAV chunks for call relationships
        for chunk in STATE.current_iff.chunks:
            if chunk.chunk_type != 'BHAV':
                continue
            
            bhav_id = chunk.chunk_id
            bhav_name = getattr(chunk, 'chunk_label', '') or f'BHAV #{bhav_id}'
            
            # Get semantic name if available
            if _toolkit_available and _toolkit:
                try:
                    semantic = _toolkit.label_global(bhav_id)
                    if semantic:
                        bhav_name = semantic
                except:
                    pass
            
            # Analyze instructions for calls
            instructions = getattr(chunk, 'instructions', [])
            for instr in instructions:
                opcode = getattr(instr, 'opcode', 0)
                
                # If opcode >= 0x100, it's a call to another BHAV
                if opcode >= 0x100:
                    target_id = opcode
                    target_name = f'BHAV 0x{target_id:04X}'
                    
                    # Get semantic name for target
                    if _toolkit_available and _toolkit:
                        try:
                            target_semantic = _toolkit.label_global(target_id)
                            if target_semantic:
                                target_name = target_semantic
                        except:
                            pass
                    
                    # Add relationship
                    from Tools.entities import Relationship, RelationType
                    self.dependency_graph.add(Relationship(
                        source_type='bhav',
                        source_id=bhav_id,
                        source_name=bhav_name,
                        target_type='bhav',
                        target_id=target_id,
                        target_name=target_name,
                        relation=RelationType.CALLS,
                    ))
    
    def _show_dependents(self):
        """Show what depends on the selected node."""
        self._update_deps_panel(mode='dependents')
    
    def _show_dependencies(self):
        """Show what the selected node depends on."""
        self._update_deps_panel(mode='dependencies')
    
    def _update_deps_panel(self, mode: str = 'dependents'):
        """Update the dependency analysis panel."""
        dpg.delete_item(self.DEPS_TAG, children_only=True)
        
        with dpg.group(parent=self.DEPS_TAG):
            if mode == 'dependents':
                dpg.add_text("🔍 What depends on this?", color=self.COLORS['cyan'])
            else:
                dpg.add_text("🔍 What does this use?", color=self.COLORS['cyan'])
            
            dpg.add_separator()
            
            # Check if node is selected
            if not self.selected_node or self.selected_node not in self.nodes:
                dpg.add_text("Select a node first", color=self.COLORS['dim'])
                return
            
            node_data = self.nodes[self.selected_node]
            node_type = node_data['type'].lower()
            node_id = node_data['id']
            
            dpg.add_text(f"Selected: {node_data['label']}", color=self.COLORS['yellow'])
            dpg.add_separator()
            
            # Build dependency graph if needed
            if not self.dependency_graph:
                self._build_dependency_graph()
            
            if not self.dependency_graph:
                dpg.add_text("(Dependency analysis unavailable)", color=self.COLORS['dim'])
                return
            
            # Get relationships
            if mode == 'dependents':
                rels = self.dependency_graph.what_depends_on(node_type, node_id)
                title = "Dependents:"
            else:
                rels = self.dependency_graph.what_does_this_depend_on(node_type, node_id)
                title = "Dependencies:"
            
            if not rels:
                dpg.add_text("Nothing found", color=self.COLORS['dim'])
                if mode == 'dependents':
                    dpg.add_text("✓ Safe to modify - nothing depends on this", 
                                 color=self.COLORS['green'])
                return
            
            dpg.add_text(title, color=self.COLORS['text'])
            
            # List relationships
            for rel in rels[:15]:  # Limit display
                if mode == 'dependents':
                    text = f"  ← {rel.source_name}"
                    color = self.COLORS['orange']
                else:
                    text = f"  → {rel.target_name}"
                    color = self.COLORS['purple']
                
                dpg.add_text(text, color=color)
                
                # Make clickable to navigate
                dpg.add_button(
                    label=f"Go →",
                    small=True,
                    callback=lambda s, a, r=rel: self._goto_node(r, mode)
                )
            
            if len(rels) > 15:
                dpg.add_text(f"  ... +{len(rels) - 15} more", color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Risk assessment
            if mode == 'dependents':
                count = len(rels)
                if count > 10:
                    dpg.add_text(f"⛔ HIGH RISK: {count} dependents", 
                                 color=(255, 87, 34, 255))
                elif count > 3:
                    dpg.add_text(f"⚠ CAUTION: {count} dependents", 
                                 color=(255, 193, 7, 255))
                else:
                    dpg.add_text(f"✓ Low risk: {count} dependents", 
                                 color=self.COLORS['green'])
    
    def _goto_node(self, rel, mode: str):
        """Navigate to a node from dependency list."""
        if mode == 'dependents':
            target_type = rel.source_type
            target_id = rel.source_id
        else:
            target_type = rel.target_type
            target_id = rel.target_id
        
        tag = f"{target_type}_{target_id}"
        if tag in self.nodes and dpg.does_item_exist(tag):
            dpg.clear_selected_nodes(self.EDITOR_TAG)
            # Note: dpg.set_selected_node doesn't exist, using workaround
            self._highlight_node(tag)
