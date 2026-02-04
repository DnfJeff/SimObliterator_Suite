"""
BHAV Operand Decoders - Parse 8-byte operand data for each primitive

Each primitive type has a specific operand structure. This module provides
decoder functions to parse the raw bytes into structured operand objects.

Source: FreeSO TSOClient/tso.simantics/Primitives/*.cs
"""

from typing import Dict, Any, Optional
from io import BytesIO
import struct

from .bhav_ast import (
    VMVariableScope, VMPrimitiveOperand, VMExpressionOperator, VMAnimationScope,
    VMCreateObjectPosition, VMMotive,
    PushVariableOperand, CompareOperand, AnimateSimOperand,
    GetDistanceToOperand, PlaySoundOperand, RandomNumberOperand,
    CreateObjectInstanceOperand, DropOntoOperand, RunSubroutineOperand,
    ShowStringOperand, UnknownOperand, VariableRef,
    ExpressionOperand, TestObjectTypeOperand, SetMotiveChangeOperand,
    RefreshOperand, RelationshipOperand, SetBalloonHeadlineOperand,
    SleepOperand, GotoRoutingSlotOperand, GotoRelativePositionOperand,
    DropOntoOperandFixed, BurnOperand, DialogOperand, FindLocationForOperand,
    IdleForInputOperand, InventoryOperationsOperand, InvokePluginOperand,
    LookTowardsOperand, PushInteractionOperand, RemoveObjectInstanceOperand,
    RunFunctionalTreeOperand, RunTreeByNameOperand, SetToNextOperand,
    SnapOperand, SpecialEffectOperand, StopAllSoundsOperand,
    TS1InventoryOperationsOperand, TS1MakeNewCharacterOperand,
    GetDirectionToOperand, ChangeSuitOrAccessoryOperand, ShowStringOperandFixed,
    BreakPointOperand, DialogGlobalStringsOperand, DialogPrivateStringsOperand,
    DialogSemiGlobalStringsOperand, FindBestActionOperand, FindBestObjectForFunctionOperand,
    GenericTS1CallOperand, GenericTSOCallOperand, GetTerrainInfoOperand,
    GosubFoundActionOperand, GrabOperand, NotifyOutOfIdleOperand,
    OnlineJobsCallOperand, ReachOperand, SysLogOperand,
    TestSimInteractingWithOperand, TransferFundsOperand, TS1BudgetOperand
)


def read_uint16_le(data: bytes, offset: int) -> int:
    """Read uint16 little-endian"""
    return struct.unpack('<H', data[offset:offset+2])[0]


def read_int16_le(data: bytes, offset: int) -> int:
    """Read int16 little-endian"""
    return struct.unpack('<h', data[offset:offset+2])[0]


def read_uint32_le(data: bytes, offset: int) -> int:
    """Read uint32 little-endian"""
    return struct.unpack('<I', data[offset:offset+4])[0]


def read_byte(data: bytes, offset: int) -> int:
    """Read single byte"""
    return data[offset] if offset < len(data) else 0


# ============================================================================
# Core Variable Primitives (0-10)
# ============================================================================

