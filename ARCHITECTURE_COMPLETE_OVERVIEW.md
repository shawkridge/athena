# ATHENA PROJECT - COMPLETE ARCHITECTURE OVERVIEW

**Comprehensive Understanding of the Athena Memory System**
**Date**: November 10, 2025
**Status**: Production-ready prototype with 500+ Python files, 250K+ LOC
**Project Location**: `/home/user/.work/athena`

---

## TABLE OF CONTENTS

1. Executive Summary
2. The 8-Layer Memory Architecture (Detailed)
3. MCP Server Architecture (40+ handlers, 228+ operations)
4. Agents Tier (Multi-agent orchestration with DAG)
5. Hooks System (Automatic lifecycle management)
6. Skills System (15 reusable capabilities)
7. Commands System (20+ slash commands, 3 tiers)
8. Integration Layer (25+ coordinators)
9. Advanced Systems (RAG, Planning, Safety, Rules, Research)
10. Core Infrastructure (Database, Config, Models)
11. Data Flow and Integration Points
12. Key File Locations and Class Hierarchies
13. Database Schema Organization
14. Test Organization
15. Design Principles and Patterns

---

## PART 1: EXECUTIVE SUMMARY

Athena is a sophisticated neuroscience-inspired memory system designed for AI agents. It implements:

### Core Innovation: Dual-Process Consolidation
- **System 1 (Fast)**: Temporal clustering + heuristic extraction (~100ms)
- **System 2 (Slow)**: LLM validation when uncertainty > 0.5
- Converts episodic events into semantic knowledge during "sleep"

### 8 Memory Layers (From Bottom to Top)
1. **Episodic** - Events with spatio-temporal grounding (8,000+ events)
2. **Semantic** - Hybrid vector+BM25 facts with embeddings
3. **Procedural** - Reusable workflows extracted from experience
4. **Prospective** - Tasks, goals, reminders with smart triggers
5. **Knowledge Graph** - Entities, relations, communities (Leiden algorithm)
6. **Meta-Memory** - Quality metrics, expertise, confidence tracking
7. **Consolidation** - Sleep-like pattern extraction with dual-process
8. **Supporting** - RAG, Planning (Q*), Safety, Rules, Research

### Orchestration
- **MCP Server**: 40+ handlers, 228+ operations (11K lines)
- **Agents Tier**: 8 agent types with orchestrator (DAG execution)
- **Hooks System**: 13 automatic lifecycle hooks with safety
- **Integration**: 25+ specialized coordinators

### User Interface
- **20+ Slash Commands** across 4 priority tiers
- **15 Claude Skills** for agentic capabilities
- **CLI Interface** for local development

---

## PART 2: THE 8-LAYER MEMORY ARCHITECTURE

### Layer 1: Episodic Memory

**Path**: `/home/user/.work/athena/src/athena/episodic/`

**Purpose**: Record events with full spatio-temporal grounding

**Components**:
```
Core:
  store.py                → EpisodicStore - Event persistence CRUD
  models.py              → EpisodicEvent, EventContext, EventType
  
Orchestration:
  orchestrator.py        → Episodic pipeline with deduplication
  pipeline.py            → Event processing pipeline
  cursor.py              → Time-series cursor for streaming
  
Quality:
  hashing.py             → Event fingerprinting + deduplication
  surprise.py            → Novelty/surprise detection
  
Sources:
  sources/               → FileSystemEventSource (Phase 2)
                           Watches file changes automatically
```

**Key Classes**:
```python
class EpisodicEvent(BaseModel):
    """Event with timestamp, context, spatial grounding"""
    timestamp: datetime
    event_type: EventType  # WORK, LEARNING, ERROR, MILESTONE, DEBUG, TESTING
    context: EventContext  # File path, line number, function, args
    description: str
    outcome: EventOutcome
    session_id: str

class EventContext(BaseModel):
    """Spatial grounding for code events"""
    file_path: str
    line_number: Optional[int]
    function_name: Optional[str]
    module_name: Optional[str]
    arguments: Dict[str, Any]

class EpisodicStore(BaseStore):
    """CRUD for episodic events"""
    def record_event(event: EpisodicEvent) → int
    def recall_events(start_time, end_time) → List[EpisodicEvent]
    def recall_events_by_session(session_id) → List[EpisodicEvent]
    def get_timeline(project_id, days_back) → TimelineData
```

**Data Volume**: ~8,000 events stored in current database

**Operations**:
- Record events with automatic deduplication
- Query by date ranges, sessions, types
- Batch record (optimized for 2000+ events/sec)
- Novelty/surprise detection

---

### Layer 2: Semantic Memory

**Path**: `/home/user/.work/athena/src/athena/memory/`

**Purpose**: Store and retrieve semantic facts with hybrid search

**Components**:
```
Core:
  store.py              → MemoryStore - Semantic facts
  search.py             → Hybrid search engine
  
Quality:
  quality.py            → SemanticMemoryQualityAnalyzer
  
Optimization:
  lexical.py            → BM25 full-text search
  optimize.py           → Query optimization + ranking
```

**Key Classes**:
```python
class MemoryStore(BaseStore):
    """Store semantic facts with embeddings"""
    def store(memory: SemanticMemory) → memory_id
    def search(query: str, k: int) → List[SemanticMemory]
    def hybrid_search(query, k, vector_weight=0.7) → List[Result]
        # Combines: 70% vector similarity + 30% BM25

class SemanticMemoryQualityAnalyzer:
    """Measure quality of semantic memories"""
    - Compression: How well patterns compress events
    - Recall: Can we reconstruct original events?
    - Consistency: No contradictions
```

**Hybrid Search Strategy**:
```
Vector Search (70% weight):
  - Semantic similarity via embeddings
  - Fast, <50ms for 1000 items
  
BM25 Lexical (30% weight):
  - Exact term matching
  - Good for precise queries
  
Combined Score:
  final_score = 0.7 * vector_sim + 0.3 * bm25_score
```

**Operations**:
- Store facts with embeddings
- Hybrid search (vector + lexical)
- Quality metrics (compression, recall, consistency)
- Query caching

---

### Layer 3: Procedural Memory

**Path**: `/home/user/.work/athena/src/athena/procedural/`

**Purpose**: Learn and reuse workflows

**Components**:
```
Core:
  store.py                     → ProceduralStore - Procedure CRUD
  models.py                    → Procedure, ProcedureCategory
  
Learning:
  extraction.py                → Extract from episodic events
  pattern_extractor.py         → Code pattern extraction
  pattern_matcher.py           → Match patterns to situations
  pattern_suggester.py         → Suggest applicable patterns
  pattern_store.py             → Pattern persistence
  code_patterns.py             → Specialized code patterns
  
Advanced:
  llm_workflow_generation.py   → LLM-based generation
```

**Key Classes**:
```python
class Procedure(BaseModel):
    """Reusable workflow"""
    name: str
    category: ProcedureCategory  # DEBUG, TEST, REFACTOR, OPTIMIZE
    steps: List[ProcedureStep]
    effectiveness_score: float   # 0.0-1.0
    times_executed: int
    times_successful: int
    context: str  # When to apply

class ProceduralStore(BaseStore):
    """Procedure management"""
    def extract_procedure(events: List[EpisodicEvent]) → Procedure
    def match_patterns(code_context) → List[Pattern]
    def suggest_procedures(task: Task) → List[Procedure]
    def update_effectiveness(proc_id, success: bool)
```

