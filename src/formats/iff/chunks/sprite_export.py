"""
Sprite Exporter - Export SPR/SPR2 sprites to PNG images

Handles:
  - SPR2 RLE decompression with all segment codes
  - Z-buffer and alpha channel extraction  
  - Palette lookup and RGBA conversion
  - PNG export with transparency
  - DGRP composite exports (4 directions × 3 zooms)

Based on FreeSO's SPR2.cs DecodeStandard/Detailed methods.
"""

import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, List, Tuple

if TYPE_CHECKING:
    from formats.iff.chunks.spr import SPR2, SPR2Frame
    from formats.iff.chunks.palt import PALT
    from formats.iff.chunks.dgrp import DGRP


@dataclass
class DecodedSprite:
    """Decoded sprite with RGBA pixels and optional z-buffer."""
    width: int
    height: int
    rgba_data: bytes        # RGBA pixels (width * height * 4)
    zbuffer_data: Optional[bytes] = None  # Z values (width * height)
    position_x: int = 0     # Sprite offset X (for compositing)
    position_y: int = 0     # Sprite offset Y


class SPR2Decoder:
    """
    Decodes SPR2 RLE-encoded sprite data.
    
    SPR2 RLE format (based on FreeSO's SPR2.cs):
        Each row starts with a marker (2 bytes):
            marker >> 13 = command (0-7)
            marker & 0x1FFF = count
        
        Row commands:
            0x00: Fill row with pixel data, count = byte size of row data
            0x04: Skip count rows (leave transparent)
            0x05: End marker
        
        Pixel commands (within row data):
            0x01: Z + palette index (2 bytes per pixel)
            0x02: Z + palette index + alpha (3 bytes per pixel)
            0x03: Skip count pixels (transparent)
            0x06: Palette index only (1 byte per pixel)
    """
    
    def __init__(self, palette: Optional['PALT'] = None):
        self.palette = palette
        self.default_color = (128, 128, 128)  # Gray for missing palette
    
    def decode_frame(self, frame: 'SPR2Frame', 
                     palette: Optional['PALT'] = None) -> Optional[DecodedSprite]:
        """
        Decode an SPR2 frame to RGBA pixels.
        
        Args:
            frame: SPR2Frame with raw_data
            palette: PALT chunk for color lookup (uses self.palette if None)
            
        Returns:
            DecodedSprite with RGBA data
        """
        if not frame.raw_data or frame.width == 0 or frame.height == 0:
            return None
        
        pal = palette or self.palette
        has_pixels = bool(frame.flags & 0x01)
        has_zbuffer = bool(frame.flags & 0x02)
        has_alpha = bool(frame.flags & 0x04)
        
        width = frame.width
        height = frame.height
        
        # Initialize output buffers
        rgba = bytearray(width * height * 4)  # RGBA
        zbuf = bytearray(width * height) if has_zbuffer else None
        
        # Initialize to transparent
        for i in range(width * height):
            rgba[i*4 + 3] = 0  # Alpha = 0
            if zbuf:
                zbuf[i] = 255  # Z = far
        
        # Parse RLE data
        data = frame.raw_data
        pos = 0
        y = 0
        
        while pos + 2 <= len(data) and y < height:
            # Read row marker
            marker = struct.unpack_from('<H', data, pos)[0]
            pos += 2
            
            command = (marker >> 13) & 0x7
            count = marker & 0x1FFF
            
            if command == 0x00:
                # Fill row with pixel data
                # count = total bytes in this row's data (including the 2-byte marker we just read)
                bytes_remaining = count - 2
                x = 0
                
                while bytes_remaining > 0 and x < width:
                    if pos + 2 > len(data):
                        break
                    
                    # Read pixel command
                    px_marker = struct.unpack_from('<H', data, pos)[0]
                    pos += 2
                    bytes_remaining -= 2
                    
                    px_cmd = (px_marker >> 13) & 0x7
                    px_count = px_marker & 0x1FFF
                    
                    if px_cmd == 0x01:
                        # Z + palette (2 bytes per pixel)
                        for _ in range(px_count):
                            if pos + 2 > len(data) or x >= width:
                                break
                            z_val = data[pos]
                            pal_idx = data[pos + 1]
                            pos += 2
                            bytes_remaining -= 2
                            
                            r, g, b = self._get_color(pal, pal_idx, frame.transparent_index)
                            a = 0 if pal_idx == frame.transparent_index else 255
                            
                            offset = (y * width + x) * 4
                            rgba[offset:offset + 4] = bytes([r, g, b, a])
                            if zbuf:
                                zbuf[y * width + x] = z_val
                            x += 1
                            
                    elif px_cmd == 0x02:
                        # Z + palette + alpha (3 bytes per pixel)
                        for _ in range(px_count):
                            if pos + 3 > len(data) or x >= width:
                                break
                            z_val = data[pos]
                            pal_idx = data[pos + 1]
                            a = data[pos + 2]
                            pos += 3
                            bytes_remaining -= 3
                            
                            r, g, b = self._get_color(pal, pal_idx, frame.transparent_index)
                            
                            offset = (y * width + x) * 4
                            rgba[offset:offset + 4] = bytes([r, g, b, a])
                            if zbuf:
                                zbuf[y * width + x] = z_val
                            x += 1
                        
                        # Padding for odd count
                        if (px_count * 3) % 2 != 0 and bytes_remaining > 0:
                            pos += 1
                            bytes_remaining -= 1
                            
                    elif px_cmd == 0x03:
                        # Skip pixels (transparent)
                        x += px_count
                        
                    elif px_cmd == 0x06:
                        # Palette only (1 byte per pixel)
                        for _ in range(px_count):
                            if pos >= len(data) or x >= width:
                                break
                            pal_idx = data[pos]
                            pos += 1
                            bytes_remaining -= 1
                            
                            r, g, b = self._get_color(pal, pal_idx, frame.transparent_index)
                            a = 0 if pal_idx == frame.transparent_index else 255
                            
                            offset = (y * width + x) * 4
                            rgba[offset:offset + 4] = bytes([r, g, b, a])
                            x += 1
                        
                        # Padding for odd count
                        if px_count % 2 != 0 and bytes_remaining > 0:
                            pos += 1
                            bytes_remaining -= 1
                    else:
                        # Unknown pixel command
                        break
                
                y += 1
                
            elif command == 0x04:
                # Skip count rows (leave transparent)
                y += count
                
            elif command == 0x05:
                # End marker
                break
            else:
                # Unknown row command
                y += 1
        
        return DecodedSprite(
            width=width,
            height=height,
            rgba_data=bytes(rgba),
            zbuffer_data=bytes(zbuf) if zbuf else None,
            position_x=frame.position_x,
            position_y=frame.position_y
        )
    
    def _get_color(self, palette: Optional['PALT'], index: int, 
                   transparent_index: int) -> Tuple[int, int, int]:
        """Get RGB color from palette index."""
        if palette and 0 <= index < len(palette.colors):
            return palette.colors[index]
        return self.default_color


