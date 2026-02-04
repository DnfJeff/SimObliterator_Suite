"""
FSOR Chunk - Floor Sort Reconstruction Parameters
Port of FreeSO's tso.files/Formats/IFF/Chunks/FSOR.cs

Metadata for an object's mesh reconstruction parameters.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


FSOR_CURRENT_VERSION = 1


@dataclass
class DGRPRCParams:
    """DGRP reconstruction parameters."""
    # These would normally contain mesh reconstruction settings
    # For now, store as raw data since we don't need full mesh support yet
    raw_data: bytes = field(default_factory=bytes)
    
    def read(self, stream: 'IoBuffer', version: int):
        """Read params from stream."""
        # Read remaining data as raw bytes for now
        # Full implementation would parse specific fields
        pos = stream.position
        stream.seek(0, 2)
        end = stream.position
        stream.seek(pos)
        if end > pos:
            self.raw_data = stream.read_bytes(end - pos)
    
    def write(self, stream: 'IoWriter'):
        """Write params to stream."""
        stream.write_bytes(self.raw_data)


@register_chunk('FSOR')
@dataclass
class FSOR(IffChunk):
    """
    Floor sort reconstruction parameters.
    Used for 3D mesh reconstruction metadata.
    """
    version: int = FSOR_CURRENT_VERSION
    params: DGRPRCParams = field(default_factory=DGRPRCParams)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read FSOR chunk."""
        self.version = stream.read_int32()
        self.params = DGRPRCParams()
        self.params.read(stream, self.version)
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write FSOR chunk."""
        stream.write_int32(self.version)
        self.params.write(stream)
        return True
