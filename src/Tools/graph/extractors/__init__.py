"""Extractors package."""

from .registry import ExtractorRegistry

# Import all extractors to register them
from . import objd
from . import objf
from . import spr
from . import bhav
from . import ttab
from . import str_
from . import bcon
from . import dgrp
from . import slot
