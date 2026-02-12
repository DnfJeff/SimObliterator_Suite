# BHAV Instruction Opcode Reference

**Extracted from FreeSO source code**

Complete semantic reference for BHAV (behavior) bytecode instructions.

## Quick Reference by Category

- **Control**: ChangeActionString, FindBestObjectForFunction, GenericTSOCall, IdleForInput, NotifyOutOfIdle, PushInteraction, RunFunctionalTree, RunTreeByName, Sleep
- **Debug**: Breakpoint
- **Looks**: Dialog, PlaySoundEvent, Refresh, SetBalloonHeadline
- **Looks/Debug**: ShowString
- **Math**: RandomNumber
- **Math/Control**: Expression
- **Math/Position**: GetDirectionTo, GetDistanceTo
- **Object**: CreateObjectInstance, RemoveObjectInstance, SetToNext, TS1InventoryOperations, TestObjectType
- **Position**: Drop, FindLocationFor, GotoRelativePosition, GotoRoutingSlot, Grab, Snap
- **Sim**: AnimateSim, ChangeSuit, LookTowards, Relationship, SetMotiveChange, TransferFunds
- **TSO**: InvokePlugin, TSOInventoryOperations
- **Unknown**: DialogChoice, DialogString, DropOnto, OldRelationship

## Instructions by Opcode

### 0: Sleep

**Category:** Control

**Description:** Pause execution for specified duration (ticks)

**Stack Effect:** Pops duration from stack

**Operand:** Sleep duration in 1/30ths of a second

**Exit Code:** CONTINUE

---

### 1: GenericTSOCall

**Category:** Control

**Description:** Call a primitive/subroutine based on operand

**Stack Effect:** Varies by called primitive

**Operand:** Primitive to call (can be subroutine ID 0x0100+)

**Exit Code:** CONTINUE, GOTO_TRUE, GOTO_FALSE, or ERROR

---

### 2: Expression

**Category:** Math/Control

**Description:** Evaluate mathematical/logical expression and branch

**Stack Effect:** Pushes result (0 or 1)

**Operand:** LHS operand, RHS operand, operator, scopes

**Exit Code:** GOTO_TRUE or GOTO_FALSE based on result

---

### 4: Grab

**Category:** Position

**Description:** Pick up object from world

**Stack Effect:** Requires object ID on stack

**Operand:** Animation type

**Exit Code:** CONTINUE or ERROR

---

### 5: Drop

**Category:** Position

**Description:** Put down held object

**Stack Effect:** No effect on stack

**Operand:** Unknown

**Exit Code:** CONTINUE or ERROR

---

### 6: ChangeSuit

**Category:** Sim

**Description:** Change sim's outfit/accessories

**Stack Effect:** Pops outfit index

**Operand:** Outfit type

**Exit Code:** CONTINUE or ERROR

---

### 7: Refresh

**Category:** Looks

**Description:** Redraw object graphics

**Stack Effect:** No effect

**Operand:** None

**Exit Code:** CONTINUE

---

### 8: RandomNumber

**Category:** Math

**Description:** Generate random number and push to stack

**Stack Effect:** Pushes random value 0 to max

**Operand:** Max value (exclusive)

**Exit Code:** CONTINUE

---

### 11: GetDistanceTo

**Category:** Math/Position

**Description:** Calculate distance to another object

**Stack Effect:** Pops target object ID, pushes distance

**Operand:** None

**Exit Code:** CONTINUE or ERROR

---

### 12: GetDirectionTo

**Category:** Math/Position

**Description:** Get direction (angle) to another object

**Stack Effect:** Pops target object ID, pushes direction

**Operand:** None

**Exit Code:** CONTINUE or ERROR

---

### 13: PushInteraction

**Category:** Control

**Description:** Queue an interaction on sim's action queue

**Stack Effect:** Complex operand stack usage

**Operand:** Interaction definition

**Exit Code:** CONTINUE or ERROR

---

### 14: FindBestObjectForFunction

**Category:** Control

**Description:** Search lot for best object with given function

**Stack Effect:** Pushes best matching object ID

**Operand:** Function/TTAB to search for

**Exit Code:** CONTINUE or GOTO_FALSE (not found)

---

### 15: Breakpoint

**Category:** Debug

**Description:** Debugging breakpoint (pause execution)

**Stack Effect:** No effect

**Operand:** Debug message or ID

**Exit Code:** CONTINUE

---

### 16: FindLocationFor

**Category:** Position

**Description:** Find suitable position for sim

**Stack Effect:** Pushes X, Y coordinates

**Operand:** Search parameters

**Exit Code:** CONTINUE or GOTO_FALSE (none found)

---

### 17: IdleForInput

**Category:** Control

**Description:** Wait for user interaction

**Stack Effect:** May push user input data

**Operand:** Idle behavior ID or function

**Exit Code:** Varies based on input

---

### 18: RemoveObjectInstance

**Category:** Object

**Description:** Delete object from world

**Stack Effect:** Pops object ID

**Operand:** Cleanup BHAV (optional)

**Exit Code:** CONTINUE or ERROR

---

### 20: RunFunctionalTree

**Category:** Control

**Description:** Execute a functional tree (interaction decision tree)

**Stack Effect:** Complex interaction parameters

**Operand:** TTAB (interaction table) ID

**Exit Code:** CONTINUE, GOTO_TRUE, GOTO_FALSE

---

### 21: ShowString

**Category:** Looks/Debug

**Description:** Display text bubble over object/sim

**Stack Effect:** Pops string data

**Operand:** String resource ID

**Exit Code:** CONTINUE

---

### 22: LookTowards

