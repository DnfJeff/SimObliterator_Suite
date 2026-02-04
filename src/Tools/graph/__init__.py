"""Resource Graph system - dependency resolution for The Sims IFF files."""

from .core import (
    ResourceNode,
    Reference,
    ReferenceKind,
    ResourceGraph,
    ChunkScope,
)
from .loader import GraphLoader

__all__ = [
    'ResourceNode',
    'Reference',
    'ReferenceKind',
    'ResourceGraph',
    'ChunkScope',
    'GraphLoader',
]
