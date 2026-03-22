# Resource Graph System - Usage Guide

## Quick Start

### 1. Basic Graph Building

```python
from Program.graph.loader import GraphLoader
from pathlib import Path

# Create loader
loader = GraphLoader()

# Load IFF files
loader.load_iff("path/to/AlarmClock.iff")
loader.load_iff("path/to/ArtGlobals.iff")

# Extract all references
ref_count = loader.extract_references()
print(f"Extracted {ref_count} references")

# Get the graph
graph = loader.graph
print(f"Nodes: {len(graph.nodes)}")
print(f"Edges: {len(graph.references)}")
```

### 2. Query the Graph

```python
# Find all references from a chunk
objd_node = graph.find_node("OBJD", 0, 16807)
outbound_refs = graph.references.get(objd_node.tgi, [])
print(f"OBJD#16807 references {len(outbound_refs)} chunks")

# Find all references TO a chunk
palt_node = graph.find_node("PALT", 0, 1000)
inbound_refs = [r for r in graph.all_references() if r.target.tgi == palt_node.tgi]
print(f"{len(inbound_refs)} chunks reference PALT#1000")

# Find orphans
orphans = graph.find_orphans()
print(f"Found {len(orphans)} orphan chunks")

# Get reference chain
chain = graph.trace_from("OBJD", 0, 16807, max_depth=3)
for level, nodes in enumerate(chain):
    print(f"  Depth {level}: {len(nodes)} chunks")
```

### 3. Analysis Patterns

```python
# What breaks if I delete this chunk?
blast_radius = graph.find_blast_radius("BHAV", 0, 4097)
print(f"Deleting BHAV#4097 would break {len(blast_radius)} chunks")

# What tuning does this BHAV use?
bhav_refs = graph.references.get(("BHAV", 0, 4097), [])
bcon_refs = [r for r in bhav_refs if r.target.chunk_type == "BCON"]
print(f"BHAV#4097 references {len(bcon_refs)} BCON constants")

# Find all objects using this sprite
spr_inbound = graph.find_inbound("SPR2", 0, 128)
print(f"Sprite#128 used by {len(spr_inbound)} drawing groups")

# Verify scope safety
objd_node = graph.find_node("OBJD", 0, 16807)
unsafe_refs = [r for r in outbound_refs
               if r.target.scope > objd_node.scope]
print(f"Found {len(unsafe_refs)} potentially unsafe references")
```

## Understanding the Graph Structure

### Nodes (Chunks)

Each node represents an IFF chunk:

```python
class ResourceNode:
    tgi: TGI              # (Type, Group, Instance)
    chunk_type: str       # "BHAV", "OBJD", etc.
    owner_iff: str        # File path
    scope: ChunkScope     # OBJECT, SEMI_GLOBAL, GLOBAL
    label: str            # Human-readable label
    size: int             # Chunk size in bytes
```

### References (Edges)

Each reference represents a dependency:

```python
class Reference:
    source: ResourceNode
    target: ResourceNode
    kind: ReferenceKind   # HARD, SOFT, INDEXED
    source_field: str     # Where in source chunk
    description: str      # Human description
```

### Scopes

```
OBJECT (ChunkScope.OBJECT)
  - Local to one object file
  - IDs: 0x0000-0x3FFF (0-16383)
  - Example: BHAV#4096, SPR2#128

SEMI_GLOBAL (ChunkScope.SEMI_GLOBAL)
  - Shared game objects
  - IDs: 0x8000-0xFFFF (32768-65535)
  - Example: BHAV#8200

GLOBAL (ChunkScope.GLOBAL)
  - Game-wide resources
  - IDs: 0x0100-0x0FFF (256-4095)
  - Example: BHAV#0256
```

### Reference Kinds

```
HARD
  - Required for object to function
  - Deletion breaks object
  - Example: OBJD → BHAV

SOFT
  - Optional/fallback
  - May not affect function
  - Example: OBJD → STR# (has defaults)

INDEXED
  - Array/table element
  - One of many options
  - Example: TTAB → TTAs[index]
```

## Common Queries

