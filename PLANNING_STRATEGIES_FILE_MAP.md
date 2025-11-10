# Planning Strategies - Complete File Reference Map

## Strategy 1: Reproduce and Document (Diagnostics)
**Status**: 70% Complete
**Key Concept**: Use diagnostics, bug analysis, and production logs to understand problems

### Implemented Components
```
✅ Code Analysis Memory
   - src/athena/code_search/code_analysis_memory.py
   - src/athena/mcp/handlers_code_analysis.py
   Tracks: Analysis results, code quality findings, metrics

✅ Git History Integration
   - src/athena/code/git_analyzer.py
   - src/athena/code/git_context.py
   Tests: tests/unit/test_git_analyzer.py, test_git_context.py
   Tracks: Changed files, diffs, commit history

✅ Execution Analytics
   - src/athena/execution/models.py
   - src/athena/execution/replanning.py
   Tracks: Plan execution, task failures, assumption violations
```

### Missing Components
```
❌ Production Log Analysis
   - No log parsing/analysis system
   - No log aggregation/correlation

❌ Root Cause Analysis Engine
   - No automatic error categorization
   - No correlation analysis for bugs

❌ Diagnostic Dashboards
   - No visualization of diagnostic data
   - No summary reports
```

---

## Strategy 2: Ground in Best Practices (Web Research)
**Status**: 50% Complete (but using MOCK DATA!)
**Key Concept**: Use web research to find and apply proven patterns

### Implemented Components
```
✅ Research Agents Framework
   - src/athena/research/agents.py
   Classes: ResearchAgent, ArxivResearcher, GitHubResearcher, StackOverflowResearcher
   Features: Multi-source research, credibility tracking
   
⚠️ WARNING: Uses MOCK/HARDCODED data - not real web search!
   Comment in code: "In production, would use: arxiv API, WebFetch to arxiv.org, or WebSearch"

✅ Research Executor
   - src/athena/research/executor.py
   Features: Multi-agent orchestration, result aggregation, caching
   
   - src/athena/research/cache.py
   Features: LRU caching for research results
   
   - src/athena/research/rate_limit.py
   Features: Rate limiting for external APIs
   
   - src/athena/research/memory_integration.py
   Features: Integration with semantic memory
   
   - src/athena/research/store.py
   Features: Research result persistence

✅ External Knowledge
   - src/athena/external/conceptnet_api.py
   Features: ConceptNet API integration, relation lookup
   
   - src/athena/mcp/handlers_external_knowledge.py
   MCP Tool: /lookup_external_knowledge
   Features: Semantic relation discovery
```

### Missing Components
```
❌ Real Web Search Integration
   - No WebSearch API calls
   - No live best practice lookup
   - Research agents return mock data

❌ Library Documentation Fetching
   - No PyPI documentation retrieval
   - No npm documentation fetching
   - No Maven central docs lookup

❌ Pattern Recommendation Engine
   - No pattern suggestions from research

❌ Best Practice Scoring
   - No quality metrics for discovered patterns

❌ Curation & Ranking
   - Results lack expert prioritization
```

### MCP Tools (Currently Returning Mock Data)
```
/lookup_external_knowledge
  - Looks up semantic relations for concepts
  - Uses ConceptNet (works) but research agents don't use real APIs
```

---

## Strategy 3: Ground in Your Codebase (Pattern Detection)
**Status**: 85% Complete
**Key Concept**: Detect existing patterns to avoid duplication

### Implemented Components
```
✅ Code Pattern Detection
   - src/athena/code_search/code_procedural_patterns.py
   Classes: PatternType, PatternCategory, CodePattern
   Features: Design patterns, architectural patterns, idioms, anti-patterns

✅ Duplication Analysis
   - src/athena/symbols/duplication_analyzer.py
   Classes: DuplicationAnalyzer, DuplicationPair, DuplicationMetrics, CloneType
   Features: Exact duplication, fuzzy matching (0.0-1.0), clone classification
   
✅ Pattern Matching
   - src/athena/procedural/pattern_matcher.py
   Classes: PatternMatcher, MatchResult
   Features: Refactoring suggestions, bug-fix patterns, code smell detection
   Tests: tests/unit/test_pattern_system.py

✅ Code Search Integration
   - src/athena/code_search/advanced_rag.py
   Features: Code symbol indexing, dependency analysis
   
   - src/athena/code_search/code_graph_integration.py
   Classes: CodeGraphBuilder, CodeEntity, CodeRelationType
   Features: Dependency relationships, code structure

✅ Procedural Learning
   - src/athena/procedural/extraction.py
   Function: extract_procedures_from_patterns()
   Database: Currently 101 extracted procedures
   Features: Learn reusable workflows, frequency-based extraction
   Tests: tests/unit/test_procedural_extraction.py
   
   - src/athena/procedural/models.py
   Classes: Procedure, ProcedureCategory

✅ Pattern Suggestion
   - src/athena/procedural/pattern_suggester.py
   Features: Suggest applicable patterns for tasks
```

