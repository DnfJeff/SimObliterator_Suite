# SimObliterator Quick Reference

Cheat sheet for common tasks.

---

## File Types

| Extension  | Format | Contains                          |
| ---------- | ------ | --------------------------------- |
| `.iff`     | IFF    | Objects, sprites, behaviors       |
| `.far`     | FAR    | Archive of IFFs                   |
| `.package` | DBPF   | Sims 2/3 format                   |
| `User*.iff`| Save   | Save game data                    |

---

## Chunk Types

| Code | Name     | Purpose                    |
| ---- | -------- | -------------------------- |
| OBJD | Object   | Object definition          |
| BHAV | Behavior | Script code                |
| STR# | Strings  | Text strings               |
| TTAB | TTAB     | Pie menu interactions      |
| SLOT | Slot     | Attachment points          |
| SPR# | Sprite   | Graphics (2D)              |
| SPR2 | Sprite2  | Graphics with depth        |
| DGRP | DrawGroup| Sprite organization        |
| GLOB | Global   | Global behavior reference  |
| TPRP | TreeProps| Behavior tree properties   |

---

## Common Opcodes

| ID   | Name                | Purpose                     |
| ---- | ------------------- | --------------------------- |
| 0x00 | Sleep               | Pause execution             |
| 0x01 | Generic Sims Call   | Core sim actions            |
| 0x02 | Expression          | Math operations             |
| 0x03 | Find Best Object    | Object selection            |
| 0x04 | Random              | Random number               |
| 0x10 | Old Animate         | Play animation              |
| 0x12 | Run Tree by Name    | Call behavior by name       |
| 0x13 | Show String         | Display text                |
| 0x16 | Go to Relative      | Routing                     |
| 0x2C | Get Distance To     | Distance calculation        |

---

## Keyboard Shortcuts

| Action           | Shortcut     |
| ---------------- | ------------ |
| Open             | Ctrl+O       |
| Save             | Ctrl+S       |
| Find             | Ctrl+F       |
| Call Graph       | Ctrl+G       |
| Hex View         | Ctrl+H       |
| Export           | Ctrl+E       |
| Go to Definition | Ctrl+Click   |

---

## GUID Ranges

| Range                    | Owner           |
| ------------------------ | --------------- |
| 0x00000000 - 0x0000FFFF  | Maxis Base      |
| 0x00010000 - 0x0001FFFF  | Livin' Large    |
| 0x00020000 - 0x0002FFFF  | House Party     |
| 0x00030000 - 0x0003FFFF  | Hot Date        |
| 0x00040000 - 0x0004FFFF  | Vacation        |
| 0x00050000 - 0x0005FFFF  | Unleashed       |
| 0x00060000 - 0x0006FFFF  | Superstar       |
| 0x00070000 - 0x0007FFFF  | Makin' Magic    |
| 0x10000000+              | Custom Content  |

---

## Expression Operators

| Op | Meaning        | Op | Meaning        |
| -- | -------------- | -- | -------------- |
| 0  | = (assign)     | 8  | += (increment) |
| 1  | + (add)        | 9  | -= (decrement) |
| 2  | - (subtract)   | 10 | &= (and-set)   |
| 3  | \* (multiply)  | 11 | Clear flag     |
| 4  | / (divide)     | 12 | \|= (or-set)   |
| 5  | <= (compare)   | 13 | Push to stack  |
| 6  | < (less)       | 14 | Pop from stack |
| 7  | == (equal)     |    |                |

---

## Data Scopes

| ID | Scope           | Description                |
| -- | --------------- | -------------------------- |
| 0  | My              | Current object locals      |
| 1  | Stack Object    | Target of action           |
| 2  | Neighbor        | Other sim                  |
| 3  | Local           | Temp variables (local)     |
| 4  | Literal         | Constant value             |
| 5  | Param           | Passed parameters          |
| 6  | My Motive       | Calling sim's motives      |
| 7  | Neighbor Motive | Other sim's motives        |

---

## Motive IDs

| ID | Motive    |
| -- | --------- |
| 0  | Hunger    |
| 1  | Comfort   |
| 2  | Hygiene   |
| 3  | Bladder   |
| 4  | Energy    |
| 5  | Fun       |
| 6  | Social    |
| 7  | Room      |

---

## Skill IDs

| ID | Skill       |
| -- | ----------- |
| 0  | Cooking     |
| 1  | Mechanical  |
| 2  | Charisma    |
| 3  | Body        |
| 4  | Logic       |
| 5  | Creativity  |

---

## CLI Usage

```bash
# Run main app
python launch.py

# Run tests
cd dev/tests
python tests.py           # All tests
python tests.py --api     # API only
python tests.py --game    # Game files only
python tests.py --quick   # Fast subset
```

---

## File Paths (Windows)

```
# Game Install
C:\Games\The Sims Legacy Collection\

# Game Data
...\GameData\

# User Saves (Legacy Collection)
C:\Users\<You>\Saved Games\Electronic Arts\The Sims 25\

# User Saves (Classic)
Documents\EA Games\The Sims\UserData\
```

---

## Resources

| Resource                    | Location                      |
| --------------------------- | ----------------------------- |
| Full User Guide             | Docs/guides/USER_GUIDE.md     |
| Developer Guide             | Docs/guides/UI_DEVELOPER_GUIDE.md |
| BHAV Reference              | Docs/research/DEFINITIVE_BHAV_REFERENCE.md |
| Opcode Database             | data/opcodes_db.json          |
| Global Behaviors            | data/global_behaviors.json    |
