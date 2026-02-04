"""OBJM chunk - Object Manager, stores all object instances in a house file."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from typing import TYPE_CHECKING, Optional, Callable, Any
from ..base import IffChunk, register_chunk
from .field_encode import IffFieldEncode

try:
    from ....utils.binary import IoBuffer, ByteOrder
except ImportError:
    from utils.binary import IoBuffer, ByteOrder

if TYPE_CHECKING:
    from ..iff_file import IffFile
    try:
        from ....utils.binary import IoWriter
    except ImportError:
        from utils.binary import IoWriter
    from .objd import OBJD
    from .objt import OBJTEntry


class OBJMInteractionFlags(IntFlag):
    """Flags for object interactions."""
    AutoFirst = 1
    PushHeadContinuation = 2
    UserInitiated = 4  # Not autonomous
    CanBeAuto = 8  # Check tree succeeds with param 0 == 1
    Unknown16 = 16  # Something to do with interaction push
    Completed = 32
    CarryNameOver = 64
    Unknown128 = 128  # Something to do with interaction push
    UserInterrupted = 256  # When interaction has X over it


class OBJMRoutingState(IntEnum):
    """Routing states for person objects."""
    NONE = 0
    Stopped = 3
    Turning = 4
    Accelerating = 6
    Walking = 9


@dataclass
class OBJMMultitile:
    """Full tile offsets of a multitile part within a group."""
    # Relative tile offset to lead tile in world space
    offset_x: int = 0
    offset_y: int = 0
    offset_level: int = 0
    
    # Absolute tile position in group space (always positive)
    group_x: int = 0
    group_y: int = 0
    group_level: int = 0
    
    # If 0, this object is the lead
    multitile_parent_id: int = 0
    
    @classmethod
    def from_field_encode(cls, iop: IffFieldEncode) -> 'OBJMMultitile':
        return cls(
            offset_x=iop.read_int32(),
            offset_y=iop.read_int32(),
            offset_level=iop.read_int32(),
            group_x=iop.read_int32(),
            group_y=iop.read_int32(),
            group_level=iop.read_int32(),
            multitile_parent_id=iop.read_int16()
        )


@dataclass
class OBJMFootprint:
    """Object footprint bounds."""
    min_y: int = 0
    min_x: int = 0
    max_y: int = 0
    max_x: int = 0
    
    @classmethod
    def from_field_encode(cls, iop: IffFieldEncode) -> 'OBJMFootprint':
        return cls(
            min_y=iop.read_int32(),
            min_x=iop.read_int32(),
            max_y=iop.read_int32(),
            max_x=iop.read_int32()
        )


@dataclass
class OBJMMotiveDelta:
    """Motive decay/change rate."""
    motive: int = 0
    tick_delta: float = 0.0  # 30 ticks per minute, 60 minutes per hour
    stop_at: float = 0.0
    
    @classmethod
    def from_field_encode(cls, iop: IffFieldEncode) -> 'OBJMMotiveDelta':
        return cls(
            motive=iop.read_int32(),
            tick_delta=iop.read_float(),
            stop_at=iop.read_float()
        )


@dataclass
class OBJMInteraction:
    """An interaction in an object's queue."""
    uid: int = 0
    caller_id: int = 0
    target_id: int = 0
    icon: int = 0
    tta_index: int = 0
    args: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    priority: int = 0
    action_tree_id: int = 0
    attenuation: float = 0.0
    flags: OBJMInteractionFlags = OBJMInteractionFlags(0)
    
    @classmethod
    def from_field_encode(cls, iop: IffFieldEncode) -> 'OBJMInteraction':
        unk_zero = iop.read_int32()
        if unk_zero != 0:
            raise ValueError("Expected zero at start of interaction")
        
        return cls(
            uid=iop.read_int32(),
            caller_id=iop.read_int16(),
            target_id=iop.read_int16(),
            icon=iop.read_int16(),
            tta_index=iop.read_int32(),
            args=[iop.read_int16() for _ in range(4)],
            priority=iop.read_int32(),
            action_tree_id=iop.read_int16(),
            attenuation=iop.read_float(),
            flags=OBJMInteractionFlags(iop.read_int32())
        )
    
    def is_valid(self) -> bool:
        return self.tta_index != -1


