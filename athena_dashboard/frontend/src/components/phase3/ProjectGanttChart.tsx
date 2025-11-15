/**
 * Project Gantt Chart Component
 *
 * Timeline visualization showing:
 * - Task start and completion dates
 * - Task duration bars
 * - Progress and status indicators
 * - Critical path highlighting
 */

import React, { useMemo } from 'react'
import { EnrichedTask } from '@/types/phase3'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'

interface ProjectGanttChartProps {
  tasks: EnrichedTask[]
}

interface GanttTask {
  id: string | number
  name: string
  start: Date
  end: Date
  duration: number
  progress: number
  status: string
  complexity?: number
}

/**
 * Gantt Chart Component
 */
export const ProjectGanttChart: React.FC<ProjectGanttChartProps> = ({ tasks }) => {
  const ganttTasks = useMemo(() => {
    const now = new Date()
    return tasks
      .map((task) => {
        const startDate = task.created_at ? new Date(task.created_at) : now
        const dueDate = task.due_at ? new Date(task.due_at) : new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)

        // Calculate progress based on status
        let progress = 0
        if (task.status === 'completed') progress = 100
        else if (task.status === 'in_progress' || task.status === 'active') progress = 50
        else progress = 0

        return {
          id: task.id,
          name: (task.content || task.title || 'Untitled').substring(0, 30),
          start: startDate,
          end: dueDate,
          duration: Math.max(1, Math.ceil((dueDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))),
          progress,
          status: task.status,
          complexity: task.complexity_score,
        }
      })
      .sort((a, b) => a.start.getTime() - b.start.getTime())
  }, [tasks])

  if (ganttTasks.length === 0) {
    return (
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Project Timeline</h3>}>
        <p className="text-gray-400 text-center py-6">No tasks to display</p>
      </Card>
    )
  }

  // Calculate date range
  const allDates = ganttTasks.flatMap((t) => [t.start.getTime(), t.end.getTime()])
  const minDate = new Date(Math.min(...allDates))
  const maxDate = new Date(Math.max(...allDates))
  const totalDays = Math.ceil((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24)) + 1

  // Generate week headers
  const weeks: Array<{ date: Date; label: string }> = []
  let currentDate = new Date(minDate)
  while (currentDate <= maxDate) {
    weeks.push({
      date: new Date(currentDate),
      label: `${currentDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`,
    })
    currentDate.setDate(currentDate.getDate() + 7)
  }

  const getTaskPosition = (task: GanttTask) => {
    const daysFromStart = Math.floor((task.start.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24))
    const percentage = (daysFromStart / totalDays) * 100
    return { start: Math.max(0, percentage), width: (task.duration / totalDays) * 100 }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return '#10b981'
      case 'in_progress':
      case 'active':
        return '#3b82f6'
      case 'blocked':
        return '#ef4444'
      default:
        return '#6366f1'
    }
  }

  return (
    <Card
      header={
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-50">Project Timeline</h3>
          <span className="text-xs text-gray-400">
            {minDate.toLocaleDateString()} - {maxDate.toLocaleDateString()}
          </span>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Timeline header */}
        <div className="overflow-x-auto">
          <div className="min-w-max flex">
            {/* Task names column */}
            <div className="w-40 flex-shrink-0 border-r border-gray-700">
              <div className="h-16 flex items-end pb-2 px-2">
                <span className="text-xs font-semibold text-gray-400">TASK</span>
              </div>
            </div>

            {/* Timeline header */}
            <div className="flex-1 flex">
              {weeks.map((week, idx) => (
                <div
                  key={idx}
                  className="flex-1 min-w-max border-r border-gray-700/30 px-2 py-2 text-center"
                >
                  <span className="text-xs text-gray-400">{week.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Timeline rows */}
          <div className="mt-2">
            {ganttTasks.map((task) => {
              const position = getTaskPosition(task)
              return (
                <div key={task.id} className="flex border-b border-gray-700/30">
                  {/* Task name */}
                  <div className="w-40 flex-shrink-0 border-r border-gray-700 px-2 py-2 flex items-center">
                    <div className="truncate">
                      <p className="text-xs font-medium text-gray-50 truncate">{task.name}</p>
                      <p className="text-xs text-gray-500 truncate">{task.duration}d</p>
                    </div>
                  </div>

                  {/* Timeline bar */}
                  <div className="flex-1 relative h-12 flex items-center px-1">
                    {/* Background grid */}
                    <div className="absolute inset-0 flex">
                      {weeks.map((_, idx) => (
                        <div
                          key={idx}
                          className="flex-1 min-w-max border-r border-gray-700/10"
                        />
                      ))}
                    </div>

                    {/* Task bar */}
                    <div
                      className="absolute h-8 rounded bg-gray-700/80 border border-gray-600 transition-all hover:bg-gray-600 cursor-pointer group"
                      style={{
                        left: `${position.start}%`,
                        width: `${position.width}%`,
                        minWidth: '40px',
                      }}
                    >
                      {/* Progress indicator */}
                      <div
                        className="h-full rounded bg-opacity-30"
                        style={{
                          backgroundColor: getStatusColor(task.status),
                          width: `${task.progress}%`,
                        }}
                      />

                      {/* Tooltip on hover */}
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-gray-900 border border-gray-700 rounded p-2 text-xs whitespace-nowrap z-10">
                        <p className="font-semibold text-gray-50">{task.name}</p>
                        <p className="text-gray-400">Status: {task.status}</p>
                        <p className="text-gray-400">Progress: {task.progress}%</p>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Legend */}
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: '#10b981' }} />
            <span className="text-gray-400">Completed</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: '#3b82f6' }} />
            <span className="text-gray-400">In Progress</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: '#ef4444' }} />
            <span className="text-gray-400">Blocked</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: '#6366f1' }} />
            <span className="text-gray-400">Pending</span>
          </div>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-3 gap-2 p-3 rounded bg-gray-700/20 border border-gray-700/50 mt-4">
          <div>
            <p className="text-xs text-gray-400">Duration</p>
            <p className="text-lg font-bold text-gray-50">{totalDays}d</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">Completed</p>
            <p className="text-lg font-bold text-green-400">
              {ganttTasks.filter((t) => t.status === 'completed').length}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400">On Track</p>
            <p className="text-lg font-bold text-blue-400">
              {ganttTasks.filter((t) => t.status === 'in_progress' || t.status === 'active').length}
            </p>
          </div>
        </div>
      </div>
    </Card>
  )
}

export default ProjectGanttChart
