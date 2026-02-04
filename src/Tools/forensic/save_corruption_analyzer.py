"""
Save File Corruption Analyzer
Compares working vs broken saves to identify what Sim Enhancer corrupts.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "Program"))

from utils.binary import IoBuffer, ByteOrder


@dataclass
class ChunkDiff:
    """Difference between two chunks."""
    chunk_type: str
    chunk_id: int
    label: str
    status: str  # 'modified', 'added', 'removed', 'identical'
    size_diff: int = 0
    byte_diffs: list = None
    old_size: int = 0
    new_size: int = 0


class SaveCorruptionAnalyzer:
    """Compares two save files to identify corruption patterns."""
    
    def __init__(self, working_path: str, broken_path: str):
        self.working_path = working_path
        self.broken_path = broken_path
        self.working_chunks = {}  # (type, id) -> chunk_data
        self.broken_chunks = {}
        
    def analyze(self) -> dict:
        """Full corruption analysis."""
        # Parse both files
        self.working_chunks = self._parse_chunks(self.working_path)
        self.broken_chunks = self._parse_chunks(self.broken_path)
        
        result = {
            'working_file': self.working_path,
            'broken_file': self.broken_path,
            'working_size': Path(self.working_path).stat().st_size,
            'broken_size': Path(self.broken_path).stat().st_size,
            'size_difference': 0,
            'chunk_diffs': [],
            'summary': {},
            'critical_changes': [],
            'likely_corruption_cause': None,
        }
        
        result['size_difference'] = result['broken_size'] - result['working_size']
        
        # Compare chunks
        all_keys = set(self.working_chunks.keys()) | set(self.broken_chunks.keys())
        
        modified_count = 0
        added_count = 0
        removed_count = 0
        identical_count = 0
        
        for key in sorted(all_keys):
            chunk_type, chunk_id = key
            working = self.working_chunks.get(key)
            broken = self.broken_chunks.get(key)
            
            if working and broken:
                # Both exist - compare
                if working['data'] == broken['data']:
                    diff = ChunkDiff(
                        chunk_type=chunk_type,
                        chunk_id=chunk_id,
                        label=working['label'],
                        status='identical',
                        old_size=len(working['data']),
                        new_size=len(broken['data']),
                    )
                    identical_count += 1
                else:
                    # Different - analyze
                    byte_diffs = self._find_byte_differences(working['data'], broken['data'])
                    diff = ChunkDiff(
                        chunk_type=chunk_type,
                        chunk_id=chunk_id,
                        label=working['label'],
                        status='modified',
                        size_diff=len(broken['data']) - len(working['data']),
                        byte_diffs=byte_diffs,
                        old_size=len(working['data']),
                        new_size=len(broken['data']),
                    )
                    modified_count += 1
                    
                    # Check if this is a critical modification
                    if self._is_critical_modification(chunk_type, chunk_id, byte_diffs):
                        result['critical_changes'].append(diff)
            elif working:
                # Removed in broken version
                diff = ChunkDiff(
                    chunk_type=chunk_type,
                    chunk_id=chunk_id,
                    label=working['label'],
                    status='removed',
                    old_size=len(working['data']),
                    new_size=0,
                )
                removed_count += 1
            else:
                # Added in broken version
                diff = ChunkDiff(
                    chunk_type=chunk_type,
                    chunk_id=chunk_id,
                    label=broken['label'],
                    status='added',
                    old_size=0,
                    new_size=len(broken['data']),
                )
                added_count += 1
            
            result['chunk_diffs'].append(diff)
        
        result['summary'] = {
            'total_chunks_working': len(self.working_chunks),
            'total_chunks_broken': len(self.broken_chunks),
            'identical': identical_count,
            'modified': modified_count,
            'added': added_count,
            'removed': removed_count,
        }
        
        # Determine likely cause
        result['likely_corruption_cause'] = self._diagnose_corruption(result)
        
        return result
    
    def _parse_chunks(self, filepath: str) -> dict:
        """Parse all chunks from a file."""
        chunks = {}
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        io = IoBuffer.from_bytes(data, ByteOrder.BIG_ENDIAN)
        
        # Skip header
        header = io.read_cstring(60, trim_null=True)
        if not header.startswith("IFF FILE"):
            raise ValueError(f"Not a valid IFF: {filepath}")
        
        rsmp_offset = io.read_uint32()
        
        # Parse chunks
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
            
            key = (type_code, chunk_id)
            chunks[key] = {
                'label': label,
                'flags': chunk_flags,
                'data': chunk_data,
                'offset': start_pos,
            }
        
        return chunks
    
    def _find_byte_differences(self, old_data: bytes, new_data: bytes) -> list:
        """Find all byte differences between two chunks."""
        diffs = []
        max_len = max(len(old_data), len(new_data))
        min_len = min(len(old_data), len(new_data))
        
        # Compare common bytes
        for i in range(min_len):
            if old_data[i] != new_data[i]:
                diffs.append({
                    'offset': i,
                    'old': old_data[i],
                    'new': new_data[i],
                    'old_hex': f'{old_data[i]:02X}',
                    'new_hex': f'{new_data[i]:02X}',
                })
        
        # Note size differences
        if len(old_data) != len(new_data):
            diffs.append({
                'offset': min_len,
                'size_change': len(new_data) - len(old_data),
                'added_or_removed': 'added' if len(new_data) > len(old_data) else 'removed',
            })
        
        return diffs
    
    def _is_critical_modification(self, chunk_type: str, chunk_id: int, byte_diffs: list) -> bool:
        """Check if modification is likely to break the save."""
        # Critical chunk types
        critical_types = ['OBJD', 'GLOB', 'BHAV', 'FAMI', 'SIMI', 'NGBH', 'PDAT']
        
        if chunk_type in critical_types:
            return True
        
        # Large number of changes
        if len(byte_diffs) > 50:
            return True
        
        # Size changes in certain chunks
        for diff in byte_diffs:
            if 'size_change' in diff:
                return True
        
        return False
    
    def _diagnose_corruption(self, result: dict) -> str:
        """Try to determine what caused the corruption."""
        issues = []
        
        # Check for common corruption patterns
        for diff in result['chunk_diffs']:
            if diff.status == 'modified':
                if diff.chunk_type == 'STR#':
                    # String table modifications are usually intentional
                    issues.append(f"STR# chunk {diff.chunk_id} modified ({len(diff.byte_diffs)} changes)")
                elif diff.chunk_type == 'OBJD':
                    issues.append(f"CRITICAL: OBJD chunk {diff.chunk_id} modified - object definition changed!")
                elif diff.chunk_type == 'GLOB':
                    issues.append(f"GLOB chunk {diff.chunk_id} modified - semi-global reference")
                elif diff.chunk_type == 'BHAV':
                    issues.append(f"BHAV chunk {diff.chunk_id} modified - behavior code!")
        
        # Size analysis
        if result['size_difference'] > 0:
            issues.append(f"File grew by {result['size_difference']} bytes")
        elif result['size_difference'] < 0:
            issues.append(f"File shrunk by {-result['size_difference']} bytes")
        
        # Chunk count changes
        if result['summary']['added'] > 0:
            issues.append(f"{result['summary']['added']} chunks added")
        if result['summary']['removed'] > 0:
            issues.append(f"CRITICAL: {result['summary']['removed']} chunks REMOVED!")
        
        return "\n".join(issues) if issues else "No obvious corruption detected"


def print_corruption_report(result: dict):
    """Print a detailed corruption report."""
    print("=" * 80)
    print("SAVE FILE CORRUPTION ANALYSIS REPORT")
    print("=" * 80)
    
    print(f"\nWorking file: {result['working_file']}")
    print(f"Broken file:  {result['broken_file']}")
    print(f"\nFile sizes:")
    print(f"  Working: {result['working_size']:,} bytes")
    print(f"  Broken:  {result['broken_size']:,} bytes")
    print(f"  Difference: {result['size_difference']:+,} bytes")
    
    print(f"\nChunk summary:")
    s = result['summary']
    print(f"  Working chunks: {s['total_chunks_working']}")
    print(f"  Broken chunks:  {s['total_chunks_broken']}")
    print(f"  Identical: {s['identical']}")
    print(f"  Modified:  {s['modified']}")
    print(f"  Added:     {s['added']}")
    print(f"  Removed:   {s['removed']}")
    
    print("\n" + "=" * 80)
    print("DETAILED CHUNK COMPARISON")
    print("=" * 80)
    
    for diff in result['chunk_diffs']:
        if diff.status == 'identical':
            continue  # Skip identical chunks
        
        status_icon = {
            'modified': '📝',
            'added': '➕',
            'removed': '❌',
        }.get(diff.status, '?')
        
        print(f"\n{status_icon} [{diff.chunk_type}] ID={diff.chunk_id} '{diff.label}'")
        print(f"   Status: {diff.status.upper()}")
        print(f"   Size: {diff.old_size} -> {diff.new_size} bytes ({diff.new_size - diff.old_size:+d})")
        
        if diff.byte_diffs:
            # Show first 10 byte differences
            byte_changes = [d for d in diff.byte_diffs if 'old' in d]
            if byte_changes:
                print(f"   Byte changes ({len(byte_changes)} total):")
                for bd in byte_changes[:10]:
                    print(f"     Offset 0x{bd['offset']:04X}: {bd['old_hex']} -> {bd['new_hex']}")
                if len(byte_changes) > 10:
                    print(f"     ... and {len(byte_changes) - 10} more changes")
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)
    print(result['likely_corruption_cause'])
    
    if result['critical_changes']:
        print("\n" + "=" * 80)
        print("⚠️  CRITICAL CHANGES DETECTED")
        print("=" * 80)
        for diff in result['critical_changes']:
            print(f"\n  [{diff.chunk_type}] ID={diff.chunk_id} '{diff.label}'")
            if diff.byte_diffs:
                print(f"    {len(diff.byte_diffs)} modifications")


def hexdump_chunk_comparison(working_path: str, broken_path: str, chunk_type: str, chunk_id: int):
    """Side-by-side hexdump comparison of a specific chunk."""
    analyzer = SaveCorruptionAnalyzer(working_path, broken_path)
    analyzer.working_chunks = analyzer._parse_chunks(working_path)
    analyzer.broken_chunks = analyzer._parse_chunks(broken_path)
    
    key = (chunk_type, chunk_id)
    working = analyzer.working_chunks.get(key)
    broken = analyzer.broken_chunks.get(key)
    
    print(f"\nHEXDUMP COMPARISON: [{chunk_type}] ID={chunk_id}")
    print("=" * 100)
    
    if not working:
        print("Chunk not found in working file")
        return
    if not broken:
        print("Chunk not found in broken file")
        return
    
    print(f"Working: {len(working['data'])} bytes, Broken: {len(broken['data'])} bytes")
    print()
    
    # Side by side comparison
    max_len = max(len(working['data']), len(broken['data']))
    
    print("OFFSET   WORKING (hex)                            BROKEN (hex)                             DIFF")
    print("-" * 100)
    
    for i in range(0, max_len, 16):
        w_chunk = working['data'][i:i+16] if i < len(working['data']) else b''
        b_chunk = broken['data'][i:i+16] if i < len(broken['data']) else b''
        
        w_hex = ' '.join(f'{b:02X}' for b in w_chunk).ljust(48)
        b_hex = ' '.join(f'{b:02X}' for b in b_chunk).ljust(48)
        
        # Mark differences
        diff_markers = []
        for j in range(min(len(w_chunk), len(b_chunk))):
            if w_chunk[j] != b_chunk[j]:
                diff_markers.append(f'{j}')
        
        diff_str = ','.join(diff_markers) if diff_markers else ''
        if len(w_chunk) != len(b_chunk):
            diff_str += ' SIZE!'
        
        print(f"{i:04X}:    {w_hex} {b_hex} {diff_str}")


if __name__ == "__main__":
    test_dir = Path(__file__).parent.parent / "Testing" / "save_analysis"
    
    working = test_dir / "User00088_WORKS.iff"
    broken = test_dir / "User00088_BROKEN.iff"
    
    if working.exists() and broken.exists():
        analyzer = SaveCorruptionAnalyzer(str(working), str(broken))
        result = analyzer.analyze()
        print_corruption_report(result)
        
        # Show detailed comparison for modified chunks
        print("\n" + "=" * 80)
        print("HEXDUMP OF MODIFIED CHUNKS")
        print("=" * 80)
        
        for diff in result['chunk_diffs']:
            if diff.status == 'modified' and diff.byte_diffs:
                hexdump_chunk_comparison(str(working), str(broken), diff.chunk_type, diff.chunk_id)
    else:
        print("Test files not found. Copy User00088_WORKS.iff and User00088_BROKEN.iff to Testing/save_analysis/")
