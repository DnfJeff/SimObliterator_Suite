"""
Library Browser Panel - Asset Library with Card Grid

Ports the beautiful library_browser.html design to DearPyGUI.
Features: search, category filtering, card-based grid, asset previews.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE


class LibraryBrowserPanel:
    """Library browser - browse objects, characters, meshes from game files."""
    
    TAG = "library_browser"
    GRID_TAG = "library_grid"
    SEARCH_TAG = "library_search"
    STATS_TAG = "library_stats"
    
    # Color palette from library_browser.html
    COLORS = {
        'cyan': (0, 212, 255),
        'red': (233, 69, 96),
        'green': (76, 175, 80),
        'orange': (255, 152, 0),
        'blue': (33, 150, 243),
        'purple': (156, 39, 176),
        'text': (224, 224, 224),
        'dim': (136, 136, 136),
        'bg': (26, 26, 46),
        'card_bg': (0, 0, 0, 80),
        'card_border': (74, 74, 106),
    }
    
    # Category definitions
    CATEGORIES = {
        'all': ('All Items', 0),
        'objects': ('Objects', 0),
        'characters': ('Characters', 0),
        'meshes': ('Meshes', 0),
        'heads': ('Heads', 0),
        'bodies': ('Bodies', 0),
        'hands': ('Hands', 0),
    }
    
    def __init__(self, width: int = 800, height: int = 600, pos: tuple = (50, 30)):
        self.width = width
        self.height = height
        self.pos = pos
        self.current_category = 'all'
        self.items = []
        self.filtered_items = []
        self._create_panel()
        self._subscribe_events()
    
    def _subscribe_events(self):
        """Subscribe to file load events (from flow map)."""
        EventBus.subscribe(Events.FILE_LOADED, self._on_file_loaded)
    
    def _on_file_loaded(self, data):
        """Handle file loaded - refresh if relevant."""
        # Reload game data when new files are loaded
        self._load_game_data()
    
    def _create_panel(self):
        """Create the library browser panel."""
        with dpg.window(
            label="📚 Asset Library",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            # Header with stats
            with dpg.group(horizontal=True):
                dpg.add_text("SimObliterator Asset Library", color=self.COLORS['cyan'])
                dpg.add_spacer(width=50)
                
                # Stats badges
                with dpg.group(horizontal=True):
                    self._create_stat_badge("Objects", "0", "stat_objects")
                    self._create_stat_badge("Characters", "0", "stat_characters")
                    self._create_stat_badge("Meshes", "0", "stat_meshes")
            
            dpg.add_separator()
            
            # Main container: sidebar + content
            with dpg.group(horizontal=True):
                # Sidebar - categories
                with dpg.child_window(width=180, height=-1, border=True):
                    dpg.add_text("CATEGORIES", color=self.COLORS['cyan'])
                    dpg.add_separator()
                    
                    for cat_id, (cat_name, count) in self.CATEGORIES.items():
                        with dpg.group(horizontal=True):
                            dpg.add_button(
                                label=cat_name,
                                callback=lambda s, a, u: self._select_category(u),
                                user_data=cat_id,
                                width=120,
                                tag=f"cat_btn_{cat_id}"
                            )
                            dpg.add_text(f"({count})", tag=f"cat_count_{cat_id}",
                                        color=self.COLORS['dim'])
                    
                    dpg.add_separator()
                    dpg.add_spacer(height=10)
                    
                    # Quick filters
                    dpg.add_text("QUICK FILTERS", color=self.COLORS['cyan'])
                    dpg.add_checkbox(label="Adults only", tag="filter_adults")
                    dpg.add_checkbox(label="Children only", tag="filter_children")
                    dpg.add_checkbox(label="Males only", tag="filter_males")
                    dpg.add_checkbox(label="Females only", tag="filter_females")
                    
                    dpg.add_separator()
                    dpg.add_spacer(height=10)
                    
                    # Actions
                    dpg.add_text("ACTIONS", color=self.COLORS['cyan'])
                    dpg.add_button(
                        label="Load Game Data",
                        callback=self._load_game_data,
                        width=160
                    )
                    dpg.add_button(
                        label="Refresh",
                        callback=self._refresh,
                        width=160
                    )
                
                # Main content area
                with dpg.child_window(width=-1, height=-1, border=True):
                    # Search bar
                    with dpg.group(horizontal=True):
                        dpg.add_input_text(
                            hint="Search by name, GUID, or type...",
                            width=400,
                            callback=self._on_search,
                            tag=self.SEARCH_TAG
                        )
                        dpg.add_button(
                            label="🔍 Search",
                            callback=self._do_search,
                            width=80
                        )
                        dpg.add_spacer(width=20)
                        
                        # View toggle
                        dpg.add_button(label="▦ Grid", width=60, tag="view_grid_btn")
                        dpg.add_button(label="☰ List", width=60, tag="view_list_btn")
                    
                    dpg.add_separator()
                    
                    # Results info
                    dpg.add_text("Showing 0 items", tag="results_info", 
                                color=self.COLORS['dim'])
                    
                    dpg.add_spacer(height=5)
                    
                    # Grid container
                    with dpg.child_window(
                        tag=self.GRID_TAG,
                        height=-1,
                        border=False
                    ):
                        self._show_empty_state()
    
    def _create_stat_badge(self, label: str, value: str, tag: str):
        """Create a stat badge like the HTML version."""
        with dpg.group():
            dpg.add_text(value, tag=tag, color=self.COLORS['cyan'])
            dpg.add_text(label, color=self.COLORS['dim'])
    
    def _show_empty_state(self):
        """Show empty state message."""
        dpg.delete_item(self.GRID_TAG, children_only=True)
        
        with dpg.group(parent=self.GRID_TAG):
            dpg.add_spacer(height=50)
            dpg.add_text("No items loaded", color=self.COLORS['dim'])
            dpg.add_text("Click 'Load Game Data' to browse assets", 
                        color=self.COLORS['dim'])
    
    def _select_category(self, category: str):
        """Select a category filter."""
        self.current_category = category
        self._apply_filters()
    
    def _on_search(self, sender, value):
        """Handle search input."""
        self._apply_filters()
    
    def _do_search(self):
        """Trigger search."""
        self._apply_filters()
    
    def _apply_filters(self):
        """Apply category and search filters."""
        search_term = dpg.get_value(self.SEARCH_TAG).lower() if dpg.does_item_exist(self.SEARCH_TAG) else ""
        
        # Filter items
        self.filtered_items = []
        for item in self.items:
            # Category filter
            if self.current_category != 'all':
                if item.get('category', 'objects') != self.current_category:
                    continue
            
            # Search filter
            if search_term:
                name = item.get('name', '').lower()
                guid = str(item.get('guid', '')).lower()
                item_type = item.get('type', '').lower()
                
                if search_term not in name and search_term not in guid and search_term not in item_type:
                    continue
            
            self.filtered_items.append(item)
        
        # Update UI
        self._render_grid()
        
        if dpg.does_item_exist("results_info"):
            dpg.set_value("results_info", f"Showing {len(self.filtered_items)} items")
    
    def _render_grid(self):
        """Render the item grid."""
        dpg.delete_item(self.GRID_TAG, children_only=True)
        
        if not self.filtered_items:
            self._show_empty_state()
            return
        
        # Create grid with card items
        # DearPyGUI doesn't have CSS grid, so we use horizontal groups
        items_per_row = 4
        current_row = None
        
        for i, item in enumerate(self.filtered_items[:50]):  # Limit to 50 for performance
            if i % items_per_row == 0:
                current_row = dpg.add_group(horizontal=True, parent=self.GRID_TAG)
            
            self._create_card(item, current_row)
    
    def _create_card(self, item: dict, parent):
        """Create a card for an item."""
        name = item.get('name', 'Unknown')[:20]
        guid = item.get('guid', 0)
        item_type = item.get('type', 'Object')
        price = item.get('price', 0)
        
        # Card container
        with dpg.child_window(width=150, height=180, border=True, parent=parent):
            # Preview area (placeholder)
            with dpg.drawlist(width=140, height=80):
                dpg.draw_rectangle(
                    (0, 0), (140, 80),
                    fill=(42, 42, 74, 255),
                    color=(74, 74, 106, 255)
                )
                # Icon based on type
                icon = "🪑" if item_type == "Object" else "🧑" if item_type == "Character" else "📦"
                dpg.draw_text((55, 30), icon, size=24, color=(74, 74, 106, 255))
            
            # Card body
            dpg.add_text(name, color=self.COLORS['cyan'])
            
            # Type tag
            type_color = self.COLORS['green'] if item_type == "Object" else self.COLORS['blue']
            dpg.add_text(item_type, color=type_color)
            
            # GUID
            dpg.add_text(f"0x{guid:08X}", color=self.COLORS['dim'])
            
            # Price if available
            if price > 0:
                dpg.add_text(f"§{price}", color=self.COLORS['green'])
            
            # Action button
            dpg.add_button(
                label="View",
                callback=lambda s, a, u: self._view_item(u),
                user_data=item,
                width=60
            )
    
    def _view_item(self, item: dict):
        """View item details - opens appropriate viewer."""
        item_type = item.get('type', 'Object')
        
        if item_type == 'Character':
            # Publish event to open character viewer
            EventBus.publish(Events.CHARACTER_SELECTED, item)
        else:
            # Publish event to open object inspector
            EventBus.publish(Events.CHUNK_SELECTED, item)
    
    def _load_game_data(self):
        """Load game data from JSON files or FAR archives."""
        # Try to load from cached JSON files first
        webviewer_path = Path(__file__).parent.parent.parent.parent.parent / "Program" / "webviewer"
        
        self.items = []
        
        # Load objects.json if exists
        objects_json = webviewer_path / "objects.json"
        if objects_json.exists():
            try:
                with open(objects_json, 'r') as f:
                    objects = json.load(f)
                    for obj in objects:
                        obj['type'] = 'Object'
                        obj['category'] = 'objects'
                        self.items.append(obj)
            except:
                pass
        
        # Load characters.json if exists
        chars_json = webviewer_path / "characters.json"
        if chars_json.exists():
            try:
                with open(chars_json, 'r') as f:
                    chars = json.load(f)
                    for char in chars:
                        char['type'] = 'Character'
                        char['category'] = 'characters'
                        self.items.append(char)
            except:
                pass
        
        # Load meshes.json if exists
        meshes_json = webviewer_path / "meshes.json"
        if meshes_json.exists():
            try:
                with open(meshes_json, 'r') as f:
                    meshes = json.load(f)
                    for mesh in meshes:
                        mesh['type'] = 'Mesh'
                        mesh['category'] = 'meshes'
                        self.items.append(mesh)
            except:
                pass
        
        # Update category counts
        counts = {'all': len(self.items), 'objects': 0, 'characters': 0, 'meshes': 0}
        for item in self.items:
            cat = item.get('category', 'objects')
            counts[cat] = counts.get(cat, 0) + 1
        
        for cat, count in counts.items():
            tag = f"cat_count_{cat}"
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, f"({count})")
        
        # Update stats
        if dpg.does_item_exist("stat_objects"):
            dpg.set_value("stat_objects", str(counts.get('objects', 0)))
        if dpg.does_item_exist("stat_characters"):
            dpg.set_value("stat_characters", str(counts.get('characters', 0)))
        if dpg.does_item_exist("stat_meshes"):
            dpg.set_value("stat_meshes", str(counts.get('meshes', 0)))
        
        # Apply filters
        self._apply_filters()
    
    def _refresh(self):
        """Refresh the display."""
        self._apply_filters()
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
