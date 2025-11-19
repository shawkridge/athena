'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import { SearchBar } from '@/components/search-bar'
import { FilterDropdown } from '@/components/filter-dropdown'
import { Pagination } from '@/components/pagination'
import { ExportButton } from '@/components/export-button'
import { DetailModal, DetailField } from '@/components/detail-modal'
import api from '@/lib/api'

export default function PerformanceMetricsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [operationFilter, setOperationFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [selectedMetric, setSelectedMetric] = useState<any>(null)

  const { data: stats } = useQuery({
    queryKey: ['performance-stats'],
    queryFn: () => api.getPerformanceStatistics(),
  })

  const { data: metricsData } = useQuery({
    queryKey: ['performance-metrics'],
    queryFn: () => api.getPerformanceMetrics(200), // Fetch more for client-side pagination
  })

  // Client-side filtering and pagination
  const filteredMetrics = metricsData?.metrics?.filter((metric: any) => {
    const matchesSearch = searchQuery
      ? metric.operation?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        metric.name?.toLowerCase().includes(searchQuery.toLowerCase())
      : true
    const matchesOperation = operationFilter
      ? metric.operation?.toLowerCase() === operationFilter.toLowerCase() ||
        metric.name?.toLowerCase() === operationFilter.toLowerCase()
      : true
    return matchesSearch && matchesOperation
  }) || []

  const totalPages = Math.ceil(filteredMetrics.length / pageSize)
  const paginatedMetrics = filteredMetrics.slice(
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

  // Extract unique operation types for filter
  const operations = Array.from(new Set(metricsData?.metrics?.map((m: any) => m.operation || m.name).filter(Boolean) || [])) as string[]
  const operationOptions = operations.map(op => ({ value: op, label: op }))

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-sky-100">
            <Activity className="h-8 w-8 text-sky-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Performance Metrics</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              System performance, benchmarks, and profiling insights
            </p>
          </div>
        </div>
        <ExportButton
          data={filteredMetrics}
          filename={`performance-metrics-${new Date().toISOString().split('T')[0]}`}
        />
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Avg Response Time</div>
          <div className="text-2xl font-bold">
            {stats?.avg_response_time ? `${stats.avg_response_time.toFixed(2)}ms` : '0ms'}
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Throughput</div>
          <div className="text-2xl font-bold text-blue-600">
            {stats?.throughput ? `${stats.throughput.toFixed(1)}/s` : '0/s'}
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Memory Usage</div>
          <div className="text-2xl font-bold text-purple-600">
            {stats?.memory_usage ? `${stats.memory_usage.toFixed(1)}MB` : '0MB'}
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">CPU Utilization</div>
          <div className="text-2xl font-bold text-orange-600">
            {stats?.cpu_utilization ? `${(stats.cpu_utilization * 100).toFixed(1)}%` : '0%'}
          </div>
        </div>
      </div>

      {/* Performance Metrics Table */}
      <div className="bg-card border rounded-lg p-6">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Recent Performance Metrics</h3>
          <div className="flex items-center space-x-3">
            <SearchBar
              placeholder="Search by operation or name..."
              onSearch={setSearchQuery}
              className="w-64"
            />
            {operationOptions.length > 0 && (
              <FilterDropdown
                label="Operation"
                options={operationOptions}
                value={operationFilter}
                onChange={setOperationFilter}
              />
            )}
          </div>
        </div>

        {paginatedMetrics && paginatedMetrics.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b">
                  <tr className="text-left text-sm text-muted-foreground">
                    <th className="pb-3 font-medium">Timestamp</th>
                    <th className="pb-3 font-medium">Operation</th>
                    <th className="pb-3 font-medium">Duration</th>
                    <th className="pb-3 font-medium">Memory</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {paginatedMetrics.map((metric: any, idx: number) => (
                    <tr key={idx} className="text-sm hover:bg-muted/50 transition-colors">
                      <td className="py-3 text-muted-foreground">
                        {metric.timestamp
                          ? new Date(metric.timestamp).toLocaleString()
                          : '-'}
                      </td>
                      <td className="py-3 font-medium">{metric.operation || metric.name || '-'}</td>
                      <td className="py-3">
                        <span className={`font-medium ${
                          metric.duration > 1000 ? 'text-red-600' :
                          metric.duration > 500 ? 'text-yellow-600' : 'text-green-600'
                        }`}>
                          {metric.duration ? `${metric.duration.toFixed(2)}ms` : '-'}
                        </span>
                      </td>
                      <td className="py-3 text-muted-foreground">
                        {metric.memory_used ? `${metric.memory_used.toFixed(1)}MB` : '-'}
                      </td>
                      <td className="py-3">
                        <span
                          className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                            metric.status === 'success'
                              ? 'bg-green-100 text-green-800'
                              : metric.status === 'error'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {metric.status || 'success'}
                        </span>
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => setSelectedMetric(metric)}
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
                totalItems={filteredMetrics.length}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
              />
            )}
          </>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Activity className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              {searchQuery || operationFilter
                ? 'No performance metrics match your filters'
                : 'No performance metrics found'}
            </p>
            <p className="text-xs mt-1">
              {searchQuery || operationFilter
                ? 'Try adjusting your search or filters'
                : 'Performance metrics will appear here once operations are tracked'}
            </p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <DetailModal
        isOpen={!!selectedMetric}
        onClose={() => setSelectedMetric(null)}
        title="Performance Metric Details"
      >
        {selectedMetric && (
          <div className="space-y-4">
            <DetailField
              label="Operation"
              value={selectedMetric.operation || selectedMetric.name || '-'}
            />
            <div className="grid grid-cols-2 gap-4">
              <DetailField
                label="Duration"
                value={
                  <span className={`font-medium ${
                    selectedMetric.duration > 1000 ? 'text-red-600' :
                    selectedMetric.duration > 500 ? 'text-yellow-600' : 'text-green-600'
                  }`}>
                    {selectedMetric.duration ? `${selectedMetric.duration.toFixed(2)}ms` : '-'}
                  </span>
                }
              />
              <DetailField
                label="Memory Used"
                value={selectedMetric.memory_used ? `${selectedMetric.memory_used.toFixed(1)}MB` : '-'}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <DetailField
                label="Status"
                value={
                  <span
                    className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                      selectedMetric.status === 'success'
                        ? 'bg-green-100 text-green-800'
                        : selectedMetric.status === 'error'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {selectedMetric.status || 'success'}
                  </span>
                }
              />
              <DetailField
                label="Timestamp"
                value={
                  selectedMetric.timestamp
                    ? new Date(selectedMetric.timestamp).toLocaleString()
                    : '-'
                }
              />
            </div>
            {selectedMetric.cpu_usage && (
              <DetailField
                label="CPU Usage"
                value={`${(selectedMetric.cpu_usage * 100).toFixed(1)}%`}
              />
            )}
            {selectedMetric.io_operations && (
              <DetailField label="I/O Operations" value={selectedMetric.io_operations} />
            )}
            {selectedMetric.cache_hits !== undefined && (
              <DetailField label="Cache Hits" value={selectedMetric.cache_hits} />
            )}
          </div>
        )}
      </DetailModal>
    </div>
  )
}
