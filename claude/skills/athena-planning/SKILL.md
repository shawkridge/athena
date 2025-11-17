---
name: athena-planning-tools
description: >
  Use when planning tasks, estimating effort, breaking down projects, or monitoring progress.
  Automatically applies proven planning patterns to complex work, predicts task duration,
  detects deviations from estimates, and captures lessons learned.
  Triggers: "break down", "estimate", "how long", "plan", "sprint", "track progress",
  "decompose", "effort", "organize", "design sprint", "time estimate"
---

# Athena Planning & Execution Tools

Athena provides filesystem-based tools for intelligent task planning and execution monitoring. This skill enables automatic use of proven planning patterns, effort estimation, and progress tracking—reducing planning overhead and improving accuracy.

## Architecture: Filesystem-Based Code Execution

Following Anthropic's code execution with MCP paradigm, these tools are exposed as TypeScript modules in the `servers/athena/` directory. Rather than calling tools directly, Claude generates TypeScript code that:

1. **Imports** tools from `./servers/athena/`
2. **Calls** them within a code execution environment
3. **Filters and aggregates** results locally
4. **Returns only summaries** to context

This approach achieves **98.7% token reduction** compared to traditional tool calling, since intermediate data stays in the execution environment rather than passing through the model context.

## Available Tools

### `planning_recommendations`

Get proven planning strategy recommendations for tasks based on their characteristics.

**When to use:**
- User asks to "break down", "plan", "organize", or "design" a project
- Task is complex or multi-step
- Need to choose between different approaches (hierarchical vs iterative vs agile)

**Function: `recommend(input)`**
```typescript
interface RecommendationInput {
  taskId: number;
  taskDescription: string;
  taskType: "feature" | "bugfix" | "docs" | "refactor";
  complexity: number; // 1-10
  domain?: string;
  minSuccessRate?: number;
}

// Returns: PatternRecommendation[]
// {
//   patternName: string;
//   patternType: string;
//   successRate: number;
//   executionCount: number;
//   confidence: 'low' | 'medium' | 'high';
//   rationale: string;
//   alternatives?: string[];
// }
```

**Example:** Task is "Implement GraphQL API for user service", complexity 8
→ Returns: Hierarchical Decomposition (92% success), Test-Driven Development (88%), Incremental Integration (75%)

**Function: `getStrategyDetails(patternType)`**

Get detailed implementation steps for a specific pattern.

---

### `effort_prediction`

Predict how long a task will take based on type, description, and historical patterns.

**When to use:**
- User asks "how long", "estimate", "effort", or "workload"
- Planning sprints or allocating resources
- Need to understand time commitment

**Function: `predictEffort(input)`**
```typescript
interface EffortInput {
  taskType: "feature" | "bugfix" | "docs" | "refactor" | "research";
  description: string;
  complexity?: number;
  dependencies?: string[];
}

// Returns: { estimatedMinutes: number; confidence: number; factors: string[] }
```

**Example:** Task is "Write API documentation", type "docs"
→ Returns: 180 minutes (3 hours), 85% confidence, factors: ["complexity", "code size"]

---

### `deviation_monitor`

Detect tasks that are deviating from their time estimates and trigger replanning.

**When to use:**
- Monitoring ongoing work
- User asks "track progress", "detect problems", or "are we on track?"
- Task is running over estimate

**Function: `checkDeviation(taskId)`**

Check if a specific task is deviating from estimate.

**Function: `getActiveDeviations()`**

Get all tasks currently deviating from estimates.

**Function: `triggerReplanning(taskId)`**

Automatically replan a task that's off-track.

---

### `execution_feedback`

Record task completions and capture lessons learned to improve future estimates.

**When to use:**
- Task just completed
- Want to record what was learned
- Improve estimates for similar future tasks

**Function: `recordCompletion(input)`**
```typescript
interface CompletionFeedback {
  taskId: number;
  actualMinutes: number;
  success: boolean;
  blockers?: string[];
  lessonsLearned?: string;
}

// Returns: { variance: number; variancePercent: number; message: string }
```

---

### `trigger_management`

Create and manage conditions for automatic task activation.

**When to use:**
- Setting up complex task dependencies
- Automating task chains
- Creating event-driven workflows

**Function: `createTrigger(config)`**

Set up a condition that activates a task automatically.

**Function: `getTriggers()`**

List all active triggers.

---

## Usage Patterns

### Pattern 1: Plan a Complex Task

**Scenario:** User says "I need to redesign the authentication system. Can you plan it?"

**What Claude does:**

1. Recognizes "plan" + "redesign" matches skill
2. Writes TypeScript:
```typescript
import { recommend } from './servers/athena/planning_recommendations.ts';

const recs = await recommend({
  taskDescription: "Redesign authentication system",
  taskType: "feature",
  complexity: 8,
  domain: "backend"
});

const top = recs[0];
console.log(`Recommended: ${top.patternName} (${(top.successRate*100).toFixed(0)}% success rate)`);
console.log(`Rationale: ${top.rationale}`);
if (top.alternatives) {
  console.log(`Alternatives: ${top.alternatives.join(', ')}`);
}
```

