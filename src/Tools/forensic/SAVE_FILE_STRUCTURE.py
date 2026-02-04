"""
Sims 1 Character Save File Structure Documentation
==================================================

Based on forensic analysis of User00088 (Jeff's character) and comparison
of working vs Sim Enhancer corrupted saves.

FILE: UserXXXXX.iff
Format: IFF (Interchange File Format) - Chunk-based binary

CHUNK STRUCTURE OVERVIEW
========================

Each character save file contains approximately 29-45 chunks depending on
customization. Standard chunks:

IDENTITY & METADATA
-------------------
- OBJD (ID 128): Object Definition - Contains character name in label
  "userXXXXX - [FirstName]"
  
- CTSS (ID 2000): Catalog Text Strings - First name and biography
  Format: FD FF [count] [strings...]
  String 1: First name
  String 2: Biography text

- GLOB (ID 128): Semi-global file reference
  Always "PersonGlobals" - links to shared behavior code

APPEARANCE DATA
---------------
- STR# (ID 200): "bodystring" - CRITICAL clothing/appearance data
  Contains: Body mesh refs, head mesh refs, hand textures, skin tone
  Format: FD FF [count:2] [strings with mesh references]
  
  Example strings:
  - "adult" (age)
  - "b011mafit_01,BODY=b011mafitlgt_beachguy2" (body mesh)
  - "c552ma_dude,HEAD-HEAD=c552malgt_dude" (head mesh)
  - "HEAD", "Top", "R_HAND", "Palm" (attachment points)
  - "male" or "female"
  - "27" (unknown - possibly age/generation)
  - "lgt" or "drk" or "med" (skin tone)
  - Clothing/uniform mesh references

- STR# (ID 304): "suit names" - Named outfit references
- STR# (ID 256): "person attributes" - Attribute labels
- STR# (ID 257): " labels" - Generic labels
- STR# (ID 258): "ross relationship labels" - Relationship type names

BEHAVIOR CODE
-------------
- BHAV (ID 4096): "Main" - Main behavior entry point
- BHAV (ID 4097): "init tree" - Initialization behavior
- BHAV (ID 4098): "load tree" - Load/restore behavior  
- BHAV (ID 4100): "init traits" - Personality initialization
- BHAV (ID 4099): "Clear Personality" - (if customized)
- BHAV (ID 4101): "Pick a Job" - (if customized)
- BHAV (ID 4102): "init skills" - (if customized)

- TPRP (ID 4096-4102): Tree Properties - Metadata for BHAV chunks
- TREE (ID 4096-4102): Behavior tree structure

SLOTS & INVENTORY
-----------------
- SLOT (ID 128): Slot definitions for attachments

IMAGES
------
- BMP_ (ID 2002): "faces" - Face thumbnails (105x41 pixels, 24-bit)
- BMP_ (ID 2003): "rel. images" - Relationship panel images (200x40)
- BMP_ (ID 2004): "newimage" - Create-a-Sim preview (25x25)
- BMP_ (ID 2005): "speech_med" - Speech bubble medium (16x16)
- BMP_ (ID 2006): "speech_large" - Speech bubble large (32x32)
- BMP_ (ID 2007): "web_image" - Web export image (45x45)

RESOURCE MAP
------------
- rsmp (ID 0): Resource map - Index of all chunks with offsets
  CRITICAL for game to locate chunks!
  
  Format:
  [8 bytes header]
  "pmsr" (magic, reversed "rsmp")
  [4 bytes: unknown]
  [4 bytes: entry count]
  [entries: type(4) count(4) offset(4) size(4) flags(2) label(varies)]


SIM ENHANCER CORRUPTION ANALYSIS
================================

Comparing User00088_WORKS.iff (55,380 bytes) vs User00088_BROKEN.iff (55,874 bytes)

CHANGES DETECTED:
1. CTSS 2000: +1 byte, added A3 A3 A3 padding at end
2. STR# 200: +43 bytes, completely restructured string content
3. rsmp 0: +450 bytes, rewritten with different format and A3 padding

ROOT CAUSE:
Sim Enhancer appears to:
1. Use 0xA3 as a padding/filler byte (instead of 0x00)
2. Rewrite the resource map (rsmp) with a bloated format
3. Restructure string tables with different encoding

The A3 padding is particularly problematic as the game expects 0x00 terminators.

FIX STRATEGY:
1. Replace all 0xA3 padding with 0x00
2. Rebuild rsmp chunk from actual chunk positions
3. Verify string table format matches expected encoding


DETAILED CHUNK FORMATS
======================

CTSS FORMAT (Catalog Text String Set)
-------------------------------------
Offset  Size  Description
0x00    2     Format code: FD FF = format -3 (extended)
0x02    2     String count (little-endian)
0x04    varies String data:
              [1 byte: length] [string bytes] [00 00]

Example (Jeff's character):
FD FF 02 00           ; Format -3, 2 strings
01 4A 65 66 66 00 00  ; String 1: length=1(?), "Jeff", null null
01 4A 65 20 48...     ; String 2: Biography "Je Het Nword\n" (placeholder)

STR# 200 FORMAT (Body String)
-----------------------------
Contains mesh/texture references for character appearance.

Format code: FD FF = format -3
String count: 23 (0x23) typical

Strings define:
[0] Age: "adult", "child", "toddler"
[1] Body mesh: "bXXXmafit_NAME,BODY=bXXXmafitSKN_NAME"
[2] Head mesh: "cXXXma_NAME,HEAD-HEAD=cXXXmaSKN_NAME"
[3-8] Attachment points: "HEAD", "Top", "R_HAND", "Palm", etc.
[9-14] Gender/age/skin: "male"/"female", "27", "lgt"/"drk"/"med"
[15-22] Outfit variations and hand textures

RSMP FORMAT (Resource Map)
--------------------------
Header:
0x00    8     Padding/reserved (00 00 00 00 00 00 00 00)
0x08    4     "pmsr" magic (rsmp reversed)
0x0C    4     Unknown (varies)
0x10    4     Entry count

Entries (variable length):
- 4 bytes: Chunk type (e.g., "STR#", "BHAV")
- 4 bytes: Chunk count for this type
- 4 bytes: Offset in file
- 4 bytes: Size
- 2 bytes: Flags
- Variable: Label (null-terminated)

OBJD FORMAT (Object Definition)
-------------------------------
Size: 216 bytes (version 0x8A)

Offset  Size  Description
0x00    4     Version (0x8A000000 = 138)
0x04    4     Initial stack size (0x30 = 48)
0x08    4     Unknown
0x0C    2     Base graphic ID
0x0E    2     Number of graphics
...
0x10+   varies Object-specific data

The label field (in chunk header) contains "userXXXXX - [Name]"


PERSONALITY & SKILLS STORAGE
============================

Character stats are NOT stored directly in character IFF files!

They are stored in:
- House files (HouseXX.iff) when Sim is at home
- Neighborhood.iff for neighborhood-level data
- PDAT chunks for motive/state data
- FAMI/FAMs chunks for family relationships

To edit money, stats, skills:
- Load the House file where Sim lives
- Find PDAT, FAMI chunks
- Modify relevant values

Money is typically stored in House file, not character file!


SAFE EDITING GUIDELINES
=======================

SAFE to modify:
- CTSS 2000: First name, biography (keep same string count)
- BMP_ chunks: Face/portrait images (keep dimensions)
- STR# 200: Appearance strings (careful with format)

DANGEROUS to modify:
- rsmp: Resource map must match actual chunk positions
- BHAV: Behavior code affects gameplay
- OBJD: Core object definition

MUST preserve:
- Chunk IDs (changing breaks cross-references)
- Overall file structure
- String encoding format


REPAIR TOOL REQUIREMENTS
========================

To fix Sim Enhancer corruption:

1. Load corrupted IFF
2. Scan for 0xA3 sequences that should be 0x00
3. Rebuild rsmp from actual chunk positions:
   - Parse all chunks sequentially
   - Record type, ID, offset, size, label
   - Write new rsmp with correct format
4. Verify CTSS/STR# string terminators
5. Write repaired file

Key insight: The game relies on rsmp to find chunks quickly.
A malformed rsmp causes load failures even if chunks are intact.
"""


