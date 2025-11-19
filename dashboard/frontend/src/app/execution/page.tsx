'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import { SearchBar } from '@/components/search-bar'
import { FilterDropdown } from '@/components/filter-dropdown'
import { Pagination } from '@/components/pagination'
import { ExportButton } from '@/components/export-button'
import { DetailModal, DetailField } from '@/components/detail-modal'
import api from '@/lib/api'

export default function ExecutionMonitoringPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [selectedTask, setSelectedTask] = useState<any>(null)

  const { data: stats } = useQuery({
    queryKey: ['execution-stats'],
    queryFn: () => api.getExecutionStatistics(),
  })

  const { data: tasksData } = useQuery({
    queryKey: ['execution-tasks'],
    queryFn: () => api.getExecutionTasks(undefined, 200), // Fetch more for client-side pagination
  })

  // Client-side filtering and pagination
  const filteredTasks = tasksData?.tasks?.filter((task: any) => {
    const matchesSearch = searchQuery
      ? task.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.content?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.id?.toString().includes(searchQuery)
      : true
    const matchesStatus = statusFilter
      ? task.status?.toLowerCase() === statusFilter.toLowerCase()
      : true
    return matchesSearch && matchesStatus
  }) || []

  const totalPages = Math.ceil(filteredTasks.length / pageSize)
  const paginatedTasks = filteredTasks.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handlePageSizeChange = (size: number) => {
    setPageSize(size)
    setCurrentPage(1)
  }

  const statusOptions = [
    { value: 'pending', label: 'Pending' },
    { value: 'running', label: 'Running' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
  ]

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
        <ExportButton
          data={filteredTasks}
          filename={`execution-tasks-${new Date().toISOString().split('T')[0]}`}
        />
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
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Execution Tasks</h3>
          <div className="flex items-center space-x-3">
            <SearchBar
              placeholder="Search by name, ID, or content..."
              onSearch={setSearchQuery}
              className="w-64"
            />
            <FilterDropdown
              label="Status"
              options={statusOptions}
              value={statusFilter}
              onChange={setStatusFilter}
            />
          </div>
        </div>

        {paginatedTasks && paginatedTasks.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b">
                  <tr className="text-left text-sm text-muted-foreground">
                    <th className="pb-3 font-medium">ID</th>
                    <th className="pb-3 font-medium">Task Name</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Duration</th>
                    <th className="pb-3 font-medium">Started</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {paginatedTasks.map((task: any) => (
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
                      <td className="py-3">
                        <button
                          onClick={() => setSelectedTask(task)}
                          className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                pageSize={pageSize}
                totalItems={filteredTasks.length}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
              />
            )}
          </>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Play className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              {searchQuery || statusFilter
                ? 'No execution tasks match your filters'
                : 'No execution tasks found'}
            </p>
            <p className="text-xs mt-1">
              {searchQuery || statusFilter
                ? 'Try adjusting your search or filters'
                : 'Execution tasks will appear here when workflows are running'}
            </p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <DetailModal
        isOpen={!!selectedTask}
        onClose={() => setSelectedTask(null)}
        title="Execution Task Details"
      >
        {selectedTask && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <DetailField label="Task ID" value={selectedTask.id} />
              <DetailField
                label="Status"
                value={
                  <span
                    className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                      selectedTask.status === 'completed'
                        ? 'bg-green-100 text-green-800'
                        : selectedTask.status === 'running' || selectedTask.status === 'in_progress'
                        ? 'bg-blue-100 text-blue-800'
                        : selectedTask.status === 'failed'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {selectedTask.status}
                  </span>
                }
              />
            </div>
            <DetailField label="Task Name" value={selectedTask.name || selectedTask.content || '-'} />
            <div className="grid grid-cols-2 gap-4">
              <DetailField
                label="Duration"
                value={selectedTask.duration ? `${selectedTask.duration.toFixed(2)}s` : '-'}
              />
              <DetailField
                label="Started At"
                value={
                  selectedTask.started_at
                    ? new Date(selectedTask.started_at).toLocaleString()
                    : '-'
                }
              />
            </div>
            {selectedTask.completed_at && (
              <DetailField
                label="Completed At"
                value={new Date(selectedTask.completed_at).toLocaleString()}
              />
            )}
            {selectedTask.error && (
              <DetailField label="Error" value={selectedTask.error} />
            )}
            {selectedTask.result && (
              <DetailField label="Result" value={selectedTask.result} />
            )}
          </div>
        )}
      </DetailModal>
    </div>
  )
}
