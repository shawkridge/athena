# Agent Testing & Measurement Guide

**Version**: 1.0 | **Date**: November 12, 2025 | **Purpose**: Verify Tier 1 agent effectiveness

This guide provides procedures for testing and measuring the impact of your first three agents.

---

## Testing Overview

**Goal**: Verify agents work correctly and achieve 60% context reduction in Week 1

**Measurements**:
- ✅ Context token usage (before/after)
- ✅ Solution quality improvements
- ✅ Task completion time
- ✅ Auto-trigger effectiveness
- ✅ Agent reliability

---

## Pre-Testing Setup

### 1. Establish Baselines

Before using agents, establish current metrics:

```bash
# Session 1: WITHOUT agents (establish baseline)
# - Record context tokens used
# - Note task completion time
# - Grade solution quality

# Session 2: WITHOUT agents (verify baseline)
# - Same task type, different code
# - Verify reproducible metrics

# Average of Session 1-2 = BASELINE
```

**Baseline Metrics to Track**:
- Main context tokens per task
- Task completion time (minutes)
- Solution quality rating (1-5 scale)
- Issues found per 1000 LOC reviewed
- Test coverage percentage

### 2. Verify Agent Installation

```bash
# Check agents exist
ls -la /home/user/.claude/agents/code-reviewer/
ls -la /home/user/.claude/agents/security-auditor/
ls -la /home/user/.claude/agents/test-generator/

# Expected files:
# - code-reviewer/agent.md + review-checklist.md
# - security-auditor/agent.md
# - test-generator/agent.md
```

---

## Testing Phase 1: Agent Auto-Activation

### Test 1.1: Code Reviewer Auto-Trigger

**Scenario**: Ask Claude to review code (should auto-trigger code-reviewer)

```
Session 1:
User: "Review the consolidation system code for quality issues"

Expected: Code-reviewer agent activates automatically
Verify:
  ✓ Agent produces comprehensive review
  ✓ Review includes grades (Quality/Security/Performance/Maintainability)
  ✓ Specific line references provided
  ✓ Recommendations prioritized by severity
  ✓ Main context stays lean (2-3K tokens only)

Record:
  - Main context tokens used
  - Time to complete
  - Review quality (1-5 scale)
  - Issues identified
```

### Test 1.2: Security Auditor Auto-Trigger

**Scenario**: Ask Claude to check for security issues (should auto-trigger security-auditor)

```
Session 2:
User: "Audit the memory layer for security vulnerabilities"

Expected: Security-auditor agent activates automatically
Verify:
  ✓ Agent performs threat modeling
  ✓ Vulnerability assessment comprehensive
  ✓ Risk levels assigned (CRITICAL/HIGH/MEDIUM/LOW)
  ✓ Remediation recommendations provided
  ✓ Main context stays lean

Record:
  - Main context tokens used
  - Time to complete
  - Issues identified
  - Risk assessment accuracy
```

### Test 1.3: Test Generator Auto-Trigger

**Scenario**: Ask Claude to write tests (should auto-trigger test-generator)

```
Session 3:
User: "Generate comprehensive tests for the semantic search function"

Expected: Test-generator agent activates automatically
Verify:
  ✓ Agent creates unit tests
  ✓ Agent creates integration tests
  ✓ Edge cases covered
  ✓ Error scenarios tested
  ✓ Tests runnable and passing
  ✓ Coverage calculation provided
  ✓ Main context stays lean

Record:
  - Main context tokens used
  - Time to complete
  - Test coverage %
  - Number of tests generated
```

---

## Testing Phase 2: Explicit Agent Invocation

If auto-triggering doesn't work, test explicit invocation:

### Test 2.1: Request Code Reviewer Explicitly

```
User: "Request code-reviewer agent to assess this function"

Verify same as Test 1.1
```

### Test 2.2: Request Security Auditor Explicitly

```
User: "Invoke security-auditor to review this component"

Verify same as Test 1.2
```

### Test 2.3: Request Test Generator Explicitly

```
User: "Ask test-generator to create tests for this module"

Verify same as Test 1.3
```

---

## Testing Phase 3: Measurement

### Measurement 3.1: Context Token Usage

Track tokens in two ways:

**Method 1: Use Claude Code `/cost` command**
```
/cost
# Displays: session tokens, estimated cost, usage breakdown
```

**Method 2: Manual tracking (if /cost unavailable)**
```
# At start of session: note context window position
# After agent task: note new position
# Difference = tokens used in main context
```

**Recording**:
```
Task: Code Review
Without agents: 150K tokens (100%)
With code-reviewer agent: 15K tokens (10%)
Reduction: 90% main context reduction
```

