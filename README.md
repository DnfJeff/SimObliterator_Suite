# SimObliterator Suite

<p align="center">
  <img src="assets/splash.png" alt="SimObliterator Suite" width="400">
</p>

<p align="center">
  <strong>Professional IFF Editor & Analyzer for The Sims 1</strong><br>
  <em>Analyze • Edit • Extract • Research</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.3-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows-green.svg" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.9+-yellow.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-purple.svg" alt="License">
</p>

---

## 🎯 Overview

SimObliterator Suite is a comprehensive desktop application for working with The Sims 1 game files. Whether you're a modder, researcher, or just curious about how the game works, this toolkit provides everything you need.

### Key Features

| Category              | Capabilities                                                  |
| --------------------- | ------------------------------------------------------------- |
| **File Formats**      | IFF, FAR1, FAR3, DBPF with 38 chunk type parsers              |
| **Behavior Analysis** | BHAV disassembly, call graphs, execution tracing, authoring   |
| **Object Editing**    | SLOT routing, TTAB autonomy, multi-object IFF support         |
| **Save Editing**      | Money, skills, motives, personality, careers, relationships   |
| **Visual Assets**     | Sprite export (PNG), mesh export (glTF/GLB), animation frames |
| **Localization**      | 20-language STR# support, translation audit, batch copy       |
| **Safety**            | Transaction pipeline, snapshots, rollback, validation, audit  |
| **Research**          | Unknowns database, opcode documentation, execution model      |

---

## 🚀 Quick Start

### Option 1: Run from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the application
python launch.py
```

### Option 2: Standalone EXE (Not ready)

Download the latest release and run `SimObliterator.exe` - no installation required!

---

## 📖 What's Inside

### 🔍 Analysis Tools

- **IFF Inspector** - Browse chunk structure, view hex data
- **BHAV Disassembler** - Decode SimAntics bytecode with semantic names
- **Call Graph Builder** - Visualize behavior relationships
- **Variable Analyzer** - Track data flow through locals, temps, params
- **Behavior Classifier** - Categorize as ROLE/ACTION/GUARD/UTILITY
- **Forensic Analyzer** - Deep pattern analysis for research

### 🎨 Visual & Export Tools

- **Sprite Exporter** - SPR2 to PNG with palette handling
- **Sprite Sheets** - Combine all frames into single image
- **Mesh Exporter** - 3D models to glTF/GLB format
- **Chunk Exporter** - Export raw bytes for any chunk

### 💾 Save Editor

- **Family Money** - Edit household simoleons
- **Sim Skills** - Cooking, Mechanical, Charisma, Logic, Body, Creativity
- **Sim Motives** - Hunger, Comfort, Hygiene, Bladder, Energy, Fun, Social, Room
- **Personality** - Neat, Outgoing, Active, Playful, Nice
- **Career Manager** - 24 career tracks with promotions
- **Relationships** - Daily and lifetime values
- **Aspirations & Memories** - Modify sim goals and history

### 🪑 Object Editing

- **SLOT Editor** - Routing slots for sit, stand, ground positions
- **SLOT Templates** - Pre-built chair/counter configurations
- **SLOT XML** - Export/import for Transmogrifier workflow
- **TTAB Editor** - Menu interactions, autonomy levels, motive effects
- **Multi-Object IFF** - Correctly handles multiple objects per file

### 📦 File Operations

- **FAR Browser** - Browse and extract archives
- **ID Conflict Scanner** - Detect GUID/BHAV/semi-global clashes
- **Safe ID Finder** - Find unused ID ranges
- **Content Validation** - Pre-flight checks before edits

---

## 🛡️ Safety First

SimObliterator uses a **transaction-based safety system**:

| Mode           | Description                          |
| -------------- | ------------------------------------ |
| 🔵 **INSPECT** | Read-only, no changes possible       |
| 🟡 **PREVIEW** | See proposed changes before applying |
| 🟢 **MUTATE**  | Apply changes with full audit trail  |

Every write operation:

- Creates automatic backups
- Shows a preview of changes
- Can be undone/redone
- Is logged for audit

---

## 📊 Coverage

All 110 canonical actions are fully implemented:

```
FILE_CONTAINER   ████████████████████ 100%
SAVE_STATE       ████████████████████ 100%
BHAV             ████████████████████ 100%
VISUALIZATION    ████████████████████ 100%
EXPORT           ████████████████████ 100%
IMPORT           ████████████████████ 100%
ANALYSIS         ████████████████████ 100%
SEARCH           ████████████████████ 100%
SYSTEM           ████████████████████ 100%
UI               ████████████████████ 100%
```

---

## 📁 Project Structure

```
SimObliterator_Suite/
├── launch.py              # 🚀 START HERE - Application entry point
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── LICENSE                # MIT License
├── VERSION                # Version info
├── CHANGELOG.md           # Release history
│
├── assets/                # Icons and splash screen
│   ├── icon.ico
│   ├── icon.png
│   └── splash.png
│
├── data/                  # Runtime databases
│   ├── opcodes_db.json           # 143 opcode definitions
│   ├── unknowns_db.json          # Unmapped opcode research
│   ├── global_behaviors.json     # Behavior library
│   ├── global_behavior_database.json  # 251 base game globals + expansion ranges
│   ├── characters.json           # 2MB extracted character data
│   ├── objects.json              # 3MB extracted object data
│   ├── meshes.json               # Mesh metadata
│   └── execution_model.json      # BHAV execution patterns
│
├── Docs/                  # Documentation
│   ├── guides/                   # User & Developer guides
│   │   ├── USER_GUIDE.md         # End-user documentation
│   │   ├── QUICK_REFERENCE.md    # Cheat sheet for common tasks
│   │   ├── UI_DEVELOPER_GUIDE.md # Panel architecture & events
│   │   └── ARCHIVER_GUIDE.md     # Archiver tool usage
│   ├── technical/                # Technical references
│   │   ├── ACTION_MAP.md         # Feature inventory
│   │   ├── ACTION_SURFACE.md     # 110 canonical actions
│   │   ├── TECHNICAL_REFERENCE.md# IFF/BHAV/SLOT/TTAB formats
│   │   └── PRIMITIVE_REFERENCE.md# SimAntics operands
│   ├── research/                 # Deep research docs
│   │   ├── DEFINITIVE_BHAV_REFERENCE.md
│   │   ├── FREESO_BEHAVIORAL_ARCHITECTURE.md
│   │   ├── BHAV_OPCODE_REFERENCE.md
│   │   └── ...                   # More research docs
│   └── INTEGRATION_GAPS.md       # Integration status
│
├── Examples/              # Sample files for testing
│   ├── IFF_Files/
│   └── SaveGames/
│
├── src/                   # Source code
│   ├── main_app.py        # Main window (Dear PyGui)
│   ├── formats/           # File parsers (IFF, FAR, DBPF)
│   ├── Tools/core/        # Parsers, analyzers, editors
│   ├── Tools/forensic/    # Deep analysis tools
│   ├── Tools/graph/       # Resource dependency graphs
│   ├── Tools/gui/         # Panel implementations (incomplete)
│   ├── Tools/save_editor/ # Save file editing
│   ├── Tools/webviewer/   # Web-based viewers & export server
│   └── utils/             # Binary utilities
│
└── dev/                   # Development tools
    ├── tests/             # Test suite
    │   ├── tests.py          # Main runner (--api, --game, --quick, --verbose)
    │   ├── test_api.py       # API tests (174 tests)
    │   ├── test_game.py      # Game file tests (73 tests)
    │   ├── action_coverage.py
    │   └── test_paths.txt
    └── build/             # Build configuration
        ├── SimObliterator.spec
        ├── pyproject.toml
        └── BUILD.md
