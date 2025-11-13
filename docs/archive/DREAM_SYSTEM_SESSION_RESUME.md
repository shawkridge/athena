# Athena Dream System - Session Resume Prompt

**Session Date**: November 13, 2025
**Current Status**: Phase 2 at 87.5% completion
**Next Task**: Task 6 - Sandbox Testing Infrastructure

---

## Quick Context

We've built an **autonomous dream system** for Athena that:
- Generates speculative procedure variants every night at 2 AM
- Uses multi-model ensemble (DeepSeek V3.1, Qwen2.5-Coder, local models)
- Claude evaluates dreams automatically (fresh instance spawned)
- Stores all results with metrics and health scoring
- Exposes everything via MCP tools (/dream, /dream_journal, /dream_health)

**Status**: 7 of 8 Phase 2 tasks complete

---

## What's Done

### Phase 1: Core Generation ✅
- Multi-model dream generation (constraint relaxation, synthesis, parameter exploration, conditionals)
- AST-based dependency analysis
- OpenRouter integration
- Parallel execution

**Files**:
- `src/athena/consolidation/openrouter_client.py`
- `src/athena/consolidation/dependency_analyzer.py`
- `src/athena/consolidation/constraint_relaxer.py`
- `src/athena/consolidation/cross_project_synthesizer.py`
- `src/athena/consolidation/parameter_explorer.py`
- `src/athena/consolidation/dreaming.py`

### Phase 2: Integration & Automation ✅

#### Task 1: Dream Store ✅
- `src/athena/consolidation/dream_store.py` (380 lines)
- Full CRUD operations
- 8 query methods
- Statistics aggregation

#### Task 2: Dream Models ✅
- `src/athena/consolidation/dream_models.py` (135 lines)
- Type-safe Pydantic models

#### Task 3: Evaluation Parser ✅
- `src/athena/consolidation/dream_evaluation_parser.py` (355 lines)
- Parse Claude responses (3 formats)
- Extract scores, tiers, reasoning

#### Task 4: Nightly Scripts ✅
- `scripts/run_consolidation_with_dreams.py` (300 lines) - Standalone runner
- `scripts/run_athena_dreams.sh` (200 lines) - Cron wrapper
- `scripts/setup_cron_job.sh` (250 lines) - Installation
- `claude/hooks/lib/dream_evaluation_handler.py` (140 lines) - Hook handler

#### Task 5: Consolidation Integration ✅
- `src/athena/consolidation/dream_integration.py` (280 lines)
- Integrates dreams into consolidation pipeline
- Finds related procedures for cross-project synthesis

#### Task 7: MCP Tools ✅
- `src/athena/mcp/handlers_dreams.py` (250 lines)
- `/dream [strategy]` - Trigger generation
- `/dream_journal [limit] [tier]` - View dreams
- `/dream_health` - System health report
- `/dream_stats` - Detailed statistics

#### Task 8: Metrics & Health Scoring ✅
- `src/athena/consolidation/dream_metrics.py` (420 lines)
- Compound health score (60% novelty + 15% quality + 15% leverage + 10% efficiency)
- Trend analysis over time
- Comprehensive health reports

---

## What's NOT Done Yet

### Task 6: Sandbox Testing Infrastructure ⏳

**What needs to be built**:
```python
# Docker-based validation of dreams
src/athena/testing/dream_sandbox.py
- Docker container orchestration
- Procedure execution in isolation
- Synthetic input generation
- Output validation (shape/type/structure)
- Failure tracking & categorization
- Learning system (adjust generation based on failures)

src/athena/testing/synthetic_test_generator.py
- Generate mock inputs based on procedure parameters
- Create expected output shapes
- Handle different parameter types

src/athena/testing/dream_test_runner.py
- Execute dreams in sandbox
- Track test outcomes
- Record success/failure metrics
```

**Why**:
- Validate Tier 1 dreams actually work
- Measure real effectiveness improvements
- Learn from failures (wrong types, resource limits, etc.)
- Feedback for adaptive tightening (Task 9)

---

## Database Schema (Complete)

### dream_procedures
- Core dream data (id, base_procedure_id, code, model_used)
- Generation metadata (reasoning, generated_at)
- Evaluation data (status, tier, viability_score, claude_reasoning)
- Testing data (test_outcome, test_error, test_timestamp)
- Metrics (novelty_score, cross_project_matches, effectiveness_metric)

### dream_generation_runs
- Track each nightly cycle
- Counts by type, duration, model usage