**Category:** Sim

**Description:** Face towards location or object

**Stack Effect:** May pop target position

**Operand:** Look duration, animation

**Exit Code:** CONTINUE

---

### 23: PlaySoundEvent

**Category:** Looks

**Description:** Play audio sound effect

**Stack Effect:** Pops sound ID or frequency

**Operand:** Sound parameters

**Exit Code:** CONTINUE

---

### 24: OldRelationship

**Category:** Unknown

**Description:** Not yet documented

**Stack Effect:** 

**Operand:** 

**Exit Code:** 

---

### 25: TransferFunds

**Category:** Sim

**Description:** Move money between objects

**Stack Effect:** Pops source, target, amount

**Operand:** None

**Exit Code:** CONTINUE or ERROR

---

### 26: Relationship

**Category:** Sim

**Description:** Modify relationship between sims

**Stack Effect:** Pops sim IDs and relationship value

**Operand:** Relationship operation (add, set, etc.)

**Exit Code:** CONTINUE or ERROR

---

### 27: GotoRelativePosition

**Category:** Position

**Description:** Walk to relative position

**Stack Effect:** Pops X, Y, Z offsets

**Operand:** Animation/routing parameters

**Exit Code:** CONTINUE or ERROR

---

### 28: RunTreeByName

**Category:** Control

**Description:** Execute interaction by name string

**Stack Effect:** Complex interaction parameters

**Operand:** Interaction name string ID

**Exit Code:** CONTINUE, GOTO_TRUE, GOTO_FALSE

---

### 29: SetMotiveChange

**Category:** Sim

**Description:** Set how sim's motives change over time

**Stack Effect:** Pops motive index and rate

**Operand:** Motive parameters

**Exit Code:** CONTINUE

---

### 31: SetToNext

**Category:** Object

**Description:** Advance to next animation frame/state

**Stack Effect:** No effect

**Operand:** None

**Exit Code:** CONTINUE or END if last frame

---

### 32: TestObjectType

**Category:** Object

**Description:** Check if object matches type

**Stack Effect:** Pops object ID

**Operand:** Object type to test

**Exit Code:** GOTO_TRUE or GOTO_FALSE

---

### 36: Dialog

**Category:** Looks

**Description:** Show dialog with global string

**Stack Effect:** Pops string ID

**Operand:** Dialog options

**Exit Code:** CONTINUE

---

### 38: DialogString

**Category:** Unknown

**Description:** Not yet documented

**Stack Effect:** 

**Operand:** 

**Exit Code:** 

---

### 39: DialogChoice

**Category:** Unknown

**Description:** Not yet documented

**Stack Effect:** 

**Operand:** 

**Exit Code:** 

---

### 41: SetBalloonHeadline

**Category:** Looks

**Description:** Set speech balloon text above sim

**Stack Effect:** Pops string ID

**Operand:** Balloon icon/type

**Exit Code:** CONTINUE

---

### 42: CreateObjectInstance

**Category:** Object

**Description:** Create new object on lot

**Stack Effect:** Pushes new object ID

**Operand:** GUID of object to create

**Exit Code:** CONTINUE or ERROR

---

### 43: DropOnto

**Category:** Unknown

**Description:** Not yet documented

**Stack Effect:** 

**Operand:** 

**Exit Code:** 

---

### 44: AnimateSim

**Category:** Sim

**Description:** Play animation on sim

**Stack Effect:** May pop animation ID

**Operand:** Animation event ID

**Exit Code:** CONTINUE

---

### 45: GotoRoutingSlot

**Category:** Position

**Description:** Walk to predefined routing slot

**Stack Effect:** May pop slot data

**Operand:** SLOT index

**Exit Code:** CONTINUE or ERROR

---

### 46: Snap

**Category:** Position

**Description:** Instantly teleport to location

**Stack Effect:** Pops X, Y, Z, rotation

**Operand:** None

**Exit Code:** CONTINUE

---

### 49: NotifyOutOfIdle

**Category:** Control

**Description:** Signal that object left idle state

**Stack Effect:** No effect

**Operand:** None

**Exit Code:** CONTINUE

---

### 50: ChangeActionString

**Category:** Control

**Description:** Update action queue string display

**Stack Effect:** Pops string ID

**Operand:** String resource

**Exit Code:** CONTINUE

---

### 51: TS1InventoryOperations

**Category:** Object

**Description:** Handle TS1-specific inventory

**Stack Effect:** Complex inventory operations

**Operand:** Operation type

**Exit Code:** CONTINUE or ERROR

---

### 62: InvokePlugin

**Category:** TSO

**Description:** Call plugin/extension

**Stack Effect:** Plugin-dependent

**Operand:** Plugin identifier

**Exit Code:** Plugin-defined

---

### 67: TSOInventoryOperations

**Category:** TSO

**Description:** Handle TSO-specific inventory operations

**Stack Effect:** Complex inventory operations

**Operand:** Operation type

**Exit Code:** CONTINUE or ERROR

---

## Special Control Flow Opcodes

These are pseudo-opcodes that represent special behavior:

### 0xff00: CALL_BEHAVIOR

**Description:** Call sub-behavior by BHAV ID

**Stack Effect:** Complex parameter passing

**Exit Code:** CONTINUE, GOTO_TRUE, GOTO_FALSE, ERROR, or RETURN

---

### 0xff01: RETURN

**Description:** Return from current BHAV

**Stack Effect:** Clears call stack frame

**Exit Code:** RETURN

---

### 0xffff: JUMP

**Description:** Unconditional jump to instruction

**Stack Effect:** No effect

**Exit Code:** CONTINUE (at new location)

---

