"""
Event bus for panel communication.
Decoupled pub/sub pattern for cross-panel events.
"""

from typing import Callable, Any


class EventBus:
    """Central event system for panel communication."""
    
    _subscribers: dict[str, list[Callable]] = {}
    
    @classmethod
    def subscribe(cls, event: str, callback: Callable):
        """Subscribe to an event."""
        if event not in cls._subscribers:
            cls._subscribers[event] = []
        cls._subscribers[event].append(callback)
    
    @classmethod
    def publish(cls, event: str, data: Any = None):
        """Publish an event to all subscribers."""
        for cb in cls._subscribers.get(event, []):
            try:
                cb(data)
            except Exception as e:
                print(f"EventBus error on '{event}': {e}")
    
    @classmethod
    def unsubscribe(cls, event: str, callback: Callable):
        """Unsubscribe from an event."""
        if event in cls._subscribers:
            try:
                cls._subscribers[event].remove(callback)
            except ValueError:
                pass
    
    @classmethod
    def clear(cls):
        """Clear all subscriptions."""
        cls._subscribers.clear()


# Event constants - use these for type safety
class Events:
    """Event name constants."""
    # File events
    FILE_LOADED = "file.loaded"
    FILE_CLEARED = "file.cleared"
    
    # Archive events
    FAR_LOADED = "far.loaded"
    IFF_LOADED = "iff.loaded"
    
    # Chunk/BHAV events
    CHUNK_SELECTED = "chunk.selected"
    BHAV_SELECTED = "bhav.selected"
    
    # Character/Sim events
    CHARACTER_SELECTED = "character.selected"
    
    # Graph events
    GRAPH_NODE_SELECTED = "graph.node_selected"
    
    # Search events
    SEARCH_RESULT_SELECTED = "search.result_selected"
    
    # Save events
    SAVE_MODIFIED = "save.modified"
    
    # Analysis events
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETE = "analysis.complete"
    STATUS_UPDATE = "status.update"