def export_sprite_png(sprite: DecodedSprite, filepath: str):
    """
    Export a decoded sprite to PNG file.
    
    Uses pure Python PNG encoding (no PIL dependency).
    """
    import zlib
    
    def make_png(width: int, height: int, rgba_data: bytes) -> bytes:
        """Create PNG file bytes from RGBA data."""
        # PNG signature
        signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk
        ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
        ihdr = make_chunk(b'IHDR', ihdr_data)
        
        # IDAT chunk (compressed image data)
        raw_data = bytearray()
        for y in range(height):
            raw_data.append(0)  # Filter type: None
            row_start = y * width * 4
            raw_data.extend(rgba_data[row_start:row_start + width * 4])
        
        compressed = zlib.compress(bytes(raw_data), 9)
        idat = make_chunk(b'IDAT', compressed)
        
        # IEND chunk
        iend = make_chunk(b'IEND', b'')
        
        return signature + ihdr + idat + iend
    
    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        """Create a PNG chunk with CRC."""
        length = struct.pack('>I', len(data))
        crc_data = chunk_type + data
        crc = zlib.crc32(crc_data) & 0xFFFFFFFF
        return length + crc_data + struct.pack('>I', crc)
    
    png_bytes = make_png(sprite.width, sprite.height, sprite.rgba_data)
    
    with open(filepath, 'wb') as f:
        f.write(png_bytes)


def export_zbuffer_png(sprite: DecodedSprite, filepath: str):
    """Export z-buffer as grayscale PNG."""
    if not sprite.zbuffer_data:
        return
    
    import zlib
    
    def make_grayscale_png(width: int, height: int, gray_data: bytes) -> bytes:
        signature = b'\x89PNG\r\n\x1a\n'
        
        # Grayscale, 8-bit
        ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0)
        ihdr = make_chunk(b'IHDR', ihdr_data)
        
        raw_data = bytearray()
        for y in range(height):
            raw_data.append(0)
            row_start = y * width
            raw_data.extend(gray_data[row_start:row_start + width])
        
        compressed = zlib.compress(bytes(raw_data), 9)
        idat = make_chunk(b'IDAT', compressed)
        iend = make_chunk(b'IEND', b'')
        
        return signature + ihdr + idat + iend
    
    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack('>I', len(data))
        crc_data = chunk_type + data
        crc = zlib.crc32(crc_data) & 0xFFFFFFFF
        return length + crc_data + struct.pack('>I', crc)
    
    png_bytes = make_grayscale_png(sprite.width, sprite.height, sprite.zbuffer_data)
    
    with open(filepath, 'wb') as f:
        f.write(png_bytes)


