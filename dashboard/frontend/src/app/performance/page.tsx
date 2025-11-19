'use client'

import { useQuery } from '@tanstack/react-query'
import { Activity } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import api from '@/lib/api'

export default function PerformanceMetricsPage() {
  const { data: stats } = useQuery({
    queryKey: ['performance-stats'],
    queryFn: () => api.getPerformanceStatistics(),
  })

  const { data: metricsData } = useQuery({
    queryKey: ['performance-metrics'],
    queryFn: () => api.getPerformanceMetrics(100),
  })

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
        <h3 className="text-lg font-semibold mb-4">Recent Performance Metrics</h3>
        {metricsData?.metrics && metricsData.metrics.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b">
                <tr className="text-left text-sm text-muted-foreground">
                  <th className="pb-3 font-medium">Timestamp</th>
                  <th className="pb-3 font-medium">Operation</th>
                  <th className="pb-3 font-medium">Duration</th>
                  <th className="pb-3 font-medium">Memory</th>
                  <th className="pb-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {metricsData.metrics.map((metric: any, idx: number) => (
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Activity className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No performance metrics found</p>
            <p className="text-xs mt-1">Performance metrics will appear here once operations are tracked</p>
          </div>
        )}
      </div>
    </div>
  )
}
