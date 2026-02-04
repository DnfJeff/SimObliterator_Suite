"""
TPRP Chunk - BHAV Property Labels
Port of FreeSO's tso.files/Formats/IFF/Chunks/TPRP.cs

Provides human-readable labels for BHAV local variables and parameters.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('TPRP')
@dataclass
class TPRP(IffChunk):
    """
    BHAV property labels chunk - names for parameters and locals.
    Matches BHAV chunks with same resource ID.
    """
    param_names: List[str] = field(default_factory=list)
    local_names: List[str] = field(default_factory=list)
    param_flags: List[int] = field(default_factory=list)  # Flags per parameter
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read TPRP chunk from stream."""
        zero = stream.read_int32()
        version = stream.read_int32()
        magic = stream.read_cstring(4)  # "PRPT" or 4 null chars
        
        param_count = stream.read_int32()
        local_count = stream.read_int32()
        
        self.param_names = []
        self.local_names = []
        
        # Read parameter names
        for _ in range(param_count):
            if version == 5:
                name = stream.read_pascal_string()
            else:
                name = stream.read_null_terminated_string()
            self.param_names.append(name)
        
        # Read local variable names
        for _ in range(local_count):
            if version == 5:
                name = stream.read_pascal_string()
            else:
                name = stream.read_null_terminated_string()
            self.local_names.append(name)
        
        # Read parameter flags
        self.param_flags = []
        for _ in range(param_count):
            flag = stream.read_byte()
            self.param_flags.append(flag)
        
        # Additional version-specific data
        if version >= 3:
            _ = stream.read_int32()  # unknown
        if version >= 4:
            _ = stream.read_int32()  # unknown
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write TPRP chunk to stream."""
        stream.write_int32(0)  # zero
        stream.write_int32(5)  # version 5
        stream.write_cstring("PRPT", 4)
        
        stream.write_int32(len(self.param_names))
        stream.write_int32(len(self.local_names))
        
        for name in self.param_names:
            stream.write_pascal_string(name)
        
        for name in self.local_names:
            stream.write_pascal_string(name)
        
        # Write parameter flags
        for i in range(len(self.param_names)):
            flag = self.param_flags[i] if i < len(self.param_flags) else 0
            stream.write_byte(flag)
        
        # Version 5 extras
        stream.write_int32(0)
        stream.write_int32(0)
        
        return True
    
    def get_param_name(self, index: int) -> str:
        """Get parameter name by index."""
        if 0 <= index < len(self.param_names):
            return self.param_names[index]
        return f"param{index}"
    
    def get_local_name(self, index: int) -> str:
        """Get local variable name by index."""
        if 0 <= index < len(self.local_names):
            return self.local_names[index]
        return f"local{index}"
