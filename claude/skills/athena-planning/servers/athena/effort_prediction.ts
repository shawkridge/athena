/**
 * Effort Prediction Tool Wrapper
 *
 * Agents use this to get effort estimates for new tasks.
 * Filesystem-based MCP paradigm.
 */

export interface PredictionResult {
  estimatedMinutes: number;
  confidence: 'low' | 'medium' | 'high';
  confidenceScore: number;
  biasFacto: number;
  estimatedRange: {
    min: number;
    max: number;
  };
}

/**
 * Predict effort for a task
 *
 * Example agent usage:
 * ```typescript
 * import { predictEffort } from './servers/athena/effort_prediction.ts';
 *
 * const estimate = await predictEffort({
 *   taskType: "feature",
 *   description: "Implement user authentication"
 * });
 * console.log(`Estimated: ${estimate.estimatedMinutes}m (±${estimate.estimatedRange.max - estimate.estimatedRange.min}m)`);
 * ```
 */
export async function predictEffort(input: {
  taskType: string;
  description: string;
  complexity?: number;
}): Promise<PredictionResult> {
  // TODO: Connect to real Athena backend via MCP
  // return callMCPTool('effort:predict', input);

  // Smart estimation based on task characteristics
  const estimate = _estimateEffort(input);
  return estimate;
}

/**
 * Internal: Estimate effort based on task characteristics
 */
function _estimateEffort(input: {
  taskType: string;
  description: string;
  complexity?: number;
}): PredictionResult {
  const { taskType, description, complexity = 5 } = input;

  // Base estimates (in minutes) by task type
  const baseEstimates: Record<string, number> = {
    feature: 480,      // 8 hours
    bugfix: 180,       // 3 hours
    docs: 240,         // 4 hours
    refactor: 300,     // 5 hours
    research: 360      // 6 hours
  };

  let estimateMinutes = baseEstimates[taskType] || 300;

  // Adjust for complexity (5 is baseline)
  const complexityFactor = complexity / 5;
  estimateMinutes = Math.round(estimateMinutes * complexityFactor);

  // Adjust for description keywords
  const desc = description.toLowerCase();
  let confidenceScore = 0.75;

  if (desc.includes("api") || desc.includes("integration")) {
    estimateMinutes = Math.round(estimateMinutes * 1.3);
  }

  if (desc.includes("database") || desc.includes("migration")) {
    estimateMinutes = Math.round(estimateMinutes * 1.4);
    confidenceScore -= 0.1;
  }

  if (desc.includes("authentication") || desc.includes("security")) {
    estimateMinutes = Math.round(estimateMinutes * 1.5);
    confidenceScore -= 0.15;
  }

  if (desc.includes("performance") || desc.includes("optimization")) {
    estimateMinutes = Math.round(estimateMinutes * 1.2);
    confidenceScore -= 0.1;
  }

  if (desc.includes("test") || desc.includes("unit")) {
    estimateMinutes = Math.round(estimateMinutes * 0.8);
  }

  // Ensure reasonable bounds
  estimateMinutes = Math.max(30, Math.min(2880, estimateMinutes)); // 30 mins to 2 days

  // Increase confidence for well-defined tasks
  if (description.length > 50) {
    confidenceScore = Math.min(0.9, confidenceScore + 0.1);
  }

  confidenceScore = Math.max(0.5, Math.min(1.0, confidenceScore));

  // Calculate confidence label
  let confidence: 'low' | 'medium' | 'high';
  if (confidenceScore >= 0.8) {
    confidence = 'high';
  } else if (confidenceScore >= 0.6) {
    confidence = 'medium';
  } else {
    confidence = 'low';
  }

  // Calculate range (±20% for high confidence, ±30% for medium, ±40% for low)
  const variance = confidence === 'high' ? 0.2 : confidence === 'medium' ? 0.3 : 0.4;
  const rangeMargin = Math.round(estimateMinutes * variance);

  return {
    estimatedMinutes: estimateMinutes,
    confidence,
    confidenceScore,
    biasFacto: 1.05, // Typical estimation bias in software projects
    estimatedRange: {
      min: Math.max(30, estimateMinutes - rangeMargin),
      max: Math.min(2880, estimateMinutes + rangeMargin)
    }
  };
}
