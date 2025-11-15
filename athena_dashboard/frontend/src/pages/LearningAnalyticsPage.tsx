import { useProject } from '@/context/ProjectContext'
import { Card, Stat, RefreshButton } from '@/components/common'
import { TimeSeriesChart } from '@/components/charts/TimeSeriesChart'
import { useRealtimeData } from '@/hooks'

interface LearningResponse {
  stats: {
    avgEffectiveness: number
    strategiesLearned: number
    gapResolutions: number
    improvementTrend: number
  }
  learningCurve: Array<{ timestamp: string; effectiveness: number; learningRate: number }>
}

export const LearningAnalyticsPage = () => {
  const { selectedProject } = useProject()
  const apiUrl = selectedProject
    ? `/api/learning/analytics?project_id=${selectedProject.id}`
    : '/api/learning/analytics'
  const { data, loading, refetch, isConnected } = useRealtimeData<LearningResponse>({
    url: apiUrl,
    dependencies: [selectedProject?.id],
    pollInterval: 5000,
    enabled: true,
  })

  if (loading) return <div className="p-6 animate-pulse h-64 bg-gray-800 rounded" />

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-50">Learning Analytics</h1>
          <p className="text-gray-400">
            Strategy effectiveness and learning patterns
            {selectedProject && <span className="ml-2 text-blue-400">(Viewing: {selectedProject.name})</span>}
          </p>
        </div>
        <RefreshButton onRefresh={refetch} isConnected={isConnected} isLoading={loading} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Avg Effectiveness" value={`${Math.round(data?.stats.avgEffectiveness || 0)}%`} />
        <Stat label="Strategies" value={data?.stats.strategiesLearned.toString() || '0'} />
        <Stat label="Gaps Resolved" value={data?.stats.gapResolutions.toString() || '0'} />
        <Stat label="Improvement" value={`+${Math.round(data?.stats.improvementTrend || 0)}%`} />
      </div>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Learning Curve</h3>}>
        <TimeSeriesChart
          data={data?.learningCurve || []}
          lines={[
            { key: 'effectiveness', stroke: '#10B981', name: 'Effectiveness' },
            { key: 'learningRate', stroke: '#3B82F6', name: 'Learning Rate' }
          ]}
          xAxisKey="timestamp"
        />
      </Card>
    </div>
  )
}

export default LearningAnalyticsPage
