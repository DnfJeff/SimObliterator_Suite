"""
FreeSO BEHAVIORAL ARCHITECTURE ANALYSIS
Reverse Engineering the SimAntics Execution Engine for Behavior Injection

Analysis Date: February 2, 2026
Purpose: Understanding where autonomous behavior systems can be inserted

============================================================================
EXECUTIVE SUMMARY
============================================================================

FreeSO's behavior system is built on a hierarchical execution model:

1. VM (global) → VMContext (world) → VMEntity (Sim) → VMThread (execution)
2. Execution happens via Tick() which steps instructions in a cooperative loop
3. Autonomy decisions are made by VMFindBestAction primitive (motive scoring)
4. Behaviors are queued with priorities and executed FIFO
5. Long-running behaviors yield via CONTINUE_NEXT_TICK / CONTINUE_FUTURE_TICK

CRITICAL INSIGHT: The system is designed for behavior layering - a new system
can coexist by:

- Injecting into ExecuteEntryPoint(1) for Main behavior
- Queueing actions with RunImmediately flag
- Setting PersonData state flags to track "zombie mode"
- Yielding back to scheduler between steps

============================================================================
QUESTION 1: BHAV EXECUTION LIFECYCLE
============================================================================

📍 ENTRY POINT: VMEntity.ExecuteEntryPoint()
File: TSOClient/tso.simantics/Entities/VMEntity.cs
Line: 623
Signature: bool ExecuteEntryPoint(int entry, VMContext context, bool runImmediately, VMEntity stackOBJ, short[] args)

Entry point 0: Init
Entry point 1: Main (autonomy entry - THIS IS CRITICAL)
Entry point 2: Cleanup
Entry point 4: Die
Entry point 11: User placement (architecture)

📍 EXECUTION OWNER: VMThread class
File: TSOClient/tso.simantics/Engine/VMThread.cs
Lines: 20-200

Key fields:

- Stack: List<VMStackFrame> - execution stack (can be nested)
- InstructionPointer: current position in BHAV
- Locals/Args: variable storage
- ContinueExecution: boolean controlling Tick() loop
- BlockingState: async state (animation, routing, etc)

📍 EXECUTION LOOP: VMThread.Tick()
File: TSOClient/tso.simantics/Engine/VMThread.cs
Lines: 288-350

Called by: VM.Update() or VM.DebugTick()
Frequency: Once per frame (every ~33ms for 30 FPS)

Loop structure:

```
public void Tick() {
    if (BlockingState != null) BlockingState.WaitTime++;
    if (!Entity.Dead) {
        if (Stack.Count == 0) Entity.ExecuteEntryPoint(1); // Main entry
        ContinueExecution = true;
        while (ContinueExecution) {
            if (TicksThisFrame++ > MAX_LOOP_COUNT) throw Infinite Loop;
            ContinueExecution = false;
            NextInstruction();  // Execute one instruction
        }
    }
}
```

Key insight: ContinueExecution controls whether we step again in THIS frame.
If a primitive returns CONTINUE_NEXT_TICK, we exit and resume next frame.

📍 INSTRUCTION STEPPING: VMThread.NextInstruction()
File: TSOClient/tso.simantics/Engine/VMThread.cs
Lines: 447-470

Flow:

1.  Get current instruction from frame
2.  Call ExecuteInstruction(frame)
3.  ExecuteInstruction dispatches to primitive handler
4.  Handler returns VMPrimitiveExitCode
5.  HandleResult() processes the result (branch/continue/return)

📍 INSTRUCTION EXECUTION: VMThread.ExecuteInstruction()
File: TSOClient/tso.simantics/Engine/VMThread.cs
Lines: 561-584

```
private void ExecuteInstruction(VMStackFrame frame) {
    var instruction = frame.GetCurrentInstruction();
    var opcode = instruction.Opcode;

    if (opcode >= 256) {
        ExecuteSubRoutine(frame, opcode, ...);  // BHAV call
        return;
    }

    var primitive = VMContext.Primitives[opcode];
    if (primitive == null) return;

    VMPrimitiveHandler handler = primitive.GetHandler();
    var result = handler.Execute(frame, instruction.Operand);
    HandleResult(frame, instruction, result);
}
```

Opcode ranges:

- 0-255: Built-in primitives
- 256+: BHAV subroutine calls (encoded as opcode)

📍 BRANCHING & RETURNS: VMThread.HandleResult()
File: TSOClient/tso.simantics/Engine/VMThread.cs
Lines: 585-660

Exit codes:

- GOTO_TRUE: branch to instruction.TruePointer
- GOTO_FALSE: branch to instruction.FalsePointer
- CONTINUE: proceed to next instruction (IP+1)
- CONTINUE_NEXT_TICK: yield, resume this frame next tick
- CONTINUE_FUTURE_TICK: yield, don't resume until scheduled
- RETURN_TRUE/FALSE: pop stack frame, return to caller
- ERROR: pop stack, execute false pointer

Special pointers:

- 254: RETURN_TRUE
- 255: RETURN_FALSE
- 253: Continue along available path

📍 STACK FRAMES: VMStackFrame class
File: TSOClient/tso.simantics/Engine/VMStackFrame.cs
Lines: 18-120

Represents one BHAV execution:

- Routine: which BHAV is running
- InstructionPointer: current instruction
- Locals: short[] - local variables
- Args: short[] - arguments
- StackObject: VMEntity - current interaction target
- Caller/Callee: who initiated this BHAV
- CodeOwner: where strings/resources come from
- ActionTree: flag for interaction vs autonomy

ANSWER TO QUESTION 1:
"BHAVs execute in VMThread via ExecuteInstruction(), which is called from
NextInstruction() inside the Tick() loop, stepping one instruction per call,
and handling branches/returns via HandleResult()."

============================================================================
QUESTION 2: SCHEDULING & EXECUTION FREQUENCY
============================================================================

📍 SCHEDULER: VMScheduler class
File: TSOClient/tso.simantics/Engine/VMScheduler.cs
Lines: 1-100

Purpose: Tracks which entities need execution and when
Key methods:

- ScheduleTickIn(entity, ticks) - defer execution N ticks
- GetScheduledEntities() - which entities run this frame
- Update(deltaTime) - advance time

📍 EXECUTION FREQUENCY
Location: VM.Update() in VM.cs
Line: ~800

Called: Once per frame (render loop)
Frequency: 30 FPS typically (~33ms per frame)

Pattern:

```
VM.Update(deltaTime) {
    Scheduler.Update(deltaTime);
    foreach (var entity in Scheduler.GetScheduledEntities()) {
        entity.Thread.Tick();
    }
}
```

So EACH ENTITY gets ONE Tick() per frame if scheduled.

📍 EXECUTION MODEL: Cooperative Time-Slicing
Model type: COOPERATIVE (not preemptive)

A BHAV executes instructions until:

1.  Primitive returns CONTINUE_NEXT_TICK
2.  Primitive returns CONTINUE_FUTURE_TICK
3.  Stack is empty (behavior completes)
4.  MAX_LOOP_COUNT exceeded (infinite loop safety)

Then the next entity runs, or frame ends.

Max loops per frame: 500,000 primitives
Location: VMThread.cs line 306
Field: public static readonly int MAX_LOOP_COUNT = 500000;

📍 YIELDING MECHANISMS
Primitive returns CONTINUE_NEXT_TICK:

- Animation playing
- Sound effect playing
- Routing in progress
- Dialog response waiting

Example: VMIdleForInput.cs

```
if (context.Args[operand.StackVarToDec] < 0) {
    return VMPrimitiveExitCode.CONTINUE_NEXT_TICK;
}
```

This means: "Come back next tick and check again"

📍 ASYNC BLOCKING STATE
Field: VMThread.BlockingState
File: VMThread.cs line: 59
Type: VMAsyncState (abstract for animation/routing/etc)

When blocking:

- BHAV doesn't execute (Stack.Count == 0)
- BlockingState.WaitTime increments each tick
- When complete, PopAsyncState() resumes stack

📍 STEP TIME
Single instruction execution: microseconds
Full behavior: depends on yield points

Example BHAV (6 instructions):

- No yields: 6 instructions per tick = 0.2ms
- With animation yield: 6 instructions spread across N frames

Can be configured:

- TS1 speed: state.Speed = 30 / 25f;
- Location: VMAnimateSim.cs

ANSWER TO QUESTION 2:
"Behaviors execute at 30 FPS with cooperative time-slicing. Each Tick() runs
instructions until a primitive yields (CONTINUE_NEXT_TICK) or stack empties.
Single steps are microseconds; full behaviors spread across frames via yields."

============================================================================
QUESTION 3: AUTONOMY & DECISION-MAKING LAYER
============================================================================

📍 AUTONOMY DECISION POINT
Primitive: VMFindBestAction
File: TSOClient/tso.simantics/Primitives/VMFindBestAction.cs
Lines: 91-310 (see full code in artifact)
Opcode: 0x006D (109 decimal)

📍 DECISION ALGORITHM

1.  Iterate all objects with TreeTable (interactions)
2.  For each object, iterate AutoInteractions (TTABs)
3.  Evaluate guard BHAV: caller.Thread.CheckAction()
4.  Score interaction:
    - Base happiness (motive curves)
    - Motive advertisements (what this interaction helps)
    - Distance attenuation (closer = higher score)
    - Personality modifiers (outgoing, playful, etc)
5.  Rank by score
6.  Select top action (or random from top 4)
7.  Enqueue with priority

📍 MOTIVE SCORING
Base score calculation:

```
score = happiness (sum of motive curves)
        - advertisements (what motives this helps)
        * personality modifiers
        / (1 + attenuation * distance)
```

WeightMotives array:

- Energy, Hunger, Bladder, Hygiene, etc (9 motives)
- Each has weight in happiness calculation

Location: VMFindBestAction.cs line 150-200

📍 GUARD EVALUATION (Check Trees)
Call: caller.Thread.CheckAction(action, true)
File: VMThread.cs line 133

Runs action's guard BHAV in SYNCHRONOUS CHECK MODE:

- Doesn't modify state
- Returns immediately (no yields)
- Determines if interaction is valid

Returns: List<VMPieMenuInteraction> if valid, else null

📍 PRIORITY-BASED QUEUEING
Method: EnqueueAction(VMQueuedAction)
File: VMThread.cs lines 756-810

Rules:

- High priority bumps ahead in queue
- RunImmediately flag: execute before current action ends
- FSOPushHead: insert at front
- Normal: queue at end, sorted by priority

Queue state:

- Queue: List<VMQueuedAction> - queued interactions
- ActiveQueueBlock: protects active/parent interactions
- QueueDirty: flag to re-evaluate priorities

ANSWER TO QUESTION 3:
"Autonomy decisions happen in VMFindBestAction.Execute(), which scores all
available interactions using motive curves, distance, and personality modifiers,
then enqueues the best-scored action via EnqueueAction() with priority-based
insertion into the Queue."

============================================================================
QUESTION 4: ENTRY POINTS & INJECTION SEAMS
============================================================================

SEAM #1: ExecuteEntryPoint() - Behavior Invocation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Location: VMEntity.cs line 623
Signature: bool ExecuteEntryPoint(int entry, VMContext context, bool runImmediately, VMEntity stackOBJ, short[] args)

What normally happens:

- Finds entry point BHAV ID from object descriptor
- Creates new stack frame with args
- Pushes onto execution stack
- Next Tick() will execute this BHAV

What could be intercepted:

- BEFORE: Check entity state, substitute alternate BHAV ID
- AFTER: Post-process return value, trigger side effects
- ENTRY POINT 1 (Main): Perfect place for state machine override

Concrete example:

```
// In ZombieController:
public void ZombieMainBehavior(VMAvatar zombie) {
    int zombieState = zombie.GetPersonData(PersonDataVariable.CreatureState);
    int mainBehaviorID = 0;

    switch (zombieState) {
        case ZOMBIE_IDLE: mainBehaviorID = 500;  // Idle BHAV
        case ZOMBIE_HUNTING: mainBehaviorID = 501;  // Chase BHAV
        case ZOMBIE_ATTACKING: mainBehaviorID = 502;  // Attack BHAV
    }

    ushort[] entryPoints = zombie.EntryPoints;
    entryPoints[1] = mainBehaviorID;  // Override Main entry point
    zombie.ExecuteEntryPoint(1, context, false);
}
```

SEAM #2: EnqueueAction() - Behavior Queueing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Location: VMThread.cs line 756
Signature: void EnqueueAction(VMQueuedAction invocation)

What normally happens:

- Action is inserted into Queue based on priority
- Next vacant action slot executes it
- Integration with queue manager

What could be intercepted:

- BEFORE: Check zombie mode, skip autonomy, force behavior
- PRIORITY: Set priority based on zombie hunger/rage
- FLAGS: Use RunImmediately for urgent actions

Concrete example:

```
// In ZombieController:
if (context.Caller.GetPersonData(PersonDataVariable.ZombieMode) > 0) {
    // Skip normal autonomy, force zombie behavior
    var zombieBehavior = CreateZombieBehavior(targetSim);
    zombieBehavior.Priority = VMQueuePriority.Urgent;
    zombieBehavior.Flags = TTABFlags.RunImmediately;
    context.Caller.Thread.EnqueueAction(zombieBehavior);
    return VMPrimitiveExitCode.CONTINUE;  // Skip normal action queue
}
```

SEAM #3: FindBestAction - Autonomy Scoring Override
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Location: VMFindBestAction.cs line 91 (Execute method)

What normally happens:

- Motive scoring for all available interactions
- Selection by score (or random from top 4)
- Enqueue selected action

What could be intercepted:

- BEFORE: Check zombie mode, return alternate action set
- SCORING: Modify scores for zombie (ignore motives, chase Sim)
- SELECTION: Replace scoring with zombie AI logic

Concrete example:

```
public override VMPrimitiveExitCode Execute(VMStackFrame context, VMPrimitiveOperand args) {
    var avatar = (VMAvatar)context.Caller;

    // SEAM: Zombie mode intercept
    if (avatar.GetPersonData(PersonDataVariable.ZombieMode) > 0) {
        var targets = FindNearbyLivingSims(avatar, 50);  // 50 tiles radius
        if (targets.Count > 0) {
            var target = targets[0];  // Pick closest
            var chaseAction = GetZombieChaseAction(target, context.VM);
            context.Caller.Thread.EnqueueAction(chaseAction);
            return VMPrimitiveExitCode.GOTO_TRUE;
        }
        return VMPrimitiveExitCode.GOTO_FALSE;
    }

    // ... normal autonomy logic continues
    return base.Execute(context, args);
}
```

SEAM #4: HandleResult() - Execution Result Processing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Location: VMThread.cs line 585
Signature: void HandleResult(VMStackFrame frame, VMInstruction instruction, VMPrimitiveExitCode result)

What normally happens:

- Branch decisions (true/false pointers)
- Stack pops (returns)
- Scheduler updates (yield schedules)

What could be intercepted:

- AFTER primitive completes: Check for side effects
- ON RETURN: Check state changes, trigger systems
- ON YIELD: Queue next behavior phase

SEAM #5: GetCurrentInstruction() - Instruction Fetching
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Location: VMStackFrame.cs line 100
Signature: VMInstruction GetCurrentInstruction()

What normally happens:

- Returns instruction at InstructionPointer
- Primitive handler executes it

What could be intercepted:

- BEFORE: Log execution for analysis
- BRANCH PREDICTION: Optimize common paths
- STATE CHECKING: Abort if mode changed

SEAM #6: NextInstruction() - Execution Loop Core
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Location: VMThread.cs line 447
Signature: void NextInstruction()

What normally happens:

- Fetch current instruction
- Execute it
- Process result
- Loop (if ContinueExecution)

What could be intercepted:

- BEFORE EACH STEP: Zombie state machine advance
- BETWEEN STEPS: Animation update
- STEP LIMIT: Custom max iterations for zombie AI

SUMMARY OF SEAMS
════════════════════════════════════════════════════════

1. ExecuteEntryPoint(1) - MAIN behavior entry
   ↓ Inject at: VMEntity.ExecuteEntryPoint()
   ↓ Strategy: Override entry point BHAV ID

2. EnqueueAction() - Behavior queueing
   ↓ Inject at: VMThread.EnqueueAction()
   ↓ Strategy: Force priority, skip autonomy

3. FindBestAction - Autonomy scoring
   ↓ Inject at: VMFindBestAction.Execute()
   ↓ Strategy: Replace scoring for zombie mode

4. HandleResult() - Result processing
   ↓ Inject at: VMThread.HandleResult()
   ↓ Strategy: Post-primitive side effects

5. GetCurrentInstruction() - Instruction fetching
   ↓ Inject at: VMStackFrame.GetCurrentInstruction()
   ↓ Strategy: Logging, state validation

6. NextInstruction() - Loop core
   ↓ Inject at: VMThread.NextInstruction()
   ↓ Strategy: Zombie state machine ticks

============================================================================
QUESTION 5: PERSISTENT SIM STATE
============================================================================

📍 ENTITY CLASS HIERARCHY
Base: VMEntity (all objects)
Extends: VMAvatar (Sims with behaviors)
File: VMEntity.cs, VMAvatar.cs

📍 PRIMARY STATE STORAGE: PersonData Array
Field: private short[] PersonData = new short[101]
File: VMAvatar.cs line 66
Type: 101 shorts (202 bytes)
Access: GetPersonData(VMPersonDataVariable), SetPersonData()

Key indices:

- [0]: Posture "3=stand, 1=sit, 2=kneel"
- [33]: Priority "interaction priority level"
- [34]: GreetStatus "greeting state"
- [36]: FreeWill "autonomy level"
- [58]: PersonAge "child/adult/elder"
- [63]: JobStatus
- [64]: Swimming
- [65]: Gender
- [71]: NonInterruptable "lock"
- [75]: InteractionTargetID
- [76]: ObjectBeingUsed
- [100]: PersonType "Sim/Pet/Visitor"

⭐ AVAILABLE SLOTS FOR ZOMBIE STATE:

- Indices 80-100 have various uses but some are free
- Can use unused slots or repurpose for zombie mode

📍 SECONDARY STATE: ObjectData Array
Field: public short[] ObjectData = new short[25]
File: VMEntity.cs line: 58

Stores:

- Stack object ID
- Placement flags
- Animation state
- Custom variables

Can add zombie-specific data here

📍 FLAGS: VMEntityFlags
File: VMEntity.cs
Type: enum with bit flags
Current flags:

- Dead
- Occupied
- UseAdjacentTiles
- InteractionCanceled
- NotifiedByIdleForInput
- etc

⭐ CAN ADD: Custom zombie flag to persist mode

📍 ATTRIBUTES & OBJECT DATA
Field: List<short> Attributes
Field: Dictionary<int, short> MeToObject
Field: Dictionary<int, short> MeToPersist

Stores relationships, cooking, etc.

📍 ANIMATIONS STATE
Field: List<VMAnimationState> Animations
Field: VMAnimationState CarryAnimationState

Current animation playing
Position in animation sequence

📍 MOTIVES (Sim drive system)
Method: GetMotiveData(VMMotive)
Method: SetMotiveData(VMMotive, short)

9 motives stored:

- Energy, Hunger, Bladder, Hygiene
- Comfort, Bladder, Full, Mood, Charisma

Decay per tick via MotiveDeltas
Modified by interactions

ARCHITECTURAL PATTERN FOR ZOMBIE STATE:
────────────────────────────────────────

Option 1: Use Free PersonData Slot

```
// Define custom variable
const int ZOMBIE_MODE_SLOT = 95;  // Free slot
const int ZOMBIE_TARGET_SLOT = 96;
const int ZOMBIE_STATE_SLOT = 97;

// Set mode
avatar.SetPersonData(ZOMBIE_MODE_SLOT, 1);  // 1 = zombie mode on

// Check mode in decision logic
int zombieMode = avatar.GetPersonData(ZOMBIE_MODE_SLOT);
if (zombieMode > 0) {
    // Execute zombie behavior
}
```

Option 2: Add Custom Field to VMAvatar

```
// In VMAvatar subclass
public short ZombieMode { get; set; }
public short ZombieTarget { get; set; }
public short ZombieState { get; set; }  // IDLE, HUNTING, ATTACKING
```

Option 3: Use ObjectData

```
const int ZOMBIE_MODE_FLAG = 20;  // Custom slot
avatar.ObjectData[ZOMBIE_MODE_FLAG] = 1;
```

ANSWER TO QUESTION 5:
"Persistent Sim state lives in VMAvatar.PersonData (101 shorts) accessed via
GetPersonData()/SetPersonData(), with free slots 80-100 for custom data. Flags
are in VMEntityFlags enum. Motives decay per tick and are modified by
interactions. Animation state stored in Animations list."

============================================================================
QUESTION 6: ANIMATION & BEHAVIOR COUPLING
============================================================================

📍 ANIMATION PRIMITIVE: VMAnimateSim
File: TSOClient/tso.simantics/Primitives/VMAnimateSim.cs
Opcode: 30
Signature: VMPrimitiveExitCode Execute(VMStackFrame context, VMPrimitiveOperand args)

📍 ANIMATION TRIGGERING
Location: VMAnimateSim.Execute() (see full code in artifact)

Steps:

1.  Get animation ID from operand (direct or from variable)
2.  Load animation asset from AvatarAnimations
3.  Create VMAnimationState object
4.  Set animation properties (speed, loop, direction)
5.  Add to avatar.Animations list
6.  Return GOTO_TRUE (immediate success)

Code:

```
animation = FSO.Content.Content.Get().AvatarAnimations.Get(id + ".anim");
var state = new VMAnimationState(animation, backwards);
state.Loop = true;  // or false for one-shot
avatar.Animations.Add(state);
return VMPrimitiveExitCode.GOTO_TRUE;
```

📍 EXECUTION DURING ANIMATION
Behavior: BHAV continues executing while animation plays

Model: NON-BLOCKING

- Animation plays in parallel
- BHAV doesn't yield
- Next instruction executes immediately
- Animation progresses frame-to-frame independently

Animation update loop:

- Part of VMAvatar.Update() (render tick)
- Independent of BHAV Tick()
- Frame advances animation state

📍 SUCCESS/FAILURE REPORTING
Mechanism: Animation completes flag
Location: VMAnimationState

How it works:

1.  Animation plays to completion
2.  IsCompleted flag sets to true
3.  BHAV can query this in next instruction
4.  Guard BHAV might check: IsAnimationComplete
5.  Branch based on completion

Example BHAV:

```
Instruction 0: PlayAnimation(waveID)
Instruction 1: IdleForInput(0)  // Wait one frame
Instruction 2: Branch(IsAnimationComplete, success, fail)
```

📍 CARRY ANIMATIONS (Objects in hands)
Field: VMAnimationState CarryAnimationState
Set by: VMAnimateSim with mode=3

Separate animation track for:

- Carrying plates
- Holding babies
- etc

📍 GESTURE SYSTEM
Avatar.LeftHandGesture, RightHandGesture
Set during animation
Example: Idle = 0, Wave = 1, Shrug = 2

Allows expression during animations

ANSWER TO QUESTION 6:
"Animations are triggered via VMAnimateSim primitive (opcode 30), which creates
VMAnimationState objects. BHAV execution does NOT block during animation - they
run in parallel. Success is reported via IsCompleted flag checked in subsequent
instructions or guard BHAVs."

============================================================================
QUESTION 7: LONG-RUNNING BEHAVIORS
============================================================================

📍 IDLE LOOPS: VMIdleForInput Primitive
File: TSOClient/tso.simantics/Primitives/VMIdleForInput.cs
Opcode: 41
Code: (see full artifact)

Behavior:

1.  Takes a countdown variable as operand
2.  Decrements it each frame
3.  Returns CONTINUE_NEXT_TICK until countdown expires
4.  On expiration, returns GOTO_TRUE

Example BHAV:

```
Local 0 = 100  // 100 frames
Instruction 0: IdleForInput(Local0)
Instruction 1: Continue
```

What happens:

- Frame 1-100: Instruction 0 returns CONTINUE_NEXT_TICK
- Frame 101: Local 0 <= 0, returns GOTO_TRUE
- Instruction 1 executes

Can check for interruption:

- AllowPush=1: Accept new interactions while idle
- Interrupt flag: Check if new action queued

Mechanism: Timer-based yielding

📍 ROUTING LOOPS: VMGotoRoutingSlot Primitive
File: TSOClient/tso.simantics/Primitives/VMGotoRoutingSlot.cs
Opcode: 32
Code: (see artifact)

Behavior:

1.  Find target slot on object
2.  Create VMRoutingFrame (special frame type)
3.  Initialize pathfinding from current position to slot
4.  Return CONTINUE to hand off to routing system

Stack model:

```
Stack frame: Main BHAV
   └─ Stack frame: Routing Frame
      └─ Pathfinding algorithm
```

Execution:

- Routing frame executes pathfinding steps
- When path complete, pops routing frame
- Returns to Main BHAV
- Main BHAV continues from branch point

Takes multiple frames to complete
Reports success/failure via exit code

📍 ANIMATION WAITING
Pattern: Play animation, then IdleForInput(1)

Example:

```
Instruction 0: PlayAnimation(waveID)  // Non-blocking
Instruction 1: IdleForInput(animationFrames)  // Block until done
Instruction 2: Continue
```

📍 MOTIVE SYSTEM (Continuous Updates)
How motives change:

1.  MotiveDeltas applied each frame
2.  Deltas set by active interaction
3.  When behavior changes, deltas reset

Example:

```
Sit and eat: +Hunger, -Bladder, -Comfort
Each frame: Motive += Delta
After 30 frames: Hunger increased by 30*DeltaHunger
```

No BHAV yielding needed - happens automatically

📍 INFINITE LOOP SAFETY: MAX_LOOP_COUNT
Location: VMThread.cs line 306
Value: 500,000 primitives
Trigger: Per frame

If exceeded:

```
throw new Exception("Thread entered infinite loop! (>" + MAX_LOOP_COUNT + " primitives)");
```

Example infinite loop:

```
Instruction 0: Expression(1==1)  // Always true
Instruction 1: Branch(goto IP 0)  // Loop
```

First 500K steps execute, then CRASH
Can add break with AllowPush or scheduled idling

ANSWER TO QUESTION 7:
"Long-running behaviors use yielding mechanisms: IdleForInput returns
CONTINUE_NEXT_TICK for timed waits, GotoRoutingSlot hands off to routing
system, animations play in parallel. Motives update automatically per tick.
Safety limit: 500,000 primitives per frame."

============================================================================
ZOMBIE TEST CASE: IMPLEMENTATION ARCHITECTURE
============================================================================

GOAL: Create autonomous zombie AI that hunts and attacks nearby living Sims.

ARCHITECTURE:
──────────────

State Machine (in Zombie avatar):

```
ZOMBIE_IDLE (no targets nearby)
  └─ Find living Sim within 50 tiles
     └─ ZOMBIE_HUNTING
        └─ Chase target via routing
           └─ If target in attack range
              └─ ZOMBIE_ATTACKING
                 └─ Play attack animation
                    └─ Check hit success
                       └─ Target dies? ZOMBIE_IDLE
                       └─ Miss? ZOMBIE_HUNTING
```

STATE STORAGE:
──────────────

```cpp
// In zombie avatar or custom controller:
const int ZOMBIE_MODE_SLOT = 95;        // 0=normal, 1=zombie
const int ZOMBIE_STATE_SLOT = 96;       // 0=idle, 1=hunting, 2=attacking
const int ZOMBIE_TARGET_SLOT = 97;      // Target sim object ID
const int ZOMBIE_RAGE_SLOT = 98;        // Rage meter (0-1000)
const int ZOMBIE_HUNT_TIMER_SLOT = 99;  // Ticks since last target check

avatar.SetPersonData(ZOMBIE_MODE_SLOT, 1);
avatar.SetPersonData(ZOMBIE_STATE_SLOT, 0);  // Start idle
```

ENTRY POINT OVERRIDE:
──────────────────────

Location: Hook into ExecuteEntryPoint(1) for Main behavior

```csharp
// In ZombieController (or patched VMEntity):
public bool ZombieExecuteEntryPoint(int entry, VMContext context) {
    var avatar = this;

    if (entry != 1) return false;  // Only override Main entry

    int zombieMode = avatar.GetPersonData(ZOMBIE_MODE_SLOT);
    if (zombieMode == 0) return false;  // Not a zombie, normal path

    // ZOMBIE PATH: Override entry point BHAV ID
    int zombieState = avatar.GetPersonData(ZOMBIE_STATE_SLOT);
    ushort mainBhavId = 0;

    switch (zombieState) {
        case 0:  // IDLE - search for targets
            mainBhavId = ZOMBIE_IDLE_BHAV;
            break;
        case 1:  // HUNTING - chase target
            mainBhavId = ZOMBIE_HUNT_BHAV;
            break;
        case 2:  // ATTACKING - melee attack
            mainBhavId = ZOMBIE_ATTACK_BHAV;
            break;
    }

    // Override entry point and execute
    avatar.EntryPoints[1] = mainBhavId;
    return avatar.ExecuteEntryPoint(1, context, false);
}
```

AUTONOMY OVERRIDE:
──────────────────

Location: Hook into VMFindBestAction.Execute()

```csharp
// In ZombieAwareFindBestAction (patched primitive):
public override VMPrimitiveExitCode Execute(VMStackFrame context, VMPrimitiveOperand args) {
    var avatar = (VMAvatar)context.Caller;
    int zombieMode = avatar.GetPersonData(ZOMBIE_MODE_SLOT);

    if (zombieMode == 0) {
        return base.Execute(context, args);  // Normal autonomy
    }

    // ZOMBIE AUTONOMY: Find nearby living Sims
    var targets = context.VM.Context.ObjectQueries.Avatars
        .Where(sim => sim != avatar && !sim.Dead)
        .OrderBy(sim => Vector2.Distance(avatar.Position.ToVector2(), sim.Position.ToVector2()))
        .ToList();

    if (targets.Count == 0) {
        avatar.SetPersonData(ZOMBIE_STATE_SLOT, 0);  // No targets, idle
        return VMPrimitiveExitCode.GOTO_FALSE;
    }

    // FOUND TARGET: Switch to hunting state
    var target = targets[0];
    avatar.SetPersonData(ZOMBIE_TARGET_SLOT, target.ObjectID);
    avatar.SetPersonData(ZOMBIE_STATE_SLOT, 1);  // HUNTING

    // Queue hunt action (will use routing)
    var huntAction = CreateZombieHuntAction(target);
    context.Caller.Thread.EnqueueAction(huntAction);

    return VMPrimitiveExitCode.GOTO_TRUE;
}

VMQueuedAction CreateZombieHuntAction(VMEntity target) {
    var action = new VMQueuedAction();
    action.Callee = target;
    action.Priority = VMQueuePriority.Urgent;
    action.Flags = TTABFlags.RunImmediately;
    // Encode: "Go to target, then try to attack"
    return action;
}
```

BHAV IMPLEMENTATIONS:
──────────────────────

ZOMBIE_IDLE_BHAV:

```
Instruction 0: VMFindBestAction  // Find targets via patched primitive
               -> True: ZOMBIE enters hunting (handled in primitive)
               -> False: wait and retry
Instruction 1: IdleForInput(30)  // Check every second
Instruction 2: Branch(goto IP 0)  // Loop until target found
```

ZOMBIE_HUNT_BHAV:

```
Instruction 0: GetStackObject(ZOMBIE_TARGET_SLOT)  // Get target
Instruction 1: GotoRoutingSlot(SlotType.Interact, target)  // Chase
               -> True: Reached target
               -> False: Target fled/unreachable
Instruction 2: SetPersonData(ZOMBIE_STATE_SLOT, 2)  // ATTACKING
Instruction 3: VMFindBestAction  // Action completed, find next target
Instruction 4: Branch(goto IP 0)  // Loop
```

ZOMBIE_ATTACK_BHAV:

```
Instruction 0: PlayAnimation(ZOMBIE_ATTACK)  // Non-blocking
Instruction 1: IdleForInput(20)  // Wait for animation
Instruction 2: TryDamageTarget()  // Custom primitive or expression
               -> True: Hit succeeded
               -> False: Miss
Instruction 3: SetPersonData(ZOMBIE_STATE_SLOT, 1)  // Back to hunting
Instruction 4: Branch(goto IP 0)
```

INTEGRATION POINTS:
────────────────────

1. VMEntity constructor:

   ```
   // Add to object initialization
   if (this.ObjectID == ZOMBIE_OBJECT_ID) {
       SetPersonData(ZOMBIE_MODE_SLOT, 1);
   }
   ```

2. VM.Update():

   ```
   foreach (var entity in Scheduler.GetScheduledEntities()) {
       if (entity is VMAvatar avatar && avatar.GetPersonData(ZOMBIE_MODE_SLOT) > 0) {
           ZombieUpdate(avatar);  // Custom zombie tick
       }
       entity.Thread.Tick();
   }
   ```

3. ExecuteEntryPoint() intercept:
   ```
   public bool ExecuteEntryPoint(int entry, ...) {
       if (GetPersonData(ZOMBIE_MODE_SLOT) > 0) {
           return ZombieExecuteEntryPoint(entry, ...);
       }
       // Normal path
   }
   ```

COEXISTENCE WITH NORMAL AUTONOMY:
─────────────────────────────────

The zombie system COEXISTS by:

1. Setting ZOMBIE_MODE_SLOT flag
2. Overriding only entry point 1 (Main)
3. Using normal queue for actions
4. Playing normal animations
5. Yielding to scheduler normally

When ZOMBIE_MODE_SLOT = 0:

- Normal Sim behavior resumes
- Normal autonomy scoring applies
- Can toggle zombie/human dynamically

============================================================================
SUMMARY: FREESO BEHAVIOR ARCHITECTURE
============================================================================

EXECUTION MODEL:
VMEntity → VMThread → Tick() → Instruction loop
30 FPS, cooperative time-slicing

AUTONOMY LAYER:
VMFindBestAction primitive scores interactions
Priority-based queue insertion
Can be completely overridden

INJECTION POINTS (6 major seams):

1. ExecuteEntryPoint(1) - Entry point override
2. EnqueueAction() - Queue insertion
3. FindBestAction - Autonomy scoring
4. HandleResult() - Result processing
5. GetCurrentInstruction() - Instruction fetch
6. NextInstruction() - Loop core

STATE STORAGE:
PersonData[101] - 101 shorts per Sim
Slots 80-100 available for custom data
ObjectData[25] - Additional state
Flags - Persistent mode bits

BEHAVIOR PATTERNS SUITABLE FOR REUSE:

- Idle loops (IdleForInput with CONTINUE_NEXT_TICK)
- Routing (GotoRoutingSlot with path following)
- Animation (PlayAnimation non-blocking)
- Motive scoring (VMFindBestAction algorithm)
- Queue management (Priority insertion)

ZOMBIE ARCHITECTURE CONCLUSION:
✅ Inherit from VMAvatar (normal Sim)
✅ Use PersonData slots 95-99 for zombie state
✅ Override ExecuteEntryPoint(1) to use zombie BHAVs
✅ Patch VMFindBestAction for zombie autonomy
✅ Coexist with normal system via flags
✅ Reuse routing, animation, queueing
✅ Can be toggled on/off at runtime

EFFORT ESTIMATE:

- Patch FindBestAction: 4 hours
- Create 3 zombie BHAVs: 8 hours
- Hook entry point: 2 hours
- Testing/debugging: 8 hours
- TOTAL: ~22 hours for full working zombie system

============================================================================
"""