**Extracted Procedures**: 101 documented in database

**Operations**:
- Extract workflows from completed work
- Pattern matching for code
- Procedure suggestions
- Effectiveness tracking (Phase 8)

---

### Layer 4: Prospective Memory

**Path**: `/home/user/.work/athena/src/athena/prospective/`

**Purpose**: Task and goal management with smart triggers

**Components**:
```
Core:
  store.py               → ProspectiveStore - Task/goal storage
  models.py             → ProspectiveTask, TaskStatus, TaskPriority
  
Management:
  monitoring.py         → Task progress tracking
  triggers.py           → Smart triggers (time/event/file)
  milestones.py         → Milestone tracking
```

**Key Classes**:
```python
class ProspectiveTask(BaseModel):
    """Task with lifecycle tracking"""
    id: str
    title: str
    status: TaskStatus  # PENDING, ACTIVE, COMPLETED, BLOCKED
    priority: TaskPriority  # LOW, MEDIUM, HIGH, CRITICAL
    phase: TaskPhase
    deadline: Optional[datetime]
    created_at: datetime
    completed_at: Optional[datetime]
    estimated_hours: float
    actual_hours: Optional[float]

class TaskTrigger(BaseModel):
    """Smart trigger for task activation"""
    trigger_type: str  # "time", "event", "file_change"
    condition: str
    action: str  # "activate", "remind", "reschedule"
```

**Trigger Types**:
- **Time-based**: At specific times or intervals
- **Event-based**: On memory events, task completions
- **File-based**: On code changes, file modifications

**Operations**:
- CRUD for tasks with deadlines
- Progress tracking and phase transitions
- Smart trigger setup and monitoring
- Milestone management

---

### Layer 5: Knowledge Graph

**Path**: `/home/user/.work/athena/src/athena/graph/`

**Purpose**: Structure semantic relationships

**Components**:
```
Core:
  store.py              → GraphStore - Entity/relation persistence
  models.py            → Entity, Relation, EntityType, RelationType
  
Analysis:
  communities.py       → Community detection (Leiden)
  analytics.py         → Graph metrics (centrality, density)
  pathfinding.py       → Path finding and traversal
  summarization.py     → Community/subgraph summaries
```

**Key Classes**:
```python
class Entity(BaseModel):
    """Knowledge graph entity"""
    id: str
    type: EntityType  # CODE, CONCEPT, PROCEDURE, PROJECT, PERSON
    name: str
    description: str
    created_at: datetime
    properties: Dict[str, Any]

class Relation(BaseModel):
    """Entity relationship"""
    source_id: str
    target_id: str
    relation_type: RelationType  # DEPENDS_ON, USES, RELATED_TO, CAUSALLY_LEADS_TO
    strength: float  # 0.0-1.0
    context: str

class Observation(BaseModel):
    """Contextual observation on entity"""
    entity_id: str
    observer_id: str
    observation: str
    timestamp: datetime
    confidence: float
```

**Relation Types**:
- DEPENDS_ON - Code/task dependencies
- USES - Module usage
- RELATED_TO - Conceptual relationships
- CAUSALLY_LEADS_TO - Causal relationships
- IMPLEMENTS - Implementation relationships
- CONTRADICTS - Contradictory information

**Community Detection**:
- Uses Leiden algorithm
- Finds natural clusters in graph
- Enables community-based retrieval

**Operations**:
- Create/update entities and relations
- Detect communities
- Find paths between concepts
- Analyze graph metrics

---

### Layer 6: Meta-Memory

**Path**: `/home/user/.work/athena/src/athena/meta/`

**Purpose**: Track knowledge about knowledge

**Components**:
```
Core:
  store.py     → MetaMemoryStore - Meta-knowledge
  models.py   → Meta-memory models
  analysis.py → Quality and expertise analysis
```

**Key Metrics**:
```
Quality Metrics:
  - Compression Ratio: How well facts compress events
  - Recall Accuracy: How well we reconstruct events
  - Consistency: Absence of contradictions
  
Domain Expertise:
  - Expertise Score: 0.0-1.0 per domain
  - Experience Count: How many events in domain
  - Confidence: Certainty of knowledge
  
Cognitive Load:
  - Working Memory Usage: 0-7±2 items
  - Processing Load: CPU-like metric
  - Saturation: When approaching limits
```

**Operations**:
- Track memory quality over time
- Measure domain expertise
- Monitor confidence levels
- Detect knowledge gaps

---

### Layer 7: Consolidation System

**Path**: `/home/user/.work/athena/src/athena/consolidation/`

**Purpose**: Convert episodic → semantic via dual-process reasoning

**Components**:
```
Core:
  system.py               → ConsolidationSystem orchestrator
  
System 1 (Fast):
  clustering.py          → Temporal clustering by proximity
  pattern_extraction.py  → Statistical pattern extraction
  event_segmentation.py  → Segment events into episodes
  
System 2 (LLM):
  dual_process.py       → Orchestrate System 1 + 2
  pattern_validation.py → LLM validation when uncertain
  llm_clustering.py     → LLM-enhanced clustering
  
Quality & Learning:
  quality_metrics.py     → Quality assessment
  advanced_metrics.py    → Advanced metric computation
  metrics_store.py       → Metric persistence
  
Domain-Specific:
  planning_pattern_extraction.py  → Planning patterns
  project_learning.py            → Project patterns
  strategy_learning.py           → Strategy patterns
  validation_learning.py         → Validation improvements
  orchestration_learning.py      → Orchestration patterns
  
Infrastructure:
  pipeline.py                    → Consolidation pipeline
  pipeline_instrumentation.py    → Observability
```

**Consolidation Algorithm**:

```
SYSTEM 1 (Fast, ~100ms):
  1. Cluster events by temporal proximity
     - Group events within 5-minute windows
     - Group events in same session
  
  2. Extract statistical patterns
     - Frequent action sequences
     - Co-occurrence analysis
     - Temporal correlations
  
  3. Calculate uncertainty
     - Pattern coherence
     - Support strength
     - Confidence in pattern

SYSTEM 2 (Slow, if uncertainty > 0.5):
  1. LLM validation
     - "Explain this pattern in natural language"
     - "Is this pattern valid?"
  
  2. Semantic verification
     - Check for contradictions
     - Verify domain relevance
  
  3. Quality refinement
     - Adjust confidence
     - Enhance description

OUTPUT:
  - New semantic facts with embeddings
  - Updated procedures with effectiveness
  - Meta-memory updates (quality, expertise)
```

**Operations**:
- Cluster episodic events
- Extract statistical patterns
- Validate with LLM (if needed)
- Convert to semantic memory
- Learn consolidation strategies

---

### Layer 8: Supporting Infrastructure

**RAG System** (`/src/athena/rag/`):
- **Strategies**: HyDE (prompt generation), reranking, reflective, query transformation
- **GraphRAG**: Community-based retrieval
- **Query Expansion**: Decompose query into sub-queries
- **Compression**: Compress long contexts
- **LLM Integration**: Ollama or Anthropic Claude

