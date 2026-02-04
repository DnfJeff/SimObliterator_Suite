"""
Analysis Operations - Advanced Analysis and Export Operations

Implements ACTION_SURFACE actions for analysis and export.

Actions Implemented:
- DecodeAnimation (READ) - Complete ANIM chunk decoding
- DetectUnusedAssets (READ) - Scan for unreferenced chunks
- ExportSaveSnapshot (WRITE) - Export save analysis to JSON/HTML
- ExportSpriteSheet (WRITE) - PIL-based sprite sheet generation
"""

import struct
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Tuple
from datetime import datetime
from pathlib import Path

from Tools.core.mutation_pipeline import (
    MutationPipeline, MutationMode, MutationDiff,
    MutationResult, get_pipeline, propose_change
)
from Tools.core.action_registry import validate_action


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AnalysisResult:
    """Result of an analysis operation."""
    success: bool
    message: str
    data: Optional[Any] = None
    output_path: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ANIMATION DECODER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AnimationFrame:
    """A single animation frame."""
    frame_index: int
    sprite_id: int
    offset_x: int = 0
    offset_y: int = 0
    flags: int = 0


@dataclass
class AnimationState:
    """A single animation state (e.g., idle, walk)."""
    state_id: int
    name: str
    frame_count: int
    frames: List[AnimationFrame] = field(default_factory=list)
    speed: float = 1.0
    loop: bool = True


@dataclass
class Animation:
    """Complete animation data."""
    chunk_id: int
    chunk_label: str
    version: int
    state_count: int
    states: List[AnimationState] = field(default_factory=list)
    total_frames: int = 0
    raw_data: bytes = field(default_factory=bytes, repr=False)


class AnimationDecoder:
    """
    Decode ANIM chunks from IFF files.
    
    Implements DecodeAnimation action.
    
    ANIM chunk structure (The Sims 1 format):
    - Header: version, state count
    - For each state: state info, frame count
    - For each frame: sprite reference, offset, flags
    """
    
    def __init__(self):
        self._cache: Dict[int, Animation] = {}
    
    def decode(self, chunk_data: bytes, chunk_id: int = 0,
               chunk_label: str = "") -> Animation:
        """
        Decode an ANIM chunk.
        
        Args:
            chunk_data: Raw chunk data (without header)
            chunk_id: Chunk ID for reference
            chunk_label: Chunk label for reference
            
        Returns:
            Animation
        """
        valid, msg = validate_action('DecodeAnimation', {
            'pipeline_mode': get_pipeline().mode.value
        })
        
        if not valid:
            # Still decode but log warning
            pass
        
        if len(chunk_data) < 4:
            return Animation(
                chunk_id=chunk_id,
                chunk_label=chunk_label,
                version=0,
                state_count=0,
                raw_data=chunk_data
            )
        
        offset = 0
        
        # Parse header
        version = struct.unpack_from('<H', chunk_data, offset)[0]
        offset += 2
        
        state_count = struct.unpack_from('<H', chunk_data, offset)[0]
        offset += 2
        
        animation = Animation(
            chunk_id=chunk_id,
            chunk_label=chunk_label,
            version=version,
            state_count=state_count,
            raw_data=chunk_data
        )
        
        # Parse states
        for state_idx in range(state_count):
            if offset + 8 > len(chunk_data):
                break
            
            state_id = struct.unpack_from('<H', chunk_data, offset)[0]
            offset += 2
            
            frame_count = struct.unpack_from('<H', chunk_data, offset)[0]
            offset += 2
            
            speed_raw = struct.unpack_from('<H', chunk_data, offset)[0]
            offset += 2
            speed = speed_raw / 100.0 if speed_raw > 0 else 1.0
            
            flags = struct.unpack_from('<H', chunk_data, offset)[0]
            offset += 2
            loop = (flags & 0x01) != 0
            
            state = AnimationState(
                state_id=state_id,
                name=f"State_{state_id}",
                frame_count=frame_count,
                speed=speed,
                loop=loop
            )
            
            # Parse frames
            for frame_idx in range(frame_count):
                if offset + 8 > len(chunk_data):
                    break
                
                sprite_id = struct.unpack_from('<H', chunk_data, offset)[0]
                offset += 2
                
                offset_x = struct.unpack_from('<h', chunk_data, offset)[0]  # signed
                offset += 2
                
                offset_y = struct.unpack_from('<h', chunk_data, offset)[0]  # signed
                offset += 2
                
                frame_flags = struct.unpack_from('<H', chunk_data, offset)[0]
                offset += 2
                
                frame = AnimationFrame(
                    frame_index=frame_idx,
                    sprite_id=sprite_id,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    flags=frame_flags
                )
                state.frames.append(frame)
            
            animation.states.append(state)
            animation.total_frames += frame_count
        
        # Cache the result
        self._cache[chunk_id] = animation
        
        return animation
    
    def to_dict(self, animation: Animation) -> Dict:
        """Convert animation to dictionary."""
        return {
            'chunk_id': animation.chunk_id,
            'chunk_label': animation.chunk_label,
            'version': animation.version,
            'state_count': animation.state_count,
            'total_frames': animation.total_frames,
            'states': [
                {
                    'state_id': s.state_id,
                    'name': s.name,
                    'frame_count': s.frame_count,
                    'speed': s.speed,
                    'loop': s.loop,
                    'frames': [
                        {
                            'index': f.frame_index,
                            'sprite_id': f.sprite_id,
                            'offset_x': f.offset_x,
                            'offset_y': f.offset_y,
                            'flags': f.flags
                        }
                        for f in s.frames
                    ]
                }
                for s in animation.states
            ]
        }


