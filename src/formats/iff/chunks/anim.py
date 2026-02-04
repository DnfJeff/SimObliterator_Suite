"""
ANIM Chunk - Keyframe Animation Data

What: Binary format for skeletal animation keyframes in The Sims 1.
Contains bone rotations and translations over time for character/object animation.

Reference: FreeSO tso.files/Formats/IFF/Chunks/ANIM.cs

Structure:
- Header: version (uint32), reserved (uint32)
- Keyframe count (uint16)
- Frame rate (float)
- For each keyframe:
  - Frame number / timestamp
  - Bone transforms (rotation quaternions + translations)
  - Per-vertex influences (for skeletal animation)

Used by: Animation players, character preview, CC Creator pose libraries, furniture animation.

Integration: Works with CMX/SKN skeletal structures to animate 3D models.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import struct
import logging
from pathlib import Path

from ..base import IffChunk, register_chunk

try:
    from ....rendering.math import Quaternion, Vec3
except ImportError:
    # Fallback if rendering module not available
    class Quaternion:
        pass
    class Vec3:
        pass

logger = logging.getLogger(__name__)


@dataclass
class BoneKeyframe:
    """Single bone's keyframe data."""
    bone_id: int
    translation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)  # Quaternion (w,x,y,z)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class AnimationFrame:
    """Complete frame data with all bone transforms."""
    frame_number: int
    timestamp: float  # Seconds from start
    bone_keyframes: Dict[int, BoneKeyframe] = field(default_factory=dict)
    
    def set_bone_transform(self, bone_id: int, 
                          translation: Tuple[float, float, float] = None,
                          rotation: Tuple[float, float, float, float] = None,
                          scale: Tuple[float, float, float] = None):
        """Set or update bone transform for this frame."""
        if bone_id not in self.bone_keyframes:
            self.bone_keyframes[bone_id] = BoneKeyframe(bone_id)
        
        kf = self.bone_keyframes[bone_id]
        if translation:
            kf.translation = translation
        if rotation:
            kf.rotation = rotation
        if scale:
            kf.scale = scale
    
    def get_bone_transform(self, bone_id: int) -> Optional[BoneKeyframe]:
        """Get bone transform for this frame."""
        return self.bone_keyframes.get(bone_id)
    
    def get_bone_ids(self) -> List[int]:
        """Get list of bone IDs with keyframes in this frame."""
        return sorted(self.bone_keyframes.keys())