**Planning System** (`/src/athena/planning/`):
- **Q* Verification**: 5 properties (optimality, completeness, consistency, soundness, minimality)
- **Scenario Simulation**: 5 scenarios for stress testing
- **Adaptive Replanning**: Auto-adjust on assumption violation
- **Cost Optimization**: Resource-aware planning

**Other Systems**:
- **Associations** - Zettelkasten, hierarchical indexing
- **Temporal** - Git-aware chains, temporal KG synthesis
- **Spatial** - Code → spatial hierarchy mapping
- **Working Memory** - Baddeley model (7±2 items)
- **Metacognition** - Learning rate adjustment
- **Compression** - Memory compression with reconstruction
- **Rules** - Rule engine and suggestion generation

---

## PART 3: MCP SERVER ARCHITECTURE

**Location**: `/home/user/.work/athena/src/athena/mcp/`
**Main File**: `handlers.py` (11,114 lines)

### MemoryMCPServer

```python
class MemoryMCPServer:
    """Main MCP server with 40+ tools and 228+ operations"""
    
    def __init__(self):
        # Initialize all 8 memory layers
        self.semantic = MemoryStore(db)
        self.episodic = EpisodicStore(db)
        self.procedural = ProceduralStore(db)
        self.prospective = ProspectiveStore(db)
        self.graph = GraphStore(db)
        self.meta = MetaMemoryStore(db)
        self.consolidation = ConsolidationSystem(db)
        self.rag_manager = RAGManager()  # Optional
        
        # Initialize manager
        self.manager = UnifiedMemoryManager(...)
        
        # Initialize rate limiter
        self.rate_limiter = MCPRateLimiter()
        
        # Initialize operation router
        self.router = OperationRouter()
```

### Handler Architecture

**Primary**: `handlers.py` (11,114 lines)
- Defines all MCP tools
- Routes to appropriate handlers
- Manages initialization

**Specialized Handlers** (30+ files):
```
Memory Core:
  handlers_tools.py              → recall, remember, forget, optimize
  handlers_episodic.py           → record_event, recall_events
  
System/Monitoring:
  handlers_system.py             → health, monitoring, stats
  handlers_consolidation.py      → consolidate, learn patterns
  
Advanced Retrieval:
  handlers_retrieval.py          → Advanced RAG operations
  handlers_code_search.py        → Code-specific search
  
Planning & Execution:
  handlers_planning.py           → plan, validate, verify
  handlers_execution.py          → execute, monitor, replan
  
Knowledge:
  handlers_learning.py           → Extract knowledge
  handlers_synthesis.py          → Synthesize information
  
Agentic:
  handlers_agentic.py            → Verification operations
  handlers_agent_optimization.py → Agent tuning
  handlers_skill_optimization.py → Skill enhancement
  
Integration:
  handlers_integration.py        → Cross-layer operations
  handlers_hook_coordination.py  → Hook management
  handlers_slash_commands.py     → Slash command handlers
  
Analysis:
  handlers_code_analysis.py      → Code structure analysis
  handlers_library_analysis.py   → Library analysis
  handlers_review.py             → Code review
  
Other:
  handlers_prototyping.py        → Experimental features
  handlers_modern_tools.py       → Modern implementations
  handlers_confidence.py         → Confidence scoring
  handlers_external_knowledge.py → External integration
  handlers_web_research.py       → Web research
```

### Operation Router

**File**: `operation_router.py`

```python
class OperationRouter:
    """Route meta-tool operations to handler methods"""
    
    MEMORY_OPERATIONS = {
        "recall": "_handle_recall",           # Semantic search
        "remember": "_handle_remember",       # Store fact
        "forget": "_handle_forget",           # Delete memory
        "list_memories": "_handle_list_memories",
        "optimize": "_handle_optimize",       # Query optimization
        # ... 22 more
    }
    
    EPISODIC_OPERATIONS = {
        "record_event": "_handle_record_event",
        "recall_events": "_handle_recall_events",
        "get_timeline": "_handle_get_timeline",
        # ... 7 more
    }
    
    GRAPH_OPERATIONS = {
        "create_entity": "_handle_create_entity",
        "create_relation": "_handle_create_relation",
        "search_graph": "_handle_search_graph",
        # ... 12 more
    }
    
    # ... 6 more operation groups
    # Total: 120+ operations organized into 10 groups
```

### Meta-Tools (10 total)

Each meta-tool has 10-30 operations:

1. **memory-tools** - Core recall/remember/forget + optimization
2. **episodic-tools** - Event recording and temporal queries
3. **graph-tools** - Entity/relation management + analysis
4. **planning-tools** - Plan creation, validation, verification
5. **consolidation-tools** - Pattern extraction, strategy selection
6. **procedural-tools** - Workflow extraction and matching
7. **prospective-tools** - Task and goal management
8. **rag-tools** - Advanced retrieval strategies
9. **code-tools** - Code analysis and semantic search
10. **agent-tools** - Agent orchestration and execution

### Rate Limiting

**File**: `rate_limiter.py`

```python
class MCPRateLimiter:
    """Prevent abuse and cascade failures"""
    
    # Limits per operation type
    RECALL_LIMIT = 100/minute          # 100 recalls/min
    REMEMBER_LIMIT = 50/minute         # 50 stores/min
    CONSOLIDATE_LIMIT = 5/hour         # 5 consolidations/hour
    
    def check_rate(operation, user_id) → bool
    def apply_backoff(operation) → int  # Backoff in ms
```

---

## PART 4: AGENTS TIER

**Location**: `/home/user/.work/athena/src/athena/agents/`

### Agent Types (8 total)

```python
class AgentType(str, Enum):
    PLANNER = "planner"          # Decompose tasks
    EXECUTOR = "executor"        # Execute tasks
    MONITOR = "monitor"          # Track progress
    PREDICTOR = "predictor"      # Predict outcomes
    LEARNER = "learner"          # Extract knowledge
    TEMPORAL_REASONER = "temporal_reasoner"
    RESEARCH_COORDINATOR = "research_coordinator"
    # ... more specialized agents
```

### BaseAgent Class

```python
class BaseAgent(ABC):
    """Base for all agent types"""
    
    def __init__(self, agent_type: AgentType, db_path: str):
        self.agent_type = agent_type
        self.db = Database(db_path)
        self.metrics = AgentMetrics()
        self.status = AgentStatus.IDLE
        self.message_queue = []
    
    async def initialize(self) → None:
        """Async setup"""
    
    async def shutdown(self) → None:
        """Async cleanup"""
    
    async def process_message(self, message: Dict) → Dict:
        """Handle incoming message"""
    
    def get_metrics(self) → AgentMetrics:
        """Return metrics"""
    
    @property
    def health(self) → dict:
        """Health status"""
```

### AgentOrchestrator

```python
class AgentOrchestrator:
    """DAG-based task execution"""
    
    def __init__(self, agents: Dict[str, Callable]):
        self.agents = agents
        self.executions = {}
    
    def create_plan(plan_id, project_id) → ExecutionPlan:
        """Create new plan"""
    
    def add_task(task_id, agent_name, input_data, dependencies):
        """Add task with dependencies"""
    
    async def execute_plan(plan_id) → Dict[str, Any]:
        """Execute DAG (parallel where possible)"""
    
    def get_results(plan_id) → Dict[str, Dict]:
        """Get aggregated results"""
```

