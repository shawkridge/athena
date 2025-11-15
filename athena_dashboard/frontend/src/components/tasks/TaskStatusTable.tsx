/**
 * Task Status Table Component
 *
 * Displays Phase 3a data: Task dependencies, effort tracking, and accuracy
 */

import { Badge } from '@/components/common/Badge'

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

interface TaskStatusTableProps {
  tasks: Task[]
  loading?: boolean
}

export const TaskStatusTable = ({ tasks, loading }: TaskStatusTableProps) => {
  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-16 bg-gray-700/30 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (!tasks || tasks.length === 0) {
    return (
      <div className="p-8 text-center text-gray-400">
        No tasks found. Start by creating a task to track progress.
      </div>
    )
  }

  const getStatusColor = (status: Task['status']) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'in_progress':
        return 'warning'
      case 'blocked':
        return 'error'
      case 'pending':
      default:
        return 'info'
    }
  }

  const getEffortAccuracy = (task: Task) => {
    if (task.actual_effort_minutes === 0) return null
    const ratio = task.actual_effort_minutes / task.estimated_effort_minutes
    if (ratio > 1.2) return 'underestimated'
    if (ratio < 0.8) return 'overestimated'
    return 'accurate'
  }

  return (
    <div className="space-y-2 overflow-x-auto">
      {/* Header */}
      <div className="hidden md:grid grid-cols-12 gap-2 px-3 py-2 text-xs font-semibold text-gray-400 uppercase border-b border-gray-700/50">
        <div className="col-span-3">Task</div>
        <div className="col-span-1">Status</div>
        <div className="col-span-2">Effort</div>
        <div className="col-span-2">Dependencies</div>
        <div className="col-span-2">Accuracy</div>
        <div className="col-span-2">Blockers</div>
      </div>

      {/* Rows */}
      {tasks.map((task) => (
        <div key={task.task_id} className="p-3 rounded bg-gray-700/20 border border-gray-700/30 hover:border-gray-600/50 transition">
          <div className="md:hidden mb-3">
            <p className="font-medium text-gray-50">{task.name}</p>
            <p className="text-xs text-gray-400">{task.task_id}</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-12 gap-2 items-center">
            {/* Task Name (hidden on mobile, shown in header) */}
            <div className="col-span-1 md:col-span-3 hidden md:block">
              <div>
                <p className="text-sm font-medium text-gray-50 truncate">{task.name}</p>
                <p className="text-xs text-gray-500">{task.task_id}</p>
              </div>
            </div>

            {/* Status */}
            <div className="col-span-1">
              <Badge variant={getStatusColor(task.status)} className="capitalize">
                {task.status.replace('_', ' ')}
              </Badge>
            </div>

            {/* Effort */}
            <div className="col-span-1 md:col-span-2">
              <div className="text-sm">
                <p className="text-gray-50">
                  {task.actual_effort_minutes > 0 ? task.actual_effort_minutes : task.estimated_effort_minutes}m
                </p>
                {task.actual_effort_minutes > 0 && (
                  <p className="text-xs text-gray-400">
                    est: {task.estimated_effort_minutes}m
                  </p>
                )}
              </div>
            </div>

            {/* Dependencies (mobile: hidden, desktop: shown) */}
            <div className="col-span-1 md:col-span-2 hidden md:block">
              {task.dependencies.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                  {task.dependencies.map((dep) => (
                    <Badge key={dep} variant="secondary" className="text-xs">
                      {dep}
                    </Badge>
                  ))}
                </div>
              ) : (
                <span className="text-xs text-gray-500">None</span>
              )}
            </div>

            {/* Accuracy Score */}
            <div className="col-span-1 md:col-span-2">
              <div className="text-right md:text-left">
                <p className={`text-sm font-semibold ${
                  task.accuracy_score > 0.8 ? 'text-green-400' :
                  task.accuracy_score > 0.6 ? 'text-yellow-400' :
                  'text-red-400'
                }`}>
                  {Math.round(task.accuracy_score * 100)}%
                </p>
                {task.actual_effort_minutes > 0 && (
                  <p className="text-xs text-gray-500">
                    {getEffortAccuracy(task)}
                  </p>
                )}
              </div>
            </div>

            {/* Blockers */}
            <div className="col-span-1 md:col-span-2">
              {task.blockers.length > 0 ? (
                <div className="flex items-center gap-1">
                  <span className="text-red-400 text-lg">⚠️</span>
                  <span className="text-xs text-gray-400">{task.blockers.length}</span>
                </div>
              ) : (
                <span className="text-xs text-gray-500">Clear</span>
              )}
            </div>
          </div>

          {/* Mobile detail view */}
          <div className="md:hidden mt-2 space-y-1 text-xs text-gray-400 border-t border-gray-700/30 pt-2">
            {task.dependencies.length > 0 && (
              <p>Depends on: {task.dependencies.join(', ')}</p>
            )}
            {task.blockers.length > 0 && (
              <p className="text-red-400">Blocked by: {task.blockers.join(', ')}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
