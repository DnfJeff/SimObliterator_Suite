"""Minimal IFF file reader - standalone to avoid import issues."""

import struct
from pathlib import Path
from typing import List, Optional
from io import BytesIO


class IFFChunk:
    """Simple IFF chunk representation."""
    def __init__(self):
        self.type_code: str = ""
        self.chunk_id: int = 0
        self.chunk_size: int = 0
        self.chunk_label: str = ""
        self.chunk_data: bytes = b""


class IFFReader:
    """Minimal IFF file reader."""
    
    IFF_SIGNATURE = b"IFF FILE 2.5:TYPE FOLLOWED BY SIZE\0JAMIE DOORNBOS & MAXIS 1"
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.chunks: List[IFFChunk] = []
    
    def read(self) -> bool:
        """Read IFF file."""
        try:
            with open(self.filepath, "rb") as f:
                # Read header (64 bytes)
                header = f.read(64)
                if len(header) < 64:
                    return False
                
                # Validate signature (60 bytes)
                signature = header[0:60]
                if signature != self.IFF_SIGNATURE:
                    # Try to continue anyway, signature validation isn't critical
                    pass
                
                # Get rsmp offset (bytes 60-64, big-endian)
                rsmp_offset = struct.unpack(">I", header[60:64])[0]
                
                # Read chunks sequentially
                while True:
                    # Read chunk header (76 bytes)
                    chunk_header = f.read(76)
                    if len(chunk_header) < 76:
                        break
                    
                    # Parse header (big-endian for IFF)
                    type_code = chunk_header[0:4].decode("ascii", errors="replace")
                    chunk_size = struct.unpack(">I", chunk_header[4:8])[0]
                    chunk_id = struct.unpack(">H", chunk_header[8:10])[0]
                    chunk_flags = struct.unpack(">H", chunk_header[10:12])[0]
                    chunk_label = chunk_header[12:76].decode("ascii", errors="replace").rstrip('\0')
                    
                    # Create chunk
                    chunk = IFFChunk()
                    chunk.type_code = type_code
                    chunk.chunk_id = chunk_id
                    chunk.chunk_size = chunk_size
                    chunk.chunk_label = chunk_label
                    
                    # Read chunk data (content after 76-byte header)
                    content_size = chunk_size - 76
                    if content_size > 0:
                        chunk.chunk_data = f.read(content_size)
                    
                    self.chunks.append(chunk)
                
                return True
        except Exception as e:
            print(f"Error reading IFF: {e}")
            return False


def read_iff_file(filepath: str) -> Optional[IFFReader]:
    """Read IFF file and return reader with chunks."""
    reader = IFFReader(filepath)
    if reader.read():
        return reader
    return None
