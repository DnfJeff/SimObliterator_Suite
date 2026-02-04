"""
FAMs Chunk - Family Strings
Port of FreeSO's tso.files/Formats/IFF/Chunks/FAMs.cs

Duplicate of STR chunk, used for family-related strings.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .str_ import STR
from ..base import register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer


@register_chunk('FAMs')
@dataclass
class FAMs(STR):
    """
    Family strings - exact duplicate of STR format.
    Used for family-related text in neighborhoods.
    """
    # No difference from STR
    pass
