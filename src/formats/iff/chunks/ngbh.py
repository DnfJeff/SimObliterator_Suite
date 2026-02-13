"""
NGBH Chunk - Neighborhood Data
Port of FreeSO's tso.files/Formats/IFF/Chunks/NGBH.cs

NGBH contains general neighborhood data and inventory information.
Originally used just for tracking the tutorial, later expanded for Hot Date.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@dataclass
class InventoryItem:
    """An item in a neighbor's inventory."""
    type: int = 0
    guid: int = 0
    count: int = 0
    
    def __str__(self) -> str:
        return f"InventoryItem(type={self.type}, guid=0x{self.guid:08X}, count={self.count})"


@register_chunk("NGBH")
@dataclass
class NGBH(IffChunk):
    """
    Neighborhood data chunk.
    Maps to: FSO.Files.Formats.IFF.Chunks.NGBH
    """
    version: int = 0x49
    neighborhood_data: list[int] = field(default_factory=lambda: [0] * 16)
    inventory_by_id: dict[int, list[InventoryItem]] = field(default_factory=dict)
    
    def read(self, iff: 'IffFile', io: 'IoBuffer'):
        """Read NGBH chunk from stream."""
        _pad = io.read_uint32()
        self.version = io.read_uint32()
        magic = io.read_cstring(4, trim_null=False)  # "HBGN"
        
        # Read 16 shorts of neighborhood data
        self.neighborhood_data = []
        for _ in range(16):
            self.neighborhood_data.append(io.read_int16())
        
        # Inventory data (added in Hot Date)
        if not io.has_more:
            self.inventory_by_id = {}
            return
        
        count = io.read_int32()
        self.inventory_by_id = {}
        
        for _ in range(count):
            _one = io.read_int32()  # Always 1
            neigh_id = io.read_int16()
            inventory_count = io.read_int32()
            
            inventory = []
            for _ in range(inventory_count):
                item = InventoryItem()
                item.type = io.read_int32()
                item.guid = io.read_uint32()
                item.count = io.read_uint16()
                inventory.append(item)
            
            self.inventory_by_id[neigh_id] = inventory
    
    def write(self, iff: 'IffFile', io: 'IoWriter') -> bool:
        """Write NGBH chunk to stream."""
        io.write_uint32(0)  # Padding
        io.write_uint32(self.version)
        io.write_bytes(b'HBGN')  # Magic
        
        # Write 16 shorts of neighborhood data
        for i in range(16):
            val = self.neighborhood_data[i] if i < len(self.neighborhood_data) else 0
            io.write_int16(val)
        
        # Write inventory data
        io.write_int32(len(self.inventory_by_id))
        
        for neigh_id, inventory in self.inventory_by_id.items():
            io.write_int32(1)  # Always 1
            io.write_int16(neigh_id)
            io.write_int32(len(inventory))
            
            for item in inventory:
                io.write_int32(item.type)
                io.write_uint32(item.guid)
                io.write_uint16(item.count)
        
        return True
    
    def get_inventory(self, neighbor_id: int) -> list[InventoryItem]:
        """Get inventory for a specific neighbor."""
        return self.inventory_by_id.get(neighbor_id, [])
    
    def add_inventory_item(self, neighbor_id: int, item: InventoryItem):
        """Add an item to a neighbor's inventory."""
        if neighbor_id not in self.inventory_by_id:
            self.inventory_by_id[neighbor_id] = []
        self.inventory_by_id[neighbor_id].append(item)
    
    @property
    def tutorial_complete(self) -> bool:
        """Check if tutorial has been completed (stored in neighborhood_data[0])."""
        return bool(self.neighborhood_data[0] if self.neighborhood_data else False)
    
    def __str__(self) -> str:
        inv_count = sum(len(inv) for inv in self.inventory_by_id.values())
        return f"NGBH #{self.chunk_id}: {self.chunk_label} (v{self.version}, {len(self.inventory_by_id)} inventories, {inv_count} items)"
