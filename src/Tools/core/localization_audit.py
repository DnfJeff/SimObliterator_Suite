"""
Localization Audit — Check string tables for missing language entries.

Provides:
- Scan pass finding all STR# references used by OBJD catalog and TTAB interactions
- Per-string language slot population check
- Optional save-time warning system
- One-click action to copy language to missing slots
- User preference toggles

This is the main interface for localization checking in the tool.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import json
from pathlib import Path

from .str_parser import (
    STRParser, STRSerializer, ParsedSTR, StringEntry, LanguageSlot,
    LanguageCode, copy_language_to_missing
)
from .str_reference_scanner import (
    STRReferenceScanner, ScanResult, STRReference, STRReferenceType
)


class AuditLevel(Enum):
    """Audit strictness levels."""
    SILENT = "silent"           # No warnings
    WARN_CATALOG = "warn_catalog"  # Warn only for catalog strings
    WARN_ALL = "warn_all"       # Warn for all referenced strings
    STRICT = "strict"           # Treat missing as error


@dataclass
class LocalizationIssue:
    """A single localization issue found."""
    str_chunk_id: int
    string_index: int
    issue_type: str             # "missing_language", "empty_string", etc.
    severity: str               # "warning", "error", "info"
    populated_languages: List[int]
    missing_languages: List[int]
    referenced_by: List[str]    # Description of what references this string
    
    def __str__(self) -> str:
        pop = ", ".join(LanguageCode.get_name(c) for c in self.populated_languages[:3])
        miss = ", ".join(LanguageCode.get_name(c) for c in self.missing_languages[:3])
        return f"STR#{self.str_chunk_id}[{self.string_index}]: has {pop}; missing {miss}"
    
    def to_dict(self) -> Dict:
        return {
            "str_chunk_id": self.str_chunk_id,
            "string_index": self.string_index,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "populated_languages": [
                {"code": c, "name": LanguageCode.get_name(c)} 
                for c in self.populated_languages
            ],
            "missing_languages": [
                {"code": c, "name": LanguageCode.get_name(c)} 
                for c in self.missing_languages
            ],
            "referenced_by": self.referenced_by,
        }


@dataclass
class LocalizationAuditResult:
    """Complete audit result for a file."""
    filename: str = ""
    
    # STR# chunks analyzed
    str_chunks_audited: List[int] = field(default_factory=list)
    
    # All issues found
    issues: List[LocalizationIssue] = field(default_factory=list)
    
    # Summary stats
    total_strings: int = 0
    strings_with_issues: int = 0
    
    # Languages found
    languages_detected: Set[int] = field(default_factory=set)
    
    # Config used
    required_languages: List[int] = field(default_factory=list)
    audit_level: AuditLevel = AuditLevel.WARN_CATALOG
    
    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")
    
    def get_issues_by_chunk(self, chunk_id: int) -> List[LocalizationIssue]:
        return [i for i in self.issues if i.str_chunk_id == chunk_id]
    
    def get_summary(self) -> Dict:
        return {
            "filename": self.filename,
            "str_chunks_audited": len(self.str_chunks_audited),
            "total_strings": self.total_strings,
            "strings_with_issues": self.strings_with_issues,
            "total_issues": len(self.issues),
            "errors": self.error_count,
            "warnings": self.warning_count,
            "languages_detected": sorted(self.languages_detected),
            "required_languages": self.required_languages,
            "audit_level": self.audit_level.value,
        }
    
    def to_report(self) -> str:
        """Generate text report."""
        lines = [
            "=" * 60,
            "LOCALIZATION AUDIT REPORT",
            "=" * 60,
            "",
            f"File: {self.filename}",
            f"STR# chunks audited: {len(self.str_chunks_audited)}",
            f"Total strings: {self.total_strings}",
            f"Strings with issues: {self.strings_with_issues}",
            f"Audit level: {self.audit_level.value}",
            "",
            f"Languages detected: {', '.join(LanguageCode.get_name(c) for c in sorted(self.languages_detected))}",
            f"Required languages: {', '.join(LanguageCode.get_name(c) for c in self.required_languages)}",
            "",
        ]
        
        if self.issues:
            lines.append("-" * 60)
            lines.append("ISSUES:")
            lines.append("-" * 60)
            
            # Group by chunk
            by_chunk: Dict[int, List[LocalizationIssue]] = {}
            for issue in self.issues:
                if issue.str_chunk_id not in by_chunk:
                    by_chunk[issue.str_chunk_id] = []
                by_chunk[issue.str_chunk_id].append(issue)
            
            for chunk_id in sorted(by_chunk.keys()):
                lines.append("")
                lines.append(f"STR# {chunk_id}:")
                for issue in by_chunk[chunk_id]:
                    lines.append(f"  [{issue.severity.upper()}] {issue}")
                    if issue.referenced_by:
                        lines.append(f"    Used by: {', '.join(issue.referenced_by[:3])}")
        else:
            lines.append("No localization issues found.")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


class LocalizationPreferences:
    """User preferences for localization checking."""
    
    DEFAULT_PREFS_FILE = "localization_prefs.json"
    
    def __init__(self):
        self.audit_level: AuditLevel = AuditLevel.WARN_CATALOG
        self.required_languages: List[int] = [0]  # US English by default
        self.source_language: int = 0  # For copy operations
        self.warn_on_save: bool = True
        self.auto_fix: bool = False  # Never auto-fix by default
    
    def to_dict(self) -> Dict:
        return {
            "audit_level": self.audit_level.value,
            "required_languages": self.required_languages,
            "source_language": self.source_language,
            "warn_on_save": self.warn_on_save,
            "auto_fix": self.auto_fix,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LocalizationPreferences':
        prefs = cls()
        if "audit_level" in data:
            prefs.audit_level = AuditLevel(data["audit_level"])
        if "required_languages" in data:
            prefs.required_languages = data["required_languages"]
        if "source_language" in data:
            prefs.source_language = data["source_language"]
        if "warn_on_save" in data:
            prefs.warn_on_save = data["warn_on_save"]
        if "auto_fix" in data:
            prefs.auto_fix = data["auto_fix"]
        return prefs
    
    def save(self, filepath: str):
        """Save preferences to JSON."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'LocalizationPreferences':
        """Load preferences from JSON."""
        if not Path(filepath).exists():
            return cls()
        with open(filepath, 'r') as f:
            return cls.from_dict(json.load(f))


