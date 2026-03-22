# Engine Primitives (Opcodes 0-255)

## Overview

Primitives are hardcoded engine functions in The Sims. They are NOT stored in IFF files - they are implemented in the game executable itself. When a BHAV instruction has an opcode < 256, it's a primitive call.

## Opcode Architecture

```
0-255:    Engine Primitives (hardcoded)
256-4095: Global Subroutine Calls (IFF files)
4096-8191: Local/Private Subroutine Calls
8192+:    Semi-Global Subroutine Calls
```

## Most Used Primitives (from 11.4GB game scan)

| Opcode | Hex  | Name (FreeSO)            | Usage Count | Notes                     |
| ------ | ---- | ------------------------ | ----------- | ------------------------- |
| 0      | 0x00 | sleep                    | 201,587     | Wait for ticks            |
| 7      | 0x07 | refresh                  | 60,212      | Update object state       |
| 10     | 0x0A | (unknown)                | 5,024       |                           |
| 2      | 0x02 | expression               | 3,559       | Math/comparison ops       |
| 1      | 0x01 | generic_sims_call        | 2,602       | TS1-specific system calls |
| 3      | 0x03 | find_best_interaction    | 1,968       | TS1-specific              |
| 6      | 0x06 | change_suit_or_accessory | 546         | Outfit changes            |
| 100    | 0x64 | (unknown)                | 461         |                           |
| 25     | 0x19 | budget/transfer_funds    | 416         | Money operations          |
| 26     | 0x1A | relationship             | 345         | Social relationship ops   |
| 4      | 0x04 | grab                     | 291         | Pick up object            |
| 5      | 0x05 | drop                     | 235         | Drop object               |
| 8      | 0x08 | random_number            | 221         | RNG                       |
| 11     | 0x0B | get_distance_to          | 99          | Spatial calculation       |
| 129    | 0x81 | (unknown)                | 58          |                           |
| 9      | 0x09 | burn                     | 51          | Fire damage               |

## Complete Primitive List (from FreeSO VMContext.cs)

### Core Primitives (Both TS1 and TSO)

| ID  | Name                          | Description                        |
| --- | ----------------------------- | ---------------------------------- |
| 0   | sleep                         | Pause execution for ticks          |
| 2   | expression                    | Mathematical/comparison operations |
| 4   | grab                          | Pick up an object                  |
| 5   | drop                          | Put down held object               |
| 6   | change_suit_or_accessory      | Change avatar clothing             |
| 7   | refresh                       | Update object visuals              |
| 8   | random_number                 | Generate random value              |
| 9   | burn                          | Apply fire damage                  |
| 11  | get_distance_to               | Calculate distance between objects |
| 12  | get_direction_to              | Get direction to target            |
| 13  | push_interaction              | Add action to queue                |
| 14  | find_best_object_for_function | Object search                      |
| 15  | breakpoint                    | Debug pause                        |
| 16  | find_location_for             | Spatial search                     |
| 17  | idle_for_input                | Wait for player action             |
| 18  | remove_object_instance        | Delete object                      |
| 20  | run_functional_tree           | Execute behavior tree              |
| 21  | show_string                   | Display text                       |
| 22  | look_towards                  | Rotate avatar                      |
| 23  | play_sound                    | Audio playback                     |
| 24  | old_relationship              | Legacy social ops                  |
| 26  | relationship                  | Social relationship operations     |
| 27  | goto_relative                 | Move to relative position          |
| 28  | run_tree_by_name              | Execute named behavior             |
| 29  | set_motive_deltas             | Modify needs                       |
| 31  | set_to_next                   | Iterator/loop                      |
| 32  | test_object_type              | Type checking                      |
| 35  | special_effect                | Visual effects                     |
| 36  | dialog_private                | Private string dialog              |
| 37  | test_sim_interacting_with     | Interaction check                  |
| 38  | dialog_global                 | Global string dialog               |
| 39  | dialog_semiglobal             | Semi-global dialog                 |
| 40  | online_jobs_call              | Job system (TSO)                   |
| 41  | set_balloon_headline          | Speech bubbles                     |
| 42  | create_object_instance        | Spawn object                       |
| 43  | drop_onto                     | Place object on surface            |
| 44  | animate                       | Play animation                     |
| 45  | goto_routing_slot             | Navigate to slot                   |
| 46  | snap                          | Snap to position                   |
| 47  | reach                         | Arm reaching animation             |
| 48  | stop_all_sounds               | Audio stop                         |
| 49  | stackobj_notify_out_of_idle   | Wake sleeping behavior             |
| 50  | change_action_string          | Modify action label                |
| 62  | invoke_plugin                 | Plugin system                      |
| 63  | get_terrain_info              | Terrain queries                    |
| 65  | find_best_action              | Autonomy system                    |
| 67  | inventory_operations          | Inventory management               |

### TS1-Specific Primitives

| ID  | Name                  | Description        |
| --- | --------------------- | ------------------ |
| 1   | generic_sims_call     | TS1 system calls   |
| 3   | find_best_interaction | Interaction finder |
| 19  | make_new_character    | Create new Sim     |
| 25  | budget                | Money operations   |
| 30  | gosub_found_action    | Action execution   |
| 51  | manage_inventory      | TS1 inventory      |

### TSO-Specific Primitives

| ID  | Name                     | Description      |
| --- | ------------------------ | ---------------- |
| 1   | generic_sims_online_call | TSO system calls |
| 25  | transfer_funds           | Money transfer   |

## Statistics

- **Total unique primitives used**: 65
- **Total primitive instructions**: 278,009
- **Most common**: sleep (72.5% of all primitives)

## Relationship to Ghost Globals

The boundary at 256 is absolute:

- Opcodes 0-255: Always engine primitives
- Opcodes 256+: Always subroutine calls

This boundary is enforced in VMThread.ExecuteInstruction():

```csharp
if (opcode >= 256)
{
    ExecuteSubRoutine(frame, opcode, ...);
    return;
}

var primitive = VMContext.Primitives[opcode];
```

The ghost globals (missing globals in 512-2815 range) are definitively NOT primitives - they must be engine-internal global subroutines that are handled before IFF file lookup.
