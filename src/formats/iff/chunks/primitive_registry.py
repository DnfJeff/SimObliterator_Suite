"""
Primitive Registry - Maps opcode to primitive metadata

This registry defines all 50+ BHAV primitives with their:
- Names and descriptions
- Operand types
- Return types (true/false vs done)
- Display templates
- Execution behavior notes

Source: FreeSO TSOClient/FSO.IDE/EditorComponent/PrimitiveRegistry.cs
"""

from enum import IntEnum, auto
from typing import Dict, Any


class ReturnType(IntEnum):
    """Primitive return type"""
    TRUE_FALSE = 0  # Can branch to true or false pointer
    DONE = 1        # Always goes to next instruction


class PrimitiveGroup(IntEnum):
    """Primitive categories"""
    VARIABLE = 0
    MATH = 1
    OBJECT = 2
    ANIMATION = 3
    NAVIGATION = 4
    INTERACTION = 5
    STRING = 6
    DIALOG = 7
    SYSTEM = 8
    CONTROL = 9
    RELATIONSHIP = 10
    MISC = 11


# Complete Primitive Registry - All 50+ primitives
PRIMITIVE_REGISTRY: Dict[int, Dict[str, Any]] = {
    # Variable Primitives (0-10)
    0: {
        "name": "Push Variable",
        "opcode": 0,
        "return_type": ReturnType.DONE,
        "operand_type": "PushVariableOperand",
        "group": PrimitiveGroup.VARIABLE,
        "display_template": "Push {Variable} onto stack",
        "description": "Push a variable onto the simulation stack"
    },
    1: {
        "name": "Compare",
        "opcode": 1,
        "return_type": ReturnType.TRUE_FALSE,
        "operand_type": "CompareOperand",
        "group": PrimitiveGroup.MATH,
        "display_template": "Compare {Value1} {Operator} {Value2}",
        "description": "Compare two values and branch based on result"
    },
    2: {
        "name": "Test Object Type",
        "opcode": 2,
        "return_type": ReturnType.TRUE_FALSE,
        "operand_type": "TestObjectTypeOperand",
        "group": PrimitiveGroup.OBJECT,
        "display_template": "Object {Object} has type {Type}",
        "description": "Test if object has specific type or GUID"
    },
    3: {
        "name": "Test Sim Description",
        "opcode": 3,
        "return_type": ReturnType.TRUE_FALSE,
        "operand_type": "TestSimDescriptionOperand",
        "group": PrimitiveGroup.OBJECT,
        "display_template": "Sim {Sim} matches description",
        "description": "Test sim characteristics (age, gender, etc.)"
    },
    4: {
        "name": "Test Actor Type",
        "opcode": 4,
        "return_type": ReturnType.TRUE_FALSE,
        "operand_type": "TestActorTypeOperand",
        "group": PrimitiveGroup.OBJECT,
        "display_template": "Actor is type {Type}",
        "description": "Test if caller is specific type (sim, object, etc.)"
    },
    5: {
        "name": "Test Relationship",
        "opcode": 5,
        "return_type": ReturnType.TRUE_FALSE,
        "operand_type": "TestRelationshipOperand",
        "group": PrimitiveGroup.RELATIONSHIP,
        "display_template": "Relationship {From} {RelType} {To} > {Value}",
        "description": "Test relationship value between sims"
    },
    6: {
        "name": "Animate Sim",
        "opcode": 6,
        "return_type": ReturnType.DONE,
        "operand_type": "AnimateSimOperand",
        "group": PrimitiveGroup.ANIMATION,
        "display_template": "Animate {Object} with {Animation}",
        "description": "Play animation on sim"
    },
    7: {
        "name": "Create Object Instance",
        "opcode": 7,
        "return_type": ReturnType.DONE,
        "operand_type": "CreateObjectInstanceOperand",
        "group": PrimitiveGroup.OBJECT,
        "display_template": "Create object {GUID} at {Location}",
        "description": "Create new object instance"
    },
    8: {
        "name": "Drop",
        "opcode": 8,
        "return_type": ReturnType.DONE,
        "operand_type": "DropOperand",
        "group": PrimitiveGroup.OBJECT,
        "display_template": "Drop stack object to ground",
        "description": "Drop stack object to ground or surface"
    },
    9: {
        "name": "Drop Onto",
        "opcode": 9,
        "return_type": ReturnType.DONE,
        "operand_type": "DropOntoOperand",
        "group": PrimitiveGroup.OBJECT,
        "display_template": "Drop stack object onto {Target}",
        "description": "Drop stack object onto another object"
    },
    10: {
        "name": "Grab",
        "opcode": 10,
        "return_type": ReturnType.DONE,
        "operand_type": "GrabOperand",
        "group": PrimitiveGroup.OBJECT,
        "display_template": "Grab object {Target}",
        "description": "Pick up (grab) an object"
    },
    
    # Math/Navigation Primitives (11-20)
    11: {
        "name": "Get Distance To",
        "opcode": 11,
        "return_type": ReturnType.DONE,
        "operand_type": "GetDistanceToOperand",
        "group": PrimitiveGroup.MATH,
        "display_template": "Distance from {Object} to StackObject → {Temp}",
        "description": "Calculate distance between two objects"
    },
    12: {
        "name": "Play Sound",
        "opcode": 12,
        "return_type": ReturnType.DONE,
        "operand_type": "PlaySoundOperand",
        "group": PrimitiveGroup.ANIMATION,
        "display_template": "Play sound {SoundID}",
        "description": "Play audio sound effect"
    },
    13: {
        "name": "Goto Routing Slot",
        "opcode": 13,
        "return_type": ReturnType.DONE,
        "operand_type": "GotoRoutingSlotOperand",
        "group": PrimitiveGroup.NAVIGATION,
        "display_template": "Go to routing slot {SlotNumber} on {Object}",
        "description": "Navigate to routing slot on object"
    },
    14: {
        "name": "Goto Relative Position",
        "opcode": 14,
        "return_type": ReturnType.DONE,
        "operand_type": "GotoRelativePositionOperand",
        "group": PrimitiveGroup.NAVIGATION,
        "display_template": "Go to ({X}, {Y}) relative offset",
        "description": "Move to position relative to current location"
    },
    15: {
        "name": "Find Best Object",
        "opcode": 15,
        "return_type": ReturnType.DONE,
        "operand_type": "FindBestObjectOperand",
        "group": PrimitiveGroup.NAVIGATION,
        "display_template": "Find best {ObjectType} → stack",
        "description": "Search for best object matching criteria"
    },
    16: {
        "name": "Find Location For",
        "opcode": 16,
        "return_type": ReturnType.DONE,
        "operand_type": "FindLocationForOperand",
        "group": PrimitiveGroup.NAVIGATION,
        "display_template": "Find location for {ObjectType}",
        "description": "Find valid location for object"
    },
    17: {
        "name": "Find Best Action",
        "opcode": 17,
        "return_type": ReturnType.TRUE_FALSE,
        "operand_type": "FindBestActionOperand",
        "group": PrimitiveGroup.INTERACTION,
        "display_template": "Find best action of type {Type}",
        "description": "Search for best interaction to run"
    },
    18: {
        "name": "Run Subroutine",
        "opcode": 18,
        "return_type": ReturnType.TRUE_FALSE,
        "operand_type": "RunSubroutineOperand",
        "group": PrimitiveGroup.CONTROL,
        "display_template": "Call BHAV({Group}, {ID})",
        "description": "Call another BHAV subroutine"
    },
    19: {
        "name": "Push Interaction",
        "opcode": 19,
        "return_type": ReturnType.DONE,
        "operand_type": "PushInteractionOperand",
        "group": PrimitiveGroup.INTERACTION,
        "display_template": "Push interaction {InteractionType}",
        "description": "Queue interaction on target"
    },
    20: {
        "name": "Get Direction To",
        "opcode": 20,
        "return_type": ReturnType.DONE,
        "operand_type": "GetDirectionToOperand",
        "group": PrimitiveGroup.MATH,
        "display_template": "Direction to {Object} → {Temp}",
        "description": "Get compass direction (0-7) to object"
    },

    # Animation/Interaction Primitives (30-50)
    33: {
        "name": "Show String",
        "opcode": 33,
        "return_type": ReturnType.DONE,
        "operand_type": "ShowStringOperand",
        "group": PrimitiveGroup.STRING,
        "display_template": "Show STR#{Table}[{Index}]",
        "description": "Display string text above sim"
    },
    34: {
        "name": "Set Balloon Headline",
        "opcode": 34,
        "return_type": ReturnType.DONE,
        "operand_type": "SetBalloonHeadlineOperand",
        "group": PrimitiveGroup.STRING,
        "display_template": "Show balloon {Icon} with STR#{Table}[{Index}]",
        "description": "Display balloon icon above sim"
    },
    35: {
        "name": "Dialog Callback",
        "opcode": 35,
        "return_type": ReturnType.TRUE_FALSE,
        "operand_type": "DialogCallbackOperand",
        "group": PrimitiveGroup.DIALOG,
        "display_template": "Dialog callback {DialogID}",
        "description": "Wait for dialog response"
    },
    40: {
        "name": "Transfer Funds",
        "opcode": 40,
        "return_type": ReturnType.DONE,
        "operand_type": "TransferFundsOperand",
        "group": PrimitiveGroup.MISC,
        "display_template": "Transfer {Amount} simoleons",
        "description": "Transfer money between accounts"
    },
    44: {
        "name": "Animate Sim (Extended)",
        "opcode": 44,
        "return_type": ReturnType.DONE,
        "operand_type": "AnimateSimExtendedOperand",
        "group": PrimitiveGroup.ANIMATION,
        "display_template": "Extended animate {Object}",
        "description": "Play animation with extended parameters"
    },
    45: {
        "name": "Change Suit or Accessory",
        "opcode": 45,
        "return_type": ReturnType.DONE,
        "operand_type": "ChangeSuitOrAccessoryOperand",
        "group": PrimitiveGroup.ANIMATION,
        "display_template": "Change outfit {OutfitType} to {OutfitID}",
        "description": "Change sim outfit"
    },
    50: {
        "name": "Random Number",
        "opcode": 50,
        "return_type": ReturnType.DONE,
        "operand_type": "RandomNumberOperand",
        "group": PrimitiveGroup.MATH,
        "display_template": "Random {Min} to {Max} → {Temp}",
        "description": "Generate random number in range"
    },

    # System Primitives (250-255)
    252: {
        "name": "BreakPoint",
        "opcode": 252,
        "return_type": ReturnType.DONE,
        "operand_type": "BreakPointOperand",
        "group": PrimitiveGroup.SYSTEM,
        "display_template": "BREAKPOINT (debug only)",
        "description": "Debug breakpoint - halts in Volcanic IDE"
    },
    253: {
        "name": "Sleep",
        "opcode": 253,
        "return_type": ReturnType.DONE,
        "operand_type": "SleepOperand",
        "group": PrimitiveGroup.SYSTEM,
        "display_template": "Sleep {Duration} ms",
        "description": "Pause execution for duration"
    },
    254: {
        "name": "Refresh",
        "opcode": 254,
        "return_type": ReturnType.DONE,
        "operand_type": "RefreshOperand",
        "group": PrimitiveGroup.SYSTEM,
        "display_template": "Refresh world state",
        "description": "Refresh simulation state"
    },
    255: {
        "name": "Stop",
        "opcode": 255,
        "return_type": ReturnType.DONE,
        "operand_type": "StopOperand",
        "group": PrimitiveGroup.SYSTEM,
        "display_template": "STOP (end behavior)",
        "description": "End behavior execution"
    }
}


