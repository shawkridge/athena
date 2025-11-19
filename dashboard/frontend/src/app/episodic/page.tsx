'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatDate, formatRelativeTime, getScoreColor, formatNumber } from '@/lib/utils'
import { Database, Filter, Download } from 'lucide-react'
import { useProjectStore } from '@/stores/project-store'
import { ScopeBadge } from '@/components/scope-badge'

export default function EpisodicMemoryPage() {
  const [limit, setLimit] = useState(100)
  const [sessionFilter, setSessionFilter] = useState<string>('')
  const { currentProjectId, getCurrentProject } = useProjectStore()
  const currentProject = getCurrentProject()

  const { data: stats } = useQuery({
    queryKey: ['episodic-stats', sessionFilter, currentProjectId],
    queryFn: () => api.getEpisodicStatistics(sessionFilter || undefined, currentProjectId),
  })

  const { data: eventsData, isLoading } = useQuery({
    queryKey: ['episodic-events', limit, sessionFilter, currentProjectId],
    queryFn: () => api.getEpisodicEvents(limit, sessionFilter || undefined, currentProjectId),
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-blue-100">
            <Database className="h-8 w-8 text-blue-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Episodic Memory</h1>
              <ScopeBadge scope="project" projectName={currentProject?.name} />
            </div>
            <p className="text-muted-foreground mt-1">
              Event storage with spatial-temporal grounding
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Events</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_events || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Quality Score</div>
          <div className={`text-2xl font-bold ${getScoreColor(stats?.quality_score || 0)}`}>
            {((stats?.quality_score || 0) * 100).toFixed(1)}%
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Time Span</div>
          <div className="text-2xl font-bold">{stats?.time_span_days || 0} days</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Earliest Event</div>
          <div className="text-sm font-medium">
            {stats?.earliest ? formatRelativeTime(stats.earliest) : 'N/A'}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {stats?.earliest ? formatDate(stats.earliest) : ''}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-card border rounded-lg p-4">
        <div className="flex items-center space-x-4">
          <Filter className="h-5 w-5 text-muted-foreground" />
          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Limit</label>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value={50}>50 events</option>
                <option value={100}>100 events</option>
                <option value={500}>500 events</option>
                <option value={1000}>1000 events</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Session ID</label>
              <input
                type="text"
                value={sessionFilter}
                onChange={(e) => setSessionFilter(e.target.value)}
                placeholder="Filter by session..."
                className="w-full px-3 py-2 border rounded-md bg-background"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={() => {
                  setSessionFilter('')
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

      {/* Events Table */}
      <div className="bg-card border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">
            Events ({eventsData?.total || 0})
          </h3>
          <button className="flex items-center space-x-2 px-3 py-2 border rounded-md hover:bg-accent transition-colors text-sm">
            <Download className="h-4 w-4" />
            <span>Export</span>
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : eventsData?.events && eventsData.events.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Timestamp
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Content
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Importance
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Session
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {eventsData.events.map((event) => (
                  <tr key={event.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 text-sm font-mono">{event.id}</td>
                    <td className="px-4 py-3 text-sm">
                      <div>{formatRelativeTime(event.timestamp)}</div>
                      <div className="text-xs text-muted-foreground">
                        {formatDate(event.timestamp)}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-secondary">
                        {event.event_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm max-w-md">
                      <div className="line-clamp-2">{event.content}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className={`text-sm font-medium ${getScoreColor(event.importance_score)}`}>
                        {(event.importance_score * 100).toFixed(0)}%
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-muted-foreground">
                      {event.session_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-3">
                      {event.lifecycle_status && (
                        <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800">
                          {event.lifecycle_status}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No events found</p>
          </div>
        )}
      </div>
    </div>
  )
}
