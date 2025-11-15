/**
 * Phase 3 Task Management TypeScript Interfaces
 *
 * Defines types for:
 * - Phase 3a: Task Dependencies + Metadata
 * - Phase 3b: Workflow Patterns & Suggestions
 * - Phase 3c: Predictive Effort Estimation
 */

// ============================================================================
// TASK STATUS & METADATA (Phase 3a)
// ============================================================================

export type TaskStatus = 'pending' | 'active' | 'in_progress' | 'completed' | 'blocked' | 'cancelled'
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'
export type TaskPhase = 'planning' | 'plan_ready' | 'executing' | 'verifying' | 'completed' | 'failed' | 'abandoned'

/**
 * Represents a single task with all metadata from Athena prospective memory
 */
export interface Task {
  id: number | string
  project_id?: number
  content: string // Task description
  active_form?: string // Present continuous tense description
  title?: string // Alternative to content

  // Status & Priority
  status: TaskStatus
  priority: TaskPriority
  phase?: TaskPhase

  // Timing
  created_at?: string
  due_at?: string
  completed_at?: string
  started_at?: string

  // Assignment
  assignee?: string // 'user' | 'claude' | 'sub-agent:name'

  // Metadata
  notes?: string
  blocked_reason?: string
  failure_reason?: string
  lessons_learned?: string
}

/**
 * Task with full enriched metadata (dependencies, effort, complexity)
 */
export interface EnrichedTask extends Task {
  // Dependencies & Blockers
  dependencies: number[] // Task IDs this task depends on
  blockers: number[] // Task IDs blocking this task
  blocked: boolean // Whether task is currently blocked

  // Effort Tracking
  effort_estimate?: number // Estimated minutes
  effort_actual?: number // Actual minutes spent
  accuracy_percent?: number // Estimate accuracy (0-100)

  // Complexity & Metadata
  complexity_score?: number // 1-10 scale
  priority_score?: number // 1-10 scale
  tags?: string[] // Topic tags
}

/**
 * Task dependency relationship
 */
export interface TaskDependency {
  from_task_id: number
  to_task_id: number
  dependency_type: 'blocks' | 'related' | 'enables'
  blocking_task?: Task // Populated if fetching full details
}

/**
 * Task metadata for analytics and tracking
 */
export interface TaskMetadata {
  task_id: number
  project_id: number
  effort_estimate?: number
  effort_actual?: number
  complexity_score?: number
  priority_score?: number
  tags?: string[]
  accuracy_percent?: number
  variance_minutes?: number
  started_at?: string
  completed_at?: string
}

/**
 * Task plan/execution blueprint
 */
export interface TaskPlan {
  id?: number
  task_id: number
  steps: string[] // Ordered list of steps
  estimated_duration_minutes: number
  created_at?: string
  validated?: boolean
  validation_notes?: string
}

// ============================================================================
// EFFORT PREDICTIONS (Phase 3c)
// ============================================================================

/**
 * Effort prediction with confidence and range
 */
export interface EffortPrediction {
  task_id: number
  predicted_effort: number // Minutes
  base_estimate: number // Original estimate
  confidence: number // 0.0-1.0, higher = more reliable

  // Effort range (PERT)
  range?: {
    optimistic: number // Best case (minutes)
    expected: number // Most likely (minutes)
    pessimistic: number // Worst case (minutes)
  }

  // Historical accuracy
  historical_accuracy?: number // 0.0-1.0
  bias_factor?: number // 1.0 = accurate, >1.0 = underestimate, <1.0 = overestimate
  sample_count?: number // How many similar tasks

  // Explanation
  explanation?: string
  task_type?: string // feature, bugfix, test, etc.
}

/**
 * Aggregated effort predictions for multiple tasks
 */
export interface PredictionsResponse {
  total_predictions: number
  predictions: EffortPrediction[]
  summary: {
    avg_confidence: number
    total_predicted_effort: number
  }
  timestamp: string
  source?: string
}

// ============================================================================
// WORKFLOW PATTERNS & SUGGESTIONS (Phase 3b)
// ============================================================================

/**
 * Task suggestion based on workflow patterns
 */