3. Executes code (results stay local)
4. Returns summary to context: "Recommended: Hierarchical Decomposition (92% success rate). Rationale: Works well for architectural changes requiring careful planning..."
5. Uses recommendation to give detailed planning advice

**Token savings:** 50+ recommendations filtered to 1 summary = 99% reduction

---

### Pattern 2: Estimate Multiple Tasks

**Scenario:** User says "I have 4 features to implement. How long will they take?"

**What Claude does:**

1. Recognizes "how long" + "estimate" matches skill
2. Writes TypeScript:
```typescript
import { predictEffort } from './servers/athena/effort_prediction.ts';

const tasks = [
  "Implement user profiles",
  "Add email notifications",
  "Create admin dashboard",
  "Write API documentation"
];

const estimates = {};
let totalTime = 0;

for (const desc of tasks) {
  const prediction = await predictEffort({
    taskType: desc.includes("doc") ? "docs" : "feature",
    description: desc
  });
  estimates[desc] = prediction.estimatedMinutes;
  totalTime += prediction.estimatedMinutes;
}

console.log(`Total effort: ${totalTime} minutes (${(totalTime/480).toFixed(1)} days)`);
console.log(`Breakdown:`);
Object.entries(estimates).forEach(([task, mins]) => {
  console.log(`  ${task}: ${mins} min`);
});
```

3. Returns summary: "Total: 1200 minutes (2.5 days). Breakdown: profiles 360min, notifications 300min, dashboard 420min, docs 120min"
4. Uses this to create sprint plan

**Token savings:** All internal calculations stay local, only summary returned

---

### Pattern 3: Monitor Task Progress

**Scenario:** User says "Track progress on our current sprint. Are we on track?"

**What Claude does:**

1. Recognizes "track progress" matches skill
2. Calls `getActiveDeviations()` to find overrun tasks
3. For critical deviations, calls `triggerReplanning(taskId)`
4. Returns: "2 tasks on track, 1 overrunning by 35%. Triggered replanning for task #7"

---

## How This Skill Implements the Anthropic Pattern

This skill demonstrates the **filesystem-based code execution with MCP** paradigm:

### Progressive Disclosure
- **Metadata loaded at start** (~500 tokens): Name + description tells Claude when to use it
- **Full SKILL.md loaded on-demand** (~3K tokens): When skill activates
- **Tool definitions never in context** (~0 tokens): Agents read `.ts` files as needed
- **Results filtered locally** (~0 tokens): Intermediate data stays in execution environment

### Token Efficiency Example

**Traditional MCP approach (150K tokens):**
- Tool schemas in context: 100K
- Full recommendation lists: 30K
- Tool responses processing: 10K
- Model reasoning: 10K

**Filesystem code execution approach (2K tokens):**
- Metadata at startup: 0.5K
- Full SKILL.md: 1.2K
- Filtered summary to context: 0.3K
- **Savings: 98.7%**

### Code Generation Pattern

When Claude uses these tools, it:

1. **Discovers** tools by listing `./servers/athena/`
2. **Reads** specific `.ts` files to understand APIs
3. **Writes** TypeScript code that imports and calls them
4. **Executes** code with `bash` (via `tsx` or similar)
5. **Filters** results locally (no context overhead)
6. **Returns** only summary (50-500 tokens max)

This approach enables:
- **Massive token savings** (99%+ for tool-heavy operations)
- **Privacy preservation** (sensitive data stays in execution environment)
- **State management** (agents write files, resume across executions)
- **Better control flow** (native loops, conditionals, chaining)

---

## Implementation Details

### Tool Location
Tools are in `servers/athena/`:
- `planning_recommendations.ts` - Planning strategies
- `effort_prediction.ts` - Time estimates
- `deviation_monitor.ts` - Progress tracking
- `execution_feedback.ts` - Learning from completions
- `trigger_management.ts` - Task automation
- `index.ts` - Tool catalog and discovery

### Execution Environment
When Claude generates code to use these tools:
- Code is written to temporary file
- Executed with `bash` command (via `tsx` or `node`)
- Results captured and filtered
- Only summary returned to Claude

### Data Flow
```
User task → Skill metadata match → Full SKILL.md loaded → Code generated
    ↓
    Code imports tools from ./servers/athena/
    ↓
    Code executes locally (bash, tsx, etc.)
    ↓
    Results filtered in execution environment
    ↓
    Summary (300 tokens max) returned to Claude
    ↓
    Claude uses summary to answer user
```

---

## When NOT to Use This Skill

- Simple, single-task questions (no need for full planning arsenal)
- Real-time monitoring (designed for batch operations)
- Tasks already well-defined and underway (use deviation_monitor instead)

---

## Configuration

The tools in this skill connect to your Athena memory system. They currently return mock data but can be wired to real Athena operations by:

1. Connecting to your PostgreSQL backend
2. Calling actual Athena MCP tools (commented out in each `.ts` file)
3. Running the Athena memory server

See `servers/athena/index.ts` for the tool catalog and discoverable interface.

---

## References

- **Anthropic Article:** https://www.anthropic.com/engineering/code-execution-with-mcp
- **Code Execution Pattern:** Filesystem-based MCP with local filtering
- **Athena Memory System:** https://github.com/anthropics/athena
