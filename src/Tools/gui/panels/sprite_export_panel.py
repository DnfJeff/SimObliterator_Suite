"""
Sprite Export Panel

Export sprites from selected objects to:
- Individual PNGs (ZIP archive)
- Sprite Sheet (single image with all frames)
- With metadata JSON

Integrates with VisualObjectBrowser for CC creator workflow.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import threading
import zipfile
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..events import EventBus, Events
from ..state import STATE

# Import sprite decoder
try:
    from formats.iff.chunks.sprite_export import SPR2Decoder, DecodedSprite
    DECODER_AVAILABLE = True
except ImportError:
    SPR2Decoder = None
    DECODER_AVAILABLE = False

# Import PIL for image export
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    PIL_AVAILABLE = False


class ExportMode(Enum):
    """Sprite export modes."""
    INDIVIDUAL_ZIP = "zip"
    SPRITE_SHEET = "sheet"
    BOTH = "both"


@dataclass
class SpriteExportResult:
    """Result of sprite export operation."""
    success: bool = True
    sprites_exported: int = 0
    output_path: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class SpriteExportPanel:
    """Panel for exporting sprites from selected objects."""
    
    TAG = "sprite_export_panel"
    
    def __init__(self, width: int = 400, height: int = 350, pos: tuple = (200, 100)):
        self.width = width
        self.height = height
        self.pos = pos
        self.current_object = None
        self.export_mode = ExportMode.INDIVIDUAL_ZIP
        self._worker = None
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the export panel."""
        with dpg.window(
            label="Sprite Export",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            show=False,
            on_close=self._on_close
        ):
            # Status bar
            dpg.add_text("🎨 Sprite Export", color=(0, 212, 255, 255))
            
            # Capability check
            if not DECODER_AVAILABLE:
                dpg.add_text("⚠️ SPR2Decoder not available", color=(255, 193, 7, 255))
            if not PIL_AVAILABLE:
                dpg.add_text("⚠️ PIL not available (sheets disabled)", color=(255, 193, 7, 255))
            
            dpg.add_separator()
            
            # Selected object info
            dpg.add_text("Selected Object:", color=(136, 136, 136, 255))
            dpg.add_text("(none)", tag="export_selected_name", color=(224, 224, 224, 255))
            dpg.add_text("Sprites: 0", tag="export_sprite_count", color=(160, 160, 160, 255))
            
            dpg.add_separator()
            
            # Export mode
            dpg.add_text("Export Mode:", color=(136, 136, 136, 255))
            dpg.add_radio_button(
                items=["Individual PNGs (ZIP)", "Sprite Sheet", "Both"],
                default_value="Individual PNGs (ZIP)",
                tag="export_mode_radio",
                callback=self._on_mode_changed
            )
            
            dpg.add_separator()
            
            # Options
            dpg.add_text("Options:", color=(136, 136, 136, 255))
            dpg.add_checkbox(
                label="Include metadata JSON",
                default_value=True,
                tag="export_include_metadata"
            )
            dpg.add_checkbox(
                label="Include Z-buffer",
                default_value=False,
                tag="export_include_zbuffer"
            )
            dpg.add_checkbox(
                label="All rotations (4 directions)",
                default_value=True,
                tag="export_all_rotations"
            )
            dpg.add_checkbox(
                label="All zoom levels",
                default_value=True,
                tag="export_all_zooms"
            )
            
            dpg.add_separator()
            
            # Output path
            dpg.add_text("Output:", color=(136, 136, 136, 255))
            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    default_value="",
                    tag="export_output_path",
                    width=280,
                    hint="Select output folder..."
                )
                dpg.add_button(
                    label="Browse",
                    callback=self._browse_output
                )
            
            dpg.add_separator()
            
            # Export button
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Export",
                    tag="export_btn",
                    width=120,
                    callback=self._do_export
                )
                dpg.add_button(
                    label="Cancel",
                    width=80,
                    callback=self._on_close
                )
            
            # Progress
            dpg.add_progress_bar(
                tag="export_progress",
                default_value=0,
                overlay="Ready"
            )
            
            # Log
            dpg.add_text("", tag="export_log", color=(136, 136, 136, 255), wrap=380)
    
    def _subscribe_events(self):
        """Subscribe to events."""
        EventBus.subscribe(Events.CHUNK_SELECTED, self._on_chunk_selected)
        EventBus.subscribe('sprite.export_requested', self._on_export_requested)
    
    def _on_export_requested(self, obj: dict):
        """Handle export request from visual browser."""
        # Show the panel
        dpg.configure_item(self.TAG, show=True)
        dpg.focus_item(self.TAG)
        
        # Set the object
        chunk = obj.get('chunk')
        if chunk:
            self._on_chunk_selected(chunk)
            name = obj.get('name', f"Object #{chunk.chunk_id}")
            dpg.set_value("export_selected_name", name)
    
    def _on_chunk_selected(self, chunk):
        """Handle chunk selection."""
        if chunk and chunk.chunk_type == "OBJD":
            self.current_object = chunk
            name = getattr(chunk, 'chunk_label', '') or f"Object #{chunk.chunk_id}"
            dpg.set_value("export_selected_name", name)
            
            # Count sprites
            sprite_count = self._count_sprites()
            dpg.set_value("export_sprite_count", f"Sprites: {sprite_count}")
    
    def _count_sprites(self) -> int:
        """Count sprites associated with current object."""
        if not STATE.current_iff:
            return 0
        
        count = 0
        for chunk in STATE.current_iff.chunks:
            if chunk.chunk_type in ("SPR#", "SPR2"):
                count += 1
        return count
    
    def _on_mode_changed(self, sender, value):
        """Handle export mode change."""
        if value == "Individual PNGs (ZIP)":
            self.export_mode = ExportMode.INDIVIDUAL_ZIP
        elif value == "Sprite Sheet":
            self.export_mode = ExportMode.SPRITE_SHEET
        else:
            self.export_mode = ExportMode.BOTH
    
    def _browse_output(self):
        """Open folder browser for output path."""
        # DearPyGUI doesn't have folder picker, use file dialog workaround
        def callback(sender, app_data):
            if app_data and 'file_path_name' in app_data:
                folder = str(Path(app_data['file_path_name']).parent)
                dpg.set_value("export_output_path", folder)
        
        with dpg.file_dialog(
            callback=callback,
            width=500,
            height=400,
            modal=True
        ):
            dpg.add_file_extension("*.*")
    
    def _do_export(self):
        """Execute sprite export."""
        if not self.current_object:
            dpg.set_value("export_log", "⚠️ Select an object first")
            return
        
        if not DECODER_AVAILABLE:
            dpg.set_value("export_log", "⚠️ SPR2Decoder not available")
            return
        
        output_path = dpg.get_value("export_output_path")
        if not output_path:
            dpg.set_value("export_log", "⚠️ Select output folder")
            return
        
        # Start export in background
        dpg.set_value("export_progress", 0.1)
        dpg.configure_item("export_progress", overlay="Exporting...")
        dpg.configure_item("export_btn", enabled=False)
        
        self._worker = threading.Thread(target=self._export_worker, args=(output_path,))
        self._worker.start()
    
    def _export_worker(self, output_path: str):
        """Background export worker."""
        try:
            result = self._export_sprites(output_path)
            
            # Update UI from main thread
            dpg.set_value("export_progress", 1.0)
            if result.success:
                dpg.configure_item("export_progress", overlay="Complete!")
                dpg.set_value("export_log", 
                    f"✓ Exported {result.sprites_exported} sprites to {result.output_path}")
            else:
                dpg.configure_item("export_progress", overlay="Failed")
                dpg.set_value("export_log", f"⚠️ Errors: {', '.join(result.errors)}")
        except Exception as e:
            dpg.set_value("export_progress", 0)
            dpg.configure_item("export_progress", overlay="Error")
            dpg.set_value("export_log", f"⛔ Error: {e}")
        finally:
            dpg.configure_item("export_btn", enabled=True)
    
    def _export_sprites(self, output_path: str) -> SpriteExportResult:
        """Export sprites to output path."""
        result = SpriteExportResult()
        
        if not STATE.current_iff:
            result.success = False
            result.errors.append("No IFF loaded")
            return result
        
        # Get sprite chunks
        spr2_chunks = [c for c in STATE.current_iff.chunks if c.chunk_type == "SPR2"]
        palt_chunks = [c for c in STATE.current_iff.chunks if c.chunk_type == "PALT"]
        
        if not spr2_chunks:
            result.success = False
            result.errors.append("No SPR2 chunks found")
            return result
        
        # Get palette (use first available)
        palette = palt_chunks[0] if palt_chunks else None
        
        # Create decoder
        decoder = SPR2Decoder(palette=palette)
        
        # Determine output filename
        obj_name = getattr(self.current_object, 'chunk_label', '') or 'object'
        obj_name = obj_name.replace(' ', '_').replace('/', '_')
        
        if self.export_mode == ExportMode.INDIVIDUAL_ZIP or self.export_mode == ExportMode.BOTH:
            zip_path = Path(output_path) / f"{obj_name}_sprites.zip"
            result.output_path = str(zip_path)
            
            with zipfile.ZipFile(zip_path, 'w') as zf:
                metadata = {"sprites": []}
                
                for spr2 in spr2_chunks:
                    frames = getattr(spr2, 'frames', [])
                    for frame_idx, frame in enumerate(frames):
                        decoded = decoder.decode_frame(frame, palette)
                        if decoded and PIL_AVAILABLE:
                            # Create PIL image
                            img = Image.frombytes('RGBA', (decoded.width, decoded.height), 
                                                 bytes(decoded.rgba_data))
                            
                            # Save to ZIP
                            filename = f"{spr2.chunk_id}_{frame_idx}.png"
                            import io
                            buf = io.BytesIO()
                            img.save(buf, 'PNG')
                            zf.writestr(filename, buf.getvalue())
                            
                            result.sprites_exported += 1
                            
                            # Add to metadata
                            metadata["sprites"].append({
                                "filename": filename,
                                "width": decoded.width,
                                "height": decoded.height,
                                "offset_x": decoded.position_x,
                                "offset_y": decoded.position_y,
                            })
                
                # Add metadata if requested
                if dpg.get_value("export_include_metadata"):
                    zf.writestr("metadata.json", json.dumps(metadata, indent=2))
        
        if self.export_mode == ExportMode.SPRITE_SHEET or self.export_mode == ExportMode.BOTH:
            if not PIL_AVAILABLE:
                result.errors.append("Sprite sheet requires PIL")
            else:
                # Create sprite sheet (grid of all frames)
                # Collect all decoded sprites first
                sprites = []
                for spr2 in spr2_chunks:
                    frames = getattr(spr2, 'frames', [])
                    for frame in frames:
                        decoded = decoder.decode_frame(frame, palette)
                        if decoded:
                            sprites.append(decoded)
                
                if sprites:
                    # Calculate grid size
                    cols = min(8, len(sprites))
                    rows = (len(sprites) + cols - 1) // cols
                    
                    max_w = max(s.width for s in sprites)
                    max_h = max(s.height for s in sprites)
                    
                    # Create sheet
                    sheet = Image.new('RGBA', (cols * max_w, rows * max_h), (0, 0, 0, 0))
                    
                    for idx, sprite in enumerate(sprites):
                        img = Image.frombytes('RGBA', (sprite.width, sprite.height),
                                            bytes(sprite.rgba_data))
                        x = (idx % cols) * max_w
                        y = (idx // cols) * max_h
                        sheet.paste(img, (x, y))
                    
                    sheet_path = Path(output_path) / f"{obj_name}_sheet.png"
                    sheet.save(sheet_path)
                    
                    if not result.output_path:
                        result.output_path = str(sheet_path)
        
        return result
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)


# Convenience function
def get_sprite_export_panel() -> Optional[SpriteExportPanel]:
    """Get the sprite export panel instance."""
    if dpg.does_item_exist(SpriteExportPanel.TAG):
        return SpriteExportPanel._instance
    return None
