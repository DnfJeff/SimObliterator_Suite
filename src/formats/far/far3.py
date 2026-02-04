"""
FAR3 Archive Format - File Archive v3 with Compression

Reference: FreeSO's tso.files/FAR3/FAR3Archive.cs
Port of the C# implementation to Python

FAR3 adds compression support to FAR1. Files can be stored uncompressed or using
RefPack (compression ID 0xFB10) which is a variant of LZ77 compression used by
Maxis games.

Structure:
  - Header: "FAR!byAZ" (8 bytes)
  - Version: 3 (4 bytes)
  - Manifest offset (4 bytes)
  - [File data...]
  - Manifest at offset:
    - Num files (4 bytes)
    - Entries...
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from io import BytesIO

from utils.binary import IoBuffer, ByteOrder


@dataclass
class Far3Entry:
    """A single file entry in a FAR3 archive."""
    
    # File size information
    decompressed_file_size: int = 0  # Uncompressed size
    compressed_file_size: int = 0    # Compressed size (3 bytes as u24)
    data_type: int = 0               # File type indicator
    data_offset: int = 0             # Offset to file data in archive
    
    # Compression info
    is_compressed: int = 0           # 0x01 if compressed, 0x00 if not
    access_number: int = 0           # Access/priority number
    
    # Identification
    filename_length: int = 0
    filename: str = ""
    type_id: int = 0                 # Resource type ID (TypeID for OBJD, etc.)
    file_id: int = 0                 # Unique file identifier (FileID)


class FAR3Decompresser:
    """
    FAR3 Decompression Engine - RefPack (LZ77 variant) decompression
    
    Reference: FreeSO's tso.files/FAR3/Decompresser.cs
    Based on: RefPack specification (wiki.niotso.org/RefPack)
    Original: DBPF4J (sc4dbpf4j.cvs.sourceforge.net)
    
    Compression format: Alternating literal and copy tokens
    - Literal: Uncompressed bytes (0-3 at a time)
    - Copy: Reference to previous data (LZ77-style)
    """
    
    def __init__(self):
        self.compressed_size: int = 0
        self.decompressed_size: int = 0
    
    @staticmethod
    def decompress(data: bytes) -> bytes:
        """
        Decompress RefPack compressed data
        
        Args:
            data: Compressed data bytes
            
        Returns:
            Decompressed data
            
        Raises:
            ValueError: If decompression fails or data is malformed
        """
        if len(data) < 9:
            raise ValueError("Compressed data too small")
        
        # RefPack header format:
        # Bytes 0-3: Compression header (0xFB10 followed by size info)
        # Bytes 4-8: Decompressed size (24-bit big-endian in specific format)
        
        output = bytearray()
        io = IoBuffer(BytesIO(data))
        
        # Skip first 9 bytes (header info already read by caller)
        io.seek(9)
        
        decompressed_size = 0
        while io.position < len(data) and len(output) < decompressed_size or decompressed_size == 0:
            cc = io.read_byte()  # Control code
            
            # Upper 2 bits determine operation type
            op_type = (cc & 0xC0) >> 6
            
            if op_type == 0x00:
                # 0b00: Literal block (1-4 bytes)
                num_literals = (cc & 0x03) + 1
                for _ in range(num_literals):
                    if io.position < len(data):
                        output.append(io.read_byte())
            
            elif op_type == 0x01:
                # 0b01: 2-byte copy (copy from earlier in output)
                next_byte = io.read_byte()
                copy_length = (cc & 0x03) + 3
                copy_offset = ((cc & 0x0C) << 6) | next_byte
                copy_offset = copy_offset + 1
                
                # Copy bytes from earlier position
                src_pos = len(output) - copy_offset
                for _ in range(copy_length):
                    if 0 <= src_pos < len(output):
                        output.append(output[src_pos])
                        src_pos += 1
            
            elif op_type == 0x02:
                # 0b10: 3-byte copy with longer range
                byte2 = io.read_byte()
                byte3 = io.read_byte()
                
                copy_length = (cc & 0x03) + 3
                copy_offset = ((cc & 0x3C) << 8) | (byte2 << 8) | byte3
                copy_offset = copy_offset + 1
                
                # Copy bytes from earlier position
                src_pos = len(output) - copy_offset
                for _ in range(copy_length):
                    if 0 <= src_pos < len(output):
                        output.append(output[src_pos])
                        src_pos += 1
            
            elif op_type == 0x03:
                # 0b11: End of block or special handling
                if cc == 0xFF:
                    break  # End of compressed data
                else:
                    # Extended literal block
                    num_literals = (cc & 0x3F) + 4
                    for _ in range(num_literals):
                        if io.position < len(data):
                            output.append(io.read_byte())
        
        return bytes(output)


class FAR3Archive:
    """
    FAR3 (File Archive v3) reader with compression support.
    
    Reference: FreeSO's tso.files/FAR3/FAR3Archive.cs
    
    Key features:
    - Supports both compressed and uncompressed files
    - Uses RefPack (compression ID 0xFB10) for compression
    - Stores both TypeID and FileID for identification
    - Supports fast lookup by FileID or filename
    """
    
    MAGIC = b"FAR!byAZ"
    VERSION = 3
    COMPRESSION_ID = 0xFB10
    
    def __init__(self, path: Optional[str] = None):
        """
        Open a FAR3 archive
        
        Args:
            path: Path to the .far3 file (optional)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If not a valid FAR3 archive
        """
        self.path = path
        self._entries_by_filename: Dict[str, Far3Entry] = {}
        self._entries_list: List[Far3Entry] = []
        self._entries_by_id: Dict[int, Far3Entry] = {}
        self._manifest_offset: int = 0
        self._io_buffer: Optional[IoBuffer] = None
        
        if path:
            self._read_manifest()
    
    def read(self, stream) -> None:
        """
        Read FAR3 archive from a stream
        
        Args:
            stream: File stream to read from
        """
        io = IoBuffer.from_stream(stream, ByteOrder.LITTLE_ENDIAN)
        
        # Read header
        magic = io.read_bytes(8)
        if magic != self.MAGIC:
            raise ValueError(f"Invalid FAR3 magic: {magic}")
        
        version = io.read_uint32()
        if version != self.VERSION:
            raise ValueError(f"Invalid FAR3 version: {version} (expected 3)")
        
        # Read manifest offset
        manifest_offset = io.read_uint32()
        
        # Seek to manifest
        io.seek(manifest_offset)
        
        # Read number of files
        num_files = io.read_uint32()
        
        # Read each entry
        for _ in range(num_files):
            entry = Far3Entry()
            
            # Read entry structure (aligned to specific offsets)
            entry.decompressed_file_size = io.read_uint32()
            
            # Compressed size is stored as 3 bytes (24-bit)
            byte0 = io.read_byte()
            byte1 = io.read_byte()
            byte2 = io.read_byte()
            entry.compressed_file_size = (byte0 << 0) | (byte1 << 8) | (byte2 << 16)
            
            entry.data_type = io.read_byte()
            entry.data_offset = io.read_uint32()
            entry.is_compressed = io.read_byte()
            entry.access_number = io.read_byte()
            entry.filename_length = io.read_uint16()
            entry.type_id = io.read_uint32()
            entry.file_id = io.read_uint32()
            
            # Read filename
            if entry.filename_length > 0:
                entry.filename = io.read_cstring(entry.filename_length, trim_null=False)
            else:
                entry.filename = ""
            
            # Store in lookup tables
            if entry.filename and entry.filename not in self._entries_by_filename:
                self._entries_by_filename[entry.filename] = entry
            
            self._entries_list.append(entry)
            self._entries_by_id[entry.file_id] = entry
        
        # Keep io_buffer for later data retrieval
        self._io_buffer = io
    
    def _read_manifest(self) -> None:
        """Read the FAR3 archive manifest"""
        with IoBuffer.from_file(self.path, ByteOrder.LITTLE_ENDIAN) as io:
            # Read header
            magic = io.read_bytes(8)
            if magic != self.MAGIC:
                raise ValueError(f"Invalid FAR3 magic: {magic}")
            
            version = io.read_uint32()
            if version != self.VERSION:
                raise ValueError(f"Invalid FAR3 version: {version} (expected 3)")
            
            # Read manifest offset
            self._manifest_offset = io.read_uint32()
            
            # Seek to manifest
            io.seek(self._manifest_offset)
            
            # Read number of files
            num_files = io.read_uint32()
            
            # Read each entry
            for _ in range(num_files):
                entry = Far3Entry()
                
                # Read entry structure (aligned to specific offsets)
                entry.decompressed_file_size = io.read_uint32()
                
                # Compressed size is stored as 3 bytes (24-bit)
                byte0 = io.read_byte()
                byte1 = io.read_byte()
                byte2 = io.read_byte()
                entry.compressed_file_size = (byte0 << 0) | (byte1 << 8) | (byte2 << 16)
                
                entry.data_type = io.read_byte()
                entry.data_offset = io.read_uint32()
                entry.is_compressed = io.read_byte()
                entry.access_number = io.read_byte()
                entry.filename_length = io.read_uint16()
                entry.type_id = io.read_uint32()
                entry.file_id = io.read_uint32()
                
                # Read filename
                if entry.filename_length > 0:
                    entry.filename = io.read_cstring(entry.filename_length, trim_null=False)
                else:
                    entry.filename = ""
                
                # Store in lookup tables
                if entry.filename and entry.filename not in self._entries_by_filename:
                    self._entries_by_filename[entry.filename] = entry
                
                self._entries_list.append(entry)
                self._entries_by_id[entry.file_id] = entry
    
    def get_entry(self, entry: Far3Entry) -> bytes:
        """
        Extract and decompress file data from archive
        
        Args:
            entry: Far3Entry to extract
            
        Returns:
            Decompressed file data
        """
        with IoBuffer.from_file(self.path, ByteOrder.LITTLE_ENDIAN) as io:
            io.seek(entry.data_offset)
            
            # Check if file is compressed
            if entry.is_compressed == 0x01:
                # Skip 9-byte compression header
                io.seek(9, 1)  # Seek relative to current position
                
                # Read compression metadata
                file_size = io.read_uint32()
                compression_id = io.read_uint16()
                
                if compression_id == self.COMPRESSION_ID:
                    # RefPack compression
                    # Read 3-byte decompressed size indicator
                    byte0 = io.read_byte()
                    byte1 = io.read_byte()
                    byte2 = io.read_byte()
                    decompressed_size = (byte0 << 0x10) | (byte1 << 0x08) | byte2
                    
                    # Read compressed data
                    compressed_data = io.read_bytes(int(file_size))
                    
                    # Decompress
                    decompressor = FAR3Decompresser()
                    return decompressor.decompress(compressed_data)
                else:
                    # Unknown compression format, try uncompressed fallback
                    io.seek(entry.data_offset)
                    return io.read_bytes(entry.decompressed_file_size)
            else:
                # Uncompressed data
                return io.read_bytes(entry.decompressed_file_size)
    
    def get_entry_by_filename(self, filename: str) -> bytes:
        """Get file data by filename"""
        if filename not in self._entries_by_filename:
            raise KeyError(f"File not found: {filename}")
        
        entry = self._entries_by_filename[filename]
        return self.get_entry(entry)
    
    def get_entry_by_id(self, file_id: int) -> bytes:
        """Get file data by FileID"""
        if file_id not in self._entries_by_id:
            raise KeyError(f"File ID not found: {file_id}")
        
        entry = self._entries_by_id[file_id]
        return self.get_entry(entry)
    
    @property
    def entries(self) -> List[Far3Entry]:
        """Get all entries"""
        return self._entries_list.copy()
    
    @property
    def num_files(self) -> int:
        """Get number of files in archive"""
        return len(self._entries_list)
    
    @property
    def num_entries(self) -> int:
        """Get number of entries in archive (alias for num_files)"""
        return len(self._entries_list)
    
    def __getitem__(self, filename: str) -> bytes:
        """Get file data by filename (dict-like access)"""
        return self.get_entry_by_filename(filename)


__all__ = [
    'Far3Entry',
    'FAR3Decompresser',
    'FAR3Archive',
]
