"""
STR# Reference Scanner — Find all string table references in IFF files.

Scans chunks that reference STR# tables:
- OBJD: catalog_strings_id, body_string_id
- TTAB: tta_index (points to TTAs string table)
- CTSS: Catalog string descriptors
- TTAs: Tree table strings (action names)

Produces a mapping of which STR# chunks are used and by what.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from .chunk_parsers import parse_objd, parse_ttab, MinimalOBJD, MinimalTTAB


class STRReferenceType(Enum):
    """Types of string references."""
    OBJD_CATALOG = "objd_catalog"      # OBJD catalog strings (name, description)
    OBJD_BODY = "objd_body"            # OBJD body strings (skin info)
    TTAB_ACTION = "ttab_action"        # TTAB action name (via TTAs)
    CTSS_CATALOG = "ctss_catalog"      # CTSS catalog description
    UNKNOWN = "unknown"


@dataclass
class STRReference:
    """A single reference to a STR# chunk."""
    str_chunk_id: int
    reference_type: STRReferenceType
    source_chunk_type: str
    source_chunk_id: int
    string_index: int = -1  # -1 means whole chunk, else specific string index
    context: str = ""       # Human-readable context
    
    def __str__(self) -> str:
        idx_str = f"[{self.string_index}]" if self.string_index >= 0 else ""
        return f"STR#{self.str_chunk_id}{idx_str} <- {self.source_chunk_type}:{self.source_chunk_id} ({self.reference_type.value})"


@dataclass
class STRUsageSummary:
    """Summary of STR# usage in a file."""
    str_chunk_id: int
    references: List[STRReference] = field(default_factory=list)
    
    @property
    def is_orphan(self) -> bool:
        """True if this STR# has no references."""
        return len(self.references) == 0
    
    @property
    def reference_count(self) -> int:
        return len(self.references)
    
    def get_referencing_chunks(self) -> Set[Tuple[str, int]]:
        """Get set of (chunk_type, chunk_id) that reference this STR#."""
        return {(ref.source_chunk_type, ref.source_chunk_id) for ref in self.references}


