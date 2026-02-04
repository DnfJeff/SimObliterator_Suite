"""
Minimal chunk parsers for Phase 1.

These parse only the fields needed for reference extraction.
This avoids importing from the formats package entirely.
"""

from dataclasses import dataclass
from typing import Optional
from utils.binary import IoBuffer, ByteOrder


@dataclass
class MinimalOBJD:
    """Minimal OBJD chunk - only what Phase 1 extractors need."""
    chunk_id: int
    object_type: int
    
    # BHAV entry points (old format - usually 0 in modern TS1)
    bhav_init: int = 0
    bhav_main_id: int = 0
    bhav_cleanup: int = 0
    
    # Graphics references
    base_graphic_id: int = 0  # DGRP
    num_graphics: int = 0
    
    # Interaction table
    tree_table_id: int = 0  # TTAB
    
    # String references
    catalog_strings_id: int = 0
    body_string_id: int = 0
    
    # Routing
    slot_id: int = 0  # SLOT


def parse_objd(chunk_data: bytes, chunk_id: int) -> Optional[MinimalOBJD]:
    """
    Parse OBJD chunk into minimal representation.
    
    OBJD structure (TS1 format, little-endian uint16 fields):
    Field offsets (in half-words):
    - [0] version (138)
    - [1] initial_stack_size
    - [2] base_graphic_id (DGRP)
    - [3] num_graphics
    - [4] object_type
    - [7] tree_table_id (TTAB)
    - [19] body_string_id
    - [20] slot_id (SLOT)
    - [41] catalog_strings_id
    """
    if len(chunk_data) < 44:
        return None
    
    try:
        buf = IoBuffer.from_bytes(chunk_data, ByteOrder.LITTLE_ENDIAN)
        
        # Read header
        version = buf.read_uint16()
        initial_stack = buf.read_uint16()
        base_graphic = buf.read_uint16()
        num_graphics = buf.read_uint16()
        obj_type = buf.read_uint16()
        unknown_5 = buf.read_uint16()
        unknown_6 = buf.read_uint16()
        tree_table = buf.read_uint16()
        
        objd = MinimalOBJD(
            chunk_id=chunk_id,
            object_type=obj_type,
            base_graphic_id=base_graphic,
            num_graphics=num_graphics,
            tree_table_id=tree_table,
        )
        
        # Continue reading fields
        interaction_group = buf.read_uint16()  # [8]
        obj_type_repeat = buf.read_uint16()    # [9]
        master_id_low = buf.read_uint16()      # [10]
        master_id_high = buf.read_uint16()     # [11]
        unknown_12 = buf.read_uint16()         # [12]
        unknown_13 = buf.read_uint16()         # [13]
        guid_low = buf.read_uint16()           # [14]
        guid_high = buf.read_uint16()          # [15]
        disabled = buf.read_uint16()           # [16]
        unused_17 = buf.read_uint16()          # [17]
        price = buf.read_uint16()              # [18]
        body_string = buf.read_uint16()        # [19]
        slot_id = buf.read_uint16()            # [20]
        
        objd.body_string_id = body_string
        objd.slot_id = slot_id
        
        # Skip ahead to catalog_strings_id at offset [41]
        # We're currently at offset [21], need to get to [41]
        for i in range(21, 41):
            buf.read_uint16()
        
        catalog_strings = buf.read_uint16()    # [41]
        objd.catalog_strings_id = catalog_strings
        
        return objd
    except Exception as e:
        print(f"Error parsing OBJD: {e}")
        return None


@dataclass
class MinimalSPR2:
    """Minimal SPR2 chunk - only palette reference."""
    chunk_id: int
    palette_id: int = 0


def parse_spr2(chunk_data: bytes, chunk_id: int) -> Optional[MinimalSPR2]:
    """
    Parse SPR2 chunk to extract palette ID.
    
    SPR2 structure:
    - Header with palette ID at specific offset
    """
    if len(chunk_data) < 10:
        return None
    
    try:
        buf = IoBuffer.from_bytes(chunk_data, ByteOrder.LITTLE_ENDIAN)
        
        spr2 = MinimalSPR2(chunk_id=chunk_id)
        
        # Palette ID is typically at offset 0-2
        spr2.palette_id = buf.read_uint16()
        
        return spr2
    except Exception as e:
        print(f"Error parsing SPR2: {e}")
        return None


@dataclass
class BHAVInstruction:
    """Minimal BHAV instruction for reference extraction."""
    opcode: int = 0
    true_pointer: int = 0
    false_pointer: int = 0
    operand: bytes = None


@dataclass
class MinimalBHAV:
    """Minimal BHAV chunk - only instructions for reference extraction."""
    chunk_id: int
    instructions: list = None
    args: int = 0
    locals: int = 0
    type: int = 0
    
    def __post_init__(self):
        if self.instructions is None:
            self.instructions = []