@dataclass
class AnimationSequence:
    """Complete animation sequence."""
    name: str
    frames_per_second: float
    frames: List[AnimationFrame] = field(default_factory=list)
    loop: bool = True
    priority: int = 0  # Higher = played first
    
    def get_duration(self) -> float:
        """Get animation duration in seconds."""
        if not self.frames:
            return 0.0
        return self.frames[-1].timestamp
    
    def get_frame_count(self) -> int:
        """Get number of frames."""
        return len(self.frames)
    
    def add_frame(self, frame: AnimationFrame):
        """Add frame to sequence."""
        self.frames.append(frame)
        self.frames.sort(key=lambda f: f.timestamp)
    
    def get_frame_at_time(self, time: float) -> Optional[AnimationFrame]:
        """Get closest frame at time (no interpolation)."""
        if not self.frames:
            return None
        
        closest = self.frames[0]
        for frame in self.frames:
            if frame.timestamp > time:
                break
            closest = frame
        
        return closest
    
    def interpolate_frame(self, time: float, frame_count: int) -> Optional[Dict[int, BoneKeyframe]]:
        """
        Interpolate between keyframes at given time.
        
        Returns dict of bone_id -> interpolated BoneKeyframe
        """
        if not self.frames:
            return None
        
        # Clamp time
        duration = self.get_duration()
        if duration <= 0:
            return self.frames[0].bone_keyframes if self.frames else {}
        
        if self.loop:
            time = time % duration
        else:
            time = min(time, duration)
        
        # Find surrounding frames
        frame_before = None
        frame_after = None
        
        for i, frame in enumerate(self.frames):
            if frame.timestamp <= time:
                frame_before = frame
            if frame.timestamp >= time and frame_after is None:
                frame_after = frame
        
        if frame_before is None:
            frame_before = self.frames[0]
        if frame_after is None:
            frame_after = self.frames[-1]
        
        # No interpolation if same frame
        if frame_before == frame_after:
            return frame_before.bone_keyframes.copy()
        
        # Linear interpolation factor
        time_diff = frame_after.timestamp - frame_before.timestamp
        if time_diff <= 0:
            return frame_before.bone_keyframes.copy()
        
        t = (time - frame_before.timestamp) / time_diff
        
        # Interpolate all bones
        result = {}
        all_bone_ids = set(frame_before.bone_keyframes.keys()) | set(frame_after.bone_keyframes.keys())
        
        for bone_id in all_bone_ids:
            kf_before = frame_before.bone_keyframes.get(bone_id)
            kf_after = frame_after.bone_keyframes.get(bone_id)
            
            if kf_before and kf_after:
                # Interpolate between both
                interp_kf = BoneKeyframe(bone_id)
                
                # Linear interpolation for translation
                interp_kf.translation = tuple(
                    b + (a - b) * t 
                    for b, a in zip(kf_before.translation, kf_after.translation)
                )
                
                # SLERP (Spherical Linear Interpolation) for rotation
                # Convert tuple quaternions (w,x,y,z) to Quaternion objects
                q_before = Quaternion(
                    kf_before.rotation[0], 
                    kf_before.rotation[1],
                    kf_before.rotation[2],
                    kf_before.rotation[3]
                )
                q_after = Quaternion(
                    kf_after.rotation[0],
                    kf_after.rotation[1],
                    kf_after.rotation[2],
                    kf_after.rotation[3]
                )
                
                # Perform SLERP interpolation
                q_interp = q_before.slerp(q_after, t)
                interp_kf.rotation = (q_interp.w, q_interp.x, q_interp.y, q_interp.z)
                
                # Linear for scale
                interp_kf.scale = tuple(
                    b + (a - b) * t 
                    for b, a in zip(kf_before.scale, kf_after.scale)
                )
                
                result[bone_id] = interp_kf
            elif kf_before:
                result[bone_id] = kf_before
            elif kf_after:
                result[bone_id] = kf_after
        
        return result
    
    def summary(self) -> str:
        """Get summary of animation."""
        return (
            f"Animation '{self.name}': "
            f"{self.get_frame_count()} frames, "
            f"{self.get_duration():.2f}s @ {self.frames_per_second}fps, "
            f"Loop={self.loop}, Priority={self.priority}"
        )