# Structure definitions for programmatic use
CHUNK_TYPES = {
    'CTSS': {'desc': 'Catalog Text String Set', 'contains': 'name, bio'},
    'STR#': {'desc': 'String Table', 'contains': 'various strings'},
    'OBJD': {'desc': 'Object Definition', 'contains': 'core identity'},
    'GLOB': {'desc': 'Semi-Global Reference', 'contains': 'PersonGlobals link'},
    'BHAV': {'desc': 'Behavior Code', 'contains': 'SimAntics bytecode'},
    'TPRP': {'desc': 'Tree Properties', 'contains': 'BHAV metadata'},
    'TREE': {'desc': 'Behavior Tree', 'contains': 'tree structure'},
    'SLOT': {'desc': 'Slot Definitions', 'contains': 'attachment points'},
    'BMP_': {'desc': 'Bitmap Image', 'contains': 'portraits/thumbnails'},
    'rsmp': {'desc': 'Resource Map', 'contains': 'chunk index'},
    'PDAT': {'desc': 'Person Data', 'contains': 'motives/state'},
    'FAMI': {'desc': 'Family Data', 'contains': 'relationships'},
    'FAMs': {'desc': 'Family Structure', 'contains': 'family tree'},
    'NGBH': {'desc': 'Neighborhood', 'contains': 'neighborhood data'},
}

