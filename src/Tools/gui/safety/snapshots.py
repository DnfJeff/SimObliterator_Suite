"""
Chunk Snapshot Manager.

Provides reversibility through chunk-level snapshots.
Supports "Restore to Vanilla" and edit history.
"""

import hashlib
import zlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from pathlib import Path


@dataclass
class ChunkSnapshot:
    """A snapshot of a chunk's state."""
    
    # Identity
    chunk_type: str
    chunk_id: int
    chunk_label: str
    source_file: str  # FAR/IFF path
    
    # Data
    original_data: bytes  # Compressed original bytes
    original_hash: str    # SHA256 of original
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""
    tool_version: str = "SimObliterator 0.1"
    author: str = ""
    
    def __post_init__(self):
        """Calculate hash if not provided."""
        if not self.original_hash and self.original_data:
            self.original_hash = hashlib.sha256(
                zlib.decompress(self.original_data)
            ).hexdigest()[:16]
    
    @classmethod
    def from_chunk(cls, chunk: Any, source_file: str, description: str = "") -> 'ChunkSnapshot':
        """Create snapshot from a chunk object."""
        # Get raw data
        raw_data = getattr(chunk, 'chunk_data', b'')
        if hasattr(chunk, 'to_bytes'):
            try:
                raw_data = chunk.to_bytes()
            except:
                pass
        
        # Compress for storage
        compressed = zlib.compress(raw_data, level=9)
        
        return cls(
            chunk_type=chunk.chunk_type,
            chunk_id=chunk.chunk_id,
            chunk_label=getattr(chunk, 'chunk_label', '') or '',
            source_file=source_file,
            original_data=compressed,
            original_hash=hashlib.sha256(raw_data).hexdigest()[:16],
            description=description
        )
    
    def get_original_bytes(self) -> bytes:
        """Get decompressed original data."""
        return zlib.decompress(self.original_data)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        import base64
        return {
            'chunk_type': self.chunk_type,
            'chunk_id': self.chunk_id,
            'chunk_label': self.chunk_label,
            'source_file': self.source_file,
            'original_data': base64.b64encode(self.original_data).decode('ascii'),
            'original_hash': self.original_hash,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'tool_version': self.tool_version,
            'author': self.author,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ChunkSnapshot':
        """Deserialize from dictionary."""
        import base64
        return cls(
            chunk_type=data['chunk_type'],
            chunk_id=data['chunk_id'],
            chunk_label=data['chunk_label'],
            source_file=data['source_file'],
            original_data=base64.b64decode(data['original_data']),
            original_hash=data['original_hash'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            description=data.get('description', ''),
            tool_version=data.get('tool_version', ''),
            author=data.get('author', ''),
        )


@dataclass
class VanillaReference:
    """Reference to pristine vanilla game state."""
    
    file_path: str
    file_hash: str
    chunk_hashes: dict[tuple[str, int], str] = field(default_factory=dict)  # (type, id) -> hash
    
    def has_chunk(self, chunk_type: str, chunk_id: int) -> bool:
        """Check if we have vanilla reference for this chunk."""
        return (chunk_type, chunk_id) in self.chunk_hashes
    
    def is_modified(self, chunk_type: str, chunk_id: int, current_hash: str) -> bool:
        """Check if chunk differs from vanilla."""
        vanilla_hash = self.chunk_hashes.get((chunk_type, chunk_id))
        if vanilla_hash is None:
            return False  # Unknown, assume not modified
        return vanilla_hash != current_hash


class SnapshotManager:
    """
    Manages chunk snapshots and vanilla references.
    
    Features:
    - Automatic snapshot on edit
    - Multiple snapshots per chunk (history)
    - Restore to any snapshot
    - Restore to vanilla
    - Persistent storage
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        # Snapshots organized by (source_file, chunk_type, chunk_id)
        self._snapshots: dict[tuple[str, str, int], list[ChunkSnapshot]] = {}
        
        # Vanilla references by file path
        self._vanilla: dict[str, VanillaReference] = {}
        
        # Storage path for persistence
        self._storage_path = storage_path or Path("snapshots")
        
        # Maximum snapshots per chunk
        self._max_history = 20
    
    def create_snapshot(
        self, 
        chunk: Any, 
        source_file: str, 
        description: str = ""
    ) -> ChunkSnapshot:
        """
        Create a snapshot of a chunk.
        
        This should be called BEFORE any edit.
        """
        snapshot = ChunkSnapshot.from_chunk(chunk, source_file, description)
        
        key = (source_file, snapshot.chunk_type, snapshot.chunk_id)
        
        if key not in self._snapshots:
            self._snapshots[key] = []
        
        self._snapshots[key].append(snapshot)
        
        # Trim history if needed
        if len(self._snapshots[key]) > self._max_history:
            self._snapshots[key] = self._snapshots[key][-self._max_history:]
        
        return snapshot
    
    def get_snapshots(
        self, 
        source_file: str, 
        chunk_type: str, 
        chunk_id: int
    ) -> list[ChunkSnapshot]:
        """Get all snapshots for a chunk."""
        key = (source_file, chunk_type, chunk_id)
        return self._snapshots.get(key, [])
    
    def get_latest_snapshot(
        self,
        source_file: str,
        chunk_type: str,
        chunk_id: int
    ) -> Optional[ChunkSnapshot]:
        """Get the most recent snapshot."""
        snapshots = self.get_snapshots(source_file, chunk_type, chunk_id)
        return snapshots[-1] if snapshots else None
    
    def restore_to_snapshot(self, snapshot: ChunkSnapshot) -> bytes:
        """
        Get data to restore from a snapshot.
        
        Returns the original bytes to write back.
        """
        return snapshot.get_original_bytes()
    
    def set_vanilla_reference(
        self,
        file_path: str,
        file_hash: str,
        chunk_hashes: dict[tuple[str, int], str]
    ):
        """Set vanilla reference for a file."""
        self._vanilla[file_path] = VanillaReference(
            file_path=file_path,
            file_hash=file_hash,
            chunk_hashes=chunk_hashes
        )
    
    def can_restore_to_vanilla(self, file_path: str, chunk_type: str, chunk_id: int) -> bool:
        """Check if we can restore this chunk to vanilla."""
        ref = self._vanilla.get(file_path)
        if ref is None:
            return False
        return ref.has_chunk(chunk_type, chunk_id)
    
    def is_modified_from_vanilla(
        self,
        file_path: str,
        chunk_type: str,
        chunk_id: int,
        current_data: bytes
    ) -> bool:
        """Check if a chunk differs from vanilla."""
        ref = self._vanilla.get(file_path)
        if ref is None:
            return False
        
        current_hash = hashlib.sha256(current_data).hexdigest()[:16]
        return ref.is_modified(chunk_type, chunk_id, current_hash)
    
    def get_snapshot_summary(self, source_file: str) -> dict:
        """Get summary of snapshots for a file."""
        summary = {}
        
        for key, snapshots in self._snapshots.items():
            if key[0] == source_file:
                chunk_key = f"{key[1]}#{key[2]}"
                summary[chunk_key] = {
                    'count': len(snapshots),
                    'latest': snapshots[-1].timestamp.isoformat() if snapshots else None,
                    'oldest': snapshots[0].timestamp.isoformat() if snapshots else None,
                }
        
        return summary
    
    def save_to_disk(self):
        """Persist snapshots to disk."""
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        # Save snapshots
        snapshot_file = self._storage_path / "snapshots.json"
        snapshot_data = {}
        
        for key, snapshots in self._snapshots.items():
            key_str = f"{key[0]}|{key[1]}|{key[2]}"
            snapshot_data[key_str] = [s.to_dict() for s in snapshots]
        
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
    
    def load_from_disk(self):
        """Load snapshots from disk."""
        snapshot_file = self._storage_path / "snapshots.json"
        
        if not snapshot_file.exists():
            return
        
        try:
            with open(snapshot_file, 'r') as f:
                snapshot_data = json.load(f)
            
            for key_str, snapshots in snapshot_data.items():
                parts = key_str.split('|')
                key = (parts[0], parts[1], int(parts[2]))
                self._snapshots[key] = [ChunkSnapshot.from_dict(s) for s in snapshots]
        except Exception as e:
            print(f"Failed to load snapshots: {e}")
    
    def clear_history(self, source_file: Optional[str] = None):
        """Clear snapshot history."""
        if source_file:
            keys_to_remove = [k for k in self._snapshots if k[0] == source_file]
            for key in keys_to_remove:
                del self._snapshots[key]
        else:
            self._snapshots.clear()


# Singleton instance
SNAPSHOTS = SnapshotManager()
