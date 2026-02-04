"""Core resource graph data structures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Set, List, Optional, Tuple


class ChunkScope(Enum):
    """Scope level of a chunk - determines visibility."""
    OBJECT = "object"           # Local to object's IFF file
    SEMI_GLOBAL = "semi_global" # From GLOB reference
    GLOBAL = "global"           # From Global.iff
    UNKNOWN = "unknown"         # Scope not determined


class ReferenceKind(Enum):
    """Type of reference between chunks."""
    HARD = "hard"               # Required (OBJD -> BHAV init)
    SOFT = "soft"               # Optional/fallback
    INDEXED = "indexed"         # Array/table lookup (TTAB -> TTAs)
    IMPORT = "import"           # Cross-file reference


@dataclass(frozen=True)
class TGI:
    """Type-Group-Instance identifier for IFF resources."""
    type_code: str              # 4-char code: "OBJD", "BHAV", etc.
    group_id: int              # Group ID (usually 0x00000001)
    instance_id: int           # Resource ID within type

    def __str__(self) -> str:
        return f"{self.type_code}#{self.instance_id}"

    def __repr__(self) -> str:
        return f"TGI({self.type_code}, {self.group_id}, {self.instance_id})"


@dataclass
class ResourceNode:
    """Represents a single chunk/resource in the dependency graph."""
    tgi: TGI
    chunk_type: str            # Redundant with tgi.type_code, for convenience
    owner_iff: str             # Path to IFF file containing this resource
    scope: ChunkScope = ChunkScope.UNKNOWN
    label: str = ""            # Human-readable name if available
    size: int = 0              # Size in bytes
    is_phantom: bool = False   # True if node created from reference (not parsed from file)
    
    def __hash__(self):
        return hash(self.tgi)
    
    def __eq__(self, other):
        if not isinstance(other, ResourceNode):
            return False
        return self.tgi == other.tgi


@dataclass
class Reference:
    """Represents an edge (reference) between two chunks."""
    source: ResourceNode       # From this chunk
    target: ResourceNode       # To this chunk
    kind: ReferenceKind        # How it references
    source_field: str = ""     # Which field in source (e.g., "bhav_init_id")
    description: str = ""      # Human description
    confidence: float = 1.0    # 0.0-1.0, lower if uncertain
    edge_kind: str = ""        # Semantic category: structural | behavioral | visual | tuning
    
    def __repr__(self) -> str:
        return f"{self.source} -{self.kind.value}-> {self.target}"


@dataclass
class ResourceGraph:
    """Dependency graph for The Sims resources."""
    
    # Nodes and edges
    nodes: Dict[TGI, ResourceNode] = field(default_factory=dict)
    edges: List[Reference] = field(default_factory=list)
    
    # Index for fast lookup
    _nodes_by_file: Dict[str, Set[TGI]] = field(default_factory=dict)
    _inbound_refs: Dict[TGI, List[Reference]] = field(default_factory=dict)
    _outbound_refs: Dict[TGI, List[Reference]] = field(default_factory=dict)
    
    def add_node(self, node: ResourceNode) -> None:
        """Add a resource node to the graph."""
        if node.tgi in self.nodes:
            return  # Already exists
        
        self.nodes[node.tgi] = node
        self._inbound_refs.setdefault(node.tgi, [])
        self._outbound_refs.setdefault(node.tgi, [])
        
        # Index by file
        if node.owner_iff not in self._nodes_by_file:
            self._nodes_by_file[node.owner_iff] = set()
        self._nodes_by_file[node.owner_iff].add(node.tgi)
    
    def add_reference(self, reference: Reference) -> None:
        """Add an edge (reference) between two nodes."""
        # Ensure source node exists
        if reference.source.tgi not in self.nodes:
            self.add_node(reference.source)
        
        # If target doesn't exist, create as phantom node
        if reference.target.tgi not in self.nodes:
            reference.target.is_phantom = True
            self.add_node(reference.target)
        
        self.edges.append(reference)
        self._outbound_refs[reference.source.tgi].append(reference)
        self._inbound_refs[reference.target.tgi].append(reference)
    
    def get_node(self, tgi: TGI) -> Optional[ResourceNode]:
        """Retrieve a node by TGI."""
        return self.nodes.get(tgi)
    
    def who_references(self, tgi: TGI) -> List[Reference]:
        """Find all references TO this chunk (inbound)."""
        return self._inbound_refs.get(tgi, [])
    
    def what_references(self, tgi: TGI) -> List[Reference]:
        """Find all references FROM this chunk (outbound)."""
        return self._outbound_refs.get(tgi, [])
    
    def find_orphans(self) -> List[ResourceNode]:
        """Find nodes with no inbound references."""
        orphans = []
        for tgi, node in self.nodes.items():
            if not self._inbound_refs.get(tgi, []):
                orphans.append(node)
        return orphans
    
    def get_nodes_in_file(self, filepath: str) -> List[ResourceNode]:
        """Get all nodes from a specific IFF file."""
        tgis = self._nodes_by_file.get(filepath, set())
        return [self.nodes[tgi] for tgi in tgis]
    
    def detect_cycles(self):
        """
        Detect cycles in the graph (Phase 3.2).
        
        Returns:
            CycleDetector instance with detected cycles
        
        Note: Cycles are NOT errors - this is diagnostic tooling.
        """
        from .cycle_detector import CycleDetector
        detector = CycleDetector(self)
        detector.detect_all_cycles()
        return detector
    
    def validate_scope(self):
        """
        Validate scope consistency and reference integrity (Phase 3.3).
        
        Returns:
            ScopeValidator instance with detected issues
        
        Checks:
            - BHAV scope consistency (GLOB imports)
            - Missing reference targets
            - Orphaned critical resources
            - Tuning constant validity
            - Interaction integrity
        """
        from .scope_validator import ScopeValidator
        validator = ScopeValidator(self)
        validator.validate_all()
        return validator
    
    def statistics(self) -> Dict:
        """Generate basic graph statistics."""
        orphans = self.find_orphans()
        
        avg_inbound = sum(len(refs) for refs in self._inbound_refs.values()) / len(self.nodes) if self.nodes else 0
        avg_outbound = sum(len(refs) for refs in self._outbound_refs.values()) / len(self.nodes) if self.nodes else 0
        
        return {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'orphan_count': len(orphans),
            'avg_inbound_refs': avg_inbound,
            'avg_outbound_refs': avg_outbound,
            'files_represented': len(self._nodes_by_file),
        }
    
    def __str__(self) -> str:
        stats = self.statistics()
        return (
            f"ResourceGraph:\n"
            f"  Nodes: {stats['total_nodes']}\n"
            f"  Edges: {stats['total_edges']}\n"
            f"  Orphans: {stats['orphan_count']}\n"
            f"  Files: {stats['files_represented']}\n"
        )