class DGRPExporter:
    """
    Export DGRP (Draw Group) composites.
    
    DGRP defines how sprites are composited for each view:
      - 4 directions (NE, SE, SW, NW) 
      - 3 zoom levels (far, medium, near)
      - Multiple sprites per view with offsets
    """
    
    def __init__(self, decoder: SPR2Decoder):
        self.decoder = decoder
    
    def export_all_views(self, dgrp: 'DGRP', spr2: 'SPR2', 
                         palette: 'PALT', output_dir: str,
                         name_prefix: str = "sprite"):
        """
        Export all 12 views (4 dir × 3 zoom) as separate PNGs.
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        directions = ['ne', 'se', 'sw', 'nw']
        zooms = ['far', 'med', 'near']
        
        for img_idx, img in enumerate(dgrp.images):
            dir_idx = img_idx // 3
            zoom_idx = img_idx % 3
            
            direction = directions[dir_idx] if dir_idx < 4 else f"d{dir_idx}"
            zoom = zooms[zoom_idx] if zoom_idx < 3 else f"z{zoom_idx}"
            
            composite = self.composite_image(img, spr2, palette)
            if composite:
                filename = f"{name_prefix}_{direction}_{zoom}.png"
                filepath = os.path.join(output_dir, filename)
                export_sprite_png(composite, filepath)
    
    def composite_image(self, dgrp_image, spr2: 'SPR2', 
                        palette: 'PALT') -> Optional[DecodedSprite]:
        """
        Composite all sprites in a DGRP image into single sprite.
        """
        if not dgrp_image.sprites:
            return None
        
        # Calculate bounding box
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        decoded_sprites = []
        for sprite_ref in dgrp_image.sprites:
            if 0 <= sprite_ref.sprite_index < len(spr2.frames):
                frame = spr2.frames[sprite_ref.sprite_index]
                decoded = self.decoder.decode_frame(frame, palette)
                if decoded:
                    # Apply sprite reference offset
                    x = sprite_ref.sprite_x + decoded.position_x
                    y = sprite_ref.sprite_y + decoded.position_y
                    
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x + decoded.width)
                    max_y = max(max_y, y + decoded.height)
                    
                    decoded_sprites.append((decoded, x, y, sprite_ref))
        
        if not decoded_sprites:
            return None
        
        # Create composite image
        width = int(max_x - min_x)
        height = int(max_y - min_y)
        
        if width <= 0 or height <= 0:
            return None
        
        rgba = bytearray(width * height * 4)
        
        # Composite sprites (back to front based on DGRP order)
        for decoded, x, y, ref in decoded_sprites:
            offset_x = int(x - min_x)
            offset_y = int(y - min_y)
            
            for sy in range(decoded.height):
                for sx in range(decoded.width):
                    dst_x = offset_x + sx
                    dst_y = offset_y + sy
                    
                    if 0 <= dst_x < width and 0 <= dst_y < height:
                        src_offset = (sy * decoded.width + sx) * 4
                        dst_offset = (dst_y * width + dst_x) * 4
                        
                        # Simple alpha compositing
                        src_a = decoded.rgba_data[src_offset + 3]
                        if src_a > 0:
                            rgba[dst_offset:dst_offset + 4] = (
                                decoded.rgba_data[src_offset:src_offset + 4]
                            )
        
        return DecodedSprite(
            width=width,
            height=height,
            rgba_data=bytes(rgba),
            position_x=int(min_x),
            position_y=int(min_y)
        )


# Convenience functions
def decode_spr2_frame(frame: 'SPR2Frame', palette: 'PALT') -> Optional[DecodedSprite]:
    """Quick decode a single SPR2 frame."""
    decoder = SPR2Decoder(palette)
    return decoder.decode_frame(frame, palette)


def export_spr2_to_png(frame: 'SPR2Frame', palette: 'PALT', filepath: str) -> bool:
    """Export a single SPR2 frame to PNG file."""
    sprite = decode_spr2_frame(frame, palette)
    if sprite:
        export_sprite_png(sprite, filepath)
        return True
    return False


# Test
if __name__ == "__main__":
    # Create test sprite (2x2 checkerboard)
    test_rgba = bytes([
        255, 0, 0, 255,    0, 255, 0, 255,   # Row 0: red, green
        0, 0, 255, 255,    255, 255, 0, 255  # Row 1: blue, yellow
    ])
    
    test_sprite = DecodedSprite(
        width=2,
        height=2,
        rgba_data=test_rgba
    )
    
    print("Testing PNG export...")
    export_sprite_png(test_sprite, "test_sprite.png")
    print("Created test_sprite.png (2x2 checkerboard)")
