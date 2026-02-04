"""Extractor registry - dynamically load and manage extractors with lazy loading."""

import sys
import importlib
from pathlib import Path
from typing import Dict, Type, Optional
from .base import ReferenceExtractor


class ExtractorRegistry:
    """Registry for reference extractors by chunk type with lazy loading support."""
    
    _extractors: Dict[str, Type[ReferenceExtractor]] = {}
    _lazy_loaders: Dict[str, tuple] = {}  # chunk_type -> (full_module_path, class_name)
    _failed_loads: set = set()  # Track failed imports
    
    @classmethod
    def register(cls, chunk_type: str):
        """Decorator to register an extractor."""
        def decorator(extractor_class: Type[ReferenceExtractor]):
            cls._extractors[chunk_type] = extractor_class
            return extractor_class
        return decorator
    
    @classmethod
    def register_lazy(cls, chunk_type: str, module_path: str, class_name: str):
        """Register a lazy-loaded extractor (loaded on-demand).
        
        Args:
            chunk_type: The chunk type string (e.g., "OBJD")
            module_path: Full module path (e.g., "graph.extractors.objd")
            class_name: Class name in that module (e.g., "OBJDExtractor")
        """
        cls._lazy_loaders[chunk_type] = (module_path, class_name)
    
    @classmethod
    def get(cls, chunk_type: str) -> Optional[Type[ReferenceExtractor]]:
        """Get extractor class for a chunk type, with lazy loading."""
        # Try immediate cache first
        if chunk_type in cls._extractors:
            return cls._extractors[chunk_type]
        
        # Skip if previous load failed
        if chunk_type in cls._failed_loads:
            return None
        
        # Try lazy loading
        if chunk_type in cls._lazy_loaders:
            module_path, class_name = cls._lazy_loaders[chunk_type]
            try:
                # Dynamically import the module
                module = importlib.import_module(module_path)
                extractor_class = getattr(module, class_name)
                # Cache the successfully loaded extractor
                cls._extractors[chunk_type] = extractor_class
                return extractor_class
            except ImportError as e:
                # Mark as failed, don't retry
                cls._failed_loads.add(chunk_type)
                print(f"WARNING: Could not lazy-load extractor for {chunk_type}: {e}")
                return None
            except Exception as e:
                cls._failed_loads.add(chunk_type)
                print(f"WARNING: Error loading extractor for {chunk_type}: {e}")
                return None
        
        return None
    
    @classmethod
    def get_all(cls) -> Dict[str, Type[ReferenceExtractor]]:
        """Get all registered extractors."""
        return cls._extractors.copy()
    
    @classmethod
    def has(cls, chunk_type: str) -> bool:
        """Check if extractor exists for chunk type (including lazy-loadable)."""
        return chunk_type in cls._extractors or chunk_type in cls._lazy_loaders
    
    @classmethod
    def try_load_all(cls):
        """Attempt to load all lazy-loadable extractors."""
        for chunk_type in list(cls._lazy_loaders.keys()):
            cls.get(chunk_type)


# Register lazy-loadable extractors
# These will only attempt to import when actually needed
# Note: Must use full module path from workspace root
try:
    # When imported normally (workspace root in sys.path)
    ExtractorRegistry.register_lazy("OBJD", "Program.graph.extractors.objd", "OBJDExtractor")
    ExtractorRegistry.register_lazy("OBJf", "Program.graph.extractors.objf", "OBJfExtractor")
    ExtractorRegistry.register_lazy("SPR2", "Program.graph.extractors.spr", "SPRExtractor")
except:
    # Fallback if module path doesn't work
    pass

__all__ = ['ExtractorRegistry']
