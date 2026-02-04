"""
TTAs Chunk - TTAB String Labels
Port of FreeSO's tso.files/Formats/IFF/Chunks/TTAs.cs

TTAs is a duplicate of STR, used for pie menu strings.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .str_ import STR
from ..base import register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer


@register_chunk('TTAs')
@dataclass
class TTAs(STR):
    """
    TTAB string labels - exact duplicate of STR format.
    Contains the pie menu text for TTAB interactions.
    Matches TTAB chunk with same resource ID.
    """
    # No difference from STR - just a different chunk type identifier
    pass
