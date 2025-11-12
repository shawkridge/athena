---
name: research-coordination
description: |
  When facing complex research questions requiring multiple perspectives or deep analysis.
  When you need comprehensive evidence-based answers from multiple specialized angles.
  When research needs synthesis across web trends, codebase patterns, and expert opinions.
---

# Research Coordination Skill

Intelligent multi-perspective research by spawning specialized sub-agents for comprehensive analysis.

## When to Use

- Complex research questions requiring multiple angles
- Need for evidence-based decisions from diverse sources
- Topics requiring both current trends and deep technical understanding
- Situations where contradiction resolution is needed
- Emerging topics needing comprehensive coverage
- Architecture or technology evaluation decisions

## How It Works

### Phase 1: Research Analysis
1. **Decompose Request** - Break research into distinct aspects
2. **Identify Gaps** - What information is needed
3. **Determine Agents** - What expertise is required
4. **Plan Coordination** - How agents should work together
5. **Synthesize Results** - Combine findings into coherent answer

### Phase 2: Sub-Agent Spawning

Spawn specialized research sub-agents as needed:

**@research-web-investigator**
- Searches web for current information
- Evaluates source credibility
- Extracts key findings
- Use for: Current trends, external research, real-world data

**@research-codebase-analyzer**
- Analyzes codebase patterns
- Extracts implementation details
- Finds relevant examples
- Use for: Code patterns, architecture insights, implementation specifics

**@research-expert-synthesizer**
- Combines multiple sources
- Identifies contradictions
- Creates unified perspective
- Use for: Consensus building, contradiction resolution, synthesis

**@research-deep-diver**
- Goes deep into specific topic
- Finds nuances and edge cases
- Explores implications
- Use for: Deep understanding, edge cases, implications

**@research-hypothesis-tester**
- Tests assumptions
- Validates claims
- Identifies weaknesses
- Use for: Validation, assumption testing, quality assurance

**@research-documentation-gatherer**
- Collects relevant documentation
- Organizes findings
- Creates reference guide
- Use for: Documentation, knowledge compilation, reference guides

### Phase 3: Coordination Patterns

**Parallel Research** - Spawn multiple agents simultaneously for comprehensive coverage
**Sequential Research** - Chain agents where results inform next steps
**Hierarchical Research** - Top-level analysis identifies sub-areas for specialized agents
**Iterative Research** - Initial research identifies gaps, spawn agents to fill them

### Phase 4: Synthesis

**Convergence** (agents agree) - Strong evidence, high confidence
**Divergence** (agents disagree) - Present multiple perspectives, recommend further research
**Gaps** (no agent covered it) - Flag as unknown, suggest how to research further

## Research Quality Standards

- **Accuracy** - Verify facts across sources
- **Completeness** - Cover all relevant aspects
- **Balance** - Present multiple perspectives
- **Clarity** - Explain findings clearly
- **Actionability** - Provide recommendations
- **Traceability** - Show sources and reasoning

## Example Use Cases

### Technology Evaluation
"Should we adopt WebAssembly for production?"
→ Spawns web-investigator (trends), codebase-analyzer (readiness), expert-synthesizer (opinions), deep-diver (implications), hypothesis-tester (risks)

### Architecture Decision
"Evaluate microservices migration"
→ Spawns web-investigator (industry patterns), codebase-analyzer (current architecture), expert-synthesizer (consensus), hypothesis-tester (risk assessment)

### Knowledge Gap Resolution
"Understand async patterns in Python"
→ Spawns web-investigator (best practices), codebase-analyzer (our examples), expert-synthesizer (expert guidance), deep-diver (concepts), hypothesis-tester (common pitfalls)

## Output Format

```
Research: [Topic]
Status: [Comprehensive / Partial / In Progress]

Key Findings:
1. [Finding 1] - Source: [agent names]
2. [Finding 2] - Source: [agent names]

Contradictions Found:
- [Area] - Agent A says [X], Agent B says [Y]

Recommendations:
1. [Action 1]
2. [Action 2]

Sources Consulted:
- Agent 1: [findings]
- Agent 2: [findings]
```

## Advanced Capabilities

- **Dynamic Agent Creation** - Spawn custom agents for specialized needs
- **Adaptive Spawning** - Adjust agents based on initial findings
- **Parallel Processing** - Maximize efficiency with concurrent analysis
- **Knowledge Integration** - Combine with existing memory

Use research coordination for powerful multi-perspective analysis and comprehensive decision-making.
