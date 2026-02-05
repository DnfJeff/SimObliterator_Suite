"""
Save Editor Panel - The Sims 1 Save File Editor

The main "normie" tool - edit family money, Sim skills, personality, motives.
Styled after the webviewer design aesthetic.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..events import EventBus, Events
from ..state import STATE

# Import MutationPipeline for write barrier
try:
    from Tools.core.mutation_pipeline import MutationPipeline, MutationRequest, MutationDiff, MutationMode, MutationResult
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False
    MutationPipeline = None


class SaveEditorPanel:
    """Save editor panel - edit family money, sim data, relationships."""
    
    TAG = "save_editor"
    FAMILY_LIST_TAG = "save_family_list"
    SIM_LIST_TAG = "save_sim_list"
    SKILLS_GROUP_TAG = "save_skills_group"
    PERSONALITY_GROUP_TAG = "save_personality_group"
    
    # Color palette from webviewer
    COLORS = {
        'cyan': (0, 212, 255),
        'red': (233, 69, 96),
        'green': (76, 175, 80),
        'yellow': (255, 213, 79),
        'blue': (148, 179, 253),
        'text': (238, 238, 238),
        'dim': (136, 136, 136),
        'bg_panel': (15, 52, 96),
        'bg_dark': (26, 26, 46),
    }
    
    def __init__(self, width: int = 450, height: int = 700, pos: tuple = (10, 30)):
        self.width = width
        self.height = height
        self.pos = pos
        self.save_manager = None
        self.current_family = None
        self.current_sim = None
        self._create_panel()
        self._subscribe_events()
    
    def _subscribe_events(self):
        """Subscribe to file load events (from flow map)."""
        EventBus.subscribe(Events.FILE_LOADED, self._on_file_loaded)
    
    def _on_file_loaded(self, data):
        """Handle file loaded - auto-detect save files."""
        if STATE.current_file_type == "SAVE":
            self._load_save_from_path(STATE.current_file.parent)
    
    def _create_panel(self):
        """Create the save editor panel."""
        with dpg.window(
            label="💾 Save Editor",
            tag=self.TAG,
            width=self.width,
            height=self.height,
            pos=self.pos,
            on_close=self._on_close
        ):
            # Header
            dpg.add_text("Save Editor", color=self.COLORS['red'])
            dpg.add_text("Edit family money, Sim skills & personality", 
                        color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Load save section
            with dpg.collapsing_header(label="📂 Load Save", default_open=True):
                with dpg.group():
                    dpg.add_text("Save Location:", color=self.COLORS['blue'])
                    
                    # Quick paths
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="Steam Save",
                            callback=self._load_steam_save,
                            width=130
                        )
                        dpg.add_button(
                            label="Browse...",
                            callback=self._browse_save,
                            width=100
                        )
                    
                    dpg.add_text("No save loaded", tag="save_status", 
                                color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Families section
            with dpg.collapsing_header(label="👨‍👩‍👧‍👦 Families", default_open=True):
                dpg.add_text("Select a family:", color=self.COLORS['blue'])
                
                with dpg.child_window(height=120, border=True, tag=self.FAMILY_LIST_TAG):
                    dpg.add_text("Load a save first", color=self.COLORS['dim'])
                
                dpg.add_spacer(height=5)
                
                # Money editor
                with dpg.group(horizontal=True):
                    dpg.add_text("Money: $", color=self.COLORS['green'])
                    dpg.add_input_int(
                        default_value=0,
                        width=120,
                        tag="money_input",
                        callback=self._on_money_changed
                    )
                    dpg.add_button(
                        label="Max §",
                        callback=lambda: dpg.set_value("money_input", 9999999),
                        width=50
                    )
            
            dpg.add_separator()
            
            # Sims section
            with dpg.collapsing_header(label="🧑 Sims", default_open=True):
                dpg.add_text("Family members:", color=self.COLORS['blue'])
                
                with dpg.child_window(height=100, border=True, tag=self.SIM_LIST_TAG):
                    dpg.add_text("Select a family first", color=self.COLORS['dim'])
            
            dpg.add_separator()
            
            # Skills section
            with dpg.collapsing_header(label="📚 Skills", default_open=False):
                with dpg.group(tag=self.SKILLS_GROUP_TAG):
                    skills = [
                        ("Cooking", "skill_cooking"),
                        ("Mechanical", "skill_mech"),
                        ("Charisma", "skill_charisma"),
                        ("Logic", "skill_logic"),
                        ("Body", "skill_body"),
                        ("Creativity", "skill_creativity"),
                    ]
                    for skill_name, tag in skills:
                        with dpg.group(horizontal=True):
                            dpg.add_text(f"{skill_name}:", color=self.COLORS['blue'], 
                                        indent=10)
                            dpg.add_slider_int(
                                default_value=0,
                                min_value=0,
                                max_value=1000,
                                width=180,
                                tag=tag,
                                format="%d/1000"
                            )
                    
                    dpg.add_spacer(height=5)
                    dpg.add_button(
                        label="Max All Skills",
                        callback=self._max_all_skills,
                        width=200
                    )
            
            # Personality section
            with dpg.collapsing_header(label="💫 Personality", default_open=False):
                with dpg.group(tag=self.PERSONALITY_GROUP_TAG):
                    traits = [
                        ("Nice", "trait_nice"),
                        ("Active", "trait_active"),
                        ("Generous", "trait_generous"),
                        ("Playful", "trait_playful"),
                        ("Outgoing", "trait_outgoing"),
                        ("Neat", "trait_neat"),
                    ]
                    for trait_name, tag in traits:
                        with dpg.group(horizontal=True):
                            dpg.add_text(f"{trait_name}:", color=self.COLORS['yellow'], 
                                        indent=10)
                            dpg.add_slider_int(
                                default_value=500,
                                min_value=0,
                                max_value=1000,
                                width=180,
                                tag=tag,
                                format="%d"
                            )
            
            # Motives section
            with dpg.collapsing_header(label="❤️ Motives", default_open=False):
                motives = [
                    ("Hunger", "motive_hunger", self.COLORS['green']),
                    ("Comfort", "motive_comfort", self.COLORS['blue']),
                    ("Hygiene", "motive_hygiene", self.COLORS['cyan']),
                    ("Bladder", "motive_bladder", self.COLORS['yellow']),
                    ("Energy", "motive_energy", self.COLORS['green']),
                    ("Fun", "motive_fun", self.COLORS['red']),
                    ("Social", "motive_social", self.COLORS['blue']),
                    ("Room", "motive_room", self.COLORS['cyan']),
                ]
                for motive_name, tag, color in motives:
                    with dpg.group(horizontal=True):
                        dpg.add_text(f"{motive_name}:", color=color, indent=10)
                        dpg.add_slider_int(
                            default_value=0,
                            min_value=-100,
                            max_value=100,
                            width=180,
                            tag=tag,
                            format="%d"
                        )
                
                dpg.add_spacer(height=5)
                dpg.add_button(
                    label="Max All Motives",
                    callback=self._max_all_motives,
                    width=200
                )
            
            dpg.add_separator()
            
            # Save buttons
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="💾 Save Changes",
                    callback=self._save_changes,
                    width=150
                )
                dpg.add_button(
                    label="↩️ Revert",
                    callback=self._revert_changes,
                    width=100
                )
            
            dpg.add_text("", tag="save_message", color=self.COLORS['green'])
    
    def _load_steam_save(self):
        """Load save from Steam default location."""
        # Try common Steam save paths
        paths = [
            Path.home() / "Saved Games" / "Electronic Arts" / "The Sims 25",
            Path(r"C:\Program Files (x86)\Steam\steamapps\common\The Sims Legacy Collection\UserData7"),
            Path.home() / "Documents" / "EA Games" / "The Sims",
        ]
        
        for path in paths:
            if path.exists():
                self._load_save_from_path(path)
                return
        
        dpg.set_value("save_status", "Steam save not found - use Browse")
        dpg.configure_item("save_status", color=self.COLORS['red'])
    
    def _browse_save(self):
        """Browse for save folder."""
        # TODO: Use file dialog
        dpg.set_value("save_status", "Browse not implemented yet")
    
    def _load_save_from_path(self, path: Path):
        """Load save from given path."""
        try:
            from Tools.save_editor.save_manager import SaveManager
            
            self.save_manager = SaveManager(str(path))
            if self.save_manager.load_neighborhood():
                families = self.save_manager.list_families()
                dpg.set_value("save_status", f"Loaded: {len(families)} families")
                dpg.configure_item("save_status", color=self.COLORS['green'])
                self._populate_families(families)
            else:
                dpg.set_value("save_status", "Failed to load neighborhood")
                dpg.configure_item("save_status", color=self.COLORS['red'])
        except Exception as e:
            dpg.set_value("save_status", f"Error: {e}")
            dpg.configure_item("save_status", color=self.COLORS['red'])
    
    def _populate_families(self, families):
        """Populate family list."""
        dpg.delete_item(self.FAMILY_LIST_TAG, children_only=True)
        
        for fami in sorted(families, key=lambda f: f.chunk_id):
            house = f"House {fami.house_number}" if fami.house_number > 0 else "No house"
            townie = " [Townie]" if fami.is_townie else ""
            label = f"${fami.budget:,} | {len(fami.member_guids)} Sims | {house}{townie}"
            
            with dpg.group(horizontal=True, parent=self.FAMILY_LIST_TAG):
                dpg.add_button(
                    label=f"Fam #{fami.chunk_id}",
                    callback=lambda s, a, u: self._select_family(u),
                    user_data=fami,
                    width=80
                )
                dpg.add_text(label, color=self.COLORS['text'])
    
    def _select_family(self, fami):
        """Select a family."""
        self.current_family = fami
        dpg.set_value("money_input", fami.budget)
        
        # Populate sims
        self._populate_sims(fami)
    
    def _populate_sims(self, fami):
        """Populate sim list for family."""
        dpg.delete_item(self.SIM_LIST_TAG, children_only=True)
        
        if not self.save_manager:
            return
        
        for guid in fami.member_guids:
            neigh = self.save_manager.get_neighbor_by_guid(guid)
            if neigh:
                name = neigh.name or f"Sim 0x{guid:08X}"
                
                with dpg.group(horizontal=True, parent=self.SIM_LIST_TAG):
                    dpg.add_button(
                        label=name[:15],
                        callback=lambda s, a, u: self._select_sim(u),
                        user_data=neigh,
                        width=120
                    )
                    dpg.add_text(f"ID: {neigh.neighbor_id}", color=self.COLORS['dim'])
    
    def _select_sim(self, neigh):
        """Select a sim and populate their data."""
        self.current_sim = neigh
        
        if not neigh.person_data or len(neigh.person_data) < 20:
            return
        
        # Skills (indices 0-5)
        skill_tags = ["skill_cooking", "skill_mech", "skill_charisma", 
                      "skill_logic", "skill_body", "skill_creativity"]
        for i, tag in enumerate(skill_tags):
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, neigh.person_data[i] if i < len(neigh.person_data) else 0)
        
        # Personality (indices 7-12)
        trait_tags = ["trait_nice", "trait_active", "trait_generous",
                      "trait_playful", "trait_outgoing", "trait_neat"]
        for i, tag in enumerate(trait_tags):
            idx = 7 + i
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, neigh.person_data[idx] if idx < len(neigh.person_data) else 500)
        
        # Motives (indices 13-20)
        motive_tags = ["motive_hunger", "motive_comfort", "motive_hygiene",
                       "motive_bladder", "motive_energy", "motive_fun",
                       "motive_social", "motive_room"]
        for i, tag in enumerate(motive_tags):
            idx = 13 + i
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, neigh.person_data[idx] if idx < len(neigh.person_data) else 0)
    
    def _on_money_changed(self, sender, value):
        """Handle money input change."""
        if self.current_family and self.save_manager:
            self.save_manager.set_family_money(self.current_family.chunk_id, value)
            dpg.set_value("save_message", "Money updated (unsaved)")
    
    def _max_all_skills(self):
        """Max all skills to 1000."""
        skill_tags = ["skill_cooking", "skill_mech", "skill_charisma",
                      "skill_logic", "skill_body", "skill_creativity"]
        for tag in skill_tags:
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, 1000)
        dpg.set_value("save_message", "Skills maxed (unsaved)")
    
    def _max_all_motives(self):
        """Max all motives to 100."""
        motive_tags = ["motive_hunger", "motive_comfort", "motive_hygiene",
                       "motive_bladder", "motive_energy", "motive_fun",
                       "motive_social", "motive_room"]
        for tag in motive_tags:
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, 100)
        dpg.set_value("save_message", "Motives maxed (unsaved)")
    
    def _save_changes(self):
        """Save all changes to file through MutationPipeline."""
        if not self.save_manager:
            dpg.set_value("save_message", "No save loaded")
            return
        
        # Route through MutationPipeline if available
        if PIPELINE_AVAILABLE and MutationPipeline:
            pipeline = MutationPipeline.get()
            
            # Create mutation request
            request = MutationRequest(
                target_type='save',
                target_id='neighborhood',
                target_file=str(self.save_manager.neighborhood_path) if self.save_manager.neighborhood_path else '',
                reason="User edit via Save Editor",
                source_panel="save_editor",
                diffs=[MutationDiff(
                    field_path="save.family.money",
                    old_value="(original)",
                    new_value="(modified)",
                    display_old="Original save state",
                    display_new="User modifications"
                )]
            )
            
            # Check if pipeline allows writes
            if not pipeline.is_writable():
                if pipeline.mode == MutationMode.INSPECT:
                    dpg.set_value("save_message", "⚠ INSPECT mode - switch to MUTATE to save")
                    dpg.configure_item("save_message", color=self.COLORS['yellow'])
                    return
                elif pipeline.is_preview():
                    dpg.set_value("save_message", "📋 PREVIEW mode - changes shown but not saved")
                    dpg.configure_item("save_message", color=self.COLORS['blue'])
                    return
            
            # Propose mutation through pipeline
            audit = pipeline.propose(request)
            
            if audit.result != MutationResult.SUCCESS and audit.result != MutationResult.PREVIEW_ONLY:
                dpg.set_value("save_message", f"⚠ {audit.risk_notes[0] if audit.risk_notes else 'Mutation blocked'}")
                dpg.configure_item("save_message", color=self.COLORS['red'])
                return
        
        # Execute save
        if self.save_manager.save_neighborhood(backup=True):
            dpg.set_value("save_message", "✓ Saved successfully (backup created)")
            dpg.configure_item("save_message", color=self.COLORS['green'])
        else:
            dpg.set_value("save_message", "✗ Save failed")
            dpg.configure_item("save_message", color=self.COLORS['red'])
    
    def _revert_changes(self):
        """Reload save, discarding changes."""
        if self.save_manager and self.save_manager.neighborhood_path:
            self._load_save_from_path(self.save_manager.neighborhood_path.parent)
            dpg.set_value("save_message", "Changes reverted")
    
    def _on_close(self):
        """Handle panel close."""
        dpg.configure_item(self.TAG, show=False)
    
    @classmethod
    def show(cls):
        """Show the panel."""
        if dpg.does_item_exist(cls.TAG):
            dpg.configure_item(cls.TAG, show=True)
            dpg.focus_item(cls.TAG)
