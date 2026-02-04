"""
Sims 1 Save File Analyzer
Comprehensive analysis and documentation of character/house save file structure.

Goal: Fully decode save files to enable safe editing (money, stats, job, friends)
for Legacy Collection where no working tools exist.
"""

import sys
import struct
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any
from collections import defaultdict

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "Program"))

from utils.binary import IoBuffer, ByteOrder


@dataclass
class ChunkInfo:
    """Raw chunk information from IFF."""
    type_code: str
    chunk_id: int
    chunk_flags: int
    label: str
    data_offset: int
    data_size: int
    raw_data: bytes = b''


@dataclass
class SimCharacter:
    """Decoded Sim character data."""
    first_name: str = ""
    last_name: str = ""
    bio: str = ""
    age: int = 0  # 0=adult, etc
    gender: int = 0  # 0=male, 1=female
    skin_tone: int = 0
    
    # Personality (0-1000 scale typically)
    neat: int = 0
    outgoing: int = 0
    active: int = 0
    playful: int = 0
    nice: int = 0
    
    # Skills (0-100 or 0-1000)
    cooking: int = 0
    mechanical: int = 0
    charisma: int = 0
    body: int = 0
    logic: int = 0
    creativity: int = 0
    
    # Relationships
    relationships: dict[int, int] = field(default_factory=dict)  # sim_id -> relationship_value
    
    # Career
    job_type: int = 0
    job_level: int = 0
    job_performance: int = 0
    
    # State
    hunger: int = 0
    comfort: int = 0
    hygiene: int = 0
    bladder: int = 0
    energy: int = 0
    fun: int = 0
    social: int = 0
    room: int = 0
    
    # Appearance IDs
    head_id: int = 0
    body_id: int = 0