### ExecutionPlan and AgentTask

```python
@dataclass
class ExecutionPlan:
    """Plan for executing tasks"""
    plan_id: str
    project_id: int
    tasks: Dict[str, AgentTask]
    execution_order: List[str]  # Topological sort
    status: TaskStatus
    results: Dict[str, Dict]
    errors: Dict[str, str]

@dataclass
class AgentTask:
    """Task with dependencies"""
    id: str
    agent_name: str
    task_type: str
    input_data: Dict
    dependencies: List[str]
    status: TaskStatus
    result: Optional[Dict]
    error: Optional[str]
```

### Execution Flow

```
User Input
  ↓
PlannerAgent.decompose()
  → Creates ExecutionPlan with dependencies
  ↓
Topological Sort
  → Determines execution_order
  ↓
Parallel Execution
  ExecutorAgent.execute(task1)  [depends on nothing]
    ↓
  ExecutorAgent.execute(task2)  [depends on task1]
  ExecutorAgent.execute(task3)  [depends on task1]
    ↓
MessageBus
  → Inter-agent communication
  → Result passing
    ↓
MonitorAgent.track()
  → Detects issues
  → Triggers replanning if needed
    ↓
Result Aggregation
  → Executor combines results
  ↓
User Output
```

### Agent Specializations

**Files**:
```
planner.py                 → Task decomposition
executor.py               → Task execution
monitor.py                → Execution monitoring
predictor.py              → Outcome prediction
learner.py                → Knowledge extraction
research_coordinator.py   → Research task coordination
temporal_reasoner.py      → Temporal reasoning
workflow_manager.py       → Workflow management
```

---

## PART 5: HOOKS SYSTEM

**Location**: `/home/user/.work/athena/src/athena/hooks/`

### HookDispatcher

```python
class HookDispatcher:
    """Automatic lifecycle management"""
    
    def __init__(self, db: Database, project_id: int = 1):
        self.db = db
        self.episodic_store = EpisodicStore(db)
        self.conversation_store = ConversationStore(db)
        self._active_session_id = None
        self._active_conversation_id = None
```

### Registered Hooks (13 total)

```python
# Hook Registry
"session_start"             # New session initialization
"session_end"              # Session finalization
"conversation_turn"        # Each turn in conversation
"user_prompt_submit"       # Before processing user input
"assistant_response"       # After generating response
"task_started"            # Task begins
"task_completed"          # Task finishes
"error_occurred"          # Error caught
"pre_tool_use"            # Before tool invocation
"post_tool_use"           # After tool invocation
"consolidation_start"     # Before consolidation
"consolidation_complete"  # After consolidation
"pre_clear"              # Before memory clear
```

### Hook Handler Pattern

```python
async def on_session_start(self, session_id: str, context: Dict) → None:
    """Initialize new session"""
    with self._execute_with_safety("session_start", context, lambda: ...):
        # Create conversation
        # Initialize episodic store
        # Load context
        # Record hook execution
```

### Safety Utilities

**idempotency_tracker.py**:
```python
class IdempotencyTracker:
    """Prevent duplicate executions"""
    
    def fingerprint(context: Dict) → str:
        """Create deterministic fingerprint"""
        return hash(sorted(context.items()))
    
    def is_duplicate(hook_id, fingerprint) → bool
    def cache_result(hook_id, fingerprint, result)
    def get_cached(hook_id, fingerprint) → Optional[Any]
```

**rate_limiter.py**:
```python
class RateLimiter:
    """Limit execution frequency"""
    
    # Per-hook limits
    limits = {
        "session_start": 10/minute,
        "consolidation_start": 5/hour,
        # ...
    }
    
    def check(hook_id) → bool
    def allow(hook_id) → bool
```

**cascade_monitor.py**:
```python
class CascadeMonitor:
    """Detect cycles and deep nesting"""
    
    def enter_hook(hook_id) → None
    def exit_hook(hook_id) → None
    def has_cycle() → bool
    def depth() → int
```

### Safety Execution Pattern

```python
def _execute_with_safety(
    self, hook_id: str, context: Dict, func: Callable
) → Any:
    """Execute with 3 safety mechanisms"""
    
    # 1. Check idempotency
    fingerprint = self.idempotency_tracker.fingerprint(context)
    if self.idempotency_tracker.is_duplicate(hook_id, fingerprint):
        return self.idempotency_tracker.get_cached(hook_id, fingerprint)
    
    # 2. Check rate limiting
    if not self.rate_limiter.allow(hook_id):
        raise RateLimitError()
    
    # 3. Check cascade
    self.cascade_monitor.enter_hook(hook_id)
    if self.cascade_monitor.has_cycle():
        raise CyclicHookError()
    
    try:
        result = func()
        self.idempotency_tracker.cache_result(hook_id, fingerprint, result)
        return result
    finally:
        self.cascade_monitor.exit_hook(hook_id)
```

---

## PART 6: SKILLS SYSTEM

**Location**: `/home/user/.work/athena/src/athena/skills/` and `/claude/skills/`

### Python Skills (5 implemented)

```
bottleneck_detector.py        → Identifies performance bottlenecks
plan_learner.py              → Learns from successful plans
estimation_improver.py       → Improves task estimation accuracy
health_trend_analyzer.py     → Analyzes system health trends
project_analyzer_skill.py    → Analyzes project structure
```

### Claude Skills (15 definitions)

Located in `/home/user/.work/athena/claude/skills/`:

```
quality-evaluation/            → Evaluate memory quality
  SKILL.md                     → Prompt definition for evaluation

pattern-extraction/            → Extract patterns from data
  SKILL.md

strategy-analysis/             → Analyze strategies
task-decomposition/            → Decompose tasks
codebase-understanding/        → Understand code structure
execution-tracking/            → Track execution
graph-navigation/              → Navigate knowledge graphs
load-management/               → Manage cognitive load
cost-estimation/               → Estimate costs
change-safety/                 → Assess change safety
plan-verification/             → Verify plans
procedure-creation/            → Create procedures
event-triggering/              → Setup triggers
memory-retrieval/              → Retrieve memories
semantic-search/               → Semantic search
```

### Skill Architecture

**File Structure**:
```
claude/skills/[skill_name]/
  SKILL.md                      → Prompt definition
  instructions.md              → How to use skill
  examples.md                  → Example invocations
```

**Integration**:
```python
class SkillInvoker:
    """Invoke Claude Skills"""
    
    async def invoke_skill(skill_name, params) → Dict:
        # Load SKILL.md prompt
        # Execute with Claude
        # Return results
```

---

## PART 7: COMMANDS SYSTEM

**Location**: `/home/user/.work/athena/claude/commands/`

### Command Tiers

#### Tier 1: Critical Commands (6 commands)