### "What does this object need?"

```python
def get_object_dependencies(graph, object_id):
    """Get all chunks required by an object."""
    objd = graph.find_node("OBJD", 0, object_id)
    deps = set()

    def traverse(node, depth=0):
        if depth > 10:  # Prevent infinite recursion
            return

        refs = graph.references.get(node.tgi, [])
        for ref in refs:
            deps.add(ref.target.tgi)
            if depth < 5:
                traverse(ref.target, depth + 1)

    traverse(objd)
    return deps

deps = get_object_dependencies(graph, 16807)
print(f"AlarmClock depends on {len(deps)} chunks")
```

### "Is this chunk safe to modify?"

```python
def is_safe_to_modify(graph, chunk_type, group, instance):
    """Check if modifying chunk is safe."""
    node = graph.find_node(chunk_type, group, instance)

    # Safety checks
    inbound = graph.find_inbound(chunk_type, group, instance)

    if len(inbound) > 5:
        return False, "High blast radius"

    # Check scope
    dangerous_scopes = [
        (ChunkScope.GLOBAL, "global"),
        (ChunkScope.SEMI_GLOBAL, "semi-global")
    ]

    for scope, name in dangerous_scopes:
        if node.scope == scope:
            return False, f"Modifying {name} resource affects all objects"

    return True, "Safe to modify (local scope, low usage)"

safe, reason = is_safe_to_modify(graph, "BHAV", 0, 4097)
print(reason)
```

### "Can I delete this and clone?"

```python
def can_clone_safely(graph, object_id):
    """Check if object can be safely cloned."""
    objd = graph.find_node("OBJD", 0, object_id)
    refs = graph.find_inbound("OBJD", 0, object_id)

    # Check for global references
    has_global_refs = any(
        r.source.scope == ChunkScope.GLOBAL
        for r in refs
    )

    if has_global_refs:
        return False, "Object is referenced from global scope"

    return True, "Safe to clone"

safe, reason = can_clone_safely(graph, 16807)
print(reason)
```

### "Find dead code"

```python
def find_unused_bhavs(graph):
    """Find BHAV chunks that no other chunk references."""
    unused = []

    for node in graph.nodes.values():
        if node.chunk_type != "BHAV":
            continue

        inbound = graph.find_inbound(
            node.chunk_type,
            node.tgi.group_id,
            node.tgi.instance_id
        )

        if len(inbound) == 0:
            unused.append(node.tgi)

    return unused

dead = find_unused_bhavs(graph)
print(f"Found {len(dead)} unused BHAV chunks")
for bhav_tgi in dead[:10]:
    print(f"  {bhav_tgi}")
```

## Integration Points

### With Editors

```python
# When user edits a chunk
def on_chunk_modified(graph, chunk_type, group, instance):
    """Alert user about consequences of edit."""
    affected = graph.find_blast_radius(chunk_type, group, instance)

    if len(affected) > 0:
        print(f"WARNING: Modifying this chunk affects:")
        for tgi in affected[:5]:
            print(f"  - {tgi}")

# When user tries to delete
def on_chunk_delete_requested(graph, chunk_type, group, instance):
    """Check if deletion is safe."""
    refs = graph.find_inbound(chunk_type, group, instance)

    if len(refs) > 0:
        print(f"ERROR: Cannot delete - referenced by:")
        for ref in refs:
            print(f"  - {ref.source.tgi} ({ref.description})")
        return False

    return True
```

### With Batch Tools

```python
# Mass operation validation
def validate_bulk_operation(graph, chunks_to_modify):
    """Validate a bulk edit operation."""
    all_affected = set()

    for chunk_spec in chunks_to_modify:
        affected = graph.find_blast_radius(*chunk_spec)
        all_affected.update(affected)

    # Check for cross-contamination
    overlaps = all_affected & set(chunks_to_modify)

    if overlaps:
        print(f"WARNING: {len(overlaps)} chunks modify each other")
        return False

    return True
```

## Testing & Validation

### Run Tests