class SaveFileAnalyzer:
    """Analyzes Sims 1 IFF save files."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.chunks: list[ChunkInfo] = []
        self.strings: dict[int, list[str]] = {}  # chunk_id -> strings
        self.raw_data: bytes = b''
        
    def analyze(self) -> dict[str, Any]:
        """Full analysis of the save file."""
        with open(self.filepath, 'rb') as f:
            self.raw_data = f.read()
        
        result = {
            'filepath': self.filepath,
            'filesize': len(self.raw_data),
            'chunks': [],
            'strings': {},
            'decoded_character': None,
            'chunk_type_summary': {},
        }
        
        # Parse IFF structure
        self._parse_iff_structure()
        
        # Analyze each chunk
        for chunk in self.chunks:
            chunk_analysis = self._analyze_chunk(chunk)
            result['chunks'].append(chunk_analysis)
            
            # Track by type
            if chunk.type_code not in result['chunk_type_summary']:
                result['chunk_type_summary'][chunk.type_code] = []
            result['chunk_type_summary'][chunk.type_code].append(chunk.chunk_id)
        
        # Try to decode character
        result['decoded_character'] = self._decode_character()
        result['strings'] = self.strings
        
        return result
    
    def _parse_iff_structure(self):
        """Parse the raw IFF chunk structure."""
        io = IoBuffer.from_bytes(self.raw_data, ByteOrder.BIG_ENDIAN)
        
        # Read header
        header = io.read_cstring(60, trim_null=True)
        if not header.startswith("IFF FILE"):
            raise ValueError(f"Not a valid IFF file: {header[:20]}")
        
        # Resource map offset
        rsmp_offset = io.read_uint32()
        
        # Parse all chunks
        while io.has_more and io.has_bytes(12):
            start_pos = io.position
            
            type_code = io.read_cstring(4, trim_null=False)
            chunk_size = io.read_uint32()
            chunk_id = io.read_uint16()
            chunk_flags = io.read_uint16()
            label = io.read_cstring(64, trim_null=True)
            
            data_size = chunk_size - 76
            if data_size < 0:
                break
                
            chunk_data = io.read_bytes(data_size) if data_size > 0 else b''
            
            chunk = ChunkInfo(
                type_code=type_code,
                chunk_id=chunk_id,
                chunk_flags=chunk_flags,
                label=label,
                data_offset=start_pos + 76,
                data_size=data_size,
                raw_data=chunk_data
            )
            self.chunks.append(chunk)
    
    def _analyze_chunk(self, chunk: ChunkInfo) -> dict:
        """Analyze a single chunk."""
        analysis = {
            'type': chunk.type_code,
            'id': chunk.chunk_id,
            'flags': chunk.chunk_flags,
            'label': chunk.label,
            'size': chunk.data_size,
            'data_preview': chunk.raw_data[:64].hex() if chunk.raw_data else '',
        }
        
        # Type-specific analysis
        if chunk.type_code == 'STR#':
            analysis['strings'] = self._parse_str_chunk(chunk)
            self.strings[chunk.chunk_id] = analysis['strings']
        elif chunk.type_code == 'CTSS':
            analysis['ctss_strings'] = self._parse_ctss_chunk(chunk)
            self.strings[chunk.chunk_id] = analysis.get('ctss_strings', [])
        elif chunk.type_code == 'FAMI':
            analysis['family_data'] = self._parse_fami_chunk(chunk)
        elif chunk.type_code == 'FAMs':
            analysis['fams_data'] = self._parse_fams_chunk(chunk)
        elif chunk.type_code == 'SIMI':
            analysis['sim_info'] = self._parse_simi_chunk(chunk)
        elif chunk.type_code == 'NGBH':
            analysis['neighborhood'] = self._parse_ngbh_chunk(chunk)
        elif chunk.type_code == 'SLOT':
            analysis['slot_data'] = self._parse_slot_chunk(chunk)
        elif chunk.type_code == 'PDAT':
            analysis['person_data'] = self._parse_pdat_chunk(chunk)
        elif chunk.type_code == 'GLOB':
            analysis['globals'] = self._parse_glob_chunk(chunk)
        elif chunk.type_code == 'BCON':
            analysis['constants'] = self._parse_bcon_chunk(chunk)
        elif chunk.type_code == 'OBJf':
            analysis['object_funcs'] = self._parse_objf_chunk(chunk)
        elif chunk.type_code == 'OBJD':
            analysis['object_data'] = self._parse_objd_chunk(chunk)
            
        return analysis
    
    def _parse_str_chunk(self, chunk: ChunkInfo) -> list[str]:
        """Parse STR# (string table) chunk."""
        if len(chunk.raw_data) < 2:
            return []
        
        strings = []
        io = IoBuffer.from_bytes(chunk.raw_data, ByteOrder.LITTLE_ENDIAN)
        
        # Format code
        format_code = io.read_int16()
        
        if format_code == 0:
            # Simple format: count, then null-terminated strings
            if io.has_bytes(2):
                count = io.read_uint16()
                for _ in range(count):
                    if not io.has_more:
                        break
                    s = self._read_pascal_or_cstring(io)
                    strings.append(s)
        elif format_code == -1:
            # Pascal strings format
            if io.has_bytes(2):
                count = io.read_uint16()
                for _ in range(count):
                    if not io.has_bytes(1):
                        break
                    length = io.read_uint8()
                    if io.has_bytes(length):
                        s = io.read_bytes(length).decode('latin-1', errors='replace')
                        strings.append(s)
        elif format_code == -2:
            # Format with language sets
            if io.has_bytes(2):
                count = io.read_uint16()
                for _ in range(count):
                    # Each string set has language codes
                    if not io.has_bytes(1):
                        break
                    lang_code = io.read_uint8()
                    s = self._read_pascal_or_cstring(io)
                    strings.append(f"[{lang_code}] {s}")
        elif format_code == -3:
            # Extended format with more language info  
            if io.has_bytes(2):
                count = io.read_uint16()
                for _ in range(count):
                    if not io.has_bytes(2):
                        break
                    lang_code = io.read_uint8()
                    s = self._read_pascal_or_cstring(io)
                    strings.append(f"[{lang_code}] {s}")
        elif format_code == -4:
            # Full unicode/extended format
            if io.has_bytes(2):
                count = io.read_uint16()
                for _ in range(count):
                    if not io.has_bytes(1):
                        break
                    lang_count = io.read_uint8()
                    for lc in range(lang_count):
                        if not io.has_bytes(2):
                            break
                        lang_code = io.read_uint8()
                        s = self._read_length_prefixed_string(io)
                        strings.append(f"[{lang_code}] {s}")
                        
        return strings
    
    def _read_pascal_or_cstring(self, io: IoBuffer) -> str:
        """Read a length-prefixed or null-terminated string."""
        if not io.has_bytes(1):
            return ""
        length = io.read_uint8()
        if length == 0:
            return ""
        if io.has_bytes(length):
            return io.read_bytes(length).decode('latin-1', errors='replace')
        return ""
    
    def _read_length_prefixed_string(self, io: IoBuffer) -> str:
        """Read a 2-byte length prefixed string."""
        if not io.has_bytes(2):
            return ""
        length = io.read_uint16()
        if length == 0:
            return ""
        if io.has_bytes(length):
            return io.read_bytes(length).decode('utf-16-le', errors='replace') if length > 1 else ""
        return ""
    
    def _parse_ctss_chunk(self, chunk: ChunkInfo) -> list[str]:
        """Parse CTSS (Catalog String) chunk - similar to STR#."""
        return self._parse_str_chunk(chunk)
    
    def _parse_fami_chunk(self, chunk: ChunkInfo) -> dict:
        """Parse FAMI (Family) chunk - contains family relationships."""
        if len(chunk.raw_data) < 4:
            return {}
        
        io = IoBuffer.from_bytes(chunk.raw_data, ByteOrder.LITTLE_ENDIAN)
        
        result = {
            'raw_values': [],
            'possible_sim_ids': [],
            'possible_relationships': []
        }
        
        # Read as uint16 pairs (common pattern for relationships)
        while io.has_bytes(2):
            val = io.read_uint16()
            result['raw_values'].append(val)
        
        return result
    
    def _parse_fams_chunk(self, chunk: ChunkInfo) -> dict:
        """Parse FAMs (Family Structure) chunk."""
        if len(chunk.raw_data) < 4:
            return {}
        
        io = IoBuffer.from_bytes(chunk.raw_data, ByteOrder.LITTLE_ENDIAN)
        
        result = {
            'version': io.read_uint32() if io.has_bytes(4) else 0,
            'raw_data_hex': chunk.raw_data[:100].hex()
        }
        
        return result
    
    def _parse_simi_chunk(self, chunk: ChunkInfo) -> dict:
        """Parse SIMI (Sim Information) chunk - core character data!"""
        if len(chunk.raw_data) < 20:
            return {}
        
        io = IoBuffer.from_bytes(chunk.raw_data, ByteOrder.LITTLE_ENDIAN)
        
        result = {
            'raw_uint16_values': [],
            'raw_int16_values': [],
            'possible_personality': {},
            'possible_skills': {},
        }
        
        # Read all as uint16 first
        pos = 0
        while io.has_bytes(2):
            val = io.read_uint16()
            result['raw_uint16_values'].append((pos, val))
            pos += 2
        
        # Try to identify personality/skills (usually in 0-1000 range)
        # Common offsets for personality: bytes 10-20 usually
        # Common offsets for skills: bytes 20-32 usually
        
        return result
    
    def _parse_ngbh_chunk(self, chunk: ChunkInfo) -> dict:
        """Parse NGBH (Neighborhood) chunk."""
        return {'size': len(chunk.raw_data), 'preview': chunk.raw_data[:50].hex()}
    
    def _parse_slot_chunk(self, chunk: ChunkInfo) -> dict:
        """Parse SLOT chunk - slot/inventory data."""
        return {'size': len(chunk.raw_data), 'preview': chunk.raw_data[:50].hex()}
    
    def _parse_pdat_chunk(self, chunk: ChunkInfo) -> dict:
        """Parse PDAT (Person Data) chunk - likely contains motive/state data."""
        if len(chunk.raw_data) < 4:
            return {}
        
        io = IoBuffer.from_bytes(chunk.raw_data, ByteOrder.LITTLE_ENDIAN)
        
        result = {
            'raw_values': [],
            'possible_motives': {}
        }
        
        # Motives are typically stored as int16 in range -100 to 100 (or 0-200)
        idx = 0
        while io.has_bytes(2):
            val = io.read_int16()
            result['raw_values'].append((idx, val))
            # Flag likely motive values
            if -200 <= val <= 200:
                result['possible_motives'][idx] = val
            idx += 1
        
        return result
    
    def _parse_glob_chunk(self, chunk: ChunkInfo) -> dict:
        """Parse GLOB chunk - global variables/state."""
        if len(chunk.raw_data) < 2:
            return {}
        
        io = IoBuffer.from_bytes(chunk.raw_data, ByteOrder.LITTLE_ENDIAN)
        
        result = {'values': []}
        while io.has_bytes(2):
            result['values'].append(io.read_int16())
        
        return result
    
    def _parse_bcon_chunk(self, chunk: ChunkInfo) -> dict:
        """Parse BCON (Constants) chunk."""
        if len(chunk.raw_data) < 2:
            return {}
        
        io = IoBuffer.from_bytes(chunk.raw_data, ByteOrder.LITTLE_ENDIAN)
        
        count = io.read_uint8()
        flags = io.read_uint8()
        
        values = []
        while io.has_bytes(2) and len(values) < count:
            values.append(io.read_int16())
        
        return {'count': count, 'flags': flags, 'values': values}
    
    def _parse_objf_chunk(self, chunk: ChunkInfo) -> dict:
        """Parse OBJf (Object Functions) chunk."""
        return {'size': len(chunk.raw_data), 'preview': chunk.raw_data[:32].hex()}
    
    def _parse_objd_chunk(self, chunk: ChunkInfo) -> dict:
        """Parse OBJD (Object Data) chunk."""
        if len(chunk.raw_data) < 100:
            return {'size': len(chunk.raw_data)}
        
        io = IoBuffer.from_bytes(chunk.raw_data, ByteOrder.LITTLE_ENDIAN)
        
        return {
            'version': io.read_uint32() if io.has_bytes(4) else 0,
            'size': len(chunk.raw_data),
            'preview': chunk.raw_data[:50].hex()
        }
    
    def _decode_character(self) -> Optional[SimCharacter]:
        """Try to decode character data from chunks."""
        char = SimCharacter()
        
        # Get names from string chunks (usually STR# id 256 or similar)
        # Find strings that look like names
        for chunk_id, strings in self.strings.items():
            for s in strings:
                # Clean up language prefixes
                clean_s = s.split('] ')[-1] if '] ' in s else s
                if clean_s and len(clean_s) < 50:
                    # First string is usually first name
                    if not char.first_name and clean_s.isalpha():
                        char.first_name = clean_s
                    elif not char.last_name and clean_s.isalpha() and clean_s != char.first_name:
                        char.last_name = clean_s
        
        return char


