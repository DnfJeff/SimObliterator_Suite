# SimAntics Primitive Reference

This document details the operand formats for commonly used SimAntics primitives (opcodes). Each primitive has an 8-byte operand that encodes its parameters.

---

## Primitive Categories

| Range     | Category               |
| --------- | ---------------------- |
| 0x00-0x0F | Core Control           |
| 0x10-0x1F | Object Operations      |
| 0x20-0x2F | Sim Control            |
| 0x30-0x3F | Motive/Need Operations |
| 0x40+     | Extended/Custom        |

---

## 0x00 - Sleep

Pauses execution for a specified number of ticks.

### Operand Format

```
[0-1]: Ticks (uint16, little-endian)
[2-7]: Unused
```

### Behavior

- Blocking primitive - yields to simulation
- 30 ticks = approximately 1 second at normal speed
- Returns true when sleep completes

---

## 0x01 - Animate

Plays an animation on the stack object or current sim.

### Operand Format

```
[0-1]: Animation ID (uint16)
[2]:   Flags
         Bit 0: Loop
         Bit 1: Reverse
         Bit 2: Reset to frame 0
[3-7]: Unused
```

### Behavior

- Blocking until animation completes
- Stack Object determines target

---

## 0x02 - Expression

The most versatile primitive - performs math and comparisons.

### Operand Format

```
[0-1]: LHS Data (uint16) - variable index or literal
[2-3]: RHS Data (uint16) - variable index or literal
[4]:   Flags
         Bit 0: 0=Assignment, 1=Comparison
[5]:   Operator
[6]:   LHS Scope (see Variable Scopes)
[7]:   RHS Scope (see Variable Scopes)
```

### Assignment Operators (Flag bit 0 = 0)

| Code | Operator | Meaning     |
| ---- | -------- | ----------- |
| 0    | :=       | Assign      |
| 1    | +=       | Add         |
| 2    | -=       | Subtract    |
| 3    | \*=      | Multiply    |
| 4    | /=       | Divide      |
| 5    | %=       | Modulo      |
| 6    | &=       | Bitwise AND |
| 7    | \|=      | Bitwise OR  |
| 8    | ^=       | Bitwise XOR |
| 9    | >>=      | Shift Right |
| 10   | <<=      | Shift Left  |

### Comparison Operators (Flag bit 0 = 1)

| Code | Operator | Meaning          |
| ---- | -------- | ---------------- |
| 0    | <        | Less than        |
| 1    | <=       | Less or equal    |
| 2    | ==       | Equal            |
| 3    | >=       | Greater or equal |
| 4    | >        | Greater than     |
| 5    | !=       | Not equal        |

### Variable Scopes

| Code | Scope                   | Writable | Description                   |
| ---- | ----------------------- | -------- | ----------------------------- |
| 0    | My                      | Yes      | Object's attributes           |
| 1    | Stack Object's          | Yes      | Target's attributes           |
| 2    | My (Person)             | Yes      | Sim's person data             |
| 3    | Stack Object's (Person) | Yes      | Target sim's person data      |
| 4    | Global                  | Yes      | Global simulation variables   |
| 5    | Literal                 | No       | Constant value (data = value) |
| 6    | Local                   | Yes      | BHAV local variable           |
| 7    | Temp                    | Yes      | Temporary variable            |
| 8    | Parameter               | Yes      | Function parameter            |
| 9    | BCON                    | No       | Named constant                |
| 10   | Attribute Array         | Yes      | Indexed attribute             |
| 11   | Temps Array             | Yes      | Indexed temp                  |

### Examples

```
temp:0 := literal:5     -> Set temp 0 to 5
local:1 += param:0      -> Add parameter 0 to local 1
temp:0 == literal:10    -> Compare temp 0 to 10 (returns T/F)
```

---

## 0x04 - Gosub

Calls another BHAV and returns.

### Operand Format

```
[0-1]: BHAV ID (uint16)
[2]:   Parameter 0
[3]:   Parameter 1
[4]:   Parameter 2
[5]:   Parameter 3
[6-7]: Unused
```

### BHAV ID Ranges

| Range      | Scope                      |
| ---------- | -------------------------- |
| 256-4095   | Global (Behavior.iff)      |
| 4096-8191  | Local (object's IFF)       |
| 8192-12287 | Semi-global (shared group) |

### Behavior

- Pushes return address to call stack
- Called BHAV's return value becomes this primitive's return
- Parameters accessible via scope 8 in callee

---

## 0x05 - Goto

Unconditionally jumps to another instruction.

### Operand Format

```
[0]: Target instruction index
[1-7]: Unused
```

### Behavior

- Always jumps (ignores true/false branch)
- Used for loop constructs

---

## 0x09 - End Tree / Return

Ends current tree execution with a result.

### Operand Format

```
[0]: Return value
       0 = False
       1 = True
[1-7]: Unused
```

---

## 0x0C - Create Object Instance

Creates a new object in the world.

### Operand Format

```
[0-3]: GUID of object to create (uint32)
[4]:   Placement mode
         0 = At position
         1 = In hand
         2 = On stack object
[5-7]: Unused
```

### Behavior

- Created object becomes new Stack Object
- Returns false if creation fails

---

## 0x14 - Walk to Slot

Routes sim to a slot on the target object.

### Operand Format

```
[0]: Slot index
[1]: Flags
       Bit 0: Allow partial routing
       Bit 1: Push interactions
[2-7]: Unused
```

### Behavior

- Blocking until routing completes
- Returns false if routing fails

---

## 0x22 - Change Suit / Access

Changes a sim's outfit or accessory.

### Operand Format

```
[0]: Suit source
       0 = Body Strings (STR# chunk)
       1 = Literal value
       2 = From temp variable
[1-2]: Suit index (uint16)
[3-7]: Unused
```

---

## Primitive Return Values

All primitives return one of:

| Value | Constant      | Meaning                   |
| ----- | ------------- | ------------------------- |
| 0-252 | (instruction) | Jump to that instruction  |
| 253   | Error         | Error condition           |
| 254   | True          | Success/condition met     |
| 255   | False         | Failure/condition not met |

---

## Debugging Tips

1. **Expression Debugging**: Check scope codes - scope 5 (literal) uses data as the actual value
2. **Gosub Tracing**: Note the BHAV ID ranges to understand call targets
3. **Variable Flow**: Local (6) and Temp (7) are most commonly debugged
4. **Return Values**: Primitives that return to instruction 253+ are terminal

---

_Reference based on analysis of Behavior.iff and game object files._