```
critical/monitor-task.md
  → Monitor task execution in real-time
  → Usage: /critical:monitor-task <task_id>
  → Returns: Real-time execution status, metrics, deviations

critical/manage-goal.md
  → Create, activate, update, complete goals
  → Usage: /critical:manage-goal <name> <action> <details>
  → Actions: create, activate, update, complete
  → Has conflict detection and lifecycle tracking

critical/memory-search.md
  → Find and recall information
  → Usage: /critical:memory-search <query>
  → Searches episodic, semantic, procedural

critical/validate-plan.md
  → Validate plan with Q* formal verification
  → Usage: /critical:validate-plan <plan_description>
  → Returns: Verification result + 5-scenario stress test

critical/plan-task.md
  → Decompose complex tasks
  → Usage: /critical:plan-task <task_description>
  → Returns: Hierarchical decomposition with dependencies

critical/session-start.md
  → Load context at session start
  → Primes memory with active goals, project status, metrics
```

#### Tier 2: Advanced Commands (2 commands)

```
advanced/optimize-agents.md
  → Enhance agent performance
  → Usage: /advanced:optimize-agents <agent_name or --all>
  → Tunes behavior based on metrics

advanced/find-communities.md
  → Discover knowledge communities
  → Usage: /advanced:find-communities <level: 0|1|2>
  → Level 0 = granular, 1 = intermediate, 2 = global
```

#### Tier 3: Useful Commands (6 commands)

```
useful/retrieve-smart.md
  → Advanced semantic search (HyDE, reranking)
  → Complex boolean and semantic queries

useful/analyze-code.md
  → Deep codebase analysis
  → Optional focus area (class, module, function)

useful/setup-automation.md
  → Create event-driven automation
  → Types: time, event, file

useful/budget-task.md
  → Estimate task costs
  → Resource requirements tracking

useful/system-health.md
  → Monitor system health
  → --detailed for full analysis

useful/evaluate-safety.md
  → Assess change safety
  → Impact recommendations
```

#### Tier 4: Important Commands (6 commands)

```
important/check-workload.md
  → Assess cognitive load (7±2 model)
  → --detailed for full capacity analysis

important/optimize-strategy.md
  → Recommend optimal strategies
  → From 9+ options based on characteristics

important/learn-procedure.md
  → Create reusable procedures
  → Learns best practices from work

important/assess-memory.md
  → Evaluate memory quality
  → Identify gaps

important/consolidate.md
  → Run consolidation
  → --strategy (balanced|speed|quality|minimal)
  → --domain (specific domain)

important/explore-graph.md
  → Navigate knowledge graph
  → Understand dependencies and connections
```

### Command Implementation

**Handler**: `handlers_slash_commands.py`

```python
class SlashCommandRouter:
    """Route and execute slash commands"""
    
    async def execute(command_name, args) → Dict:
        # Parse command
        # Load CLAUDE.md definition
        # Execute with manager
        # Return results + observability
```

---

## PART 8: INTEGRATION LAYER

**Location**: `/home/user/.work/athena/src/athena/integration/`

### Specialized Coordinators (25+ total)

**Category: Analytics & Monitoring**
```
analytics.py                       → Task analytics and metrics
analytics_aggregator_agent.py      → Aggregates across agents
health_monitor_agent.py            → System health monitoring
estimation_analyzer.py             → Task estimation accuracy
milestone_tracker.py               → Milestone tracking
```

**Category: Planning & Execution**
```
planning_assistant.py              → AI planning assistance
planning_optimizer_agent.py        → Plan optimization
confidence_planner.py              → Confidence-aware planning
plan_builder.py                    → Build executable plans
replanning_monitor.py              → Monitor replanning
```

**Category: Agent Coordination**
```
agent_optimization.py              → Agent tuning
project_coordinator.py             → Project-level coordination
project_coordinator_agent.py       → Agent-based coordination
skill_optimization.py              → Skill enhancement
```

**Category: Learning & Patterns**
```
pattern_discovery.py               → Pattern discovery
task_consolidation.py              → Task consolidation
task_consolidation_sync.py         → Synchronous consolidation
auto_populate.py                   → Auto-populate memory
```

**Category: Integration**
```
hook_coordination.py               → Hook lifecycle
slash_commands.py                  → Slash command handlers
working_memory_semantic_tagger.py → Tag working memory
research_findings_index.py         → Index findings
tier1_phase5_bridge.py            → Phase 5 bridge
phase_tracking.py                  → Phase transitions
```

---

## PART 9: ADVANCED SYSTEMS

### Safety System (`/safety/`)

```python
class SafetyStore(BaseStore):
    """Store safety rules and assessments"""
    
    def get_rules(domain: str) → List[Rule]
    def assess_change(change: str) → SafetyAssessment
    def get_approval_gates(change: str) → List[Gate]
```

### Rules Engine (`/rules/`)

```python
class RulesEngine:
    """Evaluate business rules"""
    
    def evaluate(rule: Rule, context: Dict) → bool
    def get_applicable_rules(context: Dict) → List[Rule]

class SuggestionsEngine:
    """Generate suggestions"""
    
    def get_suggestions(context: Dict) → List[Suggestion]
    def rank_suggestions(suggestions) → List[Suggestion]
```

### Research System (`/research/`)

```python
class ResearchStore(BaseStore):
    """Store research tasks and findings"""

class ResearchAgentExecutor:
    """Execute multi-agent research"""
    
    async def execute_research(task: ResearchTask) → ResearchFindings
    # Spawns agents to research from multiple angles
```

### Execution System (`/execution/`)

```
monitor.py          → Execution monitoring
validator.py        → Output validation
replanning.py       → Adaptive replanning
learning.py         → Execution learning
analytics.py        → Performance metrics
```

### Verification System (`/verification/`)

```python
class VerificationGateway:
    """Gate operations before commit"""
    
    def verify(operation_type, data) → VerificationResult

class VerificationObserver:
    """Track verification decisions"""
    
    def record_decision(operation, decision, reason)

class FeedbackMetricsCollector:
    """Measure system improvement"""
    
    def get_improvement_metrics() → Dict
```

---

## PART 10: CORE INFRASTRUCTURE

**Location**: `/home/user/.work/athena/src/athena/core/`

### Database Layer

**database.py** (42K lines):
```python
class Database:
    """SQLite/PostgreSQL abstraction"""
    
    def execute(sql: str, params: List = None) → List[tuple]:
        """Execute query"""
    
    def store_memory(memory: Memory) → int:
        """Persist memory"""
    
    def get_memory(memory_id: int) → Optional[Memory]:
        """Retrieve memory"""
    
    def delete_memory(memory_id: int) → bool:
        """Delete memory"""
    
    def list_memories(project_id: int, **filters) → List[Memory]:
        """Query with filters"""
    
    # Vector operations
    def store_vector(embedding_id: int, vector: List[float]):
        """Store embedding in sqlite-vec"""
    
    def search_vectors(query_vector: List[float], k: int) → List[int]:
        """Search by vector similarity"""
    
    # Transaction management
    def begin_transaction():
    def commit():
    def rollback():
```

**database_postgres.py** (51K lines):
- PostgreSQL-specific implementation
- Connection pooling (psycopg2-pool)
- Advanced query optimization
- Distributed memory support

### Configuration