class ANIM:
    """
    ANIM Chunk - Animation Keyframe Data
    
    Stores skeletal animation data: bone transforms over time.
    """
    
    chunk_type = b'ANIM'
    label = 'ANIM'
    
    def __init__(self):
        self.version: int = 0x4001  # Version 0x4001 (TS1)
        self.reserved: int = 0
        
        # Animation data
        self.sequences: Dict[str, AnimationSequence] = {}
        self.frame_rate: float = 30.0
    
    def read(self, data: bytes):
        """Parse ANIM chunk from binary data."""
        if len(data) < 8:
            logger.warning("ANIM chunk too small")
            return self
        
        offset = 0
        
        # Header
        self.version, self.reserved = struct.unpack('<II', data[offset:offset+8])
        offset += 8
        
        logger.debug(f"ANIM: version={self.version:#x}, reserved={self.reserved}")
        
        # Keyframe count
        if offset + 2 > len(data):
            return self
        
        frame_count = struct.unpack('<H', data[offset:offset+2])[0]
        offset += 2
        
        # Frame rate
        if offset + 4 > len(data):
            return self
        
        self.frame_rate = struct.unpack('<f', data[offset:offset+4])[0]
        offset += 4
        
        logger.debug(f"ANIM: {frame_count} frames @ {self.frame_rate}fps")
        
        # Parse keyframes
        frames = []
        for frame_idx in range(frame_count):
            if offset + 4 > len(data):
                break
            
            frame_num = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            timestamp = frame_num / self.frame_rate if self.frame_rate > 0 else 0
            frame = AnimationFrame(frame_num, timestamp)
            
            # Bone count
            if offset + 2 > len(data):
                break
            
            bone_count = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            # Parse bones in this frame
            for bone_idx in range(bone_count):
                if offset + 2 > len(data):
                    break
                
                bone_id = struct.unpack('<H', data[offset:offset+2])[0]
                offset += 2
                
                # Translation (3 floats)
                if offset + 12 > len(data):
                    break
                
                tx, ty, tz = struct.unpack('<fff', data[offset:offset+12])
                offset += 12
                
                # Rotation (4 floats - quaternion)
                if offset + 16 > len(data):
                    break
                
                rw, rx, ry, rz = struct.unpack('<ffff', data[offset:offset+16])
                offset += 16
                
                # Scale (optional, 3 floats)
                sx, sy, sz = 1.0, 1.0, 1.0
                if offset + 12 <= len(data):
                    # Peek ahead - scale is optional
                    try:
                        sx, sy, sz = struct.unpack('<fff', data[offset:offset+12])
                        offset += 12
                    except:
                        pass
                
                # Store bone transform
                frame.set_bone_transform(
                    bone_id,
                    translation=(tx, ty, tz),
                    rotation=(rw, rx, ry, rz),
                    scale=(sx, sy, sz)
                )
            
            frames.append(frame)
        
        # Create default sequence from frames
        if frames:
            seq = AnimationSequence(
                name="sequence",
                frames_per_second=self.frame_rate,
                frames=frames
            )
            self.sequences["sequence"] = seq
            logger.debug(f"ANIM: Loaded {len(frames)} frames")
        
        return self
    
    def write(self) -> bytes:
        """Write ANIM chunk to binary data."""
        data = bytearray()
        
        # Header
        data.extend(struct.pack('<II', self.version, self.reserved))
        
        # Get all frames from first sequence
        if not self.sequences:
            # No sequences - write empty ANIM
            data.extend(struct.pack('<H', 0))  # 0 frames
            data.extend(struct.pack('<f', 30.0))  # Default FPS
            return bytes(data)
        
        seq = list(self.sequences.values())[0]
        frames = seq.frames
        
        # Frame count and rate
        data.extend(struct.pack('<H', len(frames)))
        data.extend(struct.pack('<f', seq.frames_per_second))
        
        # Write frames
        for frame in frames:
            data.extend(struct.pack('<I', frame.frame_number))
            data.extend(struct.pack('<H', len(frame.bone_keyframes)))
            
            # Write bones
            for bone_id in sorted(frame.bone_keyframes.keys()):
                kf = frame.bone_keyframes[bone_id]
                
                data.extend(struct.pack('<H', bone_id))
                data.extend(struct.pack('<fff', *kf.translation))
                data.extend(struct.pack('<ffff', *kf.rotation))
                data.extend(struct.pack('<fff', *kf.scale))
        
        return bytes(data)
    
    def get_animation(self, name: str) -> Optional[AnimationSequence]:
        """Get animation by name."""
        return self.sequences.get(name)
    
    def add_animation(self, sequence: AnimationSequence):
        """Add animation sequence."""
        self.sequences[sequence.name] = sequence
    
    def list_animations(self) -> List[str]:
        """List all animation names."""
        return list(self.sequences.keys())
    
    def summary(self) -> str:
        """Get summary of all animations."""
        lines = [f"ANIM Chunk ({len(self.sequences)} animations)"]
        for name, seq in self.sequences.items():
            lines.append(f"  - {seq.summary()}")
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return f"<ANIM {len(self.sequences)} sequences>"


# Register chunk
@register_chunk('ANIM')
class ANIMChunk(ANIM):
    """ANIM chunk registered with IFF parser."""
    pass


__all__ = [
    'ANIM', 'ANIMChunk', 'AnimationSequence', 'AnimationFrame', 'BoneKeyframe'
]
