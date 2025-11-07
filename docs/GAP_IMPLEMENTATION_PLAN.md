# Athena Gap Implementation Plan

**Generated**: 2025-11-06
**Status**: Execution Phase
**Priority**: Top 10 Critical Gaps

---

## 📋 TASK BREAKDOWN & EXECUTION ORDER

### PHASE 1: Quick Wins (Weeks 1-2)

#### Task 1.1: GraphRAG Integration ⭐⭐⭐ (1 week)
**Status**: READY TO START
**Files to Create**:
- `src/athena/rag/graphrag.py` - GraphRAG manager
- `tests/unit/test_graphrag.py` - Unit tests
- `tests/integration/test_graphrag_integration.py` - Integration tests

**Implementation Steps**:
1. [ ] Create GraphRAG manager class
2. [ ] Implement community summarization
3. [ ] Implement global_search() method
4. [ ] Implement local_search() method
5. [ ] Implement hybrid_search() (combine semantic + graph + BM25)
6. [ ] Write unit tests
7. [ ] Write integration tests
8. [ ] Update MCP handlers with GraphRAG tools

**Key Metrics**:
- Community summary quality (human eval)
- Global search accuracy vs baseline
- Query latency (<500ms target)

---

#### Task 1.2: Git-Aware Context ⭐⭐ (3 days)
**Status**: READY TO START
**Files to Create**:
- `src/athena/code/git_context.py` - Git context manager
- `tests/unit/test_git_context.py` - Tests

**Implementation Steps**:
1. [ ] Create GitContext class
2. [ ] Implement get_changed_files() method
3. [ ] Implement get_changed_diff() method
4. [ ] Integrate with code analyzer
5. [ ] Write tests
6. [ ] Update context assembly to prioritize changed files

**Key Metrics**:
- Correctly identifies changed files (accuracy)
- Prioritizes changed files in context
- Git integration reliability

---

#### Task 1.3: Community Summarization ⭐⭐ (3 days)
**Status**: READY TO START
**Files to Modify**:
- `src/athena/graph/store.py` - Add summarization

**Implementation Steps**:
1. [ ] Add summary field to community entities
2. [ ] Create summarization function
3. [ ] Batch summarize all communities
4. [ ] Cache summaries
5. [ ] Update community retrieval to return summaries

**Key Metrics**:
- Summary quality (semantic similarity to original)
- Summary length (target: 100-200 tokens)
- Summarization speed (cost efficiency)

---

#### Task 1.4: Gisting (Prompt Caching) ⭐⭐ (1 week)
**Status**: READY TO START
**Files to Create**:
- `src/athena/efficiency/gisting.py` - Pre-computed summaries
- `tests/unit/test_gisting.py` - Tests

**Implementation Steps**:
1. [ ] Create GistManager class
2. [ ] Implement pre-compute_summaries() for documents
3. [ ] Integrate with Anthropic prompt caching
4. [ ] Implement summary reuse logic
5. [ ] Add cache invalidation on document updates
6. [ ] Write tests
7. [ ] Benchmark cost savings

**Key Metrics**:
- Cache hit rate (target: 70%+)
- Cost reduction (target: 20%+ savings)
- Latency improvement (reuse vs new summaries)

---

#### Task 1.5: Path Finding Algorithms ⭐ (1 week)
**Status**: READY TO START
**Files to Create**:
- `src/athena/graph/pathfinding.py` - Path algorithms
- `tests/unit/test_pathfinding.py` - Tests

**Implementation Steps**:
1. [ ] Implement shortest_path() (Dijkstra)
2. [ ] Implement all_paths() (DFS)
3. [ ] Implement weighted_path() (cost-aware)
4. [ ] Add path visualization
5. [ ] Write comprehensive tests
6. [ ] Add to MCP tools

**Key Metrics**:
- Shortest path accuracy
- All paths enumeration
- Query latency (<100ms target)

---

### PHASE 2: High-Impact Projects (Weeks 3-7)

