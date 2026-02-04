"""
BEHAVIOR TRIGGER EXTRACTOR
Extracts lifecycle bindings, entry points, and activation conditions.

This layer maps WHAT triggers WHEN:
- TTAB: User-initiated interactions (ACTION/GUARD)
- OBJf: Engine lifecycle hooks (ROLE startup, cleanup)
- Global functions: Autonomous behavior entry points
- State transitions: FLOW activation conditions
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from enum import Enum


class TriggerType(Enum):
    """How a BHAV gets triggered."""
    USER_INTERACTION = "user_interaction"      # TTAB action
    AVAILABILITY_CHECK = "availability_check"  # TTAB test
    LIFECYCLE_INIT = "lifecycle_init"          # OBJf init
    LIFECYCLE_MAIN = "lifecycle_main"          # OBJf main
    LIFECYCLE_CLEANUP = "lifecycle_cleanup"    # OBJf cleanup
    LIFECYCLE_LOAD = "lifecycle_load"          # OBJf load
    LIFECYCLE_RESET = "lifecycle_reset"        # OBJf reset
    AUTONOMOUS = "autonomous"                  # Idle/autonomous entry
    STATE_TRANSITION = "state_transition"      # Triggered by state change
    UNKNOWN = "unknown"


@dataclass
class BehaviorTrigger:
    """A single trigger binding for a BHAV."""
    bhav_id: int
    trigger_type: TriggerType
    source: str  # "TTAB#123", "OBJf.Init", "STATE:Hungry"
    context: str = ""  # Additional context (interaction name, etc.)
    priority: int = 0  # Execution priority if known


@dataclass
class TriggerMap:
    """Complete trigger mapping for an object."""
    object_name: str
    triggers: Dict[int, List[BehaviorTrigger]] = field(default_factory=dict)  # bhav_id → triggers
    
    # Lifecycle bindings (OBJf)
    init_function: Optional[int] = None
    main_function: Optional[int] = None
    cleanup_function: Optional[int] = None
    load_function: Optional[int] = None
    reset_function: Optional[int] = None
    
    # TTAB interaction count
    ttab_action_count: int = 0
    ttab_test_count: int = 0
    
    def add_trigger(self, bhav_id: int, trigger: BehaviorTrigger):
        """Add a trigger binding."""
        if bhav_id not in self.triggers:
            self.triggers[bhav_id] = []
        self.triggers[bhav_id].append(trigger)
    
    def get_trigger_types(self, bhav_id: int) -> Set[TriggerType]:
        """Get all trigger types for a BHAV."""
        if bhav_id not in self.triggers:
            return set()
        return {t.trigger_type for t in self.triggers[bhav_id]}
    
    def is_user_action(self, bhav_id: int) -> bool:
        """Is this BHAV a user-initiated action?"""
        return TriggerType.USER_INTERACTION in self.get_trigger_types(bhav_id)
    
    def is_guard(self, bhav_id: int) -> bool:
        """Is this BHAV an availability check?"""
        return TriggerType.AVAILABILITY_CHECK in self.get_trigger_types(bhav_id)
    
    def is_lifecycle(self, bhav_id: int) -> bool:
        """Is this BHAV triggered by engine lifecycle?"""
        types = self.get_trigger_types(bhav_id)
        return any(t in types for t in [
            TriggerType.LIFECYCLE_INIT,
            TriggerType.LIFECYCLE_MAIN,
            TriggerType.LIFECYCLE_CLEANUP,
            TriggerType.LIFECYCLE_LOAD,
            TriggerType.LIFECYCLE_RESET
        ])


class TriggerExtractor:
    """Extracts trigger/binding information from IFF chunks."""
    
    def __init__(self):
        self.trigger_maps: Dict[str, TriggerMap] = {}  # object_name → TriggerMap
    
    def extract(self, iff, object_name: str) -> TriggerMap:
        """Extract all trigger bindings from an IFF file."""
        trigger_map = TriggerMap(object_name=object_name)
        
        # Phase 1: TTAB interactions (user-initiated)
        self._extract_ttab_triggers(iff, trigger_map)
        
        # Phase 2: OBJf lifecycle hooks (engine-initiated)
        self._extract_objf_triggers(iff, trigger_map)
        
        # Phase 3: Global function tables (if present)
        self._extract_global_triggers(iff, trigger_map)
        
        self.trigger_maps[object_name] = trigger_map
        return trigger_map
    
    def _extract_ttab_triggers(self, iff, trigger_map: TriggerMap):
        """Extract TTAB interaction bindings."""
        for chunk in iff.chunks:
            if chunk.chunk_type != 'TTAB':
                continue
            
            if not hasattr(chunk, 'interactions'):
                continue
            
            for idx, interaction in enumerate(chunk.interactions):
                # Action function (the "do it" behavior)
                if interaction.action_function > 0:
                    trigger = BehaviorTrigger(
                        bhav_id=interaction.action_function,
                        trigger_type=TriggerType.USER_INTERACTION,
                        source=f"TTAB#{idx}",
                        context=f"Interaction slot {idx}",
                        priority=idx
                    )
                    trigger_map.add_trigger(interaction.action_function, trigger)
                    trigger_map.ttab_action_count += 1
                
                # Test function (the "can do it?" behavior)
                if interaction.test_function > 0:
                    trigger = BehaviorTrigger(
                        bhav_id=interaction.test_function,
                        trigger_type=TriggerType.AVAILABILITY_CHECK,
                        source=f"TTAB#{idx}.test",
                        context=f"Availability check for slot {idx}",
                        priority=idx
                    )
                    trigger_map.add_trigger(interaction.test_function, trigger)
                    trigger_map.ttab_test_count += 1
    
    def _extract_objf_triggers(self, iff, trigger_map: TriggerMap):
        """Extract OBJf (Object Functions) lifecycle bindings."""
        for chunk in iff.chunks:
            if chunk.chunk_type != 'OBJf':
                continue
            
            # OBJf has structured function entries (condition + action pairs)
            if hasattr(chunk, 'functions'):
                # OBJf maps event IDs to BHAV functions
                # Common lifecycle events (event IDs vary by game, these are typical):
                # 0 = Init, 1 = Main, 2 = Cleanup, 3 = Load, 4 = Reset
                lifecycle_events = {
                    0: (TriggerType.LIFECYCLE_INIT, "Init", "Object initialization"),
                    1: (TriggerType.LIFECYCLE_MAIN, "Main", "Main loop / autonomous behavior"),
                    2: (TriggerType.LIFECYCLE_CLEANUP, "Cleanup", "Object cleanup/disposal"),
                    3: (TriggerType.LIFECYCLE_LOAD, "Load", "Object loaded from save"),
                    4: (TriggerType.LIFECYCLE_RESET, "Reset", "Object reset"),
                }
                
                for event_id, entry in enumerate(chunk.functions):
                    if event_id not in lifecycle_events:
                        continue
                    
                    trigger_type, event_name, context = lifecycle_events[event_id]
                    
                    # Extract action function (primary lifecycle hook)
                    if entry.action_function > 0 and entry.action_function >= 0x1000:
                        bhav_id = entry.action_function
                        
                        trigger = BehaviorTrigger(
                            bhav_id=bhav_id,
                            trigger_type=trigger_type,
                            source=f"OBJf[{event_id}].action",
                            context=context
                        )
                        trigger_map.add_trigger(bhav_id, trigger)
                        
                        # Set specific lifecycle function pointers
                        if trigger_type == TriggerType.LIFECYCLE_INIT:
                            trigger_map.init_function = bhav_id
                        elif trigger_type == TriggerType.LIFECYCLE_MAIN:
                            trigger_map.main_function = bhav_id
                        elif trigger_type == TriggerType.LIFECYCLE_CLEANUP:
                            trigger_map.cleanup_function = bhav_id
                        elif trigger_type == TriggerType.LIFECYCLE_LOAD:
                            trigger_map.load_function = bhav_id
                        elif trigger_type == TriggerType.LIFECYCLE_RESET:
                            trigger_map.reset_function = bhav_id
    
    def _extract_global_triggers(self, iff, trigger_map: TriggerMap):
        """Extract global function table bindings (if present)."""
        # Global function tables define autonomous behaviors, idle loops, etc.
        # These are typically in GLOB chunks or similar
        for chunk in iff.chunks:
            if chunk.chunk_type == 'GLOB':
                # GLOB contains global function pointers
                # Parse structure if available
                if hasattr(chunk, 'data'):
                    # Simplified: look for BHAV IDs in data
                    import struct
                    data = chunk.data
                    
                    # Scan for valid BHAV IDs (0x1000-0xFFFF range)
                    for offset in range(0, len(data) - 1, 2):
                        try:
                            func_id = struct.unpack('<H', data[offset:offset+2])[0]
                            if 0x1000 <= func_id <= 0xFFFF:
                                # Potential autonomous/idle function
                                trigger = BehaviorTrigger(
                                    bhav_id=func_id,
                                    trigger_type=TriggerType.AUTONOMOUS,
                                    source=f"GLOB@0x{offset:04X}",
                                    context="Autonomous behavior entry"
                                )
                                trigger_map.add_trigger(func_id, trigger)
                        except:
                            continue
    
    def get_trigger_summary(self, object_name: str) -> Dict:
        """Get summary statistics for an object's triggers."""
        if object_name not in self.trigger_maps:
            return {}
        
        trigger_map = self.trigger_maps[object_name]
        
        return {
            'total_triggers': sum(len(t) for t in trigger_map.triggers.values()),
            'triggered_bhavs': len(trigger_map.triggers),
            'ttab_actions': trigger_map.ttab_action_count,
            'ttab_tests': trigger_map.ttab_test_count,
            'lifecycle_funcs': sum(1 for f in [
                trigger_map.init_function,
                trigger_map.main_function,
                trigger_map.cleanup_function,
                trigger_map.load_function,
                trigger_map.reset_function
            ] if f is not None),
            'init_function': trigger_map.init_function,
            'main_function': trigger_map.main_function
        }