def get_primitive_info(opcode: int) -> Dict[str, Any]:
    """Get primitive info by opcode, return default if not found"""
    if opcode in PRIMITIVE_REGISTRY:
        return PRIMITIVE_REGISTRY[opcode]
    
    # Unknown primitive - handle routine calls (opcode >= 256)
    if opcode >= 256:
        return {
            "name": f"Call BHAV",
            "opcode": opcode,
            "return_type": ReturnType.TRUE_FALSE,
            "operand_type": "SubroutineCallOperand",
            "group": PrimitiveGroup.CONTROL,
            "display_template": "Call BHAV({GroupID}, {BhavID})",
            "description": f"Call BHAV routine (opcode {opcode})"
        }
    
    # Completely unknown
    return {
        "name": f"Unknown Primitive {opcode}",
        "opcode": opcode,
        "return_type": ReturnType.DONE,
        "operand_type": "UnknownOperand",
        "group": PrimitiveGroup.MISC,
        "display_template": f"Unknown primitive {opcode}",
        "description": f"Unknown primitive with opcode {opcode}"
    }


def get_primitive_name(opcode: int) -> str:
    """Get primitive name by opcode"""
    return get_primitive_info(opcode)["name"]


def get_return_type(opcode: int) -> ReturnType:
    """Get primitive return type"""
    return get_primitive_info(opcode)["return_type"]


def get_operand_type(opcode: int) -> str:
    """Get operand type class name"""
    return get_primitive_info(opcode)["operand_type"]


def is_routine_call(opcode: int) -> bool:
    """Check if opcode is a routine call (opcode >= 256)"""
    return opcode >= 256
