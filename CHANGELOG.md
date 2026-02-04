# Changelog

All notable changes to SimObliterator Suite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-02-04

### 🎉 Initial Release

First public release of the SimObliterator Suite - a comprehensive toolkit for analyzing, editing, and extracting data from The Sims 1 game files.

### Added

#### Core Features

- **IFF File Parser** - Complete support for IFF container format
- **FAR Archive Support** - FAR1 and FAR3 archive reading/writing
- **DBPF Support** - Package file format support

#### Behavior Analysis

- **BHAV Disassembler** - Full SimAntics bytecode decoding
- **Semantic Name Resolution** - 2,287+ behaviors with readable names
- **Call Graph Builder** - Visualize behavior relationships
- **Execution Tracer** - Path analysis and dead code detection
- **Forensic Analyzer** - Deep pattern analysis

#### Save File Editing

- **Save Manager** - Load and modify save game files
- **Sim Editor** - Modify skills, motives, relationships
- **Household Editor** - Manage family funds and members
- **Career Manager** - 24 career tracks, promotions
- **Relationship Manager** - Daily/lifetime values

#### Visual Tools

- **Sprite Viewer** - SPR2 decoding with zoom levels
- **Animation Decoder** - Frame-by-frame analysis
- **Mesh Exporter** - glTF/GLB 3D model export
- **Sprite Sheet Export** - Combined sprite exports

#### Import/Export

- **PNG Import** - Convert PNG to SPR2 with palette quantization
- **glTF Import** - Import 3D meshes to GMDC format
- **Modern Export** - Export assets to PNG, glTF, JSON
- **Legacy Export** - Export to TS1-compatible formats

#### Safety System

- **Mutation Pipeline** - All writes validated and auditable
- **Backup Manager** - Automatic backups before modifications
- **Preview Mode** - See changes before applying
- **Undo/Redo** - Full mutation history

#### Analysis Tools

- **Unused Asset Detector** - Find orphaned chunks
- **Cross-Reference Search** - Find dependencies
- **Expansion Comparison** - Compare across packs
- **Opcode Database** - 167+ unknown opcodes catalogued

### Technical

- 110 canonical actions - all fully implemented
- DearPyGUI-based modern interface
- Self-contained, no external dependencies at runtime
- Windows 7+ compatible

---

## [Unreleased]

### Planned

- MacOS support
- Linux support
- Plugin system for custom analyzers
- Batch processing improvements