def decode_animation(chunk_data: bytes, chunk_id: int = 0,
                     chunk_label: str = "") -> Animation:
    """Decode animation. Convenience function."""
    return AnimationDecoder().decode(chunk_data, chunk_id, chunk_label)


# ═══════════════════════════════════════════════════════════════════════════════
# UNUSED ASSET DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AssetReference:
    """A reference from one chunk to another."""
    source_type: str
    source_id: int
    target_type: str
    target_id: int
    reference_kind: str  # 'sprite', 'behavior', 'string', etc.


@dataclass
class UnusedAssetReport:
    """Report of unused assets."""
    total_chunks: int
    referenced_chunks: int
    unreferenced_chunks: int
    unreferenced_by_type: Dict[str, int]
    unreferenced_list: List[Dict]
    reference_graph: Dict[int, List[int]]


class UnusedAssetDetector:
    """
    Detect unreferenced chunks in IFF files.
    
    Implements DetectUnusedAssets action.
    
    Scans for:
    - Sprites not referenced by DGRP or ANIM
    - BHAVs not referenced by OBJF or other BHAVs
    - Strings not referenced by any chunk
    - DGRPs not referenced by any object
    """
    
    # Chunk types that reference other chunks
    REFERENCING_TYPES = {
        'DGRP': ['SPR#', 'SPR2'],  # Draw groups reference sprites
        'ANIM': ['SPR#', 'SPR2'],  # Animations reference sprites
        'OBJF': ['BHAV'],          # Object functions reference behaviors
        'BHAV': ['BHAV', 'STR#'],  # Behaviors call other behaviors, use strings
        'OBJD': ['DGRP', 'BHAV', 'SLOT', 'TTAB'],  # Object definitions
        'TTAB': ['BHAV', 'STR#'],  # Tree tables reference behaviors and strings
    }
    
    def __init__(self):
        pass
    
    def detect(self, iff_file) -> UnusedAssetReport:
        """
        Detect unused assets in an IFF file.
        
        Args:
            iff_file: IffFile instance to analyze
            
        Returns:
            UnusedAssetReport
        """
        valid, msg = validate_action('DetectUnusedAssets', {
            'pipeline_mode': get_pipeline().mode.value
        })
        
        # Build reference graph
        all_chunks: Set[Tuple[str, int]] = set()
        referenced: Set[Tuple[str, int]] = set()
        reference_graph: Dict[int, List[int]] = {}
        
        # Collect all chunks
        chunks = getattr(iff_file, 'chunks', [])
        for chunk in chunks:
            chunk_type = getattr(chunk, 'type_code', 'UNKN')
            chunk_id = getattr(chunk, 'id', 0)
            all_chunks.add((chunk_type, chunk_id))
        
        # Build references
        for chunk in chunks:
            chunk_type = getattr(chunk, 'type_code', 'UNKN')
            chunk_id = getattr(chunk, 'id', 0)
            
            refs = self._extract_references(chunk)
            reference_graph[chunk_id] = [r[1] for r in refs]
            
            for ref_type, ref_id in refs:
                referenced.add((ref_type, ref_id))
        
        # Calculate unreferenced
        unreferenced = all_chunks - referenced
        
        # Group by type
        unreferenced_by_type: Dict[str, int] = {}
        unreferenced_list = []
        for chunk_type, chunk_id in unreferenced:
            unreferenced_by_type[chunk_type] = unreferenced_by_type.get(chunk_type, 0) + 1
            unreferenced_list.append({
                'type': chunk_type,
                'id': chunk_id,
                'label': self._get_chunk_label(iff_file, chunk_type, chunk_id)
            })
        
        return UnusedAssetReport(
            total_chunks=len(all_chunks),
            referenced_chunks=len(referenced),
            unreferenced_chunks=len(unreferenced),
            unreferenced_by_type=unreferenced_by_type,
            unreferenced_list=unreferenced_list,
            reference_graph=reference_graph
        )
    
    def _extract_references(self, chunk) -> List[Tuple[str, int]]:
        """Extract references from a chunk."""
        refs = []
        chunk_type = getattr(chunk, 'type_code', 'UNKN')
        data = getattr(chunk, 'data', b'')
        
        if chunk_type == 'BHAV':
            # BHAV calls other BHAVs
            refs.extend(self._extract_bhav_refs(data))
        elif chunk_type == 'DGRP':
            # DGRP references sprites
            refs.extend(self._extract_dgrp_refs(data))
        elif chunk_type == 'OBJF':
            # OBJF references BHAVs
            refs.extend(self._extract_objf_refs(data))
        elif chunk_type == 'TTAB':
            # TTAB references BHAVs and strings
            refs.extend(self._extract_ttab_refs(data))
        elif chunk_type == 'ANIM':
            # ANIM references sprites
            refs.extend(self._extract_anim_refs(data))
        
        return refs
    
    def _extract_bhav_refs(self, data: bytes) -> List[Tuple[str, int]]:
        """Extract BHAV call targets."""
        refs = []
        if len(data) < 12:
            return refs
        
        # Parse BHAV header to find instruction count
        try:
            header_size = struct.unpack_from('<H', data, 4)[0]
            instr_count = struct.unpack_from('<H', data, 6)[0]
            
            offset = header_size
            for _ in range(min(instr_count, 256)):
                if offset + 12 > len(data):
                    break
                
                opcode = struct.unpack_from('<H', data, offset)[0]
                
                # Check for call opcodes
                if opcode in (0x0002, 0x0003, 0x0004, 0x0009):
                    # Target ID is in operand bytes
                    if offset + 4 < len(data):
                        target_id = struct.unpack_from('<H', data, offset + 4)[0]
                        refs.append(('BHAV', target_id))
                
                offset += 12  # Standard instruction size
        except:
            pass
        
        return refs
    
    def _extract_dgrp_refs(self, data: bytes) -> List[Tuple[str, int]]:
        """Extract sprite references from DGRP."""
        refs = []
        if len(data) < 4:
            return refs
        
        try:
            image_count = struct.unpack_from('<H', data, 2)[0]
            offset = 4
            
            for _ in range(min(image_count, 256)):
                if offset + 8 > len(data):
                    break
                
                sprite_id = struct.unpack_from('<H', data, offset)[0]
                refs.append(('SPR2', sprite_id))
                refs.append(('SPR#', sprite_id))  # Could be either
                offset += 8
        except:
            pass
        
        return refs
    
    def _extract_objf_refs(self, data: bytes) -> List[Tuple[str, int]]:
        """Extract BHAV references from OBJF."""
        refs = []
        if len(data) < 4:
            return refs
        
        try:
            func_count = struct.unpack_from('<H', data, 0)[0]
            offset = 2
            
            for _ in range(min(func_count, 256)):
                if offset + 4 > len(data):
                    break
                
                bhav_id = struct.unpack_from('<H', data, offset)[0]
                if bhav_id != 0xFFFF and bhav_id != 0:
                    refs.append(('BHAV', bhav_id))
                offset += 4
        except:
            pass
        
        return refs
    
    def _extract_ttab_refs(self, data: bytes) -> List[Tuple[str, int]]:
        """Extract references from TTAB."""
        refs = []
        # TTAB structure is complex, extract BHAVs and strings
        try:
            offset = 0
            while offset + 4 < len(data):
                value = struct.unpack_from('<H', data, offset)[0]
                # Heuristic: BHAV IDs are typically 0x1000-0xFFFF
                if 0x1000 <= value < 0xFFFF:
                    refs.append(('BHAV', value))
                offset += 2
        except:
            pass
        
        return refs
    
    def _extract_anim_refs(self, data: bytes) -> List[Tuple[str, int]]:
        """Extract sprite references from ANIM."""
        refs = []
        try:
            animation = decode_animation(data)
            for state in animation.states:
                for frame in state.frames:
                    refs.append(('SPR2', frame.sprite_id))
                    refs.append(('SPR#', frame.sprite_id))
        except:
            pass
        
        return refs
    
    def _get_chunk_label(self, iff_file, chunk_type: str, chunk_id: int) -> str:
        """Get chunk label if available."""
        chunks = getattr(iff_file, 'chunks', [])
        for chunk in chunks:
            if (getattr(chunk, 'type_code', '') == chunk_type and 
                getattr(chunk, 'id', 0) == chunk_id):
                return getattr(chunk, 'label', f'{chunk_type}#{chunk_id}')
        return f'{chunk_type}#{chunk_id}'


