"""
BHAV AST (Abstract Syntax Tree) - Structured representation of BHAV behavior

This defines the in-memory representation of a BHAV after decompilation.
Used as intermediate format between binary and display/analysis.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import IntEnum


class VMVariableScope(IntEnum):
    """Variable scope enumeration (from FreeSO)"""
    PARAMETERS = 0      # Function arguments
    LOCALS = 1          # Local variables
    OBJECT_DATA = 4     # Per-object attributes
    GLOBAL = 5          # Global simulation state
    TEMPS = 6           # Temporary registers (0-15)
    DYNAMIC_SPRITE_ID = 7
    DYNAMIC_TILE_ID = 8


# ============================================================================
# Enums for Operand Types
# ============================================================================

class VMExpressionOperator(IntEnum):
    """Expression operation types"""
    GREATER_THAN = 0
    LESS_THAN = 1
    EQUALS = 2
    PLUS_EQUALS = 3
    MINUS_EQUALS = 4
    ASSIGN = 5
    MUL_EQUALS = 6
    DIV_EQUALS = 7
    IS_FLAG_SET = 8
    SET_FLAG = 9
    CLEAR_FLAG = 10
    INC_AND_LESS_THAN = 11
    MOD_EQUALS = 12
    AND_EQUALS = 13
    GREATER_THAN_OR_EQUAL = 14
    LESS_THAN_OR_EQUAL = 15
    NOT_EQUAL_TO = 16
    DEC_AND_GREATER_THAN = 17
    PUSH = 18
    POP = 19
    TS1_OR_EQUALS = 18
    TS1_XOR_EQUALS = 19
    TS1_ASSIGN_SQRT_RHS = 20


class VMAnimationScope(IntEnum):
    """Animation scope for Animate Sim"""
    OBJECT = 0
    STACK_OBJECT = 1
    CUSTOM = 2


class VMCreateObjectPosition(IntEnum):
    """Create object position modes"""
    UNDERNEATH_ME = 0
    ON_TOP_OF_ME = 1
    BELOW_OBJECT_IN_LOCAL = 2
    BELOW_OBJECT_IN_STACK_PARAM0 = 3
    OUT_OF_WORLD = 4
    IN_SLOT0_OF_STACK_OBJECT = 5
    IN_MY_HAND = 6
    IN_FRONT_OF_STACK_OBJECT = 7
    IN_FRONT_OF_ME = 8
    NEXT_TO_ME_IN_DIRECTION_OF_LOCAL = 9


class VMMotive(IntEnum):
    """Motive types"""
    ENERGY = 0
    COMFORT = 1
    HUNGER = 2
    HYGIENE = 3
    BLADDER = 4
    MOOD = 5
    SOCIAL = 6
    ROOM = 7
    FUN = 8


# Operand base class (for type hints)
class VMPrimitiveOperand:
    """Base class for all operand types"""
    pass


# ============================================================================
# AST Node Classes
# ============================================================================

@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    pass


@dataclass
class Instruction(ASTNode):
    """Single BHAV instruction in AST form"""
    index: int                           # Instruction index (0-255)
    opcode: int                          # Primitive opcode
    operand: Optional[Dict[str, Any]]    # Parsed operand data
    true_pointer: int                    # Branch if true
    false_pointer: int                   # Branch if false
    primitive_name: str = ""             # Human-readable name
    
    def is_conditional(self) -> bool:
        """Check if instruction branches to different addresses"""
        return self.true_pointer != self.false_pointer
    
    def is_done(self) -> bool:
        """Check if both pointers point past end (done instruction)"""
        return self.true_pointer == self.false_pointer
    
    def __str__(self) -> str:
        return f"[{self.index}] {self.primitive_name}"


@dataclass
class BasicBlock(ASTNode):
    """Group of instructions with linear control flow"""
    label: str
    instructions: List[Instruction]
    
    def __str__(self) -> str:
        return f"Block {self.label} ({len(self.instructions)} instructions)"


@dataclass
class ControlFlowGraph(ASTNode):
    """Control flow graph representation"""
    blocks: Dict[str, BasicBlock]  # label -> block
    entry_block: str                # Starting block label
    exit_block: str                 # Ending block label
    edges: Dict[str, List[tuple]]   # block_label -> [(target_label, condition)]
    
    def get_block(self, label: str) -> Optional[BasicBlock]:
        return self.blocks.get(label)
    
    def get_edges_from(self, label: str) -> List[tuple]:
        return self.edges.get(label, [])


@dataclass
class BehaviorAST(ASTNode):
    """Complete AST for a BHAV behavior"""
    # Metadata
    args: int                                # Number of arguments
    locals: int                              # Number of local variables
    behavior_type: int                       # BHAV type
    
    # Instructions
    instructions: List[Instruction] = None   # Linear instruction list
    cfg: Optional[ControlFlowGraph] = None   # Control flow graph
    
    # Source tracking
    source_bhav: Optional[Any] = None        # Original BHAV chunk (for reference)
    
    def __post_init__(self):
        if self.instructions is None:
            self.instructions = []
    
    # Backward compatibility properties
    @property
    def arg_count(self) -> int:
        """Alias for args (backward compatibility)"""
        return self.args
    
    @property
    def local_count(self) -> int:
        """Alias for locals (backward compatibility)"""
        return self.locals
    
    @property
    def local_variables(self) -> int:
        """Alias for locals (backward compatibility)"""
        return self.locals
    
    def add_instruction(self, instr: Instruction):
        """Add instruction to AST"""
        self.instructions.append(instr)
    
    def build_cfg(self) -> ControlFlowGraph:
        """Build control flow graph from instruction list"""
        if self.cfg is not None:
            return self.cfg
        
        # TODO: Implement CFG building
        # For now, return empty CFG
        self.cfg = ControlFlowGraph(
            blocks={},
            entry_block="block_0",
            exit_block="block_end",
            edges={}
        )
        return self.cfg
    
    def get_instruction(self, index: int) -> Optional[Instruction]:
        """Get instruction by index"""
        if 0 <= index < len(self.instructions):
            return self.instructions[index]
        return None
    
    def __str__(self) -> str:
        return f"BHAV(args={self.args}, locals={self.locals}, instructions={len(self.instructions)})"


# ============================================================================
# Variable Reference Classes
# ============================================================================

@dataclass
class VariableRef(ASTNode):
    """Reference to a variable"""
    scope: VMVariableScope
    index: int
    
    def __hash__(self) -> int:
        """Make VariableRef hashable"""
        return hash((self.scope, self.index))
    
    def __str__(self) -> str:
        scope_names = {
            VMVariableScope.PARAMETERS: "Param",
            VMVariableScope.LOCALS: "Local",
            VMVariableScope.OBJECT_DATA: "ObjData",
            VMVariableScope.GLOBAL: "Global",
            VMVariableScope.TEMPS: "Temps",
        }
        scope_name = scope_names.get(self.scope, f"Scope{self.scope}")
        return f"{scope_name}[{self.index}]"


@dataclass
class TempRegister(VariableRef):
    """Temporary register reference (Temps[0-15])"""
    def __init__(self, index: int):
        super().__init__(VMVariableScope.TEMPS, index)


# ============================================================================
# Operand Classes
# ============================================================================

@dataclass
class PushVariableOperand(VMPrimitiveOperand):
    """Push Variable operand"""
    variable: VariableRef


@dataclass
class CompareOperand(VMPrimitiveOperand):
    """Compare operand"""
    value1: int
    comparison_type: int  # 0=equal, 1=less, 2=greater, 3=not equal
    value2: int


@dataclass
class AnimateSimOperand(VMPrimitiveOperand):
    """Animate Sim operand"""
    source: int          # 0=TSO, 1=TS1, 2=Custom
    animation_id: int
    block_id: int
    state_id: int


@dataclass
class GetDistanceToOperand(VMPrimitiveOperand):
    """Get Distance To operand"""
    temp_num: int
    flags: int
    object_scope: VMVariableScope
    scope_data: int


@dataclass
class PlaySoundOperand(VMPrimitiveOperand):
    """Play Sound operand"""
    sound_id: int
    volume: int
    pitch: int


@dataclass
class RandomNumberOperand(VMPrimitiveOperand):
    """Random Number operand"""
    min_value: int
    max_value: int
    temp_num: int


@dataclass
class CreateObjectInstanceOperand(VMPrimitiveOperand):
    """Create Object Instance operand"""
    object_guid: int
    stack_object_flag: int
    scope_type: VMVariableScope
    scope_data: int


@dataclass
class DropOntoOperand(VMPrimitiveOperand):
    """Drop Onto operand"""
    target_scope: VMVariableScope
    target_offset: int
    drop_mode: int


@dataclass
class RunSubroutineOperand(VMPrimitiveOperand):
    """Run Subroutine / BHAV call operand"""
    group_id: int
    bhav_id: int
    argument_count: int = 0


@dataclass
class ShowStringOperand(VMPrimitiveOperand):
    """Show String operand"""
    string_table: int
    string_index: int
    duration: int


@dataclass
class UnknownOperand(VMPrimitiveOperand):
    """Unknown operand - raw bytes"""
    data: bytes
    
    def __str__(self) -> str:
        return f"UnknownOperand({self.data.hex()})"

# ============================================================================
# Missing Operand Types (Priority Implementation)
# ============================================================================

@dataclass
class ExpressionOperand(VMPrimitiveOperand):
    """Expression operand (fixed version)"""
    lhs_data: int
    rhs_data: int
    is_signed: bool
    operator: VMExpressionOperator
    lhs_owner: VMVariableScope
    rhs_owner: VMVariableScope


@dataclass
class TestObjectTypeOperand(VMPrimitiveOperand):
    """Test Object Type operand"""
    guid: int
    id_data: int
    id_owner: VMVariableScope


@dataclass
class GetDirectionToOperand(VMPrimitiveOperand):
    """Get Direction To operand"""
    result_data: int
    result_owner: VMVariableScope
    flags: int
    object_scope: VMVariableScope
    object_scope_data: int


@dataclass
class SetMotiveChangeOperand(VMPrimitiveOperand):
    """Set Motive Change operand"""
    delta_owner: VMVariableScope
    delta_data: int
    max_owner: VMVariableScope
    max_data: int
    flags: int
    motive: VMMotive
    clear_all: bool = False
    once: bool = False


@dataclass
class PlaySoundOperand(VMPrimitiveOperand):
    """Play Sound operand (fixed version)"""
    event_id: int
    flags: int
    volume: int
    pitch: int
    no_pan: bool = False
    no_zoom: bool = False
    loop: bool = False


@dataclass
class RandomNumberOperand(VMPrimitiveOperand):
    """Random Number operand (fixed version)"""
    range_scope: VMVariableScope
    range_data: int
    destination_scope: VMVariableScope
    destination_data: int


@dataclass
class ChangeSuitOrAccessoryOperand(VMPrimitiveOperand):
    """Change Suit or Accessory operand"""
    suit_data: int
    suit_scope: VMVariableScope
    flags: int


@dataclass
class RefreshOperand(VMPrimitiveOperand):
    """Refresh operand"""
    target_object: int
    refresh_type: int


@dataclass
class RelationshipOperand(VMPrimitiveOperand):
    """Relationship operand"""
    rel_var: int
    mode: int
    local: int
    flags: int


@dataclass
class SetBalloonHeadlineOperand(VMPrimitiveOperand):
    """Set Balloon Headline operand"""
    index: int
    group: int
    duration: int
    balloon_id: int


@dataclass
class ShowStringOperandFixed(VMPrimitiveOperand):
    """Show String operand (fixed version)"""
    string_table: int
    string_index: int
    flags: int


@dataclass
class SleepOperand(VMPrimitiveOperand):
    """Sleep operand"""
    stack_var_to_dec: int


@dataclass
class GotoRoutingSlotOperand(VMPrimitiveOperand):
    """Goto Routing Slot operand"""
    slot_data: int
    slot_type: int
    flags: int


@dataclass
class GotoRelativePositionOperand(VMPrimitiveOperand):
    """Goto Relative Position operand"""
    old_trap_count: int
    x: int
    y: int
    direction: int
    route_count: int
    flags: int


@dataclass
class DropOntoOperandFixed(VMPrimitiveOperand):
    """Drop Onto operand (fixed version)"""
    src_slot_mode: int
    src_slot_num: int
    dest_slot_mode: int
    dest_slot_num: int


@dataclass
class BurnOperand(VMPrimitiveOperand):
    """Burn operand"""
    burn_type: int
    burn_busy_objects: bool


@dataclass
class DialogOperand(VMPrimitiveOperand):
    """Dialog operand"""
    icon: int
    message_string_id: int
    string_table: int
    duration: int


@dataclass
class FindLocationForOperand(VMPrimitiveOperand):
    """Find Location For operand"""
    mode: int
    local: int
    flags: int
    radius: int
    min_proximity: int
    max_proximity: int


@dataclass
class IdleForInputOperand(VMPrimitiveOperand):
    """Idle For Input operand"""
    stack_var_to_dec: int
    allow_push: bool


@dataclass
class InventoryOperationsOperand(VMPrimitiveOperand):
    """Inventory Operations operand"""
    guid: int
    mode: int
    fso_scope: VMVariableScope
    fso_data: int
    ts1_scope: VMVariableScope
    ts1_data: int
    flags: int


@dataclass
class InvokePluginOperand(VMPrimitiveOperand):
    """Invoke Plugin operand"""
    person_local: int
    object_local: int
    event_local: int
    flags: int
    token: int


@dataclass
class LookTowardsOperand(VMPrimitiveOperand):
    """Look Towards operand"""
    mode: int


@dataclass
class PushInteractionOperand(VMPrimitiveOperand):
    """Push Interaction operand"""
    interaction: int
    object_location: int
    priority: int
    local: int
    flags: int


@dataclass
class RemoveObjectInstanceOperand(VMPrimitiveOperand):
    """Remove Object Instance operand"""
    target: int
    flags: int


@dataclass
class RunFunctionalTreeOperand(VMPrimitiveOperand):
    """Run Functional Tree operand"""
    function: int
    flags: int


@dataclass
class RunTreeByNameOperand(VMPrimitiveOperand):
    """Run Tree By Name operand"""
    string_table: int
    string_scope: VMVariableScope
    string_id: int
    flags: int


@dataclass
class SetToNextOperand(VMPrimitiveOperand):
    """Set To Next operand"""
    guid: int
    flags: int
    target_owner: VMVariableScope
    target_data: int
    search_type: int
    backwards: bool


@dataclass
class SnapOperand(VMPrimitiveOperand):
    """Snap operand"""
    index: int
    mode: int
    flags: int


@dataclass
class SpecialEffectOperand(VMPrimitiveOperand):
    """Special Effect operand"""
    timeout: int
    size: int
    zoom: int
    level: int
    effect_type: int


@dataclass
class StopAllSoundsOperand(VMPrimitiveOperand):
    """Stop All Sounds operand"""
    flags: int


@dataclass
class TS1InventoryOperationsOperand(VMPrimitiveOperand):
    """TS1 Inventory Operations operand"""
    mode: int
    token_type: int
    flags: int
    local: int
    guid_owner: VMVariableScope
    guid_data: int


@dataclass
class TS1MakeNewCharacterOperand(VMPrimitiveOperand):
    """TS1 Make New Character operand"""
    color_local: int
    age_local: int
    gender_local: int
    skin_tone_local: int


@dataclass
class BreakPointOperand(VMPrimitiveOperand):
    """Break Point operand"""
    data: int
    scope: VMVariableScope


@dataclass
class DialogGlobalStringsOperand(VMPrimitiveOperand):
    """Dialog Global Strings operand"""
    pass


@dataclass
class DialogPrivateStringsOperand(VMPrimitiveOperand):
    """Dialog Private Strings operand"""
    pass


@dataclass
class DialogSemiGlobalStringsOperand(VMPrimitiveOperand):
    """Dialog Semi-Global Strings operand"""
    pass


@dataclass
class FindBestActionOperand(VMPrimitiveOperand):
    """Find Best Action operand"""
    pass


@dataclass
class FindBestObjectForFunctionOperand(VMPrimitiveOperand):
    """Find Best Object For Function operand"""
    pass


@dataclass
class GenericTS1CallOperand(VMPrimitiveOperand):
    """Generic TS1 Call operand"""
    call: int


@dataclass
class GenericTSOCallOperand(VMPrimitiveOperand):
    """Generic TSO Call operand"""
    call: int


@dataclass
class GetTerrainInfoOperand(VMPrimitiveOperand):
    """Get Terrain Info operand"""
    mode: int
    unknown1: int
    flags: int
    unknown: bytes


@dataclass
class GosubFoundActionOperand(VMPrimitiveOperand):
    """Gosub Found Action operand"""
    pass


@dataclass
class GrabOperand(VMPrimitiveOperand):
    """Grab operand"""
    pass


@dataclass
class NotifyOutOfIdleOperand(VMPrimitiveOperand):
    """Notify Out Of Idle operand"""
    pass


@dataclass
class OnlineJobsCallOperand(VMPrimitiveOperand):
    """Online Jobs Call operand"""
    call: int


@dataclass
class ReachOperand(VMPrimitiveOperand):
    """Reach operand"""
    mode: int
    grab_or_drop: int
    slot_param: int


@dataclass
class SysLogOperand(VMPrimitiveOperand):
    """Sys Log operand"""
    pass


@dataclass
class TestSimInteractingWithOperand(VMPrimitiveOperand):
    """Test Sim Interacting With operand"""
    pass


@dataclass
class TransferFundsOperand(VMPrimitiveOperand):
    """Transfer Funds operand"""
    old_amount_owner: int
    amount_owner: VMVariableScope
    amount_data: int
    flags: int
    expense_type: int
    transfer_type: int


@dataclass
class TS1BudgetOperand(VMPrimitiveOperand):
    """TS1 Budget operand"""
    old_amount_owner: int
    amount_owner: VMVariableScope
    amount_data: int
    flags: int
    expense_type: int
    transfer_type: int