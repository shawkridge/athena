# Research Orchestration Guide

## Multi-Agent Research System

The Athena system now includes a **Research Orchestration System** that can spawn and coordinate specialized research agents to provide comprehensive, multi-perspective analysis of complex topics.

---

## System Architecture

### Primary Agent: Research Orchestrator

**@research-orchestrator** - Intelligent research coordinator

The research orchestrator analyzes research requests and spawns specialized sub-agents to tackle different aspects:

```
Research Request
    ↓
@research-orchestrator (analyzes request)
    ├── Determines required expertise
    ├── Plans coordination strategy
    └── Spawns specialized agents:
        ├── @research-web-investigator
        ├── @research-codebase-analyzer
        ├── @research-expert-synthesizer
        ├── @research-deep-diver
        ├── @research-hypothesis-tester
        └── @research-documentation-gatherer

    ↓
Synthesized Report
```

---

## Sub-Agent Specializations

### 1. @research-web-investigator
**Specialty:** Current information and web research

What it does:
- Searches the web for current information
- Evaluates source credibility
- Identifies trends and patterns
- Tracks recent developments
- Cites sources properly

Use for:
- Current trends and emerging technologies
- Industry practices and adoption
- Best practices and standards
- Recent developments
- External data and statistics

Output: Current findings with credibility assessment

### 2. @research-codebase-analyzer
**Specialty:** Implementation patterns and code insights

What it does:
- Analyzes Athena codebase
- Identifies design patterns
- Shows implementation examples
- Assesses code quality
- Maps dependencies

Use for:
- How features are implemented
- Code patterns and best practices
- Architecture decisions
- Technical implementation details
- Existing examples and precedents

Output: Code analysis with specific examples and file references

### 3. @research-expert-synthesizer
**Specialty:** Combining perspectives and building consensus

What it does:
- Combines multiple viewpoints
- Identifies areas of agreement
- Resolves contradictions
- Creates unified perspective
- Assesses consensus levels

Use for:
- Understanding expert consensus
- Resolving conflicting opinions
- Getting balanced perspective
- Identifying mainstream thinking
- Finding consensus vs. edge cases

Output: Consensus analysis with identified areas of disagreement

### 4. @research-deep-diver
**Specialty:** Deep understanding and implications

What it does:
- Explores nuances and subtleties
- Finds edge cases and exceptions
- Analyzes implications
- Explores "what-if" scenarios
- Identifies root causes

Use for:
- Understanding underlying principles
- Finding edge cases
- Exploring implications
- Identifying hidden assumptions
- Deep technical understanding

Output: Detailed analysis with implications and edge cases

### 5. @research-hypothesis-tester
**Specialty:** Validation and weakness identification

What it does:
- Tests assumptions
- Verifies claims
- Identifies logical weaknesses
- Assesses risks
- Tests under stress conditions

Use for:
- Validating proposals
- Assessing risks
- Identifying weak points
- Stress testing ideas
- Assumption verification

Output: Validation report with identified risks and weaknesses

### 6. @research-documentation-gatherer
**Specialty:** Organizing findings into reference materials

What it does:
- Collects research findings
- Organizes information logically
- Creates reference guides
- Cross-links related topics
- Captures for future use

Use for:
- Creating reference documentation
- Building implementation guides
- Organizing findings
- Creating architecture documents
- Building decision logs

Output: Organized reference guide or implementation documentation

---

## How to Use the Research System

### Method 1: Use the Research Orchestrator Directly

```
@research-orchestrator - Research "How should we implement authentication?"

The orchestrator will:
1. Analyze your question
2. Determine what expertise is needed
3. Spawn appropriate sub-agents
4. Coordinate their work
5. Synthesize comprehensive answer
```

### Method 2: Use the Research Command

```
/research-topic "WebAssembly adoption in production"

Options:
- /research-topic "[topic]" quick - Quick overview (30 min)
- /research-topic "[topic]" standard - Balanced research (1-2 hours)
- /research-topic "[topic]" comprehensive - Deep research (2-4 hours)
```

### Method 3: Invoke Specific Sub-Agents

```
@research-web-investigator - Find current best practices for async programming
@research-codebase-analyzer - Show me how consolidation is implemented
@research-expert-synthesizer - What do experts agree on regarding microservices?
@research-deep-diver - Explain the implications of server-side rendering
@research-hypothesis-tester - Is this authentication approach secure?
@research-documentation-gatherer - Create a guide for deploying this system
```

### Method 4: Skill-Based Activation

