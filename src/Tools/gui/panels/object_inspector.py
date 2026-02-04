"""
Object Inspector Panel - 3D-style Object View

Displays object preview with rotation, properties panel.
Uses DearPyGUI drawlist for pseudo-3D rendering.

PROGRESSIVE DEPTH (from Conceptual Directives):
- Mode 1: SUMMARY  - Quick overview with preview
- Mode 2: EXPLAIN  - Detailed properties and references
- Mode 3: EDIT     - Full access to modify object
"""

import dearpygui.dearpygui as dpg
import math
from pathlib import Path
import sys
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE

# Import safety API
try:
    from Tools.safety import is_safe_to_edit
    _safety_available = True
except ImportError:
    def is_safe_to_edit(chunk, path): return None
    _safety_available = False

# Import entity abstractions
try:
    from Tools.entities import ObjectEntity
    _entities_available = True
except ImportError:
    ObjectEntity = None
    _entities_available = False


class DepthMode(Enum):
    """Progressive depth modes."""
    SUMMARY = "summary"
    EXPLAIN = "explain"
    EDIT = "edit"


class ObjectInspectorPanel:
    """Object inspector with 3D-style preview and Progressive Depth."""
    
    TAG = "object_inspector"
    CANVAS_TAG = "object_canvas"
    PROPS_TAG = "object_props"
    
    def __init__(self, width: int = 500, height: int = 400, pos: tuple = (300, 30)):
        self.width = width
        self.height = height
        self.pos = pos
        self.rotation = 0.0
        self.current_object = None
        self.current_entity = None  # ObjectEntity
        self.depth_mode = DepthMode.SUMMARY
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the object inspector panel."""
        with dpg.window(
            label="Object Inspector",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            # Progressive Depth mode selector
            with dpg.group(horizontal=True):
                dpg.add_text("Depth:", color=(136, 136, 136, 255))
                dpg.add_button(
                    label="Summary",
                    tag="obj_depth_summary",
                    callback=lambda: self._set_depth(DepthMode.SUMMARY),
                    small=True
                )
                dpg.add_button(
                    label="Explain",
                    tag="obj_depth_explain",
                    callback=lambda: self._set_depth(DepthMode.EXPLAIN),
                    small=True
                )
                dpg.add_button(
                    label="Edit",
                    tag="obj_depth_edit",
                    callback=lambda: self._set_depth(DepthMode.EDIT),
                    small=True
                )
            
            dpg.add_separator()
            
            with dpg.group(horizontal=True):
                # Left: 3D canvas
                with dpg.child_window(width=280, height=-1, border=True):
                    dpg.add_text("3D Preview", color=(0, 212, 255, 255))
                    
                    with dpg.drawlist(
                        tag=self.CANVAS_TAG,
                        width=260,
                        height=280
                    ):
                        # Background
                        dpg.draw_rectangle(
                            (0, 0), (260, 280),
                            fill=(26, 26, 46, 255),
                            color=(74, 74, 106, 255)
                        )
                        # Placeholder object
                        self._draw_placeholder()
                    
                    # Rotation controls
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="◀",
                            width=40,
                            callback=lambda: self._rotate(-15)
                        )
                        dpg.add_slider_float(
                            label="",
                            default_value=0,
                            min_value=0,
                            max_value=360,
                            width=140,
                            callback=self._on_rotation_changed,
                            tag="rotation_slider"
                        )
                        dpg.add_button(
                            label="▶",
                            width=40,
                            callback=lambda: self._rotate(15)
                        )
                
                # Right: Properties
                with dpg.child_window(width=-1, height=-1, border=True, tag=self.PROPS_TAG):
                    dpg.add_text("Properties", color=(0, 212, 255, 255))
                    dpg.add_separator()
                    dpg.add_text("Select an object to inspect", color=(136, 136, 136, 255))
    
    def _set_depth(self, mode: DepthMode):
        """Change the inspection depth mode."""
        self.depth_mode = mode
        if self.current_object:
            self._update_properties(self.current_object)
    
    def _draw_placeholder(self):
        """Draw a placeholder 3D cube."""
        cx, cy = 130, 140
        size = 60
        
        # Isometric cube vertices
        angle = math.radians(self.rotation)
        
        # Front face
        front = [
            (cx - size * math.cos(angle), cy + size * 0.5),
            (cx + size * math.cos(angle), cy + size * 0.5),
            (cx + size * math.cos(angle), cy - size * 0.5),
            (cx - size * math.cos(angle), cy - size * 0.5),
        ]
        
        # Draw faces
        dpg.draw_polygon(
            front,
            fill=(0, 212, 255, 100),
            color=(0, 212, 255, 255),
            parent=self.CANVAS_TAG
        )
        
        # Top face
        top_offset = size * 0.4 * math.sin(angle + 0.5)
        top = [
            front[3],
            front[2],
            (front[2][0] + top_offset, front[2][1] - size * 0.4),
            (front[3][0] + top_offset, front[3][1] - size * 0.4),
        ]
        dpg.draw_polygon(
            top,
            fill=(0, 180, 220, 100),
            color=(0, 212, 255, 255),
            parent=self.CANVAS_TAG
        )
        
        # Label
        dpg.draw_text(
            (cx - 30, cy + size + 20),
            "Object Preview",
            color=(136, 136, 136, 255),
            size=12,
            parent=self.CANVAS_TAG
        )
    
    def _redraw_canvas(self):
        """Redraw the canvas with current rotation."""
        dpg.delete_item(self.CANVAS_TAG, children_only=True)
        
        # Background
        dpg.draw_rectangle(
            (0, 0), (260, 280),
            fill=(26, 26, 46, 255),
            color=(74, 74, 106, 255),
            parent=self.CANVAS_TAG
        )
        
        if self.current_object:
            self._draw_object()
        else:
            self._draw_placeholder_internal()
    
    def _draw_placeholder_internal(self):
        """Draw placeholder cube (internal)."""
        cx, cy = 130, 140
        size = 60
        
        angle = math.radians(self.rotation)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # Cube vertices in 3D
        vertices_3d = [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
        ]
        
        # Rotate and project
        def project(x, y, z):
            # Rotate around Y axis
            rx = x * cos_a - z * sin_a
            rz = x * sin_a + z * cos_a
            # Simple isometric projection
            px = cx + rx * size * 0.7 - rz * size * 0.3
            py = cy - y * size * 0.5 + rz * size * 0.2
            return (px, py)
        
        vertices_2d = [project(v[0], v[1], v[2]) for v in vertices_3d]
        
        # Draw faces (back to front)
        faces = [
            ([4, 5, 6, 7], (0, 150, 200, 100)),  # Back
            ([0, 3, 7, 4], (0, 180, 220, 100)),  # Left
            ([1, 2, 6, 5], (0, 200, 240, 100)),  # Right
            ([3, 2, 6, 7], (0, 212, 255, 100)),  # Top
            ([0, 1, 5, 4], (0, 140, 180, 100)),  # Bottom
            ([0, 1, 2, 3], (0, 212, 255, 150)),  # Front
        ]
        
        for face_indices, color in faces:
            points = [vertices_2d[i] for i in face_indices]
            dpg.draw_polygon(
                points,
                fill=color,
                color=(0, 212, 255, 255),
                parent=self.CANVAS_TAG
            )
        
        # Label
        dpg.draw_text(
            (80, 260),
            f"Rotation: {self.rotation:.0f}°",
            color=(136, 136, 136, 255),
            size=12,
            parent=self.CANVAS_TAG
        )
    
    def _draw_object(self):
        """Draw the current object."""
        # For now, draw placeholder with object info
        self._draw_placeholder_internal()
        
        if self.current_object:
            name = getattr(self.current_object, 'chunk_label', 'Unknown')
            dpg.draw_text(
                (60, 20),
                f"Object: {name}",
                color=(0, 212, 255, 255),
                size=14,
                parent=self.CANVAS_TAG
            )
    
    def _rotate(self, delta):
        """Rotate by delta degrees."""
        self.rotation = (self.rotation + delta) % 360
        dpg.set_value("rotation_slider", self.rotation)
        self._redraw_canvas()
    
    def _on_rotation_changed(self, sender, value):
        """Handle rotation slider change."""
        self.rotation = value
        self._redraw_canvas()
    
    def _subscribe_events(self):
        """Subscribe to chunk selection events."""
        EventBus.subscribe(Events.CHUNK_SELECTED, self._on_chunk_selected)
    
    def _on_chunk_selected(self, chunk):
        """Handle chunk selection."""
        if chunk and chunk.chunk_type == "OBJD":
            self.current_object = chunk
            self._update_properties(chunk)
            self._redraw_canvas()
    
    def _update_properties(self, objd):
        """Update properties panel for OBJD chunk with Progressive Depth."""
        dpg.delete_item(self.PROPS_TAG, children_only=True)
        
        with dpg.group(parent=self.PROPS_TAG):
            # Safety indicator first
            if _safety_available:
                safety = is_safe_to_edit(objd, STATE.current_file_path or "")
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
                self._render_summary_mode(objd)
            elif self.depth_mode == DepthMode.EXPLAIN:
                self._render_explain_mode(objd)
            else:
                self._render_edit_mode(objd)
    
    def _render_summary_mode(self, objd):
        """Quick summary - What is this object?"""
        dpg.add_text("📦 Object Summary", color=(0, 212, 255, 255))
        dpg.add_separator()
        
        # Name
        name = getattr(objd, 'chunk_label', None) or f"Object #{objd.chunk_id}"
        dpg.add_text(f"  {name}", color=(255, 255, 255, 255))
        
        # Type
        if hasattr(objd, 'object_type'):
            type_names = {0: "Unknown", 2: "Person", 4: "Object", 7: "System", 8: "Portal", 34: "Food"}
            type_val = int(objd.object_type) if hasattr(objd.object_type, '__int__') else objd.object_type
            dpg.add_text(f"  Type: {type_names.get(type_val, type_val)}", color=(160, 160, 160, 255))
        
        # Price
        if hasattr(objd, 'price') and objd.price:
            dpg.add_text(f"  Price: §{objd.price}", color=(76, 175, 80, 255))
        
        dpg.add_separator()
        dpg.add_text("💡 Switch to 'Explain' for full details", color=(136, 136, 136, 255))
    
    def _render_explain_mode(self, objd):
        """Detailed explanation - What does it do?"""
        dpg.add_text("📄 OBJD Details", color=(233, 69, 96, 255))
        dpg.add_separator()
        
        if hasattr(objd, 'chunk_id'):
            dpg.add_text(f"  ID: #{objd.chunk_id}", color=(224, 224, 224, 255))
        
        if hasattr(objd, 'chunk_label') and objd.chunk_label:
            dpg.add_text(f"  Name: {objd.chunk_label}", color=(224, 224, 224, 255))
        
        if hasattr(objd, 'guid'):
            dpg.add_text(f"  GUID: 0x{objd.guid:08X}", color=(224, 224, 224, 255))
        
        if hasattr(objd, 'object_type'):
            type_names = {0: "Unknown", 2: "Person", 4: "Object", 7: "System", 8: "Portal", 34: "Food"}
            type_val = int(objd.object_type) if hasattr(objd.object_type, '__int__') else objd.object_type
            dpg.add_text(f"  Type: {type_names.get(type_val, type_val)}", color=(224, 224, 224, 255))
        
        if hasattr(objd, 'price'):
            dpg.add_text(f"  Price: §{objd.price}", color=(76, 175, 80, 255))
        
        dpg.add_separator()
        
        dpg.add_text("🔗 References", color=(233, 69, 96, 255))
        
        if hasattr(objd, 'tree_table_id') and objd.tree_table_id:
            dpg.add_text(f"  TTAB: #{objd.tree_table_id}", color=(150, 200, 255, 255))
        
        if hasattr(objd, 'master_id') and objd.master_id:
            dpg.add_text(f"  Master: #{objd.master_id}", color=(150, 200, 255, 255))
        
        # Show ObjectEntity summary if available
        if _entities_available and ObjectEntity and STATE.current_iff:
            try:
                entities = ObjectEntity.from_iff(STATE.current_iff, STATE.current_iff_name or "")
                for entity in entities:
                    if entity.guid == getattr(objd, 'guid', None):
                        dpg.add_separator()
                        dpg.add_text("📊 System Summary", color=(255, 193, 7, 255))
                        dpg.add_text(f"  Complexity: {entity.get_complexity()}", color=(160, 160, 160, 255))
                        dpg.add_text(f"  Behaviors: {len(entity.behaviors)}", color=(160, 160, 160, 255))
                        dpg.add_text(f"  Interactions: {len(entity.interactions)}", color=(160, 160, 160, 255))
                        break
            except:
                pass
        
        dpg.add_separator()
        dpg.add_text("💡 Switch to 'Edit' for modifications", color=(136, 136, 136, 255))
    
    def _render_edit_mode(self, objd):
        """Full edit mode with safety gates."""
        dpg.add_text("✏️ EDIT MODE", color=(255, 193, 7, 255))
        dpg.add_separator()
        
        # Show explain content first
        self._render_explain_content_only(objd)
        
        dpg.add_separator()
        dpg.add_text("Edit Actions:", color=(255, 193, 7, 255))
        
        dpg.add_button(
            label="Edit Price...",
            callback=lambda: self._edit_price(objd)
        )
        
        dpg.add_button(
            label="Edit Name...",
            callback=lambda: self._edit_name(objd)
        )
        
        if hasattr(objd, 'tree_table_id') and objd.tree_table_id:
            dpg.add_button(
                label="Go to TTAB →",
                callback=lambda: self._goto_ttab(objd)
            )
        
        dpg.add_separator()
        dpg.add_button(
            label="Clone Object...",
            callback=lambda: self._clone_object(objd)
        )
    
    def _render_explain_content_only(self, objd):
        """Render explain content without navigation hints."""
        dpg.add_text("📄 Object Properties", color=(233, 69, 96, 255))
        
        if hasattr(objd, 'chunk_id'):
            dpg.add_text(f"  ID: #{objd.chunk_id}", color=(224, 224, 224, 255))
        
        if hasattr(objd, 'chunk_label') and objd.chunk_label:
            dpg.add_text(f"  Name: {objd.chunk_label}", color=(224, 224, 224, 255))
        
        if hasattr(objd, 'guid'):
            dpg.add_text(f"  GUID: 0x{objd.guid:08X}", color=(224, 224, 224, 255))
        
        if hasattr(objd, 'price'):
            dpg.add_text(f"  Price: §{objd.price}", color=(76, 175, 80, 255))
    
    # Edit action stubs
    def _edit_price(self, objd):
        print(f"TODO: Edit price for OBJD #{objd.chunk_id}")
    
    def _edit_name(self, objd):
        print(f"TODO: Edit name for OBJD #{objd.chunk_id}")
    
    def _goto_ttab(self, objd):
        """Navigate to the TTAB chunk."""
        if STATE.current_iff and hasattr(objd, 'tree_table_id'):
            for chunk in STATE.current_iff.chunks:
                if chunk.chunk_type == "TTAB" and chunk.chunk_id == objd.tree_table_id:
                    EventBus.publish(Events.CHUNK_SELECTED, chunk)
                    break
    
    def _clone_object(self, objd):
        print(f"TODO: Clone object OBJD #{objd.chunk_id}")
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
