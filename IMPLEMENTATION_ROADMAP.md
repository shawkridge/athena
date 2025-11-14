# Athena Memory System - Implementation Roadmap
## Strategic Plan to Complete Remaining 10-15%

**Status:** 85-90% Complete → Target: 100% in 6-8 weeks
**Last Updated:** November 14, 2025

---

## Phase Summary

| Phase | Duration | Priority | Outcome |
|-------|----------|----------|---------|
| **Phase 0** | Week 1 | 🔴 Critical | Fix async/await bugs, replace mock data |
| **Phase 1** | Week 2-3 | 🔴 High | GitHub integration, exception logging |
| **Phase 2** | Week 4-5 | 🟠 Medium | Tool migration completion, Slack source |
| **Phase 3** | Week 6-7 | 🟠 Medium | Research APIs, formal verification |
| **Phase 4** | Week 8+ | 🟡 Low | Type annotations, cleanup |

---

## Phase 0: Critical Fixes (Week 1) 🔴

### Goal: Eliminate Runtime Errors & False Data

### Task 0.1: Fix Async/Await Pattern Issues

**What:** 27 files with missing `await` keywords
**Why:** Coroutines returned instead of results; runtime errors possible

**Files to Fix:**
```
tier1_bridge.py:180-200
learning/git_analyzer.py:305-315
skills/executor.py:110-120
(27 files total)
```

**Process:**
1. Grep all `async def` functions
2. Verify all calls to async functions have `await`
3. Run `pytest tests/` with async timeout detection
4. Commit: "fix: Add missing await keywords in async functions"

**Effort:** 2-3 days
**Risk:** LOW (pure bug fix)

**Verification:**
```bash
# Find potential missing awaits
grep -r "async def" src/ | wc -l  # Should see 179
grep -r "await " src/ | wc -l     # Should be ~150
# Difference means potential missing awaits

# Run tests
pytest tests/ -v --tb=short
```

---

### Task 0.2: Replace Mock Data in MCP Handlers

**What:** 3 MCP tools return hardcoded data instead of querying database
**Why:** Dashboard and monitoring show incorrect/missing data

**Files:**
- `src/athena/mcp/handlers_system.py`
  - `_handle_get_project_stats()` (line 798)
  - `_handle_get_hook_executions()` (line 850)
  - `_handle_get_consolidation_history()` (line 740)

**Changes Required:**

```python
# BEFORE (handlers_system.py:798)
async def _handle_get_project_stats(self, args: dict):
    stats = {
        "total_projects": 1,  # ← Hardcoded
        "active_projects": 1,
        "total_memories": 0,
    }
    return stats

# AFTER
async def _handle_get_project_stats(self, args: dict):
    project_id = args.get("project_id")

    async with self.db.get_connection() as conn:
        # Query actual event count
        event_count = await conn.fetchval(
            "SELECT COUNT(*) FROM episodic_events WHERE project_id = $1",
            project_id
        )

        # Query actual procedure count
        proc_count = await conn.fetchval(
            "SELECT COUNT(*) FROM procedural_skills WHERE project_id = $1",
            project_id
        )

        # Query actual consolidation runs
        consolidation_count = await conn.fetchval(
            "SELECT COUNT(*) FROM consolidation_runs WHERE project_id = $1",
            project_id
        )

    return {
        "total_projects": 1,
        "active_projects": 1,
        "total_memories": event_count,
        "total_procedures": proc_count,
        "consolidation_runs": consolidation_count,
        "memory_health": {
            "quality_score": 0.85,
            "coverage_percent": 75.0,
            "deduplication_percent": 12.0
        }
    }
```

**Effort:** 1-2 days
**Risk:** LOW (local changes)

**Verification:**
```bash
# Verify database tables exist
psql -h localhost -U postgres -d athena -c "\dt"

# Test endpoint
curl -X POST http://localhost:8000/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_project_stats", "args": {"project_id": 1}}'
```

---

### Task 0.3: Add Logging to Silent Exception Handlers

**What:** 30+ `except: pass` blocks without logging
**Why:** Silent failures hide bugs, make debugging impossible

**Pattern:**
```python
# BEFORE
try:
    cursor.execute("INSERT INTO ...")
except psycopg.errors.UniqueViolationError:
    pass  # ← What happened?

# AFTER
try:
    cursor.execute("INSERT INTO ...")
except psycopg.errors.UniqueViolationError:
    logger.debug(f"Duplicate memory entry: {memory_id} (expected)")
except Exception as e:
    logger.error(f"Unexpected database error: {e}")
    raise
```

**Priority Fixes:**
1. `working_memory/capacity_enforcer.py:100` - Schema creation
2. `learning/git_analyzer.py:309` - Git stat parsing
3. `consolidation/system.py:513` - Insert duplicates
4. `tier1_bridge.py:251, 319` - Salience calculation
5. `episodic/pipeline.py:390` - Comment says "will be updated"