### Measurement 3.2: Task Completion Time

```
Task: Review 500 lines of code

WITHOUT agents:
- Start: 2:00 PM
- End: 2:15 PM (15 minutes)

WITH code-reviewer agent:
- Start: 2:00 PM
- End: 2:05 PM (5 minutes)

Improvement: 3x faster (15 → 5 minutes)
```

### Measurement 3.3: Quality Assessment

Rate on scale 1-5:

```
Code Review Quality:
Without agents: 3/5 (generalist review)
With code-reviewer: 4.5/5 (specialist review)
Improvement: +50%

Security Audit Quality:
Without agents: 2.5/5 (missed vulnerabilities)
With security-auditor: 4.5/5 (comprehensive)
Improvement: +80%

Test Coverage:
Without agents: 60% coverage
With test-generator: 87% coverage
Improvement: +27%
```

### Measurement 3.4: Issues Found Per Task

```
Code Review (1000 lines):
Without agents: 5 issues found
With code-reviewer: 12 issues found (70% better detection)

Security Audit:
Without agents: 2 vulnerabilities found
With security-auditor: 8 vulnerabilities found (4x better)

Test Coverage Gaps:
Without agents: 12 gaps identified
With test-generator: Tests fill all gaps
```

---

## Measurement Framework

### Week 1 (Tier 1 Agents): Expected Results

| Metric | Baseline | With Agents | Improvement |
|--------|----------|------------|-------------|
| Main context tokens/task | 150K | 15K | 90% ↓ |
| Task completion time | 15 min | 5 min | 3x faster |
| Code quality rating | 3/5 | 4.5/5 | +50% |
| Security issues found | 2/task | 8/task | 4x better |
| Test coverage | 60% | 87% | +27% |
| Development satisfaction | 2/5 | 4/5 | +100% |

**Target**: Achieve 60-90% reduction in main context tokens

### Week 2 (Tier 2 Agents): Expected Results

| Metric | After Tier 1 | After Tier 2 | Total Improvement |
|--------|-------------|--------------|------------------|
| Main context tokens | 60K | 20K | 87% ↓ |
| Architecture decisions | Manual | Automated | 50% faster |
| Documentation sync | Manual | Automated | 100% up-to-date |
| Performance analysis | None | Comprehensive | +40% new insights |

### Week 3 (Tier 3 Agents): Expected Results

| Metric | After Tier 2 | After Tier 3 | Total Improvement |
|--------|-------------|--------------|------------------|
| Main context tokens | 20K | 10K | 93% ↓ |
| Consolidation quality | 70% | 85% | +15% |
| Graph efficiency | Baseline | +40% optimization | Significant |
| Overall productivity | 3x faster | 5x faster | Exceptional |

---

## Real-World Testing Scenarios

### Scenario 1: Feature Implementation

**Task**: Add new memory layer feature

**Workflow (with agents)**:
1. User: "Plan new feature"
   - system-architect (Tier 2): Design review
   - Main context: 2K tokens

2. User: "Implement the feature"
   - code-reviewer: Code quality check
   - security-auditor: Security review
   - test-generator: Test suite creation
   - Main context: Coordinates 3 agents
   - Total main context: 5K tokens

3. User: "Prepare for deployment"
   - code-reviewer: Final review
   - test-generator: Coverage check
   - documentation-engineer (Tier 2): Update docs
   - Main context: Coordinates
   - Total main context: 3K tokens

**Total main context**: 10K tokens
**Without agents**: Would be 150K tokens
**Reduction**: 93% (matching Phase 3 target)

### Scenario 2: Security Audit

**Task**: Pre-deployment security review

**Workflow (with agents)**:
1. security-auditor: Threat modeling
2. security-auditor: Vulnerability scanning
3. code-reviewer: Security code review
4. Main context: Coordinates, prioritizes
5. Updates plan based on findings

**Timeline**: 30 minutes (vs 90 without agents)
**Main context**: 8K tokens (vs 120K without agents)

---

## Troubleshooting

### Problem: Agent Not Auto-Triggering

**Diagnosis**:
1. Check agent description has clear trigger words
2. Verify agent is in correct directory
3. Check YAML frontmatter is valid

**Solution**:
1. Update agent description with more trigger words
2. Move to correct location: `/home/user/.claude/agents/[name]/agent.md`
3. Use explicit invocation as fallback

### Problem: Main Context Still Bloated

**Diagnosis**:
1. Agent not being called
2. Agent returning too much data
3. Main context doing work agents should do