CHARACTER_CHUNKS = {
    'required': [
        ('OBJD', 128, 'Character definition'),
        ('CTSS', 2000, 'Name and bio'),
        ('GLOB', 128, 'PersonGlobals reference'),
        ('STR#', 200, 'Body/appearance strings'),
        ('STR#', 256, 'Person attributes'),
        ('BHAV', 4096, 'Main behavior'),
        ('BHAV', 4097, 'Init tree'),
        ('BHAV', 4098, 'Load tree'),
        ('BHAV', 4100, 'Init traits'),
        ('SLOT', 128, 'Slots'),
        ('rsmp', 0, 'Resource map'),
    ],
    'optional': [
        ('STR#', 257, 'Labels'),
        ('STR#', 258, 'Relationship labels'),
        ('STR#', 300, 'Behavior editor strings'),
        ('STR#', 304, 'Suit names'),
        ('BHAV', 4099, 'Clear personality'),
        ('BHAV', 4101, 'Pick a job'),
        ('BHAV', 4102, 'Init skills'),
        ('BMP_', 2002, 'Faces'),
        ('BMP_', 2003, 'Rel images'),
        ('BMP_', 2004, 'New image'),
        ('BMP_', 2005, 'Speech med'),
        ('BMP_', 2006, 'Speech large'),
        ('BMP_', 2007, 'Web image'),
        ('OBJf', 128, 'Object functions'),
    ],
}

# Known corruption signatures
CORRUPTION_SIGNATURES = {
    'sim_enhancer': {
        'pattern': b'\xA3\xA3\xA3',  # Padding with 0xA3
        'description': 'Sim Enhancer uses 0xA3 as padding instead of 0x00',
        'severity': 'HIGH',
    },
    'truncated_rsmp': {
        'pattern': None,  # Check rsmp doesn't cover all chunks
        'description': 'Resource map missing chunk entries',
        'severity': 'CRITICAL',
    },
    'bad_string_terminator': {
        'pattern': b'\xA3',  # Where 0x00 expected
        'description': 'String not properly null-terminated',
        'severity': 'MEDIUM',
    },
}


if __name__ == "__main__":
    print(__doc__)
