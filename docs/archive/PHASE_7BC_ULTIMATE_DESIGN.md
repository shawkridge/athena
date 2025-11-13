# Phase 7bc - Ultimate Hybrid Adaptive Execution System

**Status**: 🚀 In Development
**Date**: November 12, 2025
**Vision**: Build the most advanced optimal execution system combining dependency intelligence, smart caching, and distributed execution

---

## Executive Vision

Instead of choosing between Phase 7b (Layer Dependencies) OR Phase 7c (Distributed Execution), we're building **Phase 7bc** - a unified system that intelligently combines ALL optimization techniques:

```
ULTIMATE SYSTEM ARCHITECTURE
════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│  Adaptive Strategy Selector (Intelligence Layer)            │
│  ├─ Analyzes query characteristics                          │
│  ├─ Reads dependency graph                                  │
│  ├─ Consults performance profiler                           │
│  └─ Chooses: CACHE vs PARALLEL vs DISTRIBUTED               │
└─────────────────────────────────────────────────────────────┘
                            ↓
  ┌──────────────────────────────────────────────────────────┐
  │ Execution Strategy 1: CACHE-FIRST (20-40% of queries)    │
  ├─ Use dependency graph to find cached results             │
  ├─ Combine related results (cross-layer cache)             │
  ├─ Skip redundant queries entirely                         │
  └─ Overhead: <5ms, Speedup: 10-50x for cache hits          │
  ├──────────────────────────────────────────────────────────┤
  │ Execution Strategy 2: PARALLEL (60% of queries)          │
  ├─ Use existing Phase 6 parallel executor                  │
  ├─ Up to 5 concurrent layers (limited by semaphore)        │
  ├─ Smart layer selection from dependency graph             │
  └─ Overhead: ~10ms, Speedup: 3-4x                          │
  ├──────────────────────────────────────────────────────────┤
  │ Execution Strategy 3: DISTRIBUTED (10% of queries)       │
  ├─ For high-concurrency/resource-intensive queries         │
  ├─ Worker pool with 2-20 processes                         │
  ├─ Load balancing across CPU cores                         │
  └─ Overhead: ~50ms setup, Speedup: 5-10x                   │
  └──────────────────────────────────────────────────────────┘
                            ↓
  ┌──────────────────────────────────────────────────────────┐
  │ Unified Result Aggregator                                │
  ├─ Merge results from cache + parallel + distributed       │
  ├─ Resolve conflicts with confidence scoring               │
  ├─ Update dependency graph with new results                │
  └─ Record telemetry for continuous optimization            │
  └──────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Dependency Graph Engine
**File**: `src/athena/optimization/dependency_graph.py` (400 lines)

**Purpose**: Model layer relationships and result dependencies

**Key Classes**:
```python
@dataclass
class LayerDependency:
    """Models how layers depend on each other."""
    source_layer: str       # "episodic", "semantic", etc.
    target_layer: str       # Layer that depends on source
    frequency: int          # How often they appear together
    data_flow: str          # "sequential" | "parallel" | "optional"
    avg_benefit: float      # Avg improvement from parallelizing (0-1)
    cache_worthiness: float # (0-1) Is caching this pair worthwhile?

class DependencyGraph:
    def __init__(self, profiler: PerformanceProfiler):
        self.edges: Dict[str, List[LayerDependency]] = {}
        self.query_patterns: Dict[str, List[str]] = {}  # query_type -> layers

    def update_from_metrics(self, metrics: QueryMetrics) -> None:
        """Learn dependencies from query execution metrics."""

    def get_layer_selection(self, query_type: str, context: Dict) -> List[str]:
        """Smart layer selection based on learned patterns."""

    def get_parallelization_benefit(self, layers: List[str]) -> float:
        """Estimate speedup from parallelizing these layers."""

    def get_cached_results(self, layers: List[str], query_hash: str) -> Optional[Dict]:
        """Check if these layers' results are already cached together."""
```

**Algorithms**:
- **Frequency Analysis**: Track layer co-occurrence (episodic+semantic appear together 85% of the time)
- **Parallelization Benefit**: Analyze if layers run in parallel vs sequential
- **Cache Worthiness**: (Hit Rate × Result Size × Query Frequency) / Query Cost
- **Pattern Learning**: Store common query patterns (temporal → episodic+semantic, relational → graph+semantic)

---

### 2. Smart Cross-Layer Cache
**File**: `src/athena/optimization/cross_layer_cache.py` (350 lines)

**Purpose**: Cache combinations of layer results, not just individual layers

**Key Classes**:
```python
@dataclass
class CrossLayerCacheEntry:
    """Cache entry combining results from multiple layers."""
    cache_key: str              # Hash of (query_type, layers, params)
    timestamp: float            # When cached
    layers_included: List[str]  # Which layers' results are combined
    aggregate_result: Dict[str, Any]  # Merged results
    confidence: float           # 0.0-1.0, quality of cache
    hit_count: int              # Times this has been used
    total_queries_saved: int    # Cumulative benefit
    ttl_seconds: int            # Time to live

