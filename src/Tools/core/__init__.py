"""
Core analysis modules for SimObliterator.

This package contains the fundamental tools for BHAV analysis:
- bhav_disassembler: Decode SimAntics bytecode
- bhav_executor: Trace execution paths
- bhav_opcodes: Opcode reference data
- behavior_profiler: Generate behavior profiles
- behavior_classifier: Classify behaviors (ROLE/ACTION/GUARD/UTILITY)
- behavior_trigger_extractor: Extract lifecycle bindings
- behavior_relationship_extractor: Extract behavior relationships
- behavior_library_generator: Generate library documentation
- object_dominance_analyzer: Analyze per-object lifecycle
- trigger_role_graph: Build trigger->ROLE graphs
- output_formatters: Format analysis output
- forensic_module: Pattern analysis for reverse engineering
- iff_reader: Minimal IFF file reader

MUTATION SYSTEM (Write Barrier Layer):
- action_registry: Canonical action definitions (110 actions)
- mutation_pipeline: Write barrier with validation/audit
- provenance: Confidence signaling for inferred data
- file_operations: IFF/FAR/DBPF read/write operations
- bhav_operations: BHAV editing through pipeline
- import_operations: External resource import
"""

# Allow direct imports from core package
from .bhav_disassembler import BHAVDisassembler, BHAVAnalyzer
from .bhav_executor import BHAVExecutor, BHAVExecutionAnalyzer
from .bhav_opcodes import get_opcode_info, PRIMITIVE_INSTRUCTIONS
from .behavior_profiler import BehaviorProfiler, BehaviorProfile, BehaviorScope, EntryPointType, Reachability
from .behavior_classifier import BehaviorClassifier, BehaviorClass, ClassificationResult
from .behavior_trigger_extractor import TriggerExtractor, TriggerType
from .behavior_relationship_extractor import RelationshipExtractor, build_relationship_metrics
from .behavior_library_generator import BehaviorLibraryGenerator
from .object_dominance_analyzer import ObjectDominanceAnalyzer, ObjectDominanceMap
from .trigger_role_graph import TriggerRoleGraphBuilder, TriggerRoleGraph
from .output_formatters import get_formatter, FormatterContext
from .forensic_module import ForensicAnalyzer, OpcodeProfile, generate_forensic_analysis
from .iff_reader import read_iff_file, IFFChunk

# Mutation system imports
from .action_registry import (
    ActionRegistry, ActionDefinition, ActionCategory,
    Mutability, ActionScope, RiskLevel,
    validate_action, is_registered_action, get_action_info
)
from .mutation_pipeline import (
    MutationPipeline, MutationMode, MutationRequest, MutationDiff,
    MutationResult, MutationAudit, get_pipeline, propose_change
)
from .provenance import ProvenanceRegistry, ConfidenceLevel, ProvenanceSource, Provenance

# File operations
from .file_operations import (
    IFFWriter, ChunkOperations, BackupManager, ArchiveExtractor,
    ContainerValidator, FileOpResult,
    backup_file, restore_file, validate_container, extract_archive,
    get_backup_manager
)

# BHAV operations
from .bhav_operations import (
    BHAVEditor, BHAVSerializer, BHAVValidator, BHAVImporter,
    BHAVOpResult,
    validate_bhav, serialize_bhav, create_bhav_editor
)

# Import operations
from .import_operations import (
    ChunkImporter, SpriteImporter, DatabaseImporter, AssetImporter,
    ImportResult,
    import_chunk, import_png_sprite, import_asset,
    import_opcodes, import_unknowns
)

# Container operations
from .container_operations import (
    CacheManager, clear_caches,
    HeaderNormalizer, normalize_headers,
    IndexRebuilder, rebuild_indexes,
    ContainerReindexer, reindex_container,
    IFFSplitter, split_iff,
    IFFMerger, merge_iff_files,
    FARWriter, write_far,
    ContainerOpResult
)

# Save mutations
from .save_mutations import (
    SimManager, SimTemplate, 
    TimeManager, modify_time,
    InventoryManager, modify_inventory,
    AspirationManager, modify_aspirations,
    MemoryManager, modify_memories,
    CareerManager, modify_career,
    MotivesManager, modify_motives,
    SimAttributesManager, modify_sim_attributes,
    RelationshipManager, modify_relationships,
    SaveMutationResult
)

# World mutations
from .world_mutations import (
    HouseholdManager, modify_household,
    LotStateManager, modify_lot_state,
    NeighborhoodManager, modify_neighborhood_state
)

# Workspace persistence
from .workspace_persistence import (
    WorkspaceManager, WorkspaceState,
    get_workspace_manager
)

# UI actions
from .ui_actions import (
    MutationTracker, MutationUIController, PendingMutation,
    get_mutation_controller
)

# Analysis operations
from .analysis_operations import (
    AnimationDecoder, decode_animation,
    UnusedAssetDetector, detect_unused_assets,
    SaveSnapshotExporter, export_save_snapshot,
    SpriteSheetExporter, export_sprite_sheet,
    AnalysisResult
)

# Advanced import/export
from .advanced_import_export import (
    ModernAssetImporter, import_asset_from_modern,
    MeshImporter, import_mesh,
    LegacyAssetExporter, export_asset_to_legacy,
    SavePatchImporter, import_save_patch,
    DataMigrator, migrate_data,
    AdvancedImportResult
)

# BHAV patching
from .bhav_patching import (
    BHAVScope, BHAVCallOpcodes,
    BHAVIDRemapper, remap_bhav_ids,
    BHAVCallRewirer, rewire_bhav_calls,
    GlobalBHAVPatcher, patch_global_bhav,
    SemiGlobalBHAVPatcher, patch_semi_global_bhav,
    ObjectBHAVPatcher, patch_object_bhav,
    BHAVPatchResult
)

