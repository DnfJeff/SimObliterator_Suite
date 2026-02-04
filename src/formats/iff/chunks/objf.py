"""
OBJf Chunk - Object Functions
Port of FreeSO's tso.files/Formats/IFF/Chunks/OBJf.cs

This chunk assigns BHAV subroutines to object events.
Events are defined in behavior.iff chunk 00F5.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@dataclass
class OBJfFunctionEntry:
    """A function entry mapping event to BHAV subroutines."""
    condition_function: int = 0  # BHAV ID for condition check (0 = no condition)
    action_function: int = 0     # BHAV ID for action (0 = no action)


@register_chunk('OBJf')
@dataclass
class OBJf(IffChunk):
    """
    Object functions chunk - maps object events to BHAV subroutines.
    Each entry has a condition function (check if action can run)
    and an action function (actually do the thing).
    """
    functions: List[OBJfFunctionEntry] = field(default_factory=list)
    version: int = 0
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read OBJf chunk from stream."""
        pad = stream.read_uint32()  # padding
        self.version = stream.read_uint32()
        magic = stream.read_cstring(4)  # "fJBO" backwards
        count = stream.read_uint32()
        
        self.functions = []
        for _ in range(count):
            entry = OBJfFunctionEntry()
            entry.condition_function = stream.read_uint16()
            entry.action_function = stream.read_uint16()
            self.functions.append(entry)
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write OBJf chunk to stream."""
        stream.write_uint32(0)  # padding
        stream.write_uint32(self.version)
        stream.write_cstring("fJBO", 4)  # magic
        stream.write_uint32(len(self.functions))
        
        for entry in self.functions:
            stream.write_uint16(entry.condition_function)
            stream.write_uint16(entry.action_function)
        
        return True
    
    def get_function(self, event_id: int) -> OBJfFunctionEntry:
        """Get function entry for an event ID."""
        if 0 <= event_id < len(self.functions):
            return self.functions[event_id]
        return OBJfFunctionEntry()
    
    def __len__(self) -> int:
        return len(self.functions)
    
    def __getitem__(self, index: int) -> OBJfFunctionEntry:
        return self.functions[index]
