/**
 * Test file for Athena Planning Skill
 *
 * This demonstrates how Claude Code would automatically use these tools
 * when you ask it to plan tasks.
 */

import { recommend } from '../servers/athena/planning_recommendations.ts';
import { predictEffort } from '../servers/athena/effort_prediction.ts';

/**
 * Example: Plan a feature implementation
 */
async function example1_PlanFeature() {
  console.log('='.repeat(60));
  console.log('EXAMPLE 1: Plan Feature Implementation');
  console.log('='.repeat(60));

  // Get recommendations for a complex feature
  const recs = await recommend({
    taskId: 1,
    taskDescription: "Implement GraphQL API for user service with authentication",
    taskType: "feature",
    complexity: 8,
    domain: "backend"
  });

  // Filter locally - keep only top 2
  const top2 = recs.slice(0, 2);

  console.log('\nRecommended Patterns for "GraphQL API with auth" (complexity 8):');
  top2.forEach((rec, i) => {
    console.log(`  ${i + 1}. ${rec.patternName} (${(rec.successRate * 100).toFixed(0)}% success)`);
    console.log(`     ${rec.rationale}`);
  });

  console.log('\n');
}

/**
 * Example: Estimate multiple tasks in a sprint
 */
async function example2_EstimateSprint() {
  console.log('='.repeat(60));
  console.log('EXAMPLE 2: Estimate Sprint Effort');
  console.log('='.repeat(60));

  const tasks = [
    { desc: "Implement user authentication system", type: "feature" },
    { desc: "Add email notification service", type: "feature" },
    { desc: "Write API documentation", type: "docs" },
    { desc: "Optimize database queries", type: "refactor" },
    { desc: "Fix login timeout bug", type: "bugfix" }
  ];

  console.log('\nEstimating 5 sprint tasks:');

  const estimates: Record<string, any> = {};
  let totalMinutes = 0;

  for (const task of tasks) {
    const est = await predictEffort({
      taskType: task.type,
      description: task.desc
    });

    estimates[task.desc] = est;
    totalMinutes += est.estimatedMinutes;

    const hours = (est.estimatedMinutes / 60).toFixed(1);
    const confidence = est.confidence.toUpperCase();
    console.log(`  • ${task.desc.substring(0, 40)}`);
    console.log(`    Estimate: ${est.estimatedMinutes}m (${hours}h) [${confidence}]`);
  }

  const days = (totalMinutes / 480).toFixed(1);
  console.log(`\n  TOTAL: ${totalMinutes} minutes (${days} days)`);
  console.log('\n');
}

/**
 * Example: Choose approach for a complex feature
 */
async function example3_ChooseApproach() {
  console.log('='.repeat(60));
  console.log('EXAMPLE 3: Choose Implementation Approach');
  console.log('='.repeat(60));

  // Get recommendations for different task types
  const scenarios = [
    { type: "feature", complexity: 9, desc: "Redesign authentication system" },
    { type: "bugfix", complexity: 3, desc: "Fix race condition in user cache" },
    { type: "docs", complexity: 5, desc: "Create API reference documentation" }
  ];

  for (const scenario of scenarios) {
    const recs = await recommend({
      taskId: 0,
      taskDescription: scenario.desc,
      taskType: scenario.type,
      complexity: scenario.complexity
    });

    const topRec = recs[0];
    console.log(`\nTask: "${scenario.desc}"`);
    console.log(`  Type: ${scenario.type}, Complexity: ${scenario.complexity}/10`);
    console.log(`  Recommended: ${topRec.patternName}`);
    console.log(`  Success Rate: ${(topRec.successRate * 100).toFixed(0)}%`);
  }

  console.log('\n');
}

/**
 * Example: Estimate with complexity factors
 */
async function example4_ComplexityFactors() {
  console.log('='.repeat(60));
  console.log('EXAMPLE 4: How Complexity Affects Estimates');
  console.log('='.repeat(60));

  const task = "Implement user authentication";
  const complexities = [2, 5, 8];

  console.log(`\nTask: "${task}" with different complexity levels:`);

  for (const complexity of complexities) {
    const est = await predictEffort({
      taskType: "feature",
      description: task,
      complexity
    });

    const hours = (est.estimatedMinutes / 60).toFixed(1);
    console.log(`  Complexity ${complexity}: ${est.estimatedMinutes}min (${hours}h)`);
  }

  console.log('\n');
}

/**
 * Main: Run all examples
 */
async function main() {
  try {
    console.log('\n');
    console.log('█'.repeat(60));
    console.log('ATHENA PLANNING SKILL - LIVE EXAMPLES');
    console.log('█'.repeat(60));
    console.log('\nThese examples show how Claude Code automatically uses');
    console.log('planning tools when you ask it to plan tasks.\n');

    await example1_PlanFeature();
    await example2_EstimateSprint();
    await example3_ChooseApproach();
    await example4_ComplexityFactors();

    console.log('█'.repeat(60));
    console.log('All examples completed successfully!');
    console.log('█'.repeat(60));
    console.log('\nKey takeaways:');
    console.log('  ✓ Recommendations adapt to task characteristics');
    console.log('  ✓ Estimates account for complexity and dependencies');
    console.log('  ✓ Confidence scores help manage uncertainty');
    console.log('  ✓ All data stays local, only summaries returned');
    console.log('\n');

  } catch (error) {
    console.error('Error running examples:', error);
    process.exit(1);
  }
}

// Run examples
main().catch(console.error);
