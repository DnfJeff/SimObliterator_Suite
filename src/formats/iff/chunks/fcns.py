"""
FCNS Chunk - Simulator Constants
Port of FreeSO's tso.files/Formats/IFF/Chunks/FCNS.cs

Contains named float constants used by the simulator.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

from .str_ import STR, STRItem, STRLanguageSet
from ..base import register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@dataclass
class FCNSConstant:
    """A named float constant."""
    name: str = ""
    value: float = 0.0
    description: str = ""


@register_chunk('FCNS')
@dataclass
class FCNS(STR):
    """
    Simulator constants chunk.
    Contains named float constants with descriptions.
    Inherits from STR but has custom read format.
    """
    constants: List[FCNSConstant] = field(default_factory=list)
    fcns_version: int = 0
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read FCNS chunk with custom format."""
        zero = stream.read_int32()
        self.fcns_version = stream.read_int32()  # 2 in TSO
        magic = stream.read_cstring(4)  # "NSCF"
        count = stream.read_int32()
        
        self.constants = []
        
        # Also populate STR format for compatibility
        self.language_sets = [STRLanguageSet() for _ in range(20)]
        self.language_sets[0].strings = []
        
        for i in range(count):
            const = FCNSConstant()
            
            if self.fcns_version == 2:
                const.name = stream.read_variable_length_pascal_string()
                const.value = stream.read_float()
                const.description = stream.read_variable_length_pascal_string()
            else:
                const.name = stream.read_null_terminated_string()
                if len(const.name) % 2 == 0:
                    stream.read_byte()  # Padding to 2-byte align
                const.value = stream.read_float()
                const.description = stream.read_null_terminated_string()
                if len(const.description) % 2 == 0:
                    stream.read_byte()  # Padding
            
            self.constants.append(const)
            
            # Store in STR format for compatibility
            item = STRItem()
            item.value = f"{const.name}: {const.value}"
            item.comment = const.description
            self.language_sets[0].strings.append(item)
    
    def write(self, iff: 'IffFile', io: 'IoWriter') -> bool:
        """Write FCNS chunk to stream."""
        io.write_int32(0)  # Zero padding
        io.write_int32(self.fcns_version)
        io.write_bytes(b'NSCF')  # Magic
        io.write_int32(len(self.constants))
        
        for const in self.constants:
            if self.fcns_version == 2:
                io.write_variable_length_pascal_string(const.name)
                io.write_float(const.value)
                io.write_variable_length_pascal_string(const.description)
            else:
                io.write_null_terminated_string(const.name)
                if len(const.name) % 2 == 0:
                    io.write_byte(0)  # Padding to 2-byte align
                io.write_float(const.value)
                io.write_null_terminated_string(const.description)
                if len(const.description) % 2 == 0:
                    io.write_byte(0)  # Padding
        
        return True
    
    def get_constant(self, name: str) -> float:
        """Get a constant value by name."""
        for const in self.constants:
            if const.name == name:
                return const.value
        return 0.0
    
    def __len__(self) -> int:
        return len(self.constants)
