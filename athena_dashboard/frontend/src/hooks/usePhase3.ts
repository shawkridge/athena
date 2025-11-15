/**
 * Custom React hooks for Phase 3 task management
 *
 * Provides easy access to:
 * - Task status and dependencies
 * - Effort predictions
 * - Task suggestions from workflow patterns
 */

import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  EnrichedTask,
  EffortPrediction,
  TaskSuggestion,
  TaskStatusResponse,
  PredictionsResponse,
  SuggestionsResponse,
  UseTasksResult,
  UsePredictionsResult,
  UseSuggestionsResult,
} from '@/types/phase3'

const API_BASE = process.env.VITE_API_URL || 'http://localhost:8000/api'

// ============================================================================
// TASK STATUS HOOK (Phase 3a)
// ============================================================================

/**
 * Hook to fetch tasks with full metadata (dependencies, effort, complexity)
 *
 * @param projectId - Optional project filter
 * @param status - Optional status filter
 * @param autoRefresh - Refetch interval in seconds (0 = no auto-refresh)
 */
export function useTasks(
  projectId?: number,
  status?: string,
  autoRefresh: number = 0
): UseTasksResult {
  const [tasks, setTasks] = useState<EnrichedTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      if (projectId) params.append('project_id', projectId.toString())
      if (status) params.append('status', status)

      const response = await axios.get<TaskStatusResponse>(
        `${API_BASE}/tasks/status?${params}`
      )

      setTasks(response.data.tasks || [])
      setTotal(response.data.total_tasks || 0)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch tasks'
      setError(message)
      console.error('Error fetching tasks:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId, status])

  // Fetch on mount and when dependencies change
  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefresh <= 0) return

    const interval = setInterval(() => {
      fetchTasks()
    }, autoRefresh * 1000)

    return () => clearInterval(interval)
  }, [autoRefresh, fetchTasks])

  return {
    tasks,
    loading,
    error,
    total,
    refetch: fetchTasks,
  }
}

/**
 * Hook to fetch a single task with full metadata
 */
export function useTask(taskId: number | string, projectId?: number) {
  const [task, setTask] = useState<EnrichedTask | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTask = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      if (projectId) params.append('project_id', projectId.toString())
      params.append('task_id', taskId.toString())

      const response = await axios.get<TaskStatusResponse>(
        `${API_BASE}/tasks/status?${params}`
      )

      const tasks = response.data.tasks || []
      setTask(tasks.length > 0 ? tasks[0] : null)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch task'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [taskId, projectId])

  useEffect(() => {
    fetchTask()
  }, [fetchTask])

  return { task, loading, error, refetch: fetchTask }
}

// ============================================================================
// EFFORT PREDICTIONS HOOK (Phase 3c)
// ============================================================================

/**
 * Hook to fetch effort predictions for tasks
 *
 * @param taskId - Optional: get prediction for specific task
 * @param projectId - Project context
 * @param minConfidence - Filter predictions by minimum confidence
 */
export function usePredictions(
  taskId?: number,
  projectId?: number,
  minConfidence: number = 0.5
): UsePredictionsResult {
  const [predictions, setPredictions] = useState<EffortPrediction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState({ avg_confidence: 0, total_predicted_effort: 0 })

  const fetchPredictions = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      if (taskId) params.append('task_id', taskId.toString())
      if (projectId) params.append('project_id', projectId.toString())
      params.append('min_confidence', minConfidence.toString())

      const response = await axios.get<PredictionsResponse>(
        `${API_BASE}/tasks/predictions?${params}`
      )

      setPredictions(response.data.predictions || [])
      setSummary(response.data.summary)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch predictions'
      setError(message)
      console.error('Error fetching predictions:', err)
    } finally {
      setLoading(false)
    }
  }, [taskId, projectId, minConfidence])

  useEffect(() => {
    fetchPredictions()
  }, [fetchPredictions])

  return {
    predictions,
    loading,
    error,
    summary,
    refetch: fetchPredictions,
  }
}

// ============================================================================
// TASK SUGGESTIONS HOOK (Phase 3b)
// ============================================================================

/**
 * Hook to fetch suggested next tasks based on workflow patterns
 *
 * @param completedTaskId - Recently completed task
 * @param projectId - Project context
 * @param limit - Number of suggestions to return
 */
export function useSuggestions(
  completedTaskId?: number,
  projectId?: number,
  limit: number = 5
): UseSuggestionsResult {
  const [suggestions, setSuggestions] = useState<TaskSuggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [processMaturity, setProcessMaturity] = useState<'low' | 'medium' | 'high'>('low')

  const fetchSuggestions = useCallback(async () => {
    if (!completedTaskId) {
      setSuggestions([])
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      params.append('completed_task_id', completedTaskId.toString())
      if (projectId) params.append('project_id', projectId.toString())
      params.append('limit', limit.toString())

      const response = await axios.get<SuggestionsResponse>(
        `${API_BASE}/tasks/suggestions?${params}`
      )

      setSuggestions(response.data.suggestions || [])
      setProcessMaturity(response.data.process_maturity)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch suggestions'
      setError(message)
      console.error('Error fetching suggestions:', err)
    } finally {
      setLoading(false)
    }
  }, [completedTaskId, projectId, limit])

  useEffect(() => {
    fetchSuggestions()
  }, [fetchSuggestions])

  return {
    suggestions,
    loading,
    error,
    processMaturity,
    refetch: fetchSuggestions,
  }
}

// ============================================================================
// UTILITY HOOKS
// ============================================================================

/**
 * Hook to get tasks by status with auto-refresh
 */
export function useTasksByStatus(
  status: 'pending' | 'active' | 'completed' | 'blocked',
  projectId?: number,
  autoRefreshSeconds: number = 10
) {
  return useTasks(projectId, status, autoRefreshSeconds)
}

/**
 * Hook to get blockers for a specific task
 */
export function useTaskBlockers(taskId: number, projectId?: number) {
  const { task } = useTask(taskId, projectId)
  return {
    blockers: task?.blockers || [],
    isBlocked: task?.blocked || false,
  }
}

/**
 * Hook to get dependencies for a specific task
 */
export function useTaskDependencies(taskId: number, projectId?: number) {
  const { task } = useTask(taskId, projectId)
  return {
    dependencies: task?.dependencies || [],
  }
}

/**
 * Hook to get effort data for a task
 */
export function useTaskEffort(taskId: number, projectId?: number) {
  const { task } = useTask(taskId, projectId)
  const { predictions } = usePredictions(taskId, projectId)

  const prediction = predictions.length > 0 ? predictions[0] : null

  return {
    estimate: task?.effort_estimate,
    actual: task?.effort_actual,
    accuracy: task?.accuracy_percent,
    prediction: prediction,
  }
}