class LocalizationAuditor:
    """
    Main auditor for checking localization completeness.
    
    Usage:
        auditor = LocalizationAuditor()
        auditor.set_preferences(prefs)
        result = auditor.audit(iff_reader, "myobject.iff")
        print(result.to_report())
    """
    
    def __init__(self):
        self._prefs = LocalizationPreferences()
        self._reference_scanner = STRReferenceScanner()
    
    def set_preferences(self, prefs: LocalizationPreferences):
        """Set audit preferences."""
        self._prefs = prefs
    
    def audit(self, iff_reader, filename: str = "") -> LocalizationAuditResult:
        """
        Audit an IFF file for localization issues.
        
        Args:
            iff_reader: An IFFReader instance with chunks loaded
            filename: Filename for context
            
        Returns:
            LocalizationAuditResult with all issues
        """
        result = LocalizationAuditResult(
            filename=filename,
            required_languages=list(self._prefs.required_languages),
            audit_level=self._prefs.audit_level,
        )
        
        if self._prefs.audit_level == AuditLevel.SILENT:
            return result  # No checking
        
        # Scan for references
        scan_result = self._reference_scanner.scan_iff(iff_reader, filename)
        
        # Determine which STR# chunks to audit based on level
        chunks_to_audit = self._get_chunks_to_audit(scan_result)
        result.str_chunks_audited = chunks_to_audit
        
        # Parse and audit each STR# chunk
        str_chunks_data = {}
        for chunk in iff_reader.chunks:
            if chunk.type_code == 'STR#':
                str_chunks_data[chunk.chunk_id] = chunk.chunk_data
        
        for chunk_id in chunks_to_audit:
            if chunk_id not in str_chunks_data:
                continue
            
            parsed = STRParser.parse(str_chunks_data[chunk_id], chunk_id)
            result.total_strings += len(parsed.entries)
            
            # Get references for context
            refs = scan_result.usage_by_str.get(chunk_id)
            ref_descriptions = []
            if refs:
                for ref in refs.references[:3]:
                    ref_descriptions.append(f"{ref.source_chunk_type}:{ref.source_chunk_id}")
            
            # Check each string entry
            for entry in parsed.entries:
                # Track languages found
                result.languages_detected.update(entry.get_populated_languages())
                
                # Check for missing required languages
                missing = entry.get_missing_languages(self._prefs.required_languages)
                
                if missing:
                    result.strings_with_issues += 1
                    
                    severity = "warning"
                    if self._prefs.audit_level == AuditLevel.STRICT:
                        severity = "error"
                    
                    issue = LocalizationIssue(
                        str_chunk_id=chunk_id,
                        string_index=entry.index,
                        issue_type="missing_language",
                        severity=severity,
                        populated_languages=entry.get_populated_languages(),
                        missing_languages=missing,
                        referenced_by=ref_descriptions,
                    )
                    result.issues.append(issue)
        
        return result
    
    def _get_chunks_to_audit(self, scan_result: ScanResult) -> List[int]:
        """Determine which STR# chunks to audit based on preferences."""
        if self._prefs.audit_level == AuditLevel.WARN_CATALOG:
            # Only catalog-related strings
            chunks = set()
            for ref in scan_result.all_references:
                if ref.reference_type in [
                    STRReferenceType.OBJD_CATALOG,
                    STRReferenceType.CTSS_CATALOG,
                    STRReferenceType.TTAB_ACTION,
                ]:
                    chunks.add(ref.str_chunk_id)
            return sorted(chunks)
        
        elif self._prefs.audit_level in [AuditLevel.WARN_ALL, AuditLevel.STRICT]:
            # All referenced strings
            return sorted(scan_result.get_referenced_str_chunks())
        
        return []


