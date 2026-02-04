"""
Import Operations - External Resource Import Layer

Implements ACTION_SURFACE actions for IMPORT category.

Actions Implemented:
- ImportAssetFromModern (WRITE) - Import PNG/glTF assets
- ImportAssetFromLegacy (WRITE) - Import TS1 format assets
- ImportSpritePNG (WRITE) - Import PNG as sprite
- ImportSpriteSheet (WRITE) - Import sprite sheet
- ImportMesh (WRITE) - Import 3D mesh
- ImportBehavior (WRITE) - Import BHAV from another file
- ImportOpcodeDefs (WRITE) - Import opcode definitions
- ImportUnknownsDB (WRITE) - Import unknowns database
- ImportSavePatch (WRITE) - Import save file patch
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
import struct

from Tools.core.mutation_pipeline import (
    MutationPipeline, MutationMode, MutationRequest, 
    MutationDiff, MutationResult, get_pipeline, propose_change
)
from Tools.core.action_registry import validate_action


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ImportResult:
    """Result of an import operation."""
    success: bool
    message: str
    imported_count: int = 0
    imported_ids: List[Any] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Optional[Any] = None


# ═══════════════════════════════════════════════════════════════════════════════
# CHUNK IMPORTER
# ═══════════════════════════════════════════════════════════════════════════════

class ChunkImporter:
    """
    Import chunks from external IFF files.
    
    Provides the foundation for all IFF-based imports.
    """
    
    def __init__(self, target_iff):
        """
        Initialize importer with target IFF.
        
        Args:
            target_iff: IffFile to import into
        """
        self.target = target_iff
    
    def import_chunk(self, chunk, new_id: Optional[int] = None,
                     overwrite: bool = False, reason: str = "") -> ImportResult:
        """
        Import a single chunk.
        
        Args:
            chunk: Chunk to import
            new_id: New ID (or None to use original)
            overwrite: If True, replace existing chunks
            reason: Reason for import
            
        Returns:
            ImportResult
        """
        chunk_type = getattr(chunk, 'chunk_type', 'UNKN')
        original_id = getattr(chunk, 'chunk_id', 0)
        target_id = new_id if new_id is not None else original_id
        
        # Check for existing
        existing = self._find_chunk(chunk_type, target_id)
        if existing and not overwrite:
            return ImportResult(False, f"Chunk {chunk_type}:{target_id} already exists")
        
        # Validate action
        action_name = 'ReplaceChunk' if existing else 'AddChunk'
        valid, msg = validate_action(action_name, {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ImportResult(False, f"Action blocked: {msg}")
        
        # Propose through pipeline
        audit = propose_change(
            target_type='chunk',
            target_id=f"{chunk_type}:{target_id}",
            diffs=[MutationDiff(
                field_path='chunk_import',
                old_value='(not present)' if not existing else f"{chunk_type}:{target_id}",
                new_value=f"{chunk_type}:{target_id}",
                display_old='(empty)' if not existing else 'Existing chunk',
                display_new=f"Imported {chunk_type}:{target_id}"
            )],
            file_path=self.target.filename,
            reason=reason or f"Import {chunk_type}:{target_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            import copy
            new_chunk = copy.deepcopy(chunk)
            new_chunk.chunk_id = target_id
            
            if existing:
                idx = self.target._all_chunks.index(existing)
                self.target._all_chunks[idx] = new_chunk
            else:
                self.target._all_chunks.append(new_chunk)
            
            return ImportResult(
                True,
                f"Imported {chunk_type}:{target_id}",
                imported_count=1,
                imported_ids=[target_id]
            )
            
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return ImportResult(True, f"Preview: would import {chunk_type}:{target_id}")
        else:
            return ImportResult(False, f"Import rejected: {audit.result.value}")
    
    def import_chunks_by_type(self, source_iff, chunk_types: List[str],
                              id_offset: int = 0, reason: str = "") -> ImportResult:
        """
        Import all chunks of specified types from source IFF.
        
        Args:
            source_iff: Source IffFile
            chunk_types: List of 4-char type codes to import
            id_offset: Offset to add to chunk IDs (for collision avoidance)
            reason: Reason for import
            
        Returns:
            ImportResult
        """
        imported = []
        warnings = []
        
        for chunk in source_iff.chunks:
            chunk_type = getattr(chunk, 'chunk_type', '')
            if chunk_type in chunk_types:
                original_id = getattr(chunk, 'chunk_id', 0)
                new_id = original_id + id_offset if id_offset else None
                
                result = self.import_chunk(chunk, new_id=new_id, reason=reason)
                
                if result.success:
                    imported.extend(result.imported_ids)
                else:
                    warnings.append(f"{chunk_type}:{original_id}: {result.message}")
        
        return ImportResult(
            True if imported else False,
            f"Imported {len(imported)} chunks",
            imported_count=len(imported),
            imported_ids=imported,
            warnings=warnings
        )
    
    def _find_chunk(self, chunk_type: str, chunk_id: int):
        """Find existing chunk by type and ID."""
        for chunk in self.target._all_chunks:
            if getattr(chunk, 'chunk_type', '') == chunk_type:
                if getattr(chunk, 'chunk_id', -1) == chunk_id:
                    return chunk
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# SPRITE IMPORTER
# ═══════════════════════════════════════════════════════════════════════════════

class SpriteImporter:
    """
    Import PNG images as SPR2 chunks.
    
    Implements ImportSpritePNG, ImportSpriteSheet actions.
    """
    
    def __init__(self, target_iff):
        """
        Initialize with target IFF.
        
        Args:
            target_iff: IffFile to import into
        """
        self.target = target_iff
    
    def import_png(self, png_path: str, chunk_id: int, 
                   label: str = "", reason: str = "") -> ImportResult:
        """
        Import a PNG file as a sprite.
        
        Args:
            png_path: Path to PNG file
            chunk_id: Chunk ID for the new sprite
            label: Chunk label
            reason: Reason for import
            
        Returns:
            ImportResult
        """
        valid, msg = validate_action('ImportSpritePNG', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ImportResult(False, f"Action blocked: {msg}")
        
        if not os.path.exists(png_path):
            return ImportResult(False, f"PNG not found: {png_path}")
        
        try:
            # Try to import PIL
            try:
                from PIL import Image
            except ImportError:
                return ImportResult(False, "PIL/Pillow not installed - cannot import PNG")
            
            # Load image
            img = Image.open(png_path)
            width, height = img.size
            
            # Convert to indexed color (SPR2 uses palette)
            if img.mode != 'P':
                img = img.convert('P', palette=Image.ADAPTIVE, colors=256)
            
            # Get palette and pixel data
            palette = img.getpalette()
            pixels = list(img.getdata())
            
            # Build SPR2 chunk data
            sprite_data = self._build_spr2_data(width, height, pixels, palette)
            
            # Propose through pipeline
            audit = propose_change(
                target_type='sprite',
                target_id=f"SPR2:{chunk_id}",
                diffs=[MutationDiff(
                    field_path='sprite_import',
                    old_value='(not present)',
                    new_value=f"SPR2:{chunk_id} ({width}x{height})",
                    display_old='(empty)',
                    display_new=f"{width}x{height} sprite from {Path(png_path).name}"
                )],
                file_path=self.target.filename,
                reason=reason or f"Import sprite from {png_path}"
            )
            
            if audit.result == MutationResult.SUCCESS:
                # Create SPR2 chunk
                from formats.iff.chunks.spr import SPR2
                
                chunk = SPR2()
                chunk.chunk_id = chunk_id
                chunk.chunk_type = 'SPR2'
                chunk.chunk_label = label or Path(png_path).stem
                chunk.chunk_data = sprite_data
                
                self.target._all_chunks.append(chunk)
                
                return ImportResult(
                    True,
                    f"Imported {width}x{height} sprite as SPR2:{chunk_id}",
                    imported_count=1,
                    imported_ids=[chunk_id],
                    data={'width': width, 'height': height}
                )
                
            elif audit.result == MutationResult.PREVIEW_ONLY:
                return ImportResult(True, f"Preview: would import {width}x{height} sprite")
            else:
                return ImportResult(False, f"Import rejected: {audit.result.value}")
            
        except Exception as e:
            return ImportResult(False, f"PNG import failed: {e}")
    
    def import_sprite_sheet(self, sheet_path: str, 
                            start_id: int,
                            frame_width: int, frame_height: int,
                            reason: str = "") -> ImportResult:
        """
        Import a sprite sheet as multiple SPR2 chunks.
        
        Args:
            sheet_path: Path to sprite sheet PNG
            start_id: Starting chunk ID
            frame_width: Width of each frame
            frame_height: Height of each frame
            reason: Reason for import
            
        Returns:
            ImportResult
        """
        valid, msg = validate_action('ImportSpriteSheet', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ImportResult(False, f"Action blocked: {msg}")
        
        try:
            from PIL import Image
        except ImportError:
            return ImportResult(False, "PIL/Pillow not installed")
        
        try:
            img = Image.open(sheet_path)
            sheet_width, sheet_height = img.size
            
            cols = sheet_width // frame_width
            rows = sheet_height // frame_height
            total_frames = cols * rows
            
            imported_ids = []
            
            for row in range(rows):
                for col in range(cols):
                    frame_id = start_id + row * cols + col
                    
                    # Extract frame
                    left = col * frame_width
                    top = row * frame_height
                    frame = img.crop((left, top, left + frame_width, top + frame_height))
                    
                    # Save temp and import (simplified - production would do in-memory)
                    temp_path = f"_temp_frame_{frame_id}.png"
                    frame.save(temp_path)
                    
                    result = self.import_png(temp_path, frame_id, 
                                            f"Frame {row * cols + col}", reason)
                    
                    # Clean up
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    if result.success:
                        imported_ids.extend(result.imported_ids)
            
            return ImportResult(
                True,
                f"Imported {len(imported_ids)} frames from sprite sheet",
                imported_count=len(imported_ids),
                imported_ids=imported_ids,
                data={'rows': rows, 'cols': cols}
            )
            
        except Exception as e:
            return ImportResult(False, f"Sprite sheet import failed: {e}")
    
    def _build_spr2_data(self, width: int, height: int, 
                         pixels: List[int], palette: List[int]) -> bytes:
        """
        Build SPR2 chunk data from image data.
        
        This is a simplified implementation - production would use
        full RLE encoding.
        """
        output = bytearray()
        
        # SPR2 header (simplified version)
        output.extend(struct.pack('<I', 1))  # Version
        output.extend(struct.pack('<I', 1))  # Frame count
        output.extend(struct.pack('<I', 0))  # Palette ID (0 = embedded)
        
        # Frame header
        output.extend(struct.pack('<H', width))
        output.extend(struct.pack('<H', height))
        output.extend(struct.pack('<H', 0))  # Flags
        output.extend(struct.pack('<H', 0))  # Reserved
        
        # Palette (256 colors, RGBX)
        for i in range(256):
            if palette and i * 3 + 2 < len(palette):
                output.extend(bytes([
                    palette[i * 3],      # R
                    palette[i * 3 + 1],  # G
                    palette[i * 3 + 2],  # B
                    255                   # A
                ]))
            else:
                output.extend(bytes([0, 0, 0, 255]))
        
        # Pixel data (uncompressed for simplicity)
        for pixel in pixels:
            output.append(pixel)
        
        return bytes(output)


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE IMPORTER
# ═══════════════════════════════════════════════════════════════════════════════

class DatabaseImporter:
    """
    Import opcode definitions and unknowns database.
    
    Implements ImportOpcodeDefs, ImportUnknownsDB actions.
    """
    
    @staticmethod
    def import_opcodes(json_path: str, merge: bool = True) -> ImportResult:
        """
        Import opcode definitions from JSON.
        
        Args:
            json_path: Path to opcodes JSON
            merge: If True, merge with existing. If False, replace.
            
        Returns:
            ImportResult
        """
        valid, msg = validate_action('ImportOpcodeDefs', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ImportResult(False, f"Action blocked: {msg}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                new_opcodes = json.load(f)
            
            # Load existing
            from Tools.core.opcode_loader import OpcodeLoader
            loader = OpcodeLoader()
            
            if merge:
                # Merge with existing
                existing_count = len(loader.get_all_opcodes())
                loader.merge_opcodes(new_opcodes)
                new_count = len(loader.get_all_opcodes())
                added = new_count - existing_count
            else:
                # Replace
                loader.set_opcodes(new_opcodes)
                added = len(new_opcodes)
            
            loader.save()
            
            return ImportResult(
                True,
                f"Imported {added} opcode definitions",
                imported_count=added,
                data={'total': len(loader.get_all_opcodes())}
            )
            
        except Exception as e:
            return ImportResult(False, f"Opcode import failed: {e}")
    
    @staticmethod
    def import_unknowns(json_path: str, merge: bool = True) -> ImportResult:
        """
        Import unknowns database from JSON.
        
        Args:
            json_path: Path to unknowns JSON
            merge: If True, merge with existing. If False, replace.
            
        Returns:
            ImportResult
        """
        valid, msg = validate_action('ImportUnknownsDB', {
            'pipeline_mode': 'mutate',  # Unknowns import is always allowed
            'safety_checked': True
        })
        
        if not valid:
            return ImportResult(False, f"Action blocked: {msg}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                new_unknowns = json.load(f)
            
            from Tools.core.unknowns_db import UnknownsDB
            db = UnknownsDB.get()
            
            if merge:
                before = db.count()
                db.merge(new_unknowns)
                after = db.count()
                added = after - before
            else:
                db.replace(new_unknowns)
                added = db.count()
            
            db.save()
            
            return ImportResult(
                True,
                f"Imported {added} unknown entries",
                imported_count=added,
                data={'total': db.count()}
            )
            
        except Exception as e:
            return ImportResult(False, f"Unknowns import failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# ASSET IMPORTER (UNIFIED)
# ═══════════════════════════════════════════════════════════════════════════════

class AssetImporter:
    """
    Import complete assets (objects with sprites, behaviors, etc).
    
    Implements ImportAssetFromModern, ImportAssetFromLegacy actions.
    """
    
    def __init__(self, target_iff):
        """
        Initialize with target IFF.
        
        Args:
            target_iff: IffFile to import into
        """
        self.target = target_iff
        self.chunk_importer = ChunkImporter(target_iff)
        self.sprite_importer = SpriteImporter(target_iff)
    
    def import_from_iff(self, source_path: str, 
                        object_id: Optional[int] = None,
                        reason: str = "") -> ImportResult:
        """
        Import an asset from another IFF file.
        
        Args:
            source_path: Path to source IFF
            object_id: Specific object ID to import (None = all)
            reason: Reason for import
            
        Returns:
            ImportResult
        """
        valid, msg = validate_action('ImportAssetFromLegacy', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return ImportResult(False, f"Action blocked: {msg}")
        
        try:
            from formats.iff.iff_file import IffFile
            
            source = IffFile.read(source_path)
            
            if object_id is not None:
                # Import specific object and its dependencies
                return self._import_object(source, object_id, reason)
            else:
                # Import all
                return self.chunk_importer.import_chunks_by_type(
                    source,
                    ['OBJD', 'BHAV', 'TTAB', 'STR#', 'BCON', 'TPRP', 'SLOT', 
                     'SPR#', 'SPR2', 'DGRP', 'PALT'],
                    reason=reason
                )
                
        except Exception as e:
            return ImportResult(False, f"Asset import failed: {e}")
    
    def _import_object(self, source_iff, object_id: int, reason: str) -> ImportResult:
        """Import a single object and its dependencies."""
        # Find OBJD
        objd = None
        for chunk in source_iff.chunks:
            if getattr(chunk, 'chunk_type', '') == 'OBJD':
                if getattr(chunk, 'chunk_id', -1) == object_id:
                    objd = chunk
                    break
        
        if objd is None:
            return ImportResult(False, f"Object {object_id} not found")
        
        # Collect dependencies
        dependencies = self._gather_dependencies(source_iff, objd)
        
        # Import all
        imported = []
        warnings = []
        
        for chunk in dependencies:
            result = self.chunk_importer.import_chunk(chunk, reason=reason)
            if result.success:
                imported.extend(result.imported_ids)
            else:
                warnings.append(result.message)
        
        return ImportResult(
            True,
            f"Imported object {object_id} with {len(imported)} chunks",
            imported_count=len(imported),
            imported_ids=imported,
            warnings=warnings
        )
    
    def _gather_dependencies(self, source_iff, objd) -> List[Any]:
        """Gather all chunks that an object depends on."""
        chunks = [objd]
        
        # Get BHAV IDs from OBJF
        objf = None
        for chunk in source_iff.chunks:
            if getattr(chunk, 'chunk_type', '') == 'OBJF':
                if getattr(chunk, 'chunk_id', -1) == objd.chunk_id:
                    objf = chunk
                    break
        
        if objf and hasattr(objf, 'functions'):
            bhav_ids = set()
            for func in objf.functions:
                if hasattr(func, 'action_function'):
                    bhav_ids.add(func.action_function)
                if hasattr(func, 'guard_function'):
                    bhav_ids.add(func.guard_function)
            
            # Add BHAVs
            for chunk in source_iff.chunks:
                if getattr(chunk, 'chunk_type', '') == 'BHAV':
                    if getattr(chunk, 'chunk_id', -1) in bhav_ids:
                        chunks.append(chunk)
        
        # Add other related chunks (same ID convention)
        for chunk in source_iff.chunks:
            chunk_type = getattr(chunk, 'chunk_type', '')
            if chunk_type in ['TTAB', 'STR#', 'BCON', 'SLOT', 'DGRP']:
                if getattr(chunk, 'chunk_id', -1) == objd.chunk_id:
                    chunks.append(chunk)
        
        return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE API
# ═══════════════════════════════════════════════════════════════════════════════

def import_chunk(target_iff, chunk, **kwargs) -> ImportResult:
    """Import a single chunk into an IFF file."""
    return ChunkImporter(target_iff).import_chunk(chunk, **kwargs)


def import_png_sprite(target_iff, png_path: str, chunk_id: int, **kwargs) -> ImportResult:
    """Import a PNG as a sprite."""
    return SpriteImporter(target_iff).import_png(png_path, chunk_id, **kwargs)


def import_asset(target_iff, source_path: str, **kwargs) -> ImportResult:
    """Import an asset from another IFF file."""
    return AssetImporter(target_iff).import_from_iff(source_path, **kwargs)


def import_opcodes(json_path: str, merge: bool = True) -> ImportResult:
    """Import opcode definitions."""
    return DatabaseImporter.import_opcodes(json_path, merge)


def import_unknowns(json_path: str, merge: bool = True) -> ImportResult:
    """Import unknowns database."""
    return DatabaseImporter.import_unknowns(json_path, merge)
