# Skills Architecture: Autonomous Enhancement Layer

**Version**: 1.0 (Anthropic-aligned) | **Date**: November 12, 2025 | **Status**: Active

This document defines the 17 autonomous skills that extend Claude Code's capabilities. Skills are **model-invoked** - Claude autonomously decides when to use them based on your request and the skill's description.

---

## Quick Reference: All 17 Skills

### Core Enhancement Skills (Always Available)

| Skill | Location | Auto-Triggers When | Layer |
|-------|----------|-------------------|-------|
| **quality-evaluation** | `~/.claude/skills/quality-evaluation/` | Discussing memory health, gaps, metrics | Meta-Memory |
| **code-impact-analysis** | `~/.claude/skills/code-impact-analysis/` | Analyzing code changes, refactoring | Code Analysis |
| **planning-validation** | `~/.claude/skills/plan-verification/` | Validating plans, checking feasibility | Planning |

### Research Skills (Auto-Apply for Investigation)

| Skill | Purpose | Auto-Triggers When |
|-------|---------|-------------------|
| **research-coordination** | Multi-perspective research orchestration | Need comprehensive investigation from multiple angles |
| **codebase-research** | Codebase pattern analysis | Analyzing code patterns, implementation insights |
| **deep-research** | Deep-dive analysis with edge cases | Need thorough exploration of nuances and implications |
| **documentation-research** | Documentation gathering and organization | Gathering and organizing research findings |
| **research-synthesis** | Multi-source synthesis and consensus | Combining sources and identifying consensus |
| **hypothesis-validation** | Assumption testing and verification | Testing hypotheses, verifying claims, finding weaknesses |
| **web-research** | Web investigation with credibility checks | Need current information from the web |

### Utility Skills (Auto-Apply for Operations)

| Skill | Purpose | Auto-Triggers When |
|-------|---------|-------------------|
| **advanced-retrieval** | Advanced RAG strategies, context enrichment | Need sophisticated information retrieval |
| **advanced-planning** | Formal verification with Q* and scenarios | Formal plan verification, scenario testing |
| **planning-coordination** | Task decomposition and plan orchestration | Breaking down complex tasks, coordinating plans |
| **automation-management** | Event-driven automation and triggers | Setting up automated workflows or triggers |
| **graph-analysis** | GraphRAG community detection (GraphRAG) | Discovering communities, graph structure analysis |
| **memory-management** | Memory retrieval, storage, and optimization | Memory operations, recall, storage optimization |
| **workflow-engineering** | Procedure creation and workflow automation | Creating reusable procedures, workflow automation |

---

## Skill Layers & Relationships

```
Claude Code (Main Context)
    ├─ Skills (Autonomous Enhancement)
    │  ├─ Tier 1: Core Enhancement (3 skills)
    │  │  └─ Always available, auto-discovered
    │  │
    │  ├─ Tier 2: Research (7 skills)
    │  │  └─ Auto-activated when investigating
    │  │
    │  └─ Tier 3: Utility Operations (7 skills)
    │     └─ Auto-activated for specific domains
    │
    └─ Subagents (Explicit Delegation via Task)
       └─ 8 focused specialists (code-analyzer, safety-auditor, etc.)
```

---

## How Skills Work (Anthropic Model)

### The Three-Layer Discovery Pattern

1. **Metadata Layer** (Always loaded)
   - Skill name and description
   - When Claude should consider using it
   - Load time: ~0ms (part of system prompt)

2. **Content Layer** (On-demand)
   - Full SKILL.md content
   - Loaded when Claude decides skill is relevant
   - Load time: ~10-50ms

3. **Resource Layer** (Sparse)
   - Supporting scripts, templates, reference files
   - Loaded only as referenced in SKILL.md
   - Load time: ~5-20ms per file

### Example: How Research-Coordination Skill Auto-Activates

**Scenario**: You ask Claude to research a complex topic

```
You: "Research how Anthropic designs agents for production use"

Claude's reasoning:
  1. [Metadata] "User is asking for research - do I have research skills?"
  2. [Discover] "Yes, research-coordination skill exists - let me check its trigger"
  3. [Read] "research-coordination triggers when: multi-perspective needed, multiple sources, consensus building"
  4. [Match] "This matches! I need multiple perspectives (research, best practices, real-world examples)"
  5. [Activate] "Loading research-coordination skill..."
  6. [Execute] "Using web-research, documentation-research, research-synthesis skills together"
  7. [Return] "Here's comprehensive research with sources and consensus"
```

**Key**: Claude decided autonomously - you didn't explicitly request research-coordination.

---

## The 17 Skills: Detailed Descriptions

