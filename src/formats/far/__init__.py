"""FAR archive format package."""
from .far1 import FAR1Archive, FarEntry
from .far3 import FAR3Archive, Far3Entry, FAR3Decompresser

__all__ = [
    'FAR1Archive', 'FarEntry',
    'FAR3Archive', 'Far3Entry', 'FAR3Decompresser',
]
