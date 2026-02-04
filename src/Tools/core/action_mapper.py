"""
Action Mapper — CLI/Script Interface for SimObliterator
========================================================

For when someone says "fuck your UI" — this provides direct programmatic
access to ALL SimObliterator functionality without touching the GUI.

Usage Modes:
    1. Python API — Import and call functions directly
    2. CLI — Run from command line with arguments
    3. Batch — Process list of commands from file
    4. REPL — Interactive command loop

Example CLI:
    python -m src.Tools.core.action_mapper parse-bhav "path/to/file.iff" --id 0x1000
    python -m src.Tools.core.action_mapper list-objects "path/to/file.iff"
    python -m src.Tools.core.action_mapper export-report "path/to/file.iff" --format json

Example Python:
    from src.Tools.core.action_mapper import ActionMapper
    mapper = ActionMapper()
    result = mapper.execute("parse-bhav", file="path/to/file.iff", bhav_id=0x1000)
"""

import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable, Optional, Union
from enum import Enum


class OutputFormat(Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "md"
    CSV = "csv"


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    action: str
    data: Any = None
    error: str = ""
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "action": self.action,
            "data": self.data,
            "error": self.error,
            "warnings": self.warnings,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    def to_text(self) -> str:
        if not self.success:
            return f"ERROR: {self.error}"
        if isinstance(self.data, dict):
            lines = [f"{k}: {v}" for k, v in self.data.items()]
            return "\n".join(lines)
        if isinstance(self.data, list):
            return "\n".join(str(item) for item in self.data)
        return str(self.data)


@dataclass
class ActionSpec:
    """Specification for a mapped action."""
    name: str
    handler: Callable
    description: str
    category: str
    args: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


class ActionMapper:
    """
    Maps action names to handler functions.
    
    This is the "fuck the UI" interface — everything you can do in the
    GUI, you can do here with simple function calls or CLI commands.
    """
    
    def __init__(self):
        self._actions: Dict[str, ActionSpec] = {}
        self._output_format = OutputFormat.TEXT
        self._verbose = False
        self._register_all_actions()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════
    
    def execute(self, action_name: str, **kwargs) -> ActionResult:
        """
        Execute an action by name.
        
        Args:
            action_name: Name of action (e.g., "parse-bhav", "list-objects")
            **kwargs: Action-specific arguments
            
        Returns:
            ActionResult with success status and data
        """
        action_name = action_name.lower().replace("_", "-")
        
        if action_name not in self._actions:
            return ActionResult(
                success=False,
                action=action_name,
                error=f"Unknown action: {action_name}. Use 'list-actions' to see available actions."
            )
        
        spec = self._actions[action_name]
        
        try:
            result = spec.handler(**kwargs)
            return ActionResult(success=True, action=action_name, data=result)
        except Exception as e:
            return ActionResult(success=False, action=action_name, error=str(e))
    
    def list_actions(self, category: str = None) -> List[Dict[str, str]]:
        """List all available actions."""
        actions = []
        for name, spec in sorted(self._actions.items()):
            if category and spec.category != category:
                continue
            actions.append({
                "name": name,
                "description": spec.description,
                "category": spec.category,
            })
        return actions
    
    def list_categories(self) -> List[str]:
        """List all action categories."""
        return sorted(set(spec.category for spec in self._actions.values()))
    
    def get_action_help(self, action_name: str) -> Optional[Dict]:
        """Get detailed help for an action."""
        spec = self._actions.get(action_name)
        if not spec:
            return None
        return {
            "name": spec.name,
            "description": spec.description,
            "category": spec.category,
            "arguments": spec.args,
            "examples": spec.examples,
        }
    
    def run_batch(self, commands: List[Dict[str, Any]]) -> List[ActionResult]:
        """
        Run a batch of commands.
        
        Args:
            commands: List of {"action": "...", "args": {...}} dicts
            
        Returns:
            List of ActionResults
        """
        results = []
        for cmd in commands:
            action = cmd.get("action", "")
            args = cmd.get("args", {})
            result = self.execute(action, **args)
            results.append(result)
            if not result.success and cmd.get("stop_on_error", False):
                break
        return results
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ACTION REGISTRATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _register_all_actions(self):
        """Register all available actions."""
        
        # ─────────────────────────────────────────────────────────────────────
        # FILE OPERATIONS
        # ─────────────────────────────────────────────────────────────────────
        
        self._register("load-iff", self._load_iff, "file",
            "Load and parse an IFF file",
            args=[{"name": "file", "type": "path", "required": True}],
            examples=["load-iff path/to/object.iff"])
        
        self._register("list-chunks", self._list_chunks, "file",
            "List all chunks in an IFF file",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "type_filter", "type": "str", "required": False},
            ],
            examples=["list-chunks object.iff", "list-chunks object.iff --type BHAV"])
        
        self._register("extract-chunk", self._extract_chunk, "file",
            "Extract a specific chunk to file",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "chunk_type", "type": "str", "required": True},
                {"name": "chunk_id", "type": "int", "required": True},
                {"name": "output", "type": "path", "required": False},
            ])
        
        self._register("validate-iff", self._validate_iff, "file",
            "Validate IFF structure and report issues",
            args=[{"name": "file", "type": "path", "required": True}])
        
        # ─────────────────────────────────────────────────────────────────────
        # OBJECT ANALYSIS
        # ─────────────────────────────────────────────────────────────────────
        
        self._register("list-objects", self._list_objects, "object",
            "List all OBJDs in an IFF (handles multi-object files)",
            args=[{"name": "file", "type": "path", "required": True}],
            examples=["list-objects multitile.iff"])
        
        self._register("get-object-info", self._get_object_info, "object",
            "Get detailed info for an OBJD",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "objd_id", "type": "int", "required": False},
            ])
        
        self._register("scan-id-conflicts", self._scan_id_conflicts, "object",
            "Scan for ID conflicts across files",
            args=[
                {"name": "files", "type": "list[path]", "required": True},
                {"name": "scope", "type": "str", "required": False},
            ])
        
        # ─────────────────────────────────────────────────────────────────────
        # BHAV OPERATIONS
        # ─────────────────────────────────────────────────────────────────────
        
        self._register("parse-bhav", self._parse_bhav, "bhav",
            "Parse and disassemble a BHAV function",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "bhav_id", "type": "int", "required": True},
            ],
            examples=["parse-bhav object.iff --bhav-id 0x1000"])
        
        self._register("list-bhavs", self._list_bhavs, "bhav",
            "List all BHAVs in a file",
            args=[{"name": "file", "type": "path", "required": True}])
        
        self._register("bhav-call-graph", self._bhav_call_graph, "bhav",
            "Generate call graph for BHAVs",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "format", "type": "str", "required": False, "default": "text"},
            ],
            examples=["bhav-call-graph object.iff --format dot"])
        
        self._register("analyze-variables", self._analyze_variables, "bhav",
            "Analyze variable usage in a BHAV",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "bhav_id", "type": "int", "required": True},
            ])
        
        self._register("create-bhav", self._create_bhav, "bhav",
            "Create a new BHAV from instruction specs",
            args=[
                {"name": "instructions", "type": "list", "required": True},
                {"name": "bhav_id", "type": "int", "required": True},
                {"name": "output", "type": "path", "required": True},
            ])
        
        self._register("create-instruction", self._create_instruction, "bhav",
            "Create a single BHAV instruction",
            args=[
                {"name": "opcode", "type": "int", "required": True},
                {"name": "operands", "type": "dict", "required": False},
            ],
            examples=["create-instruction 0x02 --dest-scope 6 --dest-index 0 --operator 0"])
        
        # ─────────────────────────────────────────────────────────────────────
        # TTAB OPERATIONS
        # ─────────────────────────────────────────────────────────────────────
        
        self._register("parse-ttab", self._parse_ttab, "ttab",
            "Parse TTAB with all fields including autonomy",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "ttab_id", "type": "int", "required": False},
            ])
        
        self._register("list-interactions", self._list_interactions, "ttab",
            "List all interactions in a TTAB",
            args=[{"name": "file", "type": "path", "required": True}])
        
        self._register("get-autonomy", self._get_autonomy, "ttab",
            "Get autonomy values for all interactions",
            args=[{"name": "file", "type": "path", "required": True}])
        
        self._register("set-autonomy", self._set_autonomy, "ttab",
            "Set autonomy value for an interaction",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "interaction_index", "type": "int", "required": True},
                {"name": "autonomy", "type": "int", "required": True},
                {"name": "output", "type": "path", "required": False},
            ])
        
        # ─────────────────────────────────────────────────────────────────────
        # STRING OPERATIONS
        # ─────────────────────────────────────────────────────────────────────
        
        self._register("parse-str", self._parse_str, "string",
            "Parse STR# chunk with language awareness",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "str_id", "type": "int", "required": False},
            ])
        
        self._register("list-strings", self._list_strings, "string",
            "List all strings in an IFF",
            args=[{"name": "file", "type": "path", "required": True}])
        
        self._register("localization-audit", self._localization_audit, "string",
            "Check for missing language slots",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "level", "type": "str", "required": False, "default": "warn_catalog"},
            ])
        
        self._register("find-str-references", self._find_str_references, "string",
            "Find all references to STR# chunks",
            args=[{"name": "file", "type": "path", "required": True}])
        
        # ─────────────────────────────────────────────────────────────────────
        # SLOT OPERATIONS
        # ─────────────────────────────────────────────────────────────────────
        
        self._register("parse-slot", self._parse_slot, "slot",
            "Parse SLOT routing slots",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "slot_id", "type": "int", "required": False},
            ])
        
        self._register("list-slots", self._list_slots, "slot",
            "List all routing slots",
            args=[{"name": "file", "type": "path", "required": True}])
        
        self._register("add-slot", self._add_slot, "slot",
            "Add a routing slot",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "slot_type", "type": "int", "required": True},
                {"name": "x", "type": "float", "required": True},
                {"name": "y", "type": "float", "required": True},
                {"name": "z", "type": "float", "required": False, "default": 0.0},
                {"name": "facing", "type": "float", "required": False, "default": 0.0},
            ])
        
        # ─────────────────────────────────────────────────────────────────────
        # EXPORT / REPORTS
        # ─────────────────────────────────────────────────────────────────────
        
        self._register("export-report", self._export_report, "export",
            "Export comprehensive IFF report",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "format", "type": "str", "required": False, "default": "json"},
                {"name": "output", "type": "path", "required": False},
            ])
        
        self._register("export-bhav-dot", self._export_bhav_dot, "export",
            "Export BHAV call graph as DOT",
            args=[
                {"name": "file", "type": "path", "required": True},
                {"name": "output", "type": "path", "required": False},
            ])
        
        self._register("export-opcodes", self._export_opcodes, "export",
            "Export opcode database",
            args=[
                {"name": "format", "type": "str", "required": False, "default": "json"},
            ])
        
        # ─────────────────────────────────────────────────────────────────────
        # META / HELP
        # ─────────────────────────────────────────────────────────────────────
        
        self._register("list-actions", lambda: self.list_actions(), "meta",
            "List all available actions")
        
        self._register("help", self._help_action, "meta",
            "Get help for an action",
            args=[{"name": "action", "type": "str", "required": True}])
        
        self._register("version", lambda: {"version": self._get_version()}, "meta",
            "Show version info")
    
    def _register(self, name: str, handler: Callable, category: str,
                  description: str, args: List[Dict] = None, examples: List[str] = None):
        """Register an action."""
        self._actions[name] = ActionSpec(
            name=name,
            handler=handler,
            description=description,
            category=category,
            args=args or [],
            examples=examples or [],
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ACTION HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_iff(self, file: str) -> Dict:
        """Load an IFF file."""
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        return {
            "file": file,
            "chunk_count": len(reader.chunks),
            "chunks": [{"type": c.type_code, "id": c.chunk_id, "size": len(c.chunk_data)} 
                       for c in reader.chunks],
        }
    
    def _list_chunks(self, file: str, type_filter: str = None) -> List[Dict]:
        """List chunks in IFF."""
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        chunks = []
        for c in reader.chunks:
            if type_filter and c.type_code != type_filter.upper():
                continue
            chunks.append({
                "type": c.type_code,
                "id": c.chunk_id,
                "id_hex": f"0x{c.chunk_id:04X}",
                "size": len(c.chunk_data),
            })
        return chunks
    
    def _extract_chunk(self, file: str, chunk_type: str, chunk_id: int, output: str = None) -> Dict:
        """Extract a chunk."""
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        for c in reader.chunks:
            if c.type_code == chunk_type.upper() and c.chunk_id == chunk_id:
                if output:
                    Path(output).write_bytes(c.chunk_data)
                    return {"extracted": True, "output": output, "size": len(c.chunk_data)}
                return {"data": c.chunk_data.hex(), "size": len(c.chunk_data)}
        raise ValueError(f"Chunk {chunk_type} {chunk_id} not found")
    
    def _validate_iff(self, file: str) -> Dict:
        """Validate IFF structure."""
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        issues = []
        # Basic validation
        for c in reader.chunks:
            if len(c.type_code) != 4:
                issues.append(f"Invalid type code: {c.type_code}")
        return {
            "valid": len(issues) == 0,
            "chunk_count": len(reader.chunks),
            "issues": issues,
        }
    
    def _list_objects(self, file: str) -> List[Dict]:
        """List OBJDs in file."""
        from ..core.ttab_editor import build_multi_object_context
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        ctx = build_multi_object_context(reader, file)
        return [
            {
                "objd_id": obj.objd_id,
                "name": obj.name,
                "guid": f"0x{obj.guid:08X}" if obj.guid else None,
                "ttab_id": obj.ttab_id,
            }
            for obj in ctx.objects
        ]
    
    def _get_object_info(self, file: str, objd_id: int = None) -> Dict:
        """Get OBJD info."""
        from ..core.chunk_parsers import parse_objd
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        for c in reader.chunks:
            if c.type_code == 'OBJD':
                if objd_id is None or c.chunk_id == objd_id:
                    objd = parse_objd(c.chunk_data, c.chunk_id)
                    return {
                        "id": c.chunk_id,
                        "tree_table_id": objd.tree_table_id if objd else None,
                        "catalog_str_id": objd.catalog_strings_id if objd else None,
                    }
        raise ValueError(f"OBJD {objd_id} not found")
    
    def _scan_id_conflicts(self, files: List[str], scope: str = "all") -> List[Dict]:
        """Scan for ID conflicts."""
        from ..core.id_conflict_scanner import IDConflictScanner
        scanner = IDConflictScanner()
        for f in files:
            scanner.scan_file(f)
        return [c.to_dict() for c in scanner.conflicts]
    
    def _parse_bhav(self, file: str, bhav_id: int) -> Dict:
        """Parse a BHAV."""
        from ..core.bhav_disassembler import disassemble_bhav
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        for c in reader.chunks:
            if c.type_code == 'BHAV' and c.chunk_id == bhav_id:
                result = disassemble_bhav(c.chunk_data, c.chunk_id)
                return result.to_dict() if hasattr(result, 'to_dict') else {"raw": str(result)}
        raise ValueError(f"BHAV 0x{bhav_id:04X} not found")
    
    def _list_bhavs(self, file: str) -> List[Dict]:
        """List BHAVs."""
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        bhavs = []
        for c in reader.chunks:
            if c.type_code == 'BHAV':
                bhavs.append({
                    "id": c.chunk_id,
                    "id_hex": f"0x{c.chunk_id:04X}",
                    "size": len(c.chunk_data),
                })
        return bhavs
    
    def _bhav_call_graph(self, file: str, format: str = "text") -> Union[str, Dict]:
        """Generate call graph."""
        from ..core.bhav_call_graph import CallGraphBuilder
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        builder = CallGraphBuilder()
        graph = builder.build_from_iff(reader)
        if format == "dot":
            return graph.to_dot()
        return graph.to_dict() if hasattr(graph, 'to_dict') else {"nodes": len(graph.nodes)}
    
    def _analyze_variables(self, file: str, bhav_id: int) -> Dict:
        """Analyze BHAV variables."""
        from ..core.variable_analyzer import BHAVVariableAnalyzer
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        for c in reader.chunks:
            if c.type_code == 'BHAV' and c.chunk_id == bhav_id:
                analyzer = BHAVVariableAnalyzer()
                result = analyzer.analyze(c.chunk_data)
                return result.to_dict() if hasattr(result, 'to_dict') else {"analyzed": True}
        raise ValueError(f"BHAV 0x{bhav_id:04X} not found")
    
    def _create_bhav(self, instructions: List[Dict], bhav_id: int, output: str) -> Dict:
        """Create a new BHAV."""
        from ..core.bhav_authoring import BHAVFactory, BHAVInstruction
        instrs = []
        for spec in instructions:
            instr = BHAVFactory.create_instruction(
                spec["opcode"],
                true_target=spec.get("true_target", 254),
                false_target=spec.get("false_target", 255),
                **spec.get("operands", {})
            )
            instrs.append(instr)
        data = BHAVFactory.create_bhav(bhav_id, instrs)
        Path(output).write_bytes(data)
        return {"created": True, "output": output, "instruction_count": len(instrs)}
    
    def _create_instruction(self, opcode: int, operands: Dict = None) -> Dict:
        """Create a single instruction."""
        from ..core.bhav_authoring import BHAVFactory
        instr = BHAVFactory.create_instruction(opcode, **(operands or {}))
        return {
            "opcode": opcode,
            "opcode_hex": instr.opcode_hex,
            "operand_hex": instr.operand.hex(),
            "bytes": instr.to_bytes().hex(),
        }
    
    def _parse_ttab(self, file: str, ttab_id: int = None) -> Dict:
        """Parse TTAB."""
        from ..core.ttab_editor import TTABParser
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        for c in reader.chunks:
            if c.type_code == 'TTAB':
                if ttab_id is None or c.chunk_id == ttab_id:
                    result = TTABParser.parse(c.chunk_data, c.chunk_id)
                    return result.get_summary()
        raise ValueError("No TTAB found")
    
    def _list_interactions(self, file: str) -> List[Dict]:
        """List TTAB interactions."""
        from ..core.ttab_editor import TTABParser
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        interactions = []
        for c in reader.chunks:
            if c.type_code == 'TTAB':
                result = TTABParser.parse(c.chunk_data, c.chunk_id)
                for inter in result.interactions:
                    interactions.append(inter.to_dict())
        return interactions
    
    def _get_autonomy(self, file: str) -> List[Dict]:
        """Get autonomy values."""
        from ..core.ttab_editor import TTABParser
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        autonomy_list = []
        for c in reader.chunks:
            if c.type_code == 'TTAB':
                result = TTABParser.parse(c.chunk_data, c.chunk_id)
                for inter in result.interactions:
                    autonomy_list.append({
                        "ttab_id": c.chunk_id,
                        "index": inter.index,
                        "tta_index": inter.tta_index,
                        "autonomy": inter.autonomy_threshold,
                        "can_be_autonomous": inter.has_autonomy(),
                    })
        return autonomy_list
    
    def _set_autonomy(self, file: str, interaction_index: int, autonomy: int, output: str = None) -> Dict:
        """Set autonomy value."""
        from ..core.ttab_editor import TTABParser, TTABSerializer
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        for c in reader.chunks:
            if c.type_code == 'TTAB':
                result = TTABParser.parse(c.chunk_data, c.chunk_id)
                inter = result.get_interaction(interaction_index)
                if inter:
                    old_value = inter.autonomy_threshold
                    inter.autonomy_threshold = autonomy
                    new_data = TTABSerializer.serialize(result)
                    if output:
                        Path(output).write_bytes(new_data)
                    return {
                        "updated": True,
                        "index": interaction_index,
                        "old_autonomy": old_value,
                        "new_autonomy": autonomy,
                    }
        raise ValueError(f"Interaction {interaction_index} not found")
    
    def _parse_str(self, file: str, str_id: int = None) -> Dict:
        """Parse STR#."""
        from ..core.str_parser import STRParser
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        for c in reader.chunks:
            if c.type_code == 'STR#':
                if str_id is None or c.chunk_id == str_id:
                    result = STRParser.parse(c.chunk_data)
                    return {
                        "chunk_id": c.chunk_id,
                        "format": result.format_code,
                        "entry_count": len(result.entries),
                        "entries": [e.get_value(0) for e in result.entries],
                    }
        raise ValueError("No STR# found")
    
    def _list_strings(self, file: str) -> List[Dict]:
        """List all strings."""
        from ..core.str_parser import STRParser
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        strings = []
        for c in reader.chunks:
            if c.type_code == 'STR#':
                result = STRParser.parse(c.chunk_data)
                strings.append({
                    "chunk_id": c.chunk_id,
                    "entry_count": len(result.entries),
                })
        return strings
    
    def _localization_audit(self, file: str, level: str = "warn_catalog") -> Dict:
        """Audit localization."""
        from ..core.localization_audit import LocalizationAuditor, AuditLevel
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        auditor = LocalizationAuditor(getattr(AuditLevel, level.upper(), AuditLevel.WARN_CATALOG))
        issues = auditor.audit_file(reader)
        return {
            "file": file,
            "issue_count": len(issues),
            "issues": [i.to_dict() for i in issues] if hasattr(issues[0], 'to_dict') else issues,
        } if issues else {"file": file, "issue_count": 0, "issues": []}
    
    def _find_str_references(self, file: str) -> List[Dict]:
        """Find STR# references."""
        from ..core.str_reference_scanner import STRReferenceScanner
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        scanner = STRReferenceScanner()
        result = scanner.scan(reader)
        return [r.to_dict() for r in result.references] if hasattr(result.references[0], 'to_dict') else []
    
    def _parse_slot(self, file: str, slot_id: int = None) -> Dict:
        """Parse SLOT."""
        from ..core.slot_editor import SLOTParser
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        for c in reader.chunks:
            if c.type_code == 'SLOT':
                if slot_id is None or c.chunk_id == slot_id:
                    result = SLOTParser.parse(c.chunk_data, c.chunk_id)
                    return result.get_summary()
        raise ValueError("No SLOT found")
    
    def _list_slots(self, file: str) -> List[Dict]:
        """List routing slots."""
        from ..core.slot_editor import SLOTParser
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        slots = []
        for c in reader.chunks:
            if c.type_code == 'SLOT':
                result = SLOTParser.parse(c.chunk_data, c.chunk_id)
                for slot in result.slots:
                    slots.append(slot.to_dict())
        return slots
    
    def _add_slot(self, file: str, slot_type: int, x: float, y: float, 
                  z: float = 0.0, facing: float = 0.0) -> Dict:
        """Add a slot."""
        from ..core.slot_editor import SLOTParser, SLOTEditor, SLOTSerializer, SlotPosition
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        for c in reader.chunks:
            if c.type_code == 'SLOT':
                result = SLOTParser.parse(c.chunk_data, c.chunk_id)
                pos = SlotPosition(x=x, y=y, z=z, facing=facing)
                new_slot = SLOTEditor.add_slot(result, slot_type, pos)
                return {
                    "added": True,
                    "index": new_slot.index,
                    "type": new_slot.type_name,
                }
        raise ValueError("No SLOT chunk to modify")
    
    def _export_report(self, file: str, format: str = "json", output: str = None) -> Dict:
        """Export comprehensive report."""
        from ..core.iff_reader import IFFReader
        reader = IFFReader(file)
        report = {
            "file": file,
            "chunks": [{"type": c.type_code, "id": c.chunk_id} for c in reader.chunks],
            "summary": {
                "total_chunks": len(reader.chunks),
                "by_type": {},
            }
        }
        for c in reader.chunks:
            t = c.type_code
            report["summary"]["by_type"][t] = report["summary"]["by_type"].get(t, 0) + 1
        
        if output:
            Path(output).write_text(json.dumps(report, indent=2))
            return {"exported": True, "output": output}
        return report
    
    def _export_bhav_dot(self, file: str, output: str = None) -> str:
        """Export BHAV call graph as DOT."""
        result = self._bhav_call_graph(file, "dot")
        if output:
            Path(output).write_text(result)
            return f"Exported to {output}"
        return result
    
    def _export_opcodes(self, format: str = "json") -> Dict:
        """Export opcode database."""
        from ..core.opcode_loader import load_opcodes
        opcodes = load_opcodes()
        return {"opcode_count": len(opcodes), "opcodes": opcodes}
    
    def _help_action(self, action: str) -> Optional[Dict]:
        """Get help for action."""
        return self.get_action_help(action)
    
    def _get_version(self) -> str:
        """Get version."""
        try:
            return Path("VERSION").read_text().strip()
        except:
            return "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="simobliterator",
        description="SimObliterator CLI — For when you say 'fuck the UI'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s list-actions
    %(prog)s list-chunks path/to/object.iff
    %(prog)s parse-bhav path/to/object.iff --bhav-id 0x1000
    %(prog)s get-autonomy path/to/object.iff
    %(prog)s export-report path/to/object.iff --format json
    
Use '%(prog)s help <action>' for detailed help on any action.
        """
    )
    
    parser.add_argument("action", help="Action to perform (use 'list-actions' to see all)")
    parser.add_argument("file", nargs="?", help="Target file (if action requires one)")
    parser.add_argument("--format", "-f", default="text", choices=["text", "json", "md"],
                        help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--bhav-id", type=lambda x: int(x, 0), help="BHAV ID (hex OK)")
    parser.add_argument("--objd-id", type=lambda x: int(x, 0), help="OBJD ID (hex OK)")
    parser.add_argument("--ttab-id", type=lambda x: int(x, 0), help="TTAB ID (hex OK)")
    parser.add_argument("--str-id", type=lambda x: int(x, 0), help="STR# ID (hex OK)")
    parser.add_argument("--slot-id", type=lambda x: int(x, 0), help="SLOT ID (hex OK)")
    parser.add_argument("--chunk-type", help="Chunk type (e.g., BHAV, OBJD)")
    parser.add_argument("--chunk-id", type=lambda x: int(x, 0), help="Chunk ID (hex OK)")
    parser.add_argument("--type-filter", help="Filter by type")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    mapper = ActionMapper()
    
    # Build kwargs from args
    kwargs = {}
    if args.file:
        kwargs["file"] = args.file
    if args.bhav_id:
        kwargs["bhav_id"] = args.bhav_id
    if args.objd_id:
        kwargs["objd_id"] = args.objd_id
    if args.ttab_id:
        kwargs["ttab_id"] = args.ttab_id
    if args.str_id:
        kwargs["str_id"] = args.str_id
    if args.slot_id:
        kwargs["slot_id"] = args.slot_id
    if args.chunk_type:
        kwargs["chunk_type"] = args.chunk_type
    if args.chunk_id:
        kwargs["chunk_id"] = args.chunk_id
    if args.output:
        kwargs["output"] = args.output
    if args.type_filter:
        kwargs["type_filter"] = args.type_filter
    if args.format != "text":
        kwargs["format"] = args.format
    
    result = mapper.execute(args.action, **kwargs)
    
    if args.format == "json":
        print(result.to_json())
    else:
        print(result.to_text())
    
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