#### Task 2.1: CRAG (Corrective RAG) ⭐⭐⭐ (3 weeks)
**Status**: PLANNING
**Files to Create**:
- `src/athena/rag/corrective.py` - CRAG implementation
- `src/athena/rag/web_search_tool.py` - Web search integration
- `tests/integration/test_crag.py` - Integration tests

**Implementation Steps**:
1. [ ] Create CorrectiveRAGManager class
2. [ ] Implement document relevance evaluation
3. [ ] Integrate web search fallback
4. [ ] Implement query decomposition
5. [ ] Implement knowledge refinement
6. [ ] Write integration tests
7. [ ] Benchmark fallback triggers
8. [ ] Update RAG manager to use CRAG

**Key Metrics**:
- Retrieval success rate (target: 95%+)
- Relevant document quality (human eval)
- Web search fallback trigger accuracy

---

#### Task 2.2: LLMLingua Compression ⭐⭐⭐ (3 weeks)
**Status**: PLANNING
**Files to Create**:
- `src/athena/efficiency/compression.py` - Prompt compression
- `tests/unit/test_compression.py` - Tests

**Implementation Steps**:
1. [ ] Create PromptCompressor class
2. [ ] Implement token importance scoring
3. [ ] Implement token removal strategy
4. [ ] Implement reordering for coherence
5. [ ] Add quality validation
6. [ ] Benchmark compression ratios
7. [ ] Test on real prompts
8. [ ] Integrate with context assembly

**Key Metrics**:
- Compression ratio (target: 20x)
- Quality preservation (similarity >0.9)
- Speed (compression <1s)

---

#### Task 2.3: Call Graph Analysis ⭐⭐⭐ (2 weeks)
**Status**: PLANNING
**Files to Create**:
- `src/athena/code/call_graph.py` - Call graph builder
- `tests/unit/test_call_graph.py` - Tests

**Implementation Steps**:
1. [ ] Create CallGraphBuilder class
2. [ ] Implement AST parsing for functions
3. [ ] Implement call extraction
4. [ ] Implement graph construction
5. [ ] Add data flow analysis
6. [ ] Write tests
7. [ ] Integrate with code analyzer
8. [ ] Add MCP tools

**Key Metrics**:
- Call graph coverage (% of functions)
- Accuracy of call detection
- Graph query speed

---

#### Task 2.4: Token Budgeting ⭐⭐⭐ (2 weeks)
**Status**: PLANNING
**Files to Create**:
- `src/athena/efficiency/token_budget.py` - Token budgeting
- `tests/unit/test_token_budget.py` - Tests

**Implementation Steps**:
1. [ ] Create TokenBudgetManager class
2. [ ] Implement allocate() method
3. [ ] Implement intelligent truncation
4. [ ] Add priority-based truncation
5. [ ] Test on real prompts
6. [ ] Integrate with context assembly
7. [ ] Benchmark token efficiency
8. [ ] Add monitoring/alerts

**Key Metrics**:
- Budget adherence (100% compliance)
- Information preservation (quality metrics)
- Context efficiency (tokens used)

---

#### Task 2.5: Self-RAG ⭐⭐ (3 weeks)
**Status**: PLANNING
**Files to Create**:
- `src/athena/rag/selfrag.py` - Self-RAG implementation
- `tests/integration/test_selfrag.py` - Integration tests

**Implementation Steps**:
1. [ ] Create SelfRAGManager class
2. [ ] Implement critique token generation
3. [ ] Implement adaptive retrieval logic
4. [ ] Implement quality-based regeneration
5. [ ] Write integration tests
6. [ ] Benchmark quality improvements
7. [ ] Compare vs baseline RAG

**Key Metrics**:
- Answer quality (human eval)
- Retrieval efficiency (fewer queries)
- Hallucination reduction

---

### PHASE 3: Architectural Enhancements (Weeks 8+)

#### Task 3.1: Automated Graph Construction (NER) ⭐⭐⭐ (4 weeks)
**Status**: PLANNING
**Files to Create**:
- `src/athena/graph/ner_pipeline.py` - NER pipeline
- `src/athena/graph/relation_extraction.py` - Relation extraction
- `tests/integration/test_graph_construction.py` - Tests