@dataclass
class OBJMAccessory:
    """Accessory attached to a person."""
    name: str = ""
    binding: str = ""
    
    @classmethod
    def from_field_encode(cls, iop: IffFieldEncode) -> 'OBJMAccessory':
        return cls(
            name=iop.read_string(False),
            binding=iop.read_string(False)
        )


@dataclass
class OBJMObjectUse:
    """Object currently in use by a sim."""
    target_id: int = 0
    stack_length: int = 0  # If stack falls below this, object no longer in use
    unknown2: int = 0  # 1 when call functional tree?
    
    @classmethod
    def from_field_encode(cls, iop: IffFieldEncode) -> 'OBJMObjectUse':
        return cls(
            target_id=iop.read_int16(),
            stack_length=iop.read_int32(),
            unknown2=iop.read_byte()
        )


@dataclass
class OBJMPerson:
    """Person-specific data for a sim object."""
    anim_event_count: int = 0  # Events fired during current animation
    engaged: int = 0  # 0 when routing/waiting, 1 otherwise
    
    # Appearance strings
    body: str = ""
    body_tex: str = ""
    unk1: str = ""
    unk2: str = ""
    left_hand: str = ""
    left_hand_tex: str = ""
    right_hand: str = ""
    right_hand_tex: str = ""
    head: str = ""
    head_tex: str = ""
    accessories: list[OBJMAccessory] = field(default_factory=list)
    
    # Animation state
    animation: str = ""
    carry_animation: str = ""
    base_animation: str = ""
    
    routing_state: OBJMRoutingState = OBJMRoutingState.NONE
    first_floats: list[float] = field(default_factory=list)
    motive_data_old: list[float] = field(default_factory=list)
    motive_data: list[float] = field(default_factory=list)
    person_data: list[int] = field(default_factory=list)
    routing_frame_count: int = 0
    
    active_interaction: Optional[OBJMInteraction] = None
    last_interaction: Optional[OBJMInteraction] = None
    interaction_queue: list[OBJMInteraction] = field(default_factory=list)
    object_uses: list[OBJMObjectUse] = field(default_factory=list)
    motive_deltas: list[OBJMMotiveDelta] = field(default_factory=list)
    
    @classmethod
    def from_field_encode(cls, version: int, iop: IffFieldEncode) -> 'OBJMPerson':
        person = cls()
        person.anim_event_count = iop.read_int32()
        person.engaged = iop.read_int32()
        
        person.body = iop.read_string(False)
        person.body_tex = iop.read_string(False)
        person.unk1 = iop.read_string(False)
        person.unk2 = iop.read_string(False)
        person.left_hand = iop.read_string(False)
        person.left_hand_tex = iop.read_string(False)
        person.right_hand = iop.read_string(False)
        person.right_hand_tex = iop.read_string(False)
        person.head = iop.read_string(False)
        person.head_tex = iop.read_string(True)
        
        accessory_count = iop.read_int32()
        person.accessories = [OBJMAccessory.from_field_encode(iop) for _ in range(accessory_count)]
        
        person.animation = iop.read_string(False)
        person.carry_animation = iop.read_string(False)
        person.base_animation = iop.read_string(True)
        
        person.routing_state = OBJMRoutingState(iop.read_int32())
        person.first_floats = [iop.read_float() for _ in range(9)]
        person.motive_data_old = [iop.read_float() for _ in range(16)]
        person.motive_data = [iop.read_float() for _ in range(16)]
        
        # Data count varies by version
        data_count = 0x100 if version > 0x45 else 0x50
        person.person_data = [iop.read_int16() for _ in range(data_count)]
        
        person.routing_frame_count = iop.read_int32()
        
        person.active_interaction = OBJMInteraction.from_field_encode(iop)
        person.last_interaction = OBJMInteraction.from_field_encode(iop)
        
        queue_count = iop.read_int32()
        person.interaction_queue = [OBJMInteraction.from_field_encode(iop) for _ in range(queue_count)]
        
        use_count = iop.read_int32()
        person.object_uses = [OBJMObjectUse.from_field_encode(iop) for _ in range(use_count)]
        
        delta_count = iop.read_int32()
        person.motive_deltas = [OBJMMotiveDelta.from_field_encode(iop) for _ in range(delta_count)]
        
        return person


