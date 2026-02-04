"""
IFF Chunks package - all chunk type implementations.

This package contains 38+ chunk type classes for reading and writing IFF files.
For organization, import mappings, and write operation status, see:
    ../../../Docs/CHUNK_MANIFEST.md

⚠️ NOTE: Many write operations are implemented but UNTESTED for Phase 4-5 (save editing).
See CHUNK_MANIFEST.md for detailed status and testing recommendations.
"""
from .str_ import STR, CTSS, STRItem, STRLanguageSet, STRLangCode
from .objd import OBJD, OBJDType
from .bhav import BHAV, BHAVInstruction
from .spr import SPR, SPR2, SPRFrame, SPR2Frame
from .dgrp import DGRP, DGRPImage, DGRPSprite, DGRPSpriteFlags
from .bcon import BCON
from .glob import GLOB
from .slot import SLOT, SLOTItem, SLOTFlags, SLOTFacing
from .ttab import TTAB, TTABInteraction, TTABMotiveEntry, TTABFlags, TSOFlags
from .fami import FAMI
from .ngbh import NGBH, InventoryItem
from .nbrs import NBRS, Neighbour
from .palt import PALT
from .objf import OBJf, OBJfFunctionEntry
from .tprp import TPRP
from .trcn import TRCN, TRCNEntry
from .ttas import TTAs
from .fwav import FWAV
from .anim import ANIM, ANIMChunk, AnimationSequence, AnimationFrame, BoneKeyframe
# Batch 2 - Simple chunks
from .fams import FAMs
from .bmp import BMP, PNG
from .thmb import THMB
from .fsov import FSOV
from .fsor import FSOR, DGRPRCParams
from .hous import HOUS
from .mtex import MTEX
from .fsom import FSOM
from .fcns import FCNS, FCNSConstant
from .walm import WALm, FLRm, WALmEntry
from .objt import OBJT, OBJTEntry
from .arry import ARRY, ARRYType
# Batch 3 - Medium/complex chunks
from .simi import SIMI, SIMIBudgetDay
from .part import PART
from .piff import PIFF, PIFFEntry, PIFFPatch, PIFFEntryType, PIFFPatchMode
from .field_encode import IffFieldEncode
from .carr import CARR, JobLevel
from .tree import TREE, TREEBox, TREEBoxType
from .objm import (
    OBJM, OBJMInstance, OBJMPerson, OBJMStackFrame,
    OBJMInteraction, OBJMInteractionFlags, OBJMRoutingState,
    OBJMMultitile, OBJMFootprint, OBJMMotiveDelta,
    OBJMAccessory, OBJMObjectUse, OBJMSlot, OBJMRelationshipEntry
)

# Resource management chunks
from .rsmp import RSMP, RsmpEntry, RsmpTypeGroup
from .posi import POSI

# Unhandled/Legacy chunks from FreeSO
from .xxxx import XXXX
from .tmpl import TMPL
from .cats import CATS
from .pers import pers

# Phase 15-18: BHAV Decompiler - Full decompiler/editor for behavior scripts
from .bhav_decompiler import BHAVDecompiler, BHAVValidator, decompile_bhav
from .bhav_formatter import BHAVFormatter, CodeStyle, format_bhav
from .bhav_graph import analyze_bhav_flow, visualize_bhav_ascii
from .bhav_analysis import lint_bhav, analyze_bhav
from .bhav_editor import open_bhav_editor
# bhav_integration removed - was importing from simobliterator (old architecture)
from .bhav_ast import BehaviorAST, Instruction, VMVariableScope, VariableRef
from .primitive_registry import (
    PRIMITIVE_REGISTRY, get_primitive_info, get_primitive_name
)

__all__ = [
    'STR', 'CTSS', 'STRItem', 'STRLanguageSet', 'STRLangCode',
    'OBJD', 'OBJDType',
    'BHAV', 'BHAVInstruction',
    'SPR', 'SPR2', 'SPRFrame', 'SPR2Frame',
    'DGRP', 'DGRPImage', 'DGRPSprite', 'DGRPSpriteFlags',
    'BCON',
    'GLOB',
    'SLOT', 'SLOTItem', 'SLOTFlags', 'SLOTFacing',
    'TTAB', 'TTABInteraction', 'TTABMotiveEntry', 'TTABFlags', 'TSOFlags',
    'FAMI',
    'NGBH', 'InventoryItem',
    'NBRS', 'Neighbour',
    'PALT',
    'OBJf', 'OBJfFunctionEntry',
    'TPRP',
    'TRCN', 'TRCNEntry',
    'TTAs',
    'FWAV',
    'ANIM', 'ANIMChunk', 'AnimationSequence', 'AnimationFrame', 'BoneKeyframe',
    # Batch 2
    'FAMs',
    'BMP', 'PNG',
    'THMB',
    'FSOV',
    'FSOR', 'DGRPRCParams',
    'HOUS',
    'MTEX',
    'FSOM',
    'FCNS', 'FCNSConstant',
    'WALm', 'FLRm', 'WALmEntry',
    'OBJT', 'OBJTEntry',
    'ARRY', 'ARRYType',
    # Batch 3
    'SIMI', 'SIMIBudgetDay',
    'PART',
    'PIFF', 'PIFFEntry', 'PIFFPatch', 'PIFFEntryType', 'PIFFPatchMode',
    'IffFieldEncode',
    'CARR', 'JobLevel',
    'TREE', 'TREEBox', 'TREEBoxType',
    'OBJM', 'OBJMInstance', 'OBJMPerson', 'OBJMStackFrame',
    'OBJMInteraction', 'OBJMInteractionFlags', 'OBJMRoutingState',
    'OBJMMultitile', 'OBJMFootprint', 'OBJMMotiveDelta',
    'OBJMAccessory', 'OBJMObjectUse', 'OBJMSlot', 'OBJMRelationshipEntry',
    # Unhandled/Legacy chunks from FreeSO
    'XXXX', 'TMPL', 'CATS', 'pers',
    # BHAV Decompiler (Phase 15-18)
    'BHAVDecompiler', 'BHAVValidator', 'decompile_bhav',
    'BHAVFormatter', 'CodeStyle', 'format_bhav',
    'analyze_bhav_flow', 'visualize_bhav_ascii',
    'lint_bhav', 'analyze_bhav',
    'open_bhav_editor',
    'EditorFactory', 'get_bhav_preview', 'open_bhav_in_editor',
    'BHAVContentManager', 'register_bhav_editor',
    'BehaviorAST', 'Instruction', 'VMVariableScope', 'VariableRef',
    'PRIMITIVE_REGISTRY', 'get_primitive_info', 'get_primitive_name',
    # Resource management
    'RSMP', 'RsmpEntry', 'RsmpTypeGroup',
    'POSI',
]