**Implementation Steps**:
1. [ ] Implement NER (named entity recognition)
2. [ ] Implement coreference resolution
3. [ ] Implement relation extraction
4. [ ] Create graph from extracted entities
5. [ ] Write integration tests
6. [ ] Test on various document types
7. [ ] Optimize for quality/speed tradeoff

**Key Metrics**:
- Entity extraction accuracy (precision/recall)
- Relation extraction accuracy
- Graph quality (metrics TBD)

---

#### Task 3.2: ReAct Loop ⭐⭐⭐ (4 weeks)
**Status**: PLANNING
**Files to Create**:
- `src/athena/agents/react_agent.py` - ReAct implementation
- `tests/integration/test_react_agent.py` - Integration tests

**Implementation Steps**:
1. [ ] Create ReActAgent class
2. [ ] Implement reason() step
3. [ ] Implement act() step
4. [ ] Implement observe() step
5. [ ] Implement learning from observations
6. [ ] Test on multi-step tasks
7. [ ] Benchmark task completion rates

**Key Metrics**:
- Task completion rate
- Number of steps to solution
- Error recovery capability

---

## 🚀 EXECUTION CHECKLIST

### Week 1-2: GraphRAG Quick Wins
- [ ] GraphRAG implementation (1 week)
- [ ] Git-aware context (3 days)
- [ ] Community summarization (3 days)
- [ ] Path finding algorithms (1 week)
- [ ] Tests passing (100%)
- [ ] Documentation complete

### Week 3: Gisting + Initial CRAG
- [ ] Gisting implementation (1 week)
- [ ] CRAG infrastructure (1 week start)

### Week 4-6: CRAG + Compression
- [ ] CRAG completion (2 more weeks)
- [ ] LLMLingua compression (3 weeks)
- [ ] Tests and benchmarks

### Week 7-8: Code Analysis
- [ ] Call graph analysis (2 weeks)

### Week 9-10: Token Budgeting
- [ ] Token budgeting system (2 weeks)

### Week 11+: Self-RAG + Advanced
- [ ] Self-RAG (3 weeks)
- [ ] NER pipeline (4 weeks)
- [ ] ReAct loop (4 weeks)

---

## 📊 SUCCESS CRITERIA

### Per-Task Checklist

**GraphRAG**:
- [ ] All tests pass
- [ ] Global search works on real graphs
- [ ] Local search returns relevant entities
- [ ] Community summaries are coherent
- [ ] Performance: <500ms queries
- [ ] Documentation complete

**CRAG**:
- [ ] Relevance evaluation accurate
- [ ] Web fallback triggers correctly
- [ ] Query decomposition produces good sub-queries
- [ ] Knowledge refinement works
- [ ] All tests pass
- [ ] Benchmark vs baseline RAG

**Compression**:
- [ ] 20x compression achieved
- [ ] Quality preserved (>0.9 similarity)
- [ ] Speed acceptable (<1s)
- [ ] Works on various prompt types
- [ ] All tests pass

**Code Analysis**:
- [ ] Call graph covers 90%+ of functions
- [ ] Accuracy validated manually
- [ ] Data flow analysis working
- [ ] Query performance acceptable
- [ ] All tests pass

---

## 🎯 NEXT IMMEDIATE ACTIONS

1. **Start Task 1.1 (GraphRAG)** 
   - Create `src/athena/rag/graphrag.py`
   - Write unit tests
   - Implement community summarization
   - Test on existing graph

2. **Start Task 1.2 (Git Context)**
   - Create `src/athena/code/git_context.py`
   - Integrate with code analyzer
   - Test on real repos

3. **Start Task 1.5 (Path Finding)**
   - Create `src/athena/graph/pathfinding.py`
   - Implement Dijkstra
   - Write comprehensive tests

---

**Plan Generated**: 2025-11-06
**Target Completion**: Q1 2026 (16 weeks for top 10 tasks)
**Status**: Ready for execution