@dataclass
class OBJMSlot:
    """Object slot reference."""
    unknown: int = 0
    object_id: int = 0


@dataclass
class OBJMStackFrame:
    """A frame in the VM stack."""
    stack_object_id: int = 0
    tree_id: int = 0
    node_id: int = 0
    parameters: list[int] = field(default_factory=list)
    locals: list[int] = field(default_factory=list)
    primitive_state: int = 0
    code_owner_obj_type: int = 0
    
    @classmethod
    def from_field_encode(cls, iop: IffFieldEncode) -> 'OBJMStackFrame':
        stack_obj_id = iop.read_int16()
        tree_id = iop.read_int16()
        node_id = iop.read_int16()
        
        local_count = iop.read_byte()
        param_count = iop.read_byte()
        
        parameters = [iop.read_int16() for _ in range(param_count)]
        locals_ = [iop.read_int16() for _ in range(local_count)]
        
        primitive_state = iop.read_int32()
        code_owner = iop.read_int16()
        
        return cls(
            stack_object_id=stack_obj_id,
            tree_id=tree_id,
            node_id=node_id,
            parameters=parameters,
            locals=locals_,
            primitive_state=primitive_state,
            code_owner_obj_type=code_owner
        )


@dataclass
class OBJMRelationshipEntry:
    """Relationship data between objects."""
    is_present: int = 0
    target_id: int = 0
    values: list[int] = field(default_factory=list)
    
    @classmethod
    def from_field_encode(cls, iop: IffFieldEncode) -> 'OBJMRelationshipEntry':
        is_present = iop.read_int32()
        
        if is_present != 0:
            target_id = iop.read_int32()
            value_count = iop.read_int32()
            values = [iop.read_int32() for _ in range(value_count)]
            return cls(is_present=is_present, target_id=target_id, values=values)
        else:
            raise ValueError(f"Unexpected IsPresent value: {is_present}")


@dataclass
class OBJMResource:
    """Resource reference for object type lookup."""
    objd: Optional['OBJD'] = None
    objt: Optional['OBJTEntry'] = None


