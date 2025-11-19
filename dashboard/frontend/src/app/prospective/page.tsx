'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatNumber, formatDate, formatRelativeTime, getStatusColor } from '@/lib/utils'
import { Calendar, Filter } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'

export default function ProspectiveMemoryPage() {
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [limit, setLimit] = useState(100)

  const { data: stats } = useQuery({
    queryKey: ['prospective-stats'],
    queryFn: api.getProspectiveStatistics,
  })

  const { data: tasksData, isLoading } = useQuery({
    queryKey: ['prospective-tasks', statusFilter, limit],
    queryFn: () => api.getTasks(statusFilter || undefined, limit),
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-orange-100">
            <Calendar className="h-8 w-8 text-orange-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Prospective Memory</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Tasks, goals, and future intentions
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Tasks</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_tasks || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Active Tasks</div>
          <div className="text-2xl font-bold text-blue-600">
            {formatNumber(stats?.active_tasks || 0)}
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Completed Tasks</div>
          <div className="text-2xl font-bold text-green-600">
            {formatNumber(stats?.completed_tasks || 0)}
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Overdue Tasks</div>
          <div className="text-2xl font-bold text-red-600">
            {formatNumber(stats?.overdue_tasks || 0)}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-card border rounded-lg p-4">
        <div className="flex items-center space-x-4">
          <Filter className="h-5 w-5 text-muted-foreground" />
          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Limit</label>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value={50}>50 tasks</option>
                <option value={100}>100 tasks</option>
                <option value={500}>500 tasks</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={() => {
                  setStatusFilter('')
                  setLimit(100)
                }}
                className="px-4 py-2 border rounded-md hover:bg-accent transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tasks List */}
      <div className="bg-card border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">
            Tasks ({tasksData?.total || 0})
          </h3>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : tasksData?.tasks && tasksData.tasks.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Content
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Priority
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Phase
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Due Date
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {tasksData.tasks.map((task) => (
                  <tr key={task.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 text-sm max-w-md">
                      <div className="line-clamp-2">{task.content}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${getStatusColor(task.status)}`}>
                        {task.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center">
                        <div className="w-full bg-muted rounded-full h-2 mr-2">
                          <div
                            className="bg-orange-600 h-2 rounded-full"
                            style={{ width: `${task.priority * 10}%` }}
                          ></div>
                        </div>
                        <span className="text-xs text-muted-foreground">{task.priority}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{task.phase}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatRelativeTime(task.created_at)}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {task.due_at ? formatDate(task.due_at) : 'No deadline'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No tasks found</p>
          </div>
        )}
      </div>
    </div>
  )
}
