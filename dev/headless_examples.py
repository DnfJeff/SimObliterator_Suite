#!/usr/bin/env python3
"""
SimObliterator Suite - Headless API Examples
=============================================

This file demonstrates all major backend operations without any GUI.
UI developers: Copy these patterns for your implementation.

Run standalone:
    python headless_examples.py

All examples print results to console.
"""

import sys
from pathlib import Path

# Setup import path
SUITE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SUITE_ROOT / "src"))

# ═══════════════════════════════════════════════════════════════════════════════
# 1. FILE LOADING EXAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

def example_load_iff():
    """Load and inspect an IFF file."""
    print("\n" + "="*60)
    print("EXAMPLE: Load IFF File")
    print("="*60)
    
    from formats.iff.iff_file import IffFile
    
    # You'll need a real path
    test_path = SUITE_ROOT / "Examples/IFF_Files"
    iff_files = list(test_path.glob("*.iff"))
    
    if not iff_files:
        print("  No IFF files found in Examples/IFF_Files/")
        return
    
    iff = IffFile(str(iff_files[0]))
    iff.parse()
    
    print(f"  File: {iff_files[0].name}")
    print(f"  Total chunks: {len(iff.chunks)}")
    
    # Count by type
    types = {}
    for chunk in iff.chunks:
        types[chunk.type_code] = types.get(chunk.type_code, 0) + 1
    
    print("  Chunk types:")
    for t, count in sorted(types.items()):
        print(f"    {t}: {count}")


def example_load_far():
    """Load and list a FAR archive."""
    print("\n" + "="*60)
    print("EXAMPLE: Load FAR Archive")
    print("="*60)
    
    from formats.far.far1 import FAR1Archive
    
    # This requires a real game path
    print("  FAR1Archive class available")
    print("  Usage: FAR1Archive(path).entries")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ACTION REGISTRY EXAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

def example_action_registry():
    """Demonstrate action validation."""
    print("\n" + "="*60)
    print("EXAMPLE: Action Registry")
    print("="*60)
    
    from Tools.core.action_registry import (
        ActionRegistry, validate_action, is_registered_action, get_action_info
    )
    
    registry = ActionRegistry.get()
    summary = registry.summary()
    
    print(f"  Total actions: {summary['total']}")
    print(f"  Write actions: {summary['write_actions']}")
    print(f"  High risk: {summary['high_risk']}")
    
    # Check specific action
    print("\n  Action Validation Examples:")
    
    # Read action - always allowed
    valid, reason = validate_action("LoadIFF")
    print(f"    LoadIFF: {'[OK]' if valid else '[BLOCKED]'} - {reason}")
    
    # Write action in INSPECT mode - blocked
    valid, reason = validate_action("WriteSave", {'pipeline_mode': 'INSPECT'})
    print(f"    WriteSave (INSPECT): {'[OK]' if valid else '[BLOCKED]'} - {reason}")
    
    # Write action in MUTATE mode with confirmation - allowed
    valid, reason = validate_action("WriteSave", {
        'pipeline_mode': 'MUTATE',
        'user_confirmed': True,
        'safety_checked': True
    })
    print(f"    WriteSave (MUTATE+confirm): {'[OK]' if valid else '[BLOCKED]'} - {reason}")
    
    # Unknown action - rejected
    valid, reason = validate_action("FakeAction")
    print(f"    FakeAction: {'[OK]' if valid else '[REJECTED]'}")


def example_list_actions_by_category():
    """List all actions grouped by category."""
    print("\n" + "="*60)
    print("EXAMPLE: Actions by Category")
    print("="*60)
    
    from Tools.core.action_registry import ActionRegistry, ActionCategory
    
    registry = ActionRegistry.get()
    
    for category in ActionCategory:
        actions = registry.get_actions_by_category(category)
        if actions:
            write_count = sum(1 for a in actions if a.mutability.value == 'write')
            print(f"\n  {category.value}: {len(actions)} actions ({write_count} write)")
            for action in actions[:3]:  # Show first 3
                print(f"    - {action.name} [{action.risk.value}]")
            if len(actions) > 3:
                print(f"    ... and {len(actions) - 3} more")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MUTATION PIPELINE EXAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