**Effort:** 1-2 days
**Risk:** NONE (observability only)

---

## Phase 0 Completion Criteria

✅ **All async functions properly await**
✅ **MCP tools query real database data**
✅ **No silent exceptions; all logged**
✅ **Test suite passes (94/94)**
✅ **Commit: "fix: Phase 0 critical issues"**

---

## Phase 1: External Integrations (Week 2-3) 🔴

### Goal: Enable Automatic Development Activity Capture

### Task 1.1: Implement GitHub Event Source

**What:** Capture commits, PRs, issues, code reviews from GitHub

**File to Create:** `src/athena/episodic/sources/github.py`

```python
from typing import AsyncGenerator, Dict, Any
from .._base import BaseEventSource
from ...core.models import EpisodicEvent, EventType, EventOutcome
import httpx

class GitHubEventSource(BaseEventSource):
    """Capture development events from GitHub repositories."""

    def __init__(self, source_id: str, token: str, repos: List[str]):
        super().__init__(
            source_id=source_id,
            source_type='github',
            source_name=f'GitHub: {", ".join(repos)}'
        )
        self.token = token
        self.repos = repos
        self.client = None

    @classmethod
    async def create(cls, credentials: Dict[str, Any],
                     config: Dict[str, Any]) -> "GitHubEventSource":
        """Factory method.

        credentials: {"token": "ghp_xxx"}
        config: {"repos": ["owner/repo1", "owner/repo2"]}
        """
        source = cls(
            source_id=f"github_{config.get('repos')[0]}",
            token=credentials["token"],
            repos=config.get("repos", [])
        )
        source.client = httpx.AsyncClient(
            headers={"Authorization": f"token {source.token}"}
        )
        return source

    async def generate_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Stream events from GitHub."""
        for repo in self.repos:
            # Get commits
            async for event in self._stream_commits(repo):
                yield event

            # Get PR events
            async for event in self._stream_prs(repo):
                yield event

            # Get issue events
            async for event in self._stream_issues(repo):
                yield event

    async def _stream_commits(self, repo: str) -> AsyncGenerator[EpisodicEvent, None]:
        """Stream commit events."""
        url = f"https://api.github.com/repos/{repo}/commits"
        params = {"per_page": 100}

        async with self.client.stream("GET", url, params=params) as response:
            commits = await response.json()

            for commit in commits:
                yield EpisodicEvent(
                    content=f"Commit: {commit['commit']['message']}",
                    event_type=EventType.CODE_CHANGE,
                    outcome=EventOutcome.SUCCESS,
                    context={
                        "github_id": commit["sha"],
                        "author": commit["commit"]["author"]["name"],
                        "repo": repo,
                        "url": commit["html_url"]
                    }
                )

    async def _stream_prs(self, repo: str) -> AsyncGenerator[EpisodicEvent, None]:
        """Stream pull request events."""
        url = f"https://api.github.com/repos/{repo}/pulls"
        params = {"state": "all", "per_page": 100}

        async with self.client.stream("GET", url, params=params) as response:
            prs = await response.json()

            for pr in prs:
                yield EpisodicEvent(
                    content=f"PR #{pr['number']}: {pr['title']}",
                    event_type=EventType.COLLABORATION,
                    outcome=EventOutcome.SUCCESS if pr["merged_at"] else EventOutcome.ONGOING,
                    context={
                        "github_id": pr["id"],
                        "author": pr["user"]["login"],
                        "repo": repo,
                        "url": pr["html_url"],
                        "merged": pr["merged_at"] is not None
                    }
                )

    async def _stream_issues(self, repo: str) -> AsyncGenerator[EpisodicEvent, None]:
        """Stream issue events."""
        # Similar to PRs...
        pass

    async def validate(self) -> bool:
        """Verify GitHub API access."""
        try:
            response = await self.client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {self.token}"}
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Clean up client."""
        if self.client:
            await self.client.aclose()
```

**Integration:**
1. Register in `episodic/sources/factory.py`
2. Add tests in `tests/unit/test_github_source.py`
3. Update documentation

**Effort:** 3-4 days
**Risk:** MEDIUM (external API dependency)

**Verification:**
```bash
# Test with real GitHub token
source = await GitHubEventSource.create(
    credentials={"token": "ghp_..."},
    config={"repos": ["anthropics/claude-code"]}
)

# Verify can connect
assert await source.validate()

# Stream a few events
async for event in source.generate_events():
    print(event.content)
    break  # Just test first one
```

---

### Task 1.2: Improve Exception Logging (Already in Phase 0)

**Deferred to Phase 0 if not completed.**

---

### Task 1.3: Add Consolidation Run History Table

