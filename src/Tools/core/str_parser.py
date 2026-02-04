"""
STR# Parser — Full Sims 1 string table parser with language awareness.

Handles all STR# formats:
- Format 0xFFFF: Null-terminated strings
- Format 0xFDFF: Language-coded pairs (language byte + string + comment)
- Format 0xFEFF: Paired null-terminated (string + comment)
- Format 0 (Pascal): Length-prefixed strings

Language codes follow Maxis conventions:
    0: US English
    1: UK English  
    2: French
    3: German
    4: Italian
    5: Spanish
    6: Dutch
    7: Danish
    8: Swedish
    9: Norwegian
    10: Finnish
    11: Hebrew
    12: Russian
    13: Portuguese
    14: Japanese
    15: Polish
    16: Chinese (Traditional)
    17: Chinese (Simplified)
    18: Thai
    19: Korean
"""

import struct
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import IntEnum


class LanguageCode(IntEnum):
    """Sims 1 language codes."""
    US_ENGLISH = 0
    UK_ENGLISH = 1
    FRENCH = 2
    GERMAN = 3
    ITALIAN = 4
    SPANISH = 5
    DUTCH = 6
    DANISH = 7
    SWEDISH = 8
    NORWEGIAN = 9
    FINNISH = 10
    HEBREW = 11
    RUSSIAN = 12
    PORTUGUESE = 13
    JAPANESE = 14
    POLISH = 15
    CHINESE_TRADITIONAL = 16
    CHINESE_SIMPLIFIED = 17
    THAI = 18
    KOREAN = 19
    
    @classmethod
    def get_name(cls, code: int) -> str:
        """Get human-readable name for language code."""
        names = {
            0: "US English",
            1: "UK English",
            2: "French",
            3: "German",
            4: "Italian",
            5: "Spanish",
            6: "Dutch",
            7: "Danish",
            8: "Swedish",
            9: "Norwegian",
            10: "Finnish",
            11: "Hebrew",
            12: "Russian",
            13: "Portuguese",
            14: "Japanese",
            15: "Polish",
            16: "Chinese (Traditional)",
            17: "Chinese (Simplified)",
            18: "Thai",
            19: "Korean",
        }
        return names.get(code, f"Unknown ({code})")


@dataclass
class LanguageSlot:
    """A single language entry in a string table."""
    language_code: int
    value: str
    comment: str = ""
    
    @property
    def language_name(self) -> str:
        return LanguageCode.get_name(self.language_code)
    
    def is_empty(self) -> bool:
        return not self.value or self.value.strip() == ""


@dataclass 
class StringEntry:
    """
    A single string entry that may have multiple language translations.
    
    In most Sims 1 files, strings only have one language (usually US English).
    Multi-language files store all translations for each string index.
    """
    index: int
    slots: Dict[int, LanguageSlot] = field(default_factory=dict)
    
    def get_value(self, language: int = 0) -> str:
        """Get string value for a language, falls back to US English."""
        if language in self.slots:
            return self.slots[language].value
        if 0 in self.slots:
            return self.slots[0].value
        # Return first available
        if self.slots:
            return next(iter(self.slots.values())).value
        return ""
    
    def get_comment(self, language: int = 0) -> str:
        """Get comment for a language."""
        if language in self.slots:
            return self.slots[language].comment
        if 0 in self.slots:
            return self.slots[0].comment
        return ""
    
    def get_populated_languages(self) -> List[int]:
        """Get list of language codes that have non-empty values."""
        return [code for code, slot in self.slots.items() if not slot.is_empty()]
    
    def get_missing_languages(self, required: List[int] = None) -> List[int]:
        """Get language codes that are missing or empty."""
        if required is None:
            required = [0]  # Default: only US English required
        populated = set(self.get_populated_languages())
        return [code for code in required if code not in populated]


