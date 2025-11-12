# SessionContextManager Implementation Guide

## Overview

This guide shows exactly where SessionContextManager fits into the existing architecture and how to implement the integration.

---

## 1. Current Code Structure

### A. UnifiedMemoryManager (src/athena/manager.py, lines 47-782)

**Current `__init__`:**
```python
def __init__(
    self,
    semantic: "MemoryStore",
    episodic: "EpisodicStore",
    procedural: "ProceduralStore",
    prospective: "ProspectiveStore",
    graph: "GraphStore",
    meta: "MetaMemoryStore",
    consolidation: "ConsolidationSystem",
    project_manager: ProjectManager,
    rag_manager: Optional["RAGManager"] = None,
    enable_advanced_rag: bool = False,
):
    self.semantic = semantic
    self.episodic = episodic
    # ... rest of initialization
```

**Proposed Addition:**
```python
def __init__(
    self,
    semantic: "MemoryStore",
    episodic: "EpisodicStore",
    procedural: "ProceduralStore",
    prospective: "ProspectiveStore",
    graph: "GraphStore",
    meta: "MetaMemoryStore",
    consolidation: "ConsolidationSystem",
    project_manager: ProjectManager,
    rag_manager: Optional["RAGManager"] = None,
    enable_advanced_rag: bool = False,
    session_manager: Optional["SessionContextManager"] = None,  # NEW
):
    # ... existing code ...
    self.session_manager = session_manager  # NEW
```

---

### B. Current `retrieve()` Method (lines 124-199)

**Current signature:**
```python
def retrieve(
    self,
    query: str,
    context: Optional[dict] = None,
    k: int = 5,
    fields: Optional[list[str]] = None,
    conversation_history: Optional[list[dict]] = None,
    include_confidence_scores: bool = True,
    explain_reasoning: bool = False
) -> dict:
```

**At line ~148 (context handling), add:**
```python
# NEW: Load session context if available
if context is None:
    context = {}

if self.session_manager:
    try:
        session_context = self.session_manager.get_current_session()
        if session_context:
            # Merge session context into query context
            context.update({
                "session_id": session_context.session_id,
                "task": session_context.current_task,
                "phase": session_context.current_phase,
                "recent_events": session_context.recent_events,
            })
    except Exception as e:
        logger.warning(f"Failed to load session context: {e}")
```

---

### C. Current `_classify_query()` Method (lines 272-312)

**Current implementation:**
```python
def _classify_query(self, query: str) -> str:
    """Classify query type based on linguistic patterns."""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["when", "last", "recent", ...]):
        return QueryType.TEMPORAL
    
    # ... more pattern matching ...
    
    return QueryType.FACTUAL
```

**Proposed enhancement after line 312:**
```python
# NEW: Context-aware refinement
def _refine_query_type(
    self,
    initial_type: str,
    session_context: dict,
    query: str
) -> str:
    """Refine query type based on session context."""
    if initial_type != QueryType.TEMPORAL:
        return initial_type  # Only refine temporal queries
    
    # In debugging phase, look for error-related queries
    if session_context.get("current_phase") == "debugging":
        if any(word in query.lower() for word in ["error", "failed", "wrong", "exception"]):
            # Still temporal but refined
            pass
    
    return initial_type
```

**Modified `_classify_query()` signature:**
```python
def _classify_query(self, query: str, session_context: Optional[dict] = None) -> str:
    query_lower = query.lower()
    # ... existing pattern matching ...
    initial_type = QueryType.FACTUAL  # or whatever was determined
    
    # NEW: Apply context-aware refinement
    if session_context:
        initial_type = self._refine_query_type(initial_type, session_context, query)
    
    return initial_type
```

---

### D. Update Call to `_classify_query()` (line 151)

**Current:**
```python
query_type = self._classify_query(query)
```

**Proposed:**
```python
query_type = self._classify_query(query, context)  # Pass context for refinement
```

---

## 2. HookDispatcher Integration (src/athena/hooks/dispatcher.py, lines 19-893)

### A. Add SessionManager to `__init__` (line 30)

