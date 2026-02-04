"""
Character Viewer Panel - Sim/Character Details & 3D Preview

Ports the beautiful character_viewer.html design to DearPyGUI.
Features: character info, mesh list, appearance customization, 3D preview.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys
import math

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE


class CharacterViewerPanel:
    """Character viewer - view Sim details, meshes, and 3D preview."""
    
    TAG = "character_viewer"
    CANVAS_TAG = "character_canvas"
    MESH_LIST_TAG = "character_mesh_list"
    INFO_TAG = "character_info"
    
    # Color palette from character_viewer.html
    COLORS = {
        'red': (233, 69, 96),
        'blue': (148, 179, 253),
        'cyan': (0, 212, 255),
        'green': (76, 175, 80),
        'yellow': (255, 213, 79),
        'text': (238, 238, 238),
        'dim': (102, 102, 102),
        'panel_bg': (15, 52, 96),
        'dark_bg': (26, 26, 46),
    }
    
    def __init__(self, width: int = 700, height: int = 550, pos: tuple = (100, 50)):
        self.width = width
        self.height = height
        self.pos = pos
        self.current_character = None
        self.rotation = 0.0
        self.selected_meshes = set()
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the character viewer panel."""
        with dpg.window(
            label="🎮 Character Viewer",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            with dpg.group(horizontal=True):
                # Left sidebar - controls
                with dpg.child_window(width=280, height=-1, border=True):
                    dpg.add_text("SimObliterator", color=self.COLORS['red'])
                    dpg.add_text("Character Viewer", color=self.COLORS['dim'])
                    
                    dpg.add_separator()
                    
                    # Character info panel
                    with dpg.collapsing_header(label="📋 Character Info", default_open=True):
                        with dpg.group(tag=self.INFO_TAG):
                            self._create_info_row("Name:", "-", "info_name")
                            self._create_info_row("GUID:", "-", "info_guid")
                            self._create_info_row("Age:", "-", "info_age")
                            self._create_info_row("Gender:", "-", "info_gender")
                            self._create_info_row("Skin:", "-", "info_skin")
                    
                    dpg.add_separator()
                    
                    # Appearance panel
                    with dpg.collapsing_header(label="👤 Appearance", default_open=True):
                        dpg.add_text("Head:", color=self.COLORS['blue'])
                        dpg.add_combo(
                            items=["Default"],
                            default_value="Default",
                            width=240,
                            tag="head_combo"
                        )
                        
                        dpg.add_text("Body:", color=self.COLORS['blue'])
                        dpg.add_combo(
                            items=["Default"],
                            default_value="Default",
                            width=240,
                            tag="body_combo"
                        )
                        
                        dpg.add_text("Hands:", color=self.COLORS['blue'])
                        dpg.add_combo(
                            items=["Default"],
                            default_value="Default",
                            width=240,
                            tag="hands_combo"
                        )
                    
                    dpg.add_separator()
                    
                    # Mesh list panel
                    with dpg.collapsing_header(label="📦 Meshes", default_open=False):
                        with dpg.child_window(
                            height=150,
                            border=True,
                            tag=self.MESH_LIST_TAG
                        ):
                            dpg.add_text("No meshes loaded", color=self.COLORS['dim'])
                    
                    dpg.add_separator()
                    
                    # Export buttons
                    dpg.add_text("Actions", color=self.COLORS['blue'])
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="Export GLTF",
                            callback=self._export_gltf,
                            width=125
                        )
                        dpg.add_button(
                            label="Export PNG",
                            callback=self._export_png,
                            width=125
                        )
                
                # Right - 3D viewer
                with dpg.child_window(width=-1, height=-1, border=True):
                    # Canvas for 3D preview
                    with dpg.drawlist(
                        tag=self.CANVAS_TAG,
                        width=380,
                        height=400
                    ):
                        self._draw_preview()
                    
                    # Rotation controls
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="◀ Rotate",
                            callback=lambda: self._rotate(-15),
                            width=80
                        )
                        dpg.add_slider_float(
                            label="",
                            default_value=0,
                            min_value=0,
                            max_value=360,
                            width=180,
                            callback=self._on_rotation_changed,
                            tag="char_rotation_slider"
                        )
                        dpg.add_button(
                            label="Rotate ▶",
                            callback=lambda: self._rotate(15),
                            width=80
                        )
                    
                    dpg.add_spacer(height=5)
                    
                    # Stats
                    with dpg.group(horizontal=True):
                        dpg.add_text("Vertices:", color=self.COLORS['dim'])
                        dpg.add_text("0", tag="stat_vertices", color=self.COLORS['text'])
                        dpg.add_spacer(width=20)
                        dpg.add_text("Faces:", color=self.COLORS['dim'])
                        dpg.add_text("0", tag="stat_faces", color=self.COLORS['text'])
                        dpg.add_spacer(width=20)
                        dpg.add_text("Bones:", color=self.COLORS['dim'])
                        dpg.add_text("0", tag="stat_bones", color=self.COLORS['text'])
                    
                    # Controls help
                    dpg.add_text(
                        "Drag to rotate • Scroll to zoom",
                        color=self.COLORS['dim']
                    )
    
    def _create_info_row(self, label: str, value: str, tag: str):
        """Create an info row like the HTML version."""
        with dpg.group(horizontal=True):
            dpg.add_text(label, color=self.COLORS['blue'])
            dpg.add_text(value, tag=tag, color=self.COLORS['text'])
    
    def _draw_preview(self):
        """Draw the 3D preview placeholder/character."""
        # Background
        dpg.draw_rectangle(
            (0, 0), (380, 400),
            fill=(13, 13, 26, 255),
            color=(15, 52, 96, 255),
            parent=self.CANVAS_TAG
        )
        
        # Draw a simple humanoid figure
        self._draw_character_silhouette()
    
    def _draw_character_silhouette(self):
        """Draw a character silhouette that rotates."""
        cx, cy = 190, 200
        
        angle = math.radians(self.rotation)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # Simple humanoid silhouette
        # Head
        head_radius = 25
        head_x = cx + sin_a * 5
        dpg.draw_circle(
            (head_x, cy - 80),
            head_radius,
            fill=(148, 179, 253, 150),
            color=(148, 179, 253, 255),
            parent=self.CANVAS_TAG
        )
        
        # Torso (rotated rectangle approximation)
        torso_width = 50 * abs(cos_a) + 20 * abs(sin_a)
        dpg.draw_rectangle(
            (cx - torso_width/2, cy - 50),
            (cx + torso_width/2, cy + 30),
            fill=(148, 179, 253, 100),
            color=(148, 179, 253, 255),
            parent=self.CANVAS_TAG
        )
        
        # Arms
        arm_offset = 30 * sin_a
        # Left arm
        dpg.draw_line(
            (cx - 25 + arm_offset, cy - 40),
            (cx - 50 + arm_offset, cy + 20),
            color=(148, 179, 253, 255),
            thickness=8,
            parent=self.CANVAS_TAG
        )
        # Right arm
        dpg.draw_line(
            (cx + 25 - arm_offset, cy - 40),
            (cx + 50 - arm_offset, cy + 20),
            color=(148, 179, 253, 255),
            thickness=8,
            parent=self.CANVAS_TAG
        )
        
        # Legs
        # Left leg
        dpg.draw_line(
            (cx - 15, cy + 30),
            (cx - 25 + sin_a * 10, cy + 100),
            color=(148, 179, 253, 255),
            thickness=10,
            parent=self.CANVAS_TAG
        )
        # Right leg
        dpg.draw_line(
            (cx + 15, cy + 30),
            (cx + 25 - sin_a * 10, cy + 100),
            color=(148, 179, 253, 255),
            thickness=10,
            parent=self.CANVAS_TAG
        )
        
        # Character name label
        if self.current_character:
            name = self.current_character.get('name', 'Character')
            dpg.draw_text(
                (cx - 50, cy + 130),
                name,
                color=(148, 179, 253, 255),
                size=14,
                parent=self.CANVAS_TAG
            )
        else:
            dpg.draw_text(
                (cx - 60, cy + 130),
                "Select a character",
                color=(102, 102, 102, 255),
                size=12,
                parent=self.CANVAS_TAG
            )
    
    def _redraw_canvas(self):
        """Redraw the canvas with current rotation."""
        dpg.delete_item(self.CANVAS_TAG, children_only=True)
        self._draw_preview()
    
    def _rotate(self, delta: float):
        """Rotate by delta degrees."""
        self.rotation = (self.rotation + delta) % 360
        if dpg.does_item_exist("char_rotation_slider"):
            dpg.set_value("char_rotation_slider", self.rotation)
        self._redraw_canvas()
    
    def _on_rotation_changed(self, sender, value):
        """Handle rotation slider change."""
        self.rotation = value
        self._redraw_canvas()
    
    def _subscribe_events(self):
        """Subscribe to character selection events."""
        EventBus.subscribe(Events.CHARACTER_SELECTED, self._on_character_selected)
    
    def _on_character_selected(self, character: dict):
        """Handle character selection."""
        self.current_character = character
        self._update_info(character)
        self._update_meshes(character)
        self._redraw_canvas()
    
    def _update_info(self, character: dict):
        """Update character info display."""
        if dpg.does_item_exist("info_name"):
            dpg.set_value("info_name", character.get('name', '-'))
        if dpg.does_item_exist("info_guid"):
            guid = character.get('guid', 0)
            dpg.set_value("info_guid", f"0x{guid:08X}" if guid else "-")
        if dpg.does_item_exist("info_age"):
            age = character.get('age', 'Adult')
            dpg.set_value("info_age", str(age))
        if dpg.does_item_exist("info_gender"):
            gender = character.get('gender', 'Unknown')
            dpg.set_value("info_gender", str(gender))
        if dpg.does_item_exist("info_skin"):
            skin = character.get('skin', 'Light')
            dpg.set_value("info_skin", str(skin))
    
    def _update_meshes(self, character: dict):
        """Update mesh list."""
        dpg.delete_item(self.MESH_LIST_TAG, children_only=True)
        
        meshes = character.get('meshes', [])
        if not meshes:
            dpg.add_text("No meshes", color=self.COLORS['dim'], 
                        parent=self.MESH_LIST_TAG)
            return
        
        for mesh in meshes:
            mesh_name = mesh if isinstance(mesh, str) else mesh.get('name', 'Unknown')
            with dpg.group(horizontal=True, parent=self.MESH_LIST_TAG):
                dpg.add_checkbox(
                    default_value=True,
                    callback=lambda s, a, u: self._toggle_mesh(u),
                    user_data=mesh_name
                )
                dpg.add_text(mesh_name[:30], color=self.COLORS['text'])
    
    def _toggle_mesh(self, mesh_name: str):
        """Toggle mesh visibility."""
        if mesh_name in self.selected_meshes:
            self.selected_meshes.remove(mesh_name)
        else:
            self.selected_meshes.add(mesh_name)
        self._redraw_canvas()
    
    def _export_gltf(self):
        """Export character as GLTF."""
        if not self.current_character:
            return
        # TODO: Implement GLTF export
        print(f"Export GLTF: {self.current_character.get('name', 'character')}")
    
    def _export_png(self):
        """Export preview as PNG."""
        if not self.current_character:
            return
        # TODO: Implement PNG export
        print(f"Export PNG: {self.current_character.get('name', 'character')}")
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
