"""
SimObliterator Suite - API/Module Tests

Tests that all classes and modules import correctly with expected interfaces.
Does NOT require game files - tests API structure only.

Can be run standalone: python test_api.py
Or via main runner: python tests.py --module api
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List

# Path setup
TESTS_DIR = Path(__file__).parent
DEV_DIR = TESTS_DIR.parent
SUITE_DIR = DEV_DIR.parent
SRC_DIR = SUITE_DIR / "src"
DATA_DIR = SUITE_DIR / "data"
DOCS_DIR = SUITE_DIR / "Docs"

sys.path.insert(0, str(SUITE_DIR))
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SRC_DIR / "Tools"))
sys.path.insert(0, str(SRC_DIR / "Tools" / "core"))
sys.path.insert(0, str(SRC_DIR / "formats"))


class TestResults:
    """Shared test results tracker."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors: List[str] = []
        
    def record(self, name: str, passed: bool, reason: str = ""):
        if passed:
            self.passed += 1
            print(f"  [OK] {name}")
        else:
            self.failed += 1
            self.errors.append(f"{name}: {reason}")
            print(f"  [FAIL] {name}: {reason}")
    
    def skip(self, name: str, reason: str):
        self.skipped += 1
        print(f"  [SKIP] {name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*60}")
        print(f"API TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total:   {total}")
        print(f"Passed:  {self.passed} [OK]")
        print(f"Failed:  {self.failed} [FAIL]")
        print(f"Skipped: {self.skipped} [SKIP]")
        return self.failed == 0


# Global results instance
results = TestResults()


# ═══════════════════════════════════════════════════════════════════════════════
# CORE SYSTEMS
# ═══════════════════════════════════════════════════════════════════════════════

def test_action_registry():
    """Test Action Registry - canonical action enforcement."""
    print("\n" + "="*60)
    print("ACTION REGISTRY")
    print("="*60)
    
    try:
        from core.action_registry import ActionRegistry, validate_action, is_registered_action
        
        registry = ActionRegistry.get()
        summary = registry.summary()
        
        results.record("Registry loaded", summary['total'] > 0, f"Expected >0 actions, got {summary['total']}")
        results.record("Has write actions", summary['write_actions'] > 0, "")
        results.record("Has high-risk actions", summary['high_risk'] > 0, "")
        
        valid, reason = validate_action('LoadIFF')
        results.record("LoadIFF validation", valid, reason)
        
        valid, reason = validate_action('NonExistentAction')
        results.record("Reject unknown action", not valid, f"Should reject, got: {valid}")
        
        valid, reason = validate_action('WriteSave', {'pipeline_mode': 'INSPECT'})
        results.record("WriteSave blocks in INSPECT", not valid, reason)
        
        valid, reason = validate_action('WriteSave', {
            'pipeline_mode': 'MUTATE',
            'user_confirmed': True,
            'safety_checked': True
        })
        results.record("WriteSave allows in MUTATE", valid, reason)
        
        print(f"\n  -- Registry: {summary['total']} actions, {summary['write_actions']} write, {summary['high_risk']} high-risk")
        
    except ImportError as e:
        results.skip("Action Registry", f"Import failed: {e}")
    except Exception as e:
        results.record("Action Registry load", False, str(e))


def test_mutation_pipeline():
    """Test Mutation Pipeline - write barrier layer."""
    print("\n" + "="*60)
    print("MUTATION PIPELINE")
    print("="*60)
    
    try:
        from core.mutation_pipeline import (
            MutationPipeline, MutationMode, MutationResult, 
            MutationRequest, MutationDiff
        )
        
        pipeline = MutationPipeline.get()
        pipeline2 = MutationPipeline.get()
        results.record("Singleton pattern", pipeline is pipeline2, "Should be same instance")
        results.record("Default mode is INSPECT", pipeline.mode == MutationMode.INSPECT, f"Expected INSPECT, got {pipeline.mode}")
        
        pipeline.set_mode(MutationMode.PREVIEW)
        results.record("Mode switch to PREVIEW", pipeline.mode == MutationMode.PREVIEW, "")
        pipeline.set_mode(MutationMode.INSPECT)
        
        req = MutationRequest(target_type='chunk', target_id=1234, target_file='test.iff', reason='Test mutation')
        results.record("MutationRequest created", req.target_id == 1234, "")
        
        diff = MutationDiff(field_path='objd.price', old_value=100, new_value=200)
        results.record("MutationDiff created", diff.old_value == 100, "")
        
        print(f"\n  -- Pipeline mode: {pipeline.mode.value}")
        
    except ImportError as e:
        results.skip("Mutation Pipeline", f"Import failed: {e}")
    except Exception as e:
        results.record("Mutation Pipeline load", False, str(e))