**Current:**
```python
def __init__(self, db: Database, project_id: int = 1, enable_safety: bool = True):
    self.db = db
    self.project_id = project_id
    self.episodic_store = EpisodicStore(db)
    # ...
```

**Proposed:**
```python
def __init__(
    self,
    db: Database,
    project_id: int = 1,
    enable_safety: bool = True,
    session_manager: Optional["SessionContextManager"] = None,  # NEW
):
    self.db = db
    self.project_id = project_id
    self.session_manager = session_manager  # NEW
    self.episodic_store = EpisodicStore(db)
    # ...
```

### B. Update `fire_session_start()` (line 137)

**Current:**
```python
def fire_session_start(
    self, session_id: Optional[str] = None, context: Optional[dict] = None
) -> str:
    def _execute():
        nonlocal session_id
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        
        # Create session
        self.conversation_store.create_session(session_id, self.project_id)
        self._active_session_id = session_id
        # ... rest ...
```

**Add after line 158:**
```python
# NEW: Also register with SessionContextManager
if self.session_manager:
    try:
        self.session_manager.start_session(
            session_id=session_id,
            project_id=self.project_id,
            task=context.get("task") if context else None,
            phase=context.get("phase") if context else None,
        )
    except Exception as e:
        logger.warning(f"Failed to register session with SessionContextManager: {e}")
```

### C. Update `fire_conversation_turn()` (line 229)

**Add after line 310 (after turn is recorded):**
```python
# NEW: Update session context with conversation
if self.session_manager:
    try:
        self.session_manager.record_event(
            session_id=self._active_session_id,
            event_type="conversation_turn",
            event_data={
                "turn_number": self._turn_count,
                "user_content_preview": user_content[:100],
                "assistant_content_preview": assistant_content[:100],
                "duration_ms": duration_ms,
            }
        )
    except Exception as e:
        logger.warning(f"Failed to record conversation turn: {e}")
```

### D. Update `check_context_recovery_request()` (line 362)

**Current:**
```python
def check_context_recovery_request(self, prompt: str) -> Optional[dict]:
    if not self.auto_recovery.should_trigger_recovery(prompt):
        return None
    
    # User is asking for context recovery - synthesize it
    recovery_context = self.auto_recovery.auto_recover_context()
    
    # Also record this as a recovery event
    if recovery_context.get("status") == "recovered":
        event = EpisodicEvent(...)
        self.episodic_store.record_event(event)
    
    return recovery_context
```

**Proposed (after line 375, before returning):**
```python
# NEW: Try SessionContextManager first for richer recovery
if self.session_manager:
    try:
        structured_context = self.session_manager.recover_context(
            recovery_patterns=self.auto_recovery.get_recovery_patterns(),
            source="user_prompt"
        )
        if structured_context:
            return structured_context.to_dict()
    except Exception as e:
        logger.warning(f"SessionContextManager recovery failed, falling back: {e}")

# Fall back to existing recovery
recovery_context = self.auto_recovery.auto_recover_context()
```

---

## 3. WorkingMemoryAPI Integration (src/athena/episodic/working_memory.py, lines 64-89)

### A. Add SessionManager to `__init__`

**Current:**
```python
def __init__(
    self,
    db: Database,
    episodic_store: EpisodicStore,
    consolidation_callback: Optional[Callable] = None,
    capacity: int = DEFAULT_CAPACITY,
):
    self.db = db
    self.episodic_store = episodic_store
    self.consolidation_callback = consolidation_callback
    self.capacity = capacity
```

**Proposed:**
```python
def __init__(
    self,
    db: Database,
    episodic_store: EpisodicStore,
    consolidation_callback: Optional[Callable] = None,
    capacity: int = DEFAULT_CAPACITY,
    session_manager: Optional["SessionContextManager"] = None,  # NEW
):
    self.db = db
    self.episodic_store = episodic_store
    self.consolidation_callback = consolidation_callback
    self.capacity = capacity
    self.session_manager = session_manager  # NEW
```

### B. Update `_trigger_consolidation_async()` (lines 311-363)