```bash
cd Program
python test_graph.py

# Output:
# ======================================================================
# RESOURCE GRAPH TEST
# ======================================================================
# Extracted 126 references
# Nodes: 81, Edges: 126, Orphans: 32
# ✅ All tests passed
```

### Debug a Specific Chunk

```python
import json

def debug_chunk(graph, chunk_type, group, instance):
    """Print detailed debug info about a chunk."""
    node = graph.find_node(chunk_type, group, instance)

    print(f"=== {chunk_type}#{instance} ===")
    print(f"Scope: {node.scope.name}")
    print(f"Owner: {node.owner_iff}")
    print(f"Size: {node.size} bytes")

    outbound = graph.references.get(node.tgi, [])
    print(f"\nOutbound references ({len(outbound)}):")
    for ref in outbound[:10]:
        print(f"  → {ref.target.tgi} ({ref.kind.name})")
        print(f"     {ref.description}")

    inbound = graph.find_inbound(chunk_type, group, instance)
    print(f"\nInbound references ({len(inbound)}):")
    for ref in inbound[:10]:
        print(f"  ← {ref.source.tgi} ({ref.kind.name})")

debug_chunk(graph, "BHAV", 0, 4097)
```

## Performance Considerations

### Memory Usage

- ~500 bytes per chunk node
- ~200 bytes per reference edge
- Test dataset: 81 nodes + 126 refs ≈ 65 KB

### Query Performance

- `find_node()`: O(1) hash lookup
- `find_inbound()`: O(n) scan (n = total refs)
- `find_blast_radius()`: O(n\*d) BFS where d = depth
- `trace_from()`: O(n\*d) full traversal

### Optimization Tips

- Cache results of expensive queries
- Use scope filtering to reduce search space
- Implement query result caching
- Use lazy evaluation for deep traversals

## Extending the System

### Adding a New Extractor

```python
from Program.graph.extractors.base import ReferenceExtractor
from Program.graph.extractors.registry import ExtractorRegistry

@ExtractorRegistry.register("NEWCHUNK")
class NewChunkExtractor(ReferenceExtractor):
    @property
    def chunk_type(self):
        return "NEWCHUNK"

    def extract(self, chunk, node):
        refs = []
        # Parse chunk and find references
        for target_id in chunk.target_ids:
            target_node = ResourceNode(...)
            refs.append(Reference(...))
        return refs
```

### Adding a New Parser

```python
@dataclass
class MinimalNewChunk:
    chunk_id: int
    targets: list = None

    def __post_init__(self):
        if self.targets is None:
            self.targets = []

def parse_newchunk(chunk_data: bytes, chunk_id: int):
    """Parse NEWCHUNK into minimal representation."""
    buf = IoBuffer.from_bytes(chunk_data, ByteOrder.LITTLE_ENDIAN)
    chunk = MinimalNewChunk(chunk_id=chunk_id)

    # Parse structure
    count = buf.read_uint16()
    for _ in range(count):
        chunk.targets.append(buf.read_uint32())

    return chunk
```

## Troubleshooting

### Graph not building

```python
# Enable debug output
import logging
logging.basicConfig(level=logging.DEBUG)

# Check loaded files
print(f"Loaded files: {list(loader.loaded_files.keys())}")

# Check nodes
print(f"Nodes: {list(loader.graph.nodes.keys())[:10]}")
```

### Missing references

```python
# Verify extractors are registered
from Program.graph.extractors.registry import ExtractorRegistry
print(f"Registered extractors: {ExtractorRegistry._extractors.keys()}")

# Check if parser is implemented
from Program.chunk_parsers import parse_bhav
parsed = parse_bhav(raw_data, chunk_id)
print(f"Parser result: {parsed}")
```

### Unexpected scope classifications

```python
# Verify ID ranges
node = graph.find_node("BHAV", 0, instance_id)
print(f"ID {instance_id} → scope {node.scope.name}")
# 256-4095: GLOBAL
# 4096-8191: OBJECT
# 8192+: SEMI_GLOBAL
```

---

**Version**: 1.0 (Phase 2)  
**Last Updated**: 2026-02-02  
**Status**: Ready for production use
