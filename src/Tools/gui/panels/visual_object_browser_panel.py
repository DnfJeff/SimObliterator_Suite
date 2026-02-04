"""
Visual Object Browser - Thumbnail Grid Entry Point

THE #1 CC Creator Entry Point:
- Thumbnail grid (SPR2 preview)
- Click object → open inspector
- "What does this object do?" summary
- Clone button for each object

CC creators think: "I want that chair" not "Objects/Seating/ChairDining.iff"
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE
from ..focus import FOCUS


class VisualObjectBrowserPanel:
    """
    Visual-first object browser for CC creators.
    
    Features:
    - Thumbnail grid with sprites
    - Quick object info on hover
    - One-click to inspector
    - Clone button per object
    - Category/room filters
    """
    
    TAG = "visual_browser"
    GRID_TAG = "visual_grid"
    PREVIEW_TAG = "visual_preview"
    
    COLORS = {
        'cyan': (0, 212, 255),
        'red': (233, 69, 96),
        'green': (76, 175, 80),
        'yellow': (255, 193, 7),
        'text': (224, 224, 224),
        'dim': (136, 136, 136),
        'card_bg': (30, 30, 50),
    }
    
    # Room/Category filters
    CATEGORIES = {
        'all': 'All Objects',
        'seating': 'Seating',
        'surfaces': 'Surfaces',
        'decorative': 'Decorative',
        'electronics': 'Electronics',
        'plumbing': 'Plumbing',
        'lighting': 'Lighting',
        'misc': 'Miscellaneous',
    }
    
    def __init__(self, width: int = 850, height: int = 600, pos: tuple = (50, 50)):
        self.width = width
        self.height = height
        self.pos = pos
        
        self.objects = []
        self.filtered_objects = []
        self.current_category = 'all'
        self.search_query = ""
        self.selected_object = None
        
        self._create_panel()
        self._subscribe_events()
    
    def _create_panel(self):
        """Create the visual browser panel."""
        with dpg.window(
            label="🎨 Visual Object Browser",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            # Header
            with dpg.group(horizontal=True):
                dpg.add_text("Visual Object Browser", color=self.COLORS['cyan'])
                dpg.add_spacer(width=20)
                dpg.add_text("", tag="visual_count", color=self.COLORS['dim'])
            
            dpg.add_text("Browse & clone objects visually • Click to inspect • Double-click to clone",
                        color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Toolbar
            with dpg.group(horizontal=True):
                # Search
                dpg.add_input_text(
                    hint="🔍 Search objects...",
                    width=200,
                    callback=self._on_search,
                    on_enter=True
                )
                
                dpg.add_spacer(width=10)
                
                # Category filter
                dpg.add_combo(
                    items=list(self.CATEGORIES.values()),
                    default_value="All Objects",
                    width=150,
                    callback=self._on_category_change
                )
                
                dpg.add_spacer(width=10)
                
                # View controls
                dpg.add_button(label="📂 Load FAR", callback=self._load_far, width=90)
                dpg.add_button(label="🔄 Refresh", callback=self._refresh, width=70)
            
            dpg.add_separator()
            
            # Main content area
            with dpg.group(horizontal=True):
                # Left: Object grid
                with dpg.child_window(width=550, height=-1, border=True):
                    dpg.add_text("Objects", color=self.COLORS['cyan'])
                    
                    with dpg.child_window(tag=self.GRID_TAG, height=-1, border=False):
                        dpg.add_text("Load a FAR archive to browse objects",
                                    color=self.COLORS['dim'])
                
                # Right: Preview & Info
                with dpg.child_window(width=-1, height=-1, border=True):
                    dpg.add_text("Object Details", color=self.COLORS['cyan'])
                    
                    with dpg.child_window(tag=self.PREVIEW_TAG, height=-1, border=False):
                        self._create_empty_preview()
    
    def _create_empty_preview(self):
        """Create empty preview state."""
        dpg.add_text("Select an object to view details",
                    parent=self.PREVIEW_TAG, color=self.COLORS['dim'])
    
    def _subscribe_events(self):
        """Subscribe to events."""
        EventBus.subscribe(Events.IFF_LOADED, self._on_iff_loaded)
        EventBus.subscribe(Events.FAR_LOADED, self._on_far_loaded)
    
    def _on_iff_loaded(self, iff):
        """Handle IFF loaded - scan for objects."""
        self._scan_objects(iff)
    
    def _on_far_loaded(self, far):
        """Handle FAR loaded - scan all IFFs."""
        if not far:
            return
        
        self.objects = []
        
        # Scan each entry
        for entry in far.entries if hasattr(far, 'entries') else []:
            if entry.filename.lower().endswith('.iff'):
                try:
                    iff = far.read_entry(entry)
                    if iff:
                        objs = self._extract_objects(iff, entry.filename)
                        self.objects.extend(objs)
                except:
                    pass
        
        self._apply_filters()
        self._update_count()
    
    def _scan_objects(self, iff):
        """Scan IFF for objects."""
        if not iff:
            return
        
        objs = self._extract_objects(iff, STATE.current_iff_name or "loaded.iff")
        self.objects = objs
        self._apply_filters()
        self._update_count()
    
    def _extract_objects(self, iff, filename: str) -> list:
        """Extract object data from IFF."""
        objects = []
        
        chunks = iff.chunks if hasattr(iff, 'chunks') else []
        
        # Find OBJD chunks
        for chunk in chunks:
            if getattr(chunk, 'type_code', '') == 'OBJD':
                obj = {
                    'chunk': chunk,
                    'chunk_id': chunk.chunk_id,
                    'name': getattr(chunk, 'name', f'Object #{chunk.chunk_id}'),
                    'guid': getattr(chunk, 'guid', 0),
                    'filename': filename,
                    'iff': iff,
                }
                
                # Try to find associated sprite
                sprite = self._find_sprite(iff, chunk.chunk_id)
                obj['sprite'] = sprite
                
                # Get category hint from filename
                obj['category'] = self._guess_category(filename)
                
                # Get behavior summary
                obj['summary'] = self._get_object_summary(iff, chunk)
                
                objects.append(obj)
        
        return objects
    
    def _find_sprite(self, iff, objd_id: int):
        """Find sprite for object."""
        chunks = iff.chunks if hasattr(iff, 'chunks') else []
        
        for chunk in chunks:
            if getattr(chunk, 'type_code', '') in ['SPR2', 'SPR#']:
                # Return first sprite (simplified)
                return chunk
        
        return None
    
    def _guess_category(self, filename: str) -> str:
        """Guess category from filename."""
        fname = filename.lower()
        
        if 'chair' in fname or 'sofa' in fname or 'couch' in fname:
            return 'seating'
        elif 'table' in fname or 'desk' in fname or 'counter' in fname:
            return 'surfaces'
        elif 'lamp' in fname or 'light' in fname:
            return 'lighting'
        elif 'tv' in fname or 'computer' in fname or 'stereo' in fname:
            return 'electronics'
        elif 'sink' in fname or 'toilet' in fname or 'shower' in fname:
            return 'plumbing'
        elif 'art' in fname or 'sculpture' in fname or 'plant' in fname:
            return 'decorative'
        
        return 'misc'
    
    def _get_object_summary(self, iff, objd) -> dict:
        """Get human-readable object summary (CC gold!)."""
        summary = {
            'interactions': [],
            'autonomous': False,
            'breakable': False,
            'requires': [],
        }
        
        chunks = iff.chunks if hasattr(iff, 'chunks') else []
        
        # Find TTAB for interactions
        for chunk in chunks:
            if getattr(chunk, 'type_code', '') == 'TTAB':
                # TTAB contains interaction menu items
                entries = getattr(chunk, 'entries', [])
                for entry in entries[:5]:
                    name = getattr(entry, 'name', None)
                    if name:
                        summary['interactions'].append(name)
        
        # Check for autonomous flag in OBJD
        flags = getattr(objd, 'flags', 0)
        if flags:
            # Simplified check
            summary['autonomous'] = (flags & 0x0001) != 0
        
        return summary
    
    def _apply_filters(self):
        """Apply category and search filters."""
        filtered = self.objects
        
        # Category filter
        if self.current_category != 'all':
            filtered = [o for o in filtered if o.get('category') == self.current_category]
        
        # Search filter
        if self.search_query:
            q = self.search_query.lower()
            filtered = [o for o in filtered 
                       if q in o.get('name', '').lower() or 
                          q in o.get('filename', '').lower()]
        
        self.filtered_objects = filtered
        self._render_grid()
    
    def _render_grid(self):
        """Render the object grid."""
        dpg.delete_item(self.GRID_TAG, children_only=True)
        
        if not self.filtered_objects:
            dpg.add_text("No objects found", parent=self.GRID_TAG,
                        color=self.COLORS['dim'])
            return
        
        # Create cards in grid
        cols = 3
        row_group = None
        
        for i, obj in enumerate(self.filtered_objects[:50]):  # Limit for performance
            if i % cols == 0:
                row_group = dpg.add_group(horizontal=True, parent=self.GRID_TAG)
            
            self._create_object_card(obj, row_group)
        
        if len(self.filtered_objects) > 50:
            dpg.add_text(f"... and {len(self.filtered_objects) - 50} more",
                        parent=self.GRID_TAG, color=self.COLORS['dim'])
    
    def _create_object_card(self, obj: dict, parent):
        """Create an object card."""
        with dpg.child_window(width=170, height=120, parent=parent, border=True):
            # Object name
            name = obj.get('name', 'Unknown')[:20]
            dpg.add_text(name, color=self.COLORS['text'])
            
            # File source
            fname = Path(obj.get('filename', '')).stem[:15]
            dpg.add_text(fname, color=self.COLORS['dim'])
            
            # Category badge
            cat = obj.get('category', 'misc')
            dpg.add_text(f"[{cat}]", color=self.COLORS['cyan'])
            
            # Buttons
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="View",
                    callback=lambda s, a, o=obj: self._view_object(o),
                    width=50
                )
                dpg.add_button(
                    label="Clone",
                    callback=lambda s, a, o=obj: self._clone_object(o),
                    width=50
                )
    
    def _view_object(self, obj: dict):
        """View object details."""
        self.selected_object = obj
        self._update_preview(obj)
        
        # Publish selection event
        EventBus.publish(Events.CHUNK_SELECTED, obj.get('chunk'))
        
        # Update focus
        FOCUS.select(
            resource_type='OBJD',
            resource_id=obj.get('chunk_id', 0),
            label=obj.get('name', 'Object'),
            source_panel='visual_browser',
            file_path=obj.get('filename')
        )
    
    def _update_preview(self, obj: dict):
        """Update the preview panel with object details."""
        dpg.delete_item(self.PREVIEW_TAG, children_only=True)
        
        # Object name
        dpg.add_text(obj.get('name', 'Unknown'), parent=self.PREVIEW_TAG,
                    color=self.COLORS['red'])
        
        dpg.add_separator(parent=self.PREVIEW_TAG)
        
        # Info rows
        self._add_info_row("GUID", f"0x{obj.get('guid', 0):08X}")
        self._add_info_row("Chunk ID", str(obj.get('chunk_id', 0)))
        self._add_info_row("Source", Path(obj.get('filename', '')).name)
        self._add_info_row("Category", obj.get('category', 'unknown').title())
        
        dpg.add_separator(parent=self.PREVIEW_TAG)
        
        # Summary (CC gold!)
        dpg.add_text("What This Object Does:", parent=self.PREVIEW_TAG,
                    color=self.COLORS['cyan'])
        
        summary = obj.get('summary', {})
        
        # Interactions
        interactions = summary.get('interactions', [])
        if interactions:
            dpg.add_text("Interactions:", parent=self.PREVIEW_TAG, color=self.COLORS['dim'])
            for inter in interactions[:5]:
                dpg.add_text(f"  • {inter}", parent=self.PREVIEW_TAG,
                            color=self.COLORS['text'])
        else:
            dpg.add_text("  No interactions found", parent=self.PREVIEW_TAG,
                        color=self.COLORS['dim'])
        
        # Flags
        dpg.add_spacer(height=5, parent=self.PREVIEW_TAG)
        auto = "Yes" if summary.get('autonomous') else "No"
        dpg.add_text(f"Autonomous: {auto}", parent=self.PREVIEW_TAG,
                    color=self.COLORS['text'])
        
        dpg.add_separator(parent=self.PREVIEW_TAG)
        
        # Action buttons
        with dpg.group(horizontal=True, parent=self.PREVIEW_TAG):
            dpg.add_button(
                label="📋 Clone This",
                callback=lambda: self._clone_object(obj),
                width=100
            )
            dpg.add_button(
                label="🔍 Inspect",
                callback=lambda: self._deep_inspect(obj),
                width=80
            )
        
        # Export button row
        with dpg.group(horizontal=True, parent=self.PREVIEW_TAG):
            dpg.add_button(
                label="🎨 Export Sprites",
                callback=lambda: self._export_sprites(obj),
                width=120
            )
    
    def _add_info_row(self, label: str, value: str):
        """Add info row to preview."""
        with dpg.group(horizontal=True, parent=self.PREVIEW_TAG):
            dpg.add_text(f"{label}:", color=self.COLORS['dim'])
            dpg.add_text(value, color=self.COLORS['text'])
    
    def _clone_object(self, obj: dict):
        """Clone object (the #1 CC action!)."""
        # For now, publish event - full implementation needs GUID generation
        EventBus.publish('object.clone_requested', obj)
        
        self._log_action(f"Clone requested: {obj.get('name', 'Object')}")
        
        # Show feedback
        dpg.add_text("✓ Clone request sent - GUID generator coming soon!",
                    parent=self.PREVIEW_TAG, color=self.COLORS['green'])
    
    def _deep_inspect(self, obj: dict):
        """Open full inspector for object."""
        chunk = obj.get('chunk')
        if chunk:
            EventBus.publish(Events.CHUNK_SELECTED, chunk)
    
    def _export_sprites(self, obj: dict):
        """Export sprites for selected object."""
        # Set focus to object so sprite export panel can find it
        FOCUS.select(
            resource_type='OBJD',
            resource_id=obj.get('chunk_id', 0),
            label=obj.get('name', 'Object'),
            source_panel='visual_browser',
            file_path=obj.get('filename')
        )
        
        # Publish event to open sprite export panel with this object
        EventBus.publish('sprite.export_requested', obj)
        
        self._log_action(f"Export sprites requested: {obj.get('name', 'Object')}")
    
    def _log_action(self, message: str):
        """Log action to state."""
        STATE.log(message, "INFO")
    
    def _on_search(self, sender, value):
        """Handle search input."""
        self.search_query = value
        self._apply_filters()
    
    def _on_category_change(self, sender, value):
        """Handle category change."""
        # Reverse lookup
        for key, name in self.CATEGORIES.items():
            if name == value:
                self.current_category = key
                break
        self._apply_filters()
    
    def _update_count(self):
        """Update object count display."""
        total = len(self.objects)
        filtered = len(self.filtered_objects)
        dpg.set_value("visual_count", f"Showing {filtered} of {total} objects")
    
    def _load_far(self):
        """Open FAR file dialog."""
        EventBus.publish('far.browse_requested')
    
    def _refresh(self):
        """Refresh from current state."""
        if STATE.current_iff:
            self._scan_objects(STATE.current_iff)
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