class CrossLayerCache:
    def __init__(self, max_entries: int = 5000, default_ttl_seconds: int = 300):
        self.entries: OrderedDict[str, CrossLayerCacheEntry] = OrderedDict()
        self.hit_stats: Dict[str, int] = defaultdict(int)

    def get_cache_key(self, query_type: str, layers: List[str], params: Dict) -> str:
        """Generate deterministic cache key."""

    def try_get_cached(self, query_type: str, layers: List[str], params: Dict) -> Optional[Dict]:
        """Try to get cached result for this layer combination."""

    def cache_result(self, query_type: str, layers: List[str], results: Dict, ttl: int) -> None:
        """Cache results from multiple layers together."""

    def get_cache_effectiveness(self) -> Dict[str, float]:
        """Hit rate, bytes saved, queries avoided, etc."""
```

**Optimization**:
- **LRU Eviction**: Keep most-hit combinations
- **TTL Management**: Shorter TTL for volatile data (events), longer for stable (procedures)
- **Confidence Scoring**: Recent cache entries have higher confidence
- **Cross-Layer Merging**: Intelligently combine episodic + semantic results

---

### 3. Worker Pool Executor (Distributed)
**File**: `src/athena/optimization/worker_pool_executor.py` (450 lines)

**Purpose**: Scale to 100+ concurrent queries with process-based parallelism

**Key Classes**:
```python
@dataclass
class WorkerTask:
    """Task to be distributed to worker process."""
    task_id: str
    layer_name: str
    query_fn_name: str      # Serializable function reference
    args: tuple
    kwargs: dict
    timeout_seconds: float
    priority: int           # 0-10, higher = execute sooner

class WorkerPool:
    def __init__(
        self,
        min_workers: int = 2,
        max_workers: int = 20,
        task_queue_size: int = 1000,
    ):
        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=task_queue_size)
        self.result_cache: Dict[str, Any] = {}
        self.worker_processes: List[Process] = []
        self.load_balancer = LoadBalancer(window_seconds=10)

    async def submit_task(self, task: WorkerTask, timeout_seconds: float = 30.0) -> Dict[str, Any]:
        """Submit task to queue, wait for result with timeout."""

    def adjust_worker_count(self, queue_depth: int, avg_task_latency: float) -> None:
        """Dynamically adjust worker count based on load."""

    def get_health_status(self) -> Dict[str, Any]:
        """Workers active, queue depth, avg latency, etc."""
```

**Architecture**:
```
Main Process
    ↓
Task Queue (asyncio.Queue)
    ↓
Load Balancer (decides which worker gets task)
    ├─ Worker 1 (Process) ─→ Result Cache
    ├─ Worker 2 (Process) ─→ Result Cache
    ├─ Worker 3 (Process) ─→ Result Cache
    └─ Worker N (Process) ─→ Result Cache
    ↓
Result Aggregator → Returns to caller
```

**Key Features**:
- **Dynamic Scaling**: 2-20 workers based on queue depth + latency
- **Load Balancing**: Distribute tasks to least-loaded workers
- **Priority Queue**: High-priority queries (from CLI) execute first
- **Result Caching**: Worker results cached before returning
- **Graceful Degradation**: If worker pool fails, fallback to async

---

### 4. Adaptive Strategy Selector
**File**: `src/athena/optimization/adaptive_strategy_selector.py` (400 lines)

**Purpose**: Intelligently decide CACHE vs PARALLEL vs DISTRIBUTED for each query

**Key Classes**:
```python
class ExecutionStrategy(Enum):
    """Which execution approach to use."""
    CACHE = "cache"           # Use cached results
    PARALLEL = "parallel"     # Use async parallel execution
    DISTRIBUTED = "distributed"  # Use worker pool
    SEQUENTIAL = "sequential" # Fallback to sequential

@dataclass
class StrategyDecision:
    """Decision and reasoning for execution strategy."""
    strategy: ExecutionStrategy
    confidence: float           # 0.0-1.0
    reasoning: str              # Why this choice
    estimated_latency_ms: float
    estimated_speedup: float

