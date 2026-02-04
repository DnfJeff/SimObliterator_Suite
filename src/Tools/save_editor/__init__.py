# Save Editor Backend for The Sims 1 Legacy Collection
# Based on FreeSO's reverse-engineered formats

from .save_manager import SaveManager, FamilyData, NeighborData, PersonData, IFFEditor

__all__ = [
    'SaveManager', 'FamilyData', 'NeighborData', 'PersonData', 'IFFEditor'
]