export interface TaskSuggestion {
  task_id: number | string
  task_name: string
  reason: string // Why this task is suggested
  confidence: number // 0.0-1.0
  pattern_frequency: number // How often this pattern occurs
  expected_next_task?: number // Task typically following this one
}

/**
 * Suggested tasks response
 */
export interface SuggestionsResponse {
  completed_task: number | null
  total_suggestions: number
  suggestions: TaskSuggestion[]
  process_maturity: 'low' | 'medium' | 'high' // Based on pattern consistency
  timestamp: string
  source?: string
}

/**
 * Workflow pattern (transition between task types)
 */
export interface WorkflowPattern {
  from_task_type: string
  to_task_type: string
  frequency: number // How many times observed
  confidence: number // 0.0-1.0
  avg_duration_hours?: number
}

/**
 * Typical workflow sequence for a task type
 */
export interface WorkflowSequence {
  task_type: string
  workflow_sequence: string[] // List of typical task types in order
  confidence_avg: number // Average confidence of sequence
  avg_duration_hours: number
  task_count: number // How many times observed
}

// ============================================================================
// TASK STATUS RESPONSE (Combines 3a data)
// ============================================================================

/**
 * Complete task status with dependencies and metadata
 */
export interface TaskStatusResponse {
  total_tasks: number
  tasks: EnrichedTask[]
  timestamp: string
  source?: string
}

// ============================================================================
// PROJECT & MILESTONE TYPES
// ============================================================================

/**
 * Milestone representing a project checkpoint
 */
export interface Milestone {
  id: number
  project_id: number
  name: string
  description?: string
  due_date: string
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled'

  // Progress tracking
  progress_percent: number // 0-100
  completed_tasks: number
  total_tasks: number

  // Metadata
  created_at: string
  completed_at?: string
}

/**
 * Project with milestones and task organization
 */
export interface Project {
  id: number
  name: string
  description?: string
  status: 'active' | 'paused' | 'completed' | 'archived'

  // Progress tracking
  progress_percent: number
  total_tasks: number
  completed_tasks: number

  // Milestones
  milestones?: Milestone[]

  // Effort
  total_effort_estimate?: number
  total_effort_actual?: number

  // Timing
  created_at: string
  start_date?: string
  target_end_date?: string
  completed_at?: string
}

/**
 * Project analytics from metadata
 */
export interface ProjectAnalytics {
  project_id: number
  total_tasks: number
  completed_tasks: number
  in_progress_tasks: number
  blocked_tasks: number

  // Effort tracking
  avg_estimate: number
  avg_actual: number
  estimation_accuracy: number // 0.0-1.0

  // Complexity
  avg_complexity: number
  complexity_distribution: Record<string, number> // Histogram

  // Trends
  velocity: number // Tasks per day
  trend: 'improving' | 'stable' | 'degrading'
}

// ============================================================================
// API RESPONSE TYPES
// ============================================================================

/**
 * Generic API response wrapper
 */
export interface ApiResponse<T> {
  data: T
  timestamp: string
  status: 'success' | 'error'
  message?: string
}

/**
 * Error response
 */
export interface ErrorResponse {
  detail: string
  timestamp: string
  status_code: number
}

// ============================================================================
// HOOK TYPES (for React hooks)
// ============================================================================

/**
 * Hook result for useTask
 */
export interface UseTaskResult {
  task: EnrichedTask | null
  loading: boolean
  error: string | null
  refetch: () => void
}

/**
 * Hook result for useTasks
 */
export interface UseTasksResult {
  tasks: EnrichedTask[]
  loading: boolean
  error: string | null
  total: number
  refetch: () => void
}

/**
 * Hook result for usePredictions
 */
export interface UsePredictionsResult {
  predictions: EffortPrediction[]
  loading: boolean
  error: string | null
  summary: PredictionsResponse['summary']
  refetch: () => void
}

/**
 * Hook result for useSuggestions
 */
export interface UseSuggestionsResult {
  suggestions: TaskSuggestion[]
  loading: boolean
  error: string | null
  processMaturity: 'low' | 'medium' | 'high'
  refetch: () => void
}