**What:** Store consolidation execution history for analysis

**Database Schema:**
```sql
CREATE TABLE IF NOT EXISTS consolidation_runs (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    strategy TEXT NOT NULL,  -- 'balanced', 'quality', 'speed'
    patterns_extracted INT,
    quality_score FLOAT,
    error_message TEXT,
    metadata JSONB,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_consolidation_runs_project
    ON consolidation_runs(project_id, completed_at DESC);
```

**Update Consolidation Handler:**
```python
async def _handle_consolidate(self, args: dict):
    """Execute consolidation and record history."""
    project_id = args.get("project_id")
    strategy = args.get("strategy", "balanced")

    # Create run record
    async with self.db.get_connection() as conn:
        run_id = await conn.fetchval("""
            INSERT INTO consolidation_runs
                (project_id, started_at, strategy)
            VALUES ($1, NOW(), $2)
            RETURNING id
        """, project_id, strategy)

    try:
        # Execute consolidation
        result = await self.consolidator.consolidate(strategy=strategy)

        # Update run record with results
        async with self.db.get_connection() as conn:
            await conn.execute("""
                UPDATE consolidation_runs
                SET completed_at = NOW(),
                    patterns_extracted = $1,
                    quality_score = $2
                WHERE id = $3
            """, result.patterns_count, result.quality_score, run_id)

        return result

    except Exception as e:
        # Record failure
        async with self.db.get_connection() as conn:
            await conn.execute("""
                UPDATE consolidation_runs
                SET error_message = $1
                WHERE id = $2
            """, str(e), run_id)
        raise
```

**Effort:** 1-2 days
**Risk:** LOW

---

## Phase 1 Completion Criteria

✅ **GitHub source implemented and tested**
✅ **Can pull commits, PRs, issues from GitHub**
✅ **Consolidation run history recorded**
✅ **Exception logging complete**
✅ **Test suite passes**
✅ **Commit: "feat: Phase 1 external integrations"**

---

## Phase 2: Tool Architecture & Slack (Week 4-5) 🟠

### Task 2.1: Complete Tool Migration Framework

**Objective:** Move from monolithic handlers → modular filesystem-discoverable tools

**Current State:**
- handlers.py: 1,270 lines (was 12,363)
- handlers_episodic.py, handlers_procedural.py, etc. exist
- BUT: Individual tool files in `src/athena/tools/` not populated

**Target State:**
```
src/athena/tools/
├── episodic/
│   ├── __init__.py
│   ├── recall.py (executable tool)
│   ├── remember.py
│   └── forget.py
├── semantic/
│   ├── __init__.py
│   ├── search.py
│   └── hybrid_search.py
├── procedural/
│   ├── __init__.py
│   ├── execute_skill.py
│   └── extract_pattern.py
├── planning/
│   ├── plan_task.py
│   └── validate_plan.py
├── consolidation/
│   ├── consolidate.py
│   ├── get_patterns.py
│   └── get_history.py
└── __init__.py  (discovery registry)
```

**Each Tool File Pattern:**
```python
# src/athena/tools/episodic/recall.py
"""Recall memories using semantic search."""

from typing import List, Dict, Any
from athena.manager import UnifiedMemoryManager

async def recall(
    query: str,
    limit: int = 10,
    min_score: float = 0.5,
    project_id: int = 1
) -> List[Dict[str, Any]]:
    """Search and retrieve memories.

    Args:
        query: Search query
        limit: Max results
        min_score: Minimum relevance score
        project_id: Project context

    Returns:
        List of matching memories with scores
    """
    manager = UnifiedMemoryManager()
    results = await manager.recall(
        query=query,
        limit=limit,
        min_score=min_score,
        project_id=project_id
    )
    return results
```

**Discovery Registry:**
```python
# src/athena/tools/__init__.py
"""Tool discovery and loading system."""

from pathlib import Path
from typing import Dict, Callable
import importlib

TOOLS_REGISTRY: Dict[str, Callable] = {}

def discover_tools() -> Dict[str, Callable]:
    """Discover all tools in tools/ directory."""
    tools_dir = Path(__file__).parent

    for category_dir in tools_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith('_'):
            continue

        for tool_file in category_dir.glob("*.py"):
            if tool_file.name.startswith('_'):
                continue

            # Import tool
            module_name = f"athena.tools.{category_dir.name}.{tool_file.stem}"
            module = importlib.import_module(module_name)

            # Extract callable (usually first function)
            for name, obj in module.__dict__.items():
                if callable(obj) and not name.startswith('_'):
                    tool_key = f"{category_dir.name}/{tool_file.stem}"
                    TOOLS_REGISTRY[tool_key] = obj

    return TOOLS_REGISTRY

def get_tool(tool_name: str) -> Callable:
    """Get tool by name."""
    if not TOOLS_REGISTRY:
        discover_tools()
    return TOOLS_REGISTRY.get(tool_name)

# Lazy load on import
discover_tools()
```