class AdaptiveStrategySelector:
    def __init__(
        self,
        profiler: PerformanceProfiler,
        dependency_graph: DependencyGraph,
        cross_layer_cache: CrossLayerCache,
    ):
        self.decision_history: List[StrategyDecision] = []

    def select_strategy(
        self,
        query_text: str,
        query_type: str,
        num_layers: int,
        estimated_cost: float,
        cache_availability: float,  # % of results in cache
        parallelization_benefit: float,  # Expected speedup
    ) -> StrategyDecision:
        """Intelligently choose execution strategy."""
        # Logic:
        # if cache_availability > 0.8: CACHE (10-50x faster)
        # elif num_layers <= 3 and parallelization_benefit > 1.5: PARALLEL (3-4x)
        # elif estimated_cost > 500ms: DISTRIBUTED (5-10x)
        # else: SEQUENTIAL
```

**Decision Tree**:
```
Query arrives
    ↓
Check cache availability (0-100%)
    ├─ >80%: USE CACHE (estimated 20-50x speedup)
    │   └─ Try cross-layer cache
    │   └─ If miss, fall through
    ├─ 40-80%: HYBRID (cache what we can, parallelize rest)
    │   └─ Partially cache, partially parallel
    │   └─ Combine results
    └─ <40%: No cache benefit
        ↓
    Check query cost + complexity
        ├─ Low cost (<50ms), simple: SEQUENTIAL (not worth overhead)
        ├─ Medium cost (50-500ms): PARALLEL (3-4x benefit)
        └─ High cost (>500ms): DISTRIBUTED (5-10x benefit)
            └─ Also check worker pool load
            └─ If busy, fall back to PARALLEL
```

---

### 5. Unified Result Aggregator
**File**: `src/athena/optimization/result_aggregator.py` (300 lines)

**Purpose**: Intelligently merge results from different execution paths

**Key Classes**:
```python
class ResultAggregator:
    def __init__(self, confidence_scorer):
        self.merger = ResultMerger()

    def aggregate_results(
        self,
        cache_results: Optional[Dict],
        parallel_results: Dict[str, Any],
        distributed_results: Optional[Dict],
        confidence_scores: Dict[str, float],
    ) -> Tuple[Dict[str, Any], float]:
        """Merge results from multiple sources with conflict resolution."""
        # Strategy:
        # 1. Use cache if available (it's recent and verified)
        # 2. For missing layers, use parallel results
        # 3. For remaining gaps, use distributed results
        # 4. Score overall confidence based on source freshness

    def resolve_conflicts(
        self,
        cache_value: Any,
        parallel_value: Any,
        cache_age_seconds: float,
        parallel_latency_ms: float,
    ) -> Tuple[Any, float]:
        """When we have multiple values, pick the best one."""
        # Prefer fresher, higher-confidence results
```

---

### 6. Advanced Telemetry & Feedback Loop
**File**: `src/athena/optimization/execution_telemetry.py` (250 lines)

**Purpose**: Track execution effectiveness for continuous optimization

**Metrics Captured**:
```python
@dataclass
class ExecutionTelemetry:
    """Detailed telemetry of a query execution."""
    query_id: str
    strategy_chosen: ExecutionStrategy
    strategy_confidence: float
    cache_hit: bool
    cache_benefit_ms: float      # Latency saved by cache
    parallel_speedup: float      # Actual speedup vs sequential
    distributed_speedup: float   # Actual speedup vs parallel
    total_latency_ms: float
    estimated_vs_actual: float   # Was our estimate accurate?
    success: bool

    # For ML training (future)
    query_features: Dict[str, float]  # Complexity, num_layers, etc.
    execution_path: List[str]         # Which strategies were tried
