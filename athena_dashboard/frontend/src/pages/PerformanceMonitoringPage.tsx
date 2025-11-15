/**
 * Performance Monitoring Dashboard
 * Tracks system performance metrics including CPU, memory, query latency, and health indicators
 */

import { Card, Stat, Badge, RefreshButton } from '@/components/common'
import { GaugeChart } from '@/components/charts/GaugeChart'
import { TimeSeriesChart } from '@/components/charts/TimeSeriesChart'
import { BarChart } from '@/components/charts/BarChart'
import { useRealtimeData } from '@/hooks'
import { useProject } from '@/context/ProjectContext'
import { useState } from 'react'

interface PerformanceMetric {
  timestamp: string
  cpuUsage: number
  memoryUsage: number
  queryLatency: number
  apiResponseTime: number
}

interface SystemPerformance {
  current: {
    cpuUsage: number
    memoryUsage: number
    memoryAvailable: number
    queryLatency: number
    apiResponseTime: number
    activeConnections: number
    diskUsage: number
  }
  trends: PerformanceMetric[]
  topQueries: Array<{
    name: string
    avgLatency: number
    count: number
  }>
  alerts: Array<{
    id: string
    level: 'info' | 'warning' | 'critical'
    message: string
    timestamp: string
  }>
  health: {
    status: 'healthy' | 'warning' | 'critical'
    score: number
    components: {
      cpu: 'ok' | 'warning' | 'critical'
      memory: 'ok' | 'warning' | 'critical'
      database: 'ok' | 'warning' | 'critical'
      api: 'ok' | 'warning' | 'critical'
    }
  }
}

const getHealthColor = (status: string) => {
  switch (status) {
    case 'ok':
      return 'text-green-400'
    case 'warning':
      return 'text-yellow-400'
    case 'critical':
      return 'text-red-400'
    default:
      return 'text-gray-400'
  }
}

const getAlertColor = (level: string) => {
  switch (level) {
    case 'info':
      return 'bg-blue-900/20 border-blue-700 text-blue-300'
    case 'warning':
      return 'bg-yellow-900/20 border-yellow-700 text-yellow-300'
    case 'critical':
      return 'bg-red-900/20 border-red-700 text-red-300'
    default:
      return 'bg-gray-900/20 border-gray-700 text-gray-300'
  }
}

