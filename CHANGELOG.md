# Changelog

All notable changes to SimObliterator Suite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-02-04

### Initial Release

First public release of the SimObliterator Suite - a comprehensive toolkit for analyzing, editing, and extracting data from The Sims 1 game files.

### Core Systems

- **IFF File Parser** - Complete support for IFF container format with chunk-level access
- **FAR Archive Support** - FAR1 and FAR3 archive reading/writing with recursive discovery
- **DBPF Support** - Package file format support for expansion content

### Behavior Analysis

- **BHAV Disassembler** - Full SimAntics bytecode decoding with semantic primitives
- **Primitive Reference** - Operand field definitions for Expression, Gosub, Sleep, Animate
- **Variable Analyzer** - Track locals, temps, params across BHAV instructions
- **Call Graph Builder** - Visualize behavior relationships and dependencies
- **Execution Tracer** - Path analysis and dead code detection

### String Table Support

- **STR# Parser** - Full format support (0xFFFF, 0xFDFF, 0xFEFF, Pascal)
- **Language Awareness** - 20 language codes with proper slot handling
- **Reference Scanner** - Find all STR# usage from OBJD, TTAB, CTSS
- **Localization Audit** - Detect missing translations with fix utilities

### SLOT Resource Support

- **SLOT Parser** - Complete routing slot parsing (versions 2-4)
- **SLOT Editor** - Add, remove, duplicate slots programmatically
- **XML Export/Import** - Transmogrifier-compatible XML workflow
- **Binary Serialization** - Round-trip binary encoding

### TTAB Interaction Support

- **Full Field Parsing** - All versions 4-10 with autonomy and motive effects
- **Multi-Object Context** - Map resources to objects in multi-OBJD files
- **Flags Decoding** - Complete interaction flag interpretation

### Lot Analysis

- **Terrain Detection** - House number to terrain type mapping (from FreeSO)
- **Ambience System** - 35 ambient sound definitions with GUIDs
- **ARRY Chunk Analysis** - Floor, wall, object placement arrays

### Save File Editing

- **Save Manager** - Load and modify save game files
- **Sim Editor** - Modify skills, motives, relationships
- **Household Editor** - Manage family funds and members
- **Career Manager** - 24 career tracks, promotions

### ID Conflict Detection

- **GUID Scanner** - Detect duplicate GUIDs across files
- **BHAV ID Overlap** - Warn on local BHAV ID conflicts
- **Semi-Global Conflicts** - Detect group ID issues
- **Range Finder** - Find unused ID ranges

### Safety System

- **Mutation Pipeline** - All writes validated and auditable
- **Backup Manager** - Automatic backups before modifications
- **Preview Mode** - See changes before applying

### Test Coverage

- 73 tests across 17 categories
- Real game file validation
- Round-trip encoding verification

---

## [Unreleased]

### Planned

- MacOS support
- Linux support
- Plugin system for custom analyzers
- Batch processing improvements