```
User: "I need to research whether to migrate to microservices"

Skill: research-coordination activates automatically
→ Orchestrates multi-agent research
→ Spawns agents in optimal sequence
→ Synthesizes comprehensive analysis
→ Provides evidence-based recommendation
```

---

## Research Strategies

### Strategy 1: Parallel Research (Fast)

**When to use:** Time-sensitive, need quick answer

```
@research-orchestrator - Research "[topic]"
Coordination: Parallel

Process:
1. Spawn all agents simultaneously
2. Each researches independently
3. Collect findings in parallel
4. Quick synthesis
5. Deliver in 30-60 minutes

Trade-off: Less coordination, faster results
```

### Strategy 2: Sequential Research (Targeted)

**When to use:** Need building understanding

```
@research-orchestrator - Research "[topic]"
Coordination: Sequential

Process:
1. Web investigator: Overview from web
2. Results inform: Expert synthesizer
3. Results inform: Deep diver
4. Results inform: Hypothesis tester
5. Documentation gatherer: Create guide

Trade-off: More targeted, slower but deeper
```

### Strategy 3: Hierarchical Research (Complex)

**When to use:** Complex topics with sub-areas

```
@research-orchestrator - Research "[complex topic]"
Coordination: Hierarchical

Process:
1. Initial analysis: Break into sub-areas
2. Spawn agents per sub-area
3. Collect sub-area findings
4. Spawn cross-cutting agents
5. Synthesize at multiple levels

Trade-off: Handles complexity, needs coordination
```

### Strategy 4: Iterative Research (Discovery)

**When to use:** Exploring unknown territory

```
@research-orchestrator - Research "[emerging topic]"
Coordination: Iterative

Process:
1. Initial research: Broad overview
2. Analysis: Identify gaps
3. Iteration 2: Fill identified gaps
4. Analysis: More gaps identified?
5. Repeat until complete

Trade-off: Discovers unknowns, takes time
```

---

## Use Cases

### Use Case 1: Technology Evaluation

```
Query: "Should we adopt Kubernetes?"

Agents Spawned:
- Web Investigator: Current adoption, trends
- Codebase Analyzer: Current infrastructure
- Expert Synthesizer: Industry consensus
- Deep Diver: Trade-offs, implications
- Hypothesis Tester: Risks for our context
- Documentation: Migration guide if adopted

Result: Evidence-based recommendation
```

### Use Case 2: Architecture Decision

```
Query: "How should we structure the API?"

Agents Spawned:
- Codebase Analyzer: Current patterns
- Expert Synthesizer: Best practices consensus
- Deep Diver: Implications of choices
- Web Investigator: Trends in API design
- Hypothesis Tester: Validate approach
- Documentation: API design guide

Result: Well-informed architecture design
```

### Use Case 3: Learning New Technology

```
Query: "How do Rust async patterns work?"

Agents Spawned:
- Web Investigator: Current resources
- Expert Synthesizer: Expert consensus
- Deep Diver: Detailed explanation
- Codebase Analyzer: Find examples
- Hypothesis Tester: Common mistakes
- Documentation: Learning guide

Result: Comprehensive learning material
```

### Use Case 4: Validating Proposal

```
Query: "Is this performance optimization sound?"

Agents Spawned:
- Hypothesis Tester: Test assumptions
- Expert Synthesizer: Expert opinions
- Deep Diver: Implications
- Codebase Analyzer: Current practices
- Web Investigator: Industry validation
- Documentation: Implementation guide

Result: Validation with identified risks
```

---

## Research Output Format

### Executive Summary
- Key findings
- Main recommendation
- Confidence level

### Detailed Findings
- By agent perspective
- With source citations
- Organized by theme

### Consensus & Disagreements
- Areas of agreement
- Areas of disagreement
- Why they differ

### Implications
- What this means
- What to consider
- Risks and opportunities

### Next Steps
- Further research needed
- Implementation recommendations
- Monitoring suggestions

### Reference Guide
- Organized by topic
- Cross-linked
- For future reference

---

## Best Practices

### 1. Be Specific
```
❌ "Research authentication"
✅ "Research JWT authentication for microservices APIs"
```

### 2. Provide Context
```
❌ "@research-orchestrator should we migrate?"
✅ "@research-orchestrator should we migrate from monolith to microservices given our 50-person team?"
```

### 3. Set Scope
```
❌ "Research everything about Kubernetes"
✅ "Research Kubernetes adoption with quick 30-minute overview"
```