```

**Continuous Learning**:
- Track decision accuracy (did our estimate match reality?)
- Retrain dependency graph with new patterns
- Update layer parallelization benefits
- Adjust strategy selection thresholds

---

## Integration Points

### With Manager
```python
class UnifiedMemoryManager:
    def __init__(self, ...):
        # Existing components
        self.performance_profiler = PerformanceProfiler()
        self.auto_tuner = AutoTuner()
        self.parallel_tier1_executor = ParallelTier1Executor()

        # NEW: Phase 7bc components
        self.dependency_graph = DependencyGraph(self.performance_profiler)
        self.cross_layer_cache = CrossLayerCache()
        self.worker_pool = WorkerPool(min_workers=2, max_workers=20)
        self.strategy_selector = AdaptiveStrategySelector(
            profiler=self.performance_profiler,
            dependency_graph=self.dependency_graph,
            cross_layer_cache=self.cross_layer_cache,
        )
        self.result_aggregator = ResultAggregator(self.confidence_scorer)

    async def recall(self, query: str, k: int = 5, **context) -> List[Dict]:
        """Main recall method - now with ultimate optimization."""
        # 1. Classify query type
        query_type = self._classify_query(query)

        # 2. Analyze query for optimization potential
        analysis = self._analyze_query_for_optimization(query, query_type)

        # 3. SELECT STRATEGY: Cache vs Parallel vs Distributed
        strategy = self.strategy_selector.select_strategy(
            query_text=query,
            query_type=query_type,
            num_layers=len(analysis.suggested_layers),
            estimated_cost=analysis.estimated_cost,
            cache_availability=analysis.cache_hit_probability,
            parallelization_benefit=self.dependency_graph.get_parallelization_benefit(
                analysis.suggested_layers
            ),
        )

        # 4. EXECUTE with chosen strategy
        if strategy == ExecutionStrategy.CACHE:
            results = await self._execute_cache_strategy(...)
        elif strategy == ExecutionStrategy.PARALLEL:
            results = await self._execute_parallel_strategy(...)
        elif strategy == ExecutionStrategy.DISTRIBUTED:
            results = await self._execute_distributed_strategy(...)
        else:
            results = await self._execute_sequential_strategy(...)

        # 5. AGGREGATE results from all sources
        final_results, confidence = self.result_aggregator.aggregate_results(...)

        # 6. RECORD telemetry for next iteration
        self._record_execution_telemetry(...)

        return final_results
```

---

## Performance Targets

| Scenario | Current | Phase 7bc | Improvement |
|----------|---------|-----------|-------------|
| **Simple cached query** | 50ms | 5ms | **10x** |
| **Mixed workload (50% cache)** | 150ms | 30ms | **5x** |
| **Complex parallel query** | 200ms | 50ms | **4x** |
| **High-concurrency (10 parallel)** | 5000ms | 500ms | **10x** |
| **Extreme case (100 concurrent)** | timeout | 2000ms | **✅ Now possible** |
| **Overall system throughput** | 50 qps | 200+ qps | **4x** |

---

## Implementation Order

1. **Dependency Graph** (400 lines) - Foundation for all decisions
2. **Cross-Layer Cache** (350 lines) - Quick wins, 20-40% queries cached
3. **Strategy Selector** (400 lines) - Intelligent routing
4. **Result Aggregator** (300 lines) - Merge and conflict resolution
5. **Worker Pool** (450 lines) - Distributed execution for high-load
6. **Telemetry** (250 lines) - Continuous learning loop
7. **Manager Integration** (150 lines) - Bind it all together
8. **Tests** (600 lines) - Comprehensive validation
9. **Benchmarks** (200 lines) - Performance validation

---

## Testing Strategy

```python
# Unit Tests
test_dependency_graph.py (40 tests)
test_cross_layer_cache.py (35 tests)
test_strategy_selector.py (45 tests)
test_worker_pool.py (40 tests)
test_result_aggregator.py (30 tests)

# Integration Tests
test_hybrid_execution.py (60 tests)
- Cache + Parallel
- Cache + Distributed
- Parallel + Distributed
- All three combined

# Performance Tests
test_phase_7bc_performance.py (50 tests)
- Cache hit scenarios
- Parallel speedup validation
- Worker pool scaling
- Mixed workload behavior
```

---

## Success Criteria

✅ **Correctness**: All 250+ tests passing, no result conflicts
✅ **Performance**: 4-10x improvement across scenarios
✅ **Scalability**: Handle 100+ concurrent queries gracefully
✅ **Reliability**: Graceful fallback if any component fails
✅ **Maintainability**: <150 lines per class, clear abstractions
✅ **Monitoring**: Rich telemetry for continuous optimization

---

## Timeline

**Phase 7bc**: 3-4 focused sessions
- Session 1: Dependency Graph + Cross-Layer Cache
- Session 2: Strategy Selector + Result Aggregator
- Session 3: Worker Pool + Telemetry
- Session 4: Integration + Testing + Benchmarks

**Total Code**: ~3,000 lines (core) + ~600 lines (tests) + ~200 lines (benchmarks)

---

## The Vision

We're not just optimizing execution - we're building a **self-learning system** that:

1. **Understands dependencies** between layers (dependency graph)
2. **Learns which results are worth caching** (cross-layer cache)
3. **Intelligently chooses execution approaches** (strategy selector)
4. **Handles any scale** from single query to 100+ concurrent (worker pool)
5. **Continuously improves** through telemetry and feedback

This is the foundation for **truly intelligent memory orchestration**.

