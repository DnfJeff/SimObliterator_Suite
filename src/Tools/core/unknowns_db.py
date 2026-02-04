"""
Unknowns Database

Persistent JSON storage for discovered unknowns during game analysis.
Stores unknown opcodes, chunks, and patterns for later study.

Features:
- Append-only with automatic deduplication
- Tracks source file and context for each unknown
- Timestamps all discoveries
- Thread-safe file operations

Usage:
    from core.unknowns_db import UnknownsDatabase
    
    db = UnknownsDatabase()
    db.add_unknown_opcode(0x157, source_file="trash.iff", context={"bhav_id": 4096})
    db.save()
"""

import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Path to JSON database
_DATA_DIR = Path(__file__).parent.parent / "data"
_UNKNOWNS_JSON = _DATA_DIR / "unknowns_db.json"


class UnknownsDatabase:
    """Manages persistent storage of discovered unknowns."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - one database instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._data = None
        self._dirty = False
        self._load()
        self._initialized = True
    
    def _load(self):
        """Load database from JSON file."""
        try:
            if _UNKNOWNS_JSON.exists():
                with open(_UNKNOWNS_JSON, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            else:
                self._data = self._create_empty_db()
        except Exception as e:
            print(f"Warning: Could not load unknowns_db.json: {e}")
            self._data = self._create_empty_db()
    
    def _create_empty_db(self) -> Dict:
        """Create empty database structure."""
        return {
            "_meta": {
                "version": "1.0.0",
                "description": "Database of discovered unknowns from game analysis",
                "created": datetime.now().isoformat(),
                "last_scan": None,
                "total_entries": 0
            },
            "unknown_opcodes": {},
            "unknown_chunks": {},
            "unknown_patterns": {},
            "scan_history": []
        }
    
    def save(self):
        """Save database to JSON file."""
        if not self._dirty:
            return
        
        with self._lock:
            try:
                # Update meta
                self._data["_meta"]["total_entries"] = (
                    len(self._data["unknown_opcodes"]) +
                    len(self._data["unknown_chunks"]) +
                    len(self._data["unknown_patterns"])
                )
                
                # Ensure data dir exists
                _DATA_DIR.mkdir(parents=True, exist_ok=True)
                
                with open(_UNKNOWNS_JSON, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False)
                
                self._dirty = False
            except Exception as e:
                print(f"Error saving unknowns database: {e}")
    
    def add_unknown_opcode(
        self,
        opcode: int,
        source_file: str,
        context: Optional[Dict[str, Any]] = None,
        notes: str = ""
    ) -> bool:
        """
        Add an unknown opcode to the database.
        
        Args:
            opcode: The opcode value (0-65535)
            source_file: IFF file where discovered
            context: Additional context (bhav_id, instruction_index, etc.)
            notes: Human notes about this opcode
        
        Returns:
            True if new entry, False if duplicate (source added)
        """
        hex_key = f"0x{opcode:04X}"
        timestamp = datetime.now().isoformat()
        
        with self._lock:
            if hex_key not in self._data["unknown_opcodes"]:
                # New opcode
                self._data["unknown_opcodes"][hex_key] = {
                    "opcode": opcode,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "occurrence_count": 1,
                    "sources": [{
                        "file": source_file,
                        "timestamp": timestamp,
                        "context": context or {}
                    }],
                    "notes": notes,
                    "inferred_purpose": "",
                    "confidence": "UNANALYZED"
                }
                self._dirty = True
                return True
            else:
                # Existing opcode - add source if new
                entry = self._data["unknown_opcodes"][hex_key]
                entry["last_seen"] = timestamp
                entry["occurrence_count"] += 1
                
                # Check if this source file already recorded
                existing_files = {s["file"] for s in entry["sources"]}
                if source_file not in existing_files:
                    entry["sources"].append({
                        "file": source_file,
                        "timestamp": timestamp,
                        "context": context or {}
                    })
                    self._dirty = True
                
                return False
    
    def add_unknown_chunk(
        self,
        chunk_type: str,
        source_file: str,
        context: Optional[Dict[str, Any]] = None,
        notes: str = ""
    ) -> bool:
        """
        Add an unknown chunk type to the database.
        
        Args:
            chunk_type: The 4-character chunk type
            source_file: IFF file where discovered
            context: Additional context (chunk_id, size, etc.)
            notes: Human notes
        
        Returns:
            True if new entry, False if duplicate
        """
        timestamp = datetime.now().isoformat()
        
        with self._lock:
            if chunk_type not in self._data["unknown_chunks"]:
                self._data["unknown_chunks"][chunk_type] = {
                    "chunk_type": chunk_type,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "occurrence_count": 1,
                    "sources": [{
                        "file": source_file,
                        "timestamp": timestamp,
                        "context": context or {}
                    }],
                    "notes": notes,
                    "inferred_purpose": ""
                }
                self._dirty = True
                return True
            else:
                entry = self._data["unknown_chunks"][chunk_type]
                entry["last_seen"] = timestamp
                entry["occurrence_count"] += 1
                
                existing_files = {s["file"] for s in entry["sources"]}
                if source_file not in existing_files:
                    entry["sources"].append({
                        "file": source_file,
                        "timestamp": timestamp,
                        "context": context or {}
                    })
                    self._dirty = True
                
                return False
    
    def add_unknown_pattern(
        self,
        pattern_id: str,
        description: str,
        source_file: str,
        evidence: Dict[str, Any]
    ) -> bool:
        """
        Add an unknown pattern (behavioral, structural) to database.
        
        Args:
            pattern_id: Unique identifier for this pattern
            description: What makes this pattern unusual
            source_file: Where discovered
            evidence: Data supporting this pattern
        
        Returns:
            True if new, False if duplicate
        """
        timestamp = datetime.now().isoformat()
        
        with self._lock:
            if pattern_id not in self._data["unknown_patterns"]:
                self._data["unknown_patterns"][pattern_id] = {
                    "pattern_id": pattern_id,
                    "description": description,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "occurrence_count": 1,
                    "sources": [{
                        "file": source_file,
                        "timestamp": timestamp,
                        "evidence": evidence
                    }],
                    "analysis_notes": ""
                }
                self._dirty = True
                return True
            else:
                entry = self._data["unknown_patterns"][pattern_id]
                entry["last_seen"] = timestamp
                entry["occurrence_count"] += 1
                
                existing_files = {s["file"] for s in entry["sources"]}
                if source_file not in existing_files:
                    entry["sources"].append({
                        "file": source_file,
                        "timestamp": timestamp,
                        "evidence": evidence
                    })
                    self._dirty = True
                
                return False
    
    def record_scan(self, scan_type: str, directory: str, file_count: int, findings: Dict):
        """Record a scan in history."""
        with self._lock:
            self._data["scan_history"].append({
                "timestamp": datetime.now().isoformat(),
                "scan_type": scan_type,
                "directory": directory,
                "files_scanned": file_count,
                "new_unknowns_found": findings.get("new_count", 0),
                "summary": findings.get("summary", "")
            })
            self._data["_meta"]["last_scan"] = datetime.now().isoformat()
            self._dirty = True
    
    def has_unknown_opcode(self, opcode: int) -> bool:
        """Check if opcode is in unknowns database."""
        hex_key = f"0x{opcode:04X}"
        return hex_key in self._data["unknown_opcodes"]
    
    def has_unknown_chunk(self, chunk_type: str) -> bool:
        """Check if chunk type is in unknowns database."""
        return chunk_type in self._data["unknown_chunks"]
    
    def get_unknown_opcodes(self) -> Dict:
        """Get all unknown opcodes."""
        return self._data["unknown_opcodes"].copy()
    
    def get_unknown_chunks(self) -> Dict:
        """Get all unknown chunk types."""
        return self._data["unknown_chunks"].copy()
    
    def get_unknown_patterns(self) -> Dict:
        """Get all unknown patterns."""
        return self._data["unknown_patterns"].copy()
    
    def get_scan_history(self) -> List[Dict]:
        """Get scan history."""
        return self._data["scan_history"].copy()
    
    def get_statistics(self) -> Dict:
        """Get database statistics."""
        return {
            "unknown_opcodes_count": len(self._data["unknown_opcodes"]),
            "unknown_chunks_count": len(self._data["unknown_chunks"]),
            "unknown_patterns_count": len(self._data["unknown_patterns"]),
            "total_scans": len(self._data["scan_history"]),
            "last_scan": self._data["_meta"].get("last_scan"),
            "created": self._data["_meta"].get("created")
        }
    
    def update_opcode_analysis(self, opcode: int, purpose: str, confidence: str, notes: str = ""):
        """Update analysis for an unknown opcode."""
        hex_key = f"0x{opcode:04X}"
        
        with self._lock:
            if hex_key in self._data["unknown_opcodes"]:
                entry = self._data["unknown_opcodes"][hex_key]
                entry["inferred_purpose"] = purpose
                entry["confidence"] = confidence
                if notes:
                    entry["notes"] = notes
                self._dirty = True
    
    def export_report(self) -> str:
        """Generate human-readable report of unknowns."""
        lines = []
        lines.append("=" * 80)
        lines.append("UNKNOWNS DATABASE REPORT")
        lines.append("=" * 80)
        
        stats = self.get_statistics()
        lines.append(f"\nDatabase Statistics:")
        lines.append(f"  Unknown Opcodes: {stats['unknown_opcodes_count']}")
        lines.append(f"  Unknown Chunks:  {stats['unknown_chunks_count']}")
        lines.append(f"  Unknown Patterns: {stats['unknown_patterns_count']}")
        lines.append(f"  Total Scans: {stats['total_scans']}")
        lines.append(f"  Last Scan: {stats['last_scan'] or 'Never'}")
        
        if self._data["unknown_opcodes"]:
            lines.append("\n" + "-" * 40)
            lines.append("UNKNOWN OPCODES")
            lines.append("-" * 40)
            for hex_key, entry in sorted(self._data["unknown_opcodes"].items()):
                lines.append(f"\n  {hex_key}:")
                lines.append(f"    Occurrences: {entry['occurrence_count']}")
                lines.append(f"    Sources: {len(entry['sources'])} files")
                if entry.get('inferred_purpose'):
                    lines.append(f"    Purpose: {entry['inferred_purpose']} ({entry.get('confidence', '?')})")
                if entry.get('notes'):
                    lines.append(f"    Notes: {entry['notes']}")
        
        if self._data["unknown_chunks"]:
            lines.append("\n" + "-" * 40)
            lines.append("UNKNOWN CHUNK TYPES")
            lines.append("-" * 40)
            for chunk_type, entry in sorted(self._data["unknown_chunks"].items()):
                lines.append(f"\n  {chunk_type}:")
                lines.append(f"    Occurrences: {entry['occurrence_count']}")
                lines.append(f"    Sources: {len(entry['sources'])} files")
        
        return "\n".join(lines)


# Convenience function for quick access
def get_unknowns_db() -> UnknownsDatabase:
    """Get the singleton UnknownsDatabase instance."""
    return UnknownsDatabase()