@dataclass
class ScanResult:
    """Result of scanning an IFF file for STR# references."""
    filename: str = ""
    
    # All STR# chunks found in file
    str_chunks_found: List[int] = field(default_factory=list)
    
    # References organized by STR# chunk ID
    usage_by_str: Dict[int, STRUsageSummary] = field(default_factory=dict)
    
    # All references found
    all_references: List[STRReference] = field(default_factory=list)
    
    # Errors during scanning
    errors: List[str] = field(default_factory=list)
    
    def get_orphan_str_chunks(self) -> List[int]:
        """Get STR# chunks that are not referenced by anything."""
        referenced = {ref.str_chunk_id for ref in self.all_references}
        return [sid for sid in self.str_chunks_found if sid not in referenced]
    
    def get_referenced_str_chunks(self) -> List[int]:
        """Get STR# chunks that are referenced."""
        return list({ref.str_chunk_id for ref in self.all_references})
    
    def get_summary(self) -> Dict:
        """Get human-readable summary."""
        orphans = self.get_orphan_str_chunks()
        return {
            "total_str_chunks": len(self.str_chunks_found),
            "referenced_str_chunks": len(self.get_referenced_str_chunks()),
            "orphan_str_chunks": orphans,
            "total_references": len(self.all_references),
            "reference_types": self._count_by_type(),
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        counts = {}
        for ref in self.all_references:
            key = ref.reference_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts


class STRReferenceScanner:
    """
    Scanner for finding all STR# references in an IFF file.
    
    Usage:
        scanner = STRReferenceScanner()
        result = scanner.scan_iff(iff_reader)
        print(result.get_summary())
    """
    
    # Well-known STR# chunk IDs
    CATALOG_STRINGS_ID = 202      # Standard catalog strings
    BODY_STRINGS_ID = 200         # Body/skin strings (User files)
    BODY_STRINGS_ALT_ID = 51200   # Alternate body strings ID
    
    def __init__(self):
        self._reset()
    
    def _reset(self):
        """Reset scanner state."""
        self._result = ScanResult()
        self._chunks_by_type: Dict[str, List[Tuple[int, bytes]]] = {}
    
    def scan_iff(self, iff_reader, filename: str = "") -> ScanResult:
        """
        Scan an IFF file for all STR# references.
        
        Args:
            iff_reader: An IFFReader instance with chunks loaded
            filename: Optional filename for context
            
        Returns:
            ScanResult with all references found
        """
        self._reset()
        self._result.filename = filename
        
        # Index chunks by type
        self._index_chunks(iff_reader)
        
        # Find all STR# chunks
        self._find_str_chunks()
        
        # Scan for references
        self._scan_objd_references()
        self._scan_ttab_references()
        self._scan_ctss_references()
        
        # Build usage summaries
        self._build_usage_summaries()
        
        return self._result
    
    def _index_chunks(self, iff_reader):
        """Index all chunks by type for efficient lookup."""
        for chunk in iff_reader.chunks:
            type_code = chunk.type_code
            if type_code not in self._chunks_by_type:
                self._chunks_by_type[type_code] = []
            self._chunks_by_type[type_code].append((chunk.chunk_id, chunk.chunk_data))
    
    def _find_str_chunks(self):
        """Find all STR# chunks in the file."""
        str_chunks = self._chunks_by_type.get('STR#', [])
        self._result.str_chunks_found = [chunk_id for chunk_id, _ in str_chunks]
    
    def _scan_objd_references(self):
        """Scan OBJD chunks for STR# references."""
        objd_chunks = self._chunks_by_type.get('OBJD', [])
        
        for chunk_id, chunk_data in objd_chunks:
            try:
                objd = parse_objd(chunk_data, chunk_id)
                if objd is None:
                    continue
                
                # Catalog strings reference
                if objd.catalog_strings_id != 0:
                    ref = STRReference(
                        str_chunk_id=objd.catalog_strings_id,
                        reference_type=STRReferenceType.OBJD_CATALOG,
                        source_chunk_type="OBJD",
                        source_chunk_id=chunk_id,
                        context=f"Catalog strings for object"
                    )
                    self._result.all_references.append(ref)
                
                # Body strings reference  
                if objd.body_string_id != 0:
                    ref = STRReference(
                        str_chunk_id=objd.body_string_id,
                        reference_type=STRReferenceType.OBJD_BODY,
                        source_chunk_type="OBJD",
                        source_chunk_id=chunk_id,
                        context=f"Body strings for object"
                    )
                    self._result.all_references.append(ref)
                    
            except Exception as e:
                self._result.errors.append(f"Error parsing OBJD {chunk_id}: {e}")
    
    def _scan_ttab_references(self):
        """
        Scan TTAB chunks for STR# references.
        
        TTAB interactions reference TTAs (tree table strings) by index.
        TTAs is typically STR# chunk ID that matches the TTAB chunk ID.
        """
        ttab_chunks = self._chunks_by_type.get('TTAB', [])
        ttas_chunks = self._chunks_by_type.get('TTAs', [])
        
        # Map TTAs by ID for lookup
        ttas_ids = {chunk_id for chunk_id, _ in ttas_chunks}
        
        for chunk_id, chunk_data in ttab_chunks:
            try:
                ttab = parse_ttab(chunk_data, chunk_id)
                if ttab is None:
                    continue
                
                # Each TTAB typically has a matching TTAs
                # TTAs can be:
                # - Same ID as TTAB
                # - Standard ID like 202 (catalog strings)
                # - Custom ID
                
                # First, check if there's a TTAs with same ID
                ttas_id = chunk_id if chunk_id in ttas_ids else None
                
                # If no matching TTAs, check for STR# with same ID
                if ttas_id is None and chunk_id in self._result.str_chunks_found:
                    ttas_id = chunk_id
                
                for interaction in ttab.interactions:
                    if interaction.tta_index >= 0 and ttas_id is not None:
                        ref = STRReference(
                            str_chunk_id=ttas_id,
                            reference_type=STRReferenceType.TTAB_ACTION,
                            source_chunk_type="TTAB",
                            source_chunk_id=chunk_id,
                            string_index=interaction.tta_index,
                            context=f"Action name at index {interaction.tta_index}"
                        )
                        self._result.all_references.append(ref)
                        
            except Exception as e:
                self._result.errors.append(f"Error parsing TTAB {chunk_id}: {e}")
    
    def _scan_ctss_references(self):
        """
        Scan CTSS (Catalog Strings) chunks.
        
        CTSS is itself a string container but may reference other STR# chunks.
        """
        ctss_chunks = self._chunks_by_type.get('CTSS', [])
        
        for chunk_id, chunk_data in ctss_chunks:
            # CTSS is typically used directly, not as a reference
            # But record that it exists as a string source
            # Mark as self-referential (the chunk IS the string table)
            ref = STRReference(
                str_chunk_id=chunk_id,
                reference_type=STRReferenceType.CTSS_CATALOG,
                source_chunk_type="CTSS",
                source_chunk_id=chunk_id,
                context="Catalog description strings"
            )
            self._result.all_references.append(ref)
    
    def _build_usage_summaries(self):
        """Build per-STR# usage summaries."""
        # Initialize summaries for all STR# chunks
        for str_id in self._result.str_chunks_found:
            self._result.usage_by_str[str_id] = STRUsageSummary(str_chunk_id=str_id)
        
        # Add references to summaries
        for ref in self._result.all_references:
            if ref.str_chunk_id not in self._result.usage_by_str:
                # Reference to STR# that doesn't exist in this file
                self._result.usage_by_str[ref.str_chunk_id] = STRUsageSummary(
                    str_chunk_id=ref.str_chunk_id
                )
            
            self._result.usage_by_str[ref.str_chunk_id].references.append(ref)


def scan_file_for_str_references(iff_reader, filename: str = "") -> ScanResult:
    """
    Convenience function to scan a file for STR# references.
    
    Args:
        iff_reader: An IFFReader instance
        filename: Optional filename
        
    Returns:
        ScanResult with all found references
    """
    scanner = STRReferenceScanner()
    return scanner.scan_iff(iff_reader, filename)


def get_localization_audit_report(
    iff_reader,
    str_parser_module,
    filename: str = ""
) -> Dict:
    """
    Generate a localization audit report for an IFF file.
    
    Combines STR# reference scanning with language population analysis.
    
    Args:
        iff_reader: An IFFReader instance
        str_parser_module: The str_parser module (for ParsedSTR)
        filename: Optional filename
        
    Returns:
        Dict with audit results
    """
    # Scan for references
    scanner = STRReferenceScanner()
    scan_result = scanner.scan_iff(iff_reader, filename)
    
    # Analyze each referenced STR# for language population
    language_audit = {}
    
    for chunk in iff_reader.chunks:
        if chunk.type_code != 'STR#':
            continue
            
        str_id = chunk.chunk_id
        parsed = str_parser_module.STRParser.parse(chunk.chunk_data, str_id)
        
        summary = parsed.get_localization_summary()
        usage = scan_result.usage_by_str.get(str_id)
        
        language_audit[str_id] = {
            "chunk_id": str_id,
            "is_orphan": usage.is_orphan if usage else True,
            "reference_count": usage.reference_count if usage else 0,
            **summary
        }
    
    return {
        "filename": filename,
        "scan_summary": scan_result.get_summary(),
        "language_audit": language_audit,
        "errors": scan_result.errors
    }
