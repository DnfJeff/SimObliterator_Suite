"""
HOUS Chunk - House/Lot Data
Port of FreeSO's tso.files/Formats/IFF/Chunks/HOUS.cs

Contains house/lot metadata including version, camera direction, GUID, and roof name.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('HOUS')
@dataclass
class HOUS(IffChunk):
    """
    House/lot data chunk.
    Contains metadata about a house/lot including camera orientation and roof style.
    """
    version: int = 0
    unknown_flag: int = 0
    unknown_one: int = 0
    unknown_number: int = 0
    unknown_negative: int = 0
    camera_dir: int = 0       # Camera direction (short)
    unknown_one2: int = 0     # (short)
    unknown_flag2: int = 0    # (short)
    guid: int = 0             # House GUID (uint)
    roof_name: str = ""       # Roof style name
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read HOUS chunk."""
        zero = stream.read_int32()
        self.version = stream.read_int32()
        magic = stream.read_cstring(4)  # "SUOH" (HOUS backwards)
        self.unknown_flag = stream.read_int32()
        self.unknown_one = stream.read_int32()
        self.unknown_number = stream.read_int32()
        self.unknown_negative = stream.read_int32()
        self.camera_dir = stream.read_int16()
        self.unknown_one2 = stream.read_int16()
        self.unknown_flag2 = stream.read_int16()
        self.guid = stream.read_uint32()
        self.roof_name = stream.read_null_terminated_string()
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write HOUS chunk."""
        stream.write_int32(0)
        stream.write_int32(self.version)
        stream.write_cstring("SUOH", 4)
        stream.write_int32(self.unknown_flag)
        stream.write_int32(self.unknown_one)
        stream.write_int32(self.unknown_number)
        stream.write_int32(self.unknown_negative)
        stream.write_int16(self.camera_dir)
        stream.write_int16(self.unknown_one2)
        stream.write_int16(self.unknown_flag2)
        stream.write_uint32(self.guid)
        stream.write_null_terminated_string(self.roof_name)
        return True
