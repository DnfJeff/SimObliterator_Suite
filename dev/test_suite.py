"""
SimObliterator Suite - Comprehensive Test Suite

Tests all major systems:
1. Core Systems (Action Registry, Mutation Pipeline, Provenance, Safety)
2. BHAV Executor (Execution Tracing)
3. Format Parsers (IFF, FAR, DBPF)
4. Entity Abstractions
5. Focus Coordinator
6. Engine Toolkit

Run: python test_suite.py
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Any

# Ensure paths are correct
DEV_DIR = Path(__file__).parent
SUITE_DIR = DEV_DIR.parent
SRC_DIR = SUITE_DIR / "src"
sys.path.insert(0, str(SUITE_DIR))
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SRC_DIR / "Tools"))
sys.path.insert(0, str(SRC_DIR / "Tools" / "core"))
sys.path.insert(0, str(SRC_DIR / "formats"))

# Test results tracking
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors: List[str] = []
        
    def record(self, name: str, passed: bool, reason: str = ""):
        if passed:
            self.passed += 1
            print(f"  ✅ {name}")
        else:
            self.failed += 1
            self.errors.append(f"{name}: {reason}")
            print(f"  ❌ {name}: {reason}")
    
    def skip(self, name: str, reason: str):
        self.skipped += 1
        print(f"  ⏭️  {name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total:   {total}")
        print(f"Passed:  {self.passed} ✅")
        print(f"Failed:  {self.failed} ❌")
        print(f"Skipped: {self.skipped} ⏭️")
        if self.errors:
            print(f"\nFailures:")
            for err in self.errors:
                print(f"  • {err}")
        return self.failed == 0

results = TestResults()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CORE SYSTEMS
# ═══════════════════════════════════════════════════════════════════════════════

def test_action_registry():
    """Test Action Registry - canonical action enforcement."""
    print("\n" + "="*60)
    print("1. ACTION REGISTRY")
    print("="*60)
    
    try:
        from core.action_registry import ActionRegistry, validate_action, is_registered_action
        
        registry = ActionRegistry.get()
        summary = registry.summary()
        
        # Test basic counts
        results.record(
            "Registry loaded",
            summary['total'] > 0,
            f"Expected >0 actions, got {summary['total']}"
        )
        
        results.record(
            "Has write actions",
            summary['write_actions'] > 0,
            f"Expected >0 write actions, got {summary['write_actions']}"
        )
        
        results.record(
            "Has high-risk actions",
            summary['high_risk'] > 0,
            f"Expected >0 high-risk actions"
        )
        
        # Test validation
        valid, reason = validate_action('LoadIFF')
        results.record("LoadIFF validation", valid, reason)
        
        valid, reason = validate_action('NonExistentAction')
        results.record("Reject unknown action", not valid, f"Should reject, got: {valid}")
        
        # Test pipeline requirement
        valid, reason = validate_action('WriteSave', {'pipeline_mode': 'INSPECT'})
        results.record("WriteSave blocks in INSPECT", not valid, reason)
        
        valid, reason = validate_action('WriteSave', {
            'pipeline_mode': 'MUTATE',
            'user_confirmed': True,
            'safety_checked': True
        })
        results.record("WriteSave allows in MUTATE", valid, reason)
        
        # Summary stats
        print(f"\n  📊 Registry: {summary['total']} actions, "
              f"{summary['write_actions']} write, "
              f"{summary['high_risk']} high-risk")
        
    except ImportError as e:
        results.skip("Action Registry", f"Import failed: {e}")
    except Exception as e:
        results.record("Action Registry load", False, str(e))


def test_mutation_pipeline():
    """Test Mutation Pipeline - write barrier layer."""
    print("\n" + "="*60)
    print("2. MUTATION PIPELINE")
    print("="*60)
    
    try:
        from core.mutation_pipeline import (
            MutationPipeline, MutationMode, MutationResult, 
            MutationRequest, MutationDiff
        )
        
        pipeline = MutationPipeline.get()
        
        # Test singleton
        pipeline2 = MutationPipeline.get()
        results.record("Singleton pattern", pipeline is pipeline2, "Should be same instance")
        
        # Test mode defaults to INSPECT
        results.record(
            "Default mode is INSPECT",
            pipeline.mode == MutationMode.INSPECT,
            f"Expected INSPECT, got {pipeline.mode}"
        )
        
        # Test mode switching
        pipeline.set_mode(MutationMode.PREVIEW)
        results.record(
            "Mode switch to PREVIEW",
            pipeline.mode == MutationMode.PREVIEW,
            f"Expected PREVIEW, got {pipeline.mode}"
        )
        
        pipeline.set_mode(MutationMode.INSPECT)  # Reset
        
        # Test request creation
        req = MutationRequest(
            target_type='chunk',
            target_id=1234,
            target_file='test.iff',
            reason='Test mutation'
        )
        results.record("MutationRequest created", req.target_id == 1234, "")
        
        # Test diff creation
        diff = MutationDiff(
            field_path='objd.price',
            old_value=100,
            new_value=200
        )
        results.record("MutationDiff created", diff.old_value == 100, "")
        
        print(f"\n  📊 Pipeline mode: {pipeline.mode.value}")
        
    except ImportError as e:
        results.skip("Mutation Pipeline", f"Import failed: {e}")
    except Exception as e:
        results.record("Mutation Pipeline load", False, str(e))


def test_provenance():
    """Test Provenance - confidence signaling."""
    print("\n" + "="*60)
    print("3. PROVENANCE SYSTEM")
    print("="*60)
    
    try:
        from core.provenance import (
            Provenance, ProvenanceSource, ConfidenceLevel,
            ProvenanceRegistry
        )
        
        # Test basic provenance
        prov = Provenance(
            source=ProvenanceSource.OBSERVED,
            confidence=ConfidenceLevel.HIGH
        )
        
        results.record("Provenance created", prov.source == ProvenanceSource.OBSERVED, "")
        results.record("Confidence badge", prov.badge() == "✓", f"Expected ✓, got {prov.badge()}")
        
        # Test different levels
        prov_low = Provenance(confidence=ConfidenceLevel.LOW)
        results.record("Low confidence badge", prov_low.badge() == "?", f"Expected ?, got {prov_low.badge()}")
        
        # Test registry
        registry = ProvenanceRegistry()
        registry.register("BHAV", 0x1234, prov)
        
        retrieved = registry.get("BHAV", 0x1234)
        results.record(
            "Registry stores/retrieves",
            retrieved is not None and retrieved.confidence == ConfidenceLevel.HIGH,
            ""
        )
        
        print(f"\n  📊 Provenance system functional")
        
    except ImportError as e:
        results.skip("Provenance", f"Import failed: {e}")
    except Exception as e:
        results.record("Provenance load", False, str(e))


def test_safety():
    """Test Safety API."""
    print("\n" + "="*60)
    print("4. SAFETY API")
    print("="*60)
    
    try:
        from safety import (
            is_safe_to_edit, SafetyLevel, Scope, ResourceOwner, SafetyResult
        )
        
        # Test SafetyResult
        result = SafetyResult(
            level=SafetyLevel.SAFE,
            reasons=["Test reason"],
            scope=Scope.OBJECT,
            owner=ResourceOwner.MOD
        )
        
        results.record("SafetyResult.is_safe", result.is_safe, "SAFE should be is_safe")
        results.record("SafetyResult.summary", len(result.summary()) > 0, "Should have summary")
        
        # Test dangerous level
        danger = SafetyResult(
            level=SafetyLevel.DANGEROUS,
            reasons=["High risk"],
            scope=Scope.GLOBAL,
            owner=ResourceOwner.EA_BASE
        )
        
        results.record("DANGEROUS not is_safe", not danger.is_safe, "DANGEROUS should not be is_safe")
        
        # Test scope detection
        results.record("Scope enum exists", Scope.GLOBAL is not None, "")
        results.record("ResourceOwner enum exists", ResourceOwner.EA_EXPANSION is not None, "")
        
        print(f"\n  📊 Safety levels: {[s.value for s in SafetyLevel]}")
        
    except ImportError as e:
        results.skip("Safety API", f"Import failed: {e}")
    except Exception as e:
        results.record("Safety API load", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. BHAV EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

def test_bhav_executor():
    """Test BHAV Executor - execution tracing."""
    print("\n" + "="*60)
    print("5. BHAV EXECUTOR")
    print("="*60)
    
    try:
        from core.bhav_executor import (
            BHAVExecutor, ExecutionTrace, VMPrimitiveExitCode,
            StackFrame, ExecutionStep, DisassembledBHAV
        )
        
        # Test enum
        results.record(
            "VMPrimitiveExitCode exists",
            VMPrimitiveExitCode.GOTO_TRUE is not None,
            ""
        )
        results.record(
            "RETURN_TRUE exit code",
            VMPrimitiveExitCode.RETURN_TRUE.value == 4,
            f"Expected 4, got {VMPrimitiveExitCode.RETURN_TRUE.value}"
        )
        
        # Test ExecutionTrace
        trace = ExecutionTrace(bhav_id=0x1234)
        results.record("ExecutionTrace created", trace.bhav_id == 0x1234, "")
        results.record("Trace starts empty", len(trace.steps) == 0, "")
        
        # Test format methods
        summary = trace.format_summary()
        results.record("format_summary works", "BHAV" in summary, f"Got: {summary[:50]}")
        
        # Test BHAVExecutor class exists
        results.record("BHAVExecutor class exists", BHAVExecutor is not None, "")
        
        print(f"\n  📊 Exit codes: {len(VMPrimitiveExitCode)}")
        
    except ImportError as e:
        results.skip("BHAV Executor", f"Import failed: {e}")
    except Exception as e:
        results.record("BHAV Executor load", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FORMAT PARSERS
# ═══════════════════════════════════════════════════════════════════════════════

def test_iff_parser():
    """Test IFF file parser."""
    print("\n" + "="*60)
    print("6. IFF PARSER")
    print("="*60)
    
    try:
        from formats.iff.iff_file import IffFile, IffRuntimeInfo
        
        results.record("IffFile class exists", IffFile is not None, "")
        results.record("IffRuntimeInfo exists", IffRuntimeInfo is not None, "")
        
        # Test instantiation
        iff = IffFile(filename="test.iff")
        results.record("IffFile instantiation", iff.filename == "test.iff", "")
        
        print(f"\n  📊 IFF parser available")
        
    except ImportError as e:
        results.skip("IFF Parser", f"Import failed: {e}")
    except Exception as e:
        results.record("IFF Parser load", False, str(e))


def test_far_parser():
    """Test FAR archive parser."""
    print("\n" + "="*60)
    print("7. FAR PARSER")
    print("="*60)
    
    try:
        from formats.far.far1 import FAR1Archive, FarEntry
        
        results.record("FAR1Archive class exists", FAR1Archive is not None, "")
        results.record("FarEntry exists", FarEntry is not None, "")
        
        # Test FarEntry
        entry = FarEntry(filename="test.dat", data_length=1024)
        results.record("FarEntry instantiation", entry.data_length == 1024, "")
        
        print(f"\n  📊 FAR parser available")
        
    except ImportError as e:
        results.skip("FAR Parser", f"Import failed: {e}")
    except Exception as e:
        results.record("FAR Parser load", False, str(e))


def test_dbpf_parser():
    """Test DBPF archive parser."""
    print("\n" + "="*60)
    print("8. DBPF PARSER")
    print("="*60)
    
    try:
        from formats.dbpf.dbpf import DBPFTypeID, DBPFGroupID
        
        results.record("DBPFTypeID exists", DBPFTypeID is not None, "")
        results.record("OBJD type ID", DBPFTypeID.OBJD == 0xC0C0C001, f"Got {hex(DBPFTypeID.OBJD)}")
        results.record("BHAV type ID", DBPFTypeID.BHAV == 0xC0C0C002, f"Got {hex(DBPFTypeID.BHAV)}")
        
        print(f"\n  📊 DBPF parser available, {len(list(DBPFTypeID))} type IDs defined")
        
    except ImportError as e:
        results.skip("DBPF Parser", f"Import failed: {e}")
    except Exception as e:
        results.record("DBPF Parser load", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ENTITY ABSTRACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def test_entities():
    """Test entity abstractions."""
    print("\n" + "="*60)
    print("9. ENTITY ABSTRACTIONS")
    print("="*60)
    
    entities_found = []
    
    # Test ObjectEntity
    try:
        from entities.object_entity import ObjectEntity
        results.record("ObjectEntity exists", ObjectEntity is not None, "")
        entities_found.append("ObjectEntity")
    except ImportError as e:
        results.skip("ObjectEntity", str(e))
    except Exception as e:
        results.record("ObjectEntity", False, str(e))
    
    # Test BehaviorEntity
    try:
        from entities.behavior_entity import BehaviorEntity, BehaviorPurpose
        results.record("BehaviorEntity exists", BehaviorEntity is not None, "")
        results.record("BehaviorPurpose enum", BehaviorPurpose is not None, "")
        entities_found.append("BehaviorEntity")
    except ImportError as e:
        results.skip("BehaviorEntity", str(e))
    except Exception as e:
        results.record("BehaviorEntity", False, str(e))
    
    # Test SimEntity
    try:
        from entities.sim_entity import SimEntity
        results.record("SimEntity exists", SimEntity is not None, "")
        entities_found.append("SimEntity")
    except ImportError as e:
        results.skip("SimEntity", str(e))
    except Exception as e:
        results.record("SimEntity", False, str(e))
    
    # Test RelationshipGraph
    try:
        from entities.relationship_entity import RelationshipGraph
        results.record("RelationshipGraph exists", RelationshipGraph is not None, "")
        entities_found.append("RelationshipGraph")
    except ImportError as e:
        results.skip("RelationshipGraph", str(e))
    except Exception as e:
        results.record("RelationshipGraph", False, str(e))
    
    print(f"\n  📊 Entities: {', '.join(entities_found)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FOCUS COORDINATOR
# ═══════════════════════════════════════════════════════════════════════════════

def test_focus_coordinator():
    """Test Focus Coordinator - selection management."""
    print("\n" + "="*60)
    print("10. FOCUS COORDINATOR")
    print("="*60)
    
    try:
        from gui.focus import FocusCoordinator, Scope, Context, SelectionEntry
        
        coordinator = FocusCoordinator()
        
        # Test initial state
        results.record("Initial selection None", coordinator.current is None, "")
        
        # Test selection
        coordinator.select(
            resource_type="BHAV",
            resource_id=0x1234,
            label="Test Behavior",
            source_panel="test_panel"
        )
        
        results.record(
            "Selection stored",
            coordinator.current is not None,
            ""
        )
        results.record(
            "Selection type correct",
            coordinator.current.resource_type == "BHAV",
            f"Got {coordinator.current.resource_type}"
        )
        results.record(
            "Selection ID correct",
            coordinator.current.resource_id == 0x1234,
            f"Got {coordinator.current.resource_id}"
        )
        
        # Test scope enum
        results.record("Scope.ALL exists", Scope.ALL is not None, "")
        results.record("Context.FILE exists", Context.FILE is not None, "")
        
        print(f"\n  📊 Scopes: {[s.name for s in Scope]}")
        
    except ImportError as e:
        results.skip("Focus Coordinator", f"Import failed: {e}")
    except Exception as e:
        results.record("Focus Coordinator load", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ENGINE TOOLKIT
# ═══════════════════════════════════════════════════════════════════════════════

def test_engine_toolkit():
    """Test Engine Toolkit - semantic BHAV names."""
    print("\n" + "="*60)
    print("11. ENGINE TOOLKIT")
    print("="*60)
    
    try:
        from forensic.engine_toolkit import EngineToolkit
        
        toolkit = EngineToolkit()
        results.record("EngineToolkit created", toolkit is not None, "")
        
        # Test opcode lookup
        if hasattr(toolkit, 'get_opcode_name'):
            name = toolkit.get_opcode_name(0x0002)  # Expression
            results.record(
                "Opcode 0x0002 lookup",
                name is not None,
                f"Got: {name}"
            )
        
        # Test BHAV name lookup
        if hasattr(toolkit, 'get_bhav_name'):
            bhav_name = toolkit.get_bhav_name(0x100)
            results.record("BHAV name lookup", bhav_name is not None, f"Got: {bhav_name}")
        
        print(f"\n  📊 Engine toolkit functional")
        
    except ImportError as e:
        results.skip("Engine Toolkit", f"Import failed: {e}")
    except Exception as e:
        results.record("Engine Toolkit load", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 7. DATA FILES
# ═══════════════════════════════════════════════════════════════════════════════

def test_data_files():
    """Test data file presence."""
    print("\n" + "="*60)
    print("12. DATA FILES")
    print("="*60)
    
    data_dir = SUITE_DIR / "data"
    
    expected_files = [
        "unknowns_db.json",
        "opcodes_db.json",
        "global_behaviors.json"
    ]
    
    for filename in expected_files:
        filepath = data_dir / filename
        exists = filepath.exists()
        if exists:
            size = filepath.stat().st_size
            results.record(f"{filename}", True, f"Size: {size:,} bytes")
        else:
            results.record(f"{filename}", False, "File not found")
    
    print(f"\n  📊 Data directory: {data_dir}")


# ═══════════════════════════════════════════════════════════════════════════════
# 8. GUI PANELS INVENTORY
# ═══════════════════════════════════════════════════════════════════════════════

def test_panels_exist():
    """Test that all documented panels exist."""
    print("\n" + "="*60)
    print("13. GUI PANELS INVENTORY")
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
    
    print(f"\n  📊 Panels found: {found}/{len(expected_panels)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. CHUNK PARSERS INVENTORY
# ═══════════════════════════════════════════════════════════════════════════════

def test_chunk_parsers():
    """Test chunk parser availability."""
    print("\n" + "="*60)
    print("14. CHUNK PARSERS")
    print("="*60)
    
    chunks_dir = SRC_DIR / "formats" / "iff" / "chunks"
    
    critical_chunks = ["bhav.py", "objd.py", "objf.py", "ttab.py", "str_.py", "dgrp.py", "spr.py"]
    
    all_chunks = list(chunks_dir.glob("*.py")) if chunks_dir.exists() else []
    chunk_names = [c.name for c in all_chunks if not c.name.startswith("_")]
    
    for chunk in critical_chunks:
        exists = chunk in chunk_names
        results.record(f"Chunk: {chunk}", exists, "" if exists else "Missing")
    
    print(f"\n  📊 Total chunk parsers: {len(chunk_names)}")
    print(f"      {', '.join(sorted(chunk_names)[:15])}...")


# ═══════════════════════════════════════════════════════════════════════════════
# 15. FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def test_file_operations():
    """Test File Operations - backup, validation, extraction."""
    print("\n" + "="*60)
    print("15. FILE OPERATIONS")
    print("="*60)
    
    try:
        from core.file_operations import (
            BackupManager, ContainerValidator, ArchiveExtractor,
            IFFWriter, ChunkOperations, FileOpResult
        )
        
        # Test BackupManager creation
        bm = BackupManager()
        results.record("BackupManager created", bm is not None, "")
        
        # Test ContainerValidator
        results.record("ContainerValidator exists", ContainerValidator is not None, "")
        
        # Test IFFWriter
        results.record("IFFWriter exists", IFFWriter is not None, "")
        
        # Test ChunkOperations  
        results.record("ChunkOperations exists", ChunkOperations is not None, "")
        
        # Test FileOpResult
        result = FileOpResult(True, "Test message")
        results.record("FileOpResult created", result.success, "")
        
        print(f"\n  📊 File operations module loaded")
        
    except ImportError as e:
        results.skip("File Operations", f"Import failed: {e}")
    except Exception as e:
        results.record("File Operations", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 16. BHAV OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def test_bhav_operations():
    """Test BHAV Operations - editing, validation, serialization."""
    print("\n" + "="*60)
    print("16. BHAV OPERATIONS")
    print("="*60)
    
    try:
        from core.bhav_operations import (
            BHAVEditor, BHAVSerializer, BHAVValidator, BHAVImporter,
            BHAVOpResult, validate_bhav, serialize_bhav
        )
        
        # Test BHAVSerializer exists
        results.record("BHAVSerializer exists", BHAVSerializer is not None, "")
        
        # Test BHAVValidator exists
        results.record("BHAVValidator exists", BHAVValidator is not None, "")
        
        # Test BHAVEditor exists
        results.record("BHAVEditor exists", BHAVEditor is not None, "")
        
        # Test BHAVImporter exists
        results.record("BHAVImporter exists", BHAVImporter is not None, "")
        
        # Test BHAVOpResult
        result = BHAVOpResult(True, "Test", bhav_id=1234)
        results.record("BHAVOpResult created", result.bhav_id == 1234, "")
        
        print(f"\n  📊 BHAV operations module loaded")
        
    except ImportError as e:
        results.skip("BHAV Operations", f"Import failed: {e}")
    except Exception as e:
        results.record("BHAV Operations", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 17. IMPORT OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def test_import_operations():
    """Test Import Operations - chunk, sprite, asset import."""
    print("\n" + "="*60)
    print("17. IMPORT OPERATIONS")
    print("="*60)
    
    try:
        from core.import_operations import (
            ChunkImporter, SpriteImporter, DatabaseImporter, AssetImporter,
            ImportResult
        )
        
        # Test importers exist
        results.record("ChunkImporter exists", ChunkImporter is not None, "")
        results.record("SpriteImporter exists", SpriteImporter is not None, "")
        results.record("DatabaseImporter exists", DatabaseImporter is not None, "")
        results.record("AssetImporter exists", AssetImporter is not None, "")
        
        # Test ImportResult
        result = ImportResult(True, "Test", imported_count=5)
        results.record("ImportResult created", result.imported_count == 5, "")
        
        print(f"\n  📊 Import operations module loaded")
        
    except ImportError as e:
        results.skip("Import Operations", f"Import failed: {e}")
    except Exception as e:
        results.record("Import Operations", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════

def test_container_operations():
    """Test Container Operations - cache, split, merge, reindex."""
    print("\n" + "="*60)
    print("18. CONTAINER OPERATIONS")
    print("="*60)
    
    try:
        from core.container_operations import (
            CacheManager, clear_caches,
            HeaderNormalizer, normalize_headers,
            IndexRebuilder, rebuild_indexes,
            ContainerReindexer, reindex_container,
            IFFSplitter, split_iff,
            IFFMerger, merge_iff_files,
            FARWriter, write_far,
            ContainerOpResult
        )
        
        # Test cache manager
        cache_mgr = CacheManager.get()
        results.record("CacheManager singleton", cache_mgr is not None, "")
        
        # Test clear_caches function
        result = clear_caches()
        results.record("clear_caches works", result.success, result.message)
        
        # Test classes exist
        results.record("HeaderNormalizer exists", HeaderNormalizer is not None, "")
        results.record("IndexRebuilder exists", IndexRebuilder is not None, "")
        results.record("ContainerReindexer exists", ContainerReindexer is not None, "")
        results.record("IFFSplitter exists", IFFSplitter is not None, "")
        results.record("IFFMerger exists", IFFMerger is not None, "")
        results.record("FARWriter exists", FARWriter is not None, "")
        
        # Test ContainerOpResult
        result = ContainerOpResult(True, "Test", affected_chunks=10)
        results.record("ContainerOpResult created", result.affected_chunks == 10, "")
        
        print(f"\n  📊 Container operations module loaded")
        
    except ImportError as e:
        results.skip("Container Operations", f"Import failed: {e}")
    except Exception as e:
        results.record("Container Operations", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════

def test_save_mutations():
    """Test Save Mutations - sim, time, inventory, aspirations."""
    print("\n" + "="*60)
    print("19. SAVE MUTATIONS")
    print("="*60)
    
    try:
        from core.save_mutations import (
            SimManager, SimTemplate,
            TimeManager, modify_time,
            InventoryManager, modify_inventory,
            AspirationManager, modify_aspirations,
            MemoryManager, modify_memories,
            SaveMutationResult
        )
        
        # Test SimTemplate
        template = SimTemplate(first_name="Test", last_name="Sim")
        results.record("SimTemplate created", template.first_name == "Test", "")
        results.record("SimTemplate has personality", len(template.personality) > 0, "")
        
        # Test template serialization
        data = template.to_bytes()
        results.record("SimTemplate serializes", len(data) > 0, "")
        
        # Test classes exist
        results.record("SimManager exists", SimManager is not None, "")
        results.record("TimeManager exists", TimeManager is not None, "")
        results.record("InventoryManager exists", InventoryManager is not None, "")
        results.record("AspirationManager exists", AspirationManager is not None, "")
        results.record("MemoryManager exists", MemoryManager is not None, "")
        
        # Test SaveMutationResult
        result = SaveMutationResult(True, "Test", sim_id=123)
        results.record("SaveMutationResult created", result.sim_id == 123, "")
        
        print(f"\n  📊 Save mutations module loaded")
        
    except ImportError as e:
        results.skip("Save Mutations", f"Import failed: {e}")
    except Exception as e:
        results.record("Save Mutations", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════

def test_bhav_patching():
    """Test BHAV Patching - remap, rewire, patch."""
    print("\n" + "="*60)
    print("20. BHAV PATCHING")
    print("="*60)
    
    try:
        from core.bhav_patching import (
            BHAVScope, BHAVCallOpcodes,
            BHAVIDRemapper, remap_bhav_ids,
            BHAVCallRewirer, rewire_bhav_calls,
            GlobalBHAVPatcher, patch_global_bhav,
            SemiGlobalBHAVPatcher, patch_semi_global_bhav,
            ObjectBHAVPatcher, patch_object_bhav,
            BHAVPatchResult
        )
        
        # Test BHAVScope
        results.record("BHAVScope.is_global(0x50)", BHAVScope.is_global(0x50), "")
        results.record("BHAVScope.is_semi_global(0x200)", BHAVScope.is_semi_global(0x200), "")
        results.record("BHAVScope.is_object_local(0x1000)", BHAVScope.is_object_local(0x1000), "")
        results.record("BHAVScope.get_scope works", BHAVScope.get_scope(0x50) == 'global', "")
        
        # Test BHAVCallOpcodes
        results.record("BHAVCallOpcodes.is_call_opcode(0x0002)", BHAVCallOpcodes.is_call_opcode(0x0002), "")
        results.record("BHAVCallOpcodes has call info", BHAVCallOpcodes.get_call_info(0x0002) is not None, "")
        
        # Test classes exist
        results.record("BHAVIDRemapper exists", BHAVIDRemapper is not None, "")
        results.record("BHAVCallRewirer exists", BHAVCallRewirer is not None, "")
        results.record("GlobalBHAVPatcher exists", GlobalBHAVPatcher is not None, "")
        results.record("SemiGlobalBHAVPatcher exists", SemiGlobalBHAVPatcher is not None, "")
        results.record("ObjectBHAVPatcher exists", ObjectBHAVPatcher is not None, "")
        
        # Test BHAVPatchResult
        result = BHAVPatchResult(True, "Test", patches_applied=5, id_map={1: 2})
        results.record("BHAVPatchResult created", result.patches_applied == 5, "")
        results.record("BHAVPatchResult has id_map", len(result.id_map) == 1, "")
        
        print(f"\n  📊 BHAV patching module loaded")
        
    except ImportError as e:
        results.skip("BHAV Patching", f"Import failed: {e}")
    except Exception as e:
        results.record("BHAV Patching", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════

def test_mesh_export():
    """Test Mesh Export - decode, GLTF export."""
    print("\n" + "="*60)
    print("21. MESH EXPORT")
    print("="*60)
    
    try:
        from core.mesh_export import (
            Vertex, Face, Mesh,
            MeshDecoder, decode_mesh,
            GLTFExporter, export_mesh_gltf, export_mesh_glb,
            ChunkMeshExporter, export_chunk_mesh,
            MeshVisualizer, load_asset_to_3d,
            MeshExportResult
        )
        
        # Test data structures
        v = Vertex(1.0, 2.0, 3.0)
        results.record("Vertex created", v.x == 1.0, "")
        results.record("Vertex.to_list works", v.to_list() == [1.0, 2.0, 3.0], "")
        
        f = Face(0, 1, 2)
        results.record("Face created", f.v0 == 0, "")
        results.record("Face.to_list works", f.to_list() == [0, 1, 2], "")
        
        # Test Mesh
        mesh = Mesh(name="test")
        mesh.vertices.append(Vertex(0, 0, 0))
        mesh.vertices.append(Vertex(1, 0, 0))
        mesh.vertices.append(Vertex(0, 1, 0))
        mesh.faces.append(Face(0, 1, 2))
        
        results.record("Mesh created", mesh.vertex_count == 3, "")
        results.record("Mesh has faces", mesh.face_count == 1, "")
        
        bounds = mesh.get_bounds()
        results.record("Mesh.get_bounds works", bounds[0] == (0, 0, 0), "")
        
        # Test MeshVisualizer
        viz = MeshVisualizer(mesh)
        three_js = viz.to_three_js()
        results.record("MeshVisualizer.to_three_js works", 'vertices' in three_js, "")
        
        obj_str = viz.to_obj_string()
        results.record("MeshVisualizer.to_obj_string works", 'v 0' in obj_str, "")
        
        # Test classes exist
        results.record("MeshDecoder exists", MeshDecoder is not None, "")
        results.record("GLTFExporter exists", GLTFExporter is not None, "")
        results.record("ChunkMeshExporter exists", ChunkMeshExporter is not None, "")
        
        # Test MeshExportResult
        result = MeshExportResult(True, "Test", vertex_count=100, face_count=50)
        results.record("MeshExportResult created", result.vertex_count == 100, "")
        
        print(f"\n  📊 Mesh export module loaded")
        
    except ImportError as e:
        results.skip("Mesh Export", f"Import failed: {e}")
    except Exception as e:
        results.record("Mesh Export", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run all tests."""
    print("╔" + "═"*60 + "╗")
    print("║  SIMOBLITERATOR SUITE - COMPREHENSIVE TEST SUITE           ║")
    print("║  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "                                        ║")
    print("╚" + "═"*60 + "╝")
    
    # Run all test modules
    test_action_registry()
    test_mutation_pipeline()
    test_provenance()
    test_safety()
    test_bhav_executor()
    test_iff_parser()
    test_far_parser()
    test_dbpf_parser()
    test_entities()
    test_focus_coordinator()
    test_engine_toolkit()
    test_data_files()
    test_panels_exist()
    test_chunk_parsers()
    test_file_operations()
    test_bhav_operations()
    test_import_operations()
    test_container_operations()
    test_save_mutations()
    test_bhav_patching()
    test_mesh_export()
    
    # Print summary
    success = results.summary()
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {results.failed} TESTS FAILED")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