### 4. Ask for Synthesis
```
❌ "Give me all perspectives"
✅ "Synthesize the consensus on best practices for distributed tracing"
```

### 5. Follow Up
```
Ask clarifying questions on initial findings
Request deeper dives into interesting areas
Ask for validation of specific claims
```

---

## Quality Assurance

The research system ensures quality through:

✅ **Multi-Perspective Analysis**
- Multiple agents provide different angles
- Reduces single-perspective bias
- Identifies blind spots

✅ **Source Evaluation**
- Web investigator assesses credibility
- Documentation gatherer cites sources
- Hypothesis tester validates claims

✅ **Contradiction Resolution**
- Expert synthesizer identifies disagreements
- Hypothesis tester evaluates validity
- Orchestrator resolves in recommendation

✅ **Completeness Check**
- Research coordination skill monitors coverage
- Identifies gaps
- Recommends additional research

✅ **Relevance Validation**
- Results tailored to your context
- Implications analyzed
- Applicability assessed

---

## Advanced Features

### 1. Recursive Research
```
Research about research itself
- How to research effectively
- How to evaluate sources
- How to synthesize findings
```

### 2. Cross-Domain Research
```
Connect related topics
- How does X relate to Y?
- What are the integration points?
- What's the broader context?
```

### 3. Trend Analysis
```
Understand patterns over time
- How is this field evolving?
- What's emerging?
- What's declining?
```

### 4. Scenario Research
```
Explore conditional outcomes
- What if X happened?
- How would this affect Y?
- Best case vs. worst case?
```

### 5. Competitive Analysis
```
Compare approaches
- Which is better for us?
- What are trade-offs?
- What's the consensus?
```

---

## Integration with Athena

The research system integrates with Athena's knowledge management:

**Inputs from Athena:**
- Existing knowledge
- Codebase analysis
- Project context
- Decision history

**Outputs to Athena:**
- Research findings stored as memories
- Patterns extracted and learned
- Recommendations tracked
- Knowledge documented

**Synergy:**
- Research uses Athena's knowledge
- Athena learns from research
- Feedback loop improves both systems
- Continuous knowledge growth

---

## Command Reference

### Primary Research Command
```bash
/research-topic "[topic]" [depth]

Depth options:
- quick (30 min)
- standard (1-2 hours)
- comprehensive (2-4 hours)

Example:
/research-topic "Microservices migration strategy" comprehensive
```

### Direct Agent Invocation
```bash
@research-orchestrator - [research question]
@research-web-investigator - [web research topic]
@research-codebase-analyzer - [codebase analysis topic]
@research-expert-synthesizer - [synthesis topic]
@research-deep-diver - [deep dive topic]
@research-hypothesis-tester - [claim to validate]
@research-documentation-gatherer - [topic to document]
```

---

## Example: Complete Research Flow

```
User Question: "Should we adopt GraphQL for our API?"

1. @research-orchestrator analyzes
   - Identifies relevant expertise needed
   - Plans multi-agent research
   - Coordinates execution

2. @research-web-investigator
   - Finds current GraphQL adoption rates
   - Identifies trends
   - Reports on industry use

3. @research-codebase-analyzer
   - Reviews current API implementation
   - Shows REST vs GraphQL trade-offs
   - Identifies migration complexity

4. @research-expert-synthesizer
   - Summarizes expert consensus
   - Notes areas of disagreement
   - Identifies when to use GraphQL

5. @research-deep-diver
   - Explores implications
   - Edge cases and limitations
   - Performance considerations

6. @research-hypothesis-tester
   - Tests assumption: "GraphQL simplifies our queries"
   - Identifies risks
   - Validates benefits

7. @research-documentation-gatherer
   - Compiles all findings
   - Creates migration guide if needed
   - Builds reference material

8. @research-orchestrator synthesizes
   - Combines all findings
   - Creates comprehensive report
   - Recommends: "Yes, use GraphQL for new features,
     keep REST for existing APIs" (example)
```

---

## Summary

The Research Orchestration System provides:

✅ **Multi-perspective research** - See all angles
✅ **Expert synthesis** - Understand consensus
✅ **Validation** - Test your assumptions
✅ **Deep understanding** - Know the implications
✅ **Comprehensive guides** - Reference material
✅ **Evidence-based decisions** - Research-backed recommendations

**When to use:**
- Making significant decisions
- Learning new technologies
- Evaluating major changes
- Building comprehensive understanding
- Validating critical assumptions

**How to start:**
```
@research-orchestrator - Research [your topic]
```

That's it! The orchestrator handles the rest.