@dataclass
class ParsedSTR:
    """
    Complete parsed STR# chunk.
    
    Attributes:
        chunk_id: The STR# chunk ID
        format_code: Original format code from file
        entries: List of string entries, indexed by position
        parse_errors: Any errors encountered during parsing
    """
    chunk_id: int
    format_code: int
    entries: List[StringEntry] = field(default_factory=list)
    parse_errors: List[str] = field(default_factory=list)
    
    def get_string(self, index: int, language: int = 0) -> str:
        """Get string value at index for language."""
        if 0 <= index < len(self.entries):
            return self.entries[index].get_value(language)
        return ""
    
    def get_all_strings(self, language: int = 0) -> List[str]:
        """Get all strings for a language as simple list."""
        return [entry.get_value(language) for entry in self.entries]
    
    def get_localization_summary(self) -> Dict:
        """
        Get summary of language population for all entries.
        
        Returns dict with:
            - total_entries: count
            - languages_used: set of all language codes found
            - entries_missing_translations: list of indices with gaps
        """
        languages_used = set()
        entries_missing = []
        
        for entry in self.entries:
            populated = entry.get_populated_languages()
            languages_used.update(populated)
            
            # Check if US English exists but other slots are empty
            if 0 in entry.slots and len(populated) == 1:
                # Only US English populated
                entries_missing.append(entry.index)
        
        return {
            "total_entries": len(self.entries),
            "languages_used": sorted(languages_used),
            "entries_with_single_language": len(entries_missing),
            "entry_indices_single_language": entries_missing[:20],  # First 20
        }


