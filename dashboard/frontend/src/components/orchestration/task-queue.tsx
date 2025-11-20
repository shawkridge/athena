'use client'

import { Task } from '@/stores/orchestration-store'
import { Badge } from '@/components/ui/badge'
import { CheckCircle, AlertCircle, Clock, Zap } from 'lucide-react'

interface TaskQueueProps {
  tasks: Task[]
  onSelectTask?: (taskId: number) => void
  selectedTaskId?: number | null
}

const statusConfig = {
  pending: {
    icon: Clock,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    badge: 'bg-yellow-100 text-yellow-800',
  },
  in_progress: {
    icon: Zap,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    badge: 'bg-blue-100 text-blue-800',
  },
  completed: {
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    badge: 'bg-green-100 text-green-800',
  },
  failed: {
    icon: AlertCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    badge: 'bg-red-100 text-red-800',
  },
}

const priorityColors = {
  1: 'bg-gray-100 text-gray-700',
  2: 'bg-blue-100 text-blue-700',
  3: 'bg-yellow-100 text-yellow-700',
  4: 'bg-orange-100 text-orange-700',
  5: 'bg-red-100 text-red-700',
}

export function TaskQueue({
  tasks,
  onSelectTask,
  selectedTaskId,
}: TaskQueueProps) {
  if (tasks.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No tasks in queue</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {tasks.map((task) => {
        const config =
          statusConfig[task.status as keyof typeof statusConfig] ||
          statusConfig.pending
        const Icon = config.icon

        return (
          <div
            key={task.id}
            onClick={() => onSelectTask?.(task.id)}
            className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
              selectedTaskId === task.id
                ? 'border-blue-500 bg-blue-50'
                : `border-gray-200 hover:border-gray-300 ${config.bgColor}`
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2 flex-1 min-w-0">
                <Icon className={`w-4 h-4 ${config.color} mt-0.5 flex-shrink-0`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <p className="text-sm font-medium truncate text-gray-900">
                      Task #{task.id}
                    </p>
                    <Badge
                      variant="secondary"
                      className={`text-xs ${config.badge}`}
                    >
                      {task.status.replace('_', ' ')}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-600 line-clamp-2">
                    {task.content}
                  </p>
                </div>
              </div>

              {task.progress !== undefined && task.progress > 0 && (
                <div className="flex-shrink-0">
                  <Badge
                    variant="outline"
                    className={`text-xs ${
                      priorityColors[
                        task.priority as keyof typeof priorityColors
                      ] || priorityColors[3]
                    }`}
                  >
                    {task.progress}%
                  </Badge>
                </div>
              )}
            </div>

            {task.assigned_agent_id && (
              <p className="text-xs text-gray-500 mt-2">
                Assigned to: {task.assigned_agent_id}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
