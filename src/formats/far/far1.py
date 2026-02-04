"""
FAR1 Archive - File Archive v1
Port of FreeSO's tso.files/FAR1/FAR1Archive.cs

FAR archives are used by The Sims to bundle game files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Iterator

from utils.binary import IoBuffer, ByteOrder


@dataclass
class FarEntry:
    """A single file entry in a FAR archive."""
    filename: str = ""
    data_length: int = 0
    data_length2: int = 0  # Compressed length (if compressed)
    data_offset: int = 0


class FAR1Archive:
    """
    FAR1 (File Archive v1) reader.
    Maps to: FSO.Files.FAR1.FAR1Archive
    
    Format:
    - Header: "FAR!byAZ" (8 bytes)
    - Version: 1 (4 bytes)
    - Manifest offset (4 bytes)
    - [File data...]
    - Manifest at offset:
      - Num files (4 bytes)
      - Entries...
    """
    
    MAGIC = b"FAR!byAZ"
    
    def __init__(self, path: str, v1b: bool = False):
        """
        Open a FAR1 archive.
        
        Args:
            path: Path to the .far file
            v1b: True for v1b format (2-byte filename length), False for v1a (4-byte)
                 Default is False (v1a) as most Sims 1 archives use this format.
        """
        self.path = path
        self.v1b = v1b
        self._entries: list[FarEntry] = []
        self._manifest_offset: int = 0
        
        self._read_manifest()
    
    def _read_manifest(self):
        """Read the archive manifest."""
        with open(self.path, 'rb') as f:
            data = f.read()
        
        io = IoBuffer.from_bytes(data, ByteOrder.LITTLE_ENDIAN)
        
        # Read header
        magic = io.read_bytes(8)
        if magic != self.MAGIC:
            raise ValueError(f"Invalid FAR header: {magic}")
        
        version = io.read_uint32()
        if version != 1:
            raise ValueError(f"Unsupported FAR version: {version}")
        
        # Read manifest offset and seek to it
        self._manifest_offset = io.read_uint32()
        io.seek(self._manifest_offset)
        
        # Read entries
        num_files = io.read_uint32()
        
        for _ in range(num_files):
            entry = FarEntry()
            entry.data_length = io.read_int32()
            entry.data_length2 = io.read_int32()
            entry.data_offset = io.read_int32()
            
            # Filename length differs between v1a and v1b
            filename_length = io.read_int16() if self.v1b else io.read_int32()
            entry.filename = io.read_cstring(filename_length, trim_null=False)
            
            self._entries.append(entry)
    
    @property
    def entries(self) -> list[FarEntry]:
        """All entries in the archive."""
        return self._entries
    
    @property
    def num_files(self) -> int:
        """Number of files in the archive."""
        return len(self._entries)
    
    @property
    def manifest_offset(self) -> int:
        """Offset to the manifest in the archive."""
        return self._manifest_offset
    
    def get_entry(self, filename: str) -> Optional[bytes]:
        """Get file data by filename."""
        for entry in self._entries:
            if entry.filename == filename:
                return self._read_entry_data(entry)
        return None
    
    def get_entry_by_index(self, index: int) -> Optional[bytes]:
        """Get file data by index."""
        if 0 <= index < len(self._entries):
            return self._read_entry_data(self._entries[index])
        return None
    
    def _read_entry_data(self, entry: FarEntry) -> bytes:
        """Read raw data for an entry."""
        with open(self.path, 'rb') as f:
            data = f.read()
        
        io = IoBuffer.from_bytes(data, ByteOrder.LITTLE_ENDIAN)
        io.seek(entry.data_offset)
        return io.read_bytes(entry.data_length)
    
    def extract(self, filename: str, output_path: str) -> bool:
        """Extract a single file to disk."""
        data = self.get_entry(filename)
        if data is None:
            return False
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(data)
        return True
    
    def extract_all(self, output_dir: str):
        """Extract all files to a directory."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for entry in self._entries:
            data = self._read_entry_data(entry)
            file_path = output_path / entry.filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(data)
    
    def list_files(self) -> list[str]:
        """Get list of all filenames in the archive."""
        return [e.filename for e in self._entries]
    
    def __iter__(self) -> Iterator[FarEntry]:
        return iter(self._entries)
    
    def __len__(self) -> int:
        return len(self._entries)
    
    def __contains__(self, filename: str) -> bool:
        return any(e.filename == filename for e in self._entries)
    
    def summary(self) -> str:
        """Get a summary of the archive."""
        total_size = sum(e.data_length for e in self._entries)
        return f"FAR1: {self.path}\nFiles: {len(self)}\nTotal size: {total_size:,} bytes"