**config.py**:
```python
# Database
DATABASE_TYPE = env("DATABASE_TYPE", "sqlite")  # or "postgres"
DATABASE_PATH = env("DATABASE_PATH", "memory.db")
POSTGRES_URL = env("POSTGRES_URL", None)

# LLM/Embedding
EMBEDDING_PROVIDER = env("EMBEDDING_PROVIDER", "ollama")
LLM_PROVIDER = env("LLM_PROVIDER", "ollama")
OLLAMA_HOST = env("OLLAMA_HOST", "http://localhost:11434")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", None)

# Features
ENABLE_RAG = env("ENABLE_RAG", True)
ENABLE_PLANNING = env("ENABLE_PLANNING", True)
ENABLE_SAFETY = env("ENABLE_SAFETY", True)
DEBUG = env("DEBUG", False)
```

### Supporting Modules

```
base_store.py                 → BaseStore template
confidence_scoring.py        → Confidence scoring
embeddings.py                → Embedding generation
error_handling.py            → Error utilities
llamacpp_client.py          → LlamaCPP support
models.py                    → Core models (MemoryType)
production.py                → Production config
project_detector.py          → Project structure detection
result_models.py             → Result data models
scoring.py                   → Scoring utilities
temporal_inference.py        → Temporal reasoning
time_utils.py                → Time utilities
database_factory.py          → Create DB instance
```

---

## PART 11: DATA FLOW AND INTEGRATION

### Typical Query Flow

```
USER INPUT
  ↓
[MCP Tool Invocation]
  Tool: "memory-tools"
  Operation: "recall"
  Params: {"query": "...", "k": 5}
  ↓
[OperationRouter.route()]
  Determines: _handle_recall
  ↓
[Handler Method]
  handlers_tools.py::_handle_recall()
  ↓
[UnifiedMemoryManager]
  manager.retrieve(query, k=5)
  ↓
[Query Type Classification]
  Determines layer(s) to query:
  - Factual? → Semantic
  - Temporal? → Episodic
  - Relational? → Graph
  - Procedural? → Procedures
  ↓
[Layer Queries]
  semantic_store.search(query, k)          [Primary]
  if low_confidence:
    episodic_store.query(query)            [Fallback]
    graph_store.search(query)              [Contextual]
  ↓
[RAG Enhancement] (if enabled)
  rag_manager.retrieve(query, results)
  - Re-rank results
  - Enrich with context
  ↓
[Confidence Scoring]
  confidence_scorer.score(results, context)
  ↓
[Result Formatting]
  Format for MCP response
  ↓
[Rate Limiting Check]
  Check rate_limiter for this operation
  ↓
[Response Return]
  Return to MCP client
```

### Consolidation Flow

```
EPISODIC EVENTS (8,000+)
  │
  ├─ Raw Events
  │  ├─ Task completed
  │  ├─ Error occurred
  │  ├─ Code committed
  │  └─ Test passed
  │
  ↓
[ConsolidationSystem.consolidate()]
  │
  ├─ SYSTEM 1 (Fast, ~100ms)
  │  │
  │  ├─1. Cluster events
  │  │  ├─ Group by 5-minute windows
  │  │  ├─ Group by session
  │  │  ├─ Group by task
  │  │  └─ Temporal proximity
  │  │
  │  ├─2. Extract patterns
  │  │  ├─ Frequent sequences
  │  │  │  "commit" → "test" → "debug" (60% of time)
  │  │  ├─ Co-occurrences
  │  │  │  "error in file X" & "same person fixes" (80%)
  │  │  ├─ Temporal correlations
  │  │  └─ Statistical significance
  │  │
  │  └─3. Uncertainty assessment
  │     ├─ Pattern coherence
  │     ├─ Support strength
  │     └─ Confidence score
  │
  ├─ DECISION POINT
  │  ├─ If uncertainty < 0.5: Use System 1 patterns
  │  └─ If uncertainty >= 0.5: Continue to System 2
  │
  ├─ SYSTEM 2 (Slow, LLM validation)
  │  │
  │  ├─1. LLM validation
  │  │  └─ "Explain pattern: when developers commit, they test.
  │  │      Is this true? Any exceptions?"
  │  │
  │  ├─2. Semantic verification
  │  │  ├─ Check for contradictions
  │  │  └─ Verify domain relevance
  │  │
  │  └─3. Quality refinement
  │     ├─ Adjust confidence
  │     └─ Enhance description
  │
  ↓
[Store Results]
  ├─ New Semantic Facts
  │  ├─ Fact: "Developers typically test after commit"
  │  ├─ Confidence: 0.87
  │  └─ Evidence: 347 confirmations, 23 exceptions
  │
  ├─ Updated Procedures
  │  ├─ Procedure: "After-commit testing"
  │  ├─ Effectiveness: 0.82
  │  └─ Times executed: 147
  │
  └─ Meta-memory updates
     ├─ Quality: compression=0.76, recall=0.83, consistency=0.80
     ├─ Expertise: development=0.85, testing=0.79
     └─ Confidence: +5% increase
```

### Multi-Agent Workflow

```
USER TASK: "Refactor authentication module"
  ↓
[PlannerAgent]
  ├─ Analyze task complexity
  ├─ Identify subtasks:
  │  1. Review current auth code (no deps)
  │  2. Design new structure (deps: 1)
  │  3. Implement new module (deps: 1,2)
  │  4. Write tests (deps: 3)
  │  5. Run full test suite (deps: 4)
  │  6. Update docs (deps: 3,5)
  │
  └─ Create ExecutionPlan with DAG
  
  [ExecutionPlan.tasks]:
    {
      "task_1": {"agent": "analyzer", "deps": []},
      "task_2": {"agent": "designer", "deps": ["task_1"]},
      "task_3": {"agent": "coder", "deps": ["task_1", "task_2"]},
      "task_4": {"agent": "tester", "deps": ["task_3"]},
      "task_5": {"agent": "tester", "deps": ["task_4"]},
      "task_6": {"agent": "writer", "deps": ["task_3", "task_5"]}
    }
  ↓
[Topological Sort]
  Execution order: 1, 2, (3||4), 5, (6)
  (Note: 3 can start with 2; 4 can start with 3; 6 starts after 3,5)
  ↓
[Parallel Execution]
  t=0ms:     Start task_1 (analyzer)
  t=100ms:   task_1 done → Start task_2 (designer)
  t=250ms:   task_2 done → Start task_3 (coder) + task_4 (tester)
  t=1000ms:  task_3 done, task_4 done → task_5 (tester)
  t=1200ms:  task_5 done → task_6 (writer)
  t=1500ms:  task_6 done
  ↓
[MessageBus]
  ├─ task_1 result → task_2 input
  ├─ task_2 result → task_3 input
  ├─ task_3 result → task_4 input
  ├─ task_4 result → task_5 input
  └─ task_5 result → task_6 input
  ↓
[MonitorAgent]
  ├─ Tracks: task duration, resource usage, errors
  ├─ If task fails:
  │  └─ Triggers replanning
  │     ├─ Re-analyze task
  │     ├─ Propose workaround
  │     └─ Resume execution
  │
  └─ Logs: metrics, decisions, learnings
  ↓
[Result Aggregation]
  ├─ Collect all task results
  ├─ Compose into final output
  │  "✓ Auth module refactored
  │   - 4 new functions added
  │   - 2 security improvements
  │   - Test coverage: 94%
  │   - Docs updated"
  │
  └─ Store execution record for learning
    ↓
[LearnerAgent]
  ├─ Extract patterns from execution
  │  "Task decomposition X → Y → Z works 95% of time"
  ├─ Update procedural memory
  └─ Improve future estimates
```

