# Agents, Commands, and Skills Guide for Athena

Complete guide to using agents, slash commands, and skills in the Athena knowledge management system.

## Overview

The Athena system provides three levels of automation and specialization:

| Feature | Triggers | Scope | Best For |
|---------|----------|-------|----------|
| **Agents** | Explicit (use @agent-name) | Specialized domains | Complex, multi-step workflows requiring expertise |
| **Commands** | Slash (user types /command) | Single operations | Frequent, well-defined operations |
| **Skills** | Automatic (Claude decides) | Complex workflows | Sophisticated patterns Claude should recognize autonomously |

## Agents

### Available Agents

1. **memory-operator** - Memory management and recall optimization
2. **planning-orchestrator** - Task planning and decomposition
3. **consolidation-analyst** - Pattern extraction and learning
4. **knowledge-architect** - Knowledge graph design and management
5. **retrieval-specialist** - Advanced RAG and context enrichment
6. **code-analyzer** - Code structure and impact analysis

### How to Use Agents

Explicitly invoke agents in your requests:

```
@memory-operator - help me recall project architecture patterns
@planning-orchestrator - plan the implementation of feature X
@consolidation-analyst - analyze what we learned from the last project
@knowledge-architect - design the knowledge graph for our domain
@retrieval-specialist - find comprehensive context on authentication systems
@code-analyzer - analyze the impact of refactoring this module
```

### Agent Design Principles

**Single Responsibility**
- Each agent has clear, focused expertise
- Avoid agents that try to do everything
- Delegate to specialized agents when needed

**Deep Domain Knowledge**
- Agents include detailed instructions for their domain
- They understand best practices and patterns
- They can guide you through complex processes

**Tool Access**
- Agents are granted specific tools appropriate to their role
- This ensures focus and prevents misuse
- Tools are documented in each agent definition

**Proactive Guidance**
- Agents offer suggestions and improvements
- They explain their reasoning
- They help you learn best practices

### Creating New Agents

To create a new agent:

1. Create `.claude/agents/agent-name.md` with YAML frontmatter:
```markdown
---
name: agent-name
description: What this agent specializes in
tools:
  - Bash
  - Read
  - Grep
  - Glob
model: sonnet
---

# Agent Name

Your role is to...

## Key Responsibilities

- Responsibility 1
- Responsibility 2

## Tools Available

- Tool 1: description
- Tool 2: description

## Best Practices

1. Practice 1
2. Practice 2
```

2. Use clear, actionable language
3. Include examples of workflows
4. Document success criteria
5. Add to git version control

### Agent Best Practices

- **Be Specific** - Use `@agent-name` with clear context
- **Provide Context** - Explain what you're trying to achieve
- **Ask Questions** - Let agents guide you through decisions
- **Leverage Expertise** - Use agents for their specialized knowledge
- **Chain Agents** - Use multiple agents for complex problems

## Slash Commands

### Available Commands

1. `/recall-memory` - Search memories with semantic search
2. `/consolidate-memory` - Run consolidation on episodic events
3. `/plan-task` - Decompose and plan tasks
4. `/search-knowledge` - Advanced semantic search
5. `/analyze-code` - Deep code analysis
6. `/check-health` - System health diagnostics
7. `/extract-patterns` - Pattern extraction from events

### Using Commands

Type a slash and command name with arguments:

```
/recall-memory "authentication patterns"
/consolidate-memory balanced 14
/plan-task "Implement feature X" 4
/search-knowledge "deployment strategies" "reflective"
/analyze-code src/athena/manager.py dependencies
/check-health consolidation
/extract-patterns 7 temporal
```

### Command Design

Commands work best for:
- **Frequent Operations** - Tasks users do regularly
- **Well-Defined Inputs** - Clear parameters
- **Quick Execution** - Fast operations
- **Simple Workflows** - Single-step operations

### Creating New Commands

To create a new command:

1. Create `.claude/commands/command-name.md` with YAML frontmatter:
```markdown
---
description: What this command does
allowed-tools: Bash(curl), Read
argument-hint: "[param1] [optional: param2]"
---

# Description and usage

Parameter 1: $1
Parameter 2: $2 (optional)

Example usage:
- `/command-name "example"` - What this does
```

2. Keep descriptions concise
3. Document parameters clearly
4. Provide examples
5. Specify allowed tools

### Command Best Practices

- **Short Names** - Easy to remember and type
- **Clear Arguments** - Document what each parameter does
- **Predictable Behavior** - Users should know what will happen
- **Fast Feedback** - Commands should complete quickly
- **Error Handling** - Graceful failures with helpful messages

## Skills

### Available Skills

1. **memory-quality-assessment** - Evaluate memory system quality
2. **consolidation-optimization** - Optimize consolidation strategy
3. **code-impact-analysis** - Predict code change impacts
4. **planning-validation** - Validate plans with Q* and scenarios
5. **knowledge-discovery** - Discover knowledge through graph exploration

