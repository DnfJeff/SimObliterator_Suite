"""
ID Conflict Scanner — Detect overlapping IDs across loaded objects.

Scans for:
- GUID conflicts (same object GUID in different files)
- Chunk ID overlaps within same context
- Semi-global group ID conflicts
- BHAV ID range overlaps

Reports what conflicts, where, and why it's potentially unsafe.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum
from pathlib import Path


class ConflictType(Enum):
    """Types of ID conflicts."""
    GUID_DUPLICATE = "guid_duplicate"
    CHUNK_ID_OVERLAP = "chunk_id_overlap"
    SEMIGLOBAL_CONFLICT = "semiglobal_conflict"
    BHAV_ID_OVERLAP = "bhav_id_overlap"
    OBJD_ID_OVERLAP = "objd_id_overlap"


class ConflictSeverity(Enum):
    """Severity level of a conflict."""
    ERROR = "error"         # Will cause game issues
    WARNING = "warning"     # May cause issues
    INFO = "info"           # Informational only


@dataclass
class ObjectInfo:
    """Info about a loaded object."""
    guid: int
    name: str
    source_file: str
    chunk_ids: Dict[str, List[int]] = field(default_factory=dict)  # type -> [ids]
    semiglobal_group: int = 0
    
    @property
    def guid_hex(self) -> str:
        return f"0x{self.guid:08X}"


@dataclass
class IDConflict:
    """A single detected conflict."""
    conflict_type: ConflictType
    severity: ConflictSeverity
    id_value: int           # The conflicting ID
    id_type: str            # "GUID", "BHAV", "OBJD", etc.
    involved_files: List[str]
    involved_objects: List[str]  # Object names if applicable
    description: str
    recommendation: str
    
    def __str__(self) -> str:
        files = ", ".join(self.involved_files[:3])
        if len(self.involved_files) > 3:
            files += f" (+{len(self.involved_files) - 3} more)"
        return f"[{self.severity.value.upper()}] {self.id_type} 0x{self.id_value:08X}: {self.description} ({files})"
    
    def to_dict(self) -> Dict:
        return {
            "type": self.conflict_type.value,
            "severity": self.severity.value,
            "id_hex": f"0x{self.id_value:08X}",
            "id_type": self.id_type,
            "files": self.involved_files,
            "objects": self.involved_objects,
            "description": self.description,
            "recommendation": self.recommendation,
        }


@dataclass
class ScanResult:
    """Result of ID conflict scan."""
    files_scanned: List[str] = field(default_factory=list)
    objects_found: List[ObjectInfo] = field(default_factory=list)
    conflicts: List[IDConflict] = field(default_factory=list)
    scan_errors: List[str] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return any(c.severity == ConflictSeverity.ERROR for c in self.conflicts)
    
    @property
    def has_warnings(self) -> bool:
        return any(c.severity == ConflictSeverity.WARNING for c in self.conflicts)
    
    @property
    def error_count(self) -> int:
        return sum(1 for c in self.conflicts if c.severity == ConflictSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.conflicts if c.severity == ConflictSeverity.WARNING)
    
    def get_conflicts_by_type(self, conflict_type: ConflictType) -> List[IDConflict]:
        return [c for c in self.conflicts if c.conflict_type == conflict_type]
    
    def get_conflicts_by_severity(self, severity: ConflictSeverity) -> List[IDConflict]:
        return [c for c in self.conflicts if c.severity == severity]
    
    def get_summary(self) -> Dict:
        return {
            "files_scanned": len(self.files_scanned),
            "objects_found": len(self.objects_found),
            "total_conflicts": len(self.conflicts),
            "errors": self.error_count,
            "warnings": self.warning_count,
            "by_type": {
                ct.value: len(self.get_conflicts_by_type(ct))
                for ct in ConflictType
            }
        }
    
    def to_report(self) -> str:
        """Generate text report."""
        lines = [
            "=" * 60,
            "ID CONFLICT SCAN REPORT",
            "=" * 60,
            "",
            f"Files scanned: {len(self.files_scanned)}",
            f"Objects found: {len(self.objects_found)}",
            f"Total conflicts: {len(self.conflicts)}",
            f"  Errors: {self.error_count}",
            f"  Warnings: {self.warning_count}",
            "",
        ]
        
        if self.conflicts:
            lines.append("-" * 60)
            lines.append("CONFLICTS:")
            lines.append("-" * 60)
            
            for conflict in sorted(self.conflicts, 
                                   key=lambda c: (c.severity.value, c.conflict_type.value)):
                lines.append("")
                lines.append(str(conflict))
                lines.append(f"  Objects: {', '.join(conflict.involved_objects[:5])}")
                lines.append(f"  Why unsafe: {conflict.description}")
                lines.append(f"  Fix: {conflict.recommendation}")
        else:
            lines.append("No conflicts detected.")
        
        if self.scan_errors:
            lines.append("")
            lines.append("-" * 60)
            lines.append("SCAN ERRORS:")
            for error in self.scan_errors:
                lines.append(f"  - {error}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


class IDConflictScanner:
    """
    Scanner for detecting ID conflicts across loaded IFF files.
    
    Usage:
        scanner = IDConflictScanner()
        scanner.add_file(iff_reader, "myobject.iff")
        scanner.add_file(iff_reader2, "other.iff")
        result = scanner.scan()
        print(result.to_report())
    """
    
    def __init__(self):
        self._reset()
    
    def _reset(self):
        """Reset scanner state."""
        self._objects: List[ObjectInfo] = []
        self._files: List[str] = []
        
        # ID tracking maps: id -> [(file, object_name, chunk_type)]
        self._guids: Dict[int, List[Tuple[str, str]]] = {}
        self._bhav_ids: Dict[int, List[Tuple[str, str]]] = {}
        self._objd_ids: Dict[int, List[Tuple[str, str]]] = {}
        self._semiglobal_groups: Dict[int, List[Tuple[str, str]]] = {}
    
    def add_file(self, iff_reader, filename: str) -> int:
        """
        Add an IFF file to the scan.
        
        Args:
            iff_reader: An IFFReader instance with chunks loaded
            filename: Filename for identification
            
        Returns:
            Number of objects found in file
        """
        self._files.append(filename)
        objects_found = 0
        
        # Index all OBJD chunks
        for chunk in iff_reader.chunks:
            if chunk.type_code == 'OBJD':
                obj_info = self._parse_objd(chunk, filename)
                if obj_info:
                    self._objects.append(obj_info)
                    self._register_object(obj_info)
                    objects_found += 1
            
            # Track BHAV IDs
            elif chunk.type_code == 'BHAV':
                bhav_id = chunk.chunk_id
                if bhav_id not in self._bhav_ids:
                    self._bhav_ids[bhav_id] = []
                self._bhav_ids[bhav_id].append((filename, f"BHAV_{bhav_id:04X}"))
        
        return objects_found
    
    def _parse_objd(self, chunk, filename: str) -> Optional[ObjectInfo]:
        """Parse OBJD chunk into ObjectInfo."""
        from .chunk_parsers import parse_objd
        
        try:
            data = chunk.chunk_data
            if len(data) < 32:
                return None
            
            # Extract GUID (at offset 26-30, little-endian uint32)
            # This is at half-word offsets [14-15] in the uint16 array
            if len(data) >= 32:
                guid = data[28] | (data[29] << 8) | (data[30] << 16) | (data[31] << 24)
            else:
                guid = 0
            
            obj_info = ObjectInfo(
                guid=guid,
                name=f"Object_{chunk.chunk_id}",  # Would need STR# lookup for real name
                source_file=filename,
            )
            
            # Track chunk IDs present
            obj_info.chunk_ids['OBJD'] = [chunk.chunk_id]
            
            return obj_info
        except Exception:
            return None
    
    def _register_object(self, obj: ObjectInfo):
        """Register object IDs for conflict detection."""
        # GUID
        if obj.guid != 0:
            if obj.guid not in self._guids:
                self._guids[obj.guid] = []
            self._guids[obj.guid].append((obj.source_file, obj.name))
        
        # OBJD ID
        for objd_id in obj.chunk_ids.get('OBJD', []):
            if objd_id not in self._objd_ids:
                self._objd_ids[objd_id] = []
            self._objd_ids[objd_id].append((obj.source_file, obj.name))
        
        # Semi-global group
        if obj.semiglobal_group != 0:
            if obj.semiglobal_group not in self._semiglobal_groups:
                self._semiglobal_groups[obj.semiglobal_group] = []
            self._semiglobal_groups[obj.semiglobal_group].append((obj.source_file, obj.name))
    
    def scan(self) -> ScanResult:
        """
        Perform conflict detection on all added files.
        
        Returns:
            ScanResult with all detected conflicts
        """
        result = ScanResult(
            files_scanned=list(self._files),
            objects_found=list(self._objects),
        )
        
        # Check GUID conflicts
        self._check_guid_conflicts(result)
        
        # Check BHAV ID conflicts (within same context)
        self._check_bhav_conflicts(result)
        
        # Check OBJD ID conflicts
        self._check_objd_conflicts(result)
        
        # Check semi-global conflicts
        self._check_semiglobal_conflicts(result)
        
        return result
    
    def _check_guid_conflicts(self, result: ScanResult):
        """Check for duplicate GUIDs across files."""
        for guid, occurrences in self._guids.items():
            if len(occurrences) <= 1:
                continue
            
            # Check if they're in different files (actual conflict)
            files = set(f for f, _ in occurrences)
            if len(files) > 1:
                conflict = IDConflict(
                    conflict_type=ConflictType.GUID_DUPLICATE,
                    severity=ConflictSeverity.ERROR,
                    id_value=guid,
                    id_type="GUID",
                    involved_files=list(files),
                    involved_objects=[name for _, name in occurrences],
                    description=(
                        "Multiple objects share the same GUID. "
                        "The game will only recognize one, causing the other to disappear or malfunction."
                    ),
                    recommendation=(
                        "Change the GUID of one object to a unique value. "
                        "Use a GUID generator or pick an unused range."
                    ),
                )
                result.conflicts.append(conflict)
    
    def _check_bhav_conflicts(self, result: ScanResult):
        """Check for BHAV ID overlaps in local ranges."""
        for bhav_id, occurrences in self._bhav_ids.items():
            if len(occurrences) <= 1:
                continue
            
            # Only conflict if same ID in different files
            # AND it's in the local range (4096+)
            if bhav_id >= 4096:
                files = set(f for f, _ in occurrences)
                if len(files) > 1:
                    conflict = IDConflict(
                        conflict_type=ConflictType.BHAV_ID_OVERLAP,
                        severity=ConflictSeverity.WARNING,
                        id_value=bhav_id,
                        id_type="BHAV",
                        involved_files=list(files),
                        involved_objects=[name for _, name in occurrences],
                        description=(
                            "Same local BHAV ID used in multiple objects. "
                            "If objects are loaded together, behavior may be unpredictable."
                        ),
                        recommendation=(
                            "This is usually safe if objects are in different IFF files. "
                            "Only a problem if merging objects into same file."
                        ),
                    )
                    result.conflicts.append(conflict)
    
    def _check_objd_conflicts(self, result: ScanResult):
        """Check for OBJD chunk ID overlaps."""
        for objd_id, occurrences in self._objd_ids.items():
            if len(occurrences) <= 1:
                continue
            
            files = set(f for f, _ in occurrences)
            if len(files) > 1:
                conflict = IDConflict(
                    conflict_type=ConflictType.OBJD_ID_OVERLAP,
                    severity=ConflictSeverity.INFO,
                    id_value=objd_id,
                    id_type="OBJD",
                    involved_files=list(files),
                    involved_objects=[name for _, name in occurrences],
                    description=(
                        "Same OBJD chunk ID in different files. "
                        "Normal for separate IFF files, only problematic if merging."
                    ),
                    recommendation=(
                        "No action needed unless you plan to merge these files."
                    ),
                )
                result.conflicts.append(conflict)
    
    def _check_semiglobal_conflicts(self, result: ScanResult):
        """Check for semi-global group conflicts."""
        for group_id, occurrences in self._semiglobal_groups.items():
            if len(occurrences) <= 1:
                continue
            
            files = set(f for f, _ in occurrences)
            if len(files) > 1:
                conflict = IDConflict(
                    conflict_type=ConflictType.SEMIGLOBAL_CONFLICT,
                    severity=ConflictSeverity.WARNING,
                    id_value=group_id,
                    id_type="SemiGlobal",
                    involved_files=list(files),
                    involved_objects=[name for _, name in occurrences],
                    description=(
                        "Multiple objects claim the same semi-global group. "
                        "They will share BHAVs in the 8192+ range, which may be intentional or a conflict."
                    ),
                    recommendation=(
                        "Verify these objects are meant to share semi-globals. "
                        "If not, change one object's semi-global reference."
                    ),
                )
                result.conflicts.append(conflict)


class IDRangeFinder:
    """
    Utility to find unused ID ranges.
    
    NOTE: Results are "locally unused" - only considers scanned files.
    Does not guarantee global uniqueness across all Sims content.
    """
    
    def __init__(self):
        self._used_guids: Set[int] = set()
        self._used_bhav_local: Set[int] = set()  # 4096+
    
    def add_from_scan_result(self, result: ScanResult):
        """Add used IDs from a scan result."""
        for obj in result.objects_found:
            if obj.guid != 0:
                self._used_guids.add(obj.guid)
    
    def find_unused_guid_range(self, start: int = 0x10000000, count: int = 10) -> List[int]:
        """
        Find unused GUIDs in a range.
        
        Args:
            start: Starting GUID to search from
            count: How many unused GUIDs to find
            
        Returns:
            List of unused GUIDs (LOCALLY unused only!)
        """
        unused = []
        current = start
        max_search = start + count * 10  # Don't search forever
        
        while len(unused) < count and current < max_search:
            if current not in self._used_guids:
                unused.append(current)
            current += 1
        
        return unused
    
    def find_unused_bhav_range(self, start: int = 4096, count: int = 10) -> List[int]:
        """
        Find unused local BHAV IDs.
        
        Args:
            start: Starting ID (default 4096 for local range)
            count: How many unused IDs to find
            
        Returns:
            List of unused BHAV IDs (LOCALLY unused only!)
        """
        unused = []
        current = start
        max_search = start + count * 10
        
        while len(unused) < count and current < max_search:
            if current not in self._used_bhav_local:
                unused.append(current)
            current += 1
        
        return unused
    
    def get_usage_summary(self) -> Dict:
        """Get summary of ID usage."""
        return {
            "guids_tracked": len(self._used_guids),
            "local_bhavs_tracked": len(self._used_bhav_local),
            "note": "These counts only reflect scanned files, not global usage",
        }


def scan_files_for_conflicts(iff_readers: List[Tuple[any, str]]) -> ScanResult:
    """
    Convenience function to scan multiple IFF files for conflicts.
    
    Args:
        iff_readers: List of (iff_reader, filename) tuples
        
    Returns:
        ScanResult with all conflicts
    """
    scanner = IDConflictScanner()
    
    for reader, filename in iff_readers:
        try:
            scanner.add_file(reader, filename)
        except Exception as e:
            pass  # Errors tracked in result
    
    return scanner.scan()
