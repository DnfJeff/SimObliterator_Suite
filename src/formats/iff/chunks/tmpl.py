"""
TMPL Chunk - Template Definition
Port of FreeSO's tso.files/Formats/IFF/Chunks/TMPL.cs

TMPL defines template data used for object templates and blueprints.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@register_chunk('TMPL')
@dataclass
class TMPL(IffChunk):
    """
    Template definition chunk - contains template blueprint data.
    
    Used in template objects and object blueprints. The exact structure
    varies depending on object type.
    """
    data: bytes = field(default_factory=bytes)
    template_version: int = 0
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read TMPL chunk."""
        # Try to read version if present
        try:
            pos = stream.position
            self.template_version = stream.read_uint32()
            # Store remaining data after version
            self.data = stream.read_bytes(stream.remaining())
        except Exception:
            # Fall back to reading all as data
            stream.position = pos
            self.data = stream.read_bytes(stream.remaining())
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write TMPL chunk."""
        if self.template_version != 0:
            stream.write_uint32(self.template_version)
        if self.data:
            stream.write_bytes(self.data)
        return True