### How Skills Work

Skills are automatically invoked by Claude based on context. When you discuss topics like:
- Memory quality → `memory-quality-assessment` activates
- Learning and consolidation → `consolidation-optimization` activates
- Code changes → `code-impact-analysis` activates
- Planning → `planning-validation` activates
- Knowledge exploration → `knowledge-discovery` activates

### Skill Design Principles

**Autonomous Invocation**
- Skills activate automatically when relevant
- Claude decides when to use them
- No explicit user invocation needed
- Based on conversation context

**Sophisticated Workflows**
- Skills handle complex, multi-step processes
- They provide comprehensive analysis
- They offer detailed recommendations
- They explain their reasoning

**Clear Scope**
- Each skill has a well-defined purpose
- Skills can call agents or commands
- Skills don't duplicate agent functionality
- Skills focus on analysis and decision-making

### Creating New Skills

To create a new skill:

1. Create `.claude/skills/skill-name/SKILL.md`:
```markdown
---
name: skill-name
description: What this skill does and when to use it
---

# Skill Name

## What This Skill Does

- Action 1
- Action 2

## When to Use

Automatically triggered when:
- Condition 1
- Condition 2

## Output

What this skill provides...

## Example Scenarios

Scenario 1: ...
Scenario 2: ...
```

2. Write clear descriptions
3. List triggers clearly
4. Document outputs
5. Provide example scenarios

### Skill Best Practices

- **Focused Purpose** - One primary function
- **Comprehensive** - Handle complete workflows
- **Smart Triggering** - Clear activation conditions
- **Value-Added** - Provide insights beyond basic operations
- **Documentation** - Help users understand when you activate

## Integration Patterns

### Using Agents + Commands

```
User: /plan-task "Build authentication"
Command: Creates initial task breakdown
User: @planning-orchestrator refine this plan considering our team capacity
Agent: Provides detailed refinement with expertise
```

### Using Commands + Skills

```
User: /check-health memory
Command: Returns health metrics
Skill (memory-quality-assessment): Automatically analyzes metrics
Skill: Provides quality assessment and recommendations
```

### Using Agents + Skills

```
User: @consolidation-analyst help optimize consolidation
Agent: Analyzes current event state
Skill (consolidation-optimization): Activates with recommendations
Skill: Suggests optimal strategy
Agent: Executes consolidation with expert guidance
```

## HTTP Tools Endpoint

All tools are also available via HTTP at `http://localhost:3000`:

```bash
# Discover available tools
curl http://localhost:3000/tools/discover

# Get tool definition
curl http://localhost:3000/tools/{tool_name}

# Execute tool
curl -X POST http://localhost:3000/tools/{tool_name}/execute \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'
```

## Best Practices Summary

### For Agents
✓ Use when you need specialized expertise
✓ Provide context and goals
✓ Let agents guide complex decisions
✓ Ask them to explain their reasoning

### For Commands
✓ Use for frequent operations
✓ Keep parameters simple
✓ Expect quick execution
✓ Stack multiple commands for workflows

### For Skills
✓ Claude will invoke automatically
✓ Discuss relevant topics naturally
✓ Trust skill activations
✓ Follow skill recommendations

## Architecture

```
Claude Code
    ├── Agents (explicit invocation)
    │   ├── memory-operator
    │   ├── planning-orchestrator
    │   ├── consolidation-analyst
    │   ├── knowledge-architect
    │   ├── retrieval-specialist
    │   └── code-analyzer
    │
    ├── Slash Commands (user-invoked)
    │   ├── recall-memory
    │   ├── consolidate-memory
    │   ├── plan-task
    │   ├── search-knowledge
    │   ├── analyze-code
    │   ├── check-health
    │   └── extract-patterns
    │
    ├── Skills (auto-invoked)
    │   ├── memory-quality-assessment
    │   ├── consolidation-optimization
    │   ├── code-impact-analysis
    │   ├── planning-validation
    │   └── knowledge-discovery
    │
    └── HTTP Tools (programmatic)
        └── 150+ tools across 19 categories
            ├── Memory operations
            ├── Episodic events
            ├── Knowledge graph
            ├── Planning & validation
            ├── Task management
            ├── Consolidation
            ├── Procedural learning
            ├── RAG & retrieval
            ├── Monitoring
            ├── Spatial analysis
            └── ...and more
```

## Key Insights

1. **Agents** are your experts - use them for complex, nuanced problems
2. **Commands** are your shortcuts - use them for frequent operations
3. **Skills** are your AI partner - let Claude use them intelligently
4. **HTTP Tools** are your API - use for programmatic access

Together, they create a powerful system for knowledge management and task execution.

## Next Steps

1. Try invoking agents with `@agent-name`
2. Explore commands with `/command-name --help`
3. Watch skills activate in natural conversations
4. Use HTTP tools programmatically for custom workflows
5. Create new agents/commands/skills for your specific needs

Remember: The system works best when you combine all three levels of automation!
