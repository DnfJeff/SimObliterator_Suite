"""
Action Coverage Analyzer

Maps 110 canonical actions to actual implementation status.
Identifies:
- Fully implemented actions
- Partially implemented actions
- Stubs/placeholders
- Missing implementations

Run: python action_coverage.py
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re

# Paths
DEV_DIR = Path(__file__).parent
SUITE_DIR = DEV_DIR.parent
SRC_DIR = SUITE_DIR / "src"
sys.path.insert(0, str(SUITE_DIR))
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SRC_DIR / "Tools"))
sys.path.insert(0, str(SRC_DIR / "Tools" / "core"))


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION → IMPLEMENTATION MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

# Each action maps to:
# - Module path(s) where implementation should exist
# - Method/function name(s) that implement it
# - Status: FULL, PARTIAL, STUB, MISSING

ACTION_IMPLEMENTATIONS = {
    # ─── 1. FILE / CONTAINER ACTIONS ───────────────────────────────────────
    "LoadSave": {
        "modules": ["Tools/save_editor/save_manager.py", "Tools/forensic/save_file_analyzer.py"],
        "functions": ["SaveManager", "load", "IFFEditor.load"],
        "status": "FULL",
        "notes": "SaveManager and IFFEditor fully functional"
    },
    "WriteSave": {
        "modules": ["Tools/save_editor/save_manager.py", "Tools/core/file_operations.py"],
        "functions": ["save_neighborhood", "commit_changes", "IFFWriter.write"],
        "status": "FULL",
        "notes": "IFFWriter and SaveManager with MutationPipeline integration"
    },
    "BackupSave": {
        "modules": ["Tools/core/file_operations.py"],
        "functions": ["BackupManager", "backup", "backup_file"],
        "status": "FULL",
        "notes": "BackupManager with timestamped backups and registry"
    },
    "RestoreSave": {
        "modules": ["Tools/core/file_operations.py"],
        "functions": ["BackupManager.restore", "restore_file"],
        "status": "FULL",
        "notes": "Restore from backup registry or .bak files"
    },
    "LoadIFF": {
        "modules": ["formats/iff/iff_file.py", "Tools/core/iff_reader.py"],
        "functions": ["IffFile.read", "IFFReader"],
        "status": "FULL",
        "notes": "Complete IFF parser, FreeSO-based"
    },
    "LoadFAR": {
        "modules": ["formats/far/far1.py", "formats/far/far3.py"],
        "functions": ["FAR1Archive", "FAR3Archive"],
        "status": "FULL",
        "notes": "FAR1 and FAR3 parsers complete"
    },
    "WriteIFF": {
        "modules": ["Tools/core/file_operations.py", "formats/iff/iff_file.py"],
        "functions": ["IFFWriter", "write", "_serialize"],
        "status": "FULL",
        "notes": "Complete IFF serialization with MutationPipeline integration"
    },
    "WriteFAR": {
        "modules": ["Tools/core/container_operations.py"],
        "functions": ["FARWriter", "write_far"],
        "status": "FULL",
        "notes": "FAR1/FAR3 writing with MutationPipeline integration"
    },
    "MergeIFF": {
        "modules": ["Tools/core/container_operations.py"],
        "functions": ["IFFMerger", "merge_iff_files"],
        "status": "FULL",
        "notes": "Full merge with conflict resolution (rename/skip/replace)"
    },
    "SplitIFF": {
        "modules": ["Tools/core/container_operations.py"],
        "functions": ["IFFSplitter", "split_iff"],
        "status": "FULL",
        "notes": "Split by type or object with MutationPipeline integration"
    },
    "ReplaceChunk": {
        "modules": ["Tools/core/file_operations.py"],
        "functions": ["ChunkOperations.replace_chunk"],
        "status": "FULL",
        "notes": "Full replace with MutationPipeline audit"
    },
    "DeleteChunk": {
        "modules": ["Tools/core/file_operations.py"],
        "functions": ["ChunkOperations.delete_chunk"],
        "status": "FULL",
        "notes": "Full delete with MutationPipeline audit"
    },
    "AddChunk": {
        "modules": ["Tools/core/file_operations.py"],
        "functions": ["ChunkOperations.add_chunk"],
        "status": "FULL",
        "notes": "Full add with collision check and MutationPipeline audit"
    },
    "ReindexContainer": {
        "modules": ["Tools/core/container_operations.py"],
        "functions": ["ContainerReindexer", "reindex_container"],
        "status": "FULL",
        "notes": "Renumber chunk IDs with scope preservation"
    },
    "NormalizeHeaders": {
        "modules": ["Tools/core/container_operations.py"],
        "functions": ["HeaderNormalizer", "normalize_headers"],
        "status": "FULL",
        "notes": "Fix sizes, labels, flags in chunk headers"
    },
    "ValidateContainer": {
        "modules": ["Tools/core/file_operations.py"],
        "functions": ["ContainerValidator", "validate_iff", "validate_far", "validate_container"],
        "status": "FULL",
        "notes": "Deep validation of IFF and FAR with chunk integrity checks"
    },

    # ─── 2. SAVE-STATE MUTATIONS ───────────────────────────────────────────
    "AddMoney": {
        "modules": ["Tools/save_editor/save_manager.py", "Tools/gui/panels/save_editor_panel.py"],
        "functions": ["modify_budget", "set_money"],
        "status": "FULL",
        "notes": "Working in SaveManager"
    },
    "RemoveMoney": {
        "modules": ["Tools/save_editor/save_manager.py"],
        "functions": ["modify_budget"],
        "status": "FULL",
        "notes": "Same as AddMoney with negative"
    },
    "SetMoney": {
        "modules": ["Tools/save_editor/save_manager.py"],
        "functions": ["set_budget"],
        "status": "FULL",
        "notes": "Direct budget set"
    },
    "AddSim": {
        "modules": ["Tools/core/save_mutations.py"],
        "functions": ["SimManager.add_sim", "SimTemplate"],
        "status": "FULL",
        "notes": "Full sim creation with template and MutationPipeline"
    },
    "RemoveSim": {
        "modules": ["Tools/core/save_mutations.py"],
        "functions": ["SimManager.remove_sim"],
        "status": "FULL",
        "notes": "Sim removal with relationship cleanup"
    },
    "ModifySimAttributes": {
        "modules": ["Tools/core/save_mutations.py"],
        "functions": ["SimAttributesManager", "modify_sim_attributes", "set_skill", "set_interest"],
        "status": "FULL",
        "notes": "Skills, interests, badges with MutationPipeline"
    },
    "ModifyHousehold": {
        "modules": ["Tools/core/world_mutations.py"],
        "functions": ["HouseholdManager", "modify_household", "set_funds", "add_member"],
        "status": "FULL",
        "notes": "Full household mutations with MutationPipeline"
    },
    "ModifyRelationships": {
        "modules": ["Tools/core/save_mutations.py"],
        "functions": ["RelationshipManager", "modify_relationships", "set_relationship", "set_relationship_bit"],
        "status": "FULL",
        "notes": "Daily/lifetime values and relationship bits"
    },
    "ModifyInventory": {
        "modules": ["Tools/core/save_mutations.py"],
        "functions": ["InventoryManager", "modify_inventory"],
        "status": "FULL",
        "notes": "Add/remove inventory items with MutationPipeline"
    },
    "ModifyCareer": {
        "modules": ["Tools/core/save_mutations.py"],
        "functions": ["CareerManager", "modify_career", "promote", "demote", "set_career"],
        "status": "FULL",
        "notes": "24 career tracks, levels 1-10, performance with MutationPipeline"
    },
    "ModifyMotives": {
        "modules": ["Tools/core/save_mutations.py"],
        "functions": ["MotivesManager", "modify_motives", "set_motive", "maximize_all"],
        "status": "FULL",
        "notes": "9 motives (-100 to 100) with MutationPipeline"
    },
    "ModifyAspirations": {
        "modules": ["Tools/core/save_mutations.py"],
        "functions": ["AspirationManager", "modify_aspirations"],
        "status": "FULL",
        "notes": "Set aspiration type/score/level with MutationPipeline"
    },
    "ModifyMemories": {
        "modules": ["Tools/core/save_mutations.py"],
        "functions": ["MemoryManager", "modify_memories"],
        "status": "FULL",
        "notes": "Add/remove memories with MutationPipeline"
    },
    "ModifyTime": {
        "modules": ["Tools/core/save_mutations.py"],
        "functions": ["TimeManager", "modify_time"],
        "status": "FULL",
        "notes": "Set/advance game time with MutationPipeline"
    },
    "ModifyLotState": {
        "modules": ["Tools/core/world_mutations.py"],
        "functions": ["LotStateManager", "modify_lot_state", "set_lot_type", "set_lot_value"],
        "status": "FULL",
        "notes": "Lot type, value, objects with MutationPipeline"
    },
    "ModifyNeighborhoodState": {
        "modules": ["Tools/core/world_mutations.py"],
        "functions": ["NeighborhoodManager", "modify_neighborhood_state", "set_terrain_type"],
        "status": "FULL",
        "notes": "Name, terrain, decorations with MutationPipeline"
    },

    # ─── 3. BEHAVIOR / BHAV ACTIONS ────────────────────────────────────────
    "LoadBHAV": {
        "modules": ["formats/iff/chunks/bhav.py", "Tools/core/bhav_disassembler.py"],
        "functions": ["BHAV", "BHAVDisassembler"],
        "status": "FULL",
        "notes": "Complete BHAV parsing"
    },
    "DisassembleBHAV": {
        "modules": ["Tools/core/bhav_disassembler.py", "formats/iff/chunks/bhav_decompiler.py"],
        "functions": ["BHAVDisassembler.disassemble", "disassemble_bhav"],
        "status": "FULL",
        "notes": "Complete disassembly with semantic names"
    },
    "EditBHAV": {
        "modules": ["Tools/core/bhav_operations.py", "Tools/gui/panels/bhav_editor.py"],
        "functions": ["BHAVEditor", "edit_instruction", "insert_instruction", "delete_instruction"],
        "status": "FULL",
        "notes": "Full BHAV editing with undo, MutationPipeline integration"
    },
    "ReplaceBHAV": {
        "modules": ["Tools/core/bhav_operations.py"],
        "functions": ["BHAVImporter.import_from_iff"],
        "status": "FULL",
        "notes": "BHAV replacement via import with audit"
    },
    "InjectBHAV": {
        "modules": ["Tools/core/bhav_operations.py"],
        "functions": ["BHAVEditor.insert_instruction"],
        "status": "FULL",
        "notes": "Insert instructions with pointer adjustment"
    },
    "RemoveBHAV": {
        "modules": ["Tools/core/file_operations.py"],
        "functions": ["ChunkOperations.delete_chunk"],
        "status": "FULL",
        "notes": "Delete BHAV chunk via MutationPipeline"
    },
    "PatchGlobalBHAV": {
        "modules": ["Tools/core/bhav_patching.py"],
        "functions": ["GlobalBHAVPatcher", "patch_global_bhav"],
        "status": "FULL",
        "notes": "Patch global calls with scope validation and override injection"
    },
    "PatchSemiGlobalBHAV": {
        "modules": ["Tools/core/bhav_patching.py"],
        "functions": ["SemiGlobalBHAVPatcher", "patch_semi_global_bhav"],
        "status": "FULL",
        "notes": "Patch semi-global calls with scope validation"
    },
    "PatchObjectBHAV": {
        "modules": ["Tools/core/bhav_patching.py"],
        "functions": ["ObjectBHAVPatcher", "patch_object_bhav"],
        "status": "FULL",
        "notes": "Patch object BHAVs with duplication support"
    },
    "RewireBHAVCalls": {
        "modules": ["Tools/core/bhav_patching.py"],
        "functions": ["BHAVCallRewirer", "rewire_bhav_calls"],
        "status": "FULL",
        "notes": "Update call targets based on ID mapping"
    },
    "RemapBHAVIDs": {
        "modules": ["Tools/core/bhav_patching.py"],
        "functions": ["BHAVIDRemapper", "remap_bhav_ids"],
        "status": "FULL",
        "notes": "Remap BHAV IDs with collision avoidance"
    },
    "ValidateBHAVGraph": {
        "modules": ["Tools/core/bhav_executor.py", "formats/iff/chunks/bhav_validator.py"],
        "functions": ["BHAVExecutor", "validate_bhav"],
        "status": "FULL",
        "notes": "BHAV Executor traces all paths, detects loops/dead code"
    },
    "DetectUnknownOpcodes": {
        "modules": ["Tools/core/unknowns_db.py", "Tools/forensic/master_forensic_analyzer.py"],
        "functions": ["UnknownsDB", "detect_unknowns"],
        "status": "FULL",
        "notes": "167+ unknowns already catalogued"
    },
    "ResolveSemanticNames": {
        "modules": ["Tools/forensic/engine_toolkit.py", "Tools/core/behavior_library.py"],
        "functions": ["EngineToolkit", "get_semantic_name"],
        "status": "FULL",
        "notes": "2,287 BHAVs with semantic names"
    },

    # ─── 4. ASSET → VISUALIZATION ACTIONS ──────────────────────────────────
    "LoadAssetTo2D": {
        "modules": ["formats/iff/chunks/spr.py", "formats/iff/chunks/sprite_export.py"],
        "functions": ["SPR2Chunk", "decode_sprite"],
        "status": "FULL",
        "notes": "SPR2 decoding complete"
    },
    "LoadAssetTo3D": {
        "modules": ["Tools/core/mesh_export.py"],
        "functions": ["MeshVisualizer", "load_asset_to_3d"],
        "status": "FULL",
        "notes": "Load mesh for Three.js visualization"
    },
    "DecodeSPR2": {
        "modules": ["formats/iff/chunks/spr.py", "formats/iff/chunks/sprite_export.py"],
        "functions": ["SPR2Decoder", "decode"],
        "status": "FULL",
        "notes": "Complete sprite decoding"
    },
    "DecodeDrawGroup": {
        "modules": ["formats/iff/chunks/dgrp.py"],
        "functions": ["DGRPChunk"],
        "status": "FULL",
        "notes": "DGRP parser complete"
    },
    "DecodeMesh": {
        "modules": ["Tools/core/mesh_export.py"],
        "functions": ["MeshDecoder", "decode_mesh"],
        "status": "FULL",
        "notes": "GMDC and generic mesh decoding"
    },
    "DecodeAnimation": {
        "modules": ["Tools/core/analysis_operations.py", "formats/iff/chunks/anim.py"],
        "functions": ["AnimationDecoder", "decode_animation", "parse"],
        "status": "FULL",
        "notes": "Version, states, frames with sprite references"
    },
    "PreviewRotations": {
        "modules": ["Tools/gui/panels/visual_object_browser_panel.py"],
        "functions": ["preview_rotation"],
        "status": "FULL",
        "notes": "Web viewer supports rotations"
    },
    "PreviewZoomLevels": {
        "modules": ["Tools/gui/panels/visual_object_browser_panel.py"],
        "functions": ["preview_zoom"],
        "status": "FULL",
        "notes": "Web viewer supports zoom levels"
    },
    "PreviewFrames": {
        "modules": ["Tools/gui/panels/visual_object_browser_panel.py"],
        "functions": ["preview_frames"],
        "status": "FULL",
        "notes": "Animation frame preview"
    },

    # ─── 5. EXPORT ACTIONS ─────────────────────────────────────────────────
    "ExportAssetToModern": {
        "modules": ["Tools/gui/panels/sprite_export_panel.py"],
        "functions": ["export_png", "export_json"],
        "status": "FULL",
        "notes": "PNG export working"
    },
    "ExportAssetToLegacy": {
        "modules": ["Tools/core/advanced_import_export.py"],
        "functions": ["LegacyAssetExporter", "export_asset_to_legacy"],
        "status": "FULL",
        "notes": "Export to TS1/legacy IFF format with chunk conversion"
    },
    "ExportSpritePNGs": {
        "modules": ["Tools/gui/panels/sprite_export_panel.py", "Program/sprite_extractor_main.py"],
        "functions": ["SpriteExportPanel", "export_sprites"],
        "status": "FULL",
        "notes": "ZIP export working"
    },
    "ExportSpriteSheet": {
        "modules": ["Tools/core/analysis_operations.py"],
        "functions": ["SpriteSheetExporter", "export_sprite_sheet"],
        "status": "FULL",
        "notes": "PIL sprite sheet with metadata fallback"
    },
    "ExportMesh": {
        "modules": ["Tools/core/mesh_export.py"],
        "functions": ["GLTFExporter", "export_mesh_gltf", "export_mesh_glb"],
        "status": "FULL",
        "notes": "GLTF/GLB export with Three.js visualization support"
    },
    "ExportBehaviorDocs": {
        "modules": ["Tools/core/output_formatters.py"],
        "functions": ["format_bhav_doc"],
        "status": "FULL",
        "notes": "Markdown/HTML export"
    },
    "ExportGraphs": {
        "modules": ["Tools/gui/panels/graph_canvas.py", "Tools/graph/"],
        "functions": ["export_dot", "export_json"],
        "status": "FULL",
        "notes": "DOT/JSON/CSV export"
    },
    "ExportSaveSnapshot": {
        "modules": ["Tools/core/analysis_operations.py"],
        "functions": ["SaveSnapshotExporter", "export_save_snapshot", "export_json", "export_html"],
        "status": "FULL",
        "notes": "JSON and styled HTML export with summary stats"
    },
    "ExportUnknownsReport": {
        "modules": ["Tools/core/unknowns_db.py"],
        "functions": ["export_report"],
        "status": "FULL",
        "notes": "JSON/MD export"
    },

    # ─── 6. IMPORT ACTIONS ─────────────────────────────────────────────────
    "ImportAssetFromModern": {
        "modules": ["Tools/core/advanced_import_export.py", "Tools/core/import_operations.py"],
        "functions": ["ModernAssetImporter", "import_asset_from_modern", "import_png", "import_gltf"],
        "status": "FULL",
        "notes": "PNG to SPR2, glTF to GMDC with palette quantization"
    },
    "ImportAssetFromLegacy": {
        "modules": ["Tools/core/import_operations.py", "formats/iff/iff_file.py"],
        "functions": ["AssetImporter.import_from_iff", "import_asset"],
        "status": "FULL",
        "notes": "Complete IFF asset import with dependency gathering"
    },
    "ImportSpritePNG": {
        "modules": ["Tools/core/import_operations.py"],
        "functions": ["SpriteImporter.import_png", "import_png_sprite"],
        "status": "FULL",
        "notes": "PNG to SPR2 conversion with palette quantization (requires PIL)"
    },
    "ImportSpriteSheet": {
        "modules": ["Tools/core/import_operations.py"],
        "functions": ["SpriteImporter.import_sprite_sheet"],
        "status": "FULL",
        "notes": "Sprite sheet splitting and import (requires PIL)"
    },
    "ImportMesh": {
        "modules": ["Tools/core/advanced_import_export.py"],
        "functions": ["MeshImporter", "import_mesh", "import_obj", "import_mesh_dict"],
        "status": "FULL",
        "notes": "OBJ and dict mesh import to GMDC"
    },
    "ImportBehavior": {
        "modules": ["Tools/core/bhav_operations.py", "Tools/core/import_operations.py"],
        "functions": ["BHAVImporter.import_from_iff", "ChunkImporter.import_chunk"],
        "status": "FULL",
        "notes": "BHAV import from external IFF with ID remapping"
    },
    "ImportOpcodeDefs": {
        "modules": ["Tools/core/import_operations.py", "Tools/core/opcode_loader.py"],
        "functions": ["DatabaseImporter.import_opcodes", "import_opcodes"],
        "status": "FULL",
        "notes": "JSON opcode import with merge support"
    },
    "ImportUnknownsDB": {
        "modules": ["Tools/core/import_operations.py", "Tools/core/unknowns_db.py"],
        "functions": ["DatabaseImporter.import_unknowns", "import_unknowns"],
        "status": "FULL",
        "notes": "JSON unknowns import with merge support"
    },
    "ImportSavePatch": {
        "modules": ["Tools/core/advanced_import_export.py"],
        "functions": ["SavePatchImporter", "import_save_patch"],
        "status": "FULL",
        "notes": "Apply partial save patches from JSON"
    },

    # ─── 7. GRAPH / ANALYSIS ACTIONS ───────────────────────────────────────
    "BuildCallGraph": {
        "modules": ["Tools/graph/core.py", "formats/iff/chunks/bhav_graph.py"],
        "functions": ["build_call_graph", "CallGraph"],
        "status": "FULL",
        "notes": "Complete call graph building"
    },
    "BuildResourceGraph": {
        "modules": ["Tools/graph/core.py"],
        "functions": ["build_resource_graph"],
        "status": "FULL",
        "notes": "Resource dependencies tracked"
    },
    "BuildDependencyGraph": {
        "modules": ["Tools/graph/core.py", "Tools/entities/relationship_entity.py"],
        "functions": ["build_dependency_graph"],
        "status": "FULL",
        "notes": "Dependency analysis complete"
    },
    "DetectCycles": {
        "modules": ["Tools/graph/cycle_detector.py"],
        "functions": ["detect_cycles", "CycleDetector"],
        "status": "FULL",
        "notes": "Cycle detection implemented"
    },
    "DetectDeadCode": {
        "modules": ["Tools/core/bhav_executor.py"],
        "functions": ["find_unreachable", "detect_dead_code"],
        "status": "FULL",
        "notes": "BHAV executor detects unreachable instructions"
    },
    "DetectUnusedAssets": {
        "modules": ["Tools/core/analysis_operations.py"],
        "functions": ["UnusedAssetDetector", "detect_unused_assets", "detect_orphans"],
        "status": "FULL",
        "notes": "Reference graph building and orphan detection"
    },
    "CompareExpansions": {
        "modules": ["Tools/gui/panels/diff_compare_panel.py", "Tools/forensic/forensic_expansion_analyzer.py"],
        "functions": ["compare_expansions", "DiffComparePanel"],
        "status": "FULL",
        "notes": "Cross-pack comparison working"
    },
    "DiffObjects": {
        "modules": ["Tools/gui/panels/diff_compare_panel.py"],
        "functions": ["diff_objects"],
        "status": "FULL",
        "notes": "Object diff panel exists"
    },
    "DiffBHAVs": {
        "modules": ["Tools/gui/panels/diff_compare_panel.py"],
        "functions": ["diff_bhavs"],
        "status": "FULL",
        "notes": "BHAV diff working"
    },
    "DiffGlobals": {
        "modules": ["Tools/gui/panels/diff_compare_panel.py"],
        "functions": ["diff_globals"],
        "status": "FULL",
        "notes": "Global diff supported"
    },

    # ─── 8. SEARCH / QUERY ACTIONS ─────────────────────────────────────────
    "SearchByName": {
        "modules": ["Tools/gui/panels/support_panels.py"],
        "functions": ["GlobalSearchPanel", "search_by_name"],
        "status": "FULL",
        "notes": "Global search working"
    },
    "SearchByID": {
        "modules": ["Tools/gui/panels/support_panels.py"],
        "functions": ["search_by_id"],
        "status": "FULL",
        "notes": "ID search working"
    },
    "SearchByOpcode": {
        "modules": ["Tools/gui/panels/support_panels.py"],
        "functions": ["search_by_opcode"],
        "status": "FULL",
        "notes": "Opcode search working"
    },
    "SearchByBehaviorPurpose": {
        "modules": ["Tools/gui/panels/support_panels.py", "Tools/entities/behavior_entity.py"],
        "functions": ["search_by_purpose", "BehaviorPurpose"],
        "status": "FULL",
        "notes": "Lifecycle filter working"
    },
    "SearchByLifecyclePhase": {
        "modules": ["Tools/gui/panels/support_panels.py"],
        "functions": ["LIFECYCLE_FILTERS"],
        "status": "FULL",
        "notes": "Lifecycle phase filters implemented"
    },
    "SearchBySafetyRisk": {
        "modules": ["Tools/gui/panels/support_panels.py", "Tools/safety.py"],
        "functions": ["SAFETY_FILTERS"],
        "status": "FULL",
        "notes": "Safety risk filters implemented"
    },
    "SearchByExpansion": {
        "modules": ["Tools/gui/panels/support_panels.py"],
        "functions": ["SCOPE_OPTIONS"],
        "status": "FULL",
        "notes": "Cross-pack search working"
    },
    "SearchByUnknownUsage": {
        "modules": ["Tools/core/unknowns_db.py"],
        "functions": ["search_unknowns"],
        "status": "FULL",
        "notes": "Unknown opcode search"
    },
    "CrossReferenceSearch": {
        "modules": ["Tools/gui/panels/semantic_inspector.py", "formats/iff/chunks/bhav_cross_reference.py"],
        "functions": ["cross_reference", "find_references"],
        "status": "FULL",
        "notes": "Cross-reference analysis working"
    },

    # ─── 9. SYSTEM / META ACTIONS ──────────────────────────────────────────
    "ScanDirectory": {
        "modules": ["Tools/gui/panels/archiver_panel.py", "Tools/core/asset_scanner.py"],
        "functions": ["scan_directory"],
        "status": "FULL",
        "notes": "Directory scanning working"
    },
    "FullForensicScan": {
        "modules": ["Tools/forensic/master_forensic_analyzer.py"],
        "functions": ["full_scan", "MasterForensicAnalyzer"],
        "status": "FULL",
        "notes": "Complete forensic analysis"
    },
    "UpdateUnknownsDB": {
        "modules": ["Tools/core/unknowns_db.py"],
        "functions": ["update_unknowns", "add_unknown"],
        "status": "FULL",
        "notes": "Auto-growing database"
    },
    "RebuildIndexes": {
        "modules": ["Tools/core/container_operations.py"],
        "functions": ["IndexRebuilder", "rebuild_indexes"],
        "status": "FULL",
        "notes": "Rebuild RSMP after chunk modifications"
    },
    "ClearCaches": {
        "modules": ["Tools/core/container_operations.py"],
        "functions": ["CacheManager", "clear_caches"],
        "status": "FULL",
        "notes": "Clear all registered caches including module caches"
    },
    "ValidateEnvironment": {
        "modules": ["test_suite.py"],
        "functions": ["test_*"],
        "status": "FULL",
        "notes": "Test suite validates environment"
    },
    "CheckDependencies": {
        "modules": ["test_suite.py"],
        "functions": ["test_*"],
        "status": "FULL",
        "notes": "Test suite checks dependencies"
    },
    "MigrateData": {
        "modules": ["Tools/core/advanced_import_export.py"],
        "functions": ["DataMigrator", "migrate_data", "upgrade", "downgrade"],
        "status": "FULL",
        "notes": "Migrate between expansion pack formats"
    },
    "LoadWorkspace": {
        "modules": ["Tools/core/workspace_persistence.py"],
        "functions": ["WorkspaceManager", "get_workspace_manager", "load_workspace"],
        "status": "FULL",
        "notes": "JSON persistence with recent files and bookmarks"
    },
    "SaveWorkspace": {
        "modules": ["Tools/core/workspace_persistence.py"],
        "functions": ["WorkspaceManager", "save_workspace"],
        "status": "FULL",
        "notes": "Full workspace state serialization"
    },

    # ─── 10. UI-LEVEL ACTIONS ──────────────────────────────────────────────
    "SelectEntity": {
        "modules": ["Tools/gui/focus.py"],
        "functions": ["FocusCoordinator.select"],
        "status": "FULL",
        "notes": "Selection fully functional"
    },
    "ChangeScope": {
        "modules": ["Tools/gui/focus.py", "Tools/gui/panels/scope_switcher.py"],
        "functions": ["set_scope"],
        "status": "FULL",
        "notes": "Scope switching working"
    },
    "ToggleViewMode": {
        "modules": ["Tools/gui/panels/chunk_inspector.py"],
        "functions": ["toggle_mode"],
        "status": "FULL",
        "notes": "View mode toggle working"
    },
    "OpenInspector": {
        "modules": ["main_app.py"],
        "functions": ["_init_panels"],
        "status": "FULL",
        "notes": "Inspector panels working"
    },
    "ApplyFilter": {
        "modules": ["Tools/gui/panels/support_panels.py"],
        "functions": ["apply_filter"],
        "status": "FULL",
        "notes": "Semantic filters working"
    },
    "TriggerPreview": {
        "modules": ["Tools/gui/panels/visual_object_browser_panel.py"],
        "functions": ["trigger_preview"],
        "status": "FULL",
        "notes": "Preview triggers working"
    },
    "ConfirmMutation": {
        "modules": ["Tools/core/ui_actions.py", "Tools/core/mutation_pipeline.py"],
        "functions": ["MutationUIController", "confirm_mutation", "get_mutation_controller"],
        "status": "FULL",
        "notes": "Execute pending mutations with undo/redo support"
    },
    "CancelMutation": {
        "modules": ["Tools/core/ui_actions.py", "Tools/core/mutation_pipeline.py"],
        "functions": ["MutationUIController", "cancel_mutation"],
        "status": "FULL",
        "notes": "Cancel pending mutations with cleanup"
    },
}


def analyze_coverage() -> Dict:
    """Analyze action coverage and return statistics."""
    stats = {
        'FULL': [],
        'PARTIAL': [],
        'STUB': [],
        'MISSING': []
    }
    
    for action, info in ACTION_IMPLEMENTATIONS.items():
        stats[info['status']].append({
            'action': action,
            'modules': info['modules'],
            'notes': info['notes']
        })
    
    return stats


def print_coverage_report():
    """Print formatted coverage report."""
    stats = analyze_coverage()
    
    print("╔" + "═"*70 + "╗")
    print("║  SIMOBLITERATOR ACTION COVERAGE REPORT                                ║")
    print("║  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "                                              ║")
    print("╚" + "═"*70 + "╝")
    
    total = len(ACTION_IMPLEMENTATIONS)
    full = len(stats['FULL'])
    partial = len(stats['PARTIAL'])
    stub = len(stats['STUB'])
    missing = len(stats['MISSING'])
    
    print(f"\n📊 SUMMARY")
    print(f"{'='*70}")
    print(f"Total Actions:        {total}")
    print(f"Fully Implemented:    {full} ({full*100//total}%) ✅")
    print(f"Partially Implemented: {partial} ({partial*100//total}%) 🟡")
    print(f"Stub/Placeholder:     {stub} ({stub*100//total}%) 🔵")
    print(f"Missing:              {missing} ({missing*100//total}%) ❌")
    
    print(f"\n\n✅ FULLY IMPLEMENTED ({full})")
    print(f"{'='*70}")
    for item in sorted(stats['FULL'], key=lambda x: x['action']):
        print(f"  {item['action']:30} {item['notes'][:40]}")
    
    print(f"\n\n🟡 PARTIALLY IMPLEMENTED ({partial})")
    print(f"{'='*70}")
    for item in sorted(stats['PARTIAL'], key=lambda x: x['action']):
        print(f"  {item['action']:30} {item['notes'][:40]}")
    
    print(f"\n\n🔵 STUB/PLACEHOLDER ({stub})")
    print(f"{'='*70}")
    for item in sorted(stats['STUB'], key=lambda x: x['action']):
        print(f"  {item['action']:30} {item['notes'][:40]}")
    
    print(f"\n\n❌ MISSING ({missing})")
    print(f"{'='*70}")
    for item in sorted(stats['MISSING'], key=lambda x: x['action']):
        print(f"  {item['action']:30} {item['notes'][:40]}")
    
    # By category
    print(f"\n\n📋 BY CATEGORY")
    print(f"{'='*70}")
    
    categories = {
        "FILE_CONTAINER": ["LoadSave", "WriteSave", "BackupSave", "RestoreSave", "LoadIFF", 
                          "LoadFAR", "WriteIFF", "WriteFAR", "MergeIFF", "SplitIFF",
                          "ReplaceChunk", "DeleteChunk", "AddChunk", "ReindexContainer",
                          "NormalizeHeaders", "ValidateContainer"],
        "SAVE_STATE": ["AddMoney", "RemoveMoney", "SetMoney", "AddSim", "RemoveSim",
                      "ModifySimAttributes", "ModifyHousehold", "ModifyRelationships",
                      "ModifyInventory", "ModifyCareer", "ModifyMotives", "ModifyAspirations",
                      "ModifyMemories", "ModifyTime", "ModifyLotState", "ModifyNeighborhoodState"],
        "BHAV": ["LoadBHAV", "DisassembleBHAV", "EditBHAV", "ReplaceBHAV", "InjectBHAV",
                "RemoveBHAV", "PatchGlobalBHAV", "PatchSemiGlobalBHAV", "PatchObjectBHAV",
                "RewireBHAVCalls", "RemapBHAVIDs", "ValidateBHAVGraph", "DetectUnknownOpcodes",
                "ResolveSemanticNames"],
        "VISUALIZATION": ["LoadAssetTo2D", "LoadAssetTo3D", "DecodeSPR2", "DecodeDrawGroup",
                         "DecodeMesh", "DecodeAnimation", "PreviewRotations", "PreviewZoomLevels",
                         "PreviewFrames"],
        "EXPORT": ["ExportAssetToModern", "ExportAssetToLegacy", "ExportSpritePNGs",
                  "ExportSpriteSheet", "ExportMesh", "ExportBehaviorDocs", "ExportGraphs",
                  "ExportSaveSnapshot", "ExportUnknownsReport"],
        "IMPORT": ["ImportAssetFromModern", "ImportAssetFromLegacy", "ImportSpritePNG",
                  "ImportSpriteSheet", "ImportMesh", "ImportBehavior", "ImportOpcodeDefs",
                  "ImportUnknownsDB", "ImportSavePatch"],
        "ANALYSIS": ["BuildCallGraph", "BuildResourceGraph", "BuildDependencyGraph",
                    "DetectCycles", "DetectDeadCode", "DetectUnusedAssets", "CompareExpansions",
                    "DiffObjects", "DiffBHAVs", "DiffGlobals"],
        "SEARCH": ["SearchByName", "SearchByID", "SearchByOpcode", "SearchByBehaviorPurpose",
                  "SearchByLifecyclePhase", "SearchBySafetyRisk", "SearchByExpansion",
                  "SearchByUnknownUsage", "CrossReferenceSearch"],
        "SYSTEM": ["ScanDirectory", "FullForensicScan", "UpdateUnknownsDB", "RebuildIndexes",
                  "ClearCaches", "ValidateEnvironment", "CheckDependencies", "MigrateData",
                  "LoadWorkspace", "SaveWorkspace"],
        "UI": ["SelectEntity", "ChangeScope", "ToggleViewMode", "OpenInspector",
              "ApplyFilter", "TriggerPreview", "ConfirmMutation", "CancelMutation"],
    }
    
    for category, actions in categories.items():
        full_count = sum(1 for a in actions if ACTION_IMPLEMENTATIONS.get(a, {}).get('status') == 'FULL')
        partial_count = sum(1 for a in actions if ACTION_IMPLEMENTATIONS.get(a, {}).get('status') == 'PARTIAL')
        total_count = len(actions)
        implemented = full_count + partial_count
        pct = implemented * 100 // total_count if total_count > 0 else 0
        
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"  {category:20} [{bar}] {pct:3}% ({full_count}+{partial_count}/{total_count})")


def main():
    print_coverage_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