---

## PART 12: KEY FILE LOCATIONS

### Entry Points

```
/src/athena/server.py            → MCP server startup
/src/athena/cli.py               → CLI interface
/src/athena/manager.py           → UnifiedMemoryManager
/src/athena/mcp/handlers.py      → Main MCP server (11K lines)
```

### Memory Layers (Core Stores)

```
Layer 1: /src/athena/episodic/store.py              → EpisodicStore
Layer 2: /src/athena/memory/store.py                → MemoryStore (semantic)
Layer 3: /src/athena/procedural/store.py            → ProceduralStore
Layer 4: /src/athena/prospective/store.py           → ProspectiveStore
Layer 5: /src/athena/graph/store.py                 → GraphStore
Layer 6: /src/athena/meta/store.py                  → MetaMemoryStore
Layer 7: /src/athena/consolidation/system.py        → ConsolidationSystem
Layer 8: /src/athena/rag/manager.py                 → RAGManager (optional)
         /src/athena/planning/store.py              → PlanningStore
```

### Manager Extensions

```
/src/athena/manager.py             → Base UnifiedMemoryManager
/src/athena/manager_agentic.py     → AgenticMemoryManager
/src/athena/manager_extensions.py  → Additional methods
```

### Agent System

```
/src/athena/agents/base.py            → BaseAgent, AgentType
/src/athena/agents/orchestrator.py    → AgentOrchestrator
/src/athena/agents/planner.py         → PlannerAgent
/src/athena/agents/executor.py        → ExecutorAgent
... (23 more agent files)
```

### Hooks System

```
/src/athena/hooks/dispatcher.py       → HookDispatcher
/src/athena/hooks/lib/*.py            → Safety utilities
/src/athena/hooks/bridge.py           → MCP integration
```

### MCP Server

```
/src/athena/mcp/handlers.py           → Main (11K lines)
/src/athena/mcp/handlers_*.py         → Specialized (30+ files)
/src/athena/mcp/operation_router.py   → Operation routing
/src/athena/mcp/rate_limiter.py       → Rate limiting
```

### Database

```
/src/athena/core/database.py          → SQLite (42K lines)
/src/athena/core/database_postgres.py → PostgreSQL (51K lines)
/src/athena/core/database_factory.py  → Factory pattern
```

---

## PART 13: DATABASE SCHEMA

### Memory Tables

```
memories
  ├─ id (primary key)
  ├─ project_id (foreign key)
  ├─ memory_type (FACT, PROCEDURE, etc.)
  ├─ content (text)
  ├─ embedding (vector)
  ├─ quality_score (float)
  ├─ created_at (timestamp)
  └─ metadata (json)

memory_metadata
  ├─ memory_id (foreign key)
  ├─ expertise_domain (string)
  ├─ confidence (float)
  ├─ usefulness_score (float)
  └─ last_used (timestamp)
```

### Episodic Tables

```
episodic_events
  ├─ id (primary key)
  ├─ project_id (foreign key)
  ├─ event_type (WORK, ERROR, etc.)
  ├─ description (text)
  ├─ context_file (string)
  ├─ context_line (int)
  ├─ context_function (string)
  ├─ timestamp (datetime)
  ├─ session_id (string)
  ├─ outcome (SUCCESS, FAILURE, etc.)
  └─ metadata (json)

event_sessions
  ├─ session_id (primary key)
  ├─ project_id (foreign key)
  ├─ started_at (datetime)
  ├─ ended_at (datetime)
  ├─ event_count (int)
  └─ notes (text)
```

### Graph Tables

```
entities
  ├─ id (primary key)
  ├─ project_id (foreign key)
  ├─ type (CODE, CONCEPT, etc.)
  ├─ name (string)
  ├─ description (text)
  └─ properties (json)

relations
  ├─ id (primary key)
  ├─ project_id (foreign key)
  ├─ source_id (foreign key → entities)
  ├─ target_id (foreign key → entities)
  ├─ relation_type (DEPENDS_ON, USES, etc.)
  ├─ strength (float)
  └─ context (text)

communities
  ├─ id (primary key)
  ├─ project_id (foreign key)
  ├─ entity_ids (json)  -- list of entity IDs
  ├─ size (int)
  ├─ density (float)
  └─ created_at (datetime)
```

### Task Tables

```
prospective_tasks
  ├─ id (primary key)
  ├─ project_id (foreign key)
  ├─ title (string)
  ├─ status (PENDING, ACTIVE, COMPLETED, BLOCKED)
  ├─ priority (LOW, MEDIUM, HIGH, CRITICAL)
  ├─ phase (string)
  ├─ deadline (datetime)
  ├─ created_at (datetime)
  ├─ completed_at (datetime)
  ├─ estimated_hours (float)
  ├─ actual_hours (float)
  └─ metadata (json)

task_triggers
  ├─ trigger_id (primary key)
  ├─ task_id (foreign key)
  ├─ trigger_type (time, event, file_change)
  ├─ condition (string)
  ├─ action (string)
  └─ enabled (bool)
```

### Procedure Tables

```
procedures
  ├─ id (primary key)
  ├─ project_id (foreign key)
  ├─ name (string)
  ├─ category (DEBUG, TEST, REFACTOR, etc.)
  ├─ steps (json)  -- list of steps
  ├─ effectiveness_score (float)
  ├─ times_executed (int)
  ├─ times_successful (int)
  └─ context (text)

patterns
  ├─ id (primary key)
  ├─ project_id (foreign key)
  ├─ pattern_type (string)
  ├─ pattern_data (json)
  ├─ confidence (float)
  ├─ support (int)  -- number of confirmations
  └─ exceptions (int)
```

### Consolidation Tables

```
consolidation_runs
  ├─ run_id (primary key)
  ├─ project_id (foreign key)
  ├─ started_at (datetime)
  ├─ completed_at (datetime)
  ├─ events_processed (int)
  ├─ patterns_extracted (int)
  └─ metrics (json)

consolidation_metrics
  ├─ metric_id (primary key)
  ├─ run_id (foreign key)
  ├─ metric_type (compression, recall, consistency)
  ├─ value (float)
  └─ calculated_at (datetime)
```

### Planning Tables

```
plans
  ├─ plan_id (primary key)
  ├─ project_id (foreign key)
  ├─ title (string)
  ├─ tasks (json)  -- task definitions
  ├─ dependencies (json)  -- task dependencies (DAG)
  ├─ status (PENDING, EXECUTING, COMPLETED)
  ├─ created_at (datetime)
  └─ completed_at (datetime)

plan_validations
  ├─ validation_id (primary key)
  ├─ plan_id (foreign key)
  ├─ validation_type (Q*, scenario, etc.)
  ├─ result (PASSED, FAILED, WARNING)
  ├─ details (json)
  └─ validated_at (datetime)
```

---