def analyze_and_compare(filepaths: list[str]):
    """Analyze multiple files and compare structures."""
    print("=" * 80)
    print("SIMS 1 SAVE FILE STRUCTURE ANALYZER")
    print("=" * 80)
    
    all_results = []
    
    for fp in filepaths:
        print(f"\n{'='*80}")
        print(f"FILE: {Path(fp).name}")
        print(f"{'='*80}")
        
        try:
            analyzer = SaveFileAnalyzer(fp)
            result = analyzer.analyze()
            all_results.append(result)
            
            print(f"Size: {result['filesize']:,} bytes")
            print(f"Total chunks: {len(result['chunks'])}")
            
            print("\nCHUNK TYPE SUMMARY:")
            print("-" * 40)
            for type_code, ids in sorted(result['chunk_type_summary'].items()):
                print(f"  {type_code}: {len(ids)} chunks (IDs: {ids[:5]}{'...' if len(ids) > 5 else ''})")
            
            print("\nSTRINGS FOUND:")
            print("-" * 40)
            for chunk_id, strings in result['strings'].items():
                if strings:
                    print(f"  Chunk {chunk_id}:")
                    for s in strings[:10]:
                        print(f"    '{s}'")
                    if len(strings) > 10:
                        print(f"    ... and {len(strings) - 10} more")
            
            print("\nDETAILED CHUNK ANALYSIS:")
            print("-" * 40)
            for chunk_info in result['chunks']:
                print(f"\n  [{chunk_info['type']}] ID={chunk_info['id']} '{chunk_info['label']}'")
                print(f"    Size: {chunk_info['size']} bytes")
                if chunk_info.get('data_preview'):
                    preview = chunk_info['data_preview'][:80]
                    print(f"    Data: {preview}...")
                
                # Type-specific details
                if 'strings' in chunk_info and chunk_info['strings']:
                    print(f"    Strings: {chunk_info['strings'][:3]}")
                if 'person_data' in chunk_info:
                    pd = chunk_info['person_data']
                    if 'possible_motives' in pd and pd['possible_motives']:
                        print(f"    Possible motives: {dict(list(pd['possible_motives'].items())[:5])}")
                if 'constants' in chunk_info:
                    print(f"    Constants: {chunk_info['constants']}")
                if 'globals' in chunk_info and chunk_info['globals'].get('values'):
                    vals = chunk_info['globals']['values'][:10]
                    print(f"    Globals: {vals}")
                    
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Cross-file comparison
    if len(all_results) > 1:
        print("\n" + "=" * 80)
        print("CROSS-FILE COMPARISON")
        print("=" * 80)
        
        # Compare chunk types
        all_types = set()
        for r in all_results:
            all_types.update(r['chunk_type_summary'].keys())
        
        print("\nChunk types across files:")
        for t in sorted(all_types):
            counts = [len(r['chunk_type_summary'].get(t, [])) for r in all_results]
            print(f"  {t}: {counts}")