**Agents Can Now:**
```bash
# 1. Discover tools via filesystem
ls /home/user/.work/athena/src/athena/tools/
# Output: episodic  semantic  procedural  planning  consolidation

# 2. Read tool definitions
cat /home/user/.work/athena/src/athena/tools/episodic/recall.py
# Shows: function signature, docstring, parameters

# 3. Import and execute
from athena.tools.episodic.recall import recall
results = await recall("my query")
```

**Effort:** 2-3 days
**Risk:** MEDIUM (refactoring)

---

### Task 2.2: Implement Slack Event Source

**Similar to GitHub but for Slack messages/threads**

```python
class SlackEventSource(BaseEventSource):
    """Capture messages, code, and discussions from Slack."""

    async def generate_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Stream events from Slack."""
        # Get messages from all channels
        # Track code snippets
        # Extract discussions
        # Record thread replies
```

**Effort:** 2-3 days
**Risk:** MEDIUM (external API)

---

## Phase 3: Research & Verification (Week 6-7) 🟠

### Task 3.1: Implement Real Research Agent APIs

**Connect research agents to real data sources:**

```python
class ArxivResearcher:
    async def search(self, topic: str) -> List[Dict]:
        """Search real arXiv papers using WebSearch."""
        # Use existing WebSearch MCP tool
        # Parse results into paper format
        # Return with real URLs and metadata
```

**Effort:** 2-3 days

---

### Task 3.2: Complete Formal Verification

**Implement property checkers for planning:**

```python
class FormalVerifier:
    def check_safety(self, plan: Plan) -> bool:
        """Verify no invalid state transitions."""
        # Check preconditions → postconditions chain
        pass

    def check_completeness(self, plan: Plan, goals: List[Goal]) -> bool:
        """Verify all goals achieved."""
        # Check coverage of all required goals
        pass
```

**Effort:** 2-3 weeks

---

## Phase 4: Quality Improvements (Week 8+) 🟡

### Task 4.1: Add Type Annotations

**Replace `Dict[str, Any]` with typed dataclasses**

**Effort:** 3-4 days

### Task 4.2: Sync/Async Cleanup

**Remove backward compatibility checks, go async-only**

**Effort:** 1 week

---

## Success Metrics

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| **Code Completeness** | 85% | 100% | Week 8 |
| **Async Correctness** | 95% | 100% | Week 1 |
| **Real Data Integration** | 20% | 100% | Week 4 |
| **Test Coverage** | 94/94 passing | 100/100+ | Week 6 |
| **Documentation** | 80% | 100% | Week 8 |
| **Type Safety** | 60% | 90% | Week 8 |

---

## Timeline Summary

```
Week 1:     Phase 0 - Critical Fixes (Async, Mock Data, Logging)
Week 2-3:   Phase 1 - GitHub Integration, Consolidation History
Week 4-5:   Phase 2 - Tool Migration, Slack Integration
Week 6-7:   Phase 3 - Research APIs, Formal Verification
Week 8+:    Phase 4 - Type Annotations, Cleanup

Expected: 100% Complete by End of Week 8
```

---

## Resource Allocation

**Effort Estimate:**
- Phase 0: 4-5 days (Critical)
- Phase 1: 5-6 days (High Priority)
- Phase 2: 5-6 days (Medium)
- Phase 3: 10-14 days (Medium)
- Phase 4: 10-15 days (Low)

**Total: 34-46 days of development (6-9 weeks)**

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| External API changes | Medium | High | Use stable APIs, add fallbacks |
| Database schema conflicts | Low | High | Test migrations thoroughly |
| Performance degradation | Low | Medium | Profile before/after |
| Breaking changes | Low | High | Maintain backward compatibility |

---

## Checkpoint: After Each Phase

After Phase 0: ✅ Core system stable
After Phase 1: ✅ External integrations working
After Phase 2: ✅ Tool architecture complete
After Phase 3: ✅ Advanced features ready
After Phase 4: ✅ Production-ready (100%)

---

## Deployment Strategy

### Pre-Deployment (Week 9)
- [ ] Run full test suite (target: 100+/100 tests)
- [ ] Performance benchmarks
- [ ] Security audit
- [ ] Documentation review

### Deployment (Week 9-10)
- [ ] Merge to main branch
- [ ] Tag release v1.0.0
- [ ] Update documentation
- [ ] Announce features

### Post-Deployment (Week 10+)
- [ ] Monitor for issues
- [ ] Gather user feedback
- [ ] Plan Phase 5+ features

---

**Status:** Ready to implement
**Next Action:** Start Phase 0 (critical fixes)
**Estimated Completion:** 6-8 weeks
