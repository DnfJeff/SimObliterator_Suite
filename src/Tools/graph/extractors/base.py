"""Base class for reference extractors."""

from abc import ABC, abstractmethod
from typing import List

from ..core import Reference, ResourceNode


class ReferenceExtractor(ABC):
    """
    Abstract base for extractors that pull references from chunks.
    
    Each extractor handles one chunk type and understands how that
    chunk references other resources.
    """
    
    @property
    @abstractmethod
    def chunk_type(self) -> str:
        """4-char chunk type code this extractor handles."""
        pass
    
    @abstractmethod
    def extract(self, chunk, node: ResourceNode) -> List[Reference]:
        """
        Extract references from a chunk instance.
        
        Args:
            chunk: The parsed chunk object (e.g., OBJD, BHAV, SPR2)
            node: The ResourceNode representing this chunk
        
        Returns:
            List of Reference objects pointing to other chunks
        """
        pass
