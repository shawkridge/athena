/**
 * Smart Task Tracking Page
 *
 * Displays intelligent task management with:
 * - Real-time task status with dependencies and metadata
 * - AI-powered effort predictions with confidence levels
 * - Smart suggestions for next tasks based on workflow patterns
 * - Comprehensive analytics and metrics
 */

import { useEffect, useState } from 'react'
import { Card } from '@/components/common/Card'
import { Stat } from '@/components/common/Stat'
import { Badge } from '@/components/common/Badge'
import { useAPI } from '@/hooks'
import { useProject } from '@/context/ProjectContext'
import { TaskStatusTable } from '@/components/tasks/TaskStatusTable'
import { PredictionsChart } from '@/components/tasks/PredictionsChart'
import { SuggestionsPanel } from '@/components/tasks/SuggestionsPanel'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

// Type definitions matching Phase 3 API responses
interface Task {
  task_id: string
  name: string
  status: 'pending' | 'in_progress' | 'completed' | 'blocked'
  estimated_effort_minutes: number
  actual_effort_minutes: number
  blockers: string[]
  dependencies: string[]
  accuracy_score: number
  created_at: string
  updated_at: string
}

interface TaskStatusResponse {
  total_tasks: number
  tasks: Task[]
  timestamp: string
}

interface Prediction {
  task_id: string
  task_type: string
  predicted_effort_minutes: number
  confidence: number
  range: {
    optimistic: number
    expected: number
    pessimistic: number
  }
  historical_accuracy: number
  bias_factor: number
}

interface PredictionsResponse {
  total_predictions: number
  predictions: Prediction[]
  summary: {
    avg_confidence: number
    total_predicted_effort: number
  }
  timestamp: string
}

interface Suggestion {
  task_id: string
  task_name: string
  reason: string
  confidence: number
  pattern_frequency: number
  expected_next_task: string | null
}

interface SuggestionsResponse {
  current_task: string | null
  total_suggestions: number
  suggestions: Suggestion[]
  process_maturity: 'low' | 'medium' | 'high'
  timestamp: string
}

interface Metrics {
  task_completion: {
    completed: number
    in_progress: number
    pending: number
    blocked: number
    completion_rate: number
  }
  effort_accuracy: {
    overall: number
    by_type: Record<string, number>
  }
  workflow_patterns: {
    process_maturity: string
    consistency: number
    anomalies: number
  }
  predictions: {
    avg_confidence: number
    accuracy_trend: 'improving' | 'stable' | 'degrading'
  }
  timestamp: string
}

interface MetricsResponse {
  task_completion: Metrics['task_completion']
  effort_accuracy: Metrics['effort_accuracy']
  workflow_patterns: Metrics['workflow_patterns']
  predictions: Metrics['predictions']
  timestamp: string
}

