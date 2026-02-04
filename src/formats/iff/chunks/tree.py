"""TREE chunk - Behavior tree visual layout/connections for IDE."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Optional
from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


class TREEBoxType(IntEnum):
    """Types of boxes in a TREE."""
    Primitive = 0
    True_ = 1
    False_ = 2
    Comment = 3
    Label = 4
    Goto = 5  # No comment size, pointer goes to Label


@dataclass
class TREEBox:
    """A box entry in a TREE chunk representing a node in behavior tree layout."""
    parent: Optional['TREE'] = None
    internal_id: int = -1
    position_invalid: bool = False  # Forces regeneration of position
    
    # Data fields
    box_type: TREEBoxType = TREEBoxType.Primitive
    unknown: int = 0
    width: int = 0
    height: int = 0
    x: int = 0
    y: int = 0
    comment_size: int = 0x10
    true_pointer: int = -1
    special: int = 0  # 0 or -1
    false_pointer: int = -1
    comment: str = ""
    trailing_zero: int = 0
    
    @property
    def true_id(self) -> int:
        """Get the true ID for arrow connections based on box type."""
        if self.box_type == TREEBoxType.Primitive:
            return self.internal_id & 0xFF
        elif self.box_type == TREEBoxType.Goto:
            return self._label_true_id(set())
        elif self.box_type == TREEBoxType.Label:
            return 253  # Arrows cannot point to a label
        elif self.box_type == TREEBoxType.True_:
            return 254
        elif self.box_type == TREEBoxType.False_:
            return 255
        return 253
    
    def _label_true_id(self, visited: set) -> int:
        """Follow goto chain to find actual target."""
        if self.box_type != TREEBoxType.Goto:
            return self.true_id
        if self.internal_id in visited:
            return 253  # Error - circular reference
        visited.add(self.internal_id)
        
        if self.parent is None:
            return 253
        target_box = self.parent.get_box(self.true_pointer)
        if target_box is None:
            return 253
        next_box = self.parent.get_box(target_box.true_pointer)
        if next_box is None:
            return 253
        return next_box._label_true_id(visited)
    
    def read(self, io: IoBuffer, version: int) -> None:
        """Read box data from stream."""
        self.box_type = TREEBoxType(io.read_uint16())
        self.unknown = io.read_uint16()
        self.width = io.read_int16()
        self.height = io.read_int16()
        self.x = io.read_int16()
        self.y = io.read_int16()
        self.comment_size = io.read_int16()
        self.true_pointer = io.read_int16()
        self.special = io.read_int16()
        self.false_pointer = io.read_int32()
        self.comment = io.read_null_terminated_string()
        
        # Padding to 2-byte align
        if len(self.comment) % 2 == 0:
            io.read_byte()
        
        if version > 0:
            self.trailing_zero = io.read_int32()
    
    def write(self, io: IoWriter) -> None:
        """Write box data to stream."""
        io.write_uint16(self.box_type)
        io.write_uint16(self.unknown)
        io.write_int16(self.width)
        io.write_int16(self.height)
        io.write_int16(self.x)
        io.write_int16(self.y)
        io.write_int16(self.comment_size)
        io.write_int16(self.true_pointer)
        io.write_int16(self.special)
        io.write_int32(self.false_pointer)
        io.write_c_string(self.comment)
        
        # Padding to 2-byte align
        if len(self.comment) % 2 == 0:
            io.write_byte(0xCD)
        
        io.write_int32(self.trailing_zero)
    
    def __repr__(self) -> str:
        false_str = "" if self.false_pointer == -1 else f"/{self.false_pointer}"
        return f"{self.box_type.name} ({self.true_pointer}{false_str}): {self.comment}"


@register_chunk('TREE')
@dataclass
class TREE(IffChunk):
    """Behavior tree layout chunk - stores visual representation for IDE.
    
    TREE chunks are paired with BHAV chunks (same chunk ID) and store:
    - Visual positions of instruction boxes
    - Connection routing between nodes
    - Comments and labels for the visual tree
    - True/False endpoint markers
    """
    entries: list[TREEBox] = field(default_factory=list)
    tree_version: int = 0  # Runtime tracking
    
    @property
    def primitive_count(self) -> int:
        """Count of primitive boxes (comes before other box types)."""
        for i in range(len(self.entries) - 1, -1, -1):
            if self.entries[i].box_type == TREEBoxType.Primitive:
                return i + 1
        return 0
    
    def get_box(self, pointer: int) -> Optional[TREEBox]:
        """Get box by pointer index."""
        if pointer < 0 or pointer >= len(self.entries):
            return None
        return self.entries[pointer]
    
    def get_true_id(self, box_id: int) -> int:
        """Get the true ID for a box pointer."""
        box = self.get_box(box_id)
        return box.true_id if box else 253
    
    def apply_pointer_delta(self, delta: int, after: int) -> None:
        """Shift all pointers >= 'after' by delta amount."""
        for box in self.entries:
            if box.internal_id >= after:
                box.internal_id += delta
            if box.true_pointer >= after:
                box.true_pointer += delta
            if box.false_pointer >= after:
                box.false_pointer += delta
    
    def delete_box(self, box: TREEBox) -> None:
        """Remove a box and update all pointers."""
        box_id = box.internal_id
        for other in self.entries:
            if other.true_pointer == box_id:
                other.true_pointer = -1
            if other.false_pointer == box_id:
                other.false_pointer = -1
        self.entries.remove(box)
        self.apply_pointer_delta(-1, box_id)
    
    def insert_primitive_box(self, box: TREEBox) -> None:
        """Insert a primitive box at end of primitives section."""
        prim_end = self.primitive_count
        self.apply_pointer_delta(1, prim_end)
        box.internal_id = prim_end
        box.parent = self
        self.entries.insert(prim_end, box)
    
    def make_new_primitive_box(self, box_type: TREEBoxType) -> TREEBox:
        """Create and insert a new primitive box."""
        prim_end = self.primitive_count
        self.apply_pointer_delta(1, prim_end)
        
        box = TREEBox(
            parent=self,
            internal_id=prim_end,
            position_invalid=True,
            box_type=box_type
        )
        self.entries.insert(prim_end, box)
        return box
    
    def make_new_special_box(self, box_type: TREEBoxType) -> TREEBox:
        """Create and append a new special box (True/False/Comment/etc)."""
        box = TREEBox(
            parent=self,
            internal_id=len(self.entries),
            position_invalid=True,
            box_type=box_type
        )
        self.entries.append(box)
        return box
    
    def _get_correct_box(self, real_id: int) -> int:
        """Convert BHAV pointer to TREE box pointer, creating endpoints if needed."""
        if real_id == 255:
            # Create false endpoint
            return self.make_new_special_box(TREEBoxType.False_).internal_id
        elif real_id == 254:
            # Create true endpoint
            return self.make_new_special_box(TREEBoxType.True_).internal_id
        elif real_id == 253:
            return -1
        return real_id
    
    def correct_connections(self, bhav) -> None:
        """Synchronize TREE with BHAV instructions."""
        real_prim_count = len(bhav.instructions)
        tree_prim_count = self.primitive_count
        
        self.apply_pointer_delta(real_prim_count - tree_prim_count, tree_prim_count)
        
        if real_prim_count > tree_prim_count:
            # Add new tree boxes
            for i in range(tree_prim_count, real_prim_count):
                box = TREEBox(
                    parent=self,
                    internal_id=i,
                    position_invalid=True,
                    box_type=TREEBoxType.Primitive
                )
                self.entries.insert(i, box)
        elif tree_prim_count > real_prim_count:
            # Remove excess tree boxes
            for i in range(tree_prim_count, real_prim_count, -1):
                self.entries.pop(i - 1)
        
        # Sync connections for each primitive
        for i in range(real_prim_count):
            prim = bhav.instructions[i]
            box = self.entries[i]
            
            if prim.true_target != self.get_true_id(box.true_pointer):
                box.true_pointer = self._get_correct_box(prim.true_target)
            if prim.false_target != self.get_true_id(box.false_pointer):
                box.false_pointer = self._get_correct_box(prim.false_target)
    
    @classmethod
    def generate_empty(cls, bhav) -> 'TREE':
        """Generate an empty TREE for a BHAV."""
        result = cls()
        result.chunk_label = ""
        result.chunk_id = bhav.chunk_id
        result.chunk_type = "TREE"
        result.correct_connections(bhav)
        return result
    
    def read(self, iff: 'IffFile', stream: IoBuffer) -> None:
        """Read TREE chunk from stream."""
        zero = stream.read_int32()
        version = stream.read_int32()
        if version > 1:
            raise ValueError(f"Unexpected TREE version: {version}")
        
        magic = stream.read_c_string(4)
        if magic != "EERT":
            raise ValueError(f"Magic number should be 'EERT', got {magic}")
        
        entry_count = stream.read_int32()
        self.entries = []
        
        for i in range(entry_count):
            box = TREEBox(parent=self)
            box.read(stream, version)
            box.internal_id = i
            self.entries.append(box)
    
    def write(self, iff: 'IffFile', stream: IoWriter) -> bool:
        """Write TREE chunk to stream."""
        stream.write_int32(0)
        stream.write_int32(1)  # Version
        stream.write_c_string("EERT", 4)
        stream.write_int32(len(self.entries))
        
        for entry in self.entries:
            entry.write(stream)
        
        return True
