import { Card } from '@/components/common/Card'
import { GaugeChart } from '@/components/charts/GaugeChart'
import { TimeSeriesChart } from '@/components/charts/TimeSeriesChart'
import { useAPI } from '@/hooks'
import { useProject } from '@/context/ProjectContext'

interface LayerHealth {
  name: string
  health: number
  status: 'healthy' | 'warning' | 'critical'
  itemCount: number
  queryTime: number
  lastUpdated: string
}

interface SystemHealthData {
  timestamp: string
  overallHealth: number
  databaseSize: number
  queryLatency: number
}

interface SystemHealthResponse {
  layers: LayerHealth[]
  metrics: SystemHealthData[]
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'healthy':
      return 'bg-green-900/30 text-green-300'
    case 'warning':
      return 'bg-yellow-900/30 text-yellow-300'
    case 'critical':
      return 'bg-red-900/30 text-red-300'
    default:
      return 'bg-gray-700 text-gray-300'
  }
}

export const SystemHealthPage = () => {
  const { selectedProject } = useProject()

  // Build URL with project_id if a project is selected
  const apiUrl = selectedProject
    ? `/api/system/health?project_id=${selectedProject.id}`
    : '/api/system/health'

  const { data, loading, error } = useAPI<SystemHealthResponse>(
    apiUrl,
    [selectedProject?.id]
  )

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-800 rounded w-1/4" />
          <div className="h-40 bg-gray-800 rounded" />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold text-gray-50 mb-2">System Health</h1>
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 text-red-300">
          {error?.message || 'Failed to load system health'}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">System Health</h1>
        <p className="text-gray-400">8-layer health overview and performance metrics</p>
      </div>

      {/* Overall Health Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="flex items-center justify-center">
          {data.metrics.length > 0 && (
            <GaugeChart
              value={data.metrics[data.metrics.length - 1].overallHealth}
              title="Overall Health"
              color={data.metrics[data.metrics.length - 1].overallHealth >= 80 ? 'success' : 'warning'}
            />
          )}
        </Card>

        <Card>
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-50">Database</h3>
            <div>
              <p className="text-sm text-gray-400">Size</p>
              <p className="text-2xl font-bold text-gray-50">
                {data.metrics[data.metrics.length - 1]?.databaseSize.toFixed(2) || '0'} MB
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-50">Performance</h3>
            <div>
              <p className="text-sm text-gray-400">Avg Query Time</p>
              <p className="text-2xl font-bold text-gray-50">
                {Math.round(data.metrics[data.metrics.length - 1]?.queryLatency || 0)} ms
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Performance Trend */}
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Performance Trend</h3>}>
        <TimeSeriesChart
          data={data.metrics}
          lines={[
            { key: 'overallHealth', stroke: '#10B981', name: 'Overall Health' },
            { key: 'queryLatency', stroke: '#F59E0B', name: 'Query Latency (ms)' },
          ]}
          xAxisKey="timestamp"
        />
      </Card>

      {/* Memory Layers */}
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Memory Layers Status</h3>}>
        <div className="space-y-4">
          {data.layers.map((layer) => (
            <div
              key={layer.name}
              className={`p-4 rounded-lg border ${
                layer.status === 'healthy'
                  ? 'border-green-700/50 bg-green-900/10'
                  : layer.status === 'warning'
                    ? 'border-yellow-700/50 bg-yellow-900/10'
                    : 'border-red-700/50 bg-red-900/10'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div>
                    <h4 className="font-semibold text-gray-50">{layer.name}</h4>
                    <p className="text-xs text-gray-400">{layer.itemCount} items</p>
                  </div>
                </div>
                <span
                  className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(layer.status)}`}
                >
                  {layer.status.charAt(0).toUpperCase() + layer.status.slice(1)}
                </span>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Health</span>
                  <div className="flex items-center gap-2">
                    <div className="h-2 bg-gray-700 rounded-full w-32 overflow-hidden">
                      <div
                        className={`h-full ${
                          layer.health >= 80
                            ? 'bg-green-500'
                            : layer.health >= 60
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                        }`}
                        style={{ width: `${layer.health}%` }}
                      />
                    </div>
                    <span className="text-gray-50 font-semibold w-12 text-right">
                      {Math.round(layer.health)}%
                    </span>
                  </div>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Avg Query Time</span>
                  <span className="text-gray-50">{Math.round(layer.queryTime)}ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Last Updated</span>
                  <span className="text-gray-50 text-xs">{layer.lastUpdated}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Alerts & Warnings */}
      {data.layers.some((l) => l.status !== 'healthy') && (
        <Card
          header={<h3 className="text-lg font-semibold text-gray-50">⚠️ Alerts</h3>}
          className="border-yellow-700/50 bg-yellow-900/10"
        >
          <div className="space-y-2">
            {data.layers
              .filter((l) => l.status !== 'healthy')
              .map((layer) => (
                <p key={layer.name} className="text-yellow-300 text-sm">
                  {layer.name} is {layer.status} (Health: {Math.round(layer.health)}%)
                </p>
              ))}
          </div>
        </Card>
      )}
    </div>
  )
}

export default SystemHealthPage