@dataclass
class CopyLanguageResult:
    """Result of copying a language to missing slots."""
    success: bool
    slots_filled: int = 0
    chunks_modified: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    preview: Dict[int, List[str]] = field(default_factory=dict)  # chunk_id -> [changes]


class LocalizationFixer:
    """
    Utility for fixing localization issues.
    
    Provides copy operations to fill missing language slots.
    """
    
    def __init__(self):
        pass
    
    def preview_copy(
        self,
        iff_reader,
        source_language: int = 0,
        target_languages: List[int] = None,
        chunks_to_fix: List[int] = None
    ) -> CopyLanguageResult:
        """
        Preview what would change when copying a language.
        
        Args:
            iff_reader: IFF file to fix
            source_language: Language to copy from (default: US English)
            target_languages: Languages to populate
            chunks_to_fix: Specific chunks to fix (None = all)
            
        Returns:
            CopyLanguageResult with preview of changes
        """
        result = CopyLanguageResult(success=True)
        
        for chunk in iff_reader.chunks:
            if chunk.type_code != 'STR#':
                continue
            
            if chunks_to_fix and chunk.chunk_id not in chunks_to_fix:
                continue
            
            parsed = STRParser.parse(chunk.chunk_data, chunk.chunk_id)
            _, would_fill = copy_language_to_missing(
                parsed, source_language, target_languages
            )
            
            if would_fill > 0:
                result.slots_filled += would_fill
                result.chunks_modified.append(chunk.chunk_id)
                
                # Build preview descriptions
                preview_lines = []
                for entry in parsed.entries:
                    if source_language in entry.slots:
                        source_val = entry.slots[source_language].value[:30]
                        targets = [
                            LanguageCode.get_name(t) 
                            for t in (target_languages or range(20))
                            if t not in entry.get_populated_languages()
                        ]
                        if targets:
                            preview_lines.append(
                                f"[{entry.index}] \"{source_val}...\" -> {', '.join(targets[:3])}"
                            )
                
                result.preview[chunk.chunk_id] = preview_lines[:10]  # First 10
        
        return result
    
    def apply_copy(
        self,
        iff_reader,
        source_language: int = 0,
        target_languages: List[int] = None,
        chunks_to_fix: List[int] = None
    ) -> Tuple[CopyLanguageResult, Dict[int, bytes]]:
        """
        Apply language copy operation.
        
        Args:
            iff_reader: IFF file to fix
            source_language: Language to copy from
            target_languages: Languages to populate
            chunks_to_fix: Specific chunks to fix
            
        Returns:
            Tuple of (result, {chunk_id: new_chunk_data})
        """
        result = CopyLanguageResult(success=True)
        new_chunks = {}
        
        for chunk in iff_reader.chunks:
            if chunk.type_code != 'STR#':
                continue
            
            if chunks_to_fix and chunk.chunk_id not in chunks_to_fix:
                continue
            
            parsed = STRParser.parse(chunk.chunk_data, chunk.chunk_id)
            modified, filled = copy_language_to_missing(
                parsed, source_language, target_languages
            )
            
            if filled > 0:
                result.slots_filled += filled
                result.chunks_modified.append(chunk.chunk_id)
                
                # Serialize back
                # Use language-coded format if we have multiple languages
                has_multi_lang = any(
                    len(entry.slots) > 1 for entry in modified.entries
                )
                format_code = 0xFDFF if has_multi_lang else modified.format_code
                
                new_data = STRSerializer.serialize(modified, format_code)
                new_chunks[chunk.chunk_id] = new_data
        
        return result, new_chunks


def audit_file(iff_reader, filename: str = "", prefs: LocalizationPreferences = None) -> LocalizationAuditResult:
    """
    Convenience function to audit a file.
    
    Args:
        iff_reader: IFF file to audit
        filename: Filename for context
        prefs: Optional preferences (uses defaults if None)
        
    Returns:
        LocalizationAuditResult
    """
    auditor = LocalizationAuditor()
    if prefs:
        auditor.set_preferences(prefs)
    return auditor.audit(iff_reader, filename)


def check_before_save(
    iff_reader,
    filename: str = "",
    prefs: LocalizationPreferences = None
) -> Tuple[bool, LocalizationAuditResult]:
    """
    Check for localization issues before saving.
    
    Returns (should_proceed, audit_result).
    
    If prefs.warn_on_save is False, always returns (True, empty_result).
    If there are errors in STRICT mode, returns (False, result).
    Otherwise returns (True, result) - caller can show warnings.
    """
    if prefs is None:
        prefs = LocalizationPreferences()
    
    if not prefs.warn_on_save:
        return True, LocalizationAuditResult()
    
    result = audit_file(iff_reader, filename, prefs)
    
    if prefs.audit_level == AuditLevel.STRICT and result.error_count > 0:
        return False, result
    
    return True, result