### TIER 1: CORE ENHANCEMENT SKILLS

#### 1. Quality Evaluation
**Location**: `~/.claude/skills/quality-evaluation/`
**Framework**: 4-metric quality assessment
**Auto-Triggers**:
- Discussing memory system health
- Analyzing knowledge gaps
- Evaluating learning effectiveness
- Planning consolidation

**Capabilities**:
- Compression scoring (how much knowledge fits)
- Recall effectiveness (can knowledge be retrieved)
- Consistency checking (contradictions)
- Density analysis (knowledge distribution)

**Example Usage**:
```
You: "How's the memory system doing after consolidation?"
Claude: *Autonomously activates quality-evaluation skill*
         "System is at 85% quality - here's what needs improvement..."
```

---

#### 2. Code Impact Analysis
**Location**: `~/.claude/skills/code-impact-analysis/`
**Framework**: Spatial-temporal impact prediction
**Auto-Triggers**:
- Discussing code changes
- Evaluating refactoring
- Assessing architectural changes
- Planning migrations

**Capabilities**:
- Dependency impact prediction
- Risk zone identification
- Testing requirement analysis
- Integration point detection

**Example Usage**:
```
You: "What happens if we refactor the search module?"
Claude: *Autonomously activates code-impact-analysis*
         "This affects 8 files downstream, risk level: medium..."
```

---

#### 3. Planning Validation
**Location**: `~/.claude/skills/plan-verification/`
**Framework**: Q* formal verification + 5-scenario testing
**Auto-Triggers**:
- Validating plans or strategies
- Checking plan feasibility
- Risk assessment
- Assumption verification

**Capabilities**:
- Optimality checking (best approach?)
- Completeness checking (all cases covered?)
- Consistency checking (no contradictions?)
- Soundness checking (will it work?)
- Minimality checking (necessary and sufficient?)

**Example Usage**:
```
You: "Does this rollout plan look good?"
Claude: *Autonomously activates planning-validation*
         "Plan is sound but missing scenario: X. Recommend..."
```

---

### TIER 2: RESEARCH SKILLS

#### 4. Research Coordination
**Location**: `~/.claude/skills/research-coordination/`
**Purpose**: Orchestrate multi-perspective research
**Auto-Triggers**: Need comprehensive investigation from multiple angles
**Coordinates**: web-research, documentation-research, research-synthesis

**Process**:
1. Break research question into sub-questions
2. Delegate to specialized research skills
3. Synthesize findings into coherent narrative
4. Identify consensus and conflicts

---

#### 5. Codebase Research
**Location**: `~/.claude/skills/codebase-research/`
**Purpose**: Analyze code patterns and implementation insights
**Auto-Triggers**: Analyzing code patterns, finding implementation insights
**Searches**: Files, symbols, patterns, examples

**Capabilities**:
- Pattern discovery in codebase
- Implementation example finding
- Architecture pattern analysis
- Design decision tracing

---

#### 6. Deep Research
**Location**: `~/.claude/skills/deep-research/`
**Purpose**: Deep-dive analysis with edge cases and implications
**Auto-Triggers**: Need thorough exploration of nuances, edge cases
**Approach**: Multi-level exploration (surface → deeper → deepest)

**Explores**:
- Primary concepts
- Boundary cases and exceptions
- Deeper implications
- Edge cases and gotchas
- Historical context
- Future possibilities

---

#### 7. Documentation Research
**Location**: `~/.claude/skills/documentation-research/`
**Purpose**: Gather and organize research findings into guides
**Auto-Triggers**: Gathering docs, organizing findings, creating guides

**Produces**:
- Consolidated research findings
- Organized by topic
- With sources and citations
- Structured for reference

---

#### 8. Research Synthesis
**Location**: `~/.claude/skills/research-synthesis/`
**Purpose**: Combine sources and identify consensus
**Auto-Triggers**: Combining multiple sources, finding agreements

**Synthesizes**:
- Multiple source perspectives
- Consensus finding
- Conflict identification
- Confidence scoring

---

#### 9. Hypothesis Validation
**Location**: `~/.claude/skills/hypothesis-validation/`
**Purpose**: Test assumptions and verify claims
**Auto-Triggers**: Testing hypotheses, verifying claims, finding weaknesses

**Validates**:
- Assumption truth
- Claim verification
- Evidence sufficiency
- Weakness identification
- Alternative explanations

---

#### 10. Web Research
**Location**: `~/.claude/skills/web-research/`
**Purpose**: Investigate current information with source credibility
**Auto-Triggers**: Need current information from web

**Evaluates**:
- Source credibility
- Information currency
- Consensus across sources
- Confidence levels

