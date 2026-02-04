"""Graph loader - builds resource graph from IFF files."""

from pathlib import Path
from typing import List, Optional, Dict
import sys

# Ensure formats package is importable
workspace_root = Path(__file__).parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

# Ensure Program directory is in path
program_dir = Path(__file__).parent.parent
if str(program_dir) not in sys.path:
    sys.path.insert(0, str(program_dir))

# Import from core package
from core.iff_reader import read_iff_file, IFFChunk
from core.chunk_parsers import parse_objd, parse_spr2, parse_bhav, parse_ttab, parse_bcon, parse_dgrp
from core.chunk_parsers_objf import parse_objf

from .core import ResourceGraph, TGI, ResourceNode, ChunkScope
from .extractors.registry import ExtractorRegistry

# Import extractors to register them
from . import extractors


class GraphLoader:
    """
    Loads IFF files and builds the complete resource graph.
    Uses minimal IFF reader to avoid import cascades.
    """
    
    def __init__(self):
        self.graph = ResourceGraph()
        self.loaded_files: Dict[str, object] = {}
    
    def load_iff(self, filepath: str) -> Optional[object]:
        """Load a single IFF file and add its chunks to the graph."""
        try:
            path = Path(filepath)
            if not path.exists():
                print(f"ERROR: File not found: {filepath}")
                return None
            
            iff_file = read_iff_file(filepath)
            
            if not iff_file:
                print(f"ERROR: Could not parse IFF file: {filepath}")
                return None
            
            self.loaded_files[filepath] = iff_file
            self._index_chunks(iff_file, filepath)
            
            return iff_file
        except Exception as e:
            print(f"ERROR loading {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _index_chunks(self, iff_file: object, filepath: str) -> None:
        """Index all chunks from an IFF file as nodes."""
        if not hasattr(iff_file, "chunks"):
            print(f"WARNING: IFF file {filepath} has no chunks attribute")
            return
        
        for chunk in iff_file.chunks:
            if not hasattr(chunk, "type_code"):
                continue
            
            chunk_type = chunk.type_code
            chunk_id = getattr(chunk, "chunk_id", 0)
            
            tgi = TGI(chunk_type, 0x00000001, chunk_id)
            node = ResourceNode(
                tgi=tgi,
                chunk_type=chunk_type,
                owner_iff=filepath,
                scope=ChunkScope.OBJECT,
                label=getattr(chunk, "chunk_label", ""),
                size=len(getattr(chunk, "chunk_data", b"")),
            )
            
            # Store chunk data for later extraction
            if hasattr(chunk, "chunk_data"):
                node._chunk_data = chunk.chunk_data
            
            self.graph.add_node(node)
    
    def extract_references(self) -> int:
        """
        Extract references from all loaded chunks using registered extractors.
        Uses minimal parsers to avoid importing formats package.
        Returns count of references extracted.
        """
        reference_count = 0
        
        # Make a copy of nodes to iterate over (since extraction may add new nodes)
        nodes_to_process = list(self.graph.nodes.values())
        
        for node in nodes_to_process:
            chunk_type = node.chunk_type
            
            # Check if we have an extractor for this chunk type
            extractor_class = ExtractorRegistry.get(chunk_type)
            
            if extractor_class is None:
                # No extractor available for this type
                continue
            
            # Get the raw chunk data
            if not hasattr(node, "_chunk_data"):
                continue
            
            chunk_data = node._chunk_data
            chunk_id = node.tgi.instance_id
            
            # Parse chunk based on type
            parsed_chunk = None
            if chunk_type == "OBJD":
                parsed_chunk = parse_objd(chunk_data, chunk_id)
            elif chunk_type == "OBJf":
                parsed_chunk = parse_objf(chunk_data, chunk_id)
            elif chunk_type == "SPR2":
                parsed_chunk = parse_spr2(chunk_data, chunk_id)
            elif chunk_type == "BHAV":
                parsed_chunk = parse_bhav(chunk_data, chunk_id)
            elif chunk_type == "TTAB":
                parsed_chunk = parse_ttab(chunk_data, chunk_id)
            elif chunk_type == "BCON":
                parsed_chunk = parse_bcon(chunk_data, chunk_id)
            elif chunk_type == "DGRP":
                parsed_chunk = parse_dgrp(chunk_data, chunk_id)
            
            if parsed_chunk is None:
                continue
            
            # Extract references using the extractor
            try:
                extractor = extractor_class()
                refs = extractor.extract(parsed_chunk, node)
                
                for ref in refs:
                    self.graph.add_reference(ref)
                    reference_count += 1
                    
            except Exception as e:
                print(f"Error extracting from {chunk_type}#{chunk_id}: {e}")
        
        return reference_count
    
    def load_iff_directory(self, directory: str, pattern: str = "*.iff") -> List[str]:
        """
        Load all IFF files from a directory.
        Returns list of successfully loaded files.
        """
        path = Path(directory)
        loaded = []
        
        for iff_path in path.glob(pattern):
            if self.load_iff(str(iff_path)):
                loaded.append(str(iff_path))
        
        return loaded
    
    def get_graph(self) -> ResourceGraph:
        """Get the built resource graph."""
        return self.graph
    
    def print_summary(self) -> None:
        """Print summary of loaded graph."""
        stats = self.graph.statistics()
        
        print("\n" + "=" * 60)
        print("RESOURCE GRAPH SUMMARY")
        print("=" * 60)
        print(f"Nodes (chunks):        {stats['total_nodes']}")
        print(f"Edges (references):    {stats['total_edges']}")
        print(f"Orphan chunks:         {stats['orphan_count']}")
        print(f"Files loaded:          {stats['files_represented']}")
        print(f"Avg inbound refs:      {stats['avg_inbound_refs']:.2f}")
        print(f"Avg outbound refs:     {stats['avg_outbound_refs']:.2f}")
        print("=" * 60 + "\n")