## PART 14: TEST ORGANIZATION

**Location**: `/home/user/.work/athena/tests/`

```
unit/                          → Layer unit tests
  test_episodic_*.py
  test_semantic_*.py
  test_procedural_*.py
  test_prospective_*.py
  test_graph_*.py
  test_meta_*.py
  test_consolidation_*.py
  test_planning_*.py
  test_safety_*.py
  test_verification_*.py
  test_agents_*.py
  ... (30+ test files)

integration/                   → Cross-layer tests
  test_*_integration.py
  test_manager_*.py
  test_hooks_*.py
  ... (15+ integration tests)

performance/                   → Benchmark tests
  test_*_benchmark.py
  (@pytest.mark.benchmark)

mcp/                          → MCP server tests
  test_handlers_*.py
  test_operation_router.py
  ... (10+ MCP tests)

fixtures/                     → Shared fixtures
  conftest.py                → pytest fixtures
```

### Test Pattern

```python
@pytest.fixture
def db(tmp_path):
    """Create test database"""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))

@pytest.fixture
def episodic_store(db):
    """Create episodic store"""
    return EpisodicStore(db)

def test_record_event(episodic_store):
    """Test event recording"""
    event = EpisodicEvent(...)
    event_id = episodic_store.record_event(event)
    assert event_id > 0
```

---

## PART 15: DESIGN PRINCIPLES

### 1. Layer Independence

- Each memory layer is independent
- Can add/remove layers without affecting others
- Graceful degradation if layer unavailable

### 2. Graceful Degradation

- System works without RAG (falls back to semantic search)
- System works without LLM (uses heuristics)
- System works without embeddings (uses BM25)
- System works without agents (uses single-threaded)

### 3. Local-First

- No cloud dependency
- All data stays local
- Works completely offline
- Optional cloud integration for scale

### 4. Dual-Process Reasoning

- System 1: Fast heuristics (~100ms)
- System 2: Slow LLM validation (~1-5s)
- Triggered only when needed (uncertainty > 0.5)

### 5. Observability

- Comprehensive logging at all levels
- Metrics collected for all operations
- Hook execution tracked
- Agent decisions recorded
- Consolidation patterns logged

### 6. Safety First

- Verification gates before write
- Idempotency checks
- Rate limiting
- Cascade detection
- Error recovery with backoff

### 7. Extensibility

- BaseStore template for new layers
- BaseAgent template for new agents
- OperationRouter for new operations
- Hook system for new lifecycle events
- Easy to add skills, commands, coordinators

### 8. Agentic Loop

- Verification → Observation → Learning
- Every operation recorded
- Outcomes tracked
- Patterns extracted
- System improves over time

---

## SUMMARY STATISTICS

| Component | Count | Files | LOC | Notes |
|-----------|-------|-------|-----|-------|
| Memory Layers | 8 | 60+ | 15K+ | Core to system |
| MCP Handlers | 40+ | 30+ | 50K+ | All tool definitions |
| Agent Types | 8 | 25+ | 8K+ | Orchestrated execution |
| Integration Coordinators | 25+ | 25+ | 25K+ | Cross-layer |
| Claude Skills | 15 | 15+ | 10K+ | Prompt-based |
| Slash Commands | 20+ | 20+ | 8K+ | User-facing |
| Hooks | 13 | 8 | 3K+ | Lifecycle management |
| Test Files | 50+ | 50+ | 20K+ | Unit + integration |
| Python Files | 500+ | 500+ | 250K+ | Total codebase |
| Database Tables | 80+ | - | - | Schema coverage |
| Operations | 228+ | - | - | MCP operations |
| Time to Consolidation | ~100ms | - | - | System 1 |
| Time to LLM Validation | ~1-5s | - | - | System 2 (if needed) |
| Events in DB | 8,000+ | - | - | Current volume |
| Procedures Extracted | 101+ | - | - | Reusable workflows |

---

## ARCHITECTURE DECISION RECORDS (ADRs)

### ADR 1: Why SQLite + sqlite-vec?

**Decision**: Use SQLite for episodic data + sqlite-vec for vectors

**Rationale**:
- Single file, no server setup
- Local-first, no cloud dependency
- Good enough performance (<100ms queries)
- Easy testing (tmp files)
- sqlite-vec handles embeddings

**Alternative**: PostgreSQL
- Better for distributed deployments
- Included as option for production
- Factory pattern allows switching

### ADR 2: Why Dual-Process Consolidation?

**Decision**: System 1 (fast heuristics) + System 2 (LLM validation)

**Rationale**:
- Fast common case (~100ms)
- Accurate uncertain case (~1-5s)
- Reduces LLM costs (only when needed)
- Mirrors human cognition

**Alternative**: Always use LLM
- More accurate but slower and more costly
- Harder to run locally

### ADR 3: Why DAG-Based Agent Orchestration?

**Decision**: Use DAG (Directed Acyclic Graph) for task dependencies

**Rationale**:
- Enables parallel execution
- Clear dependency semantics
- Easy to visualize and debug
- Natural for software tasks
- Topological sort for execution order

**Alternative**: State machines or workflows
- Less parallelism
- More complex state tracking

### ADR 4: Why MCP Server?

**Decision**: Use MCP (Model Context Protocol) for tool interface

**Rationale**:
- Standard protocol for Claude integration
- Easy for external tools to consume
- Natural for agentic systems
- Rate limiting + observability built-in

**Alternative**: REST API
- More overhead
- Not as integrated with Claude

---

## NEXT STEPS FOR DEVELOPERS

1. **Understanding the codebase**:
   - Start with `/src/athena/manager.py` (UnifiedMemoryManager)
   - Read `/src/athena/episodic/store.py` (simplest layer)
   - Study `/src/athena/mcp/handlers.py` (how tools are exposed)

2. **Adding a new layer**:
   - Copy `/src/athena/episodic/` structure
   - Create models.py, store.py, operations
   - Extend UnifiedMemoryManager to route to your layer
   - Add MCP tools in handlers_*.py
   - Write tests in tests/unit/test_*.py

3. **Adding a new agent**:
   - Extend BaseAgent
   - Implement process_message()
   - Register with AgentOrchestrator
   - Add handler in handlers_agentic.py

4. **Adding a new command**:
   - Create /claude/commands/[tier]/[name].md
   - Implement handler in handlers_slash_commands.py
   - Test with SlashCommandRouter

5. **Adding a new skill**:
   - Create /claude/skills/[name]/SKILL.md
   - Optionally add Python implementation
   - Register in SkillInvoker

---

## CONCLUSION

Athena represents a production-ready implementation of a sophisticated, neuroscience-inspired memory system for AI agents. With 8 memory layers, 40+ MCP handlers, 8 agent types, and 25+ integration coordinators, it provides a comprehensive platform for memory, learning, and agentic task execution.

The architecture emphasizes:
- **Modularity**: Independent, replaceable layers
- **Performance**: Dual-process reasoning balancing speed and quality
- **Safety**: Verification gates and error recovery
- **Extensibility**: Clear patterns for adding new capabilities
- **Observability**: Comprehensive logging and metrics

For questions or clarifications, refer to the CLAUDE.md file in the project root, which provides both development guidance and design philosophy.

