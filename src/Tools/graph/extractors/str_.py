"""
STR# Reference Extractor

STR# (String Table) chunks are leaf nodes in the dependency graph.
They don't reference any other chunks, only get referenced by:
  - OBJD (catalog_strings_id, body_string_id)
  - TTAB (via TTAs indexing)
  - BHAV (via opcode 2 with BCON - handled by BCON extractor)

This extractor is a pass-through that returns no references,
as STR# chunks have no outbound dependencies.
"""

from typing import List, Optional

from ..core import Reference, ResourceNode
from .base import ReferenceExtractor
from .registry import ExtractorRegistry


@ExtractorRegistry.register("STR#")
class STRExtractor(ReferenceExtractor):
    """
    Extract references from STR# (String Table) chunks.
    
    STR# chunks are leaf nodes - they don't reference other chunks.
    They are referenced BY other chunks (OBJD, TTAB, BHAV).
    Therefore, this extractor returns no outbound references.
    
    Inbound references to STR# are handled by:
    - OBJD extractor (catalog text, body text)
    - TTAB extractor (via TTAs menu text)
    - BCON extractor (via BHAV opcode 2)
    """
    
    @property
    def chunk_type(self) -> str:
        return "STR#"
    
    def extract(self, str_chunk: Optional[object], node: ResourceNode) -> List[Reference]:
        """
        Extract references from STR# chunk.
        
        Since STR# chunks are leaf nodes with no outbound references,
        this always returns an empty list.
        """
        return []
