"""
Output formatters for different analytical views of the pipeline results.

Provides multiple reporting modes to analyze object chunks, BHAVs, patterns, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass


@dataclass
class FormatterContext:
    """Context containing data needed by formatters."""
    print_func: Callable  # Function to call for output (e.g., pipeline._print)
    total_objects: int
    current_idx: int
    object_name: str
    bhav_ids: List[int]
    iff_object: Optional[object]  # The IFF object if available
    chunk_types_found: Dict[str, int]  # {chunk_type: count}
    all_chunks: List[object]  # All chunks in the IFF


class OutputFormatter(ABC):
    """Abstract base class for output formatters."""
    
    @abstractmethod
    def format_header(self):
        """Format and print the header."""
        pass
    
    @abstractmethod
    def format_object(self, context: FormatterContext):
        """Format and print a single object's data."""
        pass
    
    @abstractmethod
    def format_footer(self, total_objects: int):
        """Format and print the footer."""
        pass


class BHAVAnalysisFormatter(OutputFormatter):
    """
    Current output formatter: Shows BHAVs per object with dividers.
    This is the original behavior-focused analysis.
    """
    
    def __init__(self, print_func: Callable):
        self.print_func = print_func
    
    def format_header(self):
        """Print the header for BHAV analysis."""
        self.print_func("\nPHASE 1-4: Per-Object Analysis (BHAV Focus)")
        self.print_func("-" * 120)
    
    def format_object(self, context: FormatterContext):
        """Format a single object showing its BHAVs."""
        bhav_ids = context.bhav_ids
        object_name = context.object_name
        idx = context.current_idx
        total_objects = context.total_objects
        
        # Try to get BHAV names from the IFF
        bhav_info = []
        try:
            iff = context.iff_object
            if iff and iff.chunks:
                bhavs_by_id = {chunk.chunk_id: chunk for chunk in iff.chunks if chunk.chunk_type == 'BHAV'}
                for bid in bhav_ids:
                    bhav = bhavs_by_id.get(bid)
                    if bhav and bhav.chunk_label:
                        label = bhav.chunk_label.strip() or f"BHAV#{bid}"
                        bhav_info.append(f"#{bid}({label})")
                    else:
                        bhav_info.append(f"#{bid}")
            else:
                bhav_info = [f"#{bid}" for bid in bhav_ids]
        except Exception:
            bhav_info = [f"#{bid}" for bid in bhav_ids]
        
        # Format with line breaks - 6 items per line
        self.print_func(f"  [{idx:3d}/{total_objects}] {object_name:<40}")
        items_per_line = 6
        for line_idx in range(0, len(bhav_info), items_per_line):
            line_items = bhav_info[line_idx:line_idx + items_per_line]
            line_str = ", ".join(line_items)
            if line_idx == 0:
                self.print_func(f"      BHAVs ({len(bhav_ids)}): {line_str}")
            else:
                self.print_func(f"                      {line_str}")
                # Add divider after each group (except the last one)
                if line_idx + items_per_line < len(bhav_info):
                    self.print_func("                      " + "-" * 80)
        
        # Add divider line between objects
        if idx < total_objects:
            self.print_func("-" * 120)
    
    def format_footer(self, total_objects: int):
        """Print footer for BHAV analysis."""
        self.print_func(f"\n[+] BHAV Analysis Complete: {total_objects} objects processed")


class ChunkInventoryFormatter(OutputFormatter):
    """
    Chunk inventory mode: Shows ALL chunks in each object with chunk codes.
    Format: CHUNKTYPE#ID or CHUNKTYPE#ID(Label) if available
    Example: BHAV#4096, STR#200, PALT#1, SPR#256
    """
    
    def __init__(self, print_func: Callable):
        self.print_func = print_func
    
    def format_header(self):
        """Print the header for chunk inventory."""
        self.print_func("\nPHASE 1-4: Per-Object Analysis (Chunk Inventory)")
        self.print_func("-" * 120)
    
    def format_object(self, context: FormatterContext):
        """Format a single object showing all its chunks."""
        object_name = context.object_name
        idx = context.current_idx
        total_objects = context.total_objects
        chunk_types_found = context.chunk_types_found
        
        try:
            iff = context.iff_object
            # Build chunk info list with codes (CHUNKTYPE#ID)
            chunk_info = []
            if iff and iff.chunks:
                # Group by chunk type for better organization
                chunks_by_type: Dict[str, List] = {}
                for chunk in iff.chunks:
                    ctype = chunk.chunk_type
                    if ctype not in chunks_by_type:
                        chunks_by_type[ctype] = []
                    chunks_by_type[ctype].append(chunk)
                
                # Format chunks in type-grouped order
                for ctype in sorted(chunks_by_type.keys()):
                    chunks = chunks_by_type[ctype]
                    for chunk in sorted(chunks, key=lambda c: c.chunk_id):
                        chunk_code = f"{ctype}#{chunk.chunk_id}"
                        if hasattr(chunk, 'chunk_label') and chunk.chunk_label:
                            label = chunk.chunk_label.strip()
                            if label:
                                chunk_code += f"({label})"
                        chunk_info.append(chunk_code)
            
            if not chunk_info:
                chunk_info = ["(no chunks)"]
            
        except Exception as e:
            chunk_info = [f"(error reading chunks: {str(e)[:30]})"]
        
        # Print object header with chunk count summary
        self.print_func(f"  [{idx:3d}/{total_objects}] {object_name:<40} | {len(chunk_info)} chunks")
        
        # Format chunks: 5 items per line for readability
        items_per_line = 5
        for line_idx in range(0, len(chunk_info), items_per_line):
            line_items = chunk_info[line_idx:line_idx + items_per_line]
            line_str = "  |  ".join(line_items)
            self.print_func(f"      {line_str}")
            
            # Add divider after each line except last
            if line_idx + items_per_line < len(chunk_info):
                self.print_func("      " + "-" * 110)
        
        # Add divider line between objects
        if idx < total_objects:
            self.print_func("-" * 120)
    
    def format_footer(self, total_objects: int):
        """Print footer for chunk inventory."""
        self.print_func(f"\n[+] Chunk Inventory Complete: {total_objects} objects analyzed")


