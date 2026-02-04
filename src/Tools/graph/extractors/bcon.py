"""
BCON Reference Extractor

BCON (Behavioral Constants) chunks are leaf nodes in the dependency graph.
They store integer constant values that BHAV code can reference.

BCON chunks don't reference any other chunks - they only get referenced by:
  - BHAV (via opcode 2 expression evaluation, requires operand parsing)
  - TRCN (labels and validation ranges, optional)

This extractor is a pass-through that returns no references,
as BCON chunks have no outbound dependencies.

Future enhancement: Parse BHAV opcode 2 operands to extract BCON→BCON references.
(This requires complex operand structure parsing and is deferred to post-Phase 2)
"""

from typing import List, Optional

from ..core import Reference, ResourceNode
from .base import ReferenceExtractor
from .registry import ExtractorRegistry


@ExtractorRegistry.register("BCON")
class BCONExtractor(ReferenceExtractor):
    """
    Extract references from BCON (Behavioral Constants) chunks.
    
    BCON chunks are leaf nodes - they don't reference other chunks.
    They are referenced BY other chunks (BHAV, TRCN).
    Therefore, this extractor returns no outbound references.
    
    Inbound references to BCON are handled by:
    - BHAV extractor (via opcode 2, requires operand parsing - TODO)
    - TRCN is optional metadata, not part of core dependency graph
    """
    
    @property
    def chunk_type(self) -> str:
        return "BCON"
    
    def extract(self, bcon: Optional[object], node: ResourceNode) -> List[Reference]:
        """
        Extract references from BCON chunk.
        
        Since BCON chunks are leaf nodes with no outbound references,
        this always returns an empty list.
        
        Note: Advanced operand parsing for BHAV opcode 2 would go here,
        but is deferred to Phase 3 due to complexity.
        """
        return []
