'use client'

import { useQuery } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import api from '@/lib/api'

export default function ExecutionMonitoringPage() {
  const { data: stats } = useQuery({
    queryKey: ['execution-stats'],
    queryFn: () => api.getExecutionStatistics(),
  })

  const { data: tasksData } = useQuery({
    queryKey: ['execution-tasks'],
    queryFn: () => api.getExecutionTasks(undefined, 50),
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-emerald-100">
            <Play className="h-8 w-8 text-emerald-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Execution Monitoring</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Task execution, workflow orchestration, and queue management
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Active Tasks</div>
          <div className="text-2xl font-bold text-blue-600">{stats?.active_tasks || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Queued Tasks</div>
          <div className="text-2xl font-bold text-orange-600">{stats?.queued_tasks || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Completed</div>
          <div className="text-2xl font-bold text-green-600">{stats?.completed_tasks || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Success Rate</div>
          <div className="text-2xl font-bold">
            {stats?.success_rate ? `${(stats.success_rate * 100).toFixed(1)}%` : '0%'}
          </div>
        </div>
      </div>

      {/* Execution Tasks Table */}
      <div className="bg-card border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Execution Tasks</h3>
        {tasksData?.tasks && tasksData.tasks.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b">
                <tr className="text-left text-sm text-muted-foreground">
                  <th className="pb-3 font-medium">ID</th>
                  <th className="pb-3 font-medium">Task Name</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Duration</th>
                  <th className="pb-3 font-medium">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {tasksData.tasks.map((task: any) => (
                  <tr key={task.id} className="text-sm hover:bg-muted/50 transition-colors">
                    <td className="py-3 font-mono text-xs">{task.id}</td>
                    <td className="py-3 font-medium">{task.name || task.content || '-'}</td>
                    <td className="py-3">
                      <span
                        className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                          task.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : task.status === 'running' || task.status === 'in_progress'
                            ? 'bg-blue-100 text-blue-800'
                            : task.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {task.status}
                      </span>
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {task.duration ? `${task.duration.toFixed(2)}s` : '-'}
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {task.started_at
                        ? new Date(task.started_at).toLocaleString()
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Play className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No execution tasks found</p>
            <p className="text-xs mt-1">Execution tasks will appear here when workflows are running</p>
          </div>
        )}
      </div>
    </div>
  )
}