**Add after line 361 (before `return consolidation_run_id`):**
```python
# NEW: Record consolidation in session context
if self.session_manager:
    try:
        self.session_manager.record_consolidation(
            project_id=project_id,
            consolidation_type=consolidation_type.value if consolidation_type else None,
            wm_size=size,
            consolidation_run_id=consolidation_run_id,
            trigger_type=trigger_type,
        )
    except Exception as e:
        logger.warning(f"Failed to record consolidation in session: {e}")
```

---

## 4. New File: SessionContextManager

**Create:** `src/athena/session/context_manager.py`

```python
"""Session context management for query-aware memory retrieval."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

from ..core.database import Database
from ..core.async_utils import run_async

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Structured session context."""
    
    session_id: str
    project_id: int
    current_task: Optional[str] = None
    current_phase: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    
    # Derived from recent events
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    active_items: List[Dict[str, Any]] = field(default_factory=list)
    consolidation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dict for passing to retrieve()."""
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        if self.ended_at:
            data["ended_at"] = self.ended_at.isoformat()
        return data
    
    def is_active(self) -> bool:
        """Check if session is still active."""
        return self.ended_at is None


class SessionContextManager:
    """Manages session contexts for query-aware retrieval.
    
    Coordinates with UnifiedMemoryManager, HookDispatcher, and WorkingMemoryAPI
    to maintain structured session state.
    """
    
    def __init__(self, db: Database):
        """Initialize session context manager.
        
        Args:
            db: Database instance
        """
        self.db = db
        self._current_session: Optional[SessionContext] = None
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Create session-related tables."""
        cursor = self.db.get_cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_contexts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                session_id TEXT NOT NULL UNIQUE,
                task TEXT,
                phase TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_context_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_type TEXT,
                event_data TEXT,  -- JSON
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (session_id) REFERENCES session_contexts(session_id)
                    ON DELETE CASCADE
            )
        """)
        
        self.db.commit()
    
    # ===== Core Operations =====
    
    def start_session(
        self,
        session_id: str,
        project_id: int,
        task: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> SessionContext:
        """Start a new session.
        
        Args:
            session_id: Unique session identifier
            project_id: Project ID
            task: Initial task description
            phase: Initial phase
            
        Returns:
            SessionContext instance
        """
        cursor = self.db.get_cursor()
        
        cursor.execute("""
            INSERT INTO session_contexts
            (project_id, session_id, task, phase)
            VALUES (?, ?, ?, ?)
        """, (project_id, session_id, task, phase))
        
        self.db.commit()
        
        # Create and store context
        self._current_session = SessionContext(
            session_id=session_id,
            project_id=project_id,
            current_task=task,
            current_phase=phase,
        )
        
        logger.debug(f"Started session {session_id}")
        return self._current_session
    
    def end_session(self, session_id: Optional[str] = None) -> bool:
        """End a session.
        
        Args:
            session_id: Session ID (uses current if not provided)
            
        Returns:
            True if ended successfully
        """
        end_id = session_id or (self._current_session.session_id if self._current_session else None)
        if not end_id:
            return False
        
        cursor = self.db.get_cursor()
        cursor.execute("""
            UPDATE session_contexts
            SET ended_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (end_id,))
        
        self.db.commit()
        
        if self._current_session and self._current_session.session_id == end_id:
            self._current_session.ended_at = datetime.now()
        
        logger.debug(f"Ended session {end_id}")
        return True
    
    def get_current_session(self) -> Optional[SessionContext]:
        """Get current active session.
        
        Returns:
            SessionContext or None if no active session
        """
        return self._current_session
    
    def record_event(
        self,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> int:
        """Record an event in session context.
        
        Args:
            session_id: Session ID
            event_type: Type of event (conversation_turn, consolidation, etc.)
            event_data: Event data as dict
            
        Returns:
            Event ID
        """
        cursor = self.db.get_cursor()
        
        cursor.execute("""
            INSERT INTO session_context_events
            (session_id, event_type, event_data)
            VALUES (?, ?, ?)
        """, (session_id, event_type, json.dumps(event_data)))
        
        event_id = cursor.lastrowid
        self.db.commit()
        
        logger.debug(f"Recorded {event_type} event in session {session_id}")
        return event_id
    
    def record_consolidation(
        self,
        project_id: int,
        consolidation_type: Optional[str] = None,
        wm_size: int = 0,
        consolidation_run_id: Optional[int] = None,
        trigger_type: Optional[str] = None,
    ) -> None:
        """Record consolidation event in session.
        
        Args:
            project_id: Project ID
            consolidation_type: Type of consolidation
            wm_size: Working memory size at consolidation
            consolidation_run_id: Consolidation run ID
            trigger_type: What triggered consolidation
        """
        if not self._current_session:
            return
        
        self.record_event(
            session_id=self._current_session.session_id,
            event_type="consolidation",
            event_data={
                "consolidation_type": consolidation_type,
                "wm_size": wm_size,
                "consolidation_run_id": consolidation_run_id,
                "trigger_type": trigger_type,
            }
        )
        
        # Track in memory
        self._current_session.consolidation_history.append({
            "timestamp": datetime.now().isoformat(),
            "wm_size": wm_size,
            "consolidation_run_id": consolidation_run_id,
        })
    
    def update_context(
        self,
        task: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> None:
        """Update current session context.
        
        Args:
            task: New task description
            phase: New phase
        """
        if not self._current_session:
            return
        
        if task:
            self._current_session.current_task = task
        if phase:
            self._current_session.current_phase = phase
        
        # Update database
        cursor = self.db.get_cursor()
        cursor.execute("""
            UPDATE session_contexts
            SET task = COALESCE(?, task),
                phase = COALESCE(?, phase)
            WHERE session_id = ?
        """, (task, phase, self._current_session.session_id))
        
        self.db.commit()
    
    def recover_context(
        self,
        recovery_patterns: Optional[List[str]] = None,
        source: str = "episodic_memory",
    ) -> Optional[SessionContext]:
        """Recover session context from episodic memory.
        
        Args:
            recovery_patterns: Patterns to search for
            source: Source of recovery (episodic_memory, etc.)
            
        Returns:
            Recovered SessionContext or None
        """
        if not self._current_session:
            return None
        
        # TODO: Implement recovery from episodic memory
        # This would search episodic events for recent task/phase info
        logger.debug(f"Recovering context from {source}")
        return self._current_session
```