**Solution**:
1. Verify agent is invoked (check Claude's output)
2. Ask agent to summarize results
3. Delegate more work to agents

### Problem: Agent Producing Low-Quality Output

**Diagnosis**:
1. Agent description too vague
2. Agent needs more context
3. Task too complex for single agent

**Solution**:
1. Make trigger words more specific
2. Provide more context in your prompt
3. Delegate smaller, focused tasks

---

## Measurement Checklist

### Weekly (Every Monday)

- [ ] Record main context token usage
- [ ] Track task completion times
- [ ] Rate solution quality (1-5)
- [ ] Count issues found per task
- [ ] Verify test coverage %
- [ ] Calculate cost savings (if applicable)
- [ ] Update measurement spreadsheet

### Bi-Weekly (Every other Friday)

- [ ] Compare against baseline
- [ ] Calculate cumulative improvements
- [ ] Identify bottlenecks
- [ ] Plan Tier 2 agent creation
- [ ] Review agent reliability

### Monthly (End of month)

- [ ] Generate comprehensive report
- [ ] Calculate ROI (time saved × hourly rate)
- [ ] Document lessons learned
- [ ] Plan next quarter improvements
- [ ] Share results with team

---

## Success Criteria

### Phase 1 (Tier 1): PASS if...

- ✅ Main context: 150K → 60K tokens (60% reduction achieved)
- ✅ Code review quality: 3.0 → 4.0+/5
- ✅ Security findings: 2 → 6+ per audit
- ✅ Test coverage: 60% → 75%+
- ✅ Task speed: 3x faster (15 → 5 minutes)
- ✅ Agent reliability: >95% successful invocations

### Phase 1: CONDITIONAL if...

- ⚠️ Main context: 150K → 80K (53% reduction)
- ⚠️ Quality improvements moderate
- ⚠️ Agent reliability 80-95%

**Action**: Adjust agent descriptions, test more scenarios

### Phase 1: NEEDS WORK if...

- ❌ Main context: <50% reduction
- ❌ Agent quality low
- ❌ Agent reliability <80%

**Action**: Debug agents, update descriptions, test explicitly

---

## Reporting Template

```markdown
## Week 1 Agent Testing Report

### Tier 1 Agents Performance

#### code-reviewer Agent
- Auto-trigger success: [X/Y] tests
- Main context reduction: [X]%
- Code quality rating: [X]/5
- Issues found: [X] per task
- Time savings: [X]x faster

#### security-auditor Agent
- Auto-trigger success: [X/Y] tests
- Main context reduction: [X]%
- Security findings: [X] per audit
- Vulnerability detection: [X]% accuracy
- False positive rate: [X]%

#### test-generator Agent
- Auto-trigger success: [X/Y] tests
- Main context reduction: [X]%
- Coverage improvement: [X]% → [Y]%
- Test creation speed: [X] minutes
- Test reliability: [X]%

### Overall Results
- Total main context reduction: [X]%
- Average task speed improvement: [X]x
- Overall quality improvement: +[X]%
- Agent reliability: [X]%

### Next Steps
1. [Action items based on results]
2. [Planned Tier 2 agents]
3. [Schedule for Phase 2]
```

---

## Advanced Measurements

### Context Window Health

```python
# Track context utilization over time
context_usage = {
    "start": 25000,      # Beginning of session
    "after_agent_1": 35000,   # After first agent
    "after_agent_2": 38000,   # After second agent
    "end": 42000,        # End of session
}

main_context_used = context_usage["end"] - context_usage["start"]
# 42K - 25K = 17K (only 17K in main)
# Agents used: 42K - 17K = 25K in separate contexts
```

### Quality Metrics by Dimension

```python
# Track quality improvements across dimensions
quality_scores = {
    "code_review": {
        "before": {"completeness": 0.65, "accuracy": 0.70, "actionability": 0.60},
        "after":  {"completeness": 0.95, "accuracy": 0.92, "actionability": 0.88},
    },
    "security_audit": {
        "before": {"coverage": 0.40, "accuracy": 0.50, "risk_assessment": 0.45},
        "after":  {"coverage": 0.92, "accuracy": 0.88, "risk_assessment": 0.85},
    },
}
```

---

## Next Steps

1. **This Week**: Run Phase 1 tests (auto-trigger)
2. **Next Week**: Run Phase 2 tests (explicit invocation)
3. **Following Week**: Phase 3 testing (explicit verification)
4. **End of Week 1**: Compile results and decide on Tier 2 agents

**Target Decision Point**: Friday of Week 1
- If >60% reduction achieved → Proceed to Tier 2
- If 40-60% reduction → Optimize Tier 1, then Tier 2
- If <40% reduction → Debug agents, adjust descriptions

---

**Ready to test?** Start with Test 1.1 (Code Reviewer Auto-Trigger) and track results!