def parse_bhav(chunk_data: bytes, chunk_id: int) -> Optional[MinimalBHAV]:
    """
    Parse BHAV chunk to extract subroutine call references.
    
    BHAV structure (header):
    - [0-1]: Signature (0x8002 = standard)
    - [2-3]: Instruction count
    - [4-5]: Type
    - [6-7]: Args
    - [8-9]: Locals + Flags + Reserved
    
    Then 12-byte instructions:
    - [0-1]: Opcode
    - [2]: True pointer
    - [3]: False pointer
    - [4-11]: Operands (8 bytes)
    """
    if len(chunk_data) < 12:
        return None
    
    try:
        buf = IoBuffer.from_bytes(chunk_data, ByteOrder.LITTLE_ENDIAN)
        
        bhav = MinimalBHAV(chunk_id=chunk_id)
        
        # Read header
        signature = buf.read_uint16()
        
        if signature == 0x8002:
            # Standard format
            count = buf.read_uint16()
            bhav.type = buf.read_byte()
            bhav.args = buf.read_byte()
            bhav.locals = buf.read_uint16()
            buf.read_uint16()  # skip reserved
        else:
            # Other formats (simplified)
            count = buf.read_uint16()
            buf.read_bytes(8)  # skip unknown bytes
        
        # Read instructions
        bhav.instructions = []
        for _ in range(count):
            if buf.position + 12 > len(chunk_data):
                break
                
            inst = BHAVInstruction()
            inst.opcode = buf.read_uint16()
            inst.true_pointer = buf.read_byte()
            inst.false_pointer = buf.read_byte()
            inst.operand = buf.read_bytes(8)
            
            bhav.instructions.append(inst)
        
        return bhav
    except Exception as e:
        print(f"Error parsing BHAV: {e}")
        return None


@dataclass
class TTABInteractionRef:
    """TTAB interaction with only reference-extraction fields."""
    action_function: int = 0  # BHAV ID for action
    test_function: int = 0    # BHAV ID for availability test (guard)
    tta_index: int = 0        # Index into TTAs string list


@dataclass
class MinimalTTAB:
    """Minimal TTAB chunk - only what reference extraction needs."""
    chunk_id: int
    version: int = 0
    interactions: list = None
    
    def __post_init__(self):
        if self.interactions is None:
            self.interactions = []


def parse_ttab(chunk_data: bytes, chunk_id: int) -> Optional[MinimalTTAB]:
    """
    Parse TTAB chunk to extract BHAV interaction references.
    
    TTAB structure (all versions):
    - [0-1]: Interaction count
    - [2-3]: Version (2-10)
    - [4]: Compression code (V9-10 only, 0=normal, 1=compressed)
    
    Per interaction (version-dependent):
    - [0-1]: Action BHAV ID
    - [2-3]: Test (Guard) BHAV ID
    - [4-7]: Motive count
    - [8-11]: Flags
    - [12-15]: TTAs string index
    - [16+]: More fields depending on version
    
    Versions differ mainly in field sizes and presence of optional fields.
    We extract action/test BHAV and TTAs index for all versions.
    """
    if len(chunk_data) < 4:
        return None
    
    try:
        buf = IoBuffer.from_bytes(chunk_data, ByteOrder.LITTLE_ENDIAN)
        
        ttab = MinimalTTAB(chunk_id=chunk_id)
        
        # Read header
        count = buf.read_uint16()
        if count == 0:
            return ttab
        
        ttab.version = buf.read_uint16()
        
        # Version 3 and below not supported
        if ttab.version <= 3:
            return ttab
        
        # Skip compression code for V9+ (we're not decompressing)
        if 9 <= ttab.version <= 10:
            compression_code = buf.read_byte()
            # Note: Field encoding (compression_code=1) requires special handling
            # For now, we proceed with normal reading
        
        ttab.interactions = []
        
        for _ in range(count):
            # Check if we have enough bytes for minimal interaction (8 bytes for IDs + counts)
            if not buf.has_bytes(8):
                break
            
            interaction = TTABInteractionRef()
            
            # These are present in all versions
            interaction.action_function = buf.read_uint16()
            interaction.test_function = buf.read_uint16()
            
            # Motive count and flags - check bytes first
            if not buf.has_bytes(12):  # 4 + 4 + 4 for motives, flags, tta_index
                ttab.interactions.append(interaction)
                break
            
            num_motives = buf.read_uint32()
            flags = buf.read_uint32()
            
            # TTAs string index
            interaction.tta_index = buf.read_uint32()
            
            # Version-dependent fields - with bounds checking
            if ttab.version > 6:
                if not buf.has_bytes(4):
                    ttab.interactions.append(interaction)
                    break
                attenuation_code = buf.read_uint32()
            
            if not buf.has_bytes(4):
                ttab.interactions.append(interaction)
                break
            attenuation_value = buf.read_float()
            
            if not buf.has_bytes(8):  # autonomy_threshold + joining_index
                ttab.interactions.append(interaction)
                break
            autonomy_threshold = buf.read_uint32()
            joining_index = buf.read_int32()
            
            # Skip motive entries (with bounds checking)
            motive_entry_size = 2  # effect_delta at minimum
            if ttab.version > 6:
                motive_entry_size = 6  # effect_min(2) + effect_delta(2) + personality(2)
            
            bytes_needed = num_motives * motive_entry_size
            if bytes_needed > 0 and buf.has_bytes(bytes_needed):
                for j in range(num_motives):
                    if ttab.version > 6:
                        effect_min = buf.read_int16()
                    effect_delta = buf.read_int16()
                    if ttab.version > 6:
                        personality = buf.read_uint16()
            
            # TSO flags for version > 9
            if ttab.version > 9 and buf.has_bytes(4):
                flags2 = buf.read_uint32()
            
            ttab.interactions.append(interaction)
        
        return ttab
    except Exception as e:
        # Silently return partial result instead of printing error
        return ttab if 'ttab' in dir() else None