---

### TIER 3: UTILITY OPERATION SKILLS

#### 11. Advanced Retrieval
**Location**: `~/.claude/skills/advanced-retrieval/`
**Purpose**: Advanced RAG strategies for context enrichment
**Auto-Triggers**: Need sophisticated information retrieval
**Strategies**:
- HyDE (Hypothetical Document Embeddings)
- Reranking (relevance re-scoring)
- Query transformation
- Reflective retrieval

---

#### 12. Advanced Planning
**Location**: `~/.claude/skills/advanced-planning/`
**Purpose**: Formal verification with Q* and scenario simulation
**Auto-Triggers**: Formal plan verification, scenario testing
**Properties Verified**:
- Optimality (best approach?)
- Completeness (all cases?)
- Consistency (no contradictions?)
- Soundness (will it work?)
- Minimality (no wasted steps?)

---

#### 13. Planning Coordination
**Location**: `~/.claude/skills/planning-coordination/`
**Purpose**: Task decomposition and orchestration
**Auto-Triggers**: Breaking down complex tasks, coordinating plans
**Decomposes**: Using 9+ decomposition strategies
**Strategies**:
- Hierarchical breakdown
- Dependency-based ordering
- Parallel/sequential optimization
- Resource allocation
- Risk mitigation

---

#### 14. Automation Management
**Location**: `~/.claude/skills/automation-management/`
**Purpose**: Event-driven automation setup
**Auto-Triggers**: Setting up automated workflows or event-based triggers
**Manages**:
- Time-based triggers (schedule)
- Event-based triggers (hook)
- File-based triggers (monitor)
- Smart workflows with feedback loops

---

#### 15. Graph Analysis
**Location**: `~/.claude/skills/graph-analysis/`
**Purpose**: GraphRAG community detection and relationship analysis
**Auto-Triggers**: Discovering communities, graph structure analysis
**Uses**: Leiden clustering algorithm
**Discovers**:
- Natural communities
- Bridge entities
- Knowledge structure
- Relationship patterns
- Connection optimization

---

#### 16. Memory Management
**Location**: `~/.claude/skills/memory-management/`
**Purpose**: Memory layer operations (Athena-specific)
**Auto-Triggers**: Memory operations, retrieval, storage, optimization
**Operations**:
- Episodic memory (events)
- Semantic memory (knowledge)
- Procedural memory (workflows)
- Prospective memory (goals)
- Meta-memory (knowledge about knowledge)

---

#### 17. Workflow Engineering
**Location**: `~/.claude/skills/workflow-engineering/`
**Purpose**: Procedure creation and workflow automation
**Auto-Triggers**: Creating reusable procedures, workflow automation
**Creates**:
- Extracted procedures from work
- Reusable workflow templates
- Best practice documentation
- Success pattern libraries

---

## Auto-Activation Trigger Matrix

Quick reference: When does each skill auto-activate?

| Skill | Triggers When You... |
|-------|----------------------|
| quality-evaluation | Discuss memory health, gaps, metrics |
| code-impact-analysis | Analyze changes, refactoring, migrations |
| planning-validation | Validate plans, check feasibility, risk assess |
| research-coordination | Ask for comprehensive research/investigation |
| codebase-research | Analyze code patterns, find implementations |
| deep-research | Need thorough exploration with edge cases |
| documentation-research | Gather docs, organize findings, create guides |
| research-synthesis | Combine sources, find consensus |
| hypothesis-validation | Test hypotheses, verify claims |
| web-research | Need current information from web |
| advanced-retrieval | Need sophisticated context retrieval |
| advanced-planning | Formally verify plans, test scenarios |
| planning-coordination | Break down complex tasks |
| automation-management | Set up workflows, event triggers |
| graph-analysis | Analyze graph structure, discover communities |
| memory-management | Perform memory operations (Athena-specific) |
| workflow-engineering | Create procedures, automate workflows |

---

## Skill vs Subagent: Decision Matrix

**Use Skill When**: You need Claude to autonomously apply a capability
- Asking question that needs research
- Discussing code changes
- Validating plans
- Discussing memory system

**Use Subagent When**: You need explicit delegation to specialist
- Deep code analysis needed
- Security audit required
- Architecture design
- Formal verification
- Implementation task

**Example Difference**:

```
❌ SKILL (Auto-apply):
You: "Research best practices for agent design"
Claude: *Autonomously activates research-coordination skill*
        *Auto-delegates to web-research, documentation-research*
        "Here's comprehensive research..."

✅ SUBAGENT (Explicit delegation):
You: "I need architecture design for a new feature"
Task(subagent_type="system-architect", prompt="Design X feature")
Architect: *Works in isolated 50K context on detailed design*
           "Here's my recommended approach..."
```

