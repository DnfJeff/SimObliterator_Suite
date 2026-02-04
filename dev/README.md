# Development Files

This folder contains development and build tools. **End users don't need these.**

## Contents

| File                  | Purpose                                        |
| --------------------- | ---------------------------------------------- |
| `action_coverage.py`  | Analyze implementation coverage of 110 actions |
| `test_suite.py`       | Comprehensive test suite (135 tests)           |
| `SimObliterator.spec` | PyInstaller build specification                |
| `pyproject.toml`      | Python package configuration                   |
| `version_info.txt`    | Windows EXE version metadata                   |
| `BUILD.md`            | Build instructions                             |

## Running Tests

```bash
cd dev
python test_suite.py
```

## Checking Coverage

```bash
cd dev
python action_coverage.py
```

## Building EXE

```bash
cd dev
pyinstaller SimObliterator.spec
```

Or from root:

```bash
pyinstaller dev/SimObliterator.spec
```