@dataclass
class OBJMInstance:
    """A single object instance in the house."""
    TEMP_COUNT = 8
    OBJECT_DATA_COUNT = 68
    EXTRA_DATA_COUNT = 5
    
    objd: Optional['OBJD'] = None
    objt: Optional['OBJTEntry'] = None
    
    footprint: OBJMFootprint = field(default_factory=OBJMFootprint)
    
    x: int = 0
    y: int = 0
    level: int = 0
    
    unknown_data: int = 0
    
    attributes: list[int] = field(default_factory=list)
    temp_registers: list[int] = field(default_factory=list)
    object_data: list[int] = field(default_factory=list)
    object_data_extra: list[int] = field(default_factory=list)
    
    stack_flags: int = 512
    stack: list[OBJMStackFrame] = field(default_factory=list)
    
    relationships: list[OBJMRelationshipEntry] = field(default_factory=list)
    
    # Linked list of objects on same tile
    linked_slot: OBJMSlot = field(default_factory=OBJMSlot)
    
    # Container slots
    slots: list[OBJMSlot] = field(default_factory=list)
    
    # Dynamic sprite flags (each flag stored as short)
    dynamic_sprite_flags: list[int] = field(default_factory=list)
    
    # Optional data based on object type
    multitile_data: Optional[OBJMMultitile] = None
    portal_data: Optional[list[float]] = None
    person_data: Optional[OBJMPerson] = None
    
    unknown_int: int = 0
    unhandled_data: str = ""
    
    @property
    def object_id(self) -> int:
        """Get object ID from object data array."""
        return self.object_data[11] if len(self.object_data) > 11 else 0
    
    @property
    def direction(self) -> int:
        """Get object direction."""
        return self.object_data[1] if len(self.object_data) > 1 else 0
    
    @property
    def parent_id(self) -> int:
        """Get parent object ID."""
        return self.object_data[26] if len(self.object_data) > 26 else 0
    
    @property
    def container_id(self) -> int:
        """Get container object ID."""
        return self.object_data[2] if len(self.object_data) > 2 else 0
    
    @property
    def container_slot(self) -> int:
        """Get container slot index."""
        return self.object_data[3] if len(self.object_data) > 3 else 0
    
    @classmethod
    def from_field_encode(
        cls, 
        version: int, 
        iop: IffFieldEncode, 
        skip_position: int,
        id_to_resource: Callable[[int], OBJMResource]
    ) -> 'OBJMInstance':
        """Read an object instance from field-encoded data."""
        instance = cls()
        
        instance.footprint = OBJMFootprint.from_field_encode(iop)
        
        instance.x = iop.read_int32()
        instance.y = iop.read_int32()
        instance.level = iop.read_int32()
        
        instance.unknown_data = iop.read_int16()
        
        attr_count = iop.read_int16()
        instance.attributes = [iop.read_int16() for _ in range(attr_count)]
        
        instance.temp_registers = [iop.read_int16() for _ in range(cls.TEMP_COUNT)]
        instance.object_data = [iop.read_int16() for _ in range(cls.OBJECT_DATA_COUNT)]
        instance.object_data_extra = [iop.read_int16() for _ in range(cls.EXTRA_DATA_COUNT)]
        
        # Lookup OBJD/OBJT from object data
        resources = id_to_resource(instance.object_data[11])
        instance.objd = resources.objd
        instance.objt = resources.objt
        
        stack_count = iop.read_int32()
        instance.stack_flags = iop.read_int32()
        
        instance.stack = [OBJMStackFrame.from_field_encode(iop) for _ in range(stack_count)]
        
        instance.relationships = []
        rel_flag = iop.read_int32()
        
        if rel_flag < 0:
            rel_count = iop.read_int32()
            instance.relationships = [OBJMRelationshipEntry.from_field_encode(iop) for _ in range(rel_count)]
        else:
            raise ValueError(f"Unknown relationship flag: {rel_flag}")
        
        slots_count = iop.read_int16()
        instance.slots = []
        instance.linked_slot = OBJMSlot()
        
        for i in range(slots_count):
            unk = iop.read_int16()
            obj_id = iop.read_int16()
            
            if i == 0:
                instance.linked_slot = OBJMSlot(unknown=unk, object_id=obj_id)
            else:
                instance.slots.append(OBJMSlot(unknown=unk, object_id=obj_id))
        
        sprite_flag_count = iop.read_int16()
        instance.dynamic_sprite_flags = [iop.read_int16() for _ in range(sprite_flag_count)]
        
        # Multitile data if applicable
        instance.multitile_data = None
        is_multitile = False
        if instance.objd is not None:
            is_multitile = instance.objd.is_multi_tile
        elif instance.objt is not None:
            is_multitile = instance.objt.name == ""
        
        if is_multitile:
            instance.multitile_data = OBJMMultitile.from_field_encode(iop)
        
        # Portal data if portal type
        instance.portal_data = None
        if instance.objt is not None and instance.objt.objd_type.name == 'Portal':
            portal_count = iop.read_int32()
            instance.portal_data = [iop.read_float() for _ in range(portal_count)]
        
        # Person data if person type
        instance.person_data = None
        if instance.objt is not None and instance.objt.objd_type.name == 'Person':
            instance.person_data = OBJMPerson.from_field_encode(version, iop)
            instance.unknown_int = iop.read_int32()
        else:
            instance.unknown_int = iop.read_int32()
        
        # Store any remaining unread data for debugging
        instance.unhandled_data = iop.bit_debug_til(skip_position)
        
        return instance


