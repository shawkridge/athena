/**
 * Agent Code Template: Planning & Effort Estimation
 *
 * This template shows the pattern Claude should follow when writing code
 * to invoke Athena planning tools.
 *
 * Key principles:
 * 1. Import tools from ./servers/athena/
 * 2. Filter and aggregate results LOCALLY (not in context)
 * 3. Return only summary via console.log()
 * 4. Keep intermediate data out of model context
 */

// ============================================================================
// EXAMPLE 1: Get Planning Recommendation for a Task
// ============================================================================

import { recommend } from './servers/athena/planning_recommendations.ts';

async function planComplexTask() {
  const recommendation = await recommend({
    taskId: 1,
    taskDescription: "Implement GraphQL API for user service",
    taskType: "feature",
    complexity: 8,
    domain: "backend"
  });

  // FILTER LOCALLY - keep only top recommendation
  const topRec = recommendation[0];

  // RETURN ONLY SUMMARY to context
  console.log(`Recommended: ${topRec.patternName}`);
  console.log(`Success Rate: ${(topRec.successRate * 100).toFixed(0)}%`);
  console.log(`Rationale: ${topRec.rationale}`);
  if (topRec.alternatives && topRec.alternatives.length > 0) {
    console.log(`Alternatives: ${topRec.alternatives.join(', ')}`);
  }
}

// ============================================================================
// EXAMPLE 2: Estimate Multiple Tasks (Batch Processing)
// ============================================================================

import { predictEffort } from './servers/athena/effort_prediction.ts';

async function estimateSprint() {
  const tasks = [
    { name: "Implement user profiles", type: "feature" as const },
    { name: "Add email notifications", type: "feature" as const },
    { name: "Create admin dashboard", type: "feature" as const },
    { name: "Write API documentation", type: "docs" as const }
  ];

  const estimates: Record<string, number> = {};
  let totalMinutes = 0;

  // Process each task locally
  for (const task of tasks) {
    const prediction = await predictEffort({
      taskType: task.type,
      description: task.name
    });

    estimates[task.name] = prediction.estimatedMinutes;
    totalMinutes += prediction.estimatedMinutes;
  }

  // Aggregate locally, return summary only
  const days = (totalMinutes / 480).toFixed(1);
  console.log(`Total Sprint Effort: ${totalMinutes} minutes (${days} days)`);
  console.log(`\nBreakdown:`);

  // Keep only top 5 items in summary (filter locally)
  Object.entries(estimates)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .forEach(([task, minutes]) => {
      const hours = (minutes / 60).toFixed(1);
      console.log(`  ${task}: ${minutes}min (${hours}h)`);
    });
}

// ============================================================================
// EXAMPLE 3: Monitor Deviations and Trigger Replanning
// ============================================================================

import { getActiveDeviations, triggerReplanning } from './servers/athena/deviation_monitor.ts';

async function monitorProgress() {
  // Get all deviations (stays local)
  const deviations = await getActiveDeviations();

  // Filter LOCALLY for critical issues
  const critical = deviations.filter(d => d.deviationPercent > 50);
  const moderate = deviations.filter(d => d.deviationPercent > 20 && d.deviationPercent <= 50);

  // Return summary only
  console.log(`Task Status:`);
  console.log(`  On Track: ${deviations.length - critical.length - moderate.length}`);
  console.log(`  Moderate Deviation: ${moderate.length}`);
  console.log(`  Critical Deviation: ${critical.length}`);

  // Auto-replan critical tasks (still stays local)
  if (critical.length > 0) {
    console.log(`\nReplanning ${critical.length} critical tasks...`);
    for (const deviation of critical) {
      const result = await triggerReplanning(deviation.taskId);
      console.log(`  Task #${deviation.taskId}: ${result.message}`);
    }
  }
}

// ============================================================================
// EXAMPLE 4: Comprehensive Sprint Planning
// ============================================================================

async function planSprint() {
  // Step 1: Get recommendations for overall sprint approach
  const planRec = await recommend({
    taskId: 0,
    taskDescription: "Implement 4 features in 2-week sprint",
    taskType: "feature",
    complexity: 6
  });

  // Step 2: Estimate each task
  const tasks = [
    "User authentication system",
    "Database optimization",
    "API rate limiting",
    "Admin monitoring dashboard"
  ];

  const estimates: Record<string, number> = {};
  for (const task of tasks) {
    const pred = await predictEffort({
      taskType: "feature",
      description: task
    });
    estimates[task] = pred.estimatedMinutes;
  }

  // Step 3: Allocate to days (LOCAL aggregation)
  const daysAvailable = 10; // 2 weeks
  const minutesPerDay = 480;
  let currentDay = 1;
  let dayTime = 0;
  const allocation: Record<number, string[]> = {};

  for (const [task, minutes] of Object.entries(estimates)) {
    if (dayTime + minutes > minutesPerDay) {
      currentDay++;
      dayTime = 0;
    }
    if (!allocation[currentDay]) allocation[currentDay] = [];
    allocation[currentDay].push(task);
    dayTime += minutes;
  }

  // Step 4: Return SUMMARY only
  console.log(`Sprint Plan: ${planRec[0].patternName}`);
  console.log(`Total Effort: ${Object.values(estimates).reduce((a, b) => a + b, 0)} minutes`);
  console.log(`\nDay-by-Day Allocation:`);
  Object.entries(allocation).forEach(([day, taskList]) => {
    console.log(`  Day ${day}: ${taskList.length} tasks`);
  });
}

// ============================================================================
// Pattern: Always follow this structure
// ============================================================================

/*
1. IMPORT tools from ./servers/athena/
   import { functionName } from './servers/athena/tool-name.ts';

2. CALL tool functions with appropriate parameters
   const result = await functionName(params);

3. FILTER locally (aggregation, sorting, limiting)
   const filtered = result.filter(r => r.confidence > 0.8);
   const top = filtered.slice(0, 3);

4. RETURN summary via console.log()
   console.log(`Summary: ...`);

5. DO NOT return full data structures
   // ❌ WRONG: console.log(JSON.stringify(result));
   // ✅ RIGHT: console.log(`Found ${result.length} recommendations`);
*/

// ============================================================================
// Execution
// ============================================================================

// Uncomment the function you want to run:
// planComplexTask().catch(console.error);
// estimateSprint().catch(console.error);
// monitorProgress().catch(console.error);
// planSprint().catch(console.error);