### Missing Components
```
⚠️ Incremental Pattern Updates
   - Patterns not automatically updated as codebase changes
   - Requires manual re-extraction

⚠️ Cross-File Dependency Analysis
   - Limited cross-module pattern detection
   - Doesn't track patterns across file boundaries

⚠️ API Change Detection
   - No tracking of breaking changes in codebase patterns
```

### Database Models
```
Stored in SQLite:
- Procedure: id, name, category, description, steps, effectiveness
- CodePattern: pattern_type, category, indicators, examples
- DuplicationMetrics: total_symbols, duplication_percentage, pairs
```

---

## Strategy 4: Ground in Your Libraries (Dependency Analysis)
**Status**: 20% Complete
**Key Concept**: Understand library constraints and find alternatives

### Implemented Components
```
✅ Code Graph Integration
   - src/athena/code_search/code_graph_integration.py
   Classes: CodeGraphBuilder, CodeEntity, CodeRelationType
   Features: Basic dependency relationships
   
✅ Symbol Analysis
   - src/athena/symbols/code_quality_scorer.py
   - src/athena/symbols/performance_analyzer.py
   - src/athena/symbols/pattern_detector.py
```

### Missing Components (Critical!)
```
❌ Library Documentation Retrieval
   - No system to fetch library docs
   - No PyPI/npm/Maven documentation integration

❌ Dependency Version Analysis
   - No tracking of library versions
   - No compatibility matrix checking
   - No semantic versioning interpretation

❌ Breaking Change Detection
   - No detection when library APIs change
   - No changelog parsing

❌ Vulnerability Scanning
   - No security advisory lookup
   - No CVE checking

❌ Alternative Library Suggestions
   - No recommendation system for alternatives
   - No compatibility scoring between alternatives
```

### What Needs to Be Created
```
Proposed: src/athena/library_analysis/
  - dependency_analyzer.py
    Classes: DependencyAnalyzer, VersionConstraint, CompatibilityAnalysis
    
  - documentation_fetcher.py
    Classes: LibraryDocFetcher, DocCache
    Features: PyPI, npm, Maven documentation retrieval
    
  - vulnerability_scanner.py
    Classes: VulnerabilityScanner, SecurityAdvisory
    Features: CVE checking, security alerts
    
  - alternative_suggester.py
    Classes: AlternativeAnalyzer, LibraryAlternative
    Features: Find and recommend alternatives
```

---

## Strategy 5: Study Git History (Commit Analysis)
**Status**: 80% Complete
**Key Concept**: Learn from past decisions and commit patterns

### Implemented Components
```
✅ Git Analyzer
   - src/athena/code/git_analyzer.py
   Classes: GitAwareAnalyzer
   Functions: analyze_changes(), get_prioritized_context()
   Tests: tests/unit/test_git_analyzer.py
   Features: Changed file analysis, prioritized context
   
✅ Git Context
   - src/athena/code/git_context.py
   Classes: GitContext, FileChange, FileDiff
   Functions: get_changed_files(), get_file_diff(), get_commit_history()
   Tests: tests/unit/test_git_context.py
   Features: File diffs, commit history, blame information
   
✅ Git Models
   - src/athena/temporal/git_models.py
   - src/athena/temporal/git_store.py
   - src/athena/temporal/git_retrieval.py
   Features: Git data persistence and retrieval
   
✅ Git MCP Tools
   - src/athena/mcp/git_tools.py
   MCP-accessible git operations
```

### Missing Components
```
⚠️ Commit Pattern Learning
   - No extraction of successful commit patterns
   - No learning from commit frequency or style

⚠️ Decision Rationale Extraction
   - No extraction of decision reasoning from commit messages
   - No connection between commits and decisions

⚠️ Historical Decision Replay
   - No ability to understand why past decisions were made
   - No decision history context

⚠️ Regression Detection
   - No tracking of when bugs were introduced
   - No correlation between commits and issues
```

### Git Operations Available
```
get_changed_files(since_ref) -> List[FileChange]
get_file_diff(filepath, from_ref, to_ref) -> FileDiff
get_commit_history(filepath, limit) -> List[Commit]
get_file_blame(filepath) -> List[BlameLine]
```

---

