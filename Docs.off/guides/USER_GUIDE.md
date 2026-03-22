# SimObliterator Suite - User Guide

Complete guide to using SimObliterator for exploring, analyzing, and editing The Sims 1 game files.

---

## Quick Start

### Installation

1. Download `SimObliterator.exe` from Releases
2. Run it - no installation required!

### First Steps

1. **File → Open** or drag-drop a file onto the window
2. Browse chunks in the left panel
3. Click any chunk to inspect it
4. Use the tabs for different views

---

## Supported File Types

| Format | Extension  | Description                        |
| ------ | ---------- | ---------------------------------- |
| IFF    | `.iff`     | Game objects, sprites, behaviors   |
| FAR    | `.far`     | Archive containing multiple IFFs   |
| DBPF   | `.package` | Sims 2/3 package (limited support) |
| Saves  | User\*.iff | Save game files                    |

---

## Main Interface

```
┌─────────────────────────────────────────────────────────────────────────┐
│  File   Edit   View   Tools   Analysis   Help                    [≡]   │
├─────────────────┬───────────────────────────────────────────────────────┤
│                 │                                                       │
│  📁 File Tree   │   📋 Chunk Inspector / BHAV Editor / Graph View      │
│                 │                                                       │
│  ▼ Objects      │   ┌─────────────────────────────────────────────────┐ │
│    ├ chair.iff  │   │  Name: Chair - Dining                          │ │
│    ├ table.iff  │   │  GUID: 0x12345678                               │ │
│    └ lamp.iff   │   │  Price: §120                                    │ │
│                 │   │  ...                                            │ │
│  ▼ Characters   │   └─────────────────────────────────────────────────┘ │
│    └ Bob.iff    │                                                       │
│                 │                                                       │
├─────────────────┴───────────────────────────────────────────────────────┤
│  Status: Loaded 42 chunks from chair.iff                                │
└─────────────────────────────────────────────────────────────────────────┘
```

### Panels

| Panel            | Purpose                                     |
| ---------------- | ------------------------------------------- |
| File Tree        | Browse loaded files and archives            |
| Chunk Inspector  | View chunk properties and raw data          |
| BHAV Editor      | Disassemble and edit behavior scripts       |
| Object Inspector | View object properties (price, name, GUIDs) |
| Graph Canvas     | Visualize behavior call graphs              |
| Character Viewer | Browse sims from save files                 |
| Save Editor      | Edit save game data (money, skills, etc.)   |
| Sprite Export    | Export sprites to PNG                       |

---

## Common Tasks

### Opening Files

**Single File:**

- File → Open (Ctrl+O)
- Drag-drop onto window

**FAR Archives:**

- Open the `.far` file
- Browse contents in tree
- Double-click to extract IFFs

**Entire Game:**

- File → Open Folder
- Point to `GameData` directory
- All files indexed for browsing

### Viewing Objects

1. Open an object IFF (like `chair.iff`)
2. Click **OBJD** chunk in the tree
3. See object properties:
   - Name and description
   - GUID (unique identifier)
   - Buy/sell price
   - Catalog category

### Viewing Behaviors (BHAV)

1. Select a **BHAV** chunk
2. View disassembled instructions
3. Each line shows:
   - Opcode name
   - Parameters
   - True/False branches

### Viewing Sprites

1. Select a **SPR#** or **SPR2** chunk
2. Preview appears in inspector
3. Right-click → Export to save PNG

### Editing Save Games

1. Open a save file (`User00001.iff`)
2. Select Character Viewer tab
3. Browse your sims
4. Edit attributes:
   - Money (household funds)
   - Skills (cooking, mechanical, etc.)
   - Relationships
   - Job/career

⚠️ **Always backup saves before editing!**

---

## Analysis Tools

### Call Graph Visualization

View how behaviors call each other:

1. Select a BHAV chunk
2. View → Show Call Graph
3. Interactive graph shows:
   - Which behaviors call this one
   - Which behaviors it calls
   - Recursion detection

### Conflict Detection

Find ID conflicts between mods:

1. Tools → Conflict Scanner
2. Select folders to scan
3. Report shows:
   - Duplicate GUIDs
   - Overlapping chunk IDs
   - Potential compatibility issues

### Unknown Opcode Finder

Discover undocumented behavior instructions:

1. Tools → Forensic Analysis
2. Scan game files or mods
3. Report shows:
   - Opcodes not in database
   - Frequency and locations
   - Hints for reverse engineering

---

## Export Features

### Sprites → PNG

1. Select SPR# chunk
2. Right-click → Export Sprite
3. Choose format:
   - Single frame
   - All frames (sprite sheet)
   - Animation GIF

### Objects → Text Report

1. Select object file
2. File → Export → Object Report
3. Generates readable summary:
   - All properties
   - Behavior listings
   - String tables

### BHAV → Disassembly

1. Select BHAV chunk
2. File → Export → BHAV Disassembly
3. Generates text file with:
   - Full instruction listing
   - Branch targets
   - Comments

---

## Keyboard Shortcuts

| Action           | Shortcut     |
| ---------------- | ------------ |
| Open File        | Ctrl+O       |
| Save             | Ctrl+S       |
| Close            | Ctrl+W       |
| Find             | Ctrl+F       |
| Find in Files    | Ctrl+Shift+F |
| Previous Chunk   | ↑ or Ctrl+[  |
| Next Chunk       | ↓ or Ctrl+]  |
| Go to Definition | Ctrl+Click   |
| Show Call Graph  | Ctrl+G       |
| Toggle Hex View  | Ctrl+H       |
| Export Selection | Ctrl+E       |

---

## Tips & Tricks

### Navigation

- **Ctrl+Click** on a behavior reference to jump to it
- **Back/Forward** buttons work like a browser
- **Breadcrumb bar** shows current location

### Performance

- Large FAR archives may take a moment to index
- Use search to find chunks quickly
- Close unused files to free memory

### Safety

- Read-only mode is default (no accidental changes)
- Enable Edit Mode for modifications
- Backup reminder before any write operation

---

## Troubleshooting

### "File not recognized"

- Check it's a valid Sims 1 file
- Some expansion files have different formats
- Try opening parent FAR archive instead

### "Chunk appears empty"

- Raw data is always available
- Some chunk types need specific parsers
- Check hex view for raw content

### "Changes not saving"

- Make sure Edit Mode is enabled
- Some chunks are read-only
- Check file isn't locked by game

### "Slow with large files"

- Close other files first
- Use Quick Mode for faster loading
- Consider analyzing subsets

---

## File Locations

### Windows

| Data Type   | Location                                               |
| ----------- | ------------------------------------------------------ |
| Game Files  | `C:\Games\The Sims Legacy Collection\GameData\`        |
| User Saves  | `Documents\EA Games\The Sims\UserData\`                |
| Legacy Save | `C:\Users\You\Saved Games\Electronic Arts\The Sims 25` |

### Finding Custom Content

- Objects: Look in `Downloads\` folder
- Check subdirectories in game install
- CC managers may move files elsewhere

---

## Getting Help

- **README.md** - Project overview
- **Docs/guides/** - This guide and more
- **GitHub Issues** - Report bugs, request features

---

## Safety Notice

SimObliterator can modify game files. Always:

1. ✅ **Backup before editing**
2. ✅ **Test changes on copies first**
3. ✅ **Use Read-Only mode for browsing**
4. ❌ **Don't edit files while game is running**

---

_SimObliterator Suite - Explore, Analyze, Create_
