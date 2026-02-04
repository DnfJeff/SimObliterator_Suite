"""
BHAV Node Editor Panel.
Visual node graph for BHAV instruction flow.
"""

import dearpygui.dearpygui as dpg

from ..events import EventBus, Events
from ..theme import Colors
from ..opcodes import get_opcode_name, get_node_color, format_pointer


class BHAVEditorPanel:
    """BHAV visual node editor panel."""
    
    TAG = "bhav_editor"
    NODE_EDITOR_TAG = "bhav_node_editor"
    PLACEHOLDER_TAG = "bhav_placeholder"
    
    _instance = None
    
    def __init__(self, width: int = 1020, height: int = 450, pos: tuple = (10, 500)):
        self.width = width
        self.height = height
        self.pos = pos
        BHAVEditorPanel._instance = self
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the panel window."""
        with dpg.window(
            label="BHAV Node Editor",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close,
            no_close=False
        ):
            with dpg.node_editor(
                tag=self.NODE_EDITOR_TAG,
                callback=self._on_link_created,
                delink_callback=self._on_link_deleted,
                minimap=True,
                minimap_location=dpg.mvNodeMiniMap_Location_BottomRight
            ):
                pass
            
            dpg.add_text(
                "Select a BHAV from the IFF panel to visualize",
                tag=self.PLACEHOLDER_TAG,
                color=(136, 136, 136, 255),
                pos=(20, 50)
            )
    
    def _subscribe_events(self):
        """Subscribe to relevant events."""
        EventBus.subscribe(Events.BHAV_SELECTED, self._on_bhav_selected)
    
    def _on_bhav_selected(self, bhav):
        """Handle BHAV selection event."""
        self._render_nodes(bhav)
    
    def _compute_tree_layout(self, instructions):
        """
        Compute tree-based layout positions using depth-first traversal.
        Based on Volcanic's CleanPosition algorithm from BHAVContainer.cs.
        
        Organizes nodes by depth level, with each row centered.
        True branch traversed first (goes down-left), False branch second (goes down-right).
        """
        if not instructions:
            return {}
        
        num_insts = len(instructions)
        
        # Track which nodes we've placed and their depth
        node_depths = {}  # node_index -> depth
        nodes_at_depth = {}  # depth -> [node_indices]
        visited = set()
        
        def recurse_tree(node_idx, depth):
            """Depth-first traversal to assign depths."""
            if node_idx < 0 or node_idx >= num_insts:
                return
            if node_idx in visited:
                return
            
            visited.add(node_idx)
            node_depths[node_idx] = depth
            
            if depth not in nodes_at_depth:
                nodes_at_depth[depth] = []
            nodes_at_depth[depth].append(node_idx)
            
            inst = instructions[node_idx]
            
            # True branch first (left side of tree)
            if inst.true_pointer < num_insts:
                recurse_tree(inst.true_pointer, depth + 1)
            
            # False branch second (right side of tree)
            if inst.false_pointer < num_insts:
                recurse_tree(inst.false_pointer, depth + 1)
        
        # Start traversal from node 0
        recurse_tree(0, 0)
        
        # Handle any unreachable nodes (orphans)
        for i in range(num_insts):
            if i not in visited:
                # Find max depth and add orphans below
                max_depth = max(nodes_at_depth.keys()) + 1 if nodes_at_depth else 0
                node_depths[i] = max_depth
                if max_depth not in nodes_at_depth:
                    nodes_at_depth[max_depth] = []
                nodes_at_depth[max_depth].append(i)
        
        # Layout constants
        NODE_WIDTH = 180
        NODE_HEIGHT = 100
        H_SPACING = 40
        V_SPACING = 45
        START_X = 50
        START_Y = 50
        
        # Calculate positions - center each row
        positions = {}
        
        for depth in sorted(nodes_at_depth.keys()):
            nodes = nodes_at_depth[depth]
            row_width = len(nodes) * NODE_WIDTH + (len(nodes) - 1) * H_SPACING
            
            # Center the row (assuming ~800px working width)
            start_x = START_X + max(0, (800 - row_width) // 2)
            
            for idx, node_idx in enumerate(nodes):
                x = start_x + idx * (NODE_WIDTH + H_SPACING)
                y = START_Y + depth * (NODE_HEIGHT + V_SPACING)
                positions[node_idx] = (x, y)
        
        return positions
    
    def _render_nodes(self, bhav):
        """Render BHAV instructions as nodes using tree layout."""
        # Clear existing nodes
        dpg.delete_item(self.NODE_EDITOR_TAG, children_only=True)
        
        if bhav is None or not hasattr(bhav, 'instructions') or len(bhav.instructions) == 0:
            return
        
        # Update window title
        dpg.configure_item(self.TAG, label=f"BHAV: {bhav.chunk_label} (#{bhav.chunk_id})")
        
        # Hide placeholder
        if dpg.does_item_exist(self.PLACEHOLDER_TAG):
            dpg.delete_item(self.PLACEHOLDER_TAG)
        
        num_insts = len(bhav.instructions)
        
        # Compute tree-based layout
        positions = self._compute_tree_layout(bhav.instructions)
        
        node_tags = []
        
        # Create nodes
        for i, inst in enumerate(bhav.instructions):
            x, y = positions.get(i, (50 + (i % 4) * 220, 50 + (i // 4) * 140))
            
            opcode = inst.opcode
            color = get_node_color(opcode)
            name = get_opcode_name(opcode)
            
            node_tag = f"bhav_node_{i}"
            node_tags.append(node_tag)
            
            with dpg.node(
                label=f"[{i}] {name}",
                tag=node_tag,
                parent=self.NODE_EDITOR_TAG,
                pos=(x, y)
            ):
                # Apply node theme
                self._apply_node_theme(node_tag, color)
                
                # Input attribute
                with dpg.node_attribute(
                    tag=f"in_{i}",
                    attribute_type=dpg.mvNode_Attr_Input
                ):
                    dpg.add_text("In", color=(136, 136, 136, 255))
                
                # Static info attribute
                with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                    op_hex = inst.operand[:4].hex().upper() if hasattr(inst, 'operand') else "----"
                    dpg.add_text(f"Op: {op_hex}...", color=(136, 136, 136, 255))
                
                # True output
                with dpg.node_attribute(
                    tag=f"true_{i}",
                    attribute_type=dpg.mvNode_Attr_Output,
                    shape=dpg.mvNode_PinShape_TriangleFilled
                ):
                    t_label = format_pointer(inst.true_pointer)
                    dpg.add_text(f"T->{t_label}", color=(76, 175, 80, 255))
                
                # False output
                with dpg.node_attribute(
                    tag=f"false_{i}",
                    attribute_type=dpg.mvNode_Attr_Output,
                    shape=dpg.mvNode_PinShape_TriangleFilled
                ):
                    f_label = format_pointer(inst.false_pointer)
                    dpg.add_text(f"F->{f_label}", color=(233, 69, 96, 255))
        
        # Create links
        for i, inst in enumerate(bhav.instructions):
            # True branch link
            if inst.true_pointer < num_insts:
                dpg.add_node_link(
                    f"true_{i}",
                    f"in_{inst.true_pointer}",
                    parent=self.NODE_EDITOR_TAG
                )
            
            # False branch link
            if inst.false_pointer < num_insts:
                dpg.add_node_link(
                    f"false_{i}",
                    f"in_{inst.false_pointer}",
                    parent=self.NODE_EDITOR_TAG
                )
    
    def _apply_node_theme(self, node_tag: str, color: tuple):
        """Apply a color theme to a node."""
        with dpg.theme() as node_theme:
            with dpg.theme_component(dpg.mvNode):
                dpg.add_theme_color(
                    dpg.mvNodeCol_TitleBar,
                    color,
                    category=dpg.mvThemeCat_Nodes
                )
                dpg.add_theme_color(
                    dpg.mvNodeCol_TitleBarHovered,
                    tuple(min(c + 30, 255) for c in color[:3]) + (255,),
                    category=dpg.mvThemeCat_Nodes
                )
                dpg.add_theme_color(
                    dpg.mvNodeCol_TitleBarSelected,
                    tuple(min(c + 50, 255) for c in color[:3]) + (255,),
                    category=dpg.mvThemeCat_Nodes
                )
        dpg.bind_item_theme(node_tag, node_theme)
    
    def _on_link_created(self, sender, app_data):
        """Handle link creation."""
        dpg.add_node_link(app_data[0], app_data[1], parent=sender)
    
    def _on_link_deleted(self, sender, app_data):
        """Handle link deletion."""
        dpg.delete_item(app_data)
    
    def _on_close(self):
        """Handle panel close - hide instead of destroy."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel (used by View menu)."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