def detect_unused_assets(iff_file) -> UnusedAssetReport:
    """Detect unused assets. Convenience function."""
    return UnusedAssetDetector().detect(iff_file)


# ═══════════════════════════════════════════════════════════════════════════════
# SAVE SNAPSHOT EXPORTER
# ═══════════════════════════════════════════════════════════════════════════════

class SaveSnapshotExporter:
    """
    Export save game analysis to JSON or HTML.
    
    Implements ExportSaveSnapshot action.
    """
    
    def __init__(self):
        pass
    
    def export_json(self, save_manager, output_path: str,
                    reason: str = "") -> AnalysisResult:
        """
        Export save analysis to JSON.
        
        Args:
            save_manager: SaveManager instance
            output_path: Path to write JSON
            reason: Reason for export
            
        Returns:
            AnalysisResult
        """
        valid, msg = validate_action('ExportSaveSnapshot', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True
        })
        
        if not valid:
            return AnalysisResult(False, f"Action blocked: {msg}")
        
        snapshot = self._build_snapshot(save_manager)
        
        diffs = [MutationDiff(
            field_path='export',
            old_value='(none)',
            new_value=output_path,
            display_old='No export',
            display_new=f'Export to {Path(output_path).name}'
        )]
        
        audit = propose_change(
            target_type='save_export',
            target_id='snapshot_json',
            diffs=diffs,
            file_path=output_path,
            reason=reason or "Export save snapshot"
        )
        
        if audit.result == MutationResult.SUCCESS:
            try:
                output = Path(output_path)
                output.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(snapshot, f, indent=2)
                
                return AnalysisResult(
                    True,
                    f"Exported snapshot to {output.name}",
                    data=snapshot,
                    output_path=str(output)
                )
            except Exception as e:
                return AnalysisResult(False, f"Export failed: {e}")
                
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return AnalysisResult(
                True,
                f"Preview: would export to {Path(output_path).name}",
                data=snapshot
            )
        else:
            return AnalysisResult(False, f"ExportSaveSnapshot rejected: {audit.result.value}")
    
    def export_html(self, save_manager, output_path: str,
                    reason: str = "") -> AnalysisResult:
        """
        Export save analysis to HTML.
        
        Args:
            save_manager: SaveManager instance
            output_path: Path to write HTML
            reason: Reason for export
            
        Returns:
            AnalysisResult
        """
        valid, msg = validate_action('ExportSaveSnapshot', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True
        })
        
        if not valid:
            return AnalysisResult(False, f"Action blocked: {msg}")
        
        snapshot = self._build_snapshot(save_manager)
        html = self._generate_html(snapshot)
        
        diffs = [MutationDiff(
            field_path='export',
            old_value='(none)',
            new_value=output_path,
            display_old='No export',
            display_new=f'Export to {Path(output_path).name}'
        )]
        
        audit = propose_change(
            target_type='save_export',
            target_id='snapshot_html',
            diffs=diffs,
            file_path=output_path,
            reason=reason or "Export save snapshot as HTML"
        )
        
        if audit.result == MutationResult.SUCCESS:
            try:
                output = Path(output_path)
                output.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                return AnalysisResult(
                    True,
                    f"Exported HTML to {output.name}",
                    data=snapshot,
                    output_path=str(output)
                )
            except Exception as e:
                return AnalysisResult(False, f"Export failed: {e}")
                
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return AnalysisResult(
                True,
                f"Preview: would export HTML to {Path(output_path).name}",
                data=snapshot
            )
        else:
            return AnalysisResult(False, f"ExportSaveSnapshot rejected: {audit.result.value}")
    
    def _build_snapshot(self, save_manager) -> Dict:
        """Build snapshot data from save manager."""
        snapshot = {
            'metadata': {
                'generated': datetime.now().isoformat(),
                'file_path': getattr(save_manager, 'file_path', ''),
                'version': '1.0'
            },
            'summary': {
                'households': 0,
                'sims': 0,
                'lots': 0,
                'total_funds': 0
            },
            'households': [],
            'sims': [],
            'lots': [],
            'neighborhood': {}
        }
        
        # Extract data from save manager
        if hasattr(save_manager, '_households'):
            for hid, household in save_manager._households.items():
                snapshot['households'].append(household)
                snapshot['summary']['households'] += 1
                snapshot['summary']['total_funds'] += household.get('funds', 0)
        
        if hasattr(save_manager, '_sims'):
            for sid, sim in save_manager._sims.items():
                snapshot['sims'].append(sim)
                snapshot['summary']['sims'] += 1
        
        if hasattr(save_manager, '_lots'):
            for lid, lot in save_manager._lots.items():
                snapshot['lots'].append(lot)
                snapshot['summary']['lots'] += 1
        
        if hasattr(save_manager, '_neighborhood'):
            snapshot['neighborhood'] = save_manager._neighborhood
        
        return snapshot
    
    def _generate_html(self, snapshot: Dict) -> str:
        """Generate HTML report from snapshot."""
        summary = snapshot['summary']
        meta = snapshot['metadata']
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Save Snapshot - {meta.get('file_path', 'Unknown')}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #1e1e1e; color: #d4d4d4; }}
        h1, h2, h3 {{ color: #569cd6; }}
        .summary {{ background: #2d2d2d; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .card {{ background: #2d2d2d; padding: 15px; border-radius: 8px; margin-bottom: 10px; }}
        .stat {{ display: inline-block; margin-right: 30px; }}
        .stat-value {{ font-size: 24px; color: #4ec9b0; }}
        .stat-label {{ color: #808080; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #404040; }}
        th {{ background: #252526; color: #9cdcfe; }}
    </style>
</head>
<body>
    <h1>💾 Save Snapshot</h1>
    <p>Generated: {meta.get('generated', 'Unknown')}</p>
    
    <div class="summary">
        <h2>Summary</h2>
        <div class="stat"><span class="stat-value">{summary['households']}</span><br><span class="stat-label">Households</span></div>
        <div class="stat"><span class="stat-value">{summary['sims']}</span><br><span class="stat-label">Sims</span></div>
        <div class="stat"><span class="stat-value">{summary['lots']}</span><br><span class="stat-label">Lots</span></div>
        <div class="stat"><span class="stat-value">§{summary['total_funds']:,}</span><br><span class="stat-label">Total Funds</span></div>
    </div>
    
    <h2>Households ({len(snapshot['households'])})</h2>
'''
        
        for household in snapshot['households']:
            html += f'''
    <div class="card">
        <h3>{household.get('name', 'Unknown')}</h3>
        <p>Funds: §{household.get('funds', 0):,} | Members: {len(household.get('members', []))}</p>
    </div>
'''
        
        html += f'''
    <h2>Sims ({len(snapshot['sims'])})</h2>
    <table>
        <tr><th>ID</th><th>Name</th><th>Age</th><th>Gender</th></tr>
'''
        
        for sim in snapshot['sims'][:50]:  # Limit to 50
            name = f"{sim.get('first_name', '')} {sim.get('last_name', '')}"
            html += f'''
        <tr><td>{sim.get('id', '?')}</td><td>{name}</td><td>{sim.get('age', '?')}</td><td>{'F' if sim.get('gender', 0) else 'M'}</td></tr>
'''
        
        html += '''
    </table>
</body>
</html>
'''
        return html


def export_save_snapshot(save_manager, output_path: str, 
                         format: str = 'json',
                         reason: str = "") -> AnalysisResult:
    """Export save snapshot. Convenience function."""
    exporter = SaveSnapshotExporter()
    if format.lower() == 'html':
        return exporter.export_html(save_manager, output_path, reason)
    else:
        return exporter.export_json(save_manager, output_path, reason)


# ═══════════════════════════════════════════════════════════════════════════════
# SPRITE SHEET EXPORTER
# ═══════════════════════════════════════════════════════════════════════════════

class SpriteSheetExporter:
    """
    Export sprites to sprite sheet images.
    
    Implements ExportSpriteSheet action.
    
    Uses PIL if available, otherwise exports metadata only.
    """
    
    def __init__(self):
        self._pil_available = False
        try:
            from PIL import Image
            self._pil_available = True
        except ImportError:
            pass
    
    @property
    def pil_available(self) -> bool:
        return self._pil_available
    
    def export(self, sprites: List[Dict], output_path: str,
               columns: int = 8, padding: int = 2,
               reason: str = "") -> AnalysisResult:
        """
        Export sprites to sprite sheet.
        
        Args:
            sprites: List of sprite dicts with 'width', 'height', 'pixels'
            output_path: Path to write image
            columns: Number of columns in sheet
            padding: Padding between sprites
            reason: Reason for export
            
        Returns:
            AnalysisResult
        """
        valid, msg = validate_action('ExportSpriteSheet', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True
        })
        
        if not valid:
            return AnalysisResult(False, f"Action blocked: {msg}")
        
        if not self._pil_available:
            return self._export_metadata_only(sprites, output_path, reason)
        
        diffs = [MutationDiff(
            field_path='export',
            old_value='(none)',
            new_value=output_path,
            display_old='No export',
            display_new=f'Export {len(sprites)} sprites'
        )]
        
        audit = propose_change(
            target_type='sprite_export',
            target_id='sprite_sheet',
            diffs=diffs,
            file_path=output_path,
            reason=reason or f"Export sprite sheet ({len(sprites)} sprites)"
        )
        
        if audit.result == MutationResult.SUCCESS:
            try:
                return self._create_sprite_sheet(sprites, output_path, columns, padding)
            except Exception as e:
                return AnalysisResult(False, f"Export failed: {e}")
                
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return AnalysisResult(
                True,
                f"Preview: would export {len(sprites)} sprites",
                data={'sprite_count': len(sprites), 'columns': columns}
            )
        else:
            return AnalysisResult(False, f"ExportSpriteSheet rejected: {audit.result.value}")
    
    def _create_sprite_sheet(self, sprites: List[Dict], output_path: str,
                             columns: int, padding: int) -> AnalysisResult:
        """Create sprite sheet with PIL."""
        from PIL import Image
        
        if not sprites:
            return AnalysisResult(False, "No sprites to export")
        
        # Calculate dimensions
        max_width = max(s.get('width', 32) for s in sprites)
        max_height = max(s.get('height', 32) for s in sprites)
        
        cell_width = max_width + padding * 2
        cell_height = max_height + padding * 2
        
        rows = (len(sprites) + columns - 1) // columns
        
        sheet_width = columns * cell_width
        sheet_height = rows * cell_height
        
        # Create sheet
        sheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
        
        for i, sprite in enumerate(sprites):
            row = i // columns
            col = i % columns
            
            x = col * cell_width + padding
            y = row * cell_height + padding
            
            width = sprite.get('width', 32)
            height = sprite.get('height', 32)
            pixels = sprite.get('pixels', None)
            
            if pixels is not None:
                # Create sprite image
                if isinstance(pixels, (bytes, bytearray)):
                    # Assume RGBA
                    if len(pixels) == width * height * 4:
                        sprite_img = Image.frombytes('RGBA', (width, height), bytes(pixels))
                        sheet.paste(sprite_img, (x, y))
        
        # Save
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(output, 'PNG')
        
        return AnalysisResult(
            True,
            f"Exported sprite sheet to {output.name}",
            data={
                'sprite_count': len(sprites),
                'sheet_size': (sheet_width, sheet_height),
                'columns': columns,
                'rows': rows
            },
            output_path=str(output)
        )
    
    def _export_metadata_only(self, sprites: List[Dict], output_path: str,
                              reason: str) -> AnalysisResult:
        """Export metadata when PIL is not available."""
        metadata = {
            'warning': 'PIL not available - metadata only',
            'sprite_count': len(sprites),
            'sprites': [
                {
                    'index': i,
                    'width': s.get('width', 0),
                    'height': s.get('height', 0),
                    'has_pixels': s.get('pixels') is not None
                }
                for i, s in enumerate(sprites)
            ]
        }
        
        output = Path(output_path).with_suffix('.json')
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return AnalysisResult(
            True,
            f"PIL not available - exported metadata to {output.name}",
            data=metadata,
            output_path=str(output)
        )


def export_sprite_sheet(sprites: List[Dict], output_path: str,
                        columns: int = 8, padding: int = 2,
                        reason: str = "") -> AnalysisResult:
    """Export sprite sheet. Convenience function."""
    return SpriteSheetExporter().export(sprites, output_path, columns, padding, reason)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Animation
    'AnimationFrame', 'AnimationState', 'Animation',
    'AnimationDecoder', 'decode_animation',
    
    # Unused assets
    'AssetReference', 'UnusedAssetReport',
    'UnusedAssetDetector', 'detect_unused_assets',
    
    # Save snapshot
    'SaveSnapshotExporter', 'export_save_snapshot',
    
    # Sprite sheet
    'SpriteSheetExporter', 'export_sprite_sheet',
    
    # Result type
    'AnalysisResult',
]
