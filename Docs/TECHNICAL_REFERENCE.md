# Technical Reference

This document covers the internal file formats and systems reverse-engineered during development of SimObliterator Suite. It serves as a reference for researchers and developers studying The Sims 1 engine.

---

## Table of Contents

1. [IFF Container Format](#iff-container-format)
2. [BHAV - SimAntics Bytecode](#bhav---simantics-bytecode)
3. [SLOT - Routing Slots](#slot---routing-slots)
4. [TTAB - Tree Tables](#ttab---tree-tables)
5. [STR# - String Tables](#str---string-tables)
6. [Save File Structure](#save-file-structure)
7. [Lot Files](#lot-files)
8. [ID Systems](#id-systems)

---

## IFF Container Format

IFF (Interchange File Format) is the primary container format for The Sims 1 game data.

### File Structure

```
┌─────────────────────────────────────┐
│ IFF File                            │
├─────────────────────────────────────┤
│ Header                              │
│   "IFF FILE 2.5:TYPE FOLLOWS"       │
│   (60 bytes, null-padded)           │
├─────────────────────────────────────┤
│ Chunk 1                             │
│   Type (4 bytes): "BHAV", "OBJD"... │
│   Size (4 bytes): Big-endian        │
│   ID   (2 bytes): Little-endian     │
│   Flags (2 bytes)                   │
│   Label (64 bytes, null-terminated) │
│   Data (Size - 76 bytes)            │
├─────────────────────────────────────┤
│ Chunk 2...                          │
└─────────────────────────────────────┘
```

### Common Chunk Types

| Type | Purpose |
|------|---------|
| OBJD | Object Definition - GUID, type, resource refs |
| BHAV | Behavior - SimAntics bytecode |
| TTAB | Tree Table - Pie menu interactions |
| TTAs | Tree Table Strings - Interaction names |
| STR# | String Table - Localized text |
| SLOT | Routing Slots - Where Sims stand |
| CTSS | Catalog Strings - Object descriptions |
| SPR2 | Sprite - 2D graphics |
| BCON | Constants - Named integer values |
| OBJF | Object Functions - Function table |

---

## BHAV - SimAntics Bytecode

BHAV chunks contain SimAntics bytecode - the scripting language for The Sims.

### BHAV Header

```
Offset  Size  Field
0x00    2     Signature (0x8007 = TS1, 0x8009 = TSO)
0x02    2     Instruction Count
0x04    1     Type (0=main, 1=check, 2=semi-global)
0x05    1     Argument Count
0x06    1     Local Variable Count
0x07    1     Flags
0x08    4     Tree Version (TS1 only)
```

### Instruction Format

Each instruction is 12 bytes:

```
Offset  Size  Field
0x00    2     Opcode (primitive number)
0x02    1     True branch target
0x03    1     False branch target
0x04    8     Operand data (primitive-specific)
```

### Branch Targets

| Value | Meaning |
|-------|---------|
| 0-252 | Jump to instruction at that index |
| 253   | Return Error |
| 254   | Return True |
| 255   | Return False |

### ID Ranges

| Range | Scope |
|-------|-------|
| 0-255 | Global primitives (Sleep, Expression, etc.) |
| 256-4095 | Global BHAVs (Behavior.iff) |
| 4096-8191 | Local BHAVs (within object IFF) |
| 8192-12287 | Semi-global BHAVs (shared groups) |

### Variable Scopes

The Expression primitive (opcode 0x02) references variables by scope:

| Code | Scope | Description |
|------|-------|-------------|
| 0 | My | Object's own attributes |
| 1 | Stack Object's | Target object's attributes |
| 4 | Global | Global simulation variables |
| 5 | Literal | Constant value |
| 6 | Local | BHAV local variable |
| 7 | Temp | Temporary (shared across calls) |
| 8 | Parameter | Function parameter |
| 9 | BCON | Named constant from BCON chunk |

---

## SLOT - Routing Slots

SLOT resources define where Sims can stand relative to objects.

### SLOT Header

```
Offset  Size  Field
0x00    2     Version (typically 4)
0x02    2     Slot Count
0x04    2     Unknown/Padding
```

### Slot Entry (Version 4)

```
Offset  Size  Field
0x00    2     Slot Type
0x02    4     X Position (float)
0x06    4     Y Position (float)
0x0A    4     Z Position (float)
0x0E    4     Facing (float, radians)
0x12    2     Flags
0x14    2     Target Slot Index
0x16    4     Height Offset (float)
0x1A    4     Standing Eye Offset (float)
0x1E    4     Sitting Eye Offset (float)
```

### Slot Types

| Code | Type | Purpose |
|------|------|---------|
| 0 | Absolute | Fixed world position |
| 1 | Standing | Where Sim stands to use object |
| 2 | Sitting | Where Sim sits |
| 3 | Ground | For dropped items |
| 4 | Routing Target | Intermediate routing point |

### Slot Flags

| Bit | Flag | Meaning |
|-----|------|---------|
| 0x01 | SNAP_TO_SLOT | Sim snaps to exact position |
| 0x02 | FACE_OBJECT | Sim faces the object |
| 0x04 | RANDOM_FACING | Random rotation |
| 0x08 | SITTING_SLOT | Used for sitting animations |
| 0x10 | ROUTING_SLOT | Used for pathfinding |

---

## TTAB - Tree Tables

TTAB chunks define pie menu interactions.

### TTAB Header

```
Offset  Size  Field
0x00    2     Interaction Count
0x02    2     Version (4-10)
```

Version 9+ adds a compression code byte after the version.

### Interaction Entry (Version 7+)

```
Offset  Size  Field
0x00    2     Action BHAV ID
0x02    2     Test BHAV ID (guard function)
0x04    4     Motive Effect Count
0x08    4     Flags
0x0C    4     TTAs String Index
0x10    4     Attenuation Code
0x14    4     Attenuation Value (float)
0x18    4     Autonomy Threshold (0-100)
0x1C    4     Joining Index (-1 = none)
```

### Motive Effects

For each motive (count from header):
```
Offset  Size  Field
0x00    2     Effect Min (V7+)
0x02    2     Effect Delta
0x04    2     Personality Modifier (V7+)
```

### Interaction Flags

| Bit | Flag | Meaning |
|-----|------|---------|
| 0x0001 | ALLOW_VISITORS | Visitors can use |
| 0x0002 | DEBUG_ONLY | Only in debug mode |
| 0x0008 | MUST_RUN | Cannot be cancelled |
| 0x0010 | AUTO_FIRST | Selected by default |
| 0x0040 | ALLOW_CONSOLE | Available via console |
| 0x0400 | ALLOW_GHOSTS | Ghosts can use |

---

## STR# - String Tables

String tables store localized text with multiple format options.

### Format Codes

| Code | Format | Description |
|------|--------|-------------|
| 0xFFFF | Null-Terminated | Simple null-terminated strings |
| 0xFDFF | Language-Coded | Language byte + string + comment |
| 0xFEFF | Paired Null | String + comment pairs |
| 0x00 | Pascal | Length-prefixed strings |

### Language-Coded Format (0xFDFF)

```
Header:
  [0-1]: Format (0xFDFF, big-endian)
  [2-3]: Total Entry Count (little-endian)

Each Entry:
  [0]: Language Code
  [1-N]: String (null-terminated)
  [N+1-M]: Comment (null-terminated)
```

### Language Codes

| Code | Language |
|------|----------|
| 0 | US English |
| 1 | UK English |
| 2 | French |
| 3 | German |
| 4 | Italian |
| 5 | Spanish |
| 6 | Dutch |
| 7 | Danish |
| 8 | Swedish |
| 9 | Norwegian |
| 10 | Finnish |
| 11 | Hebrew |
| 12 | Russian |
| 13 | Portuguese |
| 14 | Japanese |
| 15 | Polish |
| 16 | Chinese Traditional |
| 17 | Chinese Simplified |
| 18 | Thai |
| 19 | Korean |

---

## Save File Structure

Save files (UserXXXXX.iff) contain lot state and Sim data.

### Key Chunks

| Type | ID | Purpose |
|------|-----|---------|
| SIMI | 1 | Simulation Info - global state, time |
| HOUS | 0 | House settings - camera, roof |
| OBJM | 1 | Object Map - placed objects |
| OBJT | 0 | Object Types - GUID references |
| ARRY | 0-10 | Tile arrays - floors, walls, heights |
| NGBH | 1 | Neighborhood data |
| FAMI | * | Family/household data |
| PERS | * | Person (Sim) data |
| NBRS | * | Neighbor relationships |

### SIMI Global Data

Key indices in GlobalData array:
```
[0]  - Current Hour (0-23)
[1]  - Day of Month
[5]  - Minutes
[7]  - Month
[8]  - Year
[10] - House Number
[23] - Lot Size (32, 48, or 64)
[35] - Lot Type
```

---

## Lot Files

House IFF files contain lot structure separate from save state.

### Terrain Type by House Number

Terrain is NOT stored in the IFF - it's determined by house number:

| House Numbers | Terrain |
|---------------|---------|
| 1-27, 30-39 | Grass (default) |
| 28-29, 46-48 | Sand (beach) |
| 40-42 | Snow (winter) |
| 90-94 | Dark Grass (Studio Town) |
| 95-96 | Autumn Grass (Magic Town) |
| 99 | Cloud (Magic realm) |

This mapping was discovered in FreeSO's VMTS1Activator.

### ARRY Chunk IDs

| ID | Purpose |
|----|---------|
| 0 | Terrain heights |
| 1 | Ground floor tiles (8-bit) |
| 2 | Ground floor walls (8-bit) |
| 3 | Ground floor object IDs |
| 6 | Grass liveness state |
| 7 | Target grass state |
| 8 | Tile flags |
| 9 | Pool tiles |
| 11 | Ground floor tiles (16-bit) |
| 12 | Ground floor walls (16-bit) |
| 101-112 | Second floor equivalents |

---

## ID Systems

The Sims uses multiple ID systems that can conflict.

### GUID (Global Unique Identifier)

- 32-bit identifier for objects
- Stored in OBJD at offset 28 (4 bytes, little-endian)
- Must be unique across all loaded content
- Custom content should use ranges above 0x10000000

### Chunk IDs

- 16-bit identifier within an IFF file
- Same chunk ID in different files is normal
- Only conflicts if files are merged

### Semi-Global Groups

- Objects can share BHAVs via semi-global groups
- BHAV IDs 8192-12287 are semi-global
- Group ID in OBJD links objects to shared code

---

## References

- FreeSO Project: github.com/riperiperi/FreeSO
- The Sims Open Tech Doc
- Niotso/libtso documentation
- Community wiki archives

---

*This document represents research findings as of February 2026. Some format details may vary by expansion pack version.*
