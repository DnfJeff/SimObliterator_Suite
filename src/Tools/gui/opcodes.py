"""
BHAV opcode definitions and utilities.
Maps opcodes to names and categories.
"""

from .theme import NodeColors


# Opcode to category mapping
OPCODE_CATEGORIES = {
    0: "Control", 1: "Control", 2: "Math", 4: "Position", 5: "Position",
    6: "Sim", 7: "Looks", 8: "Math", 11: "Math", 12: "Math", 13: "Control",
    14: "Control", 15: "Debug", 16: "Position", 17: "Control", 18: "Object",
    20: "Control", 21: "Looks", 22: "Sim", 23: "Looks", 25: "Sim",
    26: "Sim", 27: "Position", 28: "Control", 29: "Sim", 31: "Object", 32: "Object"
}

# Opcode to human-readable name
OPCODE_NAMES = {
    0: "Sleep",
    1: "GenericTSOCall",
    2: "Expression",
    4: "Grab",
    5: "Drop",
    6: "ChangeSuit",
    7: "Refresh",
    8: "RandomNumber",
    11: "GetDistanceTo",
    12: "GetDirectionTo",
    13: "PushInteraction",
    14: "FindBestObject",
    15: "Breakpoint",
    16: "FindLocationFor",
    17: "IdleForInput",
    18: "RemoveObject",
    20: "RunFunctionalTree",
    21: "ShowString",
    22: "LookTowards",
    23: "PlaySound",
    25: "TransferFunds",
    26: "Relationship",
    27: "GotoRelative",
    28: "RunTreeByName",
    29: "SetMotiveChange",
    31: "SetToNext",
    32: "TestObjectType"
}

# Category to color mapping
CATEGORY_COLORS = {
    "Control": NodeColors.CONTROL,
    "Debug": NodeColors.DEBUG,
    "Math": NodeColors.MATH,
    "Sim": NodeColors.SIM,
    "Object": NodeColors.OBJECT,
    "Looks": NodeColors.LOOKS,
    "Position": NodeColors.POSITION,
}


def get_opcode_name(opcode: int) -> str:
    """Get human-readable name for an opcode."""
    if opcode >= 256:
        return f"Sub 0x{opcode:04X}"
    return OPCODE_NAMES.get(opcode, f"Op 0x{opcode:02X}")


def get_opcode_category(opcode: int) -> str:
    """Get category for an opcode."""
    if opcode >= 256:
        return "Subroutine"
    return OPCODE_CATEGORIES.get(opcode, "Unknown")


def get_node_color(opcode: int) -> tuple:
    """Get node color for an opcode based on its category."""
    if opcode >= 256:
        return NodeColors.SUBROUTINE
    category = get_opcode_category(opcode)
    return CATEGORY_COLORS.get(category, NodeColors.UNKNOWN)


def format_pointer(ptr: int) -> str:
    """Format a branch pointer for display."""
    if ptr == 0xFF:
        return "TRUE"
    elif ptr == 0xFE:
        return "FALSE"
    elif ptr == 0xFD:
        return "ERROR"
    return str(ptr)