def example_mutation_pipeline():
    """Demonstrate mutation pipeline modes."""
    print("\n" + "="*60)
    print("EXAMPLE: Mutation Pipeline")
    print("="*60)
    
    from Tools.core.mutation_pipeline import MutationPipeline, MutationMode
    
    pipeline = MutationPipeline.get()
    
    print(f"  Default mode: {pipeline.mode.value}")
    
    # Switch modes
    print("\n  Mode transitions:")
    
    pipeline.set_mode(MutationMode.PREVIEW)
    print(f"    -> PREVIEW: {pipeline.mode.value}")
    
    pipeline.set_mode(MutationMode.MUTATE)
    print(f"    -> MUTATE: {pipeline.mode.value}")
    
    pipeline.set_mode(MutationMode.INSPECT)
    print(f"    -> INSPECT: {pipeline.mode.value}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. BHAV OPERATION EXAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

def example_bhav_operations():
    """Demonstrate BHAV operations classes."""
    print("\n" + "="*60)
    print("EXAMPLE: BHAV Operations")
    print("="*60)
    
    from Tools.core.bhav_operations import (
        BHAVSerializer, BHAVValidator, BHAVEditor, BHAVImporter, BHAVOpResult
    )
    
    print("  Available classes:")
    print(f"    - BHAVSerializer: Serialize BHAV to bytes")
    print(f"    - BHAVValidator: Validate BHAV structure")
    print(f"    - BHAVEditor: Edit with undo support")
    print(f"    - BHAVImporter: Import from external")
    print(f"    - BHAVOpResult: Operation result container")
    
    # Create result
    result = BHAVOpResult(success=True, message="Example operation")
    print(f"\n  Result example: success={result.success}")


def example_opcode_lookup():
    """Demonstrate opcode database lookup."""
    print("\n" + "="*60)
    print("EXAMPLE: Opcode Lookup")
    print("="*60)
    
    from Tools.core.opcode_loader import get_opcode_info, is_known_opcode
    
    opcodes_to_check = [0x0002, 0x0003, 0x0004, 0x0029]
    
    for opcode_id in opcodes_to_check:
        if is_known_opcode(opcode_id):
            info = get_opcode_info(opcode_id)
            print(f"  0x{opcode_id:04X}: {info.get('name', 'Unknown')}")
        else:
            print(f"  0x{opcode_id:04X}: Not in database")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ENTITY EXAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

def example_entities():
    """Demonstrate entity abstractions."""
    print("\n" + "="*60)
    print("EXAMPLE: Entity Abstractions")
    print("="*60)
    
    from Tools.entities.object_entity import ObjectEntity
    from Tools.entities.behavior_entity import BehaviorEntity, BehaviorPurpose
    from Tools.entities.sim_entity import SimEntity
    from Tools.entities.relationship_entity import RelationshipGraph
    
    print("  Entity classes available:")
    print(f"    - ObjectEntity: IFF object data")
    print(f"    - BehaviorEntity: BHAV with purpose classification")
    print(f"    - SimEntity: Sim character data")
    print(f"    - RelationshipGraph: Relationship network")
    
    print(f"\n  BehaviorPurpose values:")
    for purpose in BehaviorPurpose:
        print(f"    - {purpose.name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. MESH EXPORT EXAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

def example_mesh_export():
    """Demonstrate mesh export classes."""
    print("\n" + "="*60)
    print("EXAMPLE: Mesh Export")
    print("="*60)
    
    from Tools.core.mesh_export import (
        Vertex, Face, Mesh, MeshVisualizer, GLTFExporter, ChunkMeshExporter
    )
    
    # Create a simple triangle mesh
    v1 = Vertex(0, 0, 0)
    v2 = Vertex(1, 0, 0)
    v3 = Vertex(0, 1, 0)
    
    # Face takes 3 vertex indices (v0, v1, v2)
    face = Face(v0=0, v1=1, v2=2)
    mesh = Mesh(name="triangle", vertices=[v1, v2, v3], faces=[face])
    
    print(f"  Created mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
    
    bounds = mesh.get_bounds()
    print(f"  Bounds: min={bounds[0]}, max={bounds[1]}")
    
    # Create visualizer for export
    viz = MeshVisualizer(mesh)
    
    # Export to OBJ string (no file needed)
    obj_str = viz.to_obj_string()
    print(f"  OBJ export: {len(obj_str)} characters")
    
    # Export to Three.js JSON
    threejs = viz.to_three_js()
    print(f"  Three.js export: {len(threejs['vertices'])} vertex coords")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SAVE MANAGER EXAMPLES (requires game files)
# ═══════════════════════════════════════════════════════════════════════════════

def example_save_manager():
    """Demonstrate save manager capabilities."""
    print("\n" + "="*60)
    print("EXAMPLE: Save Manager")
    print("="*60)
    
    print("  SaveManager methods available:")
    print("    - load_save(path): Load save folder")
    print("    - families: List all families")
    print("    - get_family_members(id): Get sims in family")
    print("    - set_sim_skill(sim, name, value): Edit skill")
    print("    - set_sim_motive(sim, name, value): Edit motive")
    print("    - set_sim_personality(sim, name, value): Edit trait")
    print("    - set_sim_career(sim, id, level, perf): Edit career")
    print("    - max_all_skills(sim): Max all skills")
    print("    - max_all_motives(sim): Max all motives")
    print("    - set_relationship(sim, neighbor, daily, life): Edit relationship")
    print("    - set_family_money(family_id, amount): Edit money")
    print("    - save(): Write changes")


# ═══════════════════════════════════════════════════════════════════════════════
# 8. FILE OPERATIONS EXAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

def example_file_operations():
    """Demonstrate file operations."""
    print("\n" + "="*60)
    print("EXAMPLE: File Operations")
    print("="*60)
    
    from Tools.core.file_operations import (
        BackupManager, ContainerValidator, IFFWriter, ChunkOperations, FileOpResult
    )
    
    print("  BackupManager:")
    backup = BackupManager()
    print(f"    Instance created: {backup is not None}")
    
    print("\n  ContainerValidator:")
    print("    validate(iff) -> (is_valid, errors)")
    
    print("\n  IFFWriter:")
    print("    write(iff, path) -> FileOpResult")
    
    print("\n  FileOpResult:")
    result = FileOpResult(success=True, message="Example")
    print(f"    success={result.success}")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. CONTAINER OPERATIONS EXAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

def example_container_operations():
    """Demonstrate container operations."""
    print("\n" + "="*60)
    print("EXAMPLE: Container Operations")
    print("="*60)
    
    from Tools.core.container_operations import (
        CacheManager, HeaderNormalizer, IndexRebuilder, 
        IFFSplitter, IFFMerger, ContainerOpResult, clear_caches
    )
    
    cache = CacheManager.get()
    print(f"  CacheManager singleton: {cache is not None}")
    clear_caches()
    print("  Caches cleared")
    
    print("\n  Available operations:")
    print("    - HeaderNormalizer: Fix header issues")
    print("    - IndexRebuilder: Rebuild chunk indices")
    print("    - IFFSplitter: Split multi-object IFF")
    print("    - IFFMerger: Merge IFF files")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run all examples."""
    print("="*60)
    print("SIMOBLITERATOR SUITE - HEADLESS API EXAMPLES")
    print("="*60)
    
    examples = [
        example_load_iff,
        example_action_registry,
        example_list_actions_by_category,
        example_mutation_pipeline,
        example_bhav_operations,
        example_opcode_lookup,
        example_entities,
        example_mesh_export,
        example_file_operations,
        example_container_operations,
        example_save_manager,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n  [ERROR] {example.__name__}: {e}")
    
    print("\n" + "="*60)
    print("ALL EXAMPLES COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
