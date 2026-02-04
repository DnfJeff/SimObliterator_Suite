"""SimObliterator formats package - file format parsers."""
from .iff import IffFile, IffChunk, STR, OBJD
from .far import FAR1Archive, FarEntry
from .far.far3 import FAR3Archive, Far3Entry, FAR3Decompresser
from .dbpf import DBPFFile, DBPFEntry, DBPFTypeID, DBPFGroupID

__all__ = [
    # IFF
    'IffFile', 'IffChunk', 'STR', 'OBJD',
    # FAR Archives
    'FAR1Archive', 'FarEntry',
    'FAR3Archive', 'Far3Entry', 'FAR3Decompresser',
    # DBPF
    'DBPFFile', 'DBPFEntry', 'DBPFTypeID', 'DBPFGroupID',
]
