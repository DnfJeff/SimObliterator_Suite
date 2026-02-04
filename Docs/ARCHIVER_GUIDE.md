# SimObliterator Archiver - User Guide

## Getting Started

### 1. Installation

No installation needed! Just run `SimObliterator_Archiver.exe`

### 2. First Run

The app will create a `data/` folder for databases automatically.

### 3. Point to Your Game

- **Easiest**: Point to `C:\Games\The Sims Legacy Collection\GameData`
- **Or**: Any folder containing IFF/FAR files

### 4. Choose Your Mode

- **Mapping** (default): Build complete structure maps
- **Forensics**: Find unknown opcodes and patterns

### 5. Click Start & Wait

First scan: 5-15 minutes (builds full index)
Later scans: Use cached data (much faster)

---

## Output Files

### Databases (in `data/` folder)

- **unknowns_db.json** - Unknown opcodes and chunks
- **mappings_db.json** - Objects, behaviors, relationships

### Reports (open in browser)

- **unknowns.html** - Interactive unknown opcode table
- **mappings.html** - Game structure statistics

### Stats

- **statistics.txt** - Summary of scan results

---

## Usage Examples

### Example 1: Build Complete Database

```
Input:  C:\Games\The Sims Legacy Collection\GameData
Mode:   Mapping
Result: Complete catalog of 600+ objects, 5000+ behaviors
```

### Example 2: Find Undocumented Opcodes

```
Input:  Your mod folder
Mode:   Forensics
Result: List of unknown BHAV instructions used by mod
```

### Example 3: Analyze Expansion Pack

```
Input:  Livin' Large expansion files
Mode:   Forensics
Result: Opcodes unique to that expansion
```

---

## Interpreting Results

### Unknowns Report

**High occurrence counts** = Common mystery behavior
**Single file** = Mod-specific or very rare

### Mappings Report

**Chunk distribution** = Game mostly sprite/behavior data
**Object count** = More in expansions than base game

---

## Tips & Tricks

- **First run slow?** Normal! Building index takes time
- **Rerun on same folder?** Much faster (uses cache)
- **Want fresh data?** Delete `data/` folder
- **Different game version?** Use different output folder
- **Compare expansions?** Run separate scans, compare JSON

---

## Common Questions

**Q: Is it safe to run?**  
A: Yes! Read-only tool, never modifies files.

**Q: Can I cancel mid-scan?**  
A: Yes, click Cancel. Partial data saved.

**Q: How much disk space?**  
A: Databases typically 50-200 MB depending on game size.

**Q: Can I automate this?**  
A: Not yet, but GUI makes it easy to repeat.

**Q: What about mod compatibility?**  
A: Compare unknowns_db.json between game versions!

---

## Troubleshooting

### "Path not accessible"

- Check permissions on folder
- Try different path
- Run as Administrator

### "Scan seems stuck"

- It's working! Large archives take time
- Check Task Manager - should show 1 python process
- Give it more time or cancel and try smaller folder

### HTML report won't open

- Make sure browser JavaScript is enabled
- Try different browser (Chrome works great)
- Drag HTML file into browser window

---

**For more help, check TROUBLESHOOTING.md**