@dataclass
class MappedObject:
    """A mapped object with convenience properties."""
    instance: OBJMInstance = field(default_factory=OBJMInstance)
    
    # From OBJT
    name: str = ""
    guid: int = 0
    
    # From ARRY (populated externally)
    arry_x: int = 0
    arry_y: int = 0
    arry_level: int = 0
    
    @property
    def object_id(self) -> int:
        return self.instance.object_id
    
    @property
    def direction(self) -> int:
        return self.instance.direction
    
    @property
    def parent_id(self) -> int:
        return self.instance.parent_id
    
    @property
    def container_id(self) -> int:
        return self.instance.container_id
    
    @property
    def container_slot(self) -> int:
        return self.instance.container_slot
    
    def __repr__(self) -> str:
        return self.name or "(unreferenced)"


@dataclass
class CompressedData:
    """Compressed object instance data."""
    offset: int = 0
    data: bytes = b""


@register_chunk('OBJM')
@register_chunk('ObjM')  # House files use this variant
@dataclass
class OBJM(IffChunk):
    """Object Manager chunk - stores all object instances in a house file.
    
    This is the most complex chunk type, containing:
    - Compressed object instance data using IffFieldEncode
    - Object ID to type mappings
    - Full object state including attributes, stack, relationships
    - Person-specific data for sims
    - Multitile and portal data for special objects
    """
    version: int = 0
    id_to_objt: dict[int, int] = field(default_factory=dict)
    _compressed_instances: list[CompressedData] = field(default_factory=list)
    object_data: dict[int, MappedObject] = field(default_factory=dict)
    
    def read(self, iff: 'IffFile', stream: IoBuffer) -> None:
        """Read OBJM chunk from stream."""
        stream.read_uint32()  # Padding
        self.version = stream.read_uint32()
        
        magic = stream.read_uint32()
        if magic != 0x4f626a4d:  # "MjbO" in little-endian
            raise ValueError("Invalid OBJM magic number")
        
        # Offsets are from here
        offset_base = stream.position
        
        compression_code = stream.read_byte()
        if compression_code != 1:
            raise ValueError(f"Expected OBJM to be compressed, got compression code {compression_code}")
        
        iop = IffFieldEncode(stream)
        
        # Read ID to OBJT type mapping table
        self.id_to_objt = {}
        while stream.has_more:
            obj_id = iop.read_uint16()
            if obj_id == 0:
                break
            obj_type = iop.read_uint16()
            self.id_to_objt[obj_id] = obj_type
        
        iop.interrupt()
        
        # Read compressed object instance data
        obj_count = len(self.id_to_objt)
        self._compressed_instances = []
        
        for i in range(obj_count):
            skip_offset = stream.read_int32()
            skip_position = offset_base + skip_offset
            offset = stream.position - offset_base
            
            data_length = skip_position - stream.position
            data = stream.read_bytes(data_length)
            
            self._compressed_instances.append(CompressedData(offset=offset, data=data))
    
    def prepare(self, type_id_to_resource: Callable[[int], OBJMResource]) -> None:
        """Decompress and parse all object instances.
        
        Args:
            type_id_to_resource: Function that maps type ID to OBJMResource
        """
        self.object_data = {}
        
        def id_to_resource(obj_id: int) -> OBJMResource:
            type_id = self.id_to_objt.get(obj_id, 0)
            return type_id_to_resource(type_id)
        
        for instance_data in self._compressed_instances:
            io = IoBuffer.from_bytes(instance_data.data, ByteOrder.LITTLE_ENDIAN)
            iop = IffFieldEncode(io, (instance_data.offset & 1) == 1)
            
            obj = OBJMInstance.from_field_encode(
                self.version, 
                iop, 
                len(instance_data.data),
                id_to_resource
            )
            
            mapped = MappedObject(instance=obj)
            if obj.objt is not None:
                mapped.name = obj.objt.name
                mapped.guid = obj.objt.guid
            
            self.object_data[mapped.object_id] = mapped
    
    def write(self, iff: 'IffFile', stream: IoWriter) -> bool:
        """Write OBJM chunk to stream.
        
        Note: OBJM writing requires re-compression which is complex.
        This is a placeholder for read-only use cases.
        """
        # OBJM writing is complex due to field encoding compression
        # For now, raise an error to indicate this isn't fully implemented
        raise NotImplementedError("OBJM write not yet implemented - field encoding compression required")