# Mesh export
from .mesh_export import (
    Vertex, Face, Mesh,
    MeshDecoder, decode_mesh,
    GLTFExporter, export_mesh_gltf, export_mesh_glb,
    ChunkMeshExporter, export_chunk_mesh,
    MeshVisualizer, load_asset_to_3d,
    MeshExportResult
)

__all__ = [
    # BHAV Analysis
    'BHAVDisassembler', 'BHAVAnalyzer',
    'BHAVExecutor', 'BHAVExecutionAnalyzer',
    'get_opcode_info', 'PRIMITIVE_INSTRUCTIONS',
    'BehaviorProfiler', 'BehaviorProfile', 'BehaviorScope', 'EntryPointType', 'Reachability',
    'BehaviorClassifier', 'BehaviorClass', 'ClassificationResult',
    'TriggerExtractor', 'TriggerType',
    'RelationshipExtractor', 'build_relationship_metrics',
    'BehaviorLibraryGenerator',
    'ObjectDominanceAnalyzer', 'ObjectDominanceMap',
    'TriggerRoleGraphBuilder', 'TriggerRoleGraph',
    'get_formatter', 'FormatterContext',
    'ForensicAnalyzer', 'OpcodeProfile', 'generate_forensic_analysis',
    'read_iff_file', 'IFFChunk',
    
    # Action Registry
    'ActionRegistry', 'ActionDefinition', 'ActionCategory',
    'Mutability', 'ActionScope', 'RiskLevel',
    'validate_action', 'is_registered_action', 'get_action_info',
    
    # Mutation Pipeline
    'MutationPipeline', 'MutationMode', 'MutationRequest', 'MutationDiff',
    'MutationResult', 'MutationAudit', 'get_pipeline', 'propose_change',
    
    # Provenance
    'ProvenanceRegistry', 'ConfidenceLevel', 'ProvenanceSource', 'Provenance',
    
    # File Operations
    'IFFWriter', 'ChunkOperations', 'BackupManager', 'ArchiveExtractor',
    'ContainerValidator', 'FileOpResult',
    'backup_file', 'restore_file', 'validate_container', 'extract_archive',
    'get_backup_manager',
    
    # BHAV Operations
    'BHAVEditor', 'BHAVSerializer', 'BHAVValidator', 'BHAVImporter',
    'BHAVOpResult',
    'validate_bhav', 'serialize_bhav', 'create_bhav_editor',
    
    # Import Operations
    'ChunkImporter', 'SpriteImporter', 'DatabaseImporter', 'AssetImporter',
    'ImportResult',
    'import_chunk', 'import_png_sprite', 'import_asset',
    'import_opcodes', 'import_unknowns',
    
    # Container Operations
    'CacheManager', 'clear_caches',
    'HeaderNormalizer', 'normalize_headers',
    'IndexRebuilder', 'rebuild_indexes',
    'ContainerReindexer', 'reindex_container',
    'IFFSplitter', 'split_iff',
    'IFFMerger', 'merge_iff_files',
    'FARWriter', 'write_far',
    'ContainerOpResult',
    
    # Save Mutations
    'SimManager', 'SimTemplate',
    'TimeManager', 'modify_time',
    'InventoryManager', 'modify_inventory',
    'AspirationManager', 'modify_aspirations',
    'MemoryManager', 'modify_memories',
    'CareerManager', 'modify_career',
    'MotivesManager', 'modify_motives',
    'SimAttributesManager', 'modify_sim_attributes',
    'RelationshipManager', 'modify_relationships',
    'SaveMutationResult',
    
    # World Mutations
    'HouseholdManager', 'modify_household',
    'LotStateManager', 'modify_lot_state',
    'NeighborhoodManager', 'modify_neighborhood_state',
    
    # Workspace Persistence
    'WorkspaceManager', 'WorkspaceState', 'get_workspace_manager',
    
    # UI Actions
    'MutationTracker', 'MutationUIController', 'PendingMutation',
    'get_mutation_controller',
    
    # Analysis Operations
    'AnimationDecoder', 'decode_animation',
    'UnusedAssetDetector', 'detect_unused_assets',
    'SaveSnapshotExporter', 'export_save_snapshot',
    'SpriteSheetExporter', 'export_sprite_sheet',
    'AnalysisResult',
    
    # Advanced Import/Export
    'ModernAssetImporter', 'import_asset_from_modern',
    'MeshImporter', 'import_mesh',
    'LegacyAssetExporter', 'export_asset_to_legacy',
    'SavePatchImporter', 'import_save_patch',
    'DataMigrator', 'migrate_data',
    'AdvancedImportResult',
    
    # BHAV Patching
    'BHAVScope', 'BHAVCallOpcodes',
    'BHAVIDRemapper', 'remap_bhav_ids',
    'BHAVCallRewirer', 'rewire_bhav_calls',
    'GlobalBHAVPatcher', 'patch_global_bhav',
    'SemiGlobalBHAVPatcher', 'patch_semi_global_bhav',
    'ObjectBHAVPatcher', 'patch_object_bhav',
    'BHAVPatchResult',
    
    # Mesh Export
    'Vertex', 'Face', 'Mesh',
    'MeshDecoder', 'decode_mesh',
    'GLTFExporter', 'export_mesh_gltf', 'export_mesh_glb',
    'ChunkMeshExporter', 'export_chunk_mesh',
    'MeshVisualizer', 'load_asset_to_3d',
    'MeshExportResult',
]
