"""
STR Chunk - String Tables
Port of FreeSO's tso.files/Formats/IFF/Chunks/STR.cs
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


class STRLangCode(IntEnum):
    """Language codes for string tables."""
    DEFAULT = 0
    ENGLISH_US = 1
    ENGLISH_UK = 2
    FRENCH = 3
    GERMAN = 4
    ITALIAN = 5
    SPANISH = 6
    DUTCH = 7
    DANISH = 8
    SWEDISH = 9
    NORWEGIAN = 10
    FINNISH = 11
    HEBREW = 12
    RUSSIAN = 13
    PORTUGUESE = 14
    JAPANESE = 15
    POLISH = 16
    SIMPLIFIED_CHINESE = 17
    TRADITIONAL_CHINESE = 18
    THAI = 19
    KOREAN = 20
    SLOVAK = 21


LANGUAGE_NAMES = [
    "English (US)", "English (UK)", "French", "German", "Italian",
    "Spanish", "Dutch", "Danish", "Swedish", "Norwegian", "Finnish",
    "Hebrew", "Russian", "Portuguese", "Japanese", "Polish",
    "Simplified Chinese", "Traditional Chinese", "Thai", "Korean", "Slovak"
]


@dataclass
class STRItem:
    """A single string entry."""
    value: str = ""
    comment: str = ""
    language_code: int = 1


@dataclass
class STRLanguageSet:
    """Strings for one language."""
    strings: list[STRItem] = field(default_factory=list)


@register_chunk("STR#")
@dataclass
class STR(IffChunk):
    """
    String table chunk. Holds text strings with optional multi-language support.
    Maps to: FSO.Files.Formats.IFF.Chunks.STR
    """
    language_sets: list[STRLanguageSet] = field(default_factory=lambda: [STRLanguageSet() for _ in range(20)])
    default_lang_code: STRLangCode = STRLangCode.ENGLISH_US
    format_code: int = -2  # Track original format for round-trip
    
    def __post_init__(self):
        if not self.language_sets:
            self.language_sets = [STRLanguageSet() for _ in range(20)]
    
    @property
    def length(self) -> int:
        """Number of strings in primary language."""
        if self.language_sets and self.language_sets[0].strings:
            return len(self.language_sets[0].strings)
        return 0
    
    @property
    def strings(self) -> list[str]:
        """Get all strings from primary language set as simple string list."""
        if self.language_sets and self.language_sets[0].strings:
            return [item.value for item in self.language_sets[0].strings]
        return []
    
    def get_language_set(self, lang: STRLangCode = STRLangCode.DEFAULT) -> STRLanguageSet:
        """Get strings for a language, falling back to English US."""
        if lang == STRLangCode.DEFAULT:
            lang = self.default_lang_code
        
        idx = int(lang) - 1
        if idx < 0 or idx >= len(self.language_sets):
            return self.language_sets[0]
        
        lang_set = self.language_sets[idx]
        if not lang_set.strings:
            return self.language_sets[0]  # Fallback
        return lang_set
    
    def get_string(self, index: int, lang: STRLangCode = STRLangCode.DEFAULT) -> Optional[str]:
        """Get a string by index."""
        entry = self.get_string_entry(index, lang)
        return entry.value if entry else None
    
    def get_comment(self, index: int, lang: STRLangCode = STRLangCode.DEFAULT) -> Optional[str]:
        """Get a string's comment by index."""
        entry = self.get_string_entry(index, lang)
        return entry.comment if entry else None
    
    def get_string_entry(self, index: int, lang: STRLangCode = STRLangCode.DEFAULT) -> Optional[STRItem]:
        """Get a STRItem by index."""
        lang_set = self.get_language_set(lang)
        if 0 <= index < len(lang_set.strings):
            return lang_set.strings[index]
        return None
    
    def set_string(self, index: int, value: str, lang: STRLangCode = STRLangCode.DEFAULT):
        """Set a string value."""
        lang_set = self.get_language_set(lang)
        if 0 <= index < len(lang_set.strings):
            lang_set.strings[index].value = value
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read STR chunk from stream."""
        self.language_sets = [STRLanguageSet() for _ in range(20)]
        
        self.format_code = io.read_int16()
        
        if not io.has_more:
            return
        
        # Format 0: Pascal strings, single language
        if self.format_code == 0:
            num_strings = io.read_uint16()
            strings = []
            for _ in range(num_strings):
                strings.append(STRItem(value=io.read_pascal_string()))
            self.language_sets[0].strings = strings
        
        # Format -1 (0xFFFF): C strings, single language
        elif self.format_code == -1:
            num_strings = io.read_uint16()
            strings = []
            for _ in range(num_strings):
                strings.append(STRItem(value=io.read_null_terminated_string()))
            self.language_sets[0].strings = strings
        
        # Format -2 (0xFFFE): String pairs (value + comment)
        elif self.format_code == -2:
            num_strings = io.read_uint16()
            strings = []
            for _ in range(num_strings):
                value = io.read_null_terminated_string()
                comment = io.read_null_terminated_string()
                strings.append(STRItem(value=value, comment=comment))
            self.language_sets[0].strings = strings
        
        # Format -3 (0xFFFD): Multi-language with string pairs
        elif self.format_code == -3:
            num_strings = io.read_uint16()
            for _ in range(num_strings):
                lang_code = io.read_byte()
                value = io.read_null_terminated_string()
                comment = io.read_null_terminated_string()
                
                if 0 < lang_code <= 20:
                    self.language_sets[lang_code - 1].strings.append(
                        STRItem(value=value, comment=comment, language_code=lang_code)
                    )
        
        # Format -4 (0xFFFC): Multi-language, length-prefixed
        elif self.format_code == -4:
            num_language_sets = io.read_byte()
            for _ in range(num_language_sets):
                num_strings = io.read_uint16()
                for _ in range(num_strings):
                    lang_code = io.read_byte()
                    value = self._read_length_prefixed_string(io)
                    comment = self._read_length_prefixed_string(io)
                    
                    if 0 < lang_code <= 20:
                        self.language_sets[lang_code - 1].strings.append(
                            STRItem(value=value, comment=comment, language_code=lang_code)
                        )
    
    def _read_length_prefixed_string(self, io: 'IoBuffer') -> str:
        """Read a string with 2-byte length prefix."""
        length = io.read_uint16()
        if length == 0:
            return ""
        data = io.read_bytes(length)
        return data.decode('utf-8', errors='replace').rstrip('\x00')
    
    def _write_length_prefixed_string(self, io: 'IoWriter', s: str):
        """Write a string with 2-byte length prefix."""
        data = s.encode('utf-8', errors='replace')
        io.write_uint16(len(data))
        if data:
            io.write_bytes(data)
    
    def write(self, iff: 'IffFile', io: 'IoWriter') -> bool:
        """Write STR chunk to stream."""
        io.write_int16(self.format_code)
        
        # Format 0: Pascal strings, single language
        if self.format_code == 0:
            strings = self.language_sets[0].strings if self.language_sets else []
            io.write_uint16(len(strings))
            for item in strings:
                io.write_pascal_string(item.value)
        
        # Format -1 (0xFFFF): C strings, single language
        elif self.format_code == -1:
            strings = self.language_sets[0].strings if self.language_sets else []
            io.write_uint16(len(strings))
            for item in strings:
                io.write_null_terminated_string(item.value)
        
        # Format -2 (0xFFFE): String pairs (value + comment)
        elif self.format_code == -2:
            strings = self.language_sets[0].strings if self.language_sets else []
            io.write_uint16(len(strings))
            for item in strings:
                io.write_null_terminated_string(item.value)
                io.write_null_terminated_string(item.comment)
        
        # Format -3 (0xFFFD): Multi-language with string pairs
        elif self.format_code == -3:
            # Count total strings across all languages
            total = sum(len(ls.strings) for ls in self.language_sets)
            io.write_uint16(total)
            for lang_idx, lang_set in enumerate(self.language_sets):
                lang_code = lang_idx + 1
                for item in lang_set.strings:
                    io.write_byte(lang_code)
                    io.write_null_terminated_string(item.value)
                    io.write_null_terminated_string(item.comment)
        
        # Format -4 (0xFFFC): Multi-language, length-prefixed
        elif self.format_code == -4:
            # Count non-empty language sets
            non_empty = [ls for ls in self.language_sets if ls.strings]
            io.write_byte(len(non_empty))
            for lang_idx, lang_set in enumerate(self.language_sets):
                if not lang_set.strings:
                    continue
                lang_code = lang_idx + 1
                io.write_uint16(len(lang_set.strings))
                for item in lang_set.strings:
                    io.write_byte(lang_code)
                    self._write_length_prefixed_string(io, item.value)
                    self._write_length_prefixed_string(io, item.comment)
        
        return True
    
    def __len__(self) -> int:
        return self.length
    
    def __getitem__(self, index: int) -> Optional[str]:
        return self.get_string(index)


# Also register CTSS (Catalog Strings) - same format
@register_chunk("CTSS")
class CTSS(STR):
    """Catalog strings chunk - same format as STR."""
    pass
