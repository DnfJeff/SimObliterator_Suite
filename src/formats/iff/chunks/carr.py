"""
CARR Chunk - Career Data
Port of FreeSO's tso.files/Formats/IFF/Chunks/CARR.cs

Contains career/job level information with field-encoded compression.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

from ..base import IffChunk, register_chunk
from .field_encode import IffFieldEncode

if TYPE_CHECKING:
    from ..iff_file import IffFile
    from ....utils.binary import IoBuffer, IoWriter


@dataclass
class JobLevel:
    """A single job level in a career."""
    min_required: List[int] = field(default_factory=lambda: [0] * 10)  # Friends, then skills
    motive_delta: List[int] = field(default_factory=lambda: [0] * 7)
    salary: int = 0
    start_time: int = 0
    end_time: int = 0
    car_type: int = 0
    
    job_name: str = ""
    male_uniform_mesh: str = ""
    female_uniform_mesh: str = ""
    uniform_skin: str = ""
    unknown: str = ""
    
    def read(self, iop: IffFieldEncode):
        """Read job level from field-encoded stream."""
        self.min_required = [iop.read_int32() for _ in range(10)]
        self.motive_delta = [iop.read_int32() for _ in range(7)]
        self.salary = iop.read_int32()
        self.start_time = iop.read_int32()
        self.end_time = iop.read_int32()
        self.car_type = iop.read_int32()
        
        self.job_name = iop.read_string(False)
        self.male_uniform_mesh = iop.read_string(False)
        self.female_uniform_mesh = iop.read_string(False)
        self.uniform_skin = iop.read_string(False)
        self.unknown = iop.read_string(True)


@register_chunk('CARR')
@dataclass
class CARR(IffChunk):
    """
    Career data chunk.
    Contains job levels with requirements, pay, hours, and uniforms.
    Uses field-encoded compression.
    """
    name: str = ""
    job_levels: List[JobLevel] = field(default_factory=list)
    
    def read(self, iff: 'IffFile', stream: 'IoBuffer'):
        """Read CARR chunk."""
        pad = stream.read_uint32()
        version = stream.read_uint32()
        magic = stream.read_uint32()  # "ObjM" or similar
        
        compression_code = stream.read_byte()
        if compression_code != 1:
            raise ValueError(f"Unexpected CARR compression code: {compression_code}")
        
        self.name = stream.read_null_terminated_string()
        if len(self.name) % 2 == 1:
            stream.read_byte()  # Padding
        
        # Field-encoded data
        iop = IffFieldEncode(stream)
        
        num_levels = iop.read_int32()
        self.job_levels = []
        
        for _ in range(num_levels):
            level = JobLevel()
            level.read(iop)
            self.job_levels.append(level)
    
    def get_job_data(self, level: int, data: int) -> int:
        """
        Get job data value.
        
        Args:
            level: Job level index
            data: Data type:
                0 = number of levels
                1 = salary
                2-11 = min required (friends, skills)
                12 = start hour
                13 = end hour
                14-20 = motive delta
                21 = car type
        """
        if data == 0:
            return len(self.job_levels)
        
        if level >= len(self.job_levels):
            return 0
        
        entry = self.job_levels[level]
        
        if data == 1:
            return entry.salary
        elif data == 12:
            return entry.start_time
        elif data == 13:
            return entry.end_time
        elif data == 21:
            return entry.car_type
        elif data == 22:
            return 0
        elif 2 <= data < 12:
            return entry.min_required[data - 2]
        elif 14 <= data <= 20:
            return entry.motive_delta[data - 14]
        
        return 0
    
    def __len__(self) -> int:
        return len(self.job_levels)
