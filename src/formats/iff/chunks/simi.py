"""
SIMI Chunk - Sim Instance Data
Port of FreeSO's tso.files/Formats/IFF/Chunks/SIMI.cs

Contains simulation globals, lot values, and budget tracking.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

from ..base import IffChunk, register_chunk

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@dataclass
class SIMIBudgetDay:
    """Budget tracking for a single day."""
    valid: int = 0
    misc_income: int = 0
    job_income: int = 0
    service_expense: int = 0
    food_expense: int = 0
    bills_expense: int = 0
    misc_expense: int = 0
    household_expense: int = 0
    architecture_expense: int = 0
    
    def read(self, stream: 'IoBuffer'):
        """Read budget day from stream."""
        self.valid = stream.read_int32()
        if self.valid == 0:
            return
        self.misc_income = stream.read_int32()
        self.job_income = stream.read_int32()
        self.service_expense = stream.read_int32()
        self.food_expense = stream.read_int32()
        self.bills_expense = stream.read_int32()
        self.misc_expense = stream.read_int32()
        self.household_expense = stream.read_int32()
        self.architecture_expense = stream.read_int32()
    
    def write(self, stream: 'IoWriter'):
        """Write budget day to stream."""
        stream.write_int32(self.valid)
        if self.valid == 0:
            return
        stream.write_int32(self.misc_income)
        stream.write_int32(self.job_income)
        stream.write_int32(self.service_expense)
        stream.write_int32(self.food_expense)
        stream.write_int32(self.bills_expense)
        stream.write_int32(self.misc_expense)
        stream.write_int32(self.household_expense)
        stream.write_int32(self.architecture_expense)


@register_chunk('SIMI')
@dataclass
class SIMI(IffChunk):
    """
    Sim instance data chunk.
    Contains global simulation data, lot values, and budget history.
    """
    version: int = 0
    global_data: List[int] = field(default_factory=list)  # 38 shorts
    
    unknown1: int = 0
    unknown2: int = 0
    unknown3: int = 0
    guid1: int = 0
    guid2: int = 0  # Changes on bulldoze
    unknown4: int = 0
    lot_value: int = 0
    objects_value: int = 0
    architecture_value: int = 0
    
    budget_days: List[SIMIBudgetDay] = field(default_factory=list)  # 6 days
    
    @property
    def purchase_value(self) -> int:
        """Calculate purchase value of lot."""
        return self.lot_value + self.objects_value + (self.architecture_value * 7) // 10
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read SIMI chunk."""
        pad = stream.read_uint32()
        self.version = stream.read_uint32()
        magic = stream.read_cstring(4)  # "IMIS"
        
        # Version > 0x3F has 64 items, else 32
        items = 0x40 if self.version > 0x3F else 0x20
        
        self.global_data = []
        for i in range(items):
            val = stream.read_int16()
            if i < 38:
                self.global_data.append(val)
        
        self.unknown1 = stream.read_int16()
        self.unknown2 = stream.read_int32()
        self.unknown3 = stream.read_int32()
        self.guid1 = stream.read_int32()
        self.guid2 = stream.read_int32()
        self.unknown4 = stream.read_int32()
        self.lot_value = stream.read_int32()
        self.objects_value = stream.read_int32()
        self.architecture_value = stream.read_int32()
        
        # Budget history - 6 days
        self.budget_days = []
        for _ in range(6):
            day = SIMIBudgetDay()
            day.read(stream)
            self.budget_days.append(day)
    
    def write(self, iff: 'IffFile', stream: 'IoWriter') -> bool:
        """Write SIMI chunk."""
        stream.write_int32(0)
        stream.write_int32(0x3E)  # Version
        stream.write_cstring("IMIS", 4)
        
        items = 0x40 if self.version > 0x3E else 0x20
        
        for i in range(items):
            if i < len(self.global_data):
                stream.write_int16(self.global_data[i])
            else:
                stream.write_int16(0)
        
        stream.write_int16(self.unknown1)
        stream.write_int32(self.unknown2)
        stream.write_int32(self.unknown3)
        stream.write_int32(self.guid1)
        stream.write_int32(self.guid2)
        stream.write_int32(self.unknown4)
        stream.write_int32(self.lot_value)
        stream.write_int32(self.objects_value)
        stream.write_int32(self.architecture_value)
        
        for day in self.budget_days:
            day.write(stream)
        
        return True