def search_for_name(filepath: str, name: str):
    """Search raw bytes for a name pattern."""
    print(f"\nSearching for '{name}' in {filepath}...")
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Try different encodings
    encodings = [
        ('ASCII', name.encode('ascii')),
        ('UTF-16-LE', name.encode('utf-16-le')),
        ('Latin-1', name.encode('latin-1')),
        ('Pascal', bytes([len(name)]) + name.encode('ascii')),
    ]
    
    for enc_name, pattern in encodings:
        pos = data.find(pattern)
        if pos != -1:
            print(f"  FOUND at offset {pos} (0x{pos:X}) using {enc_name}")
            # Show context
            start = max(0, pos - 16)
            end = min(len(data), pos + len(pattern) + 32)
            context = data[start:end]
            print(f"    Context: {context}")
            print(f"    Hex: {context.hex()}")


def hexdump_chunk(filepath: str, chunk_type: str, chunk_id: int):
    """Hexdump a specific chunk for detailed analysis."""
    analyzer = SaveFileAnalyzer(filepath)
    analyzer._parse_iff_structure()
    
    for chunk in analyzer.chunks:
        if chunk.type_code == chunk_type and chunk.chunk_id == chunk_id:
            print(f"\nHEXDUMP: {chunk_type} ID={chunk_id} '{chunk.label}'")
            print("=" * 80)
            
            data = chunk.raw_data
            for i in range(0, len(data), 16):
                hex_part = ' '.join(f'{b:02X}' for b in data[i:i+16])
                ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
                print(f"  {i:04X}: {hex_part:<48} {ascii_part}")
            return
    
    print(f"Chunk {chunk_type} ID={chunk_id} not found")


if __name__ == "__main__":
    # Test files
    test_dir = Path(__file__).parent.parent / "Testing" / "save_analysis"
    test_files = list(test_dir.glob("*.iff"))
    
    if test_files:
        # Analyze all test files
        analyze_and_compare([str(f) for f in test_files[:3]])
        
        # Search for specific names
        for f in test_files[:1]:
            search_for_name(str(f), "Jeff")
            search_for_name(str(f), "Goth")
            search_for_name(str(f), "Bella")
    else:
        print("No test files found. Copy some User*.iff files to Testing/save_analysis/")