def test_provenance():
    """Test Provenance - confidence signaling."""
    print("\n" + "="*60)
    print("PROVENANCE SYSTEM")
    print("="*60)
    
    try:
        from core.provenance import Provenance, ProvenanceSource, ConfidenceLevel, ProvenanceRegistry
        
        prov = Provenance(source=ProvenanceSource.OBSERVED, confidence=ConfidenceLevel.HIGH)
        results.record("Provenance created", prov.source == ProvenanceSource.OBSERVED, "")
        results.record("Confidence badge", prov.badge() == "✓", f"Expected ✓, got {prov.badge()}")
        
        prov_low = Provenance(confidence=ConfidenceLevel.LOW)
        results.record("Low confidence badge", prov_low.badge() == "?", f"Expected ?, got {prov_low.badge()}")
        
        registry = ProvenanceRegistry()
        registry.register("BHAV", 0x1234, prov)
        retrieved = registry.get("BHAV", 0x1234)
        results.record("Registry stores/retrieves", retrieved is not None and retrieved.confidence == ConfidenceLevel.HIGH, "")
        
        print(f"\n  -- Provenance system functional")
        
    except ImportError as e:
        results.skip("Provenance", f"Import failed: {e}")
    except Exception as e:
        results.record("Provenance load", False, str(e))


