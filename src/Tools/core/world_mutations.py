"""
World Mutations - World State Modification Operations

Implements ACTION_SURFACE actions for world-level save state.

Actions Implemented:
- ModifyHousehold (WRITE) - Modify household properties
- ModifyLotState (WRITE) - Modify lot properties and objects
- ModifyNeighborhoodState (WRITE) - Modify neighborhood data
"""

import struct
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from Tools.core.mutation_pipeline import (
    MutationPipeline, MutationMode, MutationRequest, 
    MutationDiff, MutationResult, get_pipeline, propose_change
)
from Tools.core.action_registry import validate_action
from Tools.core.save_mutations import SaveMutationResult


# ═══════════════════════════════════════════════════════════════════════════════
# HOUSEHOLD MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class HouseholdManager:
    """
    Manage household properties in save files.
    
    Implements ModifyHousehold action.
    
    Household data includes:
    - Family name
    - Funds (simoleons)
    - Lot assignment
    - Member sims
    - Household flags
    """
    
    def __init__(self, save_manager):
        """Initialize with SaveManager."""
        self.save = save_manager
    
    def get_household(self, household_id: int) -> Dict[str, Any]:
        """Get household data."""
        if hasattr(self.save, '_households') and household_id in self.save._households:
            return self.save._households[household_id].copy()
        return {
            'id': household_id,
            'name': 'Unknown',
            'funds': 20000,
            'lot_id': None,
            'members': [],
            'flags': 0
        }
    
    def get_all_households(self) -> List[Dict[str, Any]]:
        """Get all households."""
        if hasattr(self.save, '_households'):
            return list(self.save._households.values())
        return []
    
    def set_funds(self, household_id: int, amount: int,
                  reason: str = "") -> SaveMutationResult:
        """
        Set household funds.
        
        Args:
            household_id: Household to modify
            amount: New fund amount
            reason: Reason for change
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifyHousehold', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        household = self.get_household(household_id)
        old_funds = household['funds']
        amount = max(0, amount)  # No negative funds
        
        diffs = [MutationDiff(
            field_path=f'household[{household_id}].funds',
            old_value=str(old_funds),
            new_value=str(amount),
            display_old=f"§{old_funds:,}",
            display_new=f"§{amount:,}"
        )]
        
        audit = propose_change(
            target_type='save_household',
            target_id=f'household_{household_id}_funds',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set funds to §{amount:,}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            household['funds'] = amount
            self._set_household(household_id, household)
            return SaveMutationResult(
                True,
                f"Set funds to §{amount:,}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set funds to §{amount:,}")
        else:
            return SaveMutationResult(False, f"ModifyHousehold rejected: {audit.result.value}")
    
    def add_funds(self, household_id: int, amount: int,
                  reason: str = "") -> SaveMutationResult:
        """Add funds to household."""
        household = self.get_household(household_id)
        new_amount = household['funds'] + amount
        return self.set_funds(household_id, new_amount, 
                             reason or f"Add §{amount:,}")
    
    def set_name(self, household_id: int, name: str,
                 reason: str = "") -> SaveMutationResult:
        """Set household name."""
        valid, msg = validate_action('ModifyHousehold', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        household = self.get_household(household_id)
        old_name = household['name']
        
        diffs = [MutationDiff(
            field_path=f'household[{household_id}].name',
            old_value=old_name,
            new_value=name,
            display_old=old_name,
            display_new=name
        )]
        
        audit = propose_change(
            target_type='save_household',
            target_id=f'household_{household_id}_name',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Rename household to {name}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            household['name'] = name
            self._set_household(household_id, household)
            return SaveMutationResult(
                True,
                f"Renamed household to {name}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would rename to {name}")
        else:
            return SaveMutationResult(False, f"ModifyHousehold rejected: {audit.result.value}")
    
    def move_to_lot(self, household_id: int, lot_id: int,
                    reason: str = "") -> SaveMutationResult:
        """Move household to a lot."""
        valid, msg = validate_action('ModifyHousehold', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        household = self.get_household(household_id)
        old_lot = household.get('lot_id', 'None')
        
        diffs = [MutationDiff(
            field_path=f'household[{household_id}].lot_id',
            old_value=str(old_lot),
            new_value=str(lot_id),
            display_old=f"Lot {old_lot}" if old_lot else "Homeless",
            display_new=f"Lot {lot_id}"
        )]
        
        audit = propose_change(
            target_type='save_household',
            target_id=f'household_{household_id}_lot',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Move to lot {lot_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            household['lot_id'] = lot_id
            self._set_household(household_id, household)
            return SaveMutationResult(
                True,
                f"Moved to lot {lot_id}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would move to lot {lot_id}")
        else:
            return SaveMutationResult(False, f"ModifyHousehold rejected: {audit.result.value}")
    
    def add_member(self, household_id: int, sim_id: int,
                   reason: str = "") -> SaveMutationResult:
        """Add a sim to household."""
        valid, msg = validate_action('ModifyHousehold', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        household = self.get_household(household_id)
        if sim_id in household.get('members', []):
            return SaveMutationResult(False, f"Sim {sim_id} already in household")
        
        old_count = len(household.get('members', []))
        
        diffs = [MutationDiff(
            field_path=f'household[{household_id}].members',
            old_value=f"[{old_count} members]",
            new_value=f"[{old_count + 1} members]",
            display_old=f"{old_count} members",
            display_new=f"{old_count + 1} members"
        )]
        
        audit = propose_change(
            target_type='save_household',
            target_id=f'household_{household_id}_add_{sim_id}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Add sim {sim_id} to household"
        )
        
        if audit.result == MutationResult.SUCCESS:
            if 'members' not in household:
                household['members'] = []
            household['members'].append(sim_id)
            self._set_household(household_id, household)
            return SaveMutationResult(
                True,
                f"Added sim {sim_id} to household",
                sim_id=sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would add sim {sim_id}")
        else:
            return SaveMutationResult(False, f"ModifyHousehold rejected: {audit.result.value}")
    
    def remove_member(self, household_id: int, sim_id: int,
                      reason: str = "") -> SaveMutationResult:
        """Remove a sim from household."""
        valid, msg = validate_action('ModifyHousehold', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        household = self.get_household(household_id)
        if sim_id not in household.get('members', []):
            return SaveMutationResult(False, f"Sim {sim_id} not in household")
        
        old_count = len(household['members'])
        
        diffs = [MutationDiff(
            field_path=f'household[{household_id}].members',
            old_value=f"[{old_count} members]",
            new_value=f"[{old_count - 1} members]",
            display_old=f"{old_count} members",
            display_new=f"{old_count - 1} members"
        )]
        
        audit = propose_change(
            target_type='save_household',
            target_id=f'household_{household_id}_remove_{sim_id}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Remove sim {sim_id} from household"
        )
        
        if audit.result == MutationResult.SUCCESS:
            household['members'].remove(sim_id)
            self._set_household(household_id, household)
            return SaveMutationResult(
                True,
                f"Removed sim {sim_id} from household",
                sim_id=sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would remove sim {sim_id}")
        else:
            return SaveMutationResult(False, f"ModifyHousehold rejected: {audit.result.value}")
    
    def _set_household(self, household_id: int, household: Dict):
        """Set household in save."""
        if not hasattr(self.save, '_households'):
            self.save._households = {}
        self.save._households[household_id] = household
        self.save._dirty = True


def modify_household(save_manager, household_id: int, 
                     action: str, **kwargs) -> SaveMutationResult:
    """Modify household. Convenience function."""
    mgr = HouseholdManager(save_manager)
    if action == 'set_funds':
        return mgr.set_funds(household_id, **kwargs)
    elif action == 'add_funds':
        return mgr.add_funds(household_id, **kwargs)
    elif action == 'set_name':
        return mgr.set_name(household_id, **kwargs)
    elif action == 'move_to_lot':
        return mgr.move_to_lot(household_id, **kwargs)
    elif action == 'add_member':
        return mgr.add_member(household_id, **kwargs)
    elif action == 'remove_member':
        return mgr.remove_member(household_id, **kwargs)
    else:
        return SaveMutationResult(False, f"Unknown action: {action}")


# ═══════════════════════════════════════════════════════════════════════════════
# LOT STATE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class LotStateManager:
    """
    Manage lot properties and state.
    
    Implements ModifyLotState action.
    
    Lot data includes:
    - Lot type (residential, community)
    - Lot value
    - Objects on lot
    - Lot flags and options
    """
    
    LOT_TYPES = {
        0: 'Residential',
        1: 'Community',
        2: 'Downtown',
        3: 'Vacation',
        4: 'Campus',
        5: 'Secret',
    }
    
    def __init__(self, save_manager):
        """Initialize with SaveManager."""
        self.save = save_manager
    
    def get_lot(self, lot_id: int) -> Dict[str, Any]:
        """Get lot data."""
        if hasattr(self.save, '_lots') and lot_id in self.save._lots:
            return self.save._lots[lot_id].copy()
        return {
            'id': lot_id,
            'name': f'Lot {lot_id}',
            'type': 0,
            'value': 0,
            'size_x': 2,
            'size_y': 2,
            'objects': [],
            'flags': 0
        }
    
    def get_all_lots(self) -> List[Dict[str, Any]]:
        """Get all lots."""
        if hasattr(self.save, '_lots'):
            return list(self.save._lots.values())
        return []
    
    def set_lot_type(self, lot_id: int, lot_type: int,
                     reason: str = "") -> SaveMutationResult:
        """Set lot type."""
        valid, msg = validate_action('ModifyLotState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        if lot_type not in self.LOT_TYPES:
            return SaveMutationResult(False, f"Unknown lot type: {lot_type}")
        
        lot = self.get_lot(lot_id)
        old_type = lot['type']
        old_name = self.LOT_TYPES.get(old_type, 'Unknown')
        new_name = self.LOT_TYPES[lot_type]
        
        diffs = [MutationDiff(
            field_path=f'lot[{lot_id}].type',
            old_value=str(old_type),
            new_value=str(lot_type),
            display_old=old_name,
            display_new=new_name
        )]
        
        audit = propose_change(
            target_type='save_lot',
            target_id=f'lot_{lot_id}_type',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set lot type to {new_name}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            lot['type'] = lot_type
            self._set_lot(lot_id, lot)
            return SaveMutationResult(
                True,
                f"Set lot type to {new_name}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set type to {new_name}")
        else:
            return SaveMutationResult(False, f"ModifyLotState rejected: {audit.result.value}")
    
    def set_lot_value(self, lot_id: int, value: int,
                      reason: str = "") -> SaveMutationResult:
        """Set lot value."""
        valid, msg = validate_action('ModifyLotState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        lot = self.get_lot(lot_id)
        old_value = lot['value']
        value = max(0, value)
        
        diffs = [MutationDiff(
            field_path=f'lot[{lot_id}].value',
            old_value=str(old_value),
            new_value=str(value),
            display_old=f"§{old_value:,}",
            display_new=f"§{value:,}"
        )]
        
        audit = propose_change(
            target_type='save_lot',
            target_id=f'lot_{lot_id}_value',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set lot value to §{value:,}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            lot['value'] = value
            self._set_lot(lot_id, lot)
            return SaveMutationResult(
                True,
                f"Set lot value to §{value:,}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set value to §{value:,}")
        else:
            return SaveMutationResult(False, f"ModifyLotState rejected: {audit.result.value}")
    
    def set_lot_name(self, lot_id: int, name: str,
                     reason: str = "") -> SaveMutationResult:
        """Set lot name."""
        valid, msg = validate_action('ModifyLotState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        lot = self.get_lot(lot_id)
        old_name = lot['name']
        
        diffs = [MutationDiff(
            field_path=f'lot[{lot_id}].name',
            old_value=old_name,
            new_value=name,
            display_old=old_name,
            display_new=name
        )]
        
        audit = propose_change(
            target_type='save_lot',
            target_id=f'lot_{lot_id}_name',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Rename lot to {name}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            lot['name'] = name
            self._set_lot(lot_id, lot)
            return SaveMutationResult(
                True,
                f"Renamed lot to {name}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would rename to {name}")
        else:
            return SaveMutationResult(False, f"ModifyLotState rejected: {audit.result.value}")
    
    def add_object(self, lot_id: int, object_guid: int, 
                   x: float = 0, y: float = 0, level: int = 0,
                   reason: str = "") -> SaveMutationResult:
        """Add an object to lot."""
        valid, msg = validate_action('ModifyLotState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        lot = self.get_lot(lot_id)
        old_count = len(lot.get('objects', []))
        
        diffs = [MutationDiff(
            field_path=f'lot[{lot_id}].objects',
            old_value=f"[{old_count} objects]",
            new_value=f"[{old_count + 1} objects]",
            display_old=f"{old_count} objects",
            display_new=f"{old_count + 1} objects (+GUID 0x{object_guid:08X})"
        )]
        
        audit = propose_change(
            target_type='save_lot',
            target_id=f'lot_{lot_id}_add_obj',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Add object GUID 0x{object_guid:08X}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            obj = {
                'guid': object_guid,
                'x': x, 'y': y, 'level': level,
                'rotation': 0,
                'instance_id': self._next_instance_id(lot_id)
            }
            if 'objects' not in lot:
                lot['objects'] = []
            lot['objects'].append(obj)
            self._set_lot(lot_id, lot)
            return SaveMutationResult(
                True,
                f"Added object GUID 0x{object_guid:08X}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs],
                data=obj
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would add object")
        else:
            return SaveMutationResult(False, f"ModifyLotState rejected: {audit.result.value}")
    
    def remove_object(self, lot_id: int, instance_id: int,
                      reason: str = "") -> SaveMutationResult:
        """Remove an object from lot by instance ID."""
        valid, msg = validate_action('ModifyLotState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        lot = self.get_lot(lot_id)
        objects = lot.get('objects', [])
        
        # Find object
        obj_idx = None
        for i, obj in enumerate(objects):
            if obj.get('instance_id') == instance_id:
                obj_idx = i
                break
        
        if obj_idx is None:
            return SaveMutationResult(False, f"Object {instance_id} not found on lot")
        
        old_count = len(objects)
        
        diffs = [MutationDiff(
            field_path=f'lot[{lot_id}].objects',
            old_value=f"[{old_count} objects]",
            new_value=f"[{old_count - 1} objects]",
            display_old=f"{old_count} objects",
            display_new=f"{old_count - 1} objects (-instance {instance_id})"
        )]
        
        audit = propose_change(
            target_type='save_lot',
            target_id=f'lot_{lot_id}_remove_obj_{instance_id}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Remove object instance {instance_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            del objects[obj_idx]
            lot['objects'] = objects
            self._set_lot(lot_id, lot)
            return SaveMutationResult(
                True,
                f"Removed object instance {instance_id}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would remove object")
        else:
            return SaveMutationResult(False, f"ModifyLotState rejected: {audit.result.value}")
    
    def clear_lot(self, lot_id: int, reason: str = "") -> SaveMutationResult:
        """Remove all objects from lot."""
        valid, msg = validate_action('ModifyLotState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        lot = self.get_lot(lot_id)
        old_count = len(lot.get('objects', []))
        
        if old_count == 0:
            return SaveMutationResult(True, "Lot already empty")
        
        diffs = [MutationDiff(
            field_path=f'lot[{lot_id}].objects',
            old_value=f"[{old_count} objects]",
            new_value="[0 objects]",
            display_old=f"{old_count} objects",
            display_new="Empty lot"
        )]
        
        audit = propose_change(
            target_type='save_lot',
            target_id=f'lot_{lot_id}_clear',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Clear all {old_count} objects from lot"
        )
        
        if audit.result == MutationResult.SUCCESS:
            lot['objects'] = []
            self._set_lot(lot_id, lot)
            return SaveMutationResult(
                True,
                f"Cleared {old_count} objects from lot",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would clear {old_count} objects")
        else:
            return SaveMutationResult(False, f"ModifyLotState rejected: {audit.result.value}")
    
    def _next_instance_id(self, lot_id: int) -> int:
        """Get next available instance ID for lot."""
        lot = self.get_lot(lot_id)
        objects = lot.get('objects', [])
        if not objects:
            return 1
        return max(obj.get('instance_id', 0) for obj in objects) + 1
    
    def _set_lot(self, lot_id: int, lot: Dict):
        """Set lot in save."""
        if not hasattr(self.save, '_lots'):
            self.save._lots = {}
        self.save._lots[lot_id] = lot
        self.save._dirty = True


def modify_lot_state(save_manager, lot_id: int, 
                     action: str, **kwargs) -> SaveMutationResult:
    """Modify lot state. Convenience function."""
    mgr = LotStateManager(save_manager)
    if action == 'set_type':
        return mgr.set_lot_type(lot_id, **kwargs)
    elif action == 'set_value':
        return mgr.set_lot_value(lot_id, **kwargs)
    elif action == 'set_name':
        return mgr.set_lot_name(lot_id, **kwargs)
    elif action == 'add_object':
        return mgr.add_object(lot_id, **kwargs)
    elif action == 'remove_object':
        return mgr.remove_object(lot_id, **kwargs)
    elif action == 'clear':
        return mgr.clear_lot(lot_id, **kwargs)
    else:
        return SaveMutationResult(False, f"Unknown action: {action}")


# ═══════════════════════════════════════════════════════════════════════════════
# NEIGHBORHOOD STATE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class NeighborhoodManager:
    """
    Manage neighborhood state.
    
    Implements ModifyNeighborhoodState action.
    
    Neighborhood data includes:
    - Name and description
    - Terrain data
    - Decorations
    - Roads
    - Global flags
    """
    
    def __init__(self, save_manager):
        """Initialize with SaveManager."""
        self.save = save_manager
    
    def get_neighborhood(self) -> Dict[str, Any]:
        """Get neighborhood data."""
        if hasattr(self.save, '_neighborhood'):
            return self.save._neighborhood.copy()
        return {
            'name': 'Neighborhood',
            'description': '',
            'lots': [],
            'roads': [],
            'decorations': [],
            'flags': 0,
            'terrain_type': 0
        }
    
    def set_name(self, name: str, reason: str = "") -> SaveMutationResult:
        """Set neighborhood name."""
        valid, msg = validate_action('ModifyNeighborhoodState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        neighborhood = self.get_neighborhood()
        old_name = neighborhood['name']
        
        diffs = [MutationDiff(
            field_path='neighborhood.name',
            old_value=old_name,
            new_value=name,
            display_old=old_name,
            display_new=name
        )]
        
        audit = propose_change(
            target_type='save_neighborhood',
            target_id='neighborhood_name',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Rename neighborhood to {name}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            neighborhood['name'] = name
            self._set_neighborhood(neighborhood)
            return SaveMutationResult(
                True,
                f"Renamed neighborhood to {name}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would rename to {name}")
        else:
            return SaveMutationResult(False, f"ModifyNeighborhoodState rejected: {audit.result.value}")
    
    def set_description(self, description: str, reason: str = "") -> SaveMutationResult:
        """Set neighborhood description."""
        valid, msg = validate_action('ModifyNeighborhoodState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        neighborhood = self.get_neighborhood()
        old_desc = neighborhood.get('description', '')
        
        diffs = [MutationDiff(
            field_path='neighborhood.description',
            old_value=old_desc[:50] + '...' if len(old_desc) > 50 else old_desc,
            new_value=description[:50] + '...' if len(description) > 50 else description,
            display_old=f"{len(old_desc)} chars",
            display_new=f"{len(description)} chars"
        )]
        
        audit = propose_change(
            target_type='save_neighborhood',
            target_id='neighborhood_desc',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or "Update description"
        )
        
        if audit.result == MutationResult.SUCCESS:
            neighborhood['description'] = description
            self._set_neighborhood(neighborhood)
            return SaveMutationResult(
                True,
                "Updated description",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, "Preview: would update description")
        else:
            return SaveMutationResult(False, f"ModifyNeighborhoodState rejected: {audit.result.value}")
    
    def set_terrain_type(self, terrain_type: int, reason: str = "") -> SaveMutationResult:
        """Set terrain type (0=grass, 1=desert, 2=snow, etc.)."""
        valid, msg = validate_action('ModifyNeighborhoodState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        terrain_names = {0: 'Grass', 1: 'Desert', 2: 'Snow', 3: 'Dirt', 4: 'Tropical'}
        
        neighborhood = self.get_neighborhood()
        old_type = neighborhood.get('terrain_type', 0)
        old_name = terrain_names.get(old_type, f'Type {old_type}')
        new_name = terrain_names.get(terrain_type, f'Type {terrain_type}')
        
        diffs = [MutationDiff(
            field_path='neighborhood.terrain_type',
            old_value=str(old_type),
            new_value=str(terrain_type),
            display_old=old_name,
            display_new=new_name
        )]
        
        audit = propose_change(
            target_type='save_neighborhood',
            target_id='neighborhood_terrain',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set terrain to {new_name}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            neighborhood['terrain_type'] = terrain_type
            self._set_neighborhood(neighborhood)
            return SaveMutationResult(
                True,
                f"Set terrain to {new_name}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set terrain to {new_name}")
        else:
            return SaveMutationResult(False, f"ModifyNeighborhoodState rejected: {audit.result.value}")
    
    def add_decoration(self, deco_type: int, x: float, y: float,
                       reason: str = "") -> SaveMutationResult:
        """Add a decoration to neighborhood."""
        valid, msg = validate_action('ModifyNeighborhoodState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        neighborhood = self.get_neighborhood()
        old_count = len(neighborhood.get('decorations', []))
        
        diffs = [MutationDiff(
            field_path='neighborhood.decorations',
            old_value=f"[{old_count} decorations]",
            new_value=f"[{old_count + 1} decorations]",
            display_old=f"{old_count} decorations",
            display_new=f"{old_count + 1} decorations"
        )]
        
        audit = propose_change(
            target_type='save_neighborhood',
            target_id='neighborhood_deco',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Add decoration type {deco_type}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            deco = {'type': deco_type, 'x': x, 'y': y, 'rotation': 0}
            if 'decorations' not in neighborhood:
                neighborhood['decorations'] = []
            neighborhood['decorations'].append(deco)
            self._set_neighborhood(neighborhood)
            return SaveMutationResult(
                True,
                f"Added decoration type {deco_type}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs],
                data=deco
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, "Preview: would add decoration")
        else:
            return SaveMutationResult(False, f"ModifyNeighborhoodState rejected: {audit.result.value}")
    
    def clear_decorations(self, reason: str = "") -> SaveMutationResult:
        """Clear all decorations."""
        valid, msg = validate_action('ModifyNeighborhoodState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        neighborhood = self.get_neighborhood()
        old_count = len(neighborhood.get('decorations', []))
        
        if old_count == 0:
            return SaveMutationResult(True, "No decorations to clear")
        
        diffs = [MutationDiff(
            field_path='neighborhood.decorations',
            old_value=f"[{old_count} decorations]",
            new_value="[0 decorations]",
            display_old=f"{old_count} decorations",
            display_new="No decorations"
        )]
        
        audit = propose_change(
            target_type='save_neighborhood',
            target_id='neighborhood_clear_deco',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Clear {old_count} decorations"
        )
        
        if audit.result == MutationResult.SUCCESS:
            neighborhood['decorations'] = []
            self._set_neighborhood(neighborhood)
            return SaveMutationResult(
                True,
                f"Cleared {old_count} decorations",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would clear {old_count} decorations")
        else:
            return SaveMutationResult(False, f"ModifyNeighborhoodState rejected: {audit.result.value}")
    
    def set_flag(self, flag_name: str, value: bool, reason: str = "") -> SaveMutationResult:
        """Set a neighborhood flag."""
        valid, msg = validate_action('ModifyNeighborhoodState', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        neighborhood = self.get_neighborhood()
        
        diffs = [MutationDiff(
            field_path=f'neighborhood.flags.{flag_name}',
            old_value='unknown',
            new_value=str(value),
            display_old=f"{flag_name}: ?",
            display_new=f"{flag_name}: {value}"
        )]
        
        audit = propose_change(
            target_type='save_neighborhood',
            target_id=f'neighborhood_flag_{flag_name}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set {flag_name} to {value}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            if 'custom_flags' not in neighborhood:
                neighborhood['custom_flags'] = {}
            neighborhood['custom_flags'][flag_name] = value
            self._set_neighborhood(neighborhood)
            return SaveMutationResult(
                True,
                f"Set {flag_name} to {value}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set {flag_name}")
        else:
            return SaveMutationResult(False, f"ModifyNeighborhoodState rejected: {audit.result.value}")
    
    def _set_neighborhood(self, neighborhood: Dict):
        """Set neighborhood in save."""
        self.save._neighborhood = neighborhood
        self.save._dirty = True


def modify_neighborhood_state(save_manager, action: str, **kwargs) -> SaveMutationResult:
    """Modify neighborhood state. Convenience function."""
    mgr = NeighborhoodManager(save_manager)
    if action == 'set_name':
        return mgr.set_name(**kwargs)
    elif action == 'set_description':
        return mgr.set_description(**kwargs)
    elif action == 'set_terrain':
        return mgr.set_terrain_type(**kwargs)
    elif action == 'add_decoration':
        return mgr.add_decoration(**kwargs)
    elif action == 'clear_decorations':
        return mgr.clear_decorations(**kwargs)
    elif action == 'set_flag':
        return mgr.set_flag(**kwargs)
    else:
        return SaveMutationResult(False, f"Unknown action: {action}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Household management
    'HouseholdManager', 'modify_household',
    
    # Lot state management
    'LotStateManager', 'modify_lot_state',
    
    # Neighborhood management
    'NeighborhoodManager', 'modify_neighborhood_state',
]