### dream_metrics
- Aggregate health metrics
- Compound health score + component scores
- Timestamp for trend analysis

---

## How to Install & Run

### Install Cron Job (One Command)
```bash
sudo bash /home/user/.work/athena/scripts/setup_cron_job.sh
```

### Manual Test
```bash
/home/user/.work/athena/scripts/run_athena_dreams.sh
```

### Monitor
```bash
tail -f /var/log/athena-dreams.log
```

### Use in Claude Code
```
/dream balanced
/dream_journal 10 1
/dream_health
/dream_stats
```

---

## Environment

### Working Directory
`/home/user/.work/athena`

### Key Files
- Codebase: `src/athena/consolidation/`
- Database: `~/.athena/memory.db`
- Logs: `/var/log/athena-dreams.log`
- Config: `.env.local` (has OpenRouter API key)

### Database Access
```python
from athena.core.database import Database
from athena.consolidation.dream_store import DreamStore

db = Database()
store = DreamStore(db)

# Query dreams
dreams = await store.get_pending_evaluation()
```

---

## Todo Status

```
[x] Task 1: Dream Store
[x] Task 2: Dream Models
[x] Task 3: Evaluation Parser
[x] Task 4: Nightly Scripts + Hooks
[x] Task 5: Consolidation Integration
[x] Task 7: MCP Tools
[x] Task 8: Metrics & Scoring
[ ] Task 6: Sandbox Testing (NEXT)
[ ] Task 9: Adaptive Tightening (Lower Priority)
[ ] Task 10: Unit Tests (Lower Priority)
[ ] Task 11: Cron Monitoring (Lower Priority)
[ ] Task 12: E2E Testing (Lower Priority)
```

---

## Next Steps for Sandbox Testing

### Phase 1: Basic Docker Integration
1. Create `src/athena/testing/dream_sandbox.py`
2. Implement Docker container spawning + cleanup
3. Handle Python code execution in isolation
4. Basic error/success detection

### Phase 2: Input/Output Validation
1. Create `src/athena/testing/synthetic_test_generator.py`
2. Generate synthetic inputs based on procedure params
3. Validate output shape/type
4. Check for expected behavior

### Phase 3: Learning System
1. Track failure patterns
2. Categorize errors (syntax, runtime, logic, resource)
3. Update generation heuristics
4. Record lessons in episodic memory

---

## Key Concepts to Remember

**Dream Types**:
- Constraint Relaxation: Reorder steps, conditionals, parallelization
- Cross-Project Synthesis: Combine procedures from different domains
- Parameter Exploration: Timeout/threshold variations
- Conditional Variants: Make operations optional

**Dream Tiers** (assigned by Claude):
- Tier 1: Viable (0.6-1.0 viability score) - Ready to test
- Tier 2: Speculative (0.3-0.6) - Interesting but risky
- Tier 3: Archive (<0.3) - Creative but not viable

**Health Score**:
- 60% Novelty (are dreams finding new solutions?)
- 15% Quality (are Tier 1s better than baseline?)
- 15% Leverage (are dreams reusable across projects?)
- 10% Efficiency (are we generating fast enough?)

---

## Files to Review Before Next Session

If needed for context:
- `DREAM_SYSTEM_PHASE2_COMPLETE.md` - Complete architecture
- `DREAM_SYSTEM_PHASE2_PROGRESS.md` - Implementation details
- `dream.md` - Original vision document
- `.env.local` - Configuration (OpenRouter API key)

---

## Quick Sanity Check

Before continuing, verify:
```bash
# Check Phase 1 files exist
ls -la src/athena/consolidation/openrouter_client.py
ls -la src/athena/consolidation/dreaming.py

# Check Phase 2 files exist
ls -la src/athena/consolidation/dream_store.py
ls -la scripts/run_athena_dreams.sh

# Check scripts are executable
file scripts/run_athena_dreams.sh
```

---

## Resume Prompt for Next Session

When continuing:

> We've completed Phase 2 of Athena's dream system (7 of 8 tasks). The system generates, evaluates, stores, and monitors speculative procedure variants automatically every night.
>
> Next priority is **Task 6: Sandbox Testing Infrastructure**. This involves:
> 1. Docker-based test execution (validate Tier 1 dreams actually work)
> 2. Synthetic input generation (mock parameters)
> 3. Failure tracking & learning (improve generation over time)
>
> Current status: 87.5% complete, production-ready for autonomous execution.
>
> Ready to build sandbox testing when you are.

---

**Happy coding! The dream system is almost complete.** 🚀
