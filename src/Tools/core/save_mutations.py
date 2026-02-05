"""
Save Mutations - Save State Modification Operations

Implements ACTION_SURFACE actions for SAVE_STATE category.

Actions Implemented:
- AddSim (WRITE) - Create new sim in save
- RemoveSim (WRITE) - Delete sim from save
- ModifyTime (WRITE) - Modify game time
- ModifyInventory (WRITE) - Modify sim inventory
- ModifyAspirations (WRITE) - Modify sim aspirations
- ModifyMemories (WRITE) - Modify sim memories
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


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SaveMutationResult:
    """Result of a save mutation operation."""
    success: bool
    message: str
    sim_id: Optional[int] = None
    diffs: List[Dict] = field(default_factory=list)
    data: Optional[Any] = None


# ═══════════════════════════════════════════════════════════════════════════════
# SIM TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SimTemplate:
    """Template for creating new sims."""
    first_name: str = "New"
    last_name: str = "Sim"
    age: int = 25  # Adult
    gender: int = 0  # 0=Male, 1=Female
    skin_tone: int = 1  # 0-4
    fitness: int = 500  # 0-1000
    personality: Dict[str, int] = field(default_factory=lambda: {
        'neat': 5, 'outgoing': 5, 'active': 5, 'playful': 5, 'nice': 5
    })
    interests: Dict[str, int] = field(default_factory=dict)
    skills: Dict[str, int] = field(default_factory=dict)
    
    def to_bytes(self) -> bytes:
        """Serialize to FAMI/SIMI compatible bytes."""
        # This is a simplified structure - actual format varies by game version
        output = bytearray()
        
        # Name (length-prefixed)
        full_name = f"{self.first_name} {self.last_name}"
        name_bytes = full_name.encode('utf-16-le')
        output.extend(struct.pack('<I', len(full_name)))
        output.extend(name_bytes)
        
        # Basic attributes
        output.extend(struct.pack('<I', self.age))
        output.extend(struct.pack('<B', self.gender))
        output.extend(struct.pack('<B', self.skin_tone))
        output.extend(struct.pack('<H', self.fitness))
        
        # Personality (5 traits, 0-10 each)
        for trait in ['neat', 'outgoing', 'active', 'playful', 'nice']:
            output.extend(struct.pack('<B', self.personality.get(trait, 5)))
        
        return bytes(output)


# ═══════════════════════════════════════════════════════════════════════════════
# SIM MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class SimManager:
    """
    Manage sim creation and deletion in save files.
    
    Implements AddSim, RemoveSim actions.
    """
    
    def __init__(self, save_manager):
        """
        Initialize with a SaveManager instance.
        
        Args:
            save_manager: SaveManager for accessing save data
        """
        self.save = save_manager
    
    def add_sim(self, template: SimTemplate = None,
                family_id: int = None,
                reason: str = "") -> SaveMutationResult:
        """
        Add a new sim to the save.
        
        Args:
            template: SimTemplate with sim attributes
            family_id: Family to add sim to (None = new family)
            reason: Reason for addition
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('AddSim', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        template = template or SimTemplate()
        
        # Generate new sim ID
        new_sim_id = self._get_next_sim_id()
        
        # Build mutation diffs
        diffs = [
            MutationDiff(
                field_path='sims',
                old_value=f"[{self._count_sims()} sims]",
                new_value=f"[{self._count_sims() + 1} sims]",
                display_old=f"{self._count_sims()} sims",
                display_new=f"{self._count_sims() + 1} sims"
            ),
            MutationDiff(
                field_path=f'sim[{new_sim_id}].name',
                old_value='(none)',
                new_value=f'{template.first_name} {template.last_name}',
                display_old='New sim',
                display_new=f'{template.first_name} {template.last_name}'
            ),
        ]
        
        # Propose through pipeline
        audit = propose_change(
            target_type='save_sim',
            target_id=f'new_sim_{new_sim_id}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Add sim: {template.first_name} {template.last_name}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Create sim data structure
            sim_data = {
                'id': new_sim_id,
                'first_name': template.first_name,
                'last_name': template.last_name,
                'age': template.age,
                'gender': template.gender,
                'skin_tone': template.skin_tone,
                'fitness': template.fitness,
                'personality': template.personality.copy(),
                'family_id': family_id or self._get_next_family_id(),
                'created': datetime.now().isoformat(),
            }
            
            # Add to save data
            self._add_sim_to_save(sim_data)
            
            return SaveMutationResult(
                True,
                f"Added sim: {template.first_name} {template.last_name}",
                sim_id=new_sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs],
                data=sim_data
            )
            
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(
                True,
                f"Preview: would add {template.first_name} {template.last_name}",
                sim_id=new_sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        else:
            return SaveMutationResult(False, f"AddSim rejected: {audit.result.value}")
    
    def remove_sim(self, sim_id: int, 
                   delete_relationships: bool = True,
                   reason: str = "") -> SaveMutationResult:
        """
        Remove a sim from the save.
        
        Args:
            sim_id: ID of sim to remove
            delete_relationships: Also delete relationships involving this sim
            reason: Reason for removal
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('RemoveSim', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        # Get sim info
        sim_info = self._get_sim_info(sim_id)
        if not sim_info:
            return SaveMutationResult(False, f"Sim {sim_id} not found")
        
        sim_name = f"{sim_info.get('first_name', '?')} {sim_info.get('last_name', '?')}"
        
        # Count relationships to delete
        rel_count = self._count_sim_relationships(sim_id) if delete_relationships else 0
        
        # Build mutation diffs
        diffs = [
            MutationDiff(
                field_path='sims',
                old_value=f"[{self._count_sims()} sims]",
                new_value=f"[{self._count_sims() - 1} sims]",
                display_old=f"{self._count_sims()} sims",
                display_new=f"{self._count_sims() - 1} sims"
            ),
            MutationDiff(
                field_path=f'sim[{sim_id}]',
                old_value=sim_name,
                new_value='(deleted)',
                display_old=sim_name,
                display_new='Deleted'
            ),
        ]
        
        if rel_count > 0:
            diffs.append(MutationDiff(
                field_path='relationships',
                old_value=f"[{rel_count} relationships]",
                new_value='[deleted]',
                display_old=f"{rel_count} relationships",
                display_new="Deleted"
            ))
        
        # Propose through pipeline
        audit = propose_change(
            target_type='save_sim',
            target_id=f'sim_{sim_id}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Remove sim: {sim_name}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            # Remove from save
            self._remove_sim_from_save(sim_id)
            
            if delete_relationships:
                self._delete_sim_relationships(sim_id)
            
            return SaveMutationResult(
                True,
                f"Removed sim: {sim_name}",
                sim_id=sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
            
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(
                True,
                f"Preview: would remove {sim_name}",
                sim_id=sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        else:
            return SaveMutationResult(False, f"RemoveSim rejected: {audit.result.value}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────────────────
    
    def _get_next_sim_id(self) -> int:
        """Get next available sim ID."""
        if hasattr(self.save, '_sims') and self.save._sims:
            return max(s.get('id', 0) for s in self.save._sims) + 1
        return 1000
    
    def _get_next_family_id(self) -> int:
        """Get next available family ID."""
        if hasattr(self.save, '_families') and self.save._families:
            return max(f.get('id', 0) for f in self.save._families) + 1
        return 100
    
    def _count_sims(self) -> int:
        """Count sims in save."""
        if hasattr(self.save, '_sims'):
            return len(self.save._sims)
        return 0
    
    def _get_sim_info(self, sim_id: int) -> Optional[Dict]:
        """Get sim info by ID."""
        if hasattr(self.save, '_sims'):
            for sim in self.save._sims:
                if sim.get('id') == sim_id:
                    return sim
        return None
    
    def _count_sim_relationships(self, sim_id: int) -> int:
        """Count relationships involving a sim."""
        if hasattr(self.save, '_relationships'):
            return sum(1 for r in self.save._relationships 
                      if r.get('sim_a') == sim_id or r.get('sim_b') == sim_id)
        return 0
    
    def _add_sim_to_save(self, sim_data: Dict):
        """Add sim data to save."""
        if not hasattr(self.save, '_sims'):
            self.save._sims = []
        self.save._sims.append(sim_data)
        self.save._dirty = True
    
    def _remove_sim_from_save(self, sim_id: int):
        """Remove sim from save."""
        if hasattr(self.save, '_sims'):
            self.save._sims = [s for s in self.save._sims if s.get('id') != sim_id]
            self.save._dirty = True
    
    def _delete_sim_relationships(self, sim_id: int):
        """Delete all relationships involving sim."""
        if hasattr(self.save, '_relationships'):
            self.save._relationships = [
                r for r in self.save._relationships 
                if r.get('sim_a') != sim_id and r.get('sim_b') != sim_id
            ]
            self.save._dirty = True


# ═══════════════════════════════════════════════════════════════════════════════
# TIME MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class TimeManager:
    """
    Manage game time in save files.
    
    Implements ModifyTime action.
    """
    
    TICKS_PER_HOUR = 1000
    HOURS_PER_DAY = 24
    
    def __init__(self, save_manager):
        """
        Initialize with a SaveManager instance.
        
        Args:
            save_manager: SaveManager for accessing save data
        """
        self.save = save_manager
    
    def get_current_time(self) -> Dict:
        """
        Get current game time.
        
        Returns:
            Dict with day, hour, minute, ticks
        """
        ticks = self._get_raw_ticks()
        
        hours = ticks // self.TICKS_PER_HOUR
        minutes = (ticks % self.TICKS_PER_HOUR) * 60 // self.TICKS_PER_HOUR
        day = hours // self.HOURS_PER_DAY
        hour = hours % self.HOURS_PER_DAY
        
        return {
            'day': day,
            'hour': hour,
            'minute': minutes,
            'raw_ticks': ticks
        }
    
    def set_time(self, day: int = None, hour: int = None, 
                 minute: int = None, reason: str = "") -> SaveMutationResult:
        """
        Set game time.
        
        Args:
            day: Day number (optional)
            hour: Hour (0-23, optional)
            minute: Minute (0-59, optional)
            reason: Reason for change
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifyTime', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        current = self.get_current_time()
        
        # Build new time
        new_day = day if day is not None else current['day']
        new_hour = hour if hour is not None else current['hour']
        new_minute = minute if minute is not None else current['minute']
        
        # Validate
        if new_hour < 0 or new_hour > 23:
            return SaveMutationResult(False, f"Invalid hour: {new_hour}")
        if new_minute < 0 or new_minute > 59:
            return SaveMutationResult(False, f"Invalid minute: {new_minute}")
        if new_day < 0:
            return SaveMutationResult(False, f"Invalid day: {new_day}")
        
        # Calculate new ticks
        total_hours = new_day * self.HOURS_PER_DAY + new_hour
        new_ticks = total_hours * self.TICKS_PER_HOUR + (new_minute * self.TICKS_PER_HOUR // 60)
        
        old_time_str = f"Day {current['day']}, {current['hour']:02d}:{current['minute']:02d}"
        new_time_str = f"Day {new_day}, {new_hour:02d}:{new_minute:02d}"
        
        # Build diff
        diffs = [MutationDiff(
            field_path='game_time',
            old_value=current['raw_ticks'],
            new_value=new_ticks,
            display_old=old_time_str,
            display_new=new_time_str
        )]
        
        # Propose through pipeline
        audit = propose_change(
            target_type='save_time',
            target_id='game_time',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set time to {new_time_str}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self._set_raw_ticks(new_ticks)
            return SaveMutationResult(
                True,
                f"Set time: {old_time_str} → {new_time_str}",
                diffs=[{'field': 'game_time', 'old': old_time_str, 'new': new_time_str}]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(
                True,
                f"Preview: would set time to {new_time_str}",
                diffs=[{'field': 'game_time', 'old': old_time_str, 'new': new_time_str}]
            )
        else:
            return SaveMutationResult(False, f"ModifyTime rejected: {audit.result.value}")
    
    def advance_time(self, hours: int = 0, days: int = 0,
                     reason: str = "") -> SaveMutationResult:
        """
        Advance game time by specified amount.
        
        Args:
            hours: Hours to advance
            days: Days to advance
            reason: Reason for change
            
        Returns:
            SaveMutationResult
        """
        current = self.get_current_time()
        new_day = current['day'] + days
        new_hour = current['hour'] + hours
        
        # Handle overflow
        while new_hour >= 24:
            new_hour -= 24
            new_day += 1
        
        return self.set_time(day=new_day, hour=new_hour, 
                            minute=current['minute'],
                            reason=reason or f"Advance time by {days}d {hours}h")
    
    def _get_raw_ticks(self) -> int:
        """Get raw game ticks from save."""
        if hasattr(self.save, '_game_time'):
            return self.save._game_time
        return 0
    
    def _set_raw_ticks(self, ticks: int):
        """Set raw game ticks in save."""
        self.save._game_time = ticks
        self.save._dirty = True


def modify_time(save_manager, **kwargs) -> SaveMutationResult:
    """Modify game time. Convenience function."""
    return TimeManager(save_manager).set_time(**kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# INVENTORY MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class InventoryManager:
    """
    Manage sim inventories in save files.
    
    Implements ModifyInventory action.
    """
    
    def __init__(self, save_manager):
        """
        Initialize with a SaveManager instance.
        
        Args:
            save_manager: SaveManager for accessing save data
        """
        self.save = save_manager
    
    def add_item(self, sim_id: int, item_id: int, 
                 count: int = 1, reason: str = "") -> SaveMutationResult:
        """
        Add item to sim's inventory.
        
        Args:
            sim_id: Sim to modify
            item_id: Item GUID to add
            count: Number of items
            reason: Reason for addition
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifyInventory', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        # Get current inventory
        inventory = self._get_inventory(sim_id)
        current_count = inventory.get(item_id, 0)
        
        # Build diff
        diffs = [MutationDiff(
            field_path=f'sim[{sim_id}].inventory[{item_id}]',
            old_value=current_count,
            new_value=current_count + count,
            display_old=f"{current_count} items",
            display_new=f"{current_count + count} items"
        )]
        
        # Propose through pipeline
        audit = propose_change(
            target_type='save_inventory',
            target_id=f'sim_{sim_id}_inv_{item_id}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Add {count}x item {item_id} to sim {sim_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self._set_inventory_item(sim_id, item_id, current_count + count)
            return SaveMutationResult(
                True,
                f"Added {count}x item {item_id}",
                sim_id=sim_id,
                diffs=[{'item': item_id, 'old': current_count, 'new': current_count + count}]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(
                True,
                f"Preview: would add {count}x item {item_id}",
                sim_id=sim_id
            )
        else:
            return SaveMutationResult(False, f"ModifyInventory rejected: {audit.result.value}")
    
    def remove_item(self, sim_id: int, item_id: int,
                    count: int = 1, reason: str = "") -> SaveMutationResult:
        """
        Remove item from sim's inventory.
        
        Args:
            sim_id: Sim to modify
            item_id: Item GUID to remove
            count: Number to remove (0 = all)
            reason: Reason for removal
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifyInventory', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        inventory = self._get_inventory(sim_id)
        current_count = inventory.get(item_id, 0)
        
        if current_count == 0:
            return SaveMutationResult(False, f"Item {item_id} not in inventory")
        
        remove_count = count if count > 0 else current_count
        new_count = max(0, current_count - remove_count)
        
        # Build diff
        diffs = [MutationDiff(
            field_path=f'sim[{sim_id}].inventory[{item_id}]',
            old_value=current_count,
            new_value=new_count,
            display_old=f"{current_count} items",
            display_new=f"{new_count} items"
        )]
        
        audit = propose_change(
            target_type='save_inventory',
            target_id=f'sim_{sim_id}_inv_{item_id}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Remove {remove_count}x item {item_id} from sim {sim_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            if new_count > 0:
                self._set_inventory_item(sim_id, item_id, new_count)
            else:
                self._remove_inventory_item(sim_id, item_id)
            return SaveMutationResult(
                True,
                f"Removed {remove_count}x item {item_id}",
                sim_id=sim_id
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would remove {remove_count}x item {item_id}")
        else:
            return SaveMutationResult(False, f"ModifyInventory rejected: {audit.result.value}")
    
    def _get_inventory(self, sim_id: int) -> Dict[int, int]:
        """Get sim inventory as item_id -> count dict."""
        if hasattr(self.save, '_inventories'):
            return self.save._inventories.get(sim_id, {})
        return {}
    
    def _set_inventory_item(self, sim_id: int, item_id: int, count: int):
        """Set inventory item count."""
        if not hasattr(self.save, '_inventories'):
            self.save._inventories = {}
        if sim_id not in self.save._inventories:
            self.save._inventories[sim_id] = {}
        self.save._inventories[sim_id][item_id] = count
        self.save._dirty = True
    
    def _remove_inventory_item(self, sim_id: int, item_id: int):
        """Remove item from inventory."""
        if hasattr(self.save, '_inventories') and sim_id in self.save._inventories:
            self.save._inventories[sim_id].pop(item_id, None)
            self.save._dirty = True


def modify_inventory(save_manager, sim_id: int, item_id: int, 
                     delta: int, **kwargs) -> SaveMutationResult:
    """Modify inventory. Convenience function."""
    mgr = InventoryManager(save_manager)
    if delta > 0:
        return mgr.add_item(sim_id, item_id, delta, **kwargs)
    else:
        return mgr.remove_item(sim_id, item_id, -delta, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# ASPIRATION MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class AspirationManager:
    """
    Manage sim aspirations in save files.
    
    Implements ModifyAspirations action.
    
    NOTE: Aspirations are a SIMS 2 feature. The Sims 1 Legacy Collection
    does not have aspirations. This manager is included for future Sims 2
    support but will not affect Sims 1 save files.
    """
    
    # Aspiration types (Sims 2 only - not in Sims 1)
    ASPIRATION_TYPES = {
        0: 'Romance',
        1: 'Family',
        2: 'Fortune',
        3: 'Knowledge',
        4: 'Popularity',
        5: 'Pleasure',
        6: 'Grilled Cheese',
    }
    
    def __init__(self, save_manager):
        """
        Initialize with a SaveManager instance.
        
        Args:
            save_manager: SaveManager for accessing save data
        """
        self.save = save_manager
    
    def get_aspiration(self, sim_id: int) -> Dict:
        """
        Get sim's aspiration data.
        
        Returns:
            Dict with aspiration info
        """
        if hasattr(self.save, '_aspirations'):
            return self.save._aspirations.get(sim_id, {
                'type': 0,
                'score': 0,
                'level': 0
            })
        return {'type': 0, 'score': 0, 'level': 0}
    
    def set_aspiration(self, sim_id: int, aspiration_type: int = None,
                       score: int = None, level: int = None,
                       reason: str = "") -> SaveMutationResult:
        """
        Set sim's aspiration.
        
        Args:
            sim_id: Sim to modify
            aspiration_type: Aspiration type (0-6)
            score: Aspiration score
            level: Aspiration level (0-5)
            reason: Reason for change
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifyAspirations', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        current = self.get_aspiration(sim_id)
        diffs = []
        
        if aspiration_type is not None and aspiration_type != current['type']:
            old_name = self.ASPIRATION_TYPES.get(current['type'], 'Unknown')
            new_name = self.ASPIRATION_TYPES.get(aspiration_type, 'Unknown')
            diffs.append(MutationDiff(
                field_path=f'sim[{sim_id}].aspiration.type',
                old_value=current['type'],
                new_value=aspiration_type,
                display_old=old_name,
                display_new=new_name
            ))
        
        if score is not None and score != current['score']:
            diffs.append(MutationDiff(
                field_path=f'sim[{sim_id}].aspiration.score',
                old_value=current['score'],
                new_value=score,
                display_old=str(current['score']),
                display_new=str(score)
            ))
        
        if level is not None and level != current['level']:
            diffs.append(MutationDiff(
                field_path=f'sim[{sim_id}].aspiration.level',
                old_value=current['level'],
                new_value=level,
                display_old=f"Level {current['level']}",
                display_new=f"Level {level}"
            ))
        
        if not diffs:
            return SaveMutationResult(True, "No changes to apply")
        
        audit = propose_change(
            target_type='save_aspiration',
            target_id=f'sim_{sim_id}_aspiration',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Modify aspiration for sim {sim_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self._update_aspiration(sim_id, aspiration_type, score, level)
            return SaveMutationResult(
                True,
                f"Modified aspiration for sim {sim_id}",
                sim_id=sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, "Preview: would modify aspiration", sim_id=sim_id)
        else:
            return SaveMutationResult(False, f"ModifyAspirations rejected: {audit.result.value}")
    
    def _update_aspiration(self, sim_id: int, asp_type: int, score: int, level: int):
        """Update aspiration in save data."""
        if not hasattr(self.save, '_aspirations'):
            self.save._aspirations = {}
        if sim_id not in self.save._aspirations:
            self.save._aspirations[sim_id] = {'type': 0, 'score': 0, 'level': 0}
        
        if asp_type is not None:
            self.save._aspirations[sim_id]['type'] = asp_type
        if score is not None:
            self.save._aspirations[sim_id]['score'] = score
        if level is not None:
            self.save._aspirations[sim_id]['level'] = level
        
        self.save._dirty = True


def modify_aspirations(save_manager, sim_id: int, **kwargs) -> SaveMutationResult:
    """Modify aspirations. Convenience function."""
    return AspirationManager(save_manager).set_aspiration(sim_id, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryManager:
    """
    Manage sim memories in save files.
    
    Implements ModifyMemories action.
    
    NOTE: Memories are a SIMS 2 feature. The Sims 1 Legacy Collection
    does not have a memories system. This manager is included for future
    Sims 2 support but will not affect Sims 1 save files.
    """
    
    def __init__(self, save_manager):
        """
        Initialize with a SaveManager instance.
        
        Args:
            save_manager: SaveManager for accessing save data
        """
        self.save = save_manager
    
    def get_memories(self, sim_id: int) -> List[Dict]:
        """
        Get sim's memories.
        
        Returns:
            List of memory dicts
        """
        if hasattr(self.save, '_memories'):
            return self.save._memories.get(sim_id, [])
        return []
    
    def add_memory(self, sim_id: int, memory_type: int,
                   subject_id: int = 0, value: int = 0,
                   reason: str = "") -> SaveMutationResult:
        """
        Add a memory to sim.
        
        Args:
            sim_id: Sim to modify
            memory_type: Memory type GUID
            subject_id: Related sim/object ID
            value: Memory value/intensity
            reason: Reason for addition
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifyMemories', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        memories = self.get_memories(sim_id)
        
        diffs = [MutationDiff(
            field_path=f'sim[{sim_id}].memories',
            old_value=f"[{len(memories)} memories]",
            new_value=f"[{len(memories) + 1} memories]",
            display_old=f"{len(memories)} memories",
            display_new=f"{len(memories) + 1} memories"
        )]
        
        audit = propose_change(
            target_type='save_memories',
            target_id=f'sim_{sim_id}_memory_{memory_type}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Add memory type {memory_type} to sim {sim_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            memory = {
                'type': memory_type,
                'subject_id': subject_id,
                'value': value,
                'timestamp': datetime.now().isoformat()
            }
            self._add_memory(sim_id, memory)
            return SaveMutationResult(
                True,
                f"Added memory to sim {sim_id}",
                sim_id=sim_id,
                data=memory
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, "Preview: would add memory")
        else:
            return SaveMutationResult(False, f"ModifyMemories rejected: {audit.result.value}")
    
    def remove_memory(self, sim_id: int, memory_index: int,
                      reason: str = "") -> SaveMutationResult:
        """
        Remove a memory from sim.
        
        Args:
            sim_id: Sim to modify
            memory_index: Index of memory to remove
            reason: Reason for removal
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifyMemories', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        memories = self.get_memories(sim_id)
        
        if memory_index < 0 or memory_index >= len(memories):
            return SaveMutationResult(False, f"Invalid memory index: {memory_index}")
        
        diffs = [MutationDiff(
            field_path=f'sim[{sim_id}].memories[{memory_index}]',
            old_value=f"memory type {memories[memory_index].get('type', '?')}",
            new_value='(deleted)',
            display_old=f"Memory {memory_index}",
            display_new="Deleted"
        )]
        
        audit = propose_change(
            target_type='save_memories',
            target_id=f'sim_{sim_id}_memory_{memory_index}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Remove memory {memory_index} from sim {sim_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self._remove_memory(sim_id, memory_index)
            return SaveMutationResult(
                True,
                f"Removed memory {memory_index} from sim {sim_id}",
                sim_id=sim_id
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, "Preview: would remove memory")
        else:
            return SaveMutationResult(False, f"ModifyMemories rejected: {audit.result.value}")
    
    def _add_memory(self, sim_id: int, memory: Dict):
        """Add memory to save."""
        if not hasattr(self.save, '_memories'):
            self.save._memories = {}
        if sim_id not in self.save._memories:
            self.save._memories[sim_id] = []
        self.save._memories[sim_id].append(memory)
        self.save._dirty = True
    
    def _remove_memory(self, sim_id: int, index: int):
        """Remove memory from save."""
        if hasattr(self.save, '_memories') and sim_id in self.save._memories:
            if 0 <= index < len(self.save._memories[sim_id]):
                del self.save._memories[sim_id][index]
                self.save._dirty = True


def modify_memories(save_manager, sim_id: int, action: str, **kwargs) -> SaveMutationResult:
    """Modify memories. Convenience function."""
    mgr = MemoryManager(save_manager)
    if action == 'add':
        return mgr.add_memory(sim_id, **kwargs)
    elif action == 'remove':
        return mgr.remove_memory(sim_id, **kwargs)
    else:
        return SaveMutationResult(False, f"Unknown action: {action}")


# ═══════════════════════════════════════════════════════════════════════════════
# CAREER MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class CareerManager:
    """
    Manage sim career state.
    
    Implements ModifyCareer action.
    
    SIMS 1 Career Tracks (stored in person_data[JOB_TYPE]):
    - Cooking, Entertainment, Law Enforcement, Medicine, Military,
    - Politics, Pro Athlete, Science, Xtreme
    
    For Sims 1, use the SaveManager.set_sim_career() method directly for
    binary-level modifications. This manager provides high-level API.
    """
    
    # Sims 1 Career Tracks (from person_data values)
    CAREER_TRACKS_SIMS1 = {
        0: 'Unemployed',
        1: 'Cooking',
        2: 'Entertainment', 
        3: 'Law Enforcement',
        4: 'Medicine',
        5: 'Military',
        6: 'Politics',
        7: 'Pro Athlete',
        8: 'Science',
        9: 'Xtreme',
    }
    
    # Legacy Sims 2 tracks (kept for compatibility)
    CAREER_TRACKS = {
        0: 'Unemployed',
        1: 'Business', 2: 'Criminal', 3: 'Culinary', 
        4: 'Law Enforcement', 5: 'Medical', 6: 'Military',
        7: 'Politics', 8: 'Science', 9: 'Slacker',
        10: 'Athletic', 11: 'Entertainment', 12: 'Education',
        # Expansion careers
        13: 'Natural Scientist', 14: 'Show Business', 15: 'Artist',
        16: 'Paranormal', 17: 'Adventure', 18: 'Journalism',
        19: 'Music', 20: 'Dance', 21: 'Intelligence',
        22: 'Gamer', 23: 'Law', 24: 'Oceanography',
    }
    
    MAX_LEVELS = {
        'default': 10,
        'Business': 10, 'Medical': 10, 'Law Enforcement': 10,
    }
    
    def __init__(self, save_manager):
        """Initialize with SaveManager."""
        self.save = save_manager
    
    def get_career(self, sim_id: int) -> Dict[str, Any]:
        """Get sim's current career."""
        if hasattr(self.save, '_careers') and sim_id in self.save._careers:
            return self.save._careers[sim_id]
        return {'track': 0, 'level': 0, 'performance': 0, 'days_worked': 0}
    
    def set_career(self, sim_id: int, track: int, level: int = 1,
                   performance: int = 50, reason: str = "") -> SaveMutationResult:
        """
        Set sim's career.
        
        Args:
            sim_id: Sim to modify
            track: Career track ID (0=unemployed)
            level: Career level (1-10)
            performance: Job performance (0-100)
            reason: Reason for change
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifyCareer', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        if track not in self.CAREER_TRACKS:
            return SaveMutationResult(False, f"Unknown career track: {track}")
        
        track_name = self.CAREER_TRACKS[track]
        max_level = self.MAX_LEVELS.get(track_name, 10)
        level = max(1, min(level, max_level))
        performance = max(0, min(performance, 100))
        
        old_career = self.get_career(sim_id)
        old_track_name = self.CAREER_TRACKS.get(old_career['track'], 'Unemployed')
        
        diffs = [
            MutationDiff(
                field_path=f'sim[{sim_id}].career.track',
                old_value=str(old_career['track']),
                new_value=str(track),
                display_old=old_track_name,
                display_new=track_name
            ),
            MutationDiff(
                field_path=f'sim[{sim_id}].career.level',
                old_value=str(old_career['level']),
                new_value=str(level),
                display_old=f"Level {old_career['level']}",
                display_new=f"Level {level}"
            ),
        ]
        
        audit = propose_change(
            target_type='save_career',
            target_id=f'sim_{sim_id}_career',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set {track_name} level {level} for sim {sim_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            new_career = {
                'track': track,
                'track_name': track_name,
                'level': level,
                'performance': performance,
                'days_worked': 0,
            }
            self._set_career(sim_id, new_career)
            return SaveMutationResult(
                True,
                f"Set career to {track_name} level {level}",
                sim_id=sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs],
                data=new_career
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set {track_name} level {level}")
        else:
            return SaveMutationResult(False, f"ModifyCareer rejected: {audit.result.value}")
    
    def promote(self, sim_id: int, levels: int = 1, reason: str = "") -> SaveMutationResult:
        """Promote sim in current career."""
        career = self.get_career(sim_id)
        if career['track'] == 0:
            return SaveMutationResult(False, "Sim is unemployed")
        new_level = min(career['level'] + levels, 10)
        return self.set_career(sim_id, career['track'], new_level, 
                              career.get('performance', 50), reason)
    
    def demote(self, sim_id: int, levels: int = 1, reason: str = "") -> SaveMutationResult:
        """Demote sim in current career."""
        career = self.get_career(sim_id)
        if career['track'] == 0:
            return SaveMutationResult(False, "Sim is unemployed")
        new_level = max(1, career['level'] - levels)
        return self.set_career(sim_id, career['track'], new_level,
                              career.get('performance', 50), reason)
    
    def quit_job(self, sim_id: int, reason: str = "") -> SaveMutationResult:
        """Set sim to unemployed."""
        return self.set_career(sim_id, 0, 0, 0, reason or "Quit job")
    
    def _set_career(self, sim_id: int, career: Dict):
        """Set career in save."""
        if not hasattr(self.save, '_careers'):
            self.save._careers = {}
        self.save._careers[sim_id] = career
        self.save._dirty = True


def modify_career(save_manager, sim_id: int, action: str, **kwargs) -> SaveMutationResult:
    """Modify career. Convenience function."""
    mgr = CareerManager(save_manager)
    if action == 'set':
        return mgr.set_career(sim_id, **kwargs)
    elif action == 'promote':
        return mgr.promote(sim_id, **kwargs)
    elif action == 'demote':
        return mgr.demote(sim_id, **kwargs)
    elif action == 'quit':
        return mgr.quit_job(sim_id, **kwargs)
    else:
        return SaveMutationResult(False, f"Unknown action: {action}")


# ═══════════════════════════════════════════════════════════════════════════════
# MOTIVES MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class MotivesManager:
    """
    Manage sim motives (needs).
    
    Implements ModifyMotives action.
    
    Motive values range from -100 (critical) to 100 (full).
    """
    
    MOTIVE_NAMES = [
        'hunger', 'comfort', 'hygiene', 'bladder',
        'energy', 'fun', 'social', 'room', 'environment'
    ]
    
    MIN_VALUE = -100
    MAX_VALUE = 100
    
    def __init__(self, save_manager):
        """Initialize with SaveManager."""
        self.save = save_manager
    
    def get_motives(self, sim_id: int) -> Dict[str, int]:
        """Get all motives for a sim."""
        if hasattr(self.save, '_motives') and sim_id in self.save._motives:
            return self.save._motives[sim_id].copy()
        # Default motives
        return {name: 50 for name in self.MOTIVE_NAMES}
    
    def get_motive(self, sim_id: int, motive: str) -> int:
        """Get specific motive value."""
        motives = self.get_motives(sim_id)
        return motives.get(motive.lower(), 0)
    
    def set_motive(self, sim_id: int, motive: str, value: int,
                   reason: str = "") -> SaveMutationResult:
        """
        Set a specific motive value.
        
        Args:
            sim_id: Sim to modify
            motive: Motive name (hunger, comfort, etc.)
            value: New value (-100 to 100)
            reason: Reason for change
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifyMotives', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        motive = motive.lower()
        if motive not in self.MOTIVE_NAMES:
            return SaveMutationResult(False, f"Unknown motive: {motive}")
        
        value = max(self.MIN_VALUE, min(value, self.MAX_VALUE))
        old_value = self.get_motive(sim_id, motive)
        
        diffs = [MutationDiff(
            field_path=f'sim[{sim_id}].motives.{motive}',
            old_value=str(old_value),
            new_value=str(value),
            display_old=f"{motive.title()}: {old_value}",
            display_new=f"{motive.title()}: {value}"
        )]
        
        audit = propose_change(
            target_type='save_motives',
            target_id=f'sim_{sim_id}_motive_{motive}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set {motive} to {value} for sim {sim_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self._set_motive(sim_id, motive, value)
            return SaveMutationResult(
                True,
                f"Set {motive} to {value}",
                sim_id=sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set {motive} to {value}")
        else:
            return SaveMutationResult(False, f"ModifyMotives rejected: {audit.result.value}")
    
    def set_all_motives(self, sim_id: int, value: int,
                        reason: str = "") -> SaveMutationResult:
        """Set all motives to the same value."""
        valid, msg = validate_action('ModifyMotives', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        value = max(self.MIN_VALUE, min(value, self.MAX_VALUE))
        old_motives = self.get_motives(sim_id)
        
        diffs = [MutationDiff(
            field_path=f'sim[{sim_id}].motives',
            old_value=str(old_motives),
            new_value=f"all={value}",
            display_old="Mixed values",
            display_new=f"All motives: {value}"
        )]
        
        audit = propose_change(
            target_type='save_motives',
            target_id=f'sim_{sim_id}_all_motives',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Max all motives for sim {sim_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            for motive in self.MOTIVE_NAMES:
                self._set_motive(sim_id, motive, value)
            return SaveMutationResult(
                True,
                f"Set all motives to {value}",
                sim_id=sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set all motives to {value}")
        else:
            return SaveMutationResult(False, f"ModifyMotives rejected: {audit.result.value}")
    
    def max_motives(self, sim_id: int, reason: str = "") -> SaveMutationResult:
        """Set all motives to maximum (100)."""
        return self.set_all_motives(sim_id, self.MAX_VALUE, reason or "Max motives")
    
    def decay_motives(self, sim_id: int, amount: int = 10,
                      reason: str = "") -> SaveMutationResult:
        """Decay all motives by an amount."""
        valid, msg = validate_action('ModifyMotives', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        old_motives = self.get_motives(sim_id)
        
        diffs = [MutationDiff(
            field_path=f'sim[{sim_id}].motives',
            old_value=str(old_motives),
            new_value=f"decayed by {amount}",
            display_old="Current values",
            display_new=f"Decayed by {amount}"
        )]
        
        audit = propose_change(
            target_type='save_motives',
            target_id=f'sim_{sim_id}_decay_motives',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Decay motives by {amount}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            for motive, old_val in old_motives.items():
                new_val = max(self.MIN_VALUE, old_val - amount)
                self._set_motive(sim_id, motive, new_val)
            return SaveMutationResult(
                True,
                f"Decayed all motives by {amount}",
                sim_id=sim_id
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would decay motives by {amount}")
        else:
            return SaveMutationResult(False, f"ModifyMotives rejected: {audit.result.value}")
    
    def _set_motive(self, sim_id: int, motive: str, value: int):
        """Set motive in save."""
        if not hasattr(self.save, '_motives'):
            self.save._motives = {}
        if sim_id not in self.save._motives:
            self.save._motives[sim_id] = {name: 50 for name in self.MOTIVE_NAMES}
        self.save._motives[sim_id][motive] = value
        self.save._dirty = True


def modify_motives(save_manager, sim_id: int, action: str, **kwargs) -> SaveMutationResult:
    """Modify motives. Convenience function."""
    mgr = MotivesManager(save_manager)
    if action == 'set':
        return mgr.set_motive(sim_id, **kwargs)
    elif action == 'set_all':
        return mgr.set_all_motives(sim_id, **kwargs)
    elif action == 'max':
        return mgr.max_motives(sim_id, **kwargs)
    elif action == 'decay':
        return mgr.decay_motives(sim_id, **kwargs)
    else:
        return SaveMutationResult(False, f"Unknown action: {action}")


# ═══════════════════════════════════════════════════════════════════════════════
# SIM ATTRIBUTES MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class SimAttributesManager:
    """
    Manage sim attributes (skills, badges, interests).
    
    Implements ModifySimAttributes action.
    """
    
    SKILLS = [
        'cooking', 'mechanical', 'charisma', 'body',
        'logic', 'creativity', 'cleaning', 'gardening',
        # University/expansion skills
        'physiology', 'pottery', 'fishing', 'fire_safety'
    ]
    
    INTERESTS = [
        'politics', 'money', 'environment', 'crime', 'food',
        'sports', 'entertainment', 'health', 'fashion', 'culture',
        'travel', 'work', 'animals', 'weather', 'toys',
        'paranormal', 'school', 'sci_fi'
    ]
    
    BADGES = {
        'bronze': 1, 'silver': 2, 'gold': 3
    }
    
    def __init__(self, save_manager):
        """Initialize with SaveManager."""
        self.save = save_manager
    
    def get_skill(self, sim_id: int, skill: str) -> int:
        """Get skill level (0-10)."""
        if hasattr(self.save, '_skills') and sim_id in self.save._skills:
            return self.save._skills[sim_id].get(skill.lower(), 0)
        return 0
    
    def get_all_skills(self, sim_id: int) -> Dict[str, int]:
        """Get all skills."""
        if hasattr(self.save, '_skills') and sim_id in self.save._skills:
            return self.save._skills[sim_id].copy()
        return {skill: 0 for skill in self.SKILLS}
    
    def set_skill(self, sim_id: int, skill: str, level: int,
                  reason: str = "") -> SaveMutationResult:
        """
        Set a skill level.
        
        Args:
            sim_id: Sim to modify
            skill: Skill name
            level: New level (0-10)
            reason: Reason for change
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifySimAttributes', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        skill = skill.lower()
        if skill not in self.SKILLS:
            return SaveMutationResult(False, f"Unknown skill: {skill}")
        
        level = max(0, min(level, 10))
        old_level = self.get_skill(sim_id, skill)
        
        diffs = [MutationDiff(
            field_path=f'sim[{sim_id}].skills.{skill}',
            old_value=str(old_level),
            new_value=str(level),
            display_old=f"{skill.title()}: {old_level}",
            display_new=f"{skill.title()}: {level}"
        )]
        
        audit = propose_change(
            target_type='save_skills',
            target_id=f'sim_{sim_id}_skill_{skill}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set {skill} to {level} for sim {sim_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self._set_skill(sim_id, skill, level)
            return SaveMutationResult(
                True,
                f"Set {skill} to level {level}",
                sim_id=sim_id,
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set {skill} to {level}")
        else:
            return SaveMutationResult(False, f"ModifySimAttributes rejected: {audit.result.value}")
    
    def max_all_skills(self, sim_id: int, reason: str = "") -> SaveMutationResult:
        """Set all skills to maximum (10)."""
        valid, msg = validate_action('ModifySimAttributes', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        old_skills = self.get_all_skills(sim_id)
        
        diffs = [MutationDiff(
            field_path=f'sim[{sim_id}].skills',
            old_value=str(old_skills),
            new_value="all=10",
            display_old="Mixed levels",
            display_new="All skills: 10"
        )]
        
        audit = propose_change(
            target_type='save_skills',
            target_id=f'sim_{sim_id}_all_skills',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Max all skills for sim {sim_id}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            for skill in self.SKILLS:
                self._set_skill(sim_id, skill, 10)
            return SaveMutationResult(
                True,
                "Set all skills to 10",
                sim_id=sim_id
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, "Preview: would max all skills")
        else:
            return SaveMutationResult(False, f"ModifySimAttributes rejected: {audit.result.value}")
    
    def get_interest(self, sim_id: int, interest: str) -> int:
        """Get interest level (0-10)."""
        if hasattr(self.save, '_interests') and sim_id in self.save._interests:
            return self.save._interests[sim_id].get(interest.lower(), 5)
        return 5  # Default middle interest
    
    def set_interest(self, sim_id: int, interest: str, value: int,
                     reason: str = "") -> SaveMutationResult:
        """Set an interest level (0-10)."""
        valid, msg = validate_action('ModifySimAttributes', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        interest = interest.lower()
        if interest not in self.INTERESTS:
            return SaveMutationResult(False, f"Unknown interest: {interest}")
        
        value = max(0, min(value, 10))
        old_value = self.get_interest(sim_id, interest)
        
        diffs = [MutationDiff(
            field_path=f'sim[{sim_id}].interests.{interest}',
            old_value=str(old_value),
            new_value=str(value),
            display_old=f"{interest.title()}: {old_value}",
            display_new=f"{interest.title()}: {value}"
        )]
        
        audit = propose_change(
            target_type='save_interests',
            target_id=f'sim_{sim_id}_interest_{interest}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set {interest} interest to {value}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            self._set_interest(sim_id, interest, value)
            return SaveMutationResult(
                True,
                f"Set {interest} interest to {value}",
                sim_id=sim_id
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set {interest} to {value}")
        else:
            return SaveMutationResult(False, f"ModifySimAttributes rejected: {audit.result.value}")
    
    def _set_skill(self, sim_id: int, skill: str, level: int):
        """Set skill in save."""
        if not hasattr(self.save, '_skills'):
            self.save._skills = {}
        if sim_id not in self.save._skills:
            self.save._skills[sim_id] = {}
        self.save._skills[sim_id][skill] = level
        self.save._dirty = True
    
    def _set_interest(self, sim_id: int, interest: str, value: int):
        """Set interest in save."""
        if not hasattr(self.save, '_interests'):
            self.save._interests = {}
        if sim_id not in self.save._interests:
            self.save._interests[sim_id] = {}
        self.save._interests[sim_id][interest] = value
        self.save._dirty = True


def modify_sim_attributes(save_manager, sim_id: int, attr_type: str, 
                          action: str, **kwargs) -> SaveMutationResult:
    """Modify sim attributes. Convenience function."""
    mgr = SimAttributesManager(save_manager)
    if attr_type == 'skill':
        if action == 'set':
            return mgr.set_skill(sim_id, **kwargs)
        elif action == 'max_all':
            return mgr.max_all_skills(sim_id, **kwargs)
    elif attr_type == 'interest':
        if action == 'set':
            return mgr.set_interest(sim_id, **kwargs)
    return SaveMutationResult(False, f"Unknown attr_type/action: {attr_type}/{action}")


# ═══════════════════════════════════════════════════════════════════════════════
# RELATIONSHIP MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class RelationshipManager:
    """
    Manage sim relationships.
    
    Implements ModifyRelationships action.
    
    SIMS 1 Relationships (stored in NBRS):
    - Simple daily/lifetime values (-100 to 100)
    - No relationship bits (that's Sims 2)
    - Use SaveManager.set_relationship() for binary-level modifications
    
    SIMS 2 Relationships (for future support):
    - Daily and lifetime relationship values
    - Relationship bits (friend, best friend, enemy, crush, etc.)
    """
    
    # Relationship bits (Sims 2 only - not used in Sims 1)
    RELATIONSHIP_BITS = {
        'acquaintance': 0x0001,
        'friend': 0x0002,
        'good_friend': 0x0004,
        'best_friend': 0x0008,
        'bff': 0x0010,
        'enemy': 0x0020,
        'crush': 0x0040,
        'love': 0x0080,
        'engaged': 0x0100,
        'married': 0x0200,
        'family': 0x0400,
        'roommate': 0x0800,
    }
    
    MIN_REL = -100
    MAX_REL = 100
    
    FRIEND_THRESHOLD = 50
    BEST_FRIEND_THRESHOLD = 70
    ENEMY_THRESHOLD = -50
    
    def __init__(self, save_manager):
        """Initialize with SaveManager."""
        self.save = save_manager
    
    def get_relationship(self, sim_a: int, sim_b: int) -> Dict[str, Any]:
        """Get relationship between two sims."""
        key = self._rel_key(sim_a, sim_b)
        if hasattr(self.save, '_relationships') and key in self.save._relationships:
            return self.save._relationships[key].copy()
        return {'daily': 0, 'lifetime': 0, 'bits': 0}
    
    def set_relationship(self, sim_a: int, sim_b: int, 
                         daily: int = None, lifetime: int = None,
                         reason: str = "") -> SaveMutationResult:
        """
        Set relationship values between two sims.
        
        Args:
            sim_a: First sim ID
            sim_b: Second sim ID
            daily: Daily relationship (-100 to 100)
            lifetime: Lifetime relationship (-100 to 100)
            reason: Reason for change
            
        Returns:
            SaveMutationResult
        """
        valid, msg = validate_action('ModifyRelationships', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        old_rel = self.get_relationship(sim_a, sim_b)
        new_daily = old_rel['daily'] if daily is None else max(self.MIN_REL, min(daily, self.MAX_REL))
        new_lifetime = old_rel['lifetime'] if lifetime is None else max(self.MIN_REL, min(lifetime, self.MAX_REL))
        
        diffs = []
        if daily is not None:
            diffs.append(MutationDiff(
                field_path=f'relationship[{sim_a},{sim_b}].daily',
                old_value=str(old_rel['daily']),
                new_value=str(new_daily),
                display_old=f"Daily: {old_rel['daily']}",
                display_new=f"Daily: {new_daily}"
            ))
        if lifetime is not None:
            diffs.append(MutationDiff(
                field_path=f'relationship[{sim_a},{sim_b}].lifetime',
                old_value=str(old_rel['lifetime']),
                new_value=str(new_lifetime),
                display_old=f"Lifetime: {old_rel['lifetime']}",
                display_new=f"Lifetime: {new_lifetime}"
            ))
        
        if not diffs:
            return SaveMutationResult(False, "No changes specified")
        
        audit = propose_change(
            target_type='save_relationship',
            target_id=f'rel_{sim_a}_{sim_b}',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Set relationship between {sim_a} and {sim_b}"
        )
        
        if audit.result == MutationResult.SUCCESS:
            new_rel = {
                'daily': new_daily,
                'lifetime': new_lifetime,
                'bits': old_rel['bits']
            }
            # Auto-update relationship bits based on values
            new_rel['bits'] = self._compute_bits(new_daily, new_lifetime, old_rel['bits'])
            self._set_relationship(sim_a, sim_b, new_rel)
            return SaveMutationResult(
                True,
                f"Set relationship: daily={new_daily}, lifetime={new_lifetime}",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs],
                data=new_rel
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would set relationship")
        else:
            return SaveMutationResult(False, f"ModifyRelationships rejected: {audit.result.value}")
    
    def make_friends(self, sim_a: int, sim_b: int, reason: str = "") -> SaveMutationResult:
        """Make two sims friends."""
        return self.set_relationship(sim_a, sim_b, daily=60, lifetime=55, 
                                     reason=reason or "Make friends")
    
    def make_best_friends(self, sim_a: int, sim_b: int, reason: str = "") -> SaveMutationResult:
        """Make two sims best friends."""
        return self.set_relationship(sim_a, sim_b, daily=90, lifetime=85,
                                     reason=reason or "Make best friends")
    
    def make_enemies(self, sim_a: int, sim_b: int, reason: str = "") -> SaveMutationResult:
        """Make two sims enemies."""
        return self.set_relationship(sim_a, sim_b, daily=-70, lifetime=-60,
                                     reason=reason or "Make enemies")
    
    def add_relationship_bit(self, sim_a: int, sim_b: int, bit_name: str,
                             reason: str = "") -> SaveMutationResult:
        """Add a relationship bit (e.g., 'married', 'engaged')."""
        valid, msg = validate_action('ModifyRelationships', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        bit_name = bit_name.lower()
        if bit_name not in self.RELATIONSHIP_BITS:
            return SaveMutationResult(False, f"Unknown relationship bit: {bit_name}")
        
        bit_value = self.RELATIONSHIP_BITS[bit_name]
        old_rel = self.get_relationship(sim_a, sim_b)
        new_bits = old_rel['bits'] | bit_value
        
        diffs = [MutationDiff(
            field_path=f'relationship[{sim_a},{sim_b}].bits',
            old_value=f"0x{old_rel['bits']:04X}",
            new_value=f"0x{new_bits:04X}",
            display_old=self._bits_to_names(old_rel['bits']),
            display_new=self._bits_to_names(new_bits)
        )]
        
        audit = propose_change(
            target_type='save_relationship',
            target_id=f'rel_{sim_a}_{sim_b}_bit',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Add {bit_name} relationship"
        )
        
        if audit.result == MutationResult.SUCCESS:
            new_rel = old_rel.copy()
            new_rel['bits'] = new_bits
            self._set_relationship(sim_a, sim_b, new_rel)
            return SaveMutationResult(
                True,
                f"Added {bit_name} relationship bit",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would add {bit_name}")
        else:
            return SaveMutationResult(False, f"ModifyRelationships rejected: {audit.result.value}")
    
    def remove_relationship_bit(self, sim_a: int, sim_b: int, bit_name: str,
                                 reason: str = "") -> SaveMutationResult:
        """Remove a relationship bit."""
        valid, msg = validate_action('ModifyRelationships', {
            'pipeline_mode': get_pipeline().mode.value,
            'user_confirmed': True,
            'safety_checked': True
        })
        
        if not valid:
            return SaveMutationResult(False, f"Action blocked: {msg}")
        
        bit_name = bit_name.lower()
        if bit_name not in self.RELATIONSHIP_BITS:
            return SaveMutationResult(False, f"Unknown relationship bit: {bit_name}")
        
        bit_value = self.RELATIONSHIP_BITS[bit_name]
        old_rel = self.get_relationship(sim_a, sim_b)
        new_bits = old_rel['bits'] & ~bit_value
        
        diffs = [MutationDiff(
            field_path=f'relationship[{sim_a},{sim_b}].bits',
            old_value=f"0x{old_rel['bits']:04X}",
            new_value=f"0x{new_bits:04X}",
            display_old=self._bits_to_names(old_rel['bits']),
            display_new=self._bits_to_names(new_bits)
        )]
        
        audit = propose_change(
            target_type='save_relationship',
            target_id=f'rel_{sim_a}_{sim_b}_bit',
            diffs=diffs,
            file_path=getattr(self.save, 'file_path', ''),
            reason=reason or f"Remove {bit_name} relationship"
        )
        
        if audit.result == MutationResult.SUCCESS:
            new_rel = old_rel.copy()
            new_rel['bits'] = new_bits
            self._set_relationship(sim_a, sim_b, new_rel)
            return SaveMutationResult(
                True,
                f"Removed {bit_name} relationship bit",
                diffs=[{'field': d.field_path, 'old': d.display_old, 'new': d.display_new} for d in diffs]
            )
        elif audit.result == MutationResult.PREVIEW_ONLY:
            return SaveMutationResult(True, f"Preview: would remove {bit_name}")
        else:
            return SaveMutationResult(False, f"ModifyRelationships rejected: {audit.result.value}")
    
    def _rel_key(self, sim_a: int, sim_b: int) -> Tuple[int, int]:
        """Get canonical relationship key (ordered pair)."""
        return (min(sim_a, sim_b), max(sim_a, sim_b))
    
    def _compute_bits(self, daily: int, lifetime: int, existing_bits: int) -> int:
        """Compute relationship bits based on values."""
        bits = existing_bits
        
        # Friend status
        if daily >= self.FRIEND_THRESHOLD:
            bits |= self.RELATIONSHIP_BITS['friend']
        else:
            bits &= ~self.RELATIONSHIP_BITS['friend']
        
        # Best friend status
        if daily >= self.BEST_FRIEND_THRESHOLD and lifetime >= self.BEST_FRIEND_THRESHOLD:
            bits |= self.RELATIONSHIP_BITS['best_friend']
        else:
            bits &= ~self.RELATIONSHIP_BITS['best_friend']
        
        # Enemy status
        if daily <= self.ENEMY_THRESHOLD:
            bits |= self.RELATIONSHIP_BITS['enemy']
        else:
            bits &= ~self.RELATIONSHIP_BITS['enemy']
        
        return bits
    
    def _bits_to_names(self, bits: int) -> str:
        """Convert bits to human-readable names."""
        names = []
        for name, value in self.RELATIONSHIP_BITS.items():
            if bits & value:
                names.append(name)
        return ', '.join(names) if names else 'none'
    
    def _set_relationship(self, sim_a: int, sim_b: int, rel: Dict):
        """Set relationship in save."""
        if not hasattr(self.save, '_relationships'):
            self.save._relationships = {}
        key = self._rel_key(sim_a, sim_b)
        self.save._relationships[key] = rel
        self.save._dirty = True


def modify_relationships(save_manager, sim_a: int, sim_b: int, 
                         action: str, **kwargs) -> SaveMutationResult:
    """Modify relationships. Convenience function."""
    mgr = RelationshipManager(save_manager)
    if action == 'set':
        return mgr.set_relationship(sim_a, sim_b, **kwargs)
    elif action == 'friends':
        return mgr.make_friends(sim_a, sim_b, **kwargs)
    elif action == 'best_friends':
        return mgr.make_best_friends(sim_a, sim_b, **kwargs)
    elif action == 'enemies':
        return mgr.make_enemies(sim_a, sim_b, **kwargs)
    elif action == 'add_bit':
        return mgr.add_relationship_bit(sim_a, sim_b, **kwargs)
    elif action == 'remove_bit':
        return mgr.remove_relationship_bit(sim_a, sim_b, **kwargs)
    else:
        return SaveMutationResult(False, f"Unknown action: {action}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Sim management
    'SimManager', 'SimTemplate', 
    
    # Time management
    'TimeManager', 'modify_time',
    
    # Inventory management
    'InventoryManager', 'modify_inventory',
    
    # Aspiration management
    'AspirationManager', 'modify_aspirations',
    
    # Memory management
    'MemoryManager', 'modify_memories',
    
    # Career management
    'CareerManager', 'modify_career',
    
    # Motives management
    'MotivesManager', 'modify_motives',
    
    # Sim attributes management
    'SimAttributesManager', 'modify_sim_attributes',
    
    # Relationship management
    'RelationshipManager', 'modify_relationships',
    
    # Result type
    'SaveMutationResult',
]
