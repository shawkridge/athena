# Athena Usage Examples

Practical examples for using the 8-layer memory system across different scenarios.

## Table of Contents

1. [Episodic Memory Examples](#episodic-memory-examples)
2. [Semantic Memory Examples](#semantic-memory-examples)
3. [Procedural Memory Examples](#procedural-memory-examples)
4. [Prospective Memory Examples](#prospective-memory-examples)
5. [Knowledge Graph Examples](#knowledge-graph-examples)
6. [RAG Examples](#rag-examples)
7. [Planning & Verification Examples](#planning--verification-examples)
8. [Advanced Workflows](#advanced-workflows)

---

## Episodic Memory Examples

### Example 1: Record Development Events

```python
from athena.episodic.storage import EpisodicStorage
from athena.core.database import Database

db = Database("/home/user/.work/athena/memory.db")
episodic = EpisodicStorage(db)

# Record implementation work
event1 = episodic.record_event(
    content="Implemented JWT refresh token rotation mechanism",
    event_type="action",
    outcome="success",
    context={
        "file": "src/auth/tokens.py",
        "lines": [42, 89],
        "duration_minutes": 45,
        "complexity": "medium"
    }
)

# Record debugging
event2 = episodic.record_event(
    content="Fixed race condition in token validation",
    event_type="bug_fix",
    outcome="success",
    context={
        "bug_id": "BUGS-123",
        "root_cause": "Missing lock during concurrent writes",
        "severity": "high"
    }
)

# Record a failed attempt
event3 = episodic.record_event(
    content="Attempted optimization of vector search - reverted due to correctness issues",
    event_type="experiment",
    outcome="failure",
    context={
        "branch": "opt/faster-search",
        "test_failures": 3,
        "lesson": "Premature optimization without benchmarks"
    }
)

# Query recent events
recent = episodic.get_events(days=1, event_type="action")
for event in recent:
    print(f"{event.timestamp}: {event.content}")
```

### Example 2: Retrieve Events by Type

```python
# Get all errors from today
errors = episodic.get_events(days=1, event_type="error")
print(f"Today's errors: {len(errors)}")
for error in errors:
    print(f"- {error.context['error_type']}: {error.content}")

# Get high-complexity work
high_complexity = [
    e for e in episodic.get_events(days=7)
    if e.context.get('complexity') == 'high'
]
print(f"Complex tasks this week: {len(high_complexity)}")
```

---

## Semantic Memory Examples

### Example 3: Store Knowledge About Architecture

```python
from athena.semantic.search import SemanticSearch

semantic = SemanticSearch(db)

# Store architectural knowledge
mem1 = semantic.create(
    content="""
    JWT Authentication Architecture:
    - Access tokens: Short-lived (1 hour), includes user claims
    - Refresh tokens: Long-lived (7 days), used to obtain new access tokens
    - Token rotation: Invalidate old refresh token after use
    - Claims: user_id, roles, permissions, expiry
    """,
    memory_type="architecture",
    project_id=1
)

# Store best practice
mem2 = semantic.create(
    content="""
    API Rate Limiting Best Practices:
    - Per-user limits: 1000 requests/hour
    - Per-endpoint limits: 100 requests/minute for expensive operations
    - Implement exponential backoff (2s, 4s, 8s, 16s)
    - Return rate-limit headers: X-RateLimit-Remaining, X-RateLimit-Reset
    """,
    memory_type="best_practice",
    project_id=1
)

print(f"Created memories: {mem1}, {mem2}")
```

### Example 4: Search with Hybrid Strategy

```python
# Search for authentication knowledge
results = semantic.retrieve(
    "JWT token expiration and refresh mechanism",
    project_id=1,
    k=5
)

print(f"Found {len(results)} results:")
for i, result in enumerate(results, 1):
    print(f"\n{i}. Relevance: {result.similarity:.2f}")
    print(f"   Type: {result.memory.memory_type}")
    print(f"   Content: {result.memory.content[:100]}...")
```

### Example 5: Update Memory by Creating Version

```python
# Store memory version 1
mem = semantic.create(
    "Database connection pooling for PostgreSQL",
    project_id=1
)

# Later: Update with more information (creates version 2)
# This would be tracked via Zettelkasten
```

---

## Procedural Memory Examples

### Example 6: Define Reusable Procedures

```python
from athena.procedural.procedures import ProcedureStorage

procedural = ProcedureStorage(db)

# Create database setup procedure
db_setup = procedural.create_procedure(
    name="setup-postgres-database",
    category="devops",
    description="Initialize PostgreSQL database with migrations",
    steps=[
        {
            "action": "install",
            "package": "postgresql",
            "version": "15",
            "sudo": True
        },
        {
            "action": "start_service",
            "service": "postgresql"
        },
        {
            "action": "create_database",
            "name": "app_db",
            "owner": "app_user"
        },
        {
            "action": "run_migrations",
            "path": "db/migrations",
            "timeout_seconds": 300
        },
        {
            "action": "seed_database",
            "seed_file": "db/seeds/initial.sql"
        }
    ]
)

# Create testing procedure
testing = procedural.create_procedure(
    name="run-test-suite",
    category="testing",
    steps=[
        {
            "action": "install_dependencies",
            "command": "pip install -r requirements-test.txt"
        },
        {
            "action": "run_tests",
            "path": "tests/",
            "parallel": True,
            "verbosity": "v"
        },
        {
            "action": "generate_coverage",
            "min_coverage": 85
        },
        {
            "action": "generate_report",
            "format": "html",
            "output": "htmlcov/"
        }
    ]
)

print(f"Created procedures: {db_setup}, {testing}")
```

### Example 7: Execute Procedures

```python
# Execute database setup
result = procedural.execute_procedure("setup-postgres-database")
if result['success']:
    print("✓ Database setup complete")
else:
    print(f"❌ Setup failed: {result['error']}")

# Execute tests with tracking
result = procedural.execute_procedure("run-test-suite")
procedural.record_execution(
    procedure_id=testing,
    success=result['success'],
    duration_seconds=result['duration']
)

# Later, get effectiveness
effectiveness = procedural.get_effectiveness("run-test-suite")
print(f"Procedure success rate: {effectiveness['success_rate']:.1%}")
```

---

## Prospective Memory Examples

### Example 8: Create Tasks with Triggers

```python
from athena.prospective.tasks import TaskManager

prospective = TaskManager(db)

# Create task with time trigger
code_review = prospective.create_task(
    content="Review pull request #42",
    priority="high",
    triggers={
        "event": "pull_request_opened",
        "author": "junior-dev",
        "timeout_hours": 4
    },
    goal_id=1
)

# Create task with memory-based trigger
security_audit = prospective.create_task(
    content="Audit security implementations for high-risk patterns",
    priority="urgent",
    triggers={
        "memory_query": "security vulnerability",
        "confidence_threshold": 0.8,
        "max_wait_days": 1
    },
    goal_id=3
)

# Create task with file-change trigger
update_docs = prospective.create_task(
    content="Update API documentation after schema changes",
    priority="medium",
    triggers={
        "file": "src/models/*.py",
        "action": "modified",
        "max_wait_hours": 24
    },
    goal_id=2
)
```

### Example 9: List and Manage Tasks

```python
# Get high-priority tasks
urgent = prospective.list_tasks(
    status="pending",
    priority="urgent"
)
print(f"Urgent tasks: {len(urgent)}")
for task in urgent:
    print(f"- [{task.goal_id}] {task.content}")

# Get tasks for specific goal
goal_tasks = prospective.list_tasks(status="in_progress", goal_id=1)
print(f"Working on {len(goal_tasks)} tasks for goal 1")

# Complete a task
prospective.complete_task(
    task_id=code_review,
    status="completed",
    outcome="approved"
)
```

---

## Knowledge Graph Examples

### Example 10: Build Knowledge Graph

```python
from athena.graph.store import GraphStore

graph = GraphStore(db)

# Create entities
auth_service = graph.create_entity(
    name="AuthService",
    entity_type="Component",
    description="Handles JWT authentication and token management"
)

jwt_validator = graph.create_entity(
    name="JWTValidator",
    entity_type="Function",
    description="Validates JWT tokens and extracts claims"
)

db_connection = graph.create_entity(
    name="DatabaseConnection",
    entity_type="Component",
    description="PostgreSQL connection pool"
)

# Create relationships
graph.create_relation(
    from_entity_id=auth_service,
    to_entity_id=jwt_validator,
    relation_type="depends_on"
)

graph.create_relation(
    from_entity_id=auth_service,
    to_entity_id=db_connection,
    relation_type="contains"
)

# Add observations
graph.add_observation(
    entity_id=auth_service,
    observation="Performance bottleneck under >1000 RPS due to token validation",
    context={
        "date": "2025-11-05",
        "impact": "high",
        "priority": "P1"
    }
)
```

### Example 11: Graph Traversal

```python
# Find path from AuthService to Database
path = graph.find_path(
    from_entity_id=auth_service,
    to_entity_id=db_connection,
    max_depth=5
)
print(f"Path: {' → '.join([str(e) for e in path])}")

# Find all related components
related = graph.get_relations(from_entity_id=auth_service)
print(f"AuthService depends on: {[r.to_entity_id for r in related]}")

# Get entity details
entity = graph.get_entity(auth_service)
print(f"{entity.name}: {entity.description}")
```

---

## RAG Examples

### Example 12: Intelligent Retrieval

```python
from athena.rag.manager import RAGManager

rag = RAGManager(db)

# Auto-strategy selection based on query
results1 = rag.retrieve(
    "What changes were made to error handling?",  # Temporal → Reflective
    project_id=1,
    strategy="auto",
    k=5
)

results2 = rag.retrieve(
    "JWT expiration settings",  # Simple → Reranking
    project_id=1,
    strategy="auto",
    k=3
)

print(f"Found {len(results1)} results for question 1")
print(f"Found {len(results2)} results for question 2")
```

### Example 13: Reflective RAG with Iterative Refinement

```python
# Retrieve with explicit iteration and critique
results = rag.retrieve_reflective(
    "How do we implement JWT refresh token rotation with proper cleanup?",
    project_id=1,
    max_iterations=3,
    confidence_threshold=0.8
)

# Check iteration metadata
from athena.rag.reflective import get_iteration_metrics

metrics = get_iteration_metrics(results)
if metrics:
    print(f"Reflective iterations: {metrics['total_iterations']}")
    print(f"Queries used: {metrics['queries_used']}")
    print(f"Confidence progression: {metrics['confidences']}")
    print(f"Stopped early: {metrics['stopped_early']}")

# Results now include high-confidence answers
for result in results[:3]:
    print(f"\nScore: {result.similarity:.2f}")
    print(f"Memory: {result.memory.content[:150]}...")
```

---

## Planning & Verification Examples

### Example 14: Validate Complex Plan

```python
from athena.planning.validator import PlanValidator

validator = PlanValidator(db)

# Create detailed plan
plan = {
    "title": "Implement JWT refresh token rotation",
    "steps": [
        {
            "id": "design",
            "name": "Design token rotation algorithm",
            "duration_hours": 8,
            "resources": {"engineers": 1}
        },
        {
            "id": "implement",
            "name": "Implement token service changes",
            "duration_hours": 16,
            "resources": {"engineers": 2},
            "depends_on": ["design"]
        },
        {
            "id": "test",
            "name": "Write and run tests",
            "duration_hours": 8,
            "resources": {"engineers": 1, "testers": 1},
            "depends_on": ["implement"]
        },
        {
            "id": "deploy",
            "name": "Deploy to production",
            "duration_hours": 2,
            "resources": {"devops": 1},
            "depends_on": ["test"]
        }
    ],
    "resources": {
        "engineers": 2,
        "testers": 1,
        "devops": 1
    },
    "deadline": "2025-11-15T17:00:00Z"
}

# Validate plan (3 levels)
validation = validator.validate_plan(plan, strict=True)
print(f"Validation score: {validation['score']:.2f}/1.0")
print(f"Valid: {validation['valid']}")
if validation['issues']:
    print(f"Issues: {validation['issues']}")
if validation['warnings']:
    print(f"Warnings: {validation['warnings']}")
```

### Example 15: Q* Formal Verification

```python
from athena.planning.formal_verification import FormalVerificationEngine

verifier = FormalVerificationEngine(db)

# Verify plan properties
properties = verifier.verify_plan_properties(plan)

print(f"Property verification results:")
print(f"  Optimality:    {properties['optimality']:.2f}   {'✓' if properties['optimality'] > 0.8 else '✗'}")
print(f"  Completeness:  {properties['completeness']:.2f}   {'✓' if properties['completeness'] > 0.8 else '✗'}")
print(f"  Consistency:   {properties['consistency']:.2f}   {'✓' if properties['consistency'] > 0.8 else '✗'}")
print(f"  Soundness:     {properties['soundness']:.2f}   {'✓' if properties['soundness'] > 0.8 else '✗'}")
print(f"  Minimality:    {properties['minimality']:.2f}   {'✓' if properties['minimality'] > 0.8 else '✗'}")

overall = properties['overall_score']
print(f"\nOverall Q* Score: {overall:.2f}/1.0")
if overall >= 0.8:
    print("Status: ✓ Ready for execution")
elif overall >= 0.6:
    print("Status: ⚠ Proceed with caution")
else:
    print("Status: ❌ Requires refinement")
```

### Example 16: Scenario Simulation

```python
# Stress-test plan under 5 scenarios
simulation = validator.simulate_plan(plan)

print("Scenario Analysis:")
print(f"\n1. Best Case (ideal conditions):")
print(f"   Duration: {simulation['best_case']['duration']}")
print(f"   Success probability: {simulation['best_case']['success_prob']:.1%}")

print(f"\n2. Worst Case (multiple issues):")
print(f"   Duration: {simulation['worst_case']['duration']}")
print(f"   Success probability: {simulation['worst_case']['success_prob']:.1%}")

print(f"\n3. Likely Case (typical challenges):")
print(f"   Duration: {simulation['likely_case']['duration']}")
print(f"   Success probability: {simulation['likely_case']['success_prob']:.1%}")

print(f"\n4. Critical Path (bottleneck focus):")
print(f"   Bottleneck: {simulation['critical_path']['bottleneck']}")
print(f"   Slack time: {simulation['critical_path']['slack']}")

print(f"\nConfidence Interval: {simulation['confidence_interval']}")
print(f"Recommendation: {simulation['recommendation']}")
```

---

## Advanced Workflows

### Example 17: Complete Development Lifecycle

```python
# 1. Start development task
task = prospective.create_task(
    content="Implement password reset flow",
    priority="high",
    goal_id=1
)

# 2. Record work as events
episodic.record_event(
    "Starting implementation of password reset",
    event_type="action",
    outcome="ongoing"
)

# 3. Save design decisions as semantic memories
semantic.create(
    """
    Password Reset Security:
    - Use time-limited tokens (15 minutes)
    - Send reset link via email with random token
    - Hash tokens before storing in database
    - Invalidate all previous reset tokens on new request
    """,
    memory_type="design_decision"
)

# 4. Record implementation progress
episodic.record_event(
    "Implemented password reset endpoint",
    event_type="action",
    outcome="success",
    context={"file": "src/auth/password.py", "lines": 42}
)

# 5. Create procedure for similar tasks
procedural.create_procedure(
    name="password-reset-flow",
    category="authentication",
    steps=[
        {"action": "generate_token", "length": 32},
        {"action": "set_expiry", "minutes": 15},
        {"action": "hash_token"},
        {"action": "send_email", "template": "password_reset"}
    ]
)

# 6. Create knowledge graph entities
graph.create_entity("PasswordReset", "Feature")
graph.create_entity("TokenManager", "Component")

# 7. Complete task
prospective.complete_task(task, status="completed")

# 8. Run consolidation to extract patterns
consolidation_result = db.consolidate(
    strategy="balanced",
    max_events=500
)
print(f"✓ Task complete: {consolidation_result['patterns_extracted']} patterns extracted")
```

### Example 18: Cross-Project Knowledge Transfer

```python
# Search global knowledge base
global_results = rag.retrieve(
    "authentication patterns",
    project_id=0,  # Global scope
    k=5
)

# Filter by relevance
best_matches = [r for r in global_results if r.similarity > 0.7]

# Apply to current project
for match in best_matches:
    print(f"Found applicable pattern: {match.memory.content[:50]}...")

    # Re-use procedure from other project
    if match.memory.memory_type == "procedure":
        procedural.create_procedure(
            name=f"{match.memory.name}-adapted",
            steps=json.loads(match.memory.context['steps']),
            category="reused"
        )

print(f"✓ Transferred {len(best_matches)} patterns to current project")
```

### Example 19: Memory Health Monitoring

```python
from athena.meta.quality import MemoryQuality

meta = MemoryQuality(db)

# Measure system health
quality = meta.measure_quality(project_id=1)

print("Memory System Health:")
print(f"  Overall Score: {quality['overall_score']:.2f}/1.0")
print(f"  Compression Ratio: {quality['compression_ratio']:.1%}")
print(f"  Recall Rate: {quality['recall_rate']:.1%}")
print(f"  Consistency: {quality['consistency_rate']:.1%}")
print(f"  Coverage: {quality['coverage']:.1%}")

# Check expertise levels
expertise = meta.get_expertise(project_id=1)
for domain, score in expertise.items():
    stars = "⭐" * int(score * 5)
    print(f"  {domain}: {stars} ({score:.2f})")

# Detect knowledge gaps
gaps = meta.detect_gaps(project_id=1)
if gaps['contradictions']:
    print(f"\n⚠️  Found {len(gaps['contradictions'])} contradictions:")
    for contradiction in gaps['contradictions'][:3]:
        print(f"   - {contradiction['summary']}")

if gaps['uncertainties']:
    print(f"\n❓ Found {len(gaps['uncertainties'])} uncertainties:")
    for uncertainty in gaps['uncertainties'][:3]:
        print(f"   - {uncertainty['summary']}")
```

---

## Real-World Integration

### Example 20: GitHub Integration

```python
# Webhook handler for GitHub events
@app.post("/github/webhook")
async def github_webhook(event: dict):
    """Record GitHub events in episodic memory"""

    if event['action'] == 'opened':
        episodic.record_event(
            f"PR {event['number']} opened: {event['title']}",
            event_type="pull_request",
            context={
                "author": event['user'],
                "files_changed": event['changed_files'],
                "additions": event['additions']
            }
        )

    elif event['action'] == 'review_requested':
        prospective.create_task(
            content=f"Review PR {event['number']}",
            priority="high",
            triggers={
                "event": "pull_request_review_requested",
                "timeout_hours": 24
            }
        )

    return {"status": "recorded"}
```

### Example 21: Slack Integration

```python
# Slack command handler
@app.post("/slack/command")
async def slack_command(request: dict):
    command = request['text']

    if command.startswith("search "):
        query = command.replace("search ", "")
        results = rag.retrieve(query, project_id=1, k=3)

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Search: {query}*"}}
        ]

        for result in results:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {result.memory.content[:80]}... (score: {result.similarity:.2f})"
                }
            })

        return {"blocks": blocks}

    elif command.startswith("task "):
        task_desc = command.replace("task ", "")
        task_id = prospective.create_task(
            content=task_desc,
            priority="medium"
        )
        return {"text": f"✓ Task {task_id} created"}
```

---

## Performance Tips

1. **Batch Operations**: Use `_batch` methods for multiple operations
2. **Caching**: Leverage LRU caches for frequently accessed data
3. **Indices**: Ensure database indices created for query columns
4. **Consolidation**: Run periodically to compress episodic events
5. **Monitoring**: Use `/memory-health` regularly to track system state

---

## References

- **API Reference**: [API_REFERENCE.md](API_REFERENCE.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