@dataclass
class MinimalBCON:
    """Minimal BCON chunk - only what reference extraction needs."""
    chunk_id: int
    flags: int = 0
    constants: list = None
    
    def __post_init__(self):
        if self.constants is None:
            self.constants = []


def parse_bcon(chunk_data: bytes, chunk_id: int) -> Optional[MinimalBCON]:
    """
    Parse BCON chunk to extract constant values.
    
    BCON structure (all versions):
    - [0]: Count (N)
    - [1]: Flags (0x00 or 0x80)
    - [2+]: Constants (2 bytes each, little-endian signed int16)
    
    BCON is a simple list of integer constants that BHAV code references.
    BHAV opcode 2 (expression) can reference constants by index.
    
    For reference extraction, we just need to verify the BCON exists
    and record its size. The actual operand parsing (to find which BHAV
    instructions reference this BCON) is handled by BHAV extractor.
    """
    if len(chunk_data) < 2:
        return None
    
    try:
        buf = IoBuffer.from_bytes(chunk_data, ByteOrder.LITTLE_ENDIAN)
        
        bcon = MinimalBCON(chunk_id=chunk_id)
        
        # Read header
        count = buf.read_byte()
        bcon.flags = buf.read_byte()
        
        # Read constants
        bcon.constants = []
        for _ in range(count):
            if buf.position + 2 > len(chunk_data):
                break
            # Read as signed int16
            value = buf.read_uint16()
            # Convert to signed if needed
            if value > 32767:
                value = value - 65536
            bcon.constants.append(value)
        
        return bcon
    except Exception as e:
        print(f"Error parsing BCON: {e}")
        return None

@dataclass
class DGRPSprite:
    """Minimal DGRP sprite entry."""
    sprite_id: int = 0
    frame_index: int = 0
    
    
@dataclass
class DGRPImage:
    """Minimal DGRP image (one direction/zoom combo)."""
    direction: int = 0
    zoom: int = 0
    sprites: list = None
    
    def __post_init__(self):
        if self.sprites is None:
            self.sprites = []


@dataclass
class MinimalDGRP:
    """Minimal DGRP chunk - sprite references."""
    chunk_id: int
    version: int = 0
    images: list = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []


def parse_dgrp(chunk_data: bytes, chunk_id: int) -> Optional[MinimalDGRP]:
    """
    Parse DGRP chunk to extract sprite references.
    
    DGRP structure:
    - [0-1]: Version
    - [2-5]: Image count (varies by version)
    - Per image:
      - Direction (1-2 bytes)
      - Zoom (1-2 bytes)
      - Sprite count
      - Per sprite: SpriteID, FrameIndex, Flags, Offsets
    """
    if len(chunk_data) < 4:
        return None
    
    try:
        buf = IoBuffer.from_bytes(chunk_data, ByteOrder.LITTLE_ENDIAN)
        
        dgrp = MinimalDGRP(chunk_id=chunk_id)
        dgrp.version = buf.read_uint16()
        
        # Read image count (varies by version)
        if dgrp.version < 20003:
            image_count = buf.read_uint16()
        else:
            image_count = buf.read_uint32()
        
        # Read images
        for _ in range(image_count):
            image = DGRPImage()
            
            # Read image header
            if dgrp.version < 20003:
                sprite_count = buf.read_uint16()
                image.direction = buf.read_byte()
                image.zoom = buf.read_byte()
            else:
                image.direction = buf.read_uint32()
                image.zoom = buf.read_uint32()
                sprite_count = buf.read_uint32()
            
            # Read sprites in this image
            for _ in range(sprite_count):
                sprite = DGRPSprite()
                
                if dgrp.version < 20003:
                    buf.read_uint16()  # skip type
                    sprite.sprite_id = buf.read_uint16()
                    sprite.frame_index = buf.read_uint16()
                    buf.read_uint16()  # skip flags
                    
                    # Skip offsets (4 bytes each for 2D, 12 for 3D)
                    buf.read_bytes(4)   # sprite offset (2D)
                    buf.read_bytes(12)  # object offset (3D)
                else:
                    sprite.sprite_id = buf.read_uint32()
                    sprite.frame_index = buf.read_uint32()
                    buf.read_uint32()  # skip flags
                    
                    # Skip offsets
                    buf.read_bytes(8)   # sprite offset
                    buf.read_bytes(12)  # object offset
                
                image.sprites.append(sprite)
            
            dgrp.images.append(image)
        
        return dgrp
    except Exception as e:
        print(f"Error parsing DGRP: {e}")
        return None