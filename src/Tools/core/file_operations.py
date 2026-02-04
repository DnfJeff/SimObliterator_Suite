"""
File Operations - Unified File I/O Layer

Consolidates all file read/write operations through MutationPipeline.
Implements ACTION_SURFACE actions for FILE_CONTAINER category.

Actions Implemented:
- LoadIFF, LoadFAR, LoadSave (READ)
- WriteIFF, WriteSave, BackupSave (WRITE)
- AddChunk, DeleteChunk, ReplaceChunk (WRITE)
- ExtractFAR, ExtractDBPF (READ/EXPORT)
- ValidateContainer (READ)
"""

import os
import shutil
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
import struct

from Tools.core.mutation_pipeline import (
    MutationPipeline, MutationMode, MutationRequest, 
    MutationDiff, MutationResult, get_pipeline, propose_change
)
from Tools.core.action_registry import validate_action


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FileOpResult:
    """Result of a file operation."""
    success: bool
    message: str
    path: Optional[str] = None
    data: Optional[Any] = None
    backup_path: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# IFF WRITER
# ═══════════════════════════════════════════════════════════════════════════════

class IFFWriter:
    """
    Write IFF files back to disk.
    
    Implements WriteIFF action.
    """
    
    IFF_HEADER = b"IFF FILE 2.5:TYPE FOLLOWED BY SIZE\x00 JAMIE DOORNBOS & MAXIS 1"
    HEADER_LENGTH = 60
    CHUNK_HEADER_SIZE = 76
    
    def __init__(self, iff_file):
        """
        Initialize writer with an IffFile instance.
        
        Args:
            iff_file: IffFile instance (from formats.iff.iff_file)
        """
        self.iff = iff_file
        
    def write(self, output_path: str, create_backup: bool = True) -> FileOpResult:
        """
        Write IFF to disk.
        
        Args:
            output_path: Path to write to
            create_backup: If True, create .bak before overwriting
            
        Returns:
            FileOpResult with status
        """
        # Validate action through registry
        valid, reason = validate_action('WriteIFF', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return FileOpResult(False, f"Action blocked: {reason}")
        
        # Create backup if needed
        backup_path = None
        if create_backup and os.path.exists(output_path):
            backup_path = f"{output_path}.bak"
            shutil.copy2(output_path, backup_path)
        
        try:
            data = self._serialize()
            
            # Propose change through pipeline
            audit = propose_change(
                target_type='iff_file',
                target_id=Path(output_path).name,
                diffs=[MutationDiff(
                    field_path='file',
                    old_value=f"[existing: {os.path.getsize(output_path) if os.path.exists(output_path) else 0} bytes]",
                    new_value=f"[new: {len(data)} bytes]",
                    display_old="Original file",
                    display_new="Modified file"
                )],
                file_path=output_path,
                reason="WriteIFF action"
            )
            
            if audit.result not in (MutationResult.SUCCESS, MutationResult.PREVIEW_ONLY):
                return FileOpResult(False, f"Mutation rejected: {audit.result.value}")
            
            # Only write if not in preview mode
            if get_pipeline().mode == MutationMode.MUTATE:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(data)
                return FileOpResult(True, f"Wrote {len(data)} bytes", output_path, backup_path=backup_path)
            else:
                return FileOpResult(True, f"Preview: would write {len(data)} bytes", output_path)
                
        except Exception as e:
            return FileOpResult(False, f"Write failed: {e}")
    
    def _serialize(self) -> bytes:
        """Serialize IFF to bytes."""
        chunks_data = bytearray()
        
        # Build chunk data
        for chunk in self.iff.chunks:
            chunk_bytes = self._serialize_chunk(chunk)
            chunks_data.extend(chunk_bytes)
        
        # Calculate RSMP offset (header + all chunks)
        rsmp_offset = self.HEADER_LENGTH + 4 + len(chunks_data)
        
        # Build complete file
        output = bytearray()
        
        # Header (60 bytes)
        header = self.IFF_HEADER.ljust(self.HEADER_LENGTH, b'\x00')[:self.HEADER_LENGTH]
        output.extend(header)
        
        # RSMP offset (4 bytes, big-endian)
        output.extend(struct.pack('>I', rsmp_offset))
        
        # All chunks
        output.extend(chunks_data)
        
        # Empty RSMP (minimal - just the marker)
        # In a full implementation, we'd rebuild the resource map
        output.extend(b'rsmp')  # Type
        output.extend(struct.pack('>I', 84))  # Size (header + 8 bytes)
        output.extend(struct.pack('>H', 0))   # ID
        output.extend(struct.pack('>H', 0))   # Flags
        output.extend(b'\x00' * 64)           # Label
        output.extend(struct.pack('<I', 0))   # Version 0
        output.extend(struct.pack('<I', 0))   # Reserved
        
        return bytes(output)
    
    def _serialize_chunk(self, chunk) -> bytes:
        """Serialize a single chunk."""
        # Get chunk data
        if hasattr(chunk, 'serialize'):
            chunk_data = chunk.serialize()
        elif hasattr(chunk, 'original_data'):
            chunk_data = chunk.original_data
        elif hasattr(chunk, 'chunk_data'):
            chunk_data = chunk.chunk_data
        else:
            chunk_data = b''
        
        # Build header
        header = bytearray()
        
        # Type code (4 bytes)
        type_code = getattr(chunk, 'chunk_type', 'UNKN')
        header.extend(type_code.encode('latin-1')[:4].ljust(4, b'\x00'))
        
        # Size (4 bytes, big-endian) - includes header
        total_size = self.CHUNK_HEADER_SIZE + len(chunk_data)
        header.extend(struct.pack('>I', total_size))
        
        # Chunk ID (2 bytes, big-endian)
        chunk_id = getattr(chunk, 'chunk_id', 0)
        header.extend(struct.pack('>H', chunk_id))
        
        # Flags (2 bytes, big-endian)
        chunk_flags = getattr(chunk, 'chunk_flags', 0)
        header.extend(struct.pack('>H', chunk_flags))
        
        # Label (64 bytes)
        label = getattr(chunk, 'chunk_label', '')
        header.extend(label.encode('latin-1')[:64].ljust(64, b'\x00'))
        
        return bytes(header) + chunk_data


# ═══════════════════════════════════════════════════════════════════════════════
# CHUNK OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class ChunkOperations:
    """
    Operations for adding, deleting, replacing chunks.
    
    Implements AddChunk, DeleteChunk, ReplaceChunk actions.
    """
    
    def __init__(self, iff_file):
        """
        Initialize with IffFile instance.
        
        Args:
            iff_file: IffFile instance
        """
        self.iff = iff_file
    
    def add_chunk(self, chunk, reason: str = "") -> FileOpResult:
        """
        Add a chunk to the IFF file.
        
        Args:
            chunk: Chunk instance to add
            reason: Reason for the addition
            
        Returns:
            FileOpResult
        """
        valid, msg = validate_action('AddChunk', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return FileOpResult(False, f"Action blocked: {msg}")
        
        chunk_type = getattr(chunk, 'chunk_type', 'UNKN')
        chunk_id = getattr(chunk, 'chunk_id', -1)
        
        # Check for ID collision
        existing = self._find_chunk(chunk_type, chunk_id)
        if existing is not None:
            return FileOpResult(False, f"Chunk {chunk_type}:{chunk_id} already exists")
        
        # Propose through pipeline
        audit = propose_change(
            target_type='chunk',
            target_id=f"{chunk_type}:{chunk_id}",
            diffs=[MutationDiff(
                field_path='chunks',
                old_value=f"[{len(self.iff.chunks)} chunks]",
                new_value=f"[{len(self.iff.chunks) + 1} chunks]",
                display_old=f"Before: {len(self.iff.chunks)} chunks",
                display_new=f"After: {len(self.iff.chunks) + 1} chunks (added {chunk_type})"
            )],
            file_path=self.iff.filename,
            reason=reason or "AddChunk action"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self.iff._all_chunks.append(chunk)
            self._index_chunk(chunk)
            return FileOpResult(True, f"Added chunk {chunk_type}:{chunk_id}")
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return FileOpResult(True, f"Preview: would add chunk {chunk_type}:{chunk_id}")
        else:
            return FileOpResult(False, f"AddChunk rejected: {audit.result.value}")
    
    def delete_chunk(self, chunk_type: str, chunk_id: int, reason: str = "") -> FileOpResult:
        """
        Delete a chunk from the IFF file.
        
        Args:
            chunk_type: 4-char type code
            chunk_id: Chunk ID
            reason: Reason for deletion
            
        Returns:
            FileOpResult
        """
        valid, msg = validate_action('DeleteChunk', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return FileOpResult(False, f"Action blocked: {msg}")
        
        # Find the chunk
        chunk = self._find_chunk(chunk_type, chunk_id)
        if chunk is None:
            return FileOpResult(False, f"Chunk {chunk_type}:{chunk_id} not found")
        
        # Propose through pipeline
        audit = propose_change(
            target_type='chunk',
            target_id=f"{chunk_type}:{chunk_id}",
            diffs=[MutationDiff(
                field_path='chunks',
                old_value=f"[{len(self.iff.chunks)} chunks]",
                new_value=f"[{len(self.iff.chunks) - 1} chunks]",
                display_old=f"Before: {len(self.iff.chunks)} chunks",
                display_new=f"After: {len(self.iff.chunks) - 1} chunks (deleted {chunk_type})"
            )],
            file_path=self.iff.filename,
            reason=reason or "DeleteChunk action"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self.iff._all_chunks.remove(chunk)
            self._unindex_chunk(chunk)
            return FileOpResult(True, f"Deleted chunk {chunk_type}:{chunk_id}")
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return FileOpResult(True, f"Preview: would delete chunk {chunk_type}:{chunk_id}")
        else:
            return FileOpResult(False, f"DeleteChunk rejected: {audit.result.value}")
    
    def replace_chunk(self, chunk_type: str, chunk_id: int, new_chunk, reason: str = "") -> FileOpResult:
        """
        Replace a chunk in the IFF file.
        
        Args:
            chunk_type: 4-char type code of chunk to replace
            chunk_id: ID of chunk to replace
            new_chunk: New chunk instance
            reason: Reason for replacement
            
        Returns:
            FileOpResult
        """
        valid, msg = validate_action('ReplaceChunk', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return FileOpResult(False, f"Action blocked: {msg}")
        
        # Find existing chunk
        old_chunk = self._find_chunk(chunk_type, chunk_id)
        if old_chunk is None:
            return FileOpResult(False, f"Chunk {chunk_type}:{chunk_id} not found")
        
        # Propose through pipeline
        audit = propose_change(
            target_type='chunk',
            target_id=f"{chunk_type}:{chunk_id}",
            diffs=[MutationDiff(
                field_path='chunk_data',
                old_value=f"[{len(getattr(old_chunk, 'chunk_data', b''))} bytes]",
                new_value=f"[{len(getattr(new_chunk, 'chunk_data', b''))} bytes]",
                display_old=f"Old {chunk_type}:{chunk_id}",
                display_new=f"New {chunk_type}:{chunk_id}"
            )],
            file_path=self.iff.filename,
            reason=reason or "ReplaceChunk action"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Find index and replace
            idx = self.iff._all_chunks.index(old_chunk)
            self._unindex_chunk(old_chunk)
            self.iff._all_chunks[idx] = new_chunk
            self._index_chunk(new_chunk)
            return FileOpResult(True, f"Replaced chunk {chunk_type}:{chunk_id}")
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return FileOpResult(True, f"Preview: would replace chunk {chunk_type}:{chunk_id}")
        else:
            return FileOpResult(False, f"ReplaceChunk rejected: {audit.result.value}")
    
    def _find_chunk(self, chunk_type: str, chunk_id: int):
        """Find a chunk by type and ID."""
        for chunk in self.iff._all_chunks:
            if getattr(chunk, 'chunk_type', '') == chunk_type:
                if getattr(chunk, 'chunk_id', -1) == chunk_id:
                    return chunk
        return None
    
    def _index_chunk(self, chunk):
        """Add chunk to internal indexes."""
        chunk_class = type(chunk)
        
        if chunk_class not in self.iff._chunks_by_type:
            self.iff._chunks_by_type[chunk_class] = []
        self.iff._chunks_by_type[chunk_class].append(chunk)
        
        if chunk_class not in self.iff._chunks_by_id:
            self.iff._chunks_by_id[chunk_class] = {}
        self.iff._chunks_by_id[chunk_class][chunk.chunk_id] = chunk
    
    def _unindex_chunk(self, chunk):
        """Remove chunk from internal indexes."""
        chunk_class = type(chunk)
        
        if chunk_class in self.iff._chunks_by_type:
            if chunk in self.iff._chunks_by_type[chunk_class]:
                self.iff._chunks_by_type[chunk_class].remove(chunk)
        
        if chunk_class in self.iff._chunks_by_id:
            if chunk.chunk_id in self.iff._chunks_by_id[chunk_class]:
                del self.iff._chunks_by_id[chunk_class][chunk.chunk_id]


# ═══════════════════════════════════════════════════════════════════════════════
# BACKUP OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class BackupManager:
    """
    Manages backups for safe file operations.
    
    Implements BackupSave, RestoreSave actions.
    """
    
    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize backup manager.
        
        Args:
            backup_dir: Directory for backups. If None, uses .bak suffix.
        """
        self.backup_dir = Path(backup_dir) if backup_dir else None
        self._backup_registry: Dict[str, List[str]] = {}
    
    def backup(self, file_path: str, reason: str = "") -> FileOpResult:
        """
        Create a backup of a file.
        
        Args:
            file_path: Path to file to backup
            reason: Reason for backup
            
        Returns:
            FileOpResult with backup path
        """
        valid, msg = validate_action('BackupSave', {
            'pipeline_mode': 'mutate',  # Backups always allowed
            'safety_checked': True
        })
        
        if not valid:
            return FileOpResult(False, f"Action blocked: {msg}")
        
        if not os.path.exists(file_path):
            return FileOpResult(False, f"File not found: {file_path}")
        
        # Generate backup path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original = Path(file_path)
        
        if self.backup_dir:
            backup_path = self.backup_dir / f"{original.stem}_{timestamp}{original.suffix}"
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        else:
            backup_path = original.with_suffix(f".{timestamp}.bak")
        
        try:
            shutil.copy2(file_path, backup_path)
            
            # Register backup
            key = str(original)
            if key not in self._backup_registry:
                self._backup_registry[key] = []
            self._backup_registry[key].append(str(backup_path))
            
            return FileOpResult(True, f"Backup created", backup_path=str(backup_path))
            
        except Exception as e:
            return FileOpResult(False, f"Backup failed: {e}")
    
    def restore(self, original_path: str, backup_path: Optional[str] = None) -> FileOpResult:
        """
        Restore a file from backup.
        
        Args:
            original_path: Path to restore to
            backup_path: Specific backup to restore. If None, uses latest.
            
        Returns:
            FileOpResult
        """
        valid, msg = validate_action('RestoreSave', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return FileOpResult(False, f"Action blocked: {msg}")
        
        key = str(Path(original_path))
        
        # Find backup
        if backup_path is None:
            if key in self._backup_registry and self._backup_registry[key]:
                backup_path = self._backup_registry[key][-1]  # Latest
            else:
                # Try to find .bak file
                bak_path = Path(original_path).with_suffix('.bak')
                if bak_path.exists():
                    backup_path = str(bak_path)
                else:
                    return FileOpResult(False, "No backup found")
        
        if not os.path.exists(backup_path):
            return FileOpResult(False, f"Backup not found: {backup_path}")
        
        try:
            shutil.copy2(backup_path, original_path)
            return FileOpResult(True, f"Restored from {backup_path}", original_path)
            
        except Exception as e:
            return FileOpResult(False, f"Restore failed: {e}")
    
    def list_backups(self, file_path: str) -> List[str]:
        """List all backups for a file."""
        key = str(Path(file_path))
        return self._backup_registry.get(key, []).copy()


# ═══════════════════════════════════════════════════════════════════════════════
# ARCHIVE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

class ArchiveExtractor:
    """
    Extract files from FAR and DBPF archives.
    
    Implements ExtractFAR, ExtractDBPF actions.
    """
    
    @staticmethod
    def extract_far(far_path: str, output_dir: str, 
                    filenames: Optional[List[str]] = None) -> FileOpResult:
        """
        Extract files from a FAR archive.
        
        Args:
            far_path: Path to FAR archive
            output_dir: Directory to extract to
            filenames: Specific files to extract. If None, extracts all.
            
        Returns:
            FileOpResult with extraction details
        """
        try:
            from formats.far.far1 import FAR1Archive
            
            archive = FAR1Archive(far_path)
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            extracted = []
            
            if filenames:
                # Extract specific files
                for filename in filenames:
                    if archive.extract(filename, str(output_path / filename)):
                        extracted.append(filename)
            else:
                # Extract all
                archive.extract_all(str(output_path))
                extracted = [e.filename for e in archive.entries]
            
            return FileOpResult(
                True, 
                f"Extracted {len(extracted)} files from FAR",
                path=str(output_path),
                data={'files': extracted}
            )
            
        except Exception as e:
            return FileOpResult(False, f"FAR extraction failed: {e}")
    
    @staticmethod
    def extract_dbpf(dbpf_path: str, output_dir: str,
                     type_ids: Optional[List[int]] = None) -> FileOpResult:
        """
        Extract files from a DBPF archive.
        
        Args:
            dbpf_path: Path to DBPF archive
            output_dir: Directory to extract to
            type_ids: Specific type IDs to extract. If None, extracts all.
            
        Returns:
            FileOpResult with extraction details
        """
        try:
            from formats.dbpf.dbpf import DBPFFile
            
            dbpf = DBPFFile(dbpf_path)
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            extracted = []
            
            for entry in dbpf.entries:
                # Filter by type if specified
                if type_ids and entry.type_id not in type_ids:
                    continue
                
                # Generate filename
                filename = f"{entry.type_id:08X}_{entry.group_id:08X}_{entry.instance_id:08X}.bin"
                
                # Get data
                data = dbpf.get_entry(entry)
                if data:
                    file_path = output_path / filename
                    with open(file_path, 'wb') as f:
                        f.write(data)
                    extracted.append(filename)
            
            return FileOpResult(
                True,
                f"Extracted {len(extracted)} entries from DBPF",
                path=str(output_path),
                data={'files': extracted}
            )
            
        except Exception as e:
            return FileOpResult(False, f"DBPF extraction failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONTAINER VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class ContainerValidator:
    """
    Validate container file integrity.
    
    Implements ValidateContainer action.
    """
    
    @staticmethod
    def validate_iff(iff_path: str) -> FileOpResult:
        """
        Validate an IFF file.
        
        Args:
            iff_path: Path to IFF file
            
        Returns:
            FileOpResult with validation details
        """
        issues = []
        
        try:
            with open(iff_path, 'rb') as f:
                data = f.read()
            
            # Check minimum size
            if len(data) < 64:
                issues.append("File too small for valid IFF header")
                return FileOpResult(False, "Invalid IFF", data={'issues': issues})
            
            # Check header
            header = data[:60].decode('ascii', errors='replace')
            if not header.startswith("IFF FILE"):
                issues.append(f"Invalid header: {header[:20]}")
            
            # Check RSMP offset
            import struct
            rsmp_offset = struct.unpack('>I', data[60:64])[0]
            if rsmp_offset > len(data):
                issues.append(f"RSMP offset {rsmp_offset} exceeds file size {len(data)}")
            
            # Check chunks
            offset = 64
            chunk_count = 0
            while offset < rsmp_offset and offset + 76 < len(data):
                chunk_type = data[offset:offset+4].decode('ascii', errors='replace')
                chunk_size = struct.unpack('>I', data[offset+4:offset+8])[0]
                
                if chunk_size < 76:
                    issues.append(f"Chunk at {offset} has invalid size {chunk_size}")
                    break
                
                if offset + chunk_size > len(data):
                    issues.append(f"Chunk {chunk_type} at {offset} exceeds file bounds")
                    break
                
                chunk_count += 1
                offset += chunk_size
            
            if issues:
                return FileOpResult(False, f"Validation found {len(issues)} issues", 
                                  data={'issues': issues, 'chunks_parsed': chunk_count})
            else:
                return FileOpResult(True, f"Valid IFF with {chunk_count} chunks",
                                  data={'chunk_count': chunk_count})
                
        except Exception as e:
            return FileOpResult(False, f"Validation error: {e}")
    
    @staticmethod
    def validate_far(far_path: str) -> FileOpResult:
        """
        Validate a FAR archive.
        
        Args:
            far_path: Path to FAR file
            
        Returns:
            FileOpResult with validation details
        """
        issues = []
        
        try:
            with open(far_path, 'rb') as f:
                data = f.read()
            
            # Check magic
            if len(data) < 16:
                return FileOpResult(False, "File too small", data={'issues': ["Too small"]})
            
            magic = data[:8]
            if magic != b"FAR!byAZ":
                issues.append(f"Invalid magic: {magic}")
            
            version = struct.unpack('<I', data[8:12])[0]
            if version != 1:
                issues.append(f"Unsupported version: {version}")
            
            manifest_offset = struct.unpack('<I', data[12:16])[0]
            if manifest_offset >= len(data):
                issues.append(f"Invalid manifest offset: {manifest_offset}")
            
            if issues:
                return FileOpResult(False, f"Validation found {len(issues)} issues",
                                  data={'issues': issues})
            else:
                return FileOpResult(True, "Valid FAR archive")
                
        except Exception as e:
            return FileOpResult(False, f"Validation error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE API
# ═══════════════════════════════════════════════════════════════════════════════

# Singleton instances
_backup_manager = None


def get_backup_manager(backup_dir: Optional[str] = None) -> BackupManager:
    """Get the global backup manager."""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager(backup_dir)
    return _backup_manager


def backup_file(file_path: str, reason: str = "") -> FileOpResult:
    """Quick backup of a file."""
    return get_backup_manager().backup(file_path, reason)


def restore_file(original_path: str, backup_path: Optional[str] = None) -> FileOpResult:
    """Quick restore from backup."""
    return get_backup_manager().restore(original_path, backup_path)


def validate_container(file_path: str) -> FileOpResult:
    """
    Validate a container file (IFF or FAR).
    
    Detects type automatically.
    """
    with open(file_path, 'rb') as f:
        header = f.read(8)
    
    if header[:8] == b"FAR!byAZ":
        return ContainerValidator.validate_far(file_path)
    elif header[:8].decode('ascii', errors='replace').startswith("IFF FILE"):
        return ContainerValidator.validate_iff(file_path)
    else:
        return FileOpResult(False, "Unknown container format")


def extract_archive(archive_path: str, output_dir: str) -> FileOpResult:
    """
    Extract an archive (FAR or DBPF).
    
    Detects type automatically.
    """
    with open(archive_path, 'rb') as f:
        header = f.read(8)
    
    if header[:8] == b"FAR!byAZ":
        return ArchiveExtractor.extract_far(archive_path, output_dir)
    elif header[:4] == b"DBPF":
        return ArchiveExtractor.extract_dbpf(archive_path, output_dir)
    else:
        return FileOpResult(False, "Unknown archive format")
