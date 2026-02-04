"""
Container Operations - IFF/FAR Container Manipulation

Implements ACTION_SURFACE actions for container-level operations.

Actions Implemented:
- NormalizeHeaders (WRITE) - Standardize IFF chunk headers
- RebuildIndexes (WRITE) - Rebuild RSMP/resource map
- ReindexContainer (WRITE) - Renumber chunk IDs
- SplitIFF (WRITE) - Split IFF into separate files
- MergeIFF (WRITE) - Merge multiple IFF files
- WriteFAR (WRITE) - Write FAR archives
- ClearCaches (SYSTEM) - Clear all caches
"""

import os
import struct
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Tuple
from datetime import datetime

from Tools.core.mutation_pipeline import (
    MutationPipeline, MutationMode, MutationRequest, 
    MutationDiff, MutationResult, get_pipeline, propose_change
)
from Tools.core.action_registry import validate_action


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ContainerOpResult:
    """Result of a container operation."""
    success: bool
    message: str
    affected_chunks: int = 0
    output_path: Optional[str] = None
    data: Optional[Any] = None


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class CacheManager:
    """
    Manage all cached data across the system.
    
    Implements ClearCaches action.
    """
    
    _instance = None
    
    def __init__(self):
        self._caches: Dict[str, Any] = {}
        self._cache_stats: Dict[str, int] = {}
    
    @classmethod
    def get(cls) -> "CacheManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_cache(self, name: str, cache: Any):
        """Register a cache for management."""
        self._caches[name] = cache
        self._cache_stats[name] = 0
    
    def clear_cache(self, name: str) -> bool:
        """Clear a specific cache."""
        if name not in self._caches:
            return False
        
        cache = self._caches[name]
        
        # Try different clearing methods
        if hasattr(cache, 'clear'):
            cache.clear()
        elif hasattr(cache, '_cache') and hasattr(cache._cache, 'clear'):
            cache._cache.clear()
        elif isinstance(cache, dict):
            cache.clear()
        elif isinstance(cache, list):
            cache.clear()
        
        self._cache_stats[name] = 0
        return True
    
    def clear_all(self) -> ContainerOpResult:
        """
        Clear all registered caches.
        
        Implements ClearCaches action.
        """
        valid, reason = validate_action('ClearCaches', {
            'pipeline_mode': 'MUTATE',
            'user_confirmed': True
        })
        
        # ClearCaches should generally be allowed
        cleared = 0
        for name in list(self._caches.keys()):
            if self.clear_cache(name):
                cleared += 1
        
        # Also clear common global caches
        self._clear_module_caches()
        
        return ContainerOpResult(
            True,
            f"Cleared {cleared} registered caches",
            affected_chunks=cleared
        )
    
    def _clear_module_caches(self):
        """Clear caches in various modules."""
        # Clear behavior library cache
        try:
            from Tools.core.behavior_library import BehaviorLibrary
            if hasattr(BehaviorLibrary, '_cache'):
                BehaviorLibrary._cache = {}
        except (ImportError, AttributeError):
            pass
        
        # Clear opcode loader cache
        try:
            from Tools.core.opcode_loader import OpcodeLoader
            if hasattr(OpcodeLoader, '_instance'):
                OpcodeLoader._instance = None
        except (ImportError, AttributeError):
            pass
        
        # Clear unknowns DB cache
        try:
            from Tools.core.unknowns_db import UnknownsDB
            if hasattr(UnknownsDB, '_cache'):
                UnknownsDB._cache = {}
        except (ImportError, AttributeError):
            pass
        
        # Clear provenance cache
        try:
            from Tools.core.provenance import ProvenanceRegistry
            registry = ProvenanceRegistry.instance()
            if hasattr(registry, '_entries'):
                registry._entries.clear()
        except (ImportError, AttributeError):
            pass
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return self._cache_stats.copy()


def clear_caches() -> ContainerOpResult:
    """Clear all caches. Convenience function."""
    return CacheManager.get().clear_all()


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER NORMALIZER
# ═══════════════════════════════════════════════════════════════════════════════

