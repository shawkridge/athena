'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileSearch } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import { SearchBar } from '@/components/search-bar'
import { FilterDropdown } from '@/components/filter-dropdown'
import { Pagination } from '@/components/pagination'
import { ExportButton } from '@/components/export-button'
import { DetailModal, DetailField } from '@/components/detail-modal'
import api from '@/lib/api'

export default function ResearchPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [selectedTask, setSelectedTask] = useState<any>(null)

  const { data: stats } = useQuery({
    queryKey: ['research-stats'],
    queryFn: () => api.getResearchStatistics(),
  })

  const { data: tasks } = useQuery({
    queryKey: ['research-tasks', statusFilter],
    queryFn: () => api.getResearchTasks(statusFilter || undefined, 200), // Fetch more for client-side pagination
  })

  // Client-side filtering and pagination
  const filteredTasks = tasks?.tasks?.filter((task: any) =>
    searchQuery
      ? task.topic?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.id?.toString().includes(searchQuery)
      : true
  ) || []

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
    { value: 'in_progress', label: 'In Progress' },
    { value: 'completed', label: 'Completed' },
  ]

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
        <ExportButton
          data={filteredTasks}
          filename={`research-tasks-${new Date().toISOString().split('T')[0]}`}
        />
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
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Research Tasks</h3>
          <div className="flex items-center space-x-3">
            <SearchBar
              placeholder="Search by topic or ID..."
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
                    <th className="pb-3 font-medium">Topic</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Created</th>
                    <th className="pb-3 font-medium">Project</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {paginatedTasks.map((task: any) => (
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
            <FileSearch className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              {searchQuery || statusFilter
                ? 'No research tasks match your filters'
                : 'No research tasks found'}
            </p>
            <p className="text-xs mt-1">
              {searchQuery || statusFilter
                ? 'Try adjusting your search or filters'
                : 'Research tasks will appear here once created'}
            </p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <DetailModal
        isOpen={!!selectedTask}
        onClose={() => setSelectedTask(null)}
        title="Research Task Details"
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
                        : selectedTask.status === 'in_progress'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {selectedTask.status}
                  </span>
                }
              />
            </div>
            <DetailField label="Topic" value={selectedTask.topic} />
            <DetailField
              label="Created"
              value={
                selectedTask.created_at
                  ? new Date(selectedTask.created_at).toLocaleString()
                  : 'N/A'
              }
            />
            <DetailField label="Project ID" value={selectedTask.project_id || '-'} />
            {selectedTask.description && (
              <DetailField label="Description" value={selectedTask.description} />
            )}
            {selectedTask.findings && (
              <DetailField
                label="Findings"
                value={`${selectedTask.findings} finding(s)`}
              />
            )}
          </div>
        )}
      </DetailModal>
    </div>
  )
}