class ChunkDistributionFormatter(OutputFormatter):
    """
    Chunk distribution mode: Shows which objects have which chunk types.
    Helps identify patterns like "all chairs have TTAB, SLOT, ANIM"
    """
    
    def __init__(self, print_func: Callable, metrics: Optional[object] = None):
        self.print_func = print_func
        self.metrics = metrics
    
    def format_header(self):
        """Print the header for chunk distribution."""
        self.print_func("\nPHASE 1-4: Per-Object Analysis (Chunk Distribution)")
        self.print_func("-" * 120)
        self.print_func("Building chunk distribution matrix...\n")
    
    def format_object(self, context: FormatterContext):
        """Collect chunk data for a single object."""
        object_name = context.object_name
        chunk_types_found = context.chunk_types_found
        
        # Show progress
        idx = context.current_idx
        total_objects = context.total_objects
        chunk_summary = ", ".join([f"{ctype}({count})" for ctype, count in sorted(chunk_types_found.items())]) if chunk_types_found else "(no chunks)"
        self.print_func(f"  [{idx:3d}/{total_objects}] {object_name:<40} | {chunk_summary}")
    
    def format_footer(self, total_objects: int):
        """Print analysis of chunk patterns."""
        if not self.metrics or not hasattr(self.metrics, 'per_object_chunks'):
            self.print_func(f"\n[+] Chunk Distribution Complete: {total_objects} objects analyzed")
            return
        
        object_chunk_matrix = self.metrics.per_object_chunks
        if not object_chunk_matrix:
            return
        
        self.print_func("\n" + "=" * 120)
        self.print_func(" CHUNK PATTERN ANALYSIS")
        self.print_func("=" * 120)
        
        # Find which chunk types exist and which objects have them
        all_chunk_types = set()
        for chunks in object_chunk_matrix.values():
            all_chunk_types.update(chunks.keys())
        
        # For each chunk type, show which objects have it
        for chunk_type in sorted(all_chunk_types):
            objects_with_chunk = [obj for obj, chunks in object_chunk_matrix.items() if chunk_type in chunks]
            percentage = (len(objects_with_chunk) / total_objects) * 100 if total_objects > 0 else 0
            
            self.print_func(f"\n  {chunk_type:<8} [{len(objects_with_chunk):3d}/{total_objects} objects | {percentage:5.1f}%]")
            
            # Show objects
            for obj_name in sorted(objects_with_chunk)[:10]:  # Show first 10
                count = object_chunk_matrix[obj_name][chunk_type]
                self.print_func(f"    - {obj_name:<40} ({count} chunk{'s' if count > 1 else ''})")
            
            if len(objects_with_chunk) > 10:
                self.print_func(f"    ... and {len(objects_with_chunk) - 10} more objects")
        
        # Find common chunk combinations
        self.print_func("\n" + "-" * 120)
        self.print_func(" COMMON CHUNK PATTERNS (groups of objects with identical chunk types)")
        self.print_func("-" * 120)
        
        # Create signature (set of chunk types) for each object
        signatures: Dict[str, List[str]] = {}
        for obj_name, chunks in object_chunk_matrix.items():
            sig = tuple(sorted(chunks.keys()))
            if sig not in signatures:
                signatures[sig] = []
            signatures[sig].append(obj_name)
        
        # Show patterns (sorted by frequency)
        pattern_count = 0
        for sig, objects in sorted(signatures.items(), key=lambda x: -len(x[1]))[:15]:
            pattern_count += 1
            chunk_list = ", ".join(sig) if sig else "(empty)"
            self.print_func(f"\n  Pattern {pattern_count}: [{len(objects)} objects]")
            self.print_func(f"    Chunks: {chunk_list}")
            self.print_func(f"    Objects: {', '.join(sorted(objects)[:8])}", end='')
            if len(objects) > 8:
                self.print_func(f", ... and {len(objects) - 8} more")
            else:
                self.print_func()
        
        self.print_func(f"\n[+] Chunk Distribution Complete: {total_objects} objects analyzed | {len(all_chunk_types)} chunk types")


def get_formatter(format_mode: str, print_func: Callable, metrics: Optional[object] = None) -> OutputFormatter:
    """
    Get the appropriate formatter for the requested mode.
    
    Args:
        format_mode: 'bhav', 'chunks', or 'distribution'
        print_func: Function to call for output
        metrics: Optional metrics object for formatters that need it
    
    Returns:
        OutputFormatter instance
    """
    formatters = {
        'bhav': BHAVAnalysisFormatter,
        'chunks': ChunkInventoryFormatter,
        'distribution': ChunkDistributionFormatter,
    }
    
    formatter_class = formatters.get(format_mode, BHAVAnalysisFormatter)
    if format_mode == 'distribution' and metrics:
        return formatter_class(print_func, metrics)
    return formatter_class(print_func)
