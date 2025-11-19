'use client'

import { useQuery } from '@tanstack/react-query'
import { FileSearch } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import api from '@/lib/api'

export default function ResearchPage() {
  const { data: stats } = useQuery({
    queryKey: ['research-stats'],
    queryFn: () => api.getResearchStatistics(),
  })

  const { data: tasks } = useQuery({
    queryKey: ['research-tasks'],
    queryFn: () => api.getResearchTasks(undefined, 50),
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-cyan-100">
            <FileSearch className="h-8 w-8 text-cyan-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Research</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Multi-source research, pattern analysis, and credibility assessment
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Tasks</div>
          <div className="text-2xl font-bold">{stats?.total_tasks || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Active Tasks</div>
          <div className="text-2xl font-bold text-blue-600">{stats?.active_tasks || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Completed</div>
          <div className="text-2xl font-bold text-green-600">{stats?.completed_tasks || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Pending</div>
          <div className="text-2xl font-bold text-orange-600">{stats?.pending_tasks || 0}</div>
        </div>
      </div>

      {/* Research Tasks Table */}
      <div className="bg-card border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Research Tasks</h3>
        {tasks?.tasks && tasks.tasks.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b">
                <tr className="text-left text-sm text-muted-foreground">
                  <th className="pb-3 font-medium">ID</th>
                  <th className="pb-3 font-medium">Topic</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Created</th>
                  <th className="pb-3 font-medium">Project</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {tasks.tasks.map((task: any) => (
                  <tr key={task.id} className="text-sm hover:bg-muted/50 transition-colors">
                    <td className="py-3 font-mono text-xs">{task.id}</td>
                    <td className="py-3 font-medium">{task.topic}</td>
                    <td className="py-3">
                      <span
                        className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                          task.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : task.status === 'in_progress'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {task.status}
                      </span>
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {task.created_at
                        ? new Date(task.created_at).toLocaleString()
                        : 'N/A'}
                    </td>
                    <td className="py-3 text-muted-foreground">{task.project_id || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <FileSearch className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No research tasks found</p>
            <p className="text-xs mt-1">Research tasks will appear here once created</p>
          </div>
        )}
      </div>
    </div>
  )
}