## Strategy 6: Vibe Prototype for Clarity (Throwaway Prototypes)
**Status**: 0% Complete
**Key Concept**: Create throwaway prototypes to validate approach before full implementation

### Currently Exists (But Not For This Purpose)
```
⚠️ Lightweight Planning
   - src/athena/planning/lightweight_planning.py
   - Purpose: Resource-constrained environments, NOT prototyping
   - Different use case: execution strategy selection
```

### What's Completely Missing
```
❌ Prototype Generation
   - No system to generate prototype implementations
   - No scaffolding tools

❌ Mock Implementation Creation
   - No system to create mock versions quickly
   - No stub generation

❌ Prototype Executor
   - Can't run throwaway prototypes to validate approach
   - No execution framework

❌ Feedback Capture System
   - No system to capture learnings from prototypes
   - No feedback integration with planning

❌ Prototype Templates
   - No reusable prototype patterns
   - No quick-start templates
```

### What Needs to Be Created
```
Proposed: src/athena/prototyping/
  - prototype_generator.py
    Classes: PrototypeGenerator, PrototypeTemplate
    Features: Generate lightweight implementations
    
  - prototype_executor.py
    Classes: PrototypeExecutor, ExecutionResult
    Features: Run prototypes, capture output
    
  - feedback_capture.py
    Classes: FeedbackCollector, PrototypeLearning
    Features: Collect insights from prototypes
    
  - templates.py
    Classes: PrototypeTemplate, TemplateLibrary
    Features: Reusable prototype patterns
```

---

## Strategy 7: Synthesize with Options (Multiple Solutions)
**Status**: 80% Complete
**Key Concept**: Generate multiple solution approaches with tradeoff analysis

### Implemented Components
```
✅ Alternative Plan Generation
   - src/athena/planning/llm_validation.py
   Classes: LLMPlanValidator, EnhancedPlanValidationResult, PlanValidationInsight
   Methods: generate_alternative_plans()
   Features: Generate 3+ alternative approaches
   
✅ Replanning with Options
   - src/athena/execution/replanning.py
   Classes: AdaptiveReplanningEngine, ReplanningOption, ReplanningEvaluation
   Methods: evaluate_replanning_need(), generate_options()
   Features: Multiple replanning strategies (NONE, LOCAL, SEGMENT, FULL, ABORT)
   
✅ Scenario Simulation
   - src/athena/planning/formal_verification.py
   Classes: PlanSimulator, SimulationScenario, SimulationResult
   Methods: simulate()
   Features: Test across 5 scenarios (nominal, 20% time pressure, 50% time pressure, etc.)
   Tests: tests/integration/test_phase6_orchestrator.py
   
✅ Decision Tracking
   - src/athena/planning/postgres_planning_integration.py
   Classes: PlanningDecision
   Features: Store alternatives with context, track decision rationale
```

### MCP Tools
```
/plan_task - Generate initial plan
/validate_plan_comprehensive - Validate and get alternatives
/simulate_plan_scenarios - Run 5-scenario simulation
/trigger_adaptive_replanning - Evaluate replanning options
```

### Missing Components
```
⚠️ Tradeoff Visualization
   - No clear presentation of option tradeoffs
   - No comparison matrices

⚠️ Option Ranking
   - Options not ranked by quality/suitability
   - No scoring system for options

⚠️ Cost-Benefit Analysis
   - Limited automatic cost/benefit comparison
   - No ROI calculation for options

⚠️ User Guidance
   - No system to help users choose between options
   - No recommendation system
```

---

## Strategy 8: Review with Style Agents (Specialized Reviewers)
**Status**: 0% Complete
**Key Concept**: Get specialized expert review from multiple perspectives

### Currently Exists (Generic Only)
```
⚠️ Generic Verification Gates
   - src/athena/verification/gateway.py
   Classes: VerificationGateway
   Features: Generic operation verification, quality gates
   But: Not specialized by style/domain
   
⚠️ Agentic Handlers
   - src/athena/mcp/handlers_agentic.py
   Features: Generic verification, health checks, recommendations
   But: Not specialized review agents
```

### What's Completely Missing
```
❌ Code Style Reviewer Agent
   - No linting/style enforcement agent
   - No idiom checking

❌ Architecture Reviewer Agent
   - No architectural pattern review
   - No design review agent

❌ Performance Reviewer Agent
   - No performance and efficiency review
   - No optimization suggestions

❌ Security Reviewer Agent
   - No security-focused review
   - No vulnerability pattern detection

❌ Documentation Reviewer Agent
   - No documentation quality review
   - No completeness checking

❌ Testability Reviewer Agent
   - No test coverage review
   - No testability assessment
```

