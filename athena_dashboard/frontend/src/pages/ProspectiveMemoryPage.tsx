import { Card } from '@/components/common/Card'
import { Stat } from '@/components/common/Stat'
import { Badge } from '@/components/common/Badge'
import { useProject } from '@/context/ProjectContext'
import { useTasks, usePredictions } from '@/hooks/usePhase3'
import { EnrichedTask, TaskStatus } from '@/types/phase3'
import { DependencyGraphComponent } from '@/components/phase3/DependencyGraphComponent'
import { WorkflowPatternComponent } from '@/components/phase3/WorkflowPatternComponent'
import { ProjectGanttChart } from '@/components/phase3/ProjectGanttChart'
import { EffortBurndownChart } from '@/components/phase3/EffortBurndownChart'

/**
 * Prospective Memory Page - Layer 4: Task Management
 *
 * Displays tasks with:
 * - Real data from Athena prospective memory store
 * - Task dependencies and blockers
 * - Effort estimates and predictions
 * - Task complexity and priority
 */
export const ProspectiveMemoryPage = () => {
  const { selectedProject } = useProject()
  const projectId = selectedProject?.id

  // Fetch tasks with full metadata from Phase 3a stores
  const { tasks, loading, error, total } = useTasks(projectId, undefined, 10)

  // Fetch effort predictions
  const { predictions } = usePredictions(undefined, projectId)

  if (loading) {
    return <div className="p-6 animate-pulse h-64 bg-gray-800 rounded" />
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-lg bg-red-900/20 border border-red-700 p-4 text-red-200">
          <p className="font-semibold">Error loading tasks</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  // Calculate statistics from tasks
  const stats = {
    total: total,
    completed: tasks.filter((t) => t.status === 'completed').length,
    pending: tasks.filter((t) => t.status === 'pending').length,
    blocked: tasks.filter((t) => t.blocked).length,
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Projects & Milestones</h1>
        <p className="text-gray-400">
          Planning, task tracking, and progress monitoring
          {selectedProject && <span className="ml-2 text-blue-400">(Project: {selectedProject.name})</span>}
        </p>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Total Tasks" value={stats.total.toString()} />
        <Stat label="Completed" value={stats.completed.toString()} />
        <Stat label="Pending" value={stats.pending.toString()} />
        <Stat label="Blocked" value={stats.blocked.toString()} />
      </div>

      {/* Tasks List */}
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Tasks with Metadata</h3>}>
        {tasks.length === 0 ? (
          <div className="p-6 text-center text-gray-400">
            <p>No tasks found. Create one to get started.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {tasks.map((task) => (
              <TaskRow key={task.id} task={task} predictions={predictions} />
            ))}
          </div>
        )}
      </Card>

      {/* Effort Summary */}
      {predictions.length > 0 && (
        <Card header={<h3 className="text-lg font-semibold text-gray-50">Effort Predictions</h3>}>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="p-3 rounded bg-gray-700/30">
              <p className="text-xs text-gray-400">Total Predicted Effort</p>
              <p className="text-xl font-bold text-gray-50">
                {predictions.reduce((sum, p) => sum + (p.predicted_effort || 0), 0)} min
              </p>
            </div>
            <div className="p-3 rounded bg-gray-700/30">
              <p className="text-xs text-gray-400">Avg Confidence</p>
              <p className="text-xl font-bold text-gray-50">
                {(predictions.reduce((sum, p) => sum + (p.confidence || 0), 0) / predictions.length * 100).toFixed(0)}%
              </p>
            </div>
            <div className="p-3 rounded bg-gray-700/30">
              <p className="text-xs text-gray-400">High Confidence</p>
              <p className="text-xl font-bold text-gray-50">
                {predictions.filter((p) => (p.confidence || 0) > 0.8).length}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Advanced Visualizations */}
      {tasks.length > 0 && (
        <div className="grid grid-cols-1 gap-6">
          {/* Dependencies Visualization */}
          <DependencyGraphComponent tasks={tasks} />

          {/* Project Timeline */}
          <ProjectGanttChart tasks={tasks} />

          {/* Effort Tracking */}
          <EffortBurndownChart tasks={tasks} />

          {/* Workflow Patterns */}
          <WorkflowPatternComponent projectId={projectId} />
        </div>
      )}
    </div>
  )
}

/**
 * Task row component showing full metadata
 */
function TaskRow({
  task,
  predictions,
}: {
  task: EnrichedTask
  predictions: any[]
}) {
  const prediction = predictions.find((p) => p.task_id === task.id)
  const statusColors: Record<TaskStatus, string> = {
    pending: 'warning',
    active: 'info',
    in_progress: 'info',
    completed: 'success',
    blocked: 'error',
    cancelled: 'default',
  }

  const priorityColors: Record<string, string> = {
    low: 'default',
    medium: 'warning',
    high: 'error',
    critical: 'error',
  }

  return (
    <div className="p-4 rounded bg-gray-700/20 border border-gray-700/50 hover:bg-gray-700/40 transition-colors">
      <div className="flex items-start justify-between gap-4">
        {/* Task Info */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <p className="text-gray-50 font-medium">{task.content || task.title}</p>
            {task.blocked && <Badge variant="error">Blocked</Badge>}
          </div>
          <p className="text-xs text-gray-400 mb-2">{task.active_form || 'No description'}</p>

          {/* Tags and Dependencies */}
          <div className="flex flex-wrap gap-2 mb-2">
            {task.tags?.map((tag) => (
              <span key={tag} className="px-2 py-1 rounded text-xs bg-gray-700 text-gray-300">
                {tag}
              </span>
            ))}
            {task.dependencies && task.dependencies.length > 0 && (
              <span className="px-2 py-1 rounded text-xs bg-blue-900/40 text-blue-300">
                {task.dependencies.length} dependency
              </span>
            )}
          </div>

          {/* Effort & Complexity */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <div>
              <span className="text-gray-400">Estimate:</span>
              <span className="text-gray-50 ml-1">
                {task.effort_estimate ? `${task.effort_estimate}m` : '—'}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Actual:</span>
              <span className="text-gray-50 ml-1">
                {task.effort_actual ? `${task.effort_actual}m` : '—'}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Complexity:</span>
              <span className="text-gray-50 ml-1">
                {task.complexity_score ? `${task.complexity_score}/10` : '—'}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Accuracy:</span>
              <span className="text-gray-50 ml-1">
                {task.accuracy_percent ? `${task.accuracy_percent}%` : '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Badges & Prediction */}
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <Badge variant={priorityColors[task.priority] || 'default'}>{task.priority}</Badge>
            <Badge variant={statusColors[task.status as TaskStatus] || 'default'}>{task.status}</Badge>
          </div>

          {prediction && (
            <div className="text-xs bg-blue-900/20 border border-blue-700/50 rounded p-2 text-blue-200">
              <p className="font-semibold">Predicted: {prediction.predicted_effort}m</p>
              <p className="text-xs">Confidence: {(prediction.confidence * 100).toFixed(0)}%</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ProspectiveMemoryPage
