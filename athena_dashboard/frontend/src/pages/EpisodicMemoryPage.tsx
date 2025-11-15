import { useState } from 'react'
import { Card } from '@/components/common/Card'
import { SearchBar } from '@/components/common/SearchBar'
import { Pagination } from '@/components/common/Pagination'
import { DateRange } from '@/components/common/DateRange'
import { Stat } from '@/components/common/Stat'
import { useAPI } from '@/hooks'
import { useProject } from '@/context/ProjectContext'
import { format } from 'date-fns'

interface EpisodicEvent {
  id: string
  timestamp: string
  type: string
  description: string
  importance?: number
  project_id?: number
  data?: Record<string, any>
}

interface EpisodicResponse {
  events: EpisodicEvent[]
  total: number
  stats: {
    totalEvents: number
    avgStorageSize: number
    queryTimeMs: number
  }
}

export const EpisodicMemoryPage = () => {
  const { selectedProject } = useProject()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [search, setSearch] = useState('')
  const [startDate, setStartDate] = useState<Date | null>(null)
  const [endDate, setEndDate] = useState<Date | null>(null)

  // Calculate offset for pagination
  const offset = (page - 1) * pageSize

  const queryParams = new URLSearchParams({
    limit: pageSize.toString(),
    offset: offset.toString(),
    search,
    ...(selectedProject && { project_id: selectedProject.id.toString() }),
    ...(startDate && { startDate: format(startDate, 'yyyy-MM-dd') }),
    ...(endDate && { endDate: format(endDate, 'yyyy-MM-dd') }),
  })

  const { data, loading, error } = useAPI<EpisodicResponse>(
    `/api/episodic/events?${queryParams}`,
    [selectedProject?.id, page, pageSize, search]
  )

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-800 rounded w-1/3" />
          <div className="h-12 bg-gray-800 rounded" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-gray-800 rounded" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold text-gray-50 mb-2">Layer 1: Episodic Memory</h1>
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 text-red-300">
          {error?.message || 'Failed to load episodic events'}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Layer 1: Episodic Memory</h1>
        <p className="text-gray-400">
          Event timeline, filtering, and statistics
          {selectedProject && <span className="ml-2 text-blue-400">(Viewing: {selectedProject.name})</span>}
        </p>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Stat label="Total Events" value={data.stats.totalEvents.toLocaleString()} />
        <Stat label="Avg Size" value={`${data.stats.avgStorageSize} KB`} />
        <Stat label="Query Time" value={`${data.stats.queryTimeMs}ms`} />
      </div>

      {/* Filters */}
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Filters & Pagination</h3>}>
        <div className="space-y-4">
          <SearchBar onSearch={setSearch} placeholder="Search events..." />
          <DateRange startDate={startDate} endDate={endDate} onDateChange={(s, e) => {
            setStartDate(s)
            setEndDate(e)
            setPage(1)
          }} />
          <div className="flex items-center gap-4 pt-2">
            <label className="text-gray-400 text-sm">Items per page:</label>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(parseInt(e.target.value))
                setPage(1)
              }}
              className="px-3 py-2 rounded bg-gray-700 text-gray-50 border border-gray-600 focus:outline-none"
            >
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
            <span className="text-sm text-gray-400 ml-auto">
              {data && data.total > 0 ? `Showing ${offset + 1}-${Math.min(offset + pageSize, data.total)} of ${data.total.toLocaleString()}` : 'No results'}
            </span>
          </div>
        </div>
      </Card>

      {/* Events Timeline */}
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Events</h3>}>
        <div className="space-y-3">
          {data.events.length > 0 ? (
            data.events.map((event) => (
              <div
                key={event.id}
                className="p-4 rounded-lg border border-gray-700 bg-gray-800/50 hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-blue-900/30 text-blue-300 mb-2">
                      {event.type}
                    </span>
                    <p className="text-gray-50 font-medium">{event.description}</p>
                  </div>
                  <span className="text-xs text-gray-400 whitespace-nowrap">
                    {format(new Date(event.timestamp), 'MMM dd, HH:mm:ss')}
                  </span>
                </div>
                {event.data && Object.keys(event.data).length > 0 && (
                  <details className="text-sm text-gray-400 cursor-pointer">
                    <summary>View details</summary>
                    <pre className="mt-2 p-2 bg-gray-900 rounded text-xs overflow-x-auto">
                      {JSON.stringify(event.data, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-gray-400">
              No events found
            </div>
          )}
        </div>
      </Card>

      {/* Pagination */}
      {data.total > 0 && (
        <div className="flex justify-center">
          <Pagination
            currentPage={page}
            totalPages={Math.ceil(data.total / 10)}
            onPageChange={setPage}
          />
        </div>
      )}
    </div>
  )
}

export default EpisodicMemoryPage