class STRParser:
    """
    Parser for STR# (string table) chunks.
    
    Handles all known Sims 1 string formats and extracts
    full language information when available.
    """
    
    FORMAT_NULL_TERMINATED = 0xFFFF
    FORMAT_LANGUAGE_CODED = 0xFDFF
    FORMAT_PAIRED_NULL = 0xFEFF
    
    @classmethod
    def parse(cls, data: bytes, chunk_id: int = 0) -> ParsedSTR:
        """
        Parse STR# chunk data into structured form.
        
        Args:
            data: Raw chunk data (excluding IFF chunk header)
            chunk_id: Optional chunk ID for context
            
        Returns:
            ParsedSTR with entries and any parse errors
        """
        result = ParsedSTR(chunk_id=chunk_id, format_code=0)
        
        if len(data) < 4:
            result.parse_errors.append("Data too short for STR# header")
            return result
        
        # Read format code (big-endian first 2 bytes)
        fmt = struct.unpack('>H', data[0:2])[0]
        result.format_code = fmt
        
        try:
            if fmt == cls.FORMAT_NULL_TERMINATED:
                cls._parse_null_terminated(data, result)
            elif fmt == cls.FORMAT_LANGUAGE_CODED:
                cls._parse_language_coded(data, result)
            elif fmt == cls.FORMAT_PAIRED_NULL:
                cls._parse_paired_null(data, result)
            elif fmt < 256:
                # Format 0 - Pascal strings (count in first byte)
                cls._parse_pascal(data, result)
            else:
                # Unknown format - try null-terminated fallback
                cls._parse_fallback(data, result)
                
        except Exception as e:
            result.parse_errors.append(f"Parse exception: {e}")
        
        return result
    
    @classmethod
    def _parse_null_terminated(cls, data: bytes, result: ParsedSTR):
        """Parse format 0xFFFF: null-terminated strings."""
        count = struct.unpack('<H', data[2:4])[0]
        offset = 4
        
        for idx in range(count):
            end = data.find(b'\x00', offset)
            if end == -1:
                result.parse_errors.append(f"Missing null terminator at index {idx}")
                break
                
            value = data[offset:end].decode('latin-1', errors='replace')
            
            entry = StringEntry(index=idx)
            entry.slots[0] = LanguageSlot(
                language_code=0,
                value=value,
                comment=""
            )
            result.entries.append(entry)
            
            offset = end + 1
    
    @classmethod
    def _parse_language_coded(cls, data: bytes, result: ParsedSTR):
        """
        Parse format 0xFDFF: language-coded pairs.
        
        Each entry has:
        - 1 byte: language code
        - null-terminated string value
        - null-terminated comment
        
        Multiple entries with the same language code at different positions
        represent different string indices. Same index, different languages
        appear consecutively.
        """
        count = struct.unpack('<H', data[2:4])[0]
        offset = 4
        
        # Build entries - language coded format groups by string index
        current_index = 0
        current_entry = StringEntry(index=0)
        
        for _ in range(count):
            if offset >= len(data):
                break
                
            # Read language code
            lang_code = data[offset]
            offset += 1
            
            # Read string value
            end = data.find(b'\x00', offset)
            if end == -1:
                break
            value = data[offset:end].decode('latin-1', errors='replace')
            offset = end + 1
            
            # Read comment
            end2 = data.find(b'\x00', offset)
            comment = ""
            if end2 != -1:
                comment = data[offset:end2].decode('latin-1', errors='replace')
                offset = end2 + 1
            
            # Check if this is a new string index or same index, different language
            # Language coded format: if we see language 0 again, it's a new string
            if lang_code == 0 and current_entry.slots:
                # Start new entry
                result.entries.append(current_entry)
                current_index += 1
                current_entry = StringEntry(index=current_index)
            
            current_entry.slots[lang_code] = LanguageSlot(
                language_code=lang_code,
                value=value,
                comment=comment
            )
        
        # Don't forget last entry
        if current_entry.slots:
            result.entries.append(current_entry)
    
    @classmethod
    def _parse_paired_null(cls, data: bytes, result: ParsedSTR):
        """
        Parse format 0xFEFF: paired null-terminated.
        
        Each entry has:
        - null-terminated string value
        - null-terminated comment
        """
        count = struct.unpack('<H', data[2:4])[0]
        offset = 4
        
        for idx in range(count):
            # Read string value
            end = data.find(b'\x00', offset)
            if end == -1:
                break
            value = data[offset:end].decode('latin-1', errors='replace')
            offset = end + 1
            
            # Read comment
            end2 = data.find(b'\x00', offset)
            comment = ""
            if end2 != -1:
                comment = data[offset:end2].decode('latin-1', errors='replace')
                offset = end2 + 1
            
            entry = StringEntry(index=idx)
            entry.slots[0] = LanguageSlot(
                language_code=0,
                value=value,
                comment=comment
            )
            result.entries.append(entry)
    
    @classmethod
    def _parse_pascal(cls, data: bytes, result: ParsedSTR):
        """
        Parse format 0 (Pascal): length-prefixed strings.
        
        First byte is count, then each string is:
        - 1 byte: length
        - N bytes: string data
        """
        count = data[0]  # Format byte is the count
        offset = 2  # Skip format word
        
        for idx in range(count):
            if offset >= len(data):
                break
                
            slen = data[offset]
            offset += 1
            
            if offset + slen > len(data):
                result.parse_errors.append(f"String {idx} extends past data")
                break
                
            value = data[offset:offset + slen].decode('latin-1', errors='replace')
            offset += slen
            
            entry = StringEntry(index=idx)
            entry.slots[0] = LanguageSlot(
                language_code=0,
                value=value,
                comment=""
            )
            result.entries.append(entry)
    
    @classmethod
    def _parse_fallback(cls, data: bytes, result: ParsedSTR):
        """Fallback: try null-terminated from start."""
        result.parse_errors.append(f"Unknown format 0x{result.format_code:04X}, using fallback")
        
        offset = 0
        idx = 0
        
        while offset < len(data):
            end = data.find(b'\x00', offset)
            if end == -1 or end == offset:
                break
                
            value = data[offset:end].decode('latin-1', errors='replace')
            
            entry = StringEntry(index=idx)
            entry.slots[0] = LanguageSlot(
                language_code=0,
                value=value,
                comment=""
            )
            result.entries.append(entry)
            
            offset = end + 1
            idx += 1