### What Needs to Be Created
```
Proposed: src/athena/review_agents/
  - style_reviewer.py
    Classes: StyleReviewer
    Features: Code style, idioms, conventions
    
  - architecture_reviewer.py
    Classes: ArchitectureReviewer
    Features: Design patterns, architectural structure
    
  - performance_reviewer.py
    Classes: PerformanceReviewer
    Features: Efficiency, optimization opportunities
    
  - security_reviewer.py
    Classes: SecurityReviewer
    Features: Security vulnerabilities, best practices
    
  - documentation_reviewer.py
    Classes: DocumentationReviewer
    Features: Doc completeness, clarity
    
  - testability_reviewer.py
    Classes: TestabilityReviewer
    Features: Test coverage, test quality
    
  - review_coordinator.py
    Classes: ReviewCoordinator
    Features: Run all reviewers, aggregate feedback
```

---

## Cross-Cutting Components

### Memory Integration (Used by All Strategies)
```
- src/athena/manager.py
  Main entry point for all memory operations
  
- src/athena/core/database.py
  SQLite database abstraction
  
- src/athena/memory/store.py
  Semantic memory storage
  
- src/athena/episodic/store.py
  Episodic event storage
```

### MCP Handlers (Strategy Exposure)
```
- src/athena/mcp/handlers.py
  Main MCP handler registry

- src/athena/mcp/handlers_planning.py
  Planning-specific MCP tools
  
- src/athena/mcp/handlers_code_analysis.py
  Code analysis MCP tools
  
- src/athena/mcp/handlers_external_knowledge.py
  External knowledge MCP tools
  
- src/athena/mcp/handlers_agentic.py
  Agentic verification MCP tools
```

### RAG Integration (Used by Strategies 2, 3, 4)
```
- src/athena/rag/manager.py
  RAG orchestration
  
- src/athena/rag/planning_rag.py
  Planning-aware RAG
  
- src/athena/rag/hyde.py
  HyDE retrieval strategy
  
- src/athena/rag/reranker.py
  LLM reranking
  
- src/athena/rag/reflective.py
  Reflective RAG
```

---

## Summary: Quick File Location Guide

### For Strategy 1 (Diagnostics)
Start with: `src/athena/code/git_analyzer.py`
Then: `src/athena/execution/models.py`
TODO: Create `src/athena/diagnostics/`

### For Strategy 2 (Web Research)
Start with: `src/athena/research/agents.py` (but has MOCK DATA)
Then: Upgrade to use real WebSearch APIs
TODO: Add library docs fetching

### For Strategy 3 (Codebase Patterns)
Start with: `src/athena/procedural/extraction.py`
Then: `src/athena/symbols/duplication_analyzer.py`
Status: 85% complete - mostly done!

### For Strategy 4 (Library Analysis)
Start with: `src/athena/code_search/code_graph_integration.py`
Status: 20% complete - mostly missing!
TODO: Create `src/athena/library_analysis/`

### For Strategy 5 (Git History)
Start with: `src/athena/code/git_analyzer.py`
Then: `src/athena/code/git_context.py`
Status: 80% complete - mostly done!

### For Strategy 6 (Prototyping)
Status: 0% complete - completely missing!
TODO: Create `src/athena/prototyping/`

### For Strategy 7 (Options Synthesis)
Start with: `src/athena/planning/llm_validation.py`
Then: `src/athena/execution/replanning.py`
Status: 80% complete - mostly done!

### For Strategy 8 (Review Agents)
Status: 0% complete - completely missing!
TODO: Create `src/athena/review_agents/`

---

## Database Schema Locations

```
- src/athena/code_search/code_analysis_memory.py - Code analysis tables
- src/athena/procedural/store.py - Procedure tables
- src/athena/temporal/git_store.py - Git history tables
- src/athena/planning/store.py - Planning decision tables
- src/athena/execution/models.py - Execution tracking tables
```

---

## Testing File Locations

```
✅ tests/unit/test_git_analyzer.py
✅ tests/unit/test_git_context.py
✅ tests/unit/test_procedural_extraction.py
✅ tests/unit/test_pattern_system.py
✅ tests/integration/test_phase6_orchestrator.py (Scenario simulation)

❌ tests/unit/test_research_agents.py (doesn't exist - NEEDS TESTS!)
❌ tests/unit/test_library_analyzer.py (doesn't exist - feature missing)
❌ tests/unit/test_prototype_generator.py (doesn't exist - feature missing)
❌ tests/unit/test_review_agents.py (doesn't exist - feature missing)
```
