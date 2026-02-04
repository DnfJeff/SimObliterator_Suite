# Build Instructions

Instructions for building SimObliterator Suite as a standalone executable.

---

## Prerequisites

1. **Python 3.9+** installed
2. **PyInstaller** installed: `pip install pyinstaller`
3. All dependencies installed: `pip install -r requirements.txt`

---

## Quick Build

### One-File Executable

```bash
pyinstaller --onefile --windowed --icon=assets/icon.ico --name SimObliterator launch.py
```

Output: `dist/SimObliterator.exe`

### Using Spec File (Recommended)

```bash
pyinstaller SimObliterator.spec
```

Output: `dist/SimObliterator.exe`

---

## Build Options

### Debug Build (with console)

```bash
pyinstaller --onefile --icon=assets/icon.ico --name SimObliterator_Debug launch.py
```

### Directory Build (faster startup)

```bash
pyinstaller --onedir --windowed --icon=assets/icon.ico --name SimObliterator launch.py
```

Output: `dist/SimObliterator/` folder

---

## Included Assets

The build automatically includes:

| Asset               | Description       |
| ------------------- | ----------------- |
| `assets/icon.ico`   | Windows icon      |
| `assets/icon.png`   | PNG icon          |
| `assets/splash.png` | Splash screen     |
| `data/*.json`       | Runtime databases |
| `Docs/*.md`         | Documentation     |
| `VERSION`           | Version file      |
| `LICENSE`           | License file      |

---

## Post-Build Checklist

1. ✅ Test the EXE launches
2. ✅ Test loading an IFF file
3. ✅ Test loading a FAR archive
4. ✅ Verify icon appears in taskbar
5. ✅ Check File > About shows version

---

## Distribution Package

Create a release ZIP:

```bash
# From dist/ folder
Compress-Archive -Path SimObliterator.exe -DestinationPath SimObliterator_v1.0.0.zip
```

Or include docs:

```powershell
$items = @(
    "dist/SimObliterator.exe",
    "README.md",
    "LICENSE",
    "CHANGELOG.md"
)
Compress-Archive -Path $items -DestinationPath SimObliterator_v1.0.0.zip
```

---

## Troubleshooting

### DearPyGUI not found

```
pip install dearpygui --upgrade
```

### Missing DLL errors

Ensure Visual C++ Redistributable is installed on target machine.

### Antivirus blocks EXE

PyInstaller executables may trigger false positives. Add exception or sign the executable.

---

## Clean Build

Remove previous build artifacts:

```powershell
Remove-Item -Recurse -Force build, dist, *.spec -ErrorAction SilentlyContinue
```

Then rebuild fresh.