---

## 5. Integration with Factory/Initialization

**In your application factory (likely in `src/athena/__init__.py` or similar):**

```python
# Create SessionContextManager first (before UnifiedMemoryManager)
session_manager = SessionContextManager(db)

# Pass to UnifiedMemoryManager
unified_manager = UnifiedMemoryManager(
    semantic=semantic_store,
    episodic=episodic_store,
    procedural=procedural_store,
    prospective=prospective_store,
    graph=graph_store,
    meta=meta_store,
    consolidation=consolidation_system,
    project_manager=project_manager,
    session_manager=session_manager,  # NEW
)

# Pass to HookDispatcher
hooks = HookDispatcher(
    db=db,
    project_id=project_id,
    session_manager=session_manager,  # NEW
)

# Pass to WorkingMemoryAPI
working_memory = WorkingMemoryAPI(
    db=db,
    episodic_store=episodic_store,
    consolidation_callback=consolidation_callback,
    session_manager=session_manager,  # NEW
)
```

---

## 6. Usage Example

```python
# Session starts
hooks.fire_session_start(
    session_id="session_abc123",
    context={"task": "Debug failing test", "phase": "debugging"}
)

# User makes a query
results = unified_manager.retrieve(
    query="what was the last error?",
    auto_load_session=True  # NEW: automatically loads session context
)
# Context is merged: {"task": "Debug failing test", "phase": "debugging", ...}
# Query routing is aware of debugging phase

# During query processing
# - SessionContext biases results toward recent errors
# - Results are filtered by current session
# - More relevant results are returned

# Consolidation triggered
working_memory.push_async(event)  # Triggers consolidation if full
# - SessionContextManager records consolidation event
# - Next retrieve() call sees consolidation history

# Context recovery
recovery = hooks.check_context_recovery_request("What were we working on?")
# - Uses SessionContextManager.recover_context()
# - Returns structured context with task, phase, recent events
```

