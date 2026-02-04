"""
UI Actions - User Interface Action Operations

Implements ACTION_SURFACE actions for UI interactions.

Actions Implemented:
- ConfirmMutation (UI) - Confirm a pending mutation
- CancelMutation (UI) - Cancel a pending mutation
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from enum import Enum

from Tools.core.mutation_pipeline import (
    MutationPipeline, MutationMode, MutationRequest, 
    MutationDiff, MutationResult, MutationAudit,
    get_pipeline
)
from Tools.core.action_registry import validate_action


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UIActionResult:
    """Result of a UI action."""
    success: bool
    message: str
    action: Optional[str] = None
    data: Optional[Any] = None


# ═══════════════════════════════════════════════════════════════════════════════
# PENDING MUTATION TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PendingMutation:
    """A pending mutation awaiting confirmation."""
    mutation_id: str
    request: MutationRequest
    diffs: List[MutationDiff]
    created: str
    timeout_seconds: int = 300  # 5 minutes default
    confirmed: bool = False
    cancelled: bool = False
    execute_fn: Optional[Callable] = None  # Function to execute on confirm
    rollback_fn: Optional[Callable] = None  # Function to rollback


class MutationTracker:
    """
    Track pending mutations for UI confirmation flow.
    
    Singleton that manages the list of mutations awaiting user confirmation.
    """
    
    _instance = None
    
    def __init__(self):
        self._pending: Dict[str, PendingMutation] = {}
        self._history: List[MutationAudit] = []
        self._undo_stack: List[PendingMutation] = []
        self._redo_stack: List[PendingMutation] = []
        self._max_history = 100
        self._max_undo = 50
    
    @classmethod
    def get(cls) -> "MutationTracker":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def add_pending(self, mutation: PendingMutation):
        """Add a pending mutation."""
        self._pending[mutation.mutation_id] = mutation
    
    def get_pending(self, mutation_id: str) -> Optional[PendingMutation]:
        """Get a pending mutation by ID."""
        return self._pending.get(mutation_id)
    
    def get_all_pending(self) -> List[PendingMutation]:
        """Get all pending mutations."""
        return list(self._pending.values())
    
    def remove_pending(self, mutation_id: str) -> bool:
        """Remove a pending mutation."""
        if mutation_id in self._pending:
            del self._pending[mutation_id]
            return True
        return False
    
    def add_to_history(self, audit: MutationAudit):
        """Add a completed mutation to history."""
        self._history.append(audit)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_history(self, count: int = 20) -> List[MutationAudit]:
        """Get recent mutation history."""
        return self._history[-count:]
    
    def push_undo(self, mutation: PendingMutation):
        """Push a mutation to undo stack."""
        self._undo_stack.append(mutation)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack = self._undo_stack[-self._max_undo:]
        # Clear redo on new action
        self._redo_stack.clear()
    
    def pop_undo(self) -> Optional[PendingMutation]:
        """Pop from undo stack."""
        if self._undo_stack:
            return self._undo_stack.pop()
        return None
    
    def push_redo(self, mutation: PendingMutation):
        """Push to redo stack."""
        self._redo_stack.append(mutation)
    
    def pop_redo(self) -> Optional[PendingMutation]:
        """Pop from redo stack."""
        if self._redo_stack:
            return self._redo_stack.pop()
        return None
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0
    
    def clear_pending(self):
        """Clear all pending mutations."""
        self._pending.clear()
    
    def clear_history(self):
        """Clear mutation history."""
        self._history.clear()
    
    def clear_undo_redo(self):
        """Clear undo/redo stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION UI CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════════

