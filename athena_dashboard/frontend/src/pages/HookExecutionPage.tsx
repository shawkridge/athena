import { Card } from '@/components/common/Card'
import { Stat } from '@/components/common/Stat'
import { Badge } from '@/components/common/Badge'
import { TimeSeriesChart } from '@/components/charts/TimeSeriesChart'
import { useAPI } from '@/hooks'
import { useProject } from '@/context/ProjectContext'

interface HookStatus {
  name: string
  status: 'active' | 'idle' | 'error'
  executions: number
  avgLatency: number
  successRate: number
}

interface HookResponse {
  hooks: HookStatus[]
  metrics: Array<{ timestamp: string; latency: number; successRate: number }>
}

export const HookExecutionPage = () => {
  const { selectedProject } = useProject()

  const apiUrl = selectedProject
    ? `/api/hooks/status?project_id=${selectedProject.id}`
    : '/api/hooks/status'

  const { data, loading } = useAPI<HookResponse>(apiUrl, [selectedProject?.id])

  if (loading) return <div className="p-6 animate-pulse h-64 bg-gray-800 rounded" />

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Hook Execution Monitor</h1>
        <p className="text-gray-400">
          Track hook status, latency, and success rates
          {selectedProject && <span className="ml-2 text-blue-400">(Viewing: {selectedProject.name})</span>}
        </p>
      </div>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Performance Trends</h3>}>
        <TimeSeriesChart
          data={data?.metrics || []}
          lines={[{ key: 'latency', stroke: '#F59E0B', name: 'Latency (ms)' }]}
          xAxisKey="timestamp"
        />
      </Card>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Hook Status</h3>}>
        <div className="space-y-3">
          {data?.hooks.map((hook) => (
            <div key={hook.name} className="p-3 rounded bg-gray-700/30 flex items-center justify-between">
              <div>
                <p className="text-gray-50">{hook.name}</p>
                <p className="text-xs text-gray-400">{hook.executions} executions</p>
              </div>
              <div className="flex gap-3 items-center">
                <Badge variant={hook.status === 'active' ? 'success' : 'warning'}>{hook.status}</Badge>
                <div className="text-right">
                  <p className="text-sm font-mono text-gray-50">{Math.round(hook.avgLatency)}ms</p>
                  <p className="text-xs text-gray-400">{Math.round(hook.successRate)}%</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

export default HookExecutionPage
