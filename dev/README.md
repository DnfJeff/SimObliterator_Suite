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
├── tests/                  # Test suite (247 tests)
│   ├── tests.py            # Main runner
│   ├── test_api.py         # API tests (174 tests)
│   ├── test_game.py        # Game file tests (73 tests)
│   ├── action_coverage.py  # Coverage analysis
│   └── test_paths.txt      # Configure your game paths
└── README.md               # This file
```

---

## Test Suite

The test suite is modular with 247 tests across two modules.

### Running Tests

```bash
cd dev/tests

# Run all tests
python tests.py

# Run only API tests (no game files required)
python tests.py --api

# Run only game file tests
python tests.py --game

# Quick mode (fast subset)
python tests.py --quick

# Verbose output
python tests.py --verbose

# Run modules standalone
python test_api.py
python test_game.py
```

### Configuration

Edit `tests/test_paths.txt` for game file tests:

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

### Test Modules

| Module         | Tests | Description                                        |
| -------------- | ----- | -------------------------------------------------- |
| `test_api.py`  | 174   | API/module tests - verifies classes and interfaces |
| `test_game.py` | 73    | Real game file tests - parsers, exports, analysis  |

### Game Test Categories

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

### Expected Output

```
════════════════════════════════════════════════════════════════════════════════
SIMOBLITERATOR SUITE - UNIFIED TEST RUNNER
════════════════════════════════════════════════════════════════════════════════

Running API tests...
  API Tests: 174 passed, 0 failed

Running Game tests...
  Game Tests: 73 passed, 0 failed

════════════════════════════════════════════════════════════════════════════════
FINAL RESULTS
────────────────────────────────────────────────────────────────────────────────
Total Passed:  247
Total Failed:  0
────────────────────────────────────────────────────────────────────────────────
```

---

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
