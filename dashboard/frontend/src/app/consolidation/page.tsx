'use client'

import { useQuery } from '@tantml:function_calls>
<invoke name="api" />
import { formatNumber, formatDate, formatRelativeTime } from '@/lib/utils'
import { Sparkles } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'

export default function ConsolidationPage() {
  const { data: stats } = useQuery({
    queryKey: ['consolidation-stats'],
    queryFn: api.getConsolidationStatistics,
  })

  const { data: historyData } = useQuery({
    queryKey: ['consolidation-history'],
    queryFn: () => api.getConsolidationHistory(20),
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-yellow-100">
            <Sparkles className="h-8 w-8 text-yellow-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Consolidation</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Pattern extraction and memory compression
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Patterns</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_patterns || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Runs</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_runs || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Compression Ratio</div>
          <div className="text-2xl font-bold text-green-600">
            {((stats?.compression_ratio || 0) * 100).toFixed(1)}%
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Last Run</div>
          <div className="text-sm font-medium">
            {stats?.last_run ? formatRelativeTime(stats.last_run) : 'Never'}
          </div>
        </div>
      </div>

      {/* Consolidation Status */}
      <div className="bg-card border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Consolidation Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <div className="text-sm text-muted-foreground mb-2">Events Consolidated</div>
            <div className="text-2xl font-bold">{formatNumber(stats?.events_consolidated || 0)}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {stats?.events_remaining || 0} remaining
            </div>
          </div>

          <div>
            <div className="text-sm text-muted-foreground mb-2">Patterns Extracted</div>
            <div className="text-2xl font-bold">{formatNumber(stats?.patterns_extracted || 0)}</div>
            <div className="text-xs text-muted-foreground mt-1">
              From {stats?.total_runs || 0} runs
            </div>
          </div>

          <div>
            <div className="text-sm text-muted-foreground mb-2">Memory Saved</div>
            <div className="text-2xl font-bold text-green-600">
              {((stats?.memory_saved_mb || 0)).toFixed(1)} MB
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {((stats?.compression_ratio || 0) * 100).toFixed(0)}% reduction
            </div>
          </div>
        </div>
      </div>

      {/* Consolidation History */}
      <div className="bg-card border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">
            Consolidation Runs ({historyData?.total || 0})
          </h3>
        </div>

        {historyData?.runs && historyData.runs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Run ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Started At
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Patterns Extracted
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {historyData.runs.map((run, index) => (
                  <tr key={run.id || index} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 text-sm font-mono">{run.id || index + 1}</td>
                    <td className="px-4 py-3 text-sm">
                      {run.started_at ? (
                        <div>
                          <div>{formatRelativeTime(run.started_at)}</div>
                          <div className="text-xs text-muted-foreground">
                            {formatDate(run.started_at)}
                          </div>
                        </div>
                      ) : (
                        'N/A'
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {run.status && (
                        <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${
                          run.status === 'completed' ? 'bg-green-100 text-green-800' :
                          run.status === 'running' ? 'bg-blue-100 text-blue-800' :
                          run.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {run.status}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium">
                      {formatNumber(run.patterns_extracted || 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Sparkles className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No consolidation runs found</p>
          </div>
        )}
      </div>

      {/* Pattern Statistics */}
      <div className="bg-card border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Pattern Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Temporal Patterns</span>
              <span className="text-sm font-medium">
                {formatNumber(stats?.temporal_patterns || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Behavioral Patterns</span>
              <span className="text-sm font-medium">
                {formatNumber(stats?.behavioral_patterns || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Workflow Patterns</span>
              <span className="text-sm font-medium">
                {formatNumber(stats?.workflow_patterns || 0)}
              </span>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Avg Pattern Confidence</span>
              <span className="text-sm font-medium">
                {((stats?.avg_pattern_confidence || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">High Confidence Patterns</span>
              <span className="text-sm font-medium text-green-600">
                {formatNumber(stats?.high_confidence_patterns || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Patterns Applied</span>
              <span className="text-sm font-medium">
                {formatNumber(stats?.patterns_applied || 0)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
