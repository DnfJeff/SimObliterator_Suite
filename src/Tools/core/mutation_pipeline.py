"""
Mutation Pipeline - Write Barrier Layer

From Architectural Principles:
  All writes go through a single mutation pipeline that can:
  - validate
  - diff  
  - reject
  - annotate risk

This is the ONLY path to modify game data.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict, Callable
from enum import Enum
from datetime import datetime
import json


class MutationMode(Enum):
    """Mutation modes with increasing write access."""
    INSPECT = "inspect"     # Read-only, no writes possible
    PREVIEW = "preview"     # Show diff, no commit
    MUTATE = "mutate"       # Full write with audit


class MutationResult(Enum):
    """Result of attempting a mutation."""
    SUCCESS = "success"
    REJECTED_SAFETY = "rejected_safety"
    REJECTED_VALIDATION = "rejected_validation"
    REJECTED_USER = "rejected_user"
    PREVIEW_ONLY = "preview_only"


@dataclass
class MutationDiff:
    """Represents a proposed change."""
    field_path: str         # e.g., "objd.price" or "bhav.instructions[3].opcode"
    old_value: Any
    new_value: Any
    display_old: str = ""   # Human-readable
    display_new: str = ""


@dataclass
class MutationRequest:
    """A request to mutate data."""
    
    # What
    target_type: str        # 'chunk', 'field', 'instruction'
    target_id: Any          # Chunk ID, field name, etc.
    target_file: str        # Source file path
    
    # Change
    diffs: List[MutationDiff] = field(default_factory=list)
    
    # Context
    reason: str = ""        # Why is this change being made?
    source_panel: str = ""  # Which panel initiated?
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str = ""


@dataclass
class MutationAudit:
    """Audit record for a mutation."""
    request: MutationRequest
    result: MutationResult
    safety_level: str = ""
    risk_notes: List[str] = field(default_factory=list)
    approved_by: str = ""   # "auto" or "user"
    commit_time: Optional[datetime] = None


class MutationPipeline:
    """
    The Write Barrier Layer.
    
    All modifications to game data MUST flow through here.
    This ensures:
    1. Validation before write
    2. Diff preview available
    3. Safety gates enforced
    4. Audit trail maintained
    """
    
    _instance = None
    
    def __init__(self):
        self.mode = MutationMode.INSPECT  # Start read-only
        self.pending: List[MutationRequest] = []
        self.history: List[MutationAudit] = []
        self.validators: List[Callable] = []
        self.commit_hooks: List[Callable] = []
        
        # Load safety API if available
        try:
            from Tools.core.safety import is_safe_to_edit, SafetyLevel
            self._safety_check = is_safe_to_edit
            self._safety_available = True
        except ImportError:
            self._safety_check = None
            self._safety_available = False
    
    @classmethod
    def get(cls) -> "MutationPipeline":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    # ─────────────────────────────────────────────────────────────
    # MODE CONTROL
    # ─────────────────────────────────────────────────────────────
    
    def set_mode(self, mode: MutationMode):
        """Set the mutation mode."""
        self.mode = mode
    
    def is_writable(self) -> bool:
        """Can we write in current mode?"""
        return self.mode == MutationMode.MUTATE
    
    def is_preview(self) -> bool:
        """Are we in preview mode?"""
        return self.mode == MutationMode.PREVIEW
    
    # ─────────────────────────────────────────────────────────────
    # MUTATION FLOW
    # ─────────────────────────────────────────────────────────────
    
    def propose(self, request: MutationRequest) -> MutationAudit:
        """
        Propose a mutation. Returns audit with result.
        
        In INSPECT mode: Rejected
        In PREVIEW mode: Returns diff, no commit
        In MUTATE mode: Validates, commits if safe
        """
        audit = MutationAudit(
            request=request,
            result=MutationResult.REJECTED_SAFETY,
        )
        
        # INSPECT mode - reject all writes
        if self.mode == MutationMode.INSPECT:
            audit.result = MutationResult.REJECTED_SAFETY
            audit.risk_notes.append("Mode is INSPECT - no writes allowed")
            self.history.append(audit)
            return audit
        
        # Run safety check
        if self._safety_available and self._safety_check:
            # Create a mock chunk for safety check
            safety_result = self._safety_check(
                type('Chunk', (), {'chunk_type': request.target_type})(),
                request.target_file
            )
            if safety_result:
                audit.safety_level = safety_result.level.value
                if safety_result.level.value in ("dangerous", "blocked"):
                    audit.result = MutationResult.REJECTED_SAFETY
                    audit.risk_notes.append(f"Safety: {safety_result.summary()}")
                    self.history.append(audit)
                    return audit
                elif safety_result.level.value in ("caution", "warning"):
                    audit.risk_notes.append(f"⚠ {safety_result.summary()}")
        
        # Run custom validators
        for validator in self.validators:
            try:
                valid, reason = validator(request)
                if not valid:
                    audit.result = MutationResult.REJECTED_VALIDATION
                    audit.risk_notes.append(f"Validation failed: {reason}")
                    self.history.append(audit)
                    return audit
            except Exception as e:
                audit.risk_notes.append(f"Validator error: {e}")
        
        # PREVIEW mode - return diff without commit
        if self.mode == MutationMode.PREVIEW:
            audit.result = MutationResult.PREVIEW_ONLY
            audit.approved_by = "preview"
            self.pending.append(request)
            self.history.append(audit)
            return audit
        
        # MUTATE mode - commit
        try:
            self._commit(request)
            audit.result = MutationResult.SUCCESS
            audit.approved_by = "auto"
            audit.commit_time = datetime.now()
            
            # Run commit hooks
            for hook in self.commit_hooks:
                try:
                    hook(request, audit)
                except:
                    pass
                    
        except Exception as e:
            audit.result = MutationResult.REJECTED_VALIDATION
            audit.risk_notes.append(f"Commit failed: {e}")
        
        self.history.append(audit)
        return audit
    
    def _commit(self, request: MutationRequest):
        """Actually apply the mutation. Override in subclass."""
        # This is a stub - actual implementation depends on chunk type
        # The point is that ALL writes go through here
        pass
    
    # ─────────────────────────────────────────────────────────────
    # DIFF PREVIEW
    # ─────────────────────────────────────────────────────────────
    
    def get_pending_diffs(self) -> List[MutationDiff]:
        """Get all pending diffs for preview."""
        diffs = []
        for req in self.pending:
            diffs.extend(req.diffs)
        return diffs
    
    def clear_pending(self):
        """Clear pending mutations."""
        self.pending.clear()
    
    def commit_pending(self) -> List[MutationAudit]:
        """Commit all pending mutations."""
        results = []
        self.mode = MutationMode.MUTATE
        for req in self.pending:
            audit = self.propose(req)
            results.append(audit)
        self.pending.clear()
        return results
    
    # ─────────────────────────────────────────────────────────────
    # AUDIT
    # ─────────────────────────────────────────────────────────────
    
    def get_history(self, limit: int = 50) -> List[MutationAudit]:
        """Get recent mutation history."""
        return self.history[-limit:]
    
    def export_audit_log(self) -> str:
        """Export audit log as JSON."""
        records = []
        for audit in self.history:
            records.append({
                'timestamp': audit.request.timestamp.isoformat(),
                'target': f"{audit.request.target_type}:{audit.request.target_id}",
                'file': audit.request.target_file,
                'result': audit.result.value,
                'safety': audit.safety_level,
                'notes': audit.risk_notes,
            })
        return json.dumps(records, indent=2)
    
    # ─────────────────────────────────────────────────────────────
    # REGISTRATION
    # ─────────────────────────────────────────────────────────────
    
    def add_validator(self, fn: Callable):
        """Add a validation function. Returns (bool, reason)."""
        self.validators.append(fn)
    
    def add_commit_hook(self, fn: Callable):
        """Add a post-commit hook."""
        self.commit_hooks.append(fn)


# Convenience functions
def get_pipeline() -> MutationPipeline:
    """Get the global mutation pipeline."""
    return MutationPipeline.get()

def propose_change(target_type: str, target_id: Any, 
                   diffs: List[MutationDiff], 
                   file_path: str = "",
                   reason: str = "") -> MutationAudit:
    """Convenience function to propose a change."""
    request = MutationRequest(
        target_type=target_type,
        target_id=target_id,
        target_file=file_path,
        diffs=diffs,
        reason=reason,
    )
    return get_pipeline().propose(request)
