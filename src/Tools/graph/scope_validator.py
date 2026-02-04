"""
Scope Validation Rules (Phase 3.3)

This is where trust is built. Powerful validations that catch real issues:
  - BHAV references global scope but object has no semi-global
  - Tuning reference points to non-existent BCON
  - TTAB points to orphaned BHAV
  
These warnings make modders say: "Oh wow, this tool actually understands Sims 1."
"""

from dataclasses import dataclass
from typing import List, Set, Dict, Optional
from enum import Enum

from .core import ResourceGraph, ResourceNode, Reference, TGI, ChunkScope, ReferenceKind


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"           # Critical issue, will cause crashes
    WARNING = "warning"       # Likely issue, may cause bugs
    INFO = "info"             # Suspicious pattern, investigate
    SUGGESTION = "suggestion" # Best practice recommendation


@dataclass
class ValidationIssue:
    """Represents a validation problem found in the resource graph."""
    severity: ValidationSeverity
    category: str             # "scope", "orphan", "missing_ref", etc.
    source_node: Optional[TGI]
    target_node: Optional[TGI]
    message: str              # Human-readable description
    suggestion: str = ""      # How to fix it
    
    def __str__(self) -> str:
        severity_icon = {
            ValidationSeverity.ERROR: "❌",
            ValidationSeverity.WARNING: "⚠️ ",
            ValidationSeverity.INFO: "ℹ️ ",
            ValidationSeverity.SUGGESTION: "💡",
        }
        icon = severity_icon.get(self.severity, "")
        
        msg = f"{icon} [{self.severity.value.upper()}] {self.message}"
        if self.suggestion:
            msg += f"\n   Suggestion: {self.suggestion}"
        return msg