class STRSerializer:
    """
    Serializer for STR# chunks.
    
    Writes ParsedSTR back to binary format.
    """
    
    @classmethod
    def serialize(cls, parsed: ParsedSTR, format_code: int = None) -> bytes:
        """
        Serialize ParsedSTR back to binary.
        
        Args:
            parsed: The parsed string table
            format_code: Override format (defaults to original)
            
        Returns:
            Binary STR# chunk data
        """
        if format_code is None:
            format_code = parsed.format_code
        
        if format_code == STRParser.FORMAT_NULL_TERMINATED:
            return cls._serialize_null_terminated(parsed)
        elif format_code == STRParser.FORMAT_LANGUAGE_CODED:
            return cls._serialize_language_coded(parsed)
        elif format_code == STRParser.FORMAT_PAIRED_NULL:
            return cls._serialize_paired_null(parsed)
        else:
            # Default to null-terminated for unknown
            return cls._serialize_null_terminated(parsed)
    
    @classmethod
    def _serialize_null_terminated(cls, parsed: ParsedSTR) -> bytes:
        """Serialize to format 0xFFFF."""
        parts = []
        
        # Header
        parts.append(struct.pack('>H', 0xFFFF))  # Format
        parts.append(struct.pack('<H', len(parsed.entries)))  # Count
        
        # Strings (US English only for this format)
        for entry in parsed.entries:
            value = entry.get_value(0)
            parts.append(value.encode('latin-1', errors='replace'))
            parts.append(b'\x00')
        
        return b''.join(parts)
    
    @classmethod
    def _serialize_language_coded(cls, parsed: ParsedSTR) -> bytes:
        """Serialize to format 0xFDFF."""
        parts = []
        
        # Count total language slots
        total_slots = sum(len(entry.slots) for entry in parsed.entries)
        
        # Header
        parts.append(struct.pack('>H', 0xFDFF))  # Format
        parts.append(struct.pack('<H', total_slots))  # Count
        
        # Entries (all languages for each string)
        for entry in parsed.entries:
            # Sort by language code, US English (0) first
            for lang_code in sorted(entry.slots.keys()):
                slot = entry.slots[lang_code]
                parts.append(bytes([lang_code]))
                parts.append(slot.value.encode('latin-1', errors='replace'))
                parts.append(b'\x00')
                parts.append(slot.comment.encode('latin-1', errors='replace'))
                parts.append(b'\x00')
        
        return b''.join(parts)
    
    @classmethod
    def _serialize_paired_null(cls, parsed: ParsedSTR) -> bytes:
        """Serialize to format 0xFEFF."""
        parts = []
        
        # Header
        parts.append(struct.pack('>H', 0xFEFF))  # Format
        parts.append(struct.pack('<H', len(parsed.entries)))  # Count
        
        # Strings with comments (US English only for this format)
        for entry in parsed.entries:
            value = entry.get_value(0)
            comment = entry.get_comment(0)
            parts.append(value.encode('latin-1', errors='replace'))
            parts.append(b'\x00')
            parts.append(comment.encode('latin-1', errors='replace'))
            parts.append(b'\x00')
        
        return b''.join(parts)


def copy_language_to_missing(
    parsed: ParsedSTR,
    source_language: int = 0,
    target_languages: List[int] = None
) -> Tuple[ParsedSTR, int]:
    """
    Copy strings from source language to missing target language slots.
    
    Args:
        parsed: The string table to modify
        source_language: Language code to copy from (default: US English)
        target_languages: Languages to populate (default: all known)
        
    Returns:
        Tuple of (modified ParsedSTR, count of slots filled)
    """
    if target_languages is None:
        # All known languages except source
        target_languages = [i for i in range(20) if i != source_language]
    
    filled_count = 0
    
    for entry in parsed.entries:
        if source_language not in entry.slots:
            continue
            
        source_slot = entry.slots[source_language]
        if source_slot.is_empty():
            continue
        
        for target_lang in target_languages:
            if target_lang not in entry.slots or entry.slots[target_lang].is_empty():
                # Copy source to target
                entry.slots[target_lang] = LanguageSlot(
                    language_code=target_lang,
                    value=source_slot.value,
                    comment=source_slot.comment
                )
                filled_count += 1
    
    return parsed, filled_count


# Convenience function for simple parsing (backwards compatible)
def parse_str_simple(data: bytes) -> List[str]:
    """
    Parse STR# data and return simple list of US English strings.
    
    This is the backwards-compatible interface matching the original
    STRParser.parse() return type.
    """
    parsed = STRParser.parse(data)
    return parsed.get_all_strings(language=0)