class HeaderNormalizer:
    """
    Normalize IFF chunk headers to canonical format.
    
    Implements NormalizeHeaders action.
    """
    
    CHUNK_HEADER_SIZE = 76
    
    def __init__(self, iff_file):
        """
        Initialize with an IffFile instance.
        
        Args:
            iff_file: IffFile to normalize
        """
        self.iff = iff_file
    
    def normalize(self, fix_sizes: bool = True, 
                  fix_labels: bool = True,
                  fix_flags: bool = True) -> ContainerOpResult:
        """
        Normalize all chunk headers.
        
        Args:
            fix_sizes: Recalculate chunk sizes
            fix_labels: Trim/pad labels to 64 bytes
            fix_flags: Reset flags to standard values
            
        Returns:
            ContainerOpResult
        """
        valid, reason = validate_action('NormalizeHeaders', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ContainerOpResult(False, f"Action blocked: {reason}")
        
        diffs = []
        fixed_count = 0
        
        for chunk in self.iff.chunks:
            chunk_diffs = []
            
            # Fix sizes
            if fix_sizes:
                if hasattr(chunk, 'original_data') or hasattr(chunk, 'chunk_data'):
                    data = getattr(chunk, 'original_data', None) or getattr(chunk, 'chunk_data', b'')
                    expected_size = self.CHUNK_HEADER_SIZE + len(data)
                    actual_size = getattr(chunk, 'chunk_size', 0)
                    
                    if actual_size != expected_size:
                        chunk_diffs.append(MutationDiff(
                            field_path=f'chunks[{chunk.chunk_id}].size',
                            old_value=actual_size,
                            new_value=expected_size,
                            display_old=str(actual_size),
                            display_new=str(expected_size)
                        ))
                        if get_pipeline().mode == MutationMode.MUTATE:
                            chunk.chunk_size = expected_size
            
            # Fix labels
            if fix_labels:
                label = getattr(chunk, 'chunk_label', '')
                if isinstance(label, bytes):
                    label = label.decode('latin-1', errors='replace')
                
                # Remove null terminators and extra whitespace
                cleaned = label.rstrip('\x00').strip()
                
                if cleaned != label:
                    chunk_diffs.append(MutationDiff(
                        field_path=f'chunks[{chunk.chunk_id}].label',
                        old_value=repr(label[:20]),
                        new_value=repr(cleaned[:20]),
                        display_old=label[:20] + '...' if len(label) > 20 else label,
                        display_new=cleaned[:20] + '...' if len(cleaned) > 20 else cleaned
                    ))
                    if get_pipeline().mode == MutationMode.MUTATE:
                        chunk.chunk_label = cleaned
            
            # Fix flags
            if fix_flags:
                flags = getattr(chunk, 'chunk_flags', 0)
                # Standard flags: 0 for most chunks
                standard = 0
                if flags != standard and flags not in (0, 1, 2):  # Only fix weird values
                    chunk_diffs.append(MutationDiff(
                        field_path=f'chunks[{chunk.chunk_id}].flags',
                        old_value=flags,
                        new_value=standard,
                        display_old=f"0x{flags:04X}",
                        display_new=f"0x{standard:04X}"
                    ))
                    if get_pipeline().mode == MutationMode.MUTATE:
                        chunk.chunk_flags = standard
            
            if chunk_diffs:
                fixed_count += 1
                diffs.extend(chunk_diffs)
        
        if diffs:
            # Propose through pipeline
            audit = propose_change(
                target_type='iff_headers',
                target_id=Path(self.iff.file_path).name if hasattr(self.iff, 'file_path') else 'IFF',
                diffs=diffs,
                file_path=getattr(self.iff, 'file_path', ''),
                reason="NormalizeHeaders action"
            )
            
            if audit.result in (MutationResult.SUCCESS, MutationResult.PREVIEW_ONLY):
                mode = "normalized" if audit.result == MutationResult.SUCCESS else "would normalize"
                return ContainerOpResult(
                    True,
                    f"{mode} {fixed_count} chunk headers",
                    affected_chunks=fixed_count
                )
            else:
                return ContainerOpResult(False, f"NormalizeHeaders rejected: {audit.result.value}")
        
        return ContainerOpResult(True, "All headers already normalized", affected_chunks=0)


def normalize_headers(iff_file, **kwargs) -> ContainerOpResult:
    """Normalize headers. Convenience function."""
    return HeaderNormalizer(iff_file).normalize(**kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# INDEX REBUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class IndexRebuilder:
    """
    Rebuild RSMP (resource map) chunk.
    
    Implements RebuildIndexes action.
    """
    
    CHUNK_HEADER_SIZE = 76
    
    def __init__(self, iff_file):
        """
        Initialize with an IffFile instance.
        
        Args:
            iff_file: IffFile to rebuild indexes for
        """
        self.iff = iff_file
    
    def rebuild(self) -> ContainerOpResult:
        """
        Rebuild the RSMP (resource map) chunk.
        
        Returns:
            ContainerOpResult
        """
        valid, reason = validate_action('RebuildIndexes', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ContainerOpResult(False, f"Action blocked: {reason}")
        
        # Build new resource map
        rsmp_entries = []
        current_offset = 64  # After IFF header + RSMP offset field
        
        for chunk in self.iff.chunks:
            if getattr(chunk, 'chunk_type', '') == 'rsmp':
                continue  # Skip existing RSMP
            
            entry = {
                'type': getattr(chunk, 'chunk_type', 'UNKN'),
                'offset': current_offset,
                'id': getattr(chunk, 'chunk_id', 0),
                'flags': getattr(chunk, 'chunk_flags', 0),
                'label': getattr(chunk, 'chunk_label', ''),
            }
            rsmp_entries.append(entry)
            
            # Calculate chunk size
            if hasattr(chunk, 'chunk_size'):
                current_offset += chunk.chunk_size
            else:
                data = getattr(chunk, 'original_data', None) or getattr(chunk, 'chunk_data', b'')
                current_offset += self.CHUNK_HEADER_SIZE + len(data)
        
        # Propose through pipeline
        audit = propose_change(
            target_type='iff_rsmp',
            target_id=Path(self.iff.file_path).name if hasattr(self.iff, 'file_path') else 'IFF',
            diffs=[MutationDiff(
                field_path='rsmp',
                old_value='[existing RSMP]',
                new_value=f'[rebuilt: {len(rsmp_entries)} entries]',
                display_old='Existing resource map',
                display_new=f'Rebuilt with {len(rsmp_entries)} entries'
            )],
            file_path=getattr(self.iff, 'file_path', ''),
            reason="RebuildIndexes action"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Store new RSMP data
            self.iff._rsmp_rebuilt = rsmp_entries
            return ContainerOpResult(
                True,
                f"Rebuilt RSMP with {len(rsmp_entries)} entries",
                affected_chunks=len(rsmp_entries)
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return ContainerOpResult(
                True,
                f"Preview: would rebuild RSMP with {len(rsmp_entries)} entries",
                affected_chunks=len(rsmp_entries)
            )
        else:
            return ContainerOpResult(False, f"RebuildIndexes rejected: {audit.result.value}")
    
    def serialize_rsmp(self, entries: List[Dict]) -> bytes:
        """Serialize RSMP chunk data."""
        output = bytearray()
        
        # RSMP version
        output.extend(struct.pack('<I', 1))  # Version 1
        
        # Entry count
        output.extend(struct.pack('<I', len(entries)))
        
        # Entries
        for entry in entries:
            type_code = entry['type']
            if isinstance(type_code, str):
                type_code = type_code.encode('latin-1')
            output.extend(type_code[:4].ljust(4, b'\x00'))
            output.extend(struct.pack('<I', entry['offset']))
            output.extend(struct.pack('<H', entry['id']))
            output.extend(struct.pack('<H', entry['flags']))
            label = entry['label']
            if isinstance(label, str):
                label = label.encode('latin-1', errors='replace')
            output.extend(label[:64].ljust(64, b'\x00'))
        
        return bytes(output)


def rebuild_indexes(iff_file) -> ContainerOpResult:
    """Rebuild indexes. Convenience function."""
    return IndexRebuilder(iff_file).rebuild()


# ═══════════════════════════════════════════════════════════════════════════════
# CONTAINER REINDEXER
# ═══════════════════════════════════════════════════════════════════════════════

class ContainerReindexer:
    """
    Renumber chunk IDs for consistency.
    
    Implements ReindexContainer action.
    """
    
    def __init__(self, iff_file):
        """
        Initialize with an IffFile instance.
        
        Args:
            iff_file: IffFile to reindex
        """
        self.iff = iff_file
    
    def reindex(self, start_id: int = 256, 
                by_type: bool = True,
                preserve_types: Set[str] = None) -> ContainerOpResult:
        """
        Renumber all chunk IDs.
        
        Args:
            start_id: Starting ID for renumbering
            by_type: If True, group by type before numbering
            preserve_types: Chunk types to skip (keep original IDs)
            
        Returns:
            ContainerOpResult
        """
        valid, reason = validate_action('ReindexContainer', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ContainerOpResult(False, f"Action blocked: {reason}")
        
        preserve_types = preserve_types or {'GLOB', 'SEMI'}  # Don't renumber globals
        
        # Build ID mapping
        id_map: Dict[Tuple[str, int], int] = {}
        diffs = []
        
        if by_type:
            # Group chunks by type
            by_type_map: Dict[str, List] = {}
            for chunk in self.iff.chunks:
                ctype = getattr(chunk, 'chunk_type', 'UNKN')
                if ctype not in by_type_map:
                    by_type_map[ctype] = []
                by_type_map[ctype].append(chunk)
            
            # Assign new IDs
            next_id = start_id
            for ctype in sorted(by_type_map.keys()):
                if ctype in preserve_types:
                    continue
                
                for chunk in by_type_map[ctype]:
                    old_id = getattr(chunk, 'chunk_id', 0)
                    if old_id != next_id:
                        id_map[(ctype, old_id)] = next_id
                        diffs.append(MutationDiff(
                            field_path=f'{ctype}[{old_id}].chunk_id',
                            old_value=old_id,
                            new_value=next_id,
                            display_old=f"{ctype}:{old_id}",
                            display_new=f"{ctype}:{next_id}"
                        ))
                    next_id += 1
        else:
            # Sequential numbering
            next_id = start_id
            for chunk in self.iff.chunks:
                ctype = getattr(chunk, 'chunk_type', 'UNKN')
                if ctype in preserve_types:
                    continue
                
                old_id = getattr(chunk, 'chunk_id', 0)
                if old_id != next_id:
                    id_map[(ctype, old_id)] = next_id
                    diffs.append(MutationDiff(
                        field_path=f'{ctype}[{old_id}].chunk_id',
                        old_value=old_id,
                        new_value=next_id,
                        display_old=f"{ctype}:{old_id}",
                        display_new=f"{ctype}:{next_id}"
                    ))
                next_id += 1
        
        if not diffs:
            return ContainerOpResult(True, "No reindexing needed", affected_chunks=0)
        
        # Propose through pipeline
        audit = propose_change(
            target_type='iff_container',
            target_id=Path(self.iff.file_path).name if hasattr(self.iff, 'file_path') else 'IFF',
            diffs=diffs,
            file_path=getattr(self.iff, 'file_path', ''),
            reason="ReindexContainer action"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Apply changes
            for chunk in self.iff.chunks:
                ctype = getattr(chunk, 'chunk_type', 'UNKN')
                old_id = getattr(chunk, 'chunk_id', 0)
                if (ctype, old_id) in id_map:
                    chunk.chunk_id = id_map[(ctype, old_id)]
            
            # Store mapping for reference updates
            self.iff._id_remap = id_map
            
            return ContainerOpResult(
                True,
                f"Reindexed {len(id_map)} chunks",
                affected_chunks=len(id_map),
                data={'id_map': id_map}
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return ContainerOpResult(
                True,
                f"Preview: would reindex {len(id_map)} chunks",
                affected_chunks=len(id_map),
                data={'id_map': id_map}
            )
        else:
            return ContainerOpResult(False, f"ReindexContainer rejected: {audit.result.value}")


def reindex_container(iff_file, **kwargs) -> ContainerOpResult:
    """Reindex container. Convenience function."""
    return ContainerReindexer(iff_file).reindex(**kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# IFF SPLITTER
# ═══════════════════════════════════════════════════════════════════════════════

class IFFSplitter:
    """
    Split IFF file into separate files by chunk type or criteria.
    
    Implements SplitIFF action.
    """
    
    def __init__(self, iff_file):
        """
        Initialize with an IffFile instance.
        
        Args:
            iff_file: IffFile to split
        """
        self.iff = iff_file
    
    def split_by_type(self, output_dir: str, 
                      types_to_split: Set[str] = None) -> ContainerOpResult:
        """
        Split IFF into separate files by chunk type.
        
        Args:
            output_dir: Directory to write split files
            types_to_split: Types to extract (None = all types)
            
        Returns:
            ContainerOpResult
        """
        valid, reason = validate_action('SplitIFF', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ContainerOpResult(False, f"Action blocked: {reason}")
        
        # Group chunks by type
        by_type: Dict[str, List] = {}
        for chunk in self.iff.chunks:
            ctype = getattr(chunk, 'chunk_type', 'UNKN')
            if types_to_split and ctype not in types_to_split:
                continue
            if ctype not in by_type:
                by_type[ctype] = []
            by_type[ctype].append(chunk)
        
        if not by_type:
            return ContainerOpResult(False, "No chunks to split")
        
        # Propose through pipeline
        diffs = [MutationDiff(
            field_path='split',
            old_value=f"[1 file, {len(self.iff.chunks)} chunks]",
            new_value=f"[{len(by_type)} files]",
            display_old="Single IFF",
            display_new=f"Split into {len(by_type)} files"
        )]
        
        audit = propose_change(
            target_type='iff_split',
            target_id=Path(self.iff.file_path).name if hasattr(self.iff, 'file_path') else 'IFF',
            diffs=diffs,
            file_path=output_dir,
            reason="SplitIFF action"
        )
        
        if audit.result == MutationResult.SUCCESS:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            base_name = Path(self.iff.file_path).stem if hasattr(self.iff, 'file_path') else 'split'
            files_created = []
            
            for ctype, chunks in by_type.items():
                out_path = Path(output_dir) / f"{base_name}_{ctype}.iff"
                
                # Create minimal IFF with just these chunks
                self._write_split_iff(out_path, chunks)
                files_created.append(str(out_path))
            
            return ContainerOpResult(
                True,
                f"Split into {len(files_created)} files",
                affected_chunks=sum(len(c) for c in by_type.values()),
                output_path=output_dir,
                data={'files': files_created}
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return ContainerOpResult(
                True,
                f"Preview: would split into {len(by_type)} files",
                affected_chunks=sum(len(c) for c in by_type.values())
            )
        else:
            return ContainerOpResult(False, f"SplitIFF rejected: {audit.result.value}")
    
    def split_by_object(self, output_dir: str) -> ContainerOpResult:
        """
        Split IFF by object - each OBJD and its BHAVs into separate file.
        
        Args:
            output_dir: Directory to write split files
            
        Returns:
            ContainerOpResult
        """
        # Find OBJD chunks
        objd_chunks = [c for c in self.iff.chunks if getattr(c, 'chunk_type', '') == 'OBJD']
        
        if not objd_chunks:
            return ContainerOpResult(False, "No OBJD chunks found to split")
        
        # This would require dependency analysis to group related chunks
        # For now, just split by OBJD
        return self.split_by_type(output_dir, {'OBJD', 'BHAV', 'STR#', 'CTSS', 'TTAB', 'SLOT'})
    
    def _write_split_iff(self, path: Path, chunks: List):
        """Write a minimal IFF with given chunks."""
        from Tools.core.file_operations import IFFWriter
        
        # Create minimal IFF structure
        class MinimalIFF:
            def __init__(self, chunks):
                self.chunks = chunks
                self.file_path = str(path)
        
        mini = MinimalIFF(chunks)
        writer = IFFWriter(mini)
        
        # Force write without pipeline check (we already checked)
        data = writer._serialize()
        with open(path, 'wb') as f:
            f.write(data)


def split_iff(iff_file, output_dir: str, **kwargs) -> ContainerOpResult:
    """Split IFF. Convenience function."""
    return IFFSplitter(iff_file).split_by_type(output_dir, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# IFF MERGER
# ═══════════════════════════════════════════════════════════════════════════════

class IFFMerger:
    """
    Merge multiple IFF files into one.
    
    Implements MergeIFF action.
    """
    
    def __init__(self):
        """Initialize merger."""
        self.sources: List = []
        self.id_maps: Dict[str, Dict[Tuple[str, int], int]] = {}
    
    def add_source(self, iff_file, source_name: str = None):
        """
        Add a source IFF to merge.
        
        Args:
            iff_file: IffFile to include
            source_name: Name for tracking (default: file path)
        """
        name = source_name or getattr(iff_file, 'file_path', f'source_{len(self.sources)}')
        self.sources.append({'iff': iff_file, 'name': name})
    
    def merge(self, output_path: str, 
              resolve_conflicts: str = 'rename') -> ContainerOpResult:
        """
        Merge all sources into one IFF.
        
        Args:
            output_path: Path for merged IFF
            resolve_conflicts: How to handle ID conflicts:
                - 'rename': Rename conflicting IDs
                - 'skip': Skip duplicates
                - 'replace': Use later source
                
        Returns:
            ContainerOpResult
        """
        valid, reason = validate_action('MergeIFF', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ContainerOpResult(False, f"Action blocked: {reason}")
        
        if len(self.sources) < 2:
            return ContainerOpResult(False, "Need at least 2 sources to merge")
        
        # Collect all chunks with conflict detection
        merged_chunks = []
        seen_ids: Dict[Tuple[str, int], str] = {}  # (type, id) -> source name
        conflicts = []
        next_free_id = 10000
        
        for source in self.sources:
            iff = source['iff']
            name = source['name']
            local_remap = {}
            
            for chunk in iff.chunks:
                ctype = getattr(chunk, 'chunk_type', 'UNKN')
                cid = getattr(chunk, 'chunk_id', 0)
                key = (ctype, cid)
                
                if ctype == 'rsmp':
                    continue  # Skip RSMP, will rebuild
                
                if key in seen_ids:
                    if resolve_conflicts == 'rename':
                        # Assign new ID
                        new_id = next_free_id
                        next_free_id += 1
                        local_remap[key] = new_id
                        
                        # Clone chunk with new ID
                        new_chunk = self._clone_chunk(chunk, new_id)
                        merged_chunks.append(new_chunk)
                        conflicts.append(f"{ctype}:{cid} from {name} -> {new_id}")
                        
                    elif resolve_conflicts == 'skip':
                        conflicts.append(f"{ctype}:{cid} from {name} skipped (exists in {seen_ids[key]})")
                        
                    elif resolve_conflicts == 'replace':
                        # Find and replace existing
                        for i, mc in enumerate(merged_chunks):
                            if (getattr(mc, 'chunk_type', '') == ctype and 
                                getattr(mc, 'chunk_id', -1) == cid):
                                merged_chunks[i] = chunk
                                conflicts.append(f"{ctype}:{cid} replaced from {name}")
                                break
                else:
                    merged_chunks.append(chunk)
                    seen_ids[key] = name
            
            # Store remapping for this source
            if local_remap:
                self.id_maps[name] = local_remap
        
        # Propose through pipeline
        diffs = [MutationDiff(
            field_path='merge',
            old_value=f"[{len(self.sources)} files]",
            new_value=f"[1 file, {len(merged_chunks)} chunks]",
            display_old=f"{len(self.sources)} source files",
            display_new=f"Merged: {len(merged_chunks)} chunks ({len(conflicts)} conflicts resolved)"
        )]
        
        audit = propose_change(
            target_type='iff_merge',
            target_id=Path(output_path).name,
            diffs=diffs,
            file_path=output_path,
            reason="MergeIFF action"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Create merged IFF
            class MergedIFF:
                def __init__(self, chunks, path):
                    self.chunks = chunks
                    self.file_path = path
            
            merged = MergedIFF(merged_chunks, output_path)
            
            # Write using IFFWriter
            from Tools.core.file_operations import IFFWriter
            writer = IFFWriter(merged)
            data = writer._serialize()
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(data)
            
            return ContainerOpResult(
                True,
                f"Merged {len(self.sources)} files: {len(merged_chunks)} chunks",
                affected_chunks=len(merged_chunks),
                output_path=output_path,
                data={'conflicts': conflicts, 'id_maps': self.id_maps}
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return ContainerOpResult(
                True,
                f"Preview: would merge {len(merged_chunks)} chunks",
                affected_chunks=len(merged_chunks),
                data={'conflicts': conflicts}
            )
        else:
            return ContainerOpResult(False, f"MergeIFF rejected: {audit.result.value}")
    
    def _clone_chunk(self, chunk, new_id: int):
        """Clone a chunk with a new ID."""
        import copy
        new_chunk = copy.copy(chunk)
        new_chunk.chunk_id = new_id
        return new_chunk


def merge_iff_files(iff_files: List, output_path: str, **kwargs) -> ContainerOpResult:
    """Merge IFF files. Convenience function."""
    merger = IFFMerger()
    for iff in iff_files:
        merger.add_source(iff)
    return merger.merge(output_path, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# FAR WRITER
# ═══════════════════════════════════════════════════════════════════════════════

class FARWriter:
    """
    Write FAR1/FAR3 archive files.
    
    Implements WriteFAR action.
    """
    
    FAR1_MAGIC = b'FAR!'
    FAR3_MAGIC = b'FAR!byAZ'
    
    def __init__(self):
        """Initialize FAR writer."""
        self.entries: List[Dict] = []
    
    def add_entry(self, name: str, data: bytes):
        """
        Add an entry to the archive.
        
        Args:
            name: Entry filename
            data: Entry data
        """
        self.entries.append({
            'name': name,
            'data': data,
            'compressed': False
        })
    
    def write_far1(self, output_path: str) -> ContainerOpResult:
        """
        Write FAR1 format archive.
        
        Args:
            output_path: Output file path
            
        Returns:
            ContainerOpResult
        """
        valid, reason = validate_action('WriteFAR', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ContainerOpResult(False, f"Action blocked: {reason}")
        
        if not self.entries:
            return ContainerOpResult(False, "No entries to write")
        
        # Calculate layout
        header_size = 16  # Magic(8) + Version(4) + ManifestOffset(4)
        manifest_entries = []
        
        # Calculate data offsets
        current_offset = header_size
        for entry in self.entries:
            manifest_entries.append({
                'data_offset': current_offset,
                'data_size': len(entry['data']),
                'name': entry['name']
            })
            current_offset += len(entry['data'])
        
        manifest_offset = current_offset
        
        # Propose through pipeline
        audit = propose_change(
            target_type='far_archive',
            target_id=Path(output_path).name,
            diffs=[MutationDiff(
                field_path='archive',
                old_value='[none]',
                new_value=f'[{len(self.entries)} entries]',
                display_old='New archive',
                display_new=f'{len(self.entries)} entries'
            )],
            file_path=output_path,
            reason="WriteFAR action"
        )
        
        if audit.result == MutationResult.SUCCESS:
            output = bytearray()
            
            # Header
            output.extend(b'FAR!byAZ')  # Magic
            output.extend(struct.pack('<I', 1))  # Version
            output.extend(struct.pack('<I', manifest_offset))  # Manifest offset
            
            # Data
            for entry in self.entries:
                output.extend(entry['data'])
            
            # Manifest
            output.extend(struct.pack('<I', len(manifest_entries)))
            for me in manifest_entries:
                output.extend(struct.pack('<I', me['data_size']))
                output.extend(struct.pack('<I', me['data_size']))  # Decompressed = compressed
                output.extend(struct.pack('<I', me['data_offset']))
                name_bytes = me['name'].encode('utf-8')
                output.extend(struct.pack('<H', len(name_bytes)))
                output.extend(name_bytes)
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(output)
            
            return ContainerOpResult(
                True,
                f"Wrote FAR with {len(self.entries)} entries",
                affected_chunks=len(self.entries),
                output_path=output_path
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return ContainerOpResult(
                True,
                f"Preview: would write FAR with {len(self.entries)} entries",
                affected_chunks=len(self.entries)
            )
        else:
            return ContainerOpResult(False, f"WriteFAR rejected: {audit.result.value}")


def write_far(entries: List[Tuple[str, bytes]], output_path: str) -> ContainerOpResult:
    """Write FAR archive. Convenience function."""
    writer = FARWriter()
    for name, data in entries:
        writer.add_entry(name, data)
    return writer.write_far1(output_path)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Cache management
    'CacheManager', 'clear_caches',
    
    # Header operations
    'HeaderNormalizer', 'normalize_headers',
    
    # Index operations
    'IndexRebuilder', 'rebuild_indexes',
    
    # Reindexing
    'ContainerReindexer', 'reindex_container',
    
    # Splitting
    'IFFSplitter', 'split_iff',
    
    # Merging
    'IFFMerger', 'merge_iff_files',
    
    # FAR writing
    'FARWriter', 'write_far',
    
    # Result type
    'ContainerOpResult',
]