class ScopeValidator:
    """
    Validates scope consistency and reference integrity.
    
    The Sims 1 has complex scope rules:
      - OBJECT scope: Local to the IFF file
      - SEMI_GLOBAL: From GLOB reference (shared library)
      - GLOBAL: From Global.iff (game-wide)
    
    Common issues:
      - BHAV calls global/semi-global without proper imports
      - References to non-existent resources
      - Critical resources (like TTAB actions) pointing to orphans
    """
    
    def __init__(self, graph: ResourceGraph):
        self.graph = graph
        self.issues: List[ValidationIssue] = []
    
    def validate_all(self) -> List[ValidationIssue]:
        """Run all validation rules and return issues found."""
        self.issues = []
        
        # Run each validation rule
        self._validate_bhav_scope_consistency()
        self._validate_missing_references()
        self._validate_orphaned_critical_resources()
        self._validate_tuning_constants()
        self._validate_interaction_integrity()
        self._validate_cross_scope_references()
        
        return self.issues
    
    def _validate_bhav_scope_consistency(self):
        """
        Validate BHAV scope rules.
        
        Rule: If BHAV calls global/semi-global BHAVs, the object should have
        a GLOB chunk or the BHAVs should exist in the same file.
        """
        # Find all BHAVs
        bhav_nodes = [n for n in self.graph.nodes.values() if n.chunk_type == "BHAV"]
        
        for bhav_node in bhav_nodes:
            if bhav_node.tgi not in self.graph._outbound_refs:
                continue
            
            # Check outbound BHAV references
            for ref in self.graph._outbound_refs[bhav_node.tgi]:
                if ref.target.chunk_type != "BHAV":
                    continue
                
                # If calling global/semi-global BHAV
                if ref.target.scope in [ChunkScope.GLOBAL, ChunkScope.SEMI_GLOBAL]:
                    # Check if object has GLOB chunk
                    has_glob = self._has_glob_chunk(bhav_node.owner_iff)
                    
                    if not has_glob and ref.target.scope == ChunkScope.SEMI_GLOBAL:
                        self.issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="scope",
                            source_node=bhav_node.tgi,
                            target_node=ref.target.tgi,
                            message=f"BHAV {bhav_node.tgi} calls semi-global {ref.target.tgi} but object has no GLOB chunk",
                            suggestion="Add GLOB chunk to import semi-global library, or make BHAV call local function",
                        ))
    
    def _validate_missing_references(self):
        """
        Detect references to non-existent resources.
        
        Rule: All references should point to nodes that exist in the graph.
        Phantom nodes (created from references but never parsed) indicate missing resources.
        """
        for tgi, node in self.graph.nodes.items():
            if node.is_phantom:
                # This node was referenced but never actually loaded
                # Find what references it
                inbound = self.graph._inbound_refs.get(tgi, [])
                
                if inbound:
                    ref = inbound[0]  # Show first reference
                    severity = self._get_missing_ref_severity(ref)
                    
                    self.issues.append(ValidationIssue(
                        severity=severity,
                        category="missing_ref",
                        source_node=ref.source.tgi,
                        target_node=tgi,
                        message=f"{ref.source.tgi} references missing {node.chunk_type} {tgi}",
                        suggestion=f"Add missing {node.chunk_type} chunk or fix reference to point to existing resource",
                    ))
    
    def _validate_orphaned_critical_resources(self):
        """
        Detect critical resources with no inbound references.
        
        Rule: Some resources (like TTAB action BHAVs) should always be referenced.
        If they're orphaned, they're effectively dead code.
        """
        # Find orphans
        orphans = self.graph.find_orphans()
        
        for orphan in orphans:
            # Check if this is a critical resource type
            is_critical = False
            reason = ""
            
            if orphan.chunk_type == "BHAV":
                # Check if this BHAV has outbound behavioral refs (it does something)
                if orphan.tgi in self.graph._outbound_refs:
                    behavioral_refs = [
                        ref for ref in self.graph._outbound_refs[orphan.tgi]
                        if ref.edge_kind == "behavioral"
                    ]
                    if behavioral_refs:
                        is_critical = True
                        reason = "BHAV contains code but is never called"
            
            elif orphan.chunk_type == "TTAB":
                is_critical = True
                reason = "TTAB (interaction table) is never referenced - dead interactions"
            
            elif orphan.chunk_type == "DGRP":
                is_critical = True
                reason = "DGRP (draw group) is never referenced - invisible graphics"
            
            if is_critical:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="orphan",
                    source_node=None,
                    target_node=orphan.tgi,
                    message=f"Orphaned {orphan.chunk_type} {orphan.tgi}: {reason}",
                    suggestion="Either add reference from OBJD/OBJf or remove unused resource",
                ))
    
    def _validate_tuning_constants(self):
        """
        Validate BCON/tuning references.
        
        Rule: Tuning references (BHAV → BCON) should point to existing constants.
        """
        # Check all BCON nodes - if phantom, it's a missing tuning constant
        for tgi, node in self.graph.nodes.items():
            if node.chunk_type == "BCON" and node.is_phantom:
                # Find what references it
                inbound = self.graph._inbound_refs.get(tgi, [])
                
                for ref in inbound:
                    if ref.edge_kind == "tuning":
                        self.issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="missing_tuning",
                            source_node=ref.source.tgi,
                            target_node=tgi,
                            message=f"{ref.source.tgi} references non-existent tuning constant {tgi}",
                            suggestion="Add missing BCON table or fix expression operand to use existing constant",
                        ))
    
    def _validate_interaction_integrity(self):
        """
        Validate TTAB (interaction table) integrity.
        
        Rule: TTAB action/guard functions should exist and not be orphaned.
        """
        ttab_nodes = [n for n in self.graph.nodes.values() if n.chunk_type == "TTAB"]
        
        for ttab_node in ttab_nodes:
            if ttab_node.tgi not in self.graph._outbound_refs:
                continue
            
            # Check TTAB → BHAV references
            for ref in self.graph._outbound_refs[ttab_node.tgi]:
                if ref.target.chunk_type != "BHAV":
                    continue
                
                # Check if target BHAV exists
                if ref.target.tgi not in self.graph.nodes:
                    severity = ValidationSeverity.ERROR
                    msg = f"TTAB {ttab_node.tgi} points to missing BHAV {ref.target.tgi}"
                    suggestion = "Add missing BHAV or fix TTAB to point to existing function"
                
                else:
                    # Check if BHAV is orphaned (only referenced by this TTAB)
                    inbound_refs = self.graph._inbound_refs.get(ref.target.tgi, [])
                    
                    # If BHAV is ONLY referenced by TTAB, it's a dedicated handler (OK)
                    # But if orphaned otherwise, warn
                    ttab_refs = [r for r in inbound_refs if r.source.chunk_type == "TTAB"]
                    other_refs = [r for r in inbound_refs if r.source.chunk_type != "TTAB"]
                    
                    if not other_refs and len(ttab_refs) == 1:
                        # This is a dedicated interaction handler (common pattern)
                        continue
                    
                    if not inbound_refs:
                        severity = ValidationSeverity.INFO
                        msg = f"TTAB {ttab_node.tgi} references orphaned BHAV {ref.target.tgi}"
                        suggestion = "Verify BHAV is correct interaction handler"
                        
                        self.issues.append(ValidationIssue(
                            severity=severity,
                            category="interaction",
                            source_node=ttab_node.tgi,
                            target_node=ref.target.tgi,
                            message=msg,
                            suggestion=suggestion,
                        ))
    
    def _validate_cross_scope_references(self):
        """
        Validate cross-scope reference rules.
        
        Rule: OBJECT scope shouldn't reference GLOBAL/SEMI_GLOBAL without imports.
        """
        for ref in self.graph.edges:
            # OBJECT → GLOBAL/SEMI_GLOBAL without proper import
            if ref.source.scope == ChunkScope.OBJECT:
                if ref.target.scope in [ChunkScope.GLOBAL, ChunkScope.SEMI_GLOBAL]:
                    # Check if source file has GLOB
                    has_glob = self._has_glob_chunk(ref.source.owner_iff)
                    
                    if not has_glob and ref.target.scope == ChunkScope.SEMI_GLOBAL:
                        self.issues.append(ValidationIssue(
                            severity=ValidationSeverity.INFO,
                            category="scope",
                            source_node=ref.source.tgi,
                            target_node=ref.target.tgi,
                            message=f"{ref.source.tgi} references semi-global {ref.target.tgi} without GLOB import",
                            suggestion="Add GLOB chunk to establish semi-global library link",
                        ))
    
    def _has_glob_chunk(self, iff_file: str) -> bool:
        """Check if an IFF file has a GLOB chunk."""
        if not iff_file:
            return False
        
        nodes_in_file = self.graph.get_nodes_in_file(iff_file)
        return any(node.chunk_type == "GLOB" for node in nodes_in_file)
    
    def _get_missing_ref_severity(self, ref: Reference) -> ValidationSeverity:
        """Determine severity of a missing reference based on context."""
        # HARD behavioral refs are critical
        if ref.kind == ReferenceKind.HARD and ref.edge_kind == "behavioral":
            return ValidationSeverity.ERROR
        
        # Visual refs are important but may have fallbacks
        if ref.edge_kind == "visual":
            return ValidationSeverity.WARNING
        
        # Tuning refs are critical
        if ref.edge_kind == "tuning":
            return ValidationSeverity.ERROR
        
        # SOFT refs are less critical
        if ref.kind == ReferenceKind.SOFT:
            return ValidationSeverity.INFO
        
        return ValidationSeverity.WARNING
    
    def print_summary(self):
        """Print human-readable validation summary."""
        if not self.issues:
            self.validate_all()
        
        print("=" * 80)
        print("SCOPE VALIDATION REPORT")
        print("=" * 80)
        print()
        
        if not self.issues:
            print("✓ No validation issues found")
            print()
            return
        
        # Count by severity
        errors = sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
        warnings = sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
        infos = sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO)
        suggestions = sum(1 for i in self.issues if i.severity == ValidationSeverity.SUGGESTION)
        
        print(f"Total Issues: {len(self.issues)}")
        print(f"  Errors:      {errors}")
        print(f"  Warnings:    {warnings}")
        print(f"  Info:        {infos}")
        print(f"  Suggestions: {suggestions}")
        print()
        
        # Group by category
        by_category: Dict[str, List[ValidationIssue]] = {}
        for issue in self.issues:
            if issue.category not in by_category:
                by_category[issue.category] = []
            by_category[issue.category].append(issue)
        
        print("-" * 80)
        print("Issues by Category:")
        print("-" * 80)
        print()
        
        for category, issues in sorted(by_category.items()):
            print(f"{category.upper()} ({len(issues)} issues):")
            print()
            
            # Show first 5 issues per category
            for issue in issues[:5]:
                print(f"  {issue}")
                print()
            
            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more {category} issues")
                print()
        
        print("=" * 80)
        print("TRUST INDICATORS")
        print("=" * 80)
        print()
        
        if errors == 0:
            print("✓ No critical errors - file is structurally sound")
        else:
            print(f"❌ {errors} critical error(s) - will likely cause crashes")
        
        if warnings == 0:
            print("✓ No warnings - scope rules followed correctly")
        else:
            print(f"⚠️  {warnings} warning(s) - likely bugs or dead code")
        
        print()
        print("=" * 80)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get all issues of a specific severity."""
        return [i for i in self.issues if i.severity == severity]
    
    def get_issues_by_category(self, category: str) -> List[ValidationIssue]:
        """Get all issues in a specific category."""
        return [i for i in self.issues if i.category == category]
    
    def get_issues_for_node(self, tgi: TGI) -> List[ValidationIssue]:
        """Get all issues involving a specific node."""
        return [
            i for i in self.issues
            if i.source_node == tgi or i.target_node == tgi
        ]