class MutationUIController:
    """
    Controller for mutation UI interactions.
    
    Implements ConfirmMutation, CancelMutation actions.
    """
    
    def __init__(self):
        self.tracker = MutationTracker.get()
        self.pipeline = get_pipeline()
        self._next_id = 1
    
    def generate_mutation_id(self) -> str:
        """Generate unique mutation ID."""
        mid = f"mut_{self._next_id:06d}_{datetime.now().strftime('%H%M%S')}"
        self._next_id += 1
        return mid
    
    def request_mutation(self, request: MutationRequest, 
                         diffs: List[MutationDiff],
                         execute_fn: Callable = None,
                         rollback_fn: Callable = None) -> PendingMutation:
        """
        Request a mutation and queue for confirmation.
        
        Args:
            request: MutationRequest describing the mutation
            diffs: List of diffs for the mutation
            execute_fn: Function to call on confirm
            rollback_fn: Function to call for undo
            
        Returns:
            PendingMutation
        """
        mutation_id = self.generate_mutation_id()
        
        pending = PendingMutation(
            mutation_id=mutation_id,
            request=request,
            diffs=diffs,
            created=datetime.now().isoformat(),
            execute_fn=execute_fn,
            rollback_fn=rollback_fn
        )
        
        self.tracker.add_pending(pending)
        return pending
    
    def confirm_mutation(self, mutation_id: str,
                         reason: str = "") -> UIActionResult:
        """
        Confirm a pending mutation.
        
        Args:
            mutation_id: ID of mutation to confirm
            reason: Reason for confirmation
            
        Returns:
            UIActionResult
        """
        valid, msg = validate_action('ConfirmMutation', {
            'pipeline_mode': self.pipeline.mode.value,
            'user_confirmed': True
        })
        
        if not valid:
            return UIActionResult(False, f"Action blocked: {msg}", 'ConfirmMutation')
        
        pending = self.tracker.get_pending(mutation_id)
        if pending is None:
            return UIActionResult(False, f"Mutation {mutation_id} not found", 'ConfirmMutation')
        
        if pending.confirmed:
            return UIActionResult(False, "Mutation already confirmed", 'ConfirmMutation')
        
        if pending.cancelled:
            return UIActionResult(False, "Mutation was cancelled", 'ConfirmMutation')
        
        # Check timeout
        created = datetime.fromisoformat(pending.created)
        elapsed = (datetime.now() - created).total_seconds()
        if elapsed > pending.timeout_seconds:
            self.tracker.remove_pending(mutation_id)
            return UIActionResult(False, "Mutation timed out", 'ConfirmMutation')
        
        # Execute the mutation
        try:
            if pending.execute_fn:
                result = pending.execute_fn()
                if hasattr(result, 'success') and not result.success:
                    return UIActionResult(False, f"Execution failed: {result.message}", 'ConfirmMutation')
            
            pending.confirmed = True
            
            # Add to undo stack
            self.tracker.push_undo(pending)
            
            # Create audit record
            audit = MutationAudit(
                request=pending.request,
                result=MutationResult.SUCCESS,
                timestamp=datetime.now().isoformat(),
                user_confirmed=True
            )
            self.tracker.add_to_history(audit)
            
            # Remove from pending
            self.tracker.remove_pending(mutation_id)
            
            return UIActionResult(
                True,
                f"Mutation {mutation_id} confirmed and executed",
                'ConfirmMutation',
                data={'mutation_id': mutation_id, 'diffs_applied': len(pending.diffs)}
            )
            
        except Exception as e:
            return UIActionResult(False, f"Execution error: {e}", 'ConfirmMutation')
    
    def cancel_mutation(self, mutation_id: str,
                        reason: str = "") -> UIActionResult:
        """
        Cancel a pending mutation.
        
        Args:
            mutation_id: ID of mutation to cancel
            reason: Reason for cancellation
            
        Returns:
            UIActionResult
        """
        valid, msg = validate_action('CancelMutation', {
            'pipeline_mode': self.pipeline.mode.value
        })
        
        if not valid:
            return UIActionResult(False, f"Action blocked: {msg}", 'CancelMutation')
        
        pending = self.tracker.get_pending(mutation_id)
        if pending is None:
            return UIActionResult(False, f"Mutation {mutation_id} not found", 'CancelMutation')
        
        if pending.confirmed:
            return UIActionResult(False, "Mutation already confirmed", 'CancelMutation')
        
        if pending.cancelled:
            return UIActionResult(True, "Mutation already cancelled", 'CancelMutation')
        
        pending.cancelled = True
        
        # Create audit record
        audit = MutationAudit(
            request=pending.request,
            result=MutationResult.CANCELLED,
            timestamp=datetime.now().isoformat(),
            user_confirmed=False
        )
        self.tracker.add_to_history(audit)
        
        # Remove from pending
        self.tracker.remove_pending(mutation_id)
        
        return UIActionResult(
            True,
            f"Mutation {mutation_id} cancelled",
            'CancelMutation',
            data={'mutation_id': mutation_id, 'reason': reason}
        )
    
    def undo(self, reason: str = "") -> UIActionResult:
        """
        Undo the last confirmed mutation.
        
        Returns:
            UIActionResult
        """
        if not self.tracker.can_undo():
            return UIActionResult(False, "Nothing to undo", 'Undo')
        
        mutation = self.tracker.pop_undo()
        if mutation is None:
            return UIActionResult(False, "Undo stack empty", 'Undo')
        
        try:
            if mutation.rollback_fn:
                result = mutation.rollback_fn()
                if hasattr(result, 'success') and not result.success:
                    # Put back on stack if rollback failed
                    self.tracker.push_undo(mutation)
                    return UIActionResult(False, f"Rollback failed: {result.message}", 'Undo')
            
            # Push to redo stack
            self.tracker.push_redo(mutation)
            
            return UIActionResult(
                True,
                f"Undid mutation {mutation.mutation_id}",
                'Undo',
                data={'mutation_id': mutation.mutation_id}
            )
            
        except Exception as e:
            # Put back on stack if error
            self.tracker.push_undo(mutation)
            return UIActionResult(False, f"Undo error: {e}", 'Undo')
    
    def redo(self, reason: str = "") -> UIActionResult:
        """
        Redo the last undone mutation.
        
        Returns:
            UIActionResult
        """
        if not self.tracker.can_redo():
            return UIActionResult(False, "Nothing to redo", 'Redo')
        
        mutation = self.tracker.pop_redo()
        if mutation is None:
            return UIActionResult(False, "Redo stack empty", 'Redo')
        
        try:
            if mutation.execute_fn:
                result = mutation.execute_fn()
                if hasattr(result, 'success') and not result.success:
                    # Put back on redo stack if failed
                    self.tracker.push_redo(mutation)
                    return UIActionResult(False, f"Redo failed: {result.message}", 'Redo')
            
            # Push to undo stack
            self.tracker.push_undo(mutation)
            
            return UIActionResult(
                True,
                f"Redid mutation {mutation.mutation_id}",
                'Redo',
                data={'mutation_id': mutation.mutation_id}
            )
            
        except Exception as e:
            # Put back on redo stack if error
            self.tracker.push_redo(mutation)
            return UIActionResult(False, f"Redo error: {e}", 'Redo')
    
    def get_pending_mutations(self) -> List[Dict]:
        """Get all pending mutations as dicts for UI display."""
        return [
            {
                'mutation_id': p.mutation_id,
                'target_type': p.request.target_type,
                'target_id': p.request.target_id,
                'diff_count': len(p.diffs),
                'created': p.created,
                'confirmed': p.confirmed,
                'cancelled': p.cancelled,
                'diffs': [
                    {'field': d.field_path, 'old': d.display_old, 'new': d.display_new}
                    for d in p.diffs
                ]
            }
            for p in self.tracker.get_all_pending()
        ]
    
    def get_mutation_history(self, count: int = 20) -> List[Dict]:
        """Get mutation history for UI display."""
        return [
            {
                'target_type': a.request.target_type,
                'target_id': a.request.target_id,
                'result': a.result.value,
                'timestamp': a.timestamp,
                'confirmed': a.user_confirmed
            }
            for a in self.tracker.get_history(count)
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_controller: Optional[MutationUIController] = None

def get_mutation_controller() -> MutationUIController:
    """Get the mutation UI controller singleton."""
    global _controller
    if _controller is None:
        _controller = MutationUIController()
    return _controller


def confirm_mutation(mutation_id: str, reason: str = "") -> UIActionResult:
    """Confirm a mutation. Convenience function."""
    return get_mutation_controller().confirm_mutation(mutation_id, reason)


def cancel_mutation(mutation_id: str, reason: str = "") -> UIActionResult:
    """Cancel a mutation. Convenience function."""
    return get_mutation_controller().cancel_mutation(mutation_id, reason)


def undo_mutation(reason: str = "") -> UIActionResult:
    """Undo last mutation. Convenience function."""
    return get_mutation_controller().undo(reason)


def redo_mutation(reason: str = "") -> UIActionResult:
    """Redo last undone mutation. Convenience function."""
    return get_mutation_controller().redo(reason)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Tracker
    'PendingMutation', 'MutationTracker',
    
    # Controller
    'MutationUIController', 'get_mutation_controller',
    
    # Convenience functions
    'confirm_mutation', 'cancel_mutation',
    'undo_mutation', 'redo_mutation',
    
    # Result type
    'UIActionResult',
]
