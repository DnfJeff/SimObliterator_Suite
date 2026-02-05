"""
Character Exporter - Export Sims 1 character data to web-friendly formats.

Exports character appearance, skeleton, and mesh data for use with
the Three.js web viewer or other tools.
"""

import json
import os
import sys
from pathlib import Path
from dataclasses import asdict
from typing import Optional, Dict, Any

# Add parent paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.iff_reader import IFFReader
from core.skin_registry import SkinRegistry, CharacterAppearance, decode_mesh_naming


def export_character_to_json(iff_path: str, output_path: str = None) -> Dict[str, Any]:
    """
    Export character appearance data from IFF to JSON.
    
    Args:
        iff_path: Path to User####.iff file
        output_path: Optional output JSON path (defaults to same name + .json)
    
    Returns:
        Dictionary of character data
    """
    reader = IFFReader(iff_path)
    if not reader.read():
        raise ValueError(f"Failed to read IFF: {iff_path}")
    
    registry = SkinRegistry()
    appearance = registry.extract_from_iff(reader, iff_path)
    
    if not appearance:
        raise ValueError(f"No character appearance found in: {iff_path}")
    
    # Build comprehensive export
    export_data = {
        "source_file": iff_path,
        "character": appearance.to_dict(),
        "decoded_names": {}
    }
    
    # Decode mesh names
    if appearance.body:
        export_data["decoded_names"]["body"] = decode_mesh_naming(appearance.body.mesh_name)
    if appearance.head:
        export_data["decoded_names"]["head"] = decode_mesh_naming(appearance.head.mesh_name)
    
    # Write to file if path given
    if output_path is None:
        output_path = str(Path(iff_path).with_suffix('.json'))
    
    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Exported to: {output_path}")
    return export_data


def export_skeleton_to_json(bcf_path: str, output_path: str = None) -> Dict[str, Any]:
    """
    Export skeleton data from BCF to JSON.
    
    Args:
        bcf_path: Path to skeleton .cmx.bcf file
        output_path: Optional output JSON path
    
    Returns:
        Dictionary of skeleton data
    """
    from formats.mesh.bcf import BCFReader
    
    reader = BCFReader()
    bcf = reader.read_file(bcf_path)
    
    if not bcf or not bcf.skeletons:
        raise ValueError(f"No skeleton found in: {bcf_path}")
    
    skeleton = bcf.skeletons[0]
    
    # Build bone hierarchy
    bones = []
    for bone in skeleton.bones:
        bone_data = {
            "name": bone.name,
            "parent": bone.parent_name,
            "translation": {
                "x": bone.translation.x,
                "y": bone.translation.y,
                "z": bone.translation.z
            },
            "rotation": {
                "w": bone.rotation.w,
                "x": bone.rotation.x,
                "y": bone.rotation.y,
                "z": bone.rotation.z
            },
            "can_translate": bone.can_translate,
            "can_rotate": bone.can_rotate
        }
        bones.append(bone_data)
    
    export_data = {
        "source_file": bcf_path,
        "name": skeleton.name,
        "bone_count": len(skeleton.bones),
        "bones": bones
    }
    
    if output_path is None:
        output_path = str(Path(bcf_path).with_suffix('.skeleton.json'))
    
    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Exported skeleton to: {output_path}")
    return export_data


def batch_export_characters(directory: str, output_dir: str = None) -> int:
    """
    Export all character IFFs in a directory to JSON.
    
    Args:
        directory: Directory containing User####.iff files
        output_dir: Output directory (defaults to same as input)
    
    Returns:
        Number of characters exported
    """
    if output_dir is None:
        output_dir = directory
    
    os.makedirs(output_dir, exist_ok=True)
    
    count = 0
    path = Path(directory)
    
    for iff_path in path.glob("User*.iff"):
        try:
            output_path = Path(output_dir) / f"{iff_path.stem}.json"
            export_character_to_json(str(iff_path), str(output_path))
            count += 1
        except Exception as e:
            print(f"Failed to export {iff_path.name}: {e}")
    
    print(f"\nExported {count} characters")
    return count


def main():
    """Command line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export Sims 1 character data")
    parser.add_argument("input", help="Input IFF file or directory")
    parser.add_argument("-o", "--output", help="Output path")
    parser.add_argument("--batch", action="store_true", help="Batch process directory")
    parser.add_argument("--skeleton", help="Export skeleton from BCF file")
    
    args = parser.parse_args()
    
    if args.skeleton:
        export_skeleton_to_json(args.skeleton, args.output)
    elif args.batch:
        batch_export_characters(args.input, args.output)
    else:
        export_character_to_json(args.input, args.output)


if __name__ == "__main__":
    main()
