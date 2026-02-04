"""
Contextual Help System.

Provides:
- "I'm Lost" escape hatch
- First-encounter auto-explanations
- Context-aware help
"""

from dataclasses import dataclass, field
from typing import Optional, Callable
import dearpygui.dearpygui as dpg


@dataclass
class HelpTopic:
    """A help topic with explanation."""
    
    key: str
    title: str
    short_desc: str
    full_explanation: str
    first_encounter: bool = True  # Show automatically first time
    related_topics: list[str] = field(default_factory=list)


class HelpSystem:
    """
    Contextual help system.
    
    Features:
    - First-encounter explanations (shown once)
    - "I'm Lost" escape hatch (contextual)
    - Topic database
    """
    
    # Core TS1 concepts that need explanation
    TOPICS = {
        "bhav": HelpTopic(
            key="bhav",
            title="What is a BHAV?",
            short_desc="Behavior - The code that makes Sims do things",
            full_explanation="""
BHAV (Behavior) is the scripting system in The Sims 1.

Think of it like a flowchart:
• Each box is an instruction (primitive)
• Green arrows = "yes/true" path
• Red arrows = "no/false" path

BHAVs control EVERYTHING:
• How Sims eat, sleep, talk
• What happens when you click an object
• Autonomous decisions

BHAVs are NOT like normal code - they're more like
cooperative state machines that yield control often.
            """.strip(),
            related_topics=["primitive", "semiglobal", "ttab"]
        ),
        
        "primitive": HelpTopic(
            key="primitive",
            title="What is a Primitive?",
            short_desc="A single instruction in a BHAV",
            full_explanation="""
A Primitive is one instruction in a BHAV flowchart.

Types of primitives:
• Control: Sleep, loops, jumps, calls
• Math: Expressions, random numbers
• Sim: Change mood, relationship, motives
• Object: Find objects, remove, create
• Animation: Play animations, sounds
• Debug: Breakpoints (for testing)

Each primitive has:
• An opcode (what it does)
• Operands (parameters)
• True/False exit paths

When you see "[2] Expression T->3 F->5", it means:
Instruction 2 runs Expression, goes to 3 if true, 5 if false.
            """.strip(),
            related_topics=["bhav", "opcode"]
        ),
        
        "semiglobal": HelpTopic(
            key="semiglobal",
            title="⚠️ What is a Semi-Global?",
            short_desc="Shared behavior used by MULTIPLE objects",
            full_explanation="""
Semi-Globals are the #1 FOOTGUN in Sims 1 modding.

What they are:
• Behaviors shared across multiple objects
• Example: "Sit" behavior used by all chairs

Why they're dangerous:
• Edit one → affects DOZENS of objects
• You think you're modding a chair
• You actually broke every sofa too

How to stay safe:
• Check the scope indicator (top of screen)
• Look at "Affected Objects" panel
• Consider FORKING instead of editing
• Always create a snapshot first

Semi-globals exist to save memory (1999 computers!).
Modern modding tools should warn you. This one does.
            """.strip(),
            first_encounter=True,
            related_topics=["bhav", "global", "scope"]
        ),
        
        "global": HelpTopic(
            key="global",
            title="⚠️ What is Global.iff?",
            short_desc="THE master file - affects EVERYTHING",
            full_explanation="""
Global.iff is the GOD FILE of The Sims 1.

What's in it:
• Core game behaviors
• Universal primitives
• Base interactions

If you edit this:
• EVERY Sim is affected
• EVERY object is affected
• EVERY lot is affected

There is no "undo" if you break this.

ALWAYS:
1. Create a backup first
2. Use the snapshot system
3. Test in a throwaway game folder
4. Know EXACTLY what you're changing

The scope indicator will turn RED when editing globals.
            """.strip(),
            first_encounter=True,
            related_topics=["semiglobal", "scope"]
        ),
        
        "ttab": HelpTopic(
            key="ttab",
            title="What is a TTAB?",
            short_desc="Tree Table - Links pie menu to BHAVs",
            full_explanation="""
TTAB (Tree Table) is the bridge between:
• What you SEE (pie menu options)
• What HAPPENS (BHAV behaviors)

When you click an object and see "Watch TV":
1. TTAB defines "Watch TV" as an option
2. TTAB points to the BHAV that runs it
3. TTAB sets who can use it (adults only, etc.)

TTAB contains:
• Interaction name
• Which BHAV to run
• Autonomy settings
• Motives it advertises
• Who can see/use it

To add a new interaction:
1. Create the BHAV (behavior)
2. Add entry to TTAB (connection)
3. Add string to STR# (name)
            """.strip(),
            related_topics=["bhav", "str"]
        ),
        
        "scope": HelpTopic(
            key="scope",
            title="Understanding Edit Scope",
            short_desc="What will your edit affect?",
            full_explanation="""
The SCOPE INDICATOR shows what your edit will affect.

🟢 Single Chunk - Safest
   Only this one piece of data

🔵 This Object Only - Safe
   Only this object's files

🟡 Semi-Global - CAUTION
   Multiple objects share this behavior
   
🔴 Global - DANGER
   Affects the entire game

The scope banner is ALWAYS visible when editing.
If it says "14 objects affected" - believe it!

To reduce scope:
• Fork semi-globals to object-specific
• Duplicate before editing globals
• Use sandbox mode for experiments
            """.strip(),
            first_encounter=True,
            related_topics=["semiglobal", "global"]
        ),
        
        "iff": HelpTopic(
            key="iff",
            title="What is an IFF file?",
            short_desc="The container format for Sims 1 game data",
            full_explanation="""
IFF (Interchange File Format) is the container.

Think of it like a ZIP file:
• One IFF contains many "chunks"
• Each chunk has a type (BHAV, STR#, OBJD, etc.)
• Each chunk has an ID number
• Each chunk has a label (name)

Common chunk types:
• BHAV - Behaviors (code)
• OBJD - Object Definition (stats)
• STR# - Strings (text)
• TTAB - Interaction tree
• SLOT - Routing slots
• BCON - Constants

IFF files live inside FAR archives.
FAR is just a simple container for multiple IFFs.
            """.strip(),
            related_topics=["bhav", "far"]
        ),
        
        "far": HelpTopic(
            key="far",
            title="What is a FAR file?",
            short_desc="Archive containing multiple IFF files",
            full_explanation="""
FAR (File Archive) is a simple container format.

It's like a ZIP but simpler:
• Just a list of files
• No compression (usually)
• Quick to read

Key FAR files:
• Objects.far - All buyable objects
• UserObjects.far - Downloaded objects
• ExpansionObjects.far - Expansion content
• Global.far - Global behaviors

When modding:
1. Open the FAR
2. Extract the IFF you want
3. Edit the IFF
4. Put it back (or in Downloads)

You can also put loose IFF files in Downloads/
without re-packing into FAR.
            """.strip(),
            related_topics=["iff"]
        ),
        
        "confidence": HelpTopic(
            key="confidence",
            title="What do Confidence Levels mean?",
            short_desc="How sure the tool is about classifications",
            full_explanation="""
This tool classifies BHAVs into roles:
• ROLE - Controller behaviors
• FLOW - Glue/routing logic
• ACTION - Actual animations/effects
• GUARD - Condition checks

Confidence shows how sure we are:

🟢 High (80%+)
   Strong pattern match
   Multiple indicators agree
   Trust this classification

🟡 Medium (50-80%)
   Some indicators present
   Could be this role
   Verify if important

🟠 Low (<50%)
   Weak match
   Heuristic guess
   Don't rely on this

Click any classification to see WHY
the tool thinks it's that role.
            """.strip(),
            related_topics=["bhav"]
        ),
        
        "sandbox": HelpTopic(
            key="sandbox",
            title="Sandbox / Playground Mode",
            short_desc="Experiment without affecting real files",
            full_explanation="""
Sandbox Mode lets you experiment safely.

How it works:
• Changes are NOT saved to real files
• Work in a temporary copy
• See results without risk
• Diff against original

Use sandbox mode to:
• Learn how BHAVs work
• Test crazy ideas
• Understand before committing
• Train yourself on the tool

To exit sandbox:
• Discard all - return to real files
• Commit changes - write to disk
• Export patch - save just changes

Sandbox is PERFECT for beginners.
Break everything. Learn. No consequences.
            """.strip(),
            first_encounter=True,
            related_topics=["scope"]
        ),
    }
    
    def __init__(self):
        self._seen_topics: set[str] = set()
        self._current_context: str = ""
        self._on_first_encounter_callbacks: list[Callable] = []
    
    def mark_seen(self, topic_key: str):
        """Mark a topic as seen (no more auto-popup)."""
        self._seen_topics.add(topic_key)
    
    def has_seen(self, topic_key: str) -> bool:
        """Check if user has seen this topic."""
        return topic_key in self._seen_topics
    
    def should_show_first_encounter(self, topic_key: str) -> bool:
        """Check if we should auto-show this topic."""
        topic = self.TOPICS.get(topic_key)
        if not topic:
            return False
        return topic.first_encounter and not self.has_seen(topic_key)
    
    def set_context(self, context: str):
        """Set current context for "I'm Lost" help."""
        self._current_context = context
    
    def get_contextual_topics(self) -> list[str]:
        """Get relevant topics for current context."""
        context_map = {
            "bhav_editor": ["bhav", "primitive", "confidence"],
            "iff_viewer": ["iff", "bhav", "ttab"],
            "far_browser": ["far", "iff"],
            "chunk_inspector": ["iff", "bhav"],
            "edit_mode": ["scope", "semiglobal", "global", "sandbox"],
        }
        return context_map.get(self._current_context, ["iff", "bhav"])
    
    def on_first_encounter(self, callback: Callable):
        """Register callback for first encounter events."""
        self._on_first_encounter_callbacks.append(callback)
    
    def trigger_first_encounter(self, topic_key: str):
        """Trigger first encounter for a topic."""
        if self.should_show_first_encounter(topic_key):
            for cb in self._on_first_encounter_callbacks:
                try:
                    cb(topic_key, self.TOPICS[topic_key])
                except Exception as e:
                    print(f"First encounter callback error: {e}")
    
    def show_help_window(self, topic_key: Optional[str] = None):
        """Show the help window, optionally for a specific topic."""
        window_tag = "help_window"
        
        if dpg.does_item_exist(window_tag):
            dpg.delete_item(window_tag)
        
        with dpg.window(
            label="😬 Help - I'm Lost",
            tag=window_tag,
            width=550,
            height=450,
            pos=(525, 275),
            modal=False,
            no_collapse=True
        ):
            # Context bar
            dpg.add_text(
                f"Current context: {self._current_context or 'General'}",
                color=(150, 150, 150)
            )
            dpg.add_separator()
            
            # Topic list on left, content on right
            with dpg.group(horizontal=True):
                # Topic list
                with dpg.child_window(width=150, height=350, border=True):
                    dpg.add_text("Topics", color=(100, 180, 255))
                    dpg.add_separator()
                    
                    # Show contextual topics first
                    contextual = self.get_contextual_topics()
                    if contextual:
                        dpg.add_text("Relevant:", color=(150, 150, 150))
                        for key in contextual:
                            if key in self.TOPICS:
                                topic = self.TOPICS[key]
                                dpg.add_button(
                                    label=topic.title,
                                    width=-1,
                                    callback=lambda s, a, k=key: self._show_topic(k)
                                )
                        dpg.add_separator()
                    
                    dpg.add_text("All Topics:", color=(150, 150, 150))
                    for key, topic in self.TOPICS.items():
                        if key not in contextual:
                            dpg.add_button(
                                label=topic.title,
                                width=-1,
                                callback=lambda s, a, k=key: self._show_topic(k)
                            )
                
                # Content area
                with dpg.child_window(tag="help_content", width=-1, height=350, border=True):
                    if topic_key and topic_key in self.TOPICS:
                        self._render_topic_content(self.TOPICS[topic_key])
                    else:
                        dpg.add_text("Select a topic from the left", color=(150, 150, 150))
                        dpg.add_spacer(height=20)
                        dpg.add_text(
                            "Or just explore - the best way to learn\n"
                            "is to click around in Sandbox mode!",
                            color=(100, 180, 255)
                        )
            
            dpg.add_separator()
            dpg.add_button(
                label="Close",
                width=100,
                callback=lambda: dpg.delete_item(window_tag)
            )
    
    def _show_topic(self, topic_key: str):
        """Show a specific topic in the help content area."""
        if topic_key not in self.TOPICS:
            return
        
        topic = self.TOPICS[topic_key]
        self.mark_seen(topic_key)
        
        # Clear and re-render content
        dpg.delete_item("help_content", children_only=True)
        self._render_topic_content(topic, parent="help_content")
    
    def _render_topic_content(self, topic: HelpTopic, parent: str = None):
        """Render topic content."""
        kwargs = {'parent': parent} if parent else {}
        
        dpg.add_text(topic.title, color=(100, 220, 150), **kwargs)
        dpg.add_text(topic.short_desc, color=(180, 180, 180), **kwargs)
        dpg.add_separator(**kwargs)
        dpg.add_spacer(height=10, **kwargs)
        
        # Render full explanation with proper line breaks
        for line in topic.full_explanation.split('\n'):
            if line.startswith('•'):
                dpg.add_text(line, color=(200, 200, 200), bullet=True, **kwargs)
            elif line.strip() == '':
                dpg.add_spacer(height=5, **kwargs)
            else:
                dpg.add_text(line, wrap=480, **kwargs)
        
        # Related topics
        if topic.related_topics:
            dpg.add_spacer(height=15, **kwargs)
            dpg.add_separator(**kwargs)
            dpg.add_text("Related:", color=(150, 150, 150), **kwargs)
            with dpg.group(horizontal=True, **kwargs):
                for related in topic.related_topics:
                    if related in self.TOPICS:
                        dpg.add_button(
                            label=self.TOPICS[related].title,
                            callback=lambda s, a, k=related: self._show_topic(k)
                        )
    
    def show_first_encounter_popup(self, topic_key: str):
        """Show a first-encounter popup for a topic."""
        if topic_key not in self.TOPICS:
            return
        
        topic = self.TOPICS[topic_key]
        popup_tag = f"first_encounter_{topic_key}"
        
        if dpg.does_item_exist(popup_tag):
            return
        
        with dpg.window(
            label=f"💡 {topic.title}",
            tag=popup_tag,
            width=450,
            height=200,
            pos=(575, 400),
            modal=False,
            no_collapse=True
        ):
            dpg.add_text(topic.short_desc, color=(100, 220, 150))
            dpg.add_separator()
            
            # Show abbreviated explanation
            lines = topic.full_explanation.split('\n')[:6]
            for line in lines:
                if line.strip():
                    dpg.add_text(line, wrap=420)
            
            if len(topic.full_explanation.split('\n')) > 6:
                dpg.add_text("...", color=(150, 150, 150))
            
            dpg.add_spacer(height=10)
            
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Got it",
                    width=100,
                    callback=lambda: self._dismiss_first_encounter(popup_tag, topic_key)
                )
                dpg.add_button(
                    label="Tell me more",
                    width=120,
                    callback=lambda: self._expand_first_encounter(popup_tag, topic_key)
                )
    
    def _dismiss_first_encounter(self, popup_tag: str, topic_key: str):
        """Dismiss first encounter popup."""
        self.mark_seen(topic_key)
        if dpg.does_item_exist(popup_tag):
            dpg.delete_item(popup_tag)
    
    def _expand_first_encounter(self, popup_tag: str, topic_key: str):
        """Expand to full help window."""
        self._dismiss_first_encounter(popup_tag, topic_key)
        self.show_help_window(topic_key)


# Singleton instance
HELP = HelpSystem()
