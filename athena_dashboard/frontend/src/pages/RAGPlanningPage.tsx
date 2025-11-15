import { Card } from '@/components/common/Card'
import { Stat } from '@/components/common/Stat'
import { BarChartComponent } from '@/components/charts/BarChart'
import { useAPI } from '@/hooks'

interface RAGMetrics {
  avgQueryTime: number
  retrievalQuality: number
  planValidationRate: number
  verificationsPassed: number
}

interface RAGResponse {
  metrics: RAGMetrics
  queryPerformance: Array<{ strategy: string; avgTime: number }>
}

export const RAGPlanningPage = () => {
  const { data, loading } = useAPI<RAGResponse>('/api/rag/metrics')

  if (loading) return <div className="p-6 animate-pulse h-64 bg-gray-800 rounded" />

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">RAG & Planning</h1>
        <p className="text-gray-400">Retrieval quality and plan validation</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Query Time" value={`${Math.round(data?.metrics.avgQueryTime || 0)}ms`} />
        <Stat label="Retrieval Quality" value={`${Math.round(data?.metrics.retrievalQuality || 0)}%`} />
        <Stat label="Plan Validation" value={`${Math.round(data?.metrics.planValidationRate || 0)}%`} />
        <Stat label="Verified Plans" value={data?.metrics.verificationsPassed.toString() || '0'} />
      </div>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Query Strategy Performance</h3>}>
        <BarChartComponent
          data={data?.queryPerformance || []}
          bars={[{ key: 'avgTime', fill: '#3B82F6', name: 'Avg Time (ms)' }]}
          xAxisKey="strategy"
        />
      </Card>
    </div>
  )
}

export default RAGPlanningPage