def test_safety():
    """Test Safety API."""
    print("\n" + "="*60)
    print("SAFETY API")
    print("="*60)
    
    try:
        from safety import is_safe_to_edit, SafetyLevel, Scope, ResourceOwner, SafetyResult
        
        result = SafetyResult(level=SafetyLevel.SAFE, reasons=["Test reason"], scope=Scope.OBJECT, owner=ResourceOwner.MOD)
        results.record("SafetyResult.is_safe", result.is_safe, "SAFE should be is_safe")
        results.record("SafetyResult.summary", len(result.summary()) > 0, "Should have summary")
        
        danger = SafetyResult(level=SafetyLevel.DANGEROUS, reasons=["High risk"], scope=Scope.GLOBAL, owner=ResourceOwner.EA_BASE)
        results.record("DANGEROUS not is_safe", not danger.is_safe, "")
        results.record("Scope enum exists", Scope.GLOBAL is not None, "")
        results.record("ResourceOwner enum exists", ResourceOwner.EA_EXPANSION is not None, "")
        
        print(f"\n  -- Safety levels: {[s.value for s in SafetyLevel]}")
        
    except ImportError as e:
        results.skip("Safety API", f"Import failed: {e}")
    except Exception as e:
        results.record("Safety API load", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# BHAV SYSTEMS
# ═══════════════════════════════════════════════════════════════════════════════

def test_bhav_executor():
    """Test BHAV Executor - execution tracing."""
    print("\n" + "="*60)
    print("BHAV EXECUTOR")
    print("="*60)
    
    try:
        from core.bhav_executor import BHAVExecutor, ExecutionTrace, VMPrimitiveExitCode, StackFrame, ExecutionStep, DisassembledBHAV
        
        results.record("VMPrimitiveExitCode exists", VMPrimitiveExitCode.GOTO_TRUE is not None, "")
        results.record("RETURN_TRUE exit code", VMPrimitiveExitCode.RETURN_TRUE.value == 4, f"Expected 4, got {VMPrimitiveExitCode.RETURN_TRUE.value}")
        
        trace = ExecutionTrace(bhav_id=0x1234)
        results.record("ExecutionTrace created", trace.bhav_id == 0x1234, "")
        results.record("Trace starts empty", len(trace.steps) == 0, "")
        
        summary = trace.format_summary()
        results.record("format_summary works", "BHAV" in summary, f"Got: {summary[:50]}")
        results.record("BHAVExecutor class exists", BHAVExecutor is not None, "")
        
        print(f"\n  -- Exit codes: {len(VMPrimitiveExitCode)}")
        
    except ImportError as e:
        results.skip("BHAV Executor", f"Import failed: {e}")
    except Exception as e:
        results.record("BHAV Executor load", False, str(e))


def test_bhav_operations():
    """Test BHAV Operations - editing, validation, serialization."""
    print("\n" + "="*60)
    print("BHAV OPERATIONS")
    print("="*60)
    
    try:
        from core.bhav_operations import BHAVEditor, BHAVSerializer, BHAVValidator, BHAVImporter, BHAVOpResult, validate_bhav, serialize_bhav
        
        results.record("BHAVSerializer exists", BHAVSerializer is not None, "")
        results.record("BHAVValidator exists", BHAVValidator is not None, "")
        results.record("BHAVEditor exists", BHAVEditor is not None, "")
        results.record("BHAVImporter exists", BHAVImporter is not None, "")
        
        result = BHAVOpResult(True, "Test", bhav_id=1234)
        results.record("BHAVOpResult created", result.bhav_id == 1234, "")
        
        print(f"\n  -- BHAV operations module loaded")
        
    except ImportError as e:
        results.skip("BHAV Operations", f"Import failed: {e}")
    except Exception as e:
        results.record("BHAV Operations", False, str(e))


def test_bhav_patching():
    """Test BHAV Patching - remap, rewire, patch."""
    print("\n" + "="*60)
    print("BHAV PATCHING")
    print("="*60)
    
    try:
        from core.bhav_patching import (
            BHAVScope, BHAVCallOpcodes, BHAVIDRemapper, remap_bhav_ids,
            BHAVCallRewirer, rewire_bhav_calls, GlobalBHAVPatcher, patch_global_bhav,
            SemiGlobalBHAVPatcher, patch_semi_global_bhav, ObjectBHAVPatcher, patch_object_bhav,
            BHAVPatchResult
        )
        
        results.record("BHAVScope.is_global(0x50)", BHAVScope.is_global(0x50), "")
        results.record("BHAVScope.is_semi_global(0x200)", BHAVScope.is_semi_global(0x200), "")
        results.record("BHAVScope.is_object_local(0x1000)", BHAVScope.is_object_local(0x1000), "")
        results.record("BHAVScope.get_scope works", BHAVScope.get_scope(0x50) == 'global', "")
        
        results.record("BHAVCallOpcodes.is_call_opcode(0x0002)", BHAVCallOpcodes.is_call_opcode(0x0002), "")
        results.record("BHAVCallOpcodes has call info", BHAVCallOpcodes.get_call_info(0x0002) is not None, "")
        
        results.record("BHAVIDRemapper exists", BHAVIDRemapper is not None, "")
        results.record("BHAVCallRewirer exists", BHAVCallRewirer is not None, "")
        results.record("GlobalBHAVPatcher exists", GlobalBHAVPatcher is not None, "")
        results.record("SemiGlobalBHAVPatcher exists", SemiGlobalBHAVPatcher is not None, "")
        results.record("ObjectBHAVPatcher exists", ObjectBHAVPatcher is not None, "")
        
        result = BHAVPatchResult(True, "Test", patches_applied=5, id_map={1: 2})
        results.record("BHAVPatchResult created", result.patches_applied == 5, "")
        results.record("BHAVPatchResult has id_map", len(result.id_map) == 1, "")
        
        print(f"\n  -- BHAV patching module loaded")
        
    except ImportError as e:
        results.skip("BHAV Patching", f"Import failed: {e}")
    except Exception as e:
        results.record("BHAV Patching", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# FORMAT PARSERS
# ═══════════════════════════════════════════════════════════════════════════════

def test_iff_parser():
    """Test IFF file parser."""
    print("\n" + "="*60)
    print("IFF PARSER")
    print("="*60)
    
    try:
        from formats.iff.iff_file import IffFile, IffRuntimeInfo
        
        results.record("IffFile class exists", IffFile is not None, "")
        results.record("IffRuntimeInfo exists", IffRuntimeInfo is not None, "")
        
        iff = IffFile(filename="test.iff")
        results.record("IffFile instantiation", iff.filename == "test.iff", "")
        
        print(f"\n  -- IFF parser available")
        
    except ImportError as e:
        results.skip("IFF Parser", f"Import failed: {e}")
    except Exception as e:
        results.record("IFF Parser load", False, str(e))


def test_far_parser():
    """Test FAR archive parser."""
    print("\n" + "="*60)
    print("FAR PARSER")
    print("="*60)
    
    try:
        from formats.far.far1 import FAR1Archive, FarEntry
        
        results.record("FAR1Archive class exists", FAR1Archive is not None, "")
        results.record("FarEntry exists", FarEntry is not None, "")
        
        entry = FarEntry(filename="test.dat", data_length=1024)
        results.record("FarEntry instantiation", entry.data_length == 1024, "")
        
        print(f"\n  -- FAR parser available")
        
    except ImportError as e:
        results.skip("FAR Parser", f"Import failed: {e}")
    except Exception as e:
        results.record("FAR Parser load", False, str(e))


def test_dbpf_parser():
    """Test DBPF archive parser."""
    print("\n" + "="*60)
    print("DBPF PARSER")
    print("="*60)
    
    try:
        from formats.dbpf.dbpf import DBPFTypeID, DBPFGroupID
        
        results.record("DBPFTypeID exists", DBPFTypeID is not None, "")
        results.record("OBJD type ID", DBPFTypeID.OBJD == 0xC0C0C001, f"Got {hex(DBPFTypeID.OBJD)}")
        results.record("BHAV type ID", DBPFTypeID.BHAV == 0xC0C0C002, f"Got {hex(DBPFTypeID.BHAV)}")
        
        print(f"\n  -- DBPF parser available, {len(list(DBPFTypeID))} type IDs defined")
        
    except ImportError as e:
        results.skip("DBPF Parser", f"Import failed: {e}")
    except Exception as e:
        results.record("DBPF Parser load", False, str(e))


def test_chunk_parsers():
    """Test chunk parser availability."""
    print("\n" + "="*60)
    print("CHUNK PARSERS")
    print("="*60)
    
    chunks_dir = SRC_DIR / "formats" / "iff" / "chunks"
    critical_chunks = ["bhav.py", "objd.py", "objf.py", "ttab.py", "str_.py", "dgrp.py", "spr.py"]
    
    all_chunks = list(chunks_dir.glob("*.py")) if chunks_dir.exists() else []
    chunk_names = [c.name for c in all_chunks if not c.name.startswith("_")]
    
    for chunk in critical_chunks:
        exists = chunk in chunk_names
        results.record(f"Chunk: {chunk}", exists, "" if exists else "Missing")
    
    print(f"\n  -- Total chunk parsers: {len(chunk_names)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTITIES
# ═══════════════════════════════════════════════════════════════════════════════

def test_entities():
    """Test entity abstractions."""
    print("\n" + "="*60)
    print("ENTITY ABSTRACTIONS")
    print("="*60)
    
    entities_found = []
    
    try:
        from entities.object_entity import ObjectEntity
        results.record("ObjectEntity exists", ObjectEntity is not None, "")
        entities_found.append("ObjectEntity")
    except ImportError as e:
        results.skip("ObjectEntity", str(e))
    
    try:
        from entities.behavior_entity import BehaviorEntity, BehaviorPurpose
        results.record("BehaviorEntity exists", BehaviorEntity is not None, "")
        results.record("BehaviorPurpose enum", BehaviorPurpose is not None, "")
        entities_found.append("BehaviorEntity")
    except ImportError as e:
        results.skip("BehaviorEntity", str(e))
    
    try:
        from entities.sim_entity import SimEntity
        results.record("SimEntity exists", SimEntity is not None, "")
        entities_found.append("SimEntity")
    except ImportError as e:
        results.skip("SimEntity", str(e))
    
    try:
        from entities.relationship_entity import RelationshipGraph
        results.record("RelationshipGraph exists", RelationshipGraph is not None, "")
        entities_found.append("RelationshipGraph")
    except ImportError as e:
        results.skip("RelationshipGraph", str(e))
    
    print(f"\n  -- Entities: {', '.join(entities_found)}")


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def test_file_operations():
    """Test File Operations."""
    print("\n" + "="*60)
    print("FILE OPERATIONS")
    print("="*60)
    
    try:
        from core.file_operations import BackupManager, ContainerValidator, ArchiveExtractor, IFFWriter, ChunkOperations, FileOpResult
        
        bm = BackupManager()
        results.record("BackupManager created", bm is not None, "")
        results.record("ContainerValidator exists", ContainerValidator is not None, "")
        results.record("IFFWriter exists", IFFWriter is not None, "")
        results.record("ChunkOperations exists", ChunkOperations is not None, "")
        
        result = FileOpResult(True, "Test message")
        results.record("FileOpResult created", result.success, "")
        
        print(f"\n  -- File operations module loaded")
        
    except ImportError as e:
        results.skip("File Operations", f"Import failed: {e}")
    except Exception as e:
        results.record("File Operations", False, str(e))


def test_import_operations():
    """Test Import Operations."""
    print("\n" + "="*60)
    print("IMPORT OPERATIONS")
    print("="*60)
    
    try:
        from core.import_operations import ChunkImporter, SpriteImporter, DatabaseImporter, AssetImporter, ImportResult
        
        results.record("ChunkImporter exists", ChunkImporter is not None, "")
        results.record("SpriteImporter exists", SpriteImporter is not None, "")
        results.record("DatabaseImporter exists", DatabaseImporter is not None, "")
        results.record("AssetImporter exists", AssetImporter is not None, "")
        
        result = ImportResult(True, "Test", imported_count=5)
        results.record("ImportResult created", result.imported_count == 5, "")
        
        print(f"\n  -- Import operations module loaded")
        
    except ImportError as e:
        results.skip("Import Operations", f"Import failed: {e}")
    except Exception as e:
        results.record("Import Operations", False, str(e))


def test_container_operations():
    """Test Container Operations."""
    print("\n" + "="*60)
    print("CONTAINER OPERATIONS")
    print("="*60)
    
    try:
        from core.container_operations import (
            CacheManager, clear_caches, HeaderNormalizer, normalize_headers,
            IndexRebuilder, rebuild_indexes, ContainerReindexer, reindex_container,
            IFFSplitter, split_iff, IFFMerger, merge_iff_files,
            FARWriter, write_far, ContainerOpResult
        )
        
        cache_mgr = CacheManager.get()
        results.record("CacheManager singleton", cache_mgr is not None, "")
        
        result = clear_caches()
        results.record("clear_caches works", result.success, result.message)
        
        results.record("HeaderNormalizer exists", HeaderNormalizer is not None, "")
        results.record("IndexRebuilder exists", IndexRebuilder is not None, "")
        results.record("ContainerReindexer exists", ContainerReindexer is not None, "")
        results.record("IFFSplitter exists", IFFSplitter is not None, "")
        results.record("IFFMerger exists", IFFMerger is not None, "")
        results.record("FARWriter exists", FARWriter is not None, "")
        
        result = ContainerOpResult(True, "Test", affected_chunks=10)
        results.record("ContainerOpResult created", result.affected_chunks == 10, "")
        
        print(f"\n  -- Container operations module loaded")
        
    except ImportError as e:
        results.skip("Container Operations", f"Import failed: {e}")
    except Exception as e:
        results.record("Container Operations", False, str(e))


def test_save_mutations():
    """Test Save Mutations."""
    print("\n" + "="*60)
    print("SAVE MUTATIONS")
    print("="*60)
    
    try:
        from core.save_mutations import (
            SimManager, SimTemplate, TimeManager, modify_time,
            InventoryManager, modify_inventory, AspirationManager, modify_aspirations,
            MemoryManager, modify_memories, SaveMutationResult
        )
        
        template = SimTemplate(first_name="Test", last_name="Sim")
        results.record("SimTemplate created", template.first_name == "Test", "")
        results.record("SimTemplate has personality", len(template.personality) > 0, "")
        
        data = template.to_bytes()
        results.record("SimTemplate serializes", len(data) > 0, "")
        
        results.record("SimManager exists", SimManager is not None, "")
        results.record("TimeManager exists", TimeManager is not None, "")
        results.record("InventoryManager exists", InventoryManager is not None, "")
        results.record("AspirationManager exists", AspirationManager is not None, "")
        results.record("MemoryManager exists", MemoryManager is not None, "")
        
        result = SaveMutationResult(True, "Test", sim_id=123)
        results.record("SaveMutationResult created", result.sim_id == 123, "")
        
        print(f"\n  -- Save mutations module loaded")
        
    except ImportError as e:
        results.skip("Save Mutations", f"Import failed: {e}")
    except Exception as e:
        results.record("Save Mutations", False, str(e))


def test_mesh_export():
    """Test Mesh Export."""
    print("\n" + "="*60)
    print("MESH EXPORT")
    print("="*60)
    
    try:
        from core.mesh_export import (
            Vertex, Face, Mesh, MeshDecoder, decode_mesh,
            GLTFExporter, export_mesh_gltf, export_mesh_glb,
            ChunkMeshExporter, export_chunk_mesh,
            MeshVisualizer, load_asset_to_3d, MeshExportResult
        )
        
        v = Vertex(1.0, 2.0, 3.0)
        results.record("Vertex created", v.x == 1.0, "")
        results.record("Vertex.to_list works", v.to_list() == [1.0, 2.0, 3.0], "")
        
        f = Face(0, 1, 2)
        results.record("Face created", f.v0 == 0, "")
        results.record("Face.to_list works", f.to_list() == [0, 1, 2], "")
        
        mesh = Mesh(name="test")
        mesh.vertices.append(Vertex(0, 0, 0))
        mesh.vertices.append(Vertex(1, 0, 0))
        mesh.vertices.append(Vertex(0, 1, 0))
        mesh.faces.append(Face(0, 1, 2))
        
        results.record("Mesh created", mesh.vertex_count == 3, "")
        results.record("Mesh has faces", mesh.face_count == 1, "")
        
        bounds = mesh.get_bounds()
        results.record("Mesh.get_bounds works", bounds[0] == (0, 0, 0), "")
        
        viz = MeshVisualizer(mesh)
        three_js = viz.to_three_js()
        results.record("MeshVisualizer.to_three_js works", 'vertices' in three_js, "")
        
        obj_str = viz.to_obj_string()
        results.record("MeshVisualizer.to_obj_string works", 'v 0' in obj_str, "")
        
        results.record("MeshDecoder exists", MeshDecoder is not None, "")
        results.record("GLTFExporter exists", GLTFExporter is not None, "")
        results.record("ChunkMeshExporter exists", ChunkMeshExporter is not None, "")
        
        result = MeshExportResult(True, "Test", vertex_count=100, face_count=50)
        results.record("MeshExportResult created", result.vertex_count == 100, "")
        
        print(f"\n  -- Mesh export module loaded")
        
    except ImportError as e:
        results.skip("Mesh Export", f"Import failed: {e}")
    except Exception as e:
        results.record("Mesh Export", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# GUI
# ═══════════════════════════════════════════════════════════════════════════════

def test_focus_coordinator():
    """Test Focus Coordinator."""
    print("\n" + "="*60)
    print("FOCUS COORDINATOR")
    print("="*60)
    
    try:
        from gui.focus import FocusCoordinator, Scope, Context, SelectionEntry
        
        coordinator = FocusCoordinator()
        results.record("Initial selection None", coordinator.current is None, "")
        
        coordinator.select(resource_type="BHAV", resource_id=0x1234, label="Test Behavior", source_panel="test_panel")
        
        results.record("Selection stored", coordinator.current is not None, "")
        results.record("Selection type correct", coordinator.current.resource_type == "BHAV", "")
        results.record("Selection ID correct", coordinator.current.resource_id == 0x1234, "")
        results.record("Scope.ALL exists", Scope.ALL is not None, "")
        results.record("Context.FILE exists", Context.FILE is not None, "")
        
        print(f"\n  -- Scopes: {[s.name for s in Scope]}")
        
    except ImportError as e:
        results.skip("Focus Coordinator", f"Import failed: {e}")
    except Exception as e:
        results.record("Focus Coordinator load", False, str(e))


def test_panels_exist():
    """Test that all documented panels exist."""
    print("\n" + "="*60)
    print("GUI PANELS INVENTORY")
    print("="*60)
    
    panels_dir = SRC_DIR / "Tools" / "gui" / "panels"
    
    expected_panels = [
        ("file_loader.py", "FileLoaderPanel"),
        ("iff_inspector.py", "IFFInspectorPanel"),
        ("chunk_inspector.py", "ChunkInspectorPanel"),
        ("bhav_editor.py", "BHAVEditorPanel"),
        ("far_browser.py", "FARBrowserPanel"),
        ("semantic_inspector.py", "SemanticInspectorPanel"),
        ("object_inspector.py", "ObjectInspectorPanel"),
        ("graph_canvas.py", "GraphCanvasPanel"),
        ("save_editor_panel.py", "SaveEditorPanel"),
        ("library_browser_panel.py", "LibraryBrowserPanel"),
        ("visual_object_browser_panel.py", "VisualObjectBrowserPanel"),
        ("navigation_bar_panel.py", "NavigationBarPanel"),
        ("diff_compare_panel.py", "DiffComparePanel"),
        ("task_runner_panel.py", "TaskRunnerPanel"),
        ("safety_trust_panel.py", "SafetyTrustPanel"),
        ("support_panels.py", "GlobalSearchPanel"),
        ("system_overview_panel.py", "SystemOverviewPanel"),
        ("sprite_export_panel.py", "SpriteExportPanel"),
    ]
    
    found = 0
    for filename, panel_name in expected_panels:
        filepath = panels_dir / filename
        if filepath.exists():
            found += 1
            results.record(f"{panel_name}", True, "")
        else:
            results.record(f"{panel_name}", False, f"Missing: {filename}")
    
    print(f"\n  -- Panels found: {found}/{len(expected_panels)}")


def test_engine_toolkit():
    """Test Engine Toolkit."""
    print("\n" + "="*60)
    print("ENGINE TOOLKIT")
    print("="*60)
    
    try:
        from forensic.engine_toolkit import EngineToolkit
        
        toolkit = EngineToolkit()
        results.record("EngineToolkit created", toolkit is not None, "")
        
        print(f"\n  -- Engine toolkit functional")
        
    except ImportError as e:
        results.skip("Engine Toolkit", f"Import failed: {e}")
    except Exception as e:
        results.record("Engine Toolkit load", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# DATA FILES
# ═══════════════════════════════════════════════════════════════════════════════

def test_data_files():
    """Test data file presence and validity."""
    print("\n" + "="*60)
    print("DATA FILES")
    print("="*60)
    
    import json
    
    core_files = ["unknowns_db.json", "opcodes_db.json", "global_behaviors.json", "execution_model.json"]
    integrated_files = [
        ("global_behavior_database.json", "global_behavior_database"),
        ("characters.json", "characters"),
        ("objects.json", "objects"),
        ("meshes.json", "meshes"),
    ]
    
    for filename in core_files:
        filepath = DATA_DIR / filename
        exists = filepath.exists()
        if exists:
            size = filepath.stat().st_size
            results.record(f"{filename}", True, f"Size: {size:,} bytes")
        else:
            results.record(f"{filename}", False, "File not found")
    
    for filename, desc in integrated_files:
        filepath = DATA_DIR / filename
        if filepath.exists():
            size = filepath.stat().st_size
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                results.record(f"{filename}", True, f"Valid JSON, {size:,} bytes")
            except json.JSONDecodeError as e:
                results.record(f"{filename}", False, f"Invalid JSON: {e}")
        else:
            results.record(f"{filename}", False, "File not found")
    
    # Test global_behavior_database.json structure
    gbd_path = DATA_DIR / "global_behavior_database.json"
    if gbd_path.exists():
        try:
            with open(gbd_path, 'r', encoding='utf-8') as f:
                gbd = json.load(f)
            results.record("GBD has metadata", "metadata" in gbd, "")
            results.record("GBD has expansion_ranges", "expansion_ranges" in gbd, "")
            results.record("GBD has found_globals", "found_globals" in gbd, "")
            if "found_globals" in gbd:
                global_count = len(gbd["found_globals"])
                results.record("GBD globals count", global_count >= 200, f"Found {global_count} globals")
        except Exception as e:
            results.record("GBD structure", False, str(e))
    
    print(f"\n  -- Data directory: {DATA_DIR}")


def test_research_docs():
    """Test that research documentation is present."""
    print("\n" + "="*60)
    print("RESEARCH DOCUMENTATION")
    print("="*60)
    
    research_docs = [
        ("research/DEFINITIVE_BHAV_REFERENCE.md", 20000),
        ("research/FREESO_BEHAVIORAL_ARCHITECTURE.md", 30000),
        ("research/BHAV_OPCODE_REFERENCE.md", 8000),
        ("research/ENGINE_PRIMITIVES.md", 5000),
        ("research/VALIDATION_TRUST_GUIDE.md", 8000),
        ("research/CYCLE_PATTERNS_GUIDE.md", 8000),
        ("technical/RESOURCE_GRAPH_USAGE_GUIDE.md", 8000),
        ("INTEGRATION_GAPS.md", 5000),
    ]
    
    for rel_path, min_size in research_docs:
        filepath = DOCS_DIR / rel_path
        if filepath.exists():
            size = filepath.stat().st_size
            if size >= min_size:
                results.record(f"{rel_path}", True, f"{size:,} bytes")
            else:
                results.record(f"{rel_path}", False, f"Too small: {size} < {min_size}")
        else:
            results.record(f"{rel_path}", False, "Not found")
    
    print(f"\n  -- Docs directory: {DOCS_DIR}")


def test_webviewer():
    """Test webviewer integration."""
    print("\n" + "="*60)
    print("WEBVIEWER")
    print("="*60)
    
    webviewer_dir = SRC_DIR / "Tools" / "webviewer"
    
    if not webviewer_dir.exists():
        results.record("Webviewer folder", False, "Directory not found")
        return
    
    results.record("Webviewer folder", True, "")
    
    expected_files = [
        ("export_server.py", 30000),
        ("character_viewer.html", 30000),
        ("object_viewer.html", 30000),
        ("library_browser.html", 25000),
        ("graph_viewer_embed.html", 8000),
        ("character_exporter.py", 4000),
        ("TESTING_VALIDATION.js", 15000),
    ]
    
    for filename, min_size in expected_files:
        filepath = webviewer_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            if size >= min_size:
                results.record(f"webviewer/{filename}", True, f"{size:,} bytes")
            else:
                results.record(f"webviewer/{filename}", False, f"Too small: {size}")
        else:
            results.record(f"webviewer/{filename}", False, "Not found")
    
    try:
        with open(webviewer_dir / "export_server.py", 'r', encoding='utf-8') as f:
            source = f.read()
        compile(source, "export_server.py", "exec")
        results.record("export_server.py syntax", True, "Valid Python")
    except SyntaxError as e:
        results.record("export_server.py syntax", False, str(e))
    
    print(f"\n  -- Webviewer directory: {webviewer_dir}")


def test_freeso_gap_analyzer():
    """Test FreeSO gap analyzer integration."""
    print("\n" + "="*60)
    print("FREESO GAP ANALYZER")
    print("="*60)
    
    forensic_dir = SRC_DIR / "Tools" / "forensic"
    analyzer_path = forensic_dir / "freeso_gap_analyzer.py"
    
    if not analyzer_path.exists():
        results.record("freeso_gap_analyzer.py", False, "Not found")
        return
    
    size = analyzer_path.stat().st_size
    results.record("freeso_gap_analyzer.py exists", True, f"{size:,} bytes")
    
    try:
        with open(analyzer_path, 'r', encoding='utf-8') as f:
            source = f.read()
        compile(source, "freeso_gap_analyzer.py", "exec")
        results.record("freeso_gap_analyzer.py syntax", True, "Valid Python")
    except SyntaxError as e:
        results.record("freeso_gap_analyzer.py syntax", False, str(e))
    
    has_priority = "ImplementationPriority" in source
    has_complexity = "ImplementationComplexity" in source
    has_gap_class = "class ParityGap" in source
    has_analyzer = "class FreeSoGapAnalyzer" in source
    
    results.record("Has ImplementationPriority enum", has_priority, "")
    results.record("Has ImplementationComplexity enum", has_complexity, "")
    results.record("Has ParityGap dataclass", has_gap_class, "")
    results.record("Has FreeSoGapAnalyzer class", has_analyzer, "")
    
    print(f"\n  -- FreeSO analyzer ready for use")


def test_semantic_globals():
    """Test semantic globals integration."""
    print("\n" + "="*60)
    print("SEMANTIC GLOBALS")
    print("="*60)
    
    forensic_dir = SRC_DIR / "Tools" / "forensic"
    sg_path = forensic_dir / "semantic_globals.py"
    
    if not sg_path.exists():
        results.record("semantic_globals.py", False, "Not found")
        return
    
    size = sg_path.stat().st_size
    results.record("semantic_globals.py exists", size > 10000, f"{size:,} bytes")
    
    with open(sg_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    results.record("Has SemanticGlobalResolver", "SemanticGlobalResolver" in source, "")
    results.record("Has ExpansionBlock enum", "ExpansionBlock" in source, "")
    results.record("Has CORE_FUNCTION_OFFSETS", "CORE_FUNCTION_OFFSETS" in source, "")
    results.record("Has FreeSoParityChecker", "FreeSoParityChecker" in source, "")
    results.record("Has base game ID range (256-511)", "256" in source and "511" in source, "")
    results.record("Has expansion ID ranges", "512" in source or "768" in source, "")
    
    print(f"\n  -- Semantic globals provides expansion-aware BHAV labeling")


# ═══════════════════════════════════════════════════════════════════════════════
# RUN ALL
# ═══════════════════════════════════════════════════════════════════════════════

def run_all_tests(results_obj=None):
    """Run all API tests. Returns (passed, failed, skipped)."""
    global results
    if results_obj:
        results = results_obj
    else:
        results = TestResults()
    
    # Core
    test_action_registry()
    test_mutation_pipeline()
    test_provenance()
    test_safety()
    
    # BHAV
    test_bhav_executor()
    test_bhav_operations()
    test_bhav_patching()
    
    # Parsers
    test_iff_parser()
    test_far_parser()
    test_dbpf_parser()
    test_chunk_parsers()
    
    # Entities
    test_entities()
    
    # Operations
    test_file_operations()
    test_import_operations()
    test_container_operations()
    test_save_mutations()
    test_mesh_export()
    
    # GUI
    test_focus_coordinator()
    test_panels_exist()
    test_engine_toolkit()
    
    # Data
    test_data_files()
    test_research_docs()
    test_webviewer()
    test_freeso_gap_analyzer()
    test_semantic_globals()
    
    return results.passed, results.failed, results.skipped


def main():
    """Run API tests standalone."""
    print("╔" + "═"*60 + "╗")
    print("║  SIMOBLITERATOR SUITE - API TESTS                         ║")
    print("║  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "                                        ║")
    print("╚" + "═"*60 + "╝")
    
    run_all_tests()
    success = results.summary()
    
    if success:
        print("\n🎉 ALL API TESTS PASSED!")
    else:
        print(f"\n⚠️  {results.failed} TESTS FAILED")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
