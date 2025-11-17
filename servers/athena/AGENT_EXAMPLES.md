# Agent Usage Examples - Filesystem-Based MCP Tools

Following Anthropic's paradigm for 98.7% token reduction:
- Tool definitions NOT in context (stored as files)
- Agents discover via filesystem exploration
- Agents import and call functions in code
- Data stays in execution environment
- Only summaries return to context

## Pattern 1: Get Planning Recommendations for Multiple Tasks

**Agent discovers tools:**
```bash
ls ./servers/athena/
cat ./servers/athena/planning_recommendations.ts
```

**Agent code (filters locally):**
```typescript
import { recommend } from './servers/athena/planning_recommendations.ts';

const tasks = [
  { id: 1, desc: "Implement API", type: "feature", complexity: 7 },
  { id: 2, desc: "Write docs", type: "docs", complexity: 3 },
  { id: 3, desc: "Fix bug", type: "bugfix", complexity: 5 }
];

const recommendations = {};
for (const task of tasks) {
  const recs = await recommend({
    taskId: task.id,
    taskDescription: task.desc,
    taskType: task.type,
    complexity: task.complexity
  });
  // Agent filters locally - keep only TOP recommendation
  recommendations[task.id] = recs[0].patternName;
}

console.log("Task recommendations:");
Object.entries(recommendations).forEach(([taskId, pattern]) => {
  console.log(`  Task ${taskId}: ${pattern}`);
});
```

**What goes to context:**
```
Task recommendations:
  Task 1: Hierarchical Decomposition
  Task 2: Documentation Pattern
  Task 3: Test-Driven Bug Fix
```

**Token cost WITHOUT paradigm:** 50,000 tokens (all 9 recommendations for 3 tasks)
**Token cost WITH paradigm:** 200 tokens (just the output)
**Savings:** 99.6%

---

## Pattern 2: Detect Deviations and Trigger Replanning

**Agent code:**
```typescript
import { checkDeviation, triggerReplanning } from './servers/athena/deviation_monitor.ts';
import { getActiveDeviations } from './servers/athena/deviation_monitor.ts';

// Get all tasks that are deviating
const deviations = await getActiveDeviations();

// Agent decides locally which ones to replan
const criticalDeviations = deviations.filter(
  d => d.deviationPercent > 50 && d.recommendedAction === 'replan'
);

console.log(`Found ${deviations.length} deviations, ${criticalDeviations.length} critical`);

// Trigger replanning only for critical ones
for (const deviation of criticalDeviations) {
  const result = await triggerReplanning(deviation.taskId);
  console.log(`Replanning task ${deviation.taskId}: ${result.message}`);
}
```

**What goes to context:**
```
Found 5 deviations, 2 critical
Replanning task 3: Replanning triggered
Replanning task 7: Replanning triggered
```

**Token savings:** Deviation details stay local, only summary returns

---

## Pattern 3: Record Feedback Batch and Update Learning

**Agent code:**
```typescript
import { recordCompletion } from './servers/athena/execution_feedback.ts';

const completedTasks = [
  { taskId: 1, actualMinutes: 140, success: true, lessons: "API simpler than expected" },
  { taskId: 2, actualMinutes: 45, success: true, lessons: "Docs took less time with template" },
  { taskId: 3, actualMinutes: 95, success: false, blockers: ["DB connection issues"] }
];

const results = [];
for (const task of completedTasks) {
  const feedback = await recordCompletion({
    taskId: task.taskId,
    actualMinutes: task.actualMinutes,
    success: task.success,
    lessonsLearned: task.lessons
  });
  results.push(feedback);
}

// Agent aggregates locally
const avgVariance = results.reduce((sum, r) => sum + r.variancePercent, 0) / results.length;
console.log(`Processed ${results.length} completions`);
console.log(`Average variance: ${avgVariance.toFixed(1)}%`);
console.log(`Learning system updated`);
```

**What goes to context:**
```
Processed 3 completions
Average variance: 5.8%
Learning system updated
```

**Benefits:**
- All completion data stays in execution environment
- Only aggregated summary goes to context
- Learning happens without bloating context window

---

## Pattern 4: Intelligent Task Batching with Effort Prediction

**Agent code:**
```typescript
import { predictEffort } from './servers/athena/effort_prediction.ts';

const newTasks = [
  "Implement authentication system",
  "Write user guide",
  "Fix login bug",
  "Optimize database queries"
];

const estimates = {};
let totalTime = 0;

for (const description of newTasks) {
  // Infer task type from description
  const taskType = description.includes("guide") ? "docs"
                  : description.includes("bug") ? "bugfix"
                  : "feature";

  const prediction = await predictEffort({
    taskType,
    description
  });

  estimates[description] = prediction.estimatedMinutes;
  totalTime += prediction.estimatedMinutes;
}

// Agent groups tasks to fit in working day (480 minutes)
const grouped = { day1: [], day2: [], day3: [] };
let currentDay = 'day1';
let dayTime = 0;

for (const [desc, minutes] of Object.entries(estimates)) {
  if (dayTime + minutes > 480) {
    currentDay = currentDay === 'day1' ? 'day2' : 'day3';
    dayTime = 0;
  }
  grouped[currentDay].push(desc);
  dayTime += minutes;
}

console.log("Recommended task schedule:");
Object.entries(grouped).forEach(([day, tasks]) => {
  if (tasks.length > 0) {
    console.log(`${day}: ${tasks.length} tasks`);
  }
});
console.log(`Total estimated time: ${totalTime} minutes`);
```

**What goes to context:**
```
Recommended task schedule:
day1: 2 tasks
day2: 2 tasks
Total estimated time: 485 minutes
```

**Token savings:** All estimates stay local, agent decides scheduling, only output to context

---

## Key Principles

1. **Discovery**: Agent explores `./servers/athena/` to find tools
2. **Import**: Agent reads `.ts` files and imports functions
3. **Processing**: Agent calls functions, processes results LOCALLY
4. **Filtering**: Agent decides what to keep, what to discard
5. **Summary**: Only aggregated/filtered output returns to context

## Architecture Benefit

```
Old approach (handler-based):
  • Tool schemas in context: 100K tokens
  • Full results in context: 50K tokens
  • Model reasoning overhead: 10K tokens
  Total: 160K tokens

New approach (filesystem-based):
  • Tool definitions: 0 tokens (in files)
  • Filtered summary: 1K tokens
  • Model reasoning: 1K tokens
  Total: 2K tokens

Token reduction: 98.7%
```

This is why Anthropic's filesystem-based MCP paradigm is so powerful: the agent does all the heavy lifting (discovery, filtering, aggregation) outside of the context window, and only returns tiny summaries.
