# Development Files

This folder contains development and build tools. **End users don't need these.**

## Structure

```
dev/
├── build/                  # Build & packaging
│   ├── SimObliterator.spec # PyInstaller spec file
│   ├── pyproject.toml      # Python package config
│   ├── version_info.txt    # Windows EXE metadata
│   └── BUILD.md            # Build instructions
├── tests/                  # Test suite
│   ├── real_game_tests.py  # 73 tests against real game files
│   ├── test_suite.py       # Unit tests (135 tests)
│   ├── action_coverage.py  # Coverage analysis
│   └── test_paths.txt      # Configure your game paths
└── README.md               # This file
```

---

## Real Game Tests

The primary test suite validates all parsers and tools against actual game files.

### Configuration

Edit `tests/test_paths.txt` to point to your game installation:

```ini
# Required - Your game install path
GAME_INSTALL=G:/SteamLibrary/steamapps/common/The Sims Legacy Collection

# Required - Save game location
USER_DATA=C:/Users/YourName/Saved Games/Electronic Arts/The Sims 25

# Optional - Custom content for bulk testing
CC_FOLDER=S:/PCGames/SimsStuff/TheSims1 ModBulk
CC_FOLDER_MAXIS=S:/PCGames/SimsStuff/Official Maxis Objects
```

Tests skip gracefully if paths aren't configured.

### Running Tests

```bash
cd dev

# Run all tests
python real_game_tests.py

# Verbose output (show each test name)
python real_game_tests.py --verbose

# Quick mode (fast subset only)
python real_game_tests.py --quick

# Run specific category
python real_game_tests.py --category formats
python real_game_tests.py --category bhav
python real_game_tests.py --category saves
```

### Test Categories

| Category    | Tests                                          |
| ----------- | ---------------------------------------------- |
| `paths`     | Verify configured paths exist                  |
| `formats`   | IFF, FAR, DBPF parsing                         |
| `core`      | Action registry, mutation pipeline, provenance |
| `strings`   | STR# parsing, localization, reference scanning |
| `bhav`      | Disassembly, call graphs, rewiring             |
| `objects`   | OBJD parsing, TTAB interactions, SLOT routing  |
| `lots`      | Lot IFF analysis, terrain, ambient sounds      |
| `saves`     | Save file parsing, sim extraction              |
| `export`    | Sprite/mesh export                             |
| `conflicts` | ID conflict detection                          |
| `forensic`  | Deep pattern analysis                          |
| `all`       | Run everything (default)                       |

### Expected Output

```
════════════════════════════════════════════════════════════════════════════════
SIMOBLITERATOR SUITE - REAL GAME FILE TESTS
════════════════════════════════════════════════════════════════════════════════

Category: formats ─────────────────────────────────────────────────────────────
  [PASS] test_iff_basic_parse
  [PASS] test_far1_extraction
  [PASS] test_dbpf_read
  ...

════════════════════════════════════════════════════════════════════════════════
FINAL RESULTS
────────────────────────────────────────────────────────────────────────────────
Passed:  73
Failed:  0
Skipped: 0
────────────────────────────────────────────────────────────────────────────────
```

---

## Unit Tests

```bash
cd dev/tests
python test_suite.py
```

## Checking Coverage

```bash
cd dev/tests
python action_coverage.py
```

## Building EXE

See [build/BUILD.md](build/BUILD.md) for detailed instructions.

```bash
cd dev/build
pyinstaller SimObliterator.spec
```

Or from root:

```bash
pyinstaller dev/SimObliterator.spec
```