```

---

## � Documentation

| Guide                                                                      | Audience    | Description                                     |
| -------------------------------------------------------------------------- | ----------- | ----------------------------------------------- |
| [USER_GUIDE.md](Docs/guides/USER_GUIDE.md)                                 | End Users   | Complete walkthrough of all features            |
| [QUICK_REFERENCE.md](Docs/guides/QUICK_REFERENCE.md)                       | Modders     | Cheat sheet for chunk types, opcodes, shortcuts |
| [ARCHIVER_GUIDE.md](Docs/guides/ARCHIVER_GUIDE.md)                         | Users       | Archiver tool for bulk scanning                 |
| [UI_DEVELOPER_GUIDE.md](Docs/guides/UI_DEVELOPER_GUIDE.md)                 | Developers  | Panel architecture, events, extending the GUI   |
| [TECHNICAL_REFERENCE.md](Docs/technical/TECHNICAL_REFERENCE.md)            | Researchers | IFF, BHAV, SLOT, TTAB format specs              |
| [DEFINITIVE_BHAV_REFERENCE.md](Docs/research/DEFINITIVE_BHAV_REFERENCE.md) | Researchers | Deep BHAV execution model analysis              |

---

## �🔧 Development

### Prerequisites

- Python 3.9 or later
- pip package manager

### Setup

```bash
# Clone or extract
cd SimObliterator_Suite

# Create virtual environment (optional but recommended)
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

The test suite is modular with 247 tests across two modules:

```bash
cd dev/tests

# Run all tests (API + Game)
python tests.py

# Run only API tests (no game files needed)
python tests.py --api

# Run only game file tests
python tests.py --game

# Quick mode (fast subset)
python tests.py --quick

# Verbose output
python tests.py --verbose

# Configure game paths for game tests
# Edit test_paths.txt with your installation paths
```

See [dev/README.md](dev/README.md) for full test configuration options.

### Building Standalone EXE

```bash
pip install pyinstaller
pyinstaller dev/build/SimObliterator.spec
```

Or simple build:

```bash
pyinstaller --onefile --windowed --icon=assets/icon.ico --name SimObliterator launch.py
```

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

This software is designed to work with The Sims 1 game files. The Sims is a trademark of Electronic Arts Inc. This project is not affiliated with, endorsed by, or connected to Electronic Arts Inc.

---

## 🙏 Credits

**Created by:** Dnf_Jeff  
**For:** The Sims 1 Modding & Research Community

Special thanks to:

- The FreeSO project for format documentation
- The Sims modding community for decades of research
- Everyone who helped test and provide feedback

---

<p align="center">
  <strong>Made with ❤️ for The Sims community</strong>
</p>