def decode_push_variable(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Push Variable operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    var_id = read_uint16_le(data, 0)
    scope = VMVariableScope(read_byte(data, 2))
    offset = read_int16_le(data, 4)
    
    return PushVariableOperand(
        variable=VariableRef(scope, offset)
    )


def decode_compare(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Compare operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    value1 = read_uint16_le(data, 0)
    comparison = read_byte(data, 2)
    scope = read_byte(data, 3)
    value2 = read_int16_le(data, 4)
    
    return CompareOperand(value1, comparison, value2)


def decode_test_object_type(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Test Object Type operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    # Similar structure to compare
    object_type = read_uint16_le(data, 0)
    return CompareOperand(object_type, 0, 0)  # Placeholder


def decode_test_sim_description(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Test Sim Description operand"""
    return UnknownOperand(data)  # Complex structure


def decode_test_actor_type(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Test Actor Type operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    actor_type = read_byte(data, 0)
    return CompareOperand(actor_type, 0, 0)


def decode_test_relationship(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Test Relationship operand"""
    return UnknownOperand(data)  # Complex structure


def decode_animate_sim(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Animate Sim operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    source = read_byte(data, 0)
    animation_id = read_uint16_le(data, 1)
    block_id = read_byte(data, 3)
    state_id = read_byte(data, 4)
    
    return AnimateSimOperand(source, animation_id, block_id, state_id)


def decode_create_object_instance(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Create Object Instance operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    object_guid = read_uint16_le(data, 0)
    stack_flag = read_byte(data, 2)
    scope = VMVariableScope(read_byte(data, 3))
    scope_data = read_int16_le(data, 4)
    
    return CreateObjectInstanceOperand(object_guid, stack_flag, scope, scope_data)


def decode_drop(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Drop operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    surface_type = read_byte(data, 0)
    return CompareOperand(surface_type, 0, 0)


def decode_drop_onto(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Drop Onto operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    target_scope = VMVariableScope(read_byte(data, 0))
    target_offset = read_int16_le(data, 1)
    drop_mode = read_byte(data, 6)
    
    return DropOntoOperand(target_scope, target_offset, drop_mode)


def decode_grab(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Grab operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    grab_type = read_byte(data, 0)
    return CompareOperand(grab_type, 0, 0)


# ============================================================================
# Math & Navigation Primitives (11-20)
# ============================================================================

def decode_get_distance_to(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Get Distance To operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    temp_num = read_uint16_le(data, 0)
    flags = read_byte(data, 2)
    object_scope = VMVariableScope(read_byte(data, 3))
    scope_data = read_int16_le(data, 4)
    
    return GetDistanceToOperand(temp_num, flags, object_scope, scope_data)


def decode_play_sound(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Play Sound operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    sound_id = read_uint16_le(data, 0)
    volume = read_byte(data, 2)
    pitch = read_byte(data, 3)
    
    return PlaySoundOperand(sound_id, volume, pitch)


def decode_goto_routing_slot(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Goto Routing Slot operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    slot_type = read_byte(data, 0)
    object_id = read_uint16_le(data, 1)
    slot_num = read_byte(data, 3)
    
    return CompareOperand(slot_type, slot_num, object_id)


def decode_goto_relative_position(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Goto Relative Position operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    x_offset = read_int16_le(data, 0)
    y_offset = read_int16_le(data, 2)
    z_offset = read_byte(data, 4)
    speed = read_byte(data, 5)
    
    return CompareOperand(x_offset, speed, y_offset)


def decode_find_best_object(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Find Best Object operand"""
    return UnknownOperand(data)


def decode_find_location_for(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Find Location For operand"""
    return UnknownOperand(data)


def decode_find_best_action(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Find Best Action operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    interaction_type = read_uint16_le(data, 0)
    priority = read_byte(data, 2)
    
    return CompareOperand(interaction_type, priority, 0)


def decode_run_subroutine(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Run Subroutine (BHAV call) operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    group_id = read_uint16_le(data, 0)
    bhav_id = read_uint16_le(data, 2)
    arg_count = read_byte(data, 4)
    
    return RunSubroutineOperand(group_id, bhav_id, arg_count)


def decode_push_interaction(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Push Interaction operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    interaction_type = read_uint16_le(data, 0)
    priority = read_byte(data, 4)
    
    return CompareOperand(interaction_type, priority, 0)


def decode_get_direction_to(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Get Direction To operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    temp_num = read_uint16_le(data, 0)
    flags = read_byte(data, 2)
    object_scope = VMVariableScope(read_byte(data, 3))
    scope_data = read_int16_le(data, 4)
    
    return GetDistanceToOperand(temp_num, flags, object_scope, scope_data)


# ============================================================================
# String & Dialog Primitives (33-35)
# ============================================================================

def decode_show_string(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Show String operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    string_table = read_uint16_le(data, 0)
    string_index = read_uint16_le(data, 2)
    duration = read_byte(data, 4)
    
    return ShowStringOperand(string_table, string_index, duration)


def decode_set_balloon_headline(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Set Balloon Headline operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    icon_id = read_uint16_le(data, 0)
    string_table = read_uint16_le(data, 2)
    string_index = read_byte(data, 4)
    
    return ShowStringOperand(string_table, string_index, icon_id)


def decode_dialog_callback(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Dialog Callback operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    callback_id = read_uint16_le(data, 0)
    default_choice = read_uint16_le(data, 2)
    
    return CompareOperand(callback_id, 0, default_choice)


# ============================================================================
# Extended Primitives (40+)
# ============================================================================

def decode_transfer_funds(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Transfer Funds operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    amount = read_uint16_le(data, 0)
    flags = read_byte(data, 2)
    
    return CompareOperand(amount, flags, 0)


def decode_animate_sim_extended(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Extended Animate Sim operand"""
    return decode_animate_sim(data)


def decode_change_suit_or_accessory(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Change Suit or Accessory operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    outfit_type = read_byte(data, 0)
    outfit_id = read_uint16_le(data, 1)
    
    return CompareOperand(outfit_type, 0, outfit_id)


def decode_random_number(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Random Number operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    range_scope = VMVariableScope(read_byte(data, 0))
    range_data = read_int16_le(data, 1)
    dest_scope = VMVariableScope(read_byte(data, 3))
    dest_data = read_int16_le(data, 4)
    
    return RandomNumberOperand(range_scope, range_data, dest_scope, dest_data)


# ============================================================================
# System Primitives (250-255)
# ============================================================================

def decode_breakpoint(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode BreakPoint operand"""
    return None  # No operand data


def decode_sleep(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Sleep operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    stack_var = read_uint16_le(data, 0)
    return SleepOperand(stack_var)


# ============================================================================
# Additional Missing Operands (High Priority)
# ============================================================================

def decode_expression_fixed(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Expression operand (fixed version with correct byte layout)"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    lhs_data = read_int16_le(data, 0)
    rhs_data = read_int16_le(data, 2)
    is_signed = read_byte(data, 4) != 0
    operator = VMExpressionOperator(read_byte(data, 5))
    lhs_owner = VMVariableScope(read_byte(data, 6))
    rhs_owner = VMVariableScope(read_byte(data, 7))
    
    return ExpressionOperand(lhs_data, rhs_data, is_signed, operator, lhs_owner, rhs_owner)


def decode_test_object_type(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Test Object Type operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    guid = read_uint32_le(data, 0)
    id_data = read_int16_le(data, 4)
    id_owner = VMVariableScope(read_byte(data, 6))
    
    return TestObjectTypeOperand(guid, id_data, id_owner)


def decode_get_direction_to_fixed(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Get Direction To operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    result_data = read_int16_le(data, 0)
    result_owner = VMVariableScope(read_byte(data, 2))
    flags = read_byte(data, 3)
    object_scope = VMVariableScope(read_byte(data, 4))
    object_scope_data = read_int16_le(data, 5)
    
    return GetDirectionToOperand(result_data, result_owner, flags, object_scope, object_scope_data)


def decode_set_motive_change(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Set Motive Change operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    delta_owner = VMVariableScope(read_byte(data, 0))
    delta_data = read_int16_le(data, 1)
    max_owner = VMVariableScope(read_byte(data, 3))
    max_data = read_int16_le(data, 4)
    flags = read_byte(data, 6)
    motive = VMMotive(read_byte(data, 7))
    
    clear_all = (flags & 0x01) != 0
    once = (flags & 0x02) != 0
    
    return SetMotiveChangeOperand(delta_owner, delta_data, max_owner, max_data, flags, motive, clear_all, once)


def decode_change_suit_or_accessory(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Change Suit or Accessory operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    suit_data = read_int16_le(data, 0)
    suit_scope = VMVariableScope(read_byte(data, 2))
    flags = read_byte(data, 3)
    
    return ChangeSuitOrAccessoryOperand(suit_data, suit_scope, flags)


def decode_refresh(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Refresh operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    target_object = read_uint16_le(data, 0)
    refresh_type = read_byte(data, 2)
    
    return RefreshOperand(target_object, refresh_type)


def decode_relationship_fixed(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Relationship operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    rel_var = read_int16_le(data, 0)
    mode = read_byte(data, 2)
    local = read_int16_le(data, 3)
    flags = read_byte(data, 5)
    
    return RelationshipOperand(rel_var, mode, local, flags)


def decode_set_balloon_headline_fixed(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Set Balloon Headline operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    index = read_byte(data, 0)
    group = read_byte(data, 1)
    duration = read_uint16_le(data, 2)
    balloon_id = read_uint16_le(data, 4)
    
    return SetBalloonHeadlineOperand(index, group, duration, balloon_id)


def decode_burn(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Burn operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    burn_type = read_byte(data, 0)
    flags = read_byte(data, 1)
    burn_busy_objects = (flags & 0x01) != 0
    
    return BurnOperand(burn_type, burn_busy_objects)


def decode_dialog(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Dialog operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    icon = read_byte(data, 0)
    message_string_id = read_uint16_le(data, 1)
    string_table = read_byte(data, 3)
    duration = read_uint16_le(data, 4)
    
    return DialogOperand(icon, message_string_id, string_table, duration)


def decode_find_location_for(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Find Location For operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    mode = read_byte(data, 0)
    local = read_int16_le(data, 1)
    flags = read_byte(data, 3)
    radius = read_byte(data, 4)
    min_proximity = read_byte(data, 5)
    max_proximity = read_byte(data, 6)
    
    return FindLocationForOperand(mode, local, flags, radius, min_proximity, max_proximity)


def decode_idle_for_input(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Idle For Input operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    stack_var = read_int16_le(data, 0)
    flags = read_byte(data, 2)
    allow_push = (flags & 0x01) != 0
    
    return IdleForInputOperand(stack_var, allow_push)


def decode_inventory_operations(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Inventory Operations operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    guid = read_uint32_le(data, 0)
    mode = read_byte(data, 4)
    flags = read_byte(data, 5)
    fso_scope = VMVariableScope(read_byte(data, 6))
    fso_data = read_int16_le(data, 7)
    
    return InventoryOperationsOperand(guid, mode, fso_scope, fso_data, 
                                       VMVariableScope.TEMPS, 0, flags)


def decode_invoke_plugin(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Invoke Plugin operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    person_local = read_byte(data, 0)
    object_local = read_byte(data, 1)
    event_local = read_byte(data, 2)
    flags = read_byte(data, 3)
    token = read_uint32_le(data, 4)
    
    return InvokePluginOperand(person_local, object_local, event_local, flags, token)


def decode_look_towards(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Look Towards operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    mode = read_byte(data, 0)
    return LookTowardsOperand(mode)


def decode_push_interaction_fixed(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Push Interaction operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    interaction = read_uint16_le(data, 0)
    object_location = read_byte(data, 2)
    priority = read_byte(data, 3)
    local = read_int16_le(data, 4)
    flags = read_byte(data, 6)
    
    return PushInteractionOperand(interaction, object_location, priority, local, flags)


def decode_remove_object_instance(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Remove Object Instance operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    target = read_uint16_le(data, 0)
    flags = read_byte(data, 2)
    
    return RemoveObjectInstanceOperand(target, flags)


def decode_run_functional_tree(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Run Functional Tree operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    function = read_uint16_le(data, 0)
    flags = read_byte(data, 2)
    
    return RunFunctionalTreeOperand(function, flags)


def decode_run_tree_by_name(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Run Tree By Name operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    string_table = read_uint16_le(data, 0)
    string_scope = VMVariableScope(read_byte(data, 2))
    string_id = read_uint16_le(data, 3)
    flags = read_byte(data, 5)
    
    return RunTreeByNameOperand(string_table, string_scope, string_id, flags)


def decode_set_to_next(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Set To Next operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    guid = read_uint32_le(data, 0)
    flags = read_byte(data, 4)
    target_owner = VMVariableScope(read_byte(data, 5))
    target_data = read_int16_le(data, 6)
    backwards = (flags & 0x01) != 0
    search_type = (flags >> 1) & 0x0F
    
    return SetToNextOperand(guid, flags, target_owner, target_data, search_type, backwards)


def decode_snap(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Snap operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    index = read_byte(data, 0)
    mode = read_byte(data, 1)
    flags = read_byte(data, 2)
    
    return SnapOperand(index, mode, flags)


def decode_special_effect(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Special Effect operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    timeout = read_uint16_le(data, 0)
    size = read_byte(data, 2)
    zoom = read_byte(data, 3)
    level = read_byte(data, 4)
    effect_type = read_byte(data, 5)
    
    return SpecialEffectOperand(timeout, size, zoom, level, effect_type)


def decode_stop_all_sounds(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Stop All Sounds operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    flags = read_byte(data, 0)
    return StopAllSoundsOperand(flags)


def decode_ts1_inventory_operations(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode TS1 Inventory Operations operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    mode = read_byte(data, 0)
    token_type = read_byte(data, 1)
    flags = read_byte(data, 2)
    local = read_int16_le(data, 3)
    guid_owner = VMVariableScope(read_byte(data, 5))
    guid_data = read_int16_le(data, 6)
    
    return TS1InventoryOperationsOperand(mode, token_type, flags, local, guid_owner, guid_data)


def decode_ts1_make_new_character(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode TS1 Make New Character operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    color_local = read_byte(data, 0)
    age_local = read_byte(data, 1)
    gender_local = read_byte(data, 2)
    skin_tone_local = read_byte(data, 3)
    
    return TS1MakeNewCharacterOperand(color_local, age_local, gender_local, skin_tone_local)


def decode_goto_routing_slot_fixed(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Goto Routing Slot operand (fixed)"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    slot_data = read_uint16_le(data, 0)
    slot_type = read_byte(data, 2)
    flags = read_byte(data, 3)
    
    return GotoRoutingSlotOperand(slot_data, slot_type, flags)


def decode_goto_relative_position_fixed(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Goto Relative Position operand (fixed)"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    x = read_int16_le(data, 0)
    y = read_int16_le(data, 2)
    direction = read_byte(data, 4)
    flags = read_byte(data, 5)
    
    return GotoRelativePositionOperand(0, x, y, direction, 0, flags)


def decode_refresh(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Refresh operand"""
    return None  # No operand data


def decode_stop(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Stop operand"""
    return None  # No operand data


def decode_breakpoint(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Break Point operand"""
    if len(data) < 4:
        return UnknownOperand(data)
    
    data_val = read_int16_le(data, 0)
    scope = VMVariableScope(read_uint16_le(data, 2))
    
    return BreakPointOperand(data_val, scope)


def decode_dialog_global_strings(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Dialog Global Strings operand"""
    return DialogGlobalStringsOperand()


def decode_dialog_private_strings(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Dialog Private Strings operand"""
    return DialogPrivateStringsOperand()


def decode_dialog_semiglobal_strings(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Dialog Semi-Global Strings operand"""
    return DialogSemiGlobalStringsOperand()


def decode_find_best_action(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Find Best Action operand"""
    return FindBestActionOperand()


def decode_find_best_object_for_function(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Find Best Object For Function operand"""
    return FindBestObjectForFunctionOperand()


def decode_generic_ts1_call(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Generic TS1 Call operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    call = read_byte(data, 0)
    
    return GenericTS1CallOperand(call)


def decode_generic_tso_call(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Generic TSO Call operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    call = read_byte(data, 0)
    
    return GenericTSOCallOperand(call)


def decode_get_terrain_info(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Get Terrain Info operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    mode = read_byte(data, 0)
    unknown1 = read_byte(data, 1)
    flags = read_byte(data, 2)
    unknown = data[3:8]
    
    return GetTerrainInfoOperand(mode, unknown1, flags, unknown)


def decode_gosub_found_action(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Gosub Found Action operand"""
    return GosubFoundActionOperand()


def decode_grab(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Grab operand (empty)"""
    return GrabOperand()


def decode_notify_out_of_idle(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Notify Out Of Idle operand"""
    return NotifyOutOfIdleOperand()


def decode_online_jobs_call(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Online Jobs Call operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    call = read_byte(data, 0)
    
    return OnlineJobsCallOperand(call)


def decode_reach(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Reach operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    mode = read_uint16_le(data, 0)
    grab_or_drop = read_uint16_le(data, 2)
    slot_param = read_uint16_le(data, 4)
    
    return ReachOperand(mode, grab_or_drop, slot_param)


def decode_syslog(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Sys Log operand (empty)"""
    return SysLogOperand()


def decode_test_sim_interacting_with(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Test Sim Interacting With operand (empty)"""
    return TestSimInteractingWithOperand()


def decode_transfer_funds(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode Transfer Funds operand"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    old_amount_owner = read_byte(data, 0)
    amount_owner = VMVariableScope(read_byte(data, 1))
    amount_data = read_uint16_le(data, 2)
    flags = read_byte(data, 4)
    # byte 5 is reserved/padding
    expense_type = read_byte(data, 6)
    transfer_type = read_byte(data, 7)
    
    return TransferFundsOperand(old_amount_owner, amount_owner, amount_data, flags, expense_type, transfer_type)


def decode_ts1_budget(data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode TS1 Budget operand (same format as TransferFunds)"""
    if len(data) < 8:
        return UnknownOperand(data)
    
    old_amount_owner = read_byte(data, 0)
    amount_owner = VMVariableScope(read_byte(data, 1))
    amount_data = read_uint16_le(data, 2)
    flags = read_byte(data, 4)
    expense_type = read_byte(data, 6)
    transfer_type = read_byte(data, 7)
    
    return TS1BudgetOperand(old_amount_owner, amount_owner, amount_data, flags, expense_type, transfer_type)


# ============================================================================
# Decoder Factory
# ============================================================================

DECODER_REGISTRY = {
    # Variable primitives
    0: decode_push_variable,
    1: decode_compare,
    2: decode_test_object_type,  # Updated to fixed version
    3: decode_test_sim_description,
    4: decode_test_actor_type,
    5: decode_test_relationship,
    6: decode_animate_sim,
    7: decode_create_object_instance,
    8: decode_drop,
    9: decode_drop_onto,
    10: decode_grab,
    
    # Math & navigation
    11: decode_get_distance_to,
    12: decode_play_sound,
    13: decode_goto_routing_slot_fixed,  # Updated to fixed version
    14: decode_goto_relative_position_fixed,  # Updated to fixed version
    15: decode_find_best_object,
    16: decode_find_location_for,  # Now implemented
    17: decode_find_best_action,
    18: decode_run_subroutine,
    19: decode_push_interaction_fixed,  # Updated to fixed version
    20: decode_get_direction_to_fixed,  # Updated to fixed version
    21: decode_reach,  # NEW
    
    # String & dialog
    33: decode_show_string,
    34: decode_set_balloon_headline_fixed,  # Updated to fixed version
    35: decode_dialog,  # Updated
    36: decode_dialog_global_strings,  # NEW
    37: decode_dialog_private_strings,  # NEW
    38: decode_dialog_semiglobal_strings,  # NEW
    
    # Extended
    40: decode_transfer_funds,
    41: decode_generic_ts1_call,  # NEW
    42: decode_generic_tso_call,  # NEW
    44: decode_animate_sim_extended,
    45: decode_change_suit_or_accessory,
    46: decode_get_terrain_info,  # NEW
    47: decode_gosub_found_action,  # NEW
    50: decode_random_number,
    51: decode_online_jobs_call,  # NEW
    
    # Additional operands
    # Note: FindBestObjectForFunction, NotifyOutOfIdle, SysLog, TestSimInteractingWith
    # do not appear to have standard opcode assignments in FreeSO
    
    # System
    252: decode_breakpoint,
    253: decode_sleep,
    254: decode_refresh,
    255: decode_stop,
}



def decode_operand(opcode: int, data: bytes) -> Optional[VMPrimitiveOperand]:
    """Decode operand based on opcode"""
    decoder = DECODER_REGISTRY.get(opcode)
    
    if decoder:
        return decoder(data)
    
    # Unknown operand - return raw bytes
    return UnknownOperand(data)