export const PerformanceMonitoringPage = () => {
  const { selectedProject } = useProject()
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h'>('6h')

  const apiUrl = selectedProject
    ? `/api/performance/metrics?project_id=${selectedProject.id}&range=${timeRange}`
    : `/api/performance/metrics?range=${timeRange}`

  const { data, loading, error, refetch, isConnected } = useRealtimeData<SystemPerformance>({
    url: apiUrl,
    pollInterval: 5000,
    dependencies: [selectedProject?.id, timeRange],
    enabled: true,
  })

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-800 rounded w-1/4" />
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-800 rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold text-gray-50 mb-2">Performance Monitoring</h1>
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 text-red-300">
          {error?.message || 'Failed to load performance metrics'}
        </div>
      </div>
    )
  }

  const cpuPercentage = Math.round(data.current.cpuUsage)
  const memoryPercentage = Math.round(data.current.memoryUsage)
  const healthScore = Math.round(data.health.score * 100)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-50">Performance Monitoring</h1>
          <p className="text-gray-400">System metrics and performance indicators</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2 bg-gray-800 rounded-lg p-1">
            {(['1h', '6h', '24h'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  timeRange === range
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
          <RefreshButton onRefresh={refetch} isConnected={isConnected} isLoading={loading} />
        </div>
      </div>

      {/* System Health Status Bar */}
      <Card className="bg-gradient-to-r from-gray-800/50 to-gray-800/30">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-gray-50">System Health</h3>
            <p className="text-sm text-gray-400">Overall system performance status</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-4xl font-bold text-gray-50">{healthScore}%</p>
              <Badge
                variant={
                  data.health.status === 'healthy'
                    ? 'success'
                    : data.health.status === 'warning'
                      ? 'warning'
                      : 'error'
                }
              >
                {data.health.status}
              </Badge>
            </div>
          </div>
        </div>
      </Card>

      {/* Main Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* CPU Usage */}
        <Card className="flex flex-col items-center justify-center">
          <GaugeChart value={cpuPercentage} title="CPU Usage" color={cpuPercentage > 80 ? 'warning' : 'info'} />
        </Card>

        {/* Memory Usage */}
        <Card className="flex flex-col items-center justify-center">
          <GaugeChart
            value={memoryPercentage}
            title="Memory Usage"
            color={memoryPercentage > 80 ? 'warning' : 'info'}
          />
        </Card>

        {/* Query Latency */}
        <Card>
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-50">Query Latency</h3>
            <div>
              <p className="text-sm text-gray-400">Average (ms)</p>
              <p className="text-3xl font-bold text-gray-50">{Math.round(data.current.queryLatency)}</p>
            </div>
            <div className="text-xs text-gray-400 flex items-center gap-2">
              <span
                className={`inline-block w-2 h-2 rounded-full ${
                  data.current.queryLatency < 100 ? 'bg-green-400' : 'bg-yellow-400'
                }`}
              />
              {data.current.queryLatency < 100 ? 'Good' : 'Acceptable'}
            </div>
          </div>
        </Card>

        {/* API Response Time */}
        <Card>
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-50">API Response</h3>
            <div>
              <p className="text-sm text-gray-400">Average (ms)</p>
              <p className="text-3xl font-bold text-gray-50">{Math.round(data.current.apiResponseTime)}</p>
            </div>
            <div className="text-xs text-gray-400 flex items-center gap-2">
              <span
                className={`inline-block w-2 h-2 rounded-full ${
                  data.current.apiResponseTime < 200 ? 'bg-green-400' : 'bg-yellow-400'
                }`}
              />
              {data.current.apiResponseTime < 200 ? 'Excellent' : 'Good'}
            </div>
          </div>
        </Card>
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* CPU & Memory Trends */}
        <Card header={<h3 className="text-lg font-semibold text-gray-50">System Resource Trends</h3>}>
          <TimeSeriesChart
            data={data.trends}
            lines={[
              { key: 'cpuUsage', stroke: '#EF4444', name: 'CPU Usage (%)' },
              { key: 'memoryUsage', stroke: '#3B82F6', name: 'Memory Usage (%)' },
            ]}
            xAxisKey="timestamp"
          />
        </Card>

        {/* Query & API Performance */}
        <Card header={<h3 className="text-lg font-semibold text-gray-50">Performance Latency</h3>}>
          <TimeSeriesChart
            data={data.trends}
            lines={[
              { key: 'queryLatency', stroke: '#10B981', name: 'Query Latency (ms)' },
              { key: 'apiResponseTime', stroke: '#F59E0B', name: 'API Response (ms)' },
            ]}
            xAxisKey="timestamp"
          />
        </Card>
      </div>

      {/* Top Slow Queries */}
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Top Slow Queries</h3>}>
        {data.topQueries.length > 0 ? (
          <div className="space-y-3">
            {data.topQueries.map((query, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-700/30 rounded">
                <div className="flex-1">
                  <p className="text-gray-50 font-mono text-sm">{query.name}</p>
                  <p className="text-xs text-gray-400">{query.count} executions</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-orange-400">{Math.round(query.avgLatency)}ms</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-center py-4">No slow queries detected</p>
        )}
      </Card>

      {/* Health Components */}
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Component Health</h3>}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(data.health.components).map(([component, status]) => (
            <div key={component} className="p-4 bg-gray-700/30 rounded text-center">
              <p className="text-sm text-gray-400 capitalize mb-2">{component}</p>
              <p className={`text-lg font-semibold ${getHealthColor(status)} capitalize`}>{status}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* System Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-50">Memory Details</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">In Use</span>
                <span className="text-gray-50">{Math.round(data.current.memoryUsage)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Available</span>
                <span className="text-gray-50">{Math.round(data.current.memoryAvailable)} MB</span>
              </div>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-500"
                  style={{ width: `${data.current.memoryUsage}%` }}
                />
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-50">Disk Usage</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Used</span>
                <span className="text-gray-50">{Math.round(data.current.diskUsage)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Status</span>
                <Badge variant={data.current.diskUsage > 90 ? 'warning' : 'success'}>
                  {data.current.diskUsage > 90 ? 'Critical' : 'Healthy'}
                </Badge>
              </div>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full ${data.current.diskUsage > 90 ? 'bg-red-500' : 'bg-green-500'}`}
                  style={{ width: `${data.current.diskUsage}%` }}
                />
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-50">Active Connections</h3>
            <div className="space-y-3">
              <div className="text-4xl font-bold text-gray-50">{data.current.activeConnections}</div>
              <p className="text-sm text-gray-400">Current database connections</p>
              <div className="text-xs text-gray-500">
                Pool limit: 10 | Healthy utilization
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Active Alerts */}
      {data.alerts && data.alerts.length > 0 && (
        <Card header={<h3 className="text-lg font-semibold text-gray-50">Active Alerts</h3>}>
          <div className="space-y-2">
            {data.alerts.map((alert) => (
              <div key={alert.id} className={`p-3 rounded border ${getAlertColor(alert.level)}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold">{alert.message}</p>
                    <p className="text-xs opacity-75">{new Date(alert.timestamp).toLocaleString()}</p>
                  </div>
                  <Badge variant={alert.level === 'critical' ? 'error' : alert.level === 'warning' ? 'warning' : 'info'}>
                    {alert.level}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

export default PerformanceMonitoringPage
