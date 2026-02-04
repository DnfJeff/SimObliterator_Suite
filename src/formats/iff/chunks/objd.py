"""
OBJD Chunk - Object Definition
Port of FreeSO's tso.files/Formats/IFF/Chunks/OBJD.cs

This is THE main chunk for objects - defines all object properties.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer


class OBJDType(IntEnum):
    """Object types."""
    UNKNOWN = 0
    PERSON = 2        # Character or NPC
    NORMAL = 4        # Buyable objects
    SIM_TYPE = 7      # System objects (roaches, tutorial, etc)
    PORTAL = 8        # Stairs, doors, windows
    CURSOR = 9
    PRIZE_TOKEN = 10
    INTERNAL = 11     # Temporary location for drop/shoo
    GIFT_TOKEN = 12
    FOOD = 34


@register_chunk("OBJD")
@dataclass
class OBJD(IffChunk):
    """
    Object Definition chunk - the main chunk for any object.
    Maps to: FSO.Files.Formats.IFF.Chunks.OBJD
    """
    version: int = 0
    
    # Core properties
    stack_size: int = 0
    base_graphic_id: int = 0
    num_graphics: int = 0
    tree_table_id: int = 0
    interaction_group_id: int = 0
    object_type: OBJDType = OBJDType.UNKNOWN
    master_id: int = 0
    sub_index: int = 0
    animation_table_id: int = 0
    guid: int = 0
    disabled: int = 0
    price: int = 0
    body_string_id: int = 0
    slot_id: int = 0
    catalog_strings_id: int = 0
    
    # BHAV references (behavior scripts)
    bhav_main_id: int = 0
    bhav_gardening_id: int = 0
    bhav_wash_hands_id: int = 0
    bhav_portal: int = 0
    bhav_allow_intersection_id: int = 0
    bhav_prepare_food_id: int = 0
    bhav_cook_food_id: int = 0
    bhav_place_surface_id: int = 0
    bhav_dispose_id: int = 0
    bhav_eat_id: int = 0
    bhav_pickup_from_slot_id: int = 0
    bhav_wash_dish_id: int = 0
    bhav_eat_surface_id: int = 0
    bhav_sit_id: int = 0
    bhav_stand_id: int = 0
    bhav_init: int = 0
    bhav_place: int = 0
    bhav_user_pickup: int = 0
    bhav_load: int = 0
    bhav_user_place: int = 0
    bhav_room_change: int = 0
    bhav_cleanup: int = 0
    bhav_level_info: int = 0
    bhav_serving_surface: int = 0
    bhav_clean: int = 0
    bhav_queue_skipped: int = 0
    bhav_wall_adjacency_changed: int = 0
    bhav_pickup: int = 0
    bhav_dynamic_multitile_update: int = 0
    bhav_repair: int = 0
    
    # Economic properties
    sale_price: int = 0
    initial_depreciation: int = 0
    daily_depreciation: int = 0
    self_depreciating: int = 0
    depreciation_limit: int = 0
    
    # Flags and categories
    room_flags: int = 0
    function_flags: int = 0
    uses_fn_table: int = 0
    bit_field1: int = 0
    global_sim: int = 0
    wall_style: int = 0
    object_version: int = 0
    motive_effects_id: int = 0
    catalog_id: int = 0
    level_offset: int = 0
    shadow: int = 0
    num_attributes: int = 0
    front_direction: int = 0
    my_lead_object: int = 0
    dynamic_sprite_base_id: int = 0
    num_dynamic_sprites: int = 0
    chair_entry_flags: int = 0
    tile_width: int = 0
    lot_categories: int = 0
    build_mode_type: int = 0
    original_guid: int = 0
    suit_guid: int = 0
    thumbnail_graphic: int = 0
    shadow_flags: int = 0
    footprint_mask: int = 0
    shadow_brightness: int = 0
    wall_style_sprite_id: int = 0
    
    # Motive ratings
    rating_hunger: int = 0
    rating_comfort: int = 0
    rating_hygiene: int = 0
    rating_bladder: int = 0
    rating_energy: int = 0
    rating_fun: int = 0
    rating_room: int = 0
    rating_skill_flags: int = 0
    
    # Type attributes
    num_type_attributes: int = 0
    misc_flags: int = 0
    type_attr_guid: int = 0
    
    # Extended fields (newer versions)
    function_subsort: int = 0
    dt_subsort: int = 0
    keep_buying: int = 0
    vacation_subsort: int = 0
    reset_lot_action: int = 0
    community_subsort: int = 0
    dream_flags: int = 0
    render_flags: int = 0
    vitaboy_flags: int = 0
    st_subsort: int = 0
    mt_subsort: int = 0
    
    # Raw data for unknown fields
    raw_data: list[int] = field(default_factory=list)
    
    @property
    def is_master(self) -> bool:
        """Is this the master object in a multi-tile object?"""
        return self.master_id == 0 or self.sub_index == -1
    
    @property
    def is_multi_tile(self) -> bool:
        """Is this part of a multi-tile object?"""
        return self.master_id != 0
    
    @property
    def footprint_north(self) -> int:
        return self.footprint_mask & 0xF
    
    @property
    def footprint_east(self) -> int:
        return (self.footprint_mask >> 4) & 0xF
    
    @property
    def footprint_south(self) -> int:
        return (self.footprint_mask >> 8) & 0xF
    
    @property
    def footprint_west(self) -> int:
        return (self.footprint_mask >> 12) & 0xF
    
    def get_catalog_category(self) -> int:
        """
        Calculate catalog category for buy/build UI.
        Based on FreeSO's TS1ObjectProvider.cs logic.
        
        Returns:
            Category index 0-15:
            - 0-7: Buy mode categories (from FunctionFlags bits)
            - 8-15: Build mode categories (BuildModeType + 7)
        """
        # Only catalogable if:
        # - Has function or build flags
        # - Not disabled
        # - Is master object or single tile
        # - Has graphics or is multi-tile
        if self.disabled != 0:
            return -1
        if not (self.function_flags > 0 or self.build_mode_type > 0):
            return -1
        if not (self.master_id == 0 or self.sub_index == -1):
            return -1
        if not (self.is_multi_tile or self.num_graphics > 0):
            return -1
        
        # Buy mode: Calculate from FunctionFlags bit position
        if self.function_flags > 0:
            import math
            return int(math.log2(self.function_flags))
        
        # Build mode: BuildModeType + 7
        if self.build_mode_type > 0:
            return self.build_mode_type + 7
        
        return -1
    
    @property
    def is_catalogable(self) -> bool:
        """Check if this object should appear in buy/build catalog."""
        return self.get_catalog_category() >= 0
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read OBJD chunk from stream."""
        # Read version (first 4 bytes = field count * 2)
        self.version = io.read_uint32()
        
        # Calculate number of fields
        num_fields = self.version // 2
        
        # Read all fields as raw ushorts first
        self.raw_data = []
        for _ in range(min(num_fields, 200)):  # Safety limit
            if io.has_bytes(2):
                self.raw_data.append(io.read_uint16())
            else:
                break
        
        # Map fields to properties (based on version)
        self._map_fields()
    
    def _map_fields(self):
        """Map raw field data to named properties."""
        if len(self.raw_data) < 10:
            return
        
        # Core fields present in all versions
        idx = 0
        def get(i: int, signed: bool = False) -> int:
            if i < len(self.raw_data):
                val = self.raw_data[i]
                if signed and val > 32767:
                    return val - 65536
                return val
            return 0
        
        self.stack_size = get(0)
        self.base_graphic_id = get(1)
        self.num_graphics = get(2)
        self.bhav_main_id = get(3)
        self.bhav_gardening_id = get(4)
        self.tree_table_id = get(5)
        self.interaction_group_id = get(6, signed=True)
        self.object_type = OBJDType(get(7)) if get(7) in [e.value for e in OBJDType] else OBJDType.UNKNOWN
        self.master_id = get(8)
        self.sub_index = get(9, signed=True)
        self.bhav_wash_hands_id = get(10)
        self.animation_table_id = get(11)
        
        # GUID (2 ushorts combined)
        self.guid = get(12) | (get(13) << 16)
        
        self.disabled = get(14)
        self.bhav_portal = get(15)
        self.price = get(16)
        self.body_string_id = get(17)
        self.slot_id = get(18)
        self.bhav_allow_intersection_id = get(19)
        self.uses_fn_table = get(20)
        self.bit_field1 = get(21)
        
        # Food BHAVs
        self.bhav_prepare_food_id = get(22)
        self.bhav_cook_food_id = get(23)
        self.bhav_place_surface_id = get(24)
        self.bhav_dispose_id = get(25)
        self.bhav_eat_id = get(26)
        self.bhav_pickup_from_slot_id = get(27)
        self.bhav_wash_dish_id = get(28)
        self.bhav_eat_surface_id = get(29)
        self.bhav_sit_id = get(30)
        self.bhav_stand_id = get(31)
        
        # Economics
        self.sale_price = get(32)
        self.initial_depreciation = get(33)
        self.daily_depreciation = get(34)
        self.self_depreciating = get(35)
        self.depreciation_limit = get(36)
        self.room_flags = get(37)
        self.function_flags = get(38)
        self.catalog_strings_id = get(39)
        
        # More BHAVs
        self.global_sim = get(40)
        self.bhav_init = get(41)
        self.bhav_place = get(42)
        self.bhav_user_pickup = get(43)
        self.wall_style = get(44)
        self.bhav_load = get(45)
        self.bhav_user_place = get(46)
        self.object_version = get(47)
        self.bhav_room_change = get(48)
        self.motive_effects_id = get(49)
        self.bhav_cleanup = get(50)
        self.bhav_level_info = get(51)
        self.catalog_id = get(52)
        self.bhav_serving_surface = get(53)
        self.level_offset = get(54)
        self.shadow = get(55)
        self.num_attributes = get(56)
        
        if len(self.raw_data) > 57:
            self.bhav_clean = get(57)
            self.bhav_queue_skipped = get(58)
            self.front_direction = get(59)
            self.bhav_wall_adjacency_changed = get(60)
            self.my_lead_object = get(61)
            self.dynamic_sprite_base_id = get(62)
            self.num_dynamic_sprites = get(63)
        
        if len(self.raw_data) > 64:
            self.chair_entry_flags = get(64)
            self.tile_width = get(65)
            self.lot_categories = get(66)
            self.build_mode_type = get(67)
            self.original_guid = get(68) | (get(69) << 16)
            self.suit_guid = get(70) | (get(71) << 16)
            self.bhav_pickup = get(72)
            self.thumbnail_graphic = get(73)
            self.shadow_flags = get(74)
            self.footprint_mask = get(75)
            self.bhav_dynamic_multitile_update = get(76)
            self.shadow_brightness = get(77)
            self.bhav_repair = get(78)
        
        if len(self.raw_data) > 79:
            self.wall_style_sprite_id = get(79)
            self.rating_hunger = get(80, signed=True)
            self.rating_comfort = get(81, signed=True)
            self.rating_hygiene = get(82, signed=True)
            self.rating_bladder = get(83, signed=True)
            self.rating_energy = get(84, signed=True)
            self.rating_fun = get(85, signed=True)
            self.rating_room = get(86, signed=True)
            self.rating_skill_flags = get(87)
        
        if len(self.raw_data) > 88:
            self.num_type_attributes = get(88)
            self.misc_flags = get(89)
            self.type_attr_guid = get(90) | (get(91) << 16)
    
    def __str__(self) -> str:
        return f"OBJD #{self.chunk_id}: {self.chunk_label} (GUID: 0x{self.guid:08X}, Type: {self.object_type.name})"