export const TaskManagementPage = () => {
  const { selectedProject } = useProject()
  const [autoRefresh, setAutoRefresh] = useState(true)

  // API endpoints
  const statusUrl = selectedProject
    ? `/api/tasks/status?project_id=${selectedProject.id}`
    : '/api/tasks/status'

  const predictionsUrl = selectedProject
    ? `/api/tasks/predictions?project_id=${selectedProject.id}`
    : '/api/tasks/predictions'

  const suggestionsUrl = selectedProject
    ? `/api/tasks/suggestions?project_id=${selectedProject.id}`
    : '/api/tasks/suggestions'

  const metricsUrl = selectedProject
    ? `/api/tasks/metrics?project_id=${selectedProject.id}`
    : '/api/tasks/metrics'

  // Fetch data from Phase 3 endpoints
  const { data: statusData, loading: statusLoading } = useAPI<TaskStatusResponse>(
    statusUrl,
    [selectedProject?.id],
    { refetchInterval: autoRefresh ? 5000 : null } // Poll every 5s if auto-refresh enabled
  )

  const { data: predictionsData, loading: predictionsLoading } = useAPI<PredictionsResponse>(
    predictionsUrl,
    [selectedProject?.id],
    { refetchInterval: autoRefresh ? 5000 : null }
  )

  const { data: suggestionsData, loading: suggestionsLoading } = useAPI<SuggestionsResponse>(
    suggestionsUrl,
    [selectedProject?.id],
    { refetchInterval: autoRefresh ? 10000 : null } // Suggest less frequently
  )

  const { data: metricsData, loading: metricsLoading } = useAPI<MetricsResponse>(
    metricsUrl,
    [selectedProject?.id],
    { refetchInterval: autoRefresh ? 30000 : null } // Metrics every 30s
  )

  const allLoading = statusLoading || predictionsLoading || suggestionsLoading || metricsLoading

  if (allLoading && !statusData) {
    return <LoadingSpinner message="Loading task management data..." />
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-50">Smart Task Tracking</h1>
          <p className="text-gray-400">
            Real-time task monitoring with intelligent predictions and workflow insights
            {selectedProject && <span className="ml-2 text-blue-400">(Viewing: {selectedProject.name})</span>}
          </p>
        </div>
        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          className={`px-4 py-2 rounded text-sm font-medium transition ${
            autoRefresh
              ? 'bg-green-600/20 text-green-400 border border-green-500/30'
              : 'bg-gray-700/30 text-gray-400 border border-gray-600/30'
          }`}
        >
          {autoRefresh ? '🔄 Live' : '⏸ Paused'}
        </button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Stat
          label="Total Tasks"
          value={statusData?.total_tasks.toString() || '0'}
          change={metricsData?.task_completion.completion_rate ? `${Math.round(metricsData.task_completion.completion_rate * 100)}% complete` : undefined}
        />
        <Stat
          label="In Progress"
          value={metricsData?.task_completion.in_progress.toString() || '0'}
          variant="warning"
        />
        <Stat
          label="Pending"
          value={metricsData?.task_completion.pending.toString() || '0'}
        />
        <Stat
          label="Blocked"
          value={metricsData?.task_completion.blocked.toString() || '0'}
          variant="error"
        />
        <Stat
          label="Effort Accuracy"
          value={metricsData?.effort_accuracy.overall ? `${Math.round(metricsData.effort_accuracy.overall * 100)}%` : '0%'}
          variant="success"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Task Status - Takes 2 columns */}
        <div className="lg:col-span-2">
          <Card header={<h3 className="text-lg font-semibold text-gray-50">Task Status</h3>}>
            <TaskStatusTable tasks={statusData?.tasks || []} loading={statusLoading} />
          </Card>
        </div>

        {/* Predictions - Takes 1 column */}
        <div>
          <Card header={<h3 className="text-lg font-semibold text-gray-50">Predictions</h3>}>
            <div className="space-y-4">
              <div className="text-sm text-gray-400">
                <p className="font-medium text-gray-300">Avg. Confidence</p>
                <p className="text-2xl font-bold text-blue-400">
                  {predictionsData?.summary.avg_confidence
                    ? `${Math.round(predictionsData.summary.avg_confidence * 100)}%`
                    : '0%'}
                </p>
              </div>
              <div className="text-sm text-gray-400">
                <p className="font-medium text-gray-300">Total Predicted</p>
                <p className="text-2xl font-bold text-purple-400">
                  {predictionsData?.summary.total_predicted_effort || 0}m
                </p>
              </div>
              <div className="border-t border-gray-700 pt-4">
                <p className="text-xs text-gray-500 mb-2">Accuracy by type:</p>
                {metricsData?.effort_accuracy.by_type && Object.entries(metricsData.effort_accuracy.by_type).map(([type, accuracy]) => (
                  <div key={type} className="flex justify-between text-xs mb-2">
                    <span className="text-gray-400">{type}</span>
                    <span className={accuracy > 0.8 ? 'text-green-400' : 'text-yellow-400'}>
                      {Math.round(accuracy * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Predictions Details */}
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Effort Predictions</h3>}>
        <PredictionsChart predictions={predictionsData?.predictions || []} loading={predictionsLoading} />
      </Card>

      {/* Suggestions */}
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Suggested Next Tasks</h3>}>
        <SuggestionsPanel
          suggestions={suggestionsData?.suggestions || []}
          maturity={suggestionsData?.process_maturity || 'low'}
          loading={suggestionsLoading}
        />
      </Card>

      {/* Workflow Patterns */}
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Workflow Analysis</h3>}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-gray-700/20 p-4 rounded">
            <p className="text-xs text-gray-400 uppercase font-medium mb-2">Process Maturity</p>
            <p className="text-2xl font-bold text-gray-50 capitalize">
              {metricsData?.workflow_patterns.process_maturity || 'Unknown'}
            </p>
          </div>
          <div className="bg-gray-700/20 p-4 rounded">
            <p className="text-xs text-gray-400 uppercase font-medium mb-2">Consistency</p>
            <p className="text-2xl font-bold text-blue-400">
              {metricsData?.workflow_patterns.consistency
                ? `${Math.round(metricsData.workflow_patterns.consistency * 100)}%`
                : '0%'}
            </p>
          </div>
          <div className="bg-gray-700/20 p-4 rounded">
            <p className="text-xs text-gray-400 uppercase font-medium mb-2">Anomalies Detected</p>
            <p className="text-2xl font-bold text-red-400">
              {metricsData?.workflow_patterns.anomalies || 0}
            </p>
          </div>
        </div>
        <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded text-sm text-blue-300">
          <strong>Predictions are improving:</strong> Based on historical data and {statusData?.total_tasks || 0} tracked tasks.
        </div>
      </Card>

      {/* Last Update */}
      <div className="text-xs text-gray-500 text-right">
        Last updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  )
}

export default TaskManagementPage