---

## Progressive Disclosure Pattern

Skills use a "progressive disclosure" design to minimize context loading:

### Level 1: Metadata (Always Available)
```yaml
name: research-coordination
description: |
  When you need comprehensive investigation from multiple angles.
  This skill coordinates web research, documentation gathering,
  and synthesis to build complete understanding.
```
**Load**: ~0ms (system prompt)

### Level 2: Content (On-Demand)
```markdown
# Research Coordination Skill

When Claude detects research is needed, it loads this full content:
- Strategy breakdown
- Sub-skill coordination
- Process flow
```
**Load**: ~20ms (when relevant)

### Level 3: Resources (Sparse)
```
- templates/research-template.md
- examples/research-example.md
- reference/research-sources.md
```
**Load**: ~5-10ms each (only when referenced)

**Benefit**: Fast context loading - only what's needed is loaded

---

## Measuring Skill Effectiveness

### Success Metrics

| Metric | Good | Excellent |
|--------|------|-----------|
| Auto-Activation Rate | >50% of relevant requests | >80% |
| False Positives | <10% | <5% |
| Context Efficiency | 300-500 tokens per skill | <300 tokens |
| Task Completion | 70% first attempt | >90% |

### How to Measure

1. **Track skill invocations**: When are skills auto-activated?
2. **Measure quality**: Are results better with skill vs without?
3. **Monitor false positives**: Does skill activate inappropriately?
4. **Check efficiency**: What's the token cost per skill use?

---

## Skill Lifecycle

### Creation (Tier 3 Agent: skill-developer)
1. Define trigger conditions (when should Claude use this?)
2. Write SKILL.md with clear instructions
3. Create supporting resources (templates, examples)
4. Document auto-activation conditions

### Testing
1. Try relevant tasks that should trigger skill
2. Verify auto-activation works
3. Check quality of outputs
4. Measure false positive rate

### Optimization
1. Refine trigger descriptions
2. Add more examples
3. Improve resource organization
4. Update based on usage patterns

### Deprecation
1. Monitor if skill is still auto-activating
2. Check if better alternatives exist
3. Archive if redundant
4. Consolidate if overlapping

---

## Architecture Benefits

✅ **Progressive Disclosure**: Only load what's needed
✅ **Autonomous Enhancement**: Claude decides when to use
✅ **Context Efficiency**: Metadata → Content → Resources (on-demand)
✅ **Composition**: Skills can coordinate (research-coordination uses 3 research skills)
✅ **Discoverability**: Claude autonomously discovers relevant skills
✅ **Supervision**: You maintain oversight of main context decisions

---

## Next Steps

### This Week
- Verify all 17 skills are properly structured
- Test auto-activation on representative tasks
- Measure skill effectiveness

### Next Week
- Optimize trigger descriptions based on usage
- Create skill examples and templates
- Enhance documentation resources

### Following Week
- Consider new skills based on common needs
- Consolidate overlapping skills
- Build skill marketplace

---

## File Organization

```
~/.claude/skills/
├── quality-evaluation/
│   ├── SKILL.md
│   ├── frameworks/
│   │   └── quality-metrics.md
│   └── examples/
│       └── quality-assessment-example.md
│
├── code-impact-analysis/
│   ├── SKILL.md
│   ├── tools/
│   │   └── impact-calculator.md
│   └── examples/
│       └── impact-example.md
│
├── [14 more skills with same structure...]
│
└── README.md (this file's companion)
```

---

## Skill Development Guidelines

### For Creating New Skills

1. **Define Clear Trigger**: When should Claude autonomously use this?
2. **Keep It Focused**: One main capability per skill
3. **Progressive Disclosure**: Metadata → Content → Resources
4. **Provide Examples**: Show how skill works with examples
5. **Document Resources**: Link to supporting files

### SKILL.md Template

```yaml
---
name: skill-name
description: |
  When should Claude autonomously use this skill?
  Be specific about the trigger conditions.
---

# Skill Name

## When to Use
- Condition 1
- Condition 2

## How It Works
[Explain the process]

## Capabilities
- [List capabilities]

## Examples
[Show examples]

## Resources
- [Link to supporting files]
```

---

**Version**: 1.0 (Anthropic-aligned)
**Status**: All 17 skills active and ready
**Last Updated**: November 12, 2025

---

## See Also

- **CORE_AGENTS.md** - The 8 subagents (explicit delegation)
- **AGENT_DELEGATION_STRATEGY.md** - Strategic approach to delegation
- **README.md** - Project overview
